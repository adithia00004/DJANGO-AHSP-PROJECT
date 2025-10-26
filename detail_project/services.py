# detail_project/services.py
from typing import Dict, List, Optional, Set
from django.db import transaction
from django.db.models import Sum, F as DJF, DecimalField, ExpressionWrapper
from decimal import Decimal
from collections import defaultdict
from django.db.models import Q
from .numeric import to_dp_str, DECIMAL_SPEC
from django.core.cache import cache

from .models import (
    Klasifikasi, 
    SubKlasifikasi, 
    Pekerjaan, 
    VolumePekerjaan,
    DetailAHSPProject, 
    HargaItemProject, 
    ProjectPricing, 
    TahapPelaksanaan,
    PekerjaanTahapan,
)

def invalidate_rekap_cache(project_or_id) -> None:
    """
    Hapus cache rekap untuk 1 project.
    Terima instance Project atau angka project_id.
    """
    try:
        pid = int(getattr(project_or_id, "id", project_or_id))
    except Exception:
        return
    cache.delete(f"rekap:{pid}:v1")
    cache.delete(f"rekap:{pid}:v2")  # tambahkan ini


# Import model referensi untuk cloning (aman bila app referensi belum siap saat makemigrations)
try:
    from referensi.models import AHSPReferensi, RincianReferensi  # type: ignore
except Exception:
    AHSPReferensi = None  # type: ignore
    RincianReferensi = None  # type: ignore


def _upsert_harga_item(project, kategori: str, kode_item: str, uraian: str, satuan: str | None):
    """
    Upsert master harga unik per proyek (tanpa mengubah harga_satuan).
    """
    obj, _created = HargaItemProject.objects.get_or_create(
        project=project, kode_item=kode_item,
        defaults=dict(kategori=kategori, uraian=uraian, satuan=satuan)
    )
    changed = False
    if obj.kategori != kategori:
        obj.kategori = kategori; changed = True
    if uraian and obj.uraian != uraian:
        obj.uraian = uraian; changed = True
    if (satuan or None) != obj.satuan:
        obj.satuan = satuan or None; changed = True
    if changed:
        obj.save(update_fields=["kategori", "uraian", "satuan", "updated_at"])
    return obj


def generate_custom_code(project) -> str:
    """
    Hasilkan kode otomatis untuk pekerjaan kustom: CUST-0001, CUST-0002, ...
    Unik 'secara praktis' per proyek (berbasis jumlah yang ada).
    """
    # Hitung yang sudah ada; +1 untuk nomor berikutnya
    n = Pekerjaan.objects.filter(project=project, source_type=Pekerjaan.SOURCE_CUSTOM).count() + 1
    return f"CUST-{n:04d}"


@transaction.atomic
def clone_ref_pekerjaan(
    project,
    sub: SubKlasifikasi,
    ref_obj,
    source_type: str,
    ordering_index: int,
    auto_load_rincian: bool = True,
    *,
    override_uraian: Optional[str] = None,
    override_satuan: Optional[str] = None,
) -> Pekerjaan:
    """
    Clone snapshot identitas pekerjaan dari AHSP referensi dan,
    bila auto_load_rincian=True, clone semua rincian ke DetailAHSPProject.

    Penyesuaian:
    - source_type == ref          → snapshot_kode = <kode_ref>
    - source_type == ref_modified → snapshot_kode = "mod.X-<kode_ref>" (X bertambah per proyek)
      dan boleh override uraian/satuan dari parameter.
    """
    # Siapkan snapshot_kode sesuai mode
    rid = getattr(ref_obj, 'id', None)
    kode_ref   = getattr(ref_obj, 'kode_ahsp', None) or (f"REF-{rid}" if rid is not None else "REF")
    uraian_ref = getattr(ref_obj, 'nama_ahsp', None) or (f"AHSP {rid}" if rid is not None else "AHSP")
    satuan_ref = getattr(ref_obj, 'satuan', None)

    if source_type == Pekerjaan.SOURCE_REF_MOD:
        # nomor bertambah per proyek berdasarkan jumlah ref_modified yang sudah ada
        x = Pekerjaan.objects.filter(project=project, source_type=Pekerjaan.SOURCE_REF_MOD).count() + 1
        snap_kode = f"mod.{x}-{kode_ref}" if kode_ref else None
    else:
        snap_kode = kode_ref

    snap_uraian = override_uraian if (source_type == Pekerjaan.SOURCE_REF_MOD and override_uraian) else uraian_ref
    snap_satuan = override_satuan if (source_type == Pekerjaan.SOURCE_REF_MOD and override_satuan) else satuan_ref

    # Snapshot identitas pekerjaan dari referensi
    pkj = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=source_type,
        ref=ref_obj if AHSPReferensi is not None else None,
        snapshot_kode=snap_kode,
        snapshot_uraian=snap_uraian,
        snapshot_satuan=snap_satuan,
        auto_load_rincian=auto_load_rincian,
        ordering_index=ordering_index,
    )

    # Muat rincian dari referensi jika diminta
    if auto_load_rincian and RincianReferensi is not None:
        rincian_qs = RincianReferensi.objects.filter(ahsp=ref_obj).order_by('id')
        bulk_details: List[DetailAHSPProject] = []
        for rr in rincian_qs:
            # Kategori sinkron dengan app referensi: TK/BHN/ALT/LAIN
            kategori = rr.kategori
            kode = rr.kode_item
            uraian = rr.uraian_item
            satuan = rr.satuan_item
            koef = rr.koefisien

            hip = _upsert_harga_item(project, kategori, kode, uraian, satuan)
            bulk_details.append(DetailAHSPProject(
                project=project,
                pekerjaan=pkj,
                harga_item=hip,
                kategori=kategori,
                kode=kode,
                uraian=uraian,
                satuan=satuan,
                koefisien=koef,
            ))
        if bulk_details:
            DetailAHSPProject.objects.bulk_create(bulk_details, ignore_conflicts=True)
    return pkj

