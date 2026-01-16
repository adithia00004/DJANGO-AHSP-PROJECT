import json
import pytest

def test_tree_always_has_klasifikasi_key(client_logged, api_urls):
    r = client_logged.get(api_urls["tree"])
    assert r.status_code == 200
    j = r.json()
    assert "klasifikasi" in j  # key wajib

def test_custom_minimal_save_and_tree(client_logged, api_urls, build_payload):
    payload = build_payload(jobs=[{
        "source_type": "custom",
        "ordering_index": 1,
        "snapshot_uraian": "Pekerjaan Custom Satu",
        "snapshot_satuan": "m2",
    }])
    r = client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200, 207), r.content

    t = client_logged.get(api_urls["tree"]).json()
    assert t["ok"] is True
    assert len(t["klasifikasi"]) == 1
    sub = t["klasifikasi"][0]["sub"]; assert len(sub) == 1
    pkj = sub[0]["pekerjaan"]; assert len(pkj) == 1
    assert pkj[0]["snapshot_uraian"] == "Pekerjaan Custom Satu"
    assert pkj[0]["ordering_index"] == 1

def test_upsert_idempotent_preserves_ordering(client_logged, api_urls, build_payload):
    # buat 2 pekerjaan dengan ordering 1 & 2
    base = build_payload(jobs=[
        {"source_type":"custom","ordering_index":1,"snapshot_uraian":"A","snapshot_satuan":"u"},
        {"source_type":"custom","ordering_index":2,"snapshot_uraian":"B","snapshot_satuan":"u"},
    ])
    r1 = client_logged.post(api_urls["upsert"], data=json.dumps(base), content_type="application/json")
    assert r1.status_code in (200,207), r1.content
    # kirim ulang payload yg sama
    r2 = client_logged.post(api_urls["upsert"], data=json.dumps(base), content_type="application/json")
    assert r2.status_code in (200,207), r2.content

    t = client_logged.get(api_urls["tree"]).json()
    rows = t["klasifikasi"][0]["sub"][0]["pekerjaan"]
    assert [p["snapshot_uraian"] for p in rows] == ["A","B"]
    assert [p["ordering_index"] for p in rows] == [1,2]  # tetap

def test_ref_without_ref_id_returns_400(client_logged, api_urls, build_payload):
    bad = build_payload(jobs=[{
        "source_type": "ref", "ordering_index": 1
        # ref_id sengaja tidak dikirim
    }])
    r = client_logged.post(api_urls["upsert"], data=json.dumps(bad), content_type="application/json")
    assert r.status_code == 400
    j = r.json()
    assert any("ref_id" in e.get("path","") for e in j.get("errors", []))

def test_ref_modified_can_override_snapshot(client_logged, api_urls, build_payload, ahsp_ref):
    jobs = [{
        "source_type": "ref_modified",
        "ordering_index": 3,
        "ref_id": ahsp_ref.id,
        "snapshot_uraian": "Override Uraian",
        "snapshot_satuan": "ls",
    }]
    payload = build_payload(jobs=jobs)
    r = client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200, 207), r.content

    t = client_logged.get(api_urls["tree"]).json()
    pkj = t["klasifikasi"][0]["sub"][0]["pekerjaan"]
    # cari yang ordering_index=3
    row = next(x for x in pkj if x["ordering_index"] == 3)
    assert row["source_type"] == "ref_modified"
    assert row["ref_id"] == ahsp_ref.id
    assert row["snapshot_uraian"] == "Override Uraian"
    assert row["snapshot_satuan"] == "ls"

def test_upsert_delete_missing_items(client_logged, api_urls, build_payload):
    # seed satu pekerjaan
    seed = build_payload(jobs=[{
        "source_type":"custom","ordering_index":1,"snapshot_uraian":"TEMP","snapshot_satuan":"u"
    }])
    r1 = client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json")
    assert r1.status_code in (200,207)

    # kirim payload tanpa klasifikasi -> seharusnya membersihkan data proyek
    empty = {"klasifikasi": []}
    r2 = client_logged.post(api_urls["upsert"], data=json.dumps(empty), content_type="application/json")
    assert r2.status_code in (200,207)

    t = client_logged.get(api_urls["tree"]).json()
    assert t["klasifikasi"] == []
