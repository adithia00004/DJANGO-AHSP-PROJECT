"""Multi-file validation upload: several xlsx merged into one validation/report."""

import os
from io import BytesIO

import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from referensi.views.import_views import _get_validation_results


def _xlsx_bytes(rows):
    buffer = BytesIO()
    pd.DataFrame(rows).to_excel(buffer, sheet_name="Data", index=False, header=False)
    buffer.seek(0)
    return buffer.read()


class ValidateMultiFileUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="validate-admin",
            email="validate-admin@example.com",
            password="Secret123!",
        )
        self.client.force_login(self.user)

    def _upload(self, files):
        return self.client.post(reverse("referensi:import_validate"), {"excel_file": files})

    def test_multiple_files_merge_into_single_validation(self):
        # File 1: compact 7-column layout.
        f1 = SimpleUploadedFile(
            "part1.xlsx",
            _xlsx_bytes([
                ["1.1.1.1 Pekerjaan A"],
                ["1.1.1.1", "TK", "Pekerja", "L.01", "OH", "0,1", "OK"],
            ]),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        # File 2: wide 11-column fixed layout (different width on purpose).
        N = None
        f2 = SimpleUploadedFile(
            "part2.xlsx",
            _xlsx_bytes([
                ["2.2.2.2 Pekerjaan B", N, N, N, N, N, N, N, N, N, "OK"],
                ["2.2.2.2", "TK", "1", "Tukang", "L.02", "OH", "0,2", N, N, N, "OK"],
            ]),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        resp = self._upload([f1, f2])
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/import/validate/report/", resp.url)

        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        results, _, _ = _get_validation_results(path)
        parents = {
            r["first_col"].split(" ")[0]
            for r in results if r.get("type") == "hierarchy_parent"
        }
        # Both files' AHSP parents are present in the single merged report.
        self.assertIn("1.1.1.1", parents)
        self.assertIn("2.2.2.2", parents)

    def test_single_file_still_works(self):
        f1 = SimpleUploadedFile(
            "solo.xlsx",
            _xlsx_bytes([
                ["1.1.1.1 Pekerjaan A"],
                ["1.1.1.1", "TK", "Pekerja", "L.01", "OH", "0,1", "OK"],
            ]),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = self._upload([f1])
        self.assertEqual(resp.status_code, 302)
        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        results, _, _ = _get_validation_results(path)
        parents = {
            r["first_col"].split(" ")[0]
            for r in results if r.get("type") == "hierarchy_parent"
        }
        self.assertIn("1.1.1.1", parents)
