import json
from datetime import date, timedelta
from decimal import Decimal

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
class MassEditProjectTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="mass_edit_owner",
            password="StrongPass123!",
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.other_user = User.objects.create_user(
            username="mass_edit_other",
            password="StrongPass123!",
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project_a = self._create_project(
            self.owner,
            "Project Alpha",
            description="Deskripsi lama",
        )
        self.project_b = self._create_project(self.owner, "Project Beta")
        self.other_project = self._create_project(
            self.other_user,
            "Project Milik User Lain",
        )
        self.client.force_login(self.owner)
        self.url = reverse("dashboard:mass_edit_bulk")

    def _create_project(self, owner, name, description=None):
        return Project.objects.create(
            owner=owner,
            nama=name,
            sumber_dana="APBD",
            lokasi_project="Makassar",
            nama_client="Dinas PUPR",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 12, 31),
            deskripsi=description,
        )

    def _post(self, changes):
        return self.client.post(
            self.url,
            data=json.dumps({"changes": changes}),
            content_type="application/json",
        )

    def test_mass_edit_updates_selected_project_and_clears_optional_field(self):
        response = self._post(
            [
                {
                    "id": self.project_a.pk,
                    "nama": "Project Alpha Revisi",
                    "deskripsi": "",
                }
            ]
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.project_a.refresh_from_db()
        self.project_b.refresh_from_db()
        self.assertEqual(self.project_a.nama, "Project Alpha Revisi")
        self.assertEqual(self.project_a.deskripsi, "")
        self.assertEqual(self.project_b.nama, "Project Beta")

    def test_mass_edit_rolls_back_entire_batch_when_one_project_is_invalid(self):
        response = self._post(
            [
                {"id": self.project_a.pk, "nama": "Project Alpha Valid"},
                {"id": self.project_b.pk, "nama": "X"},
            ]
        )

        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertIn(str(self.project_b.pk), body["errors"])
        self.project_a.refresh_from_db()
        self.project_b.refresh_from_db()
        self.assertEqual(self.project_a.nama, "Project Alpha")
        self.assertEqual(self.project_b.nama, "Project Beta")

    def test_mass_edit_rejects_foreign_project_without_partial_update(self):
        response = self._post(
            [
                {"id": self.project_a.pk, "nama": "Tidak Boleh Tersimpan"},
                {"id": self.other_project.pk, "nama": "Percobaan Akses"},
            ]
        )

        self.assertEqual(response.status_code, 403, response.content)
        self.project_a.refresh_from_db()
        self.other_project.refresh_from_db()
        self.assertEqual(self.project_a.nama, "Project Alpha")
        self.assertEqual(self.other_project.nama, "Project Milik User Lain")

    def test_mass_edit_returns_field_errors_for_invalid_budget(self):
        response = self._post(
            [{"id": self.project_a.pk, "anggaran_owner": "bukan angka"}]
        )

        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertIn(
            "anggaran_owner",
            body["errors"][str(self.project_a.pk)],
        )
        self.project_a.refresh_from_db()
        self.assertEqual(self.project_a.anggaran_owner, Decimal("1000000"))


class MassEditFrontendGuardTests(TestCase):
    def test_frontend_limits_editor_to_selected_projects(self):
        source = (
            "dashboard/static/dashboard/js/mass-edit-toggle.js"
        )
        with open(source, encoding="utf-8") as handle:
            script = handle.read()

        self.assertIn("selectedProjectIds = new Set(", script)
        self.assertIn("if (!projectId || !selectedProjectIds.has(projectId)) return;", script)
        self.assertIn("const DEFAULT_FIELD_NAMES = [", script)
        self.assertIn("draftValues.has(key)", script)

    def test_frontend_preserves_empty_optional_values_in_payload(self):
        source = (
            "dashboard/static/dashboard/js/mass-edit-toggle.js"
        )
        with open(source, encoding="utf-8") as handle:
            script = handle.read()

        self.assertNotIn(
            "if (value || field.required)",
            script,
        )
        self.assertIn("projectData[field.name] = draftValues.has(key)", script)
        self.assertIn("const MULTILINE_FIELD_NAMES = new Set([", script)
        self.assertIn("function autoSizeMultiline(input)", script)

    def test_mass_edit_dropdown_and_sticky_project_column_have_layer_guards(self):
        source = "dashboard/static/dashboard/css/dashboard.css"
        with open(source, encoding="utf-8") as handle:
            styles = handle.read()

        self.assertIn(
            "#massEditActionBar .dropdown-menu.mass-edit-column-menu",
            styles,
        )
        self.assertIn(
            "z-index: var(--dp-z-dropdown, 12040) !important;",
            styles,
        )
        self.assertIn(
            ".dashboard-table-wrapper .mass-edit-mode thead th.mass-edit-project-name",
            styles,
        )
        self.assertIn(
            "z-index: calc(var(--dp-z-thead, 12030) + 1) !important;",
            styles,
        )
        self.assertIn(
            ".mass-edit-mode td[data-field]:focus-within",
            styles,
        )
        self.assertIn(
            "min-width: clamp(280px, 38vw, 560px);",
            styles,
        )
