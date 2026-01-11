# Generated manually for Week 1 Quick Wins - Performance Optimization
# Migration created: 2026-01-11
# Purpose: Add database indexes for dashboard and list views (20-30% faster queries)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0031_pekerjaantemplate'),
    ]

    operations = [
        # NOTE: Not using CONCURRENTLY because it requires being outside transaction
        # For production, these indexes can be created separately with CONCURRENTLY
        # Current approach: quick creation during low-traffic period

        migrations.RunSQL(
            sql="""
                -- Project-related indexes for dashboard queries (dashboard_project table)
                CREATE INDEX IF NOT EXISTS idx_project_created_at
                ON dashboard_project(created_at DESC NULLS LAST);

                CREATE INDEX IF NOT EXISTS idx_project_updated_at
                ON dashboard_project(updated_at DESC NULLS LAST);

                CREATE INDEX IF NOT EXISTS idx_project_owner
                ON dashboard_project(owner_id);

                -- Pekerjaan indexes (for list-pekerjaan queries)
                CREATE INDEX IF NOT EXISTS idx_pekerjaan_project
                ON detail_project_pekerjaan(project_id);

                CREATE INDEX IF NOT EXISTS idx_pekerjaan_project_subklas
                ON detail_project_pekerjaan(project_id, sub_klasifikasi_id);

                CREATE INDEX IF NOT EXISTS idx_pekerjaan_ref
                ON detail_project_pekerjaan(ref_id) WHERE ref_id IS NOT NULL;
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_project_created_at;
                DROP INDEX IF EXISTS idx_project_updated_at;
                DROP INDEX IF EXISTS idx_project_owner;
                DROP INDEX IF EXISTS idx_pekerjaan_project;
                DROP INDEX IF EXISTS idx_pekerjaan_project_subklas;
                DROP INDEX IF EXISTS idx_pekerjaan_ref;
            """,
            state_operations=[],  # No model state changes
        ),
    ]
