#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis Session Store Verification Script

This script verifies that Redis is properly configured for Django sessions.

Usage:
    python verify_redis.py
"""

import os
import sys
import io

# Fix Windows encoding issues with UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.core.cache import cache
from django.contrib.sessions.backends.cache import SessionStore
from django.conf import settings


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_check(name, status, message=""):
    """Print a check result"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if message:
        print(f"   {message}")


def main():
    print_header("Redis Session Store Verification")

    all_passed = True

    # Check 1: Verify CACHE_BACKEND environment variable
    print_check(
        "1. CACHE_BACKEND Environment Variable",
        os.getenv("CACHE_BACKEND") == "redis",
        f"CACHE_BACKEND = {os.getenv('CACHE_BACKEND')}"
    )
    if os.getenv("CACHE_BACKEND") != "redis":
        all_passed = False
        print("   💡 Set CACHE_BACKEND=redis in .env file")

    # Check 2: Verify SESSION_ENGINE setting
    expected_session_engine = "django.contrib.sessions.backends.cache"
    actual_session_engine = settings.SESSION_ENGINE
    check_passed = actual_session_engine == expected_session_engine
    print_check(
        "2. Django Session Engine Configuration",
        check_passed,
        f"SESSION_ENGINE = {actual_session_engine}"
    )
    if not check_passed:
        all_passed = False
        print(f"   💡 Expected: {expected_session_engine}")

    # Check 3: Verify CACHES configuration
    try:
        cache_backend = settings.CACHES['default']['BACKEND']
        check_passed = 'redis' in cache_backend.lower()
        print_check(
            "3. Cache Backend (Redis)",
            check_passed,
            f"BACKEND = {cache_backend}"
        )
        if not check_passed:
            all_passed = False
            print("   💡 Cache should use django_redis.cache.RedisCache")
    except KeyError as e:
        print_check("3. Cache Backend (Redis)", False, f"Error: {e}")
        all_passed = False

    # Check 4: Test Redis connection
    try:
        cache.set('verify_redis_test', 'Hello Redis!', 30)
        result = cache.get('verify_redis_test')
        check_passed = result == 'Hello Redis!'
        print_check(
            "4. Redis Connection Test",
            check_passed,
            f"Test value: {result}"
        )
        if check_passed:
            cache.delete('verify_redis_test')
        else:
            all_passed = False
    except Exception as e:
        print_check("4. Redis Connection Test", False, f"Error: {e}")
        all_passed = False
        print("   💡 Make sure Redis is running: docker-compose -f docker-compose-redis.yml up -d")

    # Check 5: Test session creation
    try:
        session = SessionStore()
        session['test_user_id'] = 12345
        session['test_timestamp'] = 'test_verification'
        session.save()

        session_key = session.session_key
        print_check(
            "5. Session Creation Test",
            True,
            f"Session key: {session_key}"
        )

        # Verify session data stored in Redis
        stored_data = cache.get(f'django.contrib.sessions.cache{session_key}')
        check_passed = stored_data is not None
        print_check(
            "6. Session Data in Redis",
            check_passed,
            f"Session stored: {check_passed}"
        )
        if not check_passed:
            all_passed = False

        # Clean up test session
        session.delete()

    except Exception as e:
        print_check("5. Session Creation Test", False, f"Error: {e}")
        all_passed = False

    # Check 6: Verify Redis memory and stats (optional)
    try:
        # Try to get Redis info (requires redis-py)
        import redis
        redis_url = settings.CACHES['default']['LOCATION']
        r = redis.from_url(redis_url)
        info = r.info('memory')

        used_memory_human = info.get('used_memory_human', 'N/A')
        maxmemory_human = info.get('maxmemory_human', 'N/A')

        print_check(
            "7. Redis Memory Usage",
            True,
            f"Used: {used_memory_human}, Max: {maxmemory_human}"
        )
    except ImportError:
        print_check(
            "7. Redis Memory Usage",
            True,
            "redis-py not installed (optional check skipped)"
        )
    except Exception as e:
        print_check(
            "7. Redis Memory Usage",
            True,
            f"Could not fetch stats: {e}"
        )

    # Summary
    print_header("Verification Summary")

    if all_passed:
        print("✅ All critical checks PASSED!")
        print("\n🎉 Redis session store is properly configured!")
        print("\nNext steps:")
        print("1. Restart Django server")
        print("2. Run load test v16:")
        print("   locust -f load_testing/locustfile.py --headless -u 50 -r 2 -t 300s \\")
        print("       --host=http://localhost:8000 \\")
        print("       --csv=hasil_test_v16_50u_redis_sessions \\")
        print("       --html=hasil_test_v16_50u_redis_sessions.html")
        print("\n📊 Expected improvements:")
        print("   - Login success rate: 50% → >95%")
        print("   - Login response time: 154s → <1s")
        print("   - Overall success rate: 97% → >99%")
    else:
        print("❌ Some checks FAILED!")
        print("\n🔧 Please fix the issues above before running load tests.")
        print("\nCommon fixes:")
        print("1. Start Redis: docker-compose -f docker-compose-redis.yml up -d")
        print("2. Set CACHE_BACKEND=redis in .env")
        print("3. Install django-redis: pip install django-redis==5.4.0")
        print("4. Restart Django server")

    print("\n" + "="*70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
