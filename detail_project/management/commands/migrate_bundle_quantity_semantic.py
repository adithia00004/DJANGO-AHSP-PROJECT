from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from dashboard.models import Project
from detail_project.models import DetailAHSPProject, HargaItemProject, Pekerjaan
from detail_project.services import _populate_expanded_from_raw


class Command(BaseCommand):
    help = (
        "Re-expand seluruh pekerjaan bundle agar memakai quantity semantic (koef per unit). "
        "Jalankan setelah deploy Phase 1/2 dan sebelum agregasi/migrasi final."
    )

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, help="Hanya migrasi satu project.")
        parser.add_argument("--all", action="store_true", help="Migrasi semua project.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hitung data yang akan diproses tanpa memodifikasi database.",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        migrate_all = options.get("all")
        dry_run = options.get("dry_run")

        if not project_id and not migrate_all:
            raise CommandError("Gunakan --project-id atau --all")

        projects = Project.objects.all() if migrate_all else Project.objects.filter(pk=project_id)

        if not projects.exists():
            self.stdout.write(self.style.WARNING("Tidak ada project yang cocok dengan parameter."))
            return

        total_bundles = 0
        total_pekerjaan = 0

        for project in projects:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(f"=== Project {project.id} - {project.nama} ==="))

            bundle_qs = DetailAHSPProject.objects.filter(
                project=project,
                kategori=HargaItemProject.KATEGORI_LAIN,
            ).filter(
                models.Q(ref_pekerjaan__isnull=False) | models.Q(ref_ahsp__isnull=False)
            )

            bundle_count = bundle_qs.count()
            if bundle_count == 0:
                self.stdout.write("  Tidak ada bundle, skip.")
                continue

            pekerjaan_ids = list(bundle_qs.values_list("pekerjaan_id", flat=True).distinct())
            total_bundles += bundle_count
            total_pekerjaan += len(pekerjaan_ids)

            self.stdout.write(f"  Ditemukan {bundle_count} bundle pada {len(pekerjaan_ids)} pekerjaan.")

            for pkj_id in pekerjaan_ids:
                try:
                    pekerjaan = Pekerjaan.objects.get(pk=pkj_id, project=project)
                except Pekerjaan.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"    - Pekerjaan {pkj_id} tidak ditemukan, skip."))
                    continue

                bundle_rows = bundle_qs.filter(pekerjaan=pekerjaan).count()
                self.stdout.write(f"    - Pekerjaan {pekerjaan.snapshot_kode} ({bundle_rows} bundle row)")

                if dry_run:
                    continue

                try:
                    with transaction.atomic():
                        _populate_expanded_from_raw(project, pekerjaan)
                    self.stdout.write("      [OK] Re-expand sukses")
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"      [ERROR] {exc}"))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== RINGKASAN ==="))
        self.stdout.write(f"Project diproses : {projects.count()}")
        self.stdout.write(f"Total bundle     : {total_bundles}")
        self.stdout.write(f"Pekerjaan bundle : {total_pekerjaan}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: tidak ada perubahan yang disimpan."))
        else:
            self.stdout.write(self.style.SUCCESS("Migrasi selesai."))
