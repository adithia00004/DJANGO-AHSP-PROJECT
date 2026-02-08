import json
import re
from pathlib import Path
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.views_api import api_project_pricing
from detail_project.views_api_tahapan_v2 import api_reset_progress
from detail_project.views_export import api_start_export_async, export_init


@override_settings(SECURE_SSL_REDIRECT=False)
class PerPageSecurityAuditTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_page_audit",
            email="owner-page-audit@example.com",
            password="Secret123!",
        )
        self.non_owner = user_model.objects.create_user(
            username="non_owner_page_audit",
            email="non-owner-page-audit@example.com",
            password="Secret123!",
        )

        # Ensure export decorators do not short-circuit before ownership checks.
        for user in (self.owner, self.non_owner):
            user.subscription_status = user.SubscriptionStatus.PRO
            user.subscription_end_date = timezone.now() + timedelta(days=30)
            user.save(update_fields=["subscription_status", "subscription_end_date"])

        self.project = Project.objects.create(
            owner=self.owner,
            nama="Security Audit Project",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Security",
            anggaran_owner=1000,
        )

    def test_f1_non_owner_blocked_from_owner_pages(self):
        self.client.force_login(self.non_owner)

        protected_pages = [
            reverse("dashboard:project_detail", args=[self.project.id]),
            reverse("detail_project:list_pekerjaan", args=[self.project.id]),
            reverse("detail_project:volume_pekerjaan", args=[self.project.id]),
            reverse("detail_project:template_ahsp", args=[self.project.id]),
            reverse("detail_project:harga_items", args=[self.project.id]),
            reverse("detail_project:rincian_ahsp", args=[self.project.id]),
            reverse("detail_project:rekap_rab", args=[self.project.id]),
            reverse("detail_project:rekap_kebutuhan", args=[self.project.id]),
            reverse("detail_project:jadwal_pekerjaan", args=[self.project.id]),
            reverse("detail_project:rincian_rab", args=[self.project.id]),
        ]

        for url in protected_pages:
            with self.subTest(url=url):
                response = self.client.get(url, secure=True)
                self.assertIn(response.status_code, (302, 403, 404))
                if response.status_code != 302:
                    self.assertNotIn(b"Traceback", response.content)

    def test_f2_owner_navigation_dashboard_to_detail_pages(self):
        self.client.force_login(self.owner)
        owner_pages = [
            reverse("dashboard:project_detail", args=[self.project.id]),
            reverse("detail_project:list_pekerjaan", args=[self.project.id]),
            reverse("detail_project:template_ahsp", args=[self.project.id]),
            reverse("detail_project:rekap_rab", args=[self.project.id]),
        ]
        for url in owner_pages:
            with self.subTest(url=url):
                response = self.client.get(url, secure=True)
                self.assertIn(response.status_code, (200, 302))

    def test_f3_owner_edit_in_detail_project_persists(self):
        update_request = self.factory.post(
            reverse("detail_project:api_project_pricing", args=[self.project.id]),
            data=json.dumps({"markup_percent": 15.25}),
            content_type="application/json",
        )
        update_request.user = self.owner
        update_response = api_project_pricing(update_request, self.project.id)
        self.assertEqual(update_response.status_code, 200)

        read_request = self.factory.get(
            reverse("detail_project:api_project_pricing", args=[self.project.id])
        )
        read_request.user = self.owner
        read_response = api_project_pricing(read_request, self.project.id)
        self.assertEqual(read_response.status_code, 200)
        payload = json.loads(read_response.content.decode("utf-8"))
        self.assertEqual(payload.get("markup_percent"), "15.25")

        self.client.force_login(self.owner)
        dashboard_response = self.client.get(reverse("dashboard:dashboard"), secure=True)
        self.assertIn(dashboard_response.status_code, (200, 302))

    def test_f4_non_owner_blocked_from_async_export_start(self):
        request = self.factory.post(
            reverse("detail_project:api_start_export_async", args=[self.project.id]),
            data=json.dumps(
                {
                    "export_type": "rekap-rab",
                    "format": "pdf",
                    "options": {},
                }
            ),
            content_type="application/json",
        )
        request.user = self.non_owner
        response = api_start_export_async(request, self.project.id)
        self.assertEqual(response.status_code, 404)

    def test_export_init_rejects_foreign_metadata_project(self):
        request = self.factory.post(
            reverse("detail_project:export_init"),
            data=json.dumps(
                {
                    "reportType": "rekap",
                    "format": "pdf",
                    "estimatedPages": 1,
                    "projectName": "Owner Project",
                    "metadata": {"projectId": self.project.id},
                }
            ),
            content_type="application/json",
        )
        request.user = self.non_owner
        response = export_init(request)
        self.assertEqual(response.status_code, 404)

    def test_v2_reset_progress_blocks_non_owner(self):
        request = self.factory.post(
            reverse("detail_project:api_v2_reset_progress", args=[self.project.id]),
            data=json.dumps({"mode": "planned"}),
            content_type="application/json",
        )
        request.user = self.non_owner
        response = api_reset_progress(request, self.project.id)
        self.assertEqual(response.status_code, 404)

    def test_client_flow_still_blocks_non_owner_even_with_redirect_middleware(self):
        self.client.force_login(self.non_owner)
        url = reverse("detail_project:api_start_export_async", args=[self.project.id])
        payload = {
            "export_type": "rekap-rab",
            "format": "pdf",
            "options": {},
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            secure=True,
        )
        self.assertIn(response.status_code, (302, 403, 404))

    def test_no_raw_project_lookup_left_in_http_views(self):
        repo_root = Path(__file__).resolve().parent.parent
        detail_project_dir = Path(__file__).resolve().parent
        files_to_scan = [
            detail_project_dir / "views.py",
            detail_project_dir / "views_api.py",
            detail_project_dir / "views_api_tahapan.py",
            detail_project_dir / "views_api_tahapan_v2.py",
            detail_project_dir / "views_export.py",
            repo_root / "dashboard" / "views.py",
            repo_root / "dashboard" / "views_export.py",
        ]

        raw_get_object_pattern = re.compile(r"get_object_or_404\(Project,\s*id=project_id\)")
        raw_get_pattern = re.compile(r"Project\.objects\.get\(id=project_id\)")

        offenders = []
        for file_path in files_to_scan:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines, start=1):
                if raw_get_object_pattern.search(line):
                    # Allowed only in helper _owner_or_404 inside views_api_tahapan.py.
                    context = "\n".join(lines[max(0, idx - 5):idx])
                    if not (file_path.name == "views_api_tahapan.py" and "def _owner_or_404" in context):
                        offenders.append(f"{file_path.name}:{idx}:{line.strip()}")
                if raw_get_pattern.search(line):
                    offenders.append(f"{file_path.name}:{idx}:{line.strip()}")

        self.assertEqual(offenders, [], msg="Raw project lookup without owner check found:\n" + "\n".join(offenders))
