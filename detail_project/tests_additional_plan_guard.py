import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, PekerjaanProgressWeekly, SubKlasifikasi, VolumePekerjaan
from detail_project.progress_utils import build_week_buckets
from detail_project.progress_write_service import PlannedProgressOutsideWorkPeriod, write_progress
from detail_project.readiness import compute_project_readiness
from detail_project.timeline_utils import TimelineChangeError, _guard_target


class AdditionalWorkPlanGuardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            "additional-plan-guard", password="StrongPass123!",
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner, nama="Additional Plan Guard", sumber_dana="APBD",
            lokasi_project="Makassar", nama_client="Dinas",
            anggaran_owner=Decimal("1000"),
            tanggal_mulai=date(2026, 9, 6),
            tanggal_selesai=date(2026, 9, 13),
            tanggal_akhir_tambahan=date(2026, 9, 20),
            week_start_day=0, week_end_day=6,
        )
        klasifikasi = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klasifikasi, name="S", ordering_index=1
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="P-EXT",
            snapshot_uraian="Pekerjaan pada masa tambahan", snapshot_satuan="m2",
            ordering_index=1,
        )
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, quantity=Decimal("100")
        )

    def _week_three_cell(self, **overrides):
        _, start, end = build_week_buckets(
            self.project.tanggal_mulai,
            self.project.tanggal_akhir_tambahan,
            self.project.week_end_day,
        )[2]
        return {
            "pekerjaan_id": self.pekerjaan.id,
            "week_number": 3,
            "week_start_date": start,
            "week_end_date": end,
            **overrides,
        }

    def _post_week_three(self, mode, proportion, **overrides):
        url = reverse(
            "detail_project:api_v2_assign_weekly",
            kwargs={"project_id": self.project.pk},
        )
        request = RequestFactory().post(
            url,
            data=json.dumps({
                "mode": mode,
                "schedule_revision": self.project.schedule_revision,
                "assignments": [{
                    "pekerjaan_id": self.pekerjaan.id,
                    "week_number": 3,
                    "proportion": proportion,
                    **overrides,
                }],
            }),
            content_type="application/json",
        )
        request.user = self.owner
        match = resolve(url)
        return match.func(request, **match.kwargs)

    def test_new_planned_is_rejected_but_actual_and_cost_are_accepted(self):
        response = self._post_week_three("planned", 10)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["errors"][0]["code"], "planned_in_extension")
        self.assertFalse(PekerjaanProgressWeekly.objects.filter(
            pekerjaan=self.pekerjaan, week_number=3
        ).exists())

        response = self._post_week_three("actual", 10, actual_cost="0")
        self.assertEqual(response.status_code, 200, response.content[:400])
        row = PekerjaanProgressWeekly.objects.get(pekerjaan=self.pekerjaan, week_number=3)
        self.assertEqual(row.actual_proportion, Decimal("10"))
        self.assertEqual(row.actual_cost, Decimal("0"))
        self.assertEqual(row.planned_proportion, Decimal("0"))

    def test_historical_plan_is_preserved_and_reported_as_readiness(self):
        write_progress(self.project, [self._week_three_cell(
            planned_proportion=Decimal("20"), actual_proportion=Decimal("0"),
            actual_cost=None, notes="rencana lama",
        )], kind="historical")
        readiness = compute_project_readiness(self.project)
        entries = readiness["planned_in_additional_weeks"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["pekerjaan_id"], self.pekerjaan.id)
        self.assertEqual(entries[0]["issue"], "planned_in_additional_work")

        # Historical planned data must not prevent actual entry on the same row.
        response = self._post_week_three("actual", 10)
        self.assertEqual(response.status_code, 200, response.content[:400])
        row = PekerjaanProgressWeekly.objects.get(pekerjaan=self.pekerjaan, week_number=3)
        self.assertEqual(row.planned_proportion, Decimal("20"))
        self.assertEqual(row.actual_proportion, Decimal("10"))

    def test_user_move_kind_cannot_put_new_plan_in_an_additional_week(self):
        with self.assertRaises(PlannedProgressOutsideWorkPeriod):
            write_progress(
                self.project,
                [self._week_three_cell(planned_proportion=Decimal("5"))],
                kind="user_move",
            )

    def test_timeline_resolution_rejects_new_plan_in_extension_but_keeps_legacy_plan(self):
        write_progress(self.project, [self._week_three_cell(
            planned_proportion=Decimal("20"),
            actual_proportion=Decimal("0"),
            actual_cost=None,
        )], kind="historical")
        source_rows = list(PekerjaanProgressWeekly.objects.filter(project=self.project))
        impact = {
            "new_start": self.project.tanggal_mulai.isoformat(),
            "new_contract_end": self.project.tanggal_selesai.isoformat(),
            "new_additional_end": self.project.tanggal_akhir_tambahan.isoformat(),
        }
        with self.assertRaises(TimelineChangeError) as raised:
            _guard_target(
                {(self.pekerjaan.id, 3): {
                    "planned": Decimal("25"), "actual": Decimal("0"), "actual_cost": None,
                }},
                impact,
                self.project,
                source_rows,
            )
        self.assertEqual(raised.exception.impact["blocking_reason"], "planned_in_extension")

        # Same-week historical planned values are left in place for review.
        _guard_target(
            {(self.pekerjaan.id, 3): {
                "planned": Decimal("20"), "actual": Decimal("0"), "actual_cost": None,
            }},
            impact,
            self.project,
            source_rows,
        )
