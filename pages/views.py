from django.shortcuts import redirect
from django.views.generic import TemplateView

from referensi.permissions import has_referensi_portal_access
from subscriptions.pricing_service import get_active_pricing_plans


class LandingPageView(TemplateView):
    """
    Landing page - the main entry point for unauthenticated users.
    Redirects authenticated users based on role/permissions.
    """
    template_name = 'pages/landing.html'

    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users to their primary area
        if request.user.is_authenticated:
            if has_referensi_portal_access(request.user):
                return redirect('referensi:admin_portal')
            return redirect('dashboard:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pricing_plans'] = self._get_pricing_plans()
        return context
    
    @staticmethod
    def _get_pricing_plans():
        return get_active_pricing_plans()


class PricingPageView(TemplateView):
    """
    Dedicated pricing page with detailed plan comparison.
    """
    template_name = 'pages/pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pricing_plans'] = LandingPageView._get_pricing_plans()
        return context

