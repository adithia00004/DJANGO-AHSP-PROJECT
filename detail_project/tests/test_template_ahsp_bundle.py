# detail_project/tests/test_template_ahsp_bundle.py
"""
Comprehensive tests for Pekerjaan Gabungan (Bundle) feature in Template AHSP.

Tests cover:
1. Circular dependency detection (self-reference, 2-level, 3-level)
2. Recursive bundle expansion
3. API endpoints (GET/SAVE) with ref_kind='job'
4. Rekap computation with bundle pekerjaan
5. Validation functions
6. Max depth limit protection
"""
import pytest
import json
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, HargaItemProject, VolumePekerjaan
)
from detail_project.services import (
    check_circular_dependency_pekerjaan,
    validate_bundle_reference,
    expand_bundle_recursive,
    compute_kebutuhan_items,
)

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def setup_bundle_test(db, user, project, sub_klas):
    """
    Setup data untuk bundle tests.
    Creates:
    - job_a: CUSTOM pekerjaan yang akan reference job_b
    - job_b: CUSTOM pekerjaan yang punya detail TK/BHN
    - job_c: CUSTOM pekerjaan untuk multi-level testing
    """
    # Job A - akan jadi parent bundle
    job_a = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="A001",
        snapshot_uraian="Bundle Job A",
        snapshot_satuan="LS",
        ordering_index=1,
    )

    # Job B - punya detail TK + BHN
    job_b = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="B002",
        snapshot_uraian="Detail Job B",
        snapshot_satuan="LS",
        ordering_index=2,
    )

    # Job C - untuk multi-level testing
    job_c = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="C003",
        snapshot_uraian="Detail Job C",
        snapshot_satuan="LS",
        ordering_index=3,
    )

    # Create HargaItemProject for details
    harga_tk = HargaItemProject.objects.create(
        project=project,
        kategori="TK",
        kode_item="TK.001",
        uraian="Pekerja",
        satuan="OH",
        harga_satuan=Decimal("150000"),
    )

    harga_bhn = HargaItemProject.objects.create(
        project=project,
        kategori="BHN",
        kode_item="BHN.001",
        uraian="Semen",
        satuan="Zak",
        harga_satuan=Decimal("85000"),
    )

    harga_alt = HargaItemProject.objects.create(
        project=project,
        kategori="ALT",
        kode_item="ALT.001",
        uraian="Excavator",
        satuan="Jam",
        harga_satuan=Decimal("500000"),
    )

    # Add details to job_b (TK + BHN)
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=job_b,
        harga_item=harga_tk,
        kategori="TK",
        kode="TK.001",
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("2.500000"),  # 2.5 OH
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=job_b,
        harga_item=harga_bhn,
        kategori="BHN",
        kode="BHN.001",
        uraian="Semen",
        satuan="Zak",
        koefisien=Decimal("10.000000"),  # 10 Zak
    )

    # Add details to job_c (ALT)
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=job_c,
        harga_item=harga_alt,
        kategori="ALT",
        kode="ALT.001",
        uraian="Excavator",
        satuan="Jam",
        koefisien=Decimal("1.500000"),  # 1.5 Jam
    )

    return {
        'job_a': job_a,
        'job_b': job_b,
        'job_c': job_c,
        'harga_tk': harga_tk,
        'harga_bhn': harga_bhn,
        'harga_alt': harga_alt,
    }


# ============================================================================
# TESTS: Circular Dependency Detection
# ============================================================================

