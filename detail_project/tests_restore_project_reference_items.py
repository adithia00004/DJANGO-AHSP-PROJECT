from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dashboard.models import Project
from detail_project.models import (
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from referensi.models import AHSPReferensi, KodeItemReferensi, RincianReferensi


class RestoreProjectReferenceItemsTests(TestCase):
    def test_restore_uses_parent_semantics_and_preserves_existing_price(self):
        owner = get_user_model().objects.create_user(
            username="restore_parent",
            password="Secret123!",
        )
        project = Project.objects.create(
            owner=owner,
            nama="Restore Parent",
            sumber_dana="APBN",
            lokasi_project="Makassar",
            nama_client="Client",
            anggaran_owner=1000,
        )
        classification = Klasifikasi.objects.create(
            project=project,
            name="K",
            ordering_index=1,
        )
        sub = SubKlasifikasi.objects.create(
            project=project,
            klasifikasi=classification,
            name="S",
            ordering_index=1,
        )
        parent = AHSPReferensi.objects.create(
            kode_ahsp="1.1.1.1",
            nama_ahsp="Pipa",
            satuan="m",
            sumber="AHSP TEST",
        )
        RincianReferensi.objects.create(
            ahsp=parent,
            kategori="TK",
            kode_item="L.02",
            uraian_item="Tukang Pipa",
            satuan_item="OH",
            koefisien=Decimal("0.5"),
        )
        KodeItemReferensi.objects.create(
            kategori="TK",
            kode_item="TK-0045",
            uraian_item="Tukang Pipa",
            satuan_item="OH",
        )
        job = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_REF_MOD,
            ref=parent,
            snapshot_kode="mod.1-1.1.1.1",
            snapshot_uraian="Pipa proyek",
            snapshot_satuan="m",
            ordering_index=1,
        )
        wrong = HargaItemProject.objects.create(
            project=project,
            kode_item="TK-0003",
            kategori="TK",
            uraian="Tukang Kayu",
            satuan="OH",
            harga_satuan=Decimal("100"),
        )
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job,
            harga_item=wrong,
            kategori="TK",
            kode=wrong.kode_item,
            uraian=wrong.uraian,
            satuan=wrong.satuan,
            koefisien=Decimal("0.5"),
        )

        call_command(
            "restore_project_reference_items",
            project_id=project.id,
            apply=True,
            stdout=StringIO(),
        )

        restored = DetailAHSPProject.objects.get(pekerjaan=job)
        self.assertEqual(restored.kode, "TK-0045")
        self.assertEqual(restored.uraian, "Tukang Pipa")
        self.assertEqual(restored.pekerjaan.snapshot_uraian, "Pipa proyek")
