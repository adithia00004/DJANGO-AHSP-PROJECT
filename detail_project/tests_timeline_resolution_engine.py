"""Langkah 1.2 — matriks mesin resolusi timeline.

Gate untuk `timeline_utils.plan_timeline_resolution` + `apply_project_timeline_change`.
Setiap test yang commit-nya sukses ikut menegakkan invariant doc 39 §6:

* I-A  `timeline_stale == False`
* I-B  jumlah kolom chart == jumlah minggu jendela baru
* I-C  tidak ada baris di luar jendela
* I-D  total planned per pekerjaan <= 100%
* I-F  realisasi tidak berubah kecuali operasi ditolak

Tracker: `Review/R5_Detail_Project/39_Timeline_Change_Implementation_Tracker_20260824.md`
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project

from .models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    VolumePekerjaan,
)
from .progress_utils import build_week_buckets
from .readiness import compute_project_readiness
from .timeline_utils import (
    TimelineChangeError,
    apply_project_timeline_change,
    expected_week_count,
)


TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'config.middleware.timeout.TimeoutMiddleware'
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class TimelineResolutionEngineTests(TestCase):
    """Proyek 1 Jan – 28 Feb 2026 = 9 minggu kanonik (bucket berakhir Minggu)."""

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            'timeline-engine',
            password='StrongPass123!',
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama='Timeline Engine',
            sumber_dana='APBD',
            lokasi_project='Makassar',
            nama_client='Dinas PUPR',
            anggaran_owner=Decimal('1000000'),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 2, 28),
        )
        klas = Klasifikasi.objects.create(project=self.project, name='K', ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name='S', ordering_index=1
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode='P1',
            snapshot_uraian='Pekerjaan 1',
            snapshot_satuan='m2',
            ordering_index=1,
        )
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, quantity=100
        )
        self.client.force_login(self.owner)

    # ------------------------------------------------------------------ utils

    def _buckets(self, start=None, end=None):
        return build_week_buckets(
            start or self.project.tanggal_mulai,
            end or self.project.tanggal_selesai,
            self.project.week_end_day,
        )

    def _seed(self, week_number, planned='0', actual='0', actual_cost=None,
              pekerjaan=None):
        """Buat baris weekly pada bucket kanonik ke-`week_number` saat ini."""
        buckets = {num: (s, e) for num, s, e in self._buckets()}
        start, end = buckets[week_number]
        return PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=pekerjaan or self.pekerjaan,
            week_number=week_number,
            week_start_date=start,
            week_end_date=end,
            planned_proportion=Decimal(planned),
            actual_proportion=Decimal(actual),
            actual_cost=actual_cost,
        )

    def _rows(self):
        return list(
            PekerjaanProgressWeekly.objects
            .filter(project=self.project)
            .order_by('week_number')
        )

    def _total_planned(self):
        return sum(
            (row.planned_proportion for row in self._rows()), Decimal('0.00')
        )

    def _apply(self, new_start, new_end, resolution):
        return apply_project_timeline_change(
            self.project, new_start, new_end, resolution=resolution, user=self.owner
        )

    def _assert_invariants(self, new_start, new_end):
        """I-A, I-C, I-D — dijalankan setelah setiap commit yang sukses."""
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, new_start)
        self.assertEqual(self.project.tanggal_selesai, new_end)

        # I-C — tidak ada baris di luar jendela baru.
        outside = PekerjaanProgressWeekly.objects.filter(project=self.project).exclude(
            week_start_date__gte=new_start, week_end_date__lte=new_end
        )
        self.assertFalse(
            outside.exists(),
            f'I-C dilanggar: {list(outside.values("week_number", "week_start_date", "week_end_date"))}',
        )

        # I-A — jadwal tidak basi setelah perubahan yang sukses (menutup T-06).
        self.assertFalse(
            compute_project_readiness(self.project)['timeline_stale'],
            'I-A dilanggar: timeline_stale masih true setelah commit sukses.',
        )

        # I-D — batas kuantitas.
        totals = {}
        for row in self._rows():
            self.assertLessEqual(row.planned_proportion, Decimal('100.00'))
            totals[row.pekerjaan_id] = (
                totals.get(row.pekerjaan_id, Decimal('0.00')) + row.planned_proportion
            )
        for total in totals.values():
            self.assertLessEqual(total, Decimal('100.00'))

        # Nomor minggu tetap berada di dalam rentang bucket baru.
        expected_numbers = {num for num, _, _ in self._buckets(new_start, new_end)}
        for row in self._rows():
            self.assertIn(row.week_number, expected_numbers)

    # -------------------------------------------------------------- baseline

    def test_baseline_project_has_nine_canonical_weeks(self):
        self.assertEqual(len(self._buckets()), 9)
        self.assertEqual(
            expected_week_count(
                self.project.tanggal_mulai,
                self.project.tanggal_selesai,
                self.project.week_end_day,
            ),
            9,
        )

    # ----------------------------------------------------------- keep_ordinal

    def test_keep_ordinal_start_shift_same_duration_is_lossless(self):
        """Skenario doc 38 §6.1 #5 — sekarang buntu, setelah ini terbuka."""
        self._seed(1, planned='10')
        self._seed(2, planned='15')
        before = self._total_planned()

        new_start, new_end = date(2026, 1, 8), date(2026, 3, 7)
        self._apply(new_start, new_end, 'keep_ordinal')

        self._assert_invariants(new_start, new_end)
        self.assertEqual(self._total_planned(), before)

        rows = {row.week_number: row for row in self._rows()}
        self.assertEqual(rows[1].planned_proportion, Decimal('10.00'))
        self.assertEqual(rows[2].planned_proportion, Decimal('15.00'))
        # Nomor minggu bertahan; hanya tanggalnya yang bergeser.
        self.assertEqual(rows[1].week_start_date, date(2026, 1, 8))
        self.assertEqual(rows[2].week_start_date, date(2026, 1, 12))

    def test_keep_ordinal_drops_overflow_when_duration_shrinks(self):
        """Keputusan owner G0-2: luapan DIHAPUS, bukan ditumpuk.

        `keep_ordinal` hanya ditawarkan saat tanggal mulai bergeser (doc 37 §4.6),
        jadi kasus "durasi memendek" diuji lewat pergeseran mulai + ujung dimajukan:
        1 Jan–28 Feb (9 minggu) menjadi 8–31 Jan (4 minggu).
        """
        self._seed(1, planned='10')
        self._seed(2, planned='15')
        self._seed(8, planned='40')

        new_start, new_end = date(2026, 1, 8), date(2026, 1, 31)
        self._apply(new_start, new_end, 'keep_ordinal')

        self._assert_invariants(new_start, new_end)
        self.assertEqual(len(self._buckets(new_start, new_end)), 4)
        self.assertFalse(
            PekerjaanProgressWeekly.objects.filter(
                project=self.project, week_number=8
            ).exists(),
            'G0-2: minggu ke-8 melampaui jendela baru dan harus dihapus.',
        )
        # Total berkurang sebesar luapan yang dibuang — bukan "utuh".
        self.assertEqual(self._total_planned(), Decimal('25.00'))
        rows = {row.week_number: row for row in self._rows()}
        self.assertEqual(rows[1].week_start_date, date(2026, 1, 8))
        self.assertEqual(rows[1].planned_proportion, Decimal('10.00'))

    # -------------------------------------------------------- accumulate_edge

    def test_accumulate_edge_preserves_total_when_end_shortens(self):
        self._seed(1, planned='10')
        self._seed(2, planned='15')
        self._seed(8, planned='40')
        before = self._total_planned()

        new_start, new_end = date(2026, 1, 1), date(2026, 1, 31)
        self._apply(new_start, new_end, 'accumulate_edge')

        self._assert_invariants(new_start, new_end)
        self.assertEqual(
            self._total_planned(), before,
            'accumulate_edge hanya memindahkan nilai; total harus terjaga.',
        )
        last_number = self._buckets(new_start, new_end)[-1][0]
        rows = {row.week_number: row for row in self._rows()}
        self.assertEqual(rows[last_number].planned_proportion, Decimal('40.00'))

    def test_accumulate_edge_merges_rows_into_first_week_on_start_shift(self):
        """Beberapa baris sumber menuju satu sel tujuan — uji merge + UNIQUE."""
        self._seed(1, planned='10')   # 01–04 Jan, seluruhnya sebelum jendela baru
        self._seed(2, planned='15')   # 05–11 Jan, tumpang tindih 08–11 Jan
        before = self._total_planned()

        new_start, new_end = date(2026, 1, 8), date(2026, 3, 7)
        self._apply(new_start, new_end, 'accumulate_edge')

        self._assert_invariants(new_start, new_end)
        self.assertEqual(self._total_planned(), before)
        rows = {row.week_number: row for row in self._rows()}
        self.assertEqual(
            rows[1].planned_proportion, Decimal('25.00'),
            'Kedua baris harus menyatu di minggu pertama jendela baru.',
        )

    def test_accumulate_eight_weeks_into_one_hits_exactly_one_hundred(self):
        """Doc 37 §9 skenario 12 — batas 100% tidak boleh dilanggar."""
        for week_number in range(1, 9):
            self._seed(week_number, planned='12.50')
        self.assertEqual(self._total_planned(), Decimal('100.00'))

        new_start, new_end = date(2026, 1, 1), date(2026, 1, 4)
        self._apply(new_start, new_end, 'accumulate_edge')

        self._assert_invariants(new_start, new_end)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].planned_proportion, Decimal('100.00'))

    # ------------------------------------------------------------ follow_date

    def test_follow_date_drops_rows_outside_and_leaves_inside_untouched(self):
        self._seed(1, planned='10')
        self._seed(2, planned='15')
        self._seed(8, planned='40')

        new_start, new_end = date(2026, 1, 1), date(2026, 1, 31)
        self._apply(new_start, new_end, 'follow_date')

        self._assert_invariants(new_start, new_end)
        rows = {row.week_number: row for row in self._rows()}
        self.assertEqual(rows[1].planned_proportion, Decimal('10.00'))
        self.assertEqual(rows[2].planned_proportion, Decimal('15.00'))
        self.assertEqual(self._total_planned(), Decimal('25.00'))

    def test_follow_date_splits_partial_week_by_day_overlap(self):
        """Bucket lama tidak sejajar bucket baru — dibagi per hari tumpang tindih.

        Baris minggu 2 (05–11 Jan, 7 hari) hanya 4 hari berada di jendela baru
        yang mulai 08 Jan. 15.00 x 4/7 = 8.571… -> 8.57 dengan sisa terbesar.
        """
        self._seed(2, planned='15')

        new_start, new_end = date(2026, 1, 8), date(2026, 3, 7)
        self._apply(new_start, new_end, 'follow_date')

        self._assert_invariants(new_start, new_end)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].week_number, 1)
        self.assertEqual(rows[0].planned_proportion, Decimal('8.57'))

    # ------------------------------------------------------- gerbang realisasi

    def test_start_shift_with_actual_anywhere_is_blocked(self):
        """K-1 baris 3 — realisasi di mana pun memblokir pergeseran tanggal mulai."""
        self._seed(1, planned='10', actual='8')

        with self.assertRaises(TimelineChangeError) as ctx:
            self._apply(date(2026, 1, 8), date(2026, 3, 7), 'keep_ordinal')

        self.assertEqual(
            ctx.exception.impact.get('blocking_reason'), 'actual_present_start_shift'
        )
        self.assertEqual(ctx.exception.impact.get('blocking_week_numbers'), [1])

        # I-F — tidak ada mutasi.
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 1, 1))
        row = self._rows()[0]
        self.assertEqual(row.actual_proportion, Decimal('8.00'))
        self.assertEqual(row.week_start_date, date(2026, 1, 1))

    def test_end_shorten_with_actual_in_affected_week_is_blocked(self):
        """K-1 baris 2 — hanya realisasi di minggu terdampak yang memblokir."""
        self._seed(8, planned='40', actual='30')

        with self.assertRaises(TimelineChangeError) as ctx:
            self._apply(date(2026, 1, 1), date(2026, 1, 31), 'follow_date')

        self.assertEqual(
            ctx.exception.impact.get('blocking_reason'), 'actual_out_of_window'
        )
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=8).actual_proportion,
            Decimal('30.00'),
        )

    def test_end_shorten_with_actual_only_inside_window_is_allowed(self):
        """K-1 baris 2 — realisasi di dalam jendela tidak menghalangi."""
        self._seed(1, planned='10', actual='8')
        self._seed(8, planned='40')

        new_start, new_end = date(2026, 1, 1), date(2026, 1, 31)
        self._apply(new_start, new_end, 'follow_date')

        self._assert_invariants(new_start, new_end)
        # I-F — realisasi di dalam jendela tidak tersentuh.
        row = PekerjaanProgressWeekly.objects.get(
            project=self.project, week_number=1
        )
        self.assertEqual(row.actual_proportion, Decimal('8.00'))

    def test_shortening_days_inside_final_week_preserves_actual_and_cost(self):
        """Weekly values remain intact when the final bucket only loses days."""
        self._seed(9, planned='20', actual='30', actual_cost=Decimal('5000'))
        new_start, new_end = date(2026, 1, 1), date(2026, 2, 25)  # Wed, still week 9
        result = self._apply(new_start, new_end, 'none')

        self.assertEqual(result['actual_records'], 0)
        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=9)
        self.assertEqual(row.actual_proportion, Decimal('30.00'))
        self.assertEqual(row.actual_cost, Decimal('5000'))
        self.assertEqual(row.week_start_date, date(2026, 2, 23))
        self.assertEqual(row.week_end_date, new_end)

    def test_extending_final_partial_week_aligns_row_dates_and_keeps_values(self):
        """Adding days through Fri expands the same week without moving progress."""
        self.project.tanggal_selesai = date(2026, 2, 25)
        self.project.durasi_hari = (date(2026, 2, 25) - self.project.tanggal_mulai).days + 1
        self.project.save(update_fields=['tanggal_selesai', 'durasi_hari', 'updated_at'])
        self._seed(9, planned='20', actual='30', actual_cost=Decimal('5000'))
        before_duration = self.project.durasi_hari
        new_start, new_additional_end = date(2026, 1, 1), date(2026, 2, 27)  # Fri, same week
        result = apply_project_timeline_change(
            self.project,
            new_start,
            new_additional_end,
            resolution='none',
            target_field='tanggal_akhir_tambahan',
            expected_revision=self.project.schedule_revision,
            user=self.owner,
        )

        self.assertEqual(result['new_week_count'], 9)
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 25))
        self.assertEqual(self.project.tanggal_akhir_tambahan, new_additional_end)
        self.assertEqual(self.project.durasi_hari, before_duration)
        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=9)
        self.assertEqual(row.actual_proportion, Decimal('30.00'))
        self.assertEqual(row.actual_cost, Decimal('5000'))
        self.assertEqual(row.week_end_date, new_additional_end)
        from detail_project.models import DetailAHSPAudit
        audit = DetailAHSPAudit.objects.filter(project=self.project).latest('id')
        self.assertEqual(
            audit.old_data['rows_before'][0]['week_end_date'],
            date(2026, 2, 25).isoformat(),
        )

    # ------------------------------------------------------- kombinasi ilegal

    def test_resolution_outside_allowed_list_is_rejected(self):
        """Doc 37 §6 — preview tidak bisa dipakai menyelundupkan resolusi."""
        self._seed(1, planned='10')

        # Tanggal selesai diperpendek tanpa planned terdampak -> hanya 'none' sah.
        with self.assertRaises(TimelineChangeError) as ctx:
            self._apply(date(2026, 1, 1), date(2026, 2, 22), 'keep_ordinal')

        self.assertNotIn('keep_ordinal', ctx.exception.impact['allowed_resolutions'])
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))

    def test_unknown_resolution_is_rejected(self):
        with self.assertRaises(TimelineChangeError):
            self._apply(date(2026, 1, 1), date(2026, 1, 31), 'obliterate')

    # ------------------------------------------------------- post-condition R-6

    def test_guard_blocks_when_preexisting_rows_exceed_one_hundred(self):
        """R-6 — batas <= 100% diperiksa, bukan diasumsikan.

        Baris seperti ini dapat lahir dari copy service atau migrasi canonical
        yang tidak melewati `api_assign_pekerjaan_weekly`.
        """
        self._seed(1, planned='80')
        self._seed(8, planned='70')

        with self.assertRaises(TimelineChangeError) as ctx:
            self._apply(date(2026, 1, 1), date(2026, 1, 31), 'accumulate_edge')

        self.assertEqual(
            ctx.exception.impact.get('blocking_reason'), 'quantity_limit_exceeded'
        )
        # Tidak ada mutasi: baris lama utuh.
        self.assertEqual(len(self._rows()), 2)
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))

    # ------------------------------------------------------------- audit + I-B

    def test_audit_stores_full_row_snapshot(self):
        """Doc 37 §4.8 — snapshot penuh, bukan hanya nilai planned lama."""
        from .models import DetailAHSPAudit

        self._seed(8, planned='40')
        self._apply(date(2026, 1, 1), date(2026, 1, 31), 'follow_date')

        audit = DetailAHSPAudit.objects.filter(
            project=self.project, pekerjaan__isnull=True
        ).order_by('-id').first()
        self.assertIsNotNone(audit)
        snapshot = audit.old_data.get('rows_before') or []
        self.assertTrue(snapshot)
        entry = next(r for r in snapshot if r['week_number'] == 8)
        for field in (
            'pekerjaan_id', 'week_number', 'week_start_date', 'week_end_date',
            'planned_proportion', 'actual_proportion', 'actual_cost',
        ):
            self.assertIn(field, entry)
        self.assertEqual(entry['planned_proportion'], '40.00')
        self.assertEqual(entry['week_start_date'], '2026-02-16')

    def test_chart_columns_match_new_window_after_resolution(self):
        """I-B end-to-end — inti T-06: kolom sisa tidak boleh tertinggal."""
        self._seed(1, planned='10')
        self._seed(8, planned='40')

        new_start, new_end = date(2026, 1, 1), date(2026, 1, 31)
        self._apply(new_start, new_end, 'follow_date')
        self._assert_invariants(new_start, new_end)

        response = self.client.get(
            reverse(
                'detail_project:api_chart_data',
                kwargs={'project_id': self.project.id},
            ),
            {'timescale': 'weekly'},
        )
        self.assertEqual(response.status_code, 200, response.content)
        columns = response.json().get('columns', [])
        self.assertEqual(
            len(columns), len(self._buckets(new_start, new_end)),
            'I-B dilanggar: jumlah kolom chart tidak sama dengan jumlah minggu '
            'jendela baru — kolom sisa masih dipadding dari week_number tertinggi.',
        )
        self.assertEqual(len(columns), 5)

    # -------------------------------------------- pembersihan minggu kosong

    def test_none_cleans_empty_rows_left_outside_the_window(self):
        """Doc 38 §6.1 #2 — minggu terbuang yang kosong dibereskan tanpa dialog."""
        self._seed(1, planned='10')
        self._seed(8, planned='0')       # kolom sisa yang kosong

        new_start, new_end = date(2026, 1, 1), date(2026, 1, 31)
        self._apply(new_start, new_end, 'none')

        self._assert_invariants(new_start, new_end)
        self.assertFalse(
            PekerjaanProgressWeekly.objects.filter(
                project=self.project, week_number=8
            ).exists(),
            'Baris kosong di luar jendela harus hilang, bukan menyisakan kolom.',
        )
        self.assertEqual(self._total_planned(), Decimal('10.00'))

    def test_none_never_touches_rows_that_carry_data(self):
        """Pembersihan hanya untuk baris tanpa data — realisasi tetap memblokir."""
        self._seed(8, planned='0', actual='5')

        with self.assertRaises(TimelineChangeError) as ctx:
            self._apply(date(2026, 1, 1), date(2026, 1, 31), 'none')

        self.assertEqual(
            ctx.exception.impact.get('blocking_reason'), 'actual_out_of_window'
        )
        self.assertTrue(
            PekerjaanProgressWeekly.objects.filter(
                project=self.project, week_number=8
            ).exists()
        )

    def test_trim_planned_still_leaves_its_zeroed_row(self):
        """Jalur legacy TIDAK ikut dibersihkan — kontraknya dipertahankan."""
        self._seed(8, planned='40')

        self._apply(date(2026, 1, 1), date(2026, 1, 31), 'trim_planned')

        row = PekerjaanProgressWeekly.objects.get(
            project=self.project, week_number=8
        )
        self.assertEqual(row.planned_proportion, Decimal('0.00'))
        self.assertEqual(row.week_start_date, date(2026, 2, 16))

    # ------------------------------------------------- instance yang sudah kotor

    def test_analysis_ignores_dates_already_mutated_in_memory(self):
        """Regresi: `ModelForm.is_valid()` menempelkan tanggal baru ke instance.

        Pemanggil yang meneruskan `form.instance` membawa tanggal BARU di
        atributnya. Bila tanggal lama dibaca dari atribut itu, `start_changed`
        selalu False dan gerbang realisasi memilih cabang yang salah — pergeseran
        tanggal mulai lolos diperlakukan sebagai perubahan tanggal selesai.
        """
        from .timeline_utils import analyze_project_timeline_change

        self._seed(1, planned='10', actual='8')

        # Tiru keadaan setelah `form.is_valid()`: atribut sudah tanggal baru,
        # baris database masih tanggal lama.
        self.project.tanggal_mulai = date(2026, 1, 8)
        self.project.tanggal_selesai = date(2026, 3, 7)

        impact = analyze_project_timeline_change(
            self.project, date(2026, 1, 8), date(2026, 3, 7)
        )

        self.assertTrue(impact['start_changed'])
        self.assertEqual(impact['old_start'], '2026-01-01')
        self.assertEqual(impact['blocking_reason'], 'actual_present_start_shift')
        self.assertEqual(
            impact['allowed_resolutions'], [],
            'Operasi yang diblokir tidak boleh menawarkan resolusi apa pun.',
        )

    # ----------------------------------------------------------- proyek kosong

    def test_empty_project_rebuilds_silently(self):
        new_start, new_end = date(2026, 2, 1), date(2026, 3, 31)
        result = self._apply(new_start, new_end, 'none')

        self.assertEqual(result['resolution'], 'none')
        self._assert_invariants(new_start, new_end)
