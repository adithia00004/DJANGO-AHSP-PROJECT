"""
Tests for Account Signals (Integration)
"""

import pytest
from unittest.mock import Mock
from accounts.models import CustomUser
from accounts.signals import start_trial_on_email_confirmation

@pytest.mark.django_db
def test_signal_starts_trial_on_email_confirm():
    """Verify trial starts when email is confirmed."""
    # Create user without subscription
    user = CustomUser.objects.create_user('signal_test', 'test@example.com', 'pass')
    assert user.subscription_status == 'TRIAL' # Default is created as TRIAL but inactive if dates not set?
    # Wait, CustomUser default is TRIAL? checking models...
    # But start_trial sets dates.
    
    # Let's ensure strict start state
    user.subscription_status = 'TRIAL'
    user.trial_end_date = None
    user.save()
    
    assert user.is_trial_active is False
    
    # Mock EmailAddress object from allauth
    email_address = Mock()
    email_address.user = user
    request = Mock()
    
    # Trigger signal manually (simulate allauth)
    start_trial_on_email_confirmation(request, email_address)
    
    # Refresh user
    user.refresh_from_db()
    
    # Assertions
    assert user.is_trial_active is True
    assert user.days_until_expiry >= 13

@pytest.mark.django_db
def test_signal_does_not_override_pro():
    """Verify signal doesn't downgrade PRO user to TRIAL."""
    user = CustomUser.objects.create_user('pro_signal', 'pro@example.com', 'pass')
    user.activate_subscription(months=1)
    
    original_end_date = user.subscription_end_date
    assert user.subscription_status == 'PRO'
    
    # Mock
    email_address = Mock()
    email_address.user = user
    request = Mock()
    
    # Trigger signal
    start_trial_on_email_confirmation(request, email_address)
    
    user.refresh_from_db()
    
    # Should still be PRO and dates unchanged
    assert user.subscription_status == 'PRO'
    assert user.subscription_end_date == original_end_date
