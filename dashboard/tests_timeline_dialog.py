"""Langkah 2.1 — dialog pilihan penataan minggu di form edit project.

Menutup dua hal sekaligus:

* dialog dampak dengan tabel nilai lama -> baru dan hanya opsi yang sah;
* **G-5** — `project_edit` mengirim `expected_revision`, kunci optimistik yang
  sebelumnya hanya dipakai jalur API. Dialog justru memperlebar jendela waktu
  antara analisis dan commit, jadi kuncinya wajib ada di sini.

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
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    VolumePekerjaan,
)
from detail_project.progress_utils import build_week_buckets


TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'config.middleware.timeout.TimeoutMiddleware'
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class TimelineDialogTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            'timeline-dialog',
            password='StrongPass123!',
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama='Proyek Dialog',
            sumber_dana='APBD',
            lokasi_project='Makassar',
            nama_client='Dinas PUPR',
            anggaran_owner=Decimal('1000000'),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 2, 28),
        )
        klas = Klasifikasi.objects.create(
            project=self.project, name='K', ordering_index=1
        )
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
        self.url = reverse('dashboard:project_edit', kwargs={'pk': self.project.pk})

    # ------------------------------------------------------------------ helpers

    def _seed(self, week_number, planned='0', actual='0'):
        buckets = {
            num: (start, end)
            for num, start, end in build_week_buckets(
                self.project.tanggal_mulai,
                self.project.tanggal_selesai,
                self.project.week_end_day,
            )
        }
        start, end = buckets[week_number]
        return PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            week_number=week_number,
            week_start_date=start,
            week_end_date=end,
            planned_proportion=Decimal(planned),
            actual_proportion=Decimal(actual),
        )

    def _payload(self, **overrides):
        data = {
            'nama': self.project.nama,
            'tanggal_mulai': '2026-01-01',
            'tanggal_selesai': '2026-02-28',
            'sumber_dana': 'APBD',
            'lokasi_project': 'Makassar',
            'nama_client': 'Dinas PUPR',
            'anggaran_owner': '1000000',
            'timeline_revision': str(self.project.schedule_revision),
        }
        data.update(overrides)
        return data

    # ------------------------------------------------------------------- render

    def test_get_renders_revision_key(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="timeline_revision"')

    # ------------------------------------------------------- dialog vs tersimpan

    def test_post_without_resolution_renders_dialog_and_saves_nothing(self):
        self._seed(1, planned='10')
        self._seed(8, planned='40')

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
        ))

        self.assertEqual(response.status_code, 200)
        previews = response.context['timeline_previews']
        self.assertIsNotNone(previews, 'Dialog harus ter-render.')
        offered = [item['resolution'] for item in previews]
        self.assertEqual(offered, ['accumulate_edge', 'follow_date'])

        # Opsi yang tidak sah tidak boleh muncul.
        self.assertNotIn('keep_ordinal', offered)
        self.assertNotIn('trim_planned', offered)

        # Tidak ada yang tersimpan.
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=8).planned_proportion,
            Decimal('40.00'),
        )

    def test_dialog_shows_old_and_new_values_per_week(self):
        self._seed(1, planned='10')
        self._seed(8, planned='40')

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
        ))

        preview = next(
            item for item in response.context['timeline_previews']
            if item['resolution'] == 'follow_date'
        )
        weeks = {week['week_number']: week for week in preview['weeks']}

        # Minggu 8 hilang dari jendela baru dan nilainya jadi 0.
        self.assertFalse(weeks[8]['exists_after'])
        self.assertEqual(weeks[8]['planned_before'], Decimal('40.00'))
        self.assertEqual(weeks[8]['planned_after'], Decimal('0.00'))
        # Minggu 1 tidak tersentuh.
        self.assertEqual(weeks[1]['planned_before'], Decimal('10.00'))
        self.assertEqual(weeks[1]['planned_after'], Decimal('10.00'))

        # K-2: kehilangan ditampilkan eksplisit, bukan disimpulkan user.
        self.assertEqual(preview['total_planned_before'], Decimal('50.00'))
        self.assertEqual(preview['total_planned_after'], Decimal('10.00'))
        self.assertEqual(preview['planned_lost'], Decimal('40.00'))

    def test_accumulate_preview_reports_no_loss(self):
        self._seed(8, planned='40')

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
        ))
        preview = next(
            item for item in response.context['timeline_previews']
            if item['resolution'] == 'accumulate_edge'
        )
        self.assertEqual(preview['planned_lost'], Decimal('0.00'))

    def test_post_with_resolution_saves(self):
        self._seed(1, planned='10')
        self._seed(8, planned='40')

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
            timeline_resolution='accumulate_edge',
        ))

        self.assertEqual(response.status_code, 302, getattr(response, 'content', b''))
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 1, 31))

        rows = PekerjaanProgressWeekly.objects.filter(project=self.project)
        self.assertFalse(rows.filter(week_end_date__gt=date(2026, 1, 31)).exists())
        total = sum((row.planned_proportion for row in rows), Decimal('0.00'))
        self.assertEqual(total, Decimal('50.00'), 'accumulate_edge menjaga total.')

    def test_start_shift_offers_three_options(self):
        self._seed(1, planned='10')

        response = self.client.post(self.url, self._payload(
            tanggal_mulai='2026-01-08',
            tanggal_selesai='2026-03-07',
        ))

        offered = [item['resolution'] for item in response.context['timeline_previews']]
        self.assertEqual(
            offered, ['keep_ordinal', 'accumulate_edge', 'follow_date']
        )
        self.assertEqual(
            response.context['timeline_impact']['recommended_resolution'],
            'keep_ordinal',
        )

    def test_safe_change_saves_without_dialog(self):
        """Perpanjangan ujung tanpa progress terdampak: tidak ada dialog."""
        self._seed(1, planned='10')

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-03-31',
        ))

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 3, 31))

    # --------------------------------------------------------- gerbang realisasi

    def test_start_shift_with_actual_is_refused_with_reason(self):
        self._seed(1, planned='10', actual='8')

        response = self.client.post(self.url, self._payload(
            tanggal_mulai='2026-01-08',
            tanggal_selesai='2026-03-07',
        ))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['timeline_previews'])
        self.assertContains(response, 'sudah memiliki')
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 1, 1))

    # ---------------------------------------------------------------- G-5

    def test_stale_revision_is_rejected_without_mutation(self):
        self._seed(8, planned='40')
        stale = self.project.schedule_revision

        # Tab lain mengubah jadwal lebih dulu.
        self.project.tanggal_selesai = date(2026, 3, 31)
        self.project.save()
        self.project.refresh_from_db()
        self.assertGreater(self.project.schedule_revision, stale)

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
            timeline_resolution='accumulate_edge',
            timeline_revision=str(stale),
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Muat ulang halaman')
        self.project.refresh_from_db()
        self.assertEqual(
            self.project.tanggal_selesai, date(2026, 3, 31),
            'Perubahan basi tidak boleh menimpa jadwal yang sudah berubah.',
        )
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=8).planned_proportion,
            Decimal('40.00'),
        )

    def test_current_revision_is_accepted(self):
        self._seed(8, planned='40')

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
            timeline_resolution='accumulate_edge',
            timeline_revision=str(self.project.schedule_revision),
        ))

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 1, 31))

    def test_dialog_rerender_preserves_the_revision_key(self):
        """Kunci tidak boleh 'menyegarkan diri' saat user memilih resolusi."""
        self._seed(8, planned='40')
        original = self.project.schedule_revision

        response = self.client.post(self.url, self._payload(
            tanggal_selesai='2026-01-31',
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['timeline_revision'], original)
