"""
N-5 regression: when the content-security scan fails unexpectedly, the
ValidationError shown to the user must not leak the raw exception detail.
"""
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from referensi.validators import AHSPFileValidator

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ContentSecurityErrorLeakTests(SimpleTestCase):
    def test_scan_failure_does_not_leak_exception_detail(self):
        validator = AHSPFileValidator()
        upload = SimpleUploadedFile("book.xlsx", b"PK\x03\x04 dummy", content_type=_XLSX_MIME)
        secret = "SECRET_INTERNAL_TRACEBACK_DETAIL"

        with patch(
            "referensi.validators.openpyxl.load_workbook",
            side_effect=Exception(secret),
        ):
            with self.assertRaises(ValidationError) as ctx:
                validator.validate_content_security(upload)

        message = " ".join(str(m) for m in ctx.exception.messages)
        self.assertNotIn(secret, message)
        self.assertIn("Gagal memeriksa keamanan file", message)
