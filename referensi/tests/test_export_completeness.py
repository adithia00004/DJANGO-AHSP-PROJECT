"""Export must not truncate: tables not rendered (DOM-limited) are supplied
server-side, while Edit Mode changes on rendered tables are preserved."""

import json
import os
from io import BytesIO

import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _block(code, nama):
    N = None
    return [
        [f"{code} {nama}", N, N, N, N, N, N, N, N, N, "OK"],
        [code, "TK", "1", "Pekerja", "L.01", "OH", "0,1", N, N, N, "OK"],
        [code, "BHN", "1", "Semen", N, "kg", "2", N, N, N, "OK"],
        [code, "PR", "1", "Alat", "E.01", "jam", "0,5", N, N, N, "OK"],
    ]


class ExportCompletenessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="export-admin", email="export-admin@example.com", password="Secret123!",
        )
        self.client.force_login(self.user)

    def test_export_supplements_unrendered_tables_and_keeps_edits(self):
        rows = _block("1.1.1.1", "Judul A") + _block("2.2.2.2", "Judul B") + _block("3.3.3.3", "Judul C")
        buf = BytesIO()
        pd.DataFrame(rows).to_excel(buf, sheet_name="Data", index=False, header=False)
        buf.seek(0)
        upload = SimpleUploadedFile("validated.xlsx", buf.read(), content_type=XLSX)

        resp = self.client.post(reverse("referensi:import_validate"), {"excel_file": [upload]})
        self.assertEqual(resp.status_code, 302)
        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        # GET the report -> stores validated_excel_path in the session.
        self.assertEqual(self.client.get(reverse("referensi:import_validate_report", args=[file_id])).status_code, 200)

        # Simulate a TRUNCATED DOM: only ONE table is "rendered", and it was edited.
        payload = {
            "type": "valid",
            "hierarchy": [{"code": "1.1.1.1", "title": "Judul A"}],
            "data_rows": [
                {"parent_code": "1.1.1.1", "segment": "A", "no": "1",
                 "uraian": "EDITED Pekerja", "kode_ref": "L.01", "satuan": "OH", "koefisien": "9.99"},
            ],
        }
        ex = self.client.post(
            reverse("referensi:export_from_frontend"),
            data=json.dumps(payload), content_type="application/json",
        )
        self.assertEqual(ex.status_code, 200)

        df = pd.read_excel(BytesIO(ex.content), sheet_name="Data")
        exported = set(df["kode_ahsp"].dropna().astype(str))
        # All three tables present, not just the one in the DOM.
        self.assertEqual(exported, {"1.1.1.1", "2.2.2.2", "3.3.3.3"})

        # The DOM edit is preserved for the rendered table.
        edited = df[(df["kode_ahsp"].astype(str) == "1.1.1.1") & (df["segmen"] == "A")]
        self.assertIn("EDITED Pekerja", set(edited["uraian"].astype(str)))

        # Server-supplied tables keep their real data + titles.
        b = df[df["kode_ahsp"].astype(str) == "2.2.2.2"]
        self.assertEqual(set(b["nama_ahsp"].astype(str)), {"Judul B"})
        self.assertIn("Semen", set(b["uraian"].astype(str)))

    def test_report_paginates_and_export_stays_complete(self):
        # 130 AHSP tables -> >250 result entries -> multiple pages.
        rows = []
        codes = [f"9.{i}.1.1" for i in range(1, 131)]
        for i, code in enumerate(codes, 1):
            rows.append([f"{code} Judul {i}"])
            rows.append([code, "TK", "1", "Pekerja", "L.01", "OH", "0,1"])
        buf = BytesIO()
        pd.DataFrame(rows).to_excel(buf, sheet_name="Data", index=False, header=False)
        buf.seek(0)
        upload = SimpleUploadedFile("big.xlsx", buf.read(), content_type=XLSX)

        resp = self.client.post(reverse("referensi:import_validate"), {"excel_file": [upload]})
        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        url = reverse("referensi:import_validate_report", args=[file_id])

        p1 = self.client.get(url + "?page=1")
        self.assertEqual(p1.status_code, 200)
        self.assertTrue(p1.context["is_paginated"])
        self.assertGreaterEqual(p1.context["page_obj"].paginator.num_pages, 2)

        def tables_on(resp):
            return {
                r["first_col"].split(" ")[0]
                for r in resp.context["results"] if r.get("type") == "table_container"
            }

        p2 = self.client.get(url + "?page=2")
        self.assertEqual(p2.context["page_obj"].number, 2)
        # Pages show different tables (no overlap, together they cover more).
        self.assertTrue(tables_on(p1).isdisjoint(tables_on(p2)))

        # Download from page 1 still includes ALL 130 tables (server supplement),
        # even with an empty/limited DOM payload.
        ex = self.client.post(
            reverse("referensi:export_from_frontend"),
            data=json.dumps({"type": "valid", "hierarchy": [], "data_rows": []}),
            content_type="application/json",
        )
        self.assertEqual(ex.status_code, 200)
        df = pd.read_excel(BytesIO(ex.content), sheet_name="Data")
        self.assertEqual(set(df["kode_ahsp"].dropna().astype(str)), set(codes))

    def test_persisted_edits_survive_pagination_and_feed_download(self):
        rows = _block("1.1.1.1", "Judul A") + _block("2.2.2.2", "Judul B")
        buf = BytesIO()
        pd.DataFrame(rows).to_excel(buf, sheet_name="Data", index=False, header=False)
        buf.seek(0)
        upload = SimpleUploadedFile("v.xlsx", buf.read(), content_type=XLSX)
        resp = self.client.post(reverse("referensi:import_validate"), {"excel_file": [upload]})
        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        edits_path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_edits.json")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        self.addCleanup(lambda: os.path.exists(edits_path) and os.remove(edits_path))

        # GET report first (sets session validated_excel_path / file_id).
        self.assertEqual(self.client.get(reverse("referensi:import_validate_report", args=[file_id])).status_code, 200)

        # Persist an edit for 1.1.1.1 (as if done on its page).
        edit = {
            "hierarchy": [{"code": "1.1.1.1", "title": "Judul A"}],
            "data_rows": [
                {"parent_code": "1.1.1.1", "segment": "A", "no": "1", "uraian": "EDITED Pekerja", "kode_ref": "L.01", "satuan": "OH", "koefisien": "9.99"},
                {"parent_code": "1.1.1.1", "segment": "B", "no": "1", "uraian": "Semen", "kode_ref": "-", "satuan": "kg", "koefisien": "2"},
                {"parent_code": "1.1.1.1", "segment": "C", "no": "1", "uraian": "Alat", "kode_ref": "E.01", "satuan": "jam", "koefisien": "0,5"},
            ],
        }
        sv = self.client.post(reverse("referensi:validate_save_edits", args=[file_id]),
                              data=json.dumps(edit), content_type="application/json")
        self.assertEqual(sv.status_code, 200)

        # Revisit the report: the edited table reflects the change.
        rp = self.client.get(reverse("referensi:import_validate_report", args=[file_id]))
        t = [r for r in rp.context["results"]
             if r.get("type") == "table_container" and r["first_col"].split(" ")[0] == "1.1.1.1"][0]
        tk_uraian = {ri["original_row"]["col_3"] for ri in t["grouped_rows"]["TK"]}
        self.assertIn("EDITED Pekerja", tk_uraian)

        # Download with an EMPTY DOM: persisted edit + the other table both present.
        ex = self.client.post(
            reverse("referensi:export_from_frontend"),
            data=json.dumps({"type": "valid", "hierarchy": [], "data_rows": []}),
            content_type="application/json",
        )
        df = pd.read_excel(BytesIO(ex.content), sheet_name="Data")
        self.assertEqual(set(df["kode_ahsp"].dropna().astype(str)), {"1.1.1.1", "2.2.2.2"})
        a = df[df["kode_ahsp"].astype(str) == "1.1.1.1"]
        self.assertIn("EDITED Pekerja", set(a["uraian"].astype(str)))

    def test_legacy_export_valid_excel_also_reflects_saved_edits(self):
        # The server-side export_valid_excel endpoint must honour persisted edits
        # too, so every download path stays consistent with the report.
        rows = _block("1.1.1.1", "Judul A") + _block("2.2.2.2", "Judul B")
        buf = BytesIO()
        pd.DataFrame(rows).to_excel(buf, sheet_name="Data", index=False, header=False)
        buf.seek(0)
        upload = SimpleUploadedFile("v.xlsx", buf.read(), content_type=XLSX)
        resp = self.client.post(reverse("referensi:import_validate"), {"excel_file": [upload]})
        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        edits_path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_edits.json")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        self.addCleanup(lambda: os.path.exists(edits_path) and os.remove(edits_path))

        # GET report sets session (validated_excel_path + validation_file_id).
        self.client.get(reverse("referensi:import_validate_report", args=[file_id]))
        self.client.post(
            reverse("referensi:validate_save_edits", args=[file_id]),
            data=json.dumps({
                "hierarchy": [{"code": "1.1.1.1", "title": "Judul A"}],
                "data_rows": [
                    {"parent_code": "1.1.1.1", "segment": "A", "no": "1", "uraian": "EDITED Pekerja", "kode_ref": "L.01", "satuan": "OH", "koefisien": "9.99"},
                ],
            }),
            content_type="application/json",
        )

        ex = self.client.get(reverse("referensi:export_valid_excel"))
        self.assertEqual(ex.status_code, 200)
        df = pd.read_excel(BytesIO(ex.content), sheet_name="Data Valid")
        self.assertIn("EDITED Pekerja", set(df["Uraian"].astype(str)))

    def test_summary_stats_reconcile_input_and_output(self):
        # 2 AHSP (4 rows each: 1 title + 3 data) + 1 discarded CATATAN noise row.
        rows = _block("1.1.1.1", "Judul A")
        rows.append(["CATATAN : harga belum termasuk PPN"])  # skipped as noise
        rows += _block("2.2.2.2", "Judul B")
        buf = BytesIO()
        pd.DataFrame(rows).to_excel(buf, sheet_name="Data", index=False, header=False)
        buf.seek(0)
        upload = SimpleUploadedFile("v.xlsx", buf.read(), content_type=XLSX)
        resp = self.client.post(reverse("referensi:import_validate"), {"excel_file": [upload]})
        file_id = resp.url.rstrip("/").split("/")[-1]
        path = os.path.join(settings.MEDIA_ROOT, "temp_imports", f"{file_id}_validate.xlsx")
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        c = self.client.get(reverse("referensi:import_validate_report", args=[file_id])).context
        self.assertEqual(c["total_rows"], 9)          # physical rows in the file
        self.assertEqual(c["ahsp_count"], 2)          # two AHSP tables
        self.assertEqual(c["data_rows_total"], 6)     # 3 data rows x 2 tables
        self.assertEqual(c["valid_rows"], 6)          # all clean
        self.assertEqual(c["warning_rows"], 0)
        self.assertEqual(c["danger_rows"], 0)
        self.assertEqual(c["struct_rows"], 2)         # two AHSP title rows
        self.assertEqual(c["discarded_rows"], 1)      # the CATATAN row
        # The reconciliation identity always holds: file = data + structure + discarded.
        self.assertEqual(
            c["total_rows"], c["data_rows_total"] + c["struct_rows"] + c["discarded_rows"]
        )
