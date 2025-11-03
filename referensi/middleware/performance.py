"""
Middleware for logging slow requests in production.
"""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("performance")


class PerformanceLoggingMiddleware:
    """
    Log any requests exceeding ``settings.PERFORMANCE_LOG_THRESHOLD`` seconds.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.threshold = getattr(settings, "PERFORMANCE_LOG_THRESHOLD", 1.0)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start

        if duration >= self.threshold:
            logger.warning(
                "slow_request",
                extra={
                    "path": request.path,
                    "method": request.method,
                    "status_code": getattr(response, "status_code", None),
                    "duration": round(duration, 3),
                    "user_id": getattr(getattr(request, "user", None), "id", None),
                },
            )
        return response
