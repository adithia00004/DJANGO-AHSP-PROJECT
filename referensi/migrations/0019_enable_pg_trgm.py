"""
Migration to enable PostgreSQL extensions for advanced search.

PHASE 3: Database Search Optimization - Fuzzy Search Support

This migration enables required PostgreSQL extensions:
1. pg_trgm: Trigram similarity functions for fuzzy matching, typo-tolerant search
2. btree_gin: Support for multi-column GIN indexes

Required for fuzzy_search_ahsp() method in AHSPRepository and advanced indexing.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('referensi', '0018_add_fulltext_search'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward: Enable pg_trgm extension for fuzzy search
            sql="""
            -- Enable pg_trgm extension for fuzzy/similarity search
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            """,
            # Reverse: Drop pg_trgm extension (careful: might affect other apps)
            reverse_sql="""
            DROP EXTENSION IF EXISTS pg_trgm;
            """
        ),
        migrations.RunSQL(
            # Forward: Enable btree_gin extension for multi-column GIN indexes
            sql="""
            -- Enable btree_gin extension for advanced indexing
            CREATE EXTENSION IF NOT EXISTS btree_gin;
            """,
            # Reverse: Drop btree_gin extension
            reverse_sql="""
            DROP EXTENSION IF EXISTS btree_gin;
            """
        ),
    ]
