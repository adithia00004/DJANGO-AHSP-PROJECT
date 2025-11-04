"""
Chunked Import Service - Handles large file imports efficiently
Prevents memory overflow and browser freezes for files with thousands of rows
"""

from typing import Iterator, Tuple, Dict, Any
import time
from django.core.cache import cache
from django.db import transaction
from decimal import Decimal

from referensi.models import AHSPReferensi, RincianReferensi
from .ahsp_parser import ParseResult, JobPreview, RincianPreview
from .import_writer import ImportSummary


class ChunkedImportService:
    """
    Service for processing large imports in chunks to prevent memory issues.

    Features:
    - Processes data in configurable batch sizes
    - Tracks progress in cache for real-time updates
    - Yields control back to server between batches
    - Prevents memory overflow
    """

    def __init__(self, batch_size: int = 100):
        """
        Args:
            batch_size: Number of rows to process per batch (default: 100)
        """
        self.batch_size = batch_size

    def create_progress_key(self, session_key: str) -> str:
        """Generate cache key for tracking progress"""
        return f"import_progress_{session_key}"

    def update_progress(
        self,
        session_key: str,
        stage: str,
        current: int,
        total: int,
        details: str = ""
    ):
        """
        Update import progress in cache

        Args:
            session_key: User session key
            stage: Current stage (parsing, validation, writing)
            current: Current progress count
            total: Total items to process
            details: Additional details message
        """
        progress_key = self.create_progress_key(session_key)

        percent = (current / total * 100) if total > 0 else 0

        progress_data = {
            'stage': stage,
            'current': current,
            'total': total,
            'percent': round(percent, 2),
            'details': details,
            'timestamp': time.time()
        }

        # Store in cache for 5 minutes
        cache.set(progress_key, progress_data, timeout=300)

    def get_progress(self, session_key: str) -> Dict[str, Any]:
        """Get current progress from cache"""
        progress_key = self.create_progress_key(session_key)
        return cache.get(progress_key, {})

    def clear_progress(self, session_key: str):
        """Clear progress from cache"""
        progress_key = self.create_progress_key(session_key)
        cache.delete(progress_key)

    def process_jobs_in_chunks(
        self,
        jobs: list[JobPreview],
        session_key: str,
        source_file: str = None
    ) -> Tuple[int, int]:
        """
        Process jobs in chunks to prevent memory issues

        Returns:
            Tuple of (jobs_created, jobs_updated)
        """
        total_jobs = len(jobs)
        jobs_created = 0
        jobs_updated = 0

        for i in range(0, total_jobs, self.batch_size):
            chunk = jobs[i:i + self.batch_size]
            current_batch = i // self.batch_size + 1
            total_batches = (total_jobs + self.batch_size - 1) // self.batch_size

            # Update progress
            self.update_progress(
                session_key,
                'writing_jobs',
                i + len(chunk),
                total_jobs,
                f"Batch {current_batch}/{total_batches}: {len(chunk)} pekerjaan"
            )

            # Process chunk
            with transaction.atomic():
                for job in chunk:
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
                        jobs_created += 1
                    else:
                        # Update if changed
                        updated_fields = []
                        if ahsp_obj.nama_ahsp != job.nama_ahsp:
                            ahsp_obj.nama_ahsp = job.nama_ahsp
                            updated_fields.append("nama_ahsp")
                        if job.klasifikasi and ahsp_obj.klasifikasi != job.klasifikasi:
                            ahsp_obj.klasifikasi = job.klasifikasi
                            updated_fields.append("klasifikasi")
                        if job.sub_klasifikasi and ahsp_obj.sub_klasifikasi != job.sub_klasifikasi:
                            ahsp_obj.sub_klasifikasi = job.sub_klasifikasi
                            updated_fields.append("sub_klasifikasi")
                        if job.satuan and ahsp_obj.satuan != job.satuan:
                            ahsp_obj.satuan = job.satuan
                            updated_fields.append("satuan")

                        if updated_fields:
                            ahsp_obj.save(update_fields=updated_fields)
                            jobs_updated += 1

        return jobs_created, jobs_updated

    def process_rincian_in_chunks(
        self,
        parse_result: ParseResult,
        session_key: str
    ) -> int:
        """
        Process rincian in chunks

        Returns:
            Total rincian written
        """
        # Collect all rincian with their parent job references
        all_rincian_data = []

        for job in parse_result.jobs:
            # Get AHSP object
            try:
                ahsp_obj = AHSPReferensi.objects.get(
                    sumber=job.sumber,
                    kode_ahsp=job.kode_ahsp
                )
            except AHSPReferensi.DoesNotExist:
                continue

            for rincian in job.rincian:
                all_rincian_data.append((ahsp_obj, rincian))

        total_rincian = len(all_rincian_data)
        rincian_written = 0

        # Process in chunks
        for i in range(0, total_rincian, self.batch_size):
            chunk = all_rincian_data[i:i + self.batch_size]
            current_batch = i // self.batch_size + 1
            total_batches = (total_rincian + self.batch_size - 1) // self.batch_size

            # Update progress
            self.update_progress(
                session_key,
                'writing_details',
                i + len(chunk),
                total_rincian,
                f"Batch {current_batch}/{total_batches}: {len(chunk)} rincian"
            )

            # Process chunk
            with transaction.atomic():
                # Delete existing rincian for these jobs (in chunk)
                ahsp_ids = set(ahsp_obj.id for ahsp_obj, _ in chunk)
                RincianReferensi.objects.filter(ahsp__in=ahsp_ids).delete()

                # Bulk create new rincian
                rincian_objects = []
                for ahsp_obj, rincian in chunk:
                    rincian_objects.append(
                        RincianReferensi(
                            ahsp=ahsp_obj,
                            kategori=rincian.kategori,
                            kode_item=rincian.kode_item,
                            uraian_item=rincian.uraian_item,
                            satuan_item=rincian.satuan_item,
                            koefisien=rincian.koefisien,
                        )
                    )

                RincianReferensi.objects.bulk_create(
                    rincian_objects,
                    batch_size=self.batch_size
                )

                rincian_written += len(rincian_objects)

        return rincian_written

    def write_parse_result_chunked(
        self,
        parse_result: ParseResult,
        session_key: str,
        source_file: str = None
    ) -> ImportSummary:
        """
        Write parse result to database in chunks

        Args:
            parse_result: Parsed data
            session_key: User session key for progress tracking
            source_file: Source filename

        Returns:
            ImportSummary with results
        """
        summary = ImportSummary()

        if parse_result.errors:
            raise ValueError("ParseResult contains errors, cannot import.")

        # Stage 1: Process jobs
        self.update_progress(session_key, 'writing_jobs', 0, len(parse_result.jobs))
        jobs_created, jobs_updated = self.process_jobs_in_chunks(
            parse_result.jobs,
            session_key,
            source_file
        )
        summary.jobs_created = jobs_created
        summary.jobs_updated = jobs_updated

        # Stage 2: Process rincian
        total_rincian = sum(len(job.rincian) for job in parse_result.jobs)
        self.update_progress(session_key, 'writing_details', 0, total_rincian)
        rincian_written = self.process_rincian_in_chunks(
            parse_result,
            session_key
        )
        summary.rincian_written = rincian_written

        # Clear progress
        self.clear_progress(session_key)

        return summary


class ProgressTracker:
    """
    Standalone progress tracker that can be used independently
    """

    def __init__(self, session_key: str, total_items: int):
        self.session_key = session_key
        self.total_items = total_items
        self.current = 0
        self.service = ChunkedImportService()

    def update(self, stage: str, increment: int = 1, details: str = ""):
        """Update progress by incrementing current count"""
        self.current += increment
        self.service.update_progress(
            self.session_key,
            stage,
            self.current,
            self.total_items,
            details
        )

    def set(self, stage: str, current: int, details: str = ""):
        """Set progress to specific value"""
        self.current = current
        self.service.update_progress(
            self.session_key,
            stage,
            current,
            self.total_items,
            details
        )

    def finish(self):
        """Mark as complete and clear"""
        self.service.clear_progress(self.session_key)
