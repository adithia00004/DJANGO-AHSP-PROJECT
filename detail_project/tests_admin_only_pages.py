from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from dashboard.models import Project
from detail_project.models import DetailAHSPAudit, Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.services import cleanup_orphaned_items, log_audit

TEST_MIDDLEWARE = [
    m for m in settings.MIDDLEWARE if m != "config.middleware.timeout.TimeoutMiddleware"
]

@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RetiredUtilityPagesTests(TestCase):
    """
    Fase 3 cleanup: Orphan Cleanup UI and Audit Trail reader UI/API are no
    longer product surfaces. Backend orphan housekeeping and audit writer stay.
    """

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="utility_cleanup_owner",
            email="utility-cleanup-owner@example.com",
            password="Secret123!",
            is_staff=True,
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Utility Cleanup Project",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Utility",
            anggaran_owner=1000,
        )
        self.klasifikasi = Klasifikasi.objects.create(project=self.project, name="Klasifikasi")
        self.sub_klasifikasi = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=self.klasifikasi,
            name="Sub",
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-UTIL",
            snapshot_uraian="Utility cleanup audit smoke",
        )

    def test_orphan_and_audit_reader_routes_are_removed(self):
        for route_name in ("orphan_cleanup", "audit_trail", "api_get_audit_trail"):
            with self.subTest(route_name=route_name):
                with self.assertRaises(NoReverseMatch):
                    reverse(
                        f"detail_project:{route_name}",
                        kwargs={"project_id": self.project.id},
                    )

    def test_sidebar_has_no_retired_utility_links_even_for_staff(self):
        self.client.force_login(
            self.owner, backend="django.contrib.auth.backends.ModelBackend"
        )
        response = self.client.get(
            reverse("detail_project:list_pekerjaan", kwargs={"project_id": self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("orphan-cleanup/", content)
        self.assertNotIn("audit-trail/", content)

    def test_orphan_housekeeping_service_is_retained(self):
        result = cleanup_orphaned_items(self.project, dry_run=True)
        self.assertIn("deleted_count", result)
        self.assertIn("candidate_count", result)

    def test_audit_writer_is_retained(self):
        log_audit(
            self.project,
            self.pekerjaan,
            action=DetailAHSPAudit.ACTION_UPDATE,
            triggered_by="system",
            change_summary="Retained writer smoke test",
        )
        self.assertEqual(
            DetailAHSPAudit.objects.filter(
                project=self.project,
                change_summary="Retained writer smoke test",
            ).count(),
            1,
        )
