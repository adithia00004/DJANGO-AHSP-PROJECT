#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PgBouncer Verification Script

This script verifies that PgBouncer is properly configured and Django can connect through it.

Usage:
    python verify_pgbouncer.py
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

from django.db import connection
from django.core.management import call_command
import psycopg


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def check_env_variables():
    """Check if required environment variables are set"""
    print_header("1. Checking Environment Variables")

    pgbouncer_port = os.getenv("PGBOUNCER_PORT")
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD")

    print(f"POSTGRES_HOST: {postgres_host}")
    print(f"POSTGRES_USER: {postgres_user}")
    print(f"POSTGRES_PASSWORD: {'***' if postgres_password else 'NOT SET'}")
    print(f"PGBOUNCER_PORT: {pgbouncer_port or 'NOT SET (using direct PostgreSQL)'}")

    if not postgres_password:
        print("\n❌ ERROR: POSTGRES_PASSWORD not set in environment")
        return False

    if not pgbouncer_port:
        print("\n⚠️  WARNING: PGBOUNCER_PORT not set - Django will connect directly to PostgreSQL")
        print("   To use PgBouncer, add PGBOUNCER_PORT=6432 to your .env file")
        return False

    print("\n✅ Environment variables configured correctly")
    return True


def check_django_settings():
    """Check Django database settings"""
    print_header("2. Checking Django Database Settings")

    from django.conf import settings

    db_config = settings.DATABASES['default']

    print(f"Engine: {db_config['ENGINE']}")
    print(f"Host: {db_config['HOST']}")
    print(f"Port: {db_config['PORT']}")
    print(f"Database: {db_config['NAME']}")
    print(f"User: {db_config['USER']}")
    print(f"CONN_MAX_AGE: {db_config.get('CONN_MAX_AGE', 'Not set')}")
    print(f"CONN_HEALTH_CHECKS: {db_config.get('CONN_HEALTH_CHECKS', 'Not set')}")
    print(f"DISABLE_SERVER_SIDE_CURSORS: {db_config.get('DISABLE_SERVER_SIDE_CURSORS', 'Not set')}")

    using_pgbouncer = db_config['PORT'] == '6432'

    if using_pgbouncer:
        print("\n✅ Django configured to use PgBouncer (port 6432)")

        # Verify PgBouncer-specific settings
        errors = []

        if db_config.get('CONN_MAX_AGE', 0) != 0:
            errors.append("CONN_MAX_AGE should be 0 for PgBouncer transaction pooling")

        if db_config.get('CONN_HEALTH_CHECKS', False) != False:
            errors.append("CONN_HEALTH_CHECKS should be False for PgBouncer")

        if db_config.get('DISABLE_SERVER_SIDE_CURSORS', False) != True:
            errors.append("DISABLE_SERVER_SIDE_CURSORS should be True for PgBouncer")

        if errors:
            print("\n❌ Configuration errors detected:")
            for error in errors:
                print(f"   - {error}")
            return False

        print("✅ PgBouncer-specific settings correct")
        return True
    else:
        print("\n⚠️  Django configured for direct PostgreSQL connection (not using PgBouncer)")
        return False


def test_django_connection():
    """Test Django database connection"""
    print_header("3. Testing Django Database Connection")

    try:
        # Force new connection
        connection.close()

        # Execute simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"PostgreSQL version: {version}")

        # Check connection details
        conn_params = connection.get_connection_params()
        print(f"\nConnected to: {conn_params.get('host')}:{conn_params.get('port')}")
        print(f"Database: {conn_params.get('dbname')}")

        print("\n✅ Django can connect to database successfully")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: Failed to connect to database")
        print(f"   {type(e).__name__}: {e}")
        return False


def test_pgbouncer_stats():
    """Test PgBouncer statistics (if connected via PgBouncer)"""
    print_header("4. Testing PgBouncer Statistics")

    from django.conf import settings
    db_config = settings.DATABASES['default']

    if db_config['PORT'] != '6432':
        print("⚠️  Skipped - not connected via PgBouncer")
        return True

    try:
        # Connect to PgBouncer admin console
        conn = psycopg.connect(
            host=db_config['HOST'],
            port=db_config['PORT'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            dbname='pgbouncer'  # Special database for PgBouncer stats
        )

        with conn.cursor() as cursor:
            # Show pools
            cursor.execute("SHOW POOLS;")
            pools = cursor.fetchall()

            print("PgBouncer Pool Status:")
            print("-" * 60)
            print(f"{'Database':<15} {'User':<15} {'Active':<10} {'Idle':<10}")
            print("-" * 60)

            for pool in pools:
                # pool format: (database, user, cl_active, cl_waiting, sv_active, sv_idle, ...)
                database, user, cl_active, cl_waiting, sv_active, sv_idle = pool[:6]
                print(f"{database:<15} {user:<15} {sv_active:<10} {sv_idle:<10}")

            print("\n✅ PgBouncer is running and accessible")

            # Show configuration
            cursor.execute("SHOW CONFIG;")
            configs = cursor.fetchall()

            print("\nPgBouncer Configuration:")
            print("-" * 60)
            important_configs = ['pool_mode', 'max_client_conn', 'default_pool_size']
            for config in configs:
                key, value = config[0], config[1]
                if key in important_configs:
                    print(f"{key}: {value}")

            print()

        conn.close()
        return True

    except Exception as e:
        print(f"\n⚠️  Could not connect to PgBouncer admin console")
        print(f"   {type(e).__name__}: {e}")
        print("\n   This might be normal - PgBouncer admin console may not be enabled")
        print("   Your application should still work if Django connection test passed")
        return True


def test_migrations():
    """Test that Django migrations work"""
    print_header("5. Testing Django Migrations")

    try:
        # Check migration status (dry run)
        print("Checking migration status...")
        call_command('showmigrations', '--list', verbosity=0)

        print("\n✅ Migrations are accessible")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: Failed to check migrations")
        print(f"   {type(e).__name__}: {e}")
        return False


def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("  PgBouncer Verification Script")
    print("=" * 60)

    results = []

    # Run all checks
    results.append(("Environment Variables", check_env_variables()))
    results.append(("Django Settings", check_django_settings()))
    results.append(("Django Connection", test_django_connection()))
    results.append(("PgBouncer Stats", test_pgbouncer_stats()))
    results.append(("Django Migrations", test_migrations()))

    # Print summary
    print_header("Verification Summary")

    all_passed = True
    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if all_passed:
        print("\n🎉 All checks passed! PgBouncer is configured correctly.")
        print("\nYou can now:")
        print("1. Restart Django server: python manage.py runserver")
        print("2. Run load test to verify improved performance")
        print()
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("1. Make sure PGBOUNCER_PORT=6432 is set in .env file")
        print("2. Verify PgBouncer container is running: docker ps")
        print("3. Check PgBouncer logs: docker logs ahsp_pgbouncer")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
