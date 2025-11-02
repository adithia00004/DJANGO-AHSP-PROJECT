from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from referensi.models import AHSPReferensi


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
    queryset = queryset.order_by("kode_ahsp")[:30]
    results = [
        {"id": obj.id, "text": f"{obj.kode_ahsp} – {obj.nama_ahsp}"} for obj in queryset
    ]
    return JsonResponse({"results": results})
