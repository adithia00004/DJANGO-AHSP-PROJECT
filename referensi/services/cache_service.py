"""
Cache service for managing Redis caching strategies.

Phase 4: Redis Cache Layer
- Centralized cache management
- Cache key generation
- Cache invalidation strategies
- Performance monitoring
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable, Optional, TypeVar
from functools import wraps

from django.core.cache import cache
from django.conf import settings
from django.db.models import Model, QuerySet

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheService:
    """
    Centralized cache service for AHSP application.

    Provides methods for:
    - Cache key generation
    - Cache get/set with logging
    - Cache invalidation
    - Bulk operations
    """

    # Cache key prefixes
    PREFIX_SEARCH = "search"
    PREFIX_AHSP = "ahsp"
    PREFIX_RINCIAN = "rincian"
    PREFIX_AUDIT = "audit"
    PREFIX_DASHBOARD = "dashboard"
    PREFIX_STATS = "stats"

    # Default timeouts (in seconds)
    TIMEOUT_SHORT = 300      # 5 minutes
    TIMEOUT_MEDIUM = 900     # 15 minutes
    TIMEOUT_LONG = 3600      # 1 hour
    TIMEOUT_VERY_LONG = 86400  # 24 hours

    @classmethod
    def generate_key(cls, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from prefix and parameters.

        Args:
            prefix: Cache key prefix (e.g., 'search', 'ahsp')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            str: Generated cache key

        Example:
            >>> CacheService.generate_key('search', 'pekerjaan', limit=50)
            'ahsp:search:a1b2c3d4e5f6...'
        """
        # Build parameter string
        params = []

        # Add positional args
        for arg in args:
            if isinstance(arg, (list, tuple, set)):
                params.append(','.join(str(x) for x in arg))
            else:
                params.append(str(arg))

        # Add keyword args (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            if value is not None:
                if isinstance(value, (list, tuple, set)):
                    value_str = ','.join(str(x) for x in value)
                else:
                    value_str = str(value)
                params.append(f"{key}={value_str}")

        # Create hash of parameters
        param_string = '|'.join(params)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()[:12]

        # Format: ahsp:<prefix>:<param_hash>
        return f"ahsp:{prefix}:{param_hash}"

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get value from cache with logging.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        try:
            value = cache.get(key, default)
            if value is not None and value != default:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache GET error for key {key}: {e}")
            return default

    @classmethod
    def set(cls, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set value in cache with logging.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Timeout in seconds (None = default)

        Returns:
            bool: True if successful
        """
        try:
            cache.set(key, value, timeout=timeout)
            logger.debug(f"Cache SET: {key} (timeout={timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {e}")
            return False

    @classmethod
    def delete(cls, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            bool: True if successful
        """
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {e}")
            return False

    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., 'ahsp:search:*')

        Returns:
            int: Number of keys deleted
        """
        try:
            # django-redis specific method
            deleted = cache.delete_pattern(pattern)
            logger.info(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
            return deleted
        except AttributeError:
            # Fallback if not using django-redis
            logger.warning(f"delete_pattern not supported, skipping: {pattern}")
            return 0
        except Exception as e:
            logger.error(f"Cache DELETE PATTERN error for {pattern}: {e}")
            return 0

    @classmethod
    def get_or_set(cls, key: str, default_callable: Callable[[], T],
                   timeout: Optional[int] = None) -> T:
        """
        Get value from cache or compute and set if missing.

        Args:
            key: Cache key
            default_callable: Function to compute value if cache miss
            timeout: Timeout in seconds

        Returns:
            Cached or computed value

        Example:
            >>> def expensive_query():
            ...     return AHSPReferensi.objects.all()[:100]
            >>> results = CacheService.get_or_set('ahsp:all', expensive_query, 3600)
        """
        value = cls.get(key)

        if value is None:
            logger.debug(f"Cache MISS - Computing: {key}")
            value = default_callable()
            cls.set(key, value, timeout=timeout)

        return value

    @classmethod
    def invalidate_search_cache(cls) -> int:
        """
        Invalidate all search-related caches.

        Returns:
            int: Number of keys invalidated
        """
        patterns = [
            f"ahsp:{cls.PREFIX_SEARCH}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            total_deleted += cls.delete_pattern(pattern)

        logger.info(f"Invalidated {total_deleted} search cache keys")
        return total_deleted

    @classmethod
    def invalidate_ahsp_cache(cls, ahsp_id: Optional[int] = None) -> int:
        """
        Invalidate AHSP-related caches.

        Args:
            ahsp_id: Specific AHSP ID to invalidate, or None for all

        Returns:
            int: Number of keys invalidated
        """
        if ahsp_id:
            pattern = f"ahsp:{cls.PREFIX_AHSP}:*{ahsp_id}*"
        else:
            pattern = f"ahsp:{cls.PREFIX_AHSP}:*"

        deleted = cls.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} AHSP cache keys")
        return deleted

    @classmethod
    def invalidate_audit_cache(cls) -> int:
        """
        Invalidate all audit-related caches.

        Returns:
            int: Number of keys invalidated
        """
        patterns = [
            f"ahsp:{cls.PREFIX_AUDIT}:*",
            f"ahsp:{cls.PREFIX_DASHBOARD}:*",
            f"ahsp:{cls.PREFIX_STATS}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            total_deleted += cls.delete_pattern(pattern)

        logger.info(f"Invalidated {total_deleted} audit cache keys")
        return total_deleted

    @classmethod
    def invalidate_all(cls) -> int:
        """
        Clear all application caches.

        Returns:
            int: Number of keys invalidated
        """
        deleted = cls.delete_pattern("ahsp:*")
        logger.warning(f"Invalidated ALL caches ({deleted} keys)")
        return deleted

    @classmethod
    def get_stats(cls) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics
        """
        try:
            # django-redis specific
            from django_redis import get_redis_connection

            redis_conn = get_redis_connection("default")
            info = redis_conn.info()

            return {
                'connected': True,
                'total_keys': redis_conn.dbsize(),
                'used_memory': info.get('used_memory_human', 'N/A'),
                'hit_rate': info.get('keyspace_hits', 0) / max(
                    info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1
                ) * 100,
                'uptime_seconds': info.get('uptime_in_seconds', 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'connected': False,
                'error': str(e),
            }


def cached_queryset(prefix: str, timeout: int = CacheService.TIMEOUT_MEDIUM):
    """
    Decorator to cache queryset results.

    Args:
        prefix: Cache key prefix
        timeout: Cache timeout in seconds

    Example:
        >>> @cached_queryset('ahsp_all', timeout=3600)
        ... def get_all_ahsp():
        ...     return AHSPReferensi.objects.all()
    """
    def decorator(func: Callable[..., QuerySet]) -> Callable[..., list]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = CacheService.generate_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = CacheService.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Compute value
            result = func(*args, **kwargs)

            # Convert QuerySet to list for caching
            if isinstance(result, QuerySet):
                result_list = list(result)
            else:
                result_list = result

            # Cache result
            CacheService.set(cache_key, result_list, timeout=timeout)

            return result_list

        return wrapper
    return decorator


def cached_method(timeout: int = CacheService.TIMEOUT_MEDIUM):
    """
    Decorator to cache method results.

    Args:
        timeout: Cache timeout in seconds

    Example:
        >>> class MyClass:
        ...     @cached_method(timeout=600)
        ...     def expensive_computation(self, x, y):
        ...         return x ** y
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key using function name and arguments
            cache_key = CacheService.generate_key(
                func.__name__,
                *args[1:],  # Skip 'self'
                **kwargs
            )

            # Try cache first
            result = CacheService.get(cache_key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            CacheService.set(cache_key, result, timeout=timeout)

            return result

        return wrapper
    return decorator


class CacheInvalidationMixin:
    """
    Mixin for Django models to automatically invalidate cache on save/delete.

    Usage:
        class MyModel(CacheInvalidationMixin, models.Model):
            cache_prefix = 'mymodel'
            ...
    """

    cache_prefix: str = None

    def save(self, *args, **kwargs):
        """Override save to invalidate cache."""
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        """Override delete to invalidate cache."""
        result = super().delete(*args, **kwargs)
        self._invalidate_cache()
        return result

    def _invalidate_cache(self):
        """Invalidate model-specific cache."""
        if self.cache_prefix:
            pattern = f"ahsp:{self.cache_prefix}:*"
            CacheService.delete_pattern(pattern)
            logger.info(f"Invalidated cache for {self.__class__.__name__}")


# Convenience instance
cache_service = CacheService()