def _get_markup_percent(project) -> Decimal:
    # ⬇️ Tambahkan import lokal ini
    from .models import ProjectPricing
    obj = ProjectPricing.objects.filter(project=project).first()
    if obj and obj.markup_percent is not None:
        return Decimal(str(obj.markup_percent))
    return Decimal("0.00")

def compute_rekap_for_project(project):
    key = f"rekap:{project.id}:v2"   # bump cache version
    data = cache.get(key)
    if data is not None:
        return data
    """
    Hitung komponen biaya per pekerjaan (pakai override Profit/Margin per-pekerjaan jika ada):
      A = Σ(TK), B = Σ(BHN), C = Σ(ALT), LAIN = Σ(LAIN)
      D = A+B+C  (kompat historis)
      E_base = A+B+C+LAIN
      F = E_base × markup_eff   (markup_eff = override% jika ada, else project Profit/Margin %)
      G = E_base + F            (HSP/unit sesudah markup)
      total = G × volume
    Nilai kompat:
      E (lama) diisi = F (margin) agar test lama tetap lolos,
      HSP = E_base (pra-markup) untuk konsistensi dengan halaman Volume & test.
    """
    # --- Ambil Profit/Margin default proyek (fallback 10.00)
    proj_markup = Decimal("0")
    try:
        pp = ProjectPricing.objects.filter(project=project).first()
        if pp and pp.markup_percent is not None:
            proj_markup = Decimal(pp.markup_percent)
    except Exception:
        pass

    # --- Agregasi nilai per kategori
    price = DJF('harga_item__harga_satuan')
    coef  = DJF('koefisien')
    nilai = ExpressionWrapper(coef * price, output_field=DecimalField(max_digits=20, decimal_places=2))

    base = (DetailAHSPProject.objects
            .filter(project=project)
            .values('pekerjaan_id', 'kategori')
            .annotate(jumlah=Sum(nilai)))

    kategori_keys = ['TK', 'BHN', 'ALT', 'LAIN']
    agg: Dict[int, Dict[str, float]] = {}
    for row in base:
        pkj_id = row['pekerjaan_id']
        kat    = row['kategori']
        if kat not in kategori_keys:
            continue
        agg.setdefault(pkj_id, {k: 0.0 for k in kategori_keys})
        agg[pkj_id][kat] = float(row['jumlah'] or 0.0)

    # --- Volume map
    vol_map = dict(VolumePekerjaan.objects
                   .filter(project=project)
                   .values_list('pekerjaan_id', 'quantity'))

    # --- Iterasi pekerjaan sekalian baca override
    result = []
    for p in (Pekerjaan.objects
              .filter(project=project)
              .order_by('ordering_index', 'id')
              .values('id', 'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan', 'markup_override_percent')):
        pkj_id   = p['id']
        A        = agg.get(pkj_id, {}).get('TK', 0.0)  or 0.0
        B        = agg.get(pkj_id, {}).get('BHN', 0.0) or 0.0
        C        = agg.get(pkj_id, {}).get('ALT', 0.0) or 0.0
        LAIN     = agg.get(pkj_id, {}).get('LAIN', 0.0) or 0.0

        D        = A + B + C
        E_base   = D + LAIN

        # --- effective markup: override jika ada, else project
        ov = p.get('markup_override_percent', None)
        mp = float(ov if ov is not None else proj_markup)   # persen (mis. 12.5)
        mp_frac = mp / 100.0

        F      = E_base * mp_frac
        G      = E_base + F
        volume = float(vol_map.get(pkj_id) or 0.0)
        total  = float(G) * volume

        result.append(dict(
            pekerjaan_id = pkj_id,
            kode         = p['snapshot_kode'],
            uraian       = p['snapshot_uraian'],
            satuan       = p['snapshot_satuan'],

            A=A, B=B, C=C, D=D,
            LAIN=LAIN,
            E_base=E_base,

            E=F,          # margin (kompat lama)
            F=F,          # margin eksplisit
            G=G,          # unit price sesudah markup

            HSP=E_base,       # ★ unit price pra-markup (dipakai beberapa test/halaman)
            unit_price=E_base,# alias aman untuk FE

            markup_eff=mp,    # persen efektif
            volume=volume,
            total=total,      # = G * volume
        ))
    cache.set(key, result, 300)  # 5 menit (atau sesuai kebutuhan)
    return result


