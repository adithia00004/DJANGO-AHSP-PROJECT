"""Preview import views and helpers."""

import os
import pickle
import secrets
import tempfile
from math import ceil
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.forms import formset_factory
from django.urls import reverse

from referensi.forms import (
    AHSPPreviewUploadForm,
    PreviewDetailForm,
    PreviewJobForm,
)
from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.ahsp_parser import (
    ParseResult,
    get_column_schema,
    load_preview_from_file,
)
from referensi.services.import_writer import write_parse_result_to_db
from referensi.services.item_code_registry import assign_item_codes

from .constants import PENDING_IMPORT_SESSION_KEY, TAB_ITEMS, TAB_JOBS


PreviewJobFormSet = formset_factory(PreviewJobForm, extra=0)
PreviewDetailFormSet = formset_factory(PreviewDetailForm, extra=0)

JOB_PAGE_SIZE = 50
DETAIL_PAGE_SIZE = 100
MAX_PREVIEW_JOBS = 1000
MAX_PREVIEW_DETAILS = 20000


def _paginate(total: int, page: int, per_page: int) -> tuple[int, int, int, int]:
    if total <= 0:
        return 0, 0, 1, 1

    total_pages = max(1, ceil(total / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = min(start + per_page, total)
    return start, end, page, total_pages


def _build_job_page(parse_result: ParseResult, page: int, *, data=None):
    jobs = parse_result.jobs if parse_result else []
    total = len(jobs)
    start, end, page, total_pages = _paginate(total, page, JOB_PAGE_SIZE)

    initial: list[dict] = []
    rows_meta: list[dict] = []
    for job_index in range(start, end):
        job = jobs[job_index]
        initial.append(
            {
                "job_index": job_index,
                "sumber": job.sumber,
                "kode_ahsp": job.kode_ahsp,
                "nama_ahsp": job.nama_ahsp,
                "klasifikasi": job.klasifikasi or "",
                "sub_klasifikasi": job.sub_klasifikasi or "",
                "satuan": job.satuan or "",
            }
        )
        rows_meta.append({"job": job, "job_index": job_index})

    if data is not None:
        formset = PreviewJobFormSet(data, prefix="jobs", initial=initial)
    else:
        formset = PreviewJobFormSet(prefix="jobs", initial=initial)

    rows: list[dict] = []
    for meta, form in zip(rows_meta, formset.forms):
        rows.append({"job": meta["job"], "form": form, "job_index": meta["job_index"]})

    page_info = {
        "page": page,
        "total_pages": total_pages,
        "total_items": total,
        "start_index": (start + 1) if total else 0,
        "end_index": end,
    }
    return formset, rows, page_info


def _build_detail_page(parse_result: ParseResult, page: int, *, data=None):
    jobs = parse_result.jobs if parse_result else []
    total = parse_result.total_rincian if parse_result else 0
    start, end, page, total_pages = _paginate(total, page, DETAIL_PAGE_SIZE)

    initial: list[dict] = []
    rows_meta: list[dict] = []

    if total:
        flat_index = 0
        for job_index, job in enumerate(jobs):
            for detail_index, detail in enumerate(job.rincian):
                if flat_index >= end:
                    break
                if flat_index >= start:
                    initial.append(
                        {
                            "job_index": job_index,
                            "detail_index": detail_index,
                            "kategori": detail.kategori,
                            "kode_item": detail.kode_item,
                            "uraian_item": detail.uraian_item,
                            "satuan_item": detail.satuan_item,
                            "koefisien": detail.koefisien,
                        }
                    )
                    rows_meta.append(
                        {
                            "detail": detail,
                            "job": job,
                            "job_index": job_index,
                        }
                    )
                flat_index += 1
                if flat_index >= end:
                    break

    if data is not None:
        formset = PreviewDetailFormSet(data, prefix="details", initial=initial)
    else:
        formset = PreviewDetailFormSet(prefix="details", initial=initial)

    rows: list[dict] = []
    for meta, form in zip(rows_meta, formset.forms):
        rows.append(
            {
                "detail": meta["detail"],
                "job": meta["job"],
                "form": form,
                "job_index": meta["job_index"],
            }
        )

    page_info = {
        "page": page,
        "total_pages": total_pages,
        "total_items": total,
        "start_index": (start + 1) if total else 0,
        "end_index": min(end, total),
    }
    return formset, rows, page_info


def _render_messages_html(request, messages_list=None) -> str:
    if messages_list is None:
        messages_list = messages.get_messages(request)
    return render_to_string(
        "referensi/partials/ajax_messages.html",
        {"messages": messages_list},
        request=request,
    )


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


def _rewrite_pending_import(session, parse_result: ParseResult) -> str:
    data = session.get(PENDING_IMPORT_SESSION_KEY)
    if not data:
        raise FileNotFoundError("Pending import tidak ditemukan")

    parse_path = data.get("parse_path")
    if not parse_path:
        raise FileNotFoundError("Path preview kosong")

    with open(parse_path, "wb") as handle:
        pickle.dump(parse_result, handle, protocol=pickle.HIGHEST_PROTOCOL)

    session.modified = True
    return data.get("token", "")


@login_required
def preview_import(request):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get(
        "format"
    )
    section = request.GET.get("section") or request.POST.get("section") or ""

    def _get_page(param: str, default: int = 1) -> int:
        if request.method == "POST":
            candidate = request.POST.get(param)
        else:
            candidate = None
        if candidate is None:
            candidate = request.GET.get(param)
        try:
            value = int(candidate)
            if value < 1:
                return default
            return value
        except (TypeError, ValueError):
            return default

    jobs_page = _get_page("jobs_page", 1)
    details_page = _get_page("details_page", 1)

    form = AHSPPreviewUploadForm(request.POST or None, request.FILES or None)
    excel_field = getattr(form, "fields", {}).get("excel_file")
    if excel_field:
        widget = excel_field.widget
        attrs = dict(getattr(widget, "attrs", {}))
        attrs.setdefault("class", "form-control form-control-sm")
        attrs.setdefault("accept", ".xlsx,.xls")
        widget.attrs = attrs

    parse_result: ParseResult | None = None
    uploaded_name: str | None = None
    import_token: str | None = None
    job_formset = None
    detail_formset = None
    job_rows: list[dict] = []
    detail_rows: list[dict] = []
    job_page_info = {
        "page": jobs_page,
        "total_pages": 1,
        "total_items": 0,
        "start_index": 0,
        "end_index": 0,
    }
    detail_page_info = {
        "page": details_page,
        "total_pages": 1,
        "total_items": 0,
        "start_index": 0,
        "end_index": 0,
    }

    pending = request.session.get(PENDING_IMPORT_SESSION_KEY)
    action = request.POST.get("action") if request.method == "POST" else ""

    if request.method == "POST" and action in {"update_jobs", "update_details"}:
        if not pending:
            messages.error(request, "Tidak ada data preview yang siap diedit.")
            if is_ajax and section in {TAB_JOBS, TAB_ITEMS}:
                return JsonResponse(
                    {"html": "", "messages_html": _render_messages_html(request)},
                    status=400,
                )
            return redirect("referensi:preview_import")

        try:
            parse_result, uploaded_name, import_token = _load_pending_result(pending)
        except Exception:
            _cleanup_pending_import(request.session)
            messages.error(request, "Data preview tidak ditemukan. Unggah ulang file Excel.")
            if is_ajax and section in {TAB_JOBS, TAB_ITEMS}:
                return JsonResponse(
                    {"html": "", "messages_html": _render_messages_html(request)},
                    status=400,
                )
            return redirect("referensi:preview_import")

        if action == "update_jobs":
            job_formset, job_rows, job_page_info = _build_job_page(
                parse_result, jobs_page, data=request.POST
            )
            if job_formset.is_valid():
                for cleaned in job_formset.cleaned_data:
                    if not cleaned:
                        continue
                    job_index = cleaned["job_index"]
                    if job_index >= len(parse_result.jobs):
                        continue
                    job = parse_result.jobs[job_index]
                    job.sumber = cleaned["sumber"]
                    job.kode_ahsp = cleaned["kode_ahsp"]
                    job.nama_ahsp = cleaned["nama_ahsp"]
                    job.klasifikasi = cleaned.get("klasifikasi") or ""
                    job.sub_klasifikasi = cleaned.get("sub_klasifikasi") or ""
                    job.satuan = cleaned.get("satuan") or ""

                assign_item_codes(parse_result)
                _rewrite_pending_import(request.session, parse_result)
                messages.success(
                    request, "Perubahan pekerjaan berhasil disimpan pada preview."
                )

                if not is_ajax:
                    query = urlencode({
                        "jobs_page": job_page_info["page"],
                        "details_page": details_page,
                    })
                    return redirect(f"{reverse('referensi:preview_import')}?{query}#pane-ahsp")

                job_formset, job_rows, job_page_info = _build_job_page(
                    parse_result, jobs_page
                )
            else:
                messages.error(
                    request,
                    "Beberapa entri pekerjaan tidak valid. Periksa pesan kesalahan pada tabel.",
                )
        else:
            detail_formset, detail_rows, detail_page_info = _build_detail_page(
                parse_result, details_page, data=request.POST
            )
            if detail_formset.is_valid():
                for cleaned in detail_formset.cleaned_data:
                    if not cleaned:
                        continue
                    job_index = cleaned["job_index"]
                    detail_index = cleaned["detail_index"]
                    if job_index >= len(parse_result.jobs):
                        continue
                    job = parse_result.jobs[job_index]
                    if detail_index >= len(job.rincian):
                        continue
                    detail = job.rincian[detail_index]
                    detail.kategori = cleaned["kategori"]
                    kode_item = cleaned.get("kode_item") or ""
                    detail.kode_item = kode_item
                    detail.kode_item_source = "manual" if kode_item else "missing"
                    detail.uraian_item = cleaned["uraian_item"]
                    detail.satuan_item = cleaned["satuan_item"]
                    detail.koefisien = cleaned["koefisien"]

                assign_item_codes(parse_result)
                _rewrite_pending_import(request.session, parse_result)
                messages.success(
                    request, "Perubahan rincian berhasil disimpan pada preview."
                )

                if not is_ajax:
                    query = urlencode({
                        "jobs_page": jobs_page,
                        "details_page": detail_page_info["page"],
                    })
                    return redirect(
                        f"{reverse('referensi:preview_import')}?{query}#pane-rincian"
                    )

                detail_formset, detail_rows, detail_page_info = _build_detail_page(
                    parse_result, details_page
                )
            else:
                messages.error(
                    request,
                    "Beberapa rincian tidak valid. Periksa pesan kesalahan pada tabel.",
                )
    elif request.method == "POST":
        if form.is_valid():
            excel_file = form.cleaned_data["excel_file"]
            uploaded_name = excel_file.name
            parse_result = load_preview_from_file(excel_file)

            if parse_result.errors:
                _cleanup_pending_import(request.session)
                for error in parse_result.errors:
                    messages.error(request, error)
            else:
                assign_item_codes(parse_result)
                _cleanup_pending_import(request.session)
                import_token = _store_pending_import(
                    request.session, parse_result, uploaded_name
                )
                jobs_page = 1
                details_page = 1
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
        if pending:
            try:
                parse_result, uploaded_name, import_token = _load_pending_result(pending)
            except Exception:
                _cleanup_pending_import(request.session)
                parse_result = None
                uploaded_name = None
                import_token = None

    if parse_result and job_formset is None:
        job_formset, job_rows, job_page_info = _build_job_page(parse_result, jobs_page)
    elif job_formset is None:
        job_formset, job_rows, job_page_info = _build_job_page(None, jobs_page)

    if parse_result and detail_formset is None:
        detail_formset, detail_rows, detail_page_info = _build_detail_page(
            parse_result, details_page
        )
    elif detail_formset is None:
        detail_formset, detail_rows, detail_page_info = _build_detail_page(None, details_page)

    if is_ajax and section in {TAB_JOBS, TAB_ITEMS}:
        if section == TAB_JOBS:
            template_name = "referensi/preview/_jobs_table.html"
            partial_context = {
                "parse_result": parse_result,
                "job_formset": job_formset,
                "job_rows": job_rows,
                "job_page_info": job_page_info,
                "details_page": details_page,
            }
        else:
            template_name = "referensi/preview/_details_table.html"
            partial_context = {
                "parse_result": parse_result,
                "detail_formset": detail_formset,
                "detail_rows": detail_rows,
                "detail_page_info": detail_page_info,
                "jobs_page": jobs_page,
            }

        html = render_to_string(template_name, partial_context, request=request)
        return JsonResponse(
            {"html": html, "messages_html": _render_messages_html(request)},
            status=200,
        )

    context = {
        "form": form,
        "parse_result": parse_result,
        "uploaded_name": uploaded_name,
        "import_token": import_token,
        "column_schema": get_column_schema(),
        "job_formset": job_formset,
        "detail_formset": detail_formset,
        "job_rows": job_rows,
        "detail_rows": detail_rows,
        "job_page_info": job_page_info,
        "detail_page_info": detail_page_info,
        "jobs_page": jobs_page,
        "details_page": details_page,
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

    assign_item_codes(parse_result)

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
