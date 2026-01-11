import logging

from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger("auth_debug")


class AuthDebugMiddleware(MiddlewareMixin):
    """Log authentication flow for troubleshooting login failures."""

    def _is_auth_request(self, request) -> bool:
        return request.path.endswith("/accounts/login/")

    def process_request(self, request):
        if not self._is_auth_request(request):
            return None

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

        logger.info(
            "auth_response status=%s path=%s user=%s",
            response.status_code,
            request.path,
            user_label,
        )

        if response.status_code >= 500:
            logger.error("auth_failure status=%s path=%s", response.status_code, request.path)

        return response
