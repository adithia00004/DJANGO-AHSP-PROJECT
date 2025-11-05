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
]
