"""
Generate Sample Weekly Tahapan (Time Periods)
Management command to create weekly tahapan for testing charts

This creates TahapPelaksanaan records that will appear as time columns in the grid.

Usage:
    python manage.py generate_sample_weekly_tahapan <project_id>
    python manage.py generate_sample_weekly_tahapan 110 --weeks 12
    python manage.py generate_sample_weekly_tahapan 110 --weeks 12 --start-date 2025-01-01
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from dashboard.models import Project
from detail_project.models import TahapPelaksanaan


class Command(BaseCommand):
    help = 'Generate sample weekly tahapan (time periods) for project scheduling'

    def add_arguments(self, parser):
        parser.add_argument(
            'project_id',
            type=int,
            help='Project ID to generate tahapan for'
        )
        parser.add_argument(
            '--weeks',
            type=int,
            default=12,
            help='Number of weeks to generate (default: 12)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD), defaults to project start or today'
        )
        parser.add_argument(
            '--clear-auto',
            action='store_true',
            help='Clear existing auto-generated weekly tahapan before creating new ones'
        )

    def handle(self, *args, **options):
        project_id = options['project_id']
        num_weeks = options['weeks']
        start_date_str = options.get('start_date')
        clear_auto = options['clear_auto']

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Project {project_id} not found'))
            return

        # Determine start date
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        elif hasattr(project, 'tanggal_mulai') and project.tanggal_mulai:
            start_date = project.tanggal_mulai
        elif hasattr(project, 'start_date') and project.start_date:
            start_date = project.start_date
        else:
            start_date = timezone.now().date()

        project_name = getattr(project, 'nama', getattr(project, 'name', f'Project #{project_id}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  GENERATE WEEKLY TAHAPAN (Time Columns)'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Project: {project_name} (ID: {project_id})')
        self.stdout.write(f'Start date: {start_date}')
        self.stdout.write(f'Number of weeks: {num_weeks}')
        self.stdout.write('')

        # Clear existing auto-generated weekly tahapan if requested
        if clear_auto:
            deleted_count = TahapPelaksanaan.objects.filter(
                project=project,
                is_auto_generated=True,
                generation_mode='weekly'
            ).count()

            if deleted_count > 0:
                TahapPelaksanaan.objects.filter(
                    project=project,
                    is_auto_generated=True,
                    generation_mode='weekly'
                ).delete()
                self.stdout.write(
                    self.style.WARNING(f'🗑️  Cleared {deleted_count} existing auto-generated weekly tahapan')
                )
                self.stdout.write('')

        created_count = 0
        skipped_count = 0

        for week_num in range(num_weeks):
            week_start = start_date + timedelta(weeks=week_num)
            week_end = week_start + timedelta(days=6)  # 7-day week (inclusive)

            tahap_name = f"Week {week_num + 1}"

            # Check if tahapan with this name already exists
            existing = TahapPelaksanaan.objects.filter(
                project=project,
                nama=tahap_name
            ).exists()

            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f'  Week {week_num + 1:2d}: {week_start} to {week_end} [EXISTS] "{tahap_name}"'
                    )
                )
                skipped_count += 1
                continue

            # Create new tahapan
            tahapan = TahapPelaksanaan.objects.create(
                project=project,
                nama=tahap_name,
                urutan=week_num,
                deskripsi=f"Auto-generated weekly period: {week_start} to {week_end}",
                tanggal_mulai=week_start,
                tanggal_selesai=week_end,
                is_auto_generated=True,
                generation_mode='weekly'
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'  Week {week_num + 1:2d}: {week_start} to {week_end} [CREATED] (ID: {tahapan.id})'
                )
            )
            created_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count} tahapan'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} existing tahapan'))
        self.stdout.write(self.style.SUCCESS('-' * 70))

        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('1. Refresh the jadwal-pekerjaan page')
        self.stdout.write('2. Check time columns appear in grid header (right panel)')
        self.stdout.write('3. Assign pekerjaan to weekly tahapan by entering percentages in cells')
        self.stdout.write('4. Verify Kurva-S and Gantt charts render with data')
        self.stdout.write('')
