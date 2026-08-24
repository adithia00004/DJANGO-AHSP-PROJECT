"""Langkah 3.1 — tombol Jadwal menjadi perbaikan terpandu.

Dulu "Perbarui Struktur Waktu" permanen di toolbar dan langsung memutasi tanpa
analisis dampak (T-04), sekaligus tidak mampu membereskan baris di luar jendela
yang justru satu-satunya alasan ia dibutuhkan (T-06).

Sekarang: alert kondisional berbasis `readiness.timeline_stale`, klik memanggil
`timeline/preview`, dan perbaikan dilakukan lewat `timeline/commit`.

Tracker: `Review/R5_Detail_Project/39_Timeline_Change_Implementation_Tracker_20260824.md`
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

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


TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'config.middleware.timeout.TimeoutMiddleware'
]

BASE_DIR = Path(settings.BASE_DIR)
TEMPLATE = BASE_DIR / 'detail_project/templates/detail_project/kelola_tahapan_grid_modern.html'
REPAIR_JS = BASE_DIR / 'detail_project/static/detail_project/js/shared/timeline_repair.js'
AUTOLOAD_JS = BASE_DIR / 'detail_project/static/detail_project/js/shared/readiness_autoload.js'


class TimelineRepairSourceGuardTests(TestCase):
    """Guard sumber: jalur buta tidak boleh diam-diam terpasang lagi."""

    def test_blind_regenerate_button_is_gone_from_the_toolbar(self):
        source = TEMPLATE.read_text(encoding='utf-8')
        self.assertNotIn(
            'id="btn-regenerate-timeline"', source,
            'T-04: tombol regenerate buta tidak boleh kembali ke toolbar.',
        )

    def test_repair_host_is_wired_to_preview_and_commit(self):
        source = TEMPLATE.read_text(encoding='utf-8')
        self.assertIn('id="kt-timeline-repair"', source)
        self.assertIn('data-preview-url', source)
        self.assertIn('data-commit-url', source)
        # Tersembunyi sampai server menyatakan basi.
        self.assertIn('id="kt-timeline-repair" class="d-none"', source)
        self.assertIn('shared/timeline_repair.js', source)

    def test_repair_script_gates_on_the_server_signal_only(self):
        source = REPAIR_JS.read_text(encoding='utf-8')
        self.assertIn('readiness.timeline_stale', source)
        self.assertIn("host.className = 'd-none'", source)
        # Preview dulu, tidak ada mutasi saat tombol diklik.
        self.assertIn("data-preview-url", source)
        self.assertIn("data-commit-url", source)
        # Teks dari server tidak boleh lewat innerHTML. Diuji sebagai PEMAKAIAN
        # (`.innerHTML`), bukan penyebutan — kata itu ada di komentar modul.
        self.assertNotIn('.innerHTML', source)
        self.assertIn('textContent', source)

    def test_readiness_autoload_publishes_the_signal(self):
        source = AUTOLOAD_JS.read_text(encoding='utf-8')
        self.assertIn("'readiness:loaded'", source)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class TimelineRepairFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            'timeline-repair',
            password='StrongPass123!',
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama='Proyek Perbaikan',
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

    # ------------------------------------------------------------------ helpers

    def _make_stale_row(self, planned='40', actual='0'):
        """Baris di luar jendela proyek — persis kondisi yang dulu tak terperbaiki."""
        return PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            week_number=12,
            week_start_date=date(2026, 3, 16),
            week_end_date=date(2026, 3, 22),
            planned_proportion=Decimal(planned),
            actual_proportion=Decimal(actual),
        )

    def _post(self, name, payload):
        return self.client.post(
            reverse(name, kwargs={'project_id': self.project.id}),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def _current_dates(self):
        return {
            'tanggal_mulai': self.project.tanggal_mulai.isoformat(),
            'tanggal_selesai': self.project.tanggal_selesai.isoformat(),
            'schedule_revision': self.project.schedule_revision,
        }

    # -------------------------------------------------------------------- alur

    def test_preview_returns_options_with_week_table(self):
        self._make_stale_row()
        self.assertTrue(compute_project_readiness(self.project)['timeline_stale'])

        response = self._post(
            'detail_project:api_preview_project_timeline', self._current_dates()
        )

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertTrue(body['ok'])
        offered = [item['resolution'] for item in body['previews']]
        self.assertEqual(offered, ['accumulate_edge', 'follow_date'])

        preview = body['previews'][0]
        self.assertTrue(preview['label'])
        self.assertTrue(preview['weeks'])
        self.assertIsInstance(preview['total_planned_before'], str)

        # Preview tidak boleh memutasi apa pun.
        self.assertTrue(compute_project_readiness(self.project)['timeline_stale'])
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=12).planned_proportion,
            Decimal('40.00'),
        )

    def test_commit_repairs_the_stale_structure(self):
        """Inti T-06: kondisi yang dulu TIDAK bisa diperbaiki tombol lama."""
        self._make_stale_row()

        payload = self._current_dates()
        payload['resolution'] = 'accumulate_edge'
        response = self._post('detail_project:api_commit_project_timeline', payload)

        self.assertEqual(response.status_code, 200, response.content)

        self.project.refresh_from_db()
        self.assertFalse(
            compute_project_readiness(self.project)['timeline_stale'],
            'Perbaikan harus menghasilkan jadwal yang tidak lagi basi.',
        )

        rows = PekerjaanProgressWeekly.objects.filter(project=self.project)
        self.assertFalse(
            rows.filter(week_end_date__gt=self.project.tanggal_selesai).exists()
        )
        # accumulate_edge memindahkan, bukan membuang.
        total = sum((row.planned_proportion for row in rows), Decimal('0.00'))
        self.assertEqual(total, Decimal('40.00'))
        last_number = build_week_buckets(
            self.project.tanggal_mulai,
            self.project.tanggal_selesai,
            self.project.week_end_day,
        )[-1][0]
        self.assertEqual(
            rows.get(week_number=last_number).planned_proportion, Decimal('40.00')
        )

    def test_empty_stale_rows_are_repairable_without_a_choice(self):
        """Kolom sisa yang kosong: tidak perlu bertanya apa pun."""
        self._make_stale_row(planned='0')

        response = self._post(
            'detail_project:api_preview_project_timeline', self._current_dates()
        )
        body = response.json()
        self.assertEqual(
            [item['resolution'] for item in body['previews']], ['none']
        )

        payload = self._current_dates()
        payload['resolution'] = 'none'
        commit = self._post('detail_project:api_commit_project_timeline', payload)
        self.assertEqual(commit.status_code, 200, commit.content)

        self.project.refresh_from_db()
        self.assertFalse(compute_project_readiness(self.project)['timeline_stale'])
        self.assertFalse(
            PekerjaanProgressWeekly.objects.filter(
                project=self.project, week_number=12
            ).exists()
        )

    def test_stale_row_with_actual_is_refused_with_reason(self):
        self._make_stale_row(planned='0', actual='15')

        payload = self._current_dates()
        payload['resolution'] = 'accumulate_edge'
        response = self._post('detail_project:api_commit_project_timeline', payload)

        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertEqual(body['impact']['blocking_reason'], 'actual_out_of_window')
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=12).actual_proportion,
            Decimal('15.00'),
        )

    def test_healthy_project_offers_nothing_to_repair(self):
        """`timeline_stale=false` -> tidak ada yang perlu ditawarkan."""
        self.assertFalse(compute_project_readiness(self.project)['timeline_stale'])

        response = self._post(
            'detail_project:api_preview_project_timeline', self._current_dates()
        )
        body = response.json()
        self.assertEqual(
            [item['resolution'] for item in body['previews']], ['none']
        )
        self.assertFalse(body['impact']['start_changed'])
        self.assertFalse(body['impact']['end_changed'])

    def test_stale_revision_is_rejected(self):
        self._make_stale_row()
        payload = self._current_dates()
        payload['schedule_revision'] = self.project.schedule_revision + 5
        payload['resolution'] = 'accumulate_edge'

        response = self._post('detail_project:api_commit_project_timeline', payload)

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=12).planned_proportion,
            Decimal('40.00'),
        )
