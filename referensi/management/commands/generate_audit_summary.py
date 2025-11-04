"""
Management command to generate AuditLogSummary records.

Pre-aggregates audit log statistics for dashboard performance.

Usage:
    python manage.py generate_audit_summary
    python manage.py generate_audit_summary --period=daily
    python manage.py generate_audit_summary --period=hourly --date=2025-01-01
    python manage.py generate_audit_summary --period=weekly --regenerate
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from referensi.models import SecurityAuditLog, AuditLogSummary


class Command(BaseCommand):
    help = 'Generate audit log summary statistics for dashboard performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            default='daily',
            choices=['hourly', 'daily', 'weekly', 'monthly'],
            help='Period type for summary (default: daily)'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Date to generate summary for (YYYY-MM-DD). Default: today/latest'
        )
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Regenerate existing summaries (overwrites existing data)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to generate summaries for (default: 7)'
        )

    def handle(self, *args, **options):
        period_type = options['period']
        date_str = options['date']
        regenerate = options['regenerate']
        days = options['days']

        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('Audit Summary Generation'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Parse date
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                target_date = timezone.make_aware(target_date)
            except ValueError:
                raise CommandError('Invalid date format. Use YYYY-MM-DD')
        else:
            target_date = timezone.now()

        # Generate summaries
        total_created = 0
        total_updated = 0

        if period_type == 'hourly':
            created, updated = self._generate_hourly(target_date, days, regenerate)
        elif period_type == 'daily':
            created, updated = self._generate_daily(target_date, days, regenerate)
        elif period_type == 'weekly':
            created, updated = self._generate_weekly(target_date, regenerate)
        elif period_type == 'monthly':
            created, updated = self._generate_monthly(target_date, regenerate)

        total_created += created
        total_updated += updated

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✓ Summary generation complete!'))
        self.stdout.write(self.style.SUCCESS(f'✓ Created: {total_created} summaries'))
        self.stdout.write(self.style.SUCCESS(f'✓ Updated: {total_updated} summaries'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

    def _generate_hourly(self, target_date, days, regenerate):
        """Generate hourly summaries for the past N days."""
        self.stdout.write(f'Generating hourly summaries for {days} days...')
        created = 0
        updated = 0

        for day_offset in range(days):
            day = target_date - timedelta(days=day_offset)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)

            for hour in range(24):
                period_start = day_start + timedelta(hours=hour)
                period_end = period_start + timedelta(hours=1)

                c, u = self._create_summary(
                    'hourly',
                    period_start,
                    period_end,
                    regenerate
                )
                created += c
                updated += u

            self.stdout.write(f'  Day {day_offset + 1}/{days}: {day_start.date()}', ending='')
            self.stdout.write(self.style.SUCCESS(' ✓'))

        return created, updated

    def _generate_daily(self, target_date, days, regenerate):
        """Generate daily summaries for the past N days."""
        self.stdout.write(f'Generating daily summaries for {days} days...')
        created = 0
        updated = 0

        for day_offset in range(days):
            day = target_date - timedelta(days=day_offset)
            period_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)

            c, u = self._create_summary(
                'daily',
                period_start,
                period_end,
                regenerate
            )
            created += c
            updated += u

            self.stdout.write(f'  {period_start.date()}', ending='')
            self.stdout.write(self.style.SUCCESS(' ✓'))

        return created, updated

    def _generate_weekly(self, target_date, regenerate):
        """Generate weekly summary for the current week."""
        self.stdout.write('Generating weekly summary...')

        # Get start of week (Monday)
        weekday = target_date.weekday()
        period_start = target_date - timedelta(days=weekday)
        period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=7)

        created, updated = self._create_summary(
            'weekly',
            period_start,
            period_end,
            regenerate
        )

        self.stdout.write(f'  Week of {period_start.date()}', ending='')
        self.stdout.write(self.style.SUCCESS(' ✓'))

        return created, updated

    def _generate_monthly(self, target_date, regenerate):
        """Generate monthly summary for the current month."""
        self.stdout.write('Generating monthly summary...')

        # Get start of month
        period_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get start of next month
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)

        created, updated = self._create_summary(
            'monthly',
            period_start,
            period_end,
            regenerate
        )

        self.stdout.write(f'  {period_start.strftime("%B %Y")}', ending='')
        self.stdout.write(self.style.SUCCESS(' ✓'))

        return created, updated

    def _create_summary(self, period_type, period_start, period_end, regenerate):
        """Create or update summary for a specific period."""
        created_count = 0
        updated_count = 0

        # Get logs for this period
        logs = SecurityAuditLog.objects.filter(
            timestamp__gte=period_start,
            timestamp__lt=period_end
        )

        if logs.count() == 0:
            return 0, 0

        # Calculate statistics for each severity/category combination
        for severity_code, _ in SecurityAuditLog.SEVERITY_CHOICES:
            for category_code, _ in SecurityAuditLog.CATEGORY_CHOICES:
                # Filter logs for this combination
                filtered_logs = logs.filter(
                    severity=severity_code,
                    category=category_code
                )

                event_count = filtered_logs.count()
                if event_count == 0 and not regenerate:
                    continue

                # Calculate unique users and IPs
                unique_users = filtered_logs.values('username').distinct().count()
                unique_ips = filtered_logs.values('ip_address').distinct().count()

                # Get top events
                top_events = list(
                    filtered_logs.values('event_type')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )

                # Get top users
                top_users = list(
                    filtered_logs.exclude(username='')
                    .values('username')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )

                # Create or update summary
                summary, created = AuditLogSummary.objects.update_or_create(
                    period_type=period_type,
                    period_start=period_start,
                    category=category_code,
                    severity=severity_code,
                    defaults={
                        'period_end': period_end,
                        'event_count': event_count,
                        'unique_users': unique_users,
                        'unique_ips': unique_ips,
                        'top_events': top_events,
                        'top_users': top_users,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count
