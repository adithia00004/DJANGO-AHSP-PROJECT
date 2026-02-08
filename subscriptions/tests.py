import json
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from subscriptions.models import PaymentTransaction, SubscriptionPlan
from subscriptions.entitlements import (
    FEATURE_EXPORT_EXCEL_WORD,
    FEATURE_EXPORT_PDF,
    FEATURE_WRITE_ACCESS,
    get_feature_access,
)
from subscriptions.models import PlanFeatureEntitlement, SubscriptionFeature
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
