"""
Regression for launch-audit finding F10 (keputusan pemilik 2026-06-10):
export database referensi digate akses portal (admin), bukan sekadar login.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ReferensiExportPortalGateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.regular_user = user_model.objects.create_user(
            username="regular_f10",
            email="regular-f10@example.com",
            password="Secret123!",
        )
        self.superuser = user_model.objects.create_superuser(
            username="admin_f10",
            email="admin-f10@example.com",
            password="Secret123!",
        )

    def test_regular_user_cannot_export_single_job(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse("referensi:export_single_job", args=[1, "excel"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

    def test_regular_user_cannot_export_search_results(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse("referensi:export_search_results", args=["excel"]) + "?q=beton"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

    def test_regular_user_cannot_poll_task_status(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(
            reverse("referensi:export_task_status", args=["fake-task-id"])
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_task_status_requires_login(self):
        response = self.client.get(
            reverse("referensi:export_task_status", args=["fake-task-id"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_superuser_passes_portal_gate(self):
        self.client.force_login(self.superuser)
        # pk 999999 tidak ada → 404 berarti gate dilewati dan view berjalan.
        response = self.client.get(
            reverse("referensi:export_single_job", args=[999999, "excel"])
        )
        self.assertEqual(response.status_code, 404)
