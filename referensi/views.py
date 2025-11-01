import os
import pickle
import secrets
import tempfile
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.forms import modelformset_factory
from django.urls import reverse

from .forms import (
    AHSPPreviewUploadForm,
    AHSPReferensiInlineForm,
    RincianReferensiInlineForm,
)
from .models import AHSPReferensi, RincianReferensi
from .services.ahsp_parser import (
    ParseResult,
    get_column_schema,
    load_preview_from_file,
)
from .services.import_writer import write_parse_result_to_db


PENDING_IMPORT_SESSION_KEY = "referensi_pending_import"
TAB_JOBS = "jobs"
TAB_ITEMS = "items"
JOB_DISPLAY_LIMIT = 150
ITEM_DISPLAY_LIMIT = 150


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
    return {
        "search": (data.get("job_q") or "").strip(),
        "sumber": (data.get("job_sumber") or "").strip(),
        "klasifikasi": (data.get("job_klasifikasi") or "").strip(),
        "kategori": (data.get("job_kategori") or "").strip(),
        "anomali": (data.get("job_anomali") or "") == "1",
    }


def _apply_job_filters(queryset, filters):
    search_query = filters.get("search")
    if search_query:
        queryset = queryset.filter(
            Q(kode_ahsp__icontains=search_query)
            | Q(nama_ahsp__icontains=search_query)
            | Q(sub_klasifikasi__icontains=search_query)
        )

    sumber_filter = filters.get("sumber")
    if sumber_filter:
        queryset = queryset.filter(sumber=sumber_filter)

    klasifikasi_filter = filters.get("klasifikasi")
    if klasifikasi_filter:
        queryset = queryset.filter(klasifikasi=klasifikasi_filter)

    kategori_filter = filters.get("kategori")
    if kategori_filter:
        queryset = queryset.filter(rincian__kategori=kategori_filter)

    if filters.get("anomali"):
        queryset = queryset.filter(
            Q(rincian_total=0)
            | Q(zero_coef_count__gt=0)
            | Q(missing_unit_count__gt=0)
            | Q(satuan__isnull=True)
            | Q(satuan="")
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
        params["job_anomali"] = "1"
    return params


def _build_job_rows(formset):
    rows = []
    anomaly_count = 0
    for form in formset.forms:
        job = form.instance
        anomaly_reasons = _job_anomalies(job)
        if anomaly_reasons:
            anomaly_count += 1
        rows.append(
            {
                "form": form,
                "object": job,
                "category_counts": {
                    "TK": getattr(job, "tk_count", 0),
                    "BHN": getattr(job, "bhn_count", 0),
                    "ALT": getattr(job, "alt_count", 0),
                    "LAIN": getattr(job, "lain_count", 0),
                },
                "anomaly_reasons": anomaly_reasons,
            }
        )
    return rows, anomaly_count


def _job_anomalies(job):
    reasons = []
    if getattr(job, "rincian_total", 0) == 0:
        reasons.append("Tidak memiliki rincian")
    if getattr(job, "zero_coef_count", 0):
        reasons.append("Koefisien bernilai 0")
    if getattr(job, "missing_unit_count", 0):
        reasons.append("Rincian tanpa satuan")
    if not (job.satuan or ""):
        reasons.append("Satuan pekerjaan kosong")
    return reasons


def _parse_item_filters(data):
    job_value = (data.get("item_job") or "").strip()
    try:
        job_id = int(job_value)
    except (TypeError, ValueError):
        job_id = None
    return {
        "search": (data.get("item_q") or "").strip(),
        "kategori": (data.get("item_kategori") or "").strip(),
        "job_id": job_id,
        "job_value": job_value,
    }


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
    if filters.get("job_id"):
        params["item_job"] = str(filters["job_id"])
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


def _cleanup_pending_import(session) -> None:
    data = session.pop(PENDING_IMPORT_SESSION_KEY, None)
    if not data:
        return
    path = data.get("parse_path")
    if path:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    session.modified = True


def _store_pending_import(session, parse_result: ParseResult, uploaded_name: str) -> str:
    token = secrets.token_urlsafe(16)
    fd, tmp_path = tempfile.mkstemp(prefix="ahsp_preview_", suffix=".pkl")
    try:
        with os.fdopen(fd, "wb") as handle:
            pickle.dump(parse_result, handle, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        os.remove(tmp_path)
        raise

    session[PENDING_IMPORT_SESSION_KEY] = {
        "parse_path": tmp_path,
        "uploaded_name": uploaded_name,
        "token": token,
    }
    session.modified = True
    return token


def _load_pending_result(data) -> tuple[ParseResult, str, str]:
    parse_path = data.get("parse_path")
    if not parse_path:
        raise FileNotFoundError("Parse path missing")

    with open(parse_path, "rb") as handle:
        parse_result: ParseResult = pickle.load(handle)

    uploaded_name = data.get("uploaded_name") or ""
    token = data.get("token") or ""
    return parse_result, uploaded_name, token


@login_required
def preview_import(request):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

    form = AHSPPreviewUploadForm(request.POST or None, request.FILES or None)
    parse_result: ParseResult | None = None
    uploaded_name: str | None = None
    import_token: str | None = None

    if request.method == "POST":
        if form.is_valid():
            excel_file = form.cleaned_data["excel_file"]
            uploaded_name = excel_file.name
            parse_result = load_preview_from_file(excel_file)

            if parse_result.errors:
                _cleanup_pending_import(request.session)
                for error in parse_result.errors:
                    messages.error(request, error)
            else:
                _cleanup_pending_import(request.session)
                import_token = _store_pending_import(
                    request.session, parse_result, uploaded_name
                )
                messages.success(
                    request,
                    (
                        f"Berhasil membaca {parse_result.total_jobs} pekerjaan "
                        f"dengan {parse_result.total_rincian} rincian."
                    ),
                )
                for warning in parse_result.warnings:
                    messages.warning(request, warning)
        else:
            _cleanup_pending_import(request.session)
    else:
        pending = request.session.get(PENDING_IMPORT_SESSION_KEY)
        if pending:
            try:
                parse_result, uploaded_name, import_token = _load_pending_result(pending)
            except Exception:
                _cleanup_pending_import(request.session)
                parse_result = None
                uploaded_name = None
                import_token = None

    context = {
        "form": form,
        "parse_result": parse_result,
        "uploaded_name": uploaded_name,
        "import_token": import_token,
        "column_schema": get_column_schema(),
    }
    return render(request, "referensi/preview_import.html", context)


@login_required
def commit_import(request):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    pending = request.session.get(PENDING_IMPORT_SESSION_KEY)
    if not pending:
        messages.error(request, "Tidak ada data preview yang siap diimpor.")
        return redirect("referensi:preview_import")

    submitted_token = request.POST.get("token") or ""
    if submitted_token != pending.get("token"):
        messages.error(request, "Token konfirmasi tidak valid atau sudah kedaluwarsa.")
        return redirect("referensi:preview_import")

    try:
        parse_result, uploaded_name, _ = _load_pending_result(pending)
    except FileNotFoundError:
        _cleanup_pending_import(request.session)
        messages.error(request, "Berkas preview tidak ditemukan. Ulangi proses upload.")
        return redirect("referensi:preview_import")
    except pickle.UnpicklingError:
        _cleanup_pending_import(request.session)
        messages.error(request, "Data preview korup. Silakan unggah ulang file Excel.")
        return redirect("referensi:preview_import")

    try:
        summary = write_parse_result_to_db(parse_result, uploaded_name)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("referensi:preview_import")

    _cleanup_pending_import(request.session)

    success_message = (
        "✅ Import selesai. "
        f"Pekerjaan baru: {summary.jobs_created}, "
        f"Pekerjaan diperbarui: {summary.jobs_updated}, "
        f"Total rincian ditulis: {summary.rincian_written}"
    )
    messages.success(request, success_message)

    for warning in parse_result.warnings:
        messages.warning(request, warning)

    for detail_error in summary.detail_errors:
        messages.warning(request, detail_error)

    return redirect("referensi:preview_import")
