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

# Django Debug Toolbar (disabled for cleaner UI)
# To re-enable, uncomment the lines below:
# try:
#     import debug_toolbar  # type: ignore  # noqa: F401
# except ImportError:
#     debug_toolbar = None  # pragma: no cover
# else:  # pragma: no cover - debug toolbar optional
#     INSTALLED_APPS += ["debug_toolbar"]
#     MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
#     INTERNAL_IPS = ["127.0.0.1", "localhost"]

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

# ---------------------------------------------------------------------------
# Django Silk - Request Profiling (only in development)
# ---------------------------------------------------------------------------
# Silk provides:
# - SQL query profiling (N+1 detection)
# - Request/response timing
# - Python code profiling
# - Memory usage analysis
#
# Access at: http://localhost:8000/silk/
# ---------------------------------------------------------------------------

try:
    import silk  # noqa: F401
    SILK_ENABLED = True
except ImportError:
    SILK_ENABLED = False

if SILK_ENABLED:
    INSTALLED_APPS += ["silk"]
    
    # Insert Silk middleware after security middleware but before most others
    # Position matters for accurate profiling
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
        "silk.middleware.SilkyMiddleware"
    )
    
    # Silk Configuration
    SILKY_PYTHON_PROFILER = False  # Disabled to prevent profiler conflicts
    SILKY_PYTHON_PROFILER_BINARY = True  # Binary profiling format
    SILKY_PYTHON_PROFILER_RESULT_PATH = BASE_DIR / "logs" / "silk_profiles"
    
    SILKY_META = True  # Track Silk's own overhead
    SILKY_INTERCEPT_PERCENT = 100  # Profile 100% of requests (adjust for production)
    
    # SQL query settings
    SILKY_MAX_RECORDED_REQUESTS = 10000  # Max requests to keep
    SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT = 10  # Check cleanup every 10%
    SILKY_MAX_REQUEST_BODY_SIZE = 1024  # Max request body to store (bytes)
    SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # Max response body to store (bytes)
    
    # Authentication for Silk UI (optional, uncomment for protection)
    # SILKY_AUTHENTICATION = True
    # SILKY_AUTHORISATION = True
    
    # Create profiles directory
    import os
    os.makedirs(SILKY_PYTHON_PROFILER_RESULT_PATH, exist_ok=True)

