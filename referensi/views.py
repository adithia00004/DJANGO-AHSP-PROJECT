import os
import pickle
import secrets
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render

from .forms import AHSPPreviewUploadForm
from .services.ahsp_parser import ParseResult, load_preview_from_file
from .services.import_writer import write_parse_result_to_db


PENDING_IMPORT_SESSION_KEY = "referensi_pending_import"


@login_required
def admin_portal(request):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

    return render(request, "referensi/admin_portal.html")


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
