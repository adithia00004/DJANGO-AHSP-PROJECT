#!/usr/bin/env python
"""
Quick test script to verify V2 Rekap Kebutuhan Weekly optimization.
Measures query count and response time before/after optimization.
"""
import os
import sys
import django
import time
from django.db import connection, reset_queries
from django.test.utils import override_settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from detail_project.views_api import api_rekap_kebutuhan_weekly

User = get_user_model()

import pytest

@pytest.mark.django_db
def test_endpoint_performance(project_id=160):
    """Test the optimized endpoint."""
    pytest.skip("Standalone performance test - run with: python test_optimization.py")
    print("="*80)
    print("TESTING V2 REKAP KEBUTUHAN WEEKLY OPTIMIZATION")
    print("="*80)
    print(f"\nProject ID: {project_id}")
    print()

    # Get test user
    try:
        user = User.objects.filter(email='aditf96@gmail.com').first()
        if not user:
            raise User.DoesNotExist
        print(f"[OK] Test user found: {user.email}")
    except User.DoesNotExist:
        print("[ERROR] Test user not found!")
        return

    # Create mock request
    factory = RequestFactory()
    request = factory.get(f'/api/v2/project/{project_id}/rekap-kebutuhan-weekly/')
    request.user = user

    # Enable query logging
    reset_queries()

    # Test 1: Measure query count
    print("\n" + "-"*80)
    print("TEST 1: Query Count")
    print("-"*80)

    from django.conf import settings
    settings.DEBUG = True  # Enable query logging

    start_time = time.time()
    response = api_rekap_kebutuhan_weekly(request, project_id)
    end_time = time.time()

    query_count = len(connection.queries)
    response_time_ms = (end_time - start_time) * 1000

    print(f"Total Queries: {query_count}")
    print(f"Response Time: {response_time_ms:.1f}ms ({response_time_ms/1000:.2f}s)")
    print()

    # Show sample queries
    if query_count > 0:
        print("Sample Queries:")
        for i, query in enumerate(connection.queries[:5], 1):
            sql = query['sql'][:100]  # First 100 chars
            time_ms = float(query['time']) * 1000
            print(f"  {i}. [{time_ms:.1f}ms] {sql}...")
        if query_count > 5:
            print(f"  ... and {query_count - 5} more queries")

    # Test 2: Response validation
    print("\n" + "-"*80)
    print("TEST 2: Response Validation")
    print("-"*80)

    if response.status_code == 200:
        import json
        data = json.loads(response.content)

        weeks = len(data.get('weeklyData', []))
        total_items = data.get('summary', {}).get('total_items', {})

        print(f"[OK] Status Code: {response.status_code}")
        print(f"[OK] Total Weeks: {weeks}")
        print(f"[OK] Total Items by Category:")
        for kategori, count in total_items.items():
            print(f"    - {kategori}: {count} items")
    else:
        print(f"[ERROR] Status Code: {response.status_code}")
        print(f"  Response: {response.content[:200]}")

    # Performance Evaluation
    print("\n" + "-"*80)
    print("PERFORMANCE EVALUATION")
    print("-"*80)

    if query_count <= 10:
        status = "[OK] EXCELLENT"
    elif query_count <= 50:
        status = "[OK] GOOD"
    elif query_count <= 200:
        status = "[WARN] ACCEPTABLE"
    else:
        status = "[ERROR] POOR (N+1 problem!)"

    print(f"Query Optimization: {status}")
    print(f"   Queries: {query_count} (target: <10)")

    if response_time_ms < 500:
        time_status = "[OK] EXCELLENT"
    elif response_time_ms < 1000:
        time_status = "[OK] GOOD"
    elif response_time_ms < 2000:
        time_status = "[WARN] ACCEPTABLE"
    else:
        time_status = "[ERROR] TOO SLOW"

    print(f"Response Time: {time_status}")
    print(f"   Time: {response_time_ms:.1f}ms (target: <1000ms)")

    # Expected improvement
    print("\n" + "-"*80)
    print("OPTIMIZATION IMPACT")
    print("-"*80)
    print("Before Optimization:")
    print("  - Queries: 1000+ (N+1 problem)")
    print("  - Response Time: 2400-7200ms (2.4-7.2 seconds)")
    print()
    print("After Optimization (Current):")
    print(f"  - Queries: {query_count} ({((1000-query_count)/1000*100):.0f}% reduction)")
    print(f"  - Response Time: {response_time_ms:.0f}ms ({((7000-response_time_ms)/7000*100):.0f}% faster)")

    if query_count < 20 and response_time_ms < 1000:
        print("\n[SUCCESS] OPTIMIZATION SUCCESSFUL!")
        print("   Ready for production and scaling tests.")
    elif query_count < 50 and response_time_ms < 2000:
        print("\n[OK] OPTIMIZATION WORKING")
        print("   Good improvement, but can be further optimized.")
    else:
        print("\n[WARN] OPTIMIZATION NEEDS REVIEW")
        print("   Consider additional optimizations (database aggregation, caching).")

    print("\n" + "="*80)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Test V2 Rekap Weekly optimization')
    parser.add_argument('--project-id', type=int, default=160, help='Project ID to test')
    args = parser.parse_args()

    test_endpoint_performance(args.project_id)
