"""
Migration to add PostgreSQL full-text search capabilities.

PHASE 3: Database Search Optimization

This migration adds:
1. Generated tsvector columns for full-text search
2. GIN indexes for fast searching
3. Weighted search (A: code, B: name, C: classification)

Performance improvement: 10-100x faster search on large datasets.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('referensi', '0017_auditlogsummary_securityauditlog'),
    ]

    operations = [
        # ================================================================
        # AHSPReferensi: Add search vector for jobs
        # ================================================================
        migrations.RunSQL(
            # Forward: Create search_vector column
            sql="""
            -- Add generated tsvector column for AHSPReferensi
            ALTER TABLE referensi_ahspreferensi
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('simple', coalesce(kode_ahsp, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(nama_ahsp, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(klasifikasi, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(sub_klasifikasi, '')), 'C')
            ) STORED;

            -- Create GIN index for fast full-text search
            CREATE INDEX IF NOT EXISTS ix_ahsp_search_vector
            ON referensi_ahspreferensi
            USING GIN(search_vector);

            -- Add comment for documentation
            COMMENT ON COLUMN referensi_ahspreferensi.search_vector IS
            'Full-text search vector (auto-generated). Weighted: A=code, B=name, C=classification';
            """,
            # Reverse: Drop search_vector column and index
            reverse_sql="""
            DROP INDEX IF EXISTS ix_ahsp_search_vector;
            ALTER TABLE referensi_ahspreferensi DROP COLUMN IF EXISTS search_vector;
            """
        ),

        # ================================================================
        # RincianReferensi: Add search vector for items
        # ================================================================
        migrations.RunSQL(
            # Forward: Create search_vector column
            sql="""
            -- Add generated tsvector column for RincianReferensi
            ALTER TABLE referensi_rincianreferensi
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('simple', coalesce(kode_item, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(uraian_item, '')), 'B')
            ) STORED;

            -- Create GIN index for fast full-text search
            CREATE INDEX IF NOT EXISTS ix_rincian_search_vector
            ON referensi_rincianreferensi
            USING GIN(search_vector);

            -- Add comment for documentation
            COMMENT ON COLUMN referensi_rincianreferensi.search_vector IS
            'Full-text search vector (auto-generated). Weighted: A=code, B=description';
            """,
            # Reverse: Drop search_vector column and index
            reverse_sql="""
            DROP INDEX IF EXISTS ix_rincian_search_vector;
            ALTER TABLE referensi_rincianreferensi DROP COLUMN IF EXISTS search_vector;
            """
        ),

        # ================================================================
        # Analyze tables for query planner optimization
        # ================================================================
        migrations.RunSQL(
            sql="""
            -- Update statistics for query planner
            ANALYZE referensi_ahspreferensi;
            ANALYZE referensi_rincianreferensi;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
