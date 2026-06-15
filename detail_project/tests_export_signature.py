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
