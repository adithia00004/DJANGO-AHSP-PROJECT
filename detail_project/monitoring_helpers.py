# detail_project/monitoring_helpers.py
"""
Monitoring Helpers for AHSP Workflow

Provides structured logging and metrics collection for critical operations:
- Bundle expansion tracking
- Cascade re-expansion monitoring
- Orphan detection
- Performance metrics

Part of FASE 0.3: Monitoring Setup

Usage:
    from .monitoring_helpers import monitor, log_operation, collect_metric

    # Structured logging with context
    log_operation(
        'bundle_expansion',
        project_id=1,
        pekerjaan_id=5,
        bundle_count=3,
        component_count=15
    )

    # Metrics collection
    collect_metric('cascade_depth', depth=2, project_id=1)

    # Decorator for automatic timing
    @monitor('populate_expanded')
    def _populate_expanded_from_raw(project, pekerjaan):
        ...
"""

import logging
import time
from functools import wraps
from typing import Any, Dict, Optional
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

def log_operation(
    operation: str,
    level: str = 'info',
    **context: Any
) -> None:
    """
    Log operation with structured context.

    Args:
        operation: Operation name (e.g., 'bundle_expansion', 'cascade_reexpand')
        level: Log level ('debug', 'info', 'warning', 'error')
        **context: Additional context key-value pairs

    Example:
        log_operation(
            'bundle_expansion',
            project_id=1,
            pekerjaan_id=5,
            bundle_count=3,
            component_count=15,
            duration_ms=125.5
        )

    Output:
        [BUNDLE_EXPANSION] project_id=1 pekerjaan_id=5 bundle_count=3
                          component_count=15 duration_ms=125.5
    """
    # Convert Decimal to float for logging
    formatted_context = {}
    for key, value in context.items():
        if isinstance(value, Decimal):
            formatted_context[key] = float(value)
        else:
            formatted_context[key] = value

    # Build structured message
    operation_upper = operation.upper()
    context_str = " ".join(f"{k}={v}" for k, v in formatted_context.items())
    message = f"[{operation_upper}] {context_str}"

    # Log at appropriate level
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message)


