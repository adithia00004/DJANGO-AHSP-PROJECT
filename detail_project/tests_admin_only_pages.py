"""
Regression for launch-audit finding U14 (2026-06-10).

Orphan Cleanup and Audit Trail are admin-role utility pages. Regular project
owners must neither see them in the sidebar nor be able to open them; staff
and superuser retain access.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from dashboard.models import Project

ADMIN_ONLY_PAGES = ("orphan_cleanup", "audit_trail")

# TimeoutMiddleware runs the view in a separate thread, which drops the
# force_login session and makes every request redirect to /accounts/login/
# (KF-01). Drop it for these page-access tests; product auth is unaffected.
TEST_MIDDLEWARE = [
    m for m in settings.MIDDLEWARE if m != "config.middleware.timeout.TimeoutMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class AdminOnlyPagesTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.regular_owner = user_model.objects.create_user(
            username="regular_owner_u14",
            email="regular-u14@example.com",
            password="Secret123!",
        )
        self.staff_owner = user_model.objects.create_user(
            username="staff_owner_u14",
            email="staff-u14@example.com",
            password="Secret123!",
            is_staff=True,
        )
        self.regular_project = Project.objects.create(
            owner=self.regular_owner,
            nama="Project U14 Regular",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client U14",
            anggaran_owner=1000,
        )
        self.staff_project = Project.objects.create(
            owner=self.staff_owner,
            nama="Project U14 Staff",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client U14",
            anggaran_owner=1000,
        )

    def _page_url(self, page_name, project):
        return reverse(
            f"detail_project:{page_name}", kwargs={"project_id": project.id}
        )

    def test_regular_owner_is_redirected_away(self):
        self.client.force_login(
            self.regular_owner, backend="django.contrib.auth.backends.ModelBackend"
        )
        for page_name in ADMIN_ONLY_PAGES:
            with self.subTest(page_name=page_name):
                response = self.client.get(
                    self._page_url(page_name, self.regular_project)
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response["Location"],
                    reverse(
                        "detail_project:list_pekerjaan",
                        kwargs={"project_id": self.regular_project.id},
                    ),
                )

    def test_staff_owner_can_open_pages(self):
        self.client.force_login(
            self.staff_owner, backend="django.contrib.auth.backends.ModelBackend"
        )
        for page_name in ADMIN_ONLY_PAGES:
            with self.subTest(page_name=page_name):
                response = self.client.get(
                    self._page_url(page_name, self.staff_project)
                )
                self.assertEqual(response.status_code, 200)

    def test_sidebar_hides_admin_links_from_regular_owner(self):
        self.client.force_login(
            self.regular_owner, backend="django.contrib.auth.backends.ModelBackend"
        )
        response = self.client.get(
            self._page_url("list_pekerjaan", self.regular_project)
        )
        content = response.content.decode()
        self.assertNotIn("orphan-cleanup/", content)
        self.assertNotIn("audit-trail/", content)

    def test_sidebar_shows_admin_links_to_staff(self):
        self.client.force_login(
            self.staff_owner, backend="django.contrib.auth.backends.ModelBackend"
        )
        response = self.client.get(
            self._page_url("list_pekerjaan", self.staff_project)
        )
        content = response.content.decode()
        self.assertIn("orphan-cleanup/", content)
        self.assertIn("audit-trail/", content)
