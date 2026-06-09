"""Admin portal and database maintenance views."""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from referensi.forms import (
    AHSPReferensiInlineForm,
    RincianReferensiInlineForm,
    SubscriptionPlanPricingForm,
    SubscriptionPlanPromotionForm,
)
from referensi.models import AHSPReferensi, RincianReferensi
from referensi.permissions import has_referensi_portal_access
from referensi.services.admin_service import AdminPortalService
from subscriptions.models import SubscriptionPlan, SubscriptionPlanPromotion
from subscriptions.pricing_service import (
    format_currency_idr,
    resolve_effective_plan_pricing,
)

from .constants import ITEM_DISPLAY_LIMIT, JOB_DISPLAY_LIMIT, TAB_ITEMS, TAB_JOBS


@login_required
def admin_portal(request):
    if not has_referensi_portal_access(request.user):
        messages.warning(request, "Anda tidak memiliki izin untuk mengakses Admin Portal.")
        return redirect("/")
        
    return render(request, "referensi/admin_portal.html")


@login_required
def ahsp_database(request):
    if not has_referensi_portal_access(request.user):
        messages.warning(request, "Anda tidak memiliki izin untuk mengakses Database AHSP.")
        return redirect("/")
    service = AdminPortalService(
        job_limit=JOB_DISPLAY_LIMIT,
        item_limit=ITEM_DISPLAY_LIMIT,
    )

    active_tab = (
        request.POST.get("active_tab")
        or request.GET.get("tab")
        or TAB_JOBS
    )
    if active_tab not in {TAB_JOBS, TAB_ITEMS}:
        active_tab = TAB_JOBS

    job_filter_source = (
        request.POST
        if request.method == "POST" and active_tab == TAB_JOBS
        else request.GET
    )
    jobs_filters = service.parse_job_filters(job_filter_source)

    jobs_queryset_base = service.apply_job_filters(
        service.base_ahsp_queryset(), jobs_filters
    )
    total_jobs_filtered = jobs_queryset_base.count()

    jobs_queryset = (
        jobs_queryset_base
        .order_by("kode_ahsp")
        .only(
            "id",
            "kode_ahsp",
            "nama_ahsp",
            "klasifikasi",
            "sub_klasifikasi",
            "satuan",
            "sumber",
            "source_file",
        )
    )
    jobs_truncated = total_jobs_filtered > service.job_limit
    if jobs_truncated:
        jobs_queryset = jobs_queryset[:service.job_limit]

    JobsFormSet = modelformset_factory(
        AHSPReferensi,
        form=AHSPReferensiInlineForm,
        extra=0,
    )

    if request.method == "POST" and active_tab == TAB_JOBS:
        jobs_formset = JobsFormSet(request.POST, queryset=jobs_queryset)
        if jobs_formset.is_valid():
            jobs_formset.save()
            messages.success(request, "Perubahan pada pekerjaan AHSP berhasil disimpan.")
            return redirect(
                _build_redirect_url(
                    TAB_JOBS,
                    jobs_filters,
                )
            )
    else:
        jobs_formset = JobsFormSet(queryset=jobs_queryset)

    jobs_rows, jobs_anomaly_displayed = service.build_job_rows(jobs_formset)

    items_filter_source = (
        request.POST
        if request.method == "POST" and active_tab == TAB_ITEMS
        else request.GET
    )
    items_filters = service.parse_item_filters(items_filter_source)

    items_queryset_base = service.apply_item_filters(
        service.base_item_queryset().only(
            "id",
            "kategori",
            "kode_item",
            "uraian_item",
            "satuan_item",
            "koefisien",
            "ahsp__id",
            "ahsp__kode_ahsp",
            "ahsp__nama_ahsp",
            "ahsp__sumber",
        ),
        items_filters,
    )
    total_items_filtered = items_queryset_base.count()

    items_queryset = items_queryset_base.order_by(
        "ahsp__kode_ahsp", "kategori", "kode_item"
    )
    items_truncated = total_items_filtered > service.item_limit
    if items_truncated:
        items_queryset = items_queryset[:service.item_limit]

    ItemsFormSet = modelformset_factory(
        RincianReferensi,
        form=RincianReferensiInlineForm,
        extra=0,
    )

    if request.method == "POST" and active_tab == TAB_ITEMS:
        items_formset = ItemsFormSet(request.POST, queryset=items_queryset)
        if items_formset.is_valid():
            items_formset.save()
            messages.success(request, "Perubahan pada rincian AHSP berhasil disimpan.")
            return redirect(
                _build_redirect_url(
                    TAB_ITEMS,
                    items_filters,
                )
            )
    else:
        items_formset = ItemsFormSet(queryset=items_queryset)

    item_rows, items_anomaly_displayed = service.build_item_rows(items_formset)

    available_sources = service.available_sources()
    available_klasifikasi = service.available_klasifikasi()

    job_filter_params = service.job_filter_query_params(jobs_filters)
    item_filter_params = service.item_filter_query_params(items_filters)

    job_choices = service.job_choices(limit=5000)

    context = {
        "active_tab": active_tab,
        "jobs": {
            "formset": jobs_formset,
            "rows": jobs_rows,
            "filters": jobs_filters,
            "filter_params": job_filter_params,
            "summary": {
                "displayed": len(jobs_rows),
                "total_filtered": total_jobs_filtered,
                "anomaly_displayed": jobs_anomaly_displayed,
                "truncated": jobs_truncated,
                "limit": service.job_limit,
            },
        },
        "jobs_filter_options": {
            "sumber": available_sources,
            "klasifikasi": available_klasifikasi,
            "kategori": RincianReferensi.Kategori.choices,
        },
        "items": {
            "formset": items_formset,
            "rows": item_rows,
            "filters": items_filters,
            "filter_params": item_filter_params,
            "summary": {
                "displayed": len(item_rows),
                "total_filtered": total_items_filtered,
                "anomaly_displayed": items_anomaly_displayed,
                "truncated": items_truncated,
                "limit": service.item_limit,
            },
        },
        "item_filter_options": {
            "kategori": RincianReferensi.Kategori.choices,
            "jobs": job_choices,
        },
    }
    return render(request, "referensi/ahsp_database.html", context)


