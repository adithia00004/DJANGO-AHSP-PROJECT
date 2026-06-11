import json
import tempfile
from pathlib import Path

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from referensi.services.import_repair import (
    coerce_koefisien,
    compute_block_status,
    validate_frontend_payload,
)
from referensi.views.import_views import _get_validation_results, export_from_frontend, repair_preflight


class ImportRepairServiceTests(TestCase):
    def test_wrapped_row_blocks_table(self):
        status = compute_block_status({
            "rows": [
                {"parent_code": "4.1.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
                {"parent_code": "4.1.1.1", "segment": "B", "uraian": "Semen", "satuan": "kg", "koefisien": "2"},
                {"parent_code": "4.1.1.1", "segment": "C", "uraian": "", "kode_ref": "Excavator", "satuan": "jam", "koefisien": "0.5"},
            ]
        })

        self.assertTrue(status["is_blocked"])
        self.assertIn("WARNING: Uraian Kosong (Wrapped Data)", status["blocked_reasons"])
        self.assertEqual(status["repair_candidates"][0]["confidence"], "high")

    def test_coerce_koefisien_rule(self):
        # Non-numeric coefficients become "0"; numeric ones are preserved as-is.
        self.assertEqual(coerce_koefisien("abc"), "0")
        self.assertEqual(coerce_koefisien(""), "0")
        self.assertEqual(coerce_koefisien("-"), "0")
        self.assertEqual(coerce_koefisien(None), "0")
        self.assertEqual(coerce_koefisien("0,5"), "0,5")
        self.assertEqual(coerce_koefisien("12"), "12")

    def test_nonnumeric_koefisien_does_not_block_table(self):
        # A non-numeric koefisien is assumed 0 -> passive warning, still exportable.
        status = compute_block_status({
            "rows": [
                {"parent_code": "5.5.5.5", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "abc"},
                {"parent_code": "5.5.5.5", "segment": "B", "uraian": "Semen", "satuan": "kg", "koefisien": "2"},
                {"parent_code": "5.5.5.5", "segment": "C", "uraian": "Alat", "satuan": "jam", "koefisien": "0,5"},
            ]
        })
        self.assertFalse(status["is_blocked"], status["blocked_reasons"])
        self.assertTrue(status["can_export"])
        self.assertTrue(any("non-numerik" in w for w in status["warnings"]))

    def test_missing_segment_is_passive_warning_not_blocked(self):
        # A labor-only AHSP item legitimately has no Bahan/Peralatan: it must
        # stay exportable (not blocked), only flagged with a passive warning.
        status = compute_block_status({
            "rows": [
                {"parent_code": "4.1.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
            ]
        })

        self.assertFalse(status["is_blocked"])
        self.assertTrue(status["can_export"])
        self.assertEqual(status["block_status"], "warning")
        self.assertEqual(status["blocked_reasons"], [])
        self.assertTrue(any("Bahan (BHN)" in w and "Peralatan (PR)" in w for w in status["warnings"]))

    def test_missing_segment_table_still_exports(self):
        summary = validate_frontend_payload([
            {"parent_code": "4.1.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
            {"parent_code": "4.1.1.1", "segment": "B", "uraian": "Semen", "satuan": "kg", "koefisien": "2"},
        ])

        self.assertEqual(summary["valid_parent_codes"], ["4.1.1.1"])
        self.assertEqual(summary["counts"]["skipped_tables"], 0)
        self.assertEqual(summary["counts"]["warning_tables"], 1)
        self.assertEqual(summary["warning_tables"][0]["parent_code"], "4.1.1.1")

    def test_frontend_payload_filters_whole_parent_table(self):
        summary = validate_frontend_payload([
            {"parent_code": "1.2.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
            {"parent_code": "1.2.1.1", "segment": "B", "uraian": "Semen", "satuan": "kg", "koefisien": "2"},
            {"parent_code": "1.2.1.1", "segment": "C", "uraian": "Alat", "satuan": "jam", "koefisien": "3"},
            {"parent_code": "4.1.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
            {"parent_code": "4.1.1.1", "segment": "B", "uraian": "", "kode_ref": "Batu belah", "satuan": "m3", "koefisien": "2"},
            {"parent_code": "4.1.1.1", "segment": "C", "uraian": "Alat", "satuan": "jam", "koefisien": "3"},
        ])

        self.assertEqual(summary["valid_parent_codes"], ["1.2.1.1"])
        self.assertEqual(summary["counts"]["skipped_tables"], 1)
        self.assertEqual({row["parent_code"] for row in summary["valid_rows"]}, {"1.2.1.1"})

    def test_shifted_numbered_row_blocks_table(self):
        status = compute_block_status({
            "rows": [
                {
                    "parent_code": "3.5.2.2.1",
                    "segment": "B",
                    "no": "",
                    "uraian": "1",
                    "kode_ref": "Plafon Serat Semen/GRC Tebal 4 mm Termasuk Alat Pasang",
                    "satuan": "m2",
                    "koefisien": "1.21",
                }
            ]
        })

        self.assertTrue(status["is_blocked"])
        self.assertIn("WARNING: Kolom Bergeser (No/Uraian/Kode)", status["blocked_reasons"])
        self.assertEqual(status["repair_candidates"][0]["confidence"], "high")

    def test_manual_lain_segment_is_valid_but_anomali_still_blocks(self):
        manual_lain = validate_frontend_payload([
            {"parent_code": "1.1.2.6", "segment": "LAIN", "uraian": "Sewa Lahan", "satuan": "m2", "koefisien": "1.0476"},
        ])

        self.assertEqual(manual_lain["valid_parent_codes"], ["1.1.2.6"])
        self.assertEqual(manual_lain["counts"]["skipped_tables"], 0)

        still_anomaly = validate_frontend_payload([
            {"parent_code": "1.1.2.6", "segment": "ANOMALI", "uraian": "Sewa Lahan", "satuan": "m2", "koefisien": "1.0476"},
        ])

        self.assertEqual(still_anomaly["valid_parent_codes"], [])
        self.assertEqual(still_anomaly["counts"]["skipped_tables"], 1)
        self.assertIn("Segmen tidak dikenal / ANOMALI", still_anomaly["skipped_tables"][0]["reasons"])


class ImportRepairValidationReportTests(TestCase):
    def test_get_validation_results_preserves_wrapped_warning_as_blocker(self):
        rows = [
            ["4.1.1.1 Pekerjaan Contoh", "OK"],
            ["4.1.1.1", "HEADER", "No", "Uraian", "Kode", "Satuan", "Koefisien", "Harga Satuan (Rp)"],
            ["4.1.1.1", "TK", "A", "Tenaga Kerja", "REDUNDANT: Segment Title"],
            ["4.1.1.1", "TK", "Pekerja", "L.01", "OH", "1", "OK"],
            ["4.1.1.1", "BHN", "B", "Bahan", "REDUNDANT: Segment Title"],
            ["4.1.1.1", "BHN", "Semen", "PC", "kg", "2", "OK"],
            ["4.1.1.1", "PR", "C", "Peralatan", "REDUNDANT: Segment Title"],
            ["4.1.1.1", "PR", "Excavator", "jam", "0.5", "WARNING: Uraian Kosong (Wrapped Data)"],
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "wrapped_validate.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        tables = [item for item in results if item.get("type") == "table_container"]
        self.assertEqual(len(tables), 1)
        self.assertTrue(tables[0]["is_blocked"])
        self.assertIn("WARNING: Uraian Kosong (Wrapped Data)", tables[0]["blocked_reasons"])

    def test_wide_fixed_format_empty_kode_is_not_a_shift(self):
        # Standard PDF->Excel conversion layout (11 fixed columns, trailing Status).
        # A Bahan item with an EMPTY Kode (col_4) is VALID -- it must be read
        # positionally and NOT be mis-shifted/blocked as "Kolom Bergeser".
        # Also: legend rows must not leak into a phantom "Unknown" table.
        N = None
        rows = [
            ["[ LEGENDA WARNA ]"],
            ["[MERAH/ABU]", "Baris ini AKAN DIBUANG di Mode Siap Impor"],
            ["3.1.1.1 Pemasangan 1 m2 Atap Genteng", N, N, N, N, N, N, N, N, N, "OK"],
            ["3.1.1.1", "HEADER", "No", "Uraian", "Kode", "Satuan", "Koefisien", N, "Harga", "Jumlah", "REDUNDANT: Header"],
            ["3.1.1.1", "TK", "A", "TENAGA KERJA", N, N, N, N, N, N, "REDUNDANT: Segment Title"],
            ["3.1.1.1", "TK", "1", "Pekerja", "L.01", "OH", "0,15", N, N, N, "OK"],
            ["3.1.1.1", "BHN", "B", "BAHAN", N, N, N, N, N, N, "REDUNDANT: Segment Title"],
            ["3.1.1.1", "BHN", "1", "Genteng Palentong", N, "buah", "25,00", N, N, N, "OK"],
            ["3.1.1.1", "PR", "C", "PERALATAN", N, N, N, N, N, N, "REDUNDANT: Segment Title"],
            ["3.1.1.1", "PR", "1", "Excavator", "E.01", "jam", "0,5", N, N, N, "OK"],
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "fixed_format.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        tables = [item for item in results if item.get("type") == "table_container"]
        self.assertEqual(len(tables), 1)
        t = tables[0]
        self.assertEqual(t["first_col"], "3.1.1.1")
        # Empty-Kode Bahan must NOT trigger a false "Kolom Bergeser" block.
        self.assertFalse(t["is_blocked"], t.get("blocked_reasons"))
        # No phantom "Unknown" table from legend rows.
        self.assertNotIn("Unknown", [x.get("first_col") for x in tables])
        # The Bahan row reads positionally: No=1, Uraian=text, Kode=empty.
        bhn = t["grouped_rows"]["BHN"][0]["original_row"]
        self.assertEqual(bhn["col_2"], "1")
        self.assertEqual(bhn["col_3"], "Genteng Palentong")
        self.assertEqual(bhn["col_4"], "-")

    def test_wide_columns_and_wrapped_continuation_are_normalized(self):
        N = None
        rows = [
            ["7.1.1.2 Paving block", N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, N, "OK"],
            ["7.1.1.2", "HEADER", "No", "Uraian", "Kode", "Satuan", "Koefisien", N, "Harga", "Jumlah", N, N, N, N, N, N, N, "REDUNDANT: Header"],
            ["7.1.1.2", "TK", N, "Tukang batu/tembok", N, N, "L.02", "OH", N, N, "0,100", N, N, N, N, N, N, "OK"],
            ["7.1.1.2", "BHN", N, N, "Paving block Tebal 6", N, N, "m2", N, N, "1,050", N, N, N, N, N, N, "OK"],
            ["7.1.1.2", "BHN", N, N, "cm f'c 25 MPa", N, N, N, N, N, N, N, N, N, N, N, N, "OK"],
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "wide_wrapped.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        tables = [item for item in results if item.get("type") == "table_container"]
        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertFalse(table["is_blocked"], table.get("blocked_reasons"))
        tk = table["grouped_rows"]["TK"][0]["original_row"]
        self.assertEqual(tk["col_3"], "Tukang batu/tembok")
        self.assertEqual(tk["col_4"], "L.02")
        bhn = table["grouped_rows"]["BHN"][0]["original_row"]
        self.assertEqual(bhn["col_3"], "Paving block Tebal 6 cm f'c 25 MPa")
        self.assertEqual(bhn["col_5"], "m2")
        self.assertEqual(bhn["col_6"], "1,050")

    def test_column_number_guide_row_is_discarded_not_blocking(self):
        # AHSP PDF tables print a "(1) (2) (3) (4) (5)" row under the header to
        # number each column. It must be discarded as noise -- otherwise it
        # leaks in as a phantom ANOMALI row and wrongly BLOCKS an otherwise
        # fully-valid AHSP (regression: 2.6.2.1 / 2.6.2.2). The cells are the
        # consecutive integer sequence 1,2,3,4,5(,6,7).
        N = None
        rows = [
            ["2.6.2.1 Pemancangan Tiang Pancang Kayu", N, N, N, N, N, N, N, N, N, "OK"],
            ["2.6.2.1", "HEADER", "No", "Uraian", "Kode", "Satuan", "Koefisien", N, "Harga", "Jumlah", "REDUNDANT: Header"],
            ["2.6.2.1", "ANOMALI", "1", "2", "3", "4", "5", N, "6", "7", "ANOMALI: Posisi baris tidak diketahui"],
            ["2.6.2.1", "TK", "1", "Pekerja", "L.01", "OJ", "0,0605", N, N, N, "OK"],
            ["2.6.2.1", "BHN", "1", "Alat sambung dolken", N, "buah", "0,2308", N, N, N, "OK"],
            ["2.6.2.1", "PR", "1", "Mini Pile Driver", N, "Jam", "0,0605", N, N, N, "OK"],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "enum_guide.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        tables = [item for item in results if item.get("type") == "table_container"]
        self.assertEqual(len(tables), 1)
        t = tables[0]
        # The enumeration row is gone -> no ANOMALI bucket, table not blocked.
        self.assertEqual(t["grouped_rows"]["ANOMALI"], [])
        self.assertFalse(t["is_anomaly"])
        self.assertFalse(t["is_blocked"], t.get("blocked_reasons"))
        self.assertTrue(t["can_export"])
        # Real item rows are untouched.
        self.assertEqual(len(t["grouped_rows"]["TK"]), 1)
        self.assertEqual(len(t["grouped_rows"]["BHN"]), 1)
        self.assertEqual(len(t["grouped_rows"]["PR"]), 1)

    def test_effective_status_is_single_source_of_truth(self):
        # One canonical tri-state per table (blocked/warning/valid) must drive
        # everything, and the nav parent must mirror its table exactly.
        N = None
        rows = [
            ["1.1.1.1 Valid lengkap", N, N, N, N, N, N, N, N, N, "OK"],
            ["1.1.1.1", "TK", "1", "Pekerja", "L.01", "OH", "0,1", N, N, N, "OK"],
            ["1.1.1.1", "BHN", "1", "Semen", N, "kg", "2", N, N, N, "OK"],
            ["1.1.1.1", "PR", "1", "Alat", "E.01", "jam", "0,5", N, N, N, "OK"],
            # Labor-only: missing BHN/PR is a SOFT warning -> exportable.
            ["2.2.2.2 Hanya tenaga kerja", N, N, N, N, N, N, N, N, N, "OK"],
            ["2.2.2.2", "TK", "1", "Pekerja", "L.01", "OH", "0,1", N, N, N, "OK"],
            # Genuine ANOMALI row -> hard block.
            ["3.3.3.3 Ada anomali", N, N, N, N, N, N, N, N, N, "OK"],
            ["3.3.3.3", "TK", "1", "Pekerja", "L.01", "OH", "0,1", N, N, N, "OK"],
            ["3.3.3.3", "ANOMALI", "9", "Baris aneh", "X", "??", "abc", N, N, N, "ANOMALI"],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "effective.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        tables = {t["first_col"]: t for t in results if t.get("type") == "table_container"}
        parents = {
            str(r["first_col"]).split(" ")[0]: r
            for r in results if r.get("type") == "hierarchy_parent"
        }
        self.assertEqual(tables["1.1.1.1"]["effective_status"], "valid")
        self.assertEqual(tables["2.2.2.2"]["effective_status"], "warning")
        self.assertEqual(tables["3.3.3.3"]["effective_status"], "blocked")
        # Invariant: effective_status == 'blocked' iff is_blocked.
        for t in tables.values():
            self.assertEqual(t["effective_status"] == "blocked", bool(t["is_blocked"]))
        # Nav parent mirrors its table's effective status (no independent drift).
        for code, t in tables.items():
            self.assertEqual(parents[code]["child_effective_status"], t["effective_status"])

    def test_nonnumeric_koefisien_coerced_to_zero_in_report(self):
        # End-to-end through the parser: a garbage koefisien is shown as "0",
        # the table is NOT blocked, and a passive warning explains it.
        N = None
        rows = [
            ["5.5.5.5 Item koef rusak", N, N, N, N, N, N, N, N, N, "OK"],
            ["5.5.5.5", "TK", "1", "Pekerja", "L.01", "OH", "abc", N, N, N, "OK"],
            ["5.5.5.5", "BHN", "1", "Semen", N, "kg", "2", N, N, N, "OK"],
            ["5.5.5.5", "PR", "1", "Alat", "E.01", "jam", "0,5", N, N, N, "OK"],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "koef.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        t = [item for item in results if item.get("type") == "table_container"][0]
        self.assertFalse(t["is_blocked"], t.get("blocked_reasons"))
        self.assertEqual(t["effective_status"], "warning")
        self.assertTrue(any("non-numerik" in w for w in t["warnings"]))
        # The displayed/exported coefficient is coerced to "0".
        tk = t["grouped_rows"]["TK"][0]["original_row"]
        self.assertEqual(tk["col_6"], "0")

    def test_real_numbered_item_row_is_not_mistaken_for_guide(self):
        # Guard against over-matching: a genuine item whose No=1 must survive
        # (its Uraian/Satuan are text, not a 2,3,4,5 sequence).
        N = None
        rows = [
            ["2.6.2.3 Pekerjaan Contoh", N, N, N, N, N, N, N, N, N, "OK"],
            ["2.6.2.3", "TK", "1", "Pekerja", "L.01", "OH", "0,1", N, N, N, "OK"],
            ["2.6.2.3", "BHN", "1", "Semen", N, "kg", "2", N, N, N, "OK"],
            ["2.6.2.3", "PR", "1", "Alat", "E.01", "jam", "0,5", N, N, N, "OK"],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "real_numbered.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        t = [item for item in results if item.get("type") == "table_container"][0]
        self.assertEqual(len(t["grouped_rows"]["TK"]), 1)
        self.assertEqual(t["grouped_rows"]["TK"][0]["original_row"]["col_3"], "Pekerja")

    def test_three_segment_code_is_parent_when_it_has_data(self):
        # AHSP 2026 uses 3-segment codes BOTH as folders (3.1.1, bare header) and
        # as real work items (3.2.1, with TK/BHN/PR). Disambiguate by data:
        #  - 3.1.1 (no data)   -> sub-klasifikasi folder
        #  - 3.2.1 (with data) -> AHSP parent (data captured, not duplicated)
        N = None
        rows = [
            ["3.1.1 ATAP GENTENG (deskripsi panjang sub-bab)", N, N, N, N, N, N, N, N, N, "OK"],
            ["3.1.1.1 Pemasangan Genteng", N, N, N, N, N, N, N, N, N, "OK"],
            ["3.1.1.1", "TK", "1", "Pekerja", "L.01", "OH", "0,1", N, N, N, "OK"],
            ["3.1.1.1", "BHN", "1", "Genteng", N, "buah", "25", N, N, N, "OK"],
            ["3.1.1.1", "PR", "1", "Alat", "E.01", "jam", "0,5", N, N, N, "OK"],
            ["3.2.1 Pemasangan 1 m2 Lembaran Insulasi Atap", N, N, N, N, N, N, N, N, N, "OK"],
            ["3.2.1", "TK", "1", "Pekerja", "L.01", "OH", "0,2", N, N, N, "OK"],
            ["3.2.1", "BHN", "1", "Insulasi", "B.01", "m2", "1,05", N, N, N, "OK"],
            ["3.2.1", "PR", "1", "Perancah", "E.02", "set", "0,1", N, N, N, "OK"],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "three_seg.xlsx"
            pd.DataFrame(rows).to_excel(path, index=False, header=False)
            results, _, _ = _get_validation_results(str(path))

        tables = {item["first_col"]: item for item in results if item.get("type") == "table_container"}
        subclasses = [
            str(r.get("first_col", "")).split(" ")[0]
            for r in results if r.get("type") == "hierarchy_subclass"
        ]
        # 3.2.1 must be an AHSP parent table with its data captured.
        self.assertIn("3.2.1", tables)
        segs = {k: len(v) for k, v in tables["3.2.1"]["grouped_rows"].items()}
        self.assertEqual((segs["TK"], segs["BHN"], segs["PR"]), (1, 1, 1))
        self.assertFalse(tables["3.2.1"]["is_blocked"])
        # 3.1.1 (no data of its own) stays a sub-klasifikasi folder, not a table.
        self.assertIn("3.1.1", subclasses)
        self.assertNotIn("3.1.1", tables)
        # No duplicate "3.2.1" hierarchy entries (the old bug).
        parents_321 = [
            r for r in results
            if r.get("type") in ("hierarchy_parent", "hierarchy_subclass")
            and str(r.get("first_col", "")).split(" ")[0] == "3.2.1"
        ]
        self.assertEqual(len(parents_321), 1)


class ImportRepairExportTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="repair-admin",
            email="repair-admin@example.com",
            password="Secret123!",
        )
        self.factory = RequestFactory()

    def _post_json(self, view, payload):
        request = self.factory.post(
            reverse(f"referensi:{view.__name__}"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.user
        return view(request)

    def test_preflight_and_export_skip_blocked_parent(self):
        payload = {
            "type": "valid",
            "hierarchy": [
                {"code": "1.2.1", "title": "Sub klasifikasi"},
                {"code": "1.2.1.1", "title": "Valid parent"},
                {"code": "4.1.1.1", "title": "Blocked parent"},
            ],
            "data_rows": [
                {"parent_code": "1.2.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
                {"parent_code": "1.2.1.1", "segment": "B", "uraian": "Semen", "satuan": "kg", "koefisien": "2"},
                {"parent_code": "1.2.1.1", "segment": "C", "uraian": "Alat", "satuan": "jam", "koefisien": "3"},
                {"parent_code": "4.1.1.1", "segment": "A", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"},
                {"parent_code": "4.1.1.1", "segment": "B", "uraian": "", "kode_ref": "Batu belah", "satuan": "m3", "koefisien": "2"},
                {"parent_code": "4.1.1.1", "segment": "C", "uraian": "Alat", "satuan": "jam", "koefisien": "3"},
            ],
        }

        preflight = self._post_json(repair_preflight, payload)
        self.assertEqual(preflight.status_code, 200, getattr(preflight, "url", ""))
        self.assertEqual(json.loads(preflight.content)["valid_parent_codes"], ["1.2.1.1"])

        response = self._post_json(export_from_frontend, payload)
        self.assertEqual(response.status_code, 200, getattr(response, "url", ""))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "export.xlsx"
            path.write_bytes(response.content)
            meta = pd.read_excel(path, sheet_name="Meta")
            data = pd.read_excel(path, sheet_name="Data")

        self.assertIn("ahsp-interchange-1.0", set(meta["value"].dropna().astype(str)))
        self.assertEqual(set(data["kode_ahsp"].tolist()), {"1.2.1.1"})
        self.assertEqual(set(data["nama_ahsp"].tolist()), {"Valid parent"})
