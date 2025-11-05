"""Utility untuk menulis hasil parse AHSP ke database."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from django.db import transaction

from referensi.models import AHSPReferensi, RincianReferensi
from .import_utils import canonicalize_kategori
from .item_code_registry import assign_item_codes, persist_item_codes
from .cache_service import CacheService


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


def _validate_ahsp_uniqueness(parse_result, stdout) -> None:
    """
    Validate AHSP uniqueness: (sumber, kode_ahsp, nama_ahsp) should be unique.

    PHASE 4 FIX: Warn if same (sumber, kode_ahsp) but different nama_ahsp.
    """
    seen = {}  # (sumber, kode_ahsp) -> nama_ahsp

    for job in parse_result.jobs:
        key = (job.sumber, job.kode_ahsp)
        if key in seen:
            existing_nama = seen[key]
            if existing_nama != job.nama_ahsp:
                warning = (
                    f"[!] PERINGATAN: Pekerjaan dengan sumber '{job.sumber}' "
                    f"dan kode '{job.kode_ahsp}' memiliki nama berbeda:\n"
                    f"    - Nama 1: {existing_nama}\n"
                    f"    - Nama 2: {job.nama_ahsp}\n"
                    f"    Hanya nama terakhir yang akan disimpan."
                )
                _log(stdout, warning)
        else:
            seen[key] = job.nama_ahsp


def _deduplicate_rincian(rincian_list, job, stdout):
    """
    Remove duplicate rincian within a single AHSP.

    Deduplication key: (kategori, kode_item, uraian_item, satuan_item)
    Keep the first occurrence, discard later duplicates.

    PHASE 4 FIX: Prevents unique constraint violation on bulk insert.
    """
    seen = set()
    unique = []
    duplicates = []

    for detail in rincian_list:
        # Normalize kategori for comparison
        kategori = canonicalize_kategori(detail.kategori or detail.kategori_source)
        key = (
            kategori,
            detail.kode_item,
            detail.uraian_item,
            detail.satuan_item,
        )

        if key in seen:
            duplicates.append(
                f"    Baris {detail.row_number}: {kategori} - {detail.uraian_item} ({detail.satuan_item})"
            )
        else:
            seen.add(key)
            unique.append(detail)

    if duplicates:
        warning = (
            f"[!] PERINGATAN: Duplikat rincian diabaikan untuk AHSP '{job.kode_ahsp} - {job.nama_ahsp}':\n"
            + "\n".join(duplicates)
        )
        _log(stdout, warning)

    return unique


def write_parse_result_to_db(parse_result, source_file: str | None = None, *, stdout=None) -> ImportSummary:
    """Persisten ParseResult ke database.

    PHASE 1 OPTIMIZATION:
    - Increased batch_size from 500 to 1000 (optimal for RincianReferensi with 6 fields)
    - Collect all rincian across jobs before bulk insert (reduces DB round-trips)
    - Better error handling and logging

    PHASE 4 FIX:
    - Deduplicate rincian within each AHSP before bulk insert
    - Use savepoint for graceful error recovery on bulk insert failure
    - Validate AHSP uniqueness (sumber + kode_ahsp + nama_ahsp)

    PHASE 5 FIX (Nov 2025):
    - Fixed TransactionManagementError by moving materialized view refresh inside atomic block
    - Enhanced logging for debugging import failures

    PHASE 6 FIX (Nov 2025):
    - Fixed duplicate AHSP in Excel causing IntegrityError on rincian bulk insert
    - Merge rincian from duplicate AHSP entries before processing
    """
    import logging
    logger = logging.getLogger(__name__)

    from referensi.services.ahsp_parser import ParseResult  # menghindari import siklik

    if not isinstance(parse_result, ParseResult):
        raise TypeError("parse_result harus instance ParseResult")

    summary = ImportSummary()

    if parse_result.errors:
        raise ValueError("ParseResult mengandung error, tidak bisa diimpor.")

    if source_file:
        source_file = os.path.basename(source_file)

    # Log import start
    logger.info(f"Starting import: {source_file}, Jobs: {len(parse_result.jobs)}, Total rincian: {parse_result.total_rincian}")
    _log(stdout, f"[START] Import file: {source_file}")
    _log(stdout, f"[INFO] Total jobs to import: {len(parse_result.jobs)}")
    _log(stdout, f"[INFO] Total rincian to import: {parse_result.total_rincian}")

    assign_item_codes(parse_result)

    # PHASE 4 FIX: Validate AHSP uniqueness (sumber, kode_ahsp, nama_ahsp)
    _validate_ahsp_uniqueness(parse_result, stdout)

    # PHASE 6 FIX: Merge duplicate AHSP in Excel file
    # If Excel has same AHSP multiple times, merge their rincian
    merged_jobs = {}  # (sumber, kode_ahsp) -> merged JobPreview
    for job in parse_result.jobs:
        key = (job.sumber, job.kode_ahsp)
        if key in merged_jobs:
            # Merge rincian from duplicate AHSP
            existing_job = merged_jobs[key]
            existing_job.rincian.extend(job.rincian)
            _log(stdout, f"[MERGE] Duplicate AHSP found in Excel: {job.kode_ahsp} - merging rincian")
            logger.warning(f"Duplicate AHSP in Excel: {job.sumber} :: {job.kode_ahsp} - merging {len(job.rincian)} rincian")
        else:
            merged_jobs[key] = job

    # Use merged jobs for processing
    jobs_to_process = list(merged_jobs.values())
    _log(stdout, f"[INFO] After merging duplicates: {len(jobs_to_process)} unique AHSP")

    with transaction.atomic():
        persist_item_codes(parse_result)

        # PHASE 1: Collect all rincian first, then bulk insert once
        all_rincian_to_delete = []
        all_pending_details = []

        # First pass: Create/update AHSP and collect rincian
        for job in jobs_to_process:
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

            # PHASE 4 FIX: Deduplicate rincian within this AHSP
            unique_rincian = _deduplicate_rincian(job.rincian, job, stdout)

            # Prepare rincian instances
            for detail in unique_rincian:
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

            # SIMPLIFIED: No savepoint - let atomic block handle errors
            # If bulk insert fails, transaction will rollback and user gets clear error message
            try:
                # PHASE 1: Increased batch_size from 500 to 1000
                # For very large imports (>10K), use larger batch size
                batch_size = 2000 if len(instances) > 10000 else 1000
                _log(stdout, f"[bulk] Inserting {len(instances)} rincian records (batch_size={batch_size})...")
                logger.info(f"Bulk creating {len(instances)} rincian records with batch_size={batch_size}")

                RincianReferensi.objects.bulk_create(instances, batch_size=batch_size)
                summary.rincian_written = len(instances)
                _log(stdout, f"[bulk] ✓ Inserted {len(instances)} rincian records")
                logger.info(f"Successfully inserted {len(instances)} rincian records")

            except Exception as exc:  # pragma: no cover - DB specific failure
                # Log error and re-raise to let atomic block handle cleanup
                error_type = type(exc).__name__
                error_msg = str(exc)
                logger.error(f"Bulk insert failed: {error_type}: {error_msg}", exc_info=True)

                # Add user-friendly error message
                summary.detail_errors.append(
                    f"Bulk insert gagal: {error_type}. "
                    f"Periksa data Anda untuk duplikat atau format yang tidak valid."
                )

                # Re-raise to trigger transaction rollback
                raise

        # PHASE 3 DAY 3: Refresh materialized view after import
        # SIMPLIFIED: Try to refresh, but don't fail import if this fails
        if summary.rincian_written > 0:
            try:
                _refresh_materialized_view(stdout)
            except Exception as exc:
                error_msg = f"[!] Failed to refresh materialized view: {exc}"
                _log(stdout, error_msg)
                logger.warning(f"Materialized view refresh failed: {exc}", exc_info=True)
                # Don't fail the import for this

        # PHASE 4: Invalidate search cache after import
        # SIMPLIFIED: Try to invalidate, but don't fail import if this fails
        if summary.rincian_written > 0:
            try:
                cache = CacheService()
                invalidated = cache.invalidate_search_cache()
                _log(stdout, f"[cache] Invalidated {invalidated} search cache keys")
            except Exception as exc:
                error_msg = f"[!] Failed to invalidate cache: {exc}"
                _log(stdout, error_msg)
                logger.warning(f"Cache invalidation failed: {exc}", exc_info=True)
                # Don't fail the import for this

    # Log import summary
    _log(stdout, "\n[COMPLETE] Import finished successfully!")
    _log(stdout, f"[SUMMARY] Jobs created: {summary.jobs_created}, Jobs updated: {summary.jobs_updated}")
    _log(stdout, f"[SUMMARY] Total rincian written: {summary.rincian_written}")
    if summary.detail_errors:
        _log(stdout, f"[SUMMARY] Errors encountered: {len(summary.detail_errors)}")

    logger.info(
        f"Import completed: {source_file}, "
        f"Jobs created: {summary.jobs_created}, "
        f"Jobs updated: {summary.jobs_updated}, "
        f"Rincian written: {summary.rincian_written}, "
        f"Errors: {len(summary.detail_errors)}"
    )

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
