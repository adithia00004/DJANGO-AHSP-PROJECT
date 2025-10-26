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
        for project in projects_without_timeline:
            # Set defaults
            today = timezone.now().date()

            if not project.tanggal_mulai:
                project.tanggal_mulai = today

            if not project.tanggal_selesai:
                # Default: 31 Desember tahun project
                year = project.tahun_project if project.tahun_project else project.tanggal_mulai.year
                project.tanggal_selesai = date(year, 12, 31)

            if not project.durasi_hari:
                delta = (project.tanggal_selesai - project.tanggal_mulai).days + 1
                project.durasi_hari = delta

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Project "{project.nama_project}" would be updated:\n'
                    f'    - tanggal_mulai: {project.tanggal_mulai}\n'
                    f'    - tanggal_selesai: {project.tanggal_selesai}\n'
                    f'    - durasi_hari: {project.durasi_hari}'
                )
            else:
                project.save()
                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated Project "{project.nama_project}"\n'
                        f'    - tanggal_mulai: {project.tanggal_mulai}\n'
                        f'    - tanggal_selesai: {project.tanggal_selesai}\n'
                        f'    - durasi_hari: {project.durasi_hari}'
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDry run complete. {count} project(s) would be updated.\n'
                    f'Run without --dry-run to apply changes.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Successfully updated {updated} project(s).'
                )
            )
