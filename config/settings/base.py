"""
Base Django settings shared across all environments.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths / Environment
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

DEFAULT_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",")
    if host.strip()
]

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django.contrib.postgres",
    "django_extensions",

    # Third-party
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "widget_tweaks",
    "simple_history",

    # Local apps
    "accounts",
    "dashboard",
    "detail_project",
    "referensi",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "referensi.middleware.ImportRateLimitMiddleware",  # Rate limiting for imports
]

# ---------------------------------------------------------------------------
# URLs / WSGI
# ---------------------------------------------------------------------------

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.tz",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

if os.getenv("DJANGO_DB_ENGINE", "postgres").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "ahsp_sni_db"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "password"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "600")),
            "OPTIONS": {"connect_timeout": int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "10"))},
        }
    }

# ---------------------------------------------------------------------------
# Security / Authentication
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1
ACCOUNT_ADAPTER = "config.adapters.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "optional")
ACCOUNT_SESSION_REMEMBER = True

LOGIN_REDIRECT_URL = "/dashboard/"
LOGIN_URL = "/accounts/login/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = False

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

WHITENOISE_USE_FINDERS = DEBUG

# ---------------------------------------------------------------------------
# Sessions / Crispy forms
# ---------------------------------------------------------------------------

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("DJANGO_SESSION_SAMESITE", "Lax")

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------------------------------------------
# REST / API
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": True,
}

# ---------------------------------------------------------------------------
# CSRF / Security
# ---------------------------------------------------------------------------

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# Cache (Phase 4: Redis Cache Layer)
# ---------------------------------------------------------------------------

# Redis cache backend for high performance
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "redis")  # 'redis', 'db', or 'locmem'

if CACHE_BACKEND == "redis":
    try:
        import importlib

        importlib.import_module("django_redis")
    except ModuleNotFoundError:
        CACHE_BACKEND = "locmem"

if CACHE_BACKEND == "redis":
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "retry_on_timeout": True,
                },
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                # Note: PARSER_CLASS removed - HiredisParser no longer available in redis-py 5.x
                # Default PythonParser will be used automatically
            },
            "KEY_PREFIX": "ahsp",
            "TIMEOUT": int(os.getenv("DJANGO_CACHE_TIMEOUT", "300")),  # 5 minutes default
        }
    }
elif CACHE_BACKEND == "db":
    # Fallback to database cache
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": os.getenv("DJANGO_CACHE_LOCATION", "django_cache_table"),
            "TIMEOUT": int(os.getenv("DJANGO_CACHE_TIMEOUT", "3600")),
            "OPTIONS": {"MAX_ENTRIES": int(os.getenv("DJANGO_CACHE_MAX_ENTRIES", "10000"))},
        }
    }
else:
    # Safe default for tests or minimal environments
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ahsp-local",
            "TIMEOUT": int(os.getenv("DJANGO_CACHE_TIMEOUT", "300")),
        }
    }

PERFORMANCE_LOG_THRESHOLD = float(os.getenv("DJANGO_PERF_THRESHOLD", "1.0"))

# ---------------------------------------------------------------------------
# Rate Limiting (Phase 1 Security)
# ---------------------------------------------------------------------------

# Import rate limiting configuration
IMPORT_RATE_LIMIT = int(os.getenv("IMPORT_RATE_LIMIT", "10"))  # Max imports per window
IMPORT_RATE_WINDOW = int(os.getenv("IMPORT_RATE_WINDOW", "3600"))  # Time window in seconds (1 hour)
IMPORT_RATE_LIMIT_PATHS = [
    "/referensi/preview/",
    "/referensi/admin/import/",
]

# ---------------------------------------------------------------------------
# Full-Text Search Configuration (Phase 3)
# ---------------------------------------------------------------------------

# PostgreSQL full-text search settings
FTS_LANGUAGE = os.getenv("FTS_LANGUAGE", "simple")  # or 'indonesian' if available
FTS_MAX_RESULTS = int(os.getenv("FTS_MAX_RESULTS", "1000"))
FTS_MIN_QUERY_LENGTH = int(os.getenv("FTS_MIN_QUERY_LENGTH", "2"))
FTS_FUZZY_THRESHOLD = float(os.getenv("FTS_FUZZY_THRESHOLD", "0.3"))  # Trigram similarity threshold
FTS_AUTOCOMPLETE_LIMIT = int(os.getenv("FTS_AUTOCOMPLETE_LIMIT", "20"))

# Search performance settings
FTS_ENABLE_SUGGESTIONS = os.getenv("FTS_ENABLE_SUGGESTIONS", "True").lower() == "true"
FTS_CACHE_RESULTS = os.getenv("FTS_CACHE_RESULTS", "True").lower() == "true"
FTS_CACHE_TTL = int(os.getenv("FTS_CACHE_TTL", "300"))  # 5 minutes

# ---------------------------------------------------------------------------
# Celery Configuration (Phase 5: Async Tasks)
# ---------------------------------------------------------------------------

# Celery broker and result backend (using Redis)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")

# Celery task settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE  # Use Django timezone
CELERY_ENABLE_UTC = True

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_TASK_ACKS_LATE = True  # Acknowledge after task completion
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time per worker

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour
CELERY_RESULT_PERSISTENT = True

# Email settings for notifications (configure in .env)
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"  # Default: print to console
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@ahsp.example.com")

# Audit alert settings
AUDIT_ALERT_EMAIL_RECIPIENTS = [
    email.strip()
    for email in os.getenv("AUDIT_ALERT_EMAIL_RECIPIENTS", "admin@example.com").split(",")
    if email.strip()
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": True},
        "performance": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Front-end feature toggles
USE_VITE_DEV_SERVER = os.getenv("USE_VITE_DEV_SERVER", "True").lower() == "true"  # ✅ Enable Vite for dev

# Increase field limit for formsets with 200 rows
# Each row has ~20 fields → 200 rows × 20 = 4000 fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = 99999

REFERENSI_CONFIG = {
    "page_sizes": {
        "jobs": 25,
        "details": 50,
    },
    "display_limits": {
        "jobs": 200,  # Increased from 50 to support row limit dropdown
        "items": 200,  # Increased from 100 to support row limit dropdown
    },
    "file_upload": {
        "max_size_mb": 10,
        "allowed_extensions": [".xlsx", ".xls"],
    },
    "api": {
        "search_limit": 30,
    },
    "cache": {
        "timeout": 3600,
    },
}
