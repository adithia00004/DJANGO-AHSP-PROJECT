import json
import re

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import ProjectComputedParameter, ProjectParameter
from detail_project.views_api import (
    _build_export_data,
    _import_template_data,
    import_project_from_json,
)


class Phase0DataSafetyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="phase0_data_safety_user",
            email="phase0-data-safety@example.com",
            password="Secret123!",
        )
        self.source = Project.objects.create(
            owner=self.user,
            nama="Phase 0 Source",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()

    def _seed_source_params(self):
        ProjectParameter.objects.create(
            project=self.source,
            name="bp_10",
            value="12.5",
            label="Panjang",
            unit="m",
        )
        ProjectComputedParameter.objects.create(
            project=self.source,
            name="cp_10",
            expression="bp_10 * 2",
            label="Luas",
            unit="m2",
        )

    def test_export_full_contains_project_computed_parameters(self):
        self._seed_source_params()
        payload = _build_export_data(self.source, mode="full")

        self.assertEqual(payload.get("export_type"), "project_full_backup")
        self.assertEqual(payload.get("export_version"), "3.0")
        self.assertIn("project_computed_parameters", payload)
        self.assertEqual(len(payload["project_computed_parameters"]), 1)
        self.assertEqual(payload["project_computed_parameters"][0]["name"], "cp_10")

    def test_export_template_contains_project_computed_parameters(self):
        self._seed_source_params()
        payload = _build_export_data(self.source, mode="template")

        self.assertEqual(payload.get("export_type"), "project_template")
        self.assertEqual(payload.get("export_version"), "3.0")
        self.assertIn("project_computed_parameters", payload)
        self.assertEqual(len(payload["project_computed_parameters"]), 1)
        self.assertEqual(payload["project_computed_parameters"][0]["name"], "cp_10")

    def test_import_full_backup_imports_and_remaps_computed_parameters(self):
        self._seed_source_params()
        export_payload = _build_export_data(self.source, mode="full")

        request = self.factory.post(
            "/api/project/import/json/",
            data=json.dumps(export_payload),
            content_type="application/json",
        )
        request.user = self.user
        response = import_project_from_json(request)
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content.decode("utf-8"))
        imported_project_id = body["project_id"]
        imported_base = list(
            ProjectParameter.objects.filter(project_id=imported_project_id)
            .values_list("name", "label", "value")
        )
        imported_cp = list(
            ProjectComputedParameter.objects.filter(project_id=imported_project_id)
            .values_list("name", "label", "expression")
        )

        self.assertEqual(len(imported_base), 1)
        self.assertEqual(len(imported_cp), 1)
        self.assertRegex(imported_base[0][0], r"^bp_[1-9][0-9]*$")
        self.assertRegex(imported_cp[0][0], r"^cp_[1-9][0-9]*$")
        self.assertEqual(imported_base[0][1], "Panjang")
        self.assertEqual(imported_cp[0][1], "Luas")
        self.assertNotIn("bp_10", imported_cp[0][2].lower())
        self.assertTrue(
            re.search(r"bp_[1-9][0-9]*\s*\*\s*2", imported_cp[0][2].lower()) is not None
        )

    def test_import_template_data_imports_and_remaps_computed_parameters(self):
        self._seed_source_params()
        template_payload = _build_export_data(self.source, mode="template")
        target = Project.objects.create(
            owner=self.user,
            nama="Phase 0 Target Template",
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client B",
            anggaran_owner=2000,
        )

        stats, errors = _import_template_data(target, template_payload, user=self.user)

        self.assertEqual(errors, [])
        self.assertEqual(stats.get("parameters"), 1)
        self.assertEqual(stats.get("computed_parameters"), 1)

        imported_base = list(
            ProjectParameter.objects.filter(project=target).values_list("name", "label")
        )
        imported_cp = list(
            ProjectComputedParameter.objects.filter(project=target).values_list(
                "name",
                "label",
                "expression",
            )
        )

        self.assertEqual(len(imported_base), 1)
        self.assertEqual(len(imported_cp), 1)
        self.assertRegex(imported_base[0][0], r"^bp_[1-9][0-9]*$")
        self.assertRegex(imported_cp[0][0], r"^cp_[1-9][0-9]*$")
        self.assertEqual(imported_base[0][1], "Panjang")
        self.assertEqual(imported_cp[0][1], "Luas")
        self.assertNotIn("bp_10", imported_cp[0][2].lower())
        self.assertTrue(
            re.search(r"bp_[1-9][0-9]*\s*\*\s*2", imported_cp[0][2].lower()) is not None
        )
