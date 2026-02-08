"""
Subscription-based access control mixins and decorators.

Usage:
- SubscriptionRequiredMixin: For class-based views
- subscription_required: For function-based views
- active_subscription_required: For API views (returns JSON error)
"""
from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from subscriptions.entitlements import (
    FEATURE_EXPORT_EXCEL_WORD,
    FEATURE_EXPORT_PDF,
    FEATURE_PRO_ONLY,
    FEATURE_WRITE_ACCESS,
    get_feature_access,
)


class SubscriptionRequiredMixin:
    """
    Mixin for class-based views that require an active subscription.
    
    Users with EXPIRED subscription will be redirected to upgrade page.
    
    Usage:
        class MyView(SubscriptionRequiredMixin, View):
            subscription_redirect_url = 'pages:pricing'  # Optional
    """
    subscription_redirect_url = 'pages:pricing'
    subscription_message = "Langganan Anda telah berakhir. Silakan upgrade untuk melanjutkan."
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')

        decision = get_feature_access(request.user, FEATURE_WRITE_ACCESS)
        if not decision.allowed:
            messages.warning(request, self.subscription_message)
            return redirect(self.subscription_redirect_url)

        return super().dispatch(request, *args, **kwargs)


class ProSubscriptionRequiredMixin(SubscriptionRequiredMixin):
    """
    Mixin that requires PRO subscription (not trial).
    
    Used for premium features like clean exports.
    """
    subscription_message = "Fitur ini hanya tersedia untuk pengguna Pro."
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')

        decision = get_feature_access(request.user, FEATURE_PRO_ONLY)
        if not decision.allowed:
            messages.warning(request, self.subscription_message)
            return redirect(self.subscription_redirect_url)

        return super(SubscriptionRequiredMixin, self).dispatch(request, *args, **kwargs)


def subscription_required(view_func=None, redirect_url='pages:pricing'):
    """
    Decorator for function-based views requiring active subscription.
    
    Usage:
        @subscription_required
        def my_view(request):
            ...
        
        @subscription_required(redirect_url='custom:upgrade')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('account_login')

            decision = get_feature_access(request.user, FEATURE_WRITE_ACCESS)
            if not decision.allowed:
                messages.warning(
                    request,
                    "Langganan Anda telah berakhir. Silakan upgrade untuk melanjutkan."
                )
                return redirect(redirect_url)

            return view_func(request, *args, **kwargs)
        return wrapper
    
    if view_func is not None:
        return decorator(view_func)
    return decorator


def pro_subscription_required(view_func=None, redirect_url='pages:pricing'):
    """
    Decorator for function-based views requiring PRO subscription.
    
    Usage:
        @pro_subscription_required
        def export_pdf(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('account_login')

            decision = get_feature_access(request.user, FEATURE_PRO_ONLY)
            if not decision.allowed:
                messages.warning(
                    request,
                    "Fitur ini hanya tersedia untuk pengguna Pro."
                )
                return redirect(redirect_url)

            return view_func(request, *args, **kwargs)
        return wrapper
    
    if view_func is not None:
        return decorator(view_func)
    return decorator


def api_subscription_required(view_func):
    """
    Decorator for API views that require active subscription.
    Returns JSON error instead of redirect.
    
    Usage:
        @api_subscription_required
        def api_save_data(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }, status=401)

        decision = get_feature_access(request.user, FEATURE_WRITE_ACCESS)
        if not decision.allowed:
            return JsonResponse({
                'success': False,
                'error': decision.message,
                'code': decision.code,
                'upgrade_url': decision.upgrade_url,
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


def api_pro_required(view_func):
    """
    Decorator for API views that require PRO subscription.
    Returns JSON error instead of redirect.
    
    Usage:
        @api_pro_required
        def api_export_clean(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }, status=401)

        decision = get_feature_access(request.user, FEATURE_PRO_ONLY)
        if not decision.allowed:
            return JsonResponse({
                'success': False,
                'error': decision.message,
                'code': decision.code,
                'upgrade_url': decision.upgrade_url,
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================
# EXPORT-SPECIFIC DECORATORS
# ============================================================

def api_export_excel_word_required(view_func):
    """
    Decorator for Excel/Word export APIs.
    Only allows PRO users (blocks TRIAL and EXPIRED).
    
    Feature Matrix:
    - TRIAL: ❌ (blocked)
    - PRO: ✅
    - EXPIRED: ❌ (blocked)
    
    Usage:
        @api_export_excel_word_required
        def export_rekap_xlsx(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Silakan login terlebih dahulu.',
                'code': 'AUTH_REQUIRED'
            }, status=401)

        decision = get_feature_access(request.user, FEATURE_EXPORT_EXCEL_WORD)
        if not decision.allowed:
            return JsonResponse({
                'success': False,
                'error': decision.message,
                'code': decision.code,
                'subscription_status': request.user.subscription_status,
                'upgrade_url': decision.upgrade_url,
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


def get_pdf_export_context(request):
    """
    Get context for PDF export based on subscription status.
    
    Returns dict with:
    - add_watermark: bool - True if watermark should be added
    - watermark_text: str - Text to use for watermark
    - is_pro: bool - True if user has PRO subscription
    
    Feature Matrix:
    - TRIAL: ❌ (blocked - cannot export PDF)
    - PRO: ✅ Clean PDF
    - EXPIRED: ✅ PDF with watermark
    
    Usage in export view:
        ctx = get_pdf_export_context(request)
        if ctx.get('blocked'):
            return ctx['response']
        if ctx['add_watermark']:
            # Add watermark logic
    """
    decision = get_feature_access(request.user, FEATURE_EXPORT_PDF)
    if not decision.allowed:
        return {
            'blocked': True,
            'response': JsonResponse({
                'success': False,
                'error': decision.message,
                'code': decision.code,
                'upgrade_url': decision.upgrade_url,
            }, status=403 if decision.code != 'AUTH_REQUIRED' else 401)
        }

    return {
        'blocked': False,
        'add_watermark': decision.add_watermark,
        'watermark_text': 'DEMO - Dashboard-RAB' if decision.add_watermark else None,
        'is_pro': not decision.add_watermark,
    }


def api_pdf_export_allowed(view_func):
    """
    Decorator for PDF export APIs.
    - Blocks TRIAL users completely
    - Allows PRO users (clean PDF)
    - Allows EXPIRED users (with watermark flag in request)
    
    The decorated view receives request.pdf_export_context with:
    - add_watermark: bool
    - watermark_text: str or None
    
    Usage:
        @api_pdf_export_allowed
        def export_rekap_pdf(request):
            if request.pdf_export_context['add_watermark']:
                # Add watermark to PDF
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        ctx = get_pdf_export_context(request)
        
        if ctx.get('blocked'):
            return ctx['response']
        
        # Attach context to request for view to use
        request.pdf_export_context = ctx
        
        return view_func(request, *args, **kwargs)
    return wrapper

