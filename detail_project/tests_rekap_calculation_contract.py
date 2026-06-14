import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase

from dashboard.models import Project

from .models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    ProjectPricing,
    SubKlasifikasi,
    VolumePekerjaan,
)
from .services import DEFAULT_PROJECT_MARKUP_PERCENT, compute_rekap_for_project
from .exports.rincian_ahsp_adapter import RincianAHSPAdapter
from .exports.rekap_rab_adapter import RekapRABAdapter
from .views_api import api_get_rekap_rab


class RekapCalculationContractTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="rekap-contract-owner",
            password="not-used",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Rekap Contract",
        )
        klasifikasi = Klasifikasi.objects.create(
            project=self.project,
            name="Pekerjaan Utama",
            ordering_index=1,
        )
        self.sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klasifikasi,
            name="Sub Pekerjaan",
            ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P-001",
            snapshot_uraian="Pekerjaan kontrak rekap",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self.item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="BHN-001",
            kategori="BHN",
            uraian="Bahan kontrak",
            satuan="kg",
            harga_satuan=Decimal("100.00"),
        )
        source = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=self.item,
            kategori="BHN",
            kode="BHN-001",
            uraian="Bahan kontrak",
            satuan="kg",
            koefisien=Decimal("2.000000"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=source,
            harga_item=self.item,
            kategori="BHN",
            kode="BHN-001",
            uraian="Bahan kontrak",
            satuan="kg",
            koefisien=Decimal("2.000000"),
            expansion_depth=0,
        )
        VolumePekerjaan.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            quantity=Decimal("3.000"),
        )

    def _row(self):
        rows = compute_rekap_for_project(self.project)
        row = next(
            (
                item
                for item in rows
                if item["pekerjaan_id"] == self.pekerjaan.id
            ),
            None,
        )
        self.assertIsNotNone(row)
        return row

    def assert_decimal_equal(self, actual, expected):
        self.assertEqual(Decimal(str(actual)), Decimal(str(expected)))

    def test_default_markup_is_ten_percent_without_pricing_row(self):
        row = self._row()

        self.assertEqual(DEFAULT_PROJECT_MARKUP_PERCENT, Decimal("10.00"))
        self.assert_decimal_equal(row["E_base"], "200")
        self.assert_decimal_equal(row["markup_eff"], "10")
        self.assert_decimal_equal(row["F"], "20")
        self.assert_decimal_equal(row["G"], "220")
        self.assert_decimal_equal(row["total"], "660")

    def test_project_markup_and_work_override_precedence(self):
        ProjectPricing.objects.create(
            project=self.project,
            markup_percent=Decimal("12.50"),
            ppn_percent=Decimal("25.00"),
        )
        row = self._row()
        self.assert_decimal_equal(row["markup_eff"], "12.5")
        self.assert_decimal_equal(row["G"], "225")
        self.assert_decimal_equal(row["total"], "675")

        self.pekerjaan.markup_override_percent = Decimal("5.00")
        self.pekerjaan.save(update_fields=["markup_override_percent"])
        row = self._row()
        self.assert_decimal_equal(row["markup_eff"], "5")
        self.assert_decimal_equal(row["G"], "210")
        self.assert_decimal_equal(row["total"], "630")

    def test_explicit_zero_markup_is_not_replaced_by_default(self):
        ProjectPricing.objects.create(
            project=self.project,
            markup_percent=Decimal("0.00"),
        )

        row = self._row()

        self.assert_decimal_equal(row["markup_percent_effective"], "0")
        self.assert_decimal_equal(row["unit_price_after_markup"], "200")
        self.assert_decimal_equal(row["work_total_after_markup"], "600")

    def test_canonical_fields_match_legacy_aliases(self):
        row = self._row()

        self.assertEqual(row["component_cost_before_markup"], row["E_base"])
        self.assertEqual(row["markup_percent_effective"], row["markup_eff"])
        self.assertEqual(row["markup_amount"], row["F"])
        self.assertEqual(row["unit_price_after_markup"], row["G"])
        self.assertEqual(row["work_total_after_markup"], row["total"])

    def test_missing_volume_is_zero_without_changing_unit_price(self):
        VolumePekerjaan.objects.filter(pekerjaan=self.pekerjaan).delete()

        row = self._row()

        self.assert_decimal_equal(row["unit_price_after_markup"], "220")
        self.assert_decimal_equal(row["volume"], "0")
        self.assert_decimal_equal(row["work_total_after_markup"], "0")

    def test_explicit_zero_volume_is_preserved(self):
        volume = VolumePekerjaan.objects.get(pekerjaan=self.pekerjaan)
        volume.quantity = Decimal("0.000")
        volume.save(update_fields=["quantity", "updated_at"])

        row = self._row()

        self.assert_decimal_equal(row["unit_price_after_markup"], "220")
        self.assert_decimal_equal(row["volume"], "0")
        self.assert_decimal_equal(row["work_total_after_markup"], "0")

    def test_rincian_export_totals_use_canonical_service(self):
        ProjectPricing.objects.create(
            project=self.project,
            markup_percent=Decimal("12.50"),
        )

        row = self._row()
        export_data = RincianAHSPAdapter(self.project).get_export_data()
        section = export_data["sections"][0]

        self.assertEqual(
            section["totals"]["G"],
            RincianAHSPAdapter(self.project)._format_number(
                row["unit_price_after_markup"],
                0,
            ),
        )
        self.assertEqual(section["totals"]["markup_eff"], "12.50")

    def test_expanded_nested_component_uses_bundle_multiplier_once(self):
        referenced = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P-REF",
            snapshot_uraian="Pekerjaan referensi bundle",
            snapshot_satuan="m2",
            ordering_index=2,
        )
        bundle_item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="BUNDLE-001",
            kategori="LAIN",
            uraian="Bundle pekerjaan",
            satuan="ls",
            harga_satuan=Decimal("0.00"),
        )
        bundle_source = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=bundle_item,
            kategori="LAIN",
            kode="BUNDLE-001",
            uraian="Bundle pekerjaan",
            satuan="ls",
            koefisien=Decimal("3.000000"),
            ref_pekerjaan=referenced,
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=bundle_source,
            harga_item=self.item,
            kategori="BHN",
            kode="BHN-NESTED",
            uraian="Komponen nested",
            satuan="kg",
            koefisien=Decimal("2.000000"),
            expansion_depth=3,
        )

        row = self._row()

        # Direct 2x100 + nested (2x3)x100 = 800 before markup.
        self.assert_decimal_equal(row["component_cost_before_markup"], "800")
        self.assert_decimal_equal(row["unit_price_after_markup"], "880")

    def test_money_rounding_is_half_up_at_canonical_stages(self):
        ProjectPricing.objects.create(
            project=self.project,
            markup_percent=Decimal("12.50"),
        )
        source = DetailAHSPProject.objects.get(
            project=self.project,
            pekerjaan=self.pekerjaan,
            kode="BHN-001",
        )
        source.koefisien = Decimal("0.333333333333")
        source.save(update_fields=["koefisien", "updated_at"])
        expanded = DetailAHSPExpanded.objects.get(source_detail=source)
        expanded.koefisien = Decimal("0.333333333333")
        expanded.save(update_fields=["koefisien", "updated_at"])
        volume = VolumePekerjaan.objects.get(pekerjaan=self.pekerjaan)
        volume.quantity = Decimal("3.333")
        volume.save(update_fields=["quantity", "updated_at"])

        row = self._row()

        self.assert_decimal_equal(row["component_cost_before_markup"], "33.33")
        self.assert_decimal_equal(row["markup_amount"], "4.17")
        self.assert_decimal_equal(row["unit_price_after_markup"], "37.50")
        self.assert_decimal_equal(row["work_total_after_markup"], "124.99")

    def test_service_web_and_rekap_export_use_identical_work_values(self):
        ProjectPricing.objects.create(
            project=self.project,
            markup_percent=Decimal("12.50"),
            ppn_percent=Decimal("25.00"),
            rounding_base=1000,
        )
        service_row = self._row()

        request = RequestFactory().get("/api/rekap-rab/")
        request.user = self.owner
        response = api_get_rekap_rab(request, self.project.id)
        payload = json.loads(response.content)
        web_row = payload["rows"][0]

        export_data = RekapRABAdapter(self.project).get_export_data()
        work_row = next(
            row
            for index, row in enumerate(export_data["table_data"]["rows"])
            if export_data["hierarchy_levels"].get(index) == 3
        )

        self.assert_decimal_equal(
            web_row["unit_price_after_markup"],
            service_row["unit_price_after_markup"],
        )
        self.assert_decimal_equal(
            web_row["work_total_after_markup"],
            service_row["work_total_after_markup"],
        )
        self.assertEqual(
            work_row[4],
            RekapRABAdapter(self.project)._format_number(
                service_row["unit_price_after_markup"],
                0,
            ),
        )
        self.assertEqual(
            work_row[5],
            RekapRABAdapter(self.project)._format_number(
                service_row["work_total_after_markup"],
                0,
            ),
        )
        self.assert_decimal_equal(
            export_data["totals"]["total_biaya_langsung"],
            service_row["work_total_after_markup"],
        )
