from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.forms import ProjectForm
from dashboard.models import Project


class AdditionalWorkTimeFieldTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            "additional-work-field",
            password="StrongPass123!",
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )

    def _project(self, **kwargs):
        return Project.objects.create(
            owner=self.owner,
            nama="Additional Work Project",
            sumber_dana="APBD",
            lokasi_project="Makassar",
            nama_client="Dinas",
            anggaran_owner=Decimal("1000"),
            tanggal_mulai=date(2026, 9, 1),
            tanggal_selesai=date(2026, 9, 30),
            **kwargs,
        )

    def test_additional_end_is_optional_and_not_editable_in_dashboard_project_form(self):
        project = self._project()
        self.assertIsNone(project.tanggal_akhir_tambahan)
        self.assertNotIn("tanggal_akhir_tambahan", ProjectForm().fields)

        project.tanggal_akhir_tambahan = date(2026, 12, 31)
        project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("dashboard:project_edit", kwargs={"pk": project.pk})
        )
        self.assertContains(response, "Tambahan waktu kerja: s.d. 31 Des 2026")
        self.assertNotContains(response, 'name="tanggal_akhir_tambahan"')

    def test_additional_end_change_increments_schedule_revision(self):
        project = self._project()
        before = project.schedule_revision
        project.tanggal_akhir_tambahan = date(2026, 12, 31)
        project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        project.refresh_from_db()
        self.assertEqual(project.schedule_revision, before + 1)

    def test_database_rejects_additional_end_on_or_before_contract_end(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._project(tanggal_akhir_tambahan=date(2026, 9, 30))

    def test_database_rejects_additional_end_without_contract_end(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                project = Project(
                    owner=self.owner,
                    nama="Missing Contract End",
                    sumber_dana="APBD",
                    lokasi_project="Makassar",
                    nama_client="Dinas",
                    anggaran_owner=Decimal("1000"),
                    tanggal_mulai=date(2026, 9, 1),
                    tanggal_selesai=None,
                    tanggal_akhir_tambahan=date(2026, 12, 31),
                )
                project.save()

    def test_edit_project_contract_past_additional_end_clears_excluded_field(self):
        from django.urls import reverse

        project = self._project(tanggal_akhir_tambahan=date(2026, 12, 31))
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("dashboard:project_edit", kwargs={"pk": project.pk}),
            {
                "nama": project.nama,
                "tanggal_mulai": "2026-09-01",
                "tanggal_selesai": "2027-01-15",
                "durasi_hari": "",
                "sumber_dana": project.sumber_dana,
                "lokasi_project": project.lokasi_project,
                "nama_client": project.nama_client,
                "anggaran_owner": "1000",
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:400])
        project.refresh_from_db()
        self.assertEqual(project.tanggal_selesai, date(2027, 1, 15))
        self.assertIsNone(project.tanggal_akhir_tambahan)
