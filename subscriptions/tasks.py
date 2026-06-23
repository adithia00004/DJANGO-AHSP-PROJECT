"""
Celery tasks for the subscriptions domain.

Beat must not schedule a management command directly; it schedules this task,
which is a thin wrapper around the reconciliation service.
"""
import logging

try:
    from celery import shared_task
except ImportError:  # pragma: no cover - exercised only when celery is absent
    def shared_task(*decorator_args, **decorator_kwargs):
        def decorator(func):
            return func

        return decorator

from .reconciliation import DEFAULT_PENDING_AGE_MINUTES, reconcile_pending_payments


logger = logging.getLogger(__name__)


@shared_task(name="subscriptions.reconcile_pending_payments")
def reconcile_pending_payments_task(
    older_than_minutes: int = DEFAULT_PENDING_AGE_MINUTES,
    limit=None,
):
    """Beat-scheduled wrapper that recovers paid-but-pending transactions."""
    summary = reconcile_pending_payments(
        older_than_minutes=older_than_minutes,
        limit=limit,
    )
    logger.info("reconcile_pending_payments_task: %s", summary)
    return summary
