"""
Unit tests for PostgreSQL Full-Text Search (Phase 3).

Tests full-text search functionality including:
- Basic search
- Fuzzy/typo-tolerant search
- Prefix search (autocomplete)
- Advanced combined search
- Performance benchmarks
"""

import time
from decimal import Decimal
import pytest
from django.test import TestCase, override_settings
from django.db import connection

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.ahsp_repository import AHSPRepository, ahsp_repository


@pytest.mark.django_db
class TestFullTextSearchSetup(TestCase):
    """Test that full-text search is properly set up."""

    def test_search_vector_column_exists_ahsp(self):
        """Test that search_vector column exists on AHSPReferensi."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'referensi_ahspreferensi'
                AND column_name = 'search_vector'
            """)
            result = cursor.fetchone()
            self.assertIsNotNone(result, "search_vector column should exist")

    def test_search_vector_index_exists_ahsp(self):
        """Test that GIN index exists on search_vector."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'referensi_ahspreferensi'
                AND indexname = 'ix_ahsp_search_vector'
            """)
            result = cursor.fetchone()
            self.assertIsNotNone(result, "GIN index should exist")

    def test_search_vector_column_exists_rincian(self):
        """Test that search_vector column exists on RincianReferensi."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'referensi_rincianreferensi'
                AND column_name = 'search_vector'
            """)
            result = cursor.fetchone()
            self.assertIsNotNone(result, "search_vector column should exist")


@pytest.mark.django_db
class TestBasicSearch(TestCase):
    """Test basic full-text search functionality."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.ahsp1 = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Beton Bertulang",
            klasifikasi="Konstruksi",
            sub_klasifikasi="Beton",
            satuan="m3"
        )
        cls.ahsp2 = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.2",
            nama_ahsp="Pekerjaan Beton Ready Mix",
            klasifikasi="Konstruksi",
            sub_klasifikasi="Beton",
            satuan="m3"
        )
        cls.ahsp3 = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="2.1.1",
            nama_ahsp="Pekerjaan Baja Struktural",
            klasifikasi="Konstruksi",
            sub_klasifikasi="Baja",
            satuan="kg"
        )

        # Create rincian for testing
        RincianReferensi.objects.create(
            ahsp=cls.ahsp1,
            kategori="BHN",
            kode_item="BHN-001",
            uraian_item="Semen Portland",
            satuan_item="kg",
            koefisien=Decimal("10.5")
        )
        RincianReferensi.objects.create(
            ahsp=cls.ahsp1,
            kategori="TK",
            kode_item="TK-001",
            uraian_item="Pekerja",
            satuan_item="OH",
            koefisien=Decimal("0.5")
        )

        cls.repo = AHSPRepository()

    def test_search_by_name(self):
        """Test searching by nama_ahsp."""
        results = self.repo.search_ahsp("beton")
        self.assertEqual(results.count(), 2)
        self.assertIn(self.ahsp1, results)
        self.assertIn(self.ahsp2, results)

    def test_search_by_name_partial(self):
        """Test searching with partial word."""
        results = self.repo.search_ahsp("bertulang")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.ahsp1)

    def test_search_by_code(self):
        """Test searching by kode_ahsp."""
        results = self.repo.search_ahsp("1.1.1")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.ahsp1)

    def test_search_by_classification(self):
        """Test searching by klasifikasi."""
        results = self.repo.search_ahsp("baja")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.ahsp3)

    def test_search_with_filter_sumber(self):
        """Test search with sumber filter."""
        results = self.repo.search_ahsp("beton", sumber="SNI 2025")
        self.assertEqual(results.count(), 2)

    def test_search_with_filter_klasifikasi(self):
        """Test search with klasifikasi filter."""
        results = self.repo.search_ahsp("pekerjaan", klasifikasi="Konstruksi")
        self.assertEqual(results.count(), 3)

    def test_search_no_results(self):
        """Test search with no matches."""
        results = self.repo.search_ahsp("xyz123notfound")
        self.assertEqual(results.count(), 0)

    def test_search_too_short_query(self):
        """Test search with query too short."""
        results = self.repo.search_ahsp("a")  # Only 1 character
        self.assertEqual(results.count(), 0)

    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.repo.search_ahsp("")
        self.assertEqual(results.count(), 0)

    def test_search_relevance_ranking(self):
        """Test that results are ranked by relevance."""
        # "beton bertulang" should rank higher than just "beton"
        results = list(self.repo.search_ahsp("beton bertulang"))
        self.assertEqual(results[0], self.ahsp1)  # Beton Bertulang first


@pytest.mark.django_db
class TestFuzzySearch(TestCase):
    """Test fuzzy/typo-tolerant search."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.ahsp1 = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Beton Bertulang",
            klasifikasi="Konstruksi"
        )
        cls.repo = AHSPRepository()

    def test_fuzzy_search_with_typo(self):
        """Test fuzzy search handles typos."""
        # "betom" should match "beton"
        results = self.repo.fuzzy_search_ahsp("betom", threshold=0.3)
        self.assertGreater(results.count(), 0)
        self.assertIn(self.ahsp1, results)

    def test_fuzzy_search_threshold(self):
        """Test fuzzy search threshold works."""
        # High threshold should give fewer results
        results_low = self.repo.fuzzy_search_ahsp("beton", threshold=0.1)
        results_high = self.repo.fuzzy_search_ahsp("beton", threshold=0.9)
        self.assertGreater(results_low.count(), results_high.count())


