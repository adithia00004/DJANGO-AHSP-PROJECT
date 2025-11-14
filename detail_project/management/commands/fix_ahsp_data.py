from django.core.management.base import BaseCommand
from dashboard.models import Project

from detail_project.services import fix_project_data


class Command(BaseCommand):
    help = "Fix AHSP data (re-expand bundles, cleanup orphans, etc.)"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, help="Project ID to fix")
        parser.add_argument(
            "--all-projects",
            action="store_true",
            help="Run fix for all active projects",
        )
        parser.add_argument(
            "--no-reexpand",
            action="store_true",
            help="Skip re-expanding DetailAHSPExpanded",
        )
        parser.add_argument(
            "--no-cleanup",
            action="store_true",
            help="Skip orphan cleanup",
        )
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=None,
            help="Only cleanup orphans older than N days",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of orphan items to cleanup per project",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run (report only, no changes)",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        all_projects = options.get("all_projects")
        dry_run = options.get("dry_run", False)
        reexpand = not options.get("no_reexpand")
        cleanup = not options.get("no_cleanup")
        older_than_days = options.get("older_than_days")
        limit = options.get("limit")

        if not project_id and not all_projects:
            self.stderr.write(
                self.style.ERROR("Gunakan --project-id atau --all-projects")
            )
            return
        if project_id and all_projects:
            self.stderr.write(
                self.style.ERROR("Gunakan salah satu: --project-id atau --all-projects")
            )
            return
        if not reexpand and not cleanup:
            self.stderr.write(
                self.style.ERROR("Tidak ada aksi yang dipilih (reexpand/cleanup)")
            )
            return

        if all_projects:
            projects = Project.objects.filter(is_active=True).order_by("id")
        else:
            try:
                projects = [Project.objects.get(id=project_id)]
            except Project.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Project {project_id} tidak ditemukan")
                )
                return

        for project in projects:
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"{'DRY-RUN ' if dry_run else ''}Fixing project #{project.id} {project.nama}"
                )
            )
            summary = fix_project_data(
                project,
                reexpand=reexpand,
                cleanup_orphans=cleanup,
                older_than_days=older_than_days,
                orphan_limit=limit,
                dry_run=dry_run,
            )
            self.stdout.write(f"  Re-expanded: {summary['reexpanded']}")
            if summary["cleanup"]:
                cleanup = summary["cleanup"]
                self.stdout.write(
                    f"  Cleanup: {cleanup['deleted_count']} deleted "
                    f"(dry_run={cleanup['dry_run']})"
                )
