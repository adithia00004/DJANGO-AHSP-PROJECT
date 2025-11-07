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

def rate_limit(max_requests: int = 100, window: int = 60, key_prefix: str = None):
    """
    Rate limiting decorator for API endpoints.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window: Time window in seconds (default: 60 seconds)
        key_prefix: Custom prefix for cache key (default: use view name)

    Returns:
        Decorator function

    Usage:
        @rate_limit(max_requests=10, window=60)
        @login_required
        def my_api_view(request, project_id):
            ...

    Example:
        # Limit to 10 requests per minute per user
        @rate_limit(max_requests=10, window=60)
        def expensive_operation(request):
            ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Generate cache key based on user and endpoint
            user_id = getattr(request.user, 'id', 'anonymous')
            endpoint = key_prefix or view_func.__name__
            cache_key = f"rate_limit:{user_id}:{endpoint}"

            # Get current request count
            current_count = cache.get(cache_key, 0)

            # Check if limit exceeded
            if current_count >= max_requests:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {endpoint}",
                    extra={
                        'user_id': user_id,
                        'endpoint': endpoint,
                        'count': current_count,
                        'limit': max_requests
                    }
                )
                return APIResponse.error(
                    message=f"Terlalu banyak permintaan. Silakan coba lagi dalam {window} detik.",
                    code='RATE_LIMIT_EXCEEDED',
                    status=429,
                    details={
                        'max_requests': max_requests,
                        'window_seconds': window,
                        'current_count': current_count
                    }
                )

            # Increment counter
            cache.set(cache_key, current_count + 1, window)

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
            "ok": true,
            "data": {...},
            "message": "Optional success message"
        }

    Error format:
        {
            "ok": false,
            "error": {
                "message": "User-friendly error message",
                "code": "ERROR_CODE",
                "details": {...}
            }
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
            'ok': True,
        }

        if data is not None:
            payload['data'] = data

        if message:
            payload['message'] = message

        return JsonResponse(payload, status=status)

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
            'ok': False,
            'error': {
                'message': message,
                'code': code or 'GENERIC_ERROR',
            }
        }

        if details:
            payload['error']['details'] = details

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

def api_endpoint(max_requests: int = 100, window: int = 60):
    """
    Combined decorator for common API endpoint requirements.

    Applies:
    - login_required
    - rate_limit

    Usage:
        @api_endpoint(max_requests=10, window=60)
        def my_api_view(request, project_id):
            ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        @rate_limit(max_requests=max_requests, window=window)
        def wrapped_view(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
