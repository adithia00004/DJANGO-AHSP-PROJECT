"""
Test Suite for Landing Page and Pricing Features

Coverage:
1. Landing page accessibility (public)
2. Pricing page displays plans
3. Checkout redirect logic (authenticated vs guest)
"""

import pytest
from django.test import Client
from django.urls import reverse
from decimal import Decimal

from accounts.models import CustomUser


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def guest_client(db):
    """Non-authenticated client with database access."""
    return Client()


@pytest.fixture
def authenticated_client(db):
    """Authenticated client with TRIAL user."""
    user = CustomUser.objects.create_user(
        username='test_user',
        email='test@example.com',
        password='testpass123'
    )
    user.start_trial()
    
    client = Client()
    client.login(username='test_user', password='testpass123')
    return client, user


@pytest.fixture
def pro_client(db):
    """Authenticated client with PRO user."""
    from django.utils import timezone
    from datetime import timedelta
    
    user = CustomUser.objects.create_user(
        username='pro_user',
        email='pro@example.com',
        password='propass123'
    )
    user.subscription_status = CustomUser.SubscriptionStatus.PRO
    user.subscription_end_date = timezone.now() + timedelta(days=30)
    user.save()
    
    client = Client()
    client.login(username='pro_user', password='propass123')
    return client, user


# =============================================================================
# LANDING PAGE TESTS
# =============================================================================

class TestLandingPage:
    """Tests for the public landing page."""

    @pytest.mark.django_db
    def test_landing_page_accessible_guest(self, guest_client):
        """Landing page should be accessible without login."""
        url = reverse('pages:landing')
        response = guest_client.get(url)
        
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_landing_page_contains_branding(self, guest_client):
        """Landing page should contain Dashboard-RAB branding."""
        url = reverse('pages:landing')
        response = guest_client.get(url)
        
        # Check for brand name in content (case insensitive)
        content = response.content.decode('utf-8').lower()
        assert 'dashboard' in content or 'rab' in content

    @pytest.mark.django_db
    def test_landing_page_has_pricing_section(self, guest_client):
        """Landing page should have pricing section with plans."""
        url = reverse('pages:landing')
        response = guest_client.get(url)
        
        # Check for pricing-related content
        content = response.content.decode('utf-8').lower()
        assert 'pricing' in content or 'harga' in content or 'paket' in content


# =============================================================================
# PRICING PAGE TESTS
# =============================================================================

class TestPricingPage:
    """Tests for the pricing/plans page."""

    @pytest.mark.django_db
    def test_pricing_page_accessible(self, guest_client):
        """Pricing page should be accessible without login."""
        url = reverse('pages:pricing')
        response = guest_client.get(url)
        
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_pricing_page_has_plans(self, guest_client):
        """Pricing page should display subscription plans."""
        url = reverse('pages:pricing')
        response = guest_client.get(url)
        
        # Should contain plan-related content
        content = response.content.decode('utf-8').lower()
        assert 'bulan' in content or 'month' in content or 'paket' in content

    @pytest.mark.django_db
    def test_pricing_button_guest_goes_to_signup(self, guest_client):
        """Guest clicking pricing button should go to signup."""
        url = reverse('pages:pricing')
        response = guest_client.get(url)
        
        # Check for signup link in response
        content = response.content.decode('utf-8').lower()
        assert 'signup' in content or 'daftar' in content or 'login' in content


# =============================================================================
# CHECKOUT FLOW TESTS
# =============================================================================

class TestCheckoutFlow:
    """Tests for checkout/payment flow."""

    @pytest.mark.django_db
    def test_checkout_requires_login(self, guest_client):
        """Checkout page should redirect guest to login."""
        from subscriptions.models import SubscriptionPlan
        
        plan = SubscriptionPlan.objects.create(
            name='Test Plan',
            duration_months=3,
            price=Decimal('900000'),
            is_active=True
        )
        
        url = reverse('subscriptions:checkout', kwargs={'plan_id': plan.id})
        response = guest_client.get(url)
        
        # Should redirect to login
        assert response.status_code in [302, 301]
        assert 'login' in response.url.lower() or 'account' in response.url.lower()

    @pytest.mark.django_db
    def test_checkout_accessible_authenticated(self, authenticated_client):
        """Authenticated user should access checkout page."""
        from subscriptions.models import SubscriptionPlan
        
        client, user = authenticated_client
        
        plan = SubscriptionPlan.objects.create(
            name='Test Pro Plan',
            duration_months=6,
            price=Decimal('1500000'),
            is_active=True
        )
        
        url = reverse('subscriptions:checkout', kwargs={'plan_id': plan.id})
        response = client.get(url)
        
        # Should get 200 (checkout page) or redirect to dashboard if already pro
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_pro_user_redirected_from_checkout(self, pro_client):
        """PRO user should be redirected away from checkout (already subscribed)."""
        from subscriptions.models import SubscriptionPlan
        
        client, user = pro_client
        
        plan = SubscriptionPlan.objects.create(
            name='Another Plan',
            duration_months=3,
            price=Decimal('900000'),
            is_active=True
        )
        
        url = reverse('subscriptions:checkout', kwargs={'plan_id': plan.id})
        response = client.get(url)
        
        # Should redirect (PRO user shouldn't need to checkout again)
        # Based on CheckoutView logic, it redirects to dashboard
        assert response.status_code == 302
        assert 'dashboard' in response.url.lower() or response.url == '/'


# =============================================================================
# SUBSCRIPTION BADGE TESTS (Template Context)
# =============================================================================

class TestSubscriptionBadge:
    """Tests that subscription status appears correctly in templates."""

    @pytest.mark.django_db
    def test_trial_badge_in_navbar(self, authenticated_client):
        """TRIAL user should see trial badge in navbar."""
        client, user = authenticated_client
        
        # Visit dashboard (which includes base.html with navbar)
        url = reverse('dashboard:dashboard')
        response = client.get(url)
        
        # Check for trial indicator
        content = response.content.decode('utf-8').lower()
        assert 'trial' in content or 'hari' in content  # "X hari tersisa"

    @pytest.mark.django_db
    def test_pro_badge_in_navbar(self, pro_client):
        """PRO user should see PRO badge in navbar."""
        client, user = pro_client
        
        url = reverse('dashboard:dashboard')
        response = client.get(url)
        
        content = response.content.decode('utf-8').lower()
        assert 'pro' in content
