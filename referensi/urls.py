# referensi/urls.py
from django.urls import path
from . import views, views_api

urlpatterns = [
    path('import/preview/', views.preview_import, name='preview_import'),
    path('import/commit/', views.commit_import, name='commit_import'),
    # Endpoint untuk Select2 (List Pekerjaan, cari kode/nama AHSP)
    path('api/search', views_api.api_search_ahsp, name='api_search_ahsp'),
]
