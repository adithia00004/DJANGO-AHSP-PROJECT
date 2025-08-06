from django.urls import path
from .views import (
    dashboard_view,
    project_edit,
    project_delete,
    project_detail,
    project_duplicate,  # ✅ Tambahkan ini
    # project_restore,  # (opsional, aktifkan jika fitur restore siap)
)

urlpatterns = [
    # === Dashboard & List ===
    path('', dashboard_view, name='dashboard'),

    # === Project Detail & CRUD ===
    path('project/<int:pk>/', project_detail, name='project_detail'),
    path('project/<int:pk>/edit/', project_edit, name='project_edit'),
    path('project/<int:pk>/delete/', project_delete, name='project_delete'),
    path('project/<int:pk>/duplicate/', project_duplicate, name='project_duplicate'),  # ✅ Duplikat
]
