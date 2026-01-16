"""
Celery configuration for AHSP project.

PHASE 5: Celery Async Tasks

This module configures Celery for:
- Async import tasks
- Periodic cleanup tasks
- Email notifications
- Background processing
"""

from __future__ import annotations

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module for celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

# Create Celery app
app = Celery('ahsp')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Daily audit log cleanup at 3 AM
    'cleanup-audit-logs-daily': {
        'task': 'referensi.tasks.cleanup_audit_logs_task',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 90, 'keep_critical_days': 180},
    },

    # Generate audit summary every hour
    'generate-audit-summary-hourly': {
        'task': 'referensi.tasks.generate_audit_summary_task',
        'schedule': crontab(minute=0),  # Every hour at :00
        'kwargs': {'period': 'hourly'},
    },

    # Send audit alerts every hour
    'send-audit-alerts-hourly': {
        'task': 'referensi.tasks.send_audit_alerts_task',
        'schedule': crontab(minute=15),  # Every hour at :15
    },

    # Cache warmup every 6 hours
    'cache-warmup-periodic': {
        'task': 'referensi.tasks.cache_warmup_task',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },

    # Cleanup old cache keys daily at 2 AM
    'cleanup-stale-cache-daily': {
        'task': 'referensi.tasks.cleanup_stale_cache_task',
        'schedule': crontab(hour=2, minute=0),
    },

    # ========== SUBSCRIPTION TASKS ==========
    
    # Check and expire subscriptions daily at midnight
    'check-subscription-expiry-daily': {
        'task': 'accounts.check_subscription_expiry',
        'schedule': crontab(hour=0, minute=5),  # 00:05 daily
    },

    # Send expiry reminders daily at 9 AM
    'send-expiry-reminder-daily': {
        'task': 'accounts.send_expiry_reminder',
        'schedule': crontab(hour=9, minute=0),  # 09:00 daily
    },
}

# Configure timezone
app.conf.timezone = 'Asia/Jakarta'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')
