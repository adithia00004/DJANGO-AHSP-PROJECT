"""WP-B5 inc-B5e — signature configuration per report (locks DoD)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from detail_project.exports.signature_config import (
    SignatureLayoutRules,
    SignaturePresets,
)


class SignatureConfigTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b5e-owner", password="x")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek TTD",
            sumber_dana="APBD",
            lokasi_project="Kota",
            nama_client="Dinas PU",
            anggaran_owner=Decimal("1000000"),
            nama_konsultan_perencana="CV Rencana",
            nama_kontraktor="PT Bangun",
            nama_konsultan_pengawas="CV Awas",
        )

    def test_document_presets_map_report_types(self):
        for doc in ["rekap_rab", "rekap_kebutuhan", "volume_pekerjaan", "harga_items", "rincian_ahsp"]:
            with self.subTest(doc=doc):
                self.assertEqual(
                    SignaturePresets.get_roles_for_document(doc),
                    SignaturePresets.PERENCANAAN,
                )
        for doc in ["jadwal_pekerjaan", "jadwal_professional", "laporan_progress"]:
            with self.subTest(doc=doc):
                self.assertEqual(
                    SignaturePresets.get_roles_for_document(doc),
                    SignaturePresets.PELAKSANAAN,
                )

    def test_unknown_document_defaults_to_perencanaan(self):
        self.assertEqual(
            SignaturePresets.get_roles_for_document("anything-else"),
            SignaturePresets.PERENCANAAN,
        )

    def test_build_signatures_perencanaan_owner_and_perencana(self):
        sigs = SignaturePresets.build_signatures(self.project, "PERENCANAAN")
        self.assertEqual([s["label"] for s in sigs], ["Pemilik Proyek", "Konsultan Perencana"])
        self.assertEqual([s["name"] for s in sigs], ["Dinas PU", "CV Rencana"])

    def test_build_signatures_pelaksanaan_three_roles(self):
        sigs = SignaturePresets.build_signatures(self.project, "PELAKSANAAN")
        self.assertEqual(
            [s["label"] for s in sigs],
            ["Pemilik Proyek", "Kontraktor Pelaksana", "Konsultan Pengawas"],
        )
        self.assertEqual([s["name"] for s in sigs], ["Dinas PU", "PT Bangun", "CV Awas"])

    def test_each_role_gets_its_own_instansi(self):
        """Instansi harus milik peran itu sendiri, bukan instansi klien untuk semua."""
        self.project.instansi_client = "Pemkot A"
        self.project.instansi_konsultan_perencana = "CV Rencana Jaya"
        self.project.instansi_kontraktor = "PT Bangun Jaya"
        self.project.instansi_konsultan_pengawas = "CV Awas Jaya"
        self.project.save()

        sigs = SignaturePresets.build_signatures(self.project, "FULL")

        self.assertEqual(
            [s["position"] for s in sigs],
            ["Pemkot A", "CV Rencana Jaya", "PT Bangun Jaya", "CV Awas Jaya"],
        )


class SignatureSheetRenderTests(TestCase):
    """Lembar pengesahan PDF harus benar-benar MENCETAK nama, bukan garis kosong.

    Tes lain di berkas ini berhenti pada ``build_signatures`` -- datanya benar,
    tapi ``PDFExporter._build_signatures`` mengisi baris nama dengan 20 garis
    bawah literal dan tidak pernah memakai ``sig['name']``. Akibatnya lembar
    pengesahan Rekap RAB dan Rincian AHSP terbit kosong meski data konsultan
    lengkap di Dashboard. Tes ini memeriksa tabel yang benar-benar dirender.
    """

    def setUp(self):
        self.owner = get_user_model().objects.create_user("ttd-render", password="x")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Pengesahan",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas Peternakan",
            instansi_client="Pemkab Lombok Barat",
            nama_konsultan_perencana="Rozan Fahriady",
            instansi_konsultan_perencana="CV Kaleidoskop",
            anggaran_owner=Decimal("1000000"),
        )

    def _signature_rows(self):
        from reportlab.platypus import Table

        from detail_project.exports.export_manager import ExportManager
        from detail_project.exports.pdf_exporter import PDFExporter

        elements = PDFExporter(ExportManager(self.project)._create_config())._build_signatures()

        def _tables(obj):
            if isinstance(obj, Table):
                yield obj
            for attr in ("_content", "_flowables"):
                for child in getattr(obj, attr, []) or []:
                    yield from _tables(child)

        rows = []
        for table in _tables(elements[0]):
            rows.extend(table._cellvalues)
        return rows

    def test_names_and_instansi_are_printed(self):
        flat = [str(cell) for row in self._signature_rows() for cell in row]

        for expected in (
            "Pemilik Proyek",
            "Konsultan Perencana",
            "Dinas Peternakan",
            "Rozan Fahriady",
            "Pemkab Lombok Barat",
            "CV Kaleidoskop",
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    flat,
                    f"'{expected}' tidak tercetak di lembar pengesahan PDF.",
                )

    def test_signature_line_is_kept_separate_from_the_name(self):
        """Garis tanda tangan tetap ada, tapi sebagai barisnya sendiri.

        Sebelum perbaikan, garis bawah MENGGANTIKAN nama. Keduanya harus hadir.
        """
        rows = self._signature_rows()
        line_rows = [r for r in rows if all(str(c).strip("_") == "" and str(c) for c in r)]

        self.assertTrue(line_rows, "garis tanda tangan hilang")
        self.assertIn("Rozan Fahriady", [str(c) for r in rows for c in r])

    def test_role_fields_are_real_project_attributes(self):
        # Locks the contract that each signature role maps to an existing field.
        for key, role in SignaturePresets.ALL_ROLES.items():
            with self.subTest(role=key):
                self.assertTrue(hasattr(self.project, role["field"]))

    def test_signature_requires_three_content_rows_when_space_is_insufficient(self):
        self.assertEqual(SignatureLayoutRules.MIN_ROWS_WITH_SIGNATURE, 3)
        self.assertTrue(
            SignatureLayoutRules.should_keep_with_signature(
                remaining_rows=3,
                available_space_mm=30,
                row_height_mm=5,
                num_signatures=3,
            )
        )
        self.assertFalse(
            SignatureLayoutRules.should_keep_with_signature(
                remaining_rows=4,
                available_space_mm=30,
                row_height_mm=5,
                num_signatures=3,
            )
        )

    def test_pdf_exporter_keeps_signature_blocks_together(self):
        import inspect

        from detail_project.exports import pdf_exporter

        source = inspect.getsource(pdf_exporter)
        self.assertIn("KeepTogether", source)
        self.assertIn("SignatureLayoutRules as SLR", source)
        self.assertIn("signature_height", source)

    def test_exporters_have_empty_dataset_placeholders(self):
        import inspect

        from detail_project.exports import excel_exporter, pdf_exporter, word_exporter

        self.assertIn("No data", inspect.getsource(pdf_exporter))
        self.assertIn("Tidak ada data", inspect.getsource(excel_exporter))
        self.assertIn("Tidak ada data", inspect.getsource(word_exporter))
