"""
Pytest configuration for referensi tests.

Disables caching to ensure consistent test behavior.
Creates PostgreSQL extensions required for fuzzy search tests.
"""

import pytest
from django.db import connection


@pytest.fixture(scope="session", autouse=True)
def create_postgres_extensions(django_db_setup, django_db_blocker):
    """
    Create PostgreSQL extensions required for full-text and fuzzy search.

    This fixture runs once at the start of the test session and ensures
    that pg_trgm and btree_gin extensions are available in the test database.

    Required for:
    - Fuzzy search with trigram similarity (TrigramSimilarity)
    - Advanced GIN indexes for full-text search
    - Typo-tolerant search functionality
    """
    with django_db_blocker.unblock():
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                try:
                    # Create pg_trgm extension for trigram similarity
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                    print("\n✅ Created pg_trgm extension in test database")
                except Exception as e:
                    print(f"\n⚠️  Could not create pg_trgm extension: {e}")

                try:
                    # Create btree_gin extension for GIN indexes
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
                    print("✅ Created btree_gin extension in test database")
                except Exception as e:
                    print(f"⚠️  Could not create btree_gin extension: {e}")

                # Verify extensions created
                cursor.execute("""
                    SELECT extname, extversion
                    FROM pg_extension
                    WHERE extname IN ('pg_trgm', 'btree_gin')
                    ORDER BY extname
                """)
                extensions = cursor.fetchall()
                if extensions:
                    print("\n📦 PostgreSQL Extensions in Test Database:")
                    for ext_name, ext_version in extensions:
                        print(f"   - {ext_name} (v{ext_version})")
                else:
                    print("\n⚠️  No extensions found in test database")


@pytest.fixture(autouse=True)
def disable_fts_cache(settings):
    """
    Disable full-text search caching during tests.

    This ensures that search methods return QuerySets instead of lists,
    which is what tests expect.
    """
    settings.FTS_CACHE_RESULTS = False
    return settings
