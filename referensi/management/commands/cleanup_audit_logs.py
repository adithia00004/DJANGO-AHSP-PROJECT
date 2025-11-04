"""
Management command to cleanup old audit logs.

Usage:
    python manage.py cleanup_audit_logs
    python manage.py cleanup_audit_logs --days=90
    python manage.py cleanup_audit_logs --days=30 --keep-critical=180 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

from referensi.models import SecurityAuditLog


class Command(BaseCommand):
    help = 'Delete old audit logs to save database space'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete logs older than this many days (default: 90)'
        )
        parser.add_argument(
            '--keep-critical',
            type=int,
            default=180,
            help='Keep critical events for this many days (default: 180)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        days = options['days']
        keep_critical = options['keep_critical']
        dry_run = options['dry_run']
        force = options['force']

        # Validate parameters
        if days < 1:
            raise CommandError('--days must be at least 1')
        if keep_critical < days:
            raise CommandError('--keep-critical must be >= --days')

        # Calculate cutoff dates
        now = timezone.now()
        cutoff_normal = now - timedelta(days=days)
        cutoff_critical = now - timedelta(days=keep_critical)

        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('Audit Log Cleanup'))
        self.stdout.write(self.style.WARNING('=' * 70))

        # Get statistics
        total_logs = SecurityAuditLog.objects.count()

        # Non-critical old logs
        old_logs = SecurityAuditLog.objects.filter(
            timestamp__lt=cutoff_normal
        ).exclude(
            severity=SecurityAuditLog.SEVERITY_CRITICAL
        )
        old_count = old_logs.count()

        # Very old critical logs
        old_critical = SecurityAuditLog.objects.filter(
            timestamp__lt=cutoff_critical,
            severity=SecurityAuditLog.SEVERITY_CRITICAL
        )
        old_critical_count = old_critical.count()

        total_to_delete = old_count + old_critical_count

        # Display summary
        self.stdout.write('')
        self.stdout.write(f'Total audit logs in database: {self.style.SUCCESS(total_logs)}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Logs to be deleted:'))
        self.stdout.write(f'  • Non-critical logs older than {days} days: {self.style.ERROR(old_count)}')
        self.stdout.write(f'  • Critical logs older than {keep_critical} days: {self.style.ERROR(old_critical_count)}')
        self.stdout.write(f'  • Total to delete: {self.style.ERROR(total_to_delete)}')
        self.stdout.write('')
        self.stdout.write(f'Logs to be kept: {self.style.SUCCESS(total_logs - total_to_delete)}')
        self.stdout.write('')

        if total_to_delete == 0:
            self.stdout.write(self.style.SUCCESS('✓ No logs to delete. Database is clean!'))
            return

        # Show breakdown by severity
        if total_to_delete > 0:
            self.stdout.write(self.style.WARNING('Breakdown by severity:'))
            for severity_code, severity_label in SecurityAuditLog.SEVERITY_CHOICES:
                if severity_code == SecurityAuditLog.SEVERITY_CRITICAL:
                    count = old_critical.filter(severity=severity_code).count()
                else:
                    count = old_logs.filter(severity=severity_code).count()

                if count > 0:
                    self.stdout.write(f'  • {severity_label}: {count}')
            self.stdout.write('')

        # Show breakdown by category
        if total_to_delete > 0:
            self.stdout.write(self.style.WARNING('Breakdown by category:'))
            for category_code, category_label in SecurityAuditLog.CATEGORY_CHOICES:
                count = (
                    old_logs.filter(category=category_code).count() +
                    old_critical.filter(category=category_code).count()
                )
                if count > 0:
                    self.stdout.write(f'  • {category_label}: {count}')
            self.stdout.write('')

        # Dry run mode
        if dry_run:
            self.stdout.write(self.style.SUCCESS('✓ Dry run complete. No logs were deleted.'))
            self.stdout.write('')
            self.stdout.write('To actually delete logs, run without --dry-run flag')
            return

        # Confirmation prompt
        if not force:
            self.stdout.write(self.style.ERROR('⚠ WARNING: This action cannot be undone!'))
            self.stdout.write('')
            confirm = input('Are you sure you want to delete these logs? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Aborted. No logs were deleted.'))
                return

        # Perform deletion
        self.stdout.write('')
        self.stdout.write('Deleting logs...')

        deleted_count = 0

        # Delete non-critical old logs
        if old_count > 0:
            self.stdout.write(f'  Deleting {old_count} non-critical logs...', ending='')
            deleted, _ = old_logs.delete()
            deleted_count += deleted
            self.stdout.write(self.style.SUCCESS(f' ✓ Done ({deleted} deleted)'))

        # Delete very old critical logs
        if old_critical_count > 0:
            self.stdout.write(f'  Deleting {old_critical_count} old critical logs...', ending='')
            deleted, _ = old_critical.delete()
            deleted_count += deleted
            self.stdout.write(self.style.SUCCESS(f' ✓ Done ({deleted} deleted)'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✓ Cleanup complete!'))
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {deleted_count} audit logs'))
        self.stdout.write(self.style.SUCCESS(f'✓ Remaining logs: {SecurityAuditLog.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # Recommendations
        remaining = SecurityAuditLog.objects.count()
        if remaining > 50000:
            self.stdout.write(self.style.WARNING('ℹ Recommendation: You have over 50,000 logs.'))
            self.stdout.write(self.style.WARNING('  Consider running cleanup more frequently.'))
        elif remaining > 100000:
            self.stdout.write(self.style.ERROR('⚠ Warning: You have over 100,000 logs!'))
            self.stdout.write(self.style.ERROR('  This may impact performance. Run cleanup ASAP.'))
