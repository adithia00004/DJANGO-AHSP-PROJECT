"""Admin portal and database maintenance views."""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.forms import modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse

from referensi.forms import AHSPReferensiInlineForm, RincianReferensiInlineForm
from referensi.models import AHSPReferensi, RincianReferensi

from .constants import ITEM_DISPLAY_LIMIT, JOB_DISPLAY_LIMIT, TAB_ITEMS, TAB_JOBS


@login_required
def admin_portal(request):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

    return render(request, "referensi/admin_portal.html")


def _base_ahsp_queryset():
    return AHSPReferensi.objects.annotate(
        rincian_total=Count("rincian", distinct=True),
        tk_count=Count(
            "rincian",
            filter=Q(rincian__kategori=RincianReferensi.Kategori.TK),
            distinct=True,
        ),
        bhn_count=Count(
            "rincian",
            filter=Q(rincian__kategori=RincianReferensi.Kategori.BHN),
            distinct=True,
        ),
        alt_count=Count(
            "rincian",
            filter=Q(rincian__kategori=RincianReferensi.Kategori.ALT),
            distinct=True,
        ),
        lain_count=Count(
            "rincian",
            filter=Q(rincian__kategori=RincianReferensi.Kategori.LAIN),
            distinct=True,
        ),
        zero_coef_count=Count(
            "rincian",
            filter=Q(rincian__koefisien=0),
            distinct=True,
        ),
        missing_unit_count=Count(
            "rincian",
            filter=Q(rincian__satuan_item__isnull=True)
            | Q(rincian__satuan_item=""),
            distinct=True,
        ),
    )


@login_required
def ahsp_database(request):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

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
    jobs_filters = _parse_job_filters(job_filter_source)

    jobs_queryset_base = _apply_job_filters(_base_ahsp_queryset(), jobs_filters)
    total_jobs_filtered = jobs_queryset_base.count()
    jobs_queryset = jobs_queryset_base.order_by("kode_ahsp")
    jobs_truncated = total_jobs_filtered > JOB_DISPLAY_LIMIT
    if jobs_truncated:
        jobs_queryset = jobs_queryset[:JOB_DISPLAY_LIMIT]

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

    jobs_rows, jobs_anomaly_displayed = _build_job_rows(jobs_formset)

    items_filter_source = (
        request.POST
        if request.method == "POST" and active_tab == TAB_ITEMS
        else request.GET
    )
    items_filters = _parse_item_filters(items_filter_source)

    items_queryset_base = _apply_item_filters(
        RincianReferensi.objects.select_related("ahsp"),
        items_filters,
    )
    total_items_filtered = items_queryset_base.count()
    items_queryset = items_queryset_base.order_by("ahsp__kode_ahsp", "kategori", "kode_item")
    items_truncated = total_items_filtered > ITEM_DISPLAY_LIMIT
    if items_truncated:
        items_queryset = items_queryset[:ITEM_DISPLAY_LIMIT]

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

    item_rows, items_anomaly_displayed = _build_item_rows(items_formset)

    available_sources = list(
        AHSPReferensi.objects.order_by("sumber")
        .values_list("sumber", flat=True)
        .distinct()
    )
    available_klasifikasi = list(
        AHSPReferensi.objects.exclude(klasifikasi__isnull=True)
        .exclude(klasifikasi="")
        .order_by("klasifikasi")
        .values_list("klasifikasi", flat=True)
        .distinct()
    )

    job_filter_params = _job_filter_query_params(jobs_filters)
    item_filter_params = _item_filter_query_params(items_filters)

    job_choices = list(
        AHSPReferensi.objects.order_by("kode_ahsp").values_list("id", "kode_ahsp", "nama_ahsp")
    )

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
                "limit": JOB_DISPLAY_LIMIT,
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
                "limit": ITEM_DISPLAY_LIMIT,
            },
        },
        "item_filter_options": {
            "kategori": RincianReferensi.Kategori.choices,
            "jobs": job_choices,
        },
    }
    return render(request, "referensi/ahsp_database.html", context)


def _parse_job_filters(data):
    filters = {
        "search": (data.get("job_q") or "").strip(),
        "sumber": (data.get("job_sumber") or "").strip(),
        "klasifikasi": (data.get("job_klasifikasi") or "").strip(),
        "kategori": (data.get("job_kategori") or "").strip(),
        "anomali": (data.get("job_anomali") or "").strip(),
    }
    if filters["anomali"] in {"1", "true", "True", "yes", "on"}:
        filters["anomali"] = "any"
    return filters


