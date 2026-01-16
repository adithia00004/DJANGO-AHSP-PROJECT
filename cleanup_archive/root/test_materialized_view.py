"""
Test script for materialized view performance.

PHASE 3 DAY 3: Compare aggregations vs materialized view performance.
"""

import time

import pytest


@pytest.mark.django_db
def test_materialized_view():
    """Test materialized view performance vs aggregations."""
    # Import inside test to avoid Django setup issues
    from django.db import connection

    from referensi.models import AHSPReferensi, RincianReferensi
    from referensi.repositories.ahsp_repository import AHSPRepository

    # Create test data if database is empty
    if AHSPReferensi.objects.count() == 0:
        print("\nCreating test data...")
        # Create some test AHSP records
        for i in range(10):
            ahsp = AHSPReferensi.objects.create(
                kode_ahsp=f"TEST{i:03d}",
                nama_ahsp=f"Test AHSP {i}",
                sumber="Test Source",
            )
            # Create rincian for each AHSP
            RincianReferensi.objects.create(
                ahsp=ahsp,
                kategori="TK",
                kode_item=f"TK{i:03d}",
                uraian_item=f"Test TK {i}",
                satuan_item="Orang",
                koefisien=1.0,
            )
            RincianReferensi.objects.create(
                ahsp=ahsp,
                kategori="BHN",
                kode_item=f"BHN{i:03d}",
                uraian_item=f"Test BHN {i}",
                satuan_item="Kg",
                koefisien=2.0,
            )
        print(f"Created {AHSPReferensi.objects.count()} test AHSP records")

        # Refresh materialized view
        print("Refreshing materialized view...")
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW referensi_ahsp_stats")
        print("Materialized view refreshed")

    print("\n" + "=" * 60)
    print("PHASE 3 DAY 3: Materialized View Performance Test")
    print("=" * 60)

    print("\nTest 1: Old Method (Expensive Aggregations)")
    print("-" * 60)
    start = time.time()
    result_old = AHSPRepository.get_with_category_counts()
    count_old = result_old.count()
    elapsed_old = (time.time() - start) * 1000
    print(f"Count query time: {elapsed_old:.2f}ms")

    start = time.time()
    first_3_old = list(result_old[:3])
    elapsed_fetch_old = (time.time() - start) * 1000
    print(f"Fetch first 3 records: {elapsed_fetch_old:.2f}ms")
    print(f"Total time (old method): {elapsed_old + elapsed_fetch_old:.2f}ms")

    if first_3_old:
        sample = first_3_old[0]
        print(f"\nSample record: {sample.kode_ahsp}")
        print(f"  Total rincian: {sample.rincian_total}")
        print(f"  TK: {sample.tk_count}, BHN: {sample.bhn_count}, ALT: {sample.alt_count}")

    print("\n" + "=" * 60)
    print("\nTest 2: New Method (Materialized View)")
    print("-" * 60)
    start = time.time()
    result_new = AHSPRepository.get_with_category_counts_fast()
    count_new = result_new.count()
    elapsed_new = (time.time() - start) * 1000
    print(f"Count query time: {elapsed_new:.2f}ms")

    start = time.time()
    first_3_new = list(result_new[:3])
    elapsed_fetch_new = (time.time() - start) * 1000
    print(f"Fetch first 3 records: {elapsed_fetch_new:.2f}ms")
    print(f"Total time (new method): {elapsed_new + elapsed_fetch_new:.2f}ms")

    if first_3_new:
        sample = first_3_new[0]
        print(f"\nSample record: {sample.kode_ahsp}")
        print(f"  Total rincian: {sample.rincian_total}")
        print(f"  TK: {sample.tk_count}, BHN: {sample.bhn_count}, ALT: {sample.alt_count}")

    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)

    total_old = elapsed_old + elapsed_fetch_old
    total_new = elapsed_new + elapsed_fetch_new

    speedup = ((total_old - total_new) / total_old) * 100 if total_old > 0 else 0

    print(f"Old method (aggregations): {total_old:.2f}ms")
    print(f"New method (materialized view): {total_new:.2f}ms")
    print(f"Speedup: {speedup:.1f}% faster!")
    print(f"Time saved: {total_old - total_new:.2f}ms")

    print("\n" + "=" * 60)
    print("SUCCESS: Materialized view is working!")
    print("=" * 60)

    # Verify data matches
    if count_old == count_new:
        print(f"\nData integrity: OK (both methods return {count_new} records)")
    else:
        print(f"\nWARNING: Count mismatch! Old={count_old}, New={count_new}")

    # Assert for pytest
    assert count_new > 0, "Materialized view should have data"
    assert count_old == count_new, f"Counts should match: old={count_old}, new={count_new}"


if __name__ == "__main__":
    # For manual testing
    import os
    import sys
    import django

    sys.path.insert(0, os.path.dirname(__file__))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    test_materialized_view()
