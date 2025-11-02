"""
Preview Import Service Layer

Handles business logic for AHSP preview import workflow.
Extracted from views/preview.py for better testability and separation of concerns.
"""

import os
import pickle
import secrets
import tempfile
from dataclasses import dataclass
from math import ceil
from typing import Optional

from django.forms import formset_factory
from django.utils import timezone

from referensi.forms import PreviewDetailForm, PreviewJobForm
from referensi.services.ahsp_parser import ParseResult
from referensi.services.item_code_registry import assign_item_codes


# Formset factories
PreviewJobFormSet = formset_factory(PreviewJobForm, extra=0)
PreviewDetailFormSet = formset_factory(PreviewDetailForm, extra=0)


@dataclass
class PageInfo:
    """Pagination information"""

    page: int
    total_pages: int
    total_items: int
    start_index: int
    end_index: int


@dataclass
class PageData:
    """Page data with formset and metadata"""

    formset: any  # FormSet
    rows: list[dict]
    page_info: PageInfo


class ImportSessionManager:
    """
    Manages import session data using pickle files.

    Provides automatic cleanup of old files and session expiration.
    In Phase 3, this will be migrated to Redis/Memcached for better scalability.
    """

    SESSION_KEY = "referensi_pending_import"
    CLEANUP_AGE_HOURS = 2

    def store(
        self, session, parse_result: ParseResult, uploaded_name: str
    ) -> str:
        """
        Store parse result to temporary file and save reference in session.

        Args:
            session: Django session object
            parse_result: Parsed AHSP data
            uploaded_name: Original filename

        Returns:
            str: Security token for verification

        Raises:
            IOError: If file cannot be written
        """
        # Cleanup old files first
        self._cleanup_old_files()

        token = secrets.token_urlsafe(16)
        fd, tmp_path = tempfile.mkstemp(prefix="ahsp_preview_", suffix=".pkl")

        try:
            with os.fdopen(fd, "wb") as handle:
                pickle.dump(
                    parse_result, handle, protocol=pickle.HIGHEST_PROTOCOL
                )
        except Exception:
            # Cleanup on failure
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            raise

        session[self.SESSION_KEY] = {
            "parse_path": tmp_path,
            "uploaded_name": uploaded_name,
            "token": token,
            "created_at": timezone.now().isoformat(),
        }
        session.modified = True
        return token

    def retrieve(self, session) -> tuple[ParseResult, str, str]:
        """
        Retrieve parse result from session.

        Args:
            session: Django session object

        Returns:
            tuple: (parse_result, uploaded_name, token)

        Raises:
            FileNotFoundError: If session data missing or expired
            pickle.UnpicklingError: If file corrupted
        """
        data = session.get(self.SESSION_KEY)
        if not data:
            raise FileNotFoundError("No pending import in session")

        # Check age (auto-expire after CLEANUP_AGE_HOURS)
        created_at = data.get("created_at")
        if created_at:
            try:
                from datetime import datetime

                created_dt = datetime.fromisoformat(created_at)
                if timezone.is_naive(created_dt):
                    created_dt = timezone.make_aware(created_dt)

                age_hours = (timezone.now() - created_dt).total_seconds() / 3600
                if age_hours > self.CLEANUP_AGE_HOURS:
                    self.cleanup(session)
                    raise FileNotFoundError(
                        f"Import session expired (>{self.CLEANUP_AGE_HOURS}h old)"
                    )
            except (ValueError, TypeError):
                # If timestamp parsing fails, continue anyway
                pass

        parse_path = data.get("parse_path")
        if not parse_path:
            raise FileNotFoundError("Parse path missing from session")

        if not os.path.exists(parse_path):
            self.cleanup(session)
            raise FileNotFoundError("Parse file not found on disk")

        with open(parse_path, "rb") as handle:
            parse_result = pickle.load(handle)

        uploaded_name = data.get("uploaded_name", "")
        token = data.get("token", "")
        return parse_result, uploaded_name, token

    def rewrite(self, session, parse_result: ParseResult) -> str:
        """
        Rewrite existing parse result (after user edits).

        Args:
            session: Django session object
            parse_result: Updated parse result

        Returns:
            str: Security token

        Raises:
            FileNotFoundError: If no pending import
        """
        data = session.get(self.SESSION_KEY)
        if not data:
            raise FileNotFoundError("No pending import to rewrite")

        parse_path = data.get("parse_path")
        if not parse_path:
            raise FileNotFoundError("Parse path missing")

        with open(parse_path, "wb") as handle:
            pickle.dump(parse_result, handle, protocol=pickle.HIGHEST_PROTOCOL)

        session.modified = True
        return data.get("token", "")

    def cleanup(self, session) -> None:
        """
        Remove session data and delete temporary file.

        Args:
            session: Django session object
        """
        data = session.pop(self.SESSION_KEY, None)
        if data:
            path = data.get("parse_path")
            if path:
                try:
                    os.remove(path)
                except (FileNotFoundError, OSError):
                    pass
        session.modified = True

    def _cleanup_old_files(self):
        """Remove old pickle files from temp directory."""
        import time

        temp_dir = tempfile.gettempdir()
        cutoff_time = time.time() - (self.CLEANUP_AGE_HOURS * 3600)

        try:
            for filename in os.listdir(temp_dir):
                if filename.startswith("ahsp_preview_") and filename.endswith(
                    ".pkl"
                ):
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        if os.path.getmtime(filepath) < cutoff_time:
                            os.remove(filepath)
                    except (OSError, FileNotFoundError):
                        # File already deleted or permission issue - ignore
                        pass
        except (OSError, PermissionError):
            # Temp directory access issue - skip cleanup
            pass


