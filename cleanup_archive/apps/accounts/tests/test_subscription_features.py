"""
Comprehensive Test Suite for Subscription Features (Phase 2)

Coverage:
1. CustomUser model subscription methods
2. Subscription status transitions (TRIAL -> PRO -> EXPIRED)
3. Access control decorators (subscription_required, pro_subscription_required)
4. Export restrictions (Excel/Word blocked for non-PRO, PDF watermark for EXPIRED)
5. Access control mixins (SubscriptionRequiredMixin, ProSubscriptionRequiredMixin)
"""

import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from django.views.generic import View
from django.shortcuts import HttpResponse

from accounts.models import CustomUser
from accounts.mixins import (
    subscription_required,
    pro_subscription_required,
    api_subscription_required,
    api_pro_required,
    api_export_excel_word_required,
    get_pdf_export_context,
    api_pdf_export_allowed,
    SubscriptionRequiredMixin,
    ProSubscriptionRequiredMixin
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def rf():
    """Request factory for creating mock requests."""
    return RequestFactory()


@pytest.fixture
def trial_user(db):
    """User with active TRIAL subscription (14 days from now)."""
    user = CustomUser.objects.create_user(
        username='trial_user',
        email='trial@example.com',
        password='testpass123'
    )
    user.subscription_status = CustomUser.SubscriptionStatus.TRIAL
    user.trial_end_date = timezone.now() + timedelta(days=14)
    user.save()
    return user


@pytest.fixture
def expired_trial_user(db):
    """User with EXPIRED trial (trial ended yesterday)."""
    user = CustomUser.objects.create_user(
        username='expired_trial',
        email='expired_trial@example.com',
        password='testpass123'
    )
    user.subscription_status = CustomUser.SubscriptionStatus.TRIAL
    user.trial_end_date = timezone.now() - timedelta(days=1)
    user.save()
    return user


@pytest.fixture
def pro_user(db):
    """User with active PRO subscription."""
    user = CustomUser.objects.create_user(
        username='pro_user',
        email='pro@example.com',
        password='testpass123'
    )
    user.subscription_status = CustomUser.SubscriptionStatus.PRO
    user.subscription_end_date = timezone.now() + timedelta(days=30)
    user.save()
    return user


@pytest.fixture
def expired_pro_user(db):
    """User with EXPIRED PRO subscription."""
    user = CustomUser.objects.create_user(
        username='expired_pro',
        email='expired_pro@example.com',
        password='testpass123'
    )
    user.subscription_status = CustomUser.SubscriptionStatus.EXPIRED
    user.subscription_end_date = timezone.now() - timedelta(days=5)
    user.save()
    return user


# =============================================================================
# MODEL TESTS: CustomUser Subscription Methods
# =============================================================================

class TestCustomUserSubscriptionModel:
    """Tests for CustomUser subscription-related methods."""

    @pytest.mark.django_db
    def test_start_trial_sets_correct_values(self, db):
        """start_trial() should set status to TRIAL and end date correctly."""
        user = CustomUser.objects.create_user(
            username='new_user', email='new@test.com', password='pass'
        )
        user.start_trial(days=14)
        
        assert user.subscription_status == CustomUser.SubscriptionStatus.TRIAL
        assert user.trial_end_date is not None
        # Should be ~14 days from now
        delta = user.trial_end_date - timezone.now()
        assert 13 <= delta.days <= 14

    @pytest.mark.django_db
    def test_activate_subscription_from_trial(self, trial_user):
        """activate_subscription() should upgrade TRIAL to PRO."""
        trial_user.activate_subscription(months=3)
        
        assert trial_user.subscription_status == CustomUser.SubscriptionStatus.PRO
        assert trial_user.subscription_end_date is not None
        # Should be ~90 days from now
        delta = trial_user.subscription_end_date - timezone.now()
        assert 89 <= delta.days <= 91

    @pytest.mark.django_db
    def test_activate_subscription_extends_existing_pro(self, pro_user):
        """activate_subscription() should extend existing PRO subscription."""
        original_end = pro_user.subscription_end_date
        pro_user.activate_subscription(months=1)
        
        # Should extend from original end date, not from now
        expected_new_end = original_end + timedelta(days=30)
        delta = abs((pro_user.subscription_end_date - expected_new_end).total_seconds())
        assert delta < 60  # Within 1 minute tolerance

    @pytest.mark.django_db
    def test_check_and_expire_trial(self, expired_trial_user):
        """check_and_expire() should transition expired TRIAL to EXPIRED."""
        result = expired_trial_user.check_and_expire()
        
        assert result is True
        assert expired_trial_user.subscription_status == CustomUser.SubscriptionStatus.EXPIRED

    @pytest.mark.django_db
    def test_check_and_expire_active_trial_no_change(self, trial_user):
        """check_and_expire() should NOT expire an active TRIAL."""
        result = trial_user.check_and_expire()
        
        assert result is False
        assert trial_user.subscription_status == CustomUser.SubscriptionStatus.TRIAL

    @pytest.mark.django_db
    def test_is_subscription_active_trial(self, trial_user):
        """is_subscription_active should return True for active TRIAL."""
        assert trial_user.is_subscription_active is True
        assert trial_user.is_trial_active is True
        assert trial_user.is_pro_active is False

    @pytest.mark.django_db
    def test_is_subscription_active_pro(self, pro_user):
        """is_subscription_active should return True for active PRO."""
        assert pro_user.is_subscription_active is True
        assert pro_user.is_trial_active is False
        assert pro_user.is_pro_active is True

    @pytest.mark.django_db
    def test_is_subscription_active_expired(self, expired_pro_user):
        """is_subscription_active should return False for EXPIRED."""
        assert expired_pro_user.is_subscription_active is False
        assert expired_pro_user.is_trial_active is False
        assert expired_pro_user.is_pro_active is False

    @pytest.mark.django_db
    def test_days_until_expiry_trial(self, trial_user):
        """days_until_expiry should return correct days for TRIAL."""
        days = trial_user.days_until_expiry
        assert 13 <= days <= 14

    @pytest.mark.django_db
    def test_days_until_expiry_expired(self, expired_pro_user):
        """days_until_expiry should return 0 for EXPIRED users."""
        assert expired_pro_user.days_until_expiry == 0

    @pytest.mark.django_db
    def test_can_edit_trial(self, trial_user):
        """TRIAL users should be able to edit."""
        assert trial_user.can_edit is True

    @pytest.mark.django_db
    def test_can_edit_expired(self, expired_pro_user):
        """EXPIRED users should NOT be able to edit."""
        assert expired_pro_user.can_edit is False

    @pytest.mark.django_db
    def test_can_export_clean_pro_only(self, trial_user, pro_user, expired_pro_user):
        """Only PRO users can export without watermark."""
        assert trial_user.can_export_clean is False
        assert pro_user.can_export_clean is True
        assert expired_pro_user.can_export_clean is False


# =============================================================================
# DECORATOR TESTS: Export Restrictions
# =============================================================================

class TestExportDecorators:
    """Tests for export-specific decorators."""

    @pytest.mark.django_db
    def test_api_export_excel_word_blocks_trial(self, rf, trial_user):
        """TRIAL users should be blocked from Excel/Word exports."""
        @api_export_excel_word_required
        def dummy_view(request):
            return {"success": True}
        
        request = rf.get('/dummy/')
        request.user = trial_user
        
        response = dummy_view(request)
        
        assert response.status_code == 403
        assert b'PRO_REQUIRED' in response.content

    @pytest.mark.django_db
    def test_api_export_excel_word_blocks_expired(self, rf, expired_pro_user):
        """EXPIRED users should be blocked from Excel/Word exports."""
        @api_export_excel_word_required
        def dummy_view(request):
            return {"success": True}
        
        request = rf.get('/dummy/')
        request.user = expired_pro_user
        
        response = dummy_view(request)
        
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_api_export_excel_word_allows_pro(self, rf, pro_user):
        """PRO users should be allowed to use Excel/Word exports."""
        from django.http import JsonResponse
        
        @api_export_excel_word_required
        def dummy_view(request):
            return JsonResponse({"success": True})
        
        request = rf.get('/dummy/')
        request.user = pro_user
        
        response = dummy_view(request)
        
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_get_pdf_export_context_trial_blocked(self, rf, trial_user):
        """TRIAL users should be completely blocked from PDF export."""
        request = rf.get('/dummy/')
        request.user = trial_user
        
        ctx = get_pdf_export_context(request)
        
        assert ctx['blocked'] is True
        assert 'TRIAL_NO_EXPORT' in str(ctx['response'].content)

    @pytest.mark.django_db
    def test_get_pdf_export_context_pro_clean(self, rf, pro_user):
        """PRO users should get clean PDF (no watermark)."""
        request = rf.get('/dummy/')
        request.user = pro_user
        
        ctx = get_pdf_export_context(request)
        
        assert ctx['blocked'] is False
        assert ctx['add_watermark'] is False
        assert ctx['is_pro'] is True

    @pytest.mark.django_db
    def test_get_pdf_export_context_expired_watermarked(self, rf, expired_pro_user):
        """EXPIRED users should get PDF with watermark."""
        request = rf.get('/dummy/')
        request.user = expired_pro_user
        
        ctx = get_pdf_export_context(request)
        
        assert ctx['blocked'] is False
        assert ctx['add_watermark'] is True
        assert ctx['watermark_text'] == 'DEMO - Dashboard-RAB'
        assert ctx['is_pro'] is False


# =============================================================================
# DECORATOR TESTS: General Access Control
# =============================================================================

class TestAccessControlDecorators:
    """Tests for general subscription access control decorators."""

    @pytest.mark.django_db
    def test_api_subscription_required_blocks_expired(self, rf, expired_pro_user):
        """api_subscription_required should block EXPIRED users."""
        from django.http import JsonResponse
        
        @api_subscription_required
        def dummy_view(request):
            return JsonResponse({"success": True})
        
        request = rf.get('/dummy/')
        request.user = expired_pro_user
        
        response = dummy_view(request)
        
        assert response.status_code == 403
        assert b'SUBSCRIPTION_EXPIRED' in response.content

    @pytest.mark.django_db
    def test_api_subscription_required_allows_trial(self, rf, trial_user):
        """api_subscription_required should allow active TRIAL users."""
        from django.http import JsonResponse
        
        @api_subscription_required
        def dummy_view(request):
            return JsonResponse({"success": True})
        
        request = rf.get('/dummy/')
        request.user = trial_user
        
        response = dummy_view(request)
        
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_api_pro_required_blocks_trial(self, rf, trial_user):
        """api_pro_required should block TRIAL users."""
        from django.http import JsonResponse
        
        @api_pro_required
        def dummy_view(request):
            return JsonResponse({"success": True})
        
        request = rf.get('/dummy/')
        request.user = trial_user
        
        response = dummy_view(request)
        
        assert response.status_code == 403
        assert b'PRO_REQUIRED' in response.content

    @pytest.mark.django_db
    def test_api_pro_required_allows_pro(self, rf, pro_user):
        """api_pro_required should allow PRO users."""
        from django.http import JsonResponse
        
        @api_pro_required
        def dummy_view(request):
            return JsonResponse({"success": True})
        
        request = rf.get('/dummy/')
        request.user = pro_user
        
        response = dummy_view(request)
        
        assert response.status_code == 200


# =============================================================================
# MIXIN TESTS: Class-Based Views Access Control
# =============================================================================

class TestSubscriptionMixins:
    """Tests for CBV mixins."""

    class DummyView(SubscriptionRequiredMixin, View):
        def get(self, request):
            return HttpResponse("Access Granted")

    class ProDummyView(ProSubscriptionRequiredMixin, View):
        def get(self, request):
            return HttpResponse("Pro Access Granted")

    @pytest.mark.django_db
    def test_subscription_mixin_blocks_expired(self, rf, expired_pro_user):
        """SubscriptionRequiredMixin should redirect EXPIRED users."""
        request = rf.get('/dummy/')
        request.user = expired_pro_user
        
        # Add messages support
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        SessionMiddleware(lambda x: None).process_request(request)
        MessageMiddleware(lambda x: None).process_request(request)
        
        view = self.DummyView.as_view()
        response = view(request)
        
        # Should redirect to pricing
        assert response.status_code == 302
        assert 'pricing' in response.url

    @pytest.mark.django_db
    def test_subscription_mixin_allows_active(self, rf, trial_user):
        """SubscriptionRequiredMixin should allow active users."""
        request = rf.get('/dummy/')
        request.user = trial_user
        
        view = self.DummyView.as_view()
        response = view(request)
        
        assert response.status_code == 200
        assert b"Access Granted" in response.content

    @pytest.mark.django_db
    def test_pro_mixin_blocks_trial(self, rf, trial_user):
        """ProSubscriptionRequiredMixin should redirect TRIAL users."""
        request = rf.get('/dummy/')
        request.user = trial_user
        
        # Add messages support
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        SessionMiddleware(lambda x: None).process_request(request)
        MessageMiddleware(lambda x: None).process_request(request)
        
        view = self.ProDummyView.as_view()
        response = view(request)
        
        assert response.status_code == 302
        assert 'pricing' in response.url

    @pytest.mark.django_db
    def test_pro_mixin_allows_pro(self, rf, pro_user):
        """ProSubscriptionRequiredMixin should allow PRO users."""
        request = rf.get('/dummy/')
        request.user = pro_user
        
        view = self.ProDummyView.as_view()
        response = view(request)
        
        assert response.status_code == 200
        assert b"Pro Access Granted" in response.content
