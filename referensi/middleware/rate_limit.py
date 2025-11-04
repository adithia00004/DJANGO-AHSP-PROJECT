"""
Rate limiting middleware for AHSP file imports.

This middleware protects the application from abuse by limiting the number
of file import attempts per user within a time window.

Features:
- Per-user rate limiting
- Configurable limits and time windows
- Django cache backend support
- Detailed rate limit headers
- JSON error responses for API requests
- HTML error page for browser requests
"""

from __future__ import annotations

import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _


class ImportRateLimitMiddleware:
    """
    Middleware to rate limit file import operations.

    Configuration (in settings.py):
        IMPORT_RATE_LIMIT = 10  # Max imports per window
        IMPORT_RATE_WINDOW = 3600  # Time window in seconds (default: 1 hour)
        IMPORT_RATE_LIMIT_PATHS = ['/referensi/preview/']  # Paths to protect

    The middleware tracks import attempts per user and returns HTTP 429
    (Too Many Requests) when the limit is exceeded.

    Rate limit information is included in response headers:
        X-RateLimit-Limit: Maximum requests allowed
        X-RateLimit-Remaining: Requests remaining
        X-RateLimit-Reset: Unix timestamp when limit resets
    """

    # Default configuration
    DEFAULT_RATE_LIMIT = 10  # Max imports per window
    DEFAULT_RATE_WINDOW = 3600  # 1 hour in seconds
    DEFAULT_PROTECTED_PATHS = [
        '/referensi/preview/',
        '/referensi/admin/import/',
    ]

    def __init__(self, get_response: Callable):
        """
        Initialize middleware.

        Args:
            get_response: Next middleware or view in the chain
        """
        self.get_response = get_response

        # Load configuration from settings
        self.rate_limit = getattr(
            settings,
            'IMPORT_RATE_LIMIT',
            self.DEFAULT_RATE_LIMIT
        )
        self.rate_window = getattr(
            settings,
            'IMPORT_RATE_WINDOW',
            self.DEFAULT_RATE_WINDOW
        )
        self.protected_paths = getattr(
            settings,
            'IMPORT_RATE_LIMIT_PATHS',
            self.DEFAULT_PROTECTED_PATHS
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process request and apply rate limiting.

        Args:
            request: Django HttpRequest

        Returns:
            HttpResponse or JsonResponse (429 if rate limited)
        """
        # Check if this path should be rate limited
        if not self._should_rate_limit(request):
            return self.get_response(request)

        # Skip rate limiting for unauthenticated users on GET requests
        # (they can't actually import, just view the page)
        if not request.user.is_authenticated and request.method == 'GET':
            return self.get_response(request)

        # Check rate limit
        is_allowed, remaining, reset_time = self._check_rate_limit(request)

        # Add rate limit headers to response
        response = None
        if is_allowed:
            response = self.get_response(request)
        else:
            # Log rate limit exceeded event
            from referensi.services.audit_logger import audit_logger
            audit_logger.log_rate_limit_exceeded(
                request=request,
                limit=self.rate_limit,
                window=self.rate_window
            )

            response = self._create_rate_limit_response(request)

        # Add headers
        response['X-RateLimit-Limit'] = str(self.rate_limit)
        response['X-RateLimit-Remaining'] = str(max(0, remaining))
        response['X-RateLimit-Reset'] = str(int(reset_time))
        response['Retry-After'] = str(int(reset_time - time.time()))

        return response

    def _should_rate_limit(self, request: HttpRequest) -> bool:
        """
        Determine if request should be rate limited.

        Args:
            request: Django HttpRequest

        Returns:
            True if request should be rate limited
        """
        path = request.path

        # Check if path matches any protected paths
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True

        return False

    def _check_rate_limit(self, request: HttpRequest) -> tuple[bool, int, float]:
        """
        Check if user has exceeded rate limit.

        Args:
            request: Django HttpRequest

        Returns:
            Tuple of (is_allowed, requests_remaining, reset_timestamp)
        """
        # Generate cache key
        cache_key = self._get_cache_key(request)

        # Get current count and reset time
        cache_data = cache.get(cache_key)

        current_time = time.time()

        if cache_data is None:
            # First request in this window
            count = 1
            reset_time = current_time + self.rate_window

            # Store in cache
            cache.set(
                cache_key,
                {'count': count, 'reset_time': reset_time},
                timeout=self.rate_window
            )

            return True, self.rate_limit - count, reset_time

        # Existing window
        count = cache_data.get('count', 0)
        reset_time = cache_data.get('reset_time', current_time + self.rate_window)

        # Check if window has expired
        if current_time >= reset_time:
            # Reset window
            count = 1
            reset_time = current_time + self.rate_window

            cache.set(
                cache_key,
                {'count': count, 'reset_time': reset_time},
                timeout=self.rate_window
            )

            return True, self.rate_limit - count, reset_time

        # Within window - check limit
        if count >= self.rate_limit:
            # Rate limit exceeded
            return False, 0, reset_time

        # Increment count
        count += 1
        cache.set(
            cache_key,
            {'count': count, 'reset_time': reset_time},
            timeout=int(reset_time - current_time) + 1
        )

        return True, self.rate_limit - count, reset_time

    def _get_cache_key(self, request: HttpRequest) -> str:
        """
        Generate cache key for rate limiting.

        Args:
            request: Django HttpRequest

        Returns:
            Cache key string
        """
        if request.user.is_authenticated:
            # Use user ID for authenticated users
            user_id = request.user.id
            return f"import_rate_limit:user:{user_id}"
        else:
            # Use IP address for anonymous users
            ip_address = self._get_client_ip(request)
            return f"import_rate_limit:ip:{ip_address}"

    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Get client IP address from request.

        Handles proxy headers (X-Forwarded-For) correctly.

        Args:
            request: Django HttpRequest

        Returns:
            IP address string
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get first IP in chain (client IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')

        return ip

    def _create_rate_limit_response(self, request: HttpRequest) -> HttpResponse:
        """
        Create appropriate response for rate limit exceeded.

        Args:
            request: Django HttpRequest

        Returns:
            JsonResponse or HTML response with 429 status
        """
        # Check if this is an AJAX/API request
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.content_type == 'application/json'
            or 'application/json' in request.headers.get('Accept', '')
        )

        error_message = _(
            f"Terlalu banyak permintaan import. "
            f"Batas: {self.rate_limit} per {self._format_window()}. "
            f"Silakan coba lagi nanti."
        )

        if is_ajax:
            # Return JSON response
            return JsonResponse(
                {
                    'error': 'rate_limit_exceeded',
                    'message': error_message,
                    'limit': self.rate_limit,
                    'window': self.rate_window,
                },
                status=429
            )

        # Return HTML response
        context = {
            'error_title': _('Terlalu Banyak Permintaan'),
            'error_message': error_message,
            'rate_limit': self.rate_limit,
            'rate_window': self._format_window(),
        }

        return render(
            request,
            'referensi/errors/rate_limit.html',
            context,
            status=429
        )

    def _format_window(self) -> str:
        """
        Format rate window for display.

        Returns:
            Human-readable time window string
        """
        if self.rate_window < 60:
            return f"{self.rate_window} detik"
        elif self.rate_window < 3600:
            minutes = self.rate_window // 60
            return f"{minutes} menit"
        else:
            hours = self.rate_window // 3600
            return f"{hours} jam"


class RateLimitChecker:
    """
    Utility class to check rate limits programmatically.

    Usage:
        checker = RateLimitChecker()
        is_allowed = checker.check_user_limit(user_id)

        if not is_allowed:
            # User has exceeded rate limit
            remaining_time = checker.get_remaining_time(user_id)
            print(f"Rate limited. Try again in {remaining_time} seconds")
    """

    def __init__(
        self,
        rate_limit: int | None = None,
        rate_window: int | None = None
    ):
        """
        Initialize rate limit checker.

        Args:
            rate_limit: Maximum requests per window
            rate_window: Time window in seconds
        """
        self.rate_limit = rate_limit or ImportRateLimitMiddleware.DEFAULT_RATE_LIMIT
        self.rate_window = rate_window or ImportRateLimitMiddleware.DEFAULT_RATE_WINDOW

    def check_user_limit(self, user_id: int) -> bool:
        """
        Check if user has exceeded rate limit.

        Args:
            user_id: User ID

        Returns:
            True if user is within rate limit
        """
        cache_key = f"import_rate_limit:user:{user_id}"
        cache_data = cache.get(cache_key)

        if cache_data is None:
            return True

        current_time = time.time()
        count = cache_data.get('count', 0)
        reset_time = cache_data.get('reset_time', current_time)

        # Check if window expired
        if current_time >= reset_time:
            return True

        return count < self.rate_limit

    def get_remaining_time(self, user_id: int) -> int:
        """
        Get remaining time until rate limit resets.

        Args:
            user_id: User ID

        Returns:
            Seconds until reset (0 if not rate limited)
        """
        cache_key = f"import_rate_limit:user:{user_id}"
        cache_data = cache.get(cache_key)

        if cache_data is None:
            return 0

        current_time = time.time()
        reset_time = cache_data.get('reset_time', current_time)

        remaining = int(reset_time - current_time)
        return max(0, remaining)

    def get_remaining_requests(self, user_id: int) -> int:
        """
        Get remaining requests in current window.

        Args:
            user_id: User ID

        Returns:
            Number of requests remaining
        """
        cache_key = f"import_rate_limit:user:{user_id}"
        cache_data = cache.get(cache_key)

        if cache_data is None:
            return self.rate_limit

        current_time = time.time()
        count = cache_data.get('count', 0)
        reset_time = cache_data.get('reset_time', current_time)

        # Check if window expired
        if current_time >= reset_time:
            return self.rate_limit

        remaining = self.rate_limit - count
        return max(0, remaining)
