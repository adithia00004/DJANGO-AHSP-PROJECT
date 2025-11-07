"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include, reverse
from django.shortcuts import redirect
from django.utils.http import urlencode
from django.conf import settings
from django.conf.urls.static import static

# Health check views
from detail_project.views_health import (
    health_check,
    health_check_simple,
    readiness_check,
    liveness_check
)


# Redirect root URL -> dashboard (jika login) atau login page
def home_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect("referensi:admin_portal")
        return redirect('dashboard:dashboard')  # pastikan dashboard/urls.py punya name="dashboard"
    return redirect('account_login')


def admin_login_redirect(request):
    """Redirect Django admin login to allauth login to avoid CSRF confusion."""

    next_url = request.GET.get("next") or request.POST.get("next") or reverse("admin:index")
    query = urlencode({"next": next_url}) if next_url else ""
    login_url = f"{reverse('account_login')}{'?' + query if query else ''}"
    return redirect(login_url)


urlpatterns = [
    # Health Check Endpoints (for monitoring & load balancers)
    path('health/', health_check, name='health_check'),
    path('health/simple/', health_check_simple, name='health_check_simple'),
    path('health/ready/', readiness_check, name='readiness_check'),
    path('health/live/', liveness_check, name='liveness_check'),

    # Admin
    path('admin/login/', admin_login_redirect, name='admin_login_redirect'),
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

# PHASE 0: Add Debug Toolbar URLs (development only)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include('debug_toolbar.urls'))] + urlpatterns
    except ImportError:
        pass
