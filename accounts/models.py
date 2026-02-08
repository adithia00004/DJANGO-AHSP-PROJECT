from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class CustomUser(AbstractUser):
    """
    Extended User model with subscription management.
    
    Subscription States:
    - TRIAL: 14-day trial period after email verification
    - PRO: Paid subscription active
    - EXPIRED: Trial or subscription has ended
    """
    
    class SubscriptionStatus(models.TextChoices):
        TRIAL = 'TRIAL', 'Trial'
        PRO = 'PRO', 'Pro'
        EXPIRED = 'EXPIRED', 'Expired'
    
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
        help_text="Current subscription status"
    )
    trial_end_date = models.DateTimeField(
        null=True, blank=True,
        help_text="When the trial period ends"
    )
    subscription_end_date = models.DateTimeField(
        null=True, blank=True,
        help_text="When the paid subscription ends"
    )
    
    # =========================================================================
    # Helper Properties
    # =========================================================================
    
    @property
    def has_full_access(self) -> bool:
        """
        Admin/Staff keypass - always has access to ALL features.
        Superusers and staff members bypass all subscription checks.
        """
        return self.is_superuser or self.is_staff
    
    @property
    def is_trial_active(self) -> bool:
        """Check if user is in active trial period."""
        if self.subscription_status != self.SubscriptionStatus.TRIAL:
            return False
        if not self.trial_end_date:
            return False
        return timezone.now() < self.trial_end_date
    
    @property
    def is_pro_active(self) -> bool:
        """Check if user has active paid subscription."""
        # Admin bypass - always considered PRO
        if self.has_full_access:
            return True
        if self.subscription_status != self.SubscriptionStatus.PRO:
            return False
        if not self.subscription_end_date:
            return False
        return timezone.now() < self.subscription_end_date
    
    @property
    def is_subscription_active(self) -> bool:
        """Check if user has any active subscription (trial, pro, or admin)."""
        # Admin bypass
        if self.has_full_access:
            return True
        return self.is_trial_active or self.is_pro_active
    
    @property
    def can_edit(self) -> bool:
        """Check if user can edit/input data (Admin, Trial, or Pro)."""
        from subscriptions.entitlements import FEATURE_WRITE_ACCESS, has_feature_access

        return has_feature_access(self, FEATURE_WRITE_ACCESS)
    
    @property
    def can_export_clean(self) -> bool:
        """Check if user can export without watermark (Admin or Pro only)."""
        from subscriptions.entitlements import FEATURE_EXPORT_CLEAN, has_feature_access

        return has_feature_access(self, FEATURE_EXPORT_CLEAN)
    
    @property
    def days_until_expiry(self) -> int:
        """Get days remaining until subscription/trial expires."""
        now = timezone.now()
        if self.is_pro_active and self.subscription_end_date:
            delta = self.subscription_end_date - now
            return max(0, delta.days)
        elif self.is_trial_active and self.trial_end_date:
            delta = self.trial_end_date - now
            return max(0, delta.days)
        return 0
    
    # =========================================================================
    # Methods
    # =========================================================================
    
    def start_trial(self, days: int = 14) -> None:
        """Start a trial period for this user."""
        self.subscription_status = self.SubscriptionStatus.TRIAL
        self.trial_end_date = timezone.now() + timedelta(days=days)
        self.save(update_fields=['subscription_status', 'trial_end_date'])
    
    def activate_subscription(self, months: int) -> None:
        """Activate or extend paid subscription."""
        now = timezone.now()
        
        # If already pro and not expired, extend from current end date
        if self.is_pro_active and self.subscription_end_date:
            base_date = self.subscription_end_date
        else:
            base_date = now
        
        # Calculate new end date (approximate months as 30 days)
        self.subscription_end_date = base_date + timedelta(days=months * 30)
        self.subscription_status = self.SubscriptionStatus.PRO
        self.save(update_fields=['subscription_status', 'subscription_end_date'])
    
    def check_and_expire(self) -> bool:
        """
        Check if subscription should be expired and update status.
        Returns True if status was changed to EXPIRED.
        """
        now = timezone.now()
        should_expire = False
        
        if self.subscription_status == self.SubscriptionStatus.TRIAL:
            if self.trial_end_date and now >= self.trial_end_date:
                should_expire = True
        elif self.subscription_status == self.SubscriptionStatus.PRO:
            if self.subscription_end_date and now >= self.subscription_end_date:
                should_expire = True
        
        if should_expire:
            self.subscription_status = self.SubscriptionStatus.EXPIRED
            self.save(update_fields=['subscription_status'])
            return True
        return False
    
    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
