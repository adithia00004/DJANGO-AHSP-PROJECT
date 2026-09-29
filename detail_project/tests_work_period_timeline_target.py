import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from dashboard.models import Project


class TimelineTargetFieldTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            "timeline-target-field",
            password="StrongPass123!",
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Timeline Target Field",
            sumber_dana="APBD",
            lokasi_project="Makassar",
            nama_client="Dinas",
            anggaran_owner=Decimal("1000"),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 2, 28),
            durasi_hari=59,
        )

    def _post(self, route, payload):
        url = reverse(route, kwargs={"project_id": self.project.pk})
        request = RequestFactory().post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.owner
        match = resolve(url)
        return match.func(request, **match.kwargs)

    def _payload(self, **updates):
        return {
            "tanggal_mulai": self.project.tanggal_mulai.isoformat(),
            "tanggal_selesai": self.project.tanggal_selesai.isoformat(),
            "schedule_revision": self.project.schedule_revision,
            **updates,
        }

    def test_extension_target_changes_only_additional_end(self):
        before_duration = self.project.durasi_hari
        response = self._post(
            "detail_project:api_commit_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                tanggal_akhir_tambahan="2026-03-07",
                resolution="none",
            ),
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))
        self.assertEqual(self.project.tanggal_akhir_tambahan, date(2026, 3, 7))
        self.assertEqual(self.project.durasi_hari, before_duration)

    def test_preview_detects_type_two_and_reduction_from_week_counts(self):
        type_two = self._post(
            "detail_project:api_preview_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                tanggal_akhir_tambahan="2026-03-31",
            ),
        )
        self.assertEqual(type_two.status_code, 200, type_two.content[:400])
        self.assertEqual(json.loads(type_two.content)["impact"]["jenis"], "tipe_2")

        self.project.tanggal_akhir_tambahan = date(2026, 3, 31)
        self.project.save()
        reduction = self._post(
            "detail_project:api_preview_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                tanggal_akhir_tambahan="2026-03-15",
            ),
        )
        self.assertEqual(reduction.status_code, 200, reduction.content[:400])
        self.assertEqual(json.loads(reduction.content)["impact"]["jenis"], "pengurangan")

        unchanged = self._post(
            "detail_project:api_preview_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                tanggal_akhir_tambahan="2026-03-31",
            ),
        )
        self.assertEqual(unchanged.status_code, 200, unchanged.content[:400])
        self.assertEqual(json.loads(unchanged.content)["impact"]["jenis"], "tidak_berubah")

    def test_preview_detects_extra_days_inside_the_same_final_week(self):
        self.project.tanggal_selesai = date(2026, 2, 25)
        self.project.durasi_hari = 56
        self.project.save(update_fields=["tanggal_selesai", "durasi_hari", "updated_at"])
        response = self._post(
            "detail_project:api_preview_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                tanggal_akhir_tambahan="2026-02-27",
            ),
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertEqual(json.loads(response.content)["impact"]["jenis"], "tipe_1")
        self.assertEqual(json.loads(response.content)["impact"]["new_week_count"], 9)


    def test_contract_change_keeps_additional_end_when_it_is_still_later(self):
        self.project.tanggal_akhir_tambahan = date(2026, 3, 31)
        self.project.save()
        response = self._post(
            "detail_project:api_commit_project_timeline",
            self._payload(tanggal_selesai="2026-03-15", resolution="none"),
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 3, 15))
        self.assertEqual(self.project.tanggal_akhir_tambahan, date(2026, 3, 31))

    def test_contract_change_clears_additional_end_when_contract_reaches_it(self):
        self.project.tanggal_akhir_tambahan = date(2026, 3, 31)
        self.project.save()
        response = self._post(
            "detail_project:api_commit_project_timeline",
            self._payload(tanggal_selesai="2026-04-15", resolution="none"),
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 4, 15))
        self.assertIsNone(self.project.tanggal_akhir_tambahan)

    def test_additional_end_must_be_after_contract_end(self):
        response = self._post(
            "detail_project:api_preview_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                tanggal_akhir_tambahan="2026-02-28",
            ),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))
        self.assertIsNone(self.project.tanggal_akhir_tambahan)

    def test_delete_additional_restores_contract_range(self):
        self.project.tanggal_akhir_tambahan = date(2026, 3, 31)
        self.project.save()
        preview = self._post(
            "detail_project:api_preview_project_timeline",
            self._payload(target_field="tanggal_akhir_tambahan", hapus_tambahan=True),
        )
        self.assertEqual(preview.status_code, 200, preview.content[:400])
        self.assertEqual(json.loads(preview.content)["impact"]["jenis"], "hapus")
        response = self._post(
            "detail_project:api_commit_project_timeline",
            self._payload(
                target_field="tanggal_akhir_tambahan",
                hapus_tambahan=True,
                resolution="none",
            ),
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))
        self.assertIsNone(self.project.tanggal_akhir_tambahan)
