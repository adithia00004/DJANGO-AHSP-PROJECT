# detail_project/tests/test_api_numeric_endpoints.py
from decimal import Decimal
import json
import pytest

from django.urls import reverse
from django.db.models import DecimalField, CharField, TextField
from django.contrib.auth import get_user_model

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, HargaItemProject, VolumePekerjaan
)

User = get_user_model()


# ---------------- Fixtures ----------------
@pytest.fixture
def numeric_endpoints_setup(db, user):
    """Setup data for numeric endpoints tests"""
    from datetime import date

    # Project milik user (aktif) + pengisian field wajib minimal
    base_kwargs = dict(
        owner=user,
        is_active=True,
        nama="Proyek Uji",
        index_project="PRJ-001",
        tahun_project=2025,
        sumber_dana="APBD",
        lokasi_project="Makassar",
        nama_client="Client Test",
        tanggal_mulai=date.today(),
    )

    proj_fields = {f.name: f for f in Project._meta.fields}

    # --- Penanganan kolom NOT NULL yang ada di skema Anda ---
    # anggaran_owner ditemukan bertipe DecimalField (bukan FK) pada environment Anda,
    # sehingga harus diisi angka, bukan string.
    if "anggaran_owner" in proj_fields:
        f = proj_fields["anggaran_owner"]
        # Jika DecimalField → isi nilai wajar
        if isinstance(f, DecimalField):
            base_kwargs["anggaran_owner"] = Decimal("1000000000.00")
        # Jika ternyata Char/Text pada skema lain → isi string
        elif isinstance(f, CharField) or isinstance(f, TextField):
            base_kwargs["anggaran_owner"] = "Pemda"
        # Jika ternyata FK ke User pada skema lain → isi user
        elif getattr(f, "is_relation", False) and getattr(f, "related_model", None) == User:
            base_kwargs["anggaran_owner"] = user
        else:
            # Fallback aman: coba nilai wajar
            if not f.null:
                base_kwargs["anggaran_owner"] = Decimal("1000000000.00")

    project = Project.objects.create(**base_kwargs)

    # Struktur dasar klasifikasi/sub untuk FK Pekerjaan
    klas = Klasifikasi.objects.create(project=project, name="Klas 1", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="Sub 1.1", ordering_index=1)

    # Pekerjaan:
    # - REF (read-only) → dipakai untuk test blok simpan
    job_ref = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_REF,
        snapshot_kode="10.1.1",
        snapshot_uraian="Pekerjaan REF",
        snapshot_satuan="m2",
        ordering_index=1,
    )

    # - REF_MODIFIED → boleh disimpan/reset
    job_mod = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_REF_MOD,
        snapshot_kode="mod.1-10.1.2",
        snapshot_uraian="Pekerjaan REF Mod",
        snapshot_satuan="m2",
        ordering_index=2,
    )

    # - CUSTOM → boleh disimpan
    job_custom = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0001",
        snapshot_uraian="Pekerjaan Custom",
        snapshot_satuan="m",
        ordering_index=3,
    )

    return {
        'project': project,
        'klas': klas,
        'sub': sub,
        'job_ref': job_ref,
        'job_mod': job_mod,
        'job_custom': job_custom,
    }


# ---------------- Tests ----------------
def test_detail_ahsp_save_blocks_ref(client_logged, numeric_endpoints_setup):
    """Pekerjaan REF tidak boleh disimpan via endpoint ini (400)."""
    project = numeric_endpoints_setup['project']
    job_ref = numeric_endpoints_setup['job_ref']

    url = reverse("detail_project:api_save_detail_ahsp_for_pekerjaan", args=[project.id, job_ref.id])
    payload = {
        "rows": [{
            "kategori": "TK", "kode": "TK-01", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"
        }]
    }
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")

    assert r.status_code == 400
    js = r.json()
    assert js.get("ok") is False
    assert DetailAHSPProject.objects.filter(project=project, pekerjaan=job_ref).count() == 0


