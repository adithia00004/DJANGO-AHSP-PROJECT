"""Fixtures and rendered-output checks for export after the contract end.

Type 1 extends the final week only. Type 2 extends that week and adds W7.
Both scenarios use the same canonical Monday-Sunday week boundary as project 217.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
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
