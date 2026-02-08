"""
Management command to seed initial subscription plans.
"""
from django.core.management.base import BaseCommand
from subscriptions.models import PlanFeatureEntitlement, SubscriptionFeature, SubscriptionPlan


class Command(BaseCommand):
    help = 'Create initial subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Quarterly (3 Bulan)',
                'duration_months': 3,
                'price': 900000,
                'description': 'Akses penuh selama 3 bulan',
            },
            {
                'name': 'Semi-Annual (6 Bulan)',
                'duration_months': 6,
                'price': 1500000,
                'description': 'Akses penuh selama 6 bulan - Hemat 17%',
            },
            {
                'name': 'Annual (12 Bulan)',
                'duration_months': 12,
                'price': 2500000,
                'description': 'Akses penuh selama 12 bulan - Hemat 31%',
            },
        ]
        
        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                duration_months=plan_data['duration_months'],
                defaults={
                    'name': plan_data['name'],
                    'price': plan_data['price'],
                    'description': plan_data['description'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created: {plan.name}'))
            else:
                self.stdout.write(f'Updated: {plan.name}')

            # Ensure plan-level entitlement defaults exist for PRO tier.
            for feature_code in [
                "write_access",
                "export_pdf",
                "export_excel_word",
                "export_clean",
                "pro_only",
            ]:
                feature = SubscriptionFeature.objects.filter(code=feature_code).first()
                if not feature:
                    continue
                PlanFeatureEntitlement.objects.get_or_create(
                    feature=feature,
                    plan=plan,
                    subscription_status="PRO",
                    defaults={
                        "access_level": PlanFeatureEntitlement.ACCESS_ALLOW,
                        "note": "Plan-level PRO default",
                    },
                )
        
        self.stdout.write(self.style.SUCCESS('Subscription plans seeded successfully!'))