@pytest.mark.django_db
class TestCircularDependencyDetection:
    """Test circular dependency detection using BFS algorithm."""

    def test_self_reference_detected(self, project, setup_bundle_test):
        """Test that self-reference (A -> A) is detected."""
        job_a = setup_bundle_test['job_a']

        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan_id=job_a.id,
            ref_pekerjaan_id=job_a.id,
            project=project
        )

        assert is_circular is True
        assert job_a.id in path
        assert len(path) == 2  # [A, A]

    def test_two_level_circular_detected(self, project, setup_bundle_test):
        """Test that 2-level circular (A -> B -> A) is detected."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Create LAIN detail in job_a that references job_b
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.001",
            uraian="Bundle Reference",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.001",
            uraian="Bundle Reference",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,  # A -> B
        )

        # Now check if B -> A creates circular
        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan_id=job_b.id,
            ref_pekerjaan_id=job_a.id,  # B -> A
            project=project
        )

        assert is_circular is True
        assert job_a.id in path
        assert job_b.id in path

    def test_three_level_circular_detected(self, project, setup_bundle_test):
        """Test that 3-level circular (A -> B -> C -> A) is detected."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']
        job_c = setup_bundle_test['job_c']

        # Setup: A -> B -> C
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.BUNDLE",
            uraian="Bundle Reference",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        # A -> B
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.001",
            uraian="A to B",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,
        )

        # B -> C
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_b,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.002",
            uraian="B to C",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_c,
        )

        # Now check if C -> A creates circular
        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan_id=job_c.id,
            ref_pekerjaan_id=job_a.id,  # C -> A
            project=project
        )

        assert is_circular is True
        # Path should contain all three jobs
        assert job_a.id in path

    def test_no_circular_in_valid_chain(self, project, setup_bundle_test):
        """Test that valid chain (A -> B -> C) without cycle is not flagged."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']
        job_c = setup_bundle_test['job_c']

        # A -> B (already exists from previous tests, so skip if needed)
        # Check B -> C (no circular)
        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan_id=job_b.id,
            ref_pekerjaan_id=job_c.id,  # B -> C
            project=project
        )

        assert is_circular is False
        assert path == []


# ============================================================================
# TESTS: Validation Functions
# ============================================================================

@pytest.mark.django_db
class TestBundleValidation:
    """Test validate_bundle_reference function."""

    def test_validate_self_reference_error(self, project, setup_bundle_test):
        """Test validation rejects self-reference."""
        job_a = setup_bundle_test['job_a']

        is_valid, error_msg = validate_bundle_reference(
            pekerjaan_id=job_a.id,
            ref_kind='job',
            ref_id=job_a.id,
            project=project
        )

        assert is_valid is False
        assert "tidak boleh mereferensi diri sendiri" in error_msg

    def test_validate_circular_dependency_error(self, project, setup_bundle_test):
        """Test validation rejects circular dependency."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Create A -> B
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.VAL",
            uraian="Bundle",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.VAL",
            uraian="Bundle",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,
        )

        # Validate B -> A (circular)
        is_valid, error_msg = validate_bundle_reference(
            pekerjaan_id=job_b.id,
            ref_kind='job',
            ref_id=job_a.id,
            project=project
        )

        assert is_valid is False
        assert "Circular dependency detected" in error_msg

    def test_validate_nonexistent_pekerjaan_error(self, project, setup_bundle_test):
        """Test validation rejects nonexistent pekerjaan reference."""
        job_a = setup_bundle_test['job_a']

        is_valid, error_msg = validate_bundle_reference(
            pekerjaan_id=job_a.id,
            ref_kind='job',
            ref_id=99999,  # Non-existent ID
            project=project
        )

        assert is_valid is False
        assert "tidak ditemukan" in error_msg

    def test_validate_valid_reference(self, project, setup_bundle_test):
        """Test validation accepts valid reference."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        is_valid, error_msg = validate_bundle_reference(
            pekerjaan_id=job_a.id,
            ref_kind='job',
            ref_id=job_b.id,
            project=project
        )

        assert is_valid is True
        assert error_msg == ""


# ============================================================================
# TESTS: Recursive Bundle Expansion
# ============================================================================

@pytest.mark.django_db
class TestRecursiveBundleExpansion:
    """Test expand_bundle_recursive function."""

    def test_expand_single_level_bundle(self, project, setup_bundle_test):
        """Test expanding a bundle with direct TK/BHN items."""
        job_b = setup_bundle_test['job_b']

        # Create LAIN item that references job_b
        detail_dict = {
            'kategori': 'LAIN',
            'kode': 'LAIN.TEST',
            'uraian': 'Bundle Test',
            'satuan': 'LS',
            'koefisien': '2.000000',  # 2x multiplier
            'ref_pekerjaan_id': job_b.id,
            'ref_ahsp_id': None,
        }

        result = expand_bundle_recursive(
            detail_dict=detail_dict,
            base_koefisien=Decimal('1.0'),
            project=project,
            depth=0,
            visited=None
        )

        # Should return 2 items: TK.001 and BHN.001
        assert len(result) == 2

        # Check TK item
        tk_item = next((r for r in result if r[0] == 'TK'), None)
        assert tk_item is not None
        assert tk_item[1] == 'TK.001'  # kode
        assert tk_item[4] == Decimal('5.000000')  # koef: 2.5 * 2.0

        # Check BHN item
        bhn_item = next((r for r in result if r[0] == 'BHN'), None)
        assert bhn_item is not None
        assert bhn_item[1] == 'BHN.001'  # kode
        assert bhn_item[4] == Decimal('20.000000')  # koef: 10.0 * 2.0

    def test_expand_multi_level_bundle(self, project, setup_bundle_test):
        """Test expanding nested bundle (A -> B -> base items)."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Create LAIN in job_a that references job_b
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.MULTI",
            uraian="Multi-level Bundle",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.MULTI",
            uraian="Multi-level Bundle",
            satuan="LS",
            koefisien=Decimal("1.500000"),  # 1.5x
            ref_pekerjaan=job_b,
        )

        # Now expand job_a's LAIN item
        detail_dict = {
            'kategori': 'LAIN',
            'kode': 'LAIN.MULTI',
            'uraian': 'Multi-level Bundle',
            'satuan': 'LS',
            'koefisien': '1.500000',
            'ref_pekerjaan_id': job_b.id,
            'ref_ahsp_id': None,
        }

        result = expand_bundle_recursive(
            detail_dict=detail_dict,
            base_koefisien=Decimal('1.0'),
            project=project,
            depth=0,
            visited=None
        )

        # Should expand to job_b's items with multiplied koefisien
        assert len(result) == 2

        # TK: 2.5 * 1.5 = 3.75
        tk_item = next((r for r in result if r[0] == 'TK'), None)
        assert tk_item[4] == Decimal('3.750000')

        # BHN: 10.0 * 1.5 = 15.0
        bhn_item = next((r for r in result if r[0] == 'BHN'), None)
        assert bhn_item[4] == Decimal('15.000000')

    def test_expand_detects_circular_reference(self, project, setup_bundle_test):
        """Test that expansion raises error on circular reference."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Create A -> B
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.CIRC",
            uraian="Circular Bundle",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.A",
            uraian="A to B",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,
        )

        # Create B -> A (circular!)
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_b,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.B",
            uraian="B to A",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_a,
        )

        # Try to expand A -> should detect circular when it hits B -> A
        detail_dict = {
            'kategori': 'LAIN',
            'kode': 'LAIN.A',
            'uraian': 'A to B',
            'satuan': 'LS',
            'koefisien': '1.000000',
            'ref_pekerjaan_id': job_b.id,
            'ref_ahsp_id': None,
        }

        with pytest.raises(ValueError, match="Circular dependency"):
            expand_bundle_recursive(
                detail_dict=detail_dict,
                base_koefisien=Decimal('1.0'),
                project=project,
                depth=0,
                visited=None
            )

    def test_expand_max_depth_limit(self, project, setup_bundle_test):
        """Test that expansion raises error when max depth exceeded."""
        # This would require creating 11+ levels of nesting
        # For simplicity, we test with lower depth by mocking or creating chain
        # In real scenario, max depth is 10

        # Create a chain: A -> B -> C -> D -> E -> F -> G -> H -> I -> J -> K (11 levels)
        # For this test, we'll manually trigger depth check

        detail_dict = {
            'kategori': 'LAIN',
            'kode': 'LAIN.DEEP',
            'uraian': 'Deep Bundle',
            'satuan': 'LS',
            'koefisien': '1.000000',
            'ref_pekerjaan_id': setup_bundle_test['job_b'].id,
            'ref_ahsp_id': None,
        }

        # Call with depth = 11 (exceeds MAX_DEPTH = 10)
        with pytest.raises(ValueError, match="Maksimum kedalaman bundle"):
            expand_bundle_recursive(
                detail_dict=detail_dict,
                base_koefisien=Decimal('1.0'),
                project=project,
                depth=11,  # Exceeds limit
                visited=None
            )


# ============================================================================
# TESTS: API Endpoints
# ============================================================================

@pytest.mark.django_db
class TestBundleAPIEndpoints:
    """Test API endpoints with ref_kind='job' support."""

    def test_get_detail_includes_ref_pekerjaan_id(self, client_logged, project, setup_bundle_test):
        """Test GET endpoint returns ref_pekerjaan_id."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Add LAIN detail to job_a that references job_b
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.GET",
            uraian="Get Test",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.GET",
            uraian="Get Test",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,
        )

        # GET request
        url = reverse('detail_project:api_get_detail_ahsp_for_pekerjaan',
                      kwargs={'project_id': project.id, 'pekerjaan_id': job_a.id})
        resp = client_logged.get(url)

        assert resp.status_code == 200
        data = resp.json()

        # Find LAIN item
        lain_item = next((item for item in data['items'] if item['kategori'] == 'LAIN'), None)
        assert lain_item is not None
        assert lain_item['ref_pekerjaan_id'] == job_b.id

    def test_save_detail_with_ref_kind_job(self, client_logged, project, setup_bundle_test):
        """Test SAVE endpoint with ref_kind='job'."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Prepare payload with ref_kind='job'
        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.SAVE',
                    'uraian': 'Save Test Bundle',
                    'satuan': 'LS',
                    'koefisien': '1.500000',
                    'ref_kind': 'job',
                    'ref_id': job_b.id,
                }
            ]
        }

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan',
                      kwargs={'project_id': project.id, 'pekerjaan_id': job_a.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True

        # Verify database
        detail = DetailAHSPProject.objects.get(
            project=project,
            pekerjaan=job_a,
            kategori='LAIN',
            kode='LAIN.SAVE'
        )
        assert detail.ref_pekerjaan_id == job_b.id
        assert detail.ref_ahsp_id is None

    def test_save_detail_rejects_self_reference(self, client_logged, project, setup_bundle_test):
        """Test SAVE endpoint rejects self-reference."""
        job_a = setup_bundle_test['job_a']

        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.SELF',
                    'uraian': 'Self Reference',
                    'satuan': 'LS',
                    'koefisien': '1.000000',
                    'ref_kind': 'job',
                    'ref_id': job_a.id,  # Self-reference!
                }
            ]
        }

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan',
                      kwargs={'project_id': project.id, 'pekerjaan_id': job_a.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 400
        data = resp.json()
        assert data['ok'] is False
        assert any('tidak boleh mereferensi diri sendiri' in err.get('message', '')
                   for err in data.get('errors', []))

    def test_save_detail_rejects_circular_reference(self, client_logged, project, setup_bundle_test):
        """Test SAVE endpoint rejects circular dependency."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # First, create A -> B
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.CIRC",
            uraian="Circular",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.A2B",
            uraian="A to B",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,
        )

        # Now try to save B -> A (circular!)
        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.B2A',
                    'uraian': 'B to A',
                    'satuan': 'LS',
                    'koefisien': '1.000000',
                    'ref_kind': 'job',
                    'ref_id': job_a.id,
                }
            ]
        }

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan',
                      kwargs={'project_id': project.id, 'pekerjaan_id': job_b.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 400
        data = resp.json()
        assert data['ok'] is False
        assert any('Circular dependency detected' in err.get('message', '')
                   for err in data.get('errors', []))


# ============================================================================
# TESTS: Compute Kebutuhan Items (Rekap)
# ============================================================================

@pytest.mark.django_db
class TestRekapWithBundles:
    """Test compute_kebutuhan_items with bundle pekerjaan."""

    def test_rekap_expands_single_bundle(self, project, setup_bundle_test):
        """Test rekap correctly expands single-level bundle."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Add LAIN to job_a that references job_b
        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.REKAP",
            uraian="Rekap Bundle",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.REKAP",
            uraian="Rekap Bundle",
            satuan="LS",
            koefisien=Decimal("2.000000"),  # 2x multiplier
            ref_pekerjaan=job_b,
        )

        # Set volume for job_a
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=job_a,
            quantity=Decimal("5.000"),  # 5 unit
        )

        # Compute rekap
        result = compute_kebutuhan_items(
            project=project,
            filters=None,
            pekerjaan_ids=[job_a.id]
        )

        # Should have TK and BHN from job_b
        # TK: 2.5 (job_b koef) * 2.0 (LAIN koef) * 5.0 (volume) = 25.0
        # BHN: 10.0 * 2.0 * 5.0 = 100.0

        tk_key = ('TK', 'TK.001', 'Pekerja', 'OH')
        bhn_key = ('BHN', 'BHN.001', 'Semen', 'Zak')

        assert tk_key in result
        assert result[tk_key] == Decimal('25.000')

        assert bhn_key in result
        assert result[bhn_key] == Decimal('100.000')

    def test_rekap_expands_nested_bundle(self, project, setup_bundle_test):
        """Test rekap correctly expands multi-level nested bundle."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']
        job_c = setup_bundle_test['job_c']

        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.NEST",
            uraian="Nested Bundle",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        # A -> B (koef 2.0)
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.A2B",
            uraian="A to B",
            satuan="LS",
            koefisien=Decimal("2.000000"),
            ref_pekerjaan=job_b,
        )

        # B -> C (koef 3.0) via LAIN
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_b,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.B2C",
            uraian="B to C",
            satuan="LS",
            koefisien=Decimal("3.000000"),
            ref_pekerjaan=job_c,
        )

        # Volume for job_a
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=job_a,
            quantity=Decimal("1.000"),
        )

        # Compute rekap
        result = compute_kebutuhan_items(
            project=project,
            filters=None,
            pekerjaan_ids=[job_a.id]
        )

        # Should have:
        # - TK/BHN from job_b direct items
        # - ALT from job_c (via B -> C)
        # TK: 2.5 * 2.0 * 1.0 = 5.0
        # BHN: 10.0 * 2.0 * 1.0 = 20.0
        # ALT: 1.5 (job_c) * 3.0 (B->C) * 2.0 (A->B) * 1.0 (vol) = 9.0

        tk_key = ('TK', 'TK.001', 'Pekerja', 'OH')
        bhn_key = ('BHN', 'BHN.001', 'Semen', 'Zak')
        alt_key = ('ALT', 'ALT.001', 'Excavator', 'Jam')

        assert tk_key in result
        assert result[tk_key] == Decimal('5.000')

        assert bhn_key in result
        assert result[bhn_key] == Decimal('20.000')

        assert alt_key in result
        assert result[alt_key] == Decimal('9.000')

    def test_rekap_skips_circular_bundle(self, project, setup_bundle_test):
        """Test rekap skips bundle with circular dependency (logs error)."""
        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.CIRC2",
            uraian="Circular Bundle",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        # Create A -> B
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_a,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.A2B",
            uraian="A to B",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_b,
        )

        # Create B -> A (circular!) - this bypasses validation
        # (simulating corrupted data or race condition)
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=job_b,
            harga_item=harga_lain,
            kategori="LAIN",
            kode="LAIN.B2A",
            uraian="B to A",
            satuan="LS",
            koefisien=Decimal("1.000000"),
            ref_pekerjaan=job_a,
        )

        # Volume
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=job_a,
            quantity=Decimal("1.000"),
        )

        # Compute rekap - should NOT crash, just skip circular item
        result = compute_kebutuhan_items(
            project=project,
            filters=None,
            pekerjaan_ids=[job_a.id]
        )

        # Result should be empty or only have non-circular items
        # Since all items are circular, result should be empty
        assert len(result) == 0  # No items aggregated due to circular skip