def compute_kebutuhan_items(
    project, 
    mode='all', 
    tahapan_id=None, 
    filters=None
):
    """
    Compute rekap kebutuhan dengan support split volume dan filtering.
    
    Args:
        project: Project instance
        mode: str - 'all' | 'tahapan'
            - 'all': Semua pekerjaan (default)
            - 'tahapan': Filter berdasarkan tahapan tertentu
        tahapan_id: int - ID tahapan (required jika mode='tahapan')
        filters: dict - Additional filters:
            - klasifikasi_ids: list[int] - Filter by klasifikasi
            - sub_klasifikasi_ids: list[int] - Filter by sub-klasifikasi
            - kategori_items: list[str] - Filter by kategori item (TK/BHN/ALT/LAIN)
    
    Returns:
        list of dict: [{kategori, kode, uraian, satuan, quantity, metadata}, ...]
        
    Examples:
        # Semua pekerjaan
        >>> rows = compute_kebutuhan_items(project)
        
        # Tahapan tertentu
        >>> rows = compute_kebutuhan_items(project, mode='tahapan', tahapan_id=1)
        
        # Dengan filter klasifikasi
        >>> rows = compute_kebutuhan_items(
        ...     project, 
        ...     filters={'klasifikasi_ids': [1, 2]}
        ... )
        
        # Tahapan + filter kategori
        >>> rows = compute_kebutuhan_items(
        ...     project,
        ...     mode='tahapan',
        ...     tahapan_id=1,
        ...     filters={'kategori_items': ['TK', 'BHN']}
        ... )
    """
    # ========================================================================
    # STEP 1: Determine scope - pekerjaan mana yang akan di-aggregate
    # ========================================================================
    
    if mode == 'tahapan' and tahapan_id:
        # Mode tahapan: ambil pekerjaan dari tahapan tertentu dengan proporsi
        pt_qs = PekerjaanTahapan.objects.filter(
            tahapan_id=tahapan_id
        ).select_related('pekerjaan', 'tahapan')
        
        # Build dict: pekerjaan_id -> proporsi (dalam bentuk Decimal 0-1)
        pekerjaan_proporsi = {
            pt.pekerjaan_id: pt.proporsi_volume / Decimal('100')
            for pt in pt_qs
        }
        pekerjaan_ids = list(pekerjaan_proporsi.keys())
        
    else:
        # Mode 'all': semua pekerjaan dengan proporsi 100%
        pekerjaan_ids = list(
            Pekerjaan.objects.filter(project=project).values_list('id', flat=True)
        )
        pekerjaan_proporsi = {pk: Decimal('1.0') for pk in pekerjaan_ids}
    
    # ========================================================================
    # STEP 2: Apply additional filters (klasifikasi, sub-klasifikasi)
    # ========================================================================
    
    if filters:
        queryset = Pekerjaan.objects.filter(id__in=pekerjaan_ids)
        
        # Filter by klasifikasi
        if filters.get('klasifikasi_ids'):
            queryset = queryset.filter(
                sub_klasifikasi__klasifikasi_id__in=filters['klasifikasi_ids']
            )
        
        # Filter by sub-klasifikasi
        if filters.get('sub_klasifikasi_ids'):
            queryset = queryset.filter(
                sub_klasifikasi_id__in=filters['sub_klasifikasi_ids']
            )
        
        # Update pekerjaan_ids setelah filter
        pekerjaan_ids = list(queryset.values_list('id', flat=True))
    
    # Jika tidak ada pekerjaan dalam scope, return empty
    if not pekerjaan_ids:
        return []
    
    # ========================================================================
    # STEP 3: Get volume map untuk semua pekerjaan dalam scope
    # ========================================================================
    
    vol_map = dict(
        VolumePekerjaan.objects
        .filter(project=project, pekerjaan_id__in=pekerjaan_ids)
        .values_list('pekerjaan_id', 'quantity')
    )
    
    # ========================================================================
    # STEP 4: Aggregate items dengan proporsi volume
    # ========================================================================
    
    # Dictionary untuk agregasi: key = (kategori, kode, uraian, satuan)
    aggregated = defaultdict(Decimal)
    
    # Get all detail items untuk pekerjaan dalam scope
    details = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan_id__in=pekerjaan_ids
    ).select_related('harga_item').values(
        'pekerjaan_id', 
        'kategori', 
        'kode', 
        'uraian', 
        'satuan', 
        'koefisien', 
        'ref_ahsp_id'
    )
    
    # Kumpulkan ref_ahsp_id untuk bundle items (kategori LAIN)
    ahsp_ids = {d['ref_ahsp_id'] for d in details if d['ref_ahsp_id']}
    
    # Get bundle items dari RincianReferensi
    ref_map = {}
    if ahsp_ids and RincianReferensi is not None:
        ref_items = RincianReferensi.objects.filter(
            ahsp_id__in=ahsp_ids,
            kategori__in=['TK', 'BHN', 'ALT']
        ).values(
            'ahsp_id', 
            'kategori', 
            'kode_item', 
            'uraian_item', 
            'satuan_item', 
            'koefisien'
        )
        
        for r in ref_items:
            ref_map.setdefault(r['ahsp_id'], []).append(r)
    
    # Process each detail item
    for detail in details:
        pekerjaan_id = detail['pekerjaan_id']
        
        # Get volume dan proporsi
        volume_total = Decimal(str(vol_map.get(pekerjaan_id, 0) or 0))
        proporsi = pekerjaan_proporsi.get(pekerjaan_id, Decimal('1.0'))
        
        # Volume efektif dengan proporsi
        volume_efektif = volume_total * proporsi
        
        if volume_efektif == 0:
            continue
        
        kategori = detail['kategori']
        koefisien = Decimal(str(detail['koefisien'] or 0))
        
        # Handle bundle items (LAIN dengan ref_ahsp)
        if detail['ref_ahsp_id'] and kategori == 'LAIN':
            # Bundle: multiply with ref items
            multiplier = koefisien
            for ref_item in ref_map.get(detail['ref_ahsp_id'], []):
                key = (
                    ref_item['kategori'],
                    ref_item['kode_item'],
                    ref_item['uraian_item'],
                    ref_item['satuan_item']
                )
                ref_koef = Decimal(str(ref_item['koefisien']))
                qty = multiplier * ref_koef * volume_efektif
                aggregated[key] += qty
        
        # Handle normal items (TK/BHN/ALT)
        elif kategori in ('TK', 'BHN', 'ALT'):
            key = (
                kategori,
                detail['kode'],
                detail['uraian'],
                detail['satuan']
            )
            qty = koefisien * volume_efektif
            aggregated[key] += qty
    
    # ========================================================================
    # STEP 5: Apply kategori filter (jika ada)
    # ========================================================================
    
    if filters and filters.get('kategori_items'):
        allowed_kat = set(filters['kategori_items'])
        aggregated = {
            k: v for k, v in aggregated.items() 
            if k[0] in allowed_kat
        }
    
    # ========================================================================
    # STEP 6: Format output
    # ========================================================================
    
    rows = []
    for (kategori, kode, uraian, satuan), quantity in aggregated.items():
        # Format quantity dengan 6 decimal places, remove trailing zeros
        qty_str = f"{quantity:.6f}".rstrip('0').rstrip('.')
        
        rows.append({
            'kategori': kategori,
            'kode': kode or '-',
            'uraian': uraian or '-',
            'satuan': satuan or '-',
            'quantity': qty_str,  # String untuk display
            'quantity_decimal': quantity,  # Decimal untuk calculation
        })
    
    # ========================================================================
    # STEP 7: Sort output
    # ========================================================================
    
    # Sort by kategori (TK -> BHN -> ALT -> LAIN), then by kode
    kategori_order = {'TK': 1, 'BHN': 2, 'ALT': 3, 'LAIN': 4}
    rows.sort(key=lambda x: (
        kategori_order.get(x['kategori'], 99), 
        x['kode'] or '', 
        x['uraian'] or ''
    ))
    
    return rows



