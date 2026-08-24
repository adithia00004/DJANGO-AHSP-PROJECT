"""Template AHSP re-audit follow-ups (2026-06-20).

TA-04: reset-to-reference must be recorded in the audit trail (parity with save).
TA-07: detail-AHSP write endpoints must carry the write rate-limit + body-limit.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from referensi.models import AHSPReferensi, RincianReferensi
from detail_project.models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    DetailAHSPProject,
    DetailAHSPAudit,
)
from detail_project.services import _populate_expanded_from_raw, clone_ref_pekerjaan
from detail_project.views_api import api_reset_detail_ahsp_to_ref


class ResetAuditTrailTA04Tests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("ta04-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="TA04")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )

    def test_reset_writes_audit_entry(self):
        master = AHSPReferensi.objects.create(
            kode_ahsp="A.X", nama_ahsp="Master A.X", sumber="AHSP 2025", satuan="m2",
        )
        RincianReferensi.objects.create(
            ahsp=master, kategori="TK", kode_item="L.01", uraian_item="Pekerja",
            satuan_item="OH", koefisien=Decimal("5"),
        )
        a = clone_ref_pekerjaan(
            self.project, self.sub, master, Pekerjaan.SOURCE_REF_MOD, ordering_index=1,
            auto_load_rincian=True,
        )
        _populate_expanded_from_raw(self.project, a)

        # Diverge from the reference so the reset actually changes the snapshot.
        DetailAHSPProject.objects.filter(project=self.project, pekerjaan=a).update(
            koefisien=Decimal("99")
        )

        before = DetailAHSPAudit.objects.filter(project=self.project, pekerjaan=a).count()
        req = RequestFactory().post("/reset/")
        req.user = self.owner
        resp = api_reset_detail_ahsp_to_ref(req, self.project.id, a.id)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))

        entries = DetailAHSPAudit.objects.filter(project=self.project, pekerjaan=a)
        self.assertEqual(entries.count(), before + 1)
        latest = entries.order_by("-id").first()
        self.assertIn("Reset detail AHSP ke referensi", (latest.change_summary or ""))


class DetailAhspRateLimitTA07Tests(TestCase):
    def test_write_endpoints_carry_rate_and_body_limit(self):
        with open("detail_project/views_api.py", encoding="utf-8") as fh:
            src = fh.read()
        expected = {
            "api_save_detail_ahsp_for_pekerjaan": "@rate_limit(category='write_interactive'",
            "api_reset_detail_ahsp_to_ref": "@rate_limit(category='write')",
            "api_sync_reference": "@rate_limit(category='write')",
            "api_rebuild_missing_expansion": "@rate_limit(category='write')",
        }
        for fn, rate_snippet in expected.items():
            idx = src.index(f"def {fn}(")
            head = src[max(0, idx - 500):idx]
            self.assertIn(rate_snippet, head, f"{fn} missing rate_limit")
            self.assertIn("@limit_request_body()", head, f"{fn} missing limit_request_body")
