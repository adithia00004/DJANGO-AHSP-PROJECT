from __future__ import annotations

from django.db import models

from referensi.models import AHSPReferensi

_SEARCH_CACHE = {"version": None, "data": []}


def rebuild_search_cache():
    aggregates = AHSPReferensi.objects.aggregate(
        total=models.Count("id"),
        max_id=models.Max("id"),
    )
    data = list(
        AHSPReferensi.objects.values("id", "kode_ahsp", "nama_ahsp").order_by("kode_ahsp")
    )
    _SEARCH_CACHE["data"] = [
        {
            "id": item["id"],
            "text": f"{item['kode_ahsp']} - {item['nama_ahsp']}",
            "normalized": f"{item['kode_ahsp']} {item['nama_ahsp']}".lower(),
        }
        for item in data
    ]
    _SEARCH_CACHE["version"] = (
        aggregates.get("total") or 0,
        aggregates.get("max_id") or 0,
    )


def invalidate_search_cache():
    _SEARCH_CACHE["version"] = None


def get_cached_search_data():
    if _SEARCH_CACHE["version"] is None:
        rebuild_search_cache()
    return _SEARCH_CACHE["data"]