def get_tahapan_summary(project):
    """
    Get summary info untuk semua tahapan dalam project.
    
    Args:
        project: Project instance
    
    Returns:
        list of dict: Summary info per tahapan
        
    Example:
        [
            {
                'tahapan_id': 1,
                'nama': 'Tahap 1: Persiapan',
                'urutan': 1,
                'jumlah_pekerjaan': 3,
                'total_assigned_proportion': 300.00,  # 3 pekerjaan @ 100%
                'tanggal_mulai': '2025-01-01',
                'tanggal_selesai': '2025-01-15'
            },
            ...
        ]
    """
    tahapan_list = TahapPelaksanaan.objects.filter(
        project=project
    ).prefetch_related('pekerjaan_items').order_by('urutan', 'id')
    
    result = []
    for tahap in tahapan_list:
        # Count pekerjaan dan total proporsi
        assignments = tahap.pekerjaan_items.all()
        jumlah_pekerjaan = assignments.values('pekerjaan').distinct().count()
        total_proporsi = sum(a.proporsi_volume for a in assignments)
        
        result.append({
            'tahapan_id': tahap.id,
            'nama': tahap.nama,
            'urutan': tahap.urutan,
            'deskripsi': tahap.deskripsi,
            'jumlah_pekerjaan': jumlah_pekerjaan,
            'total_assigned_proportion': float(total_proporsi),
            'tanggal_mulai': tahap.tanggal_mulai.isoformat() if tahap.tanggal_mulai else None,
            'tanggal_selesai': tahap.tanggal_selesai.isoformat() if tahap.tanggal_selesai else None,
            'created_at': tahap.created_at.isoformat() if tahap.created_at else None,
            'is_auto_generated': tahap.is_auto_generated,
            'generation_mode': tahap.generation_mode,
        })
    
    return result


