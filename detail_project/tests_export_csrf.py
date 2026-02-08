import json

from django.contrib.auth import get_user_model
from django.middleware.csrf import CsrfViewMiddleware, _get_new_csrf_string
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.views_export import export_init


class ExportInitCsrfTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="csrf_superuser",
            email="csrf-superuser@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Project CSRF",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client CSRF",
            anggaran_owner=1000,
        )
        self.middleware = CsrfViewMiddleware(lambda request: None)
        self.payload = json.dumps({
            "reportType": "rekap",
            "format": "pdf",
            "estimatedPages": 1,
            "projectName": "CSRF Test",
            "metadata": {"projectId": self.project.id},
        })

    def test_export_init_rejects_missing_csrf_token(self):
        request = self.factory.post(
            "/detail_project/api/export/init",
            data=self.payload,
            content_type="application/json",
        )
        request.user = self.user

        csrf_response = self.middleware.process_view(request, export_init, (), {})

        self.assertIsNotNone(csrf_response)
        self.assertEqual(csrf_response.status_code, 403)

    def test_export_init_accepts_valid_csrf_token(self):
        token = _get_new_csrf_string()
        request = self.factory.post(
            "/detail_project/api/export/init",
            data=self.payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        request.user = self.user
        request.COOKIES["csrftoken"] = token
        request.META["CSRF_COOKIE"] = token

        csrf_response = self.middleware.process_view(request, export_init, (), {})
        self.assertIsNone(csrf_response)

        response = export_init(request)
        self.assertEqual(response.status_code, 201)
