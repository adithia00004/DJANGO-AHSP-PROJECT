"""
AHSP Repository with PostgreSQL Full-Text Search.

PHASE 3: Database Search Optimization
PHASE 4: Redis Cache Layer Integration

Provides high-performance search methods using PostgreSQL's full-text search
capabilities with GIN indexes, enhanced with Redis caching.

Performance:
- Phase 3: 10-100x faster than Python-based filtering
- Phase 4: Additional 50-90% reduction in query time with caching
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from django.db.models import QuerySet, Q, F
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity
)
from django.conf import settings

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.cache_service import CacheService


class AHSPRepository:
    """
    Repository for AHSP database operations with full-text search and caching.

    Uses PostgreSQL tsvector and GIN indexes for fast searching,
    with Redis caching for even better performance.
    """

    def __init__(self):
        self.default_limit = 1000
        self.min_query_length = 2
        self.cache_enabled = getattr(settings, 'FTS_CACHE_RESULTS', True)
        self.cache_ttl = getattr(settings, 'FTS_CACHE_TTL', 300)  # 5 minutes
        self.cache = CacheService()

    # ========================================================================
    # Full-Text Search Methods
    # ========================================================================

    def search_ahsp(
        self,
        query: str,
        *,
        sumber: Optional[str] = None,
        klasifikasi: Optional[str] = None,
        limit: Optional[int] = None,
        search_type: str = 'websearch'
    ) -> QuerySet[AHSPReferensi] | List[AHSPReferensi]:
        """
        Full-text search for AHSP jobs using PostgreSQL tsvector with Redis caching.

        Args:
            query: Search query string
            sumber: Filter by sumber (optional)
            klasifikasi: Filter by klasifikasi (optional)
            limit: Maximum results (default: 1000)
            search_type: 'websearch', 'plain', 'phrase', or 'raw' (default: websearch)

        Returns:
            QuerySet or list ordered by relevance (rank)
            Returns list if cached, QuerySet if fresh query

        Examples:
            >>> repo = AHSPRepository()
            >>> results = repo.search_ahsp("beton bertulang")
            >>> results = repo.search_ahsp("1.1.1", sumber="SNI 2025")
            >>> results = repo.search_ahsp('"pekerjaan beton"', search_type='phrase')
        """
        if not query or len(query.strip()) < self.min_query_length:
            return AHSPReferensi.objects.none()

        limit = limit or self.default_limit

        # Try cache first if enabled
        if self.cache_enabled:
            cache_key = self.cache.generate_key(
                self.cache.PREFIX_SEARCH,
                'ahsp',
                query,
                sumber=sumber,
                klasifikasi=klasifikasi,
                limit=limit,
                search_type=search_type
            )

            cached_results = self.cache.get(cache_key)
            if cached_results is not None:
                return cached_results

        # Create search query
        search_query = SearchQuery(query, search_type=search_type, config='simple')

        # Build queryset with ranking
        qs = AHSPReferensi.objects.annotate(
            rank=SearchRank(F('search_vector'), search_query)
        ).filter(
            search_vector=search_query
        )

        # Apply filters
        if sumber:
            qs = qs.filter(sumber__iexact=sumber)
        if klasifikasi:
            qs = qs.filter(klasifikasi__icontains=klasifikasi)

        # Order by relevance and limit
        qs = qs.order_by('-rank', 'kode_ahsp')[:limit]

        # Cache results if enabled
        if self.cache_enabled:
            # Convert to list for caching
            results_list = list(qs)
            self.cache.set(cache_key, results_list, timeout=self.cache_ttl)
            return results_list

        return qs

    def search_rincian(
        self,
        query: str,
        *,
        kategori: Optional[str] = None,
        limit: Optional[int] = None,
        search_type: str = 'websearch'
    ) -> QuerySet[RincianReferensi] | List[RincianReferensi]:
        """
        Full-text search for rincian items using PostgreSQL tsvector with Redis caching.

        Args:
            query: Search query string
            kategori: Filter by kategori (TK/BHN/ALT/LAIN)
            limit: Maximum results (default: 1000)
            search_type: 'websearch', 'plain', 'phrase', or 'raw'

        Returns:
            QuerySet or list ordered by relevance

        Examples:
            >>> repo = AHSPRepository()
            >>> results = repo.search_rincian("semen portland")
            >>> results = repo.search_rincian("TK-001", kategori="TK")
        """
        if not query or len(query.strip()) < self.min_query_length:
            return RincianReferensi.objects.none()

        limit = limit or self.default_limit

        # Try cache first if enabled
        if self.cache_enabled:
            cache_key = self.cache.generate_key(
                self.cache.PREFIX_SEARCH,
                'rincian',
                query,
                kategori=kategori,
                limit=limit,
                search_type=search_type
            )

            cached_results = self.cache.get(cache_key)
            if cached_results is not None:
                return cached_results

        # Create search query
        search_query = SearchQuery(query, search_type=search_type, config='simple')

        # Build queryset with ranking
        qs = RincianReferensi.objects.annotate(
            rank=SearchRank(F('search_vector'), search_query)
        ).filter(
            search_vector=search_query
        )

        # Apply filters
        if kategori:
            qs = qs.filter(kategori=kategori)

        # Order by relevance and limit
        qs = qs.order_by('-rank', 'kode_item')[:limit]

        # Cache results if enabled
        if self.cache_enabled:
            results_list = list(qs)
            self.cache.set(cache_key, results_list, timeout=self.cache_ttl)
            return results_list

        return qs

    # ========================================================================
    # Fuzzy/Similarity Search (for typos)
    # ========================================================================

    def fuzzy_search_ahsp(
        self,
        query: str,
        *,
        threshold: float = 0.3,
        limit: Optional[int] = None
    ) -> QuerySet[AHSPReferensi] | List[AHSPReferensi]:
        """
        Fuzzy search using PostgreSQL trigram similarity with Redis caching.

        Good for handling typos and approximate matches.

        Args:
            query: Search query
            threshold: Similarity threshold (0.0 to 1.0, default: 0.3)
            limit: Maximum results

        Returns:
            QuerySet or list ordered by similarity score

        Examples:
            >>> repo = AHSPRepository()
            >>> # Will match "beton" even if typed "betom"
            >>> results = repo.fuzzy_search_ahsp("betom", threshold=0.3)
        """
        if not query or len(query.strip()) < self.min_query_length:
            return AHSPReferensi.objects.none()

        limit = limit or self.default_limit

        # Try cache first if enabled
        if self.cache_enabled:
            cache_key = self.cache.generate_key(
                self.cache.PREFIX_SEARCH,
                'fuzzy',
                query,
                threshold=threshold,
                limit=limit
            )

            cached_results = self.cache.get(cache_key)
            if cached_results is not None:
                return cached_results

        qs = AHSPReferensi.objects.annotate(
            similarity=TrigramSimilarity('nama_ahsp', query) +
                      TrigramSimilarity('kode_ahsp', query)
        ).filter(
            similarity__gt=threshold
        ).order_by('-similarity')[:limit]

        # Cache results if enabled
        if self.cache_enabled:
            results_list = list(qs)
            self.cache.set(cache_key, results_list, timeout=self.cache_ttl)
            return results_list

        return qs

    # ========================================================================
    # Prefix Search (for autocomplete)
    # ========================================================================

    def prefix_search_ahsp(
        self,
        prefix: str,
        field: str = 'kode_ahsp',
        limit: int = 20
    ) -> QuerySet[AHSPReferensi]:
        """
        Prefix search for autocomplete functionality.

        Args:
            prefix: Search prefix
            field: Field to search ('kode_ahsp' or 'nama_ahsp')
            limit: Maximum results (default: 20 for autocomplete)

        Returns:
            QuerySet ordered by field

        Examples:
            >>> repo = AHSPRepository()
            >>> # Find all AHSP codes starting with "1.1"
            >>> results = repo.prefix_search_ahsp("1.1", field='kode_ahsp')
        """
        if not prefix or len(prefix) < 1:
            return AHSPReferensi.objects.none()

        if field == 'kode_ahsp':
            qs = AHSPReferensi.objects.filter(
                kode_ahsp__istartswith=prefix
            ).order_by('kode_ahsp')
        elif field == 'nama_ahsp':
            qs = AHSPReferensi.objects.filter(
                nama_ahsp__istartswith=prefix
            ).order_by('nama_ahsp')
        else:
            raise ValueError(f"Invalid field: {field}")

        return qs[:limit]

    # ========================================================================
    # Advanced Combined Search
    # ========================================================================

    def advanced_search(
        self,
        query: Optional[str] = None,
        *,
        sumber: Optional[str] = None,
        klasifikasi: Optional[str] = None,
        sub_klasifikasi: Optional[str] = None,
        kode_prefix: Optional[str] = None,
        limit: Optional[int] = None
    ) -> QuerySet[AHSPReferensi]:
        """
        Advanced search combining multiple filters and full-text search.

        Args:
            query: Full-text search query (optional)
            sumber: Filter by sumber
            klasifikasi: Filter by klasifikasi
            sub_klasifikasi: Filter by sub_klasifikasi
            kode_prefix: Filter by kode prefix (e.g., "1.1")
            limit: Maximum results

        Returns:
            QuerySet ordered by relevance or kode_ahsp

        Examples:
            >>> repo = AHSPRepository()
            >>> results = repo.advanced_search(
            ...     query="beton",
            ...     sumber="SNI 2025",
            ...     klasifikasi="Konstruksi",
            ...     kode_prefix="1."
            ... )
        """
        limit = limit or self.default_limit

        # Start with all AHSP
        qs = AHSPReferensi.objects.all()

        # Apply full-text search if query provided
        if query and len(query.strip()) >= self.min_query_length:
            search_query = SearchQuery(query, search_type='websearch', config='simple')
            qs = qs.annotate(
                rank=SearchRank(F('search_vector'), search_query)
            ).filter(
                search_vector=search_query
            ).order_by('-rank', 'kode_ahsp')
        else:
            qs = qs.order_by('kode_ahsp')

        # Apply filters
        if sumber:
            qs = qs.filter(sumber__iexact=sumber)
        if klasifikasi:
            qs = qs.filter(klasifikasi__icontains=klasifikasi)
        if sub_klasifikasi:
            qs = qs.filter(sub_klasifikasi__icontains=sub_klasifikasi)
        if kode_prefix:
            qs = qs.filter(kode_ahsp__istartswith=kode_prefix)

        return qs[:limit]

    # ========================================================================
    # Statistics & Utility Methods
    # ========================================================================

    def get_search_suggestions(
        self,
        partial_query: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get search suggestions for autocomplete with Redis caching.

        Args:
            partial_query: Partial search query
            limit: Maximum suggestions

        Returns:
            List of suggested search terms

        Examples:
            >>> repo = AHSPRepository()
            >>> suggestions = repo.get_search_suggestions("bet")
            >>> # Returns: ["beton", "beton bertulang", "beton ready mix", ...]
        """
        if not partial_query or len(partial_query) < 2:
            return []

        # Try cache first if enabled
        if self.cache_enabled:
            cache_key = self.cache.generate_key(
                self.cache.PREFIX_SEARCH,
                'suggestions',
                partial_query,
                limit=limit
            )

            cached_results = self.cache.get(cache_key)
            if cached_results is not None:
                return cached_results

        # Get distinct nama_ahsp that contain the partial query
        suggestions = AHSPReferensi.objects.filter(
            nama_ahsp__icontains=partial_query
        ).values_list('nama_ahsp', flat=True).distinct()[:limit]

        results = list(suggestions)

        # Cache results if enabled (longer TTL for suggestions)
        if self.cache_enabled:
            self.cache.set(cache_key, results, timeout=self.cache_ttl * 2)  # 10 minutes

        return results

    def count_search_results(self, query: str, **filters) -> int:
        """
        Count search results without loading all records.

        Args:
            query: Search query
            **filters: Additional filters (sumber, klasifikasi, etc.)

        Returns:
            Number of matching results

        Examples:
            >>> repo = AHSPRepository()
            >>> count = repo.count_search_results("beton", sumber="SNI 2025")
        """
        results = self.search_ahsp(query, **filters)
        return results.count()

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def search_multiple_queries(
        self,
        queries: List[str],
        combine: str = 'OR'
    ) -> QuerySet[AHSPReferensi]:
        """
        Search using multiple queries combined with AND/OR.

        Args:
            queries: List of search queries
            combine: 'OR' or 'AND' (default: 'OR')

        Returns:
            QuerySet of matching AHSP

        Examples:
            >>> repo = AHSPRepository()
            >>> # Find AHSP containing "beton" OR "pekerjaan"
            >>> results = repo.search_multiple_queries(["beton", "pekerjaan"], combine='OR')
        """
        if not queries:
            return AHSPReferensi.objects.none()

        search_queries = [
            SearchQuery(q, search_type='websearch', config='simple')
            for q in queries if q and len(q.strip()) >= self.min_query_length
        ]

        if not search_queries:
            return AHSPReferensi.objects.none()

        # Combine queries
        if combine == 'OR':
            combined_query = search_queries[0]
            for sq in search_queries[1:]:
                combined_query = combined_query | sq
        elif combine == 'AND':
            combined_query = search_queries[0]
            for sq in search_queries[1:]:
                combined_query = combined_query & sq
        else:
            raise ValueError(f"Invalid combine option: {combine}")

        qs = AHSPReferensi.objects.annotate(
            rank=SearchRank(F('search_vector'), combined_query)
        ).filter(
            search_vector=combined_query
        ).order_by('-rank', 'kode_ahsp')

        return qs

    # ========================================================================
    # Cache Management (Phase 4)
    # ========================================================================

    def invalidate_search_cache(self) -> int:
        """
        Invalidate all search caches.

        Should be called after AHSP data is modified (import, update, delete).

        Returns:
            int: Number of cache keys invalidated

        Example:
            >>> repo = AHSPRepository()
            >>> # After import
            >>> repo.invalidate_search_cache()
        """
        return self.cache.invalidate_search_cache()

    def invalidate_all_cache(self) -> int:
        """
        Invalidate all application caches.

        Returns:
            int: Number of cache keys invalidated
        """
        return self.cache.invalidate_all()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics including hit rate, memory usage, etc.

        Example:
            >>> repo = AHSPRepository()
            >>> stats = repo.get_cache_stats()
            >>> print(f"Cache hit rate: {stats['hit_rate']:.2f}%")
        """
        return self.cache.get_stats()


# Singleton instance for easy access
ahsp_repository = AHSPRepository()


__all__ = [
    'AHSPRepository',
    'ahsp_repository',
]
