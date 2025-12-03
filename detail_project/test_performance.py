"""
Performance Testing Script for Rekap Kebutuhan - Phase 1

Usage:
    python manage.py shell < detail_project/test_performance.py

Or run interactively:
    python manage.py shell
    >>> exec(open('detail_project/test_performance.py').read())
"""

import time
from django.core.cache import cache
from detail_project.models import Project
from detail_project.services import compute_kebutuhan_items

print("=" * 80)
print("REKAP KEBUTUHAN PERFORMANCE TEST")
print("=" * 80)

# Get first project for testing
try:
    project = Project.objects.first()
    if not project:
        print("❌ No projects found in database")
        exit(1)

    print(f"\nTesting with Project: {project.nama} (ID: {project.id})")
    print("-" * 80)

    # ============================================================================
    # TEST 1: Cold Cache (First Load)
    # ============================================================================
    print("\nTEST 1: Cold Cache (First Load)")
    print("-" * 40)

    # Clear cache
    cache_key = f"rekap_kebutuhan:{project.id}"
    cache.delete(cache_key)

    start = time.perf_counter()
    result = compute_kebutuhan_items(project, mode='all', filters={})
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Rows returned: {len(result)}")
    print(f"  Time taken: {elapsed:.2f}ms")

    if elapsed < 500:
        print(f"  ✅ PASS - Under 500ms target")
    elif elapsed < 1000:
        print(f"  ⚠️  ACCEPTABLE - Under 1000ms but above target")
    else:
        print(f"  ❌ FAIL - Over 1000ms")

    # ============================================================================
    # TEST 2: Warm Cache (Cache Hit)
    # ============================================================================
    print("\nTEST 2: Warm Cache (Cache Hit)")
    print("-" * 40)

    start = time.perf_counter()
    result = compute_kebutuhan_items(project, mode='all', filters={})
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Rows returned: {len(result)}")
    print(f"  Time taken: {elapsed:.2f}ms")

    if elapsed < 100:
        print(f"  ✅ PASS - Excellent cache performance")
    elif elapsed < 300:
        print(f"  ✅ PASS - Good cache performance")
    else:
        print(f"  ⚠️  WARNING - Cache might not be working")

    # ============================================================================
    # TEST 3: Single Category Filter
    # ============================================================================
    print("\nTEST 3: Single Category Filter (BHN)")
    print("-" * 40)

    cache.delete(cache_key)  # Clear cache for fair test

    start = time.perf_counter()
    result = compute_kebutuhan_items(
        project,
        mode='all',
        filters={'kategori': ['BHN']}
    )
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Rows returned: {len(result)}")
    print(f"  Time taken: {elapsed:.2f}ms")

    if elapsed < 500:
        print(f"  ✅ PASS - Filter query efficient")
    else:
        print(f"  ⚠️  WARNING - Filter query slow")

    # ============================================================================
    # TEST 4: Multiple Filters
    # ============================================================================
    print("\nTEST 4: Multiple Filters (BHN + ALT)")
    print("-" * 40)

    cache.delete(cache_key)

    start = time.perf_counter()
    result = compute_kebutuhan_items(
        project,
        mode='all',
        filters={'kategori': ['BHN', 'ALT']}
    )
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Rows returned: {len(result)}")
    print(f"  Time taken: {elapsed:.2f}ms")

    if elapsed < 500:
        print(f"  ✅ PASS - Multi-filter query efficient")
    else:
        print(f"  ⚠️  WARNING - Multi-filter query slow")

    # ============================================================================
    # TEST 5: Repeated Requests (Cache Effectiveness)
    # ============================================================================
    print("\nTEST 5: Cache Effectiveness (10 requests)")
    print("-" * 40)

    cache.delete(cache_key)

    times = []
    for i in range(10):
        start = time.perf_counter()
        result = compute_kebutuhan_items(project, mode='all', filters={})
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    cache_hit_time = sum(times[1:]) / len(times[1:])  # Exclude first (cold)

    print(f"  First request (cold): {times[0]:.2f}ms")
    print(f"  Average (all): {avg_time:.2f}ms")
    print(f"  Average (cache hits): {cache_hit_time:.2f}ms")
    print(f"  Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")

    if cache_hit_time < 100:
        print(f"  ✅ EXCELLENT - Cache very effective")
    elif cache_hit_time < 200:
        print(f"  ✅ GOOD - Cache working well")
    else:
        print(f"  ⚠️  WARNING - Cache may not be effective")

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 80)

    print(f"\nProject: {project.nama}")
    print(f"Total Items: {len(result)}")

    print("\nResults:")
    print(f"  Cold cache: {times[0]:.2f}ms")
    print(f"  Warm cache: {cache_hit_time:.2f}ms")

    # Calculate overall grade
    if times[0] < 500 and cache_hit_time < 100:
        grade = "A+ EXCELLENT"
    elif times[0] < 700 and cache_hit_time < 200:
        grade = "A GOOD"
    elif times[0] < 1000 and cache_hit_time < 300:
        grade = "B ACCEPTABLE"
    else:
        grade = "C NEEDS IMPROVEMENT"

    print(f"\nOverall Grade: {grade}")

    # Recommendations
    print("\nRecommendations:")
    if times[0] > 500:
        print("  • Consider applying query optimizations (select_related)")
    if times[0] > 1000:
        print("  • Database indexes may need review")
    if cache_hit_time > 200:
        print("  • Cache configuration may need tuning")
    if len(result) > 2000:
        print("  • Consider pagination or result limiting")

    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
