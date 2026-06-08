import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
    TemplateAhspKoefFormulaState,
    VolumePekerjaan,
)
from detail_project.services import compute_rekap_for_project
from detail_project.views_api import (
    api_get_detail_ahsp,
    api_reset_detail_ahsp_to_ref,
    api_save_detail_ahsp_for_pekerjaan,
    api_template_ahsp_formula_state,
    export_template_ahsp_json,
    import_project_from_json,
)
from referensi.models import AHSPReferensi


class TemplateAhspKoefFormulaApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_template_formula_api",
            email="owner-template-formula-api@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Template Formula API",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Formula",
            anggaran_owner=1000,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="K1", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S1", ordering_index=1)

        self.pekerjaan_custom = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUS.001",
            snapshot_uraian="Pekerjaan Custom",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self.pekerjaan_mod = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_REF_MOD,
            snapshot_kode="MOD.001",
            snapshot_uraian="Pekerjaan MOD",
            snapshot_satuan="m2",
            ordering_index=2,
        )

        self.factory = RequestFactory()

    def _create_detail(self, pekerjaan, kode, koef="1.000000"):
        harga_item = HargaItemProject.objects.create(
            project=self.project,
            kode_item=kode,
            uraian=f"Item {kode}",
            satuan="m2",
            kategori=HargaItemProject.KATEGORI_TK,
            harga_satuan=Decimal("1000"),
        )
        return DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            harga_item=harga_item,
            kategori=HargaItemProject.KATEGORI_TK,
            kode=kode,
            uraian=f"Uraian {kode}",
            satuan="m2",
            koefisien=Decimal(koef),
        )

    def _call_post(self, view_func, payload, *args):
        req = self.factory.post(
            "/api/mock/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        req.user = self.owner
        return view_func(req, *args)

    def _call_get(self, view_func, *args):
        req = self.factory.get("/api/mock/")
        req.user = self.owner
        return view_func(req, *args)

    def _set_owner_pro(self):
        self.owner.subscription_status = self.owner.SubscriptionStatus.PRO
        self.owner.subscription_end_date = timezone.now() + timedelta(days=30)
        self.owner.save(update_fields=["subscription_status", "subscription_end_date"])

    def test_get_detail_includes_formula_metadata(self):
        self._create_detail(self.pekerjaan_custom, "TK.001", koef="2.500000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="TK.001",
            raw="=bp_1*2",
            is_fx=True,
        )

        response = self._call_get(
            api_get_detail_ahsp,
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertEqual(len(body.get("items", [])), 1)
        item = body["items"][0]
        self.assertEqual(item.get("kode"), "TK.001")
        self.assertEqual(item.get("koef_formula_raw"), "=bp_1*2")
        self.assertTrue(item.get("koef_is_fx"))

    def test_save_detail_syncs_formula_sidecar_by_kode(self):
        self._create_detail(self.pekerjaan_custom, "OLD.001", koef="1.000000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="OLD.001",
            raw="=bp_99",
            is_fx=True,
        )

        payload = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "TK.001",
                    "uraian": "Baris Formula",
                    "satuan": "m2",
                    "koefisien": "1.500000",
                    "koef_formula_raw": "=bp_1*2",
                    "koef_is_fx": True,
                },
                {
                    "kategori": "TK",
                    "kode": "TK.002",
                    "uraian": "Baris Angka",
                    "satuan": "m2",
                    "koefisien": "2.000000",
                    "koef_formula_raw": "",
                    "koef_is_fx": False,
                },
            ]
        }

        response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            payload,
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))

        sidecars = TemplateAhspKoefFormulaState.objects.filter(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
        )
        self.assertEqual(sidecars.count(), 1)
        self.assertTrue(sidecars.filter(row_key="TK.001", raw="=bp_1*2", is_fx=True).exists())

        payload_no_fx = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "TK.001",
                    "uraian": "Baris Formula Jadi Angka",
                    "satuan": "m2",
                    "koefisien": "1.750000",
                    "koef_formula_raw": "",
                    "koef_is_fx": False,
                }
            ]
        }
        response_2 = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            payload_no_fx,
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(response_2.status_code, 200, response_2.content.decode("utf-8"))
        self.assertFalse(
            TemplateAhspKoefFormulaState.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan_custom,
            ).exists()
        )

    def test_save_mod_rejects_bundle_payload_fail_fast(self):
        payload = {
            "rows": [
                {
                    "kategori": "LAIN",
                    "kode": "BUNDLE.01",
                    "uraian": "Bundle MOD",
                    "satuan": "ls",
                    "koefisien": "1.000000",
                    "ref_kind": "job",
                    "ref_id": "123",
                }
            ]
        }
        response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            payload,
            self.project.id,
            self.pekerjaan_mod.id,
        )
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertIn("bundle", (body.get("user_message") or "").lower())

    def test_save_detail_rejects_stale_client_timestamp(self):
        loaded_at = self.pekerjaan_custom.updated_at.isoformat()

        first_response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            {
                "rows": [
                    {
                        "kategori": "TK",
                        "kode": "TK.FIRST",
                        "uraian": "Baris Pertama",
                        "satuan": "m2",
                        "koefisien": "1.000000",
                    }
                ]
            },
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(first_response.status_code, 200, first_response.content.decode("utf-8"))

        second_response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            {
                "client_updated_at": loaded_at,
                "rows": [
                    {
                        "kategori": "TK",
                        "kode": "TK.SECOND",
                        "uraian": "Baris Kedua",
                        "satuan": "m2",
                        "koefisien": "2.000000",
                    }
                ],
            },
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(second_response.status_code, 409, second_response.content.decode("utf-8"))
        body = json.loads(second_response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(body.get("conflict"))
        self.assertTrue(body.get("server_updated_at"))

    def test_save_detail_accepts_force_overwrite_after_conflict(self):
        loaded_at = self.pekerjaan_custom.updated_at.isoformat()

        first_response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            {
                "rows": [
                    {
                        "kategori": "TK",
                        "kode": "TK.FIRST",
                        "uraian": "Baris Pertama",
                        "satuan": "m2",
                        "koefisien": "1.000000",
                    }
                ]
            },
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(first_response.status_code, 200, first_response.content.decode("utf-8"))

        overwrite_response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            {
                "client_updated_at": loaded_at,
                "force_overwrite": True,
                "rows": [
                    {
                        "kategori": "TK",
                        "kode": "TK.SECOND",
                        "uraian": "Baris Kedua",
                        "satuan": "m2",
                        "koefisien": "2.000000",
                    }
                ],
            },
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(overwrite_response.status_code, 200, overwrite_response.content.decode("utf-8"))
        self.assertTrue(json.loads(overwrite_response.content.decode("utf-8")).get("ok"))

    def test_save_detail_accepts_current_client_timestamp(self):
        first_response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            {
                "rows": [
                    {
                        "kategori": "TK",
                        "kode": "TK.CURRENT.1",
                        "uraian": "Baris Current 1",
                        "satuan": "m2",
                        "koefisien": "1.000000",
                    }
                ]
            },
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(first_response.status_code, 200, first_response.content.decode("utf-8"))
        first_body = json.loads(first_response.content.decode("utf-8"))
        current_token = first_body["pekerjaan"]["updated_at"]

        second_response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            {
                "client_updated_at": current_token,
                "rows": [
                    {
                        "kategori": "TK",
                        "kode": "TK.CURRENT.2",
                        "uraian": "Baris Current 2",
                        "satuan": "m2",
                        "koefisien": "2.000000",
                    }
                ],
            },
            self.project.id,
            self.pekerjaan_custom.id,
        )

        self.assertEqual(second_response.status_code, 200, second_response.content.decode("utf-8"))
        self.assertTrue(json.loads(second_response.content.decode("utf-8")).get("ok"))

    def test_reset_to_ref_clears_sidecar(self):
        ref = AHSPReferensi.objects.create(
            kode_ahsp="REF.TEST.001",
            nama_ahsp="Ref Test",
            sumber="AHSP SNI 2025",
        )
        self.pekerjaan_mod.ref = ref
        self.pekerjaan_mod.save(update_fields=["ref"])

        self._create_detail(self.pekerjaan_mod, "TK.MOD.1", koef="1.000000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_mod,
            row_key="TK.MOD.1",
            raw="=bp_1",
            is_fx=True,
        )

        response = self._call_post(
            api_reset_detail_ahsp_to_ref,
            {},
            self.project.id,
            self.pekerjaan_mod.id,
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        self.assertFalse(
            TemplateAhspKoefFormulaState.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan_mod,
            ).exists()
        )

    def test_bulk_formula_endpoint_returns_template_ahsp_formula_rows(self):
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="TK.001",
            raw="=bp_1*2",
            is_fx=True,
        )
        response = self._call_get(
            api_template_ahsp_formula_state,
            self.project.id,
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertEqual(len(body.get("items", [])), 1)
        row = body["items"][0]
        self.assertEqual(row.get("row_key"), "TK.001")
        self.assertEqual(row.get("raw"), "=bp_1*2")
        self.assertTrue(row.get("is_fx"))

    def test_save_detail_rolls_back_when_sidecar_sync_fails(self):
        self._create_detail(self.pekerjaan_custom, "OLD.KEEP", koef="1.000000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="OLD.KEEP",
            raw="=bp_1",
            is_fx=True,
        )

        payload = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "NEW.ROW",
                    "uraian": "Baris Baru",
                    "satuan": "m2",
                    "koefisien": "2.000000",
                    "koef_formula_raw": "=bp_2*3",
                    "koef_is_fx": True,
                }
            ]
        }

        with patch(
            "detail_project.views_api.TemplateAhspKoefFormulaState.objects.update_or_create",
            side_effect=RuntimeError("forced sidecar sync failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._call_post(
                    api_save_detail_ahsp_for_pekerjaan,
                    payload,
                    self.project.id,
                    self.pekerjaan_custom.id,
                )

        detail_qs = DetailAHSPProject.objects.filter(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
        )
        self.assertEqual(detail_qs.count(), 1)
        self.assertTrue(detail_qs.filter(kode="OLD.KEEP").exists())
        self.assertFalse(detail_qs.filter(kode="NEW.ROW").exists())

        sidecar_qs = TemplateAhspKoefFormulaState.objects.filter(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
        )
        self.assertEqual(sidecar_qs.count(), 1)
        self.assertTrue(sidecar_qs.filter(row_key="OLD.KEEP", raw="=bp_1", is_fx=True).exists())

    def test_save_detail_toggle_is_fx_true_to_false_deletes_only_target_sidecar(self):
        self._create_detail(self.pekerjaan_custom, "TK.001", koef="1.000000")
        self._create_detail(self.pekerjaan_custom, "TK.002", koef="2.000000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="TK.001",
            raw="=bp_1*2",
            is_fx=True,
        )
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="TK.002",
            raw="=bp_2+1",
            is_fx=True,
        )

        payload = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "TK.001",
                    "uraian": "Row 1 jadi angka",
                    "satuan": "m2",
                    "koefisien": "1.250000",
                    "koef_formula_raw": "",
                    "koef_is_fx": False,
                },
                {
                    "kategori": "TK",
                    "kode": "TK.002",
                    "uraian": "Row 2 tetap formula",
                    "satuan": "m2",
                    "koefisien": "2.500000",
                    "koef_formula_raw": "=bp_2+1",
                    "koef_is_fx": True,
                },
            ]
        }

        response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            payload,
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))

        sidecar_qs = TemplateAhspKoefFormulaState.objects.filter(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
        )
        self.assertEqual(sidecar_qs.count(), 1)
        self.assertFalse(sidecar_qs.filter(row_key="TK.001").exists())
        self.assertTrue(
            sidecar_qs.filter(row_key="TK.002", raw="=bp_2+1", is_fx=True).exists()
        )

    def test_save_detail_without_formula_still_succeeds_and_keeps_sidecar_empty(self):
        payload = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "TK.PLAIN.1",
                    "uraian": "Baris angka biasa",
                    "satuan": "m2",
                    "koefisien": "1.500000",
                    "koef_formula_raw": "",
                    "koef_is_fx": False,
                }
            ]
        }
        response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            payload,
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        # SSOT: kode item di-resolve kanonik dari (kategori, uraian, satuan), bukan kode input
        # literal. Identitas baris diuji lewat uraian.
        self.assertTrue(
            DetailAHSPProject.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan_custom,
                uraian="Baris angka biasa",
            ).exists()
        )
        self.assertFalse(
            TemplateAhspKoefFormulaState.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan_custom,
            ).exists()
        )

    def test_export_template_ahsp_json_still_returns_formula_metadata(self):
        self._set_owner_pro()
        self._create_detail(self.pekerjaan_custom, "TK.001", koef="2.500000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="TK.001",
            raw="=bp_1*2",
            is_fx=True,
        )

        response = self._call_get(export_template_ahsp_json, self.project.id)
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body.get("export_type"), "template_ahsp")
        self.assertEqual(len(body.get("pekerjaan_list", [])), 2)
        first_items = body["pekerjaan_list"][0].get("items", [])
        self.assertTrue(first_items)
        self.assertIn("koef_formula_raw", first_items[0])
        self.assertIn("koef_is_fx", first_items[0])

    def test_import_project_full_skips_invalid_sidecar_row_key_without_error(self):
        payload = {
            "export_type": "project_full_backup",
            "export_version": "3.0",
            "project": {
                "nama": "Imported Backup",
                "sumber_dana": "APBN",
                "lokasi_project": "Jakarta",
                "nama_client": "Client Import",
                "anggaran_owner": "1000",
            },
            "klasifikasi": [
                {"_export_id": 1, "name": "K1", "ordering_index": 1},
            ],
            "sub_klasifikasi": [
                {"_export_id": 1, "_klasifikasi_ref": 1, "name": "S1", "ordering_index": 1},
            ],
            "harga_items": [
                {
                    "_export_id": 1,
                    "kode_item": "TK.001",
                    "uraian": "Item TK",
                    "satuan": "m2",
                    "kategori": "TK",
                    "harga_satuan": "1000",
                }
            ],
            "pekerjaan": [
                {
                    "_export_id": 1,
                    "_sub_klasifikasi_ref": 1,
                    "source_type": "custom",
                    "snapshot_kode": "CUS.001",
                    "snapshot_uraian": "Pekerjaan Import",
                    "snapshot_satuan": "m2",
                    "ordering_index": 1,
                    "budgeted_cost": "0",
                }
            ],
            "detail_ahsp": [
                {
                    "_export_id": 1,
                    "_pekerjaan_ref": 1,
                    "_harga_item_ref": 1,
                    "kategori": "TK",
                    "kode": "TK.001",
                    "uraian": "Detail Import",
                    "satuan": "m2",
                    "koefisien": "1.000000",
                }
            ],
            "template_ahsp_koef_formula_states": [
                {
                    "_pekerjaan_ref": 1,
                    "row_key": "INVALID.KODE",
                    "raw": "=bp_1*2",
                    "is_fx": True,
                }
            ],
            "volume_pekerjaan": [],
            "volume_formula_states": [],
            "project_parameters": [],
            "project_computed_parameters": [],
        }

        req = self.factory.post(
            "/api/mock/import/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        req.user = self.owner
        response = import_project_from_json(req)
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body.get("status"), "success")
        self.assertEqual(body.get("stats", {}).get("template_ahsp_koef_formulas"), 0)

    def test_formula_save_keeps_harga_item_and_rekap_computation_consistent(self):
        HargaItemProject.objects.create(
            project=self.project,
            kode_item="TK.REKAP.1",
            uraian="Harga Rekap",
            satuan="m2",
            kategori=HargaItemProject.KATEGORI_TK,
            harga_satuan=Decimal("1000"),
        )

        payload = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "TK.REKAP.1",
                    "uraian": "Baris rekap",
                    "satuan": "m2",
                    "koefisien": "2.000000",
                    "koef_formula_raw": "=bp_1*2",
                    "koef_is_fx": True,
                }
            ]
        }
        response = self._call_post(
            api_save_detail_ahsp_for_pekerjaan,
            payload,
            self.project.id,
            self.pekerjaan_custom.id,
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))

        VolumePekerjaan.objects.update_or_create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            defaults={"quantity": Decimal("3.000")},
        )

        # SSOT: kode di-resolve kanonik dari uraian; query baris lewat uraian, bukan kode input.
        detail = DetailAHSPProject.objects.get(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            uraian="Baris rekap",
        )
        self.assertIsNotNone(detail.harga_item_id)
        self.assertEqual(detail.harga_item.kategori, HargaItemProject.KATEGORI_TK)

        # SSOT me-resolve item dari uraian → item baru tanpa harga. Beri harga pada item
        # yang BENAR-BENAR tertaut ke detail agar rekap punya nilai (menguji konsistensi
        # perhitungan koef x volume x harga, bukan linkage kode literal lama).
        detail.harga_item.harga_satuan = Decimal("1000")
        detail.harga_item.save(update_fields=["harga_satuan", "updated_at"])

        rekap_rows = compute_rekap_for_project(self.project)
        target_row = next((row for row in rekap_rows if row.get("pekerjaan_id") == self.pekerjaan_custom.id), None)
        self.assertIsNotNone(target_row)
        self.assertGreater(target_row.get("A", 0), 0)
        self.assertGreaterEqual(target_row.get("total", 0), 0)

    def test_query_budget_get_and_save_detail_formula_metadata(self):
        self._create_detail(self.pekerjaan_custom, "TK.Q.1", koef="1.000000")
        TemplateAhspKoefFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan_custom,
            row_key="TK.Q.1",
            raw="=bp_1",
            is_fx=True,
        )

        with CaptureQueriesContext(connection) as get_ctx:
            response_get = self._call_get(
                api_get_detail_ahsp,
                self.project.id,
                self.pekerjaan_custom.id,
            )
        self.assertEqual(response_get.status_code, 200)
        self.assertLessEqual(len(get_ctx), 20)

        payload = {
            "rows": [
                {
                    "kategori": "TK",
                    "kode": "TK.Q.1",
                    "uraian": "Row Query",
                    "satuan": "m2",
                    "koefisien": "1.250000",
                    "koef_formula_raw": "=bp_1+1",
                    "koef_is_fx": True,
                }
            ]
        }
        with CaptureQueriesContext(connection) as save_ctx:
            response_save = self._call_post(
                api_save_detail_ahsp_for_pekerjaan,
                payload,
                self.project.id,
                self.pekerjaan_custom.id,
            )
        self.assertEqual(response_save.status_code, 200, response_save.content.decode("utf-8"))
        self.assertLessEqual(len(save_ctx), 80)
