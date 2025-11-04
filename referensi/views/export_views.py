"""
Export views for AHSP data.

PHASE 6: Export System

Provides views for:
- Excel export (single, multiple, search results)
- PDF export (single, multiple, search results)
- Async export for large datasets
"""

from __future__ import annotations

import logging
from typing import Optional

from django.http import HttpResponse, JsonResponse, HttpRequest
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from referensi.models import AHSPReferensi
from referensi.services.export_service import excel_export_service
from referensi.services.pdf_export_service import pdf_export_service
from referensi.services.ahsp_repository import ahsp_repository

logger = logging.getLogger(__name__)


class ExportSingleJobView(LoginRequiredMixin, View):
    """Export single AHSP job."""

    def get(self, request: HttpRequest, pk: int, format: str = 'excel'):
        """
        Export single AHSP job.

        URL params:
            pk: AHSP primary key
            format: 'excel' or 'pdf'

        Query params:
            include_rincian: '1' or '0' (default: '1')
        """
        ahsp = get_object_or_404(AHSPReferensi, pk=pk)
        include_rincian = request.GET.get('include_rincian', '1') == '1'

        try:
            if format == 'excel':
                # Export to Excel
                output = excel_export_service.export_single_job(
                    ahsp,
                    include_rincian=include_rincian
                )

                filename = f"AHSP_{ahsp.kode_ahsp.replace('/', '_')}.xlsx"
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

            elif format == 'pdf':
                # Export to PDF
                output = pdf_export_service.export_single_job(
                    ahsp,
                    include_rincian=include_rincian
                )

                filename = f"AHSP_{ahsp.kode_ahsp.replace('/', '_')}.pdf"
                response = HttpResponse(
                    output.read(),
                    content_type='application/pdf'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

            else:
                return JsonResponse({'error': 'Invalid format'}, status=400)

            logger.info(f"User {request.user} exported AHSP {ahsp.kode_ahsp} as {format}")
            return response

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)


class ExportMultipleJobsView(LoginRequiredMixin, View):
    """Export multiple AHSP jobs."""

    def post(self, request: HttpRequest, format: str = 'excel'):
        """
        Export multiple AHSP jobs.

        POST data:
            job_ids: List of AHSP IDs (comma-separated or JSON array)
            include_rincian: '1' or '0' (default: '0')
            columns: Custom columns (optional, comma-separated)
        """
        import json

        # Get job IDs
        job_ids_raw = request.POST.get('job_ids', '')

        try:
            # Try parsing as JSON
            job_ids = json.loads(job_ids_raw)
        except (json.JSONDecodeError, TypeError):
            # Fallback to comma-separated
            job_ids = [int(id.strip()) for id in job_ids_raw.split(',') if id.strip()]

        if not job_ids:
            return JsonResponse({'error': 'No jobs selected'}, status=400)

        include_rincian = request.POST.get('include_rincian', '0') == '1'
        columns_raw = request.POST.get('columns', '')
        columns = [c.strip() for c in columns_raw.split(',') if c.strip()] if columns_raw else None

        # Get jobs
        jobs = AHSPReferensi.objects.filter(pk__in=job_ids)

        if not jobs.exists():
            return JsonResponse({'error': 'No jobs found'}, status=404)

        try:
            if format == 'excel':
                # Export to Excel
                output = excel_export_service.export_multiple_jobs(
                    jobs,
                    include_rincian=include_rincian,
                    columns=columns
                )

                filename = f"AHSP_Export_{len(job_ids)}_jobs.xlsx"
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

            elif format == 'pdf':
                # Export to PDF
                output = pdf_export_service.export_multiple_jobs(
                    jobs,
                    title=f"Daftar AHSP ({len(job_ids)} Pekerjaan)"
                )

                filename = f"AHSP_Export_{len(job_ids)}_jobs.pdf"
                response = HttpResponse(
                    output.read(),
                    content_type='application/pdf'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

            else:
                return JsonResponse({'error': 'Invalid format'}, status=400)

            logger.info(f"User {request.user} exported {len(job_ids)} AHSP jobs as {format}")
            return response

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)


