"""
Unit tests for PreviewImportService.

Tests business logic in isolation without Django request/response.
"""

import os
import pickle
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.utils import timezone

from referensi.services.ahsp_parser import ParseResult, AHSPPreview, RincianPreview
from referensi.services.preview_service import (
    ImportSessionManager,
    PageData,
    PageInfo,
    PreviewImportService,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_parse_result():
    """Create sample ParseResult with 3 jobs and 10 details."""
    jobs = []

    # Job 1: 4 details
    job1 = AHSPPreview(
        sumber="SNI 2025",
        kode_ahsp="1.1.1",
        nama_ahsp="Pekerjaan Test 1",
        klasifikasi="Konstruksi",
        sub_klasifikasi="Beton",
        satuan="m3",
        rincian=[
            RincianPreview(
                kategori="Upah",
                kode_item="U01",
                uraian_item="Pekerja",
                satuan_item="OH",
                koefisien=0.5,
                kode_item_source="registry",
                row_number=1,
            ),
            RincianPreview(
                kategori="Bahan",
                kode_item="B01",
                uraian_item="Semen",
                satuan_item="kg",
                koefisien=10.0,
                kode_item_source="registry",
                row_number=2,
            ),
            RincianPreview(
                kategori="Alat",
                kode_item="A01",
                uraian_item="Molen",
                satuan_item="jam",
                koefisien=0.25,
                kode_item_source="registry",
                row_number=3,
            ),
            RincianPreview(
                kategori="Upah",
                kode_item="U02",
                uraian_item="Tukang",
                satuan_item="OH",
                koefisien=0.3,
                kode_item_source="registry",
                row_number=4,
            ),
        ],
        row_number=1,
    )

    # Job 2: 3 details
    job2 = AHSPPreview(
        sumber="SNI 2025",
        kode_ahsp="1.1.2",
        nama_ahsp="Pekerjaan Test 2",
        klasifikasi="Konstruksi",
        sub_klasifikasi="Baja",
        satuan="kg",
        rincian=[
            RincianPreview(
                kategori="Upah",
                kode_item="U03",
                uraian_item="Tukang Las",
                satuan_item="OH",
                koefisien=0.8,
                kode_item_source="registry",
                row_number=5,
            ),
            RincianPreview(
                kategori="Bahan",
                kode_item="B02",
                uraian_item="Besi Beton",
                satuan_item="kg",
                koefisien=1.05,
                kode_item_source="registry",
                row_number=6,
            ),
            RincianPreview(
                kategori="Alat",
                kode_item="A02",
                uraian_item="Mesin Las",
                satuan_item="jam",
                koefisien=0.5,
                kode_item_source="registry",
                row_number=7,
            ),
        ],
        row_number=2,
    )

    # Job 3: 3 details
    job3 = AHSPPreview(
        sumber="AHSP 2023",
        kode_ahsp="2.1.1",
        nama_ahsp="Pekerjaan Test 3",
        klasifikasi="Finishing",
        sub_klasifikasi="Cat",
        satuan="m2",
        rincian=[
            RincianPreview(
                kategori="Upah",
                kode_item="U04",
                uraian_item="Tukang Cat",
                satuan_item="OH",
                koefisien=0.4,
                kode_item_source="registry",
                row_number=8,
            ),
            RincianPreview(
                kategori="Bahan",
                kode_item="B03",
                uraian_item="Cat Tembok",
                satuan_item="liter",
                koefisien=0.2,
                kode_item_source="registry",
                row_number=9,
            ),
            RincianPreview(
                kategori="Bahan",
                kode_item="B04",
                uraian_item="Dempul",
                satuan_item="kg",
                koefisien=0.15,
                kode_item_source="registry",
                row_number=10,
            ),
        ],
        row_number=3,
    )

    jobs = [job1, job2, job3]

    return ParseResult(
        jobs=jobs,
        errors=[],
    )


@pytest.fixture(autouse=True)
def stub_assign_item_codes(monkeypatch):
    """Prevent database access from assign_item_codes during service tests."""
    monkeypatch.setattr(
        "referensi.services.preview_service.assign_item_codes",
        lambda *args, **kwargs: None,
    )


@pytest.fixture
def empty_parse_result():
    """Create empty ParseResult."""
    return ParseResult(
        jobs=[],
        errors=[],
    )


@pytest.fixture
def session():
    """Create Django session for testing."""
    session = SessionStore()
    session.create()
    return session


# ============================================================================
# TESTS: PreviewImportService.paginate()
# ============================================================================

class TestPaginate:
    """Test pagination logic."""

    def test_paginate_normal_case(self):
        """Test pagination with normal data."""
        service = PreviewImportService()

        # 100 items, page 1, 25 per page
        start, end, page, total_pages = service.paginate(100, 1, 25)

        assert start == 0
        assert end == 25
        assert page == 1
        assert total_pages == 4

    def test_paginate_last_page(self):
        """Test pagination on last page (partial)."""
        service = PreviewImportService()

        # 100 items, page 4, 25 per page (last page has 100-75=25 items)
        start, end, page, total_pages = service.paginate(100, 4, 25)

        assert start == 75
        assert end == 100
        assert page == 4
        assert total_pages == 4

    def test_paginate_partial_last_page(self):
        """Test pagination with partial last page."""
        service = PreviewImportService()

        # 47 items, page 2, 25 per page (last page has 47-25=22 items)
        start, end, page, total_pages = service.paginate(47, 2, 25)

        assert start == 25
        assert end == 47
        assert page == 2
        assert total_pages == 2

    def test_paginate_page_too_high(self):
        """Test pagination when page number exceeds total pages."""
        service = PreviewImportService()

        # Request page 10 when only 4 pages exist
        start, end, page, total_pages = service.paginate(100, 10, 25)

        # Should return last page
        assert start == 75
        assert end == 100
        assert page == 4
        assert total_pages == 4

    def test_paginate_page_zero(self):
        """Test pagination with page 0 (should return page 1)."""
        service = PreviewImportService()

        start, end, page, total_pages = service.paginate(100, 0, 25)

        assert start == 0
        assert end == 25
        assert page == 1
        assert total_pages == 4

    def test_paginate_empty_data(self):
        """Test pagination with no data."""
        service = PreviewImportService()

        start, end, page, total_pages = service.paginate(0, 1, 25)

        assert start == 0
        assert end == 0
        assert page == 1
        assert total_pages == 1


# ============================================================================
# TESTS: PreviewImportService.build_job_page()
# ============================================================================

class TestBuildJobPage:
    """Test job page building."""

    def test_build_job_page_first_page(self, sample_parse_result):
        """Test building first page of jobs."""
        service = PreviewImportService()

        page_data = service.build_job_page(sample_parse_result, page=1)

        assert isinstance(page_data, PageData)
        assert page_data.page_info.page == 1
        assert page_data.page_info.total_items == 3
        assert page_data.page_info.total_pages == 1  # 3 jobs fit in 1 page (25 per page)
        assert page_data.page_info.start_index == 1
        assert page_data.page_info.end_index == 3
        assert len(page_data.rows) == 3
        assert page_data.formset is not None

    def test_build_job_page_empty_data(self, empty_parse_result):
        """Test building job page with no data."""
        service = PreviewImportService()

        page_data = service.build_job_page(empty_parse_result, page=1)

        assert page_data.page_info.total_items == 0
        assert page_data.page_info.start_index == 0
        assert page_data.page_info.end_index == 0
        assert len(page_data.rows) == 0

    def test_build_job_page_none(self):
        """Test building job page with None parse_result."""
        service = PreviewImportService()

        page_data = service.build_job_page(None, page=1)

        assert page_data.page_info.total_items == 0
        assert len(page_data.rows) == 0

    def test_build_job_page_with_post_data(self, sample_parse_result):
        """Test building job page with POST data (bound formset)."""
        service = PreviewImportService()

        post_data = {
            "jobs-TOTAL_FORMS": "3",
            "jobs-INITIAL_FORMS": "3",
            "jobs-MIN_NUM_FORMS": "0",
            "jobs-MAX_NUM_FORMS": "1000",
            "jobs-0-job_index": "0",
            "jobs-0-sumber": "SNI 2025",
            "jobs-0-kode_ahsp": "1.1.1",
            "jobs-0-nama_ahsp": "Updated Name",  # Changed
            "jobs-0-klasifikasi": "Konstruksi",
            "jobs-0-sub_klasifikasi": "Beton",
            "jobs-0-satuan": "m3",
        }

        page_data = service.build_job_page(sample_parse_result, page=1, data=post_data)

        assert page_data.formset.is_bound
        # Note: formset might not be valid without all required fields


# ============================================================================
# TESTS: PreviewImportService.build_detail_page()
# ============================================================================

class TestBuildDetailPage:
    """Test detail page building."""

    def test_build_detail_page_first_page(self, sample_parse_result):
        """Test building first page of details."""
        service = PreviewImportService()

        page_data = service.build_detail_page(sample_parse_result, page=1)

        assert isinstance(page_data, PageData)
        assert page_data.page_info.page == 1
        assert page_data.page_info.total_items == 10
        assert page_data.page_info.total_pages == 1  # 10 details fit in 1 page (50 per page)
        assert page_data.page_info.start_index == 1
        assert page_data.page_info.end_index == 10
        assert len(page_data.rows) == 10

    def test_build_detail_page_flattening(self, sample_parse_result):
        """Test that details are flattened across jobs."""
        service = PreviewImportService()

        page_data = service.build_detail_page(sample_parse_result, page=1)

        # Should have details from all 3 jobs
        job_indices = [row["job_index"] for row in page_data.rows]
        assert 0 in job_indices  # Job 1
        assert 1 in job_indices  # Job 2
        assert 2 in job_indices  # Job 3

        # First 4 details should be from job 0
        assert job_indices[0:4] == [0, 0, 0, 0]
        # Next 3 from job 1
        assert job_indices[4:7] == [1, 1, 1]
        # Last 3 from job 2
        assert job_indices[7:10] == [2, 2, 2]

    def test_build_detail_page_small_page_size(self, sample_parse_result):
        """Test detail pagination with small page size."""
        # Override page size to 3
        service = PreviewImportService(page_sizes={"jobs": 25, "details": 3})

        # Page 1: details 0-2
        page_data = service.build_detail_page(sample_parse_result, page=1)
        assert len(page_data.rows) == 3
        assert page_data.page_info.total_pages == 4  # 10 details / 3 per page = 4 pages

        # Page 2: details 3-5
        page_data = service.build_detail_page(sample_parse_result, page=2)
        assert len(page_data.rows) == 3
        assert page_data.page_info.start_index == 4
        assert page_data.page_info.end_index == 6


# ============================================================================
# TESTS: PreviewImportService.apply_job_updates()
# ============================================================================

class TestApplyJobUpdates:
    """Test applying job updates."""

    def test_apply_job_updates(self, sample_parse_result):
        """Test applying changes to jobs."""
        service = PreviewImportService()

        cleaned_data = [
            {
                "job_index": 0,
                "sumber": "SNI 2025 Updated",
                "kode_ahsp": "1.1.1.NEW",
                "nama_ahsp": "Updated Name",
                "klasifikasi": "Updated Klasifikasi",
                "sub_klasifikasi": "Updated Sub",
                "satuan": "m2",
            }
        ]

        original_sumber = sample_parse_result.jobs[0].sumber

        service.apply_job_updates(sample_parse_result, cleaned_data)

        # Check updates applied
        assert sample_parse_result.jobs[0].sumber == "SNI 2025 Updated"
        assert sample_parse_result.jobs[0].kode_ahsp == "1.1.1.NEW"
        assert sample_parse_result.jobs[0].nama_ahsp == "Updated Name"
        assert sample_parse_result.jobs[0].klasifikasi == "Updated Klasifikasi"
        assert sample_parse_result.jobs[0].sub_klasifikasi == "Updated Sub"
        assert sample_parse_result.jobs[0].satuan == "m2"

    def test_apply_job_updates_invalid_index(self, sample_parse_result):
        """Test applying updates with invalid job index (should skip)."""
        service = PreviewImportService()

        cleaned_data = [
            {
                "job_index": 999,  # Out of bounds
                "sumber": "Should Not Apply",
                "kode_ahsp": "X",
                "nama_ahsp": "X",
            }
        ]

        # Should not raise error
        service.apply_job_updates(sample_parse_result, cleaned_data)

        # No changes to actual jobs
        assert sample_parse_result.jobs[0].sumber == "SNI 2025"


# ============================================================================
# TESTS: PreviewImportService.apply_detail_updates()
# ============================================================================

class TestApplyDetailUpdates:
    """Test applying detail updates."""

    def test_apply_detail_updates(self, sample_parse_result):
        """Test applying changes to details."""
        service = PreviewImportService()

        cleaned_data = [
            {
                "job_index": 0,
                "detail_index": 0,
                "kategori": "Upah",
                "kode_item": "U99",
                "uraian_item": "Updated Pekerja",
                "satuan_item": "hari",
                "koefisien": 1.5,
            }
        ]

        service.apply_detail_updates(sample_parse_result, cleaned_data)

        # Check updates applied
        detail = sample_parse_result.jobs[0].rincian[0]
        assert detail.kategori == "Upah"
        assert detail.kode_item == "U99"
        assert detail.uraian_item == "Updated Pekerja"
        assert detail.satuan_item == "hari"
        assert detail.koefisien == 1.5
        assert detail.kode_item_source == "manual"


# ============================================================================
# TESTS: ImportSessionManager.store()
# ============================================================================

class TestSessionManagerStore:
    """Test session storage."""

    def test_store_creates_pickle_file(self, session, sample_parse_result):
        """Test that store creates pickle file."""
        manager = ImportSessionManager()

        token = manager.store(session, sample_parse_result, "test.xlsx")

        assert token is not None
        assert len(token) > 0

        # Check session data
        data = session.get(manager.SESSION_KEY)
        assert data is not None
        assert "parse_path" in data
        assert "uploaded_name" in data
        assert "token" in data
        assert "created_at" in data
        assert data["uploaded_name"] == "test.xlsx"
        assert data["token"] == token

        # Check file exists
        assert os.path.exists(data["parse_path"])

        # Cleanup
        manager.cleanup(session)

    def test_store_cleanup_old_files(self, session, sample_parse_result):
        """Test that store cleans up old files."""
        manager = ImportSessionManager()

        # Create an old pickle file
        fd, old_file = tempfile.mkstemp(prefix="ahsp_preview_", suffix=".pkl")
        os.close(fd)
        # Set modification time to 3 hours ago
        three_hours_ago = time.time() - (3 * 3600)
        os.utime(old_file, (three_hours_ago, three_hours_ago))

        # Store new file (should trigger cleanup)
        token = manager.store(session, sample_parse_result, "test.xlsx")

        # Old file should be deleted
        assert not os.path.exists(old_file)

        # Cleanup new file
        manager.cleanup(session)


# ============================================================================
# TESTS: ImportSessionManager.retrieve()
# ============================================================================

class TestSessionManagerRetrieve:
    """Test session retrieval."""

    def test_retrieve_success(self, session, sample_parse_result):
        """Test successful retrieval."""
        manager = ImportSessionManager()

        # Store
        token = manager.store(session, sample_parse_result, "test.xlsx")

        # Retrieve
        parse_result, uploaded_name, retrieved_token = manager.retrieve(session)

        assert parse_result is not None
        assert parse_result.total_jobs == 3
        assert uploaded_name == "test.xlsx"
        assert retrieved_token == token

        # Cleanup
        manager.cleanup(session)

    def test_retrieve_no_session(self, session):
        """Test retrieve with no session data."""
        manager = ImportSessionManager()

        with pytest.raises(FileNotFoundError, match="No pending import"):
            manager.retrieve(session)

    def test_retrieve_expired_session(self, session, sample_parse_result):
        """Test retrieve with expired session."""
        manager = ImportSessionManager()

        # Store
        manager.store(session, sample_parse_result, "test.xlsx")

        # Manually set created_at to 3 hours ago
        data = session.get(manager.SESSION_KEY)
        old_time = timezone.now() - timezone.timedelta(hours=3)
        data["created_at"] = old_time.isoformat()
        session[manager.SESSION_KEY] = data
        session.save()

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="expired"):
            manager.retrieve(session)


