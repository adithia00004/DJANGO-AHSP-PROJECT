"""
Tests for AHSPRepository.

PHASE 4: Comprehensive repository layer tests.
"""

import pytest
from django.db import connection

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.repositories.ahsp_repository import AHSPRepository


@pytest.fixture
def sample_ahsp_data(db):
    """Create sample AHSP data for testing."""
    # Create AHSP records with different sources and classifications
    ahsp1 = AHSPReferensi.objects.create(
        kode_ahsp="A.001",
        nama_ahsp="Pekerjaan Galian Tanah Biasa",
        satuan="M3",
        sumber="SNI 2025",
        klasifikasi="Pekerjaan Tanah",
        sub_klasifikasi="Galian",
    )

    ahsp2 = AHSPReferensi.objects.create(
        kode_ahsp="B.002",
        nama_ahsp="Pekerjaan Beton K-225",
        satuan="M3",
        sumber="SNI 2025",
        klasifikasi="Pekerjaan Beton",
        sub_klasifikasi="Beton Struktural",
    )

    ahsp3 = AHSPReferensi.objects.create(
        kode_ahsp="C.003",
        nama_ahsp="Pekerjaan Jalan Aspal",
        satuan="M2",
        sumber="PUPR 2024",
        klasifikasi="Pekerjaan Jalan",
        sub_klasifikasi="Perkerasan Aspal",
    )

    # Create rincian for ahsp1 (mixed categories)
    RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori="TK",
        kode_item="TK.001",
        uraian_item="Pekerja",
        satuan_item="Orang",
        koefisien=0.5,
    )
    RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori="BHN",
        kode_item="BHN.001",
        uraian_item="Material A",
        satuan_item="Kg",
        koefisien=2.0,
    )
    RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori="ALT",
        kode_item="ALT.001",
        uraian_item="Excavator",
        satuan_item="Jam",
        koefisien=0.0,  # Zero coefficient (anomaly)
    )

    # Create rincian for ahsp2 (mostly BHN with anomaly)
    RincianReferensi.objects.create(
        ahsp=ahsp2,
        kategori="BHN",
        kode_item="BHN.002",
        uraian_item="Semen",
        satuan_item="Kg",
        koefisien=350.0,
    )
    RincianReferensi.objects.create(
        ahsp=ahsp2,
        kategori="BHN",
        kode_item="BHN.003",
        uraian_item="Pasir",
        satuan_item="",  # Missing unit (empty string anomaly)
        koefisien=0.7,
    )

    # Create rincian for ahsp3 (TK only)
    RincianReferensi.objects.create(
        ahsp=ahsp3,
        kategori="TK",
        kode_item="TK.002",
        uraian_item="Mandor",
        satuan_item="Orang",
        koefisien=0.1,
    )

    # Refresh materialized view for fast queries
    with connection.cursor() as cursor:
        cursor.execute("REFRESH MATERIALIZED VIEW referensi_ahsp_stats")

    return {
        'ahsp1': ahsp1,
        'ahsp2': ahsp2,
        'ahsp3': ahsp3,
    }


class TestAHSPRepositoryBasics:
    """Test basic repository methods."""

    def test_base_queryset(self, sample_ahsp_data):
        """Test base_queryset returns all AHSP records."""
        queryset = AHSPRepository.base_queryset()
        assert queryset.count() == 3
        assert queryset.model == AHSPReferensi

    def test_base_queryset_is_queryset(self):
        """Test base_queryset returns a QuerySet."""
        result = AHSPRepository.base_queryset()
        from django.db.models import QuerySet
        assert isinstance(result, QuerySet)


