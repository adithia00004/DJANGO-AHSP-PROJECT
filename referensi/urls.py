# referensi/urls.py
from django.shortcuts import redirect
from django.urls import path

from .views import (
    admin_portal,
    ahsp_database,
    ahsp_database_api,
)
from .views.preview import debug_clear_data
from .views.api import api_bulk_delete, api_delete_preview, api_list_sources, api_search_ahsp
from .views.api.crud import (
    api_list_jobs,
    api_update_job,
    api_list_items,
    api_update_item,
    api_get_stats,
)
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
# New 3-Tier Import System
from .views.import_views import (
    import_options,
    import_options,
    import_pdf_convert,
    import_pdf_download_part,
    pdf_convert_download,
    excel_validate_upload,
    excel_validate_report,
    excel_validate_download,
    excel_clean_upload,
    staging_view,
    staging_clear,
    staging_commit,
    export_valid_excel,
    export_anomaly_excel,
    export_from_frontend,
)

urlpatterns = [
    path("admin-portal/", admin_portal, name="admin_portal"),
    path("admin/database/", lambda request: redirect('referensi:ahsp_database_api'), name="ahsp_database_legacy"),  # Redirect to new
    path("admin/database-v2/", ahsp_database_api, name="ahsp_database_api"),

    path("debug/clear-data/", debug_clear_data, name="debug_clear_data"),

    # 3-Tier Import System
    path("import/", import_options, name="import_options"),
    path("import/pdf-convert/", import_pdf_convert, name="import_pdf_convert"),
    path("import/pdf-convert/download/<str:file_id>/", pdf_convert_download, name="import_pdf_download"),
    path("import/pdf-convert/download-part/<str:file_id>/<int:part_number>/", import_pdf_download_part, name="import_pdf_download_part"),
    path("import/validate/", excel_validate_upload, name="import_validate"),
    path("import/validate/report/<str:file_id>/", excel_validate_report, name="import_validate_report"),
    path("import/validate/download/<str:file_id>/", excel_validate_download, name="import_validate_download"),
    path("import/export/valid/", export_valid_excel, name="export_valid_excel"),
    path("import/export/anomaly/", export_anomaly_excel, name="export_anomaly_excel"),
    path("import/export/from-frontend/", export_from_frontend, name="export_from_frontend"),
    path("import/excel/", excel_clean_upload, name="import_excel"),
    path("import/staging/", staging_view, name="import_staging"),
    path("import/staging/clear/", staging_clear, name="import_staging_clear"),
    path("import/staging/commit/", staging_commit, name="import_staging_commit"),


    # Audit Dashboard (Phase 2)
    path("audit/", audit_dashboard, name="audit_dashboard"),
    path("audit/logs/", audit_logs_list, name="audit_logs_list"),
    path("audit/logs/<int:log_id>/", audit_log_detail, name="audit_log_detail"),
    path("audit/logs/<int:log_id>/resolve/", mark_log_resolved, name="mark_log_resolved"),
    path("audit/statistics/", audit_statistics, name="audit_statistics"),
    path("audit/export/", export_audit_logs, name="export_audit_logs"),

    # Legacy API Endpoints
    path("api/search", api_search_ahsp, name="api_search_ahsp"),
    path("api/sources", api_list_sources, name="api_list_sources"),
    path("api/delete/preview", api_delete_preview, name="api_delete_preview"),
    path("api/delete/execute", api_bulk_delete, name="api_bulk_delete"),

    # CRUD API Endpoints (Performance optimized)
    path("api/jobs/", api_list_jobs, name="api_list_jobs"),
    path("api/jobs/<int:pk>/", api_update_job, name="api_update_job"),
    path("api/items/", api_list_items, name="api_list_items"),
    path("api/items/<int:pk>/", api_update_item, name="api_update_item"),
    path("api/stats/", api_get_stats, name="api_get_stats"),

    # Export Endpoints (Phase 6)
    path("export/single/<int:pk>/<str:format>/", ExportSingleJobView.as_view(), name="export_single_job"),
    path("export/multiple/<str:format>/", ExportMultipleJobsView.as_view(), name="export_multiple_jobs"),
    path("export/search/<str:format>/", ExportSearchResultsView.as_view(), name="export_search_results"),
    path("export/async/", ExportAsyncView.as_view(), name="export_async"),
    path("export/task-status/<str:task_id>/", export_task_status, name="export_task_status"),
]