@pytest.mark.django_db
class TestPrefixSearch(TestCase):
    """Test prefix search for autocomplete."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan A"
        )
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.2",
            nama_ahsp="Pekerjaan B"
        )
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="2.1.1",
            nama_ahsp="Pekerjaan C"
        )
        cls.repo = AHSPRepository()

    def test_prefix_search_by_code(self):
        """Test prefix search on kode_ahsp."""
        results = self.repo.prefix_search_ahsp("1.1", field='kode_ahsp')
        self.assertEqual(results.count(), 2)

    def test_prefix_search_by_name(self):
        """Test prefix search on nama_ahsp."""
        results = self.repo.prefix_search_ahsp("Pekerjaan", field='nama_ahsp')
        self.assertEqual(results.count(), 3)

    def test_prefix_search_limit(self):
        """Test prefix search respects limit."""
        results = self.repo.prefix_search_ahsp("1.", field='kode_ahsp', limit=1)
        self.assertEqual(results.count(), 1)


@pytest.mark.django_db
class TestAdvancedSearch(TestCase):
    """Test advanced combined search."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.ahsp1 = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Beton",
            klasifikasi="Konstruksi",
            sub_klasifikasi="Beton"
        )
        cls.ahsp2 = AHSPReferensi.objects.create(
            sumber="AHSP 2023",
            kode_ahsp="2.1.1",
            nama_ahsp="Pekerjaan Beton",
            klasifikasi="Konstruksi",
            sub_klasifikasi="Beton"
        )
        cls.repo = AHSPRepository()

    def test_advanced_search_all_filters(self):
        """Test advanced search with all filters."""
        results = self.repo.advanced_search(
            query="beton",
            sumber="SNI 2025",
            klasifikasi="Konstruksi",
            kode_prefix="1."
        )
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.ahsp1)

    def test_advanced_search_without_query(self):
        """Test advanced search with filters only."""
        results = self.repo.advanced_search(
            sumber="SNI 2025"
        )
        self.assertEqual(results.count(), 1)


@pytest.mark.django_db
class TestRincianSearch(TestCase):
    """Test search on RincianReferensi."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        ahsp = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Test"
        )
        cls.rincian1 = RincianReferensi.objects.create(
            ahsp=ahsp,
            kategori="BHN",
            kode_item="BHN-001",
            uraian_item="Semen Portland",
            satuan_item="kg",
            koefisien=Decimal("10")
        )
        cls.rincian2 = RincianReferensi.objects.create(
            ahsp=ahsp,
            kategori="TK",
            kode_item="TK-001",
            uraian_item="Pekerja",
            satuan_item="OH",
            koefisien=Decimal("0.5")
        )
        cls.repo = AHSPRepository()

    def test_search_rincian_by_description(self):
        """Test searching rincian by uraian_item."""
        results = self.repo.search_rincian("semen")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.rincian1)

    def test_search_rincian_with_kategori_filter(self):
        """Test search rincian with kategori filter."""
        results = self.repo.search_rincian("pekerja", kategori="TK")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.rincian2)


@pytest.mark.django_db
class TestSearchUtilities(TestCase):
    """Test utility search methods."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Beton Bertulang"
        )
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.2",
            nama_ahsp="Pekerjaan Beton Ready Mix"
        )
        cls.repo = AHSPRepository()

    def test_get_search_suggestions(self):
        """Test autocomplete suggestions."""
        suggestions = self.repo.get_search_suggestions("beton")
        self.assertEqual(len(suggestions), 2)
        self.assertIn("Pekerjaan Beton Bertulang", suggestions)

    def test_count_search_results(self):
        """Test counting search results."""
        count = self.repo.count_search_results("beton")
        self.assertEqual(count, 2)


