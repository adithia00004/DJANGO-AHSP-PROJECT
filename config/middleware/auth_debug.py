import logging
import time

from django.conf import settings
from django.db import connection, reset_queries
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger("auth_debug")


class AuthDebugMiddleware(MiddlewareMixin):
    """Log authentication flow for troubleshooting login failures."""

    def _is_auth_request(self, request) -> bool:
        return request.path.endswith("/accounts/login/")

    def process_request(self, request):
        if not self._is_auth_request(request):
            return None
        request._auth_start_ts = time.monotonic()
        if settings.DEBUG:
            reset_queries()

        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")

        user_label = "anon"
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            user_label = request.user.get_username() or str(request.user.pk)

        csrf_cookie = request.COOKIES.get("csrftoken")
        csrf_header = request.META.get("HTTP_X_CSRFTOKEN") or request.META.get("HTTP_X_CSRF_TOKEN")
        has_form_csrf = False
        if request.method == "POST":
            try:
                has_form_csrf = bool(request.POST.get("csrfmiddlewaretoken"))
            except Exception:
                has_form_csrf = False

        logger.info(
            "auth_request method=%s path=%s user=%s session=%s ip=%s csrf_cookie=%s csrf_header=%s form_csrf=%s",
            request.method,
            request.path,
            user_label,
            getattr(request.session, "session_key", None),
            client_ip,
            bool(csrf_cookie),
            bool(csrf_header),
            has_form_csrf,
        )
        return None

    def process_response(self, request, response):
        if not self._is_auth_request(request):
            return response

        user_label = "anon"
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            user_label = request.user.get_username() or str(request.user.pk)

        duration_ms = None
        start_ts = getattr(request, "_auth_start_ts", None)
        if start_ts is not None:
            duration_ms = (time.monotonic() - start_ts) * 1000

        db_queries = None
        db_time_ms = None
        if settings.DEBUG:
            try:
                queries = connection.queries
                db_queries = len(queries)
                db_time_ms = sum(float(q.get("time", 0.0)) for q in queries) * 1000
            except Exception:
                db_queries = None
                db_time_ms = None

        logger.info(
            "auth_response status=%s method=%s path=%s user=%s duration_ms=%s db_queries=%s db_time_ms=%s",
            response.status_code,
            request.method,
            request.path,
            user_label,
            f"{duration_ms:.2f}" if duration_ms is not None else "n/a",
            db_queries if db_queries is not None else "n/a",
            f"{db_time_ms:.2f}" if db_time_ms is not None else "n/a",
        )

        if response.status_code >= 500:
            logger.error("auth_failure status=%s path=%s", response.status_code, request.path)

        return response
