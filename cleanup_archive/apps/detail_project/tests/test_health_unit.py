import json
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from detail_project import views_health


@pytest.fixture
def rf():
    """Provide a lightweight request factory for view unit tests."""
    return RequestFactory()


def _payload(response):
    return json.loads(response.content.decode("utf-8"))


def test_health_check_simple_mode_short_circuits(rf):
    """Explicit ?mode=simple should skip expensive dependency probes."""
    request = rf.get("/health/", {"mode": "simple"})
    request.user = AnonymousUser()

    response = views_health.health_check(request)
    data = _payload(response)

    assert response.status_code == 200
    assert data["checks"]["mode"] == "simple"
    # Database/cache checks should be skipped entirely
    assert set(data["checks"].keys()) == {"mode"}


def test_health_check_authenticated_defaults_to_simple(rf):
    """Authenticated monitoring tools hit the fast path unless mode=deep."""
    request = rf.get("/health/")
    request.user = SimpleNamespace(is_authenticated=True)

    response = views_health.health_check(request)
    data = _payload(response)

    assert response.status_code == 200
    assert data["checks"]["mode"] == "simple"
    assert data["status"] == "ok"


def test_health_check_reports_dependency_errors(monkeypatch, rf):
    """Deep mode should surface dependency regressions cleanly."""
    request = rf.get("/health/", {"mode": "deep"})
    request.user = AnonymousUser()

    class DummyCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            self.last_sql = sql

        def fetchone(self):
            # Force unexpected SELECT 1 result to hit error branch
            return (0,)

    monkeypatch.setattr(
        views_health.connection,
        "cursor",
        lambda: DummyCursor(),
    )

    class BrokenCache:
        def set(self, key, value, timeout=None):
            return None

        def get(self, key):
            return "not-ok"

        def delete(self, key):
            return None

    monkeypatch.setattr(views_health, "cache", BrokenCache())

    response = views_health.health_check(request)
    data = _payload(response)

    assert response.status_code == 503
    assert data["status"] == "error"
    assert data["checks"]["database"]["status"] == "error"
    assert data["checks"]["cache"]["status"] == "error"
