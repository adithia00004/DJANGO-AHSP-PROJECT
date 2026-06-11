from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from subscriptions.models import SubscriptionPlan, SubscriptionPlanPromotion
from pages.views import LandingPageView, PricingPageView


class PricingPageIntegrationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        SubscriptionPlanPromotion.objects.all().delete()
        SubscriptionPlan.objects.all().delete()

        self.plan, _ = SubscriptionPlan.objects.update_or_create(
            base_tier=SubscriptionPlan.BASE_TIER_2,
            defaults={
                "name": "Pro 6 Bulan",
                "duration_months": 6,
                "price": Decimal("1500000"),
                "is_active": True,
            },
        )
        now = timezone.now()
        SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Public Promo",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_PERCENT,
            discount_value=Decimal("20"),
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=1),
            is_active=True,
            priority=1,
        )

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="pricing-user",
            email="pricing-user@example.com",
            password="Secret123!",
        )

    def test_landing_and_pricing_page_use_same_discount_badge(self):
        mocked_plans = [
            {
                "id": self.plan.id,
                "name": self.plan.name,
                "duration": "6 Bulan",
                "duration_months": 6,
                "price_display": "Rp 1.200.000",
                "per_month": "Rp 200.000/bulan",
                "features": ["Akses Penuh Semua Fitur"],
                "popular": True,
                "discount": "Hemat 20%",
            }
        ]

        with patch("pages.views.get_active_pricing_plans", return_value=mocked_plans):
            landing_response = self.client.get(reverse("pages:landing"))
            pricing_response = self.client.get(reverse("pages:pricing"))

        self.assertContains(landing_response, "Hemat 20%")
        self.assertContains(pricing_response, "Hemat 20%")

    def test_landing_shows_active_promo_price_from_database(self):
        request = self.factory.get(reverse("pages:landing"))
        request.user = AnonymousUser()
        landing_response = LandingPageView.as_view()(request)
        landing_response.render()

        self.assertEqual(landing_response.status_code, 200)
        self.assertContains(landing_response, "Hemat 20%")
        self.assertContains(landing_response, "Rp 1.200.000")

    def test_authenticated_user_cta_goes_to_checkout(self):
        request = self.factory.get(reverse("pages:pricing"))
        request.user = self.user

        response = PricingPageView.as_view()(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            reverse("subscriptions:checkout", args=[self.plan.id]),
            response.content.decode(),
        )

    def test_landing_hides_upcoming_promo_on_public_cards(self):
        now = timezone.now()
        plan_1, _ = SubscriptionPlan.objects.update_or_create(
            base_tier=SubscriptionPlan.BASE_TIER_1,
            defaults={
                "name": "Pro 3 Bulan",
                "duration_months": 3,
                "price": Decimal("900000"),
                "is_active": True,
            },
        )
        plan_3, _ = SubscriptionPlan.objects.update_or_create(
            base_tier=SubscriptionPlan.BASE_TIER_3,
            defaults={
                "name": "Pro 12 Bulan",
                "duration_months": 12,
                "price": Decimal("2500000"),
                "is_active": True,
            },
        )
        SubscriptionPlanPromotion.objects.update_or_create(
            plan=plan_1,
            name="Promo Tier 1",
            defaults={
                "discount_type": SubscriptionPlanPromotion.DISCOUNT_PERCENT,
                "discount_value": Decimal("10"),
                "start_at": now + timedelta(hours=1),
                "end_at": now + timedelta(days=2),
                "is_active": True,
                "priority": 3,
            },
        )
        SubscriptionPlanPromotion.objects.update_or_create(
            plan=plan_3,
            name="Promo Tier 3",
            defaults={
                "discount_type": SubscriptionPlanPromotion.DISCOUNT_FIXED,
                "discount_value": Decimal("250000"),
                "start_at": now + timedelta(hours=2),
                "end_at": now + timedelta(days=3),
                "is_active": True,
                "priority": 2,
            },
        )

        request = self.factory.get(reverse("pages:landing"))
        request.user = AnonymousUser()
        response = LandingPageView.as_view()(request)
        response.render()
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Promo Aktif", html)
        self.assertNotIn("Promo Akan Datang", html)
        self.assertGreaterEqual(html.count("promo-panel promo-"), 3)
        self.assertIn("Berakhir", html)


class LandingPageRedirectTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.regular_user = user_model.objects.create_user(
            username="landing-regular",
            email="landing-regular@example.com",
            password="Secret123!",
        )
        self.superuser = user_model.objects.create_superuser(
            username="landing-admin",
            email="landing-admin@example.com",
            password="Secret123!",
        )

    def test_anonymous_user_can_access_landing_page(self):
        request = self.factory.get(reverse("pages:landing"))
        request.user = AnonymousUser()
        response = LandingPageView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_authenticated_regular_user_redirected_to_dashboard(self):
        request = self.factory.get(reverse("pages:landing"))
        request.user = self.regular_user
        response = LandingPageView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:dashboard"))

    def test_authenticated_superuser_redirected_to_referensi_admin_portal(self):
        request = self.factory.get(reverse("pages:landing"))
        request.user = self.superuser
        response = LandingPageView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("referensi:admin_portal"))
