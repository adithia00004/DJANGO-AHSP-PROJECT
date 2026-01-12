"""
Performance Monitoring Utilities - Backend performance tracking

Provides:
- Query performance monitoring
- View execution time tracking
- Cache hit rate monitoring
- Database connection pool monitoring
- Memory usage tracking
"""

import time
import functools
import logging
from django.db import connection
from django.core.cache import cache
from contextlib import contextmanager

logger = logging.getLogger('performance')

# Performance metrics storage (in-memory)
METRICS = {
    'queries': [],
    'views': [],
    'cache_hits': 0,
    'cache_misses': 0
}

# Thresholds (milliseconds)
THRESHOLDS = {
    'QUERY_WARN': 100,
    'QUERY_ERROR': 500,
    'VIEW_WARN': 1000,
    'VIEW_ERROR': 3000
}


def track_query_performance(func):
    """
    Decorator to track database query performance.

    Monitors:
    - Number of queries executed
    - Total query time
    - Individual query duration

    Usage:
        @track_query_performance
        def get_project_data(project_id):
            return Project.objects.get(id=project_id)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Reset queries counter
        initial_queries = len(connection.queries)

        start_time = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start_time) * 1000  # Convert to ms

        # Calculate query metrics
        queries_executed = len(connection.queries) - initial_queries

        metric = {
            'timestamp': time.time(),
            'function': func.__name__,
            'duration_ms': duration,
            'queries_count': queries_executed,
            'queries': connection.queries[initial_queries:] if queries_executed > 0 else []
        }

        METRICS['queries'].append(metric)

        # Log warnings
        if duration > THRESHOLDS['QUERY_ERROR']:
            logger.error(
                f"{func.__name__} exceeded query error threshold: "
                f"{duration:.2f}ms ({queries_executed} queries)"
            )
        elif duration > THRESHOLDS['QUERY_WARN']:
            logger.warning(
                f"{func.__name__} exceeded query warning threshold: "
                f"{duration:.2f}ms ({queries_executed} queries)"
            )

        return result

    return wrapper


def track_view_performance(func):
    """
    Decorator to track view performance.

    Monitors:
    - View execution time
    - Response status code
    - URL path

    Usage:
        @track_view_performance
        def my_view(request, project_id):
            # ... view logic
            return JsonResponse({'ok': True})
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()

        response = func(request, *args, **kwargs)

        duration = (time.time() - start_time) * 1000  # Convert to ms

        metric = {
            'timestamp': time.time(),
            'view': func.__name__,
            'method': request.method,
            'path': request.path,
            'duration_ms': duration,
            'status_code': response.status_code
        }

        METRICS['views'].append(metric)

        # Log warnings
        if duration > THRESHOLDS['VIEW_ERROR']:
            logger.error(
                f"{func.__name__} ({request.method} {request.path}) "
                f"exceeded view error threshold: {duration:.2f}ms"
            )
        elif duration > THRESHOLDS['VIEW_WARN']:
            logger.warning(
                f"{func.__name__} ({request.method} {request.path}) "
                f"exceeded view warning threshold: {duration:.2f}ms"
            )

        return response

    return wrapper


