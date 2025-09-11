# detail_project/services.py
from typing import Dict, List, Optional
from django.db import transaction
from django.db.models import Sum, F, DecimalField, ExpressionWrapper

from .models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    DetailAHSPProject, HargaItemProject,
)

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
    kode_ref = getattr(ref_obj, 'kode_ahsp', None)
    uraian_ref = getattr(ref_obj, 'nama_ahsp', None)
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


def compute_rekap_for_project(project):
    """
    Hitung komponen biaya per pekerjaan:
    A = Σ(TK), B = Σ(BHN), C = Σ(ALT), D = A+B+C, E = 0 (placeholder margin),
    HSP = D+E, Total = HSP × Volume.
    Catatan: kategori LAIN sengaja diabaikan dari A/B/C/D.
    """
    price = F('harga_item__harga_satuan')
    coef = F('koefisien')
    nilai = ExpressionWrapper(coef * price, output_field=DecimalField(max_digits=20, decimal_places=2))

    base = (DetailAHSPProject.objects
            .filter(project=project)
            .values('pekerjaan_id', 'kategori')
            .annotate(jumlah=Sum(nilai)))

    # Peta pekerjaan -> {TK, BHN, ALT}
    kategori_keys = ['TK', 'BHN', 'ALT']
    agg: Dict[int, Dict[str, float]] = {}
    for row in base:
        pkj_id = row['pekerjaan_id']
        kat = row['kategori']
        # Skip kategori lain-lain dari komponen A/B/C/D
        if kat not in kategori_keys:
            continue
        agg.setdefault(pkj_id, {k: 0 for k in kategori_keys})
        agg[pkj_id][kat] = float(row['jumlah'] or 0)

    # Volume
    vol_map = dict(VolumePekerjaan.objects.filter(project=project).values_list('pekerjaan_id', 'quantity'))

    # Susun hasil berurut sesuai ordering_input
    result = []
    for pkj in Pekerjaan.objects.filter(project=project).order_by('ordering_index', 'id'):
        A = agg.get(pkj.id, {}).get('TK', 0) or 0
        B = agg.get(pkj.id, {}).get('BHN', 0) or 0
        C = agg.get(pkj.id, {}).get('ALT', 0) or 0
        D = (A or 0) + (B or 0) + (C or 0)
        E = 0  # TODO: margin global/override di masa depan
        HSP = (D or 0) + (E or 0)
        volume = float(vol_map.get(pkj.id) or 0)
        total = HSP * volume
        result.append(dict(
            pekerjaan_id=pkj.id,
            kode=pkj.snapshot_kode,
            uraian=pkj.snapshot_uraian,
            satuan=pkj.snapshot_satuan,
            A=A, B=B, C=C, D=D, E=E, HSP=HSP, volume=volume, total=total
        ))
    return result
