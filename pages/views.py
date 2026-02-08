from django.shortcuts import redirect
from django.views.generic import TemplateView

from referensi.permissions import has_referensi_portal_access


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
    
    def _get_pricing_plans(self):
        """Get pricing plans from database or fallback to hardcoded."""
        from subscriptions.models import SubscriptionPlan
        
        db_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('duration_months')
        
        if db_plans.exists():
            # Use database plans
            plans = []
            for plan in db_plans:
                plans.append({
                    'id': plan.id,
                    'name': plan.name,
                    'duration': f'{plan.duration_months} Bulan',
                    'price': plan.price,
                    'price_display': f'Rp {plan.price:,.0f}'.replace(',', '.'),
                    'per_month': f'Rp {plan.price / plan.duration_months:,.0f}/bulan'.replace(',', '.'),
                    'features': [
                        'Akses Penuh Semua Fitur',
                        'Export PDF & Excel',
                        'Gantt Chart Interaktif',
                        'Kurva S Otomatis',
                        'Support Prioritas' if plan.duration_months >= 6 else 'Support Email',
                    ],
                    'popular': plan.duration_months == 6,  # 6 month plan is popular
                    'discount': '17%' if plan.duration_months == 6 else ('30%' if plan.duration_months == 12 else None),
                })
            return plans
        
        # Fallback to hardcoded (for development without seeded plans)
        return [
            {
                'id': None,
                'name': 'Quarterly',
                'duration': '3 Bulan',
                'price': 900000,
                'price_display': 'Rp 900.000',
                'per_month': 'Rp 300.000/bulan',
                'features': [
                    'Akses Penuh Semua Fitur',
                    'Export PDF & Excel',
                    'Gantt Chart Interaktif',
                    'Kurva S Otomatis',
                    'Support Email',
                ],
                'popular': False,
            },
            {
                'id': None,
                'name': 'Semi-Annual',
                'duration': '6 Bulan',
                'price': 1500000,
                'price_display': 'Rp 1.500.000',
                'per_month': 'Rp 250.000/bulan',
                'features': [
                    'Akses Penuh Semua Fitur',
                    'Export PDF & Excel',
                    'Gantt Chart Interaktif',
                    'Kurva S Otomatis',
                    'Support Prioritas',
                ],
                'popular': True,
                'discount': '17%',
            },
            {
                'id': None,
                'name': 'Annual',
                'duration': '12 Bulan',
                'price': 2500000,
                'price_display': 'Rp 2.500.000',
                'per_month': 'Rp 208.000/bulan',
                'features': [
                    'Akses Penuh Semua Fitur',
                    'Export PDF & Excel',
                    'Gantt Chart Interaktif',
                    'Kurva S Otomatis',
                    'Support VIP',
                    'Konsultasi 1-on-1',
                ],
                'popular': False,
                'discount': '31%',
            },
        ]


class PricingPageView(TemplateView):
    """
    Dedicated pricing page with detailed plan comparison.
    """
    template_name = 'pages/pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Reuse pricing data from LandingPageView
        landing_view = LandingPageView()
        context.update(landing_view.get_context_data())
        return context

