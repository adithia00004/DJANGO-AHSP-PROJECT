# ================================
# detail_project/urls.py
# ================================
from django.urls import path
from . import views
from . import views_api

app_name = "detail_project"

urlpatterns = [
    # ===== Web views =====
    path('<int:project_id>/list-pekerjaan/',        views.list_pekerjaan_view,        name='list_pekerjaan'),
    path('<int:project_id>/volume-pekerjaan/',      views.volume_pekerjaan_view,      name='volume_pekerjaan'),
    path('<int:project_id>/detail-ahsp/',           views.detail_ahsp_view,           name='detail_ahsp'),            # Custom & Ref-Modified
    path('<int:project_id>/harga-items/',           views.harga_items_view,           name='harga_items'),
    path('<int:project_id>/detail-ahsp-gabungan/',  views.detail_ahsp_gabungan_view,  name='detail_ahsp_gabungan'),
    path('<int:project_id>/rekap-rab/',             views.rekap_rab_view,             name='rekap_rab'),

    # ===== API: List Pekerjaan (read + upsert) =====
    path('api/project/<int:project_id>/list-pekerjaan/save/',
         views_api.api_save_list_pekerjaan,
         name='api_save_list_pekerjaan'),
    path('api/project/<int:project_id>/list-pekerjaan/tree/',
         views_api.api_get_list_pekerjaan_tree,
         name='api_get_list_pekerjaan_tree'),
    path('api/project/<int:project_id>/list-pekerjaan/upsert/',
         views_api.api_upsert_list_pekerjaan,
         name='api_upsert_list_pekerjaan'),

    # ===== API: Volume =====
    path('api/project/<int:project_id>/volume-pekerjaan/save/',
         views_api.api_save_volume_pekerjaan,
         name='api_save_volume_pekerjaan'),

    # ===== API: Detail AHSP (per pekerjaan & gabungan) =====
    path('api/project/<int:project_id>/detail-ahsp/<int:pekerjaan_id>/save/',
         views_api.api_save_detail_ahsp_for_pekerjaan,
         name='api_save_detail_ahsp_for_pekerjaan'),
    path('api/project/<int:project_id>/detail-ahsp/save/',
         views_api.api_save_detail_ahsp_gabungan,
         name='api_save_detail_ahsp_gabungan'),

    # ===== API: Harga Items =====
    path('api/project/<int:project_id>/harga-items/save/',
         views_api.api_save_harga_items,
         name='api_save_harga_items'),
    path('api/project/<int:project_id>/harga-items/list/',
         views_api.api_list_harga_items,
         name='api_list_harga_items'),

    # ===== API: Rekap =====
    path('api/project/<int:project_id>/rekap/',
         views_api.api_get_rekap_rab,
         name='api_get_rekap_rab'),

     # detail_project/urls.py  (tambahkan di blok API, mis. tepat di bawah API Volume)

     # ===== API: Volume (nilai + formula) =====
     path('api/project/<int:project_id>/volume/formula/',
          views_api.api_volume_formula_state,
          name='api_volume_formula_state'),
]