@pytest.mark.django_db
class TestMultiQuerySearch(TestCase):
    """Test multi-query search."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Beton"
        )
        AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="2.1.1",
            nama_ahsp="Pekerjaan Baja"
        )
        cls.repo = AHSPRepository()

    def test_multi_query_or(self):
        """Test multi-query with OR."""
        results = self.repo.search_multiple_queries(
            ["beton", "baja"],
            combine='OR'
        )
        self.assertEqual(results.count(), 2)

    def test_multi_query_and(self):
        """Test multi-query with AND."""
        results = self.repo.search_multiple_queries(
            ["pekerjaan", "beton"],
            combine='AND'
        )
        self.assertEqual(results.count(), 1)


@pytest.mark.django_db
class TestPerformanceBenchmarks(TestCase):
    """Performance benchmarks for full-text search."""

    @classmethod
    def setUpTestData(cls):
        """Create larger dataset for benchmarking."""
        # Create 1000 AHSP records
        ahsp_list = []
        for i in range(1000):
            ahsp_list.append(AHSPReferensi(
                sumber=f"SNI {2020 + (i % 5)}",
                kode_ahsp=f"{(i // 100) + 1}.{(i // 10) % 10}.{i % 10}",
                nama_ahsp=f"Pekerjaan Test {i} Beton Bertulang",
                klasifikasi="Konstruksi" if i % 2 == 0 else "Finishing",
                sub_klasifikasi="Beton" if i % 3 == 0 else "Cat",
                satuan="m3"
            ))
        AHSPReferensi.objects.bulk_create(ahsp_list, batch_size=500)
        cls.repo = AHSPRepository()

    def test_search_performance_1000_records(self):
        """Benchmark search on 1000 records."""
        start_time = time.time()
        results = self.repo.search_ahsp("beton")
        result_count = results.count()
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000

        # Assert search is fast (should be < 50ms with GIN index)
        self.assertLess(elapsed_ms, 100, f"Search took {elapsed_ms:.2f}ms (expected < 100ms)")
        self.assertGreater(result_count, 0, "Should find results")

        print(f"\n📊 Search Performance on 1,000 records:")
        print(f"   Query: 'beton'")
        print(f"   Results: {result_count}")
        print(f"   Time: {elapsed_ms:.2f}ms")

    def test_complex_search_performance(self):
        """Benchmark complex search with multiple filters."""
        start_time = time.time()
        results = self.repo.advanced_search(
            query="beton bertulang",
            sumber="SNI 2024",
            klasifikasi="Konstruksi",
            kode_prefix="2."
        )
        result_count = results.count()
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000

        self.assertLess(elapsed_ms, 150, f"Complex search took {elapsed_ms:.2f}ms (expected < 150ms)")

        print(f"\n📊 Complex Search Performance on 1,000 records:")
        print(f"   Query: 'beton bertulang' + 3 filters")
        print(f"   Results: {result_count}")
        print(f"   Time: {elapsed_ms:.2f}ms")

    def test_fuzzy_search_performance(self):
        """Benchmark fuzzy search."""
        start_time = time.time()
        results = self.repo.fuzzy_search_ahsp("betom", threshold=0.3)
        result_count = results.count()
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000

        print(f"\n📊 Fuzzy Search Performance on 1,000 records:")
        print(f"   Query: 'betom' (typo for 'beton')")
        print(f"   Results: {result_count}")
        print(f"   Time: {elapsed_ms:.2f}ms")


@pytest.mark.django_db
class TestSearchTypes(TestCase):
    """Test different search types (websearch, plain, phrase)."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.ahsp1 = AHSPReferensi.objects.create(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Beton Bertulang"
        )
        cls.repo = AHSPRepository()

    def test_websearch_type(self):
        """Test websearch (default) type."""
        results = self.repo.search_ahsp("beton OR bertulang", search_type='websearch')
        self.assertGreater(results.count(), 0)

    def test_plain_type(self):
        """Test plain search type."""
        results = self.repo.search_ahsp("beton", search_type='plain')
        self.assertGreater(results.count(), 0)

    def test_phrase_type(self):
        """Test phrase search type."""
        results = self.repo.search_ahsp("Pekerjaan Beton", search_type='phrase')
        self.assertEqual(results.count(), 1)
