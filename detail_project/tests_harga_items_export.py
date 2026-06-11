import inspect
import json
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.exports.export_manager import ExportManager
from detail_project.models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from detail_project.views_api import (
    export_harga_items_json,
    export_template_ahsp_json,
)


class HargaItemsExportRegressionTests(TestCase):
    def setUp(self):
        owner = get_user_model().objects.create_user(
            username="harga_export_owner",
            email="harga-export@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=owner,
            nama="Harga Export",
            sumber_dana="APBN",
            lokasi_project="Makassar",
            nama_client="Client",
            anggaran_owner=1000,
        )
        self.owner = owner
        klasifikasi = Klasifikasi.objects.create(
            project=self.project,
            name="K1",
            ordering_index=1,
        )
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klasifikasi,
            name="S1",
            ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST.001",
            snapshot_uraian="Pekerjaan",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self.used_item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="B.001",
            kategori="BHN",
            uraian="Semen",
            satuan="kg",
            harga_satuan=Decimal("0.00"),
        )
        raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=self.used_item,
            kategori="BHN",
            kode=self.used_item.kode_item,
            uraian=self.used_item.uraian,
            satuan=self.used_item.satuan,
            koefisien=Decimal("1"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=raw,
            harga_item=self.used_item,
            kategori="BHN",
            kode=self.used_item.kode_item,
            uraian=self.used_item.uraian,
            satuan=self.used_item.satuan,
            koefisien=Decimal("1"),
        )
        self.orphan_item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="B.ORPHAN",
            kategori="BHN",
            uraian="Orphan",
            satuan="kg",
            harga_satuan=Decimal("5000.00"),
        )
        self.factory = RequestFactory()

    def test_manager_generates_every_harga_item_format(self):
        expected_types = {
            "csv": "text/csv",
            "pdf": "application/pdf",
            "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
        }

        for format_type, expected_type in expected_types.items():
            with self.subTest(format_type=format_type):
                response = ExportManager(
                    self.project,
                    self.project.owner,
                ).export_harga_items(format_type)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response["Content-Type"].startswith(expected_type))
                self.assertIn("attachment", response["Content-Disposition"])

    def test_json_export_excludes_orphans_and_preserves_zero(self):
        request = self.factory.get("/api/export/harga-items/json/")
        request.user = self.owner
        response = inspect.unwrap(export_harga_items_json)(
            request,
            self.project.id,
        )
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(payload["export_info"]["total_items"], 1)
        self.assertEqual(payload["items"][0]["kode_item"], self.used_item.kode_item)
        self.assertEqual(payload["items"][0]["harga_satuan"], 0.0)

    def test_template_export_includes_bundle_reference_metadata(self):
        target = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.pekerjaan.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST.TARGET",
            snapshot_uraian="Target bundle",
            snapshot_satuan="m2",
            ordering_index=2,
        )
        bundle_item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="BUNDLE.001",
            kategori="LAIN",
            uraian="Bundle pekerjaan",
            satuan="m2",
            harga_satuan=Decimal("0.00"),
        )
        DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=bundle_item,
            kategori="LAIN",
            kode=bundle_item.kode_item,
            uraian=bundle_item.uraian,
            satuan=bundle_item.satuan,
            koefisien=Decimal("1"),
            ref_pekerjaan=target,
        )

        request = self.factory.get("/api/export/template-ahsp/json/")
        request.user = self.owner
        response = inspect.unwrap(export_template_ahsp_json)(
            request,
            self.project.id,
        )
        payload = json.loads(response.content.decode("utf-8"))
        exported_items = [
            item
            for pekerjaan in payload["pekerjaan_list"]
            for item in pekerjaan["items"]
            if item["kode"] == "BUNDLE.001"
        ]

        self.assertEqual(payload["export_version"], "1.1")
        self.assertEqual(exported_items[0]["bundle_type"], "pekerjaan")
        self.assertEqual(
            exported_items[0]["bundle_ref_snapshot_kode"],
            target.snapshot_kode,
        )
        self.assertEqual(
            exported_items[0]["_ref_pekerjaan_export_id"],
            target.id,
        )
        exported_target = next(
            pekerjaan
            for pekerjaan in payload["pekerjaan_list"]
            if pekerjaan["kode"] == target.snapshot_kode
        )
        self.assertEqual(exported_target["_export_id"], target.id)

    def test_harga_template_waits_for_export_manager_and_has_sync_fallback(self):
        root = Path(__file__).resolve().parent
        template = (
            root / "templates" / "detail_project" / "harga_items.html"
        ).read_text(encoding="utf-8")
        base_template = (
            root / "templates" / "detail_project" / "base_detail.html"
        ).read_text(encoding="utf-8")

        self.assertIn("document.addEventListener('DOMContentLoaded'", template)
        self.assertIn("allowSyncFallback: true", template)
        self.assertIn("if (asyncOk === false)", template)
        self.assertIn("if (useAsync)", template)
        self.assertIn("handleExport('pdf', 'PDF', e)", template)
        self.assertIn("handleExport('word', 'Word', e)", template)
        self.assertNotIn("handleExport('pdf', 'PDF', e, true)", template)
        self.assertIn("ExportManager.js' %}?v=20260606-1", base_template)
        self.assertNotIn("ExportManager.js' %}\" defer", base_template)