def _apply_job_filters(queryset, filters):
    search_query = filters.get("search")
    if search_query:
        queryset = queryset.filter(
            Q(kode_ahsp__icontains=search_query)
            | Q(nama_ahsp__icontains=search_query)
        )

    sumber = filters.get("sumber")
    if sumber:
        queryset = queryset.filter(sumber=sumber)

    klasifikasi = filters.get("klasifikasi")
    if klasifikasi:
        queryset = queryset.filter(klasifikasi=klasifikasi)

    kategori = filters.get("kategori")
    if kategori:
        queryset = queryset.filter(rincian__kategori=kategori).distinct()

    anomaly = filters.get("anomali")
    if anomaly == "zero":
        queryset = queryset.filter(zero_coef_count__gt=0)
    elif anomaly == "missing_unit":
        queryset = queryset.filter(missing_unit_count__gt=0)
    elif anomaly == "any":
        queryset = queryset.filter(
            Q(zero_coef_count__gt=0) | Q(missing_unit_count__gt=0)
        )

    return queryset


def _job_filter_query_params(filters):
    params = {}
    if filters.get("search"):
        params["job_q"] = filters["search"]
    if filters.get("sumber"):
        params["job_sumber"] = filters["sumber"]
    if filters.get("klasifikasi"):
        params["job_klasifikasi"] = filters["klasifikasi"]
    if filters.get("kategori"):
        params["job_kategori"] = filters["kategori"]
    if filters.get("anomali"):
        anomaly = filters["anomali"]
        params["job_anomali"] = "1" if anomaly == "any" else anomaly
    return params


def _build_job_rows(formset):
    rows = []
    anomaly_count = 0
    for form in formset.forms:
        job = form.instance
        anomaly_reasons = _job_anomalies(job)
        if anomaly_reasons:
            anomaly_count += 1
        category_counts = {
            "TK": getattr(job, "tk_count", 0) or 0,
            "BHN": getattr(job, "bhn_count", 0) or 0,
            "ALT": getattr(job, "alt_count", 0) or 0,
            "LAIN": getattr(job, "lain_count", 0) or 0,
        }
        rows.append(
            {
                "form": form,
                "object": job,
                "anomaly_reasons": anomaly_reasons,
                "category_counts": category_counts,
            }
        )
    return rows, anomaly_count


def _job_anomalies(job: AHSPReferensi):
    reasons = []
    if job.zero_coef_count:
        reasons.append("Memiliki rincian dengan koefisien 0")
    if job.missing_unit_count:
        reasons.append("Memiliki rincian tanpa satuan")
    return reasons


def _parse_item_filters(data):
    filters = {
        "search": (data.get("item_q") or "").strip(),
        "kategori": (data.get("item_kategori") or "").strip(),
    }
    raw_job = (data.get("item_job") or "").strip()
    filters["job_value"] = raw_job
    try:
        filters["job_id"] = int(raw_job)
    except (TypeError, ValueError):
        filters["job_id"] = None
        filters["job_value"] = ""
    return filters


def _apply_item_filters(queryset, filters):
    search_query = filters.get("search")
    if search_query:
        queryset = queryset.filter(
            Q(ahsp__kode_ahsp__icontains=search_query)
            | Q(kode_item__icontains=search_query)
            | Q(uraian_item__icontains=search_query)
        )

    kategori = filters.get("kategori")
    if kategori:
        queryset = queryset.filter(kategori=kategori)

    job_id = filters.get("job_id")
    if job_id:
        queryset = queryset.filter(ahsp_id=job_id)

    return queryset


def _item_filter_query_params(filters):
    params = {}
    if filters.get("search"):
        params["item_q"] = filters["search"]
    if filters.get("kategori"):
        params["item_kategori"] = filters["kategori"]
    if filters.get("job_value"):
        params["item_job"] = filters["job_value"]
    return params


def _build_item_rows(formset):
    rows = []
    anomaly_count = 0
    for form in formset.forms:
        item = form.instance
        anomaly_reasons = _item_anomalies(item)
        if anomaly_reasons:
            anomaly_count += 1
        rows.append(
            {
                "form": form,
                "object": item,
                "job": item.ahsp,
                "anomaly_reasons": anomaly_reasons,
            }
        )
    return rows, anomaly_count


def _item_anomalies(item):
    reasons = []
    if item.koefisien == 0:
        reasons.append("Koefisien bernilai 0")
    if not (item.satuan_item or ""):
        reasons.append("Satuan item kosong")
    return reasons


def _build_redirect_url(tab, filters):
    params = {"tab": tab}
    if tab == TAB_JOBS:
        params.update(_job_filter_query_params(filters))
    else:
        params.update(_item_filter_query_params(filters))
    query = urlencode(params)
    base_url = reverse("referensi:ahsp_database")
    return f"{base_url}?{query}" if query else base_url
