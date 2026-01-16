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
        
        # Admin keypass bypass
        if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
            return super().dispatch(request, *args, **kwargs)
        
        # Check if user has active subscription
        if not request.user.is_subscription_active:
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
        
        # Admin keypass bypass
        if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
            return super(SubscriptionRequiredMixin, self).dispatch(request, *args, **kwargs)
        
        # Only allow PRO users
        if not request.user.is_pro_active:
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
            
            # Admin keypass bypass
            if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
                return view_func(request, *args, **kwargs)
            
            if not request.user.is_subscription_active:
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
            
            # Admin keypass bypass
            if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
                return view_func(request, *args, **kwargs)
            
            if not request.user.is_pro_active:
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
        
        # Admin keypass bypass
        if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
            return view_func(request, *args, **kwargs)
        
        if not request.user.is_subscription_active:
            return JsonResponse({
                'success': False,
                'error': 'Langganan Anda telah berakhir. Silakan upgrade untuk melanjutkan.',
                'code': 'SUBSCRIPTION_EXPIRED',
                'upgrade_url': '/pricing/'
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
        
        # Admin keypass bypass
        if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
            return view_func(request, *args, **kwargs)
        
        if not request.user.is_pro_active:
            return JsonResponse({
                'success': False,
                'error': 'Fitur ini hanya tersedia untuk pengguna Pro.',
                'code': 'PRO_REQUIRED',
                'upgrade_url': '/pricing/'
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
        
        # Admin keypass bypass
        if hasattr(request.user, 'has_full_access') and request.user.has_full_access:
            return view_func(request, *args, **kwargs)
        
        if not request.user.is_pro_active:
            return JsonResponse({
                'success': False,
                'error': 'Export Excel dan Word hanya tersedia untuk pengguna Pro. Silakan upgrade langganan Anda.',
                'code': 'PRO_REQUIRED',
                'subscription_status': request.user.subscription_status,
                'upgrade_url': '/subscriptions/pricing/'
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
    if not request.user.is_authenticated:
        return {
            'blocked': True,
            'response': JsonResponse({
                'success': False,
                'error': 'Silakan login terlebih dahulu.',
                'code': 'AUTH_REQUIRED'
            }, status=401)
        }
    
    user = request.user
    
    # Admin keypass bypass - treat as PRO
    if hasattr(user, 'has_full_access') and user.has_full_access:
        return {
            'blocked': False,
            'add_watermark': False,
            'watermark_text': None,
            'is_pro': True
        }
    
    # TRIAL users cannot export PDF at all (per feature matrix)
    if user.subscription_status == 'TRIAL':
        return {
            'blocked': True,
            'response': JsonResponse({
                'success': False,
                'error': 'Export PDF tersedia setelah Anda upgrade ke Pro. Trial tidak termasuk fitur export.',
                'code': 'TRIAL_NO_EXPORT',
                'upgrade_url': '/subscriptions/pricing/'
            }, status=403)
        }
    
    # PRO users get clean PDF
    if user.is_pro_active:
        return {
            'blocked': False,
            'add_watermark': False,
            'watermark_text': None,
            'is_pro': True
        }
    
    # EXPIRED users get watermarked PDF
    return {
        'blocked': False,
        'add_watermark': True,
        'watermark_text': 'DEMO - Dashboard-RAB',
        'is_pro': False
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

