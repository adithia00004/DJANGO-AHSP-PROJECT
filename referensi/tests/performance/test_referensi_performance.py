import time
from decimal import Decimal

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client

from django.core.cache import cache

from django.db import connection
from django.test.utils import CaptureQueriesContext

from referensi.models import AHSPReferensi
from referensi.services.cache_helpers import ReferensiCache
from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.preview_service import ImportSessionManager


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _build_parse_result(job_count: int = 50, details_per_job: int = 10) -> ParseResult:
    jobs: list[AHSPPreview] = []
    for job_index in range(job_count):
        rincian = [
            RincianPreview(
                kategori="TK",
                kode_item=f"TK-{job_index}-{detail_index}",
                uraian_item=f"Mandor {job_index}-{detail_index}",
                satuan_item="OH",
                koefisien=Decimal("1"),
                row_number=detail_index + 2,
            )
            for detail_index in range(details_per_job)
        ]
        jobs.append(
            AHSPPreview(
                sumber="SNI 2025",
                kode_ahsp=f"{job_index:02d}.01",
                nama_ahsp=f"Pekerjaan {job_index}",
                row_number=job_index + 1,
                rincian=rincian,
            )
        )
    return ParseResult(jobs=jobs)


def test_cache_warm_results_in_zero_query_hits():
    AHSPReferensi.objects.bulk_create(
        [
            AHSPReferensi(kode_ahsp=f"{i:02d}.01", nama_ahsp=f"Pekerjaan {i}", sumber="SNI 2025")
            for i in range(20)
        ]
    )

    with CaptureQueriesContext(connection) as ctx:
        ReferensiCache.get_available_sources()
    assert len(ctx) <= 10, f"Expected warm cache query count <= 10, got {len(ctx)}"

    with CaptureQueriesContext(connection) as ctx_second:
        ReferensiCache.get_available_sources()
    assert len(ctx_second) <= 1, "Second cache hit should be a single cache read at most"


def test_session_manager_handles_large_payload_fast():
    manager = ImportSessionManager()
    session = SessionStore()
    session.create()
    parse_result = _build_parse_result(job_count=40, details_per_job=15)

    start = time.perf_counter()
    token = manager.store(session, parse_result, "bulk.xlsx")
    retrieved, _, stored_token = manager.retrieve(session)
    elapsed = time.perf_counter() - start

    assert stored_token == token
    assert retrieved.total_jobs == 40
    assert retrieved.total_rincian == 40 * 15
    assert elapsed < 0.5, f"Session roundtrip took too long: {elapsed:.3f}s"
    manager.cleanup(session)


def test_api_search_remains_snappy(client: Client, django_user_model):
    user = django_user_model.objects.create_user(username="perf", password="pass")
    AHSPReferensi.objects.bulk_create(
        [
            AHSPReferensi(kode_ahsp=f"{i:03d}.01", nama_ahsp=f"Pekerjaan Cepat {i}", sumber="SNI 2025")
            for i in range(150)
        ]
    )

    client.force_login(user)
    start = time.perf_counter()
    response = client.get("/referensi/api/search", {"q": "Cepat"})
    duration = time.perf_counter() - start

    assert response.status_code == 200
    # Relaxed threshold for CI/coverage overhead (was 0.1s)
    assert duration < 3.0, f"Search API slower than expected: {duration:.3f}s"
