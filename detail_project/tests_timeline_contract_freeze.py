"""Contract freeze untuk perubahan timeline proyek (mula-mula langkah 1.1).

Dibuat di langkah 1.1 untuk MENGUNCI PERILAKU LAMA sebelum apa pun diubah, agar
setiap perubahan muncul sebagai diff yang disengaja. Isi file ini menyusut seiring
langkah berjalan — itu memang tujuannya.

Yang tersisa sekarang:

* **T-03** — dua lock pada jalur DEFAULT (`resolution='none'`). Masih benar:
  langkah 1.2 membuka jalan keluar lewat resolusi eksplisit, bukan dengan
  melonggarkan jalur default.
* **T-06** — lock pada jalur LEGACY `trim_planned`, permanen (lihat docstring-nya).
* **K-1** — kontrak permanen: perpanjangan tanggal selesai tetap diizinkan
  meski ada realisasi.

Yang sudah pindah:

* **T-01 dan T-02** dibalik di langkah 1.3 menjadi test perilaku baru di
  `tests_timeline_mass_edit_safety.py`.

Perilaku resolusi mesin diuji di `tests_timeline_resolution_engine.py`.

Tracker: `Review/R5_Detail_Project/39_Timeline_Change_Implementation_Tracker_20260824.md`
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from dashboard.models import Project

from .models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    VolumePekerjaan,
)
from .readiness import compute_project_readiness
from .timeline_utils import TimelineChangeError, apply_project_timeline_change


TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'config.middleware.timeout.TimeoutMiddleware'
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class TimelineContractFreezeTests(TestCase):
    """Baseline perilaku 2026-08-24, sebelum mesin resolusi dibangun."""

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            'timeline-freeze',
            password='StrongPass123!',
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = self._create_project('Timeline Freeze')
        self.pekerjaan = self._create_pekerjaan(self.project)
        self.client.force_login(self.owner)

    # ------------------------------------------------------------------ helpers

    def _create_project(self, nama):
        return Project.objects.create(
            owner=self.owner,
            nama=nama,
            sumber_dana='APBD',
            lokasi_project='Makassar',
            nama_client='Dinas PUPR',
            anggaran_owner=Decimal('1000000'),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 2, 28),
        )

    def _create_pekerjaan(self, project):
        klas = Klasifikasi.objects.create(project=project, name='K', ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=project, klasifikasi=klas, name='S', ordering_index=1
        )
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode='P1',
            snapshot_uraian='Pekerjaan 1',
            snapshot_satuan='m2',
            ordering_index=1,
        )
        VolumePekerjaan.objects.create(
            project=project, pekerjaan=pekerjaan, quantity=100
        )
        return pekerjaan

    def _weekly(self, pekerjaan, week_number, start, end, planned='0', actual='0',
                actual_cost=None):
        return PekerjaanProgressWeekly.objects.create(
            project=pekerjaan.project,
            pekerjaan=pekerjaan,
            week_number=week_number,
            week_start_date=start,
            week_end_date=end,
            planned_proportion=Decimal(planned),
            actual_proportion=Decimal(actual),
            actual_cost=actual_cost,
        )

    # ------------------------------------------------------------------- T-03

    def test_lock_t03_start_change_with_any_progress_is_rejected(self):
        """LOCK PERILAKU LAMA (T-03) — dilonggarkan di langkah 1.2.

        `start_requires_policy` menolak setiap perubahan tanggal mulai pada proyek
        yang punya progress apa pun, tanpa menawarkan jalan keluar. Langkah 1.2
        membuka jalan keluar itu lewat resolusi eksplisit.
        """
        self._weekly(self.pekerjaan, 1, date(2026, 1, 1), date(2026, 1, 4),
                     planned='10')

        with self.assertRaises(TimelineChangeError) as ctx:
            apply_project_timeline_change(
                self.project,
                date(2026, 1, 8),
                date(2026, 3, 7),
                resolution='none',
                user=self.owner,
            )

        self.assertTrue(ctx.exception.impact.get('start_requires_policy'))

        # Tidak ada mutasi sama sekali.
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 1, 1))
        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=1)
        self.assertEqual(row.planned_proportion, Decimal('10.00'))
        self.assertEqual(row.week_start_date, date(2026, 1, 1))

    def test_lock_t03_start_change_rejected_even_when_only_actual_exists(self):
        """LOCK PERILAKU LAMA (T-03) — dilonggarkan di langkah 1.2.

        `start_requires_policy` menghitung baris nonzero apa pun, jadi realisasi
        saja sudah cukup untuk memblokir — bahkan sebelum gerbang `actual_records`
        sempat dievaluasi.
        """
        self._weekly(self.pekerjaan, 1, date(2026, 1, 1), date(2026, 1, 4),
                     planned='0', actual='5')

        with self.assertRaises(TimelineChangeError) as ctx:
            apply_project_timeline_change(
                self.project,
                date(2026, 1, 8),
                date(2026, 3, 7),
                resolution='none',
                user=self.owner,
            )

        self.assertTrue(ctx.exception.impact.get('start_requires_policy'))
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 1, 1))

    # ------------------------------------------------------------ G0-1 / K-1

    def test_contract_end_extension_with_actual_stays_allowed(self):
        """KONTRAK PERMANEN (G0-1 / K-1) — harus tetap hijau setelah langkah 1.2.

        Berbeda dari test LOCK lain di file ini, yang ini BUKAN perilaku cacat
        yang menunggu dibalik. Ini kemampuan yang wajib dipertahankan.

        Memperpanjang `tanggal_selesai` tanpa menggeser `tanggal_mulai` tidak
        dapat memindahkan baris mana pun: batas minggu dijangkar ke tanggal mulai
        yang tidak berubah, dan minggu baru hanya ditambahkan di ujung. Karena itu
        realisasi tidak mungkin bergerak, dan operasi ini harus tetap diizinkan
        meski proyek sudah punya realisasi — ini kasus "proyek molor, tenggat
        diundur" yang paling sering terjadi.

        Lihat doc 39 §0 K-1 baris 1.
        """
        self._weekly(self.pekerjaan, 1, date(2026, 1, 1), date(2026, 1, 4),
                     planned='10', actual='8')

        result = apply_project_timeline_change(
            self.project,
            date(2026, 1, 1),
            date(2026, 3, 31),
            resolution='none',
            user=self.owner,
        )

        self.assertEqual(result['actual_records'], 0)
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 3, 31))

        # Realisasi tidak tersentuh oleh perpanjangan.
        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=1)
        self.assertEqual(row.actual_proportion, Decimal('8.00'))

    # ------------------------------------------------------------------- T-06

    def test_lock_t06_trim_planned_leaves_stale_rows_behind(self):
        """LOCK JALUR LEGACY (T-06) — permanen, TIDAK dibalik.

        `trim_planned` hanya menulis `planned_proportion=0`; baris beserta tanggal
        lamanya tetap ada, sehingga `timeline_stale` menjadi true tepat setelah
        perubahan yang sukses.

        Doc 37 §6 mensyaratkan `none` dan `trim_planned` mempertahankan artinya
        persis, supaya `tests_timeline_crud_hardening.py` tetap hijau tanpa
        dimodifikasi. T-06 karena itu ditutup oleh resolusi MESIN
        (`keep_ordinal` / `accumulate_edge` / `follow_date`) yang menuntaskan
        nasib setiap baris — lihat `tests_timeline_resolution_engine.py`, yang
        meng-assert `timeline_stale == False` setelah setiap commit sukses.

        `trim_planned` sendiri disupersede oleh `follow_date` dan tidak lagi
        ditawarkan di UI setelah Fase 2; test ini mengunci sisa jalur API-nya.
        """
        self._weekly(self.pekerjaan, 8, date(2026, 2, 16), date(2026, 2, 22),
                     planned='40')

        self.assertFalse(compute_project_readiness(self.project)['timeline_stale'])

        apply_project_timeline_change(
            self.project,
            date(2026, 1, 1),
            date(2026, 1, 31),
            resolution='trim_planned',
            user=self.owner,
        )

        row = PekerjaanProgressWeekly.objects.get(project=self.project, week_number=8)
        self.assertEqual(row.planned_proportion, Decimal('0.00'))
        self.assertEqual(
            row.week_start_date, date(2026, 2, 16),
            'LOCK T-06: baris di luar jendela hanya di-nol-kan, tanggalnya tidak '
            'dibereskan.',
        )

        self.project.refresh_from_db()
        self.assertTrue(
            compute_project_readiness(self.project)['timeline_stale'],
            'LOCK T-06: jadwal menjadi basi tepat setelah perubahan yang sukses. '
            'Langkah 1.2 harus membuat assertion ini gagal (timeline_stale == False).',
        )
