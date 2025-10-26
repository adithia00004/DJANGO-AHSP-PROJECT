"""
Management command to set default timeline for existing projects without timeline.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from dashboard.models import Project


class Command(BaseCommand):
    help = 'Set default timeline (tanggal_mulai, tanggal_selesai, durasi_hari) for existing projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find projects without timeline
        projects_without_timeline = Project.objects.filter(
            tanggal_mulai__isnull=True
        ) | Project.objects.filter(
            tanggal_selesai__isnull=True
        )

        count = projects_without_timeline.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('All projects already have timeline set.'))
            return

        self.stdout.write(f'Found {count} project(s) without timeline.')

        updated = 0
        skipped = 0
        for project in projects_without_timeline:
            # Set defaults
            today = timezone.now().date()

            if not project.tanggal_mulai:
                project.tanggal_mulai = today

            if not project.tanggal_selesai:
                # Default: 31 Desember tahun dari tanggal_mulai (bukan tahun_project!)
                # Ini menghindari durasi negatif untuk old projects
                year = project.tanggal_mulai.year
                project.tanggal_selesai = date(year, 12, 31)

            if not project.durasi_hari:
                delta = (project.tanggal_selesai - project.tanggal_mulai).days + 1
                project.durasi_hari = delta

            # Skip if durasi would be negative (shouldn't happen now, but safety check)
            if project.durasi_hari < 1:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Skipped Project ID {project.id} (tahun_project: {project.tahun_project})\n'
                        f'    - Calculated durasi_hari would be negative: {project.durasi_hari}\n'
                        f'    - Please set timeline manually for this project'
                    )
                )
                continue

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Project ID {project.id} would be updated:\n'
                    f'    - tanggal_mulai: {project.tanggal_mulai}\n'
                    f'    - tanggal_selesai: {project.tanggal_selesai}\n'
                    f'    - durasi_hari: {project.durasi_hari}'
                )
            else:
                project.save()
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated Project ID {project.id}\n'
                        f'    - tanggal_mulai: {project.tanggal_mulai}\n'
                        f'    - tanggal_selesai: {project.tanggal_selesai}\n'
                        f'    - durasi_hari: {project.durasi_hari}'
                    )
                )

        if dry_run:
            message = f'\nDry run complete. {count} project(s) found.'
            if skipped > 0:
                message += f'\n{skipped} project(s) would be skipped (negative duration).'
            message += '\nRun without --dry-run to apply changes.'
            self.stdout.write(self.style.WARNING(message))
        else:
            message = f'\n✓ Successfully updated {updated} project(s).'
            if skipped > 0:
                message += f'\n⚠ Skipped {skipped} project(s) (negative duration).'
            self.stdout.write(self.style.SUCCESS(message))
