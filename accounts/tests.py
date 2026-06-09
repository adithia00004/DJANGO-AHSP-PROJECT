from types import SimpleNamespace
from datetime import timedelta

from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.context_processors import app_contact_context, subscription_context
from accounts.middleware import SubscriptionMiddleware
from accounts.signals import start_trial_on_email_confirmation
from config.adapters import AccountAdapter
from config.urls import home_redirect, admin_login_redirect
from pages.views import LandingPageView
from subscriptions.entitlements import FEATURE_WRITE_ACCESS, get_feature_access


class DummyUser(SimpleNamespace):
    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - convenience helper
        return True

    def get_full_name(self):  # pragma: no cover - optional helper
        return getattr(self, "full_name", "")

    def has_perms(self, perms):  # pragma: no cover - convenience helper
        allowed = getattr(self, "perms", set())
        return all(code in allowed for code in perms)


class AdminRedirectTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = DummyUser(
            is_superuser=True,
            is_staff=True,
            username="admin",
            perms=set(),
        )
        self.staff_user = DummyUser(
            is_superuser=False,
            is_staff=True,
            username="staff",
            perms={"referensi.view_ahspreferensi", "referensi.change_ahspreferensi"},
        )
        self.staff_no_portal_perm = DummyUser(
            is_superuser=False,
            is_staff=True,
            username="staff-no-portal",
            perms=set(),
        )
        self.regular_user = DummyUser(is_superuser=False, is_staff=False, username="user")

    def _make_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_home_redirect_superuser(self):
        response = home_redirect(self._make_request(self.superuser))
        self.assertEqual(response.url, reverse("referensi:admin_portal"))

    def test_home_redirect_staff_user(self):
        response = home_redirect(self._make_request(self.staff_user))
        self.assertEqual(response.url, reverse("referensi:admin_portal"))

    def test_home_redirect_regular_user(self):
        response = home_redirect(self._make_request(self.regular_user))
        self.assertEqual(response.url, reverse("dashboard:dashboard"))

    def test_home_redirect_staff_without_portal_permission(self):
        response = home_redirect(self._make_request(self.staff_no_portal_perm))
        self.assertEqual(response.url, reverse("dashboard:dashboard"))

    def test_account_adapter_redirect_superuser(self):
        request = self._make_request(self.superuser)
        adapter = AccountAdapter()
        self.assertEqual(adapter.get_login_redirect_url(request), reverse("referensi:admin_portal"))

    def test_account_adapter_redirect_staff_user(self):
        request = self._make_request(self.staff_user)
        adapter = AccountAdapter()
        self.assertEqual(adapter.get_login_redirect_url(request), reverse("referensi:admin_portal"))

    def test_account_adapter_redirect_regular_user(self):
        request = self._make_request(self.regular_user)
        adapter = AccountAdapter()
        self.assertEqual(adapter.get_login_redirect_url(request), reverse("dashboard:dashboard"))

    def test_account_adapter_redirect_staff_without_portal_permission(self):
        request = self._make_request(self.staff_no_portal_perm)
        adapter = AccountAdapter()
        self.assertEqual(adapter.get_login_redirect_url(request), reverse("dashboard:dashboard"))

    def test_account_adapter_respects_next_parameter(self):
        request = self.factory.get("/", {"next": "/admin/"})
        request.user = self.superuser
        adapter = AccountAdapter()
        self.assertEqual(adapter.get_login_redirect_url(request), "/admin/")


class AdminLoginRedirectTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_redirects_to_allauth_with_explicit_next(self):
        request = self.factory.get("/admin/login/", {"next": "/admin/"})
        response = admin_login_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('account_login')}?next=%2Fadmin%2F")

    def test_redirects_to_admin_index_when_next_missing(self):
        request = self.factory.get("/admin/login/")
        response = admin_login_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('account_login')}?next=%2Fadmin%2F")


class LoginTemplateRedirectFieldTests(TestCase):
    def test_login_template_preserves_next_field(self):
        response = self.client.get(f"{reverse('account_login')}?next=/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'name="next" value="/admin/"',
            html=False,
        )


class SubscriptionMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SubscriptionMiddleware(lambda req: HttpResponse("OK"))
        self.expired_user = DummyUser(
            is_superuser=False,
            is_staff=False,
            is_authenticated=True,
            is_subscription_active=False,
        )
        self.active_user = DummyUser(
            is_superuser=False,
            is_staff=False,
            is_authenticated=True,
            is_subscription_active=True,
        )
        self.anonymous = SimpleNamespace(is_authenticated=False)

    def test_non_api_write_redirects_expired_user(self):
        request = self.factory.post("/dashboard/project/1/edit/")
        request.user = self.expired_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pricing/", response.url)
        self.assertIn("subscription_expired", response.url)

    def test_api_write_returns_403_for_expired_user(self):
        request = self.factory.post(
            "/detail_project/api/project/1/list-pekerjaan/save/",
            HTTP_ACCEPT="application/json",
        )
        request.user = self.expired_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_read_request_is_allowed(self):
        request = self.factory.get("/dashboard/")
        request.user = self.expired_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_write_passthrough(self):
        request = self.factory.post("/dashboard/project/1/edit/")
        request.user = self.anonymous
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)