@contextmanager
def measure_time(operation_name):
    """
    Context manager to measure operation time.

    Usage:
        with measure_time('data_processing'):
            # ... expensive operation
            process_large_dataset()
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = (time.time() - start_time) * 1000
        logger.info(f"[{operation_name}] completed in {duration:.2f}ms")


def track_cache_hit():
    """Track cache hit (used in cache wrappers)"""
    METRICS['cache_hits'] += 1


def track_cache_miss():
    """Track cache miss (used in cache wrappers)"""
    METRICS['cache_misses'] += 1


def get_cache_hit_rate():
    """
    Calculate cache hit rate.

    Returns:
        float: Hit rate percentage (0-100)
    """
    total = METRICS['cache_hits'] + METRICS['cache_misses']
    if total == 0:
        return 0.0
    return (METRICS['cache_hits'] / total) * 100


def get_metrics_summary():
    """
    Get summary of all performance metrics.

    Returns:
        dict: Summary statistics
    """
    query_metrics = METRICS['queries']
    view_metrics = METRICS['views']

    def calculate_stats(data, key):
        """Calculate min/max/avg for a metric"""
        if not data:
            return {'count': 0, 'min': 0, 'max': 0, 'avg': 0}

        values = [d[key] for d in data]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values)
        }

    return {
        'queries': {
            **calculate_stats(query_metrics, 'duration_ms'),
            'total_queries': sum(m['queries_count'] for m in query_metrics)
        },
        'views': calculate_stats(view_metrics, 'duration_ms'),
        'cache': {
            'hits': METRICS['cache_hits'],
            'misses': METRICS['cache_misses'],
            'hit_rate': get_cache_hit_rate()
        }
    }


def reset_metrics():
    """Reset all performance metrics"""
    METRICS['queries'].clear()
    METRICS['views'].clear()
    METRICS['cache_hits'] = 0
    METRICS['cache_misses'] = 0


def get_database_stats():
    """
    Get current database connection statistics.

    Returns:
        dict: Database statistics
    """
    from django.db import connections

    stats = {}
    for alias in connections:
        conn = connections[alias]
        stats[alias] = {
            'vendor': conn.vendor,
            'queries_executed': len(connection.queries) if alias == 'default' else 0,
            'is_usable': conn.is_usable() if hasattr(conn, 'is_usable') else None
        }

    return stats


def analyze_slow_queries(threshold_ms=100):
    """
    Analyze slow queries from metrics.

    Args:
        threshold_ms (int): Threshold in milliseconds

    Returns:
        list: List of slow queries
    """
    slow_queries = []

    for metric in METRICS['queries']:
        if metric['duration_ms'] > threshold_ms:
            slow_queries.append({
                'function': metric['function'],
                'duration_ms': metric['duration_ms'],
                'queries_count': metric['queries_count'],
                'timestamp': metric['timestamp']
            })

    # Sort by duration (slowest first)
    slow_queries.sort(key=lambda x: x['duration_ms'], reverse=True)

    return slow_queries


def get_query_breakdown():
    """
    Get breakdown of queries by type (SELECT, INSERT, UPDATE, DELETE).

    Returns:
        dict: Query breakdown
    """
    breakdown = {
        'SELECT': 0,
        'INSERT': 0,
        'UPDATE': 0,
        'DELETE': 0,
        'OTHER': 0
    }

    for metric in METRICS['queries']:
        for query in metric['queries']:
            sql = query['sql'].strip().upper()

            if sql.startswith('SELECT'):
                breakdown['SELECT'] += 1
            elif sql.startswith('INSERT'):
                breakdown['INSERT'] += 1
            elif sql.startswith('UPDATE'):
                breakdown['UPDATE'] += 1
            elif sql.startswith('DELETE'):
                breakdown['DELETE'] += 1
            else:
                breakdown['OTHER'] += 1

    return breakdown


# Middleware for automatic view performance tracking
class PerformanceMonitoringMiddleware:
    """
    Middleware to automatically track view performance.

    Add to MIDDLEWARE in settings.py:
        MIDDLEWARE = [
            ...
            'detail_project.utils.performance.PerformanceMonitoringMiddleware',
        ]
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration = (time.time() - start_time) * 1000

        # Store metric
        metric = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'duration_ms': duration,
            'status_code': response.status_code
        }

        METRICS['views'].append(metric)

        # Add performance header
        response['X-Response-Time'] = f"{duration:.2f}ms"

        # Log slow requests
        if duration > THRESHOLDS['VIEW_ERROR']:
            logger.error(
                f"Slow request: {request.method} {request.path} "
                f"- {duration:.2f}ms (status: {response.status_code})"
            )

        return response
