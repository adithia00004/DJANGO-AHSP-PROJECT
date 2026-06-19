"""N3 Opsi A: the upsert response must echo a COMPLETE temp_id -> id map.

The frontend stamps server ids back onto DOM rows by identity (temp_id) instead
of by position. For that to be safe the map must cover every node the client sent,
across all branches: create, update-by-id, and reuse. A missing entry would leave
a row without an id -> treated as new on the next save -> duplicate. These tests
pin map completeness/correctness for each branch.
"""
import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.views_api import api_upsert_list_pekerjaan


class ListPekerjaanIdMapN3ATests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_idmap_n3a",
            email="owner-idmap-n3a@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project IdMap",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

    def _upsert(self, payload):
        request = self.factory.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )
        request.user = self.owner
        resp = api_upsert_list_pekerjaan(request, self.project.id)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        return json.loads(resp.content.decode("utf-8"))

    def test_fresh_create_maps_every_temp_id_to_real_ids(self):
        body = self._upsert({
            "klasifikasi": [{
                "temp_id": "k_a", "name": "Klas A", "ordering_index": 1,
                "sub": [{
                    "temp_id": "s_a", "name": "Sub A", "ordering_index": 1,
                    "pekerjaan": [
                        {"temp_id": "p_1", "source_type": "custom", "ordering_index": 1,
                         "snapshot_uraian": "J1", "snapshot_satuan": "m2"},
                        {"temp_id": "p_2", "source_type": "custom", "ordering_index": 2,
                         "snapshot_uraian": "J2", "snapshot_satuan": "m2"},
                    ],
                }],
            }]
        })
        id_map = body["id_map"]
        self.assertEqual(set(id_map["klas"]), {"k_a"})
        self.assertEqual(set(id_map["sub"]), {"s_a"})
        self.assertEqual(set(id_map["pekerjaan"]), {"p_1", "p_2"})

        klas = Klasifikasi.objects.get(project=self.project, name="Klas A")
        sub = SubKlasifikasi.objects.get(project=self.project, name="Sub A")
        j1 = Pekerjaan.objects.get(project=self.project, snapshot_uraian="J1")
        j2 = Pekerjaan.objects.get(project=self.project, snapshot_uraian="J2")
        self.assertEqual(id_map["klas"]["k_a"], klas.id)
        self.assertEqual(id_map["sub"]["s_a"], sub.id)
        self.assertEqual(id_map["pekerjaan"]["p_1"], j1.id)
        self.assertEqual(id_map["pekerjaan"]["p_2"], j2.id)

    def test_update_existing_by_id_keeps_stable_mapping(self):
        first = self._upsert({
            "klasifikasi": [{
                "temp_id": "k_a", "name": "Klas A", "ordering_index": 1,
                "sub": [{
                    "temp_id": "s_a", "name": "Sub A", "ordering_index": 1,
                    "pekerjaan": [
                        {"temp_id": "p_1", "source_type": "custom", "ordering_index": 1,
                         "snapshot_uraian": "J1", "snapshot_satuan": "m2"},
                    ],
                }],
            }]
        })
        klas = Klasifikasi.objects.get(project=self.project, name="Klas A")
        sub = SubKlasifikasi.objects.get(project=self.project, name="Sub A")
        j1 = Pekerjaan.objects.get(project=self.project, snapshot_uraian="J1")

        second = self._upsert({
            "klasifikasi": [{
                "id": klas.id, "temp_id": "k_a", "name": "Klas A", "ordering_index": 1,
                "sub": [{
                    "id": sub.id, "temp_id": "s_a", "name": "Sub A", "ordering_index": 1,
                    "pekerjaan": [
                        {"id": j1.id, "temp_id": "p_1b", "source_type": "custom",
                         "ordering_index": 1, "snapshot_uraian": "J1 edited", "snapshot_satuan": "m2"},
                    ],
                }],
            }]
        })
        self.assertEqual(second["id_map"]["pekerjaan"]["p_1b"], j1.id)
        self.assertEqual(second["id_map"]["klas"]["k_a"], klas.id)
        self.assertEqual(second["id_map"]["sub"]["s_a"], sub.id)

    def test_reuse_path_maps_new_temp_id_to_surviving_row(self):
        self._upsert({
            "klasifikasi": [{
                "temp_id": "k_a", "name": "Klas A", "ordering_index": 1,
                "sub": [{
                    "temp_id": "s_a", "name": "Sub A", "ordering_index": 1,
                    "pekerjaan": [
                        {"temp_id": "p_1", "source_type": "custom", "ordering_index": 1,
                         "snapshot_uraian": "Lama", "snapshot_satuan": "m2"},
                    ],
                }],
            }]
        })
        klas = Klasifikasi.objects.get(project=self.project, name="Klas A")
        sub = SubKlasifikasi.objects.get(project=self.project, name="Sub A")

        # "Lama" omitted; a brand-new row reuses the freed slot.
        body = self._upsert({
            "klasifikasi": [{
                "id": klas.id, "temp_id": "k_a", "name": "Klas A", "ordering_index": 1,
                "sub": [{
                    "id": sub.id, "temp_id": "s_a", "name": "Sub A", "ordering_index": 1,
                    "pekerjaan": [
                        {"temp_id": "p_new", "source_type": "custom", "ordering_index": 1,
                         "snapshot_uraian": "Baru", "snapshot_satuan": "m2"},
                    ],
                }],
            }]
        })
        survivors = list(Pekerjaan.objects.filter(project=self.project))
        self.assertEqual(len(survivors), 1)
        self.assertIn("p_new", body["id_map"]["pekerjaan"])
        self.assertEqual(body["id_map"]["pekerjaan"]["p_new"], survivors[0].id)