class TestAHSPRepositoryCategoryCounts:
    """Test category counting methods."""

    def test_get_with_category_counts_old_method(self, sample_ahsp_data):
        """Test old aggregation method returns correct counts."""
        result = AHSPRepository.get_with_category_counts()

        # Check first AHSP (3 rincian: 1 TK, 1 BHN, 1 ALT)
        ahsp1 = result.get(kode_ahsp="A.001")
        assert ahsp1.rincian_total == 3
        assert ahsp1.tk_count == 1
        assert ahsp1.bhn_count == 1
        assert ahsp1.alt_count == 1
        assert ahsp1.lain_count == 0
        assert ahsp1.zero_coef_count == 1  # ALT with koefisien=0
        assert ahsp1.missing_unit_count == 0

    def test_get_with_category_counts_fast_method(self, sample_ahsp_data):
        """Test materialized view method returns correct counts."""
        result = AHSPRepository.get_with_category_counts_fast()

        # Check first AHSP stats
        stat1 = result.get(kode_ahsp="A.001")
        assert stat1.rincian_total == 3
        assert stat1.tk_count == 1
        assert stat1.bhn_count == 1
        assert stat1.alt_count == 1
        assert stat1.lain_count == 0
        assert stat1.zero_coef_count == 1
        assert stat1.missing_unit_count == 0

    def test_category_counts_methods_match(self, sample_ahsp_data):
        """Test old and new methods return same counts."""
        old_result = AHSPRepository.get_with_category_counts()
        fast_result = AHSPRepository.get_with_category_counts_fast()

        assert old_result.count() == fast_result.count()

        # Compare counts for each AHSP
        for kode in ["A.001", "B.002", "C.003"]:
            old_ahsp = old_result.get(kode_ahsp=kode)
            fast_stat = fast_result.get(kode_ahsp=kode)

            assert old_ahsp.rincian_total == fast_stat.rincian_total
            assert old_ahsp.tk_count == fast_stat.tk_count
            assert old_ahsp.bhn_count == fast_stat.bhn_count
            assert old_ahsp.alt_count == fast_stat.alt_count


class TestAHSPRepositorySearch:
    """Test search functionality."""

    def test_filter_by_search_with_keyword(self, sample_ahsp_data):
        """Test search returns matching results."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_search(queryset, "beton")

        assert result.count() == 1
        assert result.first().kode_ahsp == "B.002"

    def test_filter_by_search_empty_keyword(self, sample_ahsp_data):
        """Test search with empty keyword returns all."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_search(queryset, "")

        assert result.count() == 3

    def test_filter_by_search_no_matches(self, sample_ahsp_data):
        """Test search with no matches returns empty."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_search(queryset, "zzznonexistent")

        assert result.count() == 0

    def test_filter_by_search_ranking(self, sample_ahsp_data):
        """Test search results are ranked by relevance."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_search(queryset, "pekerjaan")

        # All 3 records have "pekerjaan" in nama_ahsp
        assert result.count() == 3

        # Results should have search_rank attribute
        first = result.first()
        assert hasattr(first, 'search_rank')
        assert first.search_rank is not None


class TestAHSPRepositoryMetadataFilters:
    """Test metadata filtering methods."""

    def test_filter_by_metadata_sumber(self, sample_ahsp_data):
        """Test filtering by sumber."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_metadata(queryset, sumber="SNI 2025")

        assert result.count() == 2
        assert set(result.values_list('kode_ahsp', flat=True)) == {"A.001", "B.002"}

    def test_filter_by_metadata_klasifikasi(self, sample_ahsp_data):
        """Test filtering by klasifikasi."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_metadata(queryset, klasifikasi="Pekerjaan Beton")

        assert result.count() == 1
        assert result.first().kode_ahsp == "B.002"

    def test_filter_by_metadata_both(self, sample_ahsp_data):
        """Test filtering by sumber and klasifikasi together."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_metadata(
            queryset,
            sumber="SNI 2025",
            klasifikasi="Pekerjaan Beton"
        )

        assert result.count() == 1
        assert result.first().kode_ahsp == "B.002"

    def test_filter_by_metadata_empty(self, sample_ahsp_data):
        """Test filtering with empty params returns all."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_metadata(queryset, sumber="", klasifikasi="")

        assert result.count() == 3


