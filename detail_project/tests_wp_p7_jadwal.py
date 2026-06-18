"""WP-P7 — Jadwal Pekerjaan (Batch A, backend).

- P7a (JDW-02): weekly save fallback honours the project's configured week_end_day,
  not a hardcoded Sunday.
- P7b (audit-gap): reset progress + regenerate (boundary change) write a project-level
  DetailAHSPAudit entry (pekerjaan=None), consistent with the RR-10 pattern.
- P7f (JDW-07): the dead `actual_updated_at` timestamp is gone from the assignments API.
- P7g (JDW-06): the removed "notes" feature is ignored on save (persists empty).
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project

from .models import (
    DetailAHSPAudit,
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    VolumePekerjaan,
)
from .views_api_tahapan_v2 import (
    api_assign_pekerjaan_weekly,
    api_get_project_assignments_v2,
    api_regenerate_tahapan_v2,
    api_reset_progress,
)


class _Base(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p7-owner", password="x")
        self.project = Project.objects.create(
            owner=self.owner, nama="P7",
            tanggal_mulai=date(2026, 1, 1), tanggal_selesai=date(2026, 2, 28),
            # Project.save() enforces week_end_day = week_start_day + 6; use a consistent
            # pair so the boundary is Wednesday(2) — NOT the hardcoded Sunday(6).
            week_start_day=3, week_end_day=2,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P1", snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )
        # progress > 0 requires capacity (volume master); else save → 400 missing_capacity.
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=self.pkj, quantity=Decimal("10"))

    def _req(self, fn, body=None, method="post", **kwargs):
        rf = RequestFactory()
        if method == "post":
            req = rf.post("/x/", data=json.dumps(body or {}), content_type="application/json")
        else:
            req = rf.get("/x/")
        req.user = self.owner
        return fn(req, self.project.id, **kwargs)


class WeekEndDayFallbackTests(_Base):
    def test_save_fallback_uses_project_week_end_day(self):
        # No TahapPelaksanaan exists → save takes the fallback date computation, which
        # must use project.week_end_day (Wednesday=2), not hardcoded Sunday.
        resp = self._req(api_assign_pekerjaan_weekly, {
            "mode": "planned",
            "assignments": [{"pekerjaan_id": self.pkj.id, "week_number": 1, "planned_proportion": 50}],
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        wp = PekerjaanProgressWeekly.objects.get(project=self.project, pekerjaan=self.pkj, week_number=1)
        self.assertEqual(wp.week_end_date.weekday(), 2)  # Wednesday, per project config


class ResetRegenerateAuditTests(_Base):
    def _weekly(self):
        return PekerjaanProgressWeekly.objects.create(
            project=self.project, pekerjaan=self.pkj, week_number=1,
            week_start_date=date(2026, 1, 1), week_end_date=date(2026, 1, 7),
            planned_proportion=Decimal("50.00"), actual_proportion=Decimal("0.00"),
        )

    def _project_audits(self):
        return DetailAHSPAudit.objects.filter(project=self.project, pekerjaan__isnull=True)

    def test_reset_progress_is_audited(self):
        self._weekly()
        resp = self._req(api_reset_progress, {"mode": "planned"})
        self.assertEqual(resp.status_code, 200, resp.content)
        entry = self._project_audits().order_by("-id").first()
        self.assertIsNotNone(entry)
        self.assertIn("Reset progress", entry.change_summary)
        self.assertEqual(entry.new_data.get("reset_mode"), "planned")

    def test_regenerate_boundary_change_is_audited(self):
        # week_end_day 2 → 6 is a real boundary change → one project-level audit entry.
        resp = self._req(api_regenerate_tahapan_v2, {"mode": "weekly", "week_end_day": 6})
        self.assertEqual(resp.status_code, 200, resp.content)
        entry = self._project_audits().order_by("-id").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.old_data.get("week_end_day"), 2)
        self.assertEqual(entry.new_data.get("week_end_day"), 6)


class ApiSurfaceTests(_Base):
    def test_assignments_response_drops_actual_updated_at(self):
        PekerjaanProgressWeekly.objects.create(
            project=self.project, pekerjaan=self.pkj, week_number=1,
            week_start_date=date(2026, 1, 1), week_end_date=date(2026, 1, 7),
            planned_proportion=Decimal("50.00"),
        )
        resp = self._req(api_get_project_assignments_v2, method="get")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = json.loads(resp.content)
        rows = body.get("assignments", [])
        self.assertTrue(rows)
        self.assertNotIn("actual_updated_at", rows[0])  # JDW-07: dead field removed

    def test_notes_input_is_ignored_on_save(self):
        resp = self._req(api_assign_pekerjaan_weekly, {
            "mode": "planned",
            "assignments": [{
                "pekerjaan_id": self.pkj.id, "week_number": 1,
                "planned_proportion": 50, "notes": "catatan lama",
            }],
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        wp = PekerjaanProgressWeekly.objects.get(project=self.project, pekerjaan=self.pkj, week_number=1)
        self.assertEqual(wp.notes, "")  # JDW-06: notes feature removed

    def test_assign_weekly_unexpected_error_does_not_leak_exception_text(self):
        secret = "secret-assign-weekly"
        with patch.object(PekerjaanProgressWeekly.objects, "get_or_create", side_effect=RuntimeError(secret)):
            resp = self._req(api_assign_pekerjaan_weekly, {
                "mode": "planned",
                "assignments": [{
                    "pekerjaan_id": self.pkj.id,
                    "week_number": 1,
                    "planned_proportion": 50,
                }],
            })
        self.assertEqual(resp.status_code, 500, resp.content)
        self.assertNotIn(secret, resp.content.decode("utf-8"))

    def test_regenerate_unexpected_error_does_not_leak_exception_text(self):
        secret = "secret-regenerate"
        with patch("detail_project.views_api_tahapan_v2.sync_weekly_to_tahapan", side_effect=RuntimeError(secret)):
            resp = self._req(api_regenerate_tahapan_v2, {"mode": "custom", "week_end_day": 2})
        self.assertEqual(resp.status_code, 500, resp.content)
        self.assertNotIn(secret, resp.content.decode("utf-8"))


class WeekNumberBuilderContractTests(TestCase):
    """WP-P7m (R4): lock the canonical week-numbering builder. After B6d, the frontend
    must consume server week metadata rather than recompute it — these tests pin the
    server's authoritative behaviour (week-end aligns to week_end_day; weeks contiguous;
    week_number round-trips)."""

    def test_week_end_aligns_to_configured_week_end_day(self):
        from .progress_utils import get_week_date_range
        start = date(2026, 1, 1)  # Thursday
        for wed in (0, 2, 6):  # Mon, Wed, Sun
            _, week_end = get_week_date_range(1, start, week_end_day=wed)
            self.assertEqual(week_end.weekday(), wed)

    def test_weeks_are_contiguous_7_day_blocks(self):
        from .progress_utils import get_week_date_range
        start = date(2026, 1, 1)
        ws1, _ = get_week_date_range(1, start, week_end_day=6)
        ws2, _ = get_week_date_range(2, start, week_end_day=6)
        self.assertEqual(ws2 - ws1, timedelta(days=7))

    def test_week_number_round_trips(self):
        from .progress_utils import calculate_week_number, get_week_date_range
        start = date(2026, 1, 1)
        for wn in (1, 2, 5, 9):
            week_start, _ = get_week_date_range(wn, start, week_end_day=6)
            self.assertEqual(calculate_week_number(week_start, start, week_end_day=6), wn)
