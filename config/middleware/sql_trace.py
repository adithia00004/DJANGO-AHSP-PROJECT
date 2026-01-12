import logging
import os
import time

from django.conf import settings
from django.db import connection, reset_queries
from django.utils.deprecation import MiddlewareMixin


class SQLTraceMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.enabled = os.getenv("SQL_TRACE", "False").lower() in ("true", "1", "yes")
        self.min_ms = float(os.getenv("SQL_TRACE_MIN_MS", "50"))
        self.logger = logging.getLogger("sql_trace")

    def process_request(self, request):
        if not self.enabled:
            return None
        connection.force_debug_cursor = True
        if settings.DEBUG:
            reset_queries()
        request._sql_trace_start_ts = time.monotonic()
        request._sql_trace_state = {"count": 0, "db_ms": 0.0}

        def _wrap(execute, sql, params, many, context):
            start = time.monotonic()
            try:
                return execute(sql, params, many, context)
            finally:
                duration_ms = (time.monotonic() - start) * 1000.0
                request._sql_trace_state["count"] += 1
                request._sql_trace_state["db_ms"] += duration_ms
                if self.min_ms and duration_ms >= self.min_ms:
                    compact_sql = (sql or "").replace("\n", " ")
                    self.logger.info("db_ms=%.2f sql=%s", duration_ms, compact_sql)

        request._sql_trace_wrapper = connection.execute_wrapper(_wrap)
        request._sql_trace_wrapper.__enter__()
        return None

    def _finalize(self, request, response):
        wrapper = getattr(request, "_sql_trace_wrapper", None)
        if wrapper is not None:
            try:
                wrapper.__exit__(None, None, None)
            except Exception:
                pass
        duration_ms = None
        start_ts = getattr(request, "_sql_trace_start_ts", None)
        if start_ts is not None:
            duration_ms = (time.monotonic() - start_ts) * 1000.0

        state = getattr(request, "_sql_trace_state", {})
        queries_count = int(state.get("count", 0) or 0)
        total_db_ms = float(state.get("db_ms", 0.0) or 0.0)

        self.logger.info(
            "path=%s status=%s queries=%s db_ms=%.2f total_ms=%.2f",
            request.path,
            response.status_code,
            queries_count,
            total_db_ms,
            duration_ms or 0.0,
        )

        return response

    def process_response(self, request, response):
        if not self.enabled:
            return response
        if hasattr(response, "render") and not getattr(response, "is_rendered", True):
            # Log after template rendering so queries executed during render are counted.
            response.add_post_render_callback(lambda resp: self._finalize(request, resp))
            return response
        return self._finalize(request, response)

    def process_exception(self, request, exception):
        if not self.enabled:
            return None
        try:
            self._finalize(request, getattr(exception, "response", None) or getattr(request, "response", None) or request)
        except Exception:
            pass
        return None