class TestAHSPRepositoryKategoriFilter:
    """Test kategori filtering."""

    def test_filter_by_kategori_tk(self, sample_ahsp_data):
        """Test filtering by TK kategori."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_kategori(queryset, "TK")

        # ahsp1 and ahsp3 have TK rincian
        assert result.count() == 2
        assert set(result.values_list('kode_ahsp', flat=True)) == {"A.001", "C.003"}

    def test_filter_by_kategori_bhn(self, sample_ahsp_data):
        """Test filtering by BHN kategori."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_kategori(queryset, "BHN")

        # ahsp1 and ahsp2 have BHN rincian
        assert result.count() == 2
        assert set(result.values_list('kode_ahsp', flat=True)) == {"A.001", "B.002"}

    def test_filter_by_kategori_alt(self, sample_ahsp_data):
        """Test filtering by ALT kategori."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_kategori(queryset, "ALT")

        # Only ahsp1 has ALT rincian
        assert result.count() == 1
        assert result.first().kode_ahsp == "A.001"

    def test_filter_by_kategori_invalid(self, sample_ahsp_data):
        """Test filtering by invalid kategori returns all."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_kategori(queryset, "INVALID")

        assert result.count() == 3

    def test_filter_by_kategori_empty(self, sample_ahsp_data):
        """Test filtering with empty kategori returns all."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_kategori(queryset, "")

        assert result.count() == 3


class TestAHSPRepositoryAnomalyFilter:
    """Test anomaly filtering."""

    def test_filter_by_anomaly_zero_coef(self, sample_ahsp_data):
        """Test filtering by zero coefficient anomaly."""
        # Need to use category counts queryset for anomaly filtering
        queryset = AHSPRepository.get_with_category_counts()
        result = AHSPRepository.filter_by_anomaly(queryset, "zero")

        # Only ahsp1 has zero coefficient
        assert result.count() == 1
        assert result.first().kode_ahsp == "A.001"

    def test_filter_by_anomaly_missing_unit(self, sample_ahsp_data):
        """Test filtering by missing unit anomaly."""
        queryset = AHSPRepository.get_with_category_counts()
        result = AHSPRepository.filter_by_anomaly(queryset, "missing_unit")

        # Only ahsp2 has missing unit
        assert result.count() == 1
        assert result.first().kode_ahsp == "B.002"

    def test_filter_by_anomaly_any(self, sample_ahsp_data):
        """Test filtering by any anomaly."""
        queryset = AHSPRepository.get_with_category_counts()
        result = AHSPRepository.filter_by_anomaly(queryset, "any")

        # ahsp1 (zero coef) and ahsp2 (missing unit) have anomalies
        assert result.count() == 2
        assert set(result.values_list('kode_ahsp', flat=True)) == {"A.001", "B.002"}

    def test_filter_by_anomaly_invalid(self, sample_ahsp_data):
        """Test filtering by invalid anomaly type returns all."""
        queryset = AHSPRepository.get_with_category_counts()
        result = AHSPRepository.filter_by_anomaly(queryset, "invalid")

        assert result.count() == 3


class TestAHSPRepositoryChaining:
    """Test method chaining and combined filters."""

    def test_chain_search_and_metadata(self, sample_ahsp_data):
        """Test chaining search and metadata filters."""
        queryset = AHSPRepository.base_queryset()
        queryset = AHSPRepository.filter_by_search(queryset, "pekerjaan")
        result = AHSPRepository.filter_by_metadata(queryset, sumber="SNI 2025")

        # Should return 2 AHSP with "pekerjaan" and sumber="SNI 2025"
        assert result.count() == 2

    def test_chain_metadata_and_kategori(self, sample_ahsp_data):
        """Test chaining metadata and kategori filters."""
        queryset = AHSPRepository.base_queryset()
        queryset = AHSPRepository.filter_by_metadata(queryset, sumber="SNI 2025")
        result = AHSPRepository.filter_by_kategori(queryset, "BHN")

        # Should return ahsp1 and ahsp2 (both SNI 2025 with BHN)
        assert result.count() == 2

    def test_complex_chain(self, sample_ahsp_data):
        """Test complex chain of multiple filters."""
        queryset = AHSPRepository.base_queryset()
        queryset = AHSPRepository.filter_by_search(queryset, "pekerjaan")
        queryset = AHSPRepository.filter_by_metadata(queryset, sumber="SNI 2025")
        result = AHSPRepository.filter_by_kategori(queryset, "TK")

        # Should return only ahsp1 (SNI 2025, has TK, contains "pekerjaan")
        assert result.count() == 1
        assert result.first().kode_ahsp == "A.001"


class TestAHSPRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_database(self, db):
        """Test repository methods with empty database."""
        queryset = AHSPRepository.base_queryset()
        assert queryset.count() == 0

        result = AHSPRepository.filter_by_search(queryset, "test")
        assert result.count() == 0

    def test_search_special_characters(self, sample_ahsp_data):
        """Test search with special characters."""
        queryset = AHSPRepository.base_queryset()
        # Search with dash
        result = AHSPRepository.filter_by_search(queryset, "K-225")

        assert result.count() == 1
        assert result.first().kode_ahsp == "B.002"

    def test_none_keyword(self, sample_ahsp_data):
        """Test search with None keyword."""
        queryset = AHSPRepository.base_queryset()
        result = AHSPRepository.filter_by_search(queryset, None)

        # Should return all (no filtering)
        assert result.count() == 3
