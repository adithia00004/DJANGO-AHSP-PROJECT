"""
Tests for ItemRepository.

PHASE 4: Comprehensive repository layer tests.
"""

import pytest

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.repositories.item_repository import ItemRepository


@pytest.fixture
def sample_item_data(db):
    """Create sample rincian (item) data for testing."""
    # Create parent AHSP records
    ahsp1 = AHSPReferensi.objects.create(
        kode_ahsp="A.001",
        nama_ahsp="Pekerjaan Galian",
        satuan="M3",
        sumber="SNI 2025",
    )

    ahsp2 = AHSPReferensi.objects.create(
        kode_ahsp="B.002",
        nama_ahsp="Pekerjaan Beton",
        satuan="M3",
        sumber="SNI 2025",
    )

    # Create rincian items for ahsp1
    item1 = RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori="TK",
        kode_item="TK.001",
        uraian_item="Pekerja",
        satuan_item="Orang",
        koefisien=0.5,
    )

    item2 = RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori="BHN",
        kode_item="BHN.001",
        uraian_item="Semen Portland",
        satuan_item="Kg",
        koefisien=350.0,
    )

    item3 = RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori="ALT",
        kode_item="ALT.001",
        uraian_item="Excavator",
        satuan_item="Jam",
        koefisien=0.25,
    )

    # Create rincian items for ahsp2
    item4 = RincianReferensi.objects.create(
        ahsp=ahsp2,
        kategori="TK",
        kode_item="TK.002",
        uraian_item="Mandor",
        satuan_item="Orang",
        koefisien=0.1,
    )

    item5 = RincianReferensi.objects.create(
        ahsp=ahsp2,
        kategori="BHN",
        kode_item="BHN.002",
        uraian_item="Pasir Beton",
        satuan_item="M3",
        koefisien=0.7,
    )

    return {
        'ahsp1': ahsp1,
        'ahsp2': ahsp2,
        'item1': item1,
        'item2': item2,
        'item3': item3,
        'item4': item4,
        'item5': item5,
    }


