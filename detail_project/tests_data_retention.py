from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from detail_project.models import DetailAHSPAudit, Klasifikasi, Pekerjaan, SubKlasifikasi


class DetailAuditRetentionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="audit_owner",
            email="audit_owner@example.com",
            password="StrongPass123!",
        )
        self.project = Project.objects.create(owner=self.owner, nama="Audit Retention Project")
        self.klasifikasi = Klasifikasi.objects.create(project=self.project, name="Klasifikasi A")
        self.sub_klasifikasi = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=self.klasifikasi,
            name="Sub A",
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001",
            snapshot_uraian="Pekerjaan Uji Retensi",
        )

    def test_detail_audit_persists_when_pekerjaan_deleted(self):
        audit = DetailAHSPAudit.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            action=DetailAHSPAudit.ACTION_CREATE,
            triggered_by="user",
        )

        self.pekerjaan.delete()
        audit.refresh_from_db()

        self.assertIsNone(audit.pekerjaan_id)
        self.assertEqual(DetailAHSPAudit.objects.count(), 1)