def get_unassigned_pekerjaan(project):
    """
    Get list pekerjaan yang belum fully assigned ke tahapan.
    
    Args:
        project: Project instance
    
    Returns:
        list of dict: Pekerjaan yang belum/partial assigned
        
    Example:
        [
            {
                'pekerjaan_id': 5,
                'kode': '1.1.1',
                'uraian': 'Galian Tanah',
                'assigned_proportion': 60.00,
                'unassigned_proportion': 40.00,
                'status': 'partial'  # 'unassigned' | 'partial'
            },
            ...
        ]
    """
    from django.db.models import Sum, F
    
    # Get all pekerjaan dengan total assigned proportion
    pekerjaan_qs = Pekerjaan.objects.filter(
        project=project
    ).annotate(
        total_assigned=Sum('tahapan_assignments__proporsi_volume')
    ).order_by('ordering_index', 'id')
    
    result = []
    for pkj in pekerjaan_qs:
        assigned = float(pkj.total_assigned or 0)
        unassigned = 100.0 - assigned
        
        # Skip jika fully assigned
        if abs(unassigned) < 0.01:
            continue
        
        # Determine status
        if assigned < 0.01:
            status = 'unassigned'
        else:
            status = 'partial'
        
        result.append({
            'pekerjaan_id': pkj.id,
            'kode': pkj.snapshot_kode,
            'uraian': pkj.snapshot_uraian,
            'assigned_proportion': assigned,
            'unassigned_proportion': unassigned,
            'status': status,
            'klasifikasi': (pkj.sub_klasifikasi.klasifikasi.name 
                        if pkj.sub_klasifikasi and pkj.sub_klasifikasi.klasifikasi 
                        else None),
            'sub_klasifikasi': (pkj.sub_klasifikasi.name 
                            if pkj.sub_klasifikasi 
                            else None),
        })
    
    return result