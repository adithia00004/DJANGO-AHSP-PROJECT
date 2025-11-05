"""Utility untuk menulis hasil parse AHSP ke database."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from django.db import transaction

from referensi.models import AHSPReferensi, RincianReferensi
from .import_utils import canonicalize_kategori
from .item_code_registry import assign_item_codes, persist_item_codes
from .cache_service import CacheService
from .duplicate_report import (
    DuplicateEntry,
    SkippedEntry,
    ImportReport,
    generate_duplicate_report_csv,
)


@dataclass
class ImportSummary:
    """Ringkasan hasil impor AHSP."""

    jobs_created: int = 0
    jobs_updated: int = 0
    rincian_written: int = 0
    rincian_duplicated: int = 0  # Number of duplicate rincian skipped
    rincian_skipped: int = 0  # Number of rows skipped (empty uraian, etc)
    detail_errors: list[str] = field(default_factory=list)
    duplicate_report_path: str = ""  # Path to CSV report file


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

    Returns:
        tuple: (unique_rincian_list, duplicate_count, duplicate_entries_list)
    """
    seen = {}  # key -> (first_detail, first_row_number)
    unique = []
    duplicates = []
    duplicate_entries = []  # For CSV export

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
            first_detail, first_row = seen[key]
            duplicates.append(
                f"    📍 Baris {detail.row_number}: {kategori} - {detail.uraian_item} ({detail.satuan_item}) - DUPLIKAT dari baris {first_row}"
            )
            # Collect for CSV export
            duplicate_entries.append(DuplicateEntry(
                row_number=detail.row_number,
                ahsp_kode=job.kode_ahsp,
                ahsp_nama=job.nama_ahsp,
                kategori=kategori,
                kode_item=detail.kode_item,
                uraian_item=detail.uraian_item,
                satuan_item=detail.satuan_item,
                koefisien=str(detail.koefisien),
                duplicate_of_row=first_row,
                reason=f"Sama persis dengan baris {first_row} (kategori + kode_item + uraian + satuan)"
            ))
        else:
            seen[key] = (detail, detail.row_number)
            unique.append(detail)

    if duplicates:
        warning = (
            f"⚠️ DUPLIKASI DITEMUKAN: {len(duplicates)} rincian duplikat diabaikan untuk AHSP '{job.kode_ahsp} - {job.nama_ahsp}':\n"
            f"📝 PENJELASAN: Rincian dengan kategori, kode item, uraian, dan satuan yang sama dianggap duplikat.\n"
            f"              Hanya kemunculan pertama yang disimpan, sisanya diabaikan.\n\n"
            f"📋 Daftar baris yang diabaikan (maksimal 10 ditampilkan):\n"
            + "\n".join(duplicates[:10])
        )
        if len(duplicates) > 10:
            warning += f"\n    ... dan {len(duplicates) - 10} duplikat lainnya\n"

        warning += (
            f"\n💡 SARAN:\n"
            f"   • Periksa file Excel Anda, mungkin ada copy-paste yang tidak disengaja\n"
            f"   • Atau hapus baris duplikat jika memang tidak diperlukan\n"
            f"   • Total: {len(unique)} rincian unik dari {len(rincian_list)} baris\n"
            f"   • 📄 Download laporan detail: Cek link di pesan sukses import\n"
        )
        _log(stdout, warning)

    return unique, len(duplicates), duplicate_entries


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

    # Initialize import report for duplicate tracking
    import_report = ImportReport(
        filename=source_file or "unknown.xlsx",
        timestamp=logger.info.__self__.name if hasattr(logger.info, '__self__') else ""
    )

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
            unique_rincian, dup_count, dup_entries = _deduplicate_rincian(job.rincian, job, stdout)
            summary.rincian_duplicated += dup_count
            import_report.duplicates.extend(dup_entries)

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

    # Calculate totals for report
    total_from_file = parse_result.total_rincian

    # Generate duplicate report CSV if there are any duplicates or skipped rows
    if import_report.duplicates or (total_from_file - summary.rincian_written) > 0:
        try:
            report_path = generate_duplicate_report_csv(import_report, source_file or "unknown.xlsx")
            summary.duplicate_report_path = report_path
            _log(stdout, f"\n📄 Laporan duplikat tersimpan: {report_path}")
            logger.info(f"Duplicate report generated: {report_path}")
        except Exception as exc:
            error_msg = f"[!] Failed to generate duplicate report: {exc}"
            _log(stdout, error_msg)
            logger.warning(f"Duplicate report generation failed: {exc}", exc_info=True)
            # Don't fail the import for this

    # Log import summary with detailed breakdown
    _log(stdout, "\n" + "="*80)
    _log(stdout, "[COMPLETE] Import finished successfully!")
    _log(stdout, "="*80)
    _log(stdout, f"\n📊 RINGKASAN IMPORT:")
    _log(stdout, f"   • Pekerjaan dibuat: {summary.jobs_created}")
    _log(stdout, f"   • Pekerjaan diperbarui: {summary.jobs_updated}")
    _log(stdout, f"   • Rincian tersimpan: {summary.rincian_written}")

    # Show skipped rows breakdown
    if summary.rincian_duplicated > 0 or summary.rincian_written < total_from_file:
        _log(stdout, f"\n⚠️ BARIS YANG DIABAIKAN:")
        if summary.rincian_duplicated > 0:
            _log(stdout, f"   • Duplikat: {summary.rincian_duplicated} baris")
        skipped_other = total_from_file - summary.rincian_written - summary.rincian_duplicated
        if skipped_other > 0:
            _log(stdout, f"   • Lainnya (uraian kosong, error format): {skipped_other} baris")
        _log(stdout, f"   • Total diabaikan: {total_from_file - summary.rincian_written} dari {total_from_file} baris")
        _log(stdout, f"\n💡 PERIKSA WARNING DI ATAS untuk detail baris yang diabaikan!")

    if summary.detail_errors:
        _log(stdout, f"\n❌ Errors encountered: {len(summary.detail_errors)}")

    _log(stdout, "="*80)

    logger.info(
        f"Import completed: {source_file}, "
        f"Jobs created: {summary.jobs_created}, "
        f"Jobs updated: {summary.jobs_updated}, "
        f"Rincian written: {summary.rincian_written}, "
        f"Rincian duplicated: {summary.rincian_duplicated}, "
        f"Total from file: {total_from_file}, "
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