class TestItemRepositoryBasics:
    """Test basic repository methods."""

    def test_base_queryset(self, sample_item_data):
        """Test base_queryset returns all items with select_related."""
        queryset = ItemRepository.base_queryset()
        assert queryset.count() == 5
        assert queryset.model == RincianReferensi

    def test_base_queryset_select_related(self, sample_item_data):
        """Test base_queryset uses select_related for optimization."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            queryset = ItemRepository.base_queryset()
            # Access AHSP data to trigger join
            for item in queryset:
                _ = item.ahsp.kode_ahsp

        # Should only have 1 query due to select_related
        assert len(queries) == 1

    def test_base_queryset_is_queryset(self):
        """Test base_queryset returns a QuerySet."""
        result = ItemRepository.base_queryset()
        from django.db.models import QuerySet
        assert isinstance(result, QuerySet)


class TestItemRepositorySearch:
    """Test search functionality."""

    def test_filter_by_search_kode_item(self, sample_item_data):
        """Test search by kode_item."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, "TK.001")

        assert result.count() == 1
        assert result.first().kode_item == "TK.001"

    def test_filter_by_search_uraian_item(self, sample_item_data):
        """Test search by uraian_item."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, "Semen")

        assert result.count() == 1
        assert result.first().uraian_item == "Semen Portland"

    def test_filter_by_search_ahsp_kode(self, sample_item_data):
        """Test search by parent AHSP kode."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, "A.001")

        # Should return all 3 items from ahsp1
        assert result.count() == 3

    def test_filter_by_search_partial_match(self, sample_item_data):
        """Test search with partial keyword."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, "Pekerja")

        # Should match "Pekerja" in uraian_item
        assert result.count() == 1
        assert result.first().uraian_item == "Pekerja"

    def test_filter_by_search_case_insensitive(self, sample_item_data):
        """Test search is case-insensitive."""
        queryset = ItemRepository.base_queryset()
        result1 = ItemRepository.filter_by_search(queryset, "pekerja")
        result2 = ItemRepository.filter_by_search(queryset, "PEKERJA")

        assert result1.count() == result2.count() == 1

    def test_filter_by_search_empty_keyword(self, sample_item_data):
        """Test search with empty keyword returns all."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, "")

        assert result.count() == 5

    def test_filter_by_search_no_matches(self, sample_item_data):
        """Test search with no matches returns empty."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, "zzznonexistent")

        assert result.count() == 0

    def test_filter_by_search_multiple_fields(self, sample_item_data):
        """Test search matches across multiple fields."""
        queryset = ItemRepository.base_queryset()

        # Search for "BHN" - should match both kode_item fields
        result = ItemRepository.filter_by_search(queryset, "BHN")

        assert result.count() == 2
        assert all("BHN" in item.kode_item for item in result)


class TestItemRepositoryCategory:
    """Test category filtering."""

    def test_filter_by_category_tk(self, sample_item_data):
        """Test filtering by TK category."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, "TK")

        assert result.count() == 2
        assert all(item.kategori == "TK" for item in result)

    def test_filter_by_category_bhn(self, sample_item_data):
        """Test filtering by BHN category."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, "BHN")

        assert result.count() == 2
        assert all(item.kategori == "BHN" for item in result)

    def test_filter_by_category_alt(self, sample_item_data):
        """Test filtering by ALT category."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, "ALT")

        assert result.count() == 1
        assert result.first().kategori == "ALT"

    def test_filter_by_category_none(self, sample_item_data):
        """Test filtering with None category returns all."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, None)

        assert result.count() == 5

    def test_filter_by_category_empty(self, sample_item_data):
        """Test filtering with empty string returns all."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, "")

        assert result.count() == 5

    def test_filter_by_category_invalid(self, sample_item_data):
        """Test filtering with invalid category."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, "INVALID")

        # Should filter but return nothing (no items with kategori="INVALID")
        assert result.count() == 0


class TestItemRepositoryJob:
    """Test job (AHSP) filtering."""

    def test_filter_by_job_ahsp1(self, sample_item_data):
        """Test filtering by ahsp1 ID."""
        queryset = ItemRepository.base_queryset()
        ahsp1_id = sample_item_data['ahsp1'].id
        result = ItemRepository.filter_by_job(queryset, ahsp1_id)

        assert result.count() == 3
        assert all(item.ahsp_id == ahsp1_id for item in result)

    def test_filter_by_job_ahsp2(self, sample_item_data):
        """Test filtering by ahsp2 ID."""
        queryset = ItemRepository.base_queryset()
        ahsp2_id = sample_item_data['ahsp2'].id
        result = ItemRepository.filter_by_job(queryset, ahsp2_id)

        assert result.count() == 2
        assert all(item.ahsp_id == ahsp2_id for item in result)

    def test_filter_by_job_none(self, sample_item_data):
        """Test filtering with None job_id returns all."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_job(queryset, None)

        assert result.count() == 5

    def test_filter_by_job_nonexistent(self, sample_item_data):
        """Test filtering with non-existent job_id."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_job(queryset, 99999)

        assert result.count() == 0


class TestItemRepositoryChaining:
    """Test method chaining and combined filters."""

    def test_chain_search_and_category(self, sample_item_data):
        """Test chaining search and category filters."""
        queryset = ItemRepository.base_queryset()
        queryset = ItemRepository.filter_by_search(queryset, "BHN")
        result = ItemRepository.filter_by_category(queryset, "BHN")

        # Should return 2 BHN items
        assert result.count() == 2

    def test_chain_category_and_job(self, sample_item_data):
        """Test chaining category and job filters."""
        queryset = ItemRepository.base_queryset()
        ahsp1_id = sample_item_data['ahsp1'].id
        queryset = ItemRepository.filter_by_category(queryset, "BHN")
        result = ItemRepository.filter_by_job(queryset, ahsp1_id)

        # Should return 1 BHN item from ahsp1
        assert result.count() == 1
        assert result.first().kode_item == "BHN.001"

    def test_chain_search_category_and_job(self, sample_item_data):
        """Test chaining all three filters."""
        queryset = ItemRepository.base_queryset()
        ahsp1_id = sample_item_data['ahsp1'].id

        queryset = ItemRepository.filter_by_search(queryset, "Portland")
        queryset = ItemRepository.filter_by_category(queryset, "BHN")
        result = ItemRepository.filter_by_job(queryset, ahsp1_id)

        # Should return only "Semen Portland" item
        assert result.count() == 1
        assert result.first().uraian_item == "Semen Portland"

    def test_chain_multiple_searches(self, sample_item_data):
        """Test chaining multiple search filters."""
        queryset = ItemRepository.base_queryset()

        # First search narrows down
        queryset = ItemRepository.filter_by_search(queryset, "A.001")
        # Second search further narrows
        result = ItemRepository.filter_by_search(queryset, "TK")

        # Should return only TK item from A.001
        assert result.count() == 1
        assert result.first().kode_item == "TK.001"


class TestItemRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_database(self, db):
        """Test repository methods with empty database."""
        queryset = ItemRepository.base_queryset()
        assert queryset.count() == 0

        result = ItemRepository.filter_by_search(queryset, "test")
        assert result.count() == 0

    def test_search_special_characters(self, sample_item_data):
        """Test search with special characters."""
        queryset = ItemRepository.base_queryset()
        # Search with dot
        result = ItemRepository.filter_by_search(queryset, "TK.001")

        assert result.count() == 1

    def test_search_none_keyword(self, sample_item_data):
        """Test search with None keyword."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_search(queryset, None)

        # Should return all (no filtering)
        assert result.count() == 5

    def test_filter_with_zero_id(self, sample_item_data):
        """Test filtering with job_id=0."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_job(queryset, 0)

        # 0 is falsy, should return all
        assert result.count() == 5


class TestItemRepositoryPerformance:
    """Test performance-related behavior."""

    def test_select_related_optimization(self, sample_item_data):
        """Test that select_related prevents N+1 queries."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        # Using base_queryset (with select_related)
        with CaptureQueriesContext(connection) as queries_optimized:
            queryset = ItemRepository.base_queryset()
            for item in queryset:
                _ = item.ahsp.kode_ahsp
                _ = item.ahsp.nama_ahsp

        # Should only have 1 query (JOIN with select_related)
        assert len(queries_optimized) == 1

        # Without select_related (baseline comparison)
        with CaptureQueriesContext(connection) as queries_baseline:
            queryset = RincianReferensi.objects.all()  # No select_related
            for item in queryset:
                _ = item.ahsp.kode_ahsp
                _ = item.ahsp.nama_ahsp

        # Should have N+1 queries (1 for items + N for each AHSP)
        assert len(queries_baseline) > 1

    def test_chained_filters_single_query(self, sample_item_data):
        """Test that chained filters result in a single query."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        ahsp1_id = sample_item_data['ahsp1'].id

        with CaptureQueriesContext(connection) as queries:
            queryset = ItemRepository.base_queryset()
            queryset = ItemRepository.filter_by_search(queryset, "BHN")
            queryset = ItemRepository.filter_by_category(queryset, "BHN")
            queryset = ItemRepository.filter_by_job(queryset, ahsp1_id)

            # Force evaluation
            _ = list(queryset)

        # Should only have 1 query despite multiple filters
        assert len(queries) == 1


class TestItemRepositoryDataIntegrity:
    """Test data integrity and relationships."""

    def test_items_have_valid_ahsp(self, sample_item_data):
        """Test all items have valid parent AHSP."""
        queryset = ItemRepository.base_queryset()

        for item in queryset:
            assert item.ahsp is not None
            assert item.ahsp.kode_ahsp is not None

    def test_filter_preserves_relationships(self, sample_item_data):
        """Test filtering preserves AHSP relationships."""
        queryset = ItemRepository.base_queryset()
        result = ItemRepository.filter_by_category(queryset, "TK")

        for item in result:
            assert item.ahsp is not None
            assert item.kategori == "TK"

    def test_kategori_values_are_valid(self, sample_item_data):
        """Test all kategori values are valid."""
        queryset = ItemRepository.base_queryset()
        valid_categories = {"TK", "BHN", "ALT", "LAIN"}

        for item in queryset:
            assert item.kategori in valid_categories
