# referensi/tests/test_import_ahsp.py
import types
import pandas as pd
from decimal import Decimal
from django.core.management import call_command
from django.test import TestCase
from referensi.models import AHSPReferensi, RincianReferensi

class ImportAHSPTests(TestCase):
    def setUp(self):
        # DataFrame contoh meniru Excel (header variasi)
        self.df = pd.DataFrame([
            # Baris pekerjaan
            {"kode_ahsp": "1.1.1", "nama_ahsp": "Pekerjaan Tanah", "kategori": "", "item": "", "satuan": "", "koefisien": ""},
            # Rincian dengan koma desimal
            {"kode_ahsp": "", "nama_ahsp": "", "kategori": "TK", "item": "Pekerja", "satuan": "OH", "koefisien": "26,406"},
            # Rincian dengan format Eropa (ribuan titik, desimal koma)
            {"kode_ahsp": "", "nama_ahsp": "", "kategori": "BHN", "item": "Semen", "satuan": "kg", "koefisien": "1.234,56"},
            # Rincian titik desimal biasa
            {"kode_ahsp": "", "nama_ahsp": "", "kategori": "ALT", "item": "Mixer", "satuan": "jam", "koefisien": "0.75"},
        ])

        # Monkeypatch pandas.read_excel untuk mengembalikan df di atas
        self._orig_read_excel = pd.read_excel
        def _fake_read_excel(*args, **kwargs):
            return self.df.copy()
        pd.read_excel = _fake_read_excel

    def tearDown(self):
        # Kembalikan fungsi asli
        pd.read_excel = self._orig_read_excel

    def test_import_decimal_canonical(self):
        # Jalankan command dengan path dummy (karena di-mock)
        call_command("import_ahsp", "dummy.xlsx")

        self.assertEqual(AHSPReferensi.objects.count(), 1)
        self.assertEqual(RincianReferensi.objects.count(), 3)

        # Ambil semua rincian & cek koefisien canonical
        koefs = list(RincianReferensi.objects.values_list("koefisien", flat=True))
        self.assertIn(Decimal("26.406"), koefs)
        self.assertIn(Decimal("1234.56"), koefs)
        self.assertIn(Decimal("0.75"), koefs)
