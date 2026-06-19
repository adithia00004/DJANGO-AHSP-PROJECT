"""V3: computed-parameter graph validation.

Server must reject expressions that reference missing base/computed parameters
or create cycles. Syntax-only validation is not enough because the client can be
bypassed.
"""
import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import ProjectComputedParameter, ProjectParameter
from detail_project.views_api import (
    api_project_computed_parameters,
    api_project_computed_parameters_sync,
)


class ComputedParameterGraphV3Tests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("v3-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="V3")
        self.factory = RequestFactory()
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="10",
            label="Panjang",
        )

    def _post_create(self, expression):
        req = self.factory.post(
            "/computed/",
            data=json.dumps({"expression": expression, "label": "Rumus"}),
            content_type="application/json",
        )
        req.user = self.owner
        return api_project_computed_parameters(req, self.project.id)

    def _post_sync(self, computed, mode="replace"):
        req = self.factory.post(
            "/computed/sync/",
            data=json.dumps({"computed_parameters": computed, "mode": mode}),
            content_type="application/json",
        )
        req.user = self.owner
        return api_project_computed_parameters_sync(req, self.project.id)

    def test_create_rejects_missing_base_reference(self):
        resp = self._post_create("bp_999 * 2")
        self.assertEqual(resp.status_code, 422, resp.content)
        body = json.loads(resp.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertIn("bp_999", json.dumps(body))
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_sync_rejects_missing_computed_reference_atomically(self):
        resp = self._post_sync({
            "cp_1": {"expression": "bp_1 + cp_99", "label": "Broken"},
        })
        self.assertEqual(resp.status_code, 422, resp.content)
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_sync_rejects_direct_cycle_atomically(self):
        resp = self._post_sync({
            "cp_1": {"expression": "cp_1 + bp_1", "label": "Loop"},
        })
        self.assertEqual(resp.status_code, 422, resp.content)
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_sync_rejects_indirect_cycle_atomically(self):
        resp = self._post_sync({
            "cp_1": {"expression": "cp_2 + bp_1", "label": "A"},
            "cp_2": {"expression": "cp_1 * 2", "label": "B"},
        })
        self.assertEqual(resp.status_code, 422, resp.content)
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_sync_accepts_existing_computed_dependency_in_merge(self):
        ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_1",
            expression="bp_1 * 2",
            label="Area",
        )
        resp = self._post_sync({
            "cp_2": {"expression": "cp_1 + bp_1", "label": "Total"},
        }, mode="merge")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(ProjectComputedParameter.objects.filter(project=self.project, name="cp_2").exists())

