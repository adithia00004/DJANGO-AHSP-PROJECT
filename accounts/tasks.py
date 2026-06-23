"""
Celery tasks for subscription management.
Scheduled daily to check and expire subscriptions.
"""
try:
    from celery import shared_task
except ImportError:  # pragma: no cover - exercised only when celery is absent
    def shared_task(*decorator_args, **decorator_kwargs):
        def decorator(func):
            return func

        return decorator
from django.conf import settings
from django.core.mail import send_mail
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
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
    support_email = getattr(settings, 'SUPPORT_EMAIL', from_email)
    pricing_url = f"{getattr(settings, 'SITE_URL', '').rstrip('/')}/pricing/"

    reminders = (
        [(user, user.trial_end_date, 'trial') for user in expiring_trials]
        + [(user, user.subscription_end_date, 'pro') for user in expiring_subs]
    )

    sent = 0
    for user, end_date, kind in reminders:
        if not user.email:
            continue

        days_left = max(0, (end_date - now).days)
        label = "Masa trial" if kind == 'trial' else "Langganan Pro"
        subject = "Langganan Dashboard-RAB Anda akan segera berakhir"
        message = (
            f"Halo {user.get_full_name() or user.username},\n\n"
            f"{label} Anda akan berakhir dalam {days_left} hari.\n\n"
            f"Perpanjang sekarang agar akses Anda tidak terputus:\n{pricing_url}\n\n"
            f"Butuh bantuan? Hubungi kami di {support_email}.\n\n"
            f"Terima kasih,\nTim Dashboard-RAB"
        )

        try:
            send_mail(subject, message, from_email, [user.email], fail_silently=False)
            sent += 1
        except Exception:
            logger.exception("Failed to send expiry reminder to %s", user.email)

    total_reminders = len(reminders)
    if total_reminders > 0:
        logger.info(
            "Expiry reminders: %s due, %s emails sent",
            total_reminders,
            sent,
        )

    return {
        'trials_expiring': expiring_trials.count(),
        'subscriptions_expiring': expiring_subs.count(),
        'sent': sent,
        'total': total_reminders,
    }
