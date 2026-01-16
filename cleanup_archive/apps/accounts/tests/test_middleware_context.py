"""
Structural Tests for Global Components
1. Context Processors (accounts.context_processors)
2. Middleware (accounts.middleware)
"""

import pytest
from django.test import RequestFactory, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock

from accounts.models import CustomUser
from accounts.context_processors import subscription_context
from accounts.middleware import SubscriptionMiddleware


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def rf():
    return RequestFactory()

@pytest.fixture
def trial_user(db):
    user = CustomUser.objects.create_user('trial_ctx', 't@t.com', 'pass')
    user.start_trial()
    return user

@pytest.fixture
def expired_user(db):
    user = CustomUser.objects.create_user('expired_ctx', 'e@t.com', 'pass')
    user.subscription_status = CustomUser.SubscriptionStatus.EXPIRED
    user.trial_end_date = timezone.now() - timedelta(days=1)
    user.save()
    return user

@pytest.fixture
def active_pro_user(db):
    user = CustomUser.objects.create_user('pro_ctx', 'p@t.com', 'pass')
    user.activate_subscription(months=1)
    return user


# =============================================================================
# CONTEXT PROCESSOR TESTS
# =============================================================================

class TestSubscriptionContextProcessor:
    """Tests for accounts.context_processors.subscription_context"""

    def test_anonymous_user_returns_empty(self, rf):
        request = rf.get('/')
        request.user = Mock(is_authenticated=False)
        ctx = subscription_context(request)
        assert ctx == {}

    @pytest.mark.django_db
    def test_trial_user_context(self, rf, trial_user):
        request = rf.get('/')
        request.user = trial_user
        
        ctx = subscription_context(request)
        
        assert ctx['subscription_status'] == 'TRIAL'
        assert ctx['is_subscription_active'] is True
        assert ctx['is_trial_active'] is True
        assert ctx['can_edit'] is True
        assert ctx['can_export_clean'] is False
        assert 13 <= ctx['days_until_expiry'] <= 14
        assert ctx['show_upgrade_banner'] is True  # Trial shows banner

    @pytest.mark.django_db
    def test_expired_user_context(self, rf, expired_user):
        request = rf.get('/')
        request.user = expired_user
        
        ctx = subscription_context(request)
        
        assert ctx['subscription_status'] == 'EXPIRED'
        assert ctx['is_subscription_active'] is False
        assert ctx['can_edit'] is False
        assert ctx['days_until_expiry'] == 0
        assert ctx['show_upgrade_banner'] is True

    @pytest.mark.django_db
    def test_pro_user_context(self, rf, active_pro_user):
        request = rf.get('/')
        request.user = active_pro_user
        
        ctx = subscription_context(request)
        
        assert ctx['subscription_status'] == 'PRO'
        assert ctx['is_pro_active'] is True
        assert ctx['can_export_clean'] is True
        # Banner shows only if < 7 days
        assert ctx['show_upgrade_banner'] is False


# =============================================================================
# MIDDLEWARE TESTS
# =============================================================================

class TestSubscriptionMiddleware:
    """Tests for accounts.middleware.SubscriptionMiddleware"""

    def setup_middleware(self):
        get_response = Mock(return_value="OK")
        middleware = SubscriptionMiddleware(get_response)
        return middleware, get_response

    @pytest.mark.django_db
    def test_get_request_allowed_expired(self, rf, expired_user):
        """GET requests always allowed (read-only) even if expired."""
        middleware, get_response = self.setup_middleware()
        request = rf.get('/some/protected/path/')
        request.user = expired_user
        
        middleware(request)
        get_response.assert_called_once()  # Passed through

    @pytest.mark.django_db
    def test_post_blocked_expired_api(self, rf, expired_user):
        """API POST blocked for expired user."""
        middleware, get_response = self.setup_middleware()
        request = rf.post(
            '/api/save/', 
            content_type='application/json',
            data={}
        )
        request.user = expired_user
        
        response = middleware(request)
        
        # Should be blocked
        get_response.assert_not_called()
        assert response.status_code == 403
        assert b'SUBSCRIPTION_EXPIRED' in response.content

    @pytest.mark.django_db
    def test_post_allowed_active(self, rf, trial_user):
        """API POST allowed for active user."""
        middleware, get_response = self.setup_middleware()
        request = rf.post('/api/save/')
        request.user = trial_user
        
        middleware(request)
        get_response.assert_called_once()

    @pytest.mark.django_db
    def test_excluded_paths_allowed(self, rf, expired_user):
        """Excluded paths (accounts, admin) allowed even for WRITE operations."""
        middleware, get_response = self.setup_middleware()
        
        # Test /accounts/login/ POST
        request = rf.post('/accounts/login/')
        request.user = expired_user
        
        middleware(request)
        get_response.assert_called_once()
