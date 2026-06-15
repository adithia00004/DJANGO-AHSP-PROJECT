"""WP-B6 inc-B6b — compute_kebutuhan_timeline canonical weekly distribution.

Locks: distribution from PekerjaanProgressWeekly.planned_proportion (not
TahapPelaksanaan overlap-day), unscheduled bucket, four-week aggregation (compat
alias for month_range), tahapan-mode deprecated (no quantity effect), and the
core parity invariant: Σ all periods + unscheduled = total per item.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project

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
from .services import (
    _build_time_scope_multiplier,
    compute_kebutuhan_timeline,
    get_project_period_options,
)


class KebutuhanTimelineCanonicalTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b6b-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B6b Kebutuhan")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self._order = 0

    def _pekerjaan(self, kode):
        self._order += 1
        return Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode=kode,
            snapshot_uraian=f"P {kode}", snapshot_satuan="m2", ordering_index=self._order,
        )

    def _item_detail(self, pekerjaan, kode_item, koef, harga, volume):
        item = HargaItemProject.objects.create(
            project=self.project, kode_item=kode_item, kategori="BHN",
            uraian=f"Bahan {kode_item}", satuan="kg", harga_satuan=Decimal(str(harga)),
        )
        src = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pekerjaan, harga_item=item,
            kategori="BHN", kode=kode_item, uraian=item.uraian, satuan="kg",
            koefisien=Decimal(str(koef)),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=pekerjaan, source_detail=src,
            harga_item=item, kategori="BHN", kode=kode_item, uraian=item.uraian,
            satuan="kg", koefisien=Decimal(str(koef)), expansion_depth=0,
        )
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=pekerjaan, quantity=Decimal(str(volume))
        )
        return item

    def _weekly(self, pekerjaan, week_number, planned, start, end):
        return PekerjaanProgressWeekly.objects.create(
            project=self.project, pekerjaan=pekerjaan, week_number=week_number,
            week_start_date=date.fromisoformat(start), week_end_date=date.fromisoformat(end),
            planned_proportion=Decimal(str(planned)),
        )

    @staticmethod
    def _qty_by_item(result):
        """Sum quantity_decimal per (kategori, kode) across ALL periods."""
        agg = defaultdict(Decimal)
        for period in result["periods"]:
            for it in period["items"]:
                agg[(it["kategori"], it["kode"])] += Decimal(str(it["quantity_decimal"]))
        return agg

    def test_weekly_distribution_uses_planned_proportion(self):
        p = self._pekerjaan("P1")
        self._item_detail(p, "BHN-1", koef=2, harga=100, volume=10)  # base = 20
        self._weekly(p, 1, "60.00", "2026-01-01", "2026-01-07")
        self._weekly(p, 2, "40.00", "2026-01-08", "2026-01-14")

        result = compute_kebutuhan_timeline(self.project)
        by_value = {pr["value"]: pr for pr in result["periods"]}

        self.assertIn("week_1", by_value)
        self.assertIn("week_2", by_value)
        w1 = next(i for i in by_value["week_1"]["items"] if i["kode"] == "BHN-1")
        w2 = next(i for i in by_value["week_2"]["items"] if i["kode"] == "BHN-1")
        self.assertEqual(Decimal(str(w1["quantity_decimal"])), Decimal("12"))  # 20×0.6
        self.assertEqual(Decimal(str(w2["quantity_decimal"])), Decimal("8"))   # 20×0.4

    def test_parity_sum_periods_plus_unscheduled_equals_total(self):
        p1 = self._pekerjaan("P1")
        self._item_detail(p1, "BHN-1", koef=2, harga=100, volume=10)  # base 20, scheduled 100%
        self._weekly(p1, 1, "60.00", "2026-01-01", "2026-01-07")
        self._weekly(p1, 2, "40.00", "2026-01-08", "2026-01-14")
        p2 = self._pekerjaan("P2")
        self._item_detail(p2, "BHN-2", koef=3, harga=50, volume=4)   # base 12, partial 50%
        self._weekly(p2, 1, "50.00", "2026-01-01", "2026-01-07")
        p3 = self._pekerjaan("P3")
        self._item_detail(p3, "BHN-3", koef=1, harga=10, volume=7)   # base 7, NO schedule

        agg = self._qty_by_item(compute_kebutuhan_timeline(self.project))
        self.assertEqual(agg[("BHN", "BHN-1")], Decimal("20"))
        self.assertEqual(agg[("BHN", "BHN-2")], Decimal("12"))
        self.assertEqual(agg[("BHN", "BHN-3")], Decimal("7"))

    def test_unscheduled_bucket_holds_remainder_and_unscheduled_jobs(self):
        p2 = self._pekerjaan("P2")
        self._item_detail(p2, "BHN-2", koef=3, harga=50, volume=4)   # base 12
        self._weekly(p2, 1, "50.00", "2026-01-01", "2026-01-07")     # 50% scheduled
        p3 = self._pekerjaan("P3")
        self._item_detail(p3, "BHN-3", koef=1, harga=10, volume=7)   # base 7, unscheduled

        result = compute_kebutuhan_timeline(self.project)
        unsched = next(pr for pr in result["periods"] if pr["value"] == "unscheduled")
        by_kode = {i["kode"]: Decimal(str(i["quantity_decimal"])) for i in unsched["items"]}
        self.assertEqual(by_kode["BHN-2"], Decimal("6"))   # 12 × 0.5 remainder
        self.assertEqual(by_kode["BHN-3"], Decimal("7"))   # fully unscheduled

    def test_four_week_aggregation_is_compat_alias_for_month_range(self):
        p = self._pekerjaan("P1")
        self._item_detail(p, "BHN-1", koef=1, harga=100, volume=100)  # base 100
        monday = date(2026, 1, 5)
        for wk in range(1, 6):  # 5 weeks @ 20% each → 100%
            start = monday + timedelta(days=(wk - 1) * 7)
            end = start + timedelta(days=6)
            self._weekly(p, wk, "20.00", start.isoformat(), end.isoformat())

        result = compute_kebutuhan_timeline(
            self.project, time_scope={"mode": "month_range", "start": "2026-01", "end": "2026-02"}
        )
        self.assertEqual(result["meta"]["bucket_mode"], "four_week")
        self.assertEqual(result["meta"]["compat_mode"], "month_range")
        values = {pr["value"] for pr in result["periods"]}
        self.assertIn("period4_1", values)  # weeks 1-4
        self.assertIn("period4_2", values)  # week 5

    def test_period_options_are_canonical_without_tahapan(self):
        p = self._pekerjaan("P1")
        self._item_detail(p, "BHN-1", koef=1, harga=100, volume=100)
        monday = date(2026, 1, 5)
        for wk in range(1, 6):
            start = monday + timedelta(days=(wk - 1) * 7)
            end = start + timedelta(days=6)
            self._weekly(p, wk, "20.00", start.isoformat(), end.isoformat())

        periods = get_project_period_options(self.project)
        self.assertEqual(
            [w["value"] for w in periods["weeks"]],
            ["week_1", "week_2", "week_3", "week_4", "week_5"],
        )
        self.assertEqual(
            [m["value"] for m in periods["months"]],
            ["period4_1", "period4_2"],
        )

    def test_canonical_time_scope_filters_periods(self):
        p = self._pekerjaan("P1")
        self._item_detail(p, "BHN-1", koef=1, harga=100, volume=100)
        monday = date(2026, 1, 5)
        for wk in range(1, 4):
            start = monday + timedelta(days=(wk - 1) * 7)
            end = start + timedelta(days=6)
            self._weekly(p, wk, "20.00", start.isoformat(), end.isoformat())

        result = compute_kebutuhan_timeline(
            self.project,
            time_scope={"mode": "week_range", "start": "week_2", "end": "week_2"},
        )
        values = {pr["value"] for pr in result["periods"]}
        self.assertIn("week_2", values)
        self.assertNotIn("week_1", values)
        self.assertNotIn("week_3", values)

    def test_tahapan_mode_is_deprecated_same_quantity_as_all(self):
        p = self._pekerjaan("P1")
        self._item_detail(p, "BHN-1", koef=2, harga=100, volume=10)
        self._weekly(p, 1, "100.00", "2026-01-01", "2026-01-07")

        all_agg = self._qty_by_item(compute_kebutuhan_timeline(self.project, mode="all"))
        tah = compute_kebutuhan_timeline(self.project, mode="tahapan", tahapan_id=999)
        tah_agg = self._qty_by_item(tah)

        self.assertEqual(all_agg, tah_agg)  # Tahapan does not change quantity
        self.assertEqual(tah["meta"]["deprecated_mode"], "tahapan")
        self.assertEqual(tah["meta"]["deprecated_tahapan_id"], 999)

    # ----- B6f part 1: snapshot scope multiplier uses canonical weekly dist -----
    def test_scope_multiplier_uses_canonical_weekly_fractions(self):
        p = self._pekerjaan("P1")
        self._item_detail(p, "BHN-1", koef=1, harga=100, volume=10)
        self._weekly(p, 1, "60.00", "2026-01-05", "2026-01-11")
        self._weekly(p, 2, "40.00", "2026-01-12", "2026-01-18")

        # Window covering only week 1 → fraction in scope = 0.60.
        only_w1 = _build_time_scope_multiplier(
            self.project, [p.id],
            {"mode": "week_range", "start_date": date(2026, 1, 5), "end_date": date(2026, 1, 11)},
        )
        self.assertEqual(only_w1[p.id], Decimal("0.60"))

        # Window covering both weeks → 1.00.
        both = _build_time_scope_multiplier(
            self.project, [p.id],
            {"mode": "week_range", "start_date": date(2026, 1, 5), "end_date": date(2026, 1, 18)},
        )
        self.assertEqual(both[p.id], Decimal("1.00"))

    def test_scope_multiplier_unscheduled_is_fully_in_scope(self):
        p = self._pekerjaan("P1")  # no weekly rows
        self._item_detail(p, "BHN-1", koef=1, harga=100, volume=10)
        res = _build_time_scope_multiplier(
            self.project, [p.id],
            {"mode": "week_range", "start_date": date(2026, 1, 5), "end_date": date(2026, 1, 11)},
        )
        self.assertEqual(res[p.id], Decimal("1.0"))  # legacy edge preserved

    def test_scope_multiplier_empty_for_all_scope(self):
        p = self._pekerjaan("P1")
        self.assertEqual(_build_time_scope_multiplier(self.project, [p.id], {"mode": "all"}), {})
