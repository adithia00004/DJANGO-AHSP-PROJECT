import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    TahapPelaksanaan,
    VolumePekerjaan,
)
from detail_project.progress_utils import build_week_buckets
from detail_project.progress_write_service import PlannedProgressOutsideWorkPeriod, write_progress
from detail_project.readiness import compute_project_readiness
from detail_project.timeline_utils import (
    TimelineChangeError,
    _guard_target,
    analyze_project_timeline_change,
    analyze_week_boundary_contract_impact,
)


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
            tanggal_selesai=date(2026, 9, 7),
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

    def test_week_boundary_preview_finds_newly_additional_planned_week(self):
        _, start, end = build_week_buckets(
            self.project.tanggal_mulai,
            self.project.tanggal_akhir_tambahan,
            self.project.week_end_day,
        )[1]
        write_progress(self.project, [{
            "pekerjaan_id": self.pekerjaan.id,
            "week_number": 2,
            "week_start_date": start,
            "week_end_date": end,
            "planned_proportion": Decimal("20"),
            "actual_proportion": Decimal("0"),
        }], kind="historical")

        impact = analyze_week_boundary_contract_impact(self.project, 0)
        self.assertEqual(impact["old_boundary_week"], 2)
        self.assertEqual(impact["new_boundary_week"], 1)
        self.assertEqual(impact["planned_extension_records"], 1)
        self.assertEqual(impact["planned_extension_rows"][0]["week_number"], 2)

    def test_tahapan_api_returns_server_work_period_markers_per_column(self):
        boundary_stage = TahapPelaksanaan.objects.create(
            project=self.project,
            nama="Week 2",
            urutan=1,
            tanggal_mulai=date(2026, 9, 7),
            tanggal_selesai=date(2026, 9, 13),
            is_auto_generated=True,
            generation_mode="weekly",
        )
        extension_stage = TahapPelaksanaan.objects.create(
            project=self.project,
            nama="Week 3",
            urutan=2,
            tanggal_mulai=date(2026, 9, 14),
            tanggal_selesai=date(2026, 9, 20),
            is_auto_generated=True,
            generation_mode="weekly",
        )
        url = reverse(
            "detail_project:api_list_create_tahapan",
            kwargs={"project_id": self.project.pk},
        )
        request = RequestFactory().get(url)
        request.user = self.owner
        match = resolve(url)
        response = match.func(request, **match.kwargs)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        by_id = {row["tahapan_id"]: row for row in payload["tahapan"]}
        self.assertTrue(by_id[boundary_stage.id]["is_boundary_week"])
        self.assertFalse(by_id[boundary_stage.id]["is_extension_week"])
        self.assertEqual(by_id[boundary_stage.id]["work_end_date"], "2026-09-07")
        self.assertTrue(by_id[extension_stage.id]["is_extension_week"])
        self.assertFalse(by_id[extension_stage.id]["is_boundary_week"])
        self.assertTrue(by_id[extension_stage.id]["contains_additional_period"])
        self.assertEqual(payload["work_period"]["extension_week_numbers"], [3])

    def test_jadwal_page_renders_extension_controls_and_timeline_metadata(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse(
            "detail_project:jadwal_pekerjaan",
            kwargs={"project_id": self.project.pk},
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="btn-work-extension"')
        self.assertContains(response, 'id="workExtensionModal"')
        self.assertContains(response, 'id="work-extension-end-date"')
        self.assertContains(response, 'data-project-contract-end="2026-09-07"')
        self.assertContains(response, 'data-project-additional-end="2026-09-20"')
        self.assertContains(response, 'data-api-timeline-preview=')
        self.assertContains(response, 'data-api-timeline-commit=')

    def test_shortening_additional_period_does_not_drop_notes_outside_new_range(self):
        write_progress(self.project, [self._week_three_cell(
            planned_proportion=Decimal("0"),
            actual_proportion=Decimal("0"),
            actual_cost=None,
            notes="catatan akhir masa kerja",
        )], kind="historical")
        preview_url = reverse(
            "detail_project:api_preview_project_timeline",
            kwargs={"project_id": self.project.pk},
        )
        payload = {
            "tanggal_mulai": self.project.tanggal_mulai.isoformat(),
            "target_field": "tanggal_akhir_tambahan",
            "tanggal_akhir_tambahan": "2026-09-13",
            "schedule_revision": self.project.schedule_revision,
        }
        request = RequestFactory().post(
            preview_url, data=json.dumps(payload), content_type="application/json"
        )
        request.user = self.owner
        match = resolve(preview_url)
        preview = match.func(request, **match.kwargs)
        impact = json.loads(preview.content)["impact"]
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(impact["blocking_reason"], "notes_out_of_window")
        self.assertEqual(impact["blocking_week_numbers"], [3])
        self.assertEqual(json.loads(preview.content)["previews"], [])

        commit_url = reverse(
            "detail_project:api_commit_project_timeline",
            kwargs={"project_id": self.project.pk},
        )
        request = RequestFactory().post(
            commit_url,
            data=json.dumps({**payload, "resolution": "none"}),
            content_type="application/json",
        )
        request.user = self.owner
        match = resolve(commit_url)
        commit = match.func(request, **match.kwargs)
        self.assertEqual(commit.status_code, 400)
        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=3)
        self.assertEqual(row.notes, "catatan akhir masa kerja")
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_akhir_tambahan, date(2026, 9, 20))

    def test_additional_timeline_api_rejects_a_changed_project_start(self):
        self.client.force_login(self.owner)
        preview_url = reverse(
            "detail_project:api_preview_project_timeline",
            kwargs={"project_id": self.project.pk},
        )
        commit_url = reverse(
            "detail_project:api_commit_project_timeline",
            kwargs={"project_id": self.project.pk},
        )
        base_payload = {
            "tanggal_mulai": "2026-09-05",
            "target_field": "tanggal_akhir_tambahan",
            "tanggal_akhir_tambahan": "2026-09-25",
            "schedule_revision": self.project.schedule_revision,
        }

        for url, extra in ((preview_url, {}), (commit_url, {"resolution": "none"})):
            response = self.client.post(
                url,
                data=json.dumps({**base_payload, **extra}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400, response.content)
            self.assertEqual(
                response.json()["impact"]["reason"],
                "additional_timeline_start_changed",
            )

        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 9, 6))
        self.assertEqual(self.project.tanggal_selesai, date(2026, 9, 7))
        self.assertEqual(self.project.tanggal_akhir_tambahan, date(2026, 9, 20))

    def test_shortening_with_remaining_extension_does_not_offer_rejected_accumulate(self):
        self.project.tanggal_akhir_tambahan = date(2026, 10, 11)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        _, start, end = build_week_buckets(
            self.project.tanggal_mulai,
            self.project.tanggal_akhir_tambahan,
            self.project.week_end_day,
        )[5]
        write_progress(self.project, [{
            "pekerjaan_id": self.pekerjaan.id,
            "week_number": 6,
            "week_start_date": start,
            "week_end_date": end,
            "planned_proportion": Decimal("20"),
            "actual_proportion": Decimal("0"),
        }], kind="historical")

        impact = analyze_project_timeline_change(
            self.project,
            self.project.tanggal_mulai,
            date(2026, 9, 27),
            target_field="tanggal_akhir_tambahan",
        )
        self.assertEqual(impact["contract_boundary_week"], 2)
        self.assertEqual(impact["new_week_count"], 4)
        self.assertEqual(impact["allowed_resolutions"], ["follow_date"])
        self.assertEqual(impact["recommended_resolution"], "follow_date")

    def _seed_week_two_extension_plan(self):
        _, start, end = build_week_buckets(
            self.project.tanggal_mulai,
            self.project.tanggal_akhir_tambahan,
            self.project.week_end_day,
        )[1]
        write_progress(self.project, [{
            "pekerjaan_id": self.pekerjaan.id,
            "week_number": 2,
            "week_start_date": start,
            "week_end_date": end,
            "planned_proportion": Decimal("20"),
            "actual_proportion": Decimal("15"),
            "actual_cost": Decimal("5000"),
            "notes": "rencana dan realisasi lama",
        }], kind="historical")

    def _seed_week_three_legacy_plan(self):
        _, start, end = build_week_buckets(
            self.project.tanggal_mulai,
            self.project.tanggal_akhir_tambahan,
            self.project.week_end_day,
        )[2]
        write_progress(self.project, [{
            "pekerjaan_id": self.pekerjaan.id,
            "week_number": 3,
            "week_start_date": start,
            "week_end_date": end,
            "planned_proportion": Decimal("7"),
            "actual_proportion": Decimal("8"),
            "actual_cost": Decimal("3000"),
            "notes": "data minggu tambahan lama",
        }], kind="historical")

    def _post_week_boundary(self, route, plan_resolution=None):
        url = reverse(route, kwargs={"project_id": self.project.pk})
        payload = {
            "week_start_day": 1,
            "week_end_day": 0,
            "schedule_revision": self.project.schedule_revision,
        }
        if route == "detail_project:api_v2_regenerate_tahapan":
            payload["mode"] = "weekly"
        if plan_resolution:
            payload["plan_resolution"] = plan_resolution
        request = RequestFactory().post(url, data=json.dumps(payload), content_type="application/json")
        request.user = self.owner
        match = resolve(url)
        return match.func(request, **match.kwargs)

    def test_week_boundary_api_requires_choice_and_moves_only_newly_additional_plan(self):
        route = "detail_project:api_update_week_boundaries"
        self._seed_week_two_extension_plan()
        self._seed_week_three_legacy_plan()

        response = self._post_week_boundary(route)
        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["code"], "week_boundary_moves_plan_into_extension")
        self.assertEqual(payload["impact"]["planned_extension_records"], 1)
        self.assertEqual(payload["impact"]["planned_extension_rows"][0]["week_number"], 2)
        self.project.refresh_from_db()
        self.assertEqual((self.project.week_start_day, self.project.week_end_day), (0, 6))

        response = self._post_week_boundary(route, "move_planned_to_boundary")
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertEqual(json.loads(response.content)["planned_moved_count"], 1)
        rows = {
            row.week_number: row
            for row in PekerjaanProgressWeekly.objects.filter(project=self.project)
        }
        self.assertEqual(rows[1].planned_proportion, Decimal("20"))
        self.assertEqual((rows[1].week_start_date, rows[1].week_end_date), (
            date(2026, 9, 6), date(2026, 9, 7),
        ))
        self.assertEqual(rows[2].planned_proportion, Decimal("0"))
        self.assertEqual(rows[2].actual_proportion, Decimal("15"))
        self.assertEqual(rows[2].actual_cost, Decimal("5000"))
        self.assertEqual((rows[2].week_start_date, rows[2].week_end_date), (
            date(2026, 9, 8), date(2026, 9, 14),
        ))
        # Historical plans already in extension weeks are not part of K-6.
        self.assertEqual(rows[3].planned_proportion, Decimal("7"))
        self.assertEqual(rows[3].actual_proportion, Decimal("8"))
        self.assertEqual(rows[3].actual_cost, Decimal("3000"))

    def test_week_boundary_without_affected_plan_saves_without_confirmation(self):
        response = self._post_week_boundary("detail_project:api_update_week_boundaries")
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertEqual(json.loads(response.content)["planned_moved_count"], 0)
        self.project.refresh_from_db()
        self.assertEqual((self.project.week_start_day, self.project.week_end_day), (1, 0))

    def test_week_boundary_regeneration_uses_the_same_plan_confirmation(self):
        route = "detail_project:api_v2_regenerate_tahapan"
        self._seed_week_two_extension_plan()

        response = self._post_week_boundary(route)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            json.loads(response.content)["code"],
            "week_boundary_moves_plan_into_extension",
        )
        self.project.refresh_from_db()
        self.assertEqual((self.project.week_start_day, self.project.week_end_day), (0, 6))

        response = self._post_week_boundary(route, "move_planned_to_boundary")
        self.assertEqual(response.status_code, 200, response.content[:400])
        rows = {
            row.week_number: row
            for row in PekerjaanProgressWeekly.objects.filter(project=self.project)
        }
        self.assertEqual(rows[1].planned_proportion, Decimal("20"))
        self.assertEqual(rows[2].planned_proportion, Decimal("0"))
        self.assertEqual(rows[2].actual_proportion, Decimal("15"))
        self.assertEqual(rows[2].actual_cost, Decimal("5000"))

    def test_failed_week_boundary_regeneration_rolls_back_plan_move_and_settings(self):
        self._seed_week_two_extension_plan()
        with patch(
            "detail_project.views_api_tahapan_v2.sync_weekly_to_tahapan",
            side_effect=RuntimeError("simulated sync failure"),
        ):
            response = self._post_week_boundary(
                "detail_project:api_v2_regenerate_tahapan",
                "move_planned_to_boundary",
            )

        self.assertEqual(response.status_code, 500)
        self.project.refresh_from_db()
        self.assertEqual((self.project.week_start_day, self.project.week_end_day), (0, 6))
        rows = {
            row.week_number: row
            for row in PekerjaanProgressWeekly.objects.filter(project=self.project)
        }
        self.assertEqual(rows[2].planned_proportion, Decimal("20"))
        self.assertEqual(rows[2].actual_proportion, Decimal("15"))
        self.assertEqual(rows[2].actual_cost, Decimal("5000"))
        self.assertNotIn(1, rows)

    def test_week_boundary_that_would_hide_progress_outside_new_work_range_is_blocked(self):
        self.project.tanggal_akhir_tambahan = date(2026, 9, 14)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        self._seed_week_three_legacy_plan()

        response = self._post_week_boundary("detail_project:api_update_week_boundaries")
        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["code"], "week_boundary_excludes_progress")
        self.assertEqual(payload["impact"]["new_work_week_count"], 2)
        self.project.refresh_from_db()
        self.assertEqual((self.project.week_start_day, self.project.week_end_day), (0, 6))
        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=3)
        self.assertEqual(row.actual_proportion, Decimal("8"))
        self.assertEqual(row.actual_cost, Decimal("3000"))

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