@login_required
def ahsp_database_api(request):
    if not has_referensi_portal_access(request.user):
        return redirect("/")
    """
    Lightweight view for API-based AHSP Database.
    
    Only passes minimal context needed for initial render.
    Data is loaded via JavaScript API calls.
    """
    # Get sources for filter dropdown (lightweight query)
    sources = list(
        AHSPReferensi.objects
        .values_list('sumber', flat=True)
        .distinct()
        .order_by('sumber')
    )
    sources = [s for s in sources if s]  # Remove empty values
    
    context = {
        'sources': sources,
    }
    return render(request, "referensi/ahsp_database_api.html", context)


@login_required
def pricing_management(request):
    if not has_referensi_portal_access(request.user):
        messages.warning(request, "Anda tidak memiliki izin untuk mengakses manajemen pricing.")
        return redirect("/")

    plans_queryset = SubscriptionPlan.objects.filter(
        base_tier__in=[
            SubscriptionPlan.BASE_TIER_1,
            SubscriptionPlan.BASE_TIER_2,
            SubscriptionPlan.BASE_TIER_3,
        ]
    ).order_by("base_tier")
    promotions_queryset = SubscriptionPlanPromotion.objects.select_related("plan").filter(
        plan__base_tier__in=[
            SubscriptionPlan.BASE_TIER_1,
            SubscriptionPlan.BASE_TIER_2,
            SubscriptionPlan.BASE_TIER_3,
        ]
    ).order_by(
        "-is_active", "-priority", "-start_at", "-created_at"
    )

    PlanFormSet = modelformset_factory(
        SubscriptionPlan,
        form=SubscriptionPlanPricingForm,
        extra=0,
    )
    PromotionFormSet = modelformset_factory(
        SubscriptionPlanPromotion,
        form=SubscriptionPlanPromotionForm,
        extra=1,
        can_delete=False,
    )

    action = request.POST.get("action")
    if request.method == "POST" and action == "save_plans":
        plans_formset = PlanFormSet(request.POST, queryset=plans_queryset, prefix="plans")
        promotions_formset = PromotionFormSet(queryset=promotions_queryset, prefix="promos")
        if plans_formset.is_valid():
            plans_formset.save()
            messages.success(request, "Harga plan berhasil diperbarui.")
            return redirect("referensi:pricing_management")
        messages.error(request, "Perubahan plan belum tersimpan. Periksa data yang dimasukkan.")
    elif request.method == "POST" and action == "save_promotions":
        plans_formset = PlanFormSet(queryset=plans_queryset, prefix="plans")
        promotions_formset = PromotionFormSet(request.POST, queryset=promotions_queryset, prefix="promos")
        if promotions_formset.is_valid():
            promotions_formset.save()
            messages.success(request, "Promo terjadwal berhasil diperbarui.")
            return redirect("referensi:pricing_management")
        messages.error(request, "Perubahan promo belum tersimpan. Periksa data yang dimasukkan.")
    else:
        plans_formset = PlanFormSet(queryset=plans_queryset, prefix="plans")
        promotions_formset = PromotionFormSet(queryset=promotions_queryset, prefix="promos")

    promotion_schedule_rows = _build_promotion_schedule_rows(promotions_queryset)

    context = {
        "plans_formset": plans_formset,
        "promotions_formset": promotions_formset,
        "promotion_schedule_rows": promotion_schedule_rows,
        "schedule_summary": {
            "total": len(promotion_schedule_rows),
            "active": sum(1 for row in promotion_schedule_rows if row["status_code"] == "active"),
            "upcoming": sum(1 for row in promotion_schedule_rows if row["status_code"] == "upcoming"),
            "ended": sum(1 for row in promotion_schedule_rows if row["status_code"] == "ended"),
            "inactive": sum(1 for row in promotion_schedule_rows if row["status_code"] == "inactive"),
        },
        "schedule_now": timezone.localtime(timezone.now()),
    }
    return render(request, "referensi/pricing_management.html", context)


