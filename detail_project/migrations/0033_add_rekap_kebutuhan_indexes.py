# Generated manually for Rekap Kebutuhan performance optimization
# Phase 1: Quick wins - database indexes

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0032_add_dashboard_performance_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- ================================================================
                -- REKAP KEBUTUHAN PERFORMANCE INDEXES
                -- ================================================================
                -- Created: 2026-01-11
                -- Purpose: Optimize slow rekap kebutuhan endpoints (58s -> <10s target)
                -- Context: See REKAP_KEBUTUHAN_OPTIMIZATION_PLAN_2026-01-11.md
                --
                -- Production Note: For production deployment, consider using
                -- CREATE INDEX CONCURRENTLY to avoid table locking
                -- ================================================================

                -- Index 1: DetailAHSPExpanded - Fast lookup by project + pekerjaan
                -- Used in: services.py:2307-2325 (compute_kebutuhan_items batch query)
                -- Query pattern: DetailAHSPExpanded.objects.filter(project=X, pekerjaan_id__in=[...])
                CREATE INDEX IF NOT EXISTS idx_detail_ahsp_expanded_project_pekerjaan
                ON detail_project_detailahspexpanded(project_id, pekerjaan_id);

                -- Index 2: VolumePekerjaan - Fast lookup by project + pekerjaan
                -- Used in: services.py:2265-2269 (volume query for kebutuhan calculation)
                -- Query pattern: VolumePekerjaan.objects.filter(project=X, pekerjaan_id__in=[...])
                CREATE INDEX IF NOT EXISTS idx_volume_pekerjaan_project_pekerjaan
                ON detail_project_volumepekerjaan(project_id, pekerjaan_id);

                -- Index 3: PekerjaanTahapan - Fast lookup by pekerjaan + tahapan
                -- Used in: services.py:2643-2650 (timeline assignment queries)
                -- Query pattern: PekerjaanTahapan.objects.filter(pekerjaan_id__in=[...])
                CREATE INDEX IF NOT EXISTS idx_pekerjaan_tahapan_pekerjaan_tahapan
                ON detail_project_pekerjaantahapan(pekerjaan_id, tahapan_id);

                -- Index 4: Pekerjaan - Fast filtering by project + sub_klasifikasi
                -- Used in: services.py:2225-2245 (filtering pekerjaan by sub_klasifikasi)
                -- Query pattern: Pekerjaan.objects.filter(project=X, sub_klasifikasi_id__in=[...])
                CREATE INDEX IF NOT EXISTS idx_pekerjaan_project_subklas
                ON detail_project_pekerjaan(project_id, sub_klasifikasi_id);
            """,
            reverse_sql="""
                -- Drop indexes in reverse order
                DROP INDEX IF EXISTS idx_pekerjaan_project_subklas;
                DROP INDEX IF EXISTS idx_pekerjaan_tahapan_pekerjaan_tahapan;
                DROP INDEX IF EXISTS idx_volume_pekerjaan_project_pekerjaan;
                DROP INDEX IF EXISTS idx_detail_ahsp_expanded_project_pekerjaan;
            """,
        ),
    ]
