"""
Development settings.
"""

from __future__ import annotations

import socket

from .base import *  # noqa: F401,F403

DEBUG = True

# Expand allowed hosts for local networks
def _local_ip() -> str:
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except OSError:
        return "127.0.0.1"


ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS + [
    _local_ip(),
    "192.168.*.*",
    "10.0.*.*",
    "*",
]))

# Add Django Debug Toolbar if available
try:
    import debug_toolbar  # type: ignore  # noqa: F401
except ImportError:
    debug_toolbar = None  # pragma: no cover
else:  # pragma: no cover - debug toolbar optional
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Use console email backend locally
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Faster storage for static lookups in development
WHITENOISE_USE_FINDERS = True

# Attach in-memory cache for quick iteration
CACHES["locmem"] = {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "referensi-dev-cache",
    "TIMEOUT": 300,
}
