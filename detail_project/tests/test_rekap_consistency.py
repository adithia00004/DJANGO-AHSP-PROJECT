import json
from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, HargaItemProject, VolumePekerjaan,
    ProjectPricing
)
from detail_project.services import compute_rekap_for_project


def _mk_project(owner, name="P1"):
    # Sesuaikan field wajib Project kamu (berdasarkan error sebelumnya)
    return Project.objects.create(
        owner=owner,
        nama=name,
        is_active=True,
        tahun_project=timezone.now().year,  # NOT NULL di env kamu
        anggaran_owner=Decimal("0"),        # NOT NULL di env kamu
    )


def _mk_harga(project, kategori, kode, uraian, satuan, harga):
    hip = HargaItemProject.objects.create(
        project=project, kategori=kategori, kode_item=kode,
        uraian=uraian, satuan=satuan, harga_satuan=Decimal(harga),
    )
    return hip


def _mk_klas_sub(project):
    """
    Buat (atau ambil) Klasifikasi/SubKlasifikasi minimal yang valid untuk project given.
    Deteksi nama field secara dinamis (mis. 'name' vs 'nama', 'code' vs 'kode'),
    dan isi field 'project' jika model memilikinya (banyak skema mewajibkan itu).
    """
    # Sudah ada sub untuk project ini?
    try:
        sub_existing = (SubKlasifikasi.objects
                        .select_related("klasifikasi")
                        .filter(klasifikasi__project=project)
                        .first())
        if sub_existing:
            return sub_existing.klasifikasi, sub_existing
    except Exception:
        # Kalau model SubKlasifikasi tidak punya hubungan ke 'project' melalui klasifikasi,
        # kita coba ambil apa pun yang ada.
        sub_any = SubKlasifikasi.objects.select_related("klasifikasi").first()
        if sub_any:
            return sub_any.klasifikasi, sub_any

    K = Klasifikasi
    S = SubKlasifikasi

    def pick_name_field(model):
        candidates = ("nama", "name", "title", "label")
        names = {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}
        for c in candidates:
            if c in names:
                return c
        return None

    def pick_code_field(model):
        candidates = ("kode", "code", "abbr", "slug")
        names = {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}
        for c in candidates:
            if c in names:
                return c
        return None

    def has_field(model, fname):
        try:
            model._meta.get_field(fname)
            return True
        except Exception:
            return False

    # Klasifikasi kwargs
    k_kwargs = {}
    k_name = pick_name_field(K)
    k_code = pick_code_field(K)
    if k_name: k_kwargs[k_name] = "Klas (auto)"
    if k_code: k_kwargs[k_code] = "KLAS-1"
    if has_field(K, "ordering_index"):
        k_kwargs.setdefault("ordering_index", 1)
    # PENTING: isi project jika field ada
    if has_field(K, "project"):
        k_kwargs["project"] = project

    klas = K.objects.create(**k_kwargs)

    # SubKlasifikasi kwargs
    s_kwargs = {"klasifikasi": klas}
    s_name = pick_name_field(S)
    s_code = pick_code_field(S)
    if s_name: s_kwargs[s_name] = "Sub (auto)"
    if s_code: s_kwargs[s_code] = "SUB-1"
    if has_field(S, "ordering_index"):
        s_kwargs.setdefault("ordering_index", 1)
    # Jika SubKlasifikasi juga punya FK project, isi sama
    if has_field(S, "project"):
        s_kwargs["project"] = project

    sub = S.objects.create(**s_kwargs)
    return klas, sub

def _mk_pekerjaan(project, sub=None, kode="CUST-0001", uraian="Pondasi", satuan="m3"):
    # cek apakah field sub_klasifikasi wajib
    sub_field = Pekerjaan._meta.get_field("sub_klasifikasi")
    if sub is None and not getattr(sub_field, "null", True):
        # kalau wajib, buatkan minimal via helper di atas
        _k, sub = _mk_klas_sub()

    kwargs = dict(
        project=project,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode=kode,
        snapshot_uraian=uraian,
        snapshot_satuan=satuan,
        ordering_index=1,
    )
    if sub is not None:
        kwargs["sub_klasifikasi"] = sub

    return Pekerjaan.objects.create(**kwargs)

def _add_detail(project, pkj, hip, kategori, kode, uraian, satuan, koef):
    return DetailAHSPProject.objects.create(
        project=project, pekerjaan=pkj, harga_item=hip,
        kategori=kategori, kode=kode, uraian=uraian, satuan=satuan,
        koefisien=Decimal(koef),
    )


def _sum_items(items, kategori):
    total = Decimal("0")
    for it in items:
        if it["kategori"] != kategori:
            continue
        kf = Decimal(str(it["koefisien"]))
        hs = Decimal(str(it.get("harga_satuan") or "0"))
        total += (kf * hs)
    return total