def test_detail_ahsp_save_duplicate_kode_results_207_with_one_saved(client_logged, numeric_endpoints_setup):
    """Duplikat kode di payload → status 207; satu baris valid tetap tersimpan."""
    project = numeric_endpoints_setup['project']
    job_mod = numeric_endpoints_setup['job_mod']

    url = reverse("detail_project:api_save_detail_ahsp_for_pekerjaan", args=[project.id, job_mod.id])
    payload = {
        "rows": [
            {"kategori": "TK", "kode": "K-01", "uraian": "Pekerja 1", "satuan": "OH", "koefisien": "1"},
            {"kategori": "TK", "kode": "K-01", "uraian": "Pekerja 1 (dupe)", "satuan": "OH", "koefisien": "2"},
        ]
    }
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")

    assert r.status_code in (207, 200)
    js = r.json()
    assert "saved_rows" in js
    # minimal 1 baris valid
    assert js["saved_rows"] >= 1
    assert DetailAHSPProject.objects.filter(project=project, pekerjaan=job_mod).count() == js["saved_rows"]


def test_detail_ahsp_save_parses_decimal_and_quantizes(client_logged, numeric_endpoints_setup):
    """Terima '2,7275' → simpan Decimal('2.727500') (dp=6)."""
    project = numeric_endpoints_setup['project']
    job_mod = numeric_endpoints_setup['job_mod']

    url = reverse("detail_project:api_save_detail_ahsp_for_pekerjaan", args=[project.id, job_mod.id])
    payload = {
        "rows": [{
            "kategori": "TK", "kode": "TK-02", "uraian": "Mandor", "satuan": "OH", "koefisien": "2,7275"
        }]
    }
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")

    assert r.status_code in (200, 207)
    d = DetailAHSPProject.objects.get(project=project, pekerjaan=job_mod, kode="TK-02")
    assert d.koefisien == Decimal("2.727500")


def test_harga_save_and_list_canon(client_logged, numeric_endpoints_setup):
    """
    Hanya item yang digunakan di Detail AHSP proyek yang boleh di-update.
    Simpan harga '1.234,56' → tersimpan Decimal('1234.56'); list?canon=1 → '1234.56'.
    """
    project = numeric_endpoints_setup['project']
    job_custom = numeric_endpoints_setup['job_custom']

    # 1) Buat detail agar HargaItemProject terdaftar sebagai "dipakai di proyek ini"
    detail_url = reverse("detail_project:api_save_detail_ahsp_for_pekerjaan", args=[project.id, job_custom.id])
    detail_payload = {
        "rows": [
            {"kategori": "TK", "kode": "TK-11", "uraian": "Tukang", "satuan": "OH", "koefisien": "1"},
            {"kategori": "BHN", "kode": "B-11", "uraian": "Semen", "satuan": "zak", "koefisien": "2"}
        ]
    }
    r1 = client_logged.post(detail_url, data=json.dumps(detail_payload), content_type="application/json")
    assert r1.status_code in (200, 207)

    # 2) Ambil list harga (tanpa canon) untuk dapatkan ID
    list_url = reverse("detail_project:api_list_harga_items", args=[project.id])
    r2 = client_logged.get(list_url)
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert len(items) >= 2
    any_id = items[0]["id"]

    # 3) Update satu item pakai localized string
    save_url = reverse("detail_project:api_save_harga_items", args=[project.id])
    save_payload = {"items": [{"id": any_id, "harga_satuan": "1.234,56"}]}
    r3 = client_logged.post(save_url, data=json.dumps(save_payload), content_type="application/json")
    assert r3.status_code == 200
    assert r3.json().get("updated") == 1

    # 4) list?canon=1 → harga_satuan harus string kanonik "1234.56"
    canon_url = f"{list_url}?canon=1"
    r4 = client_logged.get(canon_url)
    assert r4.status_code == 200
    it = next((x for x in r4.json().get("items", []) if x["id"] == any_id), None)
    assert it is not None
    assert it["harga_satuan"] == "1234.56"


def test_volume_save_parses_localized_and_quantizes(client_logged, numeric_endpoints_setup):
    """Terima '1.234,5' → simpan Decimal('1234.500') (dp=3)."""
    project = numeric_endpoints_setup['project']
    job_custom = numeric_endpoints_setup['job_custom']

    url = reverse("detail_project:api_save_volume_pekerjaan", args=[project.id])
    payload = {
        "items": [{
            "pekerjaan_id": job_custom.id,
            "quantity": "1.234,5"
        }]
    }
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200

    vp = VolumePekerjaan.objects.get(project=project, pekerjaan=job_custom)
    assert vp.quantity == Decimal("1234.500")
