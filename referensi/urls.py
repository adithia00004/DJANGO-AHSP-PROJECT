# referensi/urls.py
from django.urls import path

from .views import (
    admin_portal,
    ahsp_database,
    commit_import,
    preview_import,
)
from .views.api import api_bulk_delete, api_delete_preview, api_search_ahsp

urlpatterns = [
    path("admin-portal/", admin_portal, name="admin_portal"),
    path("admin/database/", ahsp_database, name="ahsp_database"),
    path("import/preview/", preview_import, name="preview_import"),
    path("import/commit/", commit_import, name="commit_import"),
    # API Endpoints
    path("api/search", api_search_ahsp, name="api_search_ahsp"),
    path("api/delete/preview", api_delete_preview, name="api_delete_preview"),
    path("api/delete/execute", api_bulk_delete, name="api_bulk_delete"),
]
