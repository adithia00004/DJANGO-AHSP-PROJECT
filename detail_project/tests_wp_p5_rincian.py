"""WP-P5 — Rincian AHSP.

Locks the fixes:
- P5b (RA-06): export uses snapshot_satuan, not the missing `pek.satuan` ('-').
- P5c (RA-02): export Grand Total = Σ(G×volume) × (1 + PPN%) — identical to the web
  toolbar Grand Total (kontrol margin vs pagu), not the old Σ per-unit HSP.
- P5e (RA-07): markup override set/clear is written to the audit trail.
- P5d (RA-05): reset-all-overrides clears every override + audits each.
- P5g (RA-16/RA-01): pricing endpoint payload cap + canonical default markup constant.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project

from .exports.rincian_ahsp_adapter import RincianAHSPAdapter
from .models import (
    DetailAHSPAudit,
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
from .views_api import api_pekerjaan_pricing, api_reset_all_overrides


def _build_project(owner, *, with_pricing=True, satuan="m3"):
    project = Project.objects.create(owner=owner, nama="P5")
    klas = Klasifikasi.objects.create(project=project, name="K", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="S", ordering_index=1)
    pkj = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="P1", snapshot_uraian="Pasang", snapshot_satuan=satuan, ordering_index=1,
    )
    item = HargaItemProject.objects.create(
        project=project, kode_item="TK-1", kategori="TK", uraian="Pekerja",
        satuan="OH", harga_satuan=Decimal("100"),
    )
    src = DetailAHSPProject.objects.create(
        project=project, pekerjaan=pkj, harga_item=item,
        kategori="TK", kode="TK-1", uraian="Pekerja", satuan="OH", koefisien=Decimal("2"),
    )
    DetailAHSPExpanded.objects.create(
        project=project, pekerjaan=pkj, source_detail=src, harga_item=item,
        kategori="TK", kode="TK-1", uraian="Pekerja", satuan="OH",
        koefisien=Decimal("2"), expansion_depth=0,
    )
    VolumePekerjaan.objects.create(project=project, pekerjaan=pkj, quantity=Decimal("3"))
    if with_pricing:
        ProjectPricing.objects.create(project=project, markup_percent=Decimal("10"), ppn_percent=Decimal("11"))
    return project, pkj


class RincianExportContractTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p5-owner", password="x")
        self.project, self.pkj = _build_project(self.owner)

    def test_export_satuan_uses_snapshot_satuan(self):
        # P5b/RA-06: previously always '-'.
        data = RincianAHSPAdapter(self.project).get_export_data()
        section = data["sections"][0]
        self.assertEqual(section["pekerjaan"]["satuan"], "m3")

    def test_grand_total_matches_canonical_with_ppn(self):
        # P5c/RA-02: Grand Total = Σ(G×volume) × (1 + PPN%) = web toolbar value.
        rows = compute_rekap_for_project(self.project)
        D = sum(Decimal(str(r["total"])) for r in rows)  # 2×100×1.1×3 = 660
        self.assertEqual(D, Decimal("660.00"))
        adapter = RincianAHSPAdapter(self.project)
        data = adapter.get_export_data()
        self.assertEqual(data["summary"]["ppn_percent"], "11.00")
        self.assertEqual(data["summary"]["subtotal_langsung"], adapter._format_number(D, 0))
        self.assertEqual(
            data["summary"]["grand_total"],
            adapter._format_number(D * Decimal("1.11"), 0),  # 660 × 1.11 = 732.6 → 733
        )

    def test_no_pricing_row_still_uses_default_ppn_11(self):
        # Web endpoint defaults PPN to 11.00 sans ProjectPricing — export must match.
        owner2 = get_user_model().objects.create_user("p5-owner2", password="x")
        project2, _ = _build_project(owner2, with_pricing=False)
        data = RincianAHSPAdapter(project2).get_export_data()
        self.assertEqual(data["summary"]["ppn_percent"], "11.00")


class OverrideAuditTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p5e-owner", password="x")
        self.project, self.pkj = _build_project(self.owner)

    def _pricing(self, body):
        req = RequestFactory().post(
            reverse("detail_project:api_pekerjaan_pricing",
                    kwargs={"project_id": self.project.id, "pekerjaan_id": self.pkj.id}),
            data=body, content_type="application/json",
        )
        req.user = self.owner
        return api_pekerjaan_pricing(req, self.project.id, self.pkj.id)

    def _audits(self):
        return DetailAHSPAudit.objects.filter(project=self.project, pekerjaan=self.pkj)

    def test_set_override_is_audited(self):
        resp = self._pricing(json.dumps({"override_markup": "15"}))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.pkj.refresh_from_db()
        self.assertEqual(self.pkj.markup_override_percent, Decimal("15.00"))
        latest = self._audits().order_by("-id").first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.new_data.get("markup_override_percent"), "15.00")

    def test_clear_override_is_audited(self):
        self._pricing(json.dumps({"override_markup": "15"}))
        resp = self._pricing(json.dumps({"override_markup": None}))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.pkj.refresh_from_db()
        self.assertIsNone(self.pkj.markup_override_percent)
        latest = self._audits().order_by("-id").first()
        self.assertIsNone(latest.new_data.get("markup_override_percent"))
        self.assertEqual(latest.old_data.get("markup_override_percent"), "15.00")

    def test_decimal_override_not_corrupted_backend(self):
        # Backend parser accepts "12,5" → 12.50 (parallels the RA-04 frontend fix).
        resp = self._pricing(json.dumps({"override_markup": "12,5"}))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.pkj.refresh_from_db()
        self.assertEqual(self.pkj.markup_override_percent, Decimal("12.50"))


class ResetAllOverridesTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p5d-owner", password="x")
        self.project, self.pkj = _build_project(self.owner)
        # second pekerjaan with its own override
        self.pkj2 = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.pkj.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="P2", snapshot_uraian="X",
            snapshot_satuan="m2", ordering_index=2,
        )
        Pekerjaan.objects.filter(id=self.pkj.id).update(markup_override_percent=Decimal("20"))
        Pekerjaan.objects.filter(id=self.pkj2.id).update(markup_override_percent=Decimal("30"))

    def _reset_all(self):
        req = RequestFactory().post(
            reverse("detail_project:api_reset_all_overrides", kwargs={"project_id": self.project.id}),
            data="{}", content_type="application/json",
        )
        req.user = self.owner
        return api_reset_all_overrides(req, self.project.id)

    def test_reset_all_clears_and_counts_and_audits(self):
        resp = self._reset_all()
        self.assertEqual(resp.status_code, 200, resp.content)
        body = json.loads(resp.content)
        self.assertEqual(body["reset_count"], 2)
        self.assertFalse(
            Pekerjaan.objects.filter(project=self.project, markup_override_percent__isnull=False).exists()
        )
        self.assertEqual(DetailAHSPAudit.objects.filter(project=self.project).count(), 2)

    def test_reset_all_when_none_is_noop(self):
        self._reset_all()  # first clears the two
        resp = self._reset_all()  # second: nothing to clear
        self.assertEqual(json.loads(resp.content)["reset_count"], 0)


class PricingDefaultAndLimitTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p5g-owner", password="x")
        self.project, self.pkj = _build_project(self.owner, with_pricing=False)

    def _get(self):
        req = RequestFactory().get(
            reverse("detail_project:api_pekerjaan_pricing",
                    kwargs={"project_id": self.project.id, "pekerjaan_id": self.pkj.id})
        )
        req.user = self.owner
        return api_pekerjaan_pricing(req, self.project.id, self.pkj.id)

    def test_default_markup_uses_canonical_constant(self):
        # P5g/RA-01 drift: no ProjectPricing → default = DEFAULT_PROJECT_MARKUP_PERCENT.
        body = json.loads(self._get().content)
        self.assertEqual(body["project_markup"], f"{DEFAULT_PROJECT_MARKUP_PERCENT:.2f}")

    def test_oversized_body_rejected_413(self):
        req = RequestFactory().post(
            reverse("detail_project:api_pekerjaan_pricing",
                    kwargs={"project_id": self.project.id, "pekerjaan_id": self.pkj.id}),
            data="x" * 2_000_001, content_type="application/json",
        )
        req.user = self.owner
        resp = api_pekerjaan_pricing(req, self.project.id, self.pkj.id)
        self.assertEqual(resp.status_code, 413, resp.content)
