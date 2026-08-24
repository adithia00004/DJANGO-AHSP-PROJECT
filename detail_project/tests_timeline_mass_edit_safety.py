"""Langkah 1.3 — mass edit berhenti menghapus progress secara senyap.

Membalikkan dua lock dari langkah 1.1 (`tests_timeline_contract_freeze.py`):

* **T-01** — perubahan `tanggal_mulai` dulu memanggil `reset_project_progress`,
  menghapus SELURUH `PekerjaanProgressWeekly` termasuk realisasi.
* **T-02** — perubahan `tanggal_selesai` dulu tidak memicu apa pun sehingga
  struktur jadwal langsung basi.

Juga menegakkan keputusan **G0-3**: validasi dan otorisasi tetap all-or-nothing,
sedangkan "perlu keputusan timeline" dilewati per-project tanpa membatalkan batch.

Tracker: `Review/R5_Detail_Project/39_Timeline_Change_Implementation_Tracker_20260824.md`
"""

import json
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
    TahapPelaksanaan,
    VolumePekerjaan,
)
from .progress_utils import build_week_buckets
from .readiness import compute_project_readiness


TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'config.middleware.timeout.TimeoutMiddleware'
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class MassEditTimelineSafetyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            'mass-edit-safety',
            password='StrongPass123!',
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = self._create_project('Proyek Utama')
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

    def _seed(self, project, pekerjaan, week_number, planned='0', actual='0',
              actual_cost=None):
        buckets = {
            num: (start, end)
            for num, start, end in build_week_buckets(
                project.tanggal_mulai, project.tanggal_selesai, project.week_end_day
            )
        }
        start, end = buckets[week_number]
        return PekerjaanProgressWeekly.objects.create(
            project=project,
            pekerjaan=pekerjaan,
            week_number=week_number,
            week_start_date=start,
            week_end_date=end,
            planned_proportion=Decimal(planned),
            actual_proportion=Decimal(actual),
            actual_cost=actual_cost,
        )

    def _post(self, changes):
        return self.client.post(
            reverse('dashboard:mass_edit_bulk'),
            data=json.dumps({'changes': changes}),
            content_type='application/json',
        )

    # --------------------------------------------------------------- T-01 dibalik

    def test_start_change_with_progress_is_skipped_not_wiped(self):
        """T-01 dibalik: progress tidak lagi terhapus tanpa keputusan user."""
        self._seed(self.project, self.pekerjaan, 1, planned='10', actual='8',
                   actual_cost=Decimal('500000'))
        self._seed(self.project, self.pekerjaan, 2, planned='15')

        response = self._post([
            {'id': self.project.pk, 'tanggal_mulai': '2026-02-01'},
        ])

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['updated_count'], 0)
        self.assertEqual(len(body['needs_decision']), 1)
        entry = body['needs_decision'][0]
        self.assertEqual(entry['id'], self.project.pk)
        self.assertEqual(entry['nama'], 'Proyek Utama')
        # Cabang yang benar: pergeseran tanggal mulai, bukan sekadar baris di
        # luar jendela. Menguncinya mencegah kembalinya bug instance ter-mutasi.
        self.assertEqual(entry['blocking_reason'], 'actual_present_start_shift')

        # Tidak ada satu pun yang tersimpan untuk project ini.
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 1, 1))

        # Progress utuh — termasuk realisasi.
        rows = PekerjaanProgressWeekly.objects.filter(project=self.project)
        self.assertEqual(rows.count(), 2)
        row = rows.get(week_number=1)
        self.assertEqual(row.planned_proportion, Decimal('10.00'))
        self.assertEqual(row.actual_proportion, Decimal('8.00'))
        self.assertEqual(row.actual_cost, Decimal('500000.00'))

    def test_start_change_without_progress_is_applied_safely(self):
        """Kasus aman tetap jalan otomatis — tidak ada dialog yang tidak perlu."""
        response = self._post([
            {'id': self.project.pk, 'tanggal_mulai': '2026-02-01'},
        ])

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['updated_count'], 1)
        self.assertEqual(body['needs_decision'], [])

        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_mulai, date(2026, 2, 1))
        self.assertFalse(compute_project_readiness(self.project)['timeline_stale'])

    # --------------------------------------------------------------- T-02 dibalik

    def test_end_change_now_rebuilds_the_schedule(self):
        """T-02 dibalik: perubahan tanggal selesai tidak lagi diabaikan."""
        TahapPelaksanaan.objects.create(
            project=self.project,
            nama='Minggu 8',
            urutan=7,
            tanggal_mulai=date(2026, 2, 16),
            tanggal_selesai=date(2026, 2, 22),
            is_auto_generated=True,
            generation_mode='weekly',
        )

        response = self._post([
            {'id': self.project.pk, 'tanggal_selesai': '2026-01-31'},
        ])

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['updated_count'], 1)

        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 1, 31))

        # Struktur dibangun ulang: tidak ada tahapan di luar jendela baru.
        self.assertFalse(
            TahapPelaksanaan.objects.filter(
                project=self.project, tanggal_selesai__gt=date(2026, 1, 31)
            ).exists(),
        )
        self.assertEqual(
            TahapPelaksanaan.objects.filter(
                project=self.project, is_auto_generated=True,
                generation_mode='weekly',
            ).count(),
            len(build_week_buckets(
                date(2026, 1, 1), date(2026, 1, 31), self.project.week_end_day
            )),
        )
        self.assertFalse(compute_project_readiness(self.project)['timeline_stale'])

    def test_end_change_over_planned_progress_needs_decision(self):
        """Pemendekan yang melewati rencana tetap butuh keputusan user."""
        self._seed(self.project, self.pekerjaan, 8, planned='40')

        response = self._post([
            {'id': self.project.pk, 'tanggal_selesai': '2026-01-31'},
        ])

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['updated_count'], 0)
        self.assertEqual(len(body['needs_decision']), 1)
        entry = body['needs_decision'][0]
        self.assertEqual(entry['planned_records'], 1)
        self.assertIn('accumulate_edge', entry['allowed_resolutions'])
        self.assertEqual(entry['recommended_resolution'], 'accumulate_edge')

        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 28))
        self.assertEqual(
            PekerjaanProgressWeekly.objects.get(week_number=8).planned_proportion,
            Decimal('40.00'),
        )

    # ------------------------------------------------------------------- G0-3

    def test_safe_projects_save_while_unsafe_one_is_skipped(self):
        """G0-3 — satu project perlu keputusan TIDAK membatalkan batch.

        Doc 38 §6.2 baris 10.
        """
        safe_a = self._create_project('Aman A')
        safe_b = self._create_project('Aman B')
        self._seed(self.project, self.pekerjaan, 1, planned='10')

        response = self._post([
            {'id': safe_a.pk, 'tanggal_mulai': '2026-02-01'},
            {'id': safe_b.pk, 'tanggal_mulai': '2026-02-01'},
            {'id': self.project.pk, 'tanggal_mulai': '2026-02-01'},
        ])

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['updated_count'], 2)
        self.assertEqual([e['nama'] for e in body['needs_decision']], ['Proyek Utama'])

        safe_a.refresh_from_db()
        safe_b.refresh_from_db()
        self.project.refresh_from_db()
        self.assertEqual(safe_a.tanggal_mulai, date(2026, 2, 1))
        self.assertEqual(safe_b.tanggal_mulai, date(2026, 2, 1))
        self.assertEqual(self.project.tanggal_mulai, date(2026, 1, 1))

    def test_validation_error_still_rolls_back_whole_batch(self):
        """G0-3 — kelas kegagalan validasi TIDAK ikut berubah jadi partial."""
        safe_a = self._create_project('Aman A')

        response = self._post([
            {'id': safe_a.pk, 'tanggal_mulai': '2026-02-01'},
            {'id': self.project.pk, 'anggaran_owner': 'bukan angka'},
        ])

        self.assertEqual(response.status_code, 400, response.content)
        safe_a.refresh_from_db()
        self.assertEqual(
            safe_a.tanggal_mulai, date(2026, 1, 1),
            'Kegagalan validasi harus tetap membatalkan seluruh batch.',
        )

    def test_non_timeline_edit_is_untouched_by_the_new_path(self):
        """Perubahan yang tidak menyentuh tanggal tidak melewati service timeline."""
        self._seed(self.project, self.pekerjaan, 1, planned='10', actual='8')

        response = self._post([
            {'id': self.project.pk, 'nama_client': 'Dinas Baru'},
        ])

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['updated_count'], 1)
        self.project.refresh_from_db()
        self.assertEqual(self.project.nama_client, 'Dinas Baru')
        self.assertEqual(
            PekerjaanProgressWeekly.objects.filter(project=self.project).count(), 1
        )
