"""
Signals for auto-starting trial when user email is confirmed.
"""
from django.dispatch import receiver
from allauth.account.signals import email_confirmed


@receiver(email_confirmed)
def start_trial_on_email_confirmation(request, email_address, **kwargs):
    """
    When a user confirms their email, start their 14-day trial period.
    
    This signal is triggered by django-allauth after successful email verification.
    """
    user = email_address.user
    
    # Only start trial if user doesn't already have an active subscription
    if not user.is_subscription_active:
        user.start_trial(days=14)
