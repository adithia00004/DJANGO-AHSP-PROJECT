import re
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from detail_project.models import ParameterMigrationLog, ProjectComputedParameter, ProjectParameter


BASE_RE = re.compile(r"^bp_[1-9][0-9]*$")
COMPUTED_RE = re.compile(r"^cp_[1-9][0-9]*$")


class Command(BaseCommand):
    help = "Generate post-deploy opaque ID health status (and optional strict gate checks)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Check only a specific project ID.",
        )
        parser.add_argument(
            "--window-days",
            type=int,
            default=7,
            help="Rollback window in days for cleanup check (default: 7).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail command if strict gate conditions are not met.",
        )
        parser.add_argument(
            "--require-cleanup",
            action="store_true",
            help="When used with --strict, fail if logs older than window still exist.",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        window_days = int(options.get("window_days") or 7)
        strict = bool(options.get("strict"))
        require_cleanup = bool(options.get("require_cleanup"))

        if window_days < 0:
            raise CommandError("--window-days tidak boleh negatif.")

        base_qs = ProjectParameter.objects.all()
        computed_qs = ProjectComputedParameter.objects.all()
        logs_qs = ParameterMigrationLog.objects.all()
        if project_id:
            base_qs = base_qs.filter(project_id=project_id)
            computed_qs = computed_qs.filter(project_id=project_id)
            logs_qs = logs_qs.filter(project_id=project_id)

        bad_base = self._count_bad_names(base_qs.values_list("name", flat=True), BASE_RE)
        bad_computed = self._count_bad_names(
            computed_qs.values_list("name", flat=True), COMPUTED_RE
        )

        cutoff = timezone.now() - timedelta(days=window_days)
        old_logs_count = logs_qs.filter(migrated_at__lt=cutoff).count()

        self.stdout.write("=== OPAQUE POST-DEPLOY STATUS ===")
        self.stdout.write(f"scope_project_id: {project_id or 'ALL'}")
        self.stdout.write(f"opaque_id_enabled: {bool(getattr(settings, 'OPAQUE_ID_ENABLED', True))}")
        self.stdout.write(f"base_total: {base_qs.count()}")
        self.stdout.write(f"computed_total: {computed_qs.count()}")
        self.stdout.write(f"non_opaque_base: {bad_base}")
        self.stdout.write(f"non_opaque_computed: {bad_computed}")
        self.stdout.write(f"migration_logs_total: {logs_qs.count()}")
        self.stdout.write(f"migration_logs_older_than_{window_days}d: {old_logs_count}")

        failures = []
        if strict:
            if not bool(getattr(settings, "OPAQUE_ID_ENABLED", True)):
                failures.append("OPAQUE_ID_ENABLED=False")
            if bad_base > 0:
                failures.append(f"non_opaque_base={bad_base}")
            if bad_computed > 0:
                failures.append(f"non_opaque_computed={bad_computed}")
            if require_cleanup and old_logs_count > 0:
                failures.append(
                    f"migration_logs_older_than_{window_days}d={old_logs_count}"
                )

        if failures:
            raise CommandError(" ; ".join(failures))

        if strict:
            self.stdout.write(self.style.SUCCESS("STRICT_GATE=PASS"))
        else:
            self.stdout.write(self.style.SUCCESS("STATUS_CHECK=PASS"))

    @staticmethod
    def _count_bad_names(names_iterable, pattern):
        count = 0
        for name in names_iterable:
            value = str(name or "").strip()
            if not pattern.match(value):
                count += 1
        return count
