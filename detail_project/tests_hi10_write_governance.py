from pathlib import Path
from django.test import SimpleTestCase


class HI10WriteGovernanceTests(SimpleTestCase):
    """Guard repo-wide write governance discovered from Harga Items HI-10.

    The risk here is not the rate/body-limit helper itself; it is endpoint drift
    where callable write endpoints forget to opt in. Keep this list aligned with
    the HI-10 sweep in doc 28.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = Path("detail_project/views_api.py").read_text(encoding="utf-8")

    def _decorator_block(self, func_name):
        marker = f"def {func_name}("
        idx = self.source.index(marker)
        prefix = self.source[:idx]
        start = prefix.rfind("\n@login_required")
        self.assertNotEqual(start, -1, f"{func_name} has no @login_required decorator block")
        return self.source[start:idx]

    def assertGoverned(self, func_name, *, rate_snippet="rate_limit", body=True):
        block = self._decorator_block(func_name)
        self.assertIn(rate_snippet, block, f"{func_name} missing {rate_snippet}")
        if body:
            self.assertIn("limit_request_body", block, f"{func_name} missing limit_request_body")

    def test_harga_items_write_endpoints_are_rate_and_body_limited(self):
        self.assertGoverned("api_save_harga_items", rate_snippet="rate_limit(category='write')")
        self.assertGoverned("api_save_conversion_profile", rate_snippet="rate_limit(category='write')")
        self.assertGoverned("api_cleanup_orphaned_harga_items", rate_snippet="rate_limit(category='write')")

    def test_cross_page_write_endpoints_from_hi10_sweep_are_governed(self):
        for func_name in [
            "api_project_pricing",
            "api_project_parameters",
            "api_project_computed_parameters",
        ]:
            with self.subTest(func=func_name):
                block = self._decorator_block(func_name)
                self.assertIn("@rate_limit(category='read_interactive'", block)
                self.assertIn("@rate_limit(category='sync_frequent'", block)
                self.assertIn("limit_request_body", block)

        for func_name in [
            "api_save_detail_ahsp_gabungan",
            "api_ack_source_change_flags",
            "api_delete_template",
        ]:
            with self.subTest(func=func_name):
                self.assertGoverned(func_name)

    def test_bulk_copy_endpoints_use_bulk_rate_limit_and_body_limit(self):
        self.assertGoverned("api_deep_copy_project", rate_snippet="rate_limit(category='bulk')")
        self.assertGoverned("api_batch_copy_project", rate_snippet="rate_limit(category='bulk')")
