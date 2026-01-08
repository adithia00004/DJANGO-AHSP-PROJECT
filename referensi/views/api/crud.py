"""
AHSP Database CRUD API endpoints.

Provides REST-like endpoints for:
- Paginated listing of AHSP jobs and items
- Single-field PATCH updates for inline editing
- Bulk operations

Performance-optimized for large datasets (2000+ AHSP, 14000+ items).
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from referensi.models import AHSPReferensi, RincianReferensi

logger = logging.getLogger(__name__)

# Default pagination settings
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _parse_int(value, default=1):
    """Safely parse integer from request parameter."""
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


@login_required
@permission_required("referensi.view_ahspreferensi", raise_exception=True)
@require_GET
def api_list_jobs(request):
    """
    List AHSP jobs with pagination, search, and filtering.
    
    Query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search in kode_ahsp, nama_ahsp
    - sumber: Filter by sumber
    - klasifikasi: Filter by klasifikasi
    - sort: Sort field (default: kode_ahsp)
    - order: Sort order 'asc' or 'desc' (default: asc)
    - anomaly_only: Show only rows with anomalies (1/0)
    """
    # Pagination params
    page = _parse_int(request.GET.get('page'), 1)
    page_size = min(_parse_int(request.GET.get('page_size'), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
    
    # Search & filter params
    search = request.GET.get('search', '').strip()
    sumber = request.GET.get('sumber', '').strip()
    klasifikasi = request.GET.get('klasifikasi', '').strip()
    anomaly_only = request.GET.get('anomaly_only') == '1'
    
    # Sort params
    sort_field = request.GET.get('sort', 'kode_ahsp')
    sort_order = request.GET.get('order', 'asc')
    
    # Valid sort fields
    valid_sorts = ['kode_ahsp', 'nama_ahsp', 'klasifikasi', 'sub_klasifikasi', 'satuan', 'sumber', 'source_file']
    if sort_field not in valid_sorts:
        sort_field = 'kode_ahsp'
    
    # Build queryset with annotations for rincian counts
    queryset = AHSPReferensi.objects.annotate(
        rincian_count=Count('rincian'),
        tk_count=Count('rincian', filter=Q(rincian__kategori='TK')),
        bhn_count=Count('rincian', filter=Q(rincian__kategori='BHN')),
        alt_count=Count('rincian', filter=Q(rincian__kategori='ALT')),
        lain_count=Count('rincian', filter=Q(rincian__kategori='LAIN')),
    )
    
    # Apply search filter
    if search:
        queryset = queryset.filter(
            Q(kode_ahsp__icontains=search) |
            Q(nama_ahsp__icontains=search) |
            Q(klasifikasi__icontains=search)
        )
    
    # Apply sumber filter
    if sumber:
        queryset = queryset.filter(sumber=sumber)
    
    # Apply klasifikasi filter
    if klasifikasi:
        queryset = queryset.filter(klasifikasi=klasifikasi)
    
    # Apply anomaly filter (items with no rincian or empty fields)
    if anomaly_only:
        queryset = queryset.filter(
            Q(rincian_count=0) |
            Q(satuan__isnull=True) | Q(satuan='') |
            Q(klasifikasi__isnull=True) | Q(klasifikasi='')
        )
    
    # Apply sorting
    order_prefix = '-' if sort_order == 'desc' else ''
    queryset = queryset.order_by(f'{order_prefix}{sort_field}')
    
    # Get total before pagination
    total_count = queryset.count()
    
    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    # Build response data
    items = []
    for job in page_obj:
        # Detect anomalies
        anomalies = []
        if job.rincian_count == 0:
            anomalies.append("Tidak ada rincian")
        if not job.satuan:
            anomalies.append("Satuan kosong")
        if not job.klasifikasi:
            anomalies.append("Klasifikasi kosong")
        
        items.append({
            'id': job.id,
            'kode_ahsp': job.kode_ahsp,
            'nama_ahsp': job.nama_ahsp or '',
            'klasifikasi': job.klasifikasi or '',
            'sub_klasifikasi': job.sub_klasifikasi or '',
            'satuan': job.satuan or '',
            'sumber': job.sumber or '',
            'source_file': job.source_file or '',
            'rincian_count': job.rincian_count,
            'tk_count': job.tk_count,
            'bhn_count': job.bhn_count,
            'alt_count': job.alt_count,
            'lain_count': job.lain_count,
            'anomalies': anomalies,
            'has_anomaly': len(anomalies) > 0,
        })
    
    return JsonResponse({
        'status': 'success',
        'data': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_prev': page_obj.has_previous(),
        }
    })


@login_required
@permission_required("referensi.change_ahspreferensi", raise_exception=True)
@require_http_methods(["PATCH"])
def api_update_job(request, pk):
    """
    Update a single field of an AHSP job.
    
    Request body (JSON):
    {
        "field": "field_name",
        "value": "new_value"
    }
    """
    try:
        job = AHSPReferensi.objects.get(pk=pk)
    except AHSPReferensi.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'AHSP tidak ditemukan'
        }, status=404)
    
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value', '')
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    
    # Allowed fields for update
    allowed_fields = ['kode_ahsp', 'nama_ahsp', 'klasifikasi', 'sub_klasifikasi', 'satuan', 'sumber', 'source_file']
    
    if field not in allowed_fields:
        return JsonResponse({
            'status': 'error',
            'message': f'Field "{field}" tidak dapat diubah'
        }, status=400)
    
    # Validate required fields
    if field == 'kode_ahsp' and not value.strip():
        return JsonResponse({
            'status': 'error',
            'message': 'Kode AHSP tidak boleh kosong'
        }, status=400)
    
    # Update the field
    old_value = getattr(job, field)
    setattr(job, field, value.strip() if isinstance(value, str) else value)
    
    try:
        job.save(update_fields=[field])
        logger.info(f"AHSP {pk} updated: {field} = {value} (was: {old_value})")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Berhasil disimpan',
            'data': {
                'id': job.id,
                'field': field,
                'value': getattr(job, field),
                'old_value': old_value,
            }
        })
    except Exception as e:
        logger.error(f"Failed to update AHSP {pk}: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@permission_required("referensi.view_rincianreferensi", raise_exception=True)
@require_GET
def api_list_items(request):
    """
    List Rincian items with pagination, search, and filtering.
    
    Query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search in kode_item, uraian_item
    - job_id: Filter by AHSP job ID
    - kategori: Filter by kategori (TK, BHN, ALT, LAIN)
    - sort: Sort field (default: ahsp__kode_ahsp)
    - order: Sort order 'asc' or 'desc' (default: asc)
    """
    # Pagination params
    page = _parse_int(request.GET.get('page'), 1)
    page_size = min(_parse_int(request.GET.get('page_size'), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
    
    # Search & filter params
    search = request.GET.get('search', '').strip()
    job_id = request.GET.get('job_id', '').strip()
    kategori = request.GET.get('kategori', '').strip()
    
    # Sort params
    sort_field = request.GET.get('sort', 'ahsp__kode_ahsp')
    sort_order = request.GET.get('order', 'asc')
    
    # Build queryset with select_related for performance
    queryset = RincianReferensi.objects.select_related('ahsp')
    
    # Apply search filter
    if search:
        queryset = queryset.filter(
            Q(kode_item__icontains=search) |
            Q(uraian_item__icontains=search) |
            Q(ahsp__kode_ahsp__icontains=search)
        )
    
    # Apply job_id filter
    if job_id:
        try:
            queryset = queryset.filter(ahsp_id=int(job_id))
        except ValueError:
            pass
    
    # Apply kategori filter
    if kategori and kategori in ['TK', 'BHN', 'ALT', 'LAIN']:
        queryset = queryset.filter(kategori=kategori)
    
    # Valid sort fields
    valid_sorts = ['ahsp__kode_ahsp', 'kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien']
    if sort_field not in valid_sorts:
        sort_field = 'ahsp__kode_ahsp'
    
    # Apply sorting
    order_prefix = '-' if sort_order == 'desc' else ''
    queryset = queryset.order_by(f'{order_prefix}{sort_field}', 'kategori', 'kode_item')
    
    # Get total before pagination
    total_count = queryset.count()
    
    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    # Build response data
    items = []
    for item in page_obj:
        # Detect anomalies
        anomalies = []
        if not item.koefisien or item.koefisien == 0:
            anomalies.append("Koefisien 0")
        if not item.satuan_item:
            anomalies.append("Satuan kosong")
        
        items.append({
            'id': item.id,
            'job_id': item.ahsp_id,
            'job_kode': item.ahsp.kode_ahsp,
            'job_nama': item.ahsp.nama_ahsp or '',
            'kategori': item.kategori,
            'kode_item': item.kode_item or '',
            'uraian_item': item.uraian_item or '',
            'satuan_item': item.satuan_item or '',
            'koefisien': str(item.koefisien) if item.koefisien else '0',
            'anomalies': anomalies,
            'has_anomaly': len(anomalies) > 0,
        })
    
    return JsonResponse({
        'status': 'success',
        'data': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_prev': page_obj.has_previous(),
        }
    })


@login_required
@permission_required("referensi.change_rincianreferensi", raise_exception=True)
@require_http_methods(["PATCH"])
def api_update_item(request, pk):
    """
    Update a single field of a Rincian item.
    
    Request body (JSON):
    {
        "field": "field_name",
        "value": "new_value"
    }
    """
    try:
        item = RincianReferensi.objects.get(pk=pk)
    except RincianReferensi.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Rincian tidak ditemukan'
        }, status=404)
    
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value', '')
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    
    # Allowed fields for update
    allowed_fields = ['kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien']
    
    if field not in allowed_fields:
        return JsonResponse({
            'status': 'error',
            'message': f'Field "{field}" tidak dapat diubah'
        }, status=400)
    
    # Validate kategori
    if field == 'kategori' and value not in ['TK', 'BHN', 'ALT', 'LAIN']:
        return JsonResponse({
            'status': 'error',
            'message': 'Kategori harus TK, BHN, ALT, atau LAIN'
        }, status=400)
    
    # Validate koefisien
    if field == 'koefisien':
        try:
            value = Decimal(str(value).replace(',', '.'))
        except InvalidOperation:
            return JsonResponse({
                'status': 'error',
                'message': 'Koefisien harus berupa angka'
            }, status=400)
    
    # Update the field
    old_value = getattr(item, field)
    setattr(item, field, value.strip() if isinstance(value, str) else value)
    
    try:
        item.save(update_fields=[field])
        logger.info(f"Rincian {pk} updated: {field} = {value} (was: {old_value})")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Berhasil disimpan',
            'data': {
                'id': item.id,
                'field': field,
                'value': str(getattr(item, field)),
                'old_value': str(old_value) if old_value else '',
            }
        })
    except Exception as e:
        logger.error(f"Failed to update Rincian {pk}: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@permission_required("referensi.view_ahspreferensi", raise_exception=True)
@require_GET
def api_get_stats(request):
    """
    Get summary statistics for the database.
    Used for stats header display.
    """
    jobs_count = AHSPReferensi.objects.count()
    items_count = RincianReferensi.objects.count()
    
    # Count anomalies (jobs without rincian)
    jobs_no_rincian = AHSPReferensi.objects.annotate(
        rincian_count=Count('rincian')
    ).filter(rincian_count=0).count()
    
    # Get unique sources
    sources = list(AHSPReferensi.objects.values_list('sumber', flat=True).distinct())
    
    # Get unique klasifikasi
    klasifikasi = list(AHSPReferensi.objects.values_list('klasifikasi', flat=True).distinct())
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'jobs_count': jobs_count,
            'items_count': items_count,
            'anomaly_count': jobs_no_rincian,
            'sources': [s for s in sources if s],
            'klasifikasi': [k for k in klasifikasi if k],
        }
    })
