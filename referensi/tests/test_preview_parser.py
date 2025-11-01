from decimal import Decimal

import pytest
from django.test import SimpleTestCase

from referensi.services.ahsp_parser import get_column_schema, parse_excel_dataframe

pd = pytest.importorskip("pandas")


class AHSPPreviewParserTests(SimpleTestCase):
    def test_parse_dataframe_returns_jobs_and_rincian(self):
        df = pd.DataFrame(
            [
                {
                    "sumber_ahsp": "SNI 2025",
                    "kode_ahsp": "1.1.1",
                    "nama_ahsp": "Pekerjaan Tanah",
                    "klasifikasi": "SIPIL",
                    "sub_klasifikasi": "Pekerjaan Tanah",
                    "satuan": "m3",
                    "kategori": "",
                    "item": "",
                    "satuan": "",
                    "koefisien": "",
                },
                {
                    "sumber_ahsp": "",
                    "kode_ahsp": "",
                    "nama_ahsp": "",
                    "kategori": "TK",
                    "item": "Pekerja",
                    "satuan": "OH",
                    "koefisien": "26,406",
                },
                {
                    "sumber_ahsp": "",
                    "kode_ahsp": "",
                    "nama_ahsp": "",
                    "kategori": "BHN",
                    "item": "Semen",
                    "satuan": "kg",
                    "koefisien": "1.234,56",
                },
            ]
        )

        result = parse_excel_dataframe(df)

        self.assertFalse(result.errors)
        self.assertEqual(result.total_jobs, 1)
        self.assertEqual(result.total_rincian, 2)

        job = result.jobs[0]
        self.assertEqual(job.sumber, "SNI 2025")
        self.assertEqual(job.kode_ahsp, "1.1.1")
        self.assertEqual(job.klasifikasi, "SIPIL")
        self.assertEqual(job.sub_klasifikasi, "Pekerjaan Tanah")
        self.assertEqual(job.satuan, "m3")
        self.assertEqual(job.rincian_count, 2)
        self.assertEqual(job.rincian[0].koefisien, Decimal("26.406"))
        self.assertEqual(job.rincian[1].koefisien, Decimal("1234.56"))
        self.assertEqual(job.rincian[0].kategori, "TK")
        self.assertEqual(job.rincian[0].kategori_source, "TK")

    def test_missing_required_columns_yields_error(self):
        df = pd.DataFrame(
            [
                {
                    "kode_ahsp": "1.1.1",
                    "nama_ahsp": "Pekerjaan Tanah",
                }
            ]
        )

        result = parse_excel_dataframe(df)

        self.assertTrue(result.errors)
        self.assertTrue(
            any("sumber_ahsp" in err for err in result.errors),
            result.errors,
        )
        self.assertTrue(
            any("kategori" in err for err in result.errors),
            result.errors,
        )
        self.assertEqual(result.total_jobs, 0)

    def test_category_mapping_is_reported(self):
        df = pd.DataFrame(
            [
                {
                    "sumber_ahsp": "Sumber",
                    "kode_ahsp": "J1",
                    "nama_ahsp": "Pekerjaan",
                    "kategori": "Tenaga Kerja",
                    "item": "Tukang",
                    "satuan": "OH",
                    "koefisien": "1",
                }
            ]
        )

        result = parse_excel_dataframe(df)

        self.assertFalse(result.errors)
        self.assertEqual(result.total_jobs, 1)
        self.assertEqual(result.total_rincian, 1)
        self.assertEqual(result.jobs[0].rincian[0].kategori, "TK")
        self.assertIn("dipetakan ke kode standar", " ".join(result.warnings))

    def test_invalid_koefisien_values_raise_error(self):
        df = pd.DataFrame(
            [
                {
                    "sumber_ahsp": "Sumber",
                    "kode_ahsp": "J1",
                    "nama_ahsp": "Pekerjaan",
                    "kategori": "TK",
                    "item": "Pekerja",
                    "satuan": "OH",
                    "koefisien": "angka salah",
                }
            ]
        )

        result = parse_excel_dataframe(df)

        self.assertTrue(result.errors)
        self.assertTrue(
            any("koefisien" in err and "tidak valid" in err for err in result.errors)
        )
        self.assertEqual(result.total_rincian, 0)

    def test_column_schema_export_contains_expected_groups(self):
        schema = get_column_schema()

        self.assertIn("jobs", schema)
        self.assertIn("details", schema)
        self.assertTrue(any(spec.canonical == "kode_ahsp" for spec in schema["jobs"]))
        self.assertTrue(
            any(spec.canonical == "koefisien" for spec in schema["details"])
        )
