import json
import os
import shutil
import sys
import tempfile
from datetime import timedelta
from types import ModuleType
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from dashboard.models import Project
from dashboard.views_export import export_csv, export_dashboard_xlsx, export_project_pdf
from detail_project.models_export import ExportSession
from detail_project.views_api import (
    api_export_rincian_rab_csv,
    export_jadwal_pekerjaan_professional,
    export_project_full_json,
    export_rekap_rab_pdf,
    export_rekap_rab_xlsx,
)
from detail_project.views_export import api_export_download_async, export_download


class ExportAccessControlTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()

        self.trial_user = user_model.objects.create_user(
            username="trial_export_user",
            email="trial-export@example.com",
            password="Secret123!",
        )
        self.trial_user.trial_end_date = timezone.now() + timedelta(days=7)
        self.trial_user.subscription_status = self.trial_user.SubscriptionStatus.TRIAL
        self.trial_user.save(update_fields=["trial_end_date", "subscription_status"])

        self.expired_user = user_model.objects.create_user(
            username="expired_export_user",
            email="expired-export@example.com",
            password="Secret123!",
        )
        self.expired_user.subscription_status = self.expired_user.SubscriptionStatus.EXPIRED
        self.expired_user.trial_end_date = timezone.now() - timedelta(days=1)
        self.expired_user.subscription_end_date = timezone.now() - timedelta(days=1)
        self.expired_user.save(
            update_fields=["subscription_status", "trial_end_date", "subscription_end_date"]
        )

        self.temp_media_root = tempfile.mkdtemp(prefix="export-tests-")
        self.trial_project = Project.objects.create(
            owner=self.trial_user,
            nama="Trial Project",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Trial",
            anggaran_owner=1000,
        )
        self.expired_project = Project.objects.create(
            owner=self.expired_user,
            nama="Expired Project",
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client Expired",
            anggaran_owner=2000,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def _create_completed_session(self, user, format_type):
        session = ExportSession.objects.create(
            user=user,
            report_type=ExportSession.REPORT_REKAP,
            format_type=format_type,
            estimated_pages=1,
            project_name="Project Test",
            metadata={},
        )
        ext_by_format = {
            ExportSession.FORMAT_PDF: "pdf",
            ExportSession.FORMAT_WORD: "docx",
            ExportSession.FORMAT_XLSX: "xlsx",
        }
        extension = ext_by_format.get(format_type, "bin")
        session.output_file.save(
            f"sample.{extension}",
            ContentFile(b"test-export-content"),
            save=False,
        )
        session.status = ExportSession.STATUS_COMPLETED
        session.file_size = session.output_file.size
        session.save(update_fields=["output_file", "status", "file_size", "updated_at"])
        return session

    def _override_media(self):
        return override_settings(MEDIA_ROOT=self.temp_media_root)

    def test_export_download_blocks_trial_user_for_pdf(self):
        with self._override_media():
            session = self._create_completed_session(self.trial_user, ExportSession.FORMAT_PDF)
            request = self.factory.get("/api/export/download/")
            request.user = self.trial_user
            response = export_download(request, session.export_id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "TRIAL_NO_EXPORT")

    def test_export_download_blocks_expired_user_for_word(self):
        with self._override_media():
            session = self._create_completed_session(self.expired_user, ExportSession.FORMAT_WORD)
            request = self.factory.get("/api/export/download/")
            request.user = self.expired_user
            response = export_download(request, session.export_id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_export_download_allows_expired_user_for_pdf(self):
        with self._override_media():
            session = self._create_completed_session(self.expired_user, ExportSession.FORMAT_PDF)
            request = self.factory.get("/api/export/download/")
            request.user = self.expired_user
            response = export_download(request, session.export_id)

        self.assertEqual(response.status_code, 200)
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_legacy_views_api_xlsx_blocks_trial_user(self):
        request = self.factory.get("/api/project/export/rekap-rab/xlsx/")
        request.user = self.trial_user
        response = export_rekap_rab_xlsx(request, self.trial_project.id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_legacy_views_api_json_blocks_expired_user(self):
        request = self.factory.get("/api/project/export/project-full/json/")
        request.user = self.expired_user
        response = export_project_full_json(request, self.expired_project.id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_legacy_views_api_pdf_blocks_trial_user(self):
        request = self.factory.get("/api/project/export/rekap-rab/pdf/")
        request.user = self.trial_user
        response = export_rekap_rab_pdf(request, self.trial_project.id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "TRIAL_NO_EXPORT")

    def test_professional_export_word_blocks_expired_user(self):
        request = self.factory.get("/api/project/export/jadwal-professional/?format=word")
        request.user = self.expired_user
        response = export_jadwal_pekerjaan_professional(request, self.expired_project.id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_dashboard_xlsx_blocks_trial_user(self):
        request = self.factory.get("/dashboard/export/xlsx/")
        request.user = self.trial_user
        response = export_dashboard_xlsx(request)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_dashboard_csv_blocks_expired_user(self):
        request = self.factory.get("/dashboard/export/csv/")
        request.user = self.expired_user
        response = export_csv(request)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_dashboard_pdf_blocks_trial_user(self):
        request = self.factory.get("/dashboard/project/1/export-pdf/")
        request.user = self.trial_user
        response = export_project_pdf(request, self.trial_project.id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "TRIAL_NO_EXPORT")

    def test_legacy_views_api_rincian_rab_csv_blocks_trial_user(self):
        request = self.factory.get("/api/project/rincian-rab/export.csv")
        request.user = self.trial_user
        response = api_export_rincian_rab_csv(request, self.trial_project.id)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_api_export_download_async_blocks_expired_user_for_word(self):
        async_file = os.path.join(self.temp_media_root, "async-export.docx")
        with open(async_file, "wb") as fp:
            fp.write(b"docx-content")

        mock_task = Mock()
        mock_task.state = "SUCCESS"
        mock_task.result = {
            "file_path": async_file,
            "format": "word",
            "export_type": "rekap-rab",
        }

        celery_module = ModuleType("celery")
        celery_result_module = ModuleType("celery.result")
        celery_result_module.AsyncResult = lambda _task_id: mock_task
        celery_module.result = celery_result_module

        with patch.dict(
            sys.modules,
            {"celery": celery_module, "celery.result": celery_result_module},
        ):
            request = self.factory.get("/api/export-download/async/task-word-1/")
            request.user = self.expired_user
            response = api_export_download_async(request, "task-word-1")

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "PRO_REQUIRED")

    def test_api_export_download_async_allows_expired_user_for_pdf(self):
        async_file = os.path.join(self.temp_media_root, "async-export.pdf")
        with open(async_file, "wb") as fp:
            fp.write(b"pdf-content")

        mock_task = Mock()
        mock_task.state = "SUCCESS"
        mock_task.result = {
            "file_path": async_file,
            "format": "pdf",
            "export_type": "rekap-rab",
        }

        celery_module = ModuleType("celery")
        celery_result_module = ModuleType("celery.result")
        celery_result_module.AsyncResult = lambda _task_id: mock_task
        celery_module.result = celery_result_module

        with patch.dict(
            sys.modules,
            {"celery": celery_module, "celery.result": celery_result_module},
        ):
            request = self.factory.get("/api/export-download/async/task-pdf-1/")
            request.user = self.expired_user
            response = api_export_download_async(request, "task-pdf-1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(".pdf", response["Content-Disposition"])
