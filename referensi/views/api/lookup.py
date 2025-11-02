from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from referensi.models import AHSPReferensi

# PHASE 1: Use centralized config from settings
REFERENSI_CONFIG = getattr(settings, 'REFERENSI_CONFIG', {})
SEARCH_LIMIT = REFERENSI_CONFIG.get('api', {}).get('search_limit', 30)


@login_required
@require_GET
def api_search_ahsp(request):
    """
    Response format kompatibel Select2:
    {"results": [{"id": int, "text": "KODE – NAMA"}, ...]}
    """
    query = (request.GET.get("q") or "").strip()
    queryset = AHSPReferensi.objects.all()
    if query:
        queryset = queryset.filter(
            Q(kode_ahsp__icontains=query) | Q(nama_ahsp__icontains=query)
        )
    queryset = queryset.order_by("kode_ahsp")[:SEARCH_LIMIT]
    results = [
        {"id": obj.id, "text": f"{obj.kode_ahsp} – {obj.nama_ahsp}"} for obj in queryset
    ]
    return JsonResponse({"results": results})
