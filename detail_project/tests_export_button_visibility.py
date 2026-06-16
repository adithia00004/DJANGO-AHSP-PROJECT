"""
Regression for M7 (audit UI/UX §9.2, 2026-06-10):
tombol export Pro (PDF/Excel/Word) harus terlihat TERKUNCI (link upgrade)
bagi user tanpa entitlement, dan tampil normal bagi user dengan entitlement.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project

# TimeoutMiddleware runs the view in a separate thread and drops the force_login
# session → every request 302s to /accounts/login/ (KF-02). Drop it for these
# render-inspection tests; product auth/entitlement logic is unaffected.
TEST_MIDDLEWARE = [
    m for m in settings.MIDDLEWARE if m != "config.middleware.timeout.TimeoutMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class ExportButtonVisibilityTests(TestCase):
    def _make_user(self, username, **extra):
        user_model = get_user_model()
        return user_model.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Secret123!",
            **extra,
        )

    def _make_project(self, owner):
        return Project.objects.create(
            owner=owner,
            nama=f"Project {owner.username}",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client M7",
            anggaran_owner=1000,
        )

    def _get_page(self, user):
        project = self._make_project(user)
        self.client.force_login(
            user, backend="django.contrib.auth.backends.ModelBackend"
        )
        response = self.client.get(
            reverse(
                "detail_project:rekap_rab", kwargs={"project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_trial_user_sees_locked_export_items(self):
        user_model = get_user_model()
        trial_user = self._make_user("trial_m7")
        trial_user.subscription_status = user_model.SubscriptionStatus.TRIAL
        trial_user.trial_end_date = timezone.now() + timedelta(days=7)
        trial_user.save(update_fields=["subscription_status", "trial_end_date"])

        content = self._get_page(trial_user)
        # Tombol fungsional TIDAK dirender; pengganti = link upgrade terkunci.
        self.assertNotIn('id="btn-export-pdf"', content)
        self.assertNotIn('id="btn-export-word"', content)
        self.assertIn("/pricing/?reason=export_locked", content)
        self.assertIn("bi-lock-fill", content)

    def test_staff_user_sees_functional_export_buttons(self):
        staff_user = self._make_user("staff_m7", is_staff=True)

        content = self._get_page(staff_user)
        self.assertIn('id="btn-export-pdf"', content)
        self.assertIn('id="btn-export-xlsx"', content)
        self.assertIn('id="btn-export-word"', content)
        self.assertNotIn("/pricing/?reason=export_locked", content)

    def test_pro_user_sees_functional_export_buttons(self):
        user_model = get_user_model()
        pro_user = self._make_user("pro_m7")
        pro_user.subscription_status = user_model.SubscriptionStatus.PRO
        pro_user.subscription_end_date = timezone.now() + timedelta(days=30)
        pro_user.save(
            update_fields=["subscription_status", "subscription_end_date"]
        )

        content = self._get_page(pro_user)
        self.assertIn('id="btn-export-pdf"', content)
        self.assertIn('id="btn-export-word"', content)
        self.assertNotIn("/pricing/?reason=export_locked", content)