def log_error(
    operation: str,
    error: Exception,
    **context: Any
) -> None:
    """
    Log error with structured context.

    Args:
        operation: Operation name
        error: Exception that occurred
        **context: Additional context

    Example:
        try:
            expand_bundle(...)
        except ValueError as e:
            log_error('bundle_expansion', e, pekerjaan_id=5)
    """
    log_operation(
        operation,
        level='error',
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def monitor(operation_name: str):
    """
    Decorator for monitoring function execution time.

    Args:
        operation_name: Name of operation for logging

    Example:
        @monitor('populate_expanded')
        def _populate_expanded_from_raw(project, pekerjaan):
            ...

    Output:
        [POPULATE_EXPANDED] START project_id=1 pekerjaan_id=5
        [POPULATE_EXPANDED] COMPLETE duration_ms=125.5 project_id=1 pekerjaan_id=5
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract context from common arguments
            context = {}

            # Try to extract project_id
            if args:
                if hasattr(args[0], 'id'):
                    context['project_id'] = args[0].id
                if len(args) > 1 and hasattr(args[1], 'id'):
                    context['pekerjaan_id'] = args[1].id

            # Add explicit kwargs
            if 'project' in kwargs and hasattr(kwargs['project'], 'id'):
                context['project_id'] = kwargs['project'].id
            if 'pekerjaan' in kwargs and hasattr(kwargs['pekerjaan'], 'id'):
                context['pekerjaan_id'] = kwargs['pekerjaan'].id

            # Log start
            log_operation(f"{operation_name}_start", **context)

            # Execute function with timing
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Log completion
                log_operation(
                    f"{operation_name}_complete",
                    duration_ms=round(duration_ms, 2),
                    **context
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Log error
                log_error(
                    operation_name,
                    e,
                    duration_ms=round(duration_ms, 2),
                    **context
                )
                raise

        return wrapper
    return decorator


# ============================================================================
# METRICS COLLECTION
# ============================================================================

class MetricsCollector:
    """
    In-memory metrics collector for AHSP workflow operations.

    Tracks counts and distributions for:
    - Bundle usage
    - Cascade operations
    - Orphan creation
    - Expansion depth
    - Operation duration

    Note: In production, this should be replaced with proper monitoring
    system (e.g., Prometheus, StatsD, CloudWatch).
    """

    def __init__(self):
        self.metrics: Dict[str, list] = {
            'bundle_expansions': [],
            'cascade_operations': [],
            'orphan_detections': [],
            'expansion_depths': [],
            'operation_durations': [],
        }

    def record(self, metric_name: str, value: Any, **tags: Any) -> None:
        """
        Record a metric value with optional tags.

        Args:
            metric_name: Name of metric
            value: Metric value
            **tags: Additional tags (project_id, pekerjaan_id, etc.)

        Example:
            collector.record('bundle_expansion', 1, project_id=1, bundle_count=3)
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        entry = {
            'value': value,
            'timestamp': time.time(),
            **tags
        }
        self.metrics[metric_name].append(entry)

        # Keep only last 1000 entries per metric (memory limit)
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]

    def get_stats(self, metric_name: str) -> Dict[str, Any]:
        """
        Get statistics for a metric.

        Args:
            metric_name: Name of metric

        Returns:
            Dict with count, min, max, avg, recent values

        Example:
            stats = collector.get_stats('cascade_operations')
            # {'count': 45, 'min': 1, 'max': 5, 'avg': 2.3, 'recent': [...]}
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {'count': 0}

        entries = self.metrics[metric_name]
        values = [e['value'] for e in entries]

        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'recent': entries[-10:],  # Last 10 entries
        }

    def get_summary(self) -> Dict[str, Dict]:
        """
        Get summary of all metrics.

        Returns:
            Dict of metric_name -> stats

        Example:
            summary = collector.get_summary()
            for metric, stats in summary.items():
                print(f"{metric}: {stats['count']} operations")
        """
        return {
            metric: self.get_stats(metric)
            for metric in self.metrics.keys()
        }

    def reset(self) -> None:
        """Reset all metrics."""
        for metric in self.metrics.keys():
            self.metrics[metric] = []


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def collect_metric(metric_name: str, value: Any = 1, **tags: Any) -> None:
    """
    Collect a metric value (convenience function).

    Args:
        metric_name: Name of metric
        value: Metric value (default: 1 for counters)
        **tags: Additional tags

    Example:
        collect_metric('bundle_expansion', project_id=1, bundle_count=3)
        collect_metric('cascade_depth', value=2, project_id=1)
    """
    _metrics_collector.record(metric_name, value, **tags)


def get_metrics_summary() -> Dict[str, Dict]:
    """
    Get summary of all collected metrics.

    Returns:
        Dict of metric_name -> stats

    Example:
        summary = get_metrics_summary()
        print(json.dumps(summary, indent=2))
    """
    return _metrics_collector.get_summary()


def reset_metrics() -> None:
    """Reset all collected metrics."""
    _metrics_collector.reset()


# ============================================================================
# OPERATION-SPECIFIC HELPERS
# ============================================================================

def log_bundle_expansion(
    project_id: int,
    pekerjaan_id: int,
    bundle_kode: str,
    ref_kind: str,
    ref_id: int,
    component_count: int,
    duration_ms: Optional[float] = None
) -> None:
    """
    Log bundle expansion operation.

    Args:
        project_id: Project ID
        pekerjaan_id: Pekerjaan ID
        bundle_kode: Bundle kode (LAIN item)
        ref_kind: Reference kind ('job' or 'ahsp')
        ref_id: Referenced pekerjaan/AHSP ID
        component_count: Number of components expanded
        duration_ms: Operation duration in milliseconds
    """
    context = {
        'project_id': project_id,
        'pekerjaan_id': pekerjaan_id,
        'bundle_kode': bundle_kode,
        'ref_kind': ref_kind,
        'ref_id': ref_id,
        'component_count': component_count,
    }

    if duration_ms is not None:
        context['duration_ms'] = duration_ms

    log_operation('bundle_expansion', **context)
    collect_metric('bundle_expansions', component_count, **context)


def log_cascade_operation(
    project_id: int,
    modified_pekerjaan_id: int,
    referencing_pekerjaan_ids: list,
    cascade_depth: int,
    re_expanded_count: int,
    duration_ms: Optional[float] = None
) -> None:
    """
    Log cascade re-expansion operation.

    Args:
        project_id: Project ID
        modified_pekerjaan_id: ID of modified pekerjaan
        referencing_pekerjaan_ids: List of pekerjaan IDs that reference it
        cascade_depth: Current cascade depth
        re_expanded_count: Total pekerjaan re-expanded
        duration_ms: Operation duration in milliseconds
    """
    context = {
        'project_id': project_id,
        'modified_pekerjaan_id': modified_pekerjaan_id,
        'referencing_count': len(referencing_pekerjaan_ids),
        'referencing_ids': referencing_pekerjaan_ids,
        'cascade_depth': cascade_depth,
        're_expanded_count': re_expanded_count,
    }

    if duration_ms is not None:
        context['duration_ms'] = duration_ms

    log_operation('cascade_reexpansion', **context)
    collect_metric('cascade_operations', re_expanded_count, **context)
    collect_metric('cascade_depth', cascade_depth, **context)


def log_orphan_detection(
    project_id: int,
    orphan_count: int,
    total_items: int
) -> None:
    """
    Log orphan detection operation.

    Args:
        project_id: Project ID
        orphan_count: Number of orphaned items detected
        total_items: Total HargaItemProject count
    """
    orphan_percent = (orphan_count / total_items * 100) if total_items > 0 else 0

    context = {
        'project_id': project_id,
        'orphan_count': orphan_count,
        'total_items': total_items,
        'orphan_percent': round(orphan_percent, 2),
    }

    log_operation('orphan_detection', **context)
    collect_metric('orphan_detections', orphan_count, **context)


def log_circular_dependency_check(
    project_id: int,
    source_pekerjaan_id: int,
    target_pekerjaan_id: int,
    is_circular: bool
) -> None:
    """
    Log circular dependency check.

    Args:
        project_id: Project ID
        source_pekerjaan_id: Source pekerjaan ID
        target_pekerjaan_id: Target pekerjaan ID
        is_circular: Whether circular dependency was detected
    """
    context = {
        'project_id': project_id,
        'source_pekerjaan_id': source_pekerjaan_id,
        'target_pekerjaan_id': target_pekerjaan_id,
        'is_circular': is_circular,
    }

    level = 'warning' if is_circular else 'debug'
    log_operation('circular_dependency_check', level=level, **context)

    if is_circular:
        collect_metric('circular_dependencies', 1, **context)


def log_optimistic_lock_conflict(
    project_id: int,
    pekerjaan_id: int,
    client_timestamp: str,
    server_timestamp: str
) -> None:
    """
    Log optimistic locking conflict.

    Args:
        project_id: Project ID
        pekerjaan_id: Pekerjaan ID
        client_timestamp: Client's last known timestamp
        server_timestamp: Server's current timestamp
    """
    context = {
        'project_id': project_id,
        'pekerjaan_id': pekerjaan_id,
        'client_timestamp': client_timestamp,
        'server_timestamp': server_timestamp,
    }

    log_operation('optimistic_lock_conflict', level='warning', **context)
    collect_metric('lock_conflicts', 1, **context)


# ============================================================================
# HEALTH CHECK
# ============================================================================

def get_monitoring_health() -> Dict[str, Any]:
    """
    Get monitoring system health status.

    Returns:
        Dict with:
        - is_healthy: bool
        - metrics_count: Total metrics collected
        - recent_operations: Recent operation summary

    Example:
        health = get_monitoring_health()
        if not health['is_healthy']:
            logger.error("Monitoring system unhealthy!")
    """
    summary = get_metrics_summary()

    total_operations = sum(
        stats.get('count', 0)
        for stats in summary.values()
    )

    return {
        'is_healthy': True,
        'metrics_count': total_operations,
        'summary': summary,
    }
