"""WP-B5 inc-B5a — export error wrapper (correlation ID, no str(e) leak)."""
import json
import os

from django.test import TestCase

from detail_project.exports.errors import (
    export_error_response,
    log_export_error,
    new_correlation_id,
)

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


class ExportErrorWrapperTests(TestCase):
    def test_correlation_id_is_short_hex(self):
        cid = new_correlation_id()
        self.assertEqual(len(cid), 12)
        int(cid, 16)  # raises if not hex

    def test_error_response_does_not_leak_exception_text(self):
        secret = "secret-internal-stacktrace-xyz"
        try:
            raise ValueError(secret)
        except ValueError as e:
            resp = export_error_response(e, context="unit-test")

        self.assertEqual(resp.status_code, 500)
        body = json.loads(resp.content)
        self.assertFalse(body["ok"])
        self.assertIn("correlation_id", body)
        self.assertEqual(len(body["correlation_id"]), 12)
        self.assertNotIn(secret, resp.content.decode("utf-8"))

    def test_error_response_respects_status_and_message(self):
        resp = export_error_response(
            RuntimeError("x"), status=400, user_message="Pesan khusus"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["error"], "Pesan khusus")

    def test_log_export_error_returns_correlation_id(self):
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            cid = log_export_error(e, context="unit-test")
        self.assertEqual(len(cid), 12)


class ExportLeakGuardTests(TestCase):
    """Lock the two real str(e) leaks fixed in B5a."""

    def _src(self, rel):
        with open(os.path.join(_APP_DIR, rel), encoding="utf-8") as f:
            return f.read()

    def test_word_exporter_no_exception_text_in_document(self):
        src = self._src(os.path.join("exports", "word_exporter.py"))
        self.assertNotIn("Error embedding image: {str(e)}", src)
        self.assertIn("gambar gagal dimuat. Ref:", src)
        self.assertIn("log_export_error", src)

    def test_finalize_does_not_return_raw_exception(self):
        src = self._src("views_export.py")
        self.assertNotIn("Generation failed: {error_msg}", src)
        self.assertNotIn("error_msg = str(e)", src)
        self.assertIn("log_export_error", src)
        self.assertIn("correlation_id", src)

    def test_async_failure_does_not_return_task_exception(self):
        src = self._src("views_export.py")
        self.assertNotIn(
            "response_data['error'] = error_info.get('error', str(error_info))",
            src,
        )
        self.assertNotIn("response_data['error'] = str(error_info)", src)
        self.assertIn("GENERIC_EXPORT_MESSAGE", src)
        self.assertIn("context=f\"async export task {task_id}\"", src)
