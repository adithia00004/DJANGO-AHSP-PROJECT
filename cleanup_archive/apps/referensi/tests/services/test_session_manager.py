from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone

from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.preview_service import ImportSessionManager


pytestmark = pytest.mark.django_db


def _build_parse_result() -> ParseResult:
    rincian = RincianPreview(
        kategori="TK",
        kode_item="TK-001",
        uraian_item="Mandor",
        satuan_item="OH",
        koefisien=Decimal("1"),
        row_number=2,
    )
    job = AHSPPreview(
        sumber="SNI 2025",
        kode_ahsp="01.01",
        nama_ahsp="Pekerjaan Tanah",
        row_number=1,
        rincian=[rincian],
    )
    return ParseResult(jobs=[job])


@pytest.fixture
def session():
    store = SessionStore()
    store.create()
    return store


def test_store_and_retrieve_roundtrip(session):
    manager = ImportSessionManager()

    parse_result = _build_parse_result()
    token = manager.store(session, parse_result, "data.xlsx")

    retrieved, name, stored_token = manager.retrieve(session)
    assert stored_token == token
    assert name == "data.xlsx"
    assert retrieved.total_jobs == 1
    assert retrieved.jobs[0].rincian_count == 1

    manager.cleanup(session)


def test_rewrite_updates_existing_file(session):
    manager = ImportSessionManager()
    parse_result = _build_parse_result()
    token = manager.store(session, parse_result, "data.xlsx")

    parse_result.jobs[0].nama_ahsp = "Perubahan"
    new_token = manager.rewrite(session, parse_result)
    assert new_token == token  # rewrite should keep same token

    retrieved, _, _ = manager.retrieve(session)
    assert retrieved.jobs[0].nama_ahsp == "Perubahan"

    manager.cleanup(session)


def test_cleanup_removes_session_and_file(session):
    manager = ImportSessionManager()
    manager.store(session, _build_parse_result(), "data.xlsx")

    manager.cleanup(session)
    with pytest.raises(FileNotFoundError):
        manager.retrieve(session)


def test_retrieve_expired_session_triggers_cleanup(session):
    manager = ImportSessionManager()
    manager.store(session, _build_parse_result(), "data.xlsx")

    data = session[manager.SESSION_KEY]
    expired_at = timezone.now() - timedelta(hours=manager.CLEANUP_AGE_HOURS + 1)
    data["created_at"] = expired_at.isoformat()
    session[manager.SESSION_KEY] = data

    with pytest.raises(FileNotFoundError):
        manager.retrieve(session)
    assert manager.SESSION_KEY not in session
