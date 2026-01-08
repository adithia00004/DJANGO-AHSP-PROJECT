"""
Test settings - uses file-based SQLite database for reliable testing.
"""

from __future__ import annotations

from .base import *  # noqa: F401,F403

# Use file-based SQLite for testing (more stable than :memory:)
# This allows:
# - Proper transaction isolation
# - Background signals and post_save hooks
# - Database inspection for debugging
# - Support for all Django features (materialized views, etc.)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # noqa: F405
        'OPTIONS': {
            'timeout': 20,  # Increase timeout for concurrent access
        },
        'TEST': {
            # Use separate test database file to avoid Windows file locking issues
            'NAME': BASE_DIR / 'test_pytest_db.sqlite3',  # noqa: F405
        },
    }
}

# Disable migrations for faster test execution
# Tests will create tables directly from models
class DisableMigrations(dict):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Use production-grade password hashing even in tests (security suite depends on this)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# Disable debug mode
DEBUG = False

# Simple cache backend for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Cookie/session security flags
# NOTE: Set to False in tests because Django Test Client uses HTTP (not HTTPS)
# Production uses HTTPS and these should be True in production settings
SESSION_COOKIE_SECURE = False  # Must be False for Test Client to work
SESSION_COOKIE_HTTPONLY = True  # Safe to keep True
SESSION_COOKIE_AGE = 86400 * 5  # 5 days
CSRF_COOKIE_SECURE = False  # Must be False for Test Client to work

# Django AllAuth test configuration
# Disable email verification in tests
ACCOUNT_EMAIL_VERIFICATION = 'none'
# Allow direct login without requiring email confirmation
ACCOUNT_EMAIL_REQUIRED = False

# Use only ModelBackend for testing (AllAuth backend can interfere with force_login)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Disable TimeoutMiddleware in tests (it breaks force_login by using separate threads)
# The middleware creates a new thread for each request, which breaks Django Test Client
# authentication because request.user is stored in thread-local storage
MIDDLEWARE = [
    m for m in MIDDLEWARE  # noqa: F405
    if m != 'config.middleware.timeout.TimeoutMiddleware'
]

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Celery for tests (synchronous execution)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logging configuration for tests (less verbose)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
