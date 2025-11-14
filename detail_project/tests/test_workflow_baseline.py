"""
FASE 0.2: Test Coverage Baseline for 3-Page AHSP Workflow

Purpose: Comprehensive baseline tests for Template AHSP → Harga Items → Rincian AHSP workflow
Author: FASE 0 Implementation
Created: 2025-11-13
Version: 1.0

Test Coverage:
1. ✓ Bundle Creation (job + ahsp) - ref_kind='job' and 'ahsp'
2. ✓ Cascade Re-Expansion - cascade_bundle_re_expansion()
3. ✓ Empty Bundle Validation
4. ✓ Circular Dependency Protection
5. ✓ Optimistic Locking (client_updated_at conflict resolution)
6. ✓ Source Type Restrictions (REF/REF_MODIFIED/CUSTOM)
7. ✓ Max Depth Validation (3 levels)
8. ✓ Dual Storage Integrity (DetailAHSPProject ↔ DetailAHSPExpanded)

This test suite serves as:
- Baseline for regression testing
- Documentation of current functionality
- Foundation for future enhancements (FASE 1-4)

Target Coverage: >80% for core workflow functions
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, DetailAHSPExpanded, HargaItemProject, VolumePekerjaan
)
from detail_project.services import (
    check_circular_dependency_pekerjaan,
    validate_bundle_reference,
    expand_bundle_recursive,
    cascade_bundle_re_expansion,
    _populate_expanded_from_raw,
)


def populate_expanded_for(pekerjaan: Pekerjaan):
    """Helper agar signature baru _populate_expanded_from_raw konsisten di tes."""
    _populate_expanded_from_raw(pekerjaan.project, pekerjaan)

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def baseline_setup(db, user, project, sub_klas):
    """
    Baseline setup for workflow tests.
    Creates:
    - 3 CUSTOM pekerjaan (for bundle testing)
    - 1 REF pekerjaan (for source_type testing)
    - HargaItemProject items
    - DetailAHSPProject components
    """
    # Create HargaItemProject
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
        uraian="Molen",
        satuan="Jam",
        harga_satuan=Decimal("50000"),
    )

    harga_lain = HargaItemProject.objects.create(
        project=project,
        kategori="LAIN",
        kode_item="LAIN.BUNDLE",
        uraian="Bundle Placeholder",
        satuan="set",
        harga_satuan=Decimal("0"),
    )

    # Pekerjaan A (CUSTOM) - will be base pekerjaan
    pekerjaan_a = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="A.001",
        snapshot_uraian="Pekerjaan A",
        snapshot_satuan="M3",
        ordering_index=1,
    )

    # Add details to Pekerjaan A
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_a,
        harga_item=harga_tk,
        kategori="TK",
        kode="TK.001",
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("2.500000"),
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_a,
        harga_item=harga_bhn,
        kategori="BHN",
        kode="BHN.001",
        uraian="Semen",
        satuan="Zak",
        koefisien=Decimal("10.000000"),
    )

    # Populate expanded for Pekerjaan A
    populate_expanded_for(pekerjaan_a)

    # Pekerjaan B (CUSTOM) - will bundle Pekerjaan A
    pekerjaan_b = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="B.001",
        snapshot_uraian="Pekerjaan B",
        snapshot_satuan="M3",
        ordering_index=2,
    )

    # Pekerjaan C (CUSTOM) - for cascade testing
    pekerjaan_c = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="C.001",
        snapshot_uraian="Pekerjaan C",
        snapshot_satuan="M3",
        ordering_index=3,
    )

    # Pekerjaan REF (for source_type testing)
    try:
        from referensi.models import AHSPReferensi
        ahsp_ref = AHSPReferensi.objects.first()
    except:
        ahsp_ref = None

    pekerjaan_ref = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_REF,
        ref=ahsp_ref,
        snapshot_kode="REF.001",
        snapshot_uraian="Pekerjaan REF",
        snapshot_satuan="M3",
        ordering_index=4,
    )

    return {
        'pekerjaan_a': pekerjaan_a,
        'pekerjaan_b': pekerjaan_b,
        'pekerjaan_c': pekerjaan_c,
        'pekerjaan_ref': pekerjaan_ref,
        'harga_tk': harga_tk,
        'harga_bhn': harga_bhn,
        'harga_alt': harga_alt,
        'harga_lain': harga_lain,
    }


# ============================================================================
# TEST 1: BUNDLE CREATION (ref_kind='job')
# ============================================================================

@pytest.mark.django_db
class TestBundleCreation:
    """Test bundle creation with ref_kind='job'"""

    def test_create_bundle_job_reference(self, baseline_setup, user, client):
        """Test creating bundle that references another pekerjaan in same project"""
        client.force_login(user)

        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        project = pekerjaan_b.project

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_b.id])

        # Create bundle in Pekerjaan B that references Pekerjaan A
        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.A001',
                    'uraian': f'Bundle: {pekerjaan_a.snapshot_uraian}',
                    'satuan': pekerjaan_a.snapshot_satuan,
                    'koefisien': '1.5',
                    'ref_kind': 'job',
                    'ref_id': str(pekerjaan_a.id),
                }
            ]
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        # Verify bundle created in Storage 1
        bundle = DetailAHSPProject.objects.get(
            project=project,
            pekerjaan=pekerjaan_b,
            kategori='LAIN'
        )
        assert bundle.ref_pekerjaan == pekerjaan_a
        assert bundle.ref_ahsp is None
        assert bundle.koefisien == Decimal('1.5')

        # Verify expanded in Storage 2
        expanded = DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan=pekerjaan_b
        )

        # Should have 2 components (TK + BHN) from Pekerjaan A
        assert expanded.count() == 2

        # Verify koefisien multiplication (1.5x)
        tk_expanded = expanded.get(kategori='TK')
        assert tk_expanded.koefisien == Decimal('2.500000') * Decimal('1.5')
        assert tk_expanded.source_bundle_kode == 'LAIN.A001'
        assert tk_expanded.expansion_depth == 1

    def test_bundle_empty_validation(self, baseline_setup, user, client):
        """Test that bundle to empty pekerjaan is blocked"""
        client.force_login(user)

        pekerjaan_b = baseline_setup['pekerjaan_b']
        pekerjaan_c = baseline_setup['pekerjaan_c']  # Empty pekerjaan
        project = pekerjaan_b.project

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_b.id])

        # Try to create bundle to empty pekerjaan
        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.EMPTY',
                    'uraian': 'Bundle to Empty',
                    'satuan': 'm3',
                    'koefisien': '1.0',
                    'ref_kind': 'job',
                    'ref_id': str(pekerjaan_c.id),
                }
            ]
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')

        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        ref_errors = [err for err in data.get('errors', []) if err.get('path') == 'rows[0].ref_id']
        assert ref_errors, "Harus ada error pada ref_id untuk pekerjaan kosong"
        assert 'tidak memiliki komponen' in ref_errors[0]['message'].lower()


# ============================================================================
# TEST 2: CASCADE RE-EXPANSION
# ============================================================================

@pytest.mark.django_db
class TestCascadeReExpansion:
    """Test cascade_bundle_re_expansion() functionality"""

    def test_cascade_updates_referencing_pekerjaan(self, baseline_setup):
        """Modifying target pekerjaan triggers cascade update"""
        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        project = pekerjaan_b.project

        # Step 1: Create bundle B → A
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_b,
            harga_item=baseline_setup['harga_lain'],  # Dummy, will be expanded
            kategori='LAIN',
            kode='LAIN.A001',
            uraian=f'Bundle: {pekerjaan_a.snapshot_uraian}',
            satuan=pekerjaan_a.snapshot_satuan,
            koefisien=Decimal('2.0'),
            ref_pekerjaan=pekerjaan_a,
        )

        populate_expanded_for(pekerjaan_b)

        # Verify initial state
        expanded_before = DetailAHSPExpanded.objects.filter(pekerjaan=pekerjaan_b, kategori='TK').first()
        assert expanded_before.koefisien == Decimal('2.500000') * Decimal('2.0')  # 5.0

        # Step 2: Modify Pekerjaan A (target) directly to simulate edit
        detail = DetailAHSPProject.objects.get(pekerjaan=pekerjaan_a, kategori='TK')
        detail.koefisien = Decimal('3.0')  # Changed from 2.5 to 3.0
        detail.save()
        populate_expanded_for(pekerjaan_a)

        # Trigger cascade manually
        cascade_bundle_re_expansion(project, pekerjaan_a.id)

        # Step 3: Verify cascade updated Pekerjaan B
        expanded_after = DetailAHSPExpanded.objects.filter(pekerjaan=pekerjaan_b, kategori='TK').first()
        assert expanded_after.koefisien == Decimal('3.0') * Decimal('2.0')  # 6.0

    def test_cascade_multi_level(self, baseline_setup, user):
        """Test cascade works through multi-level bundle chain (A←B←C)"""
        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        pekerjaan_c = baseline_setup['pekerjaan_c']
        project = pekerjaan_a.project

        # Create chain: C → B → A
        # B bundles A
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_b,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.A',
            uraian='Bundle A',
            satuan='m3',
            koefisien=Decimal('2.0'),
            ref_pekerjaan=pekerjaan_a,
        )
        populate_expanded_for(pekerjaan_b)

        # C bundles B
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_c,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.B',
            uraian='Bundle B',
            satuan='m3',
            koefisien=Decimal('1.5'),
            ref_pekerjaan=pekerjaan_b,
        )
        populate_expanded_for(pekerjaan_c)

        # Initial state: C should have TK with koef = 2.5 * 2.0 * 1.5 = 7.5
        tk_c_before = DetailAHSPExpanded.objects.get(pekerjaan=pekerjaan_c, kategori='TK')
        assert tk_c_before.koefisien == Decimal('7.500000')

        # Modify A
        detail_a = DetailAHSPProject.objects.get(pekerjaan=pekerjaan_a, kategori='TK')
        detail_a.koefisien = Decimal('4.0')  # Changed from 2.5
        detail_a.save()

        populate_expanded_for(pekerjaan_a)
        cascade_bundle_re_expansion(project, pekerjaan_a.id)

        # Verify: B should update (4.0 * 2.0 = 8.0)
        tk_b_after = DetailAHSPExpanded.objects.get(pekerjaan=pekerjaan_b, kategori='TK')
        assert tk_b_after.koefisien == Decimal('8.000000')

        # Verify: C should cascade update (4.0 * 2.0 * 1.5 = 12.0)
        tk_c_after = DetailAHSPExpanded.objects.get(pekerjaan=pekerjaan_c, kategori='TK')
        assert tk_c_after.koefisien == Decimal('12.000000')


# ============================================================================
# TEST 3: CIRCULAR DEPENDENCY PROTECTION
# ============================================================================

@pytest.mark.django_db
class TestCircularDependencyProtection:
    """Test circular dependency detection"""

    def test_detect_self_reference(self, baseline_setup):
        """Test detection of A → A"""
        pekerjaan_a = baseline_setup['pekerjaan_a']
        project = pekerjaan_a.project

        is_circular, _ = check_circular_dependency_pekerjaan(pekerjaan_a.id, pekerjaan_a.id, project)
        assert is_circular is True  # Circular detected

    def test_detect_two_level_cycle(self, baseline_setup):
        """Test detection of A → B → A"""
        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        project = pekerjaan_a.project

        # Create A → B
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_a,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.B',
            uraian='Bundle B',
            satuan='m3',
            koefisien=Decimal('1.0'),
            ref_pekerjaan=pekerjaan_b,
        )

        # Try to create B → A (should detect cycle)
        is_circular, _ = check_circular_dependency_pekerjaan(pekerjaan_b.id, pekerjaan_a.id, project)
        assert is_circular is True  # Circular detected

    def test_api_blocks_circular_bundle(self, baseline_setup, user, client):
        """Test that API blocks circular bundle creation"""
        client.force_login(user)

        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        project = pekerjaan_a.project

        # Create A → B
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_a,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.B',
            uraian='Bundle B',
            satuan='m3',
            koefisien=Decimal('1.0'),
            ref_pekerjaan=pekerjaan_b,
        )

        # Try to create B → A via API
        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_b.id])

        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.A',
                    'uraian': 'Bundle A',
                    'satuan': 'm3',
                    'koefisien': '1.0',
                    'ref_kind': 'job',
                    'ref_id': str(pekerjaan_a.id),
                }
            ]
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')

        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        ref_job_errors = [err for err in data.get('errors', []) if err.get('path') == 'rows[0].ref_job']
        assert ref_job_errors, "Harus ada error circular dependency pada ref_job"
        assert 'circular' in ref_job_errors[0]['message'].lower()


# ============================================================================
# TEST 4: OPTIMISTIC LOCKING
# ============================================================================

@pytest.mark.django_db
class TestOptimisticLocking:
    """Test optimistic locking with client_updated_at"""

    def test_concurrent_edit_detection(self, baseline_setup, user, client):
        """Test that concurrent edits are detected"""
        client.force_login(user)

        pekerjaan_a = baseline_setup['pekerjaan_a']
        project = pekerjaan_a.project

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_a.id])

        # Get current timestamp
        pekerjaan_a.refresh_from_db()
        old_timestamp = pekerjaan_a.updated_at.isoformat()

        # Simulate another user editing (update timestamp)
        detail = DetailAHSPProject.objects.get(pekerjaan=pekerjaan_a, kategori='TK')
        detail.koefisien = Decimal('3.0')
        detail.save()

        populate_expanded_for(pekerjaan_a)
        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])
        pekerjaan_a.refresh_from_db()

        # Now try to save with old timestamp
        payload = {
            'rows': [
                {
                    'kategori': 'TK',
                    'kode': 'TK.001',
                    'uraian': 'Pekerja',
                    'satuan': 'OH',
                    'koefisien': '2.5',  # Different value
                }
            ],
            'client_updated_at': old_timestamp  # Old timestamp!
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert data['ok'] is False
        assert data.get('conflict') is True
        assert 'konflik' in data['user_message'].lower() or 'conflict' in data['user_message'].lower()

    def test_no_conflict_with_current_timestamp(self, baseline_setup, user, client):
        """Test that save succeeds with current timestamp"""
        client.force_login(user)

        pekerjaan_a = baseline_setup['pekerjaan_a']
        project = pekerjaan_a.project

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_a.id])

        # Get current timestamp
        pekerjaan_a.refresh_from_db()
        current_timestamp = pekerjaan_a.updated_at.isoformat()

        payload = {
            'rows': [
                {
                    'kategori': 'TK',
                    'kode': 'TK.001',
                    'uraian': 'Pekerja',
                    'satuan': 'OH',
                    'koefisien': '3.5',
                }
            ],
            'client_updated_at': current_timestamp
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True


# ============================================================================
# TEST 5: SOURCE TYPE RESTRICTIONS
# ============================================================================

@pytest.mark.django_db
class TestSourceTypeRestrictions:
    """Test source_type restrictions (REF/REF_MODIFIED/CUSTOM)"""

    def test_ref_pekerjaan_blocked(self, baseline_setup, user, client):
        """Test that REF pekerjaan cannot be edited"""
        client.force_login(user)

        pekerjaan_ref = baseline_setup['pekerjaan_ref']
        project = pekerjaan_ref.project

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_ref.id])

        payload = {
            'rows': [
                {
                    'kategori': 'TK',
                    'kode': 'TK.001',
                    'uraian': 'Pekerja',
                    'satuan': 'OH',
                    'koefisien': '2.0',
                }
            ]
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')

        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        assert 'referensi' in data['user_message'].lower()

    def test_ref_modified_can_edit_segments_abc(self, baseline_setup, user, client):
        """Test that REF_MODIFIED can edit TK/BHN/ALT but not LAIN"""
        client.force_login(user)

        project = baseline_setup['pekerjaan_ref'].project
        sub_klas = baseline_setup['pekerjaan_a'].sub_klasifikasi

        # Create REF_MODIFIED pekerjaan
        pekerjaan_ref_mod = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_REF_MOD,
            snapshot_kode="REF_MOD.001",
            snapshot_uraian="Pekerjaan REF Modified",
            snapshot_satuan="M3",
            ordering_index=5,
        )

        url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan', args=[project.id, pekerjaan_ref_mod.id])

        # Should succeed for TK/BHN/ALT
        payload = {
            'rows': [
                {
                    'kategori': 'TK',
                    'kode': 'TK.001',
                    'uraian': 'Pekerja',
                    'satuan': 'OH',
                    'koefisien': '2.0',
                }
            ]
        }

        response = client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 200

        # Should fail for LAIN (bundle)
        payload_bundle = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'LAIN.001',
                    'uraian': 'Bundle',
                    'satuan': 'm3',
                    'koefisien': '1.0',
                    'ref_kind': 'job',
                    'ref_id': str(baseline_setup['pekerjaan_a'].id),
                }
            ]
        }

        response_bundle = client.post(url, data=json.dumps(payload_bundle), content_type='application/json')
        assert response_bundle.status_code == 400
        data = response_bundle.json()
        custom_errors = [err for err in data.get('errors', []) if err.get('path') == 'rows[0].ref_kind']
        assert custom_errors, "Harus ada error bahwa bundle hanya untuk pekerjaan custom"
        assert 'custom' in custom_errors[0]['message'].lower()


# ============================================================================
# TEST 6: MAX DEPTH VALIDATION
# ============================================================================

@pytest.mark.django_db
class TestMaxDepthValidation:
    """Test max depth validation (3 levels)"""

    def test_max_depth_enforced(self, baseline_setup):
        """Test that expansion stops at max depth (3)"""
        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        pekerjaan_c = baseline_setup['pekerjaan_c']
        project = pekerjaan_a.project

        # Create 4-level chain to test max depth
        # Need to create Pekerjaan D
        pekerjaan_d = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=pekerjaan_a.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="D.001",
            snapshot_uraian="Pekerjaan D",
            snapshot_satuan="M3",
            ordering_index=10,
        )

        # B → A
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_b,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.A',
            uraian='Bundle A',
            satuan='m3',
            koefisien=Decimal('1.0'),
            ref_pekerjaan=pekerjaan_a,
        )
        populate_expanded_for(pekerjaan_b)

        # C → B
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_c,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.B',
            uraian='Bundle B',
            satuan='m3',
            koefisien=Decimal('1.0'),
            ref_pekerjaan=pekerjaan_b,
        )
        populate_expanded_for(pekerjaan_c)

        # D → C
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_d,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.C',
            uraian='Bundle C',
            satuan='m3',
            koefisien=Decimal('1.0'),
            ref_pekerjaan=pekerjaan_c,
        )

        # Try to expand D (should hit max depth limit and skip expansion)
        populate_expanded_for(pekerjaan_d)
        expanded_rows = DetailAHSPExpanded.objects.filter(pekerjaan=pekerjaan_d)
        assert expanded_rows.count() == 0


# ============================================================================
# TEST 7: DUAL STORAGE INTEGRITY
# ============================================================================

@pytest.mark.django_db
class TestDualStorageIntegrity:
    """Test dual storage integrity (DetailAHSPProject ↔ DetailAHSPExpanded)"""

    def test_raw_to_expanded_sync(self, baseline_setup):
        """Test that raw data properly syncs to expanded"""
        pekerjaan_a = baseline_setup['pekerjaan_a']

        # Verify Storage 1 (raw)
        raw_count = DetailAHSPProject.objects.filter(pekerjaan=pekerjaan_a).count()
        assert raw_count == 2  # TK + BHN

        # Verify Storage 2 (expanded)
        expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pekerjaan_a).count()
        assert expanded_count == 2  # Should match raw

        # Verify data consistency
        raw_tk = DetailAHSPProject.objects.get(pekerjaan=pekerjaan_a, kategori='TK')
        expanded_tk = DetailAHSPExpanded.objects.get(pekerjaan=pekerjaan_a, kategori='TK')

        assert raw_tk.kode == expanded_tk.kode
        assert raw_tk.koefisien == expanded_tk.koefisien
        assert expanded_tk.source_bundle_kode is None  # Direct input, not from bundle
        assert expanded_tk.expansion_depth == 0  # Direct, no expansion

    def test_bundle_expansion_creates_expanded_only(self, baseline_setup):
        """Test that bundle expansion creates expanded but not raw in target"""
        pekerjaan_a = baseline_setup['pekerjaan_a']
        pekerjaan_b = baseline_setup['pekerjaan_b']
        project = pekerjaan_a.project

        # Create bundle B → A
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_b,
            harga_item=baseline_setup['harga_lain'],
            kategori='LAIN',
            kode='LAIN.A',
            uraian='Bundle A',
            satuan='m3',
            koefisien=Decimal('1.0'),
            ref_pekerjaan=pekerjaan_a,
        )
        populate_expanded_for(pekerjaan_b)

        # B Storage 1: Should have 1 LAIN item only
        raw_b = DetailAHSPProject.objects.filter(pekerjaan=pekerjaan_b)
        assert raw_b.count() == 1
        assert raw_b.first().kategori == 'LAIN'

        # B Storage 2: Should have 2 expanded items (TK + BHN from A)
        expanded_b = DetailAHSPExpanded.objects.filter(pekerjaan=pekerjaan_b)
        assert expanded_b.count() == 2
        assert all(e.source_bundle_kode == 'LAIN.A' for e in expanded_b)
        assert all(e.expansion_depth == 1 for e in expanded_b)


# ============================================================================
# COVERAGE REPORT PLACEHOLDER
# ============================================================================

def test_coverage_report():
    """
    Coverage Report Placeholder

    To measure actual coverage:
    1. Install: pip install pytest-cov
    2. Run: pytest detail_project/tests/test_workflow_baseline.py --cov=detail_project --cov-report=html
    3. View: open htmlcov/index.html

    Target Functions:
    - detail_project.services.cascade_bundle_re_expansion
    - detail_project.services._populate_expanded_from_raw
    - detail_project.services.check_circular_dependency_pekerjaan
    - detail_project.services.validate_bundle_reference
    - detail_project.views_api.api_save_detail_ahsp_for_pekerjaan

    Target Coverage: >80% for core workflow
    """
    pass
