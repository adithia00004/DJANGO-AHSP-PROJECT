"""WP-B6 inc-B6a — canonical weekly distribution builder contract tests."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project

from .models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
)
from .services import build_weekly_distribution


class WeeklyDistributionBuilderTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b6a-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B6 Weekly")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self._order = 0

    def _pekerjaan(self, kode):
        self._order += 1
        return Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode=kode,
            snapshot_uraian=f"P {kode}", snapshot_satuan="m2", ordering_index=self._order,
        )

    def _weekly(self, pekerjaan, week_number, planned, start, end):
        return PekerjaanProgressWeekly.objects.create(
            project=self.project, pekerjaan=pekerjaan, week_number=week_number,
            week_start_date=date.fromisoformat(start), week_end_date=date.fromisoformat(end),
            planned_proportion=Decimal(str(planned)),
        )

    def test_empty_project(self):
        dist = build_weekly_distribution(self.project)
        self.assertEqual(dist["weeks"], [])
        self.assertEqual(dist["by_pekerjaan"], {})

    def test_weeks_are_canonical_sorted_with_dates(self):
        p = self._pekerjaan("P1")
        self._weekly(p, 2, "50.00", "2026-01-08", "2026-01-14")
        self._weekly(p, 1, "50.00", "2026-01-01", "2026-01-07")

        weeks = build_weekly_distribution(self.project)["weeks"]
        self.assertEqual([w["week_number"] for w in weeks], [1, 2])
        self.assertEqual(weeks[0]["start_date"], date(2026, 1, 1))
        self.assertEqual(weeks[1]["end_date"], date(2026, 1, 14))

    def test_fractions_are_proportion_over_100(self):
        p = self._pekerjaan("P1")
        self._weekly(p, 1, "40.00", "2026-01-01", "2026-01-07")
        self._weekly(p, 2, "60.00", "2026-01-08", "2026-01-14")

        dist = build_weekly_distribution(self.project)
        buckets = dist["by_pekerjaan"][p.id]
        self.assertEqual(buckets[1], Decimal("0.40"))
        self.assertEqual(buckets[2], Decimal("0.60"))

    def test_full_schedule_has_zero_unscheduled(self):
        p = self._pekerjaan("P1")
        self._weekly(p, 1, "100.00", "2026-01-01", "2026-01-07")
        dist = build_weekly_distribution(self.project)
        self.assertEqual(dist["scheduled_fraction"][p.id], Decimal("1.00"))
        self.assertEqual(dist["unscheduled_fraction"][p.id], Decimal("0"))

    def test_partial_schedule_unscheduled_remainder(self):
        p = self._pekerjaan("P1")
        self._weekly(p, 1, "60.00", "2026-01-01", "2026-01-07")
        dist = build_weekly_distribution(self.project)
        self.assertEqual(dist["scheduled_fraction"][p.id], Decimal("0.60"))
        self.assertEqual(dist["unscheduled_fraction"][p.id], Decimal("0.40"))

    def test_pekerjaan_without_weekly_rows_is_fully_unscheduled(self):
        p = self._pekerjaan("P1")
        dist = build_weekly_distribution(self.project)
        self.assertEqual(dist["by_pekerjaan"][p.id], {})
        self.assertEqual(dist["scheduled_fraction"][p.id], Decimal("0"))
        self.assertEqual(dist["unscheduled_fraction"][p.id], Decimal("1"))

    def test_weekly_plus_unscheduled_equals_one(self):
        # Core invariant: distributing a base qty over weeks + unscheduled = total.
        p = self._pekerjaan("P1")
        self._weekly(p, 1, "30.00", "2026-01-01", "2026-01-07")
        self._weekly(p, 2, "45.00", "2026-01-08", "2026-01-14")
        dist = build_weekly_distribution(self.project)
        weekly_sum = sum(dist["by_pekerjaan"][p.id].values())
        self.assertEqual(weekly_sum + dist["unscheduled_fraction"][p.id], Decimal("1.00"))
