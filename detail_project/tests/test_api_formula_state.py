# detail_project/tests/test_api_formula_state.py
import json
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.apps import apps
from django.utils import timezone

from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan, VolumeFormulaState
)


# ---------------- Helpers ----------------
def _create_project_minimal(owner):
    """Coba membuat dashboard.Project dengan field minimal tanpa asumsi keras."""
    Project = apps.get_model("dashboard", "Project")
    # Deteksi field yang umum
    field_names = {f.name for f in Project._meta.get_fields() if getattr(f, "concrete", False) and not f.auto_created}
    data = {}
    if "owner" in field_names:
        data["owner"] = owner
    if "is_active" in field_names:
        data["is_active"] = True
    # Nama proyek (opsional, jika fieldnya ada & required)
    # coba 'nama' lalu 'name' (dua pola umum)
    if "nama" in field_names:
        data.setdefault("nama", "Test Project")
    if "name" in field_names:
        data.setdefault("name", "Test Project")

    # Tambah fallback untuk field non-nullable tanpa default (Char/Text/Bool/Int/Decimal/DateTime/Date)
    # NOTE: kita tidak akan membuat FK lain selain owner; jika required FK lain ada, kita gagal & skip test.
    for f in Project._meta.get_fields():
        if not getattr(f, "concrete", False) or f.auto_created:
            continue
        if getattr(f, "many_to_many", False):
            continue
        # FK?
        if getattr(f, "remote_field", None) is not None:
            # skip FK selain owner (sulit dipalsukan secara generik)
            if f.name == "owner":
                continue
            # jika FK required (null=False) tanpa default → tidak bisa dibuat generik
            if not getattr(f, "null", True):
                return None
            continue

        # Non-relational
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        if hasattr(f, "has_default") and f.has_default():
            continue
        if getattr(f, "null", False):
            continue  # nullable → tidak wajib diisi
        # Wajib? isi default generik jika belum terisi
        if f.name in data:
            continue
        from django.db import models as m
        if isinstance(f, (m.CharField, m.TextField)):
            data[f.name] = "T"
        elif isinstance(f, m.BooleanField):
            data[f.name] = True
        elif isinstance(f, m.IntegerField):
            data[f.name] = 1
        elif isinstance(f, m.DecimalField):
            data[f.name] = Decimal("0")
        elif isinstance(f, m.DateTimeField):
            data[f.name] = timezone.now()
        elif isinstance(f, m.DateField):
            data[f.name] = timezone.now().date()
        else:
            # tipe tidak dikenali & required → gagal
            return None

    try:
        return Project.objects.create(**data)
    except Exception:
        return None


def _json(resp):
    return json.loads(resp.content.decode("utf-8"))


# ---------------- Fixtures ----------------
@pytest.fixture
def api_tier1_setup(db, client_logged, user):
    """Setup data for API Tier1 tests"""
    # Buat Project minimal yang kompatibel dengan model 'dashboard.Project' milikmu.
    project = _create_project_minimal(owner=user)
    if project is None:
        pytest.skip(
            "Tidak bisa membuat dashboard.Project secara minimal. "
            "Tambahkan field default pada Project atau sesuaikan helper _create_project_minimal()."
        )

    # Buat hirarki dasar + 2 pekerjaan (custom) untuk project utama
    klas = Klasifikasi.objects.create(project=project, name="K1", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="S1", ordering_index=1)
    p1 = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0001", snapshot_uraian="Pekerjaan 1", snapshot_satuan="m2",
        ordering_index=1
    )
    p2 = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0002", snapshot_uraian="Pekerjaan 2", snapshot_satuan="m",
        ordering_index=2
    )

    # Project lain + 1 pekerjaan untuk uji cross-project reject
    other_project = _create_project_minimal(owner=user)
    px = None
    if other_project:
        klas2 = Klasifikasi.objects.create(project=other_project, name="KX", ordering_index=1)
        sub2 = SubKlasifikasi.objects.create(project=other_project, klasifikasi=klas2, name="SX", ordering_index=1)
        px = Pekerjaan.objects.create(
            project=other_project, sub_klasifikasi=sub2,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-X", snapshot_uraian="Pekerjaan X", snapshot_satuan="m",
            ordering_index=1
        )

    return {
        'project': project,
        'klas': klas,
        'sub': sub,
        'p1': p1,
        'p2': p2,
        'other_project': other_project,
        'px': px,
    }


# ---------------- Tests: Formula State ----------------
def test_formula_get_empty(client_logged, api_tier1_setup):
    """GET harus ok:true & items: []"""
    project = api_tier1_setup['project']
    url = reverse("detail_project:api_volume_formula_state", args=[project.id])

    r = client_logged.get(url)
    assert r.status_code == 200
    j = _json(r)
    assert j["ok"] is True
    assert j["items"] == []