def _build_promotion_schedule_rows(promotions_queryset):
    rows = []
    now = timezone.now()

    for promo in promotions_queryset.order_by("start_at", "-priority", "-created_at"):
        if not promo.is_active:
            status_code = "inactive"
            status_label = "Nonaktif"
            status_badge = "secondary"
        elif now < promo.start_at:
            status_code = "upcoming"
            status_label = "Akan Datang"
            status_badge = "info"
        elif promo.start_at <= now < promo.end_at:
            status_code = "active"
            status_label = "Aktif"
            status_badge = "success"
        else:
            status_code = "ended"
            status_label = "Berakhir"
            status_badge = "dark"

        preview = resolve_effective_plan_pricing(
            plan=promo.plan,
            now=promo.start_at,
            promotion=promo,
        )

        rows.append(
            {
                "promotion": promo,
                "status_code": status_code,
                "status_label": status_label,
                "status_badge": status_badge,
                "base_price_display": format_currency_idr(preview.base_price),
                "final_price_display": format_currency_idr(preview.final_price),
                "discount_amount_display": format_currency_idr(preview.discount_amount),
                "discount_badge": preview.discount_badge,
            }
        )

    return rows


def _build_redirect_url(tab, tab_filters, extra_params=None):
    base_url = reverse("referensi:ahsp_database")
    params = {
        "tab": tab,
        **tab_filters,
    }
    if extra_params:
        params.update(extra_params)
    return f"{base_url}?{urlencode(params)}"
