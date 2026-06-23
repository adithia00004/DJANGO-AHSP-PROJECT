"""
PostgreSQL 15 test settings.

Verifies backend-specific behaviour the default SQLite test settings cannot
prove: A12 row locking (`select_for_update`) and A13 `UniqueConstraint`
`nulls_distinct=False` (PostgreSQL `NULLS NOT DISTINCT`).

Inherits all the test overrides (schema built directly from models, locmem
cache, TimeoutMiddleware removed, eager Celery, ...) but runs against the
project's PostgreSQL database. Use for the PG-only integration tests, e.g.:

    python manage.py test subscriptions.tests_pg --settings=config.settings.test_pg
"""
from __future__ import annotations

import os

from .test import *  # noqa: F401,F403
from .base import DATABASES  # noqa: F401  re-bind to the PostgreSQL configuration

# Run against a dedicated PostgreSQL test database (CREATEDB required).
DATABASES["default"].setdefault("TEST", {})["NAME"] = os.getenv(
    "POSTGRES_TEST_DB", "test_ahsp_sni_db"
)
