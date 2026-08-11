"""Fixtures shared by the whole test suite."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Give every test a clean cache.

    The API rate limiters key on (user id, endpoint, method, time bucket) and
    keep their counters in the process-wide LocMemCache. Under SQLite the
    per-test rollback lets primary keys recur, so consecutive tests act as the
    same user id inside one 60-second bucket -- counters add up across tests
    until a later one is answered with a spurious 429:

        AssertionError: 429 != 400
        "limit": 20, "current_count": 26, "category": "write"
        Rate limit exceeded for user 2 on api_upsert_list_pekerjaan (POST)

    Those failures surface only in a full run and vanish when the file runs
    alone, so they read as flakiness rather than as shared state. Clearing the
    cache between tests removes the shared state instead of switching the
    limiter off, which keeps tests that assert on 429 exercising the real
    limiter (detail_project/tests_rate_limit_v2.py,
    detail_project/tests_monitoring_security.py).
    """
    cache.clear()
    yield
    cache.clear()
