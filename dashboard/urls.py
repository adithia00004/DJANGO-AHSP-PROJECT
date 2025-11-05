from django.urls import path
from .views import (
    dashboard_view,
    project_edit,
    project_delete,
    project_detail,
    project_duplicate,
    project_upload_view,
)
from .views_export import (
    export_excel,
    export_csv,
    export_project_pdf,
)
from .views_bulk import (
    bulk_delete,
    bulk_archive,
    bulk_unarchive,
    bulk_export_excel,
)

app_name = "dashboard"

urlpatterns = [
    # Dashboard & list
    path("", dashboard_view, name="dashboard"),

    # Project detail & CRUD
    path("project/<int:pk>/", project_detail, name="project_detail"),
    path("project/<int:pk>/edit/", project_edit, name="project_edit"),
    path("project/<int:pk>/delete/", project_delete, name="project_delete"),
    path("project/<int:pk>/duplicate/", project_duplicate, name="project_duplicate"),

    # Mass upload via Excel
    path("upload/", project_upload_view, name="project_upload"),

    # FASE 2.4: Export features
    path("export/excel/", export_excel, name="export_excel"),
    path("export/csv/", export_csv, name="export_csv"),
    path("project/<int:pk>/export/pdf/", export_project_pdf, name="export_project_pdf"),

    # FASE 2.3: Bulk operations
    path("bulk/delete/", bulk_delete, name="bulk_delete"),
    path("bulk/archive/", bulk_archive, name="bulk_archive"),
    path("bulk/unarchive/", bulk_unarchive, name="bulk_unarchive"),
    path("bulk/export/excel/", bulk_export_excel, name="bulk_export_excel"),
]
