from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    ParameterMigrationLog,
    Pekerjaan,
    ProjectComputedParameter,
    ProjectParameter,
    SubKlasifikasi,
    VolumeFormulaState,
    VolumePekerjaan,
)


class Phase45RollbackCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="phase45_rollback_user",
            email="phase45-rollback@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Phase 4.5 Rollback",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )

    def _create_volume_formula_fixture(self):
        klas = Klasifikasi.objects.create(project=self.project, name="Klas")
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="Sub")
        pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-1",
            snapshot_uraian="Pekerjaan 1",
            snapshot_satuan="m3",
        )
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pekerjaan, quantity="1")
        return pekerjaan

    def _seed_legacy_data(self):
        p1 = ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="10",
            label="Panjang",
        )
        p2 = ProjectParameter.objects.create(
            project=self.project,
            name="bp_2",
            value="5",
            label="Lebar",
        )
        cp = ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_1",
            expression="bp_1 * bp_2",
            label="Luas",
        )
        pekerjaan = self._create_volume_formula_fixture()
        vf = VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=bp_1 + cp_1",
            is_fx=True,
        )

        # Simulate pre-migration legacy names.
        ProjectParameter.objects.filter(id=p1.id).update(name="panjang")
        ProjectParameter.objects.filter(id=p2.id).update(name="lebar")
        ProjectComputedParameter.objects.filter(id=cp.id).update(
            name="luas",
            expression="panjang * lebar",
        )
        VolumeFormulaState.objects.filter(id=vf.id).update(raw="=panjang + luas")

    def _run_migrate_to_opaque(self):
        call_command(
            "migrate_parameters_to_opaque",
            "--project-id",
            str(self.project.id),
            "--yes",
        )

    def test_roundtrip_migrate_then_rollback_restores_legacy_names(self):
        self._seed_legacy_data()
        self._run_migrate_to_opaque()

        base_names = sorted(
            ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        self.assertEqual(base_names, ["bp_1", "bp_2"])

        call_command(
            "rollback_parameters_from_opaque",
            "--project-id",
            str(self.project.id),
            "--yes",
        )

        base_names_after = sorted(
            ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        computed_names_after = sorted(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        self.assertEqual(base_names_after, ["lebar", "panjang"])
        self.assertEqual(computed_names_after, ["luas"])

        cp_expr = ProjectComputedParameter.objects.get(project=self.project, name="luas").expression
        self.assertEqual(cp_expr, "panjang * lebar")
        vf_raw = VolumeFormulaState.objects.get(project=self.project).raw
        self.assertEqual(vf_raw, "=panjang + luas")

    def test_rollback_dry_run_does_not_write_changes(self):
        self._seed_legacy_data()
        self._run_migrate_to_opaque()

        call_command(
            "rollback_parameters_from_opaque",
            "--project-id",
            str(self.project.id),
            "--dry-run",
            "--yes",
        )

        base_names = set(ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True))
        computed_names = set(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        self.assertEqual(base_names, {"bp_1", "bp_2"})
        self.assertEqual(computed_names, {"cp_1"})

    def test_rollback_fails_if_mapping_log_missing_and_keeps_state(self):
        self._seed_legacy_data()
        self._run_migrate_to_opaque()

        ParameterMigrationLog.objects.filter(
            project=self.project,
            param_type=ParameterMigrationLog.TYPE_BASE,
            new_name="bp_1",
        ).delete()

        with self.assertRaises(CommandError):
            call_command(
                "rollback_parameters_from_opaque",
                "--project-id",
                str(self.project.id),
                "--yes",
            )

        base_names = set(ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True))
        computed_names = set(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        cp_expr = ProjectComputedParameter.objects.get(project=self.project, name="cp_1").expression
        vf_raw = VolumeFormulaState.objects.get(project=self.project).raw

        self.assertEqual(base_names, {"bp_1", "bp_2"})
        self.assertEqual(computed_names, {"cp_1"})
        self.assertEqual(cp_expr, "bp_1 * bp_2")
        self.assertEqual(vf_raw, "=bp_1 + cp_1")

    def test_rollback_skips_project_without_logs(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="10",
            label="Panjang",
        )
        out = StringIO()
        call_command(
            "rollback_parameters_from_opaque",
            "--project-id",
            str(self.project.id),
            "--yes",
            stdout=out,
        )
        text = out.getvalue()
        self.assertIn("[SKIPPED]", text)

    def test_rollback_allow_missing_log_handles_mixed_state(self):
        self._seed_legacy_data()
        self._run_migrate_to_opaque()

        ParameterMigrationLog.objects.filter(
            project=self.project,
            param_type=ParameterMigrationLog.TYPE_BASE,
            new_name="bp_1",
        ).delete()

        call_command(
            "rollback_parameters_from_opaque",
            "--project-id",
            str(self.project.id),
            "--allow-missing-log",
            "--yes",
        )

        base_names = set(ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True))
        computed_names = set(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        cp_expr = ProjectComputedParameter.objects.get(project=self.project, name="luas").expression
        vf_raw = VolumeFormulaState.objects.get(project=self.project).raw

        # Mixed-state rollback is intentional:
        # bp_1 remains opaque (missing log), bp_2 rolls back to legacy "lebar".
        self.assertEqual(base_names, {"bp_1", "lebar"})
        self.assertEqual(computed_names, {"luas"})
        self.assertEqual(cp_expr, "bp_1 * lebar")
        self.assertEqual(vf_raw, "=bp_1 + luas")
