from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from referensi.permissions import REFERENSI_IMPORT_PERMISSIONS, REFERENSI_PORTAL_PERMISSIONS


class ReferensiImportPermissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.no_perm_user = user_model.objects.create_user(
            username="no_perm_import_user",
            email="no-perm-import@example.com",
            password="Secret123!",
        )
        self.portal_only_user = user_model.objects.create_user(
            username="portal_only_user",
            email="portal-only@example.com",
            password="Secret123!",
        )
        self.import_user = user_model.objects.create_user(
            username="import_perm_user",
            email="import-perm@example.com",
            password="Secret123!",
        )

        self._grant_permissions(self.portal_only_user, REFERENSI_PORTAL_PERMISSIONS)
        self._grant_permissions(self.import_user, REFERENSI_IMPORT_PERMISSIONS)

    def _grant_permissions(self, user, codenames):
        raw_codenames = [name.split(".")[-1] for name in codenames]
        perms = Permission.objects.filter(codename__in=raw_codenames)
        user.user_permissions.add(*perms)

    def _assert_redirected_to_login(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    def test_import_endpoints_block_user_without_permissions(self):
        self.client.force_login(self.no_perm_user)

        cases = [
            ("get", reverse("referensi:import_options")),
            ("get", reverse("referensi:import_pdf_convert")),
            ("get", reverse("referensi:import_validate")),
            ("get", reverse("referensi:import_excel")),
            ("get", reverse("referensi:import_staging")),
            ("post", reverse("referensi:import_staging_clear")),
            ("post", reverse("referensi:import_staging_commit")),
            ("get", reverse("referensi:export_valid_excel")),
            ("get", reverse("referensi:export_anomaly_excel")),
            ("post", reverse("referensi:export_from_frontend")),
            ("get", reverse("referensi:import_pdf_download", args=["dummy-file-id"])),
            ("get", reverse("referensi:import_pdf_download_part", args=["dummy-file-id", 1])),
            ("get", reverse("referensi:import_validate_report", args=["dummy-file-id"])),
            ("get", reverse("referensi:import_validate_download", args=["dummy-file-id"])),
        ]

        for method, url in cases:
            if method == "post":
                response = self.client.post(url, data={})
            else:
                response = self.client.get(url)
            self._assert_redirected_to_login(response)

    def test_import_endpoints_block_portal_only_user_without_import_permission(self):
        self.client.force_login(self.portal_only_user)
        response = self.client.get(reverse("referensi:import_options"))

        self._assert_redirected_to_login(response)
