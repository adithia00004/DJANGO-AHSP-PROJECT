from pathlib import Path

from django.test import SimpleTestCase


class JadwalApiHardeningTests(SimpleTestCase):
    """Guard active Jadwal v2 endpoints.

    The page uses views_api_tahapan_v2.py, not the legacy tahapan module. Keep
    the active write endpoints aligned with the app-wide write governance.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = Path("detail_project/views_api_tahapan_v2.py").read_text(encoding="utf-8")

    def _decorator_block(self, func_name):
        marker = f"def {func_name}("
        idx = self.source.index(marker)
        prefix = self.source[:idx]
        start = prefix.rfind("\n@login_required")
        self.assertNotEqual(start, -1, f"{func_name} has no @login_required decorator block")
        return self.source[start:idx]

    def assertGoverned(self, func_name, *, rate_snippet):
        block = self._decorator_block(func_name)
        self.assertIn(rate_snippet, block, f"{func_name} missing {rate_snippet}")
        self.assertIn("limit_request_body", block, f"{func_name} missing limit_request_body")

    def test_jadwal_v2_write_endpoints_are_rate_and_body_limited(self):
        self.assertGoverned(
            "api_assign_pekerjaan_weekly",
            rate_snippet="rate_limit(max_requests=240, window=60)",
        )
        for func_name in [
            "api_update_week_boundaries",
            "api_regenerate_tahapan_v2",
            "api_reset_progress",
        ]:
            with self.subTest(func=func_name):
                self.assertGoverned(func_name, rate_snippet="rate_limit(category='write')")
