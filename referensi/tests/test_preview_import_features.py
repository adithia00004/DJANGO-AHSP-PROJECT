from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.preview_service import (
    ImportSessionManager,
    PageData,
    PageInfo,
    PreviewImportService,
)
from referensi.views.preview import preview_import


class DummySession(dict):
    """Simple dict-like session object with the attributes Django expects."""

    modified: bool = False


class DummyUser(SimpleNamespace):
    """Minimal user object with permission helpers."""

    def __init__(self, perms=None, **kwargs):
        kwargs.setdefault("username", "tester")
        self._perms = set(perms or [])
        super().__init__(**kwargs)

    @property
    def is_authenticated(self) -> bool:
        return True

    def has_perm(self, perm: str) -> bool:
        if getattr(self, "is_superuser", False):
            return True
        return perm in self._perms

    def has_perms(self, perms) -> bool:
        return all(self.has_perm(perm) for perm in perms)


def create_test_parse_result(num_jobs: int = 12, details_per_job: int = 3) -> ParseResult:
    """Build a ParseResult with predictable content for tests."""
    jobs = []
    row_number = 2

    for job_index in range(num_jobs):
        rincian = []
        for detail_index in range(details_per_job):
            rincian.append(
                RincianPreview(
                    kategori=f"Kategori {detail_index}",
                    kode_item=f"ITEM-{job_index:03d}-{detail_index:03d}",
                    uraian_item=f"Uraian item {detail_index} untuk pekerjaan {job_index}",
                    satuan_item="m3" if detail_index % 2 == 0 else "kg",
                    koefisien=Decimal(detail_index + 1),
                    row_number=row_number + detail_index + 1,
                )
            )

        suffix = ("beton", "pagar", "pasir")[job_index % 3]
        jobs.append(
            AHSPPreview(
                sumber=f"Sumber {job_index % 4}",
                kode_ahsp=f"AHSP-{job_index:04d}",
                nama_ahsp=f"Pekerjaan {suffix} {job_index}",
                row_number=row_number,
                klasifikasi=f"Klasifikasi {job_index % 5}",
                sub_klasifikasi=f"Sub {job_index % 2}",
                satuan="m2" if job_index % 2 == 0 else "m3",
                rincian=rincian,
            )
        )
        row_number += details_per_job + 1

    return ParseResult(jobs=jobs)


@pytest.fixture(autouse=True)
def signed_cookie_sessions(settings):
    """Use cookie-based sessions to keep tests self-contained."""
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"


@pytest.fixture
def parse_result():
    return create_test_parse_result()


def test_filter_jobs_handles_substring_matches(parse_result):
    service = PreviewImportService()
    filtered = service.filter_jobs(parse_result.jobs, "beton")

    assert len(filtered) == len(parse_result.jobs) // 3
    assert all("beton" in job.nama_ahsp.lower() for job in filtered)


def test_paginate_clamps_page_numbers():
    service = PreviewImportService()

    start, end, page, total = service.paginate(total=60, page=3, per_page=25)
    assert (start, end, page, total) == (50, 60, 3, 3)

    start, end, page, total = service.paginate(total=10, page=99, per_page=25)
    assert (start, end, page, total) == (0, 10, 1, 1)


def test_build_job_page_applies_search_and_settings(settings, parse_result):
    settings.REFERENSI_CONFIG["page_sizes"]["jobs"] = 25
    service = PreviewImportService(search_queries={"jobs": "pagar", "details": ""})

    page_data = service.build_job_page(parse_result, page=1)

    assert page_data.page_info.total_items == len(parse_result.jobs) // 3
    assert page_data.page_info.total_pages == 1
    assert all("pagar" in row["job"].nama_ahsp.lower() for row in page_data.rows)


def test_build_detail_page_filters_details(settings, parse_result):
    settings.REFERENSI_CONFIG["page_sizes"]["details"] = 10
    service = PreviewImportService(search_queries={"jobs": "", "details": "ITEM-000"})

    page_data = service.build_detail_page(parse_result, page=1)

    assert page_data.page_info.total_items > 0
    assert all("ITEM-000" in row["detail"].kode_item for row in page_data.rows)


def test_build_job_page_handles_missing_parse_result():
    service = PreviewImportService()
    page_data = service.build_job_page(None, page=1)

    assert page_data.page_info.total_items == 0
    assert page_data.rows == []


def test_import_session_manager_store_and_retrieve(tmp_path, monkeypatch):
    session = DummySession()
    manager = ImportSessionManager()
    parse_result = create_test_parse_result(num_jobs=1, details_per_job=1)

    # Store parse result and confirm session entry is created
    token = manager.store(session, parse_result, "sample.xlsx")
    assert manager.SESSION_KEY in session

    retrieved, filename, stored_token = manager.retrieve(session)
    assert filename == "sample.xlsx"
    assert stored_token == token
    assert retrieved.total_jobs == 1

    manager.cleanup(session)
    assert manager.SESSION_KEY not in session


def add_session_to_request(request):
    """Apply session and message middleware for view tests."""
    session_middleware = SessionMiddleware(lambda req: HttpResponse())
    session_middleware.process_request(request)
    request.session.save()

    messages_middleware = MessageMiddleware(lambda req: HttpResponse())
    messages_middleware.process_request(request)
    return request


@pytest.mark.django_db
def test_preview_import_view_passes_search_queries():
    factory = RequestFactory()
    request = factory.get("/referensi/preview/?search_jobs=beton&search_details=pasir")
    request.user = DummyUser(
        is_staff=True,
        perms={"referensi.view_ahspreferensi", "referensi.import_ahsp_data"},
    )
    request = add_session_to_request(request)

    with mock.patch("referensi.views.preview.PreviewImportService") as MockService, mock.patch(
        "referensi.views.preview.render", return_value=HttpResponse()
    ):
        service_instance = MockService.return_value
        # Prevent session lookups from raising errors during GET
        service_instance.session_manager.retrieve.return_value = (None, None, None)
        dummy_page = PageData(
            formset=mock.Mock(),
            rows=[],
            page_info=PageInfo(page=1, total_pages=1, total_items=0, start_index=0, end_index=0),
        )
        service_instance.build_job_page.return_value = dummy_page
        service_instance.build_detail_page.return_value = dummy_page

        response = preview_import(request)
        assert response.status_code == 200

    kwargs = MockService.call_args.kwargs
    assert kwargs["search_queries"] == {"jobs": "beton", "details": "pasir"}
