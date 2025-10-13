# detail_project/views_export.py
"""
Export views for Rekap RAB
Handles CSV, PDF, and Word exports
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404


@login_required
@require_http_methods(["GET"])
def export_rekap_rab(request, project_id, format_type):
    """
    Export Rekap RAB in multiple formats
    
    Args:
        project_id: Project ID
        format_type: 'csv', 'pdf', or 'word'
    """
    # Import here to avoid circular imports
    from dashboard.models import Project
    
    # Validate format
    valid_formats = ['csv', 'pdf', 'word']
    if format_type not in valid_formats:
        return JsonResponse({
            'error': f'Invalid format. Must be one of: {", ".join(valid_formats)}'
        }, status=400)
    
    # Get project
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    
    # Placeholder response (implement later)
    return JsonResponse({
        'status': 'coming_soon',
        'message': f'Export to {format_type.upper()} will be available soon',
        'project': {
            'id': project.id,
            'name': project.nama,
        },
        'format': format_type
    }, status=501)  # 501 = Not Implemented