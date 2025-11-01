from __future__ import annotations

from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    """Custom login redirect behavior for admin vs regular users."""

    def get_login_redirect_url(self, request):  # type: ignore[override]
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and (
            user.is_superuser or getattr(user, "is_staff", False)
        ):
            return reverse("referensi:admin_portal")
        return super().get_login_redirect_url(request)
