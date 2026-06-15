"""WP-B5 inc-B5d — JSON separated from report formats (B-2).

Report formats = PDF/XLSX/Word/CSV only. JSON is a data package
(project_backup / work_structure_template), served by atomic, versioned
import/export endpoints — never offered as a "report format".
"""
import os
import re

from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from detail_project.exports.export_manager import ExportManager

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(*parts):
    with open(os.path.join(_APP_DIR, *parts), encoding="utf-8") as f:
        return f.read()


class JsonNotAReportFormatTests(TestCase):
    def test_jadwal_report_endpoints_exist_but_no_json(self):
        for fmt in ["csv", "pdf", "word", "xlsx"]:
            with self.subTest(fmt=fmt):
                reverse(
                    f"detail_project:export_jadwal_pekerjaan_{fmt}",
                    kwargs={"project_id": 1},
                )
        with self.assertRaises(NoReverseMatch):
            reverse(
                "detail_project:export_jadwal_pekerjaan_json", kwargs={"project_id": 1}
            )

    def test_non_package_json_report_routes_are_retired(self):
        for route_name in [
            "export_rekap_rab_json",
            "api_export_rekap_kebutuhan_json",
            "export_volume_pekerjaan_json",
            "export_harga_items_json",
        ]:
            with self.subTest(route_name=route_name):
                with self.assertRaises(NoReverseMatch):
                    reverse(
                        f"detail_project:{route_name}",
                        kwargs={"project_id": 1},
                    )

    def test_non_package_report_pages_do_not_offer_json(self):
        for template in [
            "rekap_rab.html",
            "rekap_kebutuhan.html",
            "volume_pekerjaan.html",
            "harga_items.html",
        ]:
            with self.subTest(template=template):
                src = _read("templates", "detail_project", template)
                self.assertNotIn('id="btn-export-json"', src)

    def test_jadwal_modal_has_no_json_format_radio(self):
        src = _read("templates", "detail_project", "kelola_tahapan_grid_modern.html")
        self.assertNotIn('id="formatJson"', src)
        self.assertNotIn('value="json"', src)

    def test_export_coordinator_drops_json_format(self):
        src = _read("static", "detail_project", "js", "src", "export", "export-coordinator.js")
        self.assertNotIn("JSON: 'json'", src)

    def test_backend_export_manager_rejects_json_as_report_format(self):
        self.assertNotIn("json", ExportManager.EXPORTER_MAP)
        src = _read("exports", "export_manager.py")
        self.assertNotIn("JSONExporter", src)
        self.assertNotIn("format_type == 'json'", src)


class DataPackageContractTests(TestCase):
    """JSON data packages must be versioned and imported atomically (DoD #6)."""

    def setUp(self):
        self.src = _read("views_api.py")

    def test_data_packages_are_versioned(self):
        self.assertIn('"export_type": "project_full_backup"', self.src)
        self.assertIn('"export_type": "project_template"', self.src)
        self.assertIn('"export_version": "3.0"', self.src)

    def test_imports_are_atomic(self):
        for name in [
            "import_project_from_json",
            "api_import_template",
            "api_import_template_from_file",
        ]:
            with self.subTest(view=name):
                idx = self.src.find(f"def {name}(")
                self.assertNotEqual(idx, -1, f"{name} not found")
                decorators = self.src[max(0, idx - 200):idx]
                self.assertIn("@transaction.atomic", decorators)
