# referensi/urls.py
from django.urls import path

from .views import (
    admin_portal,
    ahsp_database,
    commit_import,
    preview_import,
)
from .views.api import api_bulk_delete, api_delete_preview, api_search_ahsp
from .views.audit_dashboard import (
    audit_dashboard,
    audit_log_detail,
    audit_logs_list,
    audit_statistics,
    export_audit_logs,
    mark_log_resolved,
)
from .views.export_views import (
    ExportSingleJobView,
    ExportMultipleJobsView,
    ExportSearchResultsView,
    ExportAsyncView,
    export_task_status,
)

urlpatterns = [
    path("admin-portal/", admin_portal, name="admin_portal"),
    path("admin/database/", ahsp_database, name="ahsp_database"),
    path("import/preview/", preview_import, name="preview_import"),
    path("import/commit/", commit_import, name="commit_import"),

    # Audit Dashboard (Phase 2)
    path("audit/", audit_dashboard, name="audit_dashboard"),
    path("audit/logs/", audit_logs_list, name="audit_logs_list"),
    path("audit/logs/<int:log_id>/", audit_log_detail, name="audit_log_detail"),
    path("audit/logs/<int:log_id>/resolve/", mark_log_resolved, name="mark_log_resolved"),
    path("audit/statistics/", audit_statistics, name="audit_statistics"),
    path("audit/export/", export_audit_logs, name="export_audit_logs"),

    # API Endpoints
    path("api/search", api_search_ahsp, name="api_search_ahsp"),
    path("api/delete/preview", api_delete_preview, name="api_delete_preview"),
    path("api/delete/execute", api_bulk_delete, name="api_bulk_delete"),

    # Export Endpoints (Phase 6)
    path("export/single/<int:pk>/<str:format>/", ExportSingleJobView.as_view(), name="export_single_job"),
    path("export/multiple/<str:format>/", ExportMultipleJobsView.as_view(), name="export_multiple_jobs"),
    path("export/search/<str:format>/", ExportSearchResultsView.as_view(), name="export_search_results"),
    path("export/async/", ExportAsyncView.as_view(), name="export_async"),
    path("export/task-status/<str:task_id>/", export_task_status, name="export_task_status"),
]
