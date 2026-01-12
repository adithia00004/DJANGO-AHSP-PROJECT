"""
API Deprecation Decorator - Marks v1 endpoints as deprecated

Provides:
- Deprecation warnings in response headers
- Usage logging for monitoring
- Migration guide references
- Configurable sunset date

Usage:
    @api_deprecated(
        sunset_date="2025-02-14",
        migration_endpoint="api_v2_assign_weekly",
        reason="Migrated to weekly canonical storage (v2)"
    )
    def api_old_endpoint(request, project_id):
        # ... old implementation
"""

import logging
from functools import wraps
from datetime import datetime
from django.http import JsonResponse
from django.urls import reverse

logger = logging.getLogger('api.deprecation')

# Track deprecation usage for monitoring
DEPRECATION_METRICS = {}


def api_deprecated(sunset_date=None, migration_endpoint=None, reason=None):
    """
    Decorator to mark API endpoints as deprecated.

    Args:
        sunset_date (str): ISO date when endpoint will be removed (YYYY-MM-DD)
        migration_endpoint (str): URL name of the replacement v2 endpoint
        reason (str): Human-readable deprecation reason

    Returns:
        Wrapped view function with deprecation headers and logging

    Example:
        @api_deprecated(
            sunset_date="2025-02-14",
            migration_endpoint="api_v2_assign_weekly",
            reason="Migrated to weekly canonical storage"
        )
        def api_assign_pekerjaan_to_tahapan(request, project_id):
            # ... implementation
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Track usage metrics
            endpoint_name = view_func.__name__
            if endpoint_name not in DEPRECATION_METRICS:
                DEPRECATION_METRICS[endpoint_name] = {
                    'first_seen': datetime.now().isoformat(),
                    'count': 0,
                    'last_access': None
                }

            DEPRECATION_METRICS[endpoint_name]['count'] += 1
            DEPRECATION_METRICS[endpoint_name]['last_access'] = datetime.now().isoformat()

            # Log deprecation warning
            logger.warning(
                f"Deprecated API called: {endpoint_name} "
                f"(total calls: {DEPRECATION_METRICS[endpoint_name]['count']}) "
                f"- User-Agent: {request.META.get('HTTP_USER_AGENT', 'unknown')}"
            )

            # Execute original view
            response = view_func(request, *args, **kwargs)

            # Add deprecation headers
            response['X-API-Deprecated'] = 'true'
            response['X-API-Deprecation-Info'] = 'This endpoint is deprecated and will be removed'

            if sunset_date:
                response['X-API-Sunset'] = sunset_date
                response['X-API-Deprecation-Info'] += f' on {sunset_date}'

            if migration_endpoint:
                try:
                    # Build migration URL
                    migration_url = request.build_absolute_uri(
                        reverse(f'detail_project:{migration_endpoint}',
                                kwargs={'project_id': kwargs.get('project_id', 0)})
                    )
                    response['X-API-Migration-Endpoint'] = migration_url
                    response['X-API-Deprecation-Info'] += f'. Migrate to: {migration_endpoint}'
                except Exception:
                    # Fallback if URL reverse fails
                    response['X-API-Migration-Endpoint'] = migration_endpoint

            if reason:
                response['X-API-Deprecation-Reason'] = reason

            # Add migration guide link
            response['Link'] = '<https://docs.example.com/api-migration-guide>; rel="deprecation"'

            return response

        # Mark function as deprecated for introspection
        wrapper._is_deprecated = True
        wrapper._deprecation_info = {
            'sunset_date': sunset_date,
            'migration_endpoint': migration_endpoint,
            'reason': reason
        }

        return wrapper
    return decorator


def get_deprecation_metrics():
    """
    Get usage metrics for all deprecated endpoints.

    Returns:
        dict: Metrics dictionary with endpoint names as keys

    Example:
        {
            'api_assign_pekerjaan_to_tahapan': {
                'first_seen': '2025-01-15T10:30:00',
                'count': 142,
                'last_access': '2025-01-15T14:22:00'
            }
        }
    """
    return DEPRECATION_METRICS.copy()


def reset_deprecation_metrics():
    """Reset all deprecation metrics (for testing)."""
    global DEPRECATION_METRICS
    DEPRECATION_METRICS = {}