@pytest.mark.django_db
def test_rekap_matches_detail_no_override(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="p")
    client.login(username="u", password="p")
    p = _mk_project(user, "P Konsistensi")
    ProjectPricing.objects.create(project=p, markup_percent=Decimal("12.5"))

    _k, sub = _mk_klas_sub(p)
    pkj = _mk_pekerjaan(p, sub)

    # Harga master
    hip_tk   = _mk_harga(p, "TK",  "TK.0006", "Mandor",     "OH", "150000")
    hip_bhn  = _mk_harga(p, "BHN", "B.1870",  "Semen",      "Kg", "12000")
    hip_alt  = _mk_harga(p, "ALT", "ALT.0101","Alat Padat", "Jam","300000")
    hip_lain = _mk_harga(p, "LAIN","LAIN.1",  "Mobilisasi", "ls", "2000000")

    # Rincian (koef × harga)
    _add_detail(p, pkj, hip_tk,   "TK",  "TK.0006",  "Mandor",     "OH", "0.15")
    _add_detail(p, pkj, hip_bhn,  "BHN", "B.1870",   "Semen",      "Kg", "7.5")
    _add_detail(p, pkj, hip_alt,  "ALT", "ALT.0101", "Alat Padat", "Jam","0.1")
    _add_detail(p, pkj, hip_lain, "LAIN","LAIN.1",   "Mobilisasi", "ls", "0.05")

    VolumePekerjaan.objects.create(project=p, pekerjaan=pkj, quantity=Decimal("10"))

    # === API detail (untuk membangun ekspektasi) ===
    url_detail = reverse("detail_project:api_get_detail_ahsp", args=[p.id, pkj.id])
    d = client.get(url_detail).json()
    assert d["ok"] is True
    items = d["items"]
    A = _sum_items(items, "TK")
    B = _sum_items(items, "BHN")
    C = _sum_items(items, "ALT")
    D = _sum_items(items, "LAIN")  # "LAIN" kita tampilkan eksplisit
    E = A + B + C + D
    F = E * Decimal("0.125")       # 12.5%
    G = E + F
    vol = Decimal("10")
    TOT = G * vol

    # === API rekap (ringkas) ===
    url_rekap = reverse("detail_project:api_get_rekap_rab", args=[p.id])
    r = client.get(url_rekap).json()
    assert r["ok"] is True
    row = next(rr for rr in r["rows"] if rr["pekerjaan_id"] == pkj.id)

    def D_(x): return Decimal(str(x))

    assert D_(row["A"]) == A
    assert D_(row["B"]) == B
    assert D_(row["C"]) == C
    assert D_(row["LAIN"]) == D
    assert D_(row["E_base"]) == E
    assert D_(row["F"]).quantize(Decimal("0.01")) == F.quantize(Decimal("0.01"))
    assert D_(row["G"]).quantize(Decimal("0.01")) == G.quantize(Decimal("0.01"))
    assert D_(row["total"]).quantize(Decimal("0.01")) == TOT.quantize(Decimal("0.01"))

    # === Service juga konsisten ===
    srows = compute_rekap_for_project(p)
    srow = next(rr for rr in srows if rr["pekerjaan_id"] == pkj.id)
    assert D_(srow["E_base"]) == E
    assert D_(srow["G"]).quantize(Decimal("0.01")) == G.quantize(Decimal("0.01"))


@pytest.mark.django_db
def test_rekap_matches_detail_with_override(client, django_user_model):
    user = django_user_model.objects.create_user(username="u2", password="p2")
    client.login(username="u2", password="p2")
    p = _mk_project(user, "P Override")
    ProjectPricing.objects.create(project=p, markup_percent=Decimal("10.00"))  # default 10%

    _k, sub = _mk_klas_sub(p) 
    pkj = _mk_pekerjaan(p, sub)

    hip_tk   = _mk_harga(p, "TK",  "TK.0008", "Pekerja",    "OH", "125000")
    hip_bhn  = _mk_harga(p, "BHN", "B.1210",  "Pasir Beton","m3", "180000")
    hip_alt  = _mk_harga(p, "ALT", "ALT.X",   "Alat X",     "Jam","300000")
    hip_lain = _mk_harga(p, "LAIN","LAIN.2",  "Lain-lain",  "ls", "1000000")

    _add_detail(p, pkj, hip_tk,   "TK",  "TK.0008",  "Pekerja",    "OH", "1.25")
    _add_detail(p, pkj, hip_bhn,  "BHN", "B.1210",   "Pasir Beton","m3", "0.30")
    _add_detail(p, pkj, hip_alt,  "ALT", "ALT.X",    "Alat X",     "Jam","0.10")
    _add_detail(p, pkj, hip_lain, "LAIN","LAIN.2",   "Lain-lain",  "ls", "0.05")

    VolumePekerjaan.objects.create(project=p, pekerjaan=pkj, quantity=Decimal("2"))

    # override BUK per-pekerjaan = 20%
    Pekerjaan.objects.filter(pk=pkj.pk).update(markup_override_percent=Decimal("20"))

    # hitung ekspektasi dari detail
    url_detail = reverse("detail_project:api_get_detail_ahsp", args=[p.id, pkj.id])
    d = client.get(url_detail).json(); items = d["items"]
    A = _sum_items(items, "TK")
    B = _sum_items(items, "BHN")
    C = _sum_items(items, "ALT")
    D = _sum_items(items, "LAIN")
    E = A + B + C + D
    F = E * Decimal("0.20")
    G = E + F
    TOT = G * Decimal("2")

    # rekap harus pakai 20% (bukan 10%)
    url_rekap = reverse("detail_project:api_get_rekap_rab", args=[p.id])
    r = client.get(url_rekap).json()
    row = next(rr for rr in r["rows"] if rr["pekerjaan_id"] == pkj.id)

    def D_(x): return Decimal(str(x))

    assert float(row["markup_eff"]) == pytest.approx(20.0, abs=1e-9)
    assert D_(row["E_base"]) == E
    assert D_(row["F"]).quantize(Decimal("0.01")) == F.quantize(Decimal("0.01"))
    assert D_(row["G"]).quantize(Decimal("0.01")) == G.quantize(Decimal("0.01"))
    assert D_(row["total"]).quantize(Decimal("0.01")) == TOT.quantize(Decimal("0.01"))