class SubscriptionContextTests(SimpleTestCase):
    def test_admin_does_not_show_upgrade_banner(self):
        admin_user = DummyUser(
            is_authenticated=True,
            has_full_access=True,
            subscription_status="TRIAL",
            is_subscription_active=True,
            is_trial_active=True,
            is_pro_active=True,
            can_edit=True,
            can_export_clean=True,
            days_until_expiry=3,
        )
        request = SimpleNamespace(user=admin_user)

        context = subscription_context(request)

        self.assertEqual(context["subscription_status"], "ADMIN")
        self.assertFalse(context["show_upgrade_banner"])


class AppContactContextTests(SimpleTestCase):
    @override_settings(SUPPORT_EMAIL="helpdesk@ahsp.test")
    def test_app_contact_context_exposes_support_email(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
        context = app_contact_context(request)

        self.assertEqual(context["support_email"], "helpdesk@ahsp.test")


class LandingRedirectTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_landing_redirects_staff_with_portal_permission_to_admin_portal(self):
        user = DummyUser(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            perms={"referensi.view_ahspreferensi", "referensi.change_ahspreferensi"},
        )
        request = self.factory.get("/")
        request.user = user

        response = LandingPageView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("referensi:admin_portal"))

    def test_landing_redirects_staff_without_portal_permission_to_dashboard(self):
        user = DummyUser(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            perms=set(),
        )
        request = self.factory.get("/")
        request.user = user

        response = LandingPageView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:dashboard"))


class TrialLifetimePolicyTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_start_trial_can_only_be_used_once(self):
        user = self.user_model.objects.create_user(
            username="trial_once_user",
            email="trial-once@example.com",
            password="Secret123!",
            subscription_status="EXPIRED",
        )

        started_first_time = user.start_trial(days=14)
        user.refresh_from_db()
        first_trial_end = user.trial_end_date

        self.assertTrue(started_first_time)
        self.assertEqual(user.subscription_status, user.SubscriptionStatus.TRIAL)
        self.assertTrue(user.trial_used_once)
        self.assertIsNotNone(first_trial_end)

        # Simulate trial expiration.
        user.subscription_status = user.SubscriptionStatus.EXPIRED
        user.trial_end_date = timezone.now() - timedelta(days=1)
        user.save(update_fields=["subscription_status", "trial_end_date"])

        started_second_time = user.start_trial(days=14)
        user.refresh_from_db()

        self.assertFalse(started_second_time)
        self.assertEqual(user.subscription_status, user.SubscriptionStatus.EXPIRED)
        self.assertLessEqual(user.trial_end_date, timezone.now())

    def test_email_confirm_signal_does_not_restart_consumed_trial(self):
        user = self.user_model.objects.create_user(
            username="signal_trial_once_user",
            email="signal-trial-once@example.com",
            password="Secret123!",
            subscription_status="EXPIRED",
            trial_used_once=True,
            trial_end_date=timezone.now() - timedelta(days=2),
        )

        email_address = SimpleNamespace(user=user)
        start_trial_on_email_confirmation(request=None, email_address=email_address)
        user.refresh_from_db()

        self.assertEqual(user.subscription_status, user.SubscriptionStatus.EXPIRED)
        self.assertTrue(user.trial_used_once)
        self.assertLessEqual(user.trial_end_date, timezone.now())


class TrialAccessGuardTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.factory = RequestFactory()
        self.middleware = SubscriptionMiddleware(lambda req: HttpResponse("OK"))

    def test_trial_without_end_date_has_no_write_access(self):
        user = self.user_model.objects.create_user(
            username="trial_no_end_guard",
            email="trial_no_end_guard@example.com",
            password="Secret123!",
            subscription_status="TRIAL",
            trial_end_date=None,
            trial_used_once=False,
        )

        decision = get_feature_access(user, FEATURE_WRITE_ACCESS)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SUBSCRIPTION_EXPIRED")

    def test_trial_without_end_date_blocked_by_middleware_for_api_write(self):
        user = self.user_model.objects.create_user(
            username="trial_no_end_middleware",
            email="trial_no_end_middleware@example.com",
            password="Secret123!",
            subscription_status="TRIAL",
            trial_end_date=None,
            trial_used_once=False,
        )

        request = self.factory.post(
            "/detail_project/api/project/1/list-pekerjaan/save/",
            HTTP_ACCEPT="application/json",
        )
        request.user = user
        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_context_processor_consistent_for_trial_without_end_date(self):
        user = self.user_model.objects.create_user(
            username="trial_no_end_context",
            email="trial_no_end_context@example.com",
            password="Secret123!",
            subscription_status="TRIAL",
            trial_end_date=None,
            trial_used_once=False,
        )
        request = self.factory.get("/")
        request.user = user

        context = subscription_context(request)
        self.assertFalse(context["is_subscription_active"])
        self.assertFalse(context["can_edit"])
