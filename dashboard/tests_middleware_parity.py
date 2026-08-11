"""Guard: the test settings must exercise the same middleware stack as production.

`TimeoutMiddleware` ran every request inside a fresh `threading.Thread`. Django
keeps database connections in thread-local storage and closes them from the
`request_finished` signal, which fires on the *parent* thread -- so every request
orphaned one PostgreSQL connection. Those connections piled up until the server
refused new ones with "sorry, too many clients already".

The middleware also broke `force_login`, and the response was to filter it out of
the test settings rather than to fix it. That divergence is what let the leak
survive: no test ever ran the stack production actually used.

If a middleware has to be dropped to make the suite pass, fix the middleware.
"""

import inspect
from importlib import import_module

from django.conf import settings
from django.test import SimpleTestCase


class MiddlewareParityTests(SimpleTestCase):
    def test_test_settings_keep_every_production_middleware(self):
        base = import_module("config.settings.base")

        dropped = [m for m in base.MIDDLEWARE if m not in settings.MIDDLEWARE]

        self.assertEqual(
            dropped,
            [],
            "The active test settings drop middleware that production runs: "
            f"{dropped}. Tests would then validate a stack that never ships. "
            "Fix the middleware instead of filtering it out.",
        )

    def test_no_middleware_runs_the_view_in_another_thread(self):
        """Middleware must keep request handling on the worker thread.

        Django's connection lifecycle is thread-local, so a middleware that
        calls `get_response` from a thread it spawned orphans that thread's
        database connection.
        """
        offenders = []
        for path in settings.MIDDLEWARE:
            module_name = path.rpartition(".")[0]
            try:
                source = inspect.getsource(import_module(module_name))
            except (OSError, TypeError):  # pragma: no cover - compiled module
                continue
            if "threading.Thread(" in source or "ThreadPoolExecutor(" in source:
                offenders.append(path)

        self.assertEqual(
            offenders,
            [],
            f"These middleware spawn threads: {offenders}. Request handling must "
            "stay on the worker thread so Django can close its database "
            "connection; if a thread is genuinely required, call "
            "`connections.close_all()` in a `finally` block inside it.",
        )
