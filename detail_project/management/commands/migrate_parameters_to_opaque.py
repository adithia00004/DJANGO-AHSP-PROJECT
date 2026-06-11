import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from dashboard.models import Project
from detail_project.formula_tokenizer import remap_expression, tokenize_formula
from detail_project.models import (
    ParameterMigrationLog,
    ParameterSequence,
    ProjectComputedParameter,
    ProjectParameter,
    VolumeFormulaState,
)


BASE_RE = re.compile(r"^bp_[1-9][0-9]*$")
COMPUTED_RE = re.compile(r"^cp_[1-9][0-9]*$")
PREFIX_RE_TEMPLATE = r"^{prefix}_([1-9][0-9]*)$"
RESERVED_IDENTIFIERS = {
    "sum",
    "min",
    "max",
    "round",
    "avg",
    "abs",
    "floor",
    "ceil",
    "sqrt",
    "pow",
    "pi",
    "e",
    "true",
    "false",
}


class Command(BaseCommand):
    help = "Migrate legacy project parameter names to opaque bp_N/cp_N format per project."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Target specific project ID. If omitted, migrate all projects that have params/computed params.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview migration result without writing database changes.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate names even if already opaque.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Run without confirmation prompt.",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        dry_run = bool(options.get("dry_run"))
        force = bool(options.get("force"))
        skip_confirm = bool(options.get("yes"))

        if project_id:
            projects = Project.objects.filter(id=project_id).order_by("id")
            if not projects.exists():
                raise CommandError(f"Project {project_id} tidak ditemukan.")
        else:
            projects = (
                Project.objects.filter(
                    id__in=(
                        ProjectParameter.objects.values_list("project_id", flat=True).distinct()
                    )
                )
                | Project.objects.filter(
                    id__in=(
                        ProjectComputedParameter.objects.values_list("project_id", flat=True).distinct()
                    )
                )
            )
            projects = projects.distinct().order_by("id")

        total_projects = projects.count()
        if total_projects == 0:
            self.stdout.write(self.style.WARNING("Tidak ada project dengan parameter untuk dimigrasikan."))
            return

        self.stdout.write(
            f"Target migration: {total_projects} project(s). "
            f"(dry_run={dry_run}, force={force})"
        )

        if not dry_run and not skip_confirm:
            confirm = input("Type 'MIGRATE' to continue: ").strip()
            if confirm != "MIGRATE":
                raise CommandError("Dibatalkan oleh user.")

        summary = {
            "ok": 0,
            "skipped": 0,
            "failed": 0,
            "base_migrated": 0,
            "computed_migrated": 0,
            "computed_formulas_updated": 0,
            "volume_formulas_updated": 0,
            "logs_created": 0,
        }

        for project in projects:
            try:
                result = self._migrate_project(project, dry_run=dry_run, force=force)
                status = result["status"]
                if status == "skipped":
                    summary["skipped"] += 1
                else:
                    summary["ok"] += 1
                summary["base_migrated"] += result["base_migrated"]
                summary["computed_migrated"] += result["computed_migrated"]
                summary["computed_formulas_updated"] += result["computed_formulas_updated"]
                summary["volume_formulas_updated"] += result["volume_formulas_updated"]
                summary["logs_created"] += result["logs_created"]
                self.stdout.write(
                    f"[{status.upper()}] project_id={project.id} "
                    f"base_migrated={result['base_migrated']} "
                    f"computed_migrated={result['computed_migrated']} "
                    f"computed_formulas_updated={result['computed_formulas_updated']} "
                    f"volume_formulas_updated={result['volume_formulas_updated']} "
                    f"logs_created={result['logs_created']}"
                )
            except Exception as exc:
                summary["failed"] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"[FAILED] project_id={project.id} error={exc}"
                    )
                )

        self.stdout.write("\n=== MIGRATION SUMMARY ===")
        for key in (
            "ok",
            "skipped",
            "failed",
            "base_migrated",
            "computed_migrated",
            "computed_formulas_updated",
            "volume_formulas_updated",
            "logs_created",
        ):
            self.stdout.write(f"{key}: {summary[key]}")

        if summary["failed"] > 0:
            raise CommandError("Sebagian project gagal dimigrasikan.")

    def _migrate_project(self, project, dry_run: bool, force: bool):
        with transaction.atomic():
            Project.objects.select_for_update().filter(id=project.id).first()

            base_rows = list(
                ProjectParameter.objects.select_for_update()
                .filter(project=project)
                .order_by("id")
            )
            computed_rows = list(
                ProjectComputedParameter.objects.select_for_update()
                .filter(project=project)
                .order_by("id")
            )
            volume_formulas = list(
                VolumeFormulaState.objects.select_for_update()
                .filter(project=project)
                .order_by("id")
            )

            if not base_rows and not computed_rows:
                return self._result(status="skipped")

            if dry_run:
                next_counters = {
                    "bp": self._max_suffix(base_rows, "bp"),
                    "cp": self._max_suffix(computed_rows, "cp"),
                }
            else:
                self._sync_sequence_seed(project, "bp", base_rows)
                self._sync_sequence_seed(project, "cp", computed_rows)
                next_counters = None

            def allocate(prefix: str) -> str:
                if dry_run:
                    next_counters[prefix] += 1
                    return f"{prefix}_{next_counters[prefix]}"
                return self._next_opaque_name(project, prefix)

            base_map, base_changes = self._build_name_map(
                rows=base_rows,
                matcher=BASE_RE,
                prefix="bp",
                force=force,
                allocate=allocate,
            )
            computed_map, computed_changes = self._build_name_map(
                rows=computed_rows,
                matcher=COMPUTED_RE,
                prefix="cp",
                force=force,
                allocate=allocate,
            )

            combined_map = {**base_map, **computed_map}
            allowed_ids = set(base_map.values()) | set(computed_map.values())

            computed_expr_updates = self._remap_computed_expressions(
                computed_rows,
                combined_map,
                allowed_ids,
            )
            volume_expr_updates = self._remap_volume_formulas(
                volume_formulas,
                combined_map,
                allowed_ids,
            )

            base_migrated = sum(1 for _, old, new in base_changes if old != new)
            computed_migrated = sum(1 for _, old, new in computed_changes if old != new)

            if (
                base_migrated == 0
                and computed_migrated == 0
                and not computed_expr_updates
                and not volume_expr_updates
            ):
                return self._result(status="skipped")

            logs_created = 0
            if not dry_run:
                self._apply_name_changes(ProjectParameter, base_changes, "bp")
                self._apply_name_changes(ProjectComputedParameter, computed_changes, "cp")
                self._apply_expression_updates(ProjectComputedParameter, computed_expr_updates, "expression")
                self._apply_expression_updates(VolumeFormulaState, volume_expr_updates, "raw")
                logs_created = self._write_migration_logs(
                    project,
                    base_changes,
                    computed_changes,
                )

            return self._result(
                status="ok",
                base_migrated=base_migrated,
                computed_migrated=computed_migrated,
                computed_formulas_updated=len(computed_expr_updates),
                volume_formulas_updated=len(volume_expr_updates),
                logs_created=logs_created,
            )

    @staticmethod
    def _result(
        *,
        status,
        base_migrated=0,
        computed_migrated=0,
        computed_formulas_updated=0,
        volume_formulas_updated=0,
        logs_created=0,
    ):
        return {
            "status": status,
            "base_migrated": base_migrated,
            "computed_migrated": computed_migrated,
            "computed_formulas_updated": computed_formulas_updated,
            "volume_formulas_updated": volume_formulas_updated,
            "logs_created": logs_created,
        }

    @staticmethod
    def _max_suffix(rows, prefix: str) -> int:
        pattern = re.compile(PREFIX_RE_TEMPLATE.format(prefix=prefix))
        max_num = 0
        for row in rows:
            name = str(row.name or "").strip().lower()
            match = pattern.match(name)
            if not match:
                continue
            value = int(match.group(1))
            if value > max_num:
                max_num = value
        return max_num

    def _sync_sequence_seed(self, project, prefix: str, rows):
        max_num = self._max_suffix(rows, prefix)
        seq, _ = ParameterSequence.objects.select_for_update().get_or_create(
            project=project,
            prefix=prefix,
            defaults={"last_num": 0},
        )
        if seq.last_num < max_num:
            seq.last_num = max_num
            seq.save(update_fields=["last_num", "updated_at"])

    @staticmethod
    def _next_opaque_name(project, prefix: str) -> str:
        seq, _ = ParameterSequence.objects.select_for_update().get_or_create(
            project=project,
            prefix=prefix,
            defaults={"last_num": 0},
        )
        seq.last_num += 1
        seq.save(update_fields=["last_num", "updated_at"])
        return f"{prefix}_{seq.last_num}"

    @staticmethod
    def _build_name_map(*, rows, matcher, prefix: str, force: bool, allocate):
        name_map = {}
        changes = []
        for row in rows:
            old_name = str(row.name or "").strip().lower()
            if not old_name:
                continue
            if matcher.match(old_name) and not force:
                new_name = old_name
            else:
                new_name = allocate(prefix)
            name_map[old_name] = new_name
            if old_name != new_name:
                changes.append((row, old_name, new_name))
        return name_map, changes

    def _remap_computed_expressions(self, rows, name_map, allowed_ids):
        updates = []
        for row in rows:
            old_expr = str(row.expression or "")
            new_expr = remap_expression(old_expr, name_map)
            unknown = self._find_unknown_identifiers(new_expr, allowed_ids)
            if unknown:
                raise CommandError(
                    f"ProjectComputedParameter id={row.id} expression invalid after remap. "
                    f"Unknown identifiers: {', '.join(unknown)}"
                )
            if new_expr != old_expr:
                updates.append((row.id, new_expr))
        return updates

    def _remap_volume_formulas(self, rows, name_map, allowed_ids):
        updates = []
        for row in rows:
            old_raw = str(row.raw or "")
            new_raw = remap_expression(old_raw, name_map)
            unknown = self._find_unknown_identifiers(new_raw, allowed_ids)
            if unknown:
                raise CommandError(
                    f"VolumeFormulaState id={row.id} raw invalid after remap. "
                    f"Unknown identifiers: {', '.join(unknown)}"
                )
            if new_raw != old_raw:
                updates.append((row.id, new_raw))
        return updates

    @staticmethod
    def _find_unknown_identifiers(expr: str, allowed_ids):
        unknown = set()
        for token_type, token_value, _, _ in tokenize_formula(expr):
            if token_type != "id":
                continue
            ident = str(token_value or "").strip().lower()
            if not ident:
                continue
            if ident in allowed_ids or ident in RESERVED_IDENTIFIERS:
                continue
            unknown.add(ident)
        return sorted(unknown)

    @staticmethod
    def _apply_name_changes(model_cls, changes, temp_prefix: str):
        if not changes:
            return
        ts = timezone.now()
        for row, _, _ in changes:
            temp_name = f"tmp_{temp_prefix}_{row.id}"
            model_cls.objects.filter(id=row.id).update(name=temp_name, updated_at=ts)
        for row, _, new_name in changes:
            model_cls.objects.filter(id=row.id).update(name=new_name, updated_at=ts)

    @staticmethod
    def _apply_expression_updates(model_cls, updates, field_name: str):
        if not updates:
            return
        ts = timezone.now()
        for row_id, new_expr in updates:
            model_cls.objects.filter(id=row_id).update(
                **{
                    field_name: new_expr,
                    "updated_at": ts,
                }
            )

    @staticmethod
    def _write_migration_logs(project, base_changes, computed_changes):
        created = 0
        for _, old_name, new_name in base_changes:
            _, was_created = ParameterMigrationLog.objects.get_or_create(
                project=project,
                old_name=old_name,
                new_name=new_name,
                param_type=ParameterMigrationLog.TYPE_BASE,
            )
            created += 1 if was_created else 0

        for _, old_name, new_name in computed_changes:
            _, was_created = ParameterMigrationLog.objects.get_or_create(
                project=project,
                old_name=old_name,
                new_name=new_name,
                param_type=ParameterMigrationLog.TYPE_COMPUTED,
            )
            created += 1 if was_created else 0

        return created
