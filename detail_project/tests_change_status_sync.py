import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, PekerjaanProgressWeekly, SubKlasifikasi
from detail_project.views import (
    jadwal_pekerjaan_view,
    rekap_kebutuhan_view,
    rekap_rab_view,
    rincian_rab_view,
)
from detail_project.views_api import api_get_change_status


class ChangeStatusSyncTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_change_status_sync",
            email="owner-change-status-sync@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Change Status Sync",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Sync",
            anggaran_owner=1000,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="Klas A", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub A",
            ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="Pekerjaan Sync",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self.factory = RequestFactory()

    def _get_change_status(self):
        request = self.factory.get(
            reverse(
                "detail_project:api_get_change_status",
                kwargs={"project_id": self.project.id},
            )
        )
        request.user = self.owner
        return api_get_change_status(request, self.project.id)

    def test_change_status_reports_jadwal_timestamp_from_weekly_progress(self):
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=self.pekerjaan,
            project=self.project,
            week_number=1,
            week_start_date=date(2026, 1, 1),
            week_end_date=date(2026, 1, 7),
            planned_proportion=Decimal("25.00"),
        )

        response = self._get_change_status()

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body["ok"])
        self.assertIsNotNone(body["jadwal_changed_at"])

    def test_summary_and_schedule_pages_render_scoped_sync_led(self):
        cases = (
            (rekap_rab_view, "rekap_rab", "pekerjaan,volume,ahsp,harga"),
            (rincian_rab_view, "rincian_rab", "pekerjaan,volume,ahsp,harga"),
            (rekap_kebutuhan_view, "rekap_kebutuhan", "pekerjaan,volume,ahsp,harga"),
            (jadwal_pekerjaan_view, "jadwal", "pekerjaan,volume,jadwal"),
        )

        for view, scope, watch in cases:
            with self.subTest(scope=scope):
                request = self.factory.get("/")
                request.user = self.owner
                response = view(request, project_id=self.project.id)
                content = response.content.decode("utf-8")

                self.assertEqual(response.status_code, 200)
                self.assertIn(f'data-scope="{scope}"', content)
                self.assertIn(f'data-watch="{watch}"', content)
                self.assertIn('data-initial-pekerjaan="', content)
                self.assertIn('data-initial-volume="', content)
                self.assertIn('data-initial-jadwal="', content)


class SyncLedTemplateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        base_dir = Path(__file__).resolve().parent
        cls.template_dir = base_dir / "templates" / "detail_project"
        cls.static_js_dir = base_dir / "static" / "detail_project" / "js"

    def test_initial_jadwal_uses_database_timestamp_context(self):
        source = (
            Path(__file__).resolve().parent
            / "templates"
            / "detail_project"
            / "_sync_led.html"
        ).read_text(encoding="utf-8")

        self.assertIn('initial_jadwal=initial_jadwal_ts|date:"c"', source)
        self.assertIn('data-initial-jadwal="{{ initial_jadwal }}"', source)
        self.assertNotIn('data-initial-jadwal="{% now', source)

    def test_active_pages_use_expected_sync_watch_policy(self):
        template_source = (self.template_dir / "template_ahsp.html").read_text(encoding="utf-8")
        volume_source = (self.template_dir / "volume_pekerjaan.html").read_text(encoding="utf-8")

        self.assertIn('scope="template" watch="pekerjaan,harga"', template_source)
        self.assertIn('scope="volume" watch="pekerjaan"', volume_source)

    def test_legacy_sync_indicator_is_not_loaded_or_present(self):
        base_source = (self.template_dir / "base_detail.html").read_text(encoding="utf-8")

        self.assertNotIn("detail_project/js/sync_indicator.js", base_source)
        self.assertFalse((self.static_js_dir / "sync_indicator.js").exists())
        self.assertFalse((self.template_dir / "_sync_indicator.html").exists())

    def test_sync_led_and_jadwal_support_safe_refresh_and_ack(self):
        sync_source = (self.static_js_dir / "sync_led.js").read_text(encoding="utf-8")
        jadwal_source = (
            self.static_js_dir / "src" / "jadwal_kegiatan_app.js"
        ).read_text(encoding="utf-8")
        legacy_save_source = (
            self.static_js_dir
            / "jadwal_pekerjaan"
            / "kelola_tahapan"
            / "save_handler_module.js"
        ).read_text(encoding="utf-8")

        self.assertIn("FULL_RELOAD_SCOPES", sync_source)
        self.assertIn("event?.detail?.scope !== 'jadwal'", jadwal_source)
        self.assertIn("dp:sync-led-ack", jadwal_source)
        self.assertIn("mode: state.progressMode || 'planned'", legacy_save_source)
        self.assertNotIn("mode: state.timeScale", legacy_save_source)