class PreviewImportService:
    """
    Service for AHSP preview import functionality.

    Handles:
    - Pagination of jobs and details
    - Formset building
    - Applying user edits to preview data
    - Session management
    """

    def __init__(self, page_sizes: Optional[dict] = None):
        """
        Initialize service.

        Args:
            page_sizes: Dict with 'jobs' and 'details' page sizes.
                       If None, uses defaults from settings.
        """
        from django.conf import settings

        self.session_manager = ImportSessionManager()

        if page_sizes is None:
            referensi_config = getattr(settings, "REFERENSI_CONFIG", {})
            page_sizes = referensi_config.get("page_sizes", {})

        self.job_page_size = page_sizes.get("jobs", 25)
        self.detail_page_size = page_sizes.get("details", 50)

    def paginate(
        self, total: int, page: int, per_page: int
    ) -> tuple[int, int, int, int]:
        """
        Calculate pagination parameters.

        Args:
            total: Total number of items
            page: Requested page number (1-indexed)
            per_page: Items per page

        Returns:
            tuple: (start_index, end_index, page_number, total_pages)
        """
        if total <= 0:
            return 0, 0, 1, 1

        total_pages = max(1, ceil(total / per_page))
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = min(start + per_page, total)
        return start, end, page, total_pages

    def build_job_page(
        self, parse_result: Optional[ParseResult], page: int, *, data=None
    ) -> PageData:
        """
        Build job formset for given page.

        Args:
            parse_result: Parsed AHSP data (None if no data)
            page: Page number (1-indexed)
            data: POST data for bound formset (None for unbound)

        Returns:
            PageData: Formset, rows, and pagination info
        """
        jobs = parse_result.jobs if parse_result else []
        total = len(jobs)
        start, end, page, total_pages = self.paginate(
            total, page, self.job_page_size
        )

        # Build initial data and metadata
        initial = []
        rows_meta = []
        for job_index in range(start, end):
            job = jobs[job_index]
            initial.append(
                {
                    "job_index": job_index,
                    "sumber": job.sumber,
                    "kode_ahsp": job.kode_ahsp,
                    "nama_ahsp": job.nama_ahsp,
                    "klasifikasi": job.klasifikasi or "",
                    "sub_klasifikasi": job.sub_klasifikasi or "",
                    "satuan": job.satuan or "",
                }
            )
            rows_meta.append({"job": job, "job_index": job_index})

        # Create formset
        if data is not None:
            formset = PreviewJobFormSet(data, prefix="jobs", initial=initial)
        else:
            formset = PreviewJobFormSet(prefix="jobs", initial=initial)

        # Combine metadata with forms
        rows = []
        for meta, form in zip(rows_meta, formset.forms):
            rows.append(
                {
                    "job": meta["job"],
                    "form": form,
                    "job_index": meta["job_index"],
                }
            )

        page_info = PageInfo(
            page=page,
            total_pages=total_pages,
            total_items=total,
            start_index=(start + 1) if total else 0,
            end_index=end,
        )

        return PageData(formset=formset, rows=rows, page_info=page_info)

    def build_detail_page(
        self, parse_result: Optional[ParseResult], page: int, *, data=None
    ) -> PageData:
        """
        Build detail formset for given page.

        Details are flattened across all jobs for pagination.

        Args:
            parse_result: Parsed AHSP data (None if no data)
            page: Page number (1-indexed)
            data: POST data for bound formset (None for unbound)

        Returns:
            PageData: Formset, rows, and pagination info
        """
        jobs = parse_result.jobs if parse_result else []
        total = parse_result.total_rincian if parse_result else 0
        start, end, page, total_pages = self.paginate(
            total, page, self.detail_page_size
        )

        # Flatten details across all jobs
        initial = []
        rows_meta = []

        if total:
            flat_index = 0
            for job_index, job in enumerate(jobs):
                for detail_index, detail in enumerate(job.rincian):
                    if flat_index >= end:
                        break
                    if flat_index >= start:
                        initial.append(
                            {
                                "job_index": job_index,
                                "detail_index": detail_index,
                                "kategori": detail.kategori,
                                "kode_item": detail.kode_item,
                                "uraian_item": detail.uraian_item,
                                "satuan_item": detail.satuan_item,
                                "koefisien": detail.koefisien,
                            }
                        )
                        rows_meta.append(
                            {
                                "detail": detail,
                                "job": job,
                                "job_index": job_index,
                            }
                        )
                    flat_index += 1
                    if flat_index >= end:
                        break

        # Create formset
        if data is not None:
            formset = PreviewDetailFormSet(
                data, prefix="details", initial=initial
            )
        else:
            formset = PreviewDetailFormSet(prefix="details", initial=initial)

        # Combine metadata with forms
        rows = []
        for meta, form in zip(rows_meta, formset.forms):
            rows.append(
                {
                    "detail": meta["detail"],
                    "job": meta["job"],
                    "form": form,
                    "job_index": meta["job_index"],
                }
            )

        page_info = PageInfo(
            page=page,
            total_pages=total_pages,
            total_items=total,
            start_index=(start + 1) if total else 0,
            end_index=min(end, total),
        )

        return PageData(formset=formset, rows=rows, page_info=page_info)

    def apply_job_updates(
        self, parse_result: ParseResult, cleaned_data: list[dict]
    ) -> None:
        """
        Apply user edits to jobs in parse result.

        Modifies parse_result in place.

        Args:
            parse_result: Parsed AHSP data
            cleaned_data: List of cleaned form data from formset
        """
        for cleaned in cleaned_data:
            if not cleaned:
                continue

            job_index = cleaned["job_index"]
            if job_index >= len(parse_result.jobs):
                continue

            job = parse_result.jobs[job_index]
            job.sumber = cleaned["sumber"]
            job.kode_ahsp = cleaned["kode_ahsp"]
            job.nama_ahsp = cleaned["nama_ahsp"]
            job.klasifikasi = cleaned.get("klasifikasi") or ""
            job.sub_klasifikasi = cleaned.get("sub_klasifikasi") or ""
            job.satuan = cleaned.get("satuan") or ""

        # Reassign item codes after job changes
        assign_item_codes(parse_result)

    def apply_detail_updates(
        self, parse_result: ParseResult, cleaned_data: list[dict]
    ) -> None:
        """
        Apply user edits to details in parse result.

        Modifies parse_result in place.

        Args:
            parse_result: Parsed AHSP data
            cleaned_data: List of cleaned form data from formset
        """
        for cleaned in cleaned_data:
            if not cleaned:
                continue

            job_index = cleaned["job_index"]
            detail_index = cleaned["detail_index"]

            if job_index >= len(parse_result.jobs):
                continue

            job = parse_result.jobs[job_index]
            if detail_index >= len(job.rincian):
                continue

            detail = job.rincian[detail_index]
            detail.kategori = cleaned["kategori"]

            kode_item = cleaned.get("kode_item") or ""
            detail.kode_item = kode_item
            detail.kode_item_source = "manual" if kode_item else "missing"

            detail.uraian_item = cleaned["uraian_item"]
            detail.satuan_item = cleaned["satuan_item"]
            detail.koefisien = cleaned["koefisien"]

        # Reassign item codes after detail changes
        assign_item_codes(parse_result)
