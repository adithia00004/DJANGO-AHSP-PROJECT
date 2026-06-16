"""WP-P1a (HI-05) — strict validation for the conversion-profile endpoint.

Bad input (negative, invalid number, non-positive factor, unknown method,
non-string unit, decimal overflow) must be rejected with 400 and NOT persisted —
previously such values were silently coerced to 0/1 defaults.
"""
import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project

from .models import HargaItemProject, ItemConversionProfile
from .views_api import api_save_conversion_profile


class ConversionProfileValidationTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p1-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P1")
        self.item = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-1", kategori="BHN",
            uraian="Besi beton", satuan="kg",
        )

    def _post(self, body):
        req = RequestFactory().post(
            "/conversion-profile/save/", data=json.dumps(body), content_type="application/json"
        )
        req.user = self.owner
        return api_save_conversion_profile(req, self.project.id)

    def _base(self, **over):
        body = {
            "harga_item_id": self.item.id,
            "market_unit": "batang",
            "market_price": "240000",
            "factor_to_base": "10",
            "method": "direct",
        }
        body.update(over)
        return body

    def test_valid_profile_saved(self):
        resp = self._post(self._base())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(json.loads(resp.content)["ok"])
        self.assertTrue(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_endpoint_syncs_harga_satuan(self):
        # WP-P1b/Model A: the (deprecated) endpoint must also write harga_satuan so
        # a direct call cannot reintroduce HI-02 divergence.
        from decimal import Decimal
        self._post(self._base(market_price="240000", factor_to_base="10"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("24000.00"))

    def test_negative_market_price_rejected(self):
        resp = self._post(self._base(market_price="-100"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_zero_factor_rejected(self):
        resp = self._post(self._base(factor_to_base="0"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_invalid_number_rejected_not_defaulted(self):
        resp = self._post(self._base(market_price="abc"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_unknown_method_rejected(self):
        resp = self._post(self._base(method="teleport"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_non_string_market_unit_rejected(self):
        resp = self._post(self._base(market_unit=123))
        self.assertEqual(resp.status_code, 400)

    def test_negative_density_rejected(self):
        resp = self._post(self._base(density="-5"))
        self.assertEqual(resp.status_code, 400)

    def test_decimal_overflow_is_400_not_500(self):
        # factor_to_base is DecimalField(max_digits=12, decimal_places=6) → max 6
        # integer digits. A 20-digit value must be a clean 400, never a 500.
        resp = self._post(self._base(factor_to_base="99999999999999999999"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())


class PayloadExposesConversionTests(TestCase):
    """WP-P1c (HI-04) — saved conversion profile is included in the items payload."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("p1c-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P1c")
        # active_harga_items_queryset includes standalone items not referenced by
        # any detail — a plain HargaItemProject qualifies.
        self.item = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-1", kategori="BHN",
            uraian="Besi beton", satuan="kg", harga_satuan=None,
        )

    def test_item_without_profile_has_conv_none(self):
        from .views_api import build_harga_items_payload
        payload = build_harga_items_payload(self.project)
        row = next(i for i in payload["items"] if i["id"] == self.item.id)
        self.assertIsNone(row["conv"])

    def test_item_with_profile_exposes_conv(self):
        from .views_api import build_harga_items_payload
        ItemConversionProfile.objects.create(
            harga_item=self.item, market_unit="batang",
            market_price="240000", factor_to_base="10", method="direct",
        )
        payload = build_harga_items_payload(self.project)
        row = next(i for i in payload["items"] if i["id"] == self.item.id)
        self.assertIsNotNone(row["conv"])
        self.assertEqual(row["conv"]["market_unit"], "batang")
        self.assertEqual(row["conv"]["factor_to_base"], "10.000000")
        self.assertEqual(row["conv"]["method"], "direct")


class MainSaveAtomicConversionTests(TestCase):
    """WP-P1b (HI-02 + Model A) — main save applies conversions atomically."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("p1b-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P1b")
        self.item = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-1", kategori="BHN",
            uraian="Besi beton", satuan="kg", harga_satuan=None,
        )

    def _save(self, body):
        from .views_api import api_save_harga_items
        req = RequestFactory().post(
            "/harga/save/", data=json.dumps(body), content_type="application/json"
        )
        req.user = self.owner
        return api_save_harga_items(req, self.project.id)

    def _conv(self, **over):
        c = {"id": self.item.id, "market_unit": "batang",
             "market_price": "240000", "factor_to_base": "10", "method": "direct"}
        c.update(over)
        return c

    def test_conversion_sets_server_computed_base_price(self):
        from decimal import Decimal
        resp = self._save({"items": [], "conversions": [self._conv()]})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("24000.00"))  # 240000/10
        self.assertTrue(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_conversion_overrides_wrong_client_price(self):
        # HI-07: client sends a bogus base price; server must ignore it and use
        # market_price/factor.
        from decimal import Decimal
        resp = self._save({
            "items": [{"id": self.item.id, "harga_satuan": "999"}],
            "conversions": [self._conv()],
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("24000.00"))

    def test_manual_override_with_flag_clears_profile(self):
        from decimal import Decimal
        ItemConversionProfile.objects.create(
            harga_item=self.item, market_unit="batang",
            market_price="240000", factor_to_base="10", method="direct",
        )
        resp = self._save({"items": [{"id": self.item.id, "harga_satuan": "23500", "clear_conversion": True}]})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("23500.00"))
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())

    def test_manual_without_flag_keeps_profile(self):
        # Non-destructive: a plain manual save must NOT delete a profile it never
        # explicitly cleared.
        prof = ItemConversionProfile.objects.create(
            harga_item=self.item, market_unit="batang",
            market_price="240000", factor_to_base="10", method="direct",
        )
        resp = self._save({"items": [{"id": self.item.id, "harga_satuan": "23500"}]})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(ItemConversionProfile.objects.filter(pk=prof.pk).exists())

    def test_invalid_conversion_is_atomic_400(self):
        resp = self._save({"items": [], "conversions": [self._conv(factor_to_base="0")]})
        self.assertEqual(resp.status_code, 400)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.harga_satuan)  # nothing applied
        self.assertFalse(ItemConversionProfile.objects.filter(harga_item=self.item).exists())


class HargaExportUsesHargaSatuanTests(TestCase):
    """WP-P1d (HI-03) — Harga Items export base table = harga_satuan (SSOT)."""

    def setUp(self):
        from decimal import Decimal

        from .models import (
            DetailAHSPExpanded, DetailAHSPProject, Klasifikasi, Pekerjaan, SubKlasifikasi,
        )
        self.owner = get_user_model().objects.create_user("p1d-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P1d")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P1", snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )
        # harga_satuan = 23500 (manually negotiated), but profile derives 24000.
        self.item = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-1", kategori="BHN",
            uraian="Besi beton", satuan="kg", harga_satuan=Decimal("23500.00"),
        )
        src = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pkj, harga_item=self.item,
            kategori="BHN", kode="BHN-1", uraian="Besi beton", satuan="kg",
            koefisien=Decimal("1"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=pkj, source_detail=src, harga_item=self.item,
            kategori="BHN", kode="BHN-1", uraian="Besi beton", satuan="kg",
            koefisien=Decimal("1"), expansion_depth=0,
        )
        ItemConversionProfile.objects.create(
            harga_item=self.item, market_unit="batang",
            market_price="240000", factor_to_base="10", method="direct",  # derived = 24000
        )

    def test_base_table_shows_harga_satuan_not_derived(self):
        from .exports.harga_items_adapter import HargaItemsAdapter
        data = HargaItemsAdapter(self.project).get_export_data()
        base_page = data["pages"][0]
        item_rows = [r for r in base_page["table_data"]["rows"] if r[1] == "BHN-1"]
        self.assertEqual(len(item_rows), 1)
        # Base price column must be 23.500 (harga_satuan), NOT 24.000 (derived).
        self.assertIn("23.500", item_rows[0][4])
        self.assertNotIn("24.000", item_rows[0][4])

    def test_konversi_table_flags_mismatch(self):
        from .exports.harga_items_adapter import HargaItemsAdapter
        data = HargaItemsAdapter(self.project).get_export_data()
        konv_page = data["pages"][1]
        narrative = " ".join(c for r in konv_page["table_data"]["rows"] for c in r)
        self.assertIn("override manual", narrative)  # reconciliation warning present
