"""Fase 4b (SYN-05): test management command `clear_stale_reload_flags`.

Perbaikan SYN-01 hanya menghentikan flag reload BARU; flag warisan tetap
tersimpan di `ProjectChangeStatus` dan terus memunculkan banner Template AHSP
serta mengunci form Harga Items. Command ini membersihkannya sekali jalan.

Yang dikunci di sini: cakupan (per-project vs --all), sifat dry-run yang tidak
menulis, dan yang paling penting -- flag VOLUME tidak ikut terhapus kecuali
diminta eksplisit, karena flag volume menandai volume yang benar-benar direset
dan masih harus diisi ulang user.

Dokumen: `Review/R5_Detail_Project/36_Cross_Page_Sync_Over_Notification_Audit_Plan_20260824.md`
"""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from dashboard.models import Project
from detail_project.models import ProjectChangeStatus


class ClearStaleReloadFlagsCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_clear_stale_flags",
            email="owner-clear-stale-flags@example.com",
            password="Secret123!",
        )
        self.project_a = self._make_project("Proyek A")
        self.project_b = self._make_project("Proyek B")

        self.tracker_a = ProjectChangeStatus.objects.create(
            project=self.project_a,
            pending_reload_job_ids=[11, 12, 13],
            pending_volume_reset_job_ids=[11],
        )
        self.tracker_b = ProjectChangeStatus.objects.create(
            project=self.project_b,
            pending_reload_job_ids=[21, 22],
            pending_volume_reset_job_ids=[],
        )

    def _make_project(self, nama):
        return Project.objects.create(
            owner=self.owner,
            nama=nama,
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )

    @staticmethod
    def _run(**kwargs):
        out = StringIO()
        call_command("clear_stale_reload_flags", stdout=out, **kwargs)
        return out.getvalue()

    # ---------- argumen ----------

    def test_requires_scope_argument(self):
        with self.assertRaises(CommandError):
            self._run()

    def test_project_id_and_all_are_mutually_exclusive(self):
        with self.assertRaises(CommandError):
            self._run(project_id=self.project_a.id, all=True)

    def test_unknown_project_id_raises(self):
        with self.assertRaises(CommandError):
            self._run(project_id=999999)

    # ---------- dry-run tidak menulis ----------

    def test_dry_run_reports_without_writing(self):
        out = self._run(all=True, dry_run=True)

        self.assertIn("DRY-RUN", out)
        self.tracker_a.refresh_from_db()
        self.tracker_b.refresh_from_db()
        self.assertEqual(self.tracker_a.pending_reload_job_ids, [11, 12, 13])
        self.assertEqual(self.tracker_b.pending_reload_job_ids, [21, 22])

    # ---------- cakupan ----------

    def test_single_project_scope_leaves_other_project_untouched(self):
        self._run(project_id=self.project_a.id, yes=True)

        self.tracker_a.refresh_from_db()
        self.tracker_b.refresh_from_db()
        self.assertEqual(self.tracker_a.pending_reload_job_ids, [])
        self.assertEqual(self.tracker_b.pending_reload_job_ids, [21, 22])

    def test_all_scope_clears_every_project(self):
        self._run(all=True, yes=True)

        self.tracker_a.refresh_from_db()
        self.tracker_b.refresh_from_db()
        self.assertEqual(self.tracker_a.pending_reload_job_ids, [])
        self.assertEqual(self.tracker_b.pending_reload_job_ids, [])

    # ---------- flag volume dilindungi ----------

    def test_volume_flags_survive_by_default(self):
        """Flag volume menandai volume yang BENAR-BENAR direset dan masih kosong.
        Menghapusnya diam-diam akan menyembunyikan pekerjaan yang perlu diisi."""
        self._run(all=True, yes=True)

        self.tracker_a.refresh_from_db()
        self.assertEqual(self.tracker_a.pending_reload_job_ids, [])
        self.assertEqual(self.tracker_a.pending_volume_reset_job_ids, [11])

    def test_include_volume_clears_both(self):
        self._run(all=True, yes=True, include_volume=True)

        self.tracker_a.refresh_from_db()
        self.assertEqual(self.tracker_a.pending_reload_job_ids, [])
        self.assertEqual(self.tracker_a.pending_volume_reset_job_ids, [])

    # ---------- idempoten ----------

    def test_second_run_reports_nothing_to_do(self):
        self._run(all=True, yes=True)
        out = self._run(all=True, yes=True)

        self.assertIn("Tidak ada flag reload menggantung", out)

    def test_project_without_tracker_is_not_an_error(self):
        project_c = self._make_project("Proyek C tanpa tracker")
        out = self._run(project_id=project_c.id, yes=True)

        self.assertIn("Tidak ada flag reload menggantung", out)
