from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from referensi.permissions import REFERENSI_PORTAL_PERMISSIONS
from referensi.views.admin_portal import admin_portal, pricing_management
from subscriptions.models import SubscriptionPlan, SubscriptionPlanPromotion


class PricingManagementPortalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        user_model = get_user_model()
        self.no_perm_user = user_model.objects.create_user(
            username="no_perm_pricing_user",
            email="no-perm-pricing@example.com",
            password="Secret123!",
        )
        self.portal_user = user_model.objects.create_user(
            username="portal_pricing_user",
            email="portal-pricing@example.com",
            password="Secret123!",
        )

        raw_codenames = [name.split(".")[-1] for name in REFERENSI_PORTAL_PERMISSIONS]
        perms = Permission.objects.filter(codename__in=raw_codenames)
        self.portal_user.user_permissions.add(*perms)

        SubscriptionPlanPromotion.objects.all().delete()
        SubscriptionPlan.objects.all().delete()

        self.plan, _ = SubscriptionPlan.objects.update_or_create(
            base_tier=SubscriptionPlan.BASE_TIER_1,
            defaults={
                "name": "Plan Pricing Test",
                "duration_months": 3,
                "price": 300000,
                "is_active": True,
            },
        )
        self.plan_2, _ = SubscriptionPlan.objects.update_or_create(
            base_tier=SubscriptionPlan.BASE_TIER_2,
            defaults={
                "name": "Plan Pricing Test 2",
                "duration_months": 6,
                "price": 600000,
                "is_active": True,
            },
        )
        self.plan_3, _ = SubscriptionPlan.objects.update_or_create(
            base_tier=SubscriptionPlan.BASE_TIER_3,
            defaults={
                "name": "Plan Pricing Test 3",
                "duration_months": 12,
                "price": 1200000,
                "is_active": True,
            },
        )
        SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Promo Future",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_PERCENT,
            discount_value=10,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=2),
            is_active=True,
            priority=5,
        )

    def test_admin_portal_contains_pricing_management_menu(self):
        request = self.factory.get(reverse("referensi:admin_portal"))
        request.user = self.portal_user

        response = admin_portal(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse("referensi:pricing_management"), response.content.decode())
        self.assertIn("Kelola Pricing & Promo", response.content.decode())

    @patch("referensi.views.admin_portal.messages.warning")
    def test_pricing_management_requires_portal_permission(self, _mock_warning):
        request = self.factory.get(reverse("referensi:pricing_management"))
        request.user = self.no_perm_user

        response = pricing_management(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    @patch("referensi.views.admin_portal.messages.success")
    def test_pricing_management_can_update_plan_price(self, _mock_success):
        plans = [self.plan, self.plan_2, self.plan_3]
        request = self.factory.post(
            reverse("referensi:pricing_management"),
            data={
                "action": "save_plans",
                "plans-TOTAL_FORMS": "3",
                "plans-INITIAL_FORMS": "3",
                "plans-MIN_NUM_FORMS": "0",
                "plans-MAX_NUM_FORMS": "1000",
                "plans-0-id": str(plans[0].id),
                "plans-0-name": plans[0].name,
                "plans-0-duration_months": str(plans[0].duration_months),
                "plans-0-price": "450000",
                "plans-0-is_active": "on",
                "plans-1-id": str(plans[1].id),
                "plans-1-name": plans[1].name,
                "plans-1-duration_months": str(plans[1].duration_months),
                "plans-1-price": str(int(plans[1].price)),
                "plans-1-is_active": "on",
                "plans-2-id": str(plans[2].id),
                "plans-2-name": plans[2].name,
                "plans-2-duration_months": str(plans[2].duration_months),
                "plans-2-price": str(int(plans[2].price)),
                "plans-2-is_active": "on",
            },
        )
        request.user = self.portal_user

        response = pricing_management(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("referensi:pricing_management"))

        self.plan.refresh_from_db()
        self.assertEqual(int(self.plan.price), 450000)

    def test_pricing_management_renders_schedule_table(self):
        request = self.factory.get(reverse("referensi:pricing_management"))
        request.user = self.portal_user

        response = pricing_management(request)
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tabel Jadwal Promo", html)
        self.assertIn("Promo Future", html)
        self.assertIn("Akan Datang", html)
