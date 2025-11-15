from types import SimpleNamespace

import pytest

from detail_project import apps as detail_apps
import django.db.backends.utils as db_utils


class DummyCursorWrapper:
    """Minimal cursor wrapper to observe SQL rewrites."""

    def __init__(self):
        self.db = SimpleNamespace(vendor="sqlite")
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append(sql.strip())
        return "ok"


def _cursor_cm(result=("detail_project_projectparameter",)):
    class CursorCM:
        def __init__(self):
            self.commands = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            self.commands.append(sql.strip())

        def fetchone(self):
            return result

    return CursorCM()


def test_patch_sqlite_explain_rewrites_refresh_and_explain(monkeypatch):
    monkeypatch.setattr(detail_apps, "_SQLITE_EXPLAIN_PATCHED", False)
    monkeypatch.setattr(db_utils, "CursorWrapper", DummyCursorWrapper)

    detail_apps._patch_sqlite_explain()

    wrapper = db_utils.CursorWrapper()
    wrapper.execute("EXPLAIN SELECT 1")
    assert wrapper.calls[-1].startswith("EXPLAIN QUERY PLAN")

    wrapper_refresh = db_utils.CursorWrapper()
    wrapper_refresh.execute("REFRESH MATERIALIZED VIEW referensi_ahsp_stats")
    assert "DROP TABLE IF EXISTS referensi_ahsp_stats" in wrapper_refresh.calls[0]
    assert "CREATE TABLE referensi_ahsp_stats AS" in wrapper_refresh.calls[1]


def test_patch_sqlite_explain_is_idempotent(monkeypatch):
    monkeypatch.setattr(detail_apps, "_SQLITE_EXPLAIN_PATCHED", True)
    # Should simply return without touching CursorWrapper
    detail_apps._patch_sqlite_explain()


def test_ensure_projectparameter_index_skips_non_sqlite():
    connection = SimpleNamespace(vendor="postgres", cursor=lambda: None)
    detail_apps.ensure_projectparameter_index(connection=connection)


def test_ensure_projectparameter_index_creates_index_when_table_exists(monkeypatch):
    cursor = _cursor_cm()
    connection = SimpleNamespace(vendor="sqlite", cursor=lambda: cursor)
    detail_apps.ensure_projectparameter_index(connection=connection)

    assert any(
        cmd.startswith("CREATE INDEX IF NOT EXISTS detail_project_param_project_name_idx")
        for cmd in cursor.commands
    )


def test_ensure_projectparameter_index_logs_exceptions(monkeypatch):
    class ExplodingCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            raise RuntimeError("boom")

    connection = SimpleNamespace(vendor="sqlite", cursor=lambda: ExplodingCursor())
    logs = []

    class DummyLogger:
        def debug(self, message, *args):
            logs.append(message)

    monkeypatch.setattr(detail_apps, "logger", DummyLogger())
    detail_apps.ensure_projectparameter_index(connection=connection)
    assert logs, "Exception branch should log diagnostic message"


def test_warmup_health_check_skips_without_env(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    called = []

    class DummyClient:
        def __init__(self):
            called.append("instantiated")

        def get(self, path):
            called.append(path)

    monkeypatch.setattr("django.test.Client", DummyClient)
    detail_apps.warmup_health_check(sender=None)
    # Without env flag the client should never be constructed
    assert called == []


def test_warmup_health_check_hits_endpoint_when_enabled(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test-node")
    hits = []

    class DummyClient:
        def get(self, path):
            hits.append(path)

    monkeypatch.setattr("django.test.Client", DummyClient)
    detail_apps.warmup_health_check(sender=None)
    assert hits == ["/health/"]


def test_warmup_health_check_handles_client_failures(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test-node")

    class ExplodingClient:
        def get(self, path):
            raise RuntimeError("unreachable during warmup")

    logs = []

    class DummyLogger:
        def debug(self, message, *args):
            logs.append(message)

    monkeypatch.setattr("django.test.Client", ExplodingClient)
    monkeypatch.setattr(detail_apps, "logger", DummyLogger())

    detail_apps.warmup_health_check(sender=None)
    assert logs
