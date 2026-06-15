"""WP-B5 inc-B5c — export filename convention tests."""
import os
import re
from datetime import date, datetime

from django.test import TestCase

from detail_project.exports.naming import build_export_filename, sanitize_for_filename

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


class ExportNamingTests(TestCase):
    def test_locked_name_and_date_only(self):
        fn = build_export_filename("Proyek Jalan", "Rekap RAB", "pdf", date(2026, 6, 15))
        self.assertEqual(fn, "Proyek_Jalan_2026-06-15.pdf")

    def test_no_label_is_name_then_date(self):
        self.assertEqual(
            build_export_filename("Proyek X", "", "csv", date(2026, 1, 2)),
            "Proyek_X_2026-01-02.csv",
        )

    def test_document_label_does_not_change_filename(self):
        first = build_export_filename("Proyek X", "Rekap RAB", "pdf", date(2026, 1, 2))
        second = build_export_filename("Proyek X", "Jadwal", "pdf", date(2026, 1, 2))
        self.assertEqual(first, second)

    def test_sanitizes_unsafe_chars(self):
        fn = build_export_filename('A/B:C*?"<>|', "x", "xlsx", date(2026, 1, 2))
        self.assertNotRegex(fn, r'[\\/:*?"<>|]')
        self.assertTrue(fn.startswith("A_B_C"))

    def test_datetime_is_accepted(self):
        fn = build_export_filename("P", "L", "pdf", datetime(2026, 3, 4, 12, 30))
        self.assertIn("2026-03-04", fn)

    def test_ext_leading_dot_tolerated(self):
        self.assertTrue(
            build_export_filename("P", "L", ".pdf", date(2026, 1, 1)).endswith(".pdf")
        )

    def test_empty_name_uses_fallback(self):
        self.assertTrue(
            build_export_filename("", "L", "pdf", date(2026, 1, 1)).startswith("Project_")
        )

    def test_sanitize_collapses_runs(self):
        self.assertEqual(sanitize_for_filename("a   b---c"), "a_b---c")


class FilenameConventionGuardTests(TestCase):
    """Generic exporters must use the canonical builder (project-name-first)."""

    def _src(self, rel):
        with open(os.path.join(_APP_DIR, "exports", rel), encoding="utf-8") as f:
            return f.read()

    def test_generic_exporters_use_builder(self):
        for fname in [
            "csv_exporter.py",
            "excel_exporter.py",
            "pdf_exporter.py",
            "word_exporter.py",
            "base.py",
            "rekap_rab.py",
            "rekap_kebutuhan.py",
        ]:
            with self.subTest(file=fname):
                self.assertIn("build_export_filename", self._src(fname))

    def test_base_no_longer_uses_project_id_in_filename(self):
        src = self._src("base.py")
        self.assertNotIn("{self.project.id}_{timestamp_str}", src)

    def test_download_endpoints_use_canonical_builder(self):
        with open(os.path.join(_APP_DIR, "views_export.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("build_export_filename", src)
        self.assertNotIn(
            "{session.project_name or 'export'}_{session.report_type}",
            src,
        )
