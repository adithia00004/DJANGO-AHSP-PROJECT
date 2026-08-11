"""Guardrails for the PostgreSQL connection lifecycle.

`idle_session_timeout` is the safety net that stops an abandoned connection from
holding a server slot until the process restarts -- the failure mode that took
the app down with "sorry, too many clients already". It is only safe while two
invariants hold:

1. it stays above CONN_MAX_AGE, so Django retires its own persistent
   connections before the server reclaims them; and
2. CONN_HEALTH_CHECKS stays on, so a connection the server did reclaim gets
   replaced instead of surfacing as "connection already closed" mid-request.

Break either one and the safety net becomes a source of random errors.

The test settings swap in SQLite, so these assertions read the PostgreSQL
configuration from `config.settings.base` directly.
"""

import re
from importlib import import_module

from django.test import SimpleTestCase


class ConnectionLifecycleGuardrailTests(SimpleTestCase):
    def setUp(self):
        self.db = import_module("config.settings.base").DATABASES["default"]
        if "postgresql" not in self.db["ENGINE"]:
            self.skipTest("base settings are not configured for PostgreSQL")
        if "options" not in self.db["OPTIONS"]:
            self.skipTest("PgBouncer mode: server-side options are deliberately unset")

    def _idle_session_timeout_ms(self):
        match = re.search(r"idle_session_timeout=(\d+)", self.db["OPTIONS"]["options"])
        self.assertIsNotNone(
            match,
            "idle_session_timeout is missing from the connection options; an "
            "abandoned connection would hold its server slot indefinitely.",
        )
        return int(match.group(1))

    def test_idle_session_timeout_outlives_conn_max_age(self):
        timeout_ms = self._idle_session_timeout_ms()
        if timeout_ms == 0:
            self.skipTest("idle_session_timeout explicitly disabled")

        conn_max_age_ms = self.db["CONN_MAX_AGE"] * 1000
        self.assertGreater(
            timeout_ms,
            conn_max_age_ms,
            f"idle_session_timeout ({timeout_ms}ms) must stay above CONN_MAX_AGE "
            f"({conn_max_age_ms}ms) so Django retires its persistent connections "
            "before the server reclaims them.",
        )

    def test_health_checks_on_while_server_can_reclaim_connections(self):
        if self._idle_session_timeout_ms() == 0:
            self.skipTest("idle_session_timeout explicitly disabled")

        self.assertTrue(
            self.db["CONN_HEALTH_CHECKS"],
            "CONN_HEALTH_CHECKS must stay on while the server can reclaim idle "
            "connections, otherwise Django hands a dead connection to the next "
            "request instead of reconnecting.",
        )
