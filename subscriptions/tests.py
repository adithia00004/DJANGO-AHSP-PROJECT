import json
from unittest.mock import patch
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.mixins import api_export_excel_word_required, api_pdf_export_allowed
from subscriptions.models import (
    PaymentTransaction,
    SubscriptionPlan,
    SubscriptionPlanPromotion,
)
from subscriptions.entitlements import (
    FEATURE_EXPORT_EXCEL_WORD,
    FEATURE_EXPORT_PDF,
    FEATURE_WRITE_ACCESS,
    get_feature_access,
)
from subscriptions.models import PlanFeatureEntitlement, SubscriptionFeature
from subscriptions.pricing_service import resolve_effective_plan_pricing
from subscriptions.views import CheckoutView, CreatePaymentView, PaymentWebhookView


class SubscriptionRolePolicyTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()

        self.staff_user = user_model.objects.create_user(
            username="staff_user",
            email="staff@example.com",
            password="Secret123!",
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username="regular_user",
            email="regular@example.com",
            password="Secret123!",
        )

        self.plan = SubscriptionPlan.objects.create(
            name="Pro 3 Bulan",
            duration_months=3,
            price=300000,
            is_active=True,
        )

    @patch("subscriptions.views.messages.info")
    def test_checkout_blocks_staff_user(self, _mock_message):
        request = self.factory.get(reverse("subscriptions:checkout", args=[self.plan.id]))
        request.user = self.staff_user

        response = CheckoutView.as_view()(request, plan_id=self.plan.id)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:dashboard"))

    def test_create_payment_blocks_staff_user(self):
        request = self.factory.post(
            reverse("subscriptions:create_payment"),
            data=json.dumps({"plan_id": self.plan.id}),
            content_type="application/json",
        )
        request.user = self.staff_user

        response = CreatePaymentView.as_view()(request)
        payload = json.loads(response.content)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload.get("code"), "ADMIN_CHECKOUT_BLOCKED")

    def test_checkout_allows_regular_user(self):
        request = self.factory.get(reverse("subscriptions:checkout", args=[self.plan.id]))
        request.user = self.regular_user

        response = CheckoutView.as_view()(request, plan_id=self.plan.id)

        self.assertEqual(response.status_code, 200)


class PaymentWebhookIdempotencyTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="payment_user",
            email="payment@example.com",
            password="Secret123!",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Pro 3 Bulan",
            duration_months=3,
            price=300000,
            is_active=True,
        )
        self.payment = PaymentTransaction.objects.create(
            order_id="AHSP-1-TEST-ORDER",
            user=self.user,
            plan=self.plan,
            amount=self.plan.price,
            duration_months_snapshot=self.plan.duration_months,
            status=PaymentTransaction.STATUS_PENDING,
        )
        self.payload = {
            "order_id": self.payment.order_id,
            "transaction_status": "settlement",
            "fraud_status": "accept",
            "status_code": "200",
            "gross_amount": str(int(self.plan.price)),
            "signature_key": "dummy",
            "transaction_id": "midtrans-tx-001",
            "payment_type": "bank_transfer",
        }

    @patch("subscriptions.views.midtrans_client.verify_signature", return_value=True)
    def test_duplicate_success_callback_is_idempotent(self, _mock_verify):
        view = PaymentWebhookView.as_view()
        webhook_url = reverse("subscriptions:webhook_midtrans")

        request_1 = self.factory.post(
            webhook_url,
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        response_1 = view(request_1)
        self.assertEqual(response_1.status_code, 200)

        self.user.refresh_from_db()
        self.payment.refresh_from_db()
        first_end_date = self.user.subscription_end_date
        first_paid_at = self.payment.paid_at

        request_2 = self.factory.post(
            webhook_url,
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        response_2 = view(request_2)
        self.assertEqual(response_2.status_code, 200)

        self.user.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.payment.status, PaymentTransaction.STATUS_SUCCESS)
        self.assertEqual(self.user.subscription_end_date, first_end_date)
        self.assertEqual(self.payment.paid_at, first_paid_at)

    @patch("subscriptions.views.midtrans_client.verify_signature", return_value=True)
    def test_success_callback_uses_duration_snapshot_for_activation(self, _mock_verify):
        self.payment.duration_months_snapshot = 1
        self.payment.save(update_fields=["duration_months_snapshot"])
        self.plan.duration_months = 12
        self.plan.save(update_fields=["duration_months"])

        request = self.factory.post(
            reverse("subscriptions:webhook_midtrans"),
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        response = PaymentWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        expected_end = timezone.now() + timedelta(days=30)
        self.assertLessEqual(abs((self.user.subscription_end_date - expected_end).days), 1)


class EntitlementPolicyEngineTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.trial_user = user_model.objects.create_user(
            username="trial_policy_user",
            email="trial-policy@example.com",
            password="Secret123!",
            subscription_status="TRIAL",
        )
        self.expired_user = user_model.objects.create_user(
            username="expired_policy_user",
            email="expired-policy@example.com",
            password="Secret123!",
            subscription_status="EXPIRED",
        )
        self.pro_user = user_model.objects.create_user(
            username="pro_policy_user",
            email="pro-policy@example.com",
            password="Secret123!",
            subscription_status="PRO",
            subscription_end_date=timezone.now() + timedelta(days=30),
        )

        self.plan = SubscriptionPlan.objects.create(
            name="Pro Matrix Plan",
            duration_months=3,
            price=300000,
            is_active=True,
        )
        PaymentTransaction.objects.create(
            order_id="AHSP-PLAN-OVERRIDE-1",
            user=self.pro_user,
            plan=self.plan,
            amount=self.plan.price,
            status=PaymentTransaction.STATUS_SUCCESS,
            paid_at=timezone.now(),
        )

    def test_trial_user_pdf_export_denied_by_matrix(self):
        decision = get_feature_access(self.trial_user, FEATURE_EXPORT_PDF)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "TRIAL_NO_EXPORT")

    def test_expired_user_pdf_export_allowed_with_watermark(self):
        decision = get_feature_access(self.expired_user, FEATURE_EXPORT_PDF)

        self.assertTrue(decision.allowed)
        self.assertTrue(decision.add_watermark)

    def test_expired_user_write_access_denied(self):
        decision = get_feature_access(self.expired_user, FEATURE_WRITE_ACCESS)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SUBSCRIPTION_EXPIRED")

    def test_plan_override_can_deny_pro_feature(self):
        feature, _ = SubscriptionFeature.objects.get_or_create(
            code=FEATURE_EXPORT_EXCEL_WORD,
            defaults={
                "name": "Export Excel/Word",
                "description": "Export Excel/Word access",
                "is_active": True,
            },
        )
        PlanFeatureEntitlement.objects.update_or_create(
            feature=feature,
            plan=self.plan,
            subscription_status="PRO",
            defaults={
                "access_level": PlanFeatureEntitlement.ACCESS_DENY,
                "note": "Test override deny",
            },
        )

        decision = get_feature_access(self.pro_user, FEATURE_EXPORT_EXCEL_WORD)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "PRO_REQUIRED")
        self.assertEqual(decision.source, "plan")


class EntitlementFeatureGatingDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.trial_pending_user = user_model.objects.create_user(
            username="trial_pending_gate",
            email="trial_pending_gate@example.com",
            password="Secret123!",
            subscription_status="TRIAL",
            trial_end_date=None,
        )
        self.trial_active_user = user_model.objects.create_user(
            username="trial_active_gate",
            email="trial_active_gate@example.com",
            password="Secret123!",
            subscription_status="TRIAL",
            trial_end_date=timezone.now() + timedelta(days=5),
        )
        self.expired_user = user_model.objects.create_user(
            username="expired_gate",
            email="expired_gate@example.com",
            password="Secret123!",
            subscription_status="EXPIRED",
        )
        self.pro_user = user_model.objects.create_user(
            username="pro_gate",
            email="pro_gate@example.com",
            password="Secret123!",
            subscription_status="PRO",
            subscription_end_date=timezone.now() + timedelta(days=30),
        )

    @staticmethod
    @api_export_excel_word_required
    def _excel_endpoint(request):
        return JsonResponse({"ok": True})

    @staticmethod
    @api_pdf_export_allowed
    def _pdf_endpoint(request):
        ctx = getattr(request, "pdf_export_context", {})
        return JsonResponse(
            {
                "ok": True,
                "add_watermark": bool(ctx.get("add_watermark")),
            }
        )

    def test_pdf_export_blocks_trial_pending_user(self):
        request = self.factory.get("/api/export/pdf")
        request.user = self.trial_pending_user

        response = self._pdf_endpoint(request)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "TRIAL_NO_EXPORT")

    def test_pdf_export_blocks_trial_active_user(self):
        request = self.factory.get("/api/export/pdf")
        request.user = self.trial_active_user

        response = self._pdf_endpoint(request)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "TRIAL_NO_EXPORT")

    def test_pdf_export_allows_expired_with_watermark(self):
        request = self.factory.get("/api/export/pdf")
        request.user = self.expired_user

        response = self._pdf_endpoint(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload.get("add_watermark"))

    def test_excel_word_export_requires_pro(self):
        trial_request = self.factory.get("/api/export/xlsx")
        trial_request.user = self.trial_active_user
        trial_response = self._excel_endpoint(trial_request)
        self.assertEqual(trial_response.status_code, 403)

        expired_request = self.factory.get("/api/export/xlsx")
        expired_request.user = self.expired_user
        expired_response = self._excel_endpoint(expired_request)
        self.assertEqual(expired_response.status_code, 403)

        pro_request = self.factory.get("/api/export/xlsx")
        pro_request.user = self.pro_user
        pro_response = self._excel_endpoint(pro_request)
        self.assertEqual(pro_response.status_code, 200)


