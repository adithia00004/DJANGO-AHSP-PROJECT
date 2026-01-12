from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from referensi.models import AHSPReferensi
from referensi.search_cache import get_cached_search_data

# PHASE 1: Use centralized config from settings
REFERENSI_CONFIG = getattr(settings, 'REFERENSI_CONFIG', {})
SEARCH_LIMIT = REFERENSI_CONFIG.get('api', {}).get('search_limit', 20)


def _get_cache_version():
    """Get current AHSP count and max ID for cache invalidation."""
    aggregates = AHSPReferensi.objects.aggregate(total=models.Count("id"), max_id=models.Max("id"))
    return (aggregates.get("total") or 0, aggregates.get("max_id") or 0)


def _should_use_cache() -> bool:
    """Use cache only for small datasets (<=1000 items)."""
    total, _ = _get_cache_version()
    return total <= 1000


@login_required
@require_GET
def api_search_ahsp(request):
    """
    Return AHSP search results in Select2 JSON format.
    
    Query parameters:
    - q: Search query (filters kode_ahsp and nama_ahsp)
    - sumber: Filter by AHSP source (e.g., 'AHSP SNI 2025')
    
    Response: {"results": [{"id": int, "text": "KODE - NAMA"}, ...]}
    """
    query = (request.GET.get("q") or "").strip()
    sumber = (request.GET.get("sumber") or "").strip()
    
    queryset = AHSPReferensi.objects.all()
    
    # Apply sumber filter first (before cache check, as cache doesn't support sumber)
    if sumber:
        queryset = queryset.filter(sumber=sumber)
    
    # Apply search filter
    if query:
        queryset = queryset.filter(
            Q(kode_ahsp__icontains=query) | Q(nama_ahsp__icontains=query)
        )
    
    # Use cache only if no sumber filter (cache doesn't include sumber info)
    if _should_use_cache() and not sumber:
        data = get_cached_search_data()
        if query:
            lowered = query.lower()
            data = [item for item in data if lowered in item["normalized"]]
        results = [
            {"id": item["id"], "text": item["text"]}
            for item in data[:SEARCH_LIMIT]
        ]
    else:
        # Direct query (with sumber filter or large dataset)
        queryset = queryset.order_by("kode_ahsp").values("id", "kode_ahsp", "nama_ahsp")[:SEARCH_LIMIT]
        results = [{"id": obj["id"], "text": f"{obj['kode_ahsp']} - {obj['nama_ahsp']}"} for obj in queryset]
    
    return JsonResponse({"results": results})


@login_required
@require_GET
def api_list_sources(request):
    """
    Return list of unique AHSP sources for dropdown selection.
    
    Response: {
        "sources": ["AHSP SNI 2026", "AHSP SNI 2025", ...],
        "default": "AHSP SNI 2026"  // newest/first source
    }
    """
    sources = list(
        AHSPReferensi.objects
        .values_list('sumber', flat=True)
        .distinct()
        .order_by('-sumber')  # Newest first (assumes year in name)
    )
    # Filter out empty sources
    sources = [s for s in sources if s]
    
    return JsonResponse({
        'sources': sources,
        'default': sources[0] if sources else None
    })
