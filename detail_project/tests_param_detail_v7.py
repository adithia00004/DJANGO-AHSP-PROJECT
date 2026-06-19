"""V7: PUT /parameters/<id>/ must reject an unparseable value (400), not skip it
silently while returning ok:true (the user would think it was saved)."""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import ProjectParameter
from detail_project.views_api import api_project_parameter_detail


class ParamDetailPutValidationV7Tests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="param_v7_user",
            email="param-v7@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Param V7",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )
        self.param = ProjectParameter.objects.create(
            project=self.project, name="bp_1", value="10", label="Panjang",
        )
        self.factory = RequestFactory()

    def _put(self, body):
        request = self.factory.put(
            f"/api/project/{self.project.id}/parameters/{self.param.id}/",
            data=json.dumps(body),
            content_type="application/json",
        )
        request.user = self.user
        return api_project_parameter_detail(request, self.project.id, self.param.id)

    def test_invalid_value_is_rejected_with_400_and_not_saved(self):
        resp = self._put({"value": "abc"})
        self.assertEqual(resp.status_code, 400, resp.content.decode("utf-8"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.param.refresh_from_db()
        self.assertEqual(self.param.value, Decimal("10"))  # unchanged

    def test_valid_value_updates(self):
        resp = self._put({"value": "42.5"})
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        self.param.refresh_from_db()
        self.assertEqual(self.param.value, Decimal("42.5"))

    def test_label_only_update_leaves_value_untouched(self):
        resp = self._put({"label": "Lebar"})
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        self.param.refresh_from_db()
        self.assertEqual(self.param.label, "Lebar")
        self.assertEqual(self.param.value, Decimal("10"))
