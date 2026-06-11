import json

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.views_api import (
    api_get_detail_ahsp,
    api_get_list_pekerjaan_tree,
    api_get_rekap_rab,
    api_upsert_list_pekerjaan,
)
from referensi.models import AHSPReferensi


class ListPekerjaanUpsertValidationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_upsert_validation",
            email="owner-upsert-validation@example.com",
            password="Secret123!",
        )
        self.non_owner = user_model.objects.create_user(
            username="non_owner_upsert_validation",
            email="non-owner-upsert-validation@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Validation",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Validation",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

    def _post_upsert(self, payload, *, user=None):
        request = self.factory.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = user or self.owner
        return api_upsert_list_pekerjaan(request, self.project.id)

    def _get_tree(self, *, user=None):
        request = self.factory.get(
            reverse(
                "detail_project:api_get_list_pekerjaan_tree",
                kwargs={"project_id": self.project.id},
            )
        )
        request.user = user or self.owner
        return api_get_list_pekerjaan_tree(request, self.project.id)

    def _get_detail_ahsp(self, pekerjaan, *, user=None):
        request = self.factory.get(
            reverse(
                "detail_project:api_get_detail_ahsp",
                kwargs={"project_id": self.project.id, "pekerjaan_id": pekerjaan.id},
            )
        )
        request.user = user or self.owner
        return api_get_detail_ahsp(request, self.project.id, pekerjaan.id)

    def _get_rekap(self, *, user=None):
        request = self.factory.get(
            reverse(
                "detail_project:api_get_rekap_rab",
                kwargs={"project_id": self.project.id},
            )
        )
        request.user = user or self.owner
        return api_get_rekap_rab(request, self.project.id)

    def _extract_error_paths(self, response):
        body = json.loads(response.content.decode("utf-8"))
        return [e.get("path") for e in body.get("errors", [])]

    def test_rejects_duplicate_klasifikasi_ordering_index(self):
        payload = {
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
                                    "snapshot_uraian": "Job A1",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                },
                {
                    "name": "Klas B",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "Sub B1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "Job B1",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                },
            ]
        }

        response = self._post_upsert(payload)
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        self.assertIn("klasifikasi[1].ordering_index", self._extract_error_paths(response))

    def test_rejects_duplicate_sub_ordering_index_in_same_klasifikasi(self):
        payload = {
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
                                    "snapshot_uraian": "Job A1",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        },
                        {
                            "name": "Sub A2",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "Job A2",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        response = self._post_upsert(payload)
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        self.assertIn("klasifikasi[0].sub[1].ordering_index", self._extract_error_paths(response))

    def test_rejects_non_object_nodes_in_payload(self):
        payload = {"klasifikasi": ["invalid-node"]}
        response = self._post_upsert(payload)
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        self.assertIn("klasifikasi[0]", self._extract_error_paths(response))

    def test_non_owner_cannot_upsert_foreign_project(self):
        payload = {"klasifikasi": []}
        with self.assertRaises(Http404):
            self._post_upsert(payload, user=self.non_owner)

    def test_existing_ref_row_can_change_to_ref_modified_without_resending_ref_id(self):
        ref = AHSPReferensi.objects.create(
            kode_ahsp="TEST-REF-001",
            nama_ahsp="Pekerjaan referensi",
            satuan="m2",
            sumber="TEST",
        )
        klas = Klasifikasi.objects.create(project=self.project, name="Klas A", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub A1",
            ordering_index=1,
        )
        pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_REF,
            ref=ref,
            snapshot_kode=ref.kode_ahsp,
            snapshot_uraian=ref.nama_ahsp,
            snapshot_satuan=ref.satuan,
            ordering_index=1,
        )

        payload = {
            "klasifikasi": [
                {
                    "id": klas.id,
                    "name": "Klas A",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "id": sub.id,
                            "name": "Sub A1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "id": pekerjaan.id,
                                    "source_type": "ref_modified",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "Pekerjaan referensi dimodifikasi",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        response = self._post_upsert(payload)
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))

        pekerjaan.refresh_from_db()
        self.assertEqual(pekerjaan.source_type, Pekerjaan.SOURCE_REF_MOD)
        self.assertEqual(pekerjaan.ref_id, ref.id)

    def test_existing_klasifikasi_name_can_be_renamed(self):
        klas = Klasifikasi.objects.create(project=self.project, name="Nama Lama", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub A1",
            ordering_index=1,
        )
        pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="Pekerjaan custom",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        payload = {
            "klasifikasi": [
                {
                    "id": klas.id,
                    "name": "Nama Baru",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "id": sub.id,
                            "name": "Sub A1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "id": pekerjaan.id,
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "Pekerjaan custom",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        response = self._post_upsert(payload)

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        klas.refresh_from_db()
        self.assertEqual(klas.name, "Nama Baru")

    def test_tree_response_includes_actual_ref_sumber(self):
        ref = AHSPReferensi.objects.create(
            kode_ahsp="TEST-REF-2025",
            nama_ahsp="Pekerjaan referensi 2025",
            satuan="m2",
            sumber="AHSP 2025",
        )
        klas = Klasifikasi.objects.create(project=self.project, name="Klas A", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub A1",
            ordering_index=1,
        )
        Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_REF,
            ref=ref,
            snapshot_kode=ref.kode_ahsp,
            snapshot_uraian=ref.nama_ahsp,
            snapshot_satuan=ref.satuan,
            ordering_index=1,
        )

        response = self._get_tree()
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        pekerjaan = body["klasifikasi"][0]["sub"][0]["pekerjaan"][0]
        self.assertEqual(pekerjaan["ref_sumber"], "AHSP 2025")
        self.assertEqual(pekerjaan["ahsp_sumber"], "AHSP 2025")

    def test_upsert_rejects_ref_id_source_mismatch(self):
        ref_2025 = AHSPReferensi.objects.create(
            kode_ahsp="TEST-REF-SAME",
            nama_ahsp="Pekerjaan referensi 2025",
            satuan="m2",
            sumber="AHSP 2025",
        )
        AHSPReferensi.objects.create(
            kode_ahsp="TEST-REF-SAME",
            nama_ahsp="Pekerjaan referensi 2026",
            satuan="m2",
            sumber="AHSP 2026",
        )

        payload = {
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
                                    "source_type": "ref",
                                    "ordering_index": 1,
                                    "ref_id": ref_2025.id,
                                    "ahsp_sumber": "AHSP 2026",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        response = self._post_upsert(payload)
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        self.assertIn("klasifikasi[0].sub[0].pekerjaan[0].ahsp_sumber", self._extract_error_paths(response))

    def test_detail_ahsp_response_includes_actual_ref_sumber(self):
        ref = AHSPReferensi.objects.create(
            kode_ahsp="TEST-DETAIL-REF-2025",
            nama_ahsp="Detail referensi 2025",
            satuan="m2",
            sumber="AHSP 2025",
        )
        klas = Klasifikasi.objects.create(project=self.project, name="Klas Detail", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub Detail",
            ordering_index=1,
        )
        pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_REF,
            ref=ref,
            snapshot_kode=ref.kode_ahsp,
            snapshot_uraian=ref.nama_ahsp,
            snapshot_satuan=ref.satuan,
            ordering_index=1,
        )

        response = self._get_detail_ahsp(pekerjaan)
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        pekerjaan_payload = json.loads(response.content.decode("utf-8"))["pekerjaan"]
        self.assertEqual(pekerjaan_payload["ref_sumber"], "AHSP 2025")
        self.assertEqual(pekerjaan_payload["ahsp_sumber"], "AHSP 2025")
        self.assertEqual(pekerjaan_payload["source_label"], "AHSP 2025")

    def test_rekap_response_includes_actual_ref_sumber(self):
        ref = AHSPReferensi.objects.create(
            kode_ahsp="TEST-REKAP-REF-2026",
            nama_ahsp="Rekap referensi 2026",
            satuan="m",
            sumber="AHSP 2026",
        )
        klas = Klasifikasi.objects.create(project=self.project, name="Klas Rekap", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub Rekap",
            ordering_index=1,
        )
        Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_REF_MOD,
            ref=ref,
            snapshot_kode=ref.kode_ahsp,
            snapshot_uraian=ref.nama_ahsp,
            snapshot_satuan=ref.satuan,
            ordering_index=1,
        )

        response = self._get_rekap()
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        row = json.loads(response.content.decode("utf-8"))["rows"][0]
        self.assertEqual(row["ref_sumber"], "AHSP 2026")
        self.assertEqual(row["ahsp_sumber"], "AHSP 2026")
        self.assertEqual(row["source_label"], "AHSP 2026 (modified)")
