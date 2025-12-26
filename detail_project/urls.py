# detail_project/urls.py
from django.urls import path
from . import views
from . import views_api
from . import views_export  # ← Clean import at root level!
from . import views_api_tahapan  # NEW IMPORT
from . import views_api_tahapan_v2  # V2 API with weekly canonical storage
from . import views_monitoring  # API deprecation monitoring

app_name = "detail_project"

urlpatterns = [
    # ===== Web views =====
    path('<int:project_id>/list-pekerjaan/',        views.list_pekerjaan_view,        name='list_pekerjaan'),
    path('<int:project_id>/volume-pekerjaan/',      views.volume_pekerjaan_view,      name='volume_pekerjaan'),

    path('<int:project_id>/template-ahsp/',         views.template_ahsp_view,         name='template_ahsp'),
    path('<int:project_id>/detail-ahsp/',           views.template_ahsp_view,         name='detail_ahsp_legacy'),
    path('<int:project_id>/harga-items/',           views.harga_items_view,           name='harga_items'),
    path('<int:project_id>/orphan-cleanup/',        views.orphan_cleanup_view,        name='orphan_cleanup'),
    path('<int:project_id>/audit-trail/',           views.audit_trail_view,           name='audit_trail'),

    # Renamed: detail_ahsp_gabungan -> rincian_ahsp (plus legacy alias)
    path('<int:project_id>/rincian-ahsp/',          views.rincian_ahsp_view,          name='rincian_ahsp'),
    path('<int:project_id>/detail-ahsp-gabungan/',  views.rincian_ahsp_view,          name='detail_ahsp_gabungan_legacy'),
    path('<int:project_id>/rekap-rab/',             views.rekap_rab_view,             name='rekap_rab'),
    path("<int:project_id>/rekap-kebutuhan/",       views.rekap_kebutuhan_view,       name="rekap_kebutuhan"),
    path('<int:project_id>/jadwal-pekerjaan/',      views.jadwal_pekerjaan_view,      name='jadwal_pekerjaan'),

    # --- NEW: Export System Test Page (Phase 4)
    path('<int:project_id>/export-test/',           views.export_test_view,           name='export_test'),

    # --- NEW: Rincian RAB (web)
    path('<int:project_id>/rincian-rab/',           views.rincian_rab_view,           name='rincian_rab'),  # NEW

    # ===== API: List Pekerjaan =====
    path('api/project/<int:project_id>/list-pekerjaan/save/',   views_api.api_save_list_pekerjaan,   name='api_save_list_pekerjaan'),
    path('api/project/<int:project_id>/list-pekerjaan/tree/',   views_api.api_get_list_pekerjaan_tree, name='api_get_list_pekerjaan_tree'),
    path('api/project/<int:project_id>/list-pekerjaan/upsert/', views_api.api_upsert_list_pekerjaan, name='api_upsert_list_pekerjaan'),

    # ===== API: Volume =====
    path('api/project/<int:project_id>/volume-pekerjaan/save/', views_api.api_save_volume_pekerjaan, name='api_save_volume_pekerjaan'),
    path('api/project/<int:project_id>/volume-pekerjaan/list/', views_api.api_list_volume_pekerjaan, name='api_list_volume_pekerjaan'),  # NEW
    # ===== API: Search AHSP (autocomplete untuk Select2) =====
    path('api/project/<int:project_id>/search-ahsp/', views_api.api_search_ahsp, name='api_search_ahsp'),

    # ===== API: Detail AHSP (per pekerjaan & gabungan) =====
    path('api/project/<int:project_id>/detail-ahsp/<int:pekerjaan_id>/',       views_api.api_get_detail_ahsp,              name='api_get_detail_ahsp'),
    path('api/project/<int:project_id>/detail-ahsp/<int:pekerjaan_id>/save/',  views_api.api_save_detail_ahsp_for_pekerjaan, name='api_save_detail_ahsp_for_pekerjaan'),
    path('api/project/<int:project_id>/detail-ahsp/<int:pekerjaan_id>/reset-to-ref/', views_api.api_reset_detail_ahsp_to_ref, name='api_reset_detail_ahsp_to_ref'),
    path('api/project/<int:project_id>/detail-ahsp/save/',                     views_api.api_save_detail_ahsp_gabungan,    name='api_save_detail_ahsp_gabungan'),

    # Bundle expansion endpoint (NEW - for rincian AHSP bundle detail visibility)
    path('api/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/bundle/<int:bundle_id>/expansion/', views_api.api_get_bundle_expansion, name='api_get_bundle_expansion'),

    # ===== API: Harga Items =====
    path('api/project/<int:project_id>/harga-items/save/', views_api.api_save_harga_items, name='api_save_harga_items'),
    path('api/project/<int:project_id>/harga-items/list/', views_api.api_list_harga_items, name='api_list_harga_items'),
    path('api/project/<int:project_id>/orphaned-items/', views_api.api_list_orphaned_harga_items, name='api_list_orphaned_items'),
    path('api/project/<int:project_id>/orphaned-items/cleanup/', views_api.api_cleanup_orphaned_harga_items, name='api_cleanup_orphaned_items'),
    path('api/project/<int:project_id>/change-status/', views_api.api_get_change_status, name='api_get_change_status'),
    path('api/project/<int:project_id>/audit-trail/', views_api.api_get_audit_trail, name='api_get_audit_trail'),
    
    # ===== API: Project Pricing (Profit/Margin) =====
    path('api/project/<int:project_id>/pricing/', views_api.api_project_pricing, name='api_project_pricing'),
    
    # Pricing per-pekerjaan
    path('api/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/pricing/', views_api.api_pekerjaan_pricing, name='api_pekerjaan_pricing'),

    # ===== API: Rekap =====
    path('api/project/<int:project_id>/rekap/', views_api.api_get_rekap_rab, name='api_get_rekap_rab'),
    path('api/project/<int:project_id>/rekap-kebutuhan/', views_api.api_get_rekap_kebutuhan, name='api_get_rekap_kebutuhan'),  # <-- Fase 5

    # PHASE 5: Data Validation
    path('api/project/<int:project_id>/rekap-kebutuhan/validate/', views_api.api_validate_rekap_kebutuhan, name='api_validate_rekap_kebutuhan'),

    # --- NEW: Rincian RAB (API)
    path('api/project/<int:project_id>/rincian-rab/',          views_api.api_get_rincian_rab,         name='api_get_rincian_rab'),          # NEW (GET)
    path('api/project/<int:project_id>/rincian-rab/export.csv', views_api.api_export_rincian_rab_csv, name='api_export_rincian_rab_csv'),   # NEW (EXPORT)


    # ===== API: Volume Formula State =====
    path('api/project/<int:project_id>/volume/formula/',       views_api.api_volume_formula_state, name='api_volume_formula_state'),
    path('api/project/<int:project_id>/volume-formula-state/', views_api.api_volume_formula_state, name='api_volume_formula_state_alias'),

    # ===== API: Deep Copy (FASE 3.1) =====
    path('api/project/<int:project_id>/deep-copy/', views_api.api_deep_copy_project, name='api_deep_copy_project'),

    # ===== API: Batch Copy (FASE 3.2) =====
    path('api/project/<int:project_id>/batch-copy/', views_api.api_batch_copy_project, name='api_batch_copy_project'),


    # Export endpoints
    # Export Rekap RAB
    path('api/project/<int:project_id>/export/rekap-rab/csv/', 
         views_api.export_rekap_rab_csv, 
         name='export_rekap_rab_csv'),
    
    path('api/project/<int:project_id>/export/rekap-rab/pdf/', 
         views_api.export_rekap_rab_pdf, 
         name='export_rekap_rab_pdf'),
    
    path('api/project/<int:project_id>/export/rekap-rab/word/', 
         views_api.export_rekap_rab_word, 
         name='export_rekap_rab_word'),

    path('api/project/<int:project_id>/export/rekap-rab/xlsx/',
         views_api.export_rekap_rab_xlsx,
         name='export_rekap_rab_xlsx'),

     # Export Rekap Kebutuhan
     path('api/project/<int:project_id>/export/rekap-kebutuhan/csv/',
          views_api.api_export_rekap_kebutuhan_csv,
          name='api_export_rekap_kebutuhan_csv'),  # ✅ CORRECT NAME

     path('api/project/<int:project_id>/export/rekap-kebutuhan/pdf/',
          views_api.export_rekap_kebutuhan_pdf,
          name='api_export_rekap_kebutuhan_pdf'),  # ✅ ADD api_ prefix

     path('api/project/<int:project_id>/export/rekap-kebutuhan/word/',
          views_api.export_rekap_kebutuhan_word,
          name='api_export_rekap_kebutuhan_word'),  # ✅ ADD api_ prefix

     # Export Volume Pekerjaan
     path('api/project/<int:project_id>/export/volume-pekerjaan/csv/',
          views_api.export_volume_pekerjaan_csv,
          name='export_volume_pekerjaan_csv'),

     path('api/project/<int:project_id>/export/volume-pekerjaan/pdf/',
          views_api.export_volume_pekerjaan_pdf,
          name='export_volume_pekerjaan_pdf'),

     path('api/project/<int:project_id>/export/volume-pekerjaan/word/',
          views_api.export_volume_pekerjaan_word,
          name='export_volume_pekerjaan_word'),

     # Export Harga Items
     path('api/project/<int:project_id>/export/harga-items/csv/',
          views_api.export_harga_items_csv,
          name='export_harga_items_csv'),

     path('api/project/<int:project_id>/export/harga-items/pdf/',
          views_api.export_harga_items_pdf,
          name='export_harga_items_pdf'),

     path('api/project/<int:project_id>/export/harga-items/word/',
          views_api.export_harga_items_word,
          name='export_harga_items_word'),

     # Export Rincian AHSP
     path('api/project/<int:project_id>/export/rincian-ahsp/csv/',
          views_api.export_rincian_ahsp_csv,
          name='export_rincian_ahsp_csv'),

     path('api/project/<int:project_id>/export/rincian-ahsp/pdf/',
          views_api.export_rincian_ahsp_pdf,
          name='export_rincian_ahsp_pdf'),

     path('api/project/<int:project_id>/export/rincian-ahsp/word/',
          views_api.export_rincian_ahsp_word,
          name='export_rincian_ahsp_word'),

     # Export Jadwal Pekerjaan
     path('api/project/<int:project_id>/export/jadwal-pekerjaan/csv/',
          views_api.export_jadwal_pekerjaan_csv,
          name='export_jadwal_pekerjaan_csv'),

     path('api/project/<int:project_id>/export/jadwal-pekerjaan/pdf/',
          views_api.export_jadwal_pekerjaan_pdf,
          name='export_jadwal_pekerjaan_pdf'),

     path('api/project/<int:project_id>/export/jadwal-pekerjaan/word/',
          views_api.export_jadwal_pekerjaan_word,
          name='export_jadwal_pekerjaan_word'),

     path('api/project/<int:project_id>/export/jadwal-pekerjaan/xlsx/',
          views_api.export_jadwal_pekerjaan_xlsx,
          name='export_jadwal_pekerjaan_xlsx'),

     # Export Jadwal Pekerjaan Professional (Laporan Tertulis)
     path('api/project/<int:project_id>/export/jadwal-pekerjaan/professional/',
          views_api.export_jadwal_pekerjaan_professional,
          name='export_jadwal_pekerjaan_professional'),


    
    # ===== TAHAPAN PELAKSANAAN API (NEW) =====
      
    # Tahapan CRUD
    path('api/project/<int:project_id>/tahapan/', 
         views_api_tahapan.api_list_create_tahapan, 
         name='api_list_create_tahapan'),
    
    path('api/project/<int:project_id>/tahapan/<int:tahapan_id>/', 
         views_api_tahapan.api_update_delete_tahapan, 
         name='api_update_delete_tahapan'),
    
    path('api/project/<int:project_id>/tahapan/reorder/', 
         views_api_tahapan.api_reorder_tahapan, 
         name='api_reorder_tahapan'),
    
    # Assignment Management
    path('api/project/<int:project_id>/tahapan/<int:tahapan_id>/assign/', 
         views_api_tahapan.api_assign_pekerjaan_to_tahapan, 
         name='api_assign_pekerjaan'),
    
    path('api/project/<int:project_id>/tahapan/<int:tahapan_id>/unassign/', 
         views_api_tahapan.api_unassign_pekerjaan_from_tahapan, 
         name='api_unassign_pekerjaan'),
    
    path('api/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/assignments/', 
         views_api_tahapan.api_get_pekerjaan_assignments, 
         name='api_get_pekerjaan_assignments'),
    
    # Validation & Status
    path('api/project/<int:project_id>/tahapan/validate/', 
         views_api_tahapan.api_validate_all_assignments, 
         name='api_validate_assignments'),
    
    path('api/project/<int:project_id>/tahapan/unassigned/', 
         views_api_tahapan.api_get_unassigned_pekerjaan, 
         name='api_unassigned_pekerjaan'),
    
    # Rekap Kebutuhan Enhanced (dapat replace yang lama atau jadi endpoint terpisah)
    path('api/project/<int:project_id>/rekap-kebutuhan/filters/',
         views_api_tahapan.api_get_rekap_kebutuhan_filters,
         name='api_get_rekap_kebutuhan_filters'),
    path('api/project/<int:project_id>/rekap-kebutuhan-enhanced/',
         views_api_tahapan.api_get_rekap_kebutuhan_enhanced,
         name='api_get_rekap_kebutuhan_enhanced'),
    path('api/project/<int:project_id>/rekap-kebutuhan-timeline/',
         views_api_tahapan.api_get_rekap_kebutuhan_timeline,
         name='api_get_rekap_kebutuhan_timeline'),

    # Time Scale Mode: Tahapan Auto-Generation (NEW - Phase 3)
    path('api/project/<int:project_id>/regenerate-tahapan/',
         views_api_tahapan.api_regenerate_tahapan,
         name='api_regenerate_tahapan'),

    # ===== API V2: Weekly Canonical Storage (NEW - Phase 4) =====
    # These endpoints use PekerjaanProgressWeekly as single source of truth

    # Assign progress in weekly units (canonical)
    path('api/v2/project/<int:project_id>/assign-weekly/',
         views_api_tahapan_v2.api_assign_pekerjaan_weekly,
         name='api_v2_assign_weekly'),

    # Get all weekly assignments
    path('api/v2/project/<int:project_id>/assignments/',
         views_api_tahapan_v2.api_get_project_assignments_v2,
         name='api_v2_get_project_assignments'),

    # Get weekly progress (canonical storage)
    path('api/v2/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/weekly-progress/',
         views_api_tahapan_v2.api_get_pekerjaan_weekly_progress,
         name='api_v2_get_weekly_progress'),

    # Get assignments in any view mode (daily/weekly/monthly)
    path('api/v2/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/assignments/',
         views_api_tahapan_v2.api_get_pekerjaan_assignments_v2,
         name='api_v2_get_assignments'),

    # Regenerate tahapan and sync from canonical storage
    path('api/v2/project/<int:project_id>/regenerate-tahapan/',
         views_api_tahapan_v2.api_regenerate_tahapan_v2,
         name='api_v2_regenerate_tahapan'),

    # Update stored week boundary preference
    path('api/v2/project/<int:project_id>/week-boundary/',
         views_api_tahapan_v2.api_update_week_boundaries,
         name='api_update_week_boundaries'),

    # Reset all progress
    path('api/v2/project/<int:project_id>/reset-progress/',
         views_api_tahapan_v2.api_reset_progress,
         name='api_v2_reset_progress'),

    # ===== API: KURVA S DATA (Phase 2F.0) =====
    # Provides harga-based data for Kurva S chart (not volume-based)
    path('api/v2/project/<int:project_id>/kurva-s-data/',
         views_api.api_kurva_s_data,
         name='api_kurva_s_data'),

    # ===== API: KURVA S HARGA DATA (Phase 1) =====
    # Provides weekly cost progression data for cost-based S-curve
    path('api/v2/project/<int:project_id>/kurva-s-harga/',
         views_api.api_kurva_s_harga_data,
         name='api_kurva_s_harga_data'),

    # ===== API: REKAP KEBUTUHAN WEEKLY (Phase 1) =====
    # Provides weekly resource requirements breakdown for procurement planning
    path('api/v2/project/<int:project_id>/rekap-kebutuhan-weekly/',
         views_api.api_rekap_kebutuhan_weekly,
         name='api_rekap_kebutuhan_weekly'),

    # ===== MONITORING: API Deprecation Tracking (Sprint 4.1) =====
    path('api/monitoring/deprecation-metrics/',
         views_monitoring.api_deprecation_metrics,
         name='api_deprecation_metrics'),

    path('monitoring/deprecation-dashboard/',
         views_monitoring.api_deprecation_dashboard,
         name='deprecation_dashboard'),

    path('api/monitoring/deprecation-metrics/reset/',
         views_monitoring.api_reset_deprecation_metrics,
         name='api_reset_deprecation_metrics'),

    # ===== MONITORING: Performance Tracking (Sprint 4.3) =====
    path('api/monitoring/performance-metrics/',
         views_monitoring.api_performance_metrics,
         name='api_performance_metrics'),

    path('monitoring/performance-dashboard/',
         views_monitoring.api_performance_dashboard,
         name='performance_dashboard'),

    path('api/monitoring/performance-metrics/reset/',
         views_monitoring.api_reset_performance_metrics,
         name='api_reset_performance_metrics'),

    path('api/monitoring/report-client-metric/',
         views_monitoring.api_report_client_metric,
         name='api_report_client_metric'),

    # ===== EXPORT SYSTEM: Batch Export API (Phase 3) =====
    # Initialize export session
    path('api/export/init',
         views_export.export_init,
         name='export_init'),

    # Upload pages in batches
    path('api/export/upload-pages',
         views_export.export_upload_pages,
         name='export_upload_pages'),

    # Finalize and generate PDF/Word
    path('api/export/finalize',
         views_export.export_finalize,
         name='export_finalize'),

    # Check export status
    path('api/export/status/<uuid:export_id>',
         views_export.export_status,
         name='export_status'),

    # Download completed export
    path('api/export/download/<uuid:export_id>',
         views_export.export_download,
         name='export_download'),

]
