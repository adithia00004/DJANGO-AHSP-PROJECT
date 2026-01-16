# detail_project/tests/test_list_pekerjaan_api_extra.py
import json
import pytest
from django.test import Client
from detail_project.models import Klasifikasi, SubKlasifikasi, Pekerjaan

# 1) Pre-flight: custom tanpa uraian -> 400
def test_upsert_preflight_custom_missing_uraian(client_logged, api_urls, build_payload):
    payload = build_payload(jobs=[{
        "source_type": "custom",
        "ordering_index": 1,
        # snapshot_uraian sengaja kosong
        "snapshot_satuan": "m"
    }])
    r = client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 400
    assert r.json().get("ok") is False

# 1b) Pre-flight: source_type invalid -> 400
def test_upsert_preflight_invalid_source_type(client_logged, api_urls, build_payload):
    payload = build_payload(jobs=[{
        "source_type": "oops",  # invalid
        "ordering_index": 1
    }])
    r = client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 400
    assert r.json().get("ok") is False

# 2) Ganti sumber dengan order sama: custom -> ref (adoption path)
def test_change_source_custom_to_ref_same_order_adopts(client_logged, api_urls, build_payload, ahsp_ref, db):
    # Step 1: custom @ order=1
    step1 = build_payload(jobs=[{
        "source_type": "custom",
        "ordering_index": 1,
        "snapshot_uraian": "Uji Custom",
        "snapshot_satuan": "u"
    }])
    r1 = client_logged.post(api_urls["upsert"], data=json.dumps(step1), content_type="application/json")
    assert r1.status_code in (200, 207)
    assert Pekerjaan.objects.count() == 1
    p1 = Pekerjaan.objects.first()
    assert p1.source_type == Pekerjaan.SOURCE_CUSTOM

    # Step 2: ganti jadi ref @ order=1 (harus tetap 1 record)
    step2 = build_payload(jobs=[{
        "source_type": "ref",
        "ordering_index": 1,
        "ref_id": ahsp_ref.id
    }])
    r2 = client_logged.post(api_urls["upsert"], data=json.dumps(step2), content_type="application/json")
    assert r2.status_code in (200, 207)
    assert Pekerjaan.objects.count() == 1
    p2 = Pekerjaan.objects.first()
    assert p2.source_type == Pekerjaan.SOURCE_REF
    # biasanya clone_ref_pekerjaan mengisi snapshot_kode; minimal tidak error

# 3) Upsert kosong menghapus Klas/Sub/Pekerjaan
def test_omitting_all_klas_deletes(client_logged, api_urls, build_payload, db):
    seed = build_payload(jobs=[{
        "source_type": "custom",
        "ordering_index": 1,
        "snapshot_uraian": "TEMP",
        "snapshot_satuan": "u"
    }])
    r1 = client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json")
    assert r1.status_code in (200, 207)
    assert Klasifikasi.objects.exists()
    assert SubKlasifikasi.objects.exists()
    assert Pekerjaan.objects.exists()

    empty = {"klasifikasi": []}
    r2 = client_logged.post(api_urls["upsert"], data=json.dumps(empty), content_type="application/json")
    assert r2.status_code == 200
    assert Klasifikasi.objects.count() == 0
    assert SubKlasifikasi.objects.count() == 0
    assert Pekerjaan.objects.count() == 0

# 4) Endpoint SAVE (full-create) dan 5) bentuk tree
def test_full_save_endpoint_creates_then_tree_matches(client_logged, api_urls, build_payload):
    payload = build_payload(jobs=[
        {"source_type":"custom","ordering_index":1,"snapshot_uraian":"A","snapshot_satuan":"m"},
        {"source_type":"custom","ordering_index":2,"snapshot_uraian":"B","snapshot_satuan":"m2"},
    ])
    r = client_logged.post(api_urls["save"], data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200, 207)
    js = r.json()
    assert js.get("ok") is True
    # id_map/summary boleh dicek sekilas
    assert "summary" in js

    t = client_logged.get(api_urls["tree"])
    assert t.status_code == 200
    data = t.json()
    assert data.get("ok") is True
    tree = data.get("klasifikasi") or []
    assert len(tree) >= 1
    subs = tree[0].get("sub") or []
    assert len(subs) >= 1
    jobs = subs[0].get("pekerjaan") or []
    assert len(jobs) == 2
    # 5) pastikan field penting tersedia
    for node in jobs:
        for key in ("id","source_type","ordering_index","snapshot_uraian","snapshot_satuan"):
            assert key in node

# 6) Owner-only: user lain dapat 404
def test_owner_access_only(client_logged, api_urls, django_user_model, db):
    # Buat user lain dengan menyesuaikan USERNAME_FIELD (email vs username)
    uname_field = getattr(django_user_model, "USERNAME_FIELD", "username")
    fields = {f.name for f in django_user_model._meta.get_fields()}

    if uname_field == "email":
        kwargs = {"email": "other@example.com"}
        # kalau field username masih ada tapi optional, biarkan kosong
    else:
        kwargs = {"username": "other"}
        if "email" in fields:
            kwargs["email"] = "other@example.com"

    other = django_user_model.objects.create_user(password="x", **kwargs)

    c2 = Client()
    c2.force_login(other)

    r = c2.get(api_urls["tree"])
    # akses project milik user lain harus ditolak
    assert r.status_code in (404, 403)