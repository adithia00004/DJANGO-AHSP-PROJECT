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
from typing import Any, Dict, Optional
from django.http import JsonResponse
from django.core.cache import cache
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


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
    'read': {
        'max_requests': 100,
        'window': 60,  # 1 minute
        'description': 'Read operations (search, list, get)'
    },
    'export': {
        'max_requests': 10,
        'window': 60,  # 1 minute
        'description': 'Export operations (PDF, Excel, CSV)'
    },
}


def rate_limit(max_requests: int = 100, window: int = 60, key_prefix: str = None, category: str = None):
    """
    Rate limiting decorator for API endpoints with category support.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window: Time window in seconds (default: 60 seconds)
        key_prefix: Custom prefix for cache key (default: use view name)
        category: Rate limit category ('bulk', 'write', 'read', 'export')
                 If provided, overrides max_requests and window with category defaults

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

    Categories:
        - 'bulk': 5 requests per 5 minutes (expensive operations)
        - 'write': 20 requests per minute (normal saves)
        - 'read': 100 requests per minute (searches, lists)
        - 'export': 10 requests per minute (PDF/Excel generation)

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
        limits = RATE_LIMIT_CATEGORIES[category]
        max_requests = limits['max_requests']
        window = limits['window']
        logger.debug(
            f"Applying category '{category}' limits: {max_requests} req/{window}s"
        )

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Generate cache key based on user and endpoint
            user_id = getattr(request.user, 'id', 'anonymous')
            view_name = view_func.__name__
            endpoint = key_prefix or view_name

            # Include category in cache key to separate limits
            cache_suffix = f":{category}" if category else ""
            cache_key = f"rate_limit:{user_id}:{endpoint}{cache_suffix}"
            alias_key = None
            if key_prefix and key_prefix != view_name:
                alias_key = f"rate_limit:{user_id}:{view_name}{cache_suffix}"

            # Get current request count
            current_count = cache.get(cache_key, 0)

            # Check if limit exceeded
            if current_count >= max_requests:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {endpoint}",
                    extra={
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'category': category,
                        'count': current_count,
                        'limit': max_requests,
                        'window': window
                    }
                )

                # User-friendly message based on window
                if window >= 300:
                    time_msg = f"{window // 60} menit"
                else:
                    time_msg = f"{window} detik"

                return APIResponse.error(
                    message=f"Terlalu banyak permintaan. Silakan coba lagi dalam {time_msg}.",
                    code='RATE_LIMIT_EXCEEDED',
                    status=429,
                    details={
                        'max_requests': max_requests,
                        'window_seconds': window,
                        'current_count': current_count,
                        'category': category or 'default'
                    }
                )

            # Increment counter
            new_count = current_count + 1
            cache.set(cache_key, new_count, window)
            if alias_key:
                cache.set(alias_key, new_count, window)

            # Call the actual view
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
        status: int = 400
    ) -> JsonResponse:
        """
        Create an error API response.

        Args:
            message: User-friendly error message (Indonesian)
            code: Error code for programmatic handling
            details: Additional error details (optional)
            status: HTTP status code (default: 400)

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
