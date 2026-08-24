# detail_project/api_helpers.py
"""
API Helper Utilities for detail_project app

Provides:
- Rate limiting decorators
- Standardized API responses
- Common validation helpers
"""

import functools
import logging
import math
import time
from typing import Any, Dict, Optional, List
from django.http import JsonResponse, QueryDict
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction as _db_transaction

logger = logging.getLogger(__name__)


# ============================================================================
# WP-B3: ATOMIC MUTATION CONVENTION (B-1 / A-5)
# ============================================================================

def atomic_error_response(errors=None, *, status=400, message=None, **extra):
    """Reject an atomic save as all-or-nothing.

    Rolls back the *current* transaction (so no partial write survives) and
    returns a consistent error envelope. Use for any single save/form where
    one or more items failed validation or processing.

    Contract (doc 26 A-5 / B-1):
    - single save = 200 / 400-422 / 500 — NEVER 207 (207 only for genuinely
      independent batches, e.g. multiple exports/projects);
    - response must NOT claim any item was saved;
    - last-write-wins: no optimistic-locking 409 here.

    Must be called inside a ``transaction.atomic`` block.
    """
    _db_transaction.set_rollback(True)
    errors = errors or []
    msg = message or "Perubahan ditolak. Tidak ada perubahan yang disimpan."
    payload = {
        "ok": False,
        "success": False,
        "error": msg,
        "message": msg,
        "errors": errors,
    }
    payload.update(extra)
    return JsonResponse(payload, status=status)


# ============================================================================
# RATE LIMITING
# ============================================================================

# Category-based rate limits for different endpoint types
RATE_LIMIT_CATEGORIES = {
    'bulk': {
        'max_requests': 5,
        'window': 300,  # 5 minutes
        'description': 'Bulk operations (deep copy, batch operations)'
    },
    'write': {
        'max_requests': 20,
        'window': 60,  # 1 minute
        'description': 'Normal write operations (save, update)'
    },
    'write_interactive': {
        'max_requests': 60,
        'window': 60,
        'description': 'Frequent interactive writes (manual save per pekerjaan)'
    },
    'sync_frequent': {
        'max_requests': 240,
        'window': 60,
        'description': 'Frequent autosave/sync operations'
    },
    'read': {
        'max_requests': 100,
        'window': 60,  # 1 minute
        'description': 'Read operations (search, list, get)'
    },
    'read_interactive': {
        'max_requests': 240,
        'window': 60,
        'description': 'Interactive reads and UI polling'
    },
    'export': {
        'max_requests': 10,
        'window': 60,  # 1 minute
        'description': 'Export operations (PDF, Excel, CSV)'
    },
}


def _rate_limit_increment(cache_key: str, timeout: int) -> int:
    """Atomically increment a fixed-window counter.

    ``cache.get()`` followed by ``cache.set()`` loses increments when two web
    workers handle requests concurrently.  ``add`` creates the first counter
    and ``incr`` performs subsequent updates atomically on the supported Redis
    backend (and under LocMem's cache lock in tests/development).

    A key can expire between ``add`` and ``incr``.  Retrying the create path
    once handles that narrow race without an unbounded loop.
    """
    if cache.add(cache_key, 1, timeout=timeout):
        return 1
    try:
        return int(cache.incr(cache_key))
    except ValueError:
        if cache.add(cache_key, 1, timeout=timeout):
            return 1
        return int(cache.incr(cache_key))


def _category_limits(category: str):
    """Resolve a category with optional deployment-level overrides."""
    limits = RATE_LIMIT_CATEGORIES.get(category)
    if not limits:
        return None
    overrides = getattr(settings, 'DETAIL_PROJECT_RATE_LIMIT_OVERRIDES', {}) or {}
    override = overrides.get(category, {}) if isinstance(overrides, dict) else {}
    return {**limits, **override}


