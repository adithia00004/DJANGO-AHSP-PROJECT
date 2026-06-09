"""
Centralized subscription feature policy engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import (
    PaymentTransaction,
    PlanFeatureEntitlement,
    SubscriptionFeature,
    SubscriptionPlan,
)


FEATURE_WRITE_ACCESS = "write_access"
FEATURE_EXPORT_PDF = "export_pdf"
FEATURE_EXPORT_EXCEL_WORD = "export_excel_word"
FEATURE_EXPORT_CLEAN = "export_clean"
FEATURE_PRO_ONLY = "pro_only"
INTERNAL_STATUS_TRIAL_PENDING = "TRIAL_PENDING"


@dataclass
class FeatureAccessDecision:
    allowed: bool
    code: str
    message: str
    add_watermark: bool = False
    upgrade_url: str = "/pricing/"
    source: str = "fallback"
    access_level: str = PlanFeatureEntitlement.ACCESS_DENY


def _latest_success_plan_for_user(user) -> Optional[SubscriptionPlan]:
    if not getattr(user, "is_authenticated", False):
        return None
    if not getattr(user, "is_pro_active", False):
        return None

    tx = (
        PaymentTransaction.objects.filter(
            user=user,
            status=PaymentTransaction.STATUS_SUCCESS,
            plan__isnull=False,
        )
        .select_related("plan")
        .order_by("-paid_at", "-created_at")
        .first()
    )
    return tx.plan if tx else None


def _deny_decision(feature_code: str, subscription_status: str, source: str, access_level: str) -> FeatureAccessDecision:
    if feature_code == FEATURE_EXPORT_PDF and subscription_status in {"TRIAL", INTERNAL_STATUS_TRIAL_PENDING}:
        return FeatureAccessDecision(
            allowed=False,
            code="TRIAL_NO_EXPORT",
            message="Export PDF tersedia setelah Anda upgrade ke Pro. Trial tidak termasuk fitur export.",
            source=source,
            access_level=access_level,
        )

    if feature_code == FEATURE_WRITE_ACCESS:
        return FeatureAccessDecision(
            allowed=False,
            code="SUBSCRIPTION_EXPIRED",
            message="Langganan Anda telah berakhir. Anda hanya memiliki akses baca.",
            source=source,
            access_level=access_level,
        )

    return FeatureAccessDecision(
        allowed=False,
        code="PRO_REQUIRED",
        message="Fitur ini hanya tersedia untuk pengguna Pro. Silakan upgrade langganan Anda.",
        source=source,
        access_level=access_level,
    )


def _level_to_decision(
    feature_code: str,
    subscription_status: str,
    access_level: str,
    source: str,
) -> FeatureAccessDecision:
    if access_level == PlanFeatureEntitlement.ACCESS_ALLOW:
        return FeatureAccessDecision(
            allowed=True,
            code="ALLOWED",
            message="allowed",
            source=source,
            access_level=access_level,
        )

    if access_level == PlanFeatureEntitlement.ACCESS_WATERMARK:
        return FeatureAccessDecision(
            allowed=True,
            code="ALLOWED_WATERMARK",
            message="allowed with watermark",
            add_watermark=(feature_code == FEATURE_EXPORT_PDF),
            source=source,
            access_level=access_level,
        )

    return _deny_decision(feature_code, subscription_status, source, access_level)


def _fallback_access_level(subscription_status: str, feature_code: str) -> str:
    matrix = {
        "TRIAL": {
            FEATURE_WRITE_ACCESS: PlanFeatureEntitlement.ACCESS_ALLOW,
            FEATURE_EXPORT_PDF: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_EXCEL_WORD: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_CLEAN: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_PRO_ONLY: PlanFeatureEntitlement.ACCESS_DENY,
        },
        "PRO": {
            FEATURE_WRITE_ACCESS: PlanFeatureEntitlement.ACCESS_ALLOW,
            FEATURE_EXPORT_PDF: PlanFeatureEntitlement.ACCESS_ALLOW,
            FEATURE_EXPORT_EXCEL_WORD: PlanFeatureEntitlement.ACCESS_ALLOW,
            FEATURE_EXPORT_CLEAN: PlanFeatureEntitlement.ACCESS_ALLOW,
            FEATURE_PRO_ONLY: PlanFeatureEntitlement.ACCESS_ALLOW,
        },
        "EXPIRED": {
            FEATURE_WRITE_ACCESS: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_PDF: PlanFeatureEntitlement.ACCESS_WATERMARK,
            FEATURE_EXPORT_EXCEL_WORD: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_CLEAN: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_PRO_ONLY: PlanFeatureEntitlement.ACCESS_DENY,
        },
        INTERNAL_STATUS_TRIAL_PENDING: {
            FEATURE_WRITE_ACCESS: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_PDF: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_EXCEL_WORD: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_EXPORT_CLEAN: PlanFeatureEntitlement.ACCESS_DENY,
            FEATURE_PRO_ONLY: PlanFeatureEntitlement.ACCESS_DENY,
        },
    }
    return matrix.get(subscription_status, {}).get(
        feature_code,
        PlanFeatureEntitlement.ACCESS_DENY,
    )


def _normalize_subscription_status(user, subscription_status: str) -> str:
    """
    Convert nominal subscription status into an effective policy status.

    This prevents a "TRIAL" label without active trial window (or stale "PRO"
    without active end date) from unintentionally receiving active entitlements.
    """
    if subscription_status == "TRIAL" and not getattr(user, "is_trial_active", False):
        return INTERNAL_STATUS_TRIAL_PENDING
    if subscription_status == "PRO" and not getattr(user, "is_pro_active", False):
        return "EXPIRED"
    return subscription_status


def get_feature_access(user, feature_code: str) -> FeatureAccessDecision:
    """
    Resolve feature access from entitlement matrix.
    """
    if not getattr(user, "is_authenticated", False):
        return FeatureAccessDecision(
            allowed=False,
            code="AUTH_REQUIRED",
            message="Silakan login terlebih dahulu.",
            source="auth",
            access_level=PlanFeatureEntitlement.ACCESS_DENY,
        )

    if getattr(user, "has_full_access", False):
        return FeatureAccessDecision(
            allowed=True,
            code="ALLOWED_ADMIN",
            message="allowed",
            source="admin",
            access_level=PlanFeatureEntitlement.ACCESS_ALLOW,
        )

    raw_subscription_status = getattr(user, "subscription_status", "EXPIRED")
    subscription_status = _normalize_subscription_status(user, raw_subscription_status)
    if not getattr(user, "pk", None):
        fallback_level = _fallback_access_level(subscription_status, feature_code)
        return _level_to_decision(
            feature_code=feature_code,
            subscription_status=subscription_status,
            access_level=fallback_level,
            source="fallback",
        )

    try:
        feature = SubscriptionFeature.objects.filter(
            code=feature_code,
            is_active=True,
        ).first()
        if feature:
            plan = _latest_success_plan_for_user(user)
            base_qs = PlanFeatureEntitlement.objects.filter(
                feature=feature,
                subscription_status=subscription_status,
            )

            if plan:
                row = base_qs.filter(plan=plan).first()
                if row:
                    return _level_to_decision(
                        feature_code=feature_code,
                        subscription_status=subscription_status,
                        access_level=row.access_level,
                        source="plan",
                    )

            row = base_qs.filter(plan__isnull=True).first()
            if row:
                return _level_to_decision(
                    feature_code=feature_code,
                    subscription_status=subscription_status,
                    access_level=row.access_level,
                    source="status",
                )
    except Exception:
        # Fallback mode keeps policy behavior deterministic even when DB access
        # is unavailable (e.g. SimpleTestCase with mocked users).
        pass

    fallback_level = _fallback_access_level(subscription_status, feature_code)
    return _level_to_decision(
        feature_code=feature_code,
        subscription_status=subscription_status,
        access_level=fallback_level,
        source="fallback",
    )


def has_feature_access(user, feature_code: str) -> bool:
    return get_feature_access(user, feature_code).allowed
