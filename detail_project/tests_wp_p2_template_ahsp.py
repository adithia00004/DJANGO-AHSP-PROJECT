"""WP-P2 — Template AHSP.

P2a (TA-01 storage): a DB CheckConstraint rejects negative koefisien even when the
app-level validator is bypassed (e.g. bulk_create / direct ORM writes).
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase

from dashboard.models import Project

from .models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)


class KoefisienConstraintTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p2-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P2")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P1", snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )
        self.hip = HargaItemProject.objects.create(
            project=self.project, kode_item="BHN-1", kategori="BHN",
            uraian="Bahan", satuan="kg", harga_satuan=Decimal("100"),
        )

    def test_negative_koef_rejected_at_db_level(self):
        # objects.create() does NOT run full_clean → only the DB constraint guards.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetailAHSPProject.objects.create(
                    project=self.project, pekerjaan=self.pkj, harga_item=self.hip,
                    kategori="BHN", kode="BHN-1", uraian="Bahan", satuan="kg",
                    koefisien=Decimal("-1"),
                )

    def test_zero_koef_allowed(self):
        obj = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=self.pkj, harga_item=self.hip,
            kategori="BHN", kode="BHN-1", uraian="Bahan", satuan="kg",
            koefisien=Decimal("0"),
        )
        self.assertEqual(obj.koefisien, Decimal("0"))

    def test_negative_expanded_koef_rejected_at_db_level(self):
        src = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=self.pkj, harga_item=self.hip,
            kategori="BHN", kode="BHN-1", uraian="Bahan", satuan="kg", koefisien=Decimal("1"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetailAHSPExpanded.objects.create(
                    project=self.project, pekerjaan=self.pkj, source_detail=src, harga_item=self.hip,
                    kategori="BHN", kode="BHN-1", uraian="Bahan", satuan="kg",
                    koefisien=Decimal("-0.5"), expansion_depth=0,
                )


class CascadeSaveAtomicTests(TestCase):
    """WP-P2b (TA-20) — a failed dependent cascade rolls back the whole save."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("p2b-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P2b")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P1", snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )

    def test_cascade_failure_rolls_back_save(self):
        from .views_api import api_save_detail_ahsp_for_pekerjaan
        body = {"rows": [{"kategori": "BHN", "kode": "B-1", "uraian": "Semen", "satuan": "kg", "koefisien": "1"}]}
        req = RequestFactory().post("/save/", data=json.dumps(body), content_type="application/json")
        req.user = self.owner
        with patch("detail_project.views_api.cascade_bundle_re_expansion", side_effect=RuntimeError("boom")):
            resp = api_save_detail_ahsp_for_pekerjaan(req, self.project.id, self.pkj.id)
        self.assertEqual(resp.status_code, 500, resp.content)
        self.assertFalse(json.loads(resp.content)["ok"])
        # Atomic rollback: nothing for this pekerjaan was persisted.
        self.assertFalse(DetailAHSPProject.objects.filter(project=self.project, pekerjaan=self.pkj).exists())

    def test_save_succeeds_when_cascade_ok(self):
        from .views_api import api_save_detail_ahsp_for_pekerjaan
        body = {"rows": [{"kategori": "BHN", "kode": "B-1", "uraian": "Semen", "satuan": "kg", "koefisien": "1"}]}
        req = RequestFactory().post("/save/", data=json.dumps(body), content_type="application/json")
        req.user = self.owner
        resp = api_save_detail_ahsp_for_pekerjaan(req, self.project.id, self.pkj.id)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(DetailAHSPProject.objects.filter(project=self.project, pekerjaan=self.pkj).exists())