def _record_rate_limit_metric(metric: str, endpoint: str = None, method: str = None, category: str = None):
    """Record low-cardinality limiter telemetry without affecting requests."""
    suffix = ''
    if endpoint:
        suffix = f":{endpoint}:{method or 'UNKNOWN'}:{category or 'default'}"
    keys = [
        f"metric:rate_limit_v2:{metric}:global",
        f"metric:rate_limit_v2:{metric}{suffix}",
    ]
    for key in keys:
        try:
            if not cache.add(key, 1, timeout=3600):
                cache.incr(key)
        except ValueError:
            try:
                if not cache.add(key, 1, timeout=3600):
                    cache.incr(key)
            except Exception:
                logger.debug("Failed to increment rate-limit metric %s", key, exc_info=True)
        except Exception:
            logger.debug("Failed to increment rate-limit metric %s", key, exc_info=True)


def get_rate_limit_metrics():
    """Return global v2 limiter telemetry for admin monitoring."""
    metrics = {}
    for name in ('allowed', 'blocked', 'would_block', 'near_limit', 'backend_error'):
        try:
            metrics[name] = int(cache.get(f'metric:rate_limit_v2:{name}:global', 0))
        except Exception:
            metrics[name] = 0
    return metrics


def rate_limit(
    max_requests: int = 100,
    window: int = 60,
    key_prefix: str = None,
    category: str = None,
    methods=None,
):
    """
    Rate limiting decorator for API endpoints with category support.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window: Time window in seconds (default: 60 seconds)
        key_prefix: Custom prefix for cache key (default: use view name)
        category: Rate limit category (for example 'bulk', 'write',
                 'write_interactive', 'sync_frequent', 'read', or 'export')
                 If provided, overrides max_requests and window with category defaults
        methods: Optional iterable of HTTP methods to count. Requests using a
                 different method pass through without consuming this quota.

    Returns:
        Decorator function

    Usage:
        # Using explicit limits
        @rate_limit(max_requests=10, window=60)
        def my_api_view(request, project_id):
            ...

        # Using category (recommended)
        @rate_limit(category='bulk')
        def deep_copy_view(request, project_id):
            # Automatically gets: 5 requests per 5 minutes
            ...

    The counter uses an absolute fixed-time bucket. Successful requests do not
    extend the bucket TTL. When ``methods`` is supplied, other HTTP methods do
    not consume this category's quota.

    Example:
        # Deep copy - expensive operation
        @rate_limit(category='bulk')
        def api_deep_copy_project(request):
            ...

        # Normal save - moderate limit
        @rate_limit(category='write')
        def api_save_pekerjaan(request):
            ...

        # Search - high limit
        @rate_limit(category='read')
        def api_search_ahsp(request):
            ...
    """
    # Apply category limits if specified
    if category and category in RATE_LIMIT_CATEGORIES:
        limits = _category_limits(category)
        max_requests = limits['max_requests']
        window = limits['window']
        logger.debug(
            f"Applying category '{category}' limits: {max_requests} req/{window}s"
        )

    method_set = None
    if methods is not None:
        if isinstance(methods, str):
            method_set = {methods.upper()}
        else:
            method_set = {str(item).upper() for item in methods}

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            method = str(getattr(request, 'method', '') or '').upper()
            if method_set is not None:
                if method not in method_set:
                    return view_func(request, *args, **kwargs)

            mode = str(getattr(settings, 'DETAIL_PROJECT_RATE_LIMIT_MODE', 'v2')).lower()
            if mode not in {'v2', 'observe', 'off'}:
                logger.error("Unknown rate limiter mode %r; falling back to v2", mode)
                mode = 'v2'
            if mode == 'off':
                return view_func(request, *args, **kwargs)

            # Generate cache key based on user, endpoint, method, and an
            # absolute bucket.  The bucket prevents each successful request
            # from extending the window indefinitely.
            user_id = getattr(request.user, 'id', 'anonymous')
            view_name = view_func.__name__
            endpoint = key_prefix or view_name
            now = time.time()
            bucket_start = int(now // window) * window
            reset_at = bucket_start + window
            retry_after = max(1, int(math.ceil(reset_at - now)))
            method_key = method or 'UNKNOWN'
            category_key = category or 'default'
            cache_key = (
                f"rate_limit:v2:{user_id}:{endpoint}:{method_key}:"
                f"{category_key}:{bucket_start}"
            )

            try:
                current_count = _rate_limit_increment(cache_key, retry_after)
            except Exception:
                # Rate limiting must not turn a Redis outage into a save outage.
                # The body-size, authentication, CSRF, and transaction guards
                # remain active in this fail-open path.
                logger.error(
                    "Rate limiter backend unavailable; allowing request",
                    extra={
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'method': method,
                        'category': category,
                    },
                    exc_info=True,
                )
                _record_rate_limit_metric('backend_error', endpoint, method, category_key)
                return view_func(request, *args, **kwargs)

            remaining = max(0, max_requests - current_count)
            common_headers = {
                'X-RateLimit-Limit': str(max_requests),
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Reset': str(reset_at),
            }

            if current_count > max_requests and mode == 'observe':
                _record_rate_limit_metric('would_block', endpoint, method, category_key)
                logger.warning(
                    "Rate limit would block request in observe mode",
                    extra={
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'method': method,
                        'category': category,
                        'count': current_count,
                        'limit': max_requests,
                        'window': window,
                        'retry_after': retry_after,
                        'rate_limit_mode': mode,
                    },
                )

            if current_count > max_requests and mode == 'v2':
                _record_rate_limit_metric('blocked', endpoint, method, category_key)
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {endpoint} ({method})",
                    extra={
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'method': method,
                        'category': category,
                        'count': current_count,
                        'limit': max_requests,
                        'window': window,
                        'retry_after': retry_after,
                    }
                )

                # User-friendly message based on window
                if retry_after >= 60:
                    time_msg = f"{math.ceil(retry_after / 60)} menit"
                else:
                    time_msg = f"{retry_after} detik"

                response = APIResponse.error(
                    message=f"Terlalu banyak permintaan. Silakan coba lagi dalam {time_msg}.",
                    code='RATE_LIMIT_EXCEEDED',
                    status=429,
                    details={
                        'limit': max_requests,
                        'max_requests': max_requests,
                        'window_seconds': window,
                        'current_count': current_count,
                        'remaining': 0,
                        'reset_at': reset_at,
                        'category': category_key,
                    },
                    extra={
                        'retry_after': retry_after,
                    }
                )
                response['Retry-After'] = str(retry_after)
                for header, value in common_headers.items():
                    response[header] = value
                return response

            if current_count <= max_requests:
                _record_rate_limit_metric('allowed', endpoint, method, category_key)
            near_limit_threshold = max(1, int(math.ceil(max_requests * 0.8)))
            if current_count == near_limit_threshold:
                _record_rate_limit_metric('near_limit', endpoint, method, category_key)

            # Call the actual view
            response = view_func(request, *args, **kwargs)
            try:
                for header, value in common_headers.items():
                    response[header] = value
            except Exception:
                # Non-HTTP test doubles or unusual response types should not
                # change the endpoint result.
                pass
            return response

        return wrapped_view
    return decorator


