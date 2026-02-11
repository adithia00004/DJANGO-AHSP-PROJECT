import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.views_api import api_upsert_list_pekerjaan


class ListPekerjaanUpsertDragDropRegressionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_upsert_dragdrop",
            email="owner-upsert-dragdrop@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project DragDrop",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )
        self.client.force_login(self.owner)
        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

    def _post_upsert(self, payload):
        request = self.factory.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.owner
        return api_upsert_list_pekerjaan(request, self.project.id)

    def test_move_pekerjaan_across_klas_when_source_sub_omitted(self):
        # Initial structure:
        # - Klas A: Sub A1(Job 1), Sub A2(Job 2)
        # - Klas B: Sub B1(Job 3)
        payload_initial = {
            "klasifikasi": [
                {
                    "name": "Klas A",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "Sub A1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "Job 1",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        },
                        {
                            "name": "Sub A2",
                            "ordering_index": 2,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "Job 2",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        },
                    ],
                },
                {
                    "name": "Klas B",
                    "ordering_index": 2,
                    "sub": [
                        {
                            "name": "Sub B1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 3,
                                    "snapshot_uraian": "Job 3",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                },
            ]
        }
        response = self._post_upsert(payload_initial)
        self.assertEqual(response.status_code, 200)

        klas_a = Klasifikasi.objects.get(project=self.project, name="Klas A")
        klas_b = Klasifikasi.objects.get(project=self.project, name="Klas B")
        sub_a1 = SubKlasifikasi.objects.get(project=self.project, klasifikasi=klas_a, name="Sub A1")
        sub_a2 = SubKlasifikasi.objects.get(project=self.project, klasifikasi=klas_a, name="Sub A2")
        sub_b1 = SubKlasifikasi.objects.get(project=self.project, klasifikasi=klas_b, name="Sub B1")

        job_1 = Pekerjaan.objects.get(project=self.project, sub_klasifikasi=sub_a1, snapshot_uraian="Job 1")
        job_2 = Pekerjaan.objects.get(project=self.project, sub_klasifikasi=sub_a2, snapshot_uraian="Job 2")
        job_3 = Pekerjaan.objects.get(project=self.project, sub_klasifikasi=sub_b1, snapshot_uraian="Job 3")

        # Regression scenario:
        # Move Job 1 from Klas A -> Klas B/Sub B2(new),
        # and omit Sub A1 in payload (typical drag-drop outcome).
        payload_move = {
            "klasifikasi": [
                {
                    "id": klas_a.id,
                    "name": "Klas A",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "id": sub_a2.id,
                            "name": "Sub A2",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "id": job_2.id,
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "Job 2",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": klas_b.id,
                    "name": "Klas B",
                    "ordering_index": 2,
                    "sub": [
                        {
                            "id": sub_b1.id,
                            "name": "Sub B1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "id": job_3.id,
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "Job 3",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        },
                        {
                            "name": "Sub B2",
                            "ordering_index": 2,
                            "pekerjaan": [
                                {
                                    "id": job_1.id,
                                    "source_type": "custom",
                                    "ordering_index": 3,
                                    "snapshot_uraian": "Job 1",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        },
                    ],
                },
            ]
        }
        response = self._post_upsert(payload_move)
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"), body)

        job_1.refresh_from_db()
        self.assertEqual(job_1.sub_klasifikasi.klasifikasi_id, klas_b.id)
        self.assertEqual(job_1.sub_klasifikasi.name, "Sub B2")
