import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from dashboard.models import Project
from detail_project.formula_tokenizer import remap_expression, tokenize_formula
from detail_project.models import (
    ParameterMigrationLog,
    ProjectComputedParameter,
    ProjectParameter,
    VolumeFormulaState,
)


BASE_RE = re.compile(r"^bp_[1-9][0-9]*$")
COMPUTED_RE = re.compile(r"^cp_[1-9][0-9]*$")
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
    help = (
        "Rollback opaque parameter names to legacy names using ParameterMigrationLog mapping."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Rollback specific project ID. If omitted, rollback all projects with migration logs.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview rollback without writing database changes.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Run without confirmation prompt.",
        )
        parser.add_argument(
            "--allow-missing-log",
            action="store_true",
            help=(
                "Allow opaque names without mapping log to remain unchanged. "
                "Default behavior is strict and fails if mapping is missing."
            ),
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        dry_run = bool(options.get("dry_run"))
        skip_confirm = bool(options.get("yes"))
        allow_missing_log = bool(options.get("allow_missing_log"))

        if project_id:
            projects = Project.objects.filter(id=project_id).order_by("id")
            if not projects.exists():
                raise CommandError(f"Project {project_id} tidak ditemukan.")
        else:
            project_ids = (
                ParameterMigrationLog.objects.values_list("project_id", flat=True)
                .distinct()
                .order_by("project_id")
            )
            projects = Project.objects.filter(id__in=project_ids).order_by("id")

        total_projects = projects.count()
        if total_projects == 0:
            self.stdout.write(
                self.style.WARNING("Tidak ada project dengan migration log untuk rollback.")
            )
            return

        self.stdout.write(
            f"Target rollback: {total_projects} project(s). "
            f"(dry_run={dry_run}, allow_missing_log={allow_missing_log})"
        )

        if not dry_run and not skip_confirm:
            confirm = input("Type 'ROLLBACK' to continue: ").strip()
            if confirm != "ROLLBACK":
                raise CommandError("Dibatalkan oleh user.")

        summary = {
            "ok": 0,
            "skipped": 0,
            "failed": 0,
            "base_rolled_back": 0,
            "computed_rolled_back": 0,
            "computed_formulas_updated": 0,
            "volume_formulas_updated": 0,
        }

        for project in projects:
            try:
                result = self._rollback_project(
                    project,
                    dry_run=dry_run,
                    allow_missing_log=allow_missing_log,
                )
                status = result["status"]
                if status == "skipped":
                    summary["skipped"] += 1
                else:
                    summary["ok"] += 1

                summary["base_rolled_back"] += result["base_rolled_back"]
                summary["computed_rolled_back"] += result["computed_rolled_back"]
                summary["computed_formulas_updated"] += result["computed_formulas_updated"]
                summary["volume_formulas_updated"] += result["volume_formulas_updated"]

                self.stdout.write(
                    f"[{status.upper()}] project_id={project.id} "
                    f"base_rolled_back={result['base_rolled_back']} "
                    f"computed_rolled_back={result['computed_rolled_back']} "
                    f"computed_formulas_updated={result['computed_formulas_updated']} "
                    f"volume_formulas_updated={result['volume_formulas_updated']}"
                )
            except Exception as exc:
                summary["failed"] += 1
                self.stdout.write(
                    self.style.ERROR(f"[FAILED] project_id={project.id} error={exc}")
                )

        self.stdout.write("\n=== ROLLBACK SUMMARY ===")
        for key in (
            "ok",
            "skipped",
            "failed",
            "base_rolled_back",
            "computed_rolled_back",
            "computed_formulas_updated",
            "volume_formulas_updated",
        ):
            self.stdout.write(f"{key}: {summary[key]}")

        if summary["failed"] > 0:
            raise CommandError("Sebagian project gagal di-rollback.")

    def _rollback_project(self, project, *, dry_run: bool, allow_missing_log: bool):
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

            logs = list(
                ParameterMigrationLog.objects.select_for_update()
                .filter(project=project)
                .order_by("-migrated_at", "-id")
            )
            if not logs:
                return self._result(status="skipped")

            reverse_base = self._build_reverse_map(
                logs=logs, param_type=ParameterMigrationLog.TYPE_BASE
            )
            reverse_computed = self._build_reverse_map(
                logs=logs, param_type=ParameterMigrationLog.TYPE_COMPUTED
            )

            base_changes, missing_base = self._plan_name_changes(
                rows=base_rows,
                matcher=BASE_RE,
                reverse_map=reverse_base,
            )
            computed_changes, missing_computed = self._plan_name_changes(
                rows=computed_rows,
                matcher=COMPUTED_RE,
                reverse_map=reverse_computed,
            )
            missing = missing_base + missing_computed
            if missing and not allow_missing_log:
                raise CommandError(
                    "Mapping log tidak lengkap untuk rollback: "
                    + ", ".join(sorted(set(missing))[:15])
                )

            target_base_names = self._collect_target_names(base_rows, base_changes)
            target_computed_names = self._collect_target_names(computed_rows, computed_changes)
            self._assert_unique_targets("base", target_base_names)
            self._assert_unique_targets("computed", target_computed_names)

            name_map = {
                old_name: new_name
                for _, old_name, new_name in (base_changes + computed_changes)
                if old_name != new_name
            }
            allowed_ids = set(target_base_names) | set(target_computed_names)

            computed_expr_updates = self._remap_computed_expressions(
                computed_rows,
                name_map,
                allowed_ids,
            )
            volume_expr_updates = self._remap_volume_formulas(
                volume_formulas,
                name_map,
                allowed_ids,
            )

            base_rolled_back = sum(1 for _, old, new in base_changes if old != new)
            computed_rolled_back = sum(1 for _, old, new in computed_changes if old != new)

            if (
                base_rolled_back == 0
                and computed_rolled_back == 0
                and not computed_expr_updates
                and not volume_expr_updates
            ):
                return self._result(status="skipped")

            if not dry_run:
                self._apply_name_changes(ProjectParameter, base_changes, "rbp")
                self._apply_name_changes(ProjectComputedParameter, computed_changes, "rcp")
                self._apply_expression_updates(ProjectComputedParameter, computed_expr_updates, "expression")
                self._apply_expression_updates(VolumeFormulaState, volume_expr_updates, "raw")

            return self._result(
                status="ok",
                base_rolled_back=base_rolled_back,
                computed_rolled_back=computed_rolled_back,
                computed_formulas_updated=len(computed_expr_updates),
                volume_formulas_updated=len(volume_expr_updates),
            )

    @staticmethod
    def _result(
        *,
        status,
        base_rolled_back=0,
        computed_rolled_back=0,
        computed_formulas_updated=0,
        volume_formulas_updated=0,
    ):
        return {
            "status": status,
            "base_rolled_back": base_rolled_back,
            "computed_rolled_back": computed_rolled_back,
            "computed_formulas_updated": computed_formulas_updated,
            "volume_formulas_updated": volume_formulas_updated,
        }

    @staticmethod
    def _build_reverse_map(*, logs, param_type: str):
        reverse_map = {}
        for log in logs:
            if log.param_type != param_type:
                continue
            new_name = str(log.new_name or "").strip().lower()
            old_name = str(log.old_name or "").strip().lower()
            if not new_name or not old_name:
                continue
            # Keep latest log if there are multiple history entries.
            if new_name not in reverse_map:
                reverse_map[new_name] = old_name
        return reverse_map

    @staticmethod
    def _plan_name_changes(*, rows, matcher, reverse_map):
        changes = []
        missing_logs = []
        for row in rows:
            old_name = str(row.name or "").strip().lower()
            if not old_name:
                continue
            if matcher.match(old_name):
                new_name = reverse_map.get(old_name)
                if new_name is None:
                    missing_logs.append(old_name)
                    new_name = old_name
            else:
                new_name = old_name
            changes.append((row, old_name, new_name))
        return changes, missing_logs

    @staticmethod
    def _collect_target_names(rows, changes):
        mapped = {row.id: new_name for row, _, new_name in changes}
        out = []
        for row in rows:
            current = str(row.name or "").strip().lower()
            out.append(mapped.get(row.id, current))
        return out

    @staticmethod
    def _assert_unique_targets(label: str, names):
        normalized = [str(name or "").strip().lower() for name in names if str(name or "").strip()]
        if len(normalized) != len(set(normalized)):
            raise CommandError(
                f"Rollback menghasilkan duplikasi nama pada {label} parameter."
            )

    def _remap_computed_expressions(self, rows, name_map, allowed_ids):
        updates = []
        for row in rows:
            old_expr = str(row.expression or "")
            new_expr = remap_expression(old_expr, name_map)
            unknown = self._find_unknown_identifiers(new_expr, allowed_ids)
            if unknown:
                raise CommandError(
                    f"ProjectComputedParameter id={row.id} expression invalid after rollback. "
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
                    f"VolumeFormulaState id={row.id} raw invalid after rollback. "
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
            if ident in allowed_ids:
                continue
            if ident in RESERVED_IDENTIFIERS:
                continue
            unknown.add(ident)
        return sorted(unknown)

    @staticmethod
    def _apply_name_changes(model_cls, changes, temp_prefix: str):
        if not changes:
            return
        ts = timezone.now()
        for row, old_name, new_name in changes:
            if old_name == new_name:
                continue
            temp_name = f"tmp_{temp_prefix}_{row.id}"
            model_cls.objects.filter(id=row.id).update(name=temp_name, updated_at=ts)
        for row, old_name, new_name in changes:
            if old_name == new_name:
                continue
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
