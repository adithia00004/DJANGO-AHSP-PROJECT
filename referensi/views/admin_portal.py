"""Admin portal and database maintenance views."""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse

from referensi.forms import AHSPReferensiInlineForm, RincianReferensiInlineForm
from referensi.models import AHSPReferensi, RincianReferensi
from referensi.permissions import has_referensi_portal_access
from referensi.services.admin_service import AdminPortalService

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


def _build_redirect_url(tab, tab_filters, extra_params=None):
    base_url = reverse("referensi:ahsp_database")
    params = {
        "tab": tab,
        **tab_filters,
    }
    if extra_params:
        params.update(extra_params)
    return f"{base_url}?{urlencode(params)}"