# ============================================================================
# TESTS: Database Constraints
# ============================================================================

@pytest.mark.django_db
class TestDatabaseConstraints:
    """Test database constraints for bundle support."""

    def test_cannot_set_both_ref_ahsp_and_ref_pekerjaan(self, project, setup_bundle_test):
        """Test exclusive constraint: cannot set both ref_ahsp and ref_pekerjaan."""
        from referensi.models import AHSPReferensi
        from django.db import IntegrityError

        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']

        # Create AHSP reference
        ahsp = AHSPReferensi.objects.create(
            kode_ahsp="AHSP.001",
            nama_ahsp="AHSP Test",
            satuan="LS",
        )

        harga_lain = HargaItemProject.objects.create(
            project=project,
            kategori="LAIN",
            kode_item="LAIN.BOTH",
            uraian="Both Refs",
            satuan="LS",
            harga_satuan=Decimal("0"),
        )

        # Try to create with both refs - should fail
        with pytest.raises(IntegrityError):
            DetailAHSPProject.objects.create(
                project=project,
                pekerjaan=job_a,
                harga_item=harga_lain,
                kategori="LAIN",
                kode="LAIN.BOTH",
                uraian="Both Refs",
                satuan="LS",
                koefisien=Decimal("1.000000"),
                ref_ahsp=ahsp,
                ref_pekerjaan=job_b,  # Both set - should fail!
            )

    def test_non_lain_cannot_have_bundle_ref(self, project, setup_bundle_test):
        """Test constraint: only LAIN category can have bundle reference."""
        from django.db import IntegrityError

        job_a = setup_bundle_test['job_a']
        job_b = setup_bundle_test['job_b']
        harga_tk = setup_bundle_test['harga_tk']

        # Try to create TK with ref_pekerjaan - should fail
        with pytest.raises(IntegrityError):
            DetailAHSPProject.objects.create(
                project=project,
                pekerjaan=job_a,
                harga_item=harga_tk,
                kategori="TK",  # Not LAIN!
                kode="TK.BAD",
                uraian="Bad TK",
                satuan="OH",
                koefisien=Decimal("1.000000"),
                ref_pekerjaan=job_b,  # Should fail!
            )
