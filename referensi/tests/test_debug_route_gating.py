"""
N-1 regression: the destructive debug clear-data route must not be present in
the URL map under production-like settings (DEBUG=False).
"""
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse


class DebugClearDataRouteGatingTests(SimpleTestCase):
    def test_route_absent_when_debug_false(self):
        # config.settings.test runs with DEBUG=False, matching production; the
        # route is only registered inside `if settings.DEBUG` in referensi/urls.
        with self.assertRaises(NoReverseMatch):
            reverse("referensi:debug_clear_data")
