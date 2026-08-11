"""Badge total RAB di halaman Volume, Harga Items, dan Template AHSP.

Angka yang ditampilkan adalah nilai pembulatan (sudah termasuk PPN). Sampai
sebelum fitur ini, angka itu hanya hidup di browser pada footer Rekap RAB
(`rekap_rab.js`), sehingga satu-satunya cara menampilkannya di halaman lain
adalah menyalin rumusnya. Tes di bawah mengunci rumus versi server supaya
salinan itu tidak pernah dibutuhkan -- dan supaya badge tidak pernah berbeda
dari halaman Rekap RAB, karena pengguna membandingkan keduanya.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import ProjectPricing
from detail_project.services import compute_rab_grand_total

User = get_user_model()

ROWS = [{"total": 1000000.0}, {"total": 234567.55}]  # subtotal 1.234.567,55


def _make_user(username):
    return User.objects.create_user(
        username=username,
        password="StrongPass123!@#",
        subscription_status=User.SubscriptionStatus.PRO,
        subscription_end_date=timezone.now() + timezone.timedelta(days=30),
    )


class RabGrandTotalCalculationTests(TestCase):
    def setUp(self):
        self.owner = _make_user("rab_owner")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Total RAB",
            tanggal_mulai=date(2026, 1, 1),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Klien",
            anggaran_owner=Decimal("1000000"),
        )

    def _compute(self, ppn="11.00", base=10000):
        ProjectPricing.objects.update_or_create(
            project=self.project,
            defaults={"ppn_percent": Decimal(ppn), "rounding_base": base},
        )
        with patch("detail_project.services.compute_rekap_for_project", return_value=ROWS):
            return compute_rab_grand_total(self.project)

    def test_follows_the_same_order_as_the_rekap_rab_footer(self):
        """PPN atas subtotal, baru dibulatkan -- bukan sebaliknya.

        Membulatkan lebih dulu lalu menambah PPN memberi angka berbeda, dan
        badge akan bertentangan dengan halaman Rekap RAB.
        """
        result = self._compute()

        self.assertEqual(result["subtotal"], Decimal("1234567.55"))
        self.assertEqual(result["ppn"], Decimal("1234567.55") * Decimal("11") / Decimal("100"))
        self.assertEqual(result["grand_total"], result["subtotal"] + result["ppn"])
        # 1.370.369,98... -> kelipatan 10.000 terdekat
        self.assertEqual(result["rounded_total"], Decimal("1370000"))

    def test_rounding_base_zero_does_not_divide_by_zero(self):
        """0 berarti 'jangan bulatkan'; sebelum penjagaan ini halaman ikut gagal."""
        result = self._compute(base=0)

        self.assertEqual(result["rounded_total"], result["grand_total"])

    def test_zero_ppn_leaves_the_subtotal_untouched(self):
        result = self._compute(ppn="0.00", base=0)

        self.assertEqual(result["ppn"], Decimal("0"))
        self.assertEqual(result["grand_total"], result["subtotal"])

    def test_missing_pricing_row_falls_back_to_defaults(self):
        ProjectPricing.objects.filter(project=self.project).delete()
        with patch("detail_project.services.compute_rekap_for_project", return_value=ROWS):
            result = compute_rab_grand_total(self.project)

        self.assertEqual(result["ppn_percent"], Decimal("11"))
        self.assertEqual(result["rounding_base"], 10000)


class RabTotalEndpointTests(TestCase):
    def setUp(self):
        self.owner = _make_user("rab_ep_owner")
        self.other = _make_user("rab_ep_other")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Endpoint",
            tanggal_mulai=date(2026, 1, 1),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Klien",
            anggaran_owner=Decimal("1000000"),
        )
        self.url = reverse(
            "detail_project:api_project_rab_total", kwargs={"project_id": self.project.id}
        )

    def test_owner_gets_every_field_the_badge_needs(self):
        self.client.force_login(self.owner)
        with patch("detail_project.services.compute_rekap_for_project", return_value=ROWS):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(
            set(payload),
            {"ok", "subtotal", "ppn_percent", "ppn", "grand_total", "rounding_base", "rounded_total"},
        )

    def test_non_owner_cannot_read_another_projects_total(self):
        """Nilai proyek adalah data komersial; 404 menyembunyikan keberadaannya."""
        self.client.force_login(self.other)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, {301, 302})


class RabTotalBadgeRenderTests(TestCase):
    """Nilai awal harus ikut SSR; tanpa itu badge berkedip di setiap page load."""

    def setUp(self):
        self.owner = _make_user("rab_page_owner")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Badge",
            tanggal_mulai=date(2026, 1, 1),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Klien",
            anggaran_owner=Decimal("1000000"),
        )
        self.client.force_login(self.owner)

    def _pages(self):
        return [
            reverse("detail_project:volume_pekerjaan", kwargs={"project_id": self.project.id}),
            reverse("detail_project:harga_items", kwargs={"project_id": self.project.id}),
            reverse("detail_project:template_ahsp", kwargs={"project_id": self.project.id}),
        ]

    def test_badge_is_present_on_all_three_pages(self):
        with patch("detail_project.services.compute_rekap_for_project", return_value=ROWS):
            for url in self._pages():
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, "data-rab-total-value")

    def test_page_still_renders_when_the_total_cannot_be_computed(self):
        """Badge adalah pelengkap: satu perhitungan gagal tidak boleh menjatuhkan halaman."""
        with patch(
            "detail_project.services.compute_rekap_for_project",
            side_effect=RuntimeError("boom"),
        ):
            for url in self._pages():
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, "data-rab-total-value")
