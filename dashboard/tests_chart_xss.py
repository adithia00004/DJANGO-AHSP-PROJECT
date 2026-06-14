"""WP-A1 / F-01 regression: stored XSS via free-text sumber_dana in dashboard chart data.

The dashboard embeds chart data (including the free-text `sumber_dana`) into an
inline <script> block. A value containing `</script>` must NOT be able to break
out of the script context. See dashboard.views._safe_inline_json.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project


User = get_user_model()
TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != "config.middleware.timeout.TimeoutMiddleware"
]

XSS_PAYLOAD = "</script><script>alert(1)</script>"


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class DashboardChartXssTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="chart_xss_owner",
            password="StrongPass123!",
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        Project.objects.create(
            owner=self.owner,
            nama="Project XSS",
            sumber_dana=XSS_PAYLOAD,
            lokasi_project="Makassar",
            nama_client="Dinas PUPR",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 12, 31),
        )
        self.client.force_login(self.owner)

    def test_malicious_sumber_dana_is_escaped_in_chart_payload(self):
        response = self.client.get(reverse("dashboard:dashboard"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # The raw breakout sequence from the stored data must NOT appear.
        self.assertNotIn("</script><script>alert(1)", content)
        self.assertNotIn("<script>alert(1)", content)

        # The payload must be present in escaped form inside the chart JSON.
        self.assertIn("\\u003c/script\\u003e\\u003cscript\\u003ealert(1)", content)

    def test_numeric_chart_values_remain_numbers(self):
        # Escaping must not turn budget/count values into strings.
        response = self.client.get(reverse("dashboard:dashboard"))
        content = response.content.decode("utf-8")
        # anggaran 1000000 serialized as float by DecimalEncoder, not quoted.
        self.assertIn("1000000.0", content)
