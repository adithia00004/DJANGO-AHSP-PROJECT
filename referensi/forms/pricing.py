from django import forms

from subscriptions.models import SubscriptionPlan, SubscriptionPlanPromotion


class SubscriptionPlanPricingForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = ["name", "duration_months", "price", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "duration_months": forms.NumberInput(
                attrs={"class": "form-control form-control-sm text-end", "min": "1", "step": "1"}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control form-control-sm text-end", "min": "0", "step": "1"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SubscriptionPlanPromotionForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlanPromotion
        fields = [
            "plan",
            "name",
            "discount_type",
            "discount_value",
            "start_at",
            "end_at",
            "priority",
            "is_active",
        ]
        widgets = {
            "plan": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "discount_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "discount_value": forms.NumberInput(
                attrs={"class": "form-control form-control-sm text-end", "min": "0", "step": "0.01"}
            ),
            "start_at": forms.DateTimeInput(
                attrs={"class": "form-control form-control-sm", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_at": forms.DateTimeInput(
                attrs={"class": "form-control form-control-sm", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "priority": forms.NumberInput(
                attrs={"class": "form-control form-control-sm text-end", "step": "1"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = SubscriptionPlan.objects.filter(
            base_tier__in=[
                SubscriptionPlan.BASE_TIER_1,
                SubscriptionPlan.BASE_TIER_2,
                SubscriptionPlan.BASE_TIER_3,
            ]
        ).order_by("base_tier")
        for field_name in ("start_at", "end_at"):
            field = self.fields[field_name]
            field.input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
