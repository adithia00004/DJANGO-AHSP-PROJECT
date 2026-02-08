"""
API Monitoring Views - Track deprecated API usage and performance metrics
"""

import hmac
import json
import logging
import os

from django.http import JsonResponse
from django.core.cache import cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .decorators import get_deprecation_metrics, reset_deprecation_metrics
from .utils.performance import (
    get_metrics_summary,
    reset_metrics,
    get_database_stats,
    analyze_slow_queries,
    get_query_breakdown
)

logger = logging.getLogger(__name__)


def is_staff_or_superuser(user):
    """Check if user is staff or superuser"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def api_deprecation_metrics(request):
    """
    Get deprecation metrics for all v1 endpoints.

    Returns JSON with usage statistics for monitoring.

    Example Response:
        {
            "ok": true,
            "metrics": {
                "api_assign_pekerjaan_to_tahapan": {
                    "first_seen": "2025-01-15T10:30:00",
                    "count": 142,
                    "last_access": "2025-01-15T14:22:00"
                },
                ...
            },
            "summary": {
                "total_endpoints": 4,
                "total_calls": 1224,
                "most_used": "api_get_pekerjaan_assignments"
            }
        }
    """
    metrics = get_deprecation_metrics()

    # Calculate summary
    total_calls = sum(m['count'] for m in metrics.values())
    most_used_endpoint = None
    max_count = 0

    for endpoint, stats in metrics.items():
        if stats['count'] > max_count:
            max_count = stats['count']
            most_used_endpoint = endpoint

    summary = {
        'total_endpoints': len(metrics),
        'total_calls': total_calls,
        'most_used': most_used_endpoint,
        'most_used_count': max_count
    }

    return JsonResponse({
        'ok': True,
        'metrics': metrics,
        'summary': summary
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def api_deprecation_dashboard(request):
    """
    Render deprecation monitoring dashboard (HTML).

    Shows real-time usage of deprecated v1 endpoints.
    """
    return render(request, 'detail_project/monitoring/deprecation_dashboard.html', {
        'title': 'API Deprecation Monitoring',
        'sunset_date': '2025-02-14'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def api_reset_deprecation_metrics(request):
    """
    Reset all deprecation metrics.

    **WARNING**: This is destructive and should only be used for testing.
    """
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'Method not allowed. Use POST.'
        }, status=405)

    reset_deprecation_metrics()

    return JsonResponse({
        'ok': True,
        'message': 'All deprecation metrics have been reset'
    })


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

@login_required
@user_passes_test(is_staff_or_superuser)
def api_performance_metrics(request):
    """
    Get performance metrics for backend operations.

    Returns JSON with query, view, and cache metrics.

    Example Response:
        {
            "ok": true,
            "summary": {
                "queries": {
                    "count": 150,
                    "min": 5.2,
                    "max": 450.3,
                    "avg": 85.6,
                    "total_queries": 1024
                },
                "views": {
                    "count": 75,
                    "min": 120.5,
                    "max": 2450.0,
                    "avg": 650.2
                },
                "cache": {
                    "hits": 450,
                    "misses": 50,
                    "hit_rate": 90.0
                }
            },
            "database": {...},
            "slow_queries": [...],
            "query_breakdown": {...}
        }
    """
    summary = get_metrics_summary()
    database = get_database_stats()
    slow_queries = analyze_slow_queries(threshold_ms=100)
    query_breakdown = get_query_breakdown()

    return JsonResponse({
        'ok': True,
        'summary': summary,
        'database': database,
        'slow_queries': slow_queries[:10],  # Top 10 slowest
        'query_breakdown': query_breakdown
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def api_performance_dashboard(request):
    """
    Render performance monitoring dashboard (HTML).

    Shows real-time backend performance metrics.
    """
    return render(request, 'detail_project/monitoring/performance_dashboard.html', {
        'title': 'Performance Monitoring'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def api_reset_performance_metrics(request):
    """
    Reset all performance metrics.

    **WARNING**: This is destructive and should only be used for testing.
    """
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'Method not allowed. Use POST.'
        }, status=405)

    reset_metrics()

    return JsonResponse({
        'ok': True,
        'message': 'All performance metrics have been reset'
    })


@csrf_exempt
def api_report_client_metric(request):
    """
    Receive client-side performance metrics.

    Endpoint for PerformanceMonitor to report client metrics.

    POST Body:
        {
            "type": "pageLoad" | "apiRequest" | "render" | "fps" | "memory",
            "metric": { ... metric data ... }
        }
    """
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'Method not allowed. Use POST.'
        }, status=405)

    required_key = os.getenv("METRICS_API_KEY", "").strip()
    if not required_key:
        # Fail closed by default: endpoint stays disabled until API key is configured.
        logger.warning("Client metrics endpoint called without METRICS_API_KEY configured")
        return JsonResponse({
            'ok': False,
            'error': 'Metrics endpoint is not configured'
        }, status=503)

    provided_key = (request.META.get("HTTP_X_METRICS_KEY") or "").strip()
    if not provided_key or not hmac.compare_digest(provided_key, required_key):
        return JsonResponse({
            'ok': False,
            'error': 'Unauthorized'
        }, status=403)

    rate_limit = int(os.getenv("METRICS_RATE_LIMIT", "60"))
    rate_window = int(os.getenv("METRICS_RATE_WINDOW", "60"))

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.META.get("REMOTE_ADDR", "unknown")

    rate_key = f"metrics_rate:{client_ip}"
    current_count = cache.get(rate_key, 0)
    if current_count >= rate_limit:
        return JsonResponse({
            'ok': False,
            'error': 'Rate limit exceeded',
            'retry_after': rate_window
        }, status=429)
    cache.set(rate_key, current_count + 1, rate_window)

    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(body)

        metric_type = data.get('type') or data.get('metric_type')
        metric = data.get('metric') if 'metric' in data else data.get('value')

        if not metric_type or metric is None:
            return JsonResponse({
                'ok': False,
                'error': 'Missing type or metric'
            }, status=400)

        # Log client metric (could also store in database)
        logging.getLogger('client_performance').info(
            "Client metric received",
            extra={
                "metric_type": metric_type,
                "metric": metric,
                "client_ip": client_ip,
            },
        )

        return JsonResponse({
            'ok': True,
            'message': 'Metric received'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'ok': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception:
        logger.exception("Failed to process client metric")
        return JsonResponse({
            'ok': False,
            'error': 'Internal server error'
        }, status=500)
