"""
Management command to reconcile PENDING payments against Midtrans.

Recovers transactions whose webhook was never delivered (audit finding A2).
Safe to run repeatedly — activation is idempotent. Intended for manual/runbook
use; the scheduled path is the Celery task
``subscriptions.reconcile_pending_payments`` (see config/celery.py beat).
"""
from django.core.management.base import BaseCommand

from subscriptions.reconciliation import (
    DEFAULT_PENDING_AGE_MINUTES,
    reconcile_pending_payments,
)


class Command(BaseCommand):
    help = "Reconcile PENDING payments against Midtrans to recover missed webhooks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-minutes",
            type=int,
            default=DEFAULT_PENDING_AGE_MINUTES,
            help="Only reconcile pending transactions older than this many minutes.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of transactions to reconcile in one run.",
        )

    def handle(self, *args, **options):
        summary = reconcile_pending_payments(
            older_than_minutes=options["older_than_minutes"],
            limit=options["limit"],
        )
        self.stdout.write(self.style.SUCCESS(f"Reconcile complete: {summary}"))
