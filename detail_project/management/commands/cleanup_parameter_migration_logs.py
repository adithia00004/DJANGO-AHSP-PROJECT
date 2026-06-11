from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import ParameterMigrationLog


class Command(BaseCommand):
    help = (
        "Cleanup ParameterMigrationLog older than rollback window. "
        "Use dry-run first before deleting."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=7,
            help="Delete logs with migrated_at older than N days (default: 7).",
        )
        parser.add_argument(
            "--project-id",
            type=int,
            help="Cleanup specific project ID only.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview deletion result without writing database changes.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Run without interactive confirmation.",
        )

    def handle(self, *args, **options):
        older_than_days = int(options.get("older_than_days") or 7)
        project_id = options.get("project_id")
        dry_run = bool(options.get("dry_run"))
        skip_confirm = bool(options.get("yes"))

        if older_than_days < 0:
            raise CommandError("--older-than-days tidak boleh negatif.")

        cutoff = timezone.now() - timedelta(days=older_than_days)

        queryset = ParameterMigrationLog.objects.filter(migrated_at__lt=cutoff)
        if project_id:
            if not Project.objects.filter(id=project_id).exists():
                raise CommandError(f"Project {project_id} tidak ditemukan.")
            queryset = queryset.filter(project_id=project_id)

        total = queryset.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "Tidak ada ParameterMigrationLog yang memenuhi kriteria cleanup."
                )
            )
            return

        self.stdout.write(
            "Cleanup target: "
            f"{total} log(s), cutoff={cutoff.isoformat()}, "
            f"project_id={project_id or 'ALL'}, dry_run={dry_run}"
        )

        project_breakdown = (
            queryset.values("project_id")
            .annotate(total=Count("id"))
            .order_by("project_id")
        )
        for row in project_breakdown:
            self.stdout.write(f" - project_id={row['project_id']}: {row['total']} log(s)")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("DRY-RUN selesai. Tidak ada data dihapus."))
            return

        if not skip_confirm:
            confirm = input("Type 'CLEANUP' to continue: ").strip()
            if confirm != "CLEANUP":
                raise CommandError("Dibatalkan oleh user.")

        deleted_count, _ = queryset.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup selesai. Deleted logs: {deleted_count}"
            )
        )
