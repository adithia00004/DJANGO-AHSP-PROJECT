# referensi/urls.py
from django.urls import path
from . import views_api

urlpatterns = [
    # Endpoint untuk Select2 (List Pekerjaan, cari kode/nama AHSP)
    path('api/search', views_api.api_search_ahsp, name='api_search_ahsp'),
]
