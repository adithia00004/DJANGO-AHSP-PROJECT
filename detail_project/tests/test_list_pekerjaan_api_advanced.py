# -*- coding: utf-8 -*-
import json
import pytest
from django.urls import reverse

def _ok(resp):
    assert resp.status_code in (200, 207), resp.content
    js = resp.json()
    assert js.get("ok") in (True, False)
    return js

def _get_tree(client, url_tree):
    r = client.get(url_tree)
    assert r.status_code == 200, r.content
    data = r.json()
    assert data.get("ok") is True
    return data["klasifikasi"]

def _flatten_pekerjaan(tree):
    for K in tree:
        for S in (K.get("sub") or []):
            for P in (S.get("pekerjaan") or []):
                yield (K, S, P)

@pytest.mark.django_db
def test_ref_create_success(client_logged, api_urls, build_payload, ahsp_ref):
    payload = build_payload(jobs=[{
        "source_type": "ref",
        "ordering_index": 1,
        "ref_id": ahsp_ref.id,
    }])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json"))

    tree = _get_tree(client_logged, api_urls["tree"])
    rows = list(_flatten_pekerjaan(tree))
    assert len(rows) == 1
    _, _, p = rows[0]
    assert p["source_type"] == "ref"
    assert p["ref_id"] == ahsp_ref.id
    assert (p.get("snapshot_uraian") or "").strip() != ""
    assert (p.get("snapshot_kode") or "").strip() != ""

@pytest.mark.django_db
def test_change_source_custom_to_ref(client_logged, api_urls, build_payload, ahsp_ref):
    seed = build_payload(jobs=[{
        "source_type": "custom", "ordering_index": 1, "snapshot_uraian": "C1", "snapshot_satuan": "u"
    }])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    tree1 = _get_tree(client_logged, api_urls["tree"])
    p_id = list(_flatten_pekerjaan(tree1))[0][2]["id"]

    upd = build_payload(jobs=[{
        "id": p_id, "source_type":"ref", "ordering_index": 1, "ref_id": ahsp_ref.id
    }])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))
    tree2 = _get_tree(client_logged, api_urls["tree"])
    p2 = list(_flatten_pekerjaan(tree2))[0][2]
    assert p2["source_type"] == "ref"
    assert p2["ref_id"] == ahsp_ref.id

@pytest.mark.django_db
def test_change_source_ref_to_custom(client_logged, api_urls, build_payload, ahsp_ref):
    seed = build_payload(jobs=[{
        "source_type":"ref", "ordering_index":1, "ref_id": ahsp_ref.id
    }])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    tree1 = _get_tree(client_logged, api_urls["tree"])
    p_id = list(_flatten_pekerjaan(tree1))[0][2]["id"]

    upd = build_payload(jobs=[{
        "id": p_id, "source_type":"custom", "ordering_index":1,
        "snapshot_uraian":"Jadi Custom", "snapshot_satuan":"ls"
    }])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))
    tree2 = _get_tree(client_logged, api_urls["tree"])
    p2 = list(_flatten_pekerjaan(tree2))[0][2]
    assert p2["source_type"] == "custom"
    assert p2["snapshot_uraian"] == "Jadi Custom"
    assert (p2.get("snapshot_kode") or "").strip() != ""

@pytest.mark.django_db
def test_rename_klasifikasi_and_sub(client_logged, api_urls, build_payload):
    seed = build_payload(
        jobs=[{"source_type":"custom","ordering_index":1,"snapshot_uraian":"X"}],
        klas_name="A", sub_name="A1"
    )
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    tree1 = _get_tree(client_logged, api_urls["tree"])
    K1 = tree1[0]; S1 = K1["sub"][0]

    upd = {
        "klasifikasi": [{
            "id": K1["id"], "name":"B", "ordering_index": K1["ordering_index"],
            "sub": [{
                "id": S1["id"], "name":"B1", "ordering_index": S1["ordering_index"],
                "pekerjaan": [{
                    "id": S1["pekerjaan"][0]["id"], "source_type":"custom", "ordering_index": S1["pekerjaan"][0]["ordering_index"],
                    "snapshot_uraian": S1["pekerjaan"][0]["snapshot_uraian"], "snapshot_satuan": S1["pekerjaan"][0]["snapshot_satuan"],
                }]
            }]
        }]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))
    tree2 = _get_tree(client_logged, api_urls["tree"])
    assert tree2[0]["name"] == "B"
    assert tree2[0]["sub"][0]["name"] == "B1"
    assert len(tree2) == 1 and len(tree2[0]["sub"]) == 1 and len(tree2[0]["sub"][0]["pekerjaan"]) == 1

