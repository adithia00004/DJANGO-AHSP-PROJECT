import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import ProjectParameter
from detail_project.views_api import api_project_parameters_sync


class Phase4NegativeParameterTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="phase4_negative_param_user",
            email="phase4-negative-param@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Phase 4 Negative Param",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()

    def test_model_allows_negative_value(self):
        obj = ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="-12.5",
            label="Diskon",
        )
        obj.refresh_from_db()
        # ProjectParameter.value kini 12dp (expand precision koef/param, migrasi 0043/0044).
        self.assertEqual(str(obj.value), "-12.500000000000")

    def test_sync_endpoint_accepts_negative_value(self):
        payload = {
            "parameters": {
                "bp_1": {"value": -7.25, "label": "Diskon"},
            },
            "mode": "replace",
        }

        request = self.factory.post(
            "/api/project/parameters/sync/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.user
        response = api_project_parameters_sync(request, self.project.id)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

        row = ProjectParameter.objects.get(project=self.project, name="bp_1")
        # value 12dp setelah expand precision koef/param.
        self.assertEqual(str(row.value), "-7.250000000000")
