"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static


# Redirect root URL -> dashboard (jika login) atau login page
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')  # pastikan dashboard/urls.py punya name="dashboard"
    return redirect('account_login')


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication (django-allauth)
    path('accounts/', include('allauth.urls')),

    # Dashboard (CRUD Project + upload Excel + link ke detail_project)
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),
    #path("dashboard/", include(("detail_project.urls", "detail_project"), namespace="detail_project")),

    # Detail Project (List Pekerjaan, Volume, Harga Items, Rekap AHSP, Detail AHSP)
    path('detail_project/', include(('detail_project.urls','detail_project'), namespace='detail_project')),

    # Referensi AHSP (aktifkan kalau UI referensi sudah siap)
    path('referensi/', include(('referensi.urls', 'referensi'), namespace='referensi')),

    # Root redirect
    path('', home_redirect, name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