@pytest.mark.django_db
def test_reorder_jobs_by_id_swap(client_logged, api_urls, build_payload):
    # Seed A (order=1) & B (order=2)
    seed = build_payload(jobs=[
        {"source_type":"custom","ordering_index":1,"snapshot_uraian":"A","snapshot_satuan":"u"},
        {"source_type":"custom","ordering_index":2,"snapshot_uraian":"B","snapshot_satuan":"u"},
    ])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    t1 = _get_tree(client_logged, api_urls["tree"])
    S = t1[0]["sub"][0]["pekerjaan"]
    id1, id2 = S[0]["id"], S[1]["id"]

    # Swap 3 tahap untuk menghindari unique(project_id, ordering_index)
    # 1) id1 -> 999
    tmp1 = build_payload(jobs=[
        {"id":id1,"source_type":"custom","ordering_index":999,"snapshot_uraian":"A","snapshot_satuan":"u"},
        {"id":id2,"source_type":"custom","ordering_index":2,  "snapshot_uraian":"B","snapshot_satuan":"u"},
    ])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(tmp1), content_type="application/json"))

    # 2) id2 -> 1
    tmp2 = build_payload(jobs=[
        {"id":id1,"source_type":"custom","ordering_index":999,"snapshot_uraian":"A","snapshot_satuan":"u"},
        {"id":id2,"source_type":"custom","ordering_index":1,  "snapshot_uraian":"B","snapshot_satuan":"u"},
    ])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(tmp2), content_type="application/json"))

    # 3) id1 -> 2
    tmp3 = build_payload(jobs=[
        {"id":id1,"source_type":"custom","ordering_index":2,"snapshot_uraian":"A","snapshot_satuan":"u"},
        {"id":id2,"source_type":"custom","ordering_index":1,"snapshot_uraian":"B","snapshot_satuan":"u"},
    ])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(tmp3), content_type="application/json"))

    t2 = _get_tree(client_logged, api_urls["tree"])
    P = t2[0]["sub"][0]["pekerjaan"]
    assert [p["snapshot_uraian"] for p in P] == ["B", "A"]

@pytest.mark.django_db
def test_reuse_by_order_adopt_tmp_preserves_id(client_logged, api_urls, build_payload, ahsp_ref, db):
    seed = build_payload(jobs=[{"source_type":"ref","ordering_index":1,"ref_id":ahsp_ref.id}])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    t1 = _get_tree(client_logged, api_urls["tree"])
    p1 = list(_flatten_pekerjaan(t1))[0][2]
    original_id = p1["id"]
    original_kode = p1.get("snapshot_kode")

    from referensi.models import AHSPReferensi
    refB = AHSPReferensi.objects.create(kode_ahsp="B-002", nama_ahsp="Ref B Uji")

    upd = build_payload(jobs=[{"source_type":"ref","ordering_index":1,"ref_id":refB.id}])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))
    t2 = _get_tree(client_logged, api_urls["tree"])
    p2 = list(_flatten_pekerjaan(t2))[0][2]
    assert p2["id"] == original_id
    assert p2.get("snapshot_kode") != original_kode

@pytest.mark.django_db
def test_move_job_to_another_sub(client_logged, api_urls, build_payload):
    # Seed 2 sub, job di A
    seed = {
        "klasifikasi": [{
            "name": "K1", "ordering_index": 1,
            "sub": [
                {"name": "A", "ordering_index": 1,
                 "pekerjaan": [{"source_type":"custom","ordering_index":1,"snapshot_uraian":"PINDAH","snapshot_satuan":"u"}]},
                {"name": "B", "ordering_index": 2, "pekerjaan": []},
            ]
        }]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    t1 = _get_tree(client_logged, api_urls["tree"])
    K = t1[0]; subA, subB = K["sub"][0], K["sub"][1]
    job = subA["pekerjaan"][0]

    # Pindah antar sub: lakukan "delete & create" (tanpa id di target)
    upd = {
        "klasifikasi": [{
            "id": K["id"], "name": K["name"], "ordering_index": K["ordering_index"],
            "sub": [
                {"id": subA["id"], "name": subA["name"], "ordering_index": subA["ordering_index"], "pekerjaan": []},
                {"id": subB["id"], "name": subB["name"], "ordering_index": subB["ordering_index"],
                 "pekerjaan": [{
                     "source_type":"custom","ordering_index": job["ordering_index"],
                     "snapshot_uraian": job["snapshot_uraian"], "snapshot_satuan": job["snapshot_satuan"]
                 }]},
            ]
        }]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))
    t2 = _get_tree(client_logged, api_urls["tree"])
    K2 = t2[0]
    assert K2["sub"][0]["pekerjaan"] == []
    assert len(K2["sub"][1]["pekerjaan"]) == 1
    assert K2["sub"][1]["pekerjaan"][0]["snapshot_uraian"] == "PINDAH"

@pytest.mark.django_db
def test_custom_snapshot_kode_autogenerated(client_logged, api_urls, build_payload):
    payload = build_payload(jobs=[{
        "source_type":"custom","ordering_index":1,"snapshot_uraian":"KODE?","snapshot_satuan":"u"
    }])
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json"))
    t = _get_tree(client_logged, api_urls["tree"])
    p = list(_flatten_pekerjaan(t))[0][2]
    assert (p.get("snapshot_kode") or "").strip() != ""

@pytest.mark.django_db
def test_http_methods_and_anonymous_access(client_logged, client, api_urls, build_payload):
    r = client_logged.get(api_urls["upsert"])
    assert r.status_code == 405

    r = client.get(api_urls["page"])
    assert r.status_code in (302, 301)
    assert "login" in (r.headers.get("Location") or "").lower()

    payload = build_payload(jobs=[])
    r = client.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (302, 401, 403)
