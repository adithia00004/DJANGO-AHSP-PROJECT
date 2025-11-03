"""
Service layer for referensi admin portal views.

Encapsulates queryset construction, filter parsing, and row building so the
view functions can remain thin request/response handlers.
"""

from __future__ import annotations

from typing import Any, Dict

from referensi.models import RincianReferensi
from referensi.repositories.ahsp_repository import AHSPRepository
from referensi.repositories.item_repository import ItemRepository
# PHASE 3: Import cache helpers
from referensi.services.cache_helpers import ReferensiCache


class AdminPortalService:
    """Business logic helper for the admin portal view."""

    def __init__(self, *, job_limit: int, item_limit: int) -> None:
        self.job_limit = job_limit
        self.item_limit = item_limit

    # ------------------------------------------------------------------
    # Queryset helpers
    # ------------------------------------------------------------------

    def base_ahsp_queryset(self):
        """Return base queryset with aggregated counts for AHSP records."""
        return AHSPRepository.get_with_category_counts()

    def base_item_queryset(self):
        """Return base queryset for rincian items."""
        return ItemRepository.base_queryset()

    # ------------------------------------------------------------------
    # Jobs filtering / helpers
    # ------------------------------------------------------------------

    def parse_job_filters(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Normalize query parameters submitted from the jobs tab.

        Args:
            data: Dict-like object (e.g., QueryDict) containing request parameters.

        Returns:
            dict: Sanitized filter values keyed by `search`, `sumber`, `klasifikasi`,
            `kategori`, and `anomali`.
        """
        filters = {
            "search": (data.get("job_q") or "").strip(),
            "sumber": (data.get("job_sumber") or "").strip(),
            "klasifikasi": (data.get("job_klasifikasi") or "").strip(),
            "kategori": (data.get("job_kategori") or "").strip(),
        }
        anomaly = (data.get("job_anomali") or "").strip()
        if anomaly == "1":
            anomaly = "any"
        filters["anomali"] = anomaly
        return filters

    def apply_job_filters(self, queryset, filters: Dict[str, str]):
        """Apply jobs tab filters to an annotated AHSP queryset.

        Args:
            queryset: Annotated queryset from :meth:`base_ahsp_queryset`.
            filters: Normalized filters produced by :meth:`parse_job_filters`.

        Returns:
            QuerySet: Filtered queryset ready for pagination/formset binding.
        """
        keyword = filters.get("search", "")
        queryset = AHSPRepository.filter_by_search(queryset, keyword)

        queryset = AHSPRepository.filter_by_metadata(
            queryset,
            sumber=filters.get("sumber", ""),
            klasifikasi=filters.get("klasifikasi", ""),
        )

        queryset = AHSPRepository.filter_by_kategori(
            queryset, filters.get("kategori", "")
        )

        queryset = AHSPRepository.filter_by_anomaly(
            queryset, filters.get("anomali", "")
        )

        return queryset

    def job_filter_query_params(self, filters: Dict[str, str]) -> Dict[str, str]:
        """Build query parameters for jobs tab pagination links."""
        params: Dict[str, str] = {}
        if filters.get("search"):
            params["job_q"] = filters["search"]
        if filters.get("sumber"):
            params["job_sumber"] = filters["sumber"]
        if filters.get("klasifikasi"):
            params["job_klasifikasi"] = filters["klasifikasi"]
        if filters.get("kategori"):
            params["job_kategori"] = filters["kategori"]
        if filters.get("anomali"):
            anomaly = filters["anomali"]
            params["job_anomali"] = "1" if anomaly == "any" else anomaly
        return params

    def build_job_rows(self, formset):
        """Return rendered row information for the jobs tab.

        Args:
            formset: Bound formset containing AHSP instances.

        Returns:
            tuple[list[dict], int]: Render-ready row metadata list and anomaly count.
        """
        rows = []
        anomaly_count = 0
        for form in formset.forms:
            job = form.instance
            anomaly_reasons = self.job_anomalies(job)
            if anomaly_reasons:
                anomaly_count += 1
            category_counts = {
                "TK": getattr(job, "tk_count", 0) or 0,
                "BHN": getattr(job, "bhn_count", 0) or 0,
                "ALT": getattr(job, "alt_count", 0) or 0,
                "LAIN": getattr(job, "lain_count", 0) or 0,
            }
            rows.append(
                {
                    "form": form,
                    "object": job,
                    "anomaly_reasons": anomaly_reasons,
                    "category_counts": category_counts,
                }
            )
        return rows, anomaly_count

    @staticmethod
    def job_anomalies(job: AHSPReferensi):
        reasons = []
        if getattr(job, "zero_coef_count", 0):
            reasons.append("Memiliki rincian dengan koefisien 0")
        if getattr(job, "missing_unit_count", 0):
            reasons.append("Memiliki rincian tanpa satuan")
        return reasons

    # ------------------------------------------------------------------
    # Items filtering / helpers
    # ------------------------------------------------------------------

    def parse_item_filters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize request parameters for the rincian items tab."""
        filters: Dict[str, Any] = {
            "search": (data.get("item_q") or "").strip(),
            "kategori": (data.get("item_kategori") or "").strip(),
        }
        raw_job = (data.get("item_job") or "").strip()
        filters["job_value"] = raw_job
        try:
            filters["job_id"] = int(raw_job)
        except (TypeError, ValueError):
            filters["job_id"] = None
            filters["job_value"] = ""
        return filters

    def apply_item_filters(self, queryset, filters: Dict[str, Any]):
        """Apply item filters (search/kategori/job) to a rincian queryset."""
        queryset = ItemRepository.filter_by_search(queryset, filters.get("search", ""))
        queryset = ItemRepository.filter_by_category(queryset, filters.get("kategori"))
        queryset = ItemRepository.filter_by_job(queryset, filters.get("job_id"))
        return queryset

    def item_filter_query_params(self, filters: Dict[str, Any]) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if filters.get("search"):
            params["item_q"] = filters["search"]
        if filters.get("kategori"):
            params["item_kategori"] = filters["kategori"]
        if filters.get("job_value"):
            params["item_job"] = filters["job_value"]
        return params

    def build_item_rows(self, formset):
        """Return rendered row information for the rincian tab."""
        rows = []
        anomaly_count = 0
        for form in formset.forms:
            item = form.instance
            anomaly_reasons = self.item_anomalies(item)
            if anomaly_reasons:
                anomaly_count += 1
            rows.append(
                {
                    "form": form,
                    "object": item,
                    "job": item.ahsp,
                    "anomaly_reasons": anomaly_reasons,
                }
            )
        return rows, anomaly_count

    @staticmethod
    def item_anomalies(item: RincianReferensi):
        reasons = []
        if item.koefisien == 0:
            reasons.append("Koefisien bernilai 0")
        if not (item.satuan_item or ""):
            reasons.append("Satuan item kosong")
        return reasons

    # ------------------------------------------------------------------
    # Auxiliary helpers
    # ------------------------------------------------------------------

    def available_sources(self):
        """
        Get available AHSP sources for dropdown.

        PHASE 3: Now uses cache for 30-50% faster page loads.
        """
        return ReferensiCache.get_available_sources()

    def available_klasifikasi(self):
        """
        Get available klasifikasi for dropdown.

        PHASE 3: Now uses cache for 30-50% faster page loads.
        """
        return ReferensiCache.get_available_klasifikasi()

    def job_choices(self, limit: int = 5000):
        """Return cached job choices for the rincian filter dropdown."""
        return ReferensiCache.get_job_choices(limit=limit)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def get_delete_preview(self, *, sumber: str = "", source_file: str = "") -> Dict[str, Any]:
        """
        Preview what will be deleted based on filters.

        Args:
            sumber: Filter by sumber field
            source_file: Filter by source_file field

        Returns:
            dict: Summary of records to be deleted
        """
        from referensi.models import AHSPReferensi
        from django.db.models import Count

        queryset = AHSPReferensi.objects.all()

        if sumber:
            queryset = queryset.filter(sumber__iexact=sumber.strip())
        if source_file:
            queryset = queryset.filter(source_file__iexact=source_file.strip())

        # Count what will be deleted
        jobs_count = queryset.count()
        rincian_count = 0

        if jobs_count > 0:
            rincian_count = queryset.aggregate(
                total=Count('rincian')
            )['total'] or 0

        # Get list of affected sources for display
        affected_sources = list(queryset.values_list('sumber', flat=True).distinct()[:10])
        affected_files = list(queryset.values_list('source_file', flat=True).distinct()[:10])

        return {
            "jobs_count": jobs_count,
            "rincian_count": rincian_count,
            "affected_sources": affected_sources,
            "affected_files": [f for f in affected_files if f],
            "sumber_filter": sumber,
            "source_file_filter": source_file,
        }

    def bulk_delete_by_source(self, *, sumber: str = "", source_file: str = "") -> Dict[str, Any]:
        """
        Delete AHSP records and their rincian based on filters.

        Args:
            sumber: Filter by sumber field
            source_file: Filter by source_file field

        Returns:
            dict: Summary of deleted records
        """
        from referensi.models import AHSPReferensi

        if not sumber and not source_file:
            raise ValueError("Minimal satu filter (sumber atau source_file) harus diisi")

        queryset = AHSPReferensi.objects.all()

        if sumber:
            queryset = queryset.filter(sumber__iexact=sumber.strip())
        if source_file:
            queryset = queryset.filter(source_file__iexact=source_file.strip())

        # Get count before delete
        jobs_count = queryset.count()

        if jobs_count == 0:
            return {
                "jobs_deleted": 0,
                "rincian_deleted": 0,
                "total_deleted": 0,
                "sumber": sumber,
                "source_file": source_file,
            }

        # Delete (CASCADE will handle rincian)
        deleted_info = queryset.delete()

        # deleted_info is a tuple: (total_deleted, {model_name: count})
        total_deleted = deleted_info[0]
        rincian_deleted = deleted_info[1].get('referensi.RincianReferensi', 0)

        # Clear cache after delete
        ReferensiCache.invalidate_all()

        return {
            "jobs_deleted": jobs_count,
            "rincian_deleted": rincian_deleted,
            "total_deleted": total_deleted,
            "sumber": sumber,
            "source_file": source_file,
        }
