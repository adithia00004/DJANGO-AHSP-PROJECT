"""WP Export — "dataset backend = nilai sel Excel" parity contract.

Owner decision (2026-06-20, all Option A): Excel is a *report* of the backend
SSOT, not a parallel calc engine. Money/quantity cells must therefore be real
Excel numbers equal to the backend canonical value (Decimal), at the agreed
precision — never a locale string and never a live formula.

This suite renders a small fixture through the real adapter+exporter and reads
the workbook back with openpyxl. One report per test class; add reports as each
slice lands (K2 -> K3 -> precision).
"""
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase

from openpyxl import load_workbook

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    HargaItemProject,
    DetailAHSPProject,
    DetailAHSPExpanded,
    VolumePekerjaan,
)
from detail_project.models import ProjectParameter, ProjectComputedParameter, VolumeFormulaState
from detail_project.exports.export_manager import ExportManager


class _RekapFixtureMixin:
    """Minimal project: 1 pekerjaan, koef 2 x harga 100 = E 200; +10% markup =>
    G 220; volume 3 => total 660."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="wp-export-parity-owner", password="not-used",
        )
        self.project = Project.objects.create(owner=self.owner, nama="Parity Project")
        klas = Klasifikasi.objects.create(project=self.project, name="Klas A", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="Sub A", ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P-001", snapshot_uraian="Pekerjaan parity", snapshot_satuan="m2",
            ordering_index=1,
        )
        item = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-001", kategori="BHN",
            uraian="Bahan parity", satuan="kg", harga_satuan=Decimal("100.00"),
        )
        source = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, harga_item=item,
            kategori="BHN", kode="BHN-001", uraian="Bahan parity", satuan="kg",
            koefisien=Decimal("2.000000"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, source_detail=source,
            harga_item=item, kategori="BHN", kode="BHN-001", uraian="Bahan parity",
            satuan="kg", koefisien=Decimal("2.000000"), expansion_depth=0,
        )
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, quantity=Decimal("3.000"),
        )

    def _render_xlsx(self, response):
        return load_workbook(BytesIO(response.content))

    def _find_row(self, ws, col1_value):
        for row in ws.iter_rows():
            if row and row[0].value == col1_value:
                return row
        return None


class RekapRABExcelParityTests(_RekapFixtureMixin, TestCase):
    def test_money_cells_are_numbers_equal_to_backend(self):
        resp = ExportManager(self.project, self.owner).export_rekap_rab("xlsx")
        wb = self._render_xlsx(resp)
        ws = wb.worksheets[0]  # page 1 = RAB table
        row = self._find_row(ws, "Pekerjaan parity")
        self.assertIsNotNone(row, "pekerjaan row not found in RAB sheet")

        volume_cell, harga_cell, jumlah_cell = row[3], row[4], row[5]

        # Real numbers, not locale strings / formulas.
        for cell in (volume_cell, harga_cell, jumlah_cell):
            self.assertIsInstance(
                cell.value, (int, float),
                f"cell {cell.coordinate}={cell.value!r} is not a number",
            )
            self.assertFalse(str(cell.value).startswith("="), "cell holds a formula")

        # Values equal the backend canonical numbers (G=220, total=660, vol=3).
        self.assertAlmostEqual(float(volume_cell.value), 3.0, places=3)
        self.assertAlmostEqual(float(harga_cell.value), 220.0, places=2)
        self.assertAlmostEqual(float(jumlah_cell.value), 660.0, places=2)

        # Agreed precision (2 dp money, 3 dp volume).
        self.assertEqual(harga_cell.number_format, "#,##0.00")
        self.assertEqual(jumlah_cell.number_format, "#,##0.00")
        self.assertEqual(volume_cell.number_format, "#,##0.000")


class RekapRABWordParityTests(_RekapFixtureMixin, TestCase):
    """The text exporters (here: Word) must render the canonical Decimal as a
    properly formatted id-ID 2-dp string at their boundary — never the raw
    str(Decimal) '220.00' and never a live formula."""

    def test_word_cells_are_formatted_idid_strings(self):
        from docx import Document

        resp = ExportManager(self.project, self.owner).export_rekap_rab("word")
        doc = Document(BytesIO(resp.content))
        texts = [
            cell.text
            for table in doc.tables
            for row in table.rows
            for cell in row.cells
        ]
        # G=220, total=660 rendered id-ID with 2 decimals.
        self.assertIn("220,00", texts)
        self.assertIn("660,00", texts)
        # The raw Decimal repr must not leak through.
        self.assertNotIn("220.00", texts)
        self.assertNotIn("660.00", texts)


class RekapKebutuhanExcelParityTests(_RekapFixtureMixin, TestCase):
    """Same fixture: volume 3 x koef 2 => kebutuhan qty 6; harga 100; total 600.
    Qty is a 3-dp number, money is 2-dp, and the grand total reconciles."""

    def test_item_and_grand_total_are_numbers(self):
        resp = ExportManager(self.project, self.owner).export_rekap_kebutuhan("xlsx")
        ws = load_workbook(BytesIO(resp.content)).worksheets[0]

        # Item row: [No, Kode, Uraian, Satuan, Qty, Harga, Total]
        item_row = None
        for row in ws.iter_rows():
            if len(row) >= 7 and row[1].value == "BHN-001":
                item_row = row
                break
        self.assertIsNotNone(item_row, "kebutuhan item row not found")

        qty_cell, harga_cell, total_cell = item_row[4], item_row[5], item_row[6]
        for cell in (qty_cell, harga_cell, total_cell):
            self.assertIsInstance(
                cell.value, (int, float), f"{cell.coordinate}={cell.value!r} not numeric",
            )
        self.assertAlmostEqual(float(qty_cell.value), 6.0, places=3)
        self.assertAlmostEqual(float(harga_cell.value), 100.0, places=2)
        self.assertAlmostEqual(float(total_cell.value), 600.0, places=2)
        self.assertEqual(qty_cell.number_format, "#,##0.000")
        self.assertEqual(harga_cell.number_format, "#,##0.00")
        self.assertEqual(total_cell.number_format, "#,##0.00")

        # Grand Total footer reconciles to the sum of item totals, as a number.
        grand_cell = None
        for row in ws.iter_rows():
            if row and row[0].value == "Grand Total Harga":
                grand_cell = row[1]
                break
        if grand_cell is not None:
            self.assertIsInstance(grand_cell.value, (int, float))
            self.assertAlmostEqual(float(grand_cell.value), 600.0, places=2)
            self.assertEqual(grand_cell.number_format, "#,##0.00")


class RincianAHSPExcelParityTests(_RekapFixtureMixin, TestCase):
    """Component koef 2 x harga 100 => jumlah 200; E 200, +10% => F 20, G 220.
    Cells must be real numbers (no live =E*F / =SUM / cross-sheet formula)."""

    def test_no_formula_cells_and_values_match_backend(self):
        resp = ExportManager(self.project, self.owner).export_rincian_ahsp("xlsx")
        wb = load_workbook(BytesIO(resp.content))

        # Gate: not a single cell may be a live formula (data_type 'f').
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    self.assertNotEqual(
                        cell.data_type, "f",
                        f"{ws.title}!{cell.coordinate} is a formula: {cell.value!r}",
                    )

        rincian = wb["Rincian"]
        # Detail row: [No, Uraian, Kode, Satuan, Koef, Harga, Jumlah]
        comp = None
        for row in rincian.iter_rows():
            if len(row) >= 7 and row[2].value == "BHN-001":
                comp = row
                break
        self.assertIsNotNone(comp, "component row not found")
        koef, harga, jumlah = comp[4], comp[5], comp[6]
        for cell in (koef, harga, jumlah):
            self.assertIsInstance(cell.value, (int, float))
        self.assertAlmostEqual(float(koef.value), 2.0, places=6)
        self.assertAlmostEqual(float(harga.value), 100.0, places=2)
        self.assertAlmostEqual(float(jumlah.value), 200.0, places=2)
        self.assertEqual(koef.number_format, "0.000000")
        self.assertEqual(harga.number_format, "#,##0.00")
        self.assertEqual(jumlah.number_format, "#,##0.00")

        # Rekap sheet row for the pekerjaan: [No, Kode, Uraian, E, F, G]
        rekap = wb["Rekap"]
        pek = None
        for row in rekap.iter_rows():
            if len(row) >= 6 and row[1].value == "P-001":
                pek = row
                break
        self.assertIsNotNone(pek, "pekerjaan recap row not found")
        e_cell, f_cell, g_cell = pek[3], pek[4], pek[5]
        for cell in (e_cell, f_cell, g_cell):
            self.assertIsInstance(cell.value, (int, float))
        self.assertAlmostEqual(float(e_cell.value), 200.0, places=2)
        self.assertAlmostEqual(float(f_cell.value), 20.0, places=2)
        self.assertAlmostEqual(float(g_cell.value), 220.0, places=2)

    def test_word_rincian_uses_materialized_idid_strings(self):
        from docx import Document

        resp = ExportManager(self.project, self.owner).export_rincian_ahsp("word")
        doc = Document(BytesIO(resp.content))
        texts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    texts.append(cell.text)
        blob = "\n".join(texts)
        # G=220 rendered id-ID; the raw str(Decimal) must not leak.
        self.assertIn("220,00", blob)
        self.assertNotIn("220.00", blob)


class VolumeExportParityTests(TestCase):
    """Volume value = canonical stored quantity (numeric); base param = backend
    value (numeric); computed param = expression text + Nilai '-'; no live formula.
    Verifies the PDF/Word boundary (materialize) for the Volume pages structure."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="wp-volume-parity-owner", password="not-used",
        )
        self.project = Project.objects.create(owner=self.owner, nama="Volume Parity")
        klas = Klasifikasi.objects.create(project=self.project, name="Klas A", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="Sub A", ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P-001", snapshot_uraian="Pekerjaan volume", snapshot_satuan="m3",
            ordering_index=1,
        )
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, quantity=Decimal("125.500"),
        )
        ProjectParameter.objects.create(
            project=self.project, name="bp_1", label="Panjang", value=Decimal("7"),
        )
        ProjectComputedParameter.objects.create(
            project=self.project, name="cp_1", label="Luas", expression="bp_1 * 2",
        )
        VolumeFormulaState.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, raw="=cp_1 + bp_1", is_fx=True,
        )

    def test_word_volume_and_params_are_materialized_numbers(self):
        from docx import Document

        resp = ExportManager(self.project, self.owner).export_volume_pekerjaan("word")
        doc = Document(BytesIO(resp.content))
        blob = "\n".join(
            [p.text for p in doc.paragraphs]
            + [c.text for t in doc.tables for r in t.rows for c in r.cells]
        )
        # Canonical volume 125.5 -> id-ID 3 dp; raw str(Decimal) must not leak.
        self.assertIn("125,500", blob)
        self.assertNotIn("125.500", blob)
        # Base param backend value present (7 -> "7,00"); computed Nilai is "-".
        self.assertIn("7,00", blob)


