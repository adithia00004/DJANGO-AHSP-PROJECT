from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import ParameterMigrationLog, ProjectComputedParameter, ProjectParameter


class OpaquePostDeployStatusCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="opaque_status_user",
            email="opaque-status@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Opaque Status Project",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )

    @override_settings(OPAQUE_ID_ENABLED=True)
    def test_strict_pass_when_names_are_opaque(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="10",
            label="Panjang",
        )
        ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_1",
            expression="bp_1 * 2",
            label="Luas",
        )

        out = StringIO()
        call_command(
            "opaque_post_deploy_status",
            "--strict",
            "--project-id",
            str(self.project.id),
            stdout=out,
        )
        text = out.getvalue()
        self.assertIn("non_opaque_base: 0", text)
        self.assertIn("non_opaque_computed: 0", text)
        self.assertIn("STRICT_GATE=PASS", text)

    @override_settings(OPAQUE_ID_ENABLED=True)
    def test_strict_fails_when_non_opaque_names_exist(self):
        row = ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="10",
            label="Panjang",
        )
        ProjectParameter.objects.filter(id=row.id).update(name="panjang")

        with self.assertRaises(CommandError):
            call_command(
                "opaque_post_deploy_status",
                "--strict",
                "--project-id",
                str(self.project.id),
            )

    @override_settings(OPAQUE_ID_ENABLED=True)
    def test_strict_require_cleanup_fails_for_old_logs(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="10",
            label="Panjang",
        )
        log = ParameterMigrationLog.objects.create(
            project=self.project,
            old_name="panjang",
            new_name="bp_1",
            param_type=ParameterMigrationLog.TYPE_BASE,
        )
        ParameterMigrationLog.objects.filter(id=log.id).update(
            migrated_at=timezone.now() - timedelta(days=30)
        )

        with self.assertRaises(CommandError):
            call_command(
                "opaque_post_deploy_status",
                "--strict",
                "--require-cleanup",
                "--window-days",
                "7",
                "--project-id",
                str(self.project.id),
            )
