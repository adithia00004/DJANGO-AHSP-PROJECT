"""
Management command to send email alerts for critical security events.

Usage:
    python manage.py send_audit_alerts
    python manage.py send_audit_alerts --since="1 hour ago"
    python manage.py send_audit_alerts --severity=critical --dry-run
    python manage.py send_audit_alerts --force
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import timedelta
import re

from referensi.models import SecurityAuditLog


class Command(BaseCommand):
    help = 'Send email alerts for critical/error security events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since',
            type=str,
            default='1 hour',
            help='Check events since this time ago (e.g., "1 hour", "30 minutes", "2 days")'
        )
        parser.add_argument(
            '--severity',
            type=str,
            default='critical,error',
            help='Comma-separated severities to alert on (default: critical,error)'
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=1,
            help='Minimum number of events to trigger alert (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send alert even if recently sent (ignores rate limit)'
        )

    def handle(self, *args, **options):
        since_str = options['since']
        severity_str = options['severity']
        threshold = options['threshold']
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('Security Audit Alerts'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Parse since time
        try:
            since_delta = self._parse_time_delta(since_str)
            since_time = timezone.now() - since_delta
        except ValueError as e:
            raise CommandError(f'Invalid --since format: {e}')

        # Parse severities
        severities = [s.strip() for s in severity_str.split(',')]
        valid_severities = [s[0] for s in SecurityAuditLog.SEVERITY_CHOICES]
        for severity in severities:
            if severity not in valid_severities:
                raise CommandError(
                    f'Invalid severity "{severity}". '
                    f'Valid options: {", ".join(valid_severities)}'
                )

        self.stdout.write(f'Checking for events:')
        self.stdout.write(f'  • Since: {since_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'  • Severities: {", ".join(severities)}')
        self.stdout.write(f'  • Threshold: {threshold} event(s)')
        self.stdout.write('')

        # Get unresolved events
        events = SecurityAuditLog.objects.filter(
            timestamp__gte=since_time,
            severity__in=severities,
            resolved=False
        ).order_by('-timestamp')

        event_count = events.count()

        self.stdout.write(f'Found {event_count} unresolved event(s)')

        if event_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No events to alert on. All clear!'))
            return

        if event_count < threshold:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Event count ({event_count}) below threshold ({threshold}). No alert sent.'
                )
            )
            return

        # Check rate limit (don't spam admins)
        if not force:
            last_alert_time = self._get_last_alert_time()
            if last_alert_time:
                time_since_last = timezone.now() - last_alert_time
                if time_since_last < timedelta(hours=1):
                    self.stdout.write(
                        self.style.WARNING(
                            f'⏳ Alert sent {time_since_last.seconds // 60} minutes ago. '
                            f'Waiting 1 hour between alerts.'
                        )
                    )
                    self.stdout.write(
                        self.style.WARNING('Use --force to override rate limit.')
                    )
                    return

        # Group events by severity
        events_by_severity = {}
        for severity_code, severity_label in SecurityAuditLog.SEVERITY_CHOICES:
            if severity_code in severities:
                count = events.filter(severity=severity_code).count()
                if count > 0:
                    events_by_severity[severity_label] = count

        # Display summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Events breakdown:'))
        for severity, count in events_by_severity.items():
            self.stdout.write(f'  • {severity}: {count}')
        self.stdout.write('')

        # Get top events for email
        top_events = events[:10]  # Include up to 10 most recent

        # Prepare email
        subject = f'[Security Alert] {event_count} Unresolved Security Event(s)'
        message = self._format_email_text(
            event_count,
            events_by_severity,
            top_events,
            since_time
        )

        # Get admin emails
        admin_emails = [email for name, email in settings.ADMINS]

        if not admin_emails:
            self.stdout.write(
                self.style.ERROR(
                    '✗ No admin emails configured in settings.ADMINS'
                )
            )
            self.stdout.write('Add admin emails to settings.py:')
            self.stdout.write("  ADMINS = [('Admin Name', 'admin@example.com')]")
            return

        # Dry run
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - Email would be sent to:'))
            for email in admin_emails:
                self.stdout.write(f'  • {email}')
            self.stdout.write('')
            self.stdout.write('Subject:')
            self.stdout.write(f'  {subject}')
            self.stdout.write('')
            self.stdout.write('Message:')
            self.stdout.write('-' * 70)
            self.stdout.write(message)
            self.stdout.write('-' * 70)
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Dry run complete. No emails sent.'))
            return

        # Send email
        try:
            self.stdout.write('Sending alert email...', ending='')
            mail_admins(
                subject=subject,
                message=message,
                fail_silently=False
            )
            self.stdout.write(self.style.SUCCESS(' ✓'))
            self._set_last_alert_time()

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS(f'✓ Alert sent successfully!'))
            self.stdout.write(self.style.SUCCESS(f'✓ Recipients: {len(admin_emails)}'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write('')

        except Exception as e:
            self.stdout.write(self.style.ERROR(' ✗'))
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))
            self.stdout.write('')
            self.stdout.write('Check your email configuration in settings.py:')
            self.stdout.write('  EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, etc.')

    def _parse_time_delta(self, time_str):
        """Parse time delta string like '1 hour', '30 minutes', '2 days'."""
        pattern = r'(\d+)\s*(minute|hour|day|week)s?'
        match = re.match(pattern, time_str.lower())
        if not match:
            raise ValueError(
                'Format must be like "1 hour", "30 minutes", "2 days"'
            )

        value = int(match.group(1))
        unit = match.group(2)

        if unit == 'minute':
            return timedelta(minutes=value)
        elif unit == 'hour':
            return timedelta(hours=value)
        elif unit == 'day':
            return timedelta(days=value)
        elif unit == 'week':
            return timedelta(weeks=value)

    def _format_email_text(self, total_count, events_by_severity, top_events, since_time):
        """Format plain text email message."""
        lines = []
        lines.append('SECURITY ALERT')
        lines.append('=' * 70)
        lines.append('')
        lines.append(f'Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append(f'Period: Since {since_time.strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append(f'Total Unresolved Events: {total_count}')
        lines.append('')
        lines.append('BREAKDOWN BY SEVERITY:')
        lines.append('-' * 70)
        for severity, count in events_by_severity.items():
            lines.append(f'  {severity}: {count}')
        lines.append('')
        lines.append('RECENT EVENTS:')
        lines.append('-' * 70)
        for i, event in enumerate(top_events, 1):
            lines.append(f'{i}. [{event.get_severity_display().upper()}] {event.event_type}')
            lines.append(f'   Time: {event.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
            lines.append(f'   User: {event.username or "Anonymous"}')
            lines.append(f'   IP: {event.ip_address or "N/A"}')
            lines.append(f'   Message: {event.message[:100]}')
            lines.append('')
        lines.append('=' * 70)
        lines.append('')
        lines.append('Please review these events in the audit dashboard:')
        lines.append(f'{settings.SITE_URL}/referensi/audit/' if hasattr(settings, 'SITE_URL') else '[Your site URL]/referensi/audit/')
        lines.append('')
        lines.append('This is an automated message from the Security Audit System.')

        return '\n'.join(lines)

    def _get_last_alert_time(self):
        """Get timestamp of last alert sent (from cache or file)."""
        try:
            from django.core.cache import cache
            return cache.get('audit_alert_last_sent')
        except:
            return None

    def _set_last_alert_time(self):
        """Record timestamp of alert sent."""
        try:
            from django.core.cache import cache
            cache.set('audit_alert_last_sent', timezone.now(), timeout=3600)  # 1 hour
        except:
            pass
