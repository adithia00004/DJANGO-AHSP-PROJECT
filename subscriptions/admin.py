from django.contrib import admin
from .models import (
    PaymentTransaction,
    PlanFeatureEntitlement,
    SubscriptionFeature,
    SubscriptionPlan,
    SubscriptionPlanPromotion,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['base_tier', 'name', 'duration_months', 'price', 'is_active', 'entitlement_count']
    list_filter = ['base_tier', 'is_active', 'duration_months']
    search_fields = ['name']

    def entitlement_count(self, obj):
        return obj.feature_entitlements.count()


@admin.register(SubscriptionPlanPromotion)
class SubscriptionPlanPromotionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "plan",
        "discount_type",
        "discount_value",
        "start_at",
        "end_at",
        "priority",
        "is_active",
    ]
    list_filter = ["discount_type", "is_active", "priority", "plan"]
    search_fields = ["name", "plan__name"]


@admin.register(SubscriptionFeature)
class SubscriptionFeatureAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(PlanFeatureEntitlement)
class PlanFeatureEntitlementAdmin(admin.ModelAdmin):
    list_display = ["feature", "subscription_status", "plan", "access_level", "note"]
    list_filter = ["subscription_status", "access_level", "plan", "feature"]
    search_fields = ["feature__code", "feature__name", "plan__name", "note"]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'order_id',
        'user',
        'plan',
        'amount',
        'duration_months_snapshot',
        'base_amount_snapshot',
        'discount_amount_snapshot',
        'status',
        'created_at',
        'paid_at',
    ]
    list_filter = ['status', 'payment_type', 'created_at']
    search_fields = ['order_id', 'user__email', 'user__username']
    readonly_fields = [
        'id', 'order_id', 'snap_token', 'midtrans_transaction_id',
        'midtrans_response', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Transaction Info', {
            'fields': (
                'id',
                'order_id',
                'user',
                'plan',
                'amount',
                'duration_months_snapshot',
                'base_amount_snapshot',
                'discount_amount_snapshot',
                'promotion_id_snapshot',
                'promotion_name_snapshot',
                'promotion_discount_type_snapshot',
                'promotion_discount_value_snapshot',
                'status',
            )
        }),
        ('Midtrans Data', {
            'fields': ('snap_token', 'midtrans_transaction_id', 'payment_type', 'midtrans_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at')
        }),
    )
