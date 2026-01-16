"""
Context processors for subscription-related template variables.
"""


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
    
    return {
        'subscription_status': user.subscription_status,
        'is_subscription_active': user.is_subscription_active,
        'is_trial_active': user.is_trial_active,
        'is_pro_active': user.is_pro_active,
        'can_edit': user.can_edit,
        'can_export_clean': user.can_export_clean,
        'days_until_expiry': user.days_until_expiry,
        'subscription_days_left': user.days_until_expiry,  # alias for templates
        'show_upgrade_banner': (
            user.subscription_status == 'TRIAL' or
            user.subscription_status == 'EXPIRED' or
            (user.is_subscription_active and user.days_until_expiry <= 7)
        ),
    }
