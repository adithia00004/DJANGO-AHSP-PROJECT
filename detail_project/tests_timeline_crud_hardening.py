import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import RequestFactory, TestCase
from django.test import override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from dashboard.forms import ProjectForm
from dashboard.models import Project

from .models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    PekerjaanTahapan,
    SubKlasifikasi,
    TahapPelaksanaan,
    VolumePekerjaan,
)


TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'config.middleware.timeout.TimeoutMiddleware'
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class TimelineCrudHardeningTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            'timeline-hardening',
            password='x',
            subscription_status=user_model.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama='Timeline Hardening',
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

    def _post(self, name, payload):
        url = reverse(name, kwargs={'project_id': self.project.id})
        request = RequestFactory().post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.user = self.owner
        match = resolve(url)
        return match.func(request, **match.kwargs)

    def _save_url(self):
        return reverse(
            'detail_project:api_v2_assign_weekly',
            kwargs={'project_id': self.project.id},
        )

    def test_project_save_does_not_invent_end_date(self):
        project = Project.objects.create(owner=self.owner, nama='No End')
        self.assertIsNone(project.tanggal_selesai)

    def test_project_form_requires_end_date(self):
        data = {
            'nama': 'No End Form',
            'tanggal_mulai': '2026-01-01',
            'tanggal_selesai': '',
            'sumber_dana': 'APBN',
            'lokasi_project': 'Jakarta',
            'nama_client': 'Client',
            'anggaran_owner': '1000',
        }
        self.assertFalse(ProjectForm(data=data).is_valid())

    def test_project_form_valid_timeline_does_not_require_internal_revision(self):
        data = {
            'nama': 'Valid Timeline Form',
            'tanggal_mulai': '2026-01-01',
            'tanggal_selesai': '2026-01-31',
            'sumber_dana': 'APBN',
            'lokasi_project': 'Jakarta',
            'nama_client': 'Client',
            'anggaran_owner': '1000',
        }
        form = ProjectForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_weekly_save_rejects_incomplete_timeline(self):
        self.project.tanggal_selesai = None
        self.project.save(update_fields=['tanggal_selesai', 'updated_at'])
        response = self._post('detail_project:api_v2_assign_weekly', {
                'mode': 'planned',
                'schedule_revision': self.project.schedule_revision,
                'assignments': [{
                    'pekerjaan_id': self.pekerjaan.id,
                    'week_number': 1,
                    'proportion': 10,
                }],
            })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content).get('code'), 'incomplete_timeline')

    def test_weekly_save_works_before_tahapan_structure_exists(self):
        self.assertFalse(TahapPelaksanaan.objects.filter(project=self.project).exists())

        response = self._post('detail_project:api_v2_assign_weekly', {
            'mode': 'planned',
            'schedule_revision': self.project.schedule_revision,
            'assignments': [{
                'pekerjaan_id': self.pekerjaan.id,
                'week_number': 1,
                'proportion': 10,
            }],
        })

        self.assertEqual(response.status_code, 200, response.content)
        progress = PekerjaanProgressWeekly.objects.get(
            project=self.project,
            pekerjaan=self.pekerjaan,
            week_number=1,
        )
        self.assertEqual(progress.planned_proportion, Decimal('10.00'))
        self.assertEqual(progress.week_start_date, date(2026, 1, 1))
        self.assertEqual(progress.week_end_date, date(2026, 1, 4))

    def test_stale_schedule_revision_is_rejected(self):
        old_revision = self.project.schedule_revision
        self.project.week_start_day = 1
        self.project.save()
        response = self._post('detail_project:api_v2_assign_weekly', {
                'mode': 'planned',
                'schedule_revision': old_revision,
                'assignments': [{
                    'pekerjaan_id': self.pekerjaan.id,
                    'week_number': 1,
                    'proportion': 10,
                }],
            })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.content).get('code'), 'schedule_revision_conflict')
        self.assertFalse(PekerjaanProgressWeekly.objects.exists())

    def test_week_outside_project_range_is_rejected(self):
        response = self._post('detail_project:api_v2_assign_weekly', {
                'mode': 'planned',
                'schedule_revision': self.project.schedule_revision,
                'assignments': [{
                    'pekerjaan_id': self.pekerjaan.id,
                    'week_number': 99,
                    'proportion': 10,
                }],
            })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['errors'][0]['code'], 'week_out_of_range')

    def test_reset_planned_syncs_derived_projection(self):
        tahap = TahapPelaksanaan.objects.create(
            project=self.project,
            nama='Week 1',
            urutan=0,
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 1, 7),
            is_auto_generated=True,
            generation_mode='weekly',
        )
        PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            week_number=1,
            week_start_date=date(2026, 1, 1),
            week_end_date=date(2026, 1, 7),
            planned_proportion=Decimal('50'),
        )
        PekerjaanTahapan.objects.create(
            pekerjaan=self.pekerjaan,
            tahapan=tahap,
            proporsi_volume=Decimal('50'),
        )
        response = self._post('detail_project:api_v2_reset_progress', {'mode': 'planned'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(PekerjaanTahapan.objects.filter(tahapan=tahap).exists())

    def test_timeline_trim_planned_preserves_actual_contract(self):
        PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            week_number=9,
            week_start_date=date(2026, 2, 26),
            week_end_date=date(2026, 3, 4),
            planned_proportion=Decimal('20'),
        )
        response = self._post('detail_project:api_commit_project_timeline', {
                'tanggal_mulai': '2026-01-01',
                'tanggal_selesai': '2026-02-20',
                'resolution': 'trim_planned',
                'schedule_revision': self.project.schedule_revision,
            })
        self.assertEqual(response.status_code, 200, response.content)
        row = PekerjaanProgressWeekly.objects.get(week_number=9)
        self.assertEqual(row.planned_proportion, Decimal('0.00'))
        self.project.refresh_from_db()
        self.assertEqual(self.project.tanggal_selesai, date(2026, 2, 20))
        self.assertGreater(self.project.schedule_revision, 1)

    def test_regenerate_incomplete_timeline_does_not_save_boundary(self):
        self.project.tanggal_selesai = None
        self.project.week_start_day = 2
        self.project.save(update_fields=['tanggal_selesai', 'week_start_day', 'updated_at'])
        old_boundary = self.project.week_start_day
        response = self._post('detail_project:api_v2_regenerate_tahapan', {
                'mode': 'weekly',
                'week_start_day': 5,
                'week_end_day': 4,
                'schedule_revision': self.project.schedule_revision,
            })
        self.assertEqual(response.status_code, 400)
        self.project.refresh_from_db()
        self.assertEqual(self.project.week_start_day, old_boundary)
