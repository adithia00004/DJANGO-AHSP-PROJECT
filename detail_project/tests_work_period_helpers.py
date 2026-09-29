from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from .timeline_utils import (
    contract_boundary_week,
    is_extension_day,
    is_extension_week,
    project_report_period_counts,
    work_period_end,
)


class WorkPeriodHelperTests(SimpleTestCase):
    def setUp(self):
        self.project = SimpleNamespace(
            tanggal_mulai=date(2026, 9, 28),  # Senin
            tanggal_selesai=date(2026, 9, 30),  # Rabu, minggu 1
            tanggal_akhir_tambahan=None,
            week_end_day=6,
        )

    def test_no_additional_date_preserves_existing_contract_end(self):
        self.assertEqual(work_period_end(self.project), date(2026, 9, 30))
        self.assertFalse(is_extension_week(self.project, 2))
        self.assertFalse(is_extension_day(self.project, date(2026, 10, 1)))

    def test_additional_end_extends_capture_range_without_moving_contract_boundary(self):
        self.project.tanggal_akhir_tambahan = date(2026, 10, 2)  # Jumat, minggu yang sama
        self.assertEqual(work_period_end(self.project), date(2026, 10, 2))
        self.assertEqual(contract_boundary_week(self.project), 1)
        self.assertFalse(is_extension_week(self.project, 1))
        self.assertTrue(is_extension_week(self.project, 2))
        self.assertTrue(is_extension_day(self.project, date(2026, 10, 1)))
        self.assertTrue(is_extension_day(self.project, date(2026, 10, 2)))
        self.assertFalse(is_extension_day(self.project, date(2026, 10, 3)))

    def test_report_period_count_uses_additional_end(self):
        self.project.tanggal_akhir_tambahan = date(2026, 12, 31)
        self.assertEqual(project_report_period_counts(self.project), (14, 4))
