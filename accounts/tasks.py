"""
Celery tasks for subscription management.
Scheduled daily to check and expire subscriptions.
"""
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)


@shared_task(name='accounts.check_subscription_expiry')
def check_subscription_expiry():
    """
    Daily task to check and expire subscriptions.
    Runs at midnight (configured in celery beat schedule).
    
    Transitions:
    - TRIAL users past trial_end_date → EXPIRED
    - PRO users past subscription_end_date → EXPIRED
    """
    User = get_user_model()
    now = timezone.now()
    
    # Expire trials
    expired_trials = User.objects.filter(
        subscription_status='TRIAL',
        trial_end_date__lte=now
    ).update(subscription_status='EXPIRED')
    
    # Expire subscriptions
    expired_subs = User.objects.filter(
        subscription_status='PRO',
        subscription_end_date__lte=now
    ).update(subscription_status='EXPIRED')
    
    total_expired = expired_trials + expired_subs
    
    if total_expired > 0:
        logger.info(f"Subscription expiry check: {expired_trials} trials, {expired_subs} subscriptions expired")
    
    return {
        'expired_trials': expired_trials,
        'expired_subscriptions': expired_subs,
        'total': total_expired
    }


@shared_task(name='accounts.send_expiry_reminder')
def send_expiry_reminder():
    """
    Send reminder emails to users whose subscriptions are expiring soon.
    Runs daily, sends reminders for users expiring in 3 days.
    """
    User = get_user_model()
    now = timezone.now()
    reminder_threshold = now + timezone.timedelta(days=3)
    
    # Find users expiring in 3 days
    expiring_trials = User.objects.filter(
        subscription_status='TRIAL',
        trial_end_date__gt=now,
        trial_end_date__lte=reminder_threshold
    )
    
    expiring_subs = User.objects.filter(
        subscription_status='PRO',
        subscription_end_date__gt=now,
        subscription_end_date__lte=reminder_threshold
    )
    
    # TODO: Implement actual email sending
    # For now, just log
    total_reminders = expiring_trials.count() + expiring_subs.count()
    
    if total_reminders > 0:
        logger.info(f"Expiry reminders: {expiring_trials.count()} trials, {expiring_subs.count()} subscriptions expiring in 3 days")
    
    return {
        'trials_expiring': expiring_trials.count(),
        'subscriptions_expiring': expiring_subs.count(),
        'total': total_reminders
    }
