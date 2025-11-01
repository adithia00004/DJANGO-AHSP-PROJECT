from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from config.adapters import AccountAdapter
from config.urls import home_redirect


class DummyUser(SimpleNamespace):
    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - convenience helper
        return True

    def get_full_name(self):  # pragma: no cover - optional helper
        return getattr(self, "full_name", "")


class AdminRedirectTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = DummyUser(is_superuser=True, is_staff=True, username="admin")
        self.staff_user = DummyUser(is_superuser=False, is_staff=True, username="staff")
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
