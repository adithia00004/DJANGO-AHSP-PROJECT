# referensi/urls.py
from django.urls import path

from .views import (
    admin_portal,
    ahsp_database,
    commit_import,
    preview_import,
)
from .views.api import api_search_ahsp

urlpatterns = [
    path("admin-portal/", admin_portal, name="admin_portal"),
    path("admin/database/", ahsp_database, name="ahsp_database"),
    path("import/preview/", preview_import, name="preview_import"),
    path("import/commit/", commit_import, name="commit_import"),
    # Endpoint untuk Select2 (List Pekerjaan, cari kode/nama AHSP)
    path("api/search", api_search_ahsp, name="api_search_ahsp"),
]
