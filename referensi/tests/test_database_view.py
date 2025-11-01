from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from referensi.models import AHSPReferensi, RincianReferensi


class AHSPDatabaseViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="pass", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@example.com", password="pass"
        )

    def _create_job(self, **kwargs):
        defaults = {
            "kode_ahsp": "01.01",
            "nama_ahsp": "Pekerjaan Tanah",
            "klasifikasi": "Sipil",
            "sub_klasifikasi": "Galian",
            "satuan": "LS",
            "sumber": "SNI 2025",
        }
        defaults.update(kwargs)
        return AHSPReferensi.objects.create(**defaults)

    def test_requires_privileged_user(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("referensi:ahsp_database"))
        self.assertEqual(response.status_code, 403)

    def test_renders_jobs_with_summary(self):
        job = self._create_job()
        RincianReferensi.objects.create(
            ahsp=job,
            kategori=RincianReferensi.Kategori.TK,
            kode_item="T-001",
            uraian_item="Mandor",
            satuan_item="OH",
            koefisien=Decimal("1"),
        )
        RincianReferensi.objects.create(
            ahsp=job,
            kategori=RincianReferensi.Kategori.BHN,
            kode_item="B-001",
            uraian_item="Semen",
            satuan_item="Zak",
            koefisien=Decimal("2"),
        )

        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("referensi:ahsp_database"))

        self.assertEqual(response.status_code, 200)
        jobs = response.context["jobs"]
        self.assertEqual(len(jobs), 1)
        first_row = jobs[0]
        self.assertFalse(first_row["has_anomaly"])
        self.assertEqual(first_row["category_counts"]["TK"], 1)
        self.assertEqual(first_row["category_counts"]["BHN"], 1)
        summary = response.context["summary"]
        self.assertEqual(summary["total_filtered"], 1)
        self.assertEqual(summary["anomaly_displayed"], 0)

    def test_anomaly_filter_returns_only_problematic_jobs(self):
        healthy = self._create_job(kode_ahsp="02.01", nama_ahsp="Normal Job")
        RincianReferensi.objects.create(
            ahsp=healthy,
            kategori=RincianReferensi.Kategori.TK,
            kode_item="T-100",
            uraian_item="Pekerja",
            satuan_item="OH",
            koefisien=Decimal("1"),
        )

        problematic = self._create_job(
            kode_ahsp="03.01",
            nama_ahsp="Anomali",
            satuan="",
        )
        RincianReferensi.objects.create(
            ahsp=problematic,
            kategori=RincianReferensi.Kategori.BHN,
            kode_item="B-200",
            uraian_item="Bahan",
            satuan_item="",
            koefisien=Decimal("0"),
        )

        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("referensi:ahsp_database"), {"anomali": "1"})

        jobs = response.context["jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0]["has_anomaly"])
        self.assertEqual(jobs[0]["object"].kode_ahsp, "03.01")
