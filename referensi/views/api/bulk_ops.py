"""
API endpoints for bulk operations on referensi database.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from referensi.services.admin_service import AdminPortalService

logger = logging.getLogger(__name__)


@login_required
@permission_required("referensi.delete_ahspreferensi", raise_exception=True)
@require_GET
def api_delete_preview(request):
    """
    Preview what will be deleted based on sumber/source_file filters.

    GET params:
        - sumber: Filter by sumber field
        - source_file: Filter by source_file field

    Returns:
        JSON with preview data
    """
    sumber = (request.GET.get("sumber") or "").strip()
    source_file = (request.GET.get("source_file") or "").strip()

    if not sumber and not source_file:
        return JsonResponse({
            "error": "Minimal satu filter (sumber atau source_file) harus diisi"
        }, status=400)

    service = AdminPortalService(job_limit=1000, item_limit=5000)

    try:
        preview = service.get_delete_preview(
            sumber=sumber,
            source_file=source_file
        )
        return JsonResponse({
            "success": True,
            "preview": preview
        })
    except Exception as e:
        logger.exception("Error in delete preview")
        return JsonResponse({
            "error": str(e)
        }, status=500)


@login_required
@permission_required("referensi.delete_ahspreferensi", raise_exception=True)
@require_POST
def api_bulk_delete(request):
    """
    Execute bulk delete based on sumber/source_file filters.

    POST body (JSON):
        - sumber: Filter by sumber field
        - source_file: Filter by source_file field
        - confirm: Must be true

    Returns:
        JSON with delete summary
    """
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JsonResponse({
            "error": "Invalid JSON"
        }, status=400)

    sumber = (data.get("sumber") or "").strip()
    source_file = (data.get("source_file") or "").strip()
    confirm = data.get("confirm", False)

    if not confirm:
        return JsonResponse({
            "error": "Konfirmasi diperlukan untuk menghapus data"
        }, status=400)

    if not sumber and not source_file:
        return JsonResponse({
            "error": "Minimal satu filter (sumber atau source_file) harus diisi"
        }, status=400)

    service = AdminPortalService(job_limit=1000, item_limit=5000)

    try:
        result = service.bulk_delete_by_source(
            sumber=sumber,
            source_file=source_file
        )

        # Add success message to session
        messages.success(
            request,
            f"Berhasil menghapus {result['jobs_deleted']} pekerjaan "
            f"dan {result['rincian_deleted']} rincian."
        )

        return JsonResponse({
            "success": True,
            "result": result
        })
    except ValueError as e:
        logger.warning(f"Validation error in bulk delete: {e}")
        return JsonResponse({
            "error": str(e)
        }, status=400)
    except Exception as e:
        logger.exception("Unexpected error in bulk delete")
        return JsonResponse({
            "error": f"Terjadi kesalahan: {str(e)}"
        }, status=500)
