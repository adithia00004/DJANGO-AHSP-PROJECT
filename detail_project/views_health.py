"""
Health Check Endpoint for Monitoring

Provides system health status including:
- Database connectivity
- Redis cache connectivity
- Application version
- System timestamp

Used by monitoring systems (Prometheus, Datadog, etc.) to verify application health.
"""

import os
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_GET
def health_check(request):
    """
    Health check endpoint for monitoring systems.

    Returns JSON with status of all critical components:
    - database: PostgreSQL/MySQL connectivity
    - cache: Redis connectivity
    - version: Application version from environment
    - timestamp: Current server time

    Returns:
        200 OK: All systems operational
        503 Service Unavailable: One or more systems failed

    Example Response (Success):
    {
        "status": "ok",
        "checks": {
            "database": {"status": "ok"},
            "cache": {"status": "ok", "backend": "django_redis.cache.RedisCache"}
        },
        "version": "1.0.0",
        "timestamp": "2025-11-07T12:00:00Z"
    }

    Example Response (Error):
    {
        "status": "error",
        "checks": {
            "database": {"status": "ok"},
            "cache": {"status": "error", "message": "Connection refused"}
        },
        "version": "1.0.0",
        "timestamp": "2025-11-07T12:00:00Z"
    }
    """
    from datetime import datetime, timezone

    health = {
        'status': 'ok',
        'checks': {},
        'version': os.environ.get('APP_VERSION', 'dev'),
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                health['checks']['database'] = {
                    'status': 'ok',
                    'vendor': connection.vendor
                }
            else:
                health['status'] = 'error'
                health['checks']['database'] = {
                    'status': 'error',
                    'message': 'Query returned unexpected result'
                }
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        health['status'] = 'error'
        health['checks']['database'] = {
            'status': 'error',
            'message': str(e)
        }

    # Check cache (Redis) connectivity
    try:
        # Set a test key
        cache.set('health_check_test', 'ok', 10)

        # Retrieve the test key
        result = cache.get('health_check_test')

        if result == 'ok':
            # Get cache backend info
            cache_backend = cache.__class__.__module__ + '.' + cache.__class__.__name__

            health['checks']['cache'] = {
                'status': 'ok',
                'backend': cache_backend
            }

            # Clean up test key
            cache.delete('health_check_test')
        else:
            health['status'] = 'error'
            health['checks']['cache'] = {
                'status': 'error',
                'message': 'Cache read/write test failed'
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        health['status'] = 'error'
        health['checks']['cache'] = {
            'status': 'error',
            'message': str(e)
        }

    # Determine HTTP status code
    status_code = 200 if health['status'] == 'ok' else 503

    return JsonResponse(health, status=status_code)


@csrf_exempt
@require_GET
def health_check_simple(request):
    """
    Simple health check that only verifies the application is running.

    Does not check database or cache connectivity.
    Useful for load balancer health checks that don't need detailed status.

    Returns:
        200 OK: {"status": "ok"}
    """
    return JsonResponse({'status': 'ok'}, status=200)


@csrf_exempt
@require_GET
def readiness_check(request):
    """
    Readiness check for Kubernetes/container orchestration.

    Similar to health_check but specifically indicates if the application
    is ready to receive traffic.

    Returns:
        200 OK: Application is ready
        503 Service Unavailable: Application is not ready
    """
    # For now, same as health check
    # In the future, could add additional checks like:
    # - Database migrations complete
    # - Required background jobs running
    # - External dependencies available
    return health_check(request)


@csrf_exempt
@require_GET
def liveness_check(request):
    """
    Liveness check for Kubernetes/container orchestration.

    Indicates if the application process is alive and should not be restarted.
    Only checks basic application functionality.

    Returns:
        200 OK: Application is alive
    """
    return JsonResponse({'status': 'alive'}, status=200)
