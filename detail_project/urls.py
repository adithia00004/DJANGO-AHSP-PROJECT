# detail_project/urls.py
from django.urls import path
from . import views
from . import views_api
from . import views_export  # ← Clean import at root level!

app_name = "detail_project"

urlpatterns = [
    # ===== Web views =====
    path('<int:project_id>/list-pekerjaan/',        views.list_pekerjaan_view,        name='list_pekerjaan'),
    path('<int:project_id>/volume-pekerjaan/',      views.volume_pekerjaan_view,      name='volume_pekerjaan'),

    path('<int:project_id>/template-ahsp/',         views.template_ahsp_view,         name='template_ahsp'),
    path('<int:project_id>/detail-ahsp/',           views.template_ahsp_view,         name='detail_ahsp_legacy'),
    path('<int:project_id>/harga-items/',           views.harga_items_view,           name='harga_items'),

    # Renamed: detail_ahsp_gabungan -> rincian_ahsp (plus legacy alias)
    path('<int:project_id>/rincian-ahsp/',          views.rincian_ahsp_view,          name='rincian_ahsp'),
    path('<int:project_id>/detail-ahsp-gabungan/',  views.rincian_ahsp_view,          name='detail_ahsp_gabungan_legacy'),
    path('<int:project_id>/rekap-rab/',             views.rekap_rab_view,             name='rekap_rab'),
    path("<int:project_id>/rekap-kebutuhan/",       views.rekap_kebutuhan_view,       name="rekap_kebutuhan"),
    
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

    # ===== API: Harga Items =====
    path('api/project/<int:project_id>/harga-items/save/', views_api.api_save_harga_items, name='api_save_harga_items'),
    path('api/project/<int:project_id>/harga-items/list/', views_api.api_list_harga_items, name='api_list_harga_items'),
    
    # ===== API: Project Pricing (Profit/Margin) =====
    path('api/project/<int:project_id>/pricing/', views_api.api_project_pricing, name='api_project_pricing'),
    
    # Pricing per-pekerjaan
    path('api/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/pricing/', views_api.api_pekerjaan_pricing, name='api_pekerjaan_pricing'),

    # ===== API: Rekap =====
    path('api/project/<int:project_id>/rekap/', views_api.api_get_rekap_rab, name='api_get_rekap_rab'),
    path('api/project/<int:project_id>/rekap-kebutuhan/', views_api.api_get_rekap_kebutuhan, name='api_get_rekap_kebutuhan'),  # <-- Fase 5
    
    # --- NEW: Rincian RAB (API)
    path('api/project/<int:project_id>/rincian-rab/',          views_api.api_get_rincian_rab,         name='api_get_rincian_rab'),          # NEW (GET)
    path('api/project/<int:project_id>/rincian-rab/export.csv', views_api.api_export_rincian_rab_csv, name='api_export_rincian_rab_csv'),   # NEW (EXPORT)


    # ===== API: Volume Formula State =====
    path('api/project/<int:project_id>/volume/formula/',       views_api.api_volume_formula_state, name='api_volume_formula_state'),
    path('api/project/<int:project_id>/volume-formula-state/', views_api.api_volume_formula_state, name='api_volume_formula_state_alias'),


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



]

