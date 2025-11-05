"""
Migration to enable pg_trgm extension for fuzzy search.

PHASE 3: Database Search Optimization - Fuzzy Search Support

This migration enables the pg_trgm extension which provides:
1. Trigram similarity functions for fuzzy matching
2. Support for typo-tolerant search
3. GIN/GiST indexes for fast similarity search

Required for fuzzy_search_ahsp() method in AHSPRepository.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('referensi', '0018_add_fulltext_search'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward: Enable pg_trgm extension
            sql="""
            -- Enable pg_trgm extension for fuzzy/similarity search
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            """,
            # Reverse: Drop pg_trgm extension (careful: might affect other apps)
            reverse_sql="""
            DROP EXTENSION IF EXISTS pg_trgm;
            """
        ),
    ]
