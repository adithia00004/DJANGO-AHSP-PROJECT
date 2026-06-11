import json
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.views_api import export_list_pekerjaan_json


class ListPekerjaanExportTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="list-export-owner",
            password="Secret123!",
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.other_user = user_model.objects.create_user(
            username="list-export-other",
            password="Secret123!",
            is_staff=True,
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama='Project "Export" / Utama',
            sumber_dana="APBN",
            lokasi_project="Makassar",
            nama_client="Client",
            anggaran_owner=1000,
        )
        klasifikasi = Klasifikasi.objects.create(
            project=self.project,
            name="Pekerjaan Persiapan",
            ordering_index=0,
        )
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klasifikasi,
            name="Pembersihan",
            ordering_index=0,
        )
        Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="A.1",
            snapshot_uraian="Pembersihan lokasi",
            snapshot_satuan="m2",
            ordering_index=0,
            budgeted_cost="125000.50",
        )
        self.url = reverse(
            "detail_project:export_list_pekerjaan_json",
            args=[self.project.id],
        )

    def test_owner_downloads_complete_json_with_safe_headers(self):
        request = self.factory.get(
            self.url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = self.owner

        response = export_list_pekerjaan_json(request, self.project.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertRegex(
            response["Content-Disposition"],
            r'attachment; filename="list_pekerjaan_project-export-utama_\d{8}_\d{6}\.json"',
        )

        payload = json.loads(response.content)
        self.assertEqual(payload["export_type"], "list_pekerjaan")
        self.assertEqual(payload["stats"], {
            "total_klasifikasi": 1,
            "total_sub": 1,
            "total_pekerjaan": 1,
        })
        pekerjaan = payload["klasifikasi"][0]["sub"][0]["pekerjaan"][0]
        self.assertEqual(pekerjaan["snapshot_kode"], "A.1")
        self.assertEqual(pekerjaan["budgeted_cost"], "125000.50")

    def test_non_owner_receives_404_instead_of_internal_error(self):
        request = self.factory.get(self.url)
        request.user = self.other_user

        with self.assertRaises(Http404):
            export_list_pekerjaan_json(request, self.project.id)

    def test_frontend_uses_fetch_export_without_navigation(self):
        template = Path(
            "detail_project/templates/detail_project/list_pekerjaan.html"
        ).read_text(encoding="utf-8")
        script = Path(
            "detail_project/static/detail_project/js/list_pekerjaan.js"
        ).read_text(encoding="utf-8")

        self.assertIn('id="btn-export-json"', template)
        self.assertIn("new window.ExportManager", script)
        self.assertIn("modalId: null", script)
        self.assertIn("await handleSave()", script)
        self.assertIn("await exporter.exportAs('json'", script)
