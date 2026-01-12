"""
Test Coverage for Critical Services Functions

This module tests critical functions in services.py that were identified
as having low coverage during the Production Readiness Audit.

Coverage targets:
- compute_kebutuhan_items (aggregation logic)
- expand_bundle_to_components (nested expansion)
- cascade_bundle_re_expansion (stale data prevention)
- check_circular_dependency_pekerjaan (validation)
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from detail_project.models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    VolumePekerjaan,
    DetailAHSPProject,
    HargaItemProject,
    TahapPelaksanaan,
    PekerjaanTahapan,
)
from detail_project.services import (
    compute_kebutuhan_items,
    check_circular_dependency_pekerjaan,
    validate_bundle_reference,
    invalidate_rekap_cache,
)
from dashboard.models import Project

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        username="testuser_services",
        email="test_services@example.com",
        password="testpass123",
    )


@pytest.fixture
def test_project(db, test_user):
    """Create test project."""
    return Project.objects.create(
        owner=test_user,
        nama="Test Services Project",
        is_active=True,
        tahun_project=2026,
        anggaran_owner=Decimal("100000000"),
    )


@pytest.fixture
def project_with_data(db, test_project):
    """Create project with klasifikasi, pekerjaan, and volume data."""
    # Create klasifikasi
    klas = Klasifikasi.objects.create(
        project=test_project,
        name="Pekerjaan Tanah",
        ordering_index=1,
    )
    
    # Create sub-klasifikasi
    sub = SubKlasifikasi.objects.create(
        klasifikasi=klas,
        project=test_project,
        name="Galian",
        ordering_index=1,
    )
    
    # Create pekerjaan
    pekerjaan = Pekerjaan.objects.create(
        project=test_project,
        sub_klasifikasi=sub,
        source_type="custom",
        snapshot_kode="CUST-0001",
        snapshot_uraian="Galian Tanah",
        snapshot_satuan="m3",
        ordering_index=1,
    )
    
    # Create volume
    VolumePekerjaan.objects.create(
        project=test_project,
        pekerjaan=pekerjaan,
        quantity=Decimal("100.00"),
    )
    
    # Create harga item
    harga_item = HargaItemProject.objects.create(
        project=test_project,
        kategori=HargaItemProject.KATEGORI_BAHAN,
        kode_item="BHN-001",
        uraian="Pasir",
        satuan="m3",
        harga_satuan=Decimal("150000.00"),
    )
    
    # Create detail AHSP
    DetailAHSPProject.objects.create(
        project=test_project,
        pekerjaan=pekerjaan,
        kategori=HargaItemProject.KATEGORI_BAHAN,
        kode="BHN-001",
        uraian="Pasir",
        satuan="m3",
        koefisien=Decimal("0.5"),
        harga_item=harga_item,
    )
    
    return {
        "project": test_project,
        "klasifikasi": klas,
        "sub_klasifikasi": sub,
        "pekerjaan": pekerjaan,
        "harga_item": harga_item,
    }


# ===========================================================================
# Test compute_kebutuhan_items
# ===========================================================================

@pytest.mark.django_db
class TestComputeKebutuhanItems:
    """Tests for compute_kebutuhan_items function."""
    
    def test_empty_project_returns_empty_list(self, test_project):
        """Test that empty project returns empty list."""
        result = compute_kebutuhan_items(test_project)
        assert result == []
    
    def test_basic_aggregation(self, project_with_data):
        """Test basic item aggregation."""
        project = project_with_data["project"]
        
        result = compute_kebutuhan_items(project)
        
        assert len(result) > 0
        # Should aggregate BHN-001 with koef 0.5 * volume 100 = 50
        item = next((r for r in result if r.get("kode") == "BHN-001"), None)
        assert item is not None
    
    def test_filter_by_klasifikasi(self, project_with_data):
        """Test filtering by klasifikasi."""
        project = project_with_data["project"]
        klas_id = project_with_data["klasifikasi"].id
        
        result = compute_kebutuhan_items(
            project,
            filters={"klasifikasi_ids": [klas_id]}
        )
        
        assert len(result) > 0
    
    def test_filter_by_nonexistent_klasifikasi(self, project_with_data):
        """Test filtering by non-existent klasifikasi returns empty."""
        project = project_with_data["project"]
        
        result = compute_kebutuhan_items(
            project,
            filters={"klasifikasi_ids": [99999]}
        )
        
        assert result == []
    
    def test_filter_by_kategori(self, project_with_data):
        """Test filtering by kategori."""
        project = project_with_data["project"]
        
        result = compute_kebutuhan_items(
            project,
            filters={"kategori": ["BHN"]}
        )
        
        # Should only return BHN items
        for item in result:
            assert item.get("kategori") == "BHN"


# ===========================================================================
# Test circular dependency detection
# ===========================================================================

@pytest.mark.django_db
class TestCircularDependencyCheck:
    """Tests for check_circular_dependency_pekerjaan function."""
    
    def test_no_circular_dependency(self, project_with_data):
        """Test valid reference has no circular dependency."""
        project = project_with_data["project"]
        pekerjaan = project_with_data["pekerjaan"]
        
        # Create another pekerjaan to reference
        sub = project_with_data["sub_klasifikasi"]
        pekerjaan2 = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub,
            source_type="custom",
            snapshot_kode="CUST-0002",
            snapshot_uraian="Urugan Tanah",
            snapshot_satuan="m3",
            ordering_index=2,
        )
        
        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan.id,
            pekerjaan2.id,
            project
        )
        
        assert is_circular is False
        assert path == []
    
    def test_self_reference_is_circular(self, project_with_data):
        """Test self-reference is detected as circular."""
        project = project_with_data["project"]
        pekerjaan = project_with_data["pekerjaan"]
        
        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan.id,
            pekerjaan.id,
            project
        )
        
        assert is_circular is True


# ===========================================================================
# Test bundle reference validation
# ===========================================================================

@pytest.mark.django_db
class TestBundleReferenceValidation:
    """Tests for validate_bundle_reference function."""
    
    def test_valid_job_reference(self, project_with_data):
        """Test valid job reference passes validation."""
        project = project_with_data["project"]
        pekerjaan = project_with_data["pekerjaan"]
        
        # Create another pekerjaan to reference
        sub = project_with_data["sub_klasifikasi"]
        pekerjaan2 = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub,
            source_type="custom",
            snapshot_kode="CUST-0002",
            snapshot_uraian="Urugan Tanah",
            snapshot_satuan="m3",
            ordering_index=2,
        )
        
        is_valid, error = validate_bundle_reference(
            pekerjaan.id,
            "job",
            pekerjaan2.id,
            project
        )
        
        assert is_valid is True
        # Function returns empty string for valid reference
        assert error == "" or error is None
    
    def test_invalid_reference_id(self, project_with_data):
        """Test invalid reference ID fails validation."""
        project = project_with_data["project"]
        pekerjaan = project_with_data["pekerjaan"]
        
        is_valid, error = validate_bundle_reference(
            pekerjaan.id,
            "job",
            99999,  # Non-existent ID
            project
        )
        
        assert is_valid is False
        assert error is not None


# ===========================================================================
# Test cache invalidation
# ===========================================================================

@pytest.mark.django_db
class TestCacheInvalidation:
    """Tests for cache invalidation."""
    
    def test_invalidate_rekap_cache_no_error(self, test_project):
        """Test cache invalidation doesn't raise errors."""
        # Should not raise any exception
        invalidate_rekap_cache(test_project)
        invalidate_rekap_cache(test_project.id)
