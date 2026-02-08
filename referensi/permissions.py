"""
Centralized permission helpers for Referensi access control.
"""

from __future__ import annotations


REFERENSI_PORTAL_PERMISSIONS = [
    "referensi.view_ahspreferensi",
    "referensi.change_ahspreferensi",
]

REFERENSI_IMPORT_PERMISSIONS = REFERENSI_PORTAL_PERMISSIONS + [
    "referensi.import_ahsp_data",
]


def has_referensi_portal_access(user) -> bool:
    """
    True when user can access Referensi admin portal.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perms(REFERENSI_PORTAL_PERMISSIONS)


def has_referensi_import_access(user) -> bool:
    """
    True when user can run Referensi import actions.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perms(REFERENSI_IMPORT_PERMISSIONS)