def test_formula_post_upsert_and_get(client_logged, api_tier1_setup):
    """POST satu item → created=1"""
    project = api_tier1_setup['project']
    p1 = api_tier1_setup['p1']
    url = reverse("detail_project:api_volume_formula_state", args=[project.id])

    # POST satu item
    payload = {"items": [{"pekerjaan_id": p1.id, "raw": "=L*W*H", "is_fx": True}]}
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200
    j = _json(r)
    assert j["ok"] is True
    assert j["created"] == 1
    assert j["updated"] == 0
    assert j["errors"] == []

    # GET ulang → items berisi entri tadi
    r2 = client_logged.get(url)
    assert r2.status_code == 200
    j2 = _json(r2)
    assert j2["ok"] is True
    assert len(j2["items"]) == 1
    assert j2["items"][0]["pekerjaan_id"] == p1.id
    assert j2["items"][0]["raw"] == "=L*W*H"
    assert j2["items"][0]["is_fx"] is True


def test_formula_post_update_same_row(client_logged, api_tier1_setup):
    """Update raw & is_fx"""
    project = api_tier1_setup['project']
    p1 = api_tier1_setup['p1']
    url = reverse("detail_project:api_volume_formula_state", args=[project.id])

    # Create awal
    VolumeFormulaState.objects.create(project=project, pekerjaan=p1, raw="=A*B", is_fx=True)

    # Update raw & is_fx
    payload = {"items": [{"pekerjaan_id": p1.id, "raw": "123.456", "is_fx": False}]}
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200
    j = _json(r)
    assert j["ok"] is True
    assert j["created"] == 0
    assert j["updated"] == 1
    assert j["errors"] == []

    obj = VolumeFormulaState.objects.get(project=project, pekerjaan=p1)
    assert obj.raw == "123.456"
    assert obj.is_fx is False


def test_formula_post_cross_project_rejected(client_logged, api_tier1_setup):
    """Kirim pekerjaan milik other_project ke endpoint project utama → harus error"""
    project = api_tier1_setup['project']
    px = api_tier1_setup['px']

    if not px:
        pytest.skip("Project kedua tidak tersedia; melewati cross-project test.")

    url = reverse("detail_project:api_volume_formula_state", args=[project.id])
    payload = {"items": [{"pekerjaan_id": px.id, "raw": "=BAD", "is_fx": True}]}
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")

    # partial failure → status 400 hanya jika tidak ada yang tersimpan;
    # di sini semuanya invalid → 400
    assert r.status_code == 400
    j = _json(r)
    assert j["ok"] is False
    assert len(j["errors"]) >= 1


# ---------------- Tests: Tree Sanity ----------------
def test_tree_contains_pekerjaan(client_logged, api_tier1_setup):
    """Minimal ada satu klasifikasi dan pekerjaan yang kita buat"""
    project = api_tier1_setup['project']
    p1 = api_tier1_setup['p1']
    p2 = api_tier1_setup['p2']
    url = reverse("detail_project:api_get_list_pekerjaan_tree", args=[project.id])

    r = client_logged.get(url)
    assert r.status_code == 200
    j = _json(r)
    assert j["ok"] is True
    # minimal ada satu klasifikasi dan pekerjaan yang kita buat
    assert len(j["klasifikasi"]) >= 1

    # flatten pekerjaan ids
    ids = []
    for k in j["klasifikasi"]:
        for s in k.get("sub", []):
            ids += [p["id"] for p in s.get("pekerjaan", [])]
    assert p1.id in ids
    assert p2.id in ids


# ---------------- Tests: Volume Save (Partial + Normalisasi Angka) ----------------
def test_volume_partial_success_and_number_normalization(client_logged, api_tier1_setup):
    """
    - Kirim dua item: satu valid (p1: '1234,5'), satu invalid (pekerjaan lain project) → status 200 (partial)
    - Cek pembulatan HALF_UP ke 3dp
    """
    project = api_tier1_setup['project']
    p1 = api_tier1_setup['p1']
    px = api_tier1_setup['px']
    url = reverse("detail_project:api_save_volume_pekerjaan", args=[project.id])

    # invalid id → pakai pekerjaan milik project lain jika ada; kalau tidak, pakai id besar
    invalid_id = px.id if px else 9999999

    payload = {
        "items": [
            {"pekerjaan_id": p1.id, "quantity": "1234,5"},  # comma decimal → 1234.5
            {"pekerjaan_id": invalid_id, "quantity": "10"}
        ]
    }
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")

    # karena 1 tersimpan dan 1 error → 200
    assert r.status_code == 200
    j = _json(r)
    assert j["ok"] is True
    assert j["saved"] == 1
    assert len(j["errors"]) >= 1
    assert j["decimal_places"] == 3

    # Cek DB tersimpan dengan 3dp HALF_UP
    vp = VolumePekerjaan.objects.get(project=project, pekerjaan=p1)
    assert vp.quantity == Decimal("1234.500")


def test_volume_reject_negative_or_invalid(client_logged, api_tier1_setup):
    """Reject negative quantity"""
    project = api_tier1_setup['project']
    p2 = api_tier1_setup['p2']
    url = reverse("detail_project:api_save_volume_pekerjaan", args=[project.id])

    payload = {"items": [{"pekerjaan_id": p2.id, "quantity": "-1"}]}
    r = client_logged.post(url, data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 400
    j = _json(r)
    assert j["ok"] is False
    assert len(j["errors"]) >= 1
