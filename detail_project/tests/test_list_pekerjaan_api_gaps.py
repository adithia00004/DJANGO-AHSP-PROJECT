# detail_project/tests/test_list_pekerjaan_api_gaps.py
import json
import pytest


def _ok(resp):
    assert resp.status_code in (200, 201, 204), resp.content


def _get_tree(client, tree_url):
    r = client.get(tree_url)
    _ok(r)
    data = r.json()
    return data.get("klasifikasi", [])


def _assert_sorted_by_ordering(items):
    orders = [x.get("ordering_index") for x in items]
    assert orders == sorted(orders), f"Not sorted: {orders}"


@pytest.mark.django_db
def test_custom_without_uraian_returns_400_or_noop(client_logged, api_urls):
    """Negatif: custom tanpa snapshot_uraian.
    Prefer 400; kalau server longgar, minimal tidak membuat data."""
    payload = {
        "klasifikasi": [{
            "name": "K1", "ordering_index": 1,
            "sub": [{
                "name": "S1", "ordering_index": 1,
                "pekerjaan": [{
                    "source_type": "custom",
                    "ordering_index": 1,
                    # "snapshot_uraian": "MISSING",
                    "snapshot_satuan": "m2",
                }]
            }]
        }]
    }
    res = client_logged.post(
        api_urls["upsert"], data=json.dumps(payload), content_type="application/json"
    )
    if res.status_code >= 400:
        # ideal: ditolak
        assert res.status_code in (400, 422)
    else:
        # fallback: jika diterima, pastikan tidak ada pekerjaan tercipta
        T = _get_tree(client_logged, api_urls["tree"])
        assert not T or not T[0]["sub"] or not T[0]["sub"][0]["pekerjaan"]


@pytest.mark.django_db
def test_ref_bad_ref_id_type_400(client_logged, api_urls):
    """Negatif: ref_id bertipe string → harus 4xx."""
    payload = {
        "klasifikasi": [{
            "name": "K1", "ordering_index": 1,
            "sub": [{
                "name": "S1", "ordering_index": 1,
                "pekerjaan": [{
                    "source_type": "ref",
                    "ordering_index": 1,
                    "ref_id": "abc"  # salah tipe
                }]
            }]
        }]
    }
    r = client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert 400 <= r.status_code < 500, r.content


@pytest.mark.django_db
def test_ref_nonexistent_ref_id_400(client_logged, api_urls):
    """Negatif: ref_id tidak ada di DB → 4xx."""
    payload = {
        "klasifikasi": [{
            "name": "K1", "ordering_index": 1,
            "sub": [{
                "name": "S1", "ordering_index": 1,
                "pekerjaan": [{
                    "source_type": "ref",
                    "ordering_index": 1,
                    "ref_id": 99999999  # tidak ada
                }]
            }]
        }]
    }
    r = client_logged.post(api_urls["upsert"], data=json.dumps(payload), content_type="application/json")
    assert 400 <= r.status_code < 500, r.content


@pytest.mark.django_db
def test_delete_whole_sub(client_logged, api_urls):
    """Omit 1 Sub pada upsert → Sub + pekerjaan di dalamnya terhapus."""
    seed = {
        "klasifikasi": [{
            "name": "K1", "ordering_index": 1,
            "sub": [
                {"name": "A", "ordering_index": 1,
                 "pekerjaan": [{"source_type":"custom","ordering_index":1,"snapshot_uraian":"X","snapshot_satuan":"u"}]},
                {"name": "B", "ordering_index": 2,
                 "pekerjaan": [{"source_type":"custom","ordering_index":1,"snapshot_uraian":"Y","snapshot_satuan":"u"}]},
            ]
        }]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    T1 = _get_tree(client_logged, api_urls["tree"])
    K = T1[0]
    subA, subB = K["sub"][0], K["sub"][1]

    # Upsert hanya menyertakan Sub B (Sub A dihilangkan)
    upd = {
        "klasifikasi": [{
            "id": K["id"], "name": K["name"], "ordering_index": K["ordering_index"],
            "sub": [{
                "id": subB["id"], "name": subB["name"], "ordering_index": subB["ordering_index"],
                "pekerjaan": subB["pekerjaan"]
            }]
        }]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))

    T2 = _get_tree(client_logged, api_urls["tree"])
    assert len(T2[0]["sub"]) == 1
    assert T2[0]["sub"][0]["name"] == subB["name"]


@pytest.mark.django_db
def test_delete_whole_klas(client_logged, api_urls):
    """Omit 1 Klas pada upsert → Klas + seluruh Sub/pekerjaan terhapus."""
    seed = {
        "klasifikasi": [
            {"name":"K1","ordering_index":1,"sub":[
                {"name":"A","ordering_index":1,"pekerjaan":[
                    {"source_type":"custom","ordering_index":1,"snapshot_uraian":"X","snapshot_satuan":"u"}
                ]}
            ]},
            {"name":"K2","ordering_index":2,"sub":[
                {"name":"B","ordering_index":1,"pekerjaan":[
                    {"source_type":"custom","ordering_index":1,"snapshot_uraian":"Y","snapshot_satuan":"u"}
                ]}
            ]},
        ]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    T1 = _get_tree(client_logged, api_urls["tree"])
    assert len(T1) == 2

    # Upsert hanya menyertakan K2
    K2 = T1[1]
    upd = {"klasifikasi": [{
        "id": K2["id"], "name": K2["name"], "ordering_index": K2["ordering_index"],
        "sub": K2["sub"]
    }]}
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))

    T2 = _get_tree(client_logged, api_urls["tree"])
    assert len(T2) == 1
    assert T2[0]["name"] == "K2"