def limit_request_body(max_bytes: int = 2_000_000):
    """WP-P3b (VP-07): reject oversized request bodies per endpoint (DoS/abuse
    protection) without throttling legitimate request *frequency* (autosave).

    The global body limit (~50 MB) is far too large for these JSON endpoints; a
    tight per-endpoint cap is the cheap, deterministic guard. Returns 413 before
    the body is parsed. Default 2 MB — generous for parameter/volume payloads.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            size = None
            try:
                cl = request.META.get('CONTENT_LENGTH')
                size = int(cl) if cl not in (None, '') else None
            except (TypeError, ValueError):
                size = None
            if size is None:
                try:
                    size = len(request.body)
                except Exception:
                    size = 0
            if size is not None and size > max_bytes:
                logger.warning(
                    "Request body too large on %s: %s > %s bytes",
                    view_func.__name__, size, max_bytes,
                )
                return APIResponse.error(
                    message="Data yang dikirim terlalu besar. Kurangi jumlah baris lalu coba lagi.",
                    code='PAYLOAD_TOO_LARGE',
                    status=413,
                    details={'max_bytes': max_bytes, 'received_bytes': size},
                )
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


# ============================================================================
# STANDARDIZED API RESPONSES
# ============================================================================

class APIResponse:
    """
    Standardized JSON response format for all API endpoints.

    Success format:
        {
            "success": true,
            "data": {...},
            "message": "Optional success message"
        }

    Error format:
        {
            "success": false,
            "message": "User-friendly error message",
            "code": "ERROR_CODE",
            "details": {...}
        }
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = None,
        status: int = 200
    ) -> JsonResponse:
        """
        Create a successful API response.

        Args:
            data: Response data (dict, list, or any JSON-serializable type)
            message: Optional success message
            status: HTTP status code (default: 200)

        Returns:
            JsonResponse with standardized format

        Example:
            return APIResponse.success(
                data={'count': 10, 'items': [...]},
                message='Data berhasil disimpan'
            )
        """
        payload = {
            'success': True,
            'message': message,
        }

        if data is not None:
            payload['data'] = data

        return JsonResponse(payload, status=status)

    @staticmethod
    def created(
        data: Any = None,
        message: str = None
    ) -> JsonResponse:
        """
        Create a successful API response for resource creation (HTTP 201).

        Args:
            data: Response data (dict, list, or any JSON-serializable type)
            message: Optional success message

        Returns:
            JsonResponse with standardized format and 201 status

        Example:
            return APIResponse.created(
                data={'id': 123, 'name': 'New Item'},
                message='Resource created successfully'
            )
        """
        return APIResponse.success(data=data, message=message, status=201)

    @staticmethod
    def error(
        message: str,
        code: str = None,
        details: Dict = None,
        status: int = 400,
        extra: Optional[Dict[str, Any]] = None,
    ) -> JsonResponse:
        """
        Create an error API response.

        Args:
            message: User-friendly error message (Indonesian)
            code: Error code for programmatic handling
            details: Additional error details (optional)
            status: HTTP status code (default: 400)
            extra: Optional additional payload fields (e.g., retry_after)

        Returns:
            JsonResponse with standardized error format

        Example:
            return APIResponse.error(
                message='Data tidak valid',
                code='VALIDATION_ERROR',
                details={'field': 'nama', 'reason': 'Required'},
                status=400
            )
        """
        payload = {
            'success': False,
            'message': message,
            'code': code or 'GENERIC_ERROR',
        }

        if details:
            payload['details'] = details

        if extra:
            payload.update(extra)

        return JsonResponse(payload, status=status)

    @staticmethod
    def validation_error(
        message: str,
        field_errors: Dict[str, str] = None
    ) -> JsonResponse:
        """
        Create a validation error response.

        Args:
            message: General validation error message
            field_errors: Dict mapping field names to error messages

        Returns:
            JsonResponse with validation error format

        Example:
            return APIResponse.validation_error(
                message='Input tidak valid',
                field_errors={
                    'nama': 'Nama wajib diisi',
                    'email': 'Format email tidak valid'
                }
            )
        """
        return APIResponse.error(
            message=message,
            code='VALIDATION_ERROR',
            details={'fields': field_errors or {}},
            status=400
        )

    @staticmethod
    def not_found(message: str = "Data tidak ditemukan") -> JsonResponse:
        """Create a 404 not found response."""
        return APIResponse.error(
            message=message,
            code='NOT_FOUND',
            status=404
        )

    @staticmethod
    def forbidden(message: str = "Akses ditolak") -> JsonResponse:
        """Create a 403 forbidden response."""
        return APIResponse.error(
            message=message,
            code='FORBIDDEN',
            status=403
        )

    @staticmethod
    def server_error(
        message: str = "Terjadi kesalahan server",
        exception: Exception = None
    ) -> JsonResponse:
        """
        Create a 500 server error response.

        Args:
            message: User-friendly error message
            exception: Original exception (will be logged but not exposed)

        Returns:
            JsonResponse with server error format
        """
        if exception:
            logger.exception(
                "Server error in API endpoint",
                exc_info=exception,
                extra={'error_message': str(exception)}
            )

        return APIResponse.error(
            message=message,
            code='SERVER_ERROR',
            status=500
        )


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, Optional[str]]:
    """
    Validate that required fields are present in data.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_required_fields(
            data={'name': 'Test'},
            required_fields=['name', 'email']
        )
        if not is_valid:
            return APIResponse.validation_error(error)
    """
    missing_fields = []

    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)

    if missing_fields:
        return False, f"Field wajib tidak lengkap: {', '.join(missing_fields)}"

    return True, None


