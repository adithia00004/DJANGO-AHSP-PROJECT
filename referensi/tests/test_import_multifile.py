"""Multi-file import: several clean/interchange xlsx merge into ONE staging batch."""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from referensi.models import AHSPReferensi
from referensi.models_staging import AHSPImportBatch, AHSPImportStaging
from referensi.services.import_schema import dump_workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _ahsp_rows(code, nama):
    return [
        {"kode_ahsp": code, "nama_ahsp": nama, "segmen": "A", "kode_item": "L.01", "uraian": "Pekerja", "satuan": "OH", "koefisien": "0.1"},
        {"kode_ahsp": code, "nama_ahsp": nama, "segmen": "B", "kode_item": "B.01", "uraian": "Bahan", "satuan": "kg", "koefisien": "2"},
        {"kode_ahsp": code, "nama_ahsp": nama, "segmen": "C", "kode_item": "E.01", "uraian": "Alat", "satuan": "jam", "koefisien": "0.5"},
    ]


class ImportMultiFileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="import-multi-admin",
            email="import-multi-admin@example.com",
            password="Secret123!",
        )
        self.client.force_login(self.user)

    def _interchange(self, name, code, nama, sumber):
        data = dump_workbook(_ahsp_rows(code, nama), meta={"sumber": sumber, "export_type": "valid"})
        return SimpleUploadedFile(name, data, content_type=XLSX)

    def test_multiple_interchange_files_merge_into_one_batch_and_commit(self):
        f1 = self._interchange("part_a.xlsx", "1.1.1.1", "Pekerjaan A", "AHSP 2026")
        f2 = self._interchange("part_b.xlsx", "2.2.1.1.5.a", "Pekerjaan Suffix B", "AHSP 2026")

        # Leave the form sumber blank: it must be read from each file's Meta.
        resp = self.client.post(
            reverse("referensi:import_excel"), {"excel_file": [f1, f2], "sumber": ""}
        )
        self.assertEqual(resp.status_code, 302)

        # Exactly ONE staging batch holds rows from BOTH files.
        batches = AHSPImportBatch.objects.filter(
            user=self.user, status=AHSPImportBatch.Status.STAGED
        )
        self.assertEqual(batches.count(), 1)
        batch = batches.first()
        self.assertEqual(batch.sumber, "AHSP 2026")  # auto-read from Meta

        staged_parents = set(
            AHSPImportStaging.objects.filter(
                batch=batch, segment_type__in=["A", "B", "C"]
            ).values_list("parent_ahsp_code", flat=True)
        )
        self.assertEqual(staged_parents, {"1.1.1.1", "2.2.1.1.5.a"})

        # HEADING names are carried per parent.
        headings = dict(
            AHSPImportStaging.objects.filter(batch=batch, segment_type="HEADING")
            .values_list("kode_item", "uraian_item")
        )
        self.assertEqual(headings.get("1.1.1.1"), "Pekerjaan A")
        self.assertEqual(headings.get("2.2.1.1.5.a"), "Pekerjaan Suffix B")

        # Commit -> both AHSP land in the reference DB with correct names.
        self.client.post(
            reverse("referensi:import_staging_commit"),
            {"sumber": "AHSP 2026", "batch_id": batch.id, "commit_mode": "merge"},
        )
        names = dict(
            AHSPReferensi.objects.filter(sumber="AHSP 2026").values_list("kode_ahsp", "nama_ahsp")
        )
        self.assertEqual(names.get("1.1.1.1"), "Pekerjaan A")
        self.assertEqual(names.get("2.2.1.1.5.a"), "Pekerjaan Suffix B")

    def test_staging_view_groups_children_directly_under_parent(self):
        # Regression: stagers insert all HEADINGs first then all data rows; the
        # staging view must regroup so each parent HEADING is immediately followed
        # by its own data rows (otherwise parents look empty).
        f1 = self._interchange("part_a.xlsx", "1.1.1.1", "Pekerjaan A", "AHSP 2026")
        f2 = self._interchange("part_b.xlsx", "2.2.2.2", "Pekerjaan B", "AHSP 2026")
        self.client.post(reverse("referensi:import_excel"), {"excel_file": [f1, f2], "sumber": ""})

        resp = self.client.get(reverse("referensi:import_staging"))
        self.assertEqual(resp.status_code, 200)
        rows = list(resp.context["staging_data"])

        # Every data row must immediately follow (belong to) the most recent HEADING.
        current_parent = None
        for r in rows:
            if r.segment_type == "HEADING":
                current_parent = r.kode_item
            else:
                self.assertEqual(
                    r.parent_ahsp_code, current_parent,
                    f"Data row {r.kode_item!r} is not grouped under its parent "
                    f"(current heading={current_parent!r})",
                )

        headings = [r.kode_item for r in rows if r.segment_type == "HEADING"]
        self.assertEqual(headings, ["1.1.1.1", "2.2.2.2"])
        # Each parent has its 3 data rows grouped right after it.
        self.assertEqual(len([r for r in rows if r.segment_type != "HEADING"]), 6)
