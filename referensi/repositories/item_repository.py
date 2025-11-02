"""Repository helpers for Rincian (item) referensi data access."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from referensi.models import RincianReferensi


class ItemRepository:
    """Encapsulate common item-rincian ORM queries."""

    @staticmethod
    def base_queryset() -> QuerySet:
        """Base queryset with select_related to AHSP."""
        return RincianReferensi.objects.select_related("ahsp")

    @staticmethod
    def filter_by_search(queryset: QuerySet, keyword: str) -> QuerySet:
        """Filter item queryset by search keyword."""
        if not keyword:
            return queryset
        return queryset.filter(
            Q(ahsp__kode_ahsp__icontains=keyword)
            | Q(kode_item__icontains=keyword)
            | Q(uraian_item__icontains=keyword)
        )

    @staticmethod
    def filter_by_category(queryset: QuerySet, kategori: str | None) -> QuerySet:
        """Filter item queryset by kategori."""
        if kategori:
            return queryset.filter(kategori=kategori)
        return queryset

    @staticmethod
    def filter_by_job(queryset: QuerySet, job_id: int | None) -> QuerySet:
        """Filter item queryset by parent AHSP id."""
        if job_id:
            return queryset.filter(ahsp_id=job_id)
        return queryset
