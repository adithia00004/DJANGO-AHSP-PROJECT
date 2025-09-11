# referensi/views_api.py
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Q
from .models import AHSPReferensi

@login_required
@require_GET
def api_search_ahsp(request):
    """
    Response format kompatibel Select2:
    {"results": [{"id": int, "text": "KODE — NAMA"}, ...]}
    """
    q = (request.GET.get('q') or '').strip()
    qs = AHSPReferensi.objects.all()
    if q:
        qs = qs.filter(Q(kode_ahsp__icontains=q) | Q(nama_ahsp__icontains=q))
    qs = qs.order_by('kode_ahsp')[:30]
    results = [{"id": o.id, "text": f"{o.kode_ahsp} — {o.nama_ahsp}"} for o in qs]
    return JsonResponse({"results": results})
