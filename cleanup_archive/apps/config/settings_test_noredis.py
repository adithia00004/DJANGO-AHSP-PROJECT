# settings_test_noredis.py
# TEMPORARY: Use this for testing without Redis
# WARNING: Only for local testing with single process!

from config.settings import *

# Override CACHES to use local memory instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ahsp-test-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

print("=" * 70)
print("⚠️  WARNING: Using LocMemCache (in-memory cache)")
print("   This is TEMPORARY and only works with single process!")
print("   For production, you MUST use Redis!")
print("=" * 70)
