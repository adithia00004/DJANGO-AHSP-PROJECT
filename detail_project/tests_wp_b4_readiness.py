"""WP-B4 inc-2.1 — Canonical readiness service contract tests.

Locks the hardened contract: null-vs-zero (volume absent vs zero, price NULL vs
zero), per-source_detail expansion analysis (partial & stale), rich traceable
diagnostic entries, live jadwal signals, and live recomputation under
value-only ``QuerySet.update()`` mutations.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from dashboard.models import Project

TEST_MIDDLEWARE = [
    m for m in settings.MIDDLEWARE if m != "config.middleware.timeout.TimeoutMiddleware"
]

from .models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    VolumePekerjaan,
)
from .readiness import PENDING_SIGNALS, compute_project_readiness, source_signature


class ReadinessContractTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="b4-readiness-owner", password="not-used"
        )
        self.project = Project.objects.create(owner=self.owner, nama="B4 Readiness")
        klas = Klasifikasi.objects.create(
            project=self.project, name="K", ordering_index=1
        )
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self._order = 0

    # ----- helpers -------------------------------------------------------
    def _pekerjaan(self, kode):
        self._order += 1
        return Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode=kode,
            snapshot_uraian=f"Pekerjaan {kode}",
            snapshot_satuan="m2",
            ordering_index=self._order,
        )

    def _item(self, kode, harga):
        return HargaItemProject.objects.create(
            project=self.project,
            kode_item=kode,
            kategori="BHN",
            uraian=f"Bahan {kode}",
            satuan="kg",
            harga_satuan=harga,
        )

    def _detail(self, pekerjaan, item, koef="2.000000", expand=True):
        src = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            harga_item=item,
            kategori="BHN",
            kode=item.kode_item,
            uraian=item.uraian,
            satuan="kg",
            koefisien=Decimal(koef),
        )
        if expand:
            DetailAHSPExpanded.objects.create(
                project=self.project,
                pekerjaan=pekerjaan,
                source_detail=src,
                harga_item=item,
                kategori="BHN",
                kode=item.kode_item,
                uraian=item.uraian,
                satuan="kg",
                koefisien=Decimal(koef),
                expansion_depth=0,
                # mirror production: stamp the source signature at expansion time.
                source_signature=source_signature(
                    "BHN", item.kode_item, Decimal(koef), None, None, item.id
                ),
            )
        return src

    def _volume(self, pekerjaan, qty):
        return VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=pekerjaan, quantity=Decimal(qty)
        )

    def _weekly(self, pekerjaan, week_number, planned, start="2026-01-01", end="2026-01-07"):
        return PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            week_number=week_number,
            week_start_date=date.fromisoformat(start),
            week_end_date=date.fromisoformat(end),
            planned_proportion=Decimal(str(planned)),
        )

    # ----- jadwal signals: incomplete / allocation-without-volume / stale (inc-4a)
    def test_incomplete_planned_allocation_flags_partial_only(self):
        p_partial = self._pekerjaan("P-PART")
        p_full = self._pekerjaan("P-FULL")
        p_unsched = self._pekerjaan("P-UNSCHED")
        self._volume(p_partial, "1.000")
        self._volume(p_full, "1.000")
        self._volume(p_unsched, "1.000")
        self._weekly(p_partial, 1, "60.00")            # 60% < 100 → incomplete
        self._weekly(p_full, 1, "40.00")
        self._weekly(p_full, 2, "60.00")               # 100% → complete
        # p_unsched has no weekly rows (Σ=0) → excluded

        r = compute_project_readiness(self.project)
        flagged = {e["pekerjaan_id"] for e in r["incomplete_planned_allocation"]}

        self.assertIn(p_partial.id, flagged)
        self.assertNotIn(p_full.id, flagged)
        self.assertNotIn(p_unsched.id, flagged)  # not scheduled ≠ incomplete
        entry = next(e for e in r["incomplete_planned_allocation"] if e["pekerjaan_id"] == p_partial.id)
        self.assertEqual(entry["actual"], "60.00")
        self.assertEqual(entry["source_page"], "jadwal")

    def test_incomplete_planned_allocation_honors_one_basis_point_tolerance(self):
        p_tolerated = self._pekerjaan("P-99-99")
        p_incomplete = self._pekerjaan("P-99-98")
        self._volume(p_tolerated, "1.000")
        self._volume(p_incomplete, "1.000")
        self._weekly(p_tolerated, 1, "99.99")
        self._weekly(p_incomplete, 1, "99.98")

        flagged = {
            e["pekerjaan_id"]
            for e in compute_project_readiness(self.project)[
                "incomplete_planned_allocation"
            ]
        }

        self.assertNotIn(p_tolerated.id, flagged)
        self.assertIn(p_incomplete.id, flagged)

    def test_allocation_without_volume_flags_scheduled_without_capacity(self):
        p_novol = self._pekerjaan("P-NOVOL")    # scheduled, no volume row
        p_zerovol = self._pekerjaan("P-ZEROVOL")  # scheduled, volume 0
        p_ok = self._pekerjaan("P-OK")          # scheduled, has volume
        self._zerovol = self._volume(p_zerovol, "0.000")
        self._volume(p_ok, "5.000")
        self._weekly(p_novol, 1, "50.00")
        self._weekly(p_zerovol, 1, "50.00")
        self._weekly(p_ok, 1, "50.00")

        r = compute_project_readiness(self.project)
        flagged = {e["pekerjaan_id"] for e in r["allocation_without_volume"]}

        self.assertIn(p_novol.id, flagged)
        self.assertIn(p_zerovol.id, flagged)
        self.assertNotIn(p_ok.id, flagged)
        entry = next(
            e
            for e in r["allocation_without_volume"]
            if e["pekerjaan_id"] == p_novol.id
        )
        self.assertEqual(
            entry["source_table"],
            "PekerjaanProgressWeekly+VolumePekerjaan",
        )

    def test_timeline_stale_only_when_week_outside_project_window(self):
        self.project.tanggal_mulai = date(2026, 1, 1)
        self.project.tanggal_selesai = date(2026, 1, 31)
        self.project.save(update_fields=["tanggal_mulai", "tanggal_selesai"])
        p = self._pekerjaan("P-1")
        self._volume(p, "1.000")
        self._weekly(p, 1, "50.00", start="2026-01-01", end="2026-01-07")  # in-window

        self.assertFalse(compute_project_readiness(self.project)["timeline_stale"])

        # Add a week ending in February — outside the project window.
        self._weekly(p, 5, "50.00", start="2026-02-01", end="2026-02-07")

        self.assertTrue(compute_project_readiness(self.project)["timeline_stale"])

    def test_timeline_stale_detects_week_before_project_start(self):
        self.project.tanggal_mulai = date(2026, 1, 8)
        self.project.tanggal_selesai = date(2026, 1, 31)
        self.project.save(update_fields=["tanggal_mulai", "tanggal_selesai"])
        p = self._pekerjaan("P-BEFORE")
        self._volume(p, "1.000")
        self._weekly(p, 1, "100.00", start="2026-01-01", end="2026-01-07")

        self.assertTrue(compute_project_readiness(self.project)["timeline_stale"])

    def test_jadwal_signals_index_into_affected_pekerjaan(self):
        p = self._pekerjaan("P-1")  # scheduled partial, no volume
        self._weekly(p, 1, "30.00")

        r = compute_project_readiness(self.project)

        self.assertIn(p.id, r["affected_pekerjaan"])

    # ----- missing_volume: absent row vs explicit zero -------------------
    def test_missing_volume_flags_absent_row_only(self):
        p_no_vol = self._pekerjaan("P-NOVOL")
        p_zero = self._pekerjaan("P-ZERO")
        p_val = self._pekerjaan("P-VAL")
        self._volume(p_zero, "0.000")  # explicit zero — intentional, NOT missing
        self._volume(p_val, "3.000")

        r = compute_project_readiness(self.project)
        flagged = {e["pekerjaan_id"] for e in r["missing_volume"]}

        self.assertIn(p_no_vol.id, flagged)
        self.assertNotIn(p_zero.id, flagged)
        self.assertNotIn(p_val.id, flagged)

    def test_missing_volume_entry_is_traceable(self):
        p = self._pekerjaan("P-NOVOL")
        r = compute_project_readiness(self.project)
        entry = next(e for e in r["missing_volume"] if e["pekerjaan_id"] == p.id)
        self.assertEqual(entry["kode"], "P-NOVOL")
        self.assertEqual(entry["uraian"], "Pekerjaan P-NOVOL")
        self.assertEqual(entry["source_table"], "VolumePekerjaan")
        self.assertEqual(entry["source_page"], "volume")
        self.assertEqual(entry["issue"], "missing_volume")

    # ----- missing_price: NULL vs explicit zero --------------------------
    def test_missing_price_flags_null_not_zero(self):
        p = self._pekerjaan("P-1")
        item_null = self._item("BHN-NULL", None)  # belum diisi
        item_zero = self._item("BHN-ZERO", Decimal("0.00"))  # explicit free
        item_set = self._item("BHN-SET", Decimal("100.00"))
        self._detail(p, item_null)
        self._detail(p, item_zero)
        self._detail(p, item_set)

        r = compute_project_readiness(self.project)
        flagged = {e["kode"] for e in r["missing_price"]}

        self.assertIn("BHN-NULL", flagged)
        self.assertNotIn("BHN-ZERO", flagged)
        self.assertNotIn("BHN-SET", flagged)
        entry = next(e for e in r["missing_price"] if e["kode"] == "BHN-NULL")
        self.assertEqual(entry["affected_pekerjaan"], [p.id])
        self.assertEqual(entry["uraian"], "Bahan BHN-NULL")
        self.assertEqual(entry["source_table"], "HargaItemProject")
        self.assertEqual(entry["source_page"], "harga_items")

    def test_missing_price_uses_raw_fallback_when_no_expanded(self):
        p = self._pekerjaan("P-RAWONLY")
        item_null = self._item("BHN-NULL", None)
        self._detail(p, item_null, expand=False)

        r = compute_project_readiness(self.project)

        self.assertIn("BHN-NULL", {e["kode"] for e in r["missing_price"]})

    # ----- expansion: per-source_detail (partial & stale) ----------------
    def test_partial_expansion_flags_unexpanded_raw_row(self):
        # The dangerous D-06 case: job HAS one expanded row, so it is in the
        # calc's expanded set, but a second raw row was never expanded.
        p = self._pekerjaan("P-PARTIAL")
        item_a = self._item("BHN-A", Decimal("100.00"))
        item_b = self._item("BHN-B", Decimal("50.00"))
        self._detail(p, item_a, expand=True)
        src_b = self._detail(p, item_b, expand=False)  # unexpanded

        r = compute_project_readiness(self.project)

        self.assertFalse(r["expanded_ready"])
        flagged = {
            (e["source_detail_id"], e["issue"]) for e in r["expansion_not_ready"]
        }
        self.assertIn((src_b.id, "missing_expansion"), flagged)

    def test_stale_expansion_flags_raw_newer_than_expansion(self):
        p = self._pekerjaan("P-STALE")
        item = self._item("BHN-1", Decimal("100.00"))
        src = self._detail(p, item, expand=True)
        # Re-save the raw row so its updated_at moves past its expansion's.
        src.koefisien = Decimal("3.000000")
        src.save(update_fields=["koefisien", "updated_at"])

        r = compute_project_readiness(self.project)

        issues = {
            (e["source_detail_id"], e["issue"]) for e in r["expansion_not_ready"]
        }
        self.assertIn((src.id, "stale_expansion"), issues)
        self.assertFalse(r["expanded_ready"])

    def test_stale_expansion_detected_via_signature_bypassing_updated_at(self):
        # inc-4b: a value-only QuerySet.update() bypasses auto_now (updated_at
        # unchanged) and does not re-expand. The old updated_at heuristic would
        # MISS this; the content signature catches it.
        p = self._pekerjaan("P-BYPASS")
        item = self._item("BHN-1", Decimal("100.00"))
        src = self._detail(p, item, koef="2.000000", expand=True)

        DetailAHSPProject.objects.filter(id=src.id).update(koefisien=Decimal("9.000000"))

        r = compute_project_readiness(self.project)
        issues = {
            (e["source_detail_id"], e["issue"]) for e in r["expansion_not_ready"]
        }
        self.assertIn((src.id, "stale_expansion"), issues)
        self.assertFalse(r["expanded_ready"])

    def test_fresh_expansion_signature_matches_not_stale(self):
        p = self._pekerjaan("P-FRESH")
        item = self._item("BHN-1", Decimal("100.00"))
        self._detail(p, item, koef="2.000000", expand=True)

        r = compute_project_readiness(self.project)

        self.assertTrue(r["expanded_ready"])
        self.assertEqual(r["expansion_not_ready"], [])

    def test_direct_harga_item_change_is_detected_as_stale(self):
        p = self._pekerjaan("P-ITEM-SWAP")
        old_item = self._item("BHN-OLD", Decimal("100.00"))
        new_item = self._item("BHN-NEW", Decimal("200.00"))
        src = self._detail(p, old_item, koef="2.000000", expand=True)

        DetailAHSPProject.objects.filter(id=src.id).update(harga_item_id=new_item.id)

        issues = {
            (e["source_detail_id"], e["issue"])
            for e in compute_project_readiness(self.project)["expansion_not_ready"]
        }
        self.assertIn((src.id, "stale_expansion"), issues)

    def test_mixed_expansion_signatures_are_detected_as_stale(self):
        p = self._pekerjaan("P-MIXED-SIG")
        item = self._item("BHN-1", Decimal("100.00"))
        src = self._detail(p, item, koef="2.000000", expand=True)
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=p,
            source_detail=src,
            harga_item=item,
            kategori="BHN",
            kode=item.kode_item,
            uraian=item.uraian,
            satuan="kg",
            koefisien=Decimal("2.000000"),
            expansion_depth=0,
            source_signature="0" * 40,
        )

        issues = {
            (e["source_detail_id"], e["issue"])
            for e in compute_project_readiness(self.project)["expansion_not_ready"]
        }
        self.assertIn((src.id, "stale_expansion"), issues)

    def test_expanded_ready_true_when_all_fresh_and_complete(self):
        p = self._pekerjaan("P-OK")
        item = self._item("BHN-1", Decimal("100.00"))
        self._detail(p, item, expand=True)
        self._volume(p, "1.000")

        r = compute_project_readiness(self.project)

        self.assertTrue(r["expanded_ready"])
        self.assertEqual(r["expansion_not_ready"], [])

    def test_expansion_entry_carries_expected_actual(self):
        p = self._pekerjaan("P-RAW")
        item = self._item("BHN-1", Decimal("100.00"))
        src = self._detail(p, item, expand=False)  # direct row → expected 1

        r = compute_project_readiness(self.project)
        entry = next(
            e for e in r["expansion_not_ready"] if e["source_detail_id"] == src.id
        )
        self.assertEqual(entry["expected"], 1)
        self.assertEqual(entry["actual"], 0)
        self.assertEqual(entry["source_page"], "template_ahsp")

    # ----- invalid coefficient (defensive) ------------------------------
    def test_invalid_coefficient_flags_negative(self):
        p = self._pekerjaan("P-1")
        item = self._item("BHN-1", Decimal("100.00"))
        self._detail(p, item, expand=False)
        DetailAHSPProject.objects.filter(pekerjaan=p).update(koefisien=Decimal("-1"))

        r = compute_project_readiness(self.project)

        entry = next(
            (e for e in r["invalid_coefficient"] if e["pekerjaan_id"] == p.id), None
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["actual"], "-1.000000000000")
        self.assertEqual(entry["source_table"], "DetailAHSPProject")

    def test_invalid_coefficient_empty_for_clean_project(self):
        p = self._pekerjaan("P-1")
        item = self._item("BHN-1", Decimal("100.00"))
        self._detail(p, item, expand=True)

        r = compute_project_readiness(self.project)

        self.assertEqual(r["invalid_coefficient"], [])

    # ----- jadwal signals empty/false when nothing scheduled (live, inc-4a) ----
    def test_jadwal_signals_empty_when_unscheduled(self):
        r = compute_project_readiness(self.project)

        self.assertEqual(r["incomplete_planned_allocation"], [])
        self.assertEqual(r["allocation_without_volume"], [])
        self.assertFalse(r["timeline_stale"])
        self.assertEqual(r["pending_signals"], [])
        self.assertEqual(list(PENDING_SIGNALS), [])

    # ----- traceability union -------------------------------------------
    def test_affected_pekerjaan_indexes_all_causes(self):
        p_novol = self._pekerjaan("P-NOVOL")
        p_price = self._pekerjaan("P-PRICE")
        item_null = self._item("BHN-NULL", None)
        self._detail(p_price, item_null)
        self._volume(p_price, "1.000")

        r = compute_project_readiness(self.project)

        self.assertIn(p_novol.id, r["affected_pekerjaan"])
        self.assertIn(p_price.id, r["affected_pekerjaan"])

    def test_empty_project_is_ready(self):
        r = compute_project_readiness(self.project)

        self.assertTrue(r["expanded_ready"])
        self.assertEqual(r["missing_volume"], [])
        self.assertEqual(r["missing_price"], [])
        self.assertEqual(r["affected_pekerjaan"], [])
        self.assertEqual(r["affected_items"], [])
        self.assertEqual(r["incomplete_planned_allocation"], [])
        self.assertEqual(r["allocation_without_volume"], [])
        self.assertFalse(r["timeline_stale"])
        self.assertEqual(r["schema_version"], "b4.4")

    # ----- affected_items canonical index (Master Plan minimum contract) -
    def test_affected_items_is_canonical_item_index(self):
        p = self._pekerjaan("P1")
        item = self._item("BHN-NULL", None)
        self._detail(p, item)

        r = compute_project_readiness(self.project)

        self.assertIn(
            {"harga_item_id": item.id, "kode": "BHN-NULL"}, r["affected_items"]
        )

    # ----- bundle expansion completeness (expected/actual) --------------
    def test_bundle_incomplete_expansion_flagged(self):
        # Referenced pekerjaan A has 2 expanded components.
        a = self._pekerjaan("A")
        ia1 = self._item("A-1", Decimal("10.00"))
        ia2 = self._item("A-2", Decimal("20.00"))
        self._detail(a, ia1, expand=True)
        self._detail(a, ia2, expand=True)
        # Bundle pekerjaan B references A but only 1 of the 2 components expanded.
        b = self._pekerjaan("B")
        bundle_item = HargaItemProject.objects.create(
            project=self.project, kode_item="LAIN-A", kategori="LAIN",
            uraian="Bundle A", satuan="ls", harga_satuan=Decimal("0.00"),
        )
        bundle = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=b, harga_item=bundle_item,
            kategori="LAIN", kode="LAIN-A", uraian="Bundle A", satuan=None,
            koefisien=Decimal("1.000000"), ref_pekerjaan=a,
        )
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=b, source_detail=bundle, harga_item=ia1,
            kategori="BHN", kode="A-1", uraian="x", satuan="kg",
            koefisien=Decimal("10.000000"), expansion_depth=1,
        )

        r = compute_project_readiness(self.project)
        entry = next(
            (e for e in r["expansion_not_ready"] if e["source_detail_id"] == bundle.id),
            None,
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["issue"], "incomplete_expansion")
        self.assertEqual(entry["expected"], 2)
        self.assertEqual(entry["actual"], 1)
        self.assertFalse(r["expanded_ready"])

    def test_direct_excess_expansion_is_not_ready(self):
        p = self._pekerjaan("P-EXCESS")
        item = self._item("BHN-EXCESS", Decimal("10.00"))
        src = self._detail(p, item, expand=True)
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=p,
            source_detail=src,
            harga_item=item,
            kategori="BHN",
            kode="BHN-EXCESS-DUP",
            uraian="Komponen berlebih",
            satuan="kg",
            koefisien=Decimal("1.000000"),
            expansion_depth=0,
            source_signature=source_signature(
                src.kategori,
                src.kode,
                src.koefisien,
                src.ref_pekerjaan_id,
                src.ref_ahsp_id,
                src.harga_item_id,
            ),
        )

        r = compute_project_readiness(self.project)
        entry = next(
            e
            for e in r["expansion_not_ready"]
            if e["source_detail_id"] == src.id
        )
        self.assertEqual(entry["issue"], "excess_expansion")
        self.assertEqual(entry["expected"], 1)
        self.assertEqual(entry["actual"], 2)
        self.assertFalse(r["expanded_ready"])

    # ----- no cross-request cache: value-only bulk mutations reflected ---
    def test_bulk_update_negative_coef_is_reflected(self):
        p = self._pekerjaan("P-1")
        item = self._item("BHN-1", Decimal("100.00"))
        self._detail(p, item, expand=False)

        self.assertEqual(compute_project_readiness(self.project)["invalid_coefficient"], [])
        DetailAHSPProject.objects.filter(pekerjaan=p).update(koefisien=Decimal("-5"))
        self.assertTrue(
            any(
                e["pekerjaan_id"] == p.id
                for e in compute_project_readiness(self.project)["invalid_coefficient"]
            )
        )

    def test_relation_move_updates_affected_set_no_stale(self):
        # The digest-collision case: swap which detail row points at the NULL-price
        # item. Row counts and HargaItemProject null-count are unchanged, so a
        # count/sum digest would not change — a cache keyed on it would go stale.
        p1 = self._pekerjaan("P1")
        p2 = self._pekerjaan("P2")
        priced = self._item("BHN-PRICED", Decimal("100.00"))
        nullitem = self._item("BHN-NULL", None)
        d1 = self._detail(p1, priced, expand=False)
        d2 = self._detail(p2, nullitem, expand=False)

        first = compute_project_readiness(self.project)
        mp = next(e for e in first["missing_price"] if e["kode"] == "BHN-NULL")
        self.assertEqual(mp["affected_pekerjaan"], [p2.id])

        # Move the FK relations (counts identical, only the target changes).
        DetailAHSPProject.objects.filter(id=d1.id).update(harga_item=nullitem)
        DetailAHSPProject.objects.filter(id=d2.id).update(harga_item=priced)

        second = compute_project_readiness(self.project)
        mp2 = next(e for e in second["missing_price"] if e["kode"] == "BHN-NULL")
        self.assertEqual(mp2["affected_pekerjaan"], [p1.id])

    # ----- performance: bounded, constant query count (no N+1) ----------
    def test_query_budget_constant_no_n_plus_1(self):
        def seed(n, prefix):
            for i in range(n):
                p = self._pekerjaan(f"{prefix}{i}")
                it = self._item(f"{prefix}I{i}", Decimal("100.00"))
                self._detail(p, it, expand=True)
                self._volume(p, "1.000")

        seed(2, "A")
        with CaptureQueriesContext(connection) as c1:
            compute_project_readiness(self.project)
        seed(8, "B")
        with CaptureQueriesContext(connection) as c2:
            compute_project_readiness(self.project)

        self.assertEqual(
            len(c1.captured_queries),
            len(c2.captured_queries),
            "readiness query count must not grow with project size (N+1)",
        )
        self.assertLessEqual(len(c2.captured_queries), 12)

    def test_request_scoped_memoization(self):
        class _Req:
            pass

        self._pekerjaan("P-1")
        # Two calls sharing one request must cost the same as a single fresh call
        # (the second is served from the request-scoped memo).
        req = _Req()
        with CaptureQueriesContext(connection) as two_calls:
            compute_project_readiness(self.project, request=req)
            compute_project_readiness(self.project, request=req)
        req2 = _Req()
        with CaptureQueriesContext(connection) as one_call:
            compute_project_readiness(self.project, request=req2)
        self.assertGreater(len(one_call.captured_queries), 0)
        self.assertEqual(
            len(two_calls.captured_queries), len(one_call.captured_queries)
        )


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RekapRabReadinessWiringTests(TestCase):
    """WP-B4 inc-3 pilot: api_get_rekap_rab surfaces the canonical readiness
    schema (display-only) instead of the page recomputing it."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="b4-wire-owner", password="not-used"
        )
        self.project = Project.objects.create(owner=self.owner, nama="B4 Wire")
        klas = Klasifikasi.objects.create(
            project=self.project, name="K", ordering_index=1
        )
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="P-001",
            snapshot_uraian="Pekerjaan wiring",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        # Item with NULL price (belum diisi) used by the pekerjaan; no volume row.
        self.item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="BHN-NULL",
            kategori="BHN",
            uraian="Bahan belum diisi",
            satuan="kg",
            harga_satuan=None,
        )
        src = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=self.item,
            kategori="BHN",
            kode="BHN-NULL",
            uraian="Bahan belum diisi",
            satuan="kg",
            koefisien=Decimal("2.000000"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=src,
            harga_item=self.item,
            kategori="BHN",
            kode="BHN-NULL",
            uraian="Bahan belum diisi",
            satuan="kg",
            koefisien=Decimal("2.000000"),
            expansion_depth=0,
        )
        self.client.force_login(self.owner)
        self.url = reverse(
            "detail_project:api_get_rekap_rab",
            kwargs={"project_id": self.project.id},
        )
        self.page_url = reverse(
            "detail_project:rekap_rab",
            kwargs={"project_id": self.project.id},
        )

    def test_response_includes_readiness_schema(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertIn("readiness", body)
        self.assertEqual(body["readiness"]["schema_version"], "b4.4")

    def test_readiness_reflects_missing_price_and_volume(self):
        body = self.client.get(self.url).json()
        readiness = body["readiness"]
        self.assertIn("BHN-NULL", {e["kode"] for e in readiness["missing_price"]})
        self.assertIn(
            self.pekerjaan.id, {e["pekerjaan_id"] for e in readiness["missing_volume"]}
        )
        # Jadwal-derived signals are live (inc-4a); no schedule here → not stale.
        self.assertFalse(readiness["timeline_stale"])
        self.assertEqual(readiness["pending_signals"], [])

    def test_dedicated_readiness_endpoint(self):
        # WP-B4 inc-3: dedicated GET for consumers that don't load /rekap/
        # (Template AHSP, Jadwal, Rekap Kebutuhan).
        url = reverse(
            "detail_project:api_get_readiness",
            kwargs={"project_id": self.project.id},
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["readiness"]["schema_version"], "b4.4")
        self.assertIn("BHN-NULL", {e["kode"] for e in body["readiness"]["missing_price"]})

    def test_dedicated_readiness_endpoint_is_owner_scoped(self):
        other = get_user_model().objects.create_user(
            username="b4-readiness-other",
            password="not-used",
        )
        self.client.force_login(other)
        url = reverse(
            "detail_project:api_get_readiness",
            kwargs={"project_id": self.project.id},
        )

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_dedicated_readiness_endpoint_requires_login(self):
        self.client.logout()
        url = reverse(
            "detail_project:api_get_readiness",
            kwargs={"project_id": self.project.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_banner_builder_loads_synchronously_before_rekap_script(self):
        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200, response.content)
        html = response.content.decode()
        banner_pos = html.index("js/shared/readiness_banner.js")
        rekap_pos = html.index("js/rekap_rab.js")

        self.assertLess(banner_pos, rekap_pos)
        banner_tag_start = html.rfind("<script", 0, banner_pos)
        banner_tag_end = html.index(">", banner_pos)
        banner_tag = html[banner_tag_start : banner_tag_end + 1]
        self.assertNotIn('type="module"', banner_tag)
