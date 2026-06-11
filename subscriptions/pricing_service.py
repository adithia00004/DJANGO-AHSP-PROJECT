from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db.models import Prefetch
from django.utils import timezone

from .models import SubscriptionPlan, SubscriptionPlanPromotion


ZERO = Decimal("0")
MONEY_QUANT = Decimal("1")
PERCENT_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class EffectivePlanPricing:
    plan: SubscriptionPlan
    base_price: Decimal
    final_price: Decimal
    discount_amount: Decimal
    discount_percent: Decimal
    promotion: Optional[SubscriptionPlanPromotion]
    discount_badge: Optional[str]


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_currency_idr(value: Decimal) -> str:
    return f"Rp {int(_quantize_money(value)):,}".replace(",", ".")


def _format_promo_datetime(value) -> str:
    if not value:
        return ""
    local_value = timezone.localtime(value)
    return local_value.strftime("%d %b %Y %H:%M %Z").strip()


def _format_discount_badge(
    promotion: Optional[SubscriptionPlanPromotion],
    discount_amount: Decimal,
) -> Optional[str]:
    if not promotion or discount_amount <= ZERO:
        return None

    if promotion.discount_type == SubscriptionPlanPromotion.DISCOUNT_PERCENT:
        return f"Hemat {_format_decimal(promotion.discount_value)}%"

    return f"Hemat {format_currency_idr(discount_amount)}"


def _get_plan_features(duration_months: int):
    base_features = [
        "Akses Penuh Semua Fitur",
        "Export PDF & Excel",
        "Gantt Chart Interaktif",
        "Kurva S Otomatis",
    ]

    if duration_months >= 12:
        return base_features + ["Support VIP", "Konsultasi 1-on-1"]

    if duration_months >= 6:
        return base_features + ["Support Prioritas"]

    return base_features + ["Support Email"]


def select_active_promotion(
    plan: SubscriptionPlan,
    now=None,
) -> Optional[SubscriptionPlanPromotion]:
    now = now or timezone.now()

    prefetched = getattr(plan, "active_promotions_now", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None

    return (
        plan.promotions.filter(
            is_active=True,
            start_at__lte=now,
            end_at__gt=now,
        )
        .order_by("-priority", "-created_at", "-id")
        .first()
    )


def resolve_effective_plan_pricing(
    plan: SubscriptionPlan,
    now=None,
    promotion: Optional[SubscriptionPlanPromotion] = None,
) -> EffectivePlanPricing:
    now = now or timezone.now()
    base_price = _quantize_money(plan.price)
    promotion = promotion if promotion is not None else select_active_promotion(plan, now=now)

    discount_amount = ZERO
    if promotion:
        if promotion.discount_type == SubscriptionPlanPromotion.DISCOUNT_PERCENT:
            discount_amount = _quantize_money(
                base_price * (promotion.discount_value / Decimal("100"))
            )
        else:
            discount_amount = _quantize_money(promotion.discount_value)

    if discount_amount > base_price:
        discount_amount = base_price

    final_price = base_price - discount_amount
    discount_percent = ZERO
    if base_price > ZERO and discount_amount > ZERO:
        discount_percent = (discount_amount / base_price * Decimal("100")).quantize(
            PERCENT_QUANT,
            rounding=ROUND_HALF_UP,
        )

    return EffectivePlanPricing(
        plan=plan,
        base_price=base_price,
        final_price=final_price,
        discount_amount=discount_amount,
        discount_percent=discount_percent,
        promotion=promotion,
        discount_badge=_format_discount_badge(promotion, discount_amount),
    )


def serialize_pricing_for_display(
    pricing: EffectivePlanPricing,
    now=None,
) -> dict:
    now = now or timezone.now()
    plan = pricing.plan
    monthly_price = _quantize_money(pricing.final_price / Decimal(plan.duration_months))
    promotion_state = "none"
    promotion_state_label = "Belum Ada Promo"
    promotion_timing_label = "Pantau update promo berikutnya."
    promotion_panel_name = ""

    if pricing.promotion:
        promotion_state = "active"
        promotion_state_label = "Promo Aktif"
        promotion_timing_label = (
            f"Berakhir { _format_promo_datetime(pricing.promotion.end_at) }"
        )
        promotion_panel_name = pricing.promotion.name

    return {
        "id": plan.id,
        "base_tier": plan.base_tier,
        "base_tier_label": plan.get_base_tier_display() if plan.base_tier else "",
        "name": plan.name,
        "duration": f"{plan.duration_months} Bulan",
        "duration_months": plan.duration_months,
        "price": pricing.final_price,
        "base_price": pricing.base_price,
        "discount_amount": pricing.discount_amount,
        "discount_percent": pricing.discount_percent,
        "price_display": format_currency_idr(pricing.final_price),
        "base_price_display": format_currency_idr(pricing.base_price),
        "per_month": f"{format_currency_idr(monthly_price)}/bulan",
        "features": _get_plan_features(plan.duration_months),
        "popular": plan.duration_months == 6,
        "discount": pricing.discount_badge,
        "promotion_name": pricing.promotion.name if pricing.promotion else "",
        "promotion_panel_name": promotion_panel_name,
        "promotion_state": promotion_state,
        "promotion_state_label": promotion_state_label,
        "promotion_timing_label": promotion_timing_label,
        "promotion_end_at_display": (
            _format_promo_datetime(pricing.promotion.end_at) if pricing.promotion else ""
        ),
        "promotion_start_at_display": "",
        "is_promo_highlighted": promotion_state == "active",
        "is_upcoming_promo": False,
        "is_no_promo": promotion_state == "none",
        "now_display": _format_promo_datetime(now),
    }


def get_active_pricing_plans(now=None):
    now = now or timezone.now()

    active_promotion_qs = SubscriptionPlanPromotion.objects.filter(
        is_active=True,
        start_at__lte=now,
        end_at__gt=now,
    ).order_by("-priority", "-created_at", "-id")
    plans = (
        SubscriptionPlan.objects.filter(
            is_active=True,
            base_tier__in=[
                SubscriptionPlan.BASE_TIER_1,
                SubscriptionPlan.BASE_TIER_2,
                SubscriptionPlan.BASE_TIER_3,
            ],
        )
        .order_by("base_tier", "duration_months")
        .prefetch_related(
            Prefetch(
                "promotions",
                queryset=active_promotion_qs,
                to_attr="active_promotions_now",
            )
        )
    )

    return [
        serialize_pricing_for_display(
            resolve_effective_plan_pricing(
                plan=plan,
                now=now,
                promotion=plan.active_promotions_now[0] if plan.active_promotions_now else None,
            ),
            now=now,
        )
        for plan in plans
    ]
