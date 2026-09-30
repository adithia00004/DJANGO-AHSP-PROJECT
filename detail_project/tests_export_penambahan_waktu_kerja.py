"""Fixtures and rendered-output checks for export after the contract end.

Type 1 extends the final week only. Type 2 extends that week and adds W7.
Both scenarios use the same canonical Monday-Sunday week boundary as project 217.
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from docx import Document

from dashboard.models import Project
from detail_project.exports.errors import ExportValidationError
from detail_project.exports.export_manager import ExportManager
from detail_project.exports.jadwal_pekerjaan_adapter import JadwalPekerjaanExportAdapter
from detail_project.timeline_utils import (
    contract_boundary_week,
    is_extension_day,
    is_extension_week,
    project_report_period_counts,
    work_period_end,
)


class ExtensionExportFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="export-extension-owner", password="StrongPass123!"
        )
        base = {
            "owner": cls.owner,
            "sumber_dana": "APBD",
            "lokasi_project": "Makassar",
            "nama_client": "Pemilik",
            "anggaran_owner": Decimal("1000000.00"),
            "week_start_day": 0,
            "week_end_day": 6,
        }
        cls.same_week = Project.objects.create(
            **base,
            nama="Tambahan dalam minggu batas",
            tanggal_mulai=date(2026, 9, 14),
            tanggal_selesai=date(2026, 9, 16),  # Rabu
            tanggal_akhir_tambahan=date(2026, 9, 19),  # Sabtu
        )
        cls.next_week = Project.objects.create(
            **base,
            nama="Tambahan sampai W7",
            tanggal_mulai=date(2026, 8, 10),
            tanggal_selesai=date(2026, 9, 19),  # Sabtu di W6
            tanggal_akhir_tambahan=date(2026, 9, 27),  # Minggu di W7
        )
        cls.without_extension = Project.objects.create(
            **base,
            nama="Tanpa tambahan",
            tanggal_mulai=date(2026, 8, 10),
            tanggal_selesai=date(2026, 9, 19),
        )


class ExtensionExportFixtureTests(ExtensionExportFixtureMixin, TestCase):
    def test_same_week_extension_has_days_but_no_new_week(self):
        self.assertEqual(work_period_end(self.same_week), date(2026, 9, 19))
        self.assertEqual(contract_boundary_week(self.same_week), 1)
        self.assertEqual(project_report_period_counts(self.same_week), (1, 1))
        self.assertFalse(is_extension_week(self.same_week, 1))
        self.assertFalse(is_extension_day(self.same_week, date(2026, 9, 16)))
        self.assertTrue(is_extension_day(self.same_week, date(2026, 9, 17)))

    def test_new_week_extension_keeps_boundary_in_w6(self):
        self.assertEqual(work_period_end(self.next_week), date(2026, 9, 27))
        self.assertEqual(contract_boundary_week(self.next_week), 6)
        self.assertEqual(project_report_period_counts(self.next_week), (7, 2))
        self.assertFalse(is_extension_week(self.next_week, 6))
        self.assertTrue(is_extension_week(self.next_week, 7))
        self.assertTrue(is_extension_day(self.next_week, date(2026, 9, 20)))

    def test_project_without_extension_has_no_markers(self):
        self.assertEqual(work_period_end(self.without_extension), date(2026, 9, 19))
        self.assertEqual(project_report_period_counts(self.without_extension), (6, 2))
        self.assertFalse(is_extension_week(self.without_extension, 7))
        self.assertFalse(is_extension_day(self.without_extension, date(2026, 9, 20)))


class ExtensionExportAdapterTests(ExtensionExportFixtureMixin, TestCase):
    def test_same_week_extension_marks_boundary_without_an_extra_week(self):
        data = JadwalPekerjaanExportAdapter(self.same_week).get_rekap_report_data()
        self.assertEqual(data["contract_end"], date(2026, 9, 16))
        self.assertEqual(data["additional_end"], date(2026, 9, 19))
        self.assertEqual(data["boundary_week"], 1)
        self.assertEqual(len(data["weekly_columns"]), 1)
        self.assertTrue(data["weekly_columns"][0]["is_boundary_week"])
        self.assertFalse(data["weekly_columns"][0]["is_extension_week"])

    def test_w6_boundary_and_w7_extension_reach_all_report_payloads(self):
        adapter = JadwalPekerjaanExportAdapter(self.next_week)
        for data in (
            adapter.get_rekap_report_data(),
            adapter.get_monthly_comparison_data(2),
            adapter.get_weekly_comparison_data(7),
        ):
            self.assertEqual(data["contract_end"], date(2026, 9, 19))
            self.assertEqual(data["additional_end"], date(2026, 9, 27))
            self.assertEqual(data["boundary_week"], 6)
        columns = adapter.get_rekap_report_data()["weekly_columns"]
        self.assertEqual(len(columns), 7)
        self.assertTrue(columns[5]["is_boundary_week"])
        self.assertFalse(columns[5]["is_extension_week"])
        self.assertFalse(columns[6]["is_boundary_week"])
        self.assertTrue(columns[6]["is_extension_week"])

    def test_project_without_extension_has_no_column_markers(self):
        data = JadwalPekerjaanExportAdapter(self.without_extension).get_rekap_report_data()
        self.assertIsNone(data["additional_end"])
        self.assertIsNone(data["boundary_week"])
        self.assertEqual(len(data["weekly_columns"]), 6)
        self.assertTrue(all(not col["is_boundary_week"] for col in data["weekly_columns"]))
        self.assertTrue(all(not col["is_extension_week"] for col in data["weekly_columns"]))


class ExtensionDailyWordTests(ExtensionExportFixtureMixin, TestCase):
    def _document_text(self, project, week):
        response = ExportManager(project, self.owner).export_jadwal_professional(
            "word", report_type="daily", daily_mode="week", period=week,
        )
        self.assertTrue(response.content.startswith(b"PK"))
        document = Document(BytesIO(response.content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    def test_w7_daily_word_renders_extension_days(self):
        text = self._document_text(self.next_week, 7)
        self.assertIn("Senin, 21 September 2026 | Minggu 7 | Penambahan Waktu Kerja", text)
        self.assertNotIn("terlambat", text.lower())

    def test_boundary_week_marks_only_the_day_after_contract_end(self):
        text = self._document_text(self.next_week, 6)
        self.assertIn("Sabtu, 19 September 2026 | Minggu 6", text)
        self.assertNotIn("Sabtu, 19 September 2026 | Minggu 6 | Penambahan", text)
        self.assertIn("Minggu, 20 September 2026 | Minggu 6 | Penambahan Waktu Kerja", text)

    def test_same_week_extension_marks_days_without_a_new_week(self):
        text = self._document_text(self.same_week, 1)
        self.assertIn("Rabu, 16 September 2026 | Minggu 1", text)
        self.assertIn("Kamis, 17 September 2026 | Minggu 1 | Penambahan Waktu Kerja", text)

    def test_day_after_work_period_remains_rejected(self):
        with self.assertRaises(ExportValidationError):
            ExportManager(self.next_week, self.owner).export_jadwal_professional(
                "word", report_type="daily", daily_mode="day", days=[50],
            )
