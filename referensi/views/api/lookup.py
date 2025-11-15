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


@login_required
@require_GET
def api_search_ahsp(request):
    """Return AHSP search results in Select2 JSON format."""

    # Response schema: {"results": [{"id": int, "text": "KODE - NAMA"}, ...]}
    query = (request.GET.get("q") or "").strip()
    queryset = AHSPReferensi.objects.all()
    if query:
        queryset = queryset.filter(
            Q(kode_ahsp__icontains=query) | Q(nama_ahsp__icontains=query)
        )
    if _should_use_cache():
        data = get_cached_search_data()
        if query:
            lowered = query.lower()
            data = [item for item in data if lowered in item["normalized"]]
        results = [
            {"id": item["id"], "text": item["text"]}
            for item in data[:SEARCH_LIMIT]
        ]
    else:
        queryset = queryset.order_by("kode_ahsp").values("id", "kode_ahsp", "nama_ahsp")[:SEARCH_LIMIT]
        results = [{"id": obj["id"], "text": f"{obj['kode_ahsp']} - {obj['nama_ahsp']}"} for obj in queryset]
    return JsonResponse({"results": results})


def _should_use_cache() -> bool:
    if _SEARCH_CACHE["version"] is None:
        return True
    total, _ = _SEARCH_CACHE["version"]
    return total <= 1000


def _get_cache_version():
    aggregates = AHSPReferensi.objects.aggregate(total=models.Count("id"), max_id=models.Max("id"))
    return (aggregates.get("total") or 0, aggregates.get("max_id") or 0)


def _should_use_cache() -> bool:
    total, _ = _get_cache_version()
    return total <= 1000
