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
