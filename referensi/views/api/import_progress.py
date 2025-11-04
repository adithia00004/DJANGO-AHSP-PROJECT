"""
API endpoints for import progress tracking
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from referensi.services.chunked_import import ChunkedImportService


@login_required
@require_http_methods(["GET"])
def get_import_progress(request):
    """
    Get current import progress for the user's session

    Returns JSON:
    {
        "stage": "writing_jobs|writing_details|complete",
        "current": 150,
        "total": 1000,
        "percent": 15.0,
        "details": "Batch 2/10: 100 pekerjaan",
        "timestamp": 1234567890.123
    }
    """
    service = ChunkedImportService()
    session_key = request.session.session_key

    if not session_key:
        return JsonResponse({
            "error": "No active session"
        }, status=400)

    progress = service.get_progress(session_key)

    if not progress:
        return JsonResponse({
            "stage": "idle",
            "current": 0,
            "total": 0,
            "percent": 0,
            "details": "",
            "timestamp": None
        })

    return JsonResponse(progress)


@login_required
@require_http_methods(["POST"])
def clear_import_progress(request):
    """Clear import progress from cache"""
    service = ChunkedImportService()
    session_key = request.session.session_key

    if session_key:
        service.clear_progress(session_key)

    return JsonResponse({"success": True})
