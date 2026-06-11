"""
Context processors for subscription-related template variables.
"""
from django.conf import settings


def app_contact_context(request):
    """
    Add support contact variables available to all templates.
    """
    return {
        "support_email": getattr(settings, "SUPPORT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "")),
    }


def subscription_context(request):
    """
    Add subscription-related variables to all templates.
    
    Available in templates:
    - subscription_status: Current status (TRIAL/PRO/EXPIRED)
    - is_subscription_active: True if user has active subscription
    - can_edit: True if user can edit/input data
    - can_export_clean: True if user can export without watermark
    - days_until_expiry: Days remaining until expiry
    - show_upgrade_banner: True if should show upgrade prompt
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user

    # M7 (audit UI/UX): tombol export Pro harus terlihat TERKUNCI bagi user
    # tanpa entitlement, bukan gagal setelah diklik. Dipakai oleh
    # detail_project/_export_menu_item.html.
    from subscriptions.entitlements import (
        FEATURE_EXPORT_EXCEL_WORD,
        FEATURE_EXPORT_PDF,
        get_feature_access,
    )
    pdf_access = get_feature_access(user, FEATURE_EXPORT_PDF)
    excel_word_access = get_feature_access(user, FEATURE_EXPORT_EXCEL_WORD)

    return {
        'export_pdf_allowed': pdf_access.allowed,
        'export_pdf_watermark': pdf_access.add_watermark,
        'export_excel_word_allowed': excel_word_access.allowed,
        'subscription_status': 'ADMIN' if user.has_full_access else user.subscription_status,
        'is_subscription_active': user.is_subscription_active,
        'is_trial_active': user.is_trial_active,
        'is_pro_active': user.is_pro_active,
        'can_edit': user.can_edit,
        'can_export_clean': user.can_export_clean,
        'days_until_expiry': user.days_until_expiry,
        'subscription_days_left': user.days_until_expiry,  # alias for templates
        'show_upgrade_banner': (
            (not user.has_full_access) and (
                user.subscription_status == 'TRIAL' or
                user.subscription_status == 'EXPIRED' or
                (user.is_subscription_active and user.days_until_expiry <= 7)
            )
        ),
    }
