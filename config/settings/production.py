"""
Production settings.
"""

from __future__ import annotations

import os

from .base import *  # noqa: F401,F403

DEBUG = False

# ---------------------------------------------------------------------------
# Hosts / Security
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set for production.")

SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"

# ---------------------------------------------------------------------------
# Middleware / Static optimisation
# ---------------------------------------------------------------------------

MIDDLEWARE = MIDDLEWARE[:2] + ["referensi.middleware.performance.PerformanceLoggingMiddleware"] + MIDDLEWARE[2:]

WHITENOISE_USE_FINDERS = False
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Cached template loader for faster rendering
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": True},
        "django.request": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "performance": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Email / Misc
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "no-reply@example.com")

# Ensure cached_db sessions stored in primary cache (e.g., Redis) when configured
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_SAMESITE = "Lax"

# Observability defaults
PERFORMANCE_LOG_THRESHOLD = float(os.getenv("DJANGO_PERF_THRESHOLD", "0.8"))