# ============================================================================
# TESTS: ImportSessionManager.cleanup()
# ============================================================================

class TestSessionManagerCleanup:
    """Test session cleanup."""

    def test_cleanup_removes_file_and_session(self, session, sample_parse_result):
        """Test cleanup removes both file and session data."""
        manager = ImportSessionManager()

        # Store
        manager.store(session, sample_parse_result, "test.xlsx")

        # Get file path before cleanup
        data = session.get(manager.SESSION_KEY)
        file_path = data["parse_path"]

        assert os.path.exists(file_path)
        assert manager.SESSION_KEY in session

        # Cleanup
        manager.cleanup(session)

        # File should be deleted
        assert not os.path.exists(file_path)
        # Session data should be removed
        assert manager.SESSION_KEY not in session

    def test_cleanup_handles_missing_file(self, session):
        """Test cleanup handles case where file already deleted."""
        manager = ImportSessionManager()

        # Manually create session data with non-existent file
        session[manager.SESSION_KEY] = {
            "parse_path": "/nonexistent/file.pkl",
            "uploaded_name": "test.xlsx",
            "token": "abc123",
        }
        session.save()

        # Should not raise error
        manager.cleanup(session)

        # Session should be cleared
        assert manager.SESSION_KEY not in session


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow(self, session, sample_parse_result):
        """Test complete workflow: store → retrieve → update → rewrite → retrieve → cleanup."""
        service = PreviewImportService()

        # 1. Store
        token = service.session_manager.store(session, sample_parse_result, "test.xlsx")
        assert token is not None

        # 2. Retrieve
        parse_result, uploaded_name, retrieved_token = service.session_manager.retrieve(session)
        assert parse_result.total_jobs == 3
        assert uploaded_name == "test.xlsx"
        assert retrieved_token == token

        # 3. Build page
        page_data = service.build_job_page(parse_result, page=1)
        assert len(page_data.rows) == 3

        # 4. Apply updates
        cleaned_data = [{
            "job_index": 0,
            "sumber": "Updated Source",
            "kode_ahsp": "NEW",
            "nama_ahsp": "New Name",
            "klasifikasi": "",
            "sub_klasifikasi": "",
            "satuan": "",
        }]
        service.apply_job_updates(parse_result, cleaned_data)

        # 5. Rewrite
        service.session_manager.rewrite(session, parse_result)

        # 6. Retrieve again
        parse_result2, _, _ = service.session_manager.retrieve(session)
        assert parse_result2.jobs[0].sumber == "Updated Source"
        assert parse_result2.jobs[0].kode_ahsp == "NEW"

        # 7. Cleanup
        service.session_manager.cleanup(session)
        assert service.session_manager.SESSION_KEY not in session
