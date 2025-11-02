"""Utility untuk menulis hasil parse AHSP ke database."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from django.db import transaction

from referensi.models import AHSPReferensi, RincianReferensi
from .import_utils import canonicalize_kategori
from .item_code_registry import assign_item_codes, persist_item_codes


@dataclass
class ImportSummary:
    """Ringkasan hasil impor AHSP."""

    jobs_created: int = 0
    jobs_updated: int = 0
    rincian_written: int = 0
    detail_errors: list[str] = field(default_factory=list)


def _log(stdout, message: str) -> None:
    if stdout is None:
        return
    stdout.write(f"{message}\n")


def write_parse_result_to_db(parse_result, source_file: str | None = None, *, stdout=None) -> ImportSummary:
    """Persisten ParseResult ke database.

    PHASE 1 OPTIMIZATION:
    - Increased batch_size from 500 to 1000 (optimal for RincianReferensi with 6 fields)
    - Collect all rincian across jobs before bulk insert (reduces DB round-trips)
    - Better error handling and logging
    """

    from referensi.services.ahsp_parser import ParseResult  # menghindari import siklik

    if not isinstance(parse_result, ParseResult):
        raise TypeError("parse_result harus instance ParseResult")

    summary = ImportSummary()

    if parse_result.errors:
        raise ValueError("ParseResult mengandung error, tidak bisa diimpor.")

    if source_file:
        source_file = os.path.basename(source_file)

    assign_item_codes(parse_result)

    with transaction.atomic():
        persist_item_codes(parse_result)

        # PHASE 1: Collect all rincian first, then bulk insert once
        all_rincian_to_delete = []
        all_pending_details = []

        # First pass: Create/update AHSP and collect rincian
        for job in parse_result.jobs:
            defaults = {
                "nama_ahsp": job.nama_ahsp,
                "satuan": job.satuan or "",
                "klasifikasi": job.klasifikasi or "",
                "sub_klasifikasi": job.sub_klasifikasi or "",
                "source_file": source_file,
            }
            ahsp_obj, created = AHSPReferensi.objects.get_or_create(
                sumber=job.sumber,
                kode_ahsp=job.kode_ahsp,
                defaults=defaults,
            )

            if created:
                summary.jobs_created += 1
            else:
                updated_fields: list[str] = []
                if ahsp_obj.nama_ahsp != job.nama_ahsp:
                    ahsp_obj.nama_ahsp = job.nama_ahsp
                    updated_fields.append("nama_ahsp")
                if job.klasifikasi is not None and ahsp_obj.klasifikasi != job.klasifikasi:
                    ahsp_obj.klasifikasi = job.klasifikasi or ""
                    updated_fields.append("klasifikasi")
                if (
                    job.sub_klasifikasi is not None
                    and ahsp_obj.sub_klasifikasi != job.sub_klasifikasi
                ):
                    ahsp_obj.sub_klasifikasi = job.sub_klasifikasi or ""
                    updated_fields.append("sub_klasifikasi")
                if job.satuan is not None and ahsp_obj.satuan != job.satuan:
                    ahsp_obj.satuan = job.satuan or ""
                    updated_fields.append("satuan")
                if source_file and ahsp_obj.source_file != source_file:
                    ahsp_obj.source_file = source_file
                    updated_fields.append("source_file")
                if updated_fields:
                    ahsp_obj.save(update_fields=updated_fields)
                summary.jobs_updated += 1

            _log(stdout, f"[job] {job.sumber} :: {job.kode_ahsp} - {job.nama_ahsp}")

            # Mark for deletion
            all_rincian_to_delete.append(ahsp_obj.id)

            # Prepare rincian instances
            for detail in job.rincian:
                try:
                    kategori = canonicalize_kategori(detail.kategori or detail.kategori_source)
                    fields = dict(
                        ahsp=ahsp_obj,
                        kategori=kategori,
                        kode_item=detail.kode_item,
                        uraian_item=detail.uraian_item,
                        satuan_item=detail.satuan_item,
                        koefisien=detail.koefisien,
                    )
                    all_pending_details.append((RincianReferensi(**fields), detail.row_number))
                except Exception as exc:  # pragma: no cover - validasi runtime
                    message = f"[!] Gagal menyiapkan rincian baris {detail.row_number}: {exc}"
                    summary.detail_errors.append(message)
                    _log(stdout, message)

        # PHASE 1: Bulk delete all old rincian in one query
        if all_rincian_to_delete:
            deleted_count = RincianReferensi.objects.filter(
                ahsp_id__in=all_rincian_to_delete
            ).delete()[0]
            _log(stdout, f"[bulk] Deleted {deleted_count} old rincian records")

        # PHASE 1: Bulk insert all new rincian with optimal batch size
        if all_pending_details:
            instances = [instance for instance, _ in all_pending_details]
            try:
                # PHASE 1: Increased batch_size from 500 to 1000
                # RincianReferensi has 6 fields → optimal batch ~1000-2000
                RincianReferensi.objects.bulk_create(instances, batch_size=1000)
                summary.rincian_written = len(instances)
                _log(stdout, f"[bulk] Inserted {len(instances)} rincian records")
            except Exception as exc:  # pragma: no cover - DB specific failure
                fallback_msg = (
                    f"[!] Bulk create failed: {exc}. Trying individual inserts..."
                )
                summary.detail_errors.append(fallback_msg)
                _log(stdout, fallback_msg)

                # Fallback to individual inserts
                for instance, row_number in all_pending_details:
                    try:
                        instance.save(force_insert=True)
                        summary.rincian_written += 1
                    except Exception as inner_exc:  # pragma: no cover - DB specific
                        message = f"[!] Gagal import rincian baris {row_number}: {inner_exc}"
                        summary.detail_errors.append(message)
                        _log(stdout, message)

    # PHASE 3 DAY 3: Refresh materialized view after import
    _refresh_materialized_view(stdout)

    return summary


def _refresh_materialized_view(stdout=None) -> None:
    """
    Refresh AHSP statistics materialized view after data changes.

    PHASE 3 DAY 3: Auto-refresh materialized view for instant stats.
    """
    from django.db import connection

    _log(stdout, "\n[Materialized View] Refreshing AHSP statistics...")

    try:
        import time
        start_time = time.time()

        with connection.cursor() as cursor:
            # Use standard refresh (faster, but locks view briefly)
            cursor.execute("REFRESH MATERIALIZED VIEW referensi_ahsp_stats")

        elapsed_ms = (time.time() - start_time) * 1000
        _log(stdout, f"[Materialized View] Refreshed in {elapsed_ms:.2f}ms")
    except Exception as exc:  # pragma: no cover - DB specific
        _log(stdout, f"[!] Failed to refresh materialized view: {exc}")


__all__ = [
    "ImportSummary",
    "write_parse_result_to_db",
]
