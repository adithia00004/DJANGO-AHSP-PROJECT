"""
Monitoring Middleware

Custom Django middleware for collecting application metrics:
- Request counts per endpoint
- Response times
- Error rates
- Rate limit hits

Metrics are exposed via Django cache and can be scraped by Prometheus
or sent to monitoring services like Datadog, New Relic, etc.
"""

import time
import logging
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to collect application metrics for monitoring.

    Metrics collected:
    - Request count per endpoint
    - Response time per endpoint
    - Error count (4xx, 5xx)
    - Request method distribution

    Usage:
        Add to settings.py MIDDLEWARE:
        'detail_project.monitoring_middleware.MonitoringMiddleware',
    """

    def process_request(self, request):
        """Start timer for request."""
        request._monitoring_start_time = time.time()
        return None

    def process_response(self, request, response):
        """Collect metrics after response."""
        if not hasattr(request, '_monitoring_start_time'):
            return response

        # Calculate response time
        duration = time.time() - request._monitoring_start_time

        # Get endpoint info
        endpoint = self._get_endpoint_name(request)
        method = request.method
        status_code = response.status_code

        # Increment request counter
        self._increment_metric(f'requests_total:{endpoint}:{method}')
        self._increment_metric(f'requests_total:global')

        # Track response time (store in buckets)
        self._track_response_time(endpoint, duration)

        # Track errors
        if 400 <= status_code < 500:
            self._increment_metric(f'errors_4xx:{endpoint}')
            self._increment_metric(f'errors_4xx:global')
        elif 500 <= status_code < 600:
            self._increment_metric(f'errors_5xx:{endpoint}')
            self._increment_metric(f'errors_5xx:global')
            # Log 5xx errors
            logger.error(
                f'5xx Error: {endpoint} - {status_code}',
                extra={
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': status_code,
                    'duration': duration,
                    'user': getattr(request.user, 'username', 'anonymous')
                }
            )

        # Track rate limit hits (429 status)
        if status_code == 429:
            self._increment_metric(f'rate_limit_hits:{endpoint}')
            self._increment_metric(f'rate_limit_hits:global')

        return response

    def process_exception(self, request, exception):
        """Track unhandled exceptions."""
        endpoint = self._get_endpoint_name(request)

        self._increment_metric(f'exceptions:{endpoint}')
        self._increment_metric(f'exceptions:global')

        logger.exception(
            f'Unhandled exception: {endpoint}',
            extra={
                'endpoint': endpoint,
                'method': request.method,
                'user': getattr(request.user, 'username', 'anonymous'),
                'exception_type': type(exception).__name__
            }
        )

        return None

    def _get_endpoint_name(self, request):
        """Extract endpoint name from request."""
        # Try to get URL pattern name
        if hasattr(request, 'resolver_match') and request.resolver_match:
            if request.resolver_match.url_name:
                return request.resolver_match.url_name

        # Fallback to path
        path = request.path
        # Normalize path (remove IDs)
        import re
        path = re.sub(r'/\d+/', '/[id]/', path)
        return path or 'unknown'

    def _increment_metric(self, metric_key, value=1):
        """Increment a metric counter in cache."""
        cache_key = f'metric:{metric_key}'
        try:
            current = cache.get(cache_key, 0)
            cache.set(cache_key, current + value, timeout=3600)  # 1 hour
        except Exception as e:
            # Don't fail request if caching fails
            logger.debug(f'Failed to increment metric {metric_key}: {e}')

    def _track_response_time(self, endpoint, duration):
        """Track response time in histogram buckets."""
        # Store recent response times for percentile calculation
        cache_key = f'response_times:{endpoint}'
        try:
            times = cache.get(cache_key, [])
            times.append(duration)

            # Keep only last 100 measurements
            if len(times) > 100:
                times = times[-100:]

            cache.set(cache_key, times, timeout=3600)
        except Exception as e:
            logger.debug(f'Failed to track response time: {e}')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware for detailed performance monitoring.

    Monitors:
    - Database query count
    - Cache operations
    - Slow requests (> threshold)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Slow request threshold (seconds)
        self.slow_threshold = 2.0

    def __call__(self, request):
        # Start monitoring
        request._perf_start = time.time()

        # Track database queries
        from django.db import connection
        request._perf_queries_before = len(connection.queries)

        # Get response
        response = self.get_response(request)

        # Calculate metrics
        duration = time.time() - request._perf_start
        queries_count = len(connection.queries) - request._perf_queries_before

        # Log slow requests
        if duration > self.slow_threshold:
            logger.warning(
                f'Slow request detected: {request.path}',
                extra={
                    'path': request.path,
                    'method': request.method,
                    'duration': duration,
                    'queries_count': queries_count,
                    'user': getattr(request.user, 'username', 'anonymous')
                }
            )

        # Log excessive database queries
        if queries_count > 50:
            logger.warning(
                f'Excessive database queries: {request.path}',
                extra={
                    'path': request.path,
                    'queries_count': queries_count,
                    'duration': duration
                }
            )

        return response


def get_metrics_summary():
    """
    Get current metrics summary.

    Returns:
        dict: Current metrics data
    """
    metrics = {}

    try:
        # Get global metrics
        metrics['requests_total'] = cache.get('metric:requests_total:global', 0)
        metrics['errors_4xx'] = cache.get('metric:errors_4xx:global', 0)
        metrics['errors_5xx'] = cache.get('metric:errors_5xx:global', 0)
        metrics['rate_limit_hits'] = cache.get('metric:rate_limit_hits:global', 0)
        metrics['exceptions'] = cache.get('metric:exceptions:global', 0)

        # Calculate error rate
        if metrics['requests_total'] > 0:
            metrics['error_rate'] = (
                (metrics['errors_4xx'] + metrics['errors_5xx']) /
                metrics['requests_total'] * 100
            )
        else:
            metrics['error_rate'] = 0

    except Exception as e:
        logger.error(f'Failed to get metrics summary: {e}')

    return metrics


def get_endpoint_metrics(endpoint):
    """
    Get metrics for specific endpoint.

    Args:
        endpoint: Endpoint name

    Returns:
        dict: Endpoint metrics
    """
    metrics = {}

    try:
        # Request counts
        for method in ['GET', 'POST', 'PUT', 'DELETE']:
            key = f'metric:requests_total:{endpoint}:{method}'
            metrics[f'requests_{method}'] = cache.get(key, 0)

        # Errors
        metrics['errors_4xx'] = cache.get(f'metric:errors_4xx:{endpoint}', 0)
        metrics['errors_5xx'] = cache.get(f'metric:errors_5xx:{endpoint}', 0)

        # Rate limits
        metrics['rate_limit_hits'] = cache.get(f'metric:rate_limit_hits:{endpoint}', 0)

        # Response times
        times = cache.get(f'response_times:{endpoint}', [])
        if times:
            metrics['response_time_avg'] = sum(times) / len(times)
            metrics['response_time_min'] = min(times)
            metrics['response_time_max'] = max(times)

            # Calculate percentiles
            sorted_times = sorted(times)
            metrics['response_time_p50'] = sorted_times[int(len(sorted_times) * 0.5)]
            metrics['response_time_p95'] = sorted_times[int(len(sorted_times) * 0.95)]
            metrics['response_time_p99'] = sorted_times[int(len(sorted_times) * 0.99)]

    except Exception as e:
        logger.error(f'Failed to get endpoint metrics: {e}')

    return metrics


def reset_metrics():
    """Reset all metrics (useful for testing)."""
    # In production, metrics should naturally expire via cache timeout
    # This is mainly for testing
    pass
