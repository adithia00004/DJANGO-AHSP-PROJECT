"""
N-7 regression: the import rate-limit middleware must actually cover the real
3-tier import endpoints (/referensi/import/...) and only throttle write
operations, not page navigation.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from referensi.middleware.rate_limit import ImportRateLimitMiddleware


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    IMPORT_RATE_LIMIT=2,
    IMPORT_RATE_WINDOW=3600,
    IMPORT_RATE_LIMIT_PATHS=["/referensi/import/"],
)
class ImportRateLimitMiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.middleware = ImportRateLimitMiddleware(lambda r: HttpResponse("ok"))
        self.user = get_user_model().objects.create_user(
            username="rate_limit_user",
            email="rate-limit@example.com",
            password="Secret123!",
        )

    def _send(self, method="post", path="/referensi/import/staging/commit/"):
        request = getattr(self.factory, method)(
            path, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        request.user = self.user
        return self.middleware(request)

    @patch("referensi.services.audit_logger.audit_logger.log_rate_limit_exceeded")
    def test_import_post_is_rate_limited_after_limit(self, _mock_log):
        # The actual import endpoint is now covered (previously it matched no path).
        self.assertEqual(self._send().status_code, 200)
        self.assertEqual(self._send().status_code, 200)
        # Third write exceeds IMPORT_RATE_LIMIT=2.
        self.assertEqual(self._send().status_code, 429)

    def test_import_get_navigation_is_not_rate_limited(self):
        # GET on import paths (report view, download, landing) must not consume
        # the import budget even past the limit.
        for _ in range(5):
            response = self._send(
                method="get", path="/referensi/import/validate/report/abc/"
            )
            self.assertEqual(response.status_code, 200)

    def test_non_import_path_is_not_rate_limited(self):
        for _ in range(5):
            response = self._send(method="post", path="/dashboard/whatever/")
            self.assertEqual(response.status_code, 200)
