from decimal import Decimal

import pytest
from django.core.management import call_command
from django.test import TestCase

pd = pytest.importorskip("pandas")
from referensi.models import AHSPReferensi, RincianReferensi

class ImportAHSPTests(TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"sumber_ahsp":"SNI 2025", "kode_ahsp":"1.1.1", "nama_ahsp":"Pekerjaan Tanah",
             "satuan_pekerjaan":"m3", "kategori":"", "item":"", "satuan":"", "koefisien":""},
            {"sumber_ahsp":"", "kode_ahsp":"", "nama_ahsp":"",
             "kategori":"TK", "item":"Pekerja", "satuan":"OH", "koefisien":"26,406"},
            {"sumber_ahsp":"", "kode_ahsp":"", "nama_ahsp":"",
             "kategori":"BHN", "item":"Semen", "satuan":"kg", "koefisien":"1.234,56"},
            {"sumber_ahsp":"", "kode_ahsp":"", "nama_ahsp":"",
             "kategori":"ALT", "item":"Mixer", "satuan":"jam", "koefisien":"0.75"},
        ])
        self._orig_read_excel = pd.read_excel
        pd.read_excel = lambda *a, **k: self.df.copy()

    def tearDown(self):
        pd.read_excel = self._orig_read_excel

    def test_import_with_sumber(self):
        call_command("import_ahsp", "dummy.xlsx")
        self.assertEqual(AHSPReferensi.objects.count(), 1)
        a = AHSPReferensi.objects.first()
        self.assertEqual(a.sumber, "SNI 2025")

        self.assertEqual(RincianReferensi.objects.count(), 3)
        koefs = list(RincianReferensi.objects.values_list("koefisien", flat=True))
        self.assertIn(Decimal("26.406"), koefs)
        self.assertIn(Decimal("1234.56"), koefs)
        self.assertIn(Decimal("0.75"), koefs)
