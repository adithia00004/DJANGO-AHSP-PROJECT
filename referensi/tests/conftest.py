"""
Pytest configuration for referensi tests.

Disables caching to ensure consistent test behavior.
"""

import pytest


@pytest.fixture(autouse=True)
def disable_fts_cache(settings):
    """
    Disable full-text search caching during tests.

    This ensures that search methods return QuerySets instead of lists,
    which is what tests expect.
    """
    settings.FTS_CACHE_RESULTS = False
    return settings
