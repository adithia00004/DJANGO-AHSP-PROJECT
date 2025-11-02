"""
Django settings for config project.
Django 5.2.4
"""

import os
import socket
from pathlib import Path
from dotenv import load_dotenv


# === Paths ===
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env after BASE_DIR is defined
load_dotenv(BASE_DIR / ".env")

# === Security / ENV (aman untuk dev, siap di-hardening saat deploy) ===
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key")  # ganti di .env saat production
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"


# Dapatkan IP lokal komputer Anda
def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except:
        return '192.168.1.100'  # Ganti dengan IP Anda jika error

# Update ALLOWED_HOSTS untuk testing lokal
if DEBUG:
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        'testserver',
        get_local_ip(),  # IP lokal komputer Anda
        '192.168.*.*',   # Atau spesifik: '192.168.1.*'
        '10.0.*.*',      # Jika pakai jaringan 10.x.x.x
        '*'              # HANYA untuk testing internal!
    ]

# ALLOWED_HOSTS = [
#     h.strip()
#     for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
#     if h.strip()
# ]


# === Apps ===
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
    "django.contrib.postgres",  # PHASE 0: Enable PostgreSQL features
    "django_extensions",

    # Third-party
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "widget_tweaks",

    # Local apps
    "accounts",
    "dashboard",
    "detail_project",
    "referensi",
]

# PHASE 0: Add Debug Toolbar for development only
if DEBUG:
    try:
        import debug_toolbar  # type: ignore  # noqa: F401
    except ImportError:
        debug_toolbar = None
    else:
        INSTALLED_APPS += ["debug_toolbar"]

AUTH_USER_MODEL = "accounts.CustomUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Allauth
    "allauth.account.middleware.AccountMiddleware",
]

# PHASE 0: Add Debug Toolbar middleware for development only
if DEBUG and "debug_toolbar" in INSTALLED_APPS:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

ROOT_URLCONF = "config.urls"

# === Templates ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # optional global templates dir
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.static",   # penting utk {% static %}
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.tz",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

"""Database
Default: PostgreSQL via env.
Optional: set DJANGO_DB_ENGINE=sqlite to use local file db for quick testing.
"""

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
            # PHASE 0: Enable connection pooling for better performance
            "CONN_MAX_AGE": 600,  # 10 minutes - reuse connections
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }

# === Password validators ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === I18N / TZ ===
LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

# === Static / Media ===
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]          # asset global (dev)
STATIC_ROOT = BASE_DIR / "staticfiles"            # collectstatic (deploy)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# === Defaults ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === Auth / Allauth ===
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

ACCOUNT_ADAPTER = "config.adapters.AccountAdapter"

# Redirects
LOGIN_REDIRECT_URL = "/dashboard/"
LOGIN_URL = "/accounts/login/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"

# Allauth sane defaults
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = "optional"           # bisa "none" jika ingin tanpa verifikasi
ACCOUNT_SESSION_REMEMBER = True

# === Session Configuration ===
# PHASE 3 DAY 4: Optimized session storage using cached_db backend
# Hybrid approach: cache for reads (fast), database for persistence (reliable)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'  # Use default cache (DatabaseCache)
SESSION_COOKIE_AGE = 1209600  # 2 weeks (default)
SESSION_SAVE_EVERY_REQUEST = False  # Only save when modified (performance)
SESSION_COOKIE_HTTPONLY = True  # Security: prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # Security: CSRF protection

# === Crispy Forms ===
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# === Numeric & Localization Guardrails (Batch 0) ===
# Gunakan lokal hanya untuk TEMPLATE (display), bukan untuk API JSON.
USE_L10N = True  # pastikan True

# DRF: kirim Decimal sebagai string (hindari float rounding).
try:
    REST_FRAMEWORK  # type: ignore
except NameError:
    REST_FRAMEWORK = {}
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'COERCE_DECIMAL_TO_STRING': True,
}

# Jangan paksa pemisah ribuan secara global; biarkan UI yang format saat display.
USE_THOUSAND_SEPARATOR = False
# === Security: optional CSRF trusted origins via env (for HTTPS/reverse proxy) ===
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Enable Whitenoise finders in dev so static works without collectstatic
WHITENOISE_USE_FINDERS = True

# ============================================================================
# PHASE 0: PERFORMANCE OPTIMIZATION SETUP
# ============================================================================

# === Cache Configuration ===
# Using database cache for now (no Redis dependency)
# Can upgrade to Redis later for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
        'TIMEOUT': 3600,  # 1 hour default
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        }
    }
}

# Optional: Use local memory cache for development (faster but not persistent)
if DEBUG:
    CACHES['locmem'] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes
    }

# === Referensi App Configuration ===
# Centralized configuration for referensi app
REFERENSI_CONFIG = {
    'page_sizes': {
        'jobs': 25,
        'details': 50,
    },
    'display_limits': {
        'jobs': 50,
        'items': 100,
    },
    'file_upload': {
        'max_size_mb': 10,
        'allowed_extensions': ['.xlsx', '.xls'],
    },
    'api': {
        'search_limit': 30,
    },
    'cache': {
        'timeout': 3600,  # 1 hour
    },
}
