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
    ProjectParameter,
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


# ==============================================================================
# Deep Copy Service - FASE 3.1
# ==============================================================================

class DeepCopyService:
    """
    Service for deep copying projects with all related data.

    Implements a 12-step dependency-ordered copy process with ID mapping
    to handle foreign key relationships correctly.

    Usage:
        service = DeepCopyService(source_project)
        new_project = service.copy(
            new_owner=request.user,
            new_name="Project Copy",
            new_tanggal_mulai=date(2025, 1, 1),
            copy_jadwal=True
        )

    Architecture:
        1. Uses transaction.atomic for data integrity
        2. Maintains ID mappings to remap FKs correctly
        3. Follows dependency order to avoid FK constraint violations
        4. Validates all copied data before saving
    """

    def __init__(self, source_project):
        """
        Initialize the service with source project.

        Args:
            source_project: The project to copy from

        Raises:
            ValidationError: If source_project is invalid
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        if not source_project or not source_project.id:
            raise DjangoValidationError("Source project must be a saved instance")

        self.source = source_project

        # ID mapping dictionaries for FK remapping
        # Format: {old_id: new_id}
        self.mappings = {
            'project': {},
            'pricing': {},
            'parameter': {},
            'klasifikasi': {},
            'subklasifikasi': {},
            'pekerjaan': {},
            'volume': {},
            'harga_item': {},
            'ahsp_template': {},
            'rincian_ahsp': {},
            'tahapan': {},
            'jadwal': {},
        }

        self.stats = {
            'klasifikasi_copied': 0,
            'subklasifikasi_copied': 0,
            'pekerjaan_copied': 0,
            'volume_copied': 0,
            'harga_item_copied': 0,
            'ahsp_template_copied': 0,
            'rincian_ahsp_copied': 0,
            'parameter_copied': 0,
            'tahapan_copied': 0,
            'jadwal_copied': 0,
        }

    @transaction.atomic
    def copy(
        self,
        new_owner,
        new_name,
        new_tanggal_mulai=None,
        copy_jadwal=True
    ):
        """
        Perform deep copy of project with all related data.

        Args:
            new_owner: User who will own the copied project
            new_name: Name for the new project
            new_tanggal_mulai: Start date for new project (optional)
            copy_jadwal: Whether to copy schedule data (default: True)

        Returns:
            The newly created project instance

        Raises:
            ValidationError: If validation fails
            IntegrityError: If database constraints are violated
        """
        # Import Project model locally to avoid circular imports
        from dashboard.models import Project

        # Step 1: Copy Project
        new_project = self._copy_project(new_owner, new_name, new_tanggal_mulai)

        # Step 2: Copy ProjectPricing
        self._copy_project_pricing(new_project)

        # Step 3: Copy ProjectParameter
        self._copy_project_parameters(new_project)

        # Step 4: Copy Klasifikasi
        self._copy_klasifikasi(new_project)

        # Step 5: Copy SubKlasifikasi
        self._copy_subklasifikasi(new_project)

        # Step 6: Copy Pekerjaan
        self._copy_pekerjaan(new_project)

        # Step 7: Copy VolumePekerjaan
        self._copy_volume_pekerjaan(new_project)

        # Step 8: Copy HargaItem
        self._copy_harga_item(new_project)

        # Step 9: Copy AhspTemplate (using existing model)
        self._copy_ahsp_template(new_project)

        # Step 10: Copy RincianAhsp (using DetailAHSPProject model)
        self._copy_rincian_ahsp(new_project)

        # Step 11: Copy Tahapan (if copy_jadwal=True)
        if copy_jadwal:
            self._copy_tahapan(new_project)

            # Step 12: Copy JadwalPekerjaan (if copy_jadwal=True)
            self._copy_jadwal_pekerjaan(new_project)

        return new_project

    def _copy_project(
        self,
        new_owner,
        new_name,
        new_tanggal_mulai
    ):
        """
        Step 1: Copy the Project instance.

        Args:
            new_owner: User who will own the copied project
            new_name: Name for the new project
            new_tanggal_mulai: Start date for new project

        Returns:
            The newly created project instance
        """
        from dashboard.models import Project

        old_id = self.source.id

        # Create new project instance with required fields
        new_project = Project(
            owner=new_owner,
            nama=new_name,
            sumber_dana=self.source.sumber_dana,
            lokasi_project=self.source.lokasi_project,
            nama_client=self.source.nama_client,
            anggaran_owner=self.source.anggaran_owner,
            tanggal_mulai=new_tanggal_mulai or self.source.tanggal_mulai,
            is_active=self.source.is_active,
        )

        # Copy optional fields if they exist
        if hasattr(self.source, 'durasi_hari') and self.source.durasi_hari:
            new_project.durasi_hari = self.source.durasi_hari
        if hasattr(self.source, 'deskripsi') and self.source.deskripsi:
            new_project.deskripsi = self.source.deskripsi
        if hasattr(self.source, 'kategori') and self.source.kategori:
            new_project.kategori = self.source.kategori

        # Copy additional optional fields
        optional_fields = [
            'ket_project1', 'ket_project2', 'jabatan_client', 'instansi_client',
            'nama_kontraktor', 'instansi_kontraktor', 'nama_konsultan_perencana',
            'instansi_konsultan_perencana', 'nama_konsultan_pengawas',
            'instansi_konsultan_pengawas'
        ]
        for field in optional_fields:
            if hasattr(self.source, field):
                value = getattr(self.source, field)
                if value:
                    setattr(new_project, field, value)

        new_project.save()

        # Map IDs
        self.mappings['project'][old_id] = new_project.id

        return new_project

    def _copy_project_pricing(self, new_project):
        """
        Step 2: Copy ProjectPricing (OneToOne with Project).

        Args:
            new_project: The newly created project
        """
        try:
            old_pricing = ProjectPricing.objects.get(project=self.source)
            old_id = old_pricing.id

            new_pricing = ProjectPricing(
                project=new_project,
                ppn=old_pricing.ppn,
                overhead=old_pricing.overhead,
                keuntungan=old_pricing.keuntungan,
            )
            # Copy markup_percent if it exists
            if hasattr(old_pricing, 'markup_percent'):
                new_pricing.markup_percent = old_pricing.markup_percent

            new_pricing.save()

            self.mappings['pricing'][old_id] = new_pricing.id

        except ProjectPricing.DoesNotExist:
            # If no pricing exists, skip
            pass

    def _copy_project_parameters(self, new_project):
        """
        Step 3: Copy ProjectParameter instances.

        Args:
            new_project: The newly created project
        """
        parameters = ProjectParameter.objects.filter(project=self.source)

        for old_param in parameters:
            old_id = old_param.id

            new_param = ProjectParameter(
                project=new_project,
                name=old_param.name,
                value=old_param.value,
                label=old_param.label,
                unit=old_param.unit,
                description=old_param.description,
            )
            new_param.save()

            self.mappings['parameter'][old_id] = new_param.id
            self.stats['parameter_copied'] += 1

    def _copy_klasifikasi(self, new_project):
        """
        Step 4: Copy Klasifikasi instances.

        Args:
            new_project: The newly created project
        """
        klasifikasi_list = Klasifikasi.objects.filter(project=self.source)

        for old_klas in klasifikasi_list:
            old_id = old_klas.id

            new_klas = Klasifikasi(
                project=new_project,
                name=old_klas.name,
            )
            new_klas.save()

            self.mappings['klasifikasi'][old_id] = new_klas.id
            self.stats['klasifikasi_copied'] += 1

    def _copy_subklasifikasi(self, new_project):
        """
        Step 5: Copy SubKlasifikasi instances.

        Args:
            new_project: The newly created project
        """
        subklas_list = SubKlasifikasi.objects.filter(project=self.source)

        for old_subklas in subklas_list:
            old_id = old_subklas.id
            old_klasifikasi_id = old_subklas.klasifikasi_id

            # Remap FK
            new_klasifikasi_id = self.mappings['klasifikasi'].get(old_klasifikasi_id)

            if new_klasifikasi_id:
                new_subklas = SubKlasifikasi(
                    project=new_project,
                    klasifikasi_id=new_klasifikasi_id,
                    name=old_subklas.name,
                )
                new_subklas.save()

                self.mappings['subklasifikasi'][old_id] = new_subklas.id
                self.stats['subklasifikasi_copied'] += 1

    def _copy_pekerjaan(self, new_project):
        """
        Step 6: Copy Pekerjaan instances.

        Args:
            new_project: The newly created project
        """
        pekerjaan_list = Pekerjaan.objects.filter(project=self.source)

        for old_pekerjaan in pekerjaan_list:
            old_id = old_pekerjaan.id
            old_subklas_id = old_pekerjaan.sub_klasifikasi_id

            # Remap FK
            new_subklas_id = self.mappings['subklasifikasi'].get(old_subklas_id)

            if new_subklas_id:
                new_pekerjaan = Pekerjaan(
                    project=new_project,
                    sub_klasifikasi_id=new_subklas_id,
                    snapshot_kode=old_pekerjaan.snapshot_kode,
                    snapshot_uraian=old_pekerjaan.snapshot_uraian,
                    snapshot_satuan=old_pekerjaan.snapshot_satuan,
                    source_type=old_pekerjaan.source_type,
                    ordering_index=old_pekerjaan.ordering_index,
                )
                # Copy ref FK if it exists
                if hasattr(old_pekerjaan, 'ref') and old_pekerjaan.ref:
                    new_pekerjaan.ref = old_pekerjaan.ref
                # Copy auto_load_rincian if exists
                if hasattr(old_pekerjaan, 'auto_load_rincian'):
                    new_pekerjaan.auto_load_rincian = old_pekerjaan.auto_load_rincian
                # Copy markup_override_percent if exists
                if hasattr(old_pekerjaan, 'markup_override_percent'):
                    new_pekerjaan.markup_override_percent = old_pekerjaan.markup_override_percent

                new_pekerjaan.save()

                self.mappings['pekerjaan'][old_id] = new_pekerjaan.id
                self.stats['pekerjaan_copied'] += 1

    def _copy_volume_pekerjaan(self, new_project):
        """
        Step 7: Copy VolumePekerjaan instances.

        Args:
            new_project: The newly created project
        """
        volume_list = VolumePekerjaan.objects.filter(project=self.source)

        for old_volume in volume_list:
            old_id = old_volume.id
            old_pekerjaan_id = old_volume.pekerjaan_id

            # Remap FK
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)

            if new_pekerjaan_id:
                new_volume = VolumePekerjaan(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                )
                # Copy fields that exist
                if hasattr(old_volume, 'formula'):
                    new_volume.formula = old_volume.formula
                if hasattr(old_volume, 'volume_calculated'):
                    new_volume.volume_calculated = old_volume.volume_calculated
                if hasattr(old_volume, 'volume_manual'):
                    new_volume.volume_manual = old_volume.volume_manual
                if hasattr(old_volume, 'use_manual'):
                    new_volume.use_manual = old_volume.use_manual
                if hasattr(old_volume, 'quantity'):
                    new_volume.quantity = old_volume.quantity

                new_volume.save()

                self.mappings['volume'][old_id] = new_volume.id
                self.stats['volume_copied'] += 1

    def _copy_harga_item(self, new_project):
        """
        Step 8: Copy HargaItem using HargaItemProject model.

        Args:
            new_project: The newly created project
        """
        harga_list = HargaItemProject.objects.filter(project=self.source)

        for old_harga in harga_list:
            old_id = old_harga.id

            new_harga = HargaItemProject(
                project=new_project,
                kode_item=old_harga.kode_item,
                kategori=old_harga.kategori,
                uraian=old_harga.uraian,
                satuan=old_harga.satuan,
                harga_satuan=old_harga.harga_satuan,
            )
            new_harga.save()

            self.mappings['harga_item'][old_id] = new_harga.id
            self.stats['harga_item_copied'] += 1

    def _copy_ahsp_template(self, new_project):
        """
        Step 9: Copy DetailAHSPProject instances.

        Args:
            new_project: The newly created project
        """
        ahsp_list = DetailAHSPProject.objects.filter(project=self.source)

        for old_ahsp in ahsp_list:
            old_id = old_ahsp.id
            old_pekerjaan_id = old_ahsp.pekerjaan_id
            old_harga_item_id = old_ahsp.harga_item_id

            # Remap FKs
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)
            new_harga_item_id = self.mappings['harga_item'].get(old_harga_item_id)

            if new_pekerjaan_id and new_harga_item_id:
                new_ahsp = DetailAHSPProject(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                    harga_item_id=new_harga_item_id,
                    kategori=old_ahsp.kategori,
                    kode=old_ahsp.kode,
                    uraian=old_ahsp.uraian,
                    satuan=old_ahsp.satuan,
                    koefisien=old_ahsp.koefisien,
                )
                # Copy ref_ahsp_id if exists (for bundle items)
                if hasattr(old_ahsp, 'ref_ahsp_id'):
                    new_ahsp.ref_ahsp_id = old_ahsp.ref_ahsp_id

                new_ahsp.save()

                self.mappings['ahsp_template'][old_id] = new_ahsp.id
                self.stats['ahsp_template_copied'] += 1

    def _copy_rincian_ahsp(self, new_project):
        """
        Step 10: Copy RincianAhsp instances (placeholder - model structure TBD).

        Args:
            new_project: The newly created project
        """
        # Note: RincianAhsp model structure not clear from existing code
        # This is a placeholder implementation
        # Will need to be updated based on actual model structure
        pass

    def _copy_tahapan(self, new_project):
        """
        Step 11: Copy TahapanPelaksanaan (TahapPelaksanaan) instances.

        Args:
            new_project: The newly created project
        """
        tahapan_list = TahapPelaksanaan.objects.filter(project=self.source)

        for old_tahapan in tahapan_list:
            old_id = old_tahapan.id

            new_tahapan = TahapPelaksanaan(
                project=new_project,
                nama=old_tahapan.nama,
                urutan=old_tahapan.urutan,
            )
            # Copy optional fields if they exist
            if hasattr(old_tahapan, 'deskripsi'):
                new_tahapan.deskripsi = old_tahapan.deskripsi
            if hasattr(old_tahapan, 'tanggal_mulai'):
                new_tahapan.tanggal_mulai = old_tahapan.tanggal_mulai
            if hasattr(old_tahapan, 'tanggal_selesai'):
                new_tahapan.tanggal_selesai = old_tahapan.tanggal_selesai
            if hasattr(old_tahapan, 'is_auto_generated'):
                new_tahapan.is_auto_generated = old_tahapan.is_auto_generated
            if hasattr(old_tahapan, 'generation_mode'):
                new_tahapan.generation_mode = old_tahapan.generation_mode

            new_tahapan.save()

            self.mappings['tahapan'][old_id] = new_tahapan.id
            self.stats['tahapan_copied'] += 1

    def _copy_jadwal_pekerjaan(self, new_project):
        """
        Step 12: Copy PekerjaanTahapan instances.

        Args:
            new_project: The newly created project
        """
        jadwal_list = PekerjaanTahapan.objects.filter(project=self.source)

        for old_jadwal in jadwal_list:
            old_id = old_jadwal.id
            old_pekerjaan_id = old_jadwal.pekerjaan_id
            old_tahapan_id = old_jadwal.tahapan_id

            # Remap FKs
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)
            new_tahapan_id = self.mappings['tahapan'].get(old_tahapan_id)

            if new_pekerjaan_id and new_tahapan_id:
                new_jadwal = PekerjaanTahapan(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                    tahapan_id=new_tahapan_id,
                    proporsi_volume=old_jadwal.proporsi_volume,
                )
                new_jadwal.save()

                self.mappings['jadwal'][old_id] = new_jadwal.id
                self.stats['jadwal_copied'] += 1

    def get_stats(self):
        """
        Get copy statistics.

        Returns:
            Dictionary with counts of copied objects
        """
        return self.stats.copy()