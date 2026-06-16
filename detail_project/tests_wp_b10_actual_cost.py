"""WP-B10 (JDW-05) — clearing actual realization must also clear actual_cost.

actual_cost is canonical on PekerjaanProgressWeekly (no separate legacy field →
mapping migration NOT REQUIRED). The only defect is the "reset actual" path
leaving actual_cost orphaned after actual_proportion is zeroed.
"""
import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project

from .models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
)
from .views_api_tahapan_v2 import api_reset_progress


class ResetActualClearsCostTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b10-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B10")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="P1",
            snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )
        self.week = PekerjaanProgressWeekly.objects.create(
            project=self.project, pekerjaan=self.pkj, week_number=1,
            week_start_date=date(2026, 1, 1), week_end_date=date(2026, 1, 7),
            planned_proportion=Decimal("50.00"), actual_proportion=Decimal("40.00"),
            actual_cost=Decimal("1500000.00"),
        )

    def _reset(self, mode):
        req = RequestFactory().post(
            "/reset-progress/", data=json.dumps({"mode": mode}),
            content_type="application/json",
        )
        req.user = self.owner
        return api_reset_progress(req, self.project.id)

    def test_reset_actual_clears_actual_cost(self):
        resp = self._reset("actual")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(json.loads(resp.content)["ok"])
        self.week.refresh_from_db()
        self.assertEqual(self.week.actual_proportion, Decimal("0.00"))
        self.assertIsNone(self.week.actual_cost)  # no orphan actual cost
        # planned untouched
        self.assertEqual(self.week.planned_proportion, Decimal("50.00"))

    def test_reset_planned_leaves_actual_cost_intact(self):
        resp = self._reset("planned")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.week.refresh_from_db()
        self.assertEqual(self.week.planned_proportion, Decimal("0.00"))
        # clearing planned must NOT disturb the actual-side cost projection
        self.assertEqual(self.week.actual_cost, Decimal("1500000.00"))
        self.assertEqual(self.week.actual_proportion, Decimal("40.00"))
