"""
Payment and subscription models.
"""
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """
    Available subscription plans with pricing.
    """
    DURATION_3_MONTHS = 3
    DURATION_6_MONTHS = 6
    DURATION_12_MONTHS = 12
    
    BASE_TIER_1 = 1
    BASE_TIER_2 = 2
    BASE_TIER_3 = 3
    BASE_TIER_CHOICES = [
        (BASE_TIER_1, "Harga Dasar 1"),
        (BASE_TIER_2, "Harga Dasar 2"),
        (BASE_TIER_3, "Harga Dasar 3"),
    ]

    base_tier = models.PositiveSmallIntegerField(
        choices=BASE_TIER_CHOICES,
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=100)
    duration_months = models.PositiveIntegerField(default=DURATION_3_MONTHS)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['base_tier', 'duration_months']
        constraints = [
            models.UniqueConstraint(
                fields=["base_tier"],
                condition=models.Q(base_tier__isnull=False),
                name="uniq_subscriptionplan_base_tier",
            )
        ]
    
    def __str__(self):
        tier_label = self.get_base_tier_display() if self.base_tier else "Custom"
        return f"{tier_label} | {self.name} - Rp {self.price:,.0f}"


class SubscriptionPlanPromotion(models.Model):
    """
    Time-based promotion for a subscription plan.
    """

    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENT, "Percent"),
        (DISCOUNT_FIXED, "Fixed"),
    ]

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="promotions",
    )
    name = models.CharField(max_length=120)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "-start_at", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["plan", "is_active"]),
            models.Index(fields=["start_at", "end_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_at__gt=models.F("start_at")),
                name="promo_end_after_start",
            ),
            models.CheckConstraint(
                check=models.Q(discount_value__gt=0),
                name="promo_discount_value_positive",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(discount_type="fixed")
                    | models.Q(discount_value__lte=Decimal("100"))
                ),
                name="promo_percent_lte_100",
            ),
        ]

    def clean(self):
        errors = {}

        if self.start_at and timezone.is_naive(self.start_at):
            errors["start_at"] = "Start time must be timezone-aware."

        if self.end_at and timezone.is_naive(self.end_at):
            errors["end_at"] = "End time must be timezone-aware."

        if self.start_at and self.end_at and self.end_at <= self.start_at:
            errors["end_at"] = "End time must be greater than start time."

        if self.discount_value is not None and self.discount_value <= 0:
            errors["discount_value"] = "Discount value must be greater than 0."

        if (
            self.discount_type == self.DISCOUNT_PERCENT
            and self.discount_value is not None
            and self.discount_value > Decimal("100")
        ):
            errors["discount_value"] = "Percent discount cannot exceed 100."

        if (
            self.discount_type == self.DISCOUNT_FIXED
            and self.discount_value is not None
            and self.plan_id
            and self.discount_value > self.plan.price
        ):
            errors["discount_value"] = "Fixed discount cannot exceed plan base price."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.plan.name} - {self.name}"


class SubscriptionFeature(models.Model):
    """
    Feature catalog for entitlement policy checks.
    """

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class PlanFeatureEntitlement(models.Model):
    """
    Data-driven entitlement matrix by subscription status and optional plan override.

    - If plan is NULL: acts as status-level default matrix.
    - If plan is set: acts as plan-specific override.
    """

    ACCESS_DENY = "deny"
    ACCESS_ALLOW = "allow"
    ACCESS_WATERMARK = "watermark"
    ACCESS_CHOICES = [
        (ACCESS_DENY, "Deny"),
        (ACCESS_ALLOW, "Allow"),
        (ACCESS_WATERMARK, "Allow with Watermark"),
    ]

    STATUS_TRIAL = "TRIAL"
    STATUS_PRO = "PRO"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_PRO, "Pro"),
        (STATUS_EXPIRED, "Expired"),
    ]

    feature = models.ForeignKey(
        SubscriptionFeature,
        on_delete=models.CASCADE,
        related_name="entitlements",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feature_entitlements",
    )
    subscription_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_CHOICES,
        default=ACCESS_DENY,
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["feature__code", "subscription_status", "plan__duration_months"]
        constraints = [
            models.UniqueConstraint(
                fields=["feature", "plan", "subscription_status"],
                name="uniq_entitlement_feature_plan_status",
            )
        ]

    def __str__(self):
        plan_label = self.plan.name if self.plan else "DEFAULT"
        return f"{self.feature.code}:{self.subscription_status}:{plan_label}={self.access_level}"


class PaymentTransaction(models.Model):
    """
    Record of payment transactions via Midtrans.
    """
    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_EXPIRED = 'expired'
    STATUS_REFUND = 'refund'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_REFUND, 'Refund'),
    ]

    PROMOTION_DISCOUNT_TYPE_CHOICES = [
        ("", "-"),
        (SubscriptionPlanPromotion.DISCOUNT_PERCENT, "Percent"),
        (SubscriptionPlanPromotion.DISCOUNT_FIXED, "Fixed"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=100, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    duration_months_snapshot = models.PositiveIntegerField(default=0)
    base_amount_snapshot = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    discount_amount_snapshot = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    promotion_id_snapshot = models.BigIntegerField(null=True, blank=True)
    promotion_name_snapshot = models.CharField(max_length=120, blank=True)
    promotion_discount_type_snapshot = models.CharField(
        max_length=20,
        choices=PROMOTION_DISCOUNT_TYPE_CHOICES,
        blank=True,
    )
    promotion_discount_value_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    payment_type = models.CharField(max_length=50, blank=True)  # bank_transfer, gopay, etc.
    
    # Midtrans data
    snap_token = models.CharField(max_length=255, blank=True)
    midtrans_transaction_id = models.CharField(max_length=100, blank=True)
    midtrans_response = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_id} - {self.user.email} - {self.status}"
    
    def generate_order_id(self) -> str:
        """Generate unique order ID for Midtrans."""
        import time
        timestamp = int(time.time())
        return f"AHSP-{self.user.id}-{timestamp}"
