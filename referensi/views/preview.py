"""
Preview import views.

PHASE 2 REFACTORING:
- Extracted business logic to PreviewImportService
- View now only handles request/response
- Reduced from 550 lines to ~200 lines (64% reduction)
"""

import pickle
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from django.core.exceptions import ValidationError

from referensi.forms import AHSPPreviewUploadForm
from referensi.services.ahsp_parser import (
    get_column_schema,
    load_preview_from_file,
)
from referensi.services.audit_logger import audit_logger
from referensi.services.import_writer import write_parse_result_to_db
from referensi.services.item_code_registry import assign_item_codes
from referensi.services.preview_service import PreviewImportService
from referensi.validators import validate_ahsp_file

from .constants import TAB_ITEMS, TAB_JOBS

# Limits
MAX_PREVIEW_JOBS = 1000
MAX_PREVIEW_DETAILS = 20000


def _render_messages_html(request, messages_list=None) -> str:
    """Render messages as HTML for AJAX responses."""
    if messages_list is None:
        messages_list = messages.get_messages(request)
    return render_to_string(
        "referensi/partials/ajax_messages.html",
        {"messages": messages_list},
        request=request,
    )


def _get_page(request, param: str, default: int = 1) -> int:
    """Extract page number from request."""
    candidate = request.POST.get(param) if request.method == "POST" else None
    if candidate is None:
        candidate = request.GET.get(param)
    try:
        value = int(candidate)
        return value if value >= 1 else default
    except (TypeError, ValueError):
        return default


