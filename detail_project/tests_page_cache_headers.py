from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, TransactionTestCase
from django.urls import reverse

from config.middleware.cache_control import DetailProjectNoStoreMiddleware
from dashboard.models import Project


class DetailProjectNoStoreMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _response_for(self, path, response):
        middleware = DetailProjectNoStoreMiddleware(lambda request: response)
        return middleware(self.factory.get(path))

    def test_adds_no_store_to_detail_project_html(self):
        response = self._response_for(
            "/detail_project/1/volume-pekerjaan/",
            HttpResponse("<html></html>", content_type="text/html"),
        )

        cache_control = response.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_does_not_modify_detail_project_api_response(self):
        response = self._response_for(
            "/detail_project/api/project/1/list-pekerjaan/tree/",
            HttpResponse("<html></html>", content_type="text/html"),
        )

        self.assertNotIn("no-store", response.get("Cache-Control", ""))

    def test_does_not_modify_attachment_response(self):
        response = HttpResponse("<html></html>", content_type="text/html")
        response["Content-Disposition"] = 'attachment; filename="report.html"'

        result = self._response_for(
            "/detail_project/1/report-download/",
            response,
        )

        self.assertNotIn("no-store", result.get("Cache-Control", ""))

    def test_does_not_modify_non_html_response(self):
        response = self._response_for(
            "/detail_project/1/volume-pekerjaan/",
            JsonResponse({"ok": True}),
        )

        self.assertNotIn("no-store", response.get("Cache-Control", ""))


class DetailProjectPageCacheHeaderTests(TransactionTestCase):
    PAGE_NAMES = (
        "list_pekerjaan",
        "volume_pekerjaan",
        "template_ahsp",
        "harga_items",
        "orphan_cleanup",
        "audit_trail",
        "rincian_ahsp",
        "rekap_rab",
        "rekap_kebutuhan",
        "jadwal_pekerjaan",
        "export_test",
        "rincian_rab",
    )

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_page_cache_headers",
            email="owner-page-cache-headers@example.com",
            password="Secret123!",
            # Staff agar halaman admin-only (orphan_cleanup, audit_trail — U14)
            # tetap 200 dan header cache-nya bisa diverifikasi.
            is_staff=True,
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Cache Headers",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Cache Headers",
            anggaran_owner=1000,
        )
        self.client.force_login(
            self.owner,
            backend="django.contrib.auth.backends.ModelBackend",
        )

    def test_all_detail_project_html_pages_are_no_store(self):
        for page_name in self.PAGE_NAMES:
            with self.subTest(page_name=page_name):
                response = self.client.get(
                    reverse(
                        f"detail_project:{page_name}",
                        kwargs={"project_id": self.project.id},
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                    response.get("Location", ""),
                )
                self.assertIn("text/html", response.get("Content-Type", ""))
                self.assertIn("no-store", response.get("Cache-Control", ""))
