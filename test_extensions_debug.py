#!/usr/bin/env python
"""
Debug script to check why PostgreSQL extensions aren't being created in test database.
Run this to diagnose the issue.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.db import connection
from django.test.utils import setup_test_environment, teardown_test_environment
from django.db import connections
from django.conf import settings

print("=" * 70)
print("PostgreSQL Extensions Debug Test")
print("=" * 70)

# Check main database
print("\n1. MAIN DATABASE:")
print(f"   Database: {connection.settings_dict['NAME']}")
print(f"   User: {connection.settings_dict['USER']}")
print(f"   Vendor: {connection.vendor}")

with connection.cursor() as cursor:
    # Check current user privileges
    cursor.execute("SELECT current_user, session_user;")
    user_info = cursor.fetchone()
    print(f"   Current User: {user_info[0]}")
    print(f"   Session User: {user_info[1]}")

    # Check if user is superuser
    cursor.execute("""
        SELECT rolsuper FROM pg_roles WHERE rolname = current_user;
    """)
    is_superuser = cursor.fetchone()
    print(f"   Is Superuser: {is_superuser[0] if is_superuser else 'Unknown'}")

    # Check existing extensions
    cursor.execute("""
        SELECT extname, extversion
        FROM pg_extension
        WHERE extname IN ('pg_trgm', 'btree_gin')
        ORDER BY extname;
    """)
    extensions = cursor.fetchall()
    print(f"\n2. EXTENSIONS IN MAIN DATABASE:")
    if extensions:
        for ext_name, ext_version in extensions:
            print(f"   ✅ {ext_name} v{ext_version}")
    else:
        print("   ❌ No extensions found")

# Try to create extension
print(f"\n3. TESTING EXTENSION CREATION:")
try:
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        print("   ✅ pg_trgm creation successful")
except Exception as e:
    print(f"   ❌ pg_trgm creation failed: {e}")

try:
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
        print("   ✅ btree_gin creation successful")
except Exception as e:
    print(f"   ❌ btree_gin creation failed: {e}")

# Test similarity function
print(f"\n4. TESTING SIMILARITY FUNCTION:")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT similarity('hello', 'helo');")
        result = cursor.fetchone()
        print(f"   ✅ similarity('hello', 'helo') = {result[0]}")
except Exception as e:
    print(f"   ❌ Similarity test failed: {e}")

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
print("\nIf 'Is Superuser: False', you need to either:")
print("1. Grant SUPERUSER to your PostgreSQL user (temporary)")
print("2. Create extensions in template1 database (permanent)")
print("3. Accept 99.5% completion (fuzzy search optional)")
print("=" * 70)
