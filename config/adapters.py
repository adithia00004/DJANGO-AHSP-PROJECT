from __future__ import annotations

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from referensi.permissions import has_referensi_portal_access


class AccountAdapter(DefaultAccountAdapter):
    """Custom login redirect behavior based on explicit access permissions."""

    def get_login_redirect_url(self, request):  # type: ignore[override]
        """Respect explicit ?next=... but default staff to admin portal."""

        next_url = request.POST.get("next") or request.GET.get("next")
        allowed_hosts = {request.get_host()}
        allowed_hosts.update(host for host in settings.ALLOWED_HOSTS if host)
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts=allowed_hosts,
            require_https=request.is_secure(),
        ):
            return next_url

        user = getattr(request, "user", None)
        if user is not None and has_referensi_portal_access(user):
            return reverse("referensi:admin_portal")

        return super().get_login_redirect_url(request)
