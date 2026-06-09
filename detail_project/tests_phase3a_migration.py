from io import StringIO
import time

from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    ParameterMigrationLog,
    ParameterSequence,
    Pekerjaan,
    ProjectComputedParameter,
    ProjectParameter,
    SubKlasifikasi,
    VolumeFormulaState,
    VolumePekerjaan,
)


class Phase3AParameterMigrationCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="phase3a_migration_user",
            email="phase3a-migration@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Phase 3A Migration",
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

        # Simulate pre-migration legacy descriptive names (bypass model clean via update()).
        ProjectParameter.objects.filter(id=p1.id).update(name="panjang")
        ProjectParameter.objects.filter(id=p2.id).update(name="lebar")
        ProjectComputedParameter.objects.filter(id=cp.id).update(
            name="luas",
            expression="panjang * lebar",
        )
        VolumeFormulaState.objects.filter(id=vf.id).update(raw="=panjang + luas")

    def test_command_migrates_legacy_names_and_formulas(self):
        self._seed_legacy_data()
        out = StringIO()
        call_command(
            "migrate_parameters_to_opaque",
            "--project-id",
            str(self.project.id),
            "--yes",
            stdout=out,
        )

        base_names = sorted(
            ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        computed_names = sorted(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        self.assertEqual(base_names, ["bp_1", "bp_2"])
        self.assertEqual(computed_names, ["cp_1"])

        cp_expr = ProjectComputedParameter.objects.get(project=self.project, name="cp_1").expression
        self.assertEqual(cp_expr, "bp_1 * bp_2")
        vf_raw = VolumeFormulaState.objects.get(project=self.project).raw
        self.assertEqual(vf_raw, "=bp_1 + cp_1")

        logs = ParameterMigrationLog.objects.filter(project=self.project)
        self.assertEqual(logs.count(), 3)
        self.assertTrue(logs.filter(old_name="panjang", new_name="bp_1", param_type="base").exists())
        self.assertTrue(logs.filter(old_name="lebar", new_name="bp_2", param_type="base").exists())
        self.assertTrue(logs.filter(old_name="luas", new_name="cp_1", param_type="computed").exists())

        bp_seq = ParameterSequence.objects.get(project=self.project, prefix="bp")
        cp_seq = ParameterSequence.objects.get(project=self.project, prefix="cp")
        self.assertEqual(bp_seq.last_num, 2)
        self.assertEqual(cp_seq.last_num, 1)

    def test_command_dry_run_does_not_write_changes(self):
        self._seed_legacy_data()
        call_command(
            "migrate_parameters_to_opaque",
            "--project-id",
            str(self.project.id),
            "--dry-run",
            "--yes",
        )

        base_names = set(ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True))
        computed_names = set(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        self.assertEqual(base_names, {"panjang", "lebar"})
        self.assertEqual(computed_names, {"luas"})
        self.assertFalse(ParameterMigrationLog.objects.filter(project=self.project).exists())

    def test_command_rolls_back_project_on_invalid_formula_reference(self):
        self._seed_legacy_data()
        bad_cp = ProjectComputedParameter.objects.get(project=self.project)
        ProjectComputedParameter.objects.filter(id=bad_cp.id).update(expression="panjang + tidak_ada")

        with self.assertRaises(CommandError):
            call_command(
                "migrate_parameters_to_opaque",
                "--project-id",
                str(self.project.id),
                "--yes",
            )

        base_names = set(ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True))
        computed_names = set(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        cp_expr = ProjectComputedParameter.objects.get(project=self.project).expression

        self.assertEqual(base_names, {"panjang", "lebar"})
        self.assertEqual(computed_names, {"luas"})
        self.assertEqual(cp_expr, "panjang + tidak_ada")
        self.assertFalse(ParameterMigrationLog.objects.filter(project=self.project).exists())

    def test_command_remaps_multi_ref_and_computed_dependency_and_substring_safety(self):
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
        cp1 = ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_1",
            expression="bp_1 * bp_2 + bp_1",
            label="Luas",
        )
        cp2 = ProjectComputedParameter.objects.create(
            project=self.project,
            name="cp_2",
            expression="cp_1 + bp_1",
            label="Total",
        )
        pekerjaan = self._create_volume_formula_fixture()
        vf = VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=abs(bp_1) + bp_1 * max(bp_1, bp_2)",
            is_fx=True,
        )

        ProjectParameter.objects.filter(id=p1.id).update(name="panjang")
        ProjectParameter.objects.filter(id=p2.id).update(name="lebar")
        ProjectComputedParameter.objects.filter(id=cp1.id).update(
            name="luas",
            expression="panjang * lebar + panjang",
        )
        ProjectComputedParameter.objects.filter(id=cp2.id).update(
            name="total",
            expression="luas + panjang",
        )
        VolumeFormulaState.objects.filter(id=vf.id).update(
            raw="=abs(panjang) + panjang * max(panjang, lebar)"
        )

        call_command(
            "migrate_parameters_to_opaque",
            "--project-id",
            str(self.project.id),
            "--yes",
        )

        rows = list(
            ProjectComputedParameter.objects.filter(project=self.project)
            .order_by("name")
            .values_list("name", "expression")
        )
        self.assertEqual(rows[0], ("cp_1", "bp_1 * bp_2 + bp_1"))
        self.assertEqual(rows[1], ("cp_2", "cp_1 + bp_1"))

        vf_raw = VolumeFormulaState.objects.get(project=self.project).raw
        self.assertEqual(vf_raw, "=abs(bp_1) + bp_1 * max(bp_1, bp_2)")

    def test_command_handles_empty_project_without_error(self):
        empty_project = Project.objects.create(
            owner=self.user,
            nama="Empty Migration Project",
            sumber_dana="APBN",
            lokasi_project="Bandung",
            nama_client="Client",
            anggaran_owner=1000,
        )

        out = StringIO()
        call_command(
            "migrate_parameters_to_opaque",
            "--project-id",
            str(empty_project.id),
            "--yes",
            stdout=out,
        )
        text = out.getvalue()
        self.assertIn("[SKIPPED]", text)
        self.assertFalse(ParameterMigrationLog.objects.filter(project=empty_project).exists())

    def test_m5_large_project_migrates_under_ten_seconds(self):
        pekerjaan = self._create_volume_formula_fixture()

        base_rows = []
        for i in range(1, 121):
            row = ProjectParameter.objects.create(
                project=self.project,
                name=f"bp_{i}",
                value=str(i),
                label=f"Param {i}",
            )
            base_rows.append((row.id, f"p{i}"))
        for row_id, legacy_name in base_rows:
            ProjectParameter.objects.filter(id=row_id).update(name=legacy_name)

        computed_rows = []
        for i in range(1, 41):
            row = ProjectComputedParameter.objects.create(
                project=self.project,
                name=f"cp_{i}",
                expression=f"bp_{i} + bp_{i+1}",
                label=f"Calc {i}",
            )
            computed_rows.append((row.id, f"c{i}", f"p{i} + p{i+1}"))
        for row_id, legacy_name, legacy_expression in computed_rows:
            ProjectComputedParameter.objects.filter(id=row_id).update(
                name=legacy_name,
                expression=legacy_expression,
            )

        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            raw="=p1 + p2 + c1 + c2 + c3",
            is_fx=True,
        )

        started = time.perf_counter()
        call_command(
            "migrate_parameters_to_opaque",
            "--project-id",
            str(self.project.id),
            "--yes",
            stdout=StringIO(),
        )
        elapsed_seconds = time.perf_counter() - started

        self.assertLess(
            elapsed_seconds,
            10.0,
            msg=f"Large-project migration took {elapsed_seconds:.2f}s (expected < 10s).",
        )

        base_names = list(
            ProjectParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        computed_names = list(
            ProjectComputedParameter.objects.filter(project=self.project).values_list("name", flat=True)
        )
        self.assertEqual(len(base_names), 120)
        self.assertEqual(len(computed_names), 40)
        self.assertTrue(all(name.startswith("bp_") for name in base_names))
        self.assertTrue(all(name.startswith("cp_") for name in computed_names))
