"""
Quick performance check for Phase 1 completion verification
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import time
from django.core.cache import cache
from detail_project.models import Project
from detail_project.services import compute_kebutuhan_items

print("=" * 80)
print("REKAP KEBUTUHAN PERFORMANCE TEST - Phase 1 Verification")
print("=" * 80)

try:
    project = Project.objects.first()
    if not project:
        print("No projects found")
        exit(1)

    print(f"\nProject: {project.nama} (ID: {project.id})")
    print("-" * 80)

    # Clear cache
    cache_key = f"rekap_kebutuhan:{project.id}"
    cache.delete(cache_key)

    # Test 1: Cold cache
    print("\nTEST 1: Cold Cache (First Load)")
    start = time.perf_counter()
    result = compute_kebutuhan_items(project, mode='all', filters={})
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Rows: {len(result)}")
    print(f"  Time: {elapsed:.2f}ms")

    if elapsed < 500:
        print(f"  PASS - Under 500ms target")
        test1_pass = True
    else:
        print(f"  WARNING - Over 500ms target")
        test1_pass = False

    # Test 2: Warm cache
    print("\nTEST 2: Warm Cache")
    start = time.perf_counter()
    result = compute_kebutuhan_items(project, mode='all', filters={})
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Time: {elapsed:.2f}ms")

    if elapsed < 100:
        print(f"  PASS - Excellent cache")
        test2_pass = True
    else:
        print(f"  WARNING - Cache may not be optimal")
        test2_pass = False

    # Summary
    print("\n" + "=" * 80)
    print("PHASE 1 PERFORMANCE VERIFICATION")
    print("=" * 80)

    if test1_pass and test2_pass:
        print("\nRESULT: PASS")
        print("Phase 1 Performance track is COMPLETE")
    else:
        print("\nRESULT: NEEDS OPTIMIZATION")
        print("Phase 1 Performance track requires additional work")

    print("\n" + "=" * 80)

except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()
