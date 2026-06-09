from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import ParameterMigrationLog


class CleanupParameterMigrationLogsCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="cleanup_logs_user",
            email="cleanup-logs@example.com",
            password="Secret123!",
        )
        self.project_a = Project.objects.create(
            owner=self.user,
            nama="Cleanup Project A",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )
        self.project_b = Project.objects.create(
            owner=self.user,
            nama="Cleanup Project B",
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client B",
            anggaran_owner=2000,
        )

    def _create_log(self, project, old_name, new_name, param_type, days_ago):
        log = ParameterMigrationLog.objects.create(
            project=project,
            old_name=old_name,
            new_name=new_name,
            param_type=param_type,
        )
        ParameterMigrationLog.objects.filter(id=log.id).update(
            migrated_at=timezone.now() - timedelta(days=days_ago)
        )
        return log

    def test_dry_run_does_not_delete_logs(self):
        self._create_log(self.project_a, "panjang", "bp_1", ParameterMigrationLog.TYPE_BASE, 30)
        self._create_log(self.project_a, "luas", "cp_1", ParameterMigrationLog.TYPE_COMPUTED, 1)

        out = StringIO()
        call_command(
            "cleanup_parameter_migration_logs",
            "--older-than-days",
            "7",
            "--dry-run",
            "--yes",
            stdout=out,
        )

        self.assertIn("DRY-RUN", out.getvalue())
        self.assertEqual(ParameterMigrationLog.objects.count(), 2)

    def test_cleanup_deletes_only_logs_older_than_threshold(self):
        old_log = self._create_log(
            self.project_a, "panjang", "bp_1", ParameterMigrationLog.TYPE_BASE, 20
        )
        recent_log = self._create_log(
            self.project_a, "lebar", "bp_2", ParameterMigrationLog.TYPE_BASE, 2
        )

        call_command(
            "cleanup_parameter_migration_logs",
            "--older-than-days",
            "7",
            "--yes",
        )

        self.assertFalse(ParameterMigrationLog.objects.filter(id=old_log.id).exists())
        self.assertTrue(ParameterMigrationLog.objects.filter(id=recent_log.id).exists())

    def test_cleanup_can_scope_to_single_project(self):
        log_a = self._create_log(
            self.project_a, "panjang", "bp_1", ParameterMigrationLog.TYPE_BASE, 30
        )
        log_b = self._create_log(
            self.project_b, "luas", "cp_1", ParameterMigrationLog.TYPE_COMPUTED, 30
        )

        call_command(
            "cleanup_parameter_migration_logs",
            "--older-than-days",
            "7",
            "--project-id",
            str(self.project_a.id),
            "--yes",
        )

        self.assertFalse(ParameterMigrationLog.objects.filter(id=log_a.id).exists())
        self.assertTrue(ParameterMigrationLog.objects.filter(id=log_b.id).exists())
