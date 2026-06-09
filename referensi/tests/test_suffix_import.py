"""Integration/regression tests for letter-suffix AHSP codes (e.g. 2.2.1.1.5.a)."""

import tempfile
from io import BytesIO
from pathlib import Path

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from referensi.models import AHSPReferensi
from referensi.models_staging import AHSPImportBatch, AHSPImportStaging
from referensi.views.import_views import _get_validation_results, _stage_rincian_legacy_flat, staging_commit


def _parent_block(code):
    """Validation-report shape: title row + full TK/BHN/PR data for one parent.

    Columns: [parent, segment, no, uraian, kode, satuan, koefisien].
    """
    return [
        [f"{code} Pekerjaan {code}"],
        [code, "TK", "1", "Tenaga Kerja", "tenaga kerja", "-", "-"],
        [code, "TK", "1", "Pekerja", "L.01", "OH", "1"],
        [code, "BHN", "2", "Bahan", "bahan", "-", "-"],
        [code, "BHN", "1", "Semen", "PC.01", "kg", "2"],
        [code, "PR", "3", "Peralatan", "peralatan", "-", "-"],
        [code, "PR", "1", "Alat", "E.01", "jam", "0.5"],
    ]


def _clean_block(code):
    """Clean-import shape: title row + one A/B/C item each for one parent.

    Clean import expects document segment labels (A/B/C) in column 1 and the
    layout [parent, segment, kode_item, uraian, satuan, koefisien].
    """
    return [
        [f"{code} Pekerjaan {code}"],
        [code, "A", "L.01", "Pekerja", "OH", "1"],
        [code, "B", "PC.01", "Semen", "kg", "2"],
        [code, "C", "E.01", "Alat", "jam", "0.5"],
    ]


class SuffixValidationReportTests(TestCase):
    def test_suffix_parents_are_not_merged(self):
        rows = (
            _parent_block("2.2.1.1.5.a")
            + _parent_block("2.2.1.1.5.b")
            + _parent_block("2.2.1.1.5.c")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "suffix_validate.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        parent_codes = [
            item["first_col"].split(" ")[0]
            for item in results
            if item.get("type") == "hierarchy_parent"
        ]
        self.assertEqual(parent_codes, ["2.2.1.1.5.a", "2.2.1.1.5.b", "2.2.1.1.5.c"])

        table_codes = [
            item["first_col"]
            for item in results
            if item.get("type") == "table_container"
        ]
        # Three distinct tables, never collapsed onto the numeric base 2.2.1.1.5.
        self.assertEqual(
            set(table_codes), {"2.2.1.1.5.a", "2.2.1.1.5.b", "2.2.1.1.5.c"}
        )
        self.assertNotIn("2.2.1.1.5", table_codes)

    def test_three_digit_first_segment_does_not_crash(self):
        # Regression: this code previously reached an undefined `regex_kode_ahsp`
        # in _get_validation_results and raised NameError.
        rows = _parent_block("123.4.5.6")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "threedigit.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        parents = [r for r in results if r.get("type") == "hierarchy_parent"]
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0]["first_col"].split(" ")[0], "123.4.5.6")


class SuffixCleanImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="suffix-admin",
            email="suffix-admin@example.com",
            password="Secret123!",
        )
        self.client.force_login(self.user)
        self.factory = RequestFactory()

    def _upload_xlsx(self, rows, name="clean.xlsx", sumber=""):
        buffer = BytesIO()
        pd.DataFrame(rows).to_excel(buffer, index=False, header=False)
        buffer.seek(0)
        upload = SimpleUploadedFile(
            name,
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return self.client.post(
            reverse("referensi:import_excel"), {"excel_file": upload, "sumber": sumber}
        )

    def test_suffix_codes_commit_as_separate_ahsp(self):
        rows = (
            _clean_block("2.2.1.1.5.a")
            + _clean_block("2.2.1.1.5.b")
            + _clean_block("2.2.1.1.5.c")
        )
        self._upload_xlsx(rows, sumber="AHSP 2024")

        # Count parents from DATA rows (segment A/B/C); HEADING bookkeeping rows
        # carry an empty/None parent_ahsp_code and must not be counted here.
        staged_parents = set(
            AHSPImportStaging.objects.filter(
                user=self.user, segment_type__in=["A", "B", "C"]
            ).values_list("parent_ahsp_code", flat=True)
        )
        self.assertEqual(staged_parents, {"2.2.1.1.5.a", "2.2.1.1.5.b", "2.2.1.1.5.c"})

        # Regression: the staging page must render. import_staging.html had a
        # cross-line {% endif %} tag that raised TemplateSyntaxError (500).
        page = self.client.get(reverse("referensi:import_staging"))
        self.assertEqual(page.status_code, 200)

        self.client.post(reverse("referensi:import_staging_commit"), {"sumber": "AHSP 2024"})

        committed = set(
            AHSPReferensi.objects.filter(
                kode_ahsp__startswith="2.2.1.1.5", sumber="AHSP 2024"
            ).values_list("kode_ahsp", flat=True)
        )
        self.assertEqual(committed, {"2.2.1.1.5.a", "2.2.1.1.5.b", "2.2.1.1.5.c"})

    def test_three_segment_clean_import_can_be_parent_when_it_has_data(self):
        rows = [
            ["3.2.1 Pemasangan 1 m2 Lembaran Insulasi Atap"],
            ["3.2.1", "A", "L.01", "Pekerja", "OH", "0.2"],
            ["3.2.1", "B", "B.01", "Insulasi", "m2", "1.05"],
            ["3.2.1", "C", "E.02", "Perancah", "set", "0.1"],
        ]
        batch = AHSPImportBatch.objects.create(
            user=self.user,
            file_name="three-segment.xlsx",
            sumber="AHSP 2026",
        )
        imported = _stage_rincian_legacy_flat(
            self.user,
            "three-segment.xlsx",
            pd.DataFrame(rows),
            "AHSP 2026",
            batch=batch,
        )

        self.assertEqual(imported, 3)
        staged_parents = set(
            AHSPImportStaging.objects.filter(
                user=self.user,
                segment_type__in=["A", "B", "C"],
            ).values_list("parent_ahsp_code", flat=True)
        )
        self.assertEqual(staged_parents, {"3.2.1"})

        request = self.factory.post(
            reverse("referensi:import_staging_commit"),
            {"batch_id": batch.id, "sumber": "AHSP 2026"},
        )
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        response = staging_commit(request)

        self.assertEqual(response.status_code, 302)
        ahsp = AHSPReferensi.objects.get(kode_ahsp="3.2.1", sumber="AHSP 2026")
        self.assertEqual(ahsp.nama_ahsp, "Pemasangan 1 m2 Lembaran Insulasi Atap")
        self.assertEqual(ahsp.rincian.count(), 3)

    def test_commit_without_sumber_is_rejected(self):
        self._upload_xlsx(_clean_block("3.3.3.3"), sumber="")
        # No sumber anywhere -> commit must refuse and create nothing.
        self.client.post(reverse("referensi:import_staging_commit"))
        self.assertFalse(AHSPReferensi.objects.filter(kode_ahsp="3.3.3.3").exists())

    def test_export_format_roundtrip(self):
        """The 2-sheet 'Data Valid' export (Daftar Isi + Data Valid, with a 'No'
        column) must import and commit correctly: right sheet, columns by name."""
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            pd.DataFrame(
                [{"Kode AHSP": "1.2.3.4", "Judul Pekerjaan": "Galian Tanah"}]
            ).to_excel(writer, index=False, sheet_name="Daftar Isi")
            pd.DataFrame(
                [
                    {"Kode Induk": "1.2.3.4", "Segment": "A", "No": "1", "Uraian": "Pekerja", "Kode Referensi": "L.01", "Satuan": "OH", "Koefisien": "0.5"},
                    {"Kode Induk": "1.2.3.4", "Segment": "B", "No": "1", "Uraian": "Semen", "Kode Referensi": "PC.01", "Satuan": "kg", "Koefisien": "2"},
                    {"Kode Induk": "1.2.3.4", "Segment": "C", "No": "1", "Uraian": "Alat", "Kode Referensi": "E.01", "Satuan": "jam", "Koefisien": "3"},
                ]
            ).to_excel(writer, index=False, sheet_name="Data Valid")
        out.seek(0)
        upload = SimpleUploadedFile(
            "ahsp_valid_data.xlsx",
            out.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.client.post(
            reverse("referensi:import_excel"), {"excel_file": upload, "sumber": "AHSP 2024"}
        )

        # Data rows reached staging with kode_item from "Kode Referensi" (not "No").
        staged = {
            (s.segment_type, s.kode_item, s.satuan_item)
            for s in AHSPImportStaging.objects.filter(
                user=self.user, parent_ahsp_code="1.2.3.4"
            )
        }
        self.assertEqual(
            staged,
            {("A", "L.01", "OH"), ("B", "PC.01", "kg"), ("C", "E.01", "jam")},
        )

        self.client.post(reverse("referensi:import_staging_commit"), {"sumber": "AHSP 2024"})

        ahsp = AHSPReferensi.objects.get(kode_ahsp="1.2.3.4", sumber="AHSP 2024")
        self.assertEqual(ahsp.nama_ahsp, "Galian Tanah")  # title from Daftar Isi
        rincian = {(r.kategori, r.kode_item, r.satuan_item) for r in ahsp.rincian.all()}
        self.assertEqual(
            rincian,
            {("TK", "L.01", "OH"), ("BHN", "PC.01", "kg"), ("ALT", "E.01", "jam")},
        )
