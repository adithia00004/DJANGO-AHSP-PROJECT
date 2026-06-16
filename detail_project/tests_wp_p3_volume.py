"""WP-P3 — Volume Pekerjaan.

P3a (VP-05): computed-parameter expressions are validated server-side with the
SAME formula validator used by quantity formulas (char/token/function whitelist,
identifier format bp_N/cp_N) — previously only emptiness was checked.
"""
import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project

from .models import ProjectComputedParameter
from .views_api import (
    api_project_computed_parameters,
    api_project_computed_parameters_sync,
)


class ComputedExpressionValidationTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p3-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P3")

    def _sync(self, computed):
        req = RequestFactory().post(
            "/computed/sync/",
            data=json.dumps({"computed_parameters": computed, "mode": "replace"}),
            content_type="application/json",
        )
        req.user = self.owner
        return api_project_computed_parameters_sync(req, self.project.id)

    def _create(self, expression):
        req = RequestFactory().post(
            "/computed/",
            data=json.dumps({"expression": expression, "label": "Rumus"}),
            content_type="application/json",
        )
        req.user = self.owner
        return api_project_computed_parameters(req, self.project.id)

    def test_sync_accepts_valid_expression(self):
        resp = self._sync({"cp_1": {"expression": "bp_1 * bp_2", "label": "Area"}})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(json.loads(resp.content)["ok"])
        self.assertTrue(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_sync_rejects_invalid_expression(self):
        # 'foo' is not a bp_N/cp_N identifier → rejected; nothing persisted (atomic).
        resp = self._sync({"cp_1": {"expression": "bp_1 + foo", "label": "Area"}})
        self.assertEqual(resp.status_code, 422, resp.content)
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_sync_rejects_unsafe_chars(self):
        resp = self._sync({"cp_1": {"expression": "bp_1; DROP TABLE", "label": "X"}})
        self.assertEqual(resp.status_code, 422, resp.content)
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())

    def test_create_accepts_valid_expression(self):
        resp = self._create("bp_1 * 2")
        self.assertIn(resp.status_code, (200, 201), resp.content)
        self.assertTrue(json.loads(resp.content).get("created"))

    def test_create_rejects_invalid_expression(self):
        resp = self._create("bp_1 + foo")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project).exists())


class PayloadLimitTests(TestCase):
    """WP-P3b (VP-07): per-endpoint body-size cap (DoS guard) — rejects oversized
    bodies with 413 before parsing, without throttling request frequency."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("p3b-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P3b")

    def _post(self, body):
        from .views_api import api_save_volume_pekerjaan
        req = RequestFactory().post("/volume/save/", data=body, content_type="application/json")
        req.user = self.owner
        return api_save_volume_pekerjaan(req, self.project.id)

    def test_oversized_body_rejected_413(self):
        big = "x" * (2_000_001)  # just over the 2 MB default cap
        resp = self._post(big)
        self.assertEqual(resp.status_code, 413, resp.content)

    def test_normal_body_not_413(self):
        resp = self._post(json.dumps({"items": []}))
        self.assertNotEqual(resp.status_code, 413)


class VolumeCrossPageSSOTTests(TestCase):
    """WP-P3e — cross-page contract: VolumePekerjaan.quantity is the SINGLE SSOT
    consumed by BOTH Rekap RAB (G × quantity) and Rekap Kebutuhan
    (koef_expanded × quantity). Changing the volume moves both consistently."""

    def setUp(self):
        from decimal import Decimal
        from .models import (
            DetailAHSPExpanded, DetailAHSPProject, HargaItemProject, Klasifikasi,
            Pekerjaan, SubKlasifikasi, VolumePekerjaan,
        )
        self.Decimal = Decimal
        self.VolumePekerjaan = VolumePekerjaan
        self.owner = get_user_model().objects.create_user("p3e-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P3e")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P1", snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )
        item = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-1", kategori="BHN",
            uraian="Semen", satuan="kg", harga_satuan=Decimal("100"),
        )
        src = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=self.pkj, harga_item=item,
            kategori="BHN", kode="BHN-1", uraian="Semen", satuan="kg", koefisien=Decimal("2"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=self.pkj, source_detail=src, harga_item=item,
            kategori="BHN", kode="BHN-1", uraian="Semen", satuan="kg",
            koefisien=Decimal("2"), expansion_depth=0,
        )
        self.vol = VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=self.pkj, quantity=Decimal("3"),
        )

    def _rab_total(self):
        from .services import compute_rekap_for_project
        rows = compute_rekap_for_project(self.project)
        row = next(r for r in rows if r["pekerjaan_id"] == self.pkj.id)
        return self.Decimal(str(row["total"]))

    def _kebutuhan_qty(self):
        from .services import compute_kebutuhan_timeline
        result = compute_kebutuhan_timeline(self.project, mode="all")
        total = self.Decimal("0")
        for period in result["periods"]:
            for it in period["items"]:
                if it["kode"] == "BHN-1":
                    total += self.Decimal(str(it["quantity_decimal"]))
        return total

    def test_volume_quantity_drives_both_rab_and_kebutuhan(self):
        # quantity = 3 → RAB total = 2×100×1.1×3 = 660; Kebutuhan = koef 2 × vol 3 = 6.
        self.assertEqual(self._rab_total(), self.Decimal("660"))
        self.assertEqual(self._kebutuhan_qty(), self.Decimal("6"))

    def test_changing_volume_moves_both_consistently(self):
        self.vol.quantity = self.Decimal("5")
        self.vol.save(update_fields=["quantity"])
        # Same single SSOT → both pages reflect the new volume.
        self.assertEqual(self._rab_total(), self.Decimal("1100"))   # 2×100×1.1×5
        self.assertEqual(self._kebutuhan_qty(), self.Decimal("10"))  # 2×5
