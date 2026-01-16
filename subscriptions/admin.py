from django.contrib import admin
from .models import SubscriptionPlan, PaymentTransaction


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_months', 'price', 'is_active']
    list_filter = ['is_active', 'duration_months']
    search_fields = ['name']


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'plan', 'amount', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'payment_type', 'created_at']
    search_fields = ['order_id', 'user__email', 'user__username']
    readonly_fields = [
        'id', 'order_id', 'snap_token', 'midtrans_transaction_id',
        'midtrans_response', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('id', 'order_id', 'user', 'plan', 'amount', 'status')
        }),
        ('Midtrans Data', {
            'fields': ('snap_token', 'midtrans_transaction_id', 'payment_type', 'midtrans_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at')
        }),
    )
