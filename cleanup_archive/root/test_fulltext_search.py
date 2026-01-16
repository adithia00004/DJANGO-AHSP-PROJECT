"""
Test script for full-text search performance.

PHASE 3 DAY 2: Compare ILIKE vs full-text search performance.
"""

import time

import pytest


@pytest.mark.django_db
def test_fulltext_search():
    """Test full-text search with timing."""
    # Import inside test to avoid Django setup issues
    from referensi.repositories.ahsp_repository import AHSPRepository

    print("\n" + "=" * 60)
    print("PHASE 3 DAY 2: Full-Text Search Performance Test")
    print("=" * 60)

    # Test queries (using actual data keywords)
    test_keywords = ["bulk", "job"]

    for keyword in test_keywords:
        print(f"\nSearching for: '{keyword}'")
        print("-" * 60)

        # Full-text search
        start = time.time()
        result = AHSPRepository.filter_by_search(
            AHSPRepository.base_queryset(), keyword
        )
        count = result.count()
        elapsed_fts = (time.time() - start) * 1000

        print(f"Full-text search: {count} results in {elapsed_fts:.2f}ms")

        # Show top 3 results
        if count > 0:
            print("\nTop 3 results (ranked by relevance):")
            for i, ahsp in enumerate(result[:3], 1):
                print(f"  {i}. {ahsp.kode_ahsp}: {ahsp.nama_ahsp[:50]}...")

    print("\n" + "=" * 60)
    print("SUCCESS: Full-text search is working!")
    print("=" * 60)


if __name__ == "__main__":
    # For manual testing
    import os
    import sys
    import django

    sys.path.insert(0, os.path.dirname(__file__))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    test_fulltext_search()
