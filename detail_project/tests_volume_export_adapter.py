import re
from decimal import Decimal
from io import BytesIO
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from detail_project.exports.excel_exporter import OPENPYXL_AVAILABLE
from detail_project.exports.export_manager import ExportManager
from detail_project.exports.volume_pekerjaan_adapter import VolumePekerjaanAdapter
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    ProjectComputedParameter,
    ProjectParameter,
    SubKlasifikasi,
    VolumeFormulaState,
    VolumePekerjaan,
)
from detail_project.services import DeepCopyService

if OPENPYXL_AVAILABLE:
    from openpyxl import load_workbook


class VolumeExportAdapterHardeningTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="volume_export_adapter_user",
            email="volume-export-adapter@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(owner=self.owner, nama="Volume Export Adapter")

    def _create_one_pekerjaan(self):
        klas = Klasifikasi.objects.create(project=self.project, name="Klasifikasi A")
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="Sub A")
        pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001",
            snapshot_uraian="Pekerjaan Uji",
            snapshot_satuan="m3",
        )
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pekerjaan, quantity="10")
        return pekerjaan

    def test_adapter_normalizes_parameter_payload_and_keeps_label_formula(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            label="Panjang Dinding",
            value="7",
        )
        pekerjaan = self._create_one_pekerjaan()
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=bp_1 * 2",
            is_fx=True,
        )

        adapter = VolumePekerjaanAdapter(
            self.project,
            parameters={"BP_1": {"value": 12}},
        )
        data = adapter.get_export_data()

        param_rows = data["pages"][1]["table_data"]["rows"]
        headers = data["pages"][1]["table_data"]["headers"]
        self.assertEqual(headers, ["No", "Nama Parameter", "Expression", "Nilai", "Satuan"])

        # Row: [No, Nama, Expression, Nilai, Satuan]. A base parameter shows the
        # canonical BACKEND value (7) — never the request payload (12) — and has no
        # expression.
        bp_rows = [row for row in param_rows if len(row) >= 5 and row[1] == "Panjang Dinding"]
        self.assertEqual(len(bp_rows), 1)
        self.assertEqual(bp_rows[0][2], "-")                          # Expression
        self.assertEqual(Decimal(str(bp_rows[0][3])), Decimal("7"))   # Nilai (backend, not 12)
        self.assertEqual(data["pages"][1]["table_data"]["param_codes"], ["bp_1"])

        volume_rows = data["pages"][0]["table_data"]["rows"]
        item_rows = [row for row in volume_rows if len(row) >= 3 and row[0] == "1"]
        self.assertEqual(len(item_rows), 1)
        self.assertIn("Panjang Dinding", item_rows[0][2])
        self.assertNotIn("bp_1", item_rows[0][2].lower())

        row_formulas = data["pages"][0]["row_formulas"]
        row_pekerjaan_ids = data["pages"][0]["row_pekerjaan_ids"]
        self.assertEqual(len(row_formulas), len(volume_rows))
        self.assertEqual(len(row_pekerjaan_ids), len(volume_rows))
        item_row_idx = next(idx for idx, row in enumerate(volume_rows) if len(row) >= 3 and row[0] == "1")
        self.assertEqual(row_formulas[item_row_idx], "=bp_1 * 2")
        self.assertEqual(row_pekerjaan_ids[item_row_idx], pekerjaan.id)

    def test_adapter_exposes_computed_parameter_formula_metadata(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            label="Panjang",
            value="7",
        )
        ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_1",
            label="Luas",
            expression="bp_1 * 2",
        )
        pekerjaan = self._create_one_pekerjaan()
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=cp_1 + bp_1",
            is_fx=True,
        )

        data = VolumePekerjaanAdapter(self.project).get_export_data()
        param_table = data["pages"][1]["table_data"]
        rows = param_table["rows"]
        codes = param_table["param_codes"]
        self.assertEqual(codes, ["bp_1", "cp_1"])

        # Row: [No, Nama, Expression, Nilai, Satuan]. Base = numeric Nilai, no
        # expression. Computed = humanized expression text + Nilai '-' (its value is
        # not canonical backend data; never 0, never a live formula).
        by_label = {row[1]: row for row in rows}
        self.assertEqual(by_label["Panjang"][2], "-")
        self.assertEqual(Decimal(str(by_label["Panjang"][3])), Decimal("7"))
        self.assertIn("Panjang", by_label["Luas"][2])   # cp_1 = bp_1 * 2, humanized
        self.assertEqual(by_label["Luas"][3], "-")

    @skipUnless(OPENPYXL_AVAILABLE, "openpyxl is required for XLSX export test")
    def test_xlsx_volume_column_is_canonical_backend_number(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            label="Panjang Dinding",
            value="7",
        )
        pekerjaan = self._create_one_pekerjaan()  # VolumePekerjaan.quantity = 10
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=bp_1 * 2",
            is_fx=True,
        )

        manager = ExportManager(self.project)
        response = manager.export_volume_pekerjaan("xlsx", parameters={"bp_1": 12})
        wb = load_workbook(BytesIO(response.content), data_only=False)

        self.assertIn("Parameters", wb.sheetnames)
        self.assertIn("Volume Pekerjaan", wb.sheetnames)

        ws_volume = wb["Volume Pekerjaan"]
        item_row = None
        for r in range(1, ws_volume.max_row + 1):
            if str(ws_volume.cell(row=r, column=1).value or "").strip() == "1":
                item_row = r
                break
        self.assertIsNotNone(item_row, "Row item nomor 1 tidak ditemukan pada sheet Volume Pekerjaan")

        # WP Export: Volume is the canonical stored quantity (10) as a real number,
        # never a live =Parameters!.. formula that Excel could recompute.
        volume_cell = ws_volume.cell(row=item_row, column=5)
        self.assertEqual(volume_cell.data_type, "n")
        self.assertAlmostEqual(float(volume_cell.value), 10.0, places=3)
        self.assertEqual(volume_cell.number_format, "#,##0.000")

        # The Formula column stays as text provenance (not a live formula).
        formula_cell = ws_volume.cell(row=item_row, column=3)
        self.assertNotEqual(formula_cell.data_type, "f")

    @skipUnless(OPENPYXL_AVAILABLE, "openpyxl is required for XLSX export test")
    def test_xlsx_computed_parameter_is_text_not_live_formula(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            label="Panjang",
            value="7",
        )
        ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_1",
            label="Luas",
            expression="bp_1 * 2",
        )
        pekerjaan = self._create_one_pekerjaan()
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=cp_1 + bp_1",
            is_fx=True,
        )

        manager = ExportManager(self.project)
        response = manager.export_volume_pekerjaan("xlsx")
        wb = load_workbook(BytesIO(response.content), data_only=False)
        ws_params = wb["Parameters"]
        ws_volume = wb["Volume Pekerjaan"]

        # Layout: col 2 = Nama, col 3 = Expression, col 4 = Nilai.
        cp_row = None
        for r in range(1, ws_params.max_row + 1):
            if str(ws_params.cell(row=r, column=2).value or "").strip() == "Luas":
                cp_row = r
        self.assertIsNotNone(cp_row, "Computed parameter row tidak ditemukan")

        # Computed param: Nilai is '-' (no canonical value; never 0, never a formula);
        # the Expression column holds the humanized formula text.
        nilai_cell = ws_params.cell(row=cp_row, column=4)
        self.assertEqual(nilai_cell.value, "-")
        self.assertNotEqual(nilai_cell.data_type, "f")
        self.assertNotEqual(ws_params.cell(row=cp_row, column=3).data_type, "f")

        # Gate: not one cell in either sheet is a live formula.
        for ws in (ws_params, ws_volume):
            for row in ws.iter_rows():
                for cell in row:
                    self.assertNotEqual(
                        cell.data_type, "f",
                        f"{ws.title}!{cell.coordinate} is a formula: {cell.value!r}",
                    )


class DeepCopyVolumeFormulaStateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="deep_copy_formula_state_user",
            email="deep-copy-formula-state@example.com",
            password="Secret123!",
        )
        self.source = Project.objects.create(owner=self.owner, nama="Source Project Formula State")

    def test_copy_project_also_copies_and_remaps_volume_formula_state(self):
        ProjectParameter.objects.create(
            project=self.source,
            name="bp_10",
            label="Panjang",
            value="10",
        )
        ProjectComputedParameter.objects.create(
            project=self.source,
            name="cp_10",
            label="Luas",
            expression="=bp_10 * 2",
        )

        klas = Klasifikasi.objects.create(project=self.source, name="Klasifikasi")
        sub = SubKlasifikasi.objects.create(project=self.source, klasifikasi=klas, name="Sub")
        pekerjaan = Pekerjaan.objects.create(
            project=self.source,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001",
            snapshot_uraian="Pekerjaan Sumber",
            snapshot_satuan="m3",
        )
        VolumePekerjaan.objects.create(project=self.source, pekerjaan=pekerjaan, quantity="1")
        VolumeFormulaState.objects.create(
            project=self.source,
            pekerjaan=pekerjaan,
            raw="=bp_10 + cp_10",
            is_fx=True,
        )

        copied = DeepCopyService(self.source).copy(
            new_owner=self.owner,
            new_name="Copied Project Formula State",
            copy_jadwal=False,
        )

        copied_formula = VolumeFormulaState.objects.get(project=copied)
        copied_raw = copied_formula.raw or ""

        self.assertNotIn("bp_10", copied_raw.lower())
        self.assertNotIn("cp_10", copied_raw.lower())
        self.assertRegex(copied_raw.lower(), r"bp_[1-9][0-9]*")
        self.assertRegex(copied_raw.lower(), r"cp_[1-9][0-9]*")

        copied_param_names = set(
            ProjectParameter.objects.filter(project=copied).values_list("name", flat=True)
        )
        copied_computed_names = set(
            ProjectComputedParameter.objects.filter(project=copied).values_list("name", flat=True)
        )
        self.assertTrue(all(re.match(r"^bp_[1-9][0-9]*$", name) for name in copied_param_names))
        self.assertTrue(all(re.match(r"^cp_[1-9][0-9]*$", name) for name in copied_computed_names))
