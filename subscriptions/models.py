"""
Payment and subscription models.
"""
import uuid
from django.db import models
from django.conf import settings


class SubscriptionPlan(models.Model):
    """
    Available subscription plans with pricing.
    """
    DURATION_3_MONTHS = 3
    DURATION_6_MONTHS = 6
    DURATION_12_MONTHS = 12
    
    DURATION_CHOICES = [
        (DURATION_3_MONTHS, '3 Bulan'),
        (DURATION_6_MONTHS, '6 Bulan'),
        (DURATION_12_MONTHS, '12 Bulan'),
    ]
    
    name = models.CharField(max_length=100)
    duration_months = models.IntegerField(choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['duration_months']
    
    def __str__(self):
        return f"{self.name} - Rp {self.price:,.0f}"


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
