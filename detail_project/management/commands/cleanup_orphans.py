from django.core.management.base import BaseCommand
from detail_project.services import cleanup_orphaned_items
from dashboard.models import Project


class Command(BaseCommand):
    help = "Cleanup orphaned HargaItemProject per project"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Project ID yang akan dibersihkan",
        )
        parser.add_argument(
            "--all-projects",
            action="store_true",
            help="Jalankan untuk semua project aktif",
        )
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=0,
            help="Hanya hapus orphan yang terakhir terpakai lebih tua dari N hari",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Batasi jumlah orphan yang dibersihkan per project",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hanya tampilkan kandidat tanpa menghapus",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        all_projects = options.get("all_projects")
        older_than_days = options.get("older_than_days")
        limit = options.get("limit")
        dry_run = options.get("dry_run")

        if not project_id and not all_projects:
            self.stderr.write(
                self.style.ERROR(
                    "Harus menentukan --project-id atau --all-projects"
                )
            )
            return

        if project_id and all_projects:
            self.stderr.write(
                self.style.ERROR(
                    "Gunakan salah satu: --project-id atau --all-projects"
                )
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

        total_deleted = 0
        total_value = 0
        total_candidates = 0

        for project in projects:
            result = cleanup_orphaned_items(
                project,
                older_than_days=older_than_days,
                dry_run=dry_run,
                limit=limit,
            )

            total_candidates += result["candidate_count"]
            if not dry_run:
                total_deleted += result["deleted_count"]
                total_value += result["deleted_value"]

            cutoff_msg = (
                f", older_than={older_than_days}d"
                if older_than_days and older_than_days > 0
                else ""
            )
            limit_msg = f", limit={limit}" if limit else ""
            header = (
                f"[Project {project.id}] candidates={result['candidate_count']}"
                f"{cutoff_msg}{limit_msg}"
            )
            self.stdout.write(header)

            if dry_run:
                self.stdout.write(
                    f"  DRY-RUN: {result['candidate_count']} orphan "
                    f"(total value {result['candidate_value']})"
                )
            else:
                self.stdout.write(
                    f"  Deleted {result['deleted_count']} orphan items "
                    f"(value {result['deleted_value']})"
                )
                if result["skipped_ids"]:
                    self.stdout.write(
                        f"  Skipped (tidak orphan lagi): {result['skipped_ids']}"
                    )

        footer = (
            f"Total candidates: {total_candidates}. "
            f"{'Dry-run selesai.' if dry_run else f'Deleted {total_deleted} items (value {total_value}).'}"
        )
        self.stdout.write(self.style.SUCCESS(footer))
