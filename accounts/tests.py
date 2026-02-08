from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from accounts.context_processors import subscription_context
from accounts.middleware import SubscriptionMiddleware
from config.adapters import AccountAdapter
from config.urls import home_redirect, admin_login_redirect
from pages.views import LandingPageView


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
