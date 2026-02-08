from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project


User = get_user_model()
TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != "config.middleware.timeout.TimeoutMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PrelaunchFunctionalSmokeTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!@#"
        self.owner = User.objects.create_user(
            username="owner_smoke",
            email="owner_smoke@example.com",
            password=self.password,
            is_staff=False,
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.non_owner = User.objects.create_user(
            username="non_owner_smoke",
            email="non_owner_smoke@example.com",
            password=self.password,
            subscription_status=User.SubscriptionStatus.TRIAL,
            trial_end_date=timezone.now() + timedelta(days=14),
        )

    def test_login_logout_and_dashboard_access(self):
        login_url = reverse("account_login")
        dashboard_url = reverse("dashboard:dashboard")
        logout_url = reverse("account_logout")

        self.assertEqual(self.client.get(login_url).status_code, 200)

        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        self.assertEqual(self.client.get(dashboard_url).status_code, 200)

        logout_response = self.client.post(logout_url)
        self.assertIn(logout_response.status_code, {200, 302, 303})

        dashboard_after_logout = self.client.get(dashboard_url)
        self.assertIn(dashboard_after_logout.status_code, {301, 302})

    def test_signup_page_available_and_creates_user(self):
        signup_url = reverse("account_signup")
        self.assertEqual(self.client.get(signup_url).status_code, 200)

        response = self.client.post(
            signup_url,
            {
                "username": "signup_smoke",
                "email": "signup_smoke@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertIn(response.status_code, {200, 302, 303})

    def test_owner_edit_delete_project(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))

        create_response = self.client.post(
            reverse("dashboard:dashboard"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-nama": "Project Smoke",
                "form-0-tanggal_mulai": "2026-01-01",
                "form-0-sumber_dana": "APBD",
                "form-0-lokasi_project": "Jakarta",
                "form-0-nama_client": "Client Smoke",
                "form-0-anggaran_owner": "1000000",
            },
        )
        self.assertIn(create_response.status_code, {302, 303})
        project = Project.objects.get(owner=self.owner, nama="Project Smoke")

        edit_response = self.client.post(
            reverse("dashboard:project_edit", kwargs={"pk": project.pk}),
            {
                "nama": "Project Smoke Updated",
                "tanggal_mulai": "2026-01-01",
                "sumber_dana": "APBD",
                "lokasi_project": "Bandung",
                "nama_client": "Client Smoke Updated",
                "anggaran_owner": "2000000",
                "next": reverse("dashboard:dashboard"),
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.nama, "Project Smoke Updated")
        self.assertEqual(project.lokasi_project, "Bandung")

        delete_response = self.client.post(
            reverse("dashboard:project_delete", kwargs={"pk": project.pk}),
            {"next": reverse("dashboard:dashboard")},
        )
        self.assertEqual(delete_response.status_code, 302)
        project.refresh_from_db()
        self.assertFalse(project.is_active)

    def test_non_owner_blocked_from_project_pages(self):
        project = Project.objects.create(
            owner=self.owner,
            nama="Private Project",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Surabaya",
            nama_client="Private Client",
            anggaran_owner=123456,
        )
        self.assertTrue(self.client.login(username=self.non_owner.username, password=self.password))

        detail_status = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": project.pk})).status_code
        edit_status = self.client.get(reverse("dashboard:project_edit", kwargs={"pk": project.pk})).status_code
        delete_status = self.client.get(reverse("dashboard:project_delete", kwargs={"pk": project.pk})).status_code

        self.assertIn(detail_status, {302, 403, 404})
        self.assertIn(edit_status, {302, 403, 404})
        self.assertIn(delete_status, {302, 403, 404})