@login_required
@permission_required(
    ("referensi.view_ahspreferensi", "referensi.import_ahsp_data"),
    raise_exception=True,
)
def preview_import(request):
    """
    Handle AHSP preview import workflow.

    PHASE 2: Refactored to use PreviewImportService.
    View now only handles request/response logic.
    """
    # Request parameters
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get(
        "format"
    )
    section = request.GET.get("section") or request.POST.get("section") or ""
    jobs_page = _get_page(request, "jobs_page", 1)
    details_page = _get_page(request, "details_page", 1)

    # Get search queries from request
    search_jobs_query = request.GET.get("search_jobs", "").strip()
    search_details_query = request.GET.get("search_details", "").strip()

    # Initialize service with search queries
    service = PreviewImportService(
        search_queries={
            "jobs": search_jobs_query,
            "details": search_details_query
        }
    )

    # Upload form
    form = AHSPPreviewUploadForm(request.POST or None, request.FILES or None)
    excel_field = getattr(form, "fields", {}).get("excel_file")
    if excel_field:
        widget = excel_field.widget
        attrs = dict(getattr(widget, "attrs", {}))
        attrs.setdefault("class", "form-control form-control-sm")
        attrs.setdefault("accept", ".xlsx,.xls")
        widget.attrs = attrs

    # Initialize state
    parse_result = None
    uploaded_name = None
    import_token = None
    job_page_data = None
    detail_page_data = None

    action = request.POST.get("action") if request.method == "POST" else ""

    # Handle update actions (edit jobs/details)
    if request.method == "POST" and action in {"update_jobs", "update_details"}:
        try:
            parse_result, uploaded_name, import_token = service.session_manager.retrieve(
                request.session
            )
        except (FileNotFoundError, pickle.UnpicklingError):
            messages.error(request, "Data preview tidak ditemukan. Unggah ulang file Excel.")
            if is_ajax and section in {TAB_JOBS, TAB_ITEMS}:
                return JsonResponse(
                    {"html": "", "messages_html": _render_messages_html(request)},
                    status=400,
                )
            return redirect("referensi:preview_import")

        if action == "update_jobs":
            # Build formset with POST data
            job_page_data = service.build_job_page(parse_result, jobs_page, data=request.POST)

            if job_page_data.formset.is_valid():
                # Apply changes
                service.apply_job_updates(parse_result, job_page_data.formset.cleaned_data)
                service.session_manager.rewrite(request.session, parse_result)
                messages.success(request, "Perubahan pekerjaan berhasil disimpan pada preview.")

                if not is_ajax:
                    query = urlencode({
                        "jobs_page": job_page_data.page_info.page,
                        "details_page": details_page,
                    })
                    return redirect(f"{reverse('referensi:preview_import')}?{query}#pane-ahsp")

                # Rebuild formset for display
                job_page_data = service.build_job_page(parse_result, jobs_page)
            else:
                messages.error(
                    request,
                    "Beberapa entri pekerjaan tidak valid. Periksa pesan kesalahan pada tabel.",
                )

        else:  # update_details
            # Build formset with POST data
            detail_page_data = service.build_detail_page(
                parse_result, details_page, data=request.POST
            )

            if detail_page_data.formset.is_valid():
                # Apply changes
                service.apply_detail_updates(
                    parse_result, detail_page_data.formset.cleaned_data
                )
                service.session_manager.rewrite(request.session, parse_result)
                messages.success(request, "Perubahan rincian berhasil disimpan pada preview.")

                if not is_ajax:
                    query = urlencode({
                        "jobs_page": jobs_page,
                        "details_page": detail_page_data.page_info.page,
                    })
                    return redirect(
                        f"{reverse('referensi:preview_import')}?{query}#pane-rincian"
                    )

                # Rebuild formset for display
                detail_page_data = service.build_detail_page(parse_result, details_page)
            else:
                messages.error(
                    request,
                    "Beberapa rincian tidak valid. Periksa pesan kesalahan pada tabel.",
                )

    # Handle file upload
    elif request.method == "POST":
        if form.is_valid():
            excel_file = form.cleaned_data["excel_file"]
            uploaded_name = excel_file.name
            file_size = getattr(excel_file, "size", None)

            # Validate file security before processing
            try:
                validate_ahsp_file(excel_file)

                # Log successful validation
                audit_logger.log_file_validation(
                    request=request,
                    filename=uploaded_name,
                    success=True,
                    file_size=file_size
                )

            except ValidationError as e:
                service.session_manager.cleanup(request.session)

                # Log validation failure
                error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
                reason = '; '.join(error_messages)

                # Check for malicious content indicators
                is_malicious = any(
                    keyword in reason.lower()
                    for keyword in ['zip bomb', 'formula berbahaya', 'malicious', 'dangerous']
                )

                if is_malicious:
                    # Log as malicious file detection
                    threat_type = 'unknown'
                    if 'zip bomb' in reason.lower():
                        threat_type = 'zip_bomb'
                    elif 'formula' in reason.lower():
                        threat_type = 'dangerous_formula'

                    audit_logger.log_malicious_file_detected(
                        request=request,
                        filename=uploaded_name,
                        threat_type=threat_type,
                        reason=reason,
                        file_size=file_size
                    )
                else:
                    # Log as normal validation failure
                    audit_logger.log_file_validation(
                        request=request,
                        filename=uploaded_name,
                        success=False,
                        file_size=file_size,
                        reason=reason
                    )

                # Display all validation errors
                for error_message in error_messages:
                    messages.error(request, error_message)
                # Skip further processing
                parse_result = None
            else:
                # File is valid, proceed with parsing
                parse_result = load_preview_from_file(excel_file)

                if parse_result.errors:
                    service.session_manager.cleanup(request.session)
                    for error in parse_result.errors:
                        messages.error(request, error)
                else:
                    assign_item_codes(parse_result)
                    service.session_manager.cleanup(request.session)
                    import_token = service.session_manager.store(
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
            service.session_manager.cleanup(request.session)

    # Load from session (GET request or after upload)
    else:
        try:
            parse_result, uploaded_name, import_token = service.session_manager.retrieve(
                request.session
            )
        except (FileNotFoundError, pickle.UnpicklingError):
            parse_result = None
            uploaded_name = None
            import_token = None

    # Build formsets if not already built
    if job_page_data is None:
        job_page_data = service.build_job_page(parse_result, jobs_page)

    if detail_page_data is None:
        detail_page_data = service.build_detail_page(parse_result, details_page)

    # Handle AJAX requests
    if is_ajax and section in {TAB_JOBS, TAB_ITEMS}:
        if section == TAB_JOBS:
            template_name = "referensi/preview/_jobs_table.html"
            partial_context = {
                "parse_result": parse_result,
                "job_formset": job_page_data.formset,
                "job_rows": job_page_data.rows,
                "job_page_info": {
                    "page": job_page_data.page_info.page,
                    "total_pages": job_page_data.page_info.total_pages,
                    "total_items": job_page_data.page_info.total_items,
                    "start_index": job_page_data.page_info.start_index,
                    "end_index": job_page_data.page_info.end_index,
                },
                "details_page": details_page,
            }
        else:
            template_name = "referensi/preview/_details_table.html"
            partial_context = {
                "parse_result": parse_result,
                "detail_formset": detail_page_data.formset,
                "detail_rows": detail_page_data.rows,
                "detail_page_info": {
                    "page": detail_page_data.page_info.page,
                    "total_pages": detail_page_data.page_info.total_pages,
                    "total_items": detail_page_data.page_info.total_items,
                    "start_index": detail_page_data.page_info.start_index,
                    "end_index": detail_page_data.page_info.end_index,
                },
                "jobs_page": jobs_page,
            }

        html = render_to_string(template_name, partial_context, request=request)
        return JsonResponse(
            {"html": html, "messages_html": _render_messages_html(request)},
            status=200,
        )

    # Render full page
    context = {
        "form": form,
        "parse_result": parse_result,
        "uploaded_name": uploaded_name,
        "import_token": import_token,
        "column_schema": get_column_schema(),
        "job_formset": job_page_data.formset,
        "detail_formset": detail_page_data.formset,
        "job_rows": job_page_data.rows,
        "detail_rows": detail_page_data.rows,
        "job_page_info": {
            "page": job_page_data.page_info.page,
            "total_pages": job_page_data.page_info.total_pages,
            "total_items": job_page_data.page_info.total_items,
            "start_index": job_page_data.page_info.start_index,
            "end_index": job_page_data.page_info.end_index,
        },
        "detail_page_info": {
            "page": detail_page_data.page_info.page,
            "total_pages": detail_page_data.page_info.total_pages,
            "total_items": detail_page_data.page_info.total_items,
            "start_index": detail_page_data.page_info.start_index,
            "end_index": detail_page_data.page_info.end_index,
        },
        "jobs_page": jobs_page,
        "details_page": details_page,
    }
    return render(request, "referensi/preview_import.html", context)


@login_required
@permission_required("referensi.import_ahsp_data", raise_exception=True)
def commit_import(request):
    """
    Commit preview data to database.

    PHASE 2: Refactored to use PreviewImportService.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    service = PreviewImportService()

    # Retrieve from session
    try:
        parse_result, uploaded_name, token = service.session_manager.retrieve(request.session)
    except FileNotFoundError:
        messages.error(request, "Tidak ada data preview yang siap diimpor.")
        return redirect("referensi:preview_import")
    except pickle.UnpicklingError:
        service.session_manager.cleanup(request.session)
        messages.error(request, "Data preview korup. Silakan unggah ulang file Excel.")
        return redirect("referensi:preview_import")

    # Verify token
    submitted_token = request.POST.get("token") or ""
    if submitted_token != token:
        messages.error(request, "Token konfirmasi tidak valid atau sudah kedaluwarsa.")
        return redirect("referensi:preview_import")

    # Assign item codes
    assign_item_codes(parse_result)

    # Write to database
    try:
        summary = write_parse_result_to_db(parse_result, uploaded_name)

        # Log successful import operation
        audit_logger.log_import_operation(
            request=request,
            filename=uploaded_name,
            jobs_count=summary.jobs_created + summary.jobs_updated,
            details_count=summary.rincian_written,
            jobs_created=summary.jobs_created,
            jobs_updated=summary.jobs_updated,
            detail_errors=len(summary.detail_errors) if summary.detail_errors else 0
        )

    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("referensi:preview_import")

    # Cleanup session
    service.session_manager.cleanup(request.session)

    # Success message
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
