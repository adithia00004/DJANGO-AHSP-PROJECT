"""Tinggi baris MINIMUM pada tabel export (keputusan owner 2026-09-22).

Minimum, bukan tetap: baris dengan uraian panjang tetap boleh lebih tinggi.
Rincian AHSP memakai ambang lebih rendah karena tabelnya paling padat.

Lembar pengesahan DIKECUALIKAN -- blok itu sengaja dirapatkan atas permintaan
owner 2026-08-18, dan ambang ini tidak boleh membatalkannya.
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from detail_project.exports.table_styles import (
    ROW_MIN_HEIGHT_CM,
    ROW_MIN_HEIGHT_RINCIAN_CM,
)


class ExportRowHeightTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="row-height-owner", password="StrongPass123!"
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Tinggi Baris",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas",
            # Baris pertama lembar pengesahan = instansi (R-37); dipakai untuk
            # mengenali tabel tanda tangan.
            instansi_client="Pemkab Uji Tinggi Baris",
            nama_konsultan_perencana="Perencana",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2027, 1, 1),
        )
        self._seed_one_pekerjaan()

    def _seed_one_pekerjaan(self):
        """Rincian AHSP hanya menghasilkan tabel bila ada pekerjaan.

        Tanpa ini tesnya lulus karena dokumennya kosong -- bukan karena
        ambangnya benar.
        """
        from detail_project.models import Klasifikasi, Pekerjaan, SubKlasifikasi

        klas = Klasifikasi.objects.create(
            project=self.project, name="Klas A", ordering_index=1
        )
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="Sub A1", ordering_index=1
        )
        Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            ordering_index=1,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUS-001",
            snapshot_uraian="Pekerjaan uji tinggi baris",
            snapshot_satuan="m2",
        )

    def _manager(self):
        from detail_project.exports.export_manager import ExportManager

        return ExportManager(self.project)

    # ---------- Word ----------

    def _word_heights(self, export_call):
        from docx import Document

        doc = Document(BytesIO(bytes(export_call().content)))
        rows = []
        for table in doc.tables:
            header = " ".join(c.text for c in table.rows[0].cells)
            is_signature = "Pemkab Uji Tinggi Baris" in header
            for row in table.rows:
                rows.append((is_signature, row.height.cm if row.height else None))
        return rows

    def test_word_data_tables_meet_the_default_minimum(self):
        rows = self._word_heights(lambda: self._manager().export_rekap_rab("word"))
        data_heights = [h for sig, h in rows if not sig and h is not None]

        self.assertTrue(data_heights, "tak satu pun baris data punya tinggi tercatat")
        self.assertGreaterEqual(min(data_heights), ROW_MIN_HEIGHT_CM - 0.01)

    def test_word_rincian_uses_the_lower_minimum(self):
        rows = self._word_heights(lambda: self._manager().export_rincian_ahsp("word"))
        data_heights = [h for sig, h in rows if not sig and h is not None]

        self.assertTrue(data_heights)
        self.assertAlmostEqual(min(data_heights), ROW_MIN_HEIGHT_RINCIAN_CM, places=2)

    def test_word_signature_block_stays_tight(self):
        """Blok tanda tangan tidak boleh ikut dinaikkan ke 0,7 cm."""
        rows = self._word_heights(lambda: self._manager().export_rekap_rab("word"))
        sig_heights = [h for sig, h in rows if sig and h is not None]

        # Satu-satunya baris bertinggi adalah ruang tanda tangan basah (1,5 cm);
        # sisanya harus tetap otomatis.
        self.assertNotIn(
            round(ROW_MIN_HEIGHT_CM, 2),
            [round(h, 2) for h in sig_heights],
            "lembar pengesahan ikut dinaikkan ke tinggi minimum",
        )

    # ---------- PDF ----------

    def _pdf_min_heights(self, export_call):
        from reportlab.lib.units import cm

        from detail_project.exports import pdf_exporter as pdf

        captured = []
        original = pdf.Table._calc

        def spy(table_self, avail_w, avail_h):
            original(table_self, avail_w, avail_h)
            heights = getattr(table_self, "_rowHeights", None) or []
            if len(heights) >= 3:
                captured.append(
                    (
                        getattr(table_self, "enforce_min_row_height", True),
                        min(heights) / cm,
                    )
                )

        pdf.Table._calc = spy
        try:
            export_call()
        finally:
            pdf.Table._calc = original
        return captured

    def test_pdf_data_tables_meet_the_default_minimum(self):
        caught = self._pdf_min_heights(
            lambda: self._manager().export_rekap_rab("pdf")
        )
        data = [h for enforced, h in caught if enforced]

        self.assertTrue(data, "tak ada tabel data tertangkap")
        self.assertGreaterEqual(min(data), ROW_MIN_HEIGHT_CM - 0.01)

    def test_pdf_tall_rows_are_not_squashed(self):
        """Ambang ini MINIMUM: baris yang isinya membungkus tetap lebih tinggi."""
        from reportlab.lib.units import cm

        from detail_project.exports import pdf_exporter as pdf

        tallest = []
        original = pdf.Table._calc

        def spy(table_self, avail_w, avail_h):
            original(table_self, avail_w, avail_h)
            heights = getattr(table_self, "_rowHeights", None) or []
            if heights:
                tallest.append(max(heights) / cm)

        pdf.Table._calc = spy
        try:
            self._manager().export_rincian_ahsp("pdf")
        finally:
            pdf.Table._calc = original

        self.assertGreater(
            max(tallest),
            ROW_MIN_HEIGHT_CM,
            "semua baris terpotong ke ambang -- ini tetap, bukan minimum",
        )
