from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dashboard.models import Project
from detail_project.models import HargaItemProject
from referensi.models import KodeItemReferensi


class RepairProjectItemCodesTests(TestCase):
    def test_dry_run_then_apply_preserves_price(self):
        owner = get_user_model().objects.create_user(
            username="repair_project_codes",
            email="repair-project-codes@example.com",
            password="Secret123!",
        )
        project = Project.objects.create(
            owner=owner,
            nama="Repair Codes",
            sumber_dana="APBN",
            lokasi_project="Makassar",
            nama_client="Client",
            anggaran_owner=1000,
        )
        item = HargaItemProject.objects.create(
            project=project,
            kode_item="AUTO-OLD",
            kategori="ALT",
            uraian="Gergaji",
            satuan="hari",
            harga_satuan="2500.00",
        )
        KodeItemReferensi.objects.create(
            kategori="ALT",
            uraian_item="Gergaji",
            satuan_item="hari",
            kode_item="PR-0042",
        )

        call_command(
            "repair_project_item_codes",
            project_id=project.id,
            stdout=StringIO(),
        )
        item.refresh_from_db()
        self.assertEqual(item.kode_item, "AUTO-OLD")

        call_command(
            "repair_project_item_codes",
            project_id=project.id,
            apply=True,
            stdout=StringIO(),
        )
        item.refresh_from_db()
        self.assertEqual(item.kode_item, "PR-0042")
        self.assertEqual(str(item.harga_satuan), "2500.00")