class ScheduledPromotionPricingServiceTests(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Pro Promo Plan",
            duration_months=6,
            price=Decimal("1500000"),
            is_active=True,
        )
        self.now = timezone.now()

    def test_promotion_not_started_is_ignored(self):
        SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Soon Promo",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_PERCENT,
            discount_value=Decimal("20"),
            start_at=self.now + timedelta(days=1),
            end_at=self.now + timedelta(days=2),
            is_active=True,
        )

        pricing = resolve_effective_plan_pricing(self.plan, now=self.now)

        self.assertEqual(pricing.final_price, Decimal("1500000"))
        self.assertIsNone(pricing.promotion)

    def test_active_promotion_is_applied(self):
        promo = SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Live Promo",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_PERCENT,
            discount_value=Decimal("20"),
            start_at=self.now - timedelta(hours=1),
            end_at=self.now + timedelta(hours=1),
            is_active=True,
            priority=5,
        )

        pricing = resolve_effective_plan_pricing(self.plan, now=self.now)

        self.assertEqual(pricing.promotion, promo)
        self.assertEqual(pricing.final_price, Decimal("1200000"))
        self.assertEqual(pricing.discount_amount, Decimal("300000"))

    def test_expired_promotion_is_ignored(self):
        SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Expired Promo",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_FIXED,
            discount_value=Decimal("100000"),
            start_at=self.now - timedelta(days=2),
            end_at=self.now - timedelta(days=1),
            is_active=True,
        )

        pricing = resolve_effective_plan_pricing(self.plan, now=self.now)

        self.assertEqual(pricing.final_price, Decimal("1500000"))
        self.assertIsNone(pricing.promotion)

    def test_overlap_uses_highest_priority_then_newest(self):
        oldest = SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Priority 10 Old",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_FIXED,
            discount_value=Decimal("100000"),
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
            priority=10,
        )
        newest = SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Priority 10 New",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_FIXED,
            discount_value=Decimal("200000"),
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
            priority=10,
        )
        lower_priority = SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Priority 5",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_FIXED,
            discount_value=Decimal("500000"),
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
            priority=5,
        )

        SubscriptionPlanPromotion.objects.filter(pk=oldest.pk).update(
            created_at=self.now - timedelta(minutes=3)
        )
        SubscriptionPlanPromotion.objects.filter(pk=newest.pk).update(
            created_at=self.now - timedelta(minutes=1)
        )
        SubscriptionPlanPromotion.objects.filter(pk=lower_priority.pk).update(
            created_at=self.now
        )

        pricing = resolve_effective_plan_pricing(self.plan, now=self.now)

        self.assertEqual(pricing.promotion.id, newest.id)
        self.assertEqual(pricing.discount_amount, Decimal("200000"))

    def test_promotion_validation_rejects_invalid_ranges(self):
        promo = SubscriptionPlanPromotion(
            plan=self.plan,
            name="Invalid Promo",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_PERCENT,
            discount_value=Decimal("120"),
            start_at=self.now,
            end_at=self.now - timedelta(minutes=1),
            is_active=True,
        )

        with self.assertRaises(ValidationError) as ctx:
            promo.full_clean()
        self.assertIn("end_at", ctx.exception.message_dict)
        self.assertIn("discount_value", ctx.exception.message_dict)

    def test_promotion_validation_requires_timezone_aware_datetime(self):
        promo = SubscriptionPlanPromotion(
            plan=self.plan,
            name="Naive Promo",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_FIXED,
            discount_value=Decimal("1000"),
            start_at=datetime(2026, 2, 16, 10, 0, 0),
            end_at=datetime(2026, 2, 16, 11, 0, 0),
            is_active=True,
        )

        with self.assertRaises(ValidationError) as ctx:
            promo.full_clean()
        self.assertIn("start_at", ctx.exception.message_dict)
        self.assertIn("end_at", ctx.exception.message_dict)


class PaymentPricingIntegrityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="Secret123!",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Pro 12 Bulan",
            duration_months=12,
            price=Decimal("2500000"),
            is_active=True,
        )
        now = timezone.now()
        self.promo = SubscriptionPlanPromotion.objects.create(
            plan=self.plan,
            name="Annual Campaign",
            discount_type=SubscriptionPlanPromotion.DISCOUNT_PERCENT,
            discount_value=Decimal("10"),
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(days=1),
            is_active=True,
            priority=1,
        )

    @patch("subscriptions.views.midtrans_client.create_snap_token")
    def test_create_payment_uses_server_side_effective_pricing(self, mock_snap_token):
        mock_snap_token.return_value = {"token": "snap-token-1", "redirect_url": ""}
        request = self.factory.post(
            reverse("subscriptions:create_payment"),
            data=json.dumps(
                {
                    "plan_id": self.plan.id,
                    "amount": 1,  # must be ignored by server
                }
            ),
            content_type="application/json",
        )
        request.user = self.user
        response = CreatePaymentView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload["success"])

        tx = PaymentTransaction.objects.get(order_id=payload["order_id"])
        self.assertEqual(tx.amount, Decimal("2250000"))
        self.assertEqual(tx.duration_months_snapshot, 12)
        self.assertEqual(tx.base_amount_snapshot, Decimal("2500000"))
        self.assertEqual(tx.discount_amount_snapshot, Decimal("250000"))
        self.assertEqual(tx.promotion_id_snapshot, self.promo.id)
        self.assertEqual(tx.promotion_name_snapshot, "Annual Campaign")
        self.assertEqual(
            tx.promotion_discount_type_snapshot,
            SubscriptionPlanPromotion.DISCOUNT_PERCENT,
        )
        self.assertEqual(tx.promotion_discount_value_snapshot, Decimal("10.00"))
        mock_snap_token.assert_called_once()
        self.assertEqual(mock_snap_token.call_args.kwargs["amount"], 2250000)


class SubscriptionPricingRouteTests(TestCase):
    def test_legacy_pricing_route_redirects_to_primary_pricing_page(self):
        response = self.client.get(reverse("subscriptions:pricing"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("pages:pricing"))


class ExpiredUserRenewalFlowTests(TestCase):
    """
    Regression for launch-audit finding F9 (2026-06-10).

    SubscriptionMiddleware blocks write methods for users without write
    entitlement. /subscriptions/ must be excluded, otherwise an EXPIRED user
    can never POST /subscriptions/payment/create/ to renew their plan.
    Uses the real test client so the middleware chain actually runs
    (RequestFactory-based tests bypass middleware and missed this).
    """

    def setUp(self):
        user_model = get_user_model()
        self.expired_user = user_model.objects.create_user(
            username="expired_buyer",
            email="expired@example.com",
            password="Secret123!",
        )
        self.expired_user.subscription_status = (
            user_model.SubscriptionStatus.EXPIRED
        )
        self.expired_user.save(update_fields=["subscription_status"])

        self.plan = SubscriptionPlan.objects.create(
            name="Pro 1 Bulan",
            duration_months=1,
            price=Decimal("250000"),
            is_active=True,
        )

    @patch("subscriptions.views.midtrans_client.create_snap_token")
    def test_expired_user_can_create_payment_through_middleware(
        self, mock_snap_token
    ):
        mock_snap_token.return_value = {"token": "snap-renewal", "redirect_url": ""}
        self.client.force_login(self.expired_user)

        response = self.client.post(
            reverse("subscriptions:create_payment"),
            data=json.dumps({"plan_id": self.plan.id}),
            content_type="application/json",
        )

        payload = json.loads(response.content)
        # Must NOT be the middleware's SUBSCRIPTION_EXPIRED block.
        self.assertNotEqual(payload.get("code"), "SUBSCRIPTION_EXPIRED")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])

    def test_expired_user_writes_elsewhere_still_blocked(self):
        """The exclusion must not loosen write-gating outside /subscriptions/."""
        self.client.force_login(self.expired_user)

        response = self.client.post(
            "/dashboard/bulk/archive/",
            data=json.dumps({"project_ids": []}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("code"), "SUBSCRIPTION_EXPIRED")
