# detail_project/services.py
from typing import Dict, List, Optional
from django.db import transaction
from django.db.models import Sum, F as DJF, DecimalField, ExpressionWrapper
from decimal import Decimal
from collections import defaultdict
from .numeric import to_dp_str, DECIMAL_SPEC
from django.core.cache import cache

from .models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    DetailAHSPProject, HargaItemProject, ProjectPricing, 
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
    Hitung komponen biaya per pekerjaan (pakai override BUK per-pekerjaan jika ada):
      A = Σ(TK), B = Σ(BHN), C = Σ(ALT), LAIN = Σ(LAIN)
      D = A+B+C  (kompat historis)
      E_base = A+B+C+LAIN
      F = E_base × markup_eff   (markup_eff = override% jika ada, else project BUK %)
      G = E_base + F            (HSP/unit sesudah markup)
      total = G × volume
    Nilai kompat:
      E (lama) diisi = F (margin) agar test lama tetap lolos,
      HSP = E_base (pra-markup) untuk konsistensi dengan halaman Volume & test.
    """
    # --- Ambil BUK default proyek (fallback 10.00)
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


def compute_kebutuhan_items(project):
    """
    Rekap kebutuhan kuantitas per item (TK/BHN/ALT) untuk 1 project.
    Rumus:
      - Normal (TK/BHN/ALT): qty = koef_detail × volume
      - Bundle (CUSTOM.LAIN + ref_ahsp): qty = multiplier (koef LAIN) × koef_ref(item) × volume
    Baris LAIN non-bundle diabaikan.
    Hasil dikembalikan sebagai list dict terurut.
    """
    # 1) Volume map
    vol_map = dict(
        (pid, Decimal(str(qty)))
        for pid, qty in
        project.volume_list.values_list('pekerjaan_id', 'quantity')
    )

    # 2) Ambil semua detail (termasuk ref_ahsp_id)
    rows = (DetailAHSPProject.objects
            .filter(project=project)
            .values('pekerjaan_id', 'kategori', 'kode', 'uraian', 'satuan', 'koefisien', 'ref_ahsp_id'))

    # 3) Kumpulkan AHSP referensi dari baris LAIN (bundle)
    ahsp_ids = {r['ref_ahsp_id'] for r in rows if r['ref_ahsp_id']}

    ref_map = {}
    if ahsp_ids and RincianReferensi is not None:
        rqs = (RincianReferensi.objects
               .filter(ahsp_id__in=ahsp_ids, kategori__in=['TK', 'BHN', 'ALT'])
               .values('ahsp_id', 'kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien'))
        for r in rqs:
            ref_map.setdefault(r['ahsp_id'], []).append(r)

    # 4) Agregasi kuantitas
    agg = defaultdict(Decimal)
    for r in rows:
        volume = Decimal(str(vol_map.get(r['pekerjaan_id'], 0) or 0))
        if volume == 0:
            continue

        kat = r['kategori']
        if r['ref_ahsp_id'] and kat == 'LAIN':
            # Bundle
            m = Decimal(str(r['koefisien'] or 0))
            for i in ref_map.get(r['ref_ahsp_id'], []):
                key = (i['kategori'], i['kode_item'], i['uraian_item'], i['satuan_item'])
                agg[key] += m * Decimal(str(i['koefisien'])) * volume
        else:
            # Normal (hanya TK/BHN/ALT)
            if kat in ('TK', 'BHN', 'ALT'):
                key = (kat, r['kode'], r['uraian'], r['satuan'])
                agg[key] += Decimal(str(r['koefisien'] or 0)) * volume

    # 5) Kemas hasil (format dp = KOEF)
    dp = DECIMAL_SPEC["KOEF"].dp
    items = [
        dict(kategori=k, kode=code, uraian=ura, satuan=sat, quantity=to_dp_str(q, dp))
        for (k, code, ura, sat), q in agg.items()
        if q is not None
    ]

    # Urutkan: TK, BHN, ALT → lalu kode, uraian
    order_kat = {'TK': 0, 'BHN': 1, 'ALT': 2}
    items.sort(key=lambda x: (order_kat.get(x['kategori'], 99), str(x['kode'] or ''), str(x['uraian'] or '')))
    return items