class HargaItemsExcelParityTests(TestCase):
    """Three USED price items: one priced, one NULL (not filled), one explicit 0.00.
    The Excel price cell must be a real 2-dp number for priced/zero, and a distinct
    '-' marker for NULL (D-HI-01: NULL must never collapse into 0.00)."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="wp-harga-parity-owner", password="not-used",
        )
        self.project = Project.objects.create(owner=self.owner, nama="Harga Parity")
        klas = Klasifikasi.objects.create(project=self.project, name="Klas A", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="Sub A", ordering_index=1,
        )
        pekerjaan = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P-001", snapshot_uraian="Pekerjaan harga", snapshot_satuan="m2",
            ordering_index=1,
        )
        # kode, harga_satuan
        specs = [
            ("BHN-PRICED", Decimal("1500.00")),
            ("BHN-NULLED", None),
            ("BHN-ZEROED", Decimal("0.00")),
        ]
        for kode, harga in specs:
            item = HargaItemProject.objects.create(
                project=self.project, kode_item=kode, kategori="BHN",
                uraian=f"Bahan {kode}", satuan="kg", harga_satuan=harga,
            )
            source = DetailAHSPProject.objects.create(
                project=self.project, pekerjaan=pekerjaan, harga_item=item,
                kategori="BHN", kode=kode, uraian=f"Bahan {kode}", satuan="kg",
                koefisien=Decimal("1.000000"),
            )
            DetailAHSPExpanded.objects.create(
                project=self.project, pekerjaan=pekerjaan, source_detail=source,
                harga_item=item, kategori="BHN", kode=kode, uraian=f"Bahan {kode}",
                satuan="kg", koefisien=Decimal("1.000000"), expansion_depth=0,
            )

    def _harga_cell(self, ws, kode):
        for row in ws.iter_rows():
            if len(row) >= 5 and row[1].value == kode:
                return row[4]
        return None

    def test_price_cells_numeric_and_null_stays_distinct(self):
        resp = ExportManager(self.project, self.owner).export_harga_items("xlsx")
        ws = load_workbook(BytesIO(resp.content)).worksheets[0]

        priced = self._harga_cell(ws, "BHN-PRICED")
        nulled = self._harga_cell(ws, "BHN-NULLED")
        zeroed = self._harga_cell(ws, "BHN-ZEROED")
        for cell, kode in ((priced, "PRICED"), (nulled, "NULLED"), (zeroed, "ZEROED")):
            self.assertIsNotNone(cell, f"row {kode} not found")

        # Priced + explicit zero are real numbers at 2 dp.
        self.assertIsInstance(priced.value, (int, float))
        self.assertAlmostEqual(float(priced.value), 1500.0, places=2)
        self.assertEqual(priced.number_format, "#,##0.00")

        self.assertIsInstance(zeroed.value, (int, float))
        self.assertAlmostEqual(float(zeroed.value), 0.0, places=2)

        # NULL stays a distinct text marker — never a numeric 0.
        self.assertEqual(nulled.value, "-")
        self.assertNotEqual(nulled.value, zeroed.value)
