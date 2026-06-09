from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from dashboard.models import Project
from detail_project.models import HargaItemProject, Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.services import clone_ref_pekerjaan, expand_ahsp_bundle_to_components
from referensi.models import AHSPReferensi, RincianReferensi


class ImportDetailProjectTemplateRegressionTests(SimpleTestCase):
    def test_wysiwyg_export_regex_accepts_suffix_ahsp_codes(self):
        with open(
            "referensi/templates/referensi/import_validate_report.html",
            encoding="utf-8",
        ) as handle:
            template = handle.read()

        self.assertNotIn(r"rawText.match(/^([\d\.]+)/)", template)
        self.assertIn(r"(?:\.[A-Za-z])?", template)


class DetailProjectMultiSourceRegressionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_multi_source_regression",
            email="owner-multi-source-regression@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Multi Source Regression",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )
        self.klasifikasi = Klasifikasi.objects.create(
            project=self.project,
            name="Klasifikasi",
            ordering_index=1,
        )
        self.sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=self.klasifikasi,
            name="Sub",
            ordering_index=1,
        )

    def _ahsp(self, kode, nama, sumber):
        return AHSPReferensi.objects.create(
            kode_ahsp=kode,
            nama_ahsp=nama,
            satuan="m2",
            sumber=sumber,
        )

    def _rincian(self, ahsp, kategori, kode, uraian, koef="1.000000"):
        return RincianReferensi.objects.create(
            ahsp=ahsp,
            kategori=kategori,
            kode_item=kode,
            uraian_item=uraian,
            satuan_item="unit",
            koefisien=Decimal(koef),
        )

    def test_source_badge_uses_ahsp_sumber(self):
        ref = self._ahsp("1.1.1.1", "Pekerjaan Lama", "AHSP 2025")
        pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_REF,
            ref=ref,
            snapshot_kode=ref.kode_ahsp,
            snapshot_uraian=ref.nama_ahsp,
            snapshot_satuan=ref.satuan,
            ordering_index=1,
        )

        self.assertEqual(pekerjaan.source_badge(), "AHSP 2025")

    def test_clone_ref_pekerjaan_resolves_lain_bundle_in_same_source(self):
        parent_2025 = self._ahsp("2.2.1.1.5.a", "Parent 2025", "AHSP 2025")
        nested_2025 = self._ahsp("9.9.9.9", "Nested 2025", "AHSP 2025")
        nested_2026 = self._ahsp("9.9.9.9", "Nested 2026", "AHSP 2026")
        self._rincian(parent_2025, "LAIN", nested_2025.kode_ahsp, "Bundle nested")
        self._rincian(nested_2025, "TK", "TK-2025", "Tenaga 2025")
        self._rincian(nested_2026, "TK", "TK-2026", "Tenaga 2026")

        pekerjaan = clone_ref_pekerjaan(
            self.project,
            self.sub,
            parent_2025,
            Pekerjaan.SOURCE_REF,
            ordering_index=1,
        )
        detail = pekerjaan.detail_list.get(kategori="LAIN")

        self.assertEqual(detail.ref_ahsp_id, nested_2025.id)
        self.assertEqual(detail.ref_ahsp.sumber, "AHSP 2025")

    def test_expand_ahsp_bundle_does_not_get_duplicate_code_from_other_source(self):
        parent_2025 = self._ahsp("3.3.3.3", "Parent 2025", "AHSP 2025")
        nested_2025 = self._ahsp("8.8.8.8", "Nested 2025", "AHSP 2025")
        nested_2026 = self._ahsp("8.8.8.8", "Nested 2026", "AHSP 2026")
        self._rincian(parent_2025, "LAIN", nested_2025.kode_ahsp, "Bundle nested")
        self._rincian(nested_2025, "TK", "TK-2025", "Tenaga 2025")
        self._rincian(nested_2026, "TK", "TK-2026", "Tenaga 2026")

        components = expand_ahsp_bundle_to_components(
            ref_ahsp_id=parent_2025.id,
            project=self.project,
        )

        self.assertEqual(len(components), 1)
        self.assertRegex(components[0]["kode"], r"^TK-\d{4}$")
        self.assertEqual(components[0]["uraian"], "Tenaga 2025")

    def test_clone_ref_pekerjaan_generates_safe_codes_for_placeholder_items(self):
        ahsp = self._ahsp("4.4.4.4", "Placeholder item codes", "AHSP 2026")
        self._rincian(ahsp, "BHN", "-", "Semen Portland", "1.000000")
        self._rincian(ahsp, "ALT", "-", "Concrete mixer", "1.000000")

        pekerjaan = clone_ref_pekerjaan(
            self.project,
            self.sub,
            ahsp,
            Pekerjaan.SOURCE_REF,
            ordering_index=1,
        )

        details = list(pekerjaan.detail_list.order_by("kategori", "uraian"))
        self.assertEqual(len(details), 2)
        self.assertTrue(
            all(
                detail.kode.startswith(("B-", "PR-"))
                for detail in details
            )
        )
        self.assertNotEqual(details[0].kode, details[1].kode)
        self.assertEqual(
            HargaItemProject.objects.filter(project=self.project).count(),
            2,
        )
