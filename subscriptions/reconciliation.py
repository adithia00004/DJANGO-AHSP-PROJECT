"""
Reconciliation for payments whose Midtrans webhook was never delivered.

The webhook is the primary activation path; if it never arrives (gateway
downtime, dropped delivery) a paid transaction would otherwise stay PENDING
forever and the user never becomes PRO despite paying (audit finding A2).

This module re-fetches authoritative status from Midtrans for stale pending
transactions and runs the SAME idempotent activation path the webhook uses
(`mark_paid_and_activate`), so there is exactly one place that grants access.
"""
import logging
from datetime import timedelta

from django.db import transaction as db_transaction
from django.utils import timezone

from .midtrans import midtrans_client
from .models import PaymentTransaction


logger = logging.getLogger(__name__)

DEFAULT_PENDING_AGE_MINUTES = 30


def mark_paid_and_activate(transaction: PaymentTransaction) -> None:
    """Mark a transaction SUCCESS/paid and activate the user's subscription.

    Shared by the webhook and the reconciliation job so there is a single
    activation path. Does NOT persist the transaction — the caller saves it
    (the webhook saves once at the end of its atomic block). Idempotency (the
    ``paid_at`` guard) is the caller's responsibility.
    """
    transaction.status = PaymentTransaction.STATUS_SUCCESS
    transaction.paid_at = timezone.now()

    # Activate using the immutable duration snapshot when available.
    duration_months = transaction.duration_months_snapshot or getattr(
        transaction.plan,
        "duration_months",
        0,
    )
    if duration_months > 0:
        transaction.user.activate_subscription(months=duration_months)
        logger.info(
            "Subscription activated for %s: %s months",
            transaction.user.email,
            duration_months,
        )


def reconcile_pending_payments(
    older_than_minutes: int = DEFAULT_PENDING_AGE_MINUTES,
    limit=None,
) -> dict:
    """Re-fetch Midtrans status for stale PENDING transactions and finalize them.

    Only transactions that actually reached Midtrans (have a snap token) and are
    older than ``older_than_minutes`` are considered, so an in-flight webhook is
    never raced. Settled transactions are activated idempotently under a row
    lock; other statuses are tallied but left untouched.

    Returns a summary dict suitable for logging.
    """
    cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
    queryset = (
        PaymentTransaction.objects.filter(
            status=PaymentTransaction.STATUS_PENDING,
            created_at__lte=cutoff,
        )
        .exclude(snap_token="")
        .order_by("created_at")
    )
    if limit:
        queryset = queryset[:limit]

    summary = {
        "checked": 0,
        "activated": 0,
        "still_pending": 0,
        "not_found": 0,
        "errors": 0,
    }

    for tx in queryset:
        summary["checked"] += 1
        try:
            status_data = midtrans_client.get_transaction_status(tx.order_id)
        except Exception:
            logger.exception("Reconcile: status fetch failed for %s", tx.order_id)
            summary["errors"] += 1
            continue

        if status_data is None:
            summary["not_found"] += 1
            continue

        transaction_status = status_data.get("transaction_status")
        fraud_status = status_data.get("fraud_status", "accept")

        if transaction_status in ("capture", "settlement") and fraud_status == "accept":
            with db_transaction.atomic():
                locked = PaymentTransaction.objects.select_for_update().get(pk=tx.pk)
                if locked.paid_at is not None:
                    # A webhook activated it between our query and the lock.
                    continue
                mark_paid_and_activate(locked)
                locked.midtrans_response = status_data
                locked.save()
            logger.info("Reconcile: activated pending order %s", tx.order_id)
            summary["activated"] += 1
        else:
            summary["still_pending"] += 1

    return summary
