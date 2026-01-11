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

# CRITICAL: Disable Silk when using PgBouncer transaction pooling
# Silk middleware conflicts with PgBouncer's transaction mode causing query_wait_timeout errors
# Silk tries to save requests to DB before view execution, which PgBouncer rejects
using_pgbouncer = os.getenv("PGBOUNCER_PORT") is not None
if using_pgbouncer:
    SILK_ENABLED = False
    print("WARNING: Django Silk DISABLED - incompatible with PgBouncer transaction pooling")

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

# ---------------------------------------------------------------------------
# Auth debug logging (development only)
# ---------------------------------------------------------------------------

AUTH_DEBUG_ENABLED = os.getenv("AUTH_DEBUG", "True").lower() == "true"
if AUTH_DEBUG_ENABLED:
    MIDDLEWARE.append("config.middleware.auth_debug.AuthDebugMiddleware")

    auth_debug_log_path = BASE_DIR / "logs" / "auth_debug.log"
    auth_debug_log_path.parent.mkdir(parents=True, exist_ok=True)

    LOGGING.setdefault("handlers", {})
    LOGGING.setdefault("loggers", {})

    LOGGING["handlers"]["auth_debug_file"] = {
        "class": "logging.FileHandler",
        "filename": str(auth_debug_log_path),
        "formatter": "standard",
    }
    LOGGING["loggers"]["auth_debug"] = {
        "handlers": ["auth_debug_file", "console"],
        "level": "DEBUG",
        "propagate": False,
    }

# ---------------------------------------------------------------------------
# Allauth rate limit overrides (development only)
# ---------------------------------------------------------------------------

if os.getenv("ACCOUNT_RATE_LIMITS_DISABLED", "False").lower() == "true":
    ACCOUNT_RATE_LIMITS = False

django_error_log_path = BASE_DIR / "logs" / "django_errors.log"
django_error_log_path.parent.mkdir(parents=True, exist_ok=True)

LOGGING.setdefault("handlers", {})
LOGGING.setdefault("loggers", {})

LOGGING["handlers"]["django_error_file"] = {
    "class": "logging.FileHandler",
    "filename": str(django_error_log_path),
    "formatter": "standard",
}
LOGGING["loggers"]["django.request"] = {
    "handlers": ["django_error_file", "console"],
    "level": "ERROR",
    "propagate": False,
}
LOGGING["loggers"]["django.security"] = {
    "handlers": ["django_error_file", "console"],
    "level": "ERROR",
    "propagate": False,
}