def validate_positive_number(value, field_name: str = 'value') -> tuple[bool, Optional[str]]:
    """
    Validate that a value is a positive number.

    Args:
        value: Value to validate
        field_name: Name of the field (for error message)

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num = float(value)
        if num < 0:
            return False, f"{field_name} harus positif"
        return True, None
    except (ValueError, TypeError):
        return False, f"{field_name} harus berupa angka"


def validate_choice(value, choices: list, field_name: str = 'value') -> tuple[bool, Optional[str]]:
    """
    Validate that a value is in allowed choices.

    Args:
        value: Value to validate
        choices: List of allowed values
        field_name: Name of the field (for error message)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value not in choices:
        return False, f"{field_name} tidak valid. Pilihan: {', '.join(map(str, choices))}"
    return True, None


# ============================================================================
# DECORATOR COMBINATIONS
# ============================================================================

def api_endpoint(max_requests: int = 100, window: int = 60, category: str = None):
    """
    Combined decorator for common API endpoint requirements.

    Applies:
    - login_required
    - rate_limit

    Usage:
        # Explicit limits
        @api_endpoint(max_requests=10, window=60)
        def my_api_view(request, project_id):
            ...

        # Using category (recommended)
        @api_endpoint(category='bulk')
        def deep_copy_view(request, project_id):
            ...

    Categories:
        - 'bulk': 5 requests per 5 minutes
        - 'write': 20 requests per minute
        - 'read': 100 requests per minute
        - 'export': 10 requests per minute
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        @rate_limit(max_requests=max_requests, window=window, category=category)
        def wrapped_view(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


# ============================================================================
# REKAP KEBUTUHAN HELPERS
# ============================================================================

def _parse_int_csv_list(raw: str) -> List[int]:
    """Parse comma-separated ints safely."""
    if not raw:
        return []
    result: List[int] = []
    for chunk in raw.split(','):
        chunk = (chunk or '').strip()
        if not chunk:
            continue
        try:
            result.append(int(chunk))
        except (TypeError, ValueError):
            continue
    return result


def parse_kebutuhan_query_params(query: QueryDict) -> Dict[str, Any]:
    """
    Normalize Rekap Kebutuhan query parameters (mode, filters, search).

    Returns dict:
        {
            "mode": "all" | "tahapan",
            "tahapan_id": Optional[int],
            "filters": {
                "klasifikasi_ids": [int],
                "sub_klasifikasi_ids": [int],
                "kategori_items": [str],
                "pekerjaan_ids": [int],
            },
            "search": str,
            "time_scope": {"mode": str, "start": Optional[str], "end": Optional[str]},
        }
    """
    mode_raw = (query.get('mode') or 'all').strip().lower()
    mode = 'tahapan' if mode_raw == 'tahapan' else 'all'

    tahapan_id = None
    if mode == 'tahapan':
        tahapan_raw = query.get('tahapan_id')
        if tahapan_raw:
            try:
                tahapan_id = int(tahapan_raw)
            except (TypeError, ValueError):
                tahapan_id = None

    filters = {
        'klasifikasi_ids': _parse_int_csv_list(query.get('klasifikasi')),
        'sub_klasifikasi_ids': _parse_int_csv_list(query.get('sub_klasifikasi')),
        'kategori_items': [],
        'pekerjaan_ids': _parse_int_csv_list(query.get('pekerjaan')),
    }

    kategori_raw = query.get('kategori')
    if kategori_raw:
        allowed = {'TK', 'BHN', 'ALT', 'LAIN'}
        kategori_list = [
            chunk.strip().upper()
            for chunk in kategori_raw.split(',')
            if chunk.strip()
        ]
        filters['kategori_items'] = [k for k in kategori_list if k in allowed]

    search = (query.get('search') or '').strip()

    time_scope = {
        'mode': (query.get('period_mode') or 'all').strip().lower(),
        'start': (query.get('period_start') or '').strip(),
        'end': (query.get('period_end') or '').strip(),
    }

    tahapan_ids = _parse_int_csv_list(query.get('tahapan_ids'))

    return {
        'mode': mode,
        'tahapan_id': tahapan_id,
        'tahapan_ids': tahapan_ids,
        'filters': filters,
        'search': search,
        'time_scope': time_scope,
    }
