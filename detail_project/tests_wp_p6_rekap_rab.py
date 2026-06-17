"""WP-P6 — Rekap RAB.

P6d (RR-10): project-level pricing changes (markup / PPN / rounding) are recorded —
a lightweight, single-user-friendly trail (timestamp + old→new) reusing DetailAHSPAudit
with pekerjaan=None. Logged ONLY when a value actually changes (server-light).
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project

from .models import DetailAHSPAudit, ProjectPricing
from .views_api import api_project_pricing


class PricingChangeAuditTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p6-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P6")
        ProjectPricing.objects.create(
            project=self.project, markup_percent=Decimal("10"),
            ppn_percent=Decimal("11"), rounding_base=10000,
        )

    def _post(self, body):
        req = RequestFactory().post(
            reverse("detail_project:api_project_pricing", kwargs={"project_id": self.project.id}),
            data=json.dumps(body), content_type="application/json",
        )
        req.user = self.owner
        return api_project_pricing(req, self.project.id)

    def _audits(self):
        return DetailAHSPAudit.objects.filter(project=self.project, pekerjaan__isnull=True)

    def test_changing_markup_is_recorded(self):
        resp = self._post({"markup_percent": "15"})
        self.assertEqual(resp.status_code, 200, resp.content)
        entry = self._audits().order_by("-id").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.old_data.get("markup_percent"), "10.00")
        self.assertEqual(entry.new_data.get("markup_percent"), "15.00")
        self.assertIn("Markup", entry.change_summary)

    def test_changing_ppn_and_rounding_records_only_changed_fields(self):
        resp = self._post({"ppn_percent": "12", "rounding_base": 1000})
        self.assertEqual(resp.status_code, 200, resp.content)
        entry = self._audits().order_by("-id").first()
        self.assertIsNotNone(entry)
        self.assertEqual(set(entry.new_data.keys()), {"ppn_percent", "rounding_base"})
        self.assertNotIn("markup_percent", entry.new_data)  # markup unchanged → not logged

    def test_no_change_writes_no_audit(self):
        # Re-posting identical values must NOT create an audit row (server-light).
        resp = self._post({"markup_percent": "10", "ppn_percent": "11", "rounding_base": 10000})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self._audits().count(), 0)

    def test_pricing_audit_has_no_pekerjaan(self):
        self._post({"markup_percent": "20"})
        entry = self._audits().order_by("-id").first()
        self.assertIsNone(entry.pekerjaan_id)  # project-level event
        self.assertEqual(entry.triggered_by, "user")


class MarkupOverrideFlagTests(TestCase):
    """WP-P6h (D-RR-06): the canonical rekap row exposes `markup_is_override` so the
    Rekap RAB can flag pekerjaan that use an override (vs the project default)."""

    def setUp(self):
        from .models import (
            DetailAHSPExpanded, DetailAHSPProject, HargaItemProject,
            Klasifikasi, Pekerjaan, SubKlasifikasi, VolumePekerjaan,
        )
        self.owner = get_user_model().objects.create_user("p6h-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P6h")
        ProjectPricing.objects.create(project=self.project, markup_percent=Decimal("10"), ppn_percent=Decimal("11"))
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)

        def _job(kode, order, override=None):
            p = Pekerjaan.objects.create(
                project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
                snapshot_kode=kode, snapshot_uraian=kode, snapshot_satuan="m2", ordering_index=order,
            )
            if override is not None:
                Pekerjaan.objects.filter(id=p.id).update(markup_override_percent=override)
            item = HargaItemProject.objects.create(
                project=self.project, kode_item=f"TK-{kode}", kategori="TK", uraian="x",
                satuan="OH", harga_satuan=Decimal("100"),
            )
            src = DetailAHSPProject.objects.create(
                project=self.project, pekerjaan=p, harga_item=item, kategori="TK",
                kode=f"TK-{kode}", uraian="x", satuan="OH", koefisien=Decimal("1"),
            )
            DetailAHSPExpanded.objects.create(
                project=self.project, pekerjaan=p, source_detail=src, harga_item=item,
                kategori="TK", kode=f"TK-{kode}", uraian="x", satuan="OH",
                koefisien=Decimal("1"), expansion_depth=0,
            )
            VolumePekerjaan.objects.create(project=self.project, pekerjaan=p, quantity=Decimal("1"))
            return p

        self.p_default = _job("A", 1)
        self.p_override = _job("B", 2, override=Decimal("25"))

    def test_row_flags_override_vs_default(self):
        from .services import compute_rekap_for_project
        rows = {r["pekerjaan_id"]: r for r in compute_rekap_for_project(self.project)}
        self.assertFalse(rows[self.p_default.id]["markup_is_override"])
        self.assertTrue(rows[self.p_override.id]["markup_is_override"])
        self.assertEqual(rows[self.p_override.id]["markup_eff"], 25.0)