@pytest.mark.django_db
def test_tree_ordering_sorted(client_logged, api_urls):
    """/tree/ harus mengembalikan urutan ascending pada semua level."""
    seed = {
        "klasifikasi": [
            {"name":"K2","ordering_index":2,"sub":[
                {"name":"S2","ordering_index":2,"pekerjaan":[
                    {"source_type":"custom","ordering_index":2,"snapshot_uraian":"B2","snapshot_satuan":"u"},
                    {"source_type":"custom","ordering_index":1,"snapshot_uraian":"B1","snapshot_satuan":"u"},
                ]},
                {"name":"S1","ordering_index":1,"pekerjaan":[
                    {"source_type":"custom","ordering_index":2,"snapshot_uraian":"A2","snapshot_satuan":"u"},
                    {"source_type":"custom","ordering_index":1,"snapshot_uraian":"A1","snapshot_satuan":"u"},
                ]},
            ]},
            {"name":"K1","ordering_index":1,"sub":[
                {"name":"S1","ordering_index":1,"pekerjaan":[
                    {"source_type":"custom","ordering_index":2,"snapshot_uraian":"X2","snapshot_satuan":"u"},
                    {"source_type":"custom","ordering_index":1,"snapshot_uraian":"X1","snapshot_satuan":"u"},
                ]},
            ]},
        ]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    T = _get_tree(client_logged, api_urls["tree"])

    _assert_sorted_by_ordering(T)
    for K in T:
        _assert_sorted_by_ordering(K["sub"])
        for S in K["sub"]:
            _assert_sorted_by_ordering(S["pekerjaan"])


@pytest.mark.django_db
def test_page_and_api_404_for_missing_project(client_logged):
    """Semua endpoint menolak project_id yang tidak ada."""
    missing = 999999
    base = f"/detail_project/{missing}/list-pekerjaan/"
    upsert = f"/detail_project/api/project/{missing}/list-pekerjaan/upsert/"
    tree = f"/detail_project/api/project/{missing}/list-pekerjaan/tree/"

    assert client_logged.get(base).status_code == 404
    assert client_logged.get(tree).status_code == 404
    assert 400 <= client_logged.post(upsert, data=json.dumps({"klasifikasi":[]}),
                                     content_type="application/json").status_code < 500


@pytest.mark.django_db
def test_move_job_to_another_klas(client_logged, api_urls):
    """Pindah pekerjaan dari Sub di Klas A → Sub di Klas B (FK sub_klasifikasi berubah)."""
    seed = {
        "klasifikasi": [
            {"name":"K_A","ordering_index":1,"sub":[
                {"name":"SA","ordering_index":1,"pekerjaan":[
                    {"source_type":"custom","ordering_index":1,"snapshot_uraian":"PINDAH","snapshot_satuan":"u"}
                ]}
            ]},
            {"name":"K_B","ordering_index":2,"sub":[
                {"name":"SB","ordering_index":1,"pekerjaan":[]}
            ]},
        ]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(seed), content_type="application/json"))
    T1 = _get_tree(client_logged, api_urls["tree"])
    K_A, K_B = T1[0], T1[1]
    SA, SB = K_A["sub"][0], K_B["sub"][0]
    job = SA["pekerjaan"][0]

    # Upsert: pindahkan job (id sama) ke Sub SB di K_B
    upd = {
        "klasifikasi": [
            {"id":K_A["id"], "name":K_A["name"], "ordering_index":K_A["ordering_index"],
             "sub":[{"id":SA["id"], "name":SA["name"], "ordering_index":SA["ordering_index"], "pekerjaan":[]}]},
            {"id":K_B["id"], "name":K_B["name"], "ordering_index":K_B["ordering_index"],
             "sub":[{"id":SB["id"], "name":SB["name"], "ordering_index":SB["ordering_index"],
                     "pekerjaan":[{"id":job["id"], "source_type":"custom","ordering_index":job["ordering_index"],
                                   "snapshot_uraian":job["snapshot_uraian"], "snapshot_satuan":job["snapshot_satuan"]}]}]},
        ]
    }
    _ok(client_logged.post(api_urls["upsert"], data=json.dumps(upd), content_type="application/json"))
    T2 = _get_tree(client_logged, api_urls["tree"])

    # Pastikan SA kosong & SB berisi job yg sama
    SA2 = [s for s in T2 if s["id"] == K_A["id"]][0]["sub"][0]
    SB2 = [s for s in T2 if s["id"] == K_B["id"]][0]["sub"][0]
    assert SA2["pekerjaan"] == []
    assert len(SB2["pekerjaan"]) == 1
    assert SB2["pekerjaan"][0]["id"] == job["id"]
