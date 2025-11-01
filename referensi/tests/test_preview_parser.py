from decimal import Decimal

import pytest
from django.test import SimpleTestCase

from referensi.services.ahsp_parser import parse_excel_dataframe

pd = pytest.importorskip("pandas")


class AHSPPreviewParserTests(SimpleTestCase):
    def test_parse_dataframe_returns_jobs_and_rincian(self):
        df = pd.DataFrame(
            [
                {
                    "sumber_ahsp": "SNI 2025",
                    "kode_ahsp": "1.1.1",
                    "nama_ahsp": "Pekerjaan Tanah",
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
        self.assertEqual(job.rincian_count, 2)
        self.assertEqual(job.rincian[0].koefisien, Decimal("26.406"))
        self.assertEqual(job.rincian[1].koefisien, Decimal("1234.56"))

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
        self.assertIn("Kolom wajib hilang", result.errors[0])
        self.assertEqual(result.total_jobs, 0)
