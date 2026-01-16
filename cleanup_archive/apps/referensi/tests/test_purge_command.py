from decimal import Decimal
import os

import pytest

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from dashboard.models import Project
from detail_project.models import (
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from referensi.models import AHSPReferensi, RincianReferensi


pytestmark = pytest.mark.skipif(
    os.getenv("DJANGO_DB_ENGINE", "postgres").lower() != "sqlite",
    reason="Set DJANGO_DB_ENGINE=sqlite to run purge command tests without PostgreSQL.",
)


SQLITE_SETTINGS = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


@override_settings(DATABASES=SQLITE_SETTINGS)
class PurgeAHSPReferensiCommandTests(TestCase):
    databases = {"default"}

    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass1234",
        )

        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Uji",
            tahun_project=2025,
            sumber_dana="APBD",
            lokasi_project="Jakarta",
            nama_client="Pemda",
            anggaran_owner=Decimal("1000000"),
        )

        self.klas = Klasifikasi.objects.create(project=self.project, name="Sipil")
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=self.klas, name="Galian")

        self.job_ref = AHSPReferensi.objects.create(
            kode_ahsp="01.01",
            nama_ahsp="Pekerjaan Tanah",
            klasifikasi="Sipil",
            sub_klasifikasi="Galian",
            satuan="LS",
            sumber="SNI 2025",
        )

        self.project_job = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_REF,
            ref=self.job_ref,
            snapshot_kode="01.01",
            snapshot_uraian="Pekerjaan Tanah",
            snapshot_satuan="LS",
        )

        self.harga = HargaItemProject.objects.create(
            project=self.project,
            kode_item="TK-001",
            uraian="Mandor",
            satuan="OH",
            kategori=HargaItemProject.KATEGORI_LAIN,
            harga_satuan=Decimal("100000"),
        )

        RincianReferensi.objects.create(
            ahsp=self.job_ref,
            kategori=RincianReferensi.Kategori.TK,
            kode_item="TK-001",
            uraian_item="Mandor",
            satuan_item="OH",
            koefisien=Decimal("1"),
        )

        DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.project_job,
            harga_item=self.harga,
            kategori=HargaItemProject.KATEGORI_LAIN,
            kode="TK-001",
            uraian="Mandor",
            satuan="OH",
            koefisien=Decimal("1"),
            ref_ahsp=self.job_ref,
        )

    def test_purge_command_detaches_and_deletes(self):
        call_command("purge_ahsp_referensi", "--noinput")

        self.assertEqual(AHSPReferensi.objects.count(), 0)
        self.assertEqual(RincianReferensi.objects.count(), 0)
        self.assertFalse(
            DetailAHSPProject.objects.filter(ref_ahsp__isnull=False).exists()
        )

        detail = DetailAHSPProject.objects.get()
        self.assertIsNone(detail.ref_ahsp)
