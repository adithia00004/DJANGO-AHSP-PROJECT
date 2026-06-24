from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser

# Subscription fields live on CustomUser but the stock UserAdmin never showed
# them, so support/admins could not view or adjust trial/PRO state from the
# admin UI. Surface them in the changelist, filters, and the edit form.
_SUBSCRIPTION_FIELDS = (
    "subscription_status",
    "trial_end_date",
    "subscription_end_date",
    "trial_used_once",
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + (
        "subscription_status",
        "is_subscription_active",
    )
    list_filter = UserAdmin.list_filter + (
        "subscription_status",
        "trial_used_once",
    )
    fieldsets = UserAdmin.fieldsets + (
        ("Subscription", {"fields": _SUBSCRIPTION_FIELDS}),
    )

    @admin.display(boolean=True, description="Subscription active")
    def is_subscription_active(self, obj):
        return obj.is_subscription_active
