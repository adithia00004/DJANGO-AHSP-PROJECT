"""
Production settings.
"""

from __future__ import annotations

import os

from .base import *  # noqa: F401,F403

DEBUG = False

if os.getenv("DJANGO_ENV", "").lower() not in {"prod", "production"}:
    raise RuntimeError("Production settings loaded without DJANGO_ENV=production/prod.")

_secret_key = (SECRET_KEY or "").strip()
_secret_key_lower = _secret_key.lower()
_insecure_secret_fragments = (
    "insecure-dev-key",
    "change-this",
    "replace-me",
    "your-secret-key",
    "staging-secret-key-change-me",
)

if not _secret_key:
    raise RuntimeError("DJANGO_SECRET_KEY must be set for production.")

if any(fragment in _secret_key_lower for fragment in _insecure_secret_fragments):
    raise RuntimeError("DJANGO_SECRET_KEY uses an insecure/default placeholder value in production.")

if len(_secret_key) < 32:
    raise RuntimeError("DJANGO_SECRET_KEY is too short for production (minimum 32 characters).")

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

_invalid_prod_hosts = {
    "yourdomain.com",
    "www.yourdomain.com",
    "api.yourdomain.com",
    "example.com",
    "localhost",
    "127.0.0.1",
    "::1",
    "testserver",
}
_found_invalid_hosts = [host for host in ALLOWED_HOSTS if host.lower() in _invalid_prod_hosts]
if _found_invalid_hosts:
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS still contains placeholder/dev hosts: "
        + ", ".join(_found_invalid_hosts)
    )

if not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError("DJANGO_CSRF_TRUSTED_ORIGINS must be set for production.")

_invalid_csrf = [
    origin
    for origin in CSRF_TRUSTED_ORIGINS
    if not origin.lower().startswith("https://")
    or "yourdomain.com" in origin.lower()
    or "example.com" in origin.lower()
]
if _invalid_csrf:
    raise RuntimeError(
        "DJANGO_CSRF_TRUSTED_ORIGINS contains invalid/placeholder values: "
        + ", ".join(_invalid_csrf)
    )

SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"  # Always mandatory in production
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
# Must disable APP_DIRS when using custom loaders
TEMPLATES[0]["APP_DIRS"] = False
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

# ---------------------------------------------------------------------------
# Sentry Error Tracking
# ---------------------------------------------------------------------------

SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
            ),
            LoggingIntegration(
                level=None,  # Capture all as breadcrumbs
                event_level="ERROR",  # Only send ERROR+ as events
            ),
        ],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_RATE", "0.1")),
        send_default_pii=False,  # Privacy: don't send PII
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
    )