class CustomEndToEndContractTests(TestCase):
    """WP-P2c (TA-21) — lock CUSTOM → expansion → Harga → Rekap RAB end-to-end,
    exercising the REAL ``_populate_expanded_from_raw`` pipeline (not hand-made
    expanded rows). Default markup 10%, no PPN row.
    """

    def setUp(self):
        from referensi.models import AHSPReferensi, RincianReferensi  # noqa: F401
        self.owner = get_user_model().objects.create_user("p2c-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P2c")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        self._order = 0

    def _pekerjaan(self, kode):
        self._order += 1
        return Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode=kode, snapshot_uraian=f"P {kode}", snapshot_satuan="m2", ordering_index=self._order,
        )

    def _hip(self, kode, kategori, harga=None):
        return HargaItemProject.objects.create(
            project=self.project, kode_item=kode, kategori=kategori,
            uraian=f"Item {kode}", satuan="kg" if kategori != "LAIN" else "ls",
            harga_satuan=(Decimal(str(harga)) if harga is not None else None),
        )

    def _rekap_row(self, pkj):
        from .services import compute_rekap_for_project
        rows = compute_rekap_for_project(self.project)
        return next((r for r in rows if r["pekerjaan_id"] == pkj.id), None)

    def test_custom_direct_component_to_rekap(self):
        from .services import _populate_expanded_from_raw
        pkj = self._pekerjaan("D1")
        DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pkj, harga_item=self._hip("BHN-1", "BHN", 100),
            kategori="BHN", kode="BHN-1", uraian="Semen", satuan="kg", koefisien=Decimal("2"),
        )
        _populate_expanded_from_raw(self.project, pkj)
        from .models import VolumePekerjaan
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pkj, quantity=Decimal("3"))
        row = self._rekap_row(pkj)
        self.assertIsNotNone(row)
        self.assertEqual(Decimal(str(row["E_base"])), Decimal("200"))   # 2 × 100
        self.assertEqual(Decimal(str(row["G"])), Decimal("220"))        # +10%
        self.assertEqual(Decimal(str(row["total"])), Decimal("660"))    # × 3

    def test_custom_bundle_ahsp_koef_gt_one_to_rekap(self):
        from referensi.models import AHSPReferensi, RincianReferensi
        from .services import _populate_expanded_from_raw
        from .models import DetailAHSPExpanded, VolumePekerjaan
        master = AHSPReferensi.objects.create(kode_ahsp="A.1", nama_ahsp="Master", sumber="AHSP 2025", satuan="m2")
        RincianReferensi.objects.create(ahsp=master, kategori="TK", kode_item="L.01", uraian_item="Pekerja", satuan_item="OH", koefisien=Decimal("5"))
        pkj = self._pekerjaan("B1")
        DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pkj, harga_item=self._hip("A.1", "LAIN"),
            kategori="LAIN", kode="A.1", uraian="Bundle", satuan="ls",
            koefisien=Decimal("2"), ref_ahsp=master,  # bundle koef > 1
        )
        _populate_expanded_from_raw(self.project, pkj)
        # Price the expanded base component.
        exp = DetailAHSPExpanded.objects.get(project=self.project, pekerjaan=pkj, kategori="TK")
        exp.harga_item.harga_satuan = Decimal("100")
        exp.harga_item.save(update_fields=["harga_satuan"])
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pkj, quantity=Decimal("3"))
        row = self._rekap_row(pkj)
        self.assertIsNotNone(row)
        # expanded koef 5 (per-unit) × bundle koef 2 × harga 100 = 1000 base.
        self.assertEqual(Decimal(str(row["E_base"])), Decimal("1000"))
        self.assertEqual(Decimal(str(row["total"])), Decimal("3300"))   # 1000 ×1.1 ×3

    def test_custom_nested_pekerjaan_bundle_propagates(self):
        from .services import _populate_expanded_from_raw
        from .models import DetailAHSPExpanded, VolumePekerjaan
        # Inner pekerjaan with a base component.
        inner = self._pekerjaan("INNER")
        DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=inner, harga_item=self._hip("BHN-2", "BHN", 50),
            kategori="BHN", kode="BHN-2", uraian="Pasir", satuan="kg", koefisien=Decimal("4"),
        )
        _populate_expanded_from_raw(self.project, inner)
        # Outer pekerjaan bundling inner.
        outer = self._pekerjaan("OUTER")
        DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=outer, harga_item=self._hip("INNER", "LAIN"),
            kategori="LAIN", kode=inner.snapshot_kode, uraian="Bundle inner", satuan="ls",
            koefisien=Decimal("1"), ref_pekerjaan=inner,
        )
        _populate_expanded_from_raw(self.project, outer)
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=outer, quantity=Decimal("1"))
        # Outer's expanded must contain the inner base component (nested propagation).
        outer_bhn = DetailAHSPExpanded.objects.filter(
            project=self.project, pekerjaan=outer, kategori="BHN"
        ).first()
        self.assertIsNotNone(outer_bhn, "nested bundle must propagate inner base component to outer")
        # Price the propagated component and confirm it flows into the rekap total.
        outer_bhn.harga_item.harga_satuan = Decimal("50")
        outer_bhn.harga_item.save(update_fields=["harga_satuan"])
        row = self._rekap_row(outer)
        self.assertIsNotNone(row)
        self.assertGreater(Decimal(str(row["total"])), Decimal("0"))
