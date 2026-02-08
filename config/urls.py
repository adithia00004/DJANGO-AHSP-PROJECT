"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include, reverse
from django.shortcuts import redirect
from django.utils.http import urlencode
from django.conf import settings
from django.conf.urls.static import static

from referensi.permissions import has_referensi_portal_access

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
        if has_referensi_portal_access(request.user):
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

    # Subscription & Payment
    path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),

    # Landing Page (root URL - redirects to dashboard if logged in)
    path('', include(('pages.urls', 'pages'), namespace='pages')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# PHASE 0: Debug Toolbar URLs (disabled for cleaner UI)
# if settings.DEBUG:
#     try:
#         import debug_toolbar
#         urlpatterns = [path('__debug__/', include('debug_toolbar.urls'))] + urlpatterns
#     except ImportError:
#         pass

# Django Silk Profiling URLs (development only)
# Only add Silk URLs if it's actually enabled (not when using PgBouncer)
if settings.DEBUG and getattr(settings, 'SILK_ENABLED', False):
    try:
        import silk  # noqa: F401
        urlpatterns = [path('silk/', include('silk.urls', namespace='silk'))] + urlpatterns
    except ImportError:
        pass
