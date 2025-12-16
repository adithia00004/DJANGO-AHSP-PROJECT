"""
Custom decorators for detail_project app
"""

from .api_deprecation import api_deprecated, get_deprecation_metrics, reset_deprecation_metrics

__all__ = [
    'api_deprecated',
    'get_deprecation_metrics',
    'reset_deprecation_metrics',
]