class ExportSearchResultsView(LoginRequiredMixin, View):
    """Export search results."""

    def get(self, request: HttpRequest, format: str = 'excel'):
        """
        Export search results.

        Query params:
            q: Search query (required)
            sumber: Filter by sumber (optional)
            klasifikasi: Filter by klasifikasi (optional)
            limit: Max results (default: 1000)
        """
        query = request.GET.get('q', '')

        if not query:
            return JsonResponse({'error': 'Search query required'}, status=400)

        # Get filters
        sumber = request.GET.get('sumber', '')
        klasifikasi = request.GET.get('klasifikasi', '')
        limit = int(request.GET.get('limit', 1000))

        # Perform search
        results = ahsp_repository.search_ahsp(
            query,
            sumber=sumber if sumber else None,
            klasifikasi=klasifikasi if klasifikasi else None,
            limit=limit
        )

        # Convert to list if cached
        if not hasattr(results, 'count'):
            results = list(results)

        if not results:
            return JsonResponse({'error': 'No results found'}, status=404)

        # Prepare filters for export
        filters = {}
        if sumber:
            filters['sumber'] = sumber
        if klasifikasi:
            filters['klasifikasi'] = klasifikasi

        try:
            if format == 'excel':
                # Export to Excel
                output = excel_export_service.export_search_results(
                    results,
                    query,
                    filters=filters
                )

                filename = f"AHSP_Search_{query[:20].replace(' ', '_')}.xlsx"
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

            elif format == 'pdf':
                # Export to PDF
                output = pdf_export_service.export_search_results(
                    results,
                    query,
                    filters=filters
                )

                filename = f"AHSP_Search_{query[:20].replace(' ', '_')}.pdf"
                response = HttpResponse(
                    output.read(),
                    content_type='application/pdf'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

            else:
                return JsonResponse({'error': 'Invalid format'}, status=400)

            result_count = len(results) if isinstance(results, list) else results.count()
            logger.info(f"User {request.user} exported search results for '{query}' ({result_count} results) as {format}")
            return response

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)


class ExportAsyncView(LoginRequiredMixin, View):
    """Queue async export for large datasets."""

    def post(self, request: HttpRequest):
        """
        Queue async export task.

        POST data:
            export_type: 'search' or 'multiple'
            format: 'excel' or 'pdf'
            ... (parameters depend on export_type)

        Returns:
            JSON with task_id for status checking
        """
        from referensi.tasks import async_export_task

        export_type = request.POST.get('export_type', '')
        format = request.POST.get('format', 'excel')

        if export_type not in ['search', 'multiple']:
            return JsonResponse({'error': 'Invalid export_type'}, status=400)

        if format not in ['excel', 'pdf']:
            return JsonResponse({'error': 'Invalid format'}, status=400)

        # Prepare task parameters
        params = {
            'export_type': export_type,
            'format': format,
            'user_id': request.user.id,
        }

        if export_type == 'search':
            params['query'] = request.POST.get('q', '')
            params['sumber'] = request.POST.get('sumber', '')
            params['klasifikasi'] = request.POST.get('klasifikasi', '')
            params['limit'] = int(request.POST.get('limit', 10000))

        elif export_type == 'multiple':
            import json
            job_ids_raw = request.POST.get('job_ids', '')
            try:
                job_ids = json.loads(job_ids_raw)
            except (json.JSONDecodeError, TypeError):
                job_ids = [int(id.strip()) for id in job_ids_raw.split(',') if id.strip()]

            params['job_ids'] = job_ids
            params['include_rincian'] = request.POST.get('include_rincian', '0') == '1'

        # Queue task
        try:
            result = async_export_task.delay(**params)

            return JsonResponse({
                'status': 'queued',
                'task_id': result.id,
                'message': 'Export task queued. You will receive an email when it\'s ready.'
            })

        except Exception as e:
            logger.error(f"Failed to queue export task: {e}")
            return JsonResponse({'error': str(e)}, status=500)


# Export task status check
@require_http_methods(["GET"])
def export_task_status(request: HttpRequest, task_id: str):
    """
    Check export task status.

    Returns:
        JSON with task status and download URL when ready
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    response_data = {
        'task_id': task_id,
        'status': result.status,
    }

    if result.ready():
        if result.successful():
            response_data['result'] = result.result
            response_data['download_url'] = f'/referensi/export/download/{task_id}/'
        else:
            response_data['error'] = str(result.result)

    return JsonResponse(response_data)
