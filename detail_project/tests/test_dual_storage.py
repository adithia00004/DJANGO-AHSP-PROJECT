"""
Test Suite: Dual Storage Implementation
Purpose: Validate REF/REF_MODIFIED/CUSTOM pekerjaan dual storage behavior
Author: Claude + User
Created: 2025-11-09
"""

import pytest
import json
from decimal import Decimal
from django.contrib.auth import get_user_model

from detail_project.models import (
    Pekerjaan, DetailAHSPProject, DetailAHSPExpanded,
    HargaItemProject, Klasifikasi, SubKlasifikasi
)
from detail_project.services import clone_ref_pekerjaan, _populate_expanded_from_raw


# ==================== FIXTURES ====================

@pytest.fixture
def ahsp_referensi(db):
    """Create AHSP Referensi with components for testing"""
    try:
        from referensi.models import AHSPReferensi, RincianReferensi
    except ImportError:
        pytest.skip("referensi app not available")

    ahsp = AHSPReferensi.objects.create(
        kode_ahsp='1.1.4.1',
        nama_ahsp="Pekerjaan Beton f'c 15 MPa",
        satuan='m3'
    )

    # Add components
    RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori='TK',
        kode_item='L.01',
        uraian_item='Pekerja',
        satuan_item='OH',
        koefisien=Decimal('0.66')
    )
    RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori='BHN',
        kode_item='C.01',
        uraian_item='Semen',
        satuan_item='kg',
        koefisien=Decimal('326')
    )
    RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori='BHN',
        kode_item='D.01',
        uraian_item='Pasir',
        satuan_item='m3',
        koefisien=Decimal('0.52')
    )

    return ahsp


@pytest.fixture
def bundle_pekerjaan(db, project, sub_klas):
    """Create a bundle pekerjaan with components for testing CUSTOM bundles"""
    # Create bundle pekerjaan
    bundle = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type='custom',
        snapshot_kode='CUST-0001',
        snapshot_uraian='Bundle - 1 m2 Bekisting',
        snapshot_satuan='m2',
        ordering_index=1
    )

    # Create HargaItemProject for components
    hip_tk = HargaItemProject.objects.create(
        project=project,
        kategori='TK',
        kode_item='L.01',
        uraian='Pekerja',
        satuan='OH',
        harga_satuan=Decimal('150000')
    )

    hip_bhn1 = HargaItemProject.objects.create(
        project=project,
        kategori='BHN',
        kode_item='M.01',
        uraian='Kayu Meranti',
        satuan='m3',
        harga_satuan=Decimal('5500000')
    )

    hip_bhn2 = HargaItemProject.objects.create(
        project=project,
        kategori='BHN',
        kode_item='N.01',
        uraian='Paku',
        satuan='kg',
        harga_satuan=Decimal('18000')
    )

    # Add components to bundle
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=bundle,
        harga_item=hip_tk,
        kategori='TK',
        kode='L.01',
        uraian='Pekerja',
        satuan='OH',
        koefisien=Decimal('0.66')
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=bundle,
        harga_item=hip_bhn1,
        kategori='BHN',
        kode='M.01',
        uraian='Kayu Meranti',
        satuan='m3',
        koefisien=Decimal('0.04')
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=bundle,
        harga_item=hip_bhn2,
        kategori='BHN',
        kode='N.01',
        uraian='Paku',
        satuan='kg',
        koefisien=Decimal('0.40')
    )

    # CRITICAL: Populate expanded storage for bundle
    _populate_expanded_from_raw(project, bundle)

    return bundle


# ==================== TEST CASE 1: REF ====================

@pytest.mark.django_db
class TestREFPekerjaanDualStorage:
    """Test dual storage for REF (referensi read-only) pekerjaan"""

    def test_clone_ref_populates_both_storages(self, project, sub_klas, ahsp_referensi):
        """Test that clone_ref_pekerjaan populates both DetailAHSPProject and DetailAHSPExpanded"""

        # When: User creates pekerjaan from referensi
        pekerjaan = clone_ref_pekerjaan(
            project=project,
            sub=sub_klas,
            ref_obj=ahsp_referensi,
            source_type='ref',
            ordering_index=1,
            auto_load_rincian=True
        )

        # Then: Pekerjaan metadata correct
        assert pekerjaan.source_type == 'ref'
        assert pekerjaan.snapshot_kode == '1.1.4.1'
        assert "Beton f'c 15 MPa" in pekerjaan.snapshot_uraian

        # Then: DetailAHSPProject (Storage 1) populated
        raw_details = DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        ).order_by('kategori', 'kode')

        assert raw_details.count() == 3
        assert raw_details[0].kategori == 'BHN'
        assert raw_details[0].kode == 'C.01'
        assert raw_details[0].koefisien == Decimal('326')

        # Then: DetailAHSPExpanded (Storage 2) populated
        expanded_details = DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        ).order_by('kategori', 'kode')

        assert expanded_details.count() == 3
        assert expanded_details[0].kategori == 'BHN'
        assert expanded_details[0].kode == 'C.01'
        assert expanded_details[0].koefisien == Decimal('326')
        assert expanded_details[0].source_bundle_kode is None  # Direct input
        assert expanded_details[0].expansion_depth == 0

    def test_harga_items_api_returns_ref_items(self, client_logged, project, sub_klas, ahsp_referensi):
        """Test that Harga Items API returns items from REF pekerjaan"""

        # Given: REF pekerjaan created
        pekerjaan = clone_ref_pekerjaan(
            project=project,
            sub=sub_klas,
            ref_obj=ahsp_referensi,
            source_type='ref',
            ordering_index=1,
            auto_load_rincian=True
        )

        # When: Request Harga Items list
        url = f'/detail_project/api/project/{project.id}/harga-items/list/?canon=1'
        response = client_logged.get(url)

        # Then: Returns 3 items
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['items']) == 3

        kodes = [item['kode_item'] for item in data['items']]
        assert 'L.01' in kodes
        assert 'C.01' in kodes
        assert 'D.01' in kodes


# ==================== TEST CASE 2: REF_MODIFIED ====================

@pytest.mark.django_db
class TestREFMODIFIEDPekerjaanDualStorage:
    """Test dual storage for REF_MODIFIED (editable referensi) pekerjaan"""

    def test_clone_ref_modified_populates_both_storages(self, project, sub_klas, ahsp_referensi):
        """Test that clone_ref_pekerjaan with ref_modified populates both storages"""

        # When: User creates modified referensi pekerjaan
        pekerjaan = clone_ref_pekerjaan(
            project=project,
            sub=sub_klas,
            ref_obj=ahsp_referensi,
            source_type='ref_modified',
            ordering_index=1,
            auto_load_rincian=True,
            override_uraian="Modified Beton f'c 25 MPa"
        )

        # Then: Pekerjaan metadata correct
        assert pekerjaan.source_type == 'ref_modified'
        assert pekerjaan.snapshot_kode.startswith('mod.')
        assert pekerjaan.snapshot_uraian == "Modified Beton f'c 25 MPa"

        # Then: DetailAHSPProject populated (same as REF)
        raw_count = DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        ).count()
        assert raw_count == 3

        # Then: DetailAHSPExpanded populated (same as REF)
        expanded_count = DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        ).count()
        assert expanded_count == 3

    def test_harga_items_api_returns_ref_modified_items(self, client_logged, project, sub_klas, ahsp_referensi):
        """Test that Harga Items API returns items from REF_MODIFIED pekerjaan"""

        # Given: REF_MODIFIED pekerjaan created
        pekerjaan = clone_ref_pekerjaan(
            project=project,
            sub=sub_klas,
            ref_obj=ahsp_referensi,
            source_type='ref_modified',
            ordering_index=1,
            auto_load_rincian=True
        )

        # When: Request Harga Items list
        url = f'/detail_project/api/project/{project.id}/harga-items/list/?canon=1'
        response = client_logged.get(url)

        # Then: Returns 3 items (NOT empty!)
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['items']) == 3, f"Expected 3 items, got {len(data['items'])}"


# ==================== TEST CASE 3: CUSTOM BUNDLE ====================

@pytest.mark.django_db
class TestCUSTOMBundleDualStorage:
    """Test dual storage for CUSTOM pekerjaan with bundle references"""

    def test_custom_bundle_expansion_populates_expanded_storage(
        self, client_logged, project, sub_klas, bundle_pekerjaan
    ):
        """Test that CUSTOM pekerjaan with bundle reference expands to components"""

        # Given: Custom pekerjaan
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type='custom',
            snapshot_kode='CUST-0002',
            snapshot_uraian='Pekerjaan Custom 1',
            snapshot_satuan='m2',
            ordering_index=2
        )

        # When: User saves LAIN item with bundle reference
        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'Bundle - 1 m2 Bekisting',
                    'uraian': 'Pemasangan Bekisting',
                    'satuan': 'm2',
                    'koefisien': '10.0',
                    'ref_kind': 'job',  # NEW FORMAT
                    'ref_id': bundle_pekerjaan.id
                }
            ]
        }

        url = f'/detail_project/api/project/{project.id}/detail-ahsp/{pekerjaan.id}/save/'
        response = client_logged.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Then: Save successful
        assert response.status_code in [200, 207]
        data = response.json()
        assert data['saved_raw_rows'] == 1  # 1 bundle item
        assert data['saved_expanded_rows'] == 3  # 3 components
        assert len(data.get('errors', [])) == 0, f"Unexpected errors: {data.get('errors')}"

        # Then: DetailAHSPProject has 1 row (bundle, NOT expanded)
        raw_details = DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        )
        assert raw_details.count() == 1
        bundle_row = raw_details.first()
        assert bundle_row.kategori == 'LAIN'
        assert bundle_row.ref_pekerjaan == bundle_pekerjaan
        assert bundle_row.koefisien == Decimal('10.0')

        # Then: DetailAHSPExpanded has 3 rows (expanded components)
        expanded_details = DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        ).order_by('kode')

        assert expanded_details.count() == 3

        # Check TK component
        tk_expanded = expanded_details[0]
        assert tk_expanded.kategori == 'TK'
        assert tk_expanded.kode == 'L.01'
        assert tk_expanded.koefisien == Decimal('6.60')  # 10 × 0.66
        assert tk_expanded.source_bundle_kode == 'Bundle - 1 m2 Bekisting'
        assert tk_expanded.expansion_depth == 1

        # Check BHN components
        bhn1 = expanded_details[1]
        assert bhn1.kategori == 'BHN'
        assert bhn1.kode == 'M.01'
        assert bhn1.koefisien == Decimal('0.40')  # 10 × 0.04

        bhn2 = expanded_details[2]
        assert bhn2.kategori == 'BHN'
        assert bhn2.kode == 'N.01'
        assert bhn2.koefisien == Decimal('4.00')  # 10 × 0.40

    def test_harga_items_shows_expanded_components_not_bundle(
        self, client_logged, project, sub_klas, bundle_pekerjaan
    ):
        """Test that Harga Items shows expanded components, NOT bundle item"""

        # Given: Custom pekerjaan with bundle
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type='custom',
            snapshot_kode='CUST-0002',
            snapshot_uraian='Test Bundle',
            snapshot_satuan='m2',
            ordering_index=2
        )

        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'Bundle - 1 m2 Bekisting',
                    'uraian': 'Pemasangan Bekisting',
                    'satuan': 'm2',
                    'koefisien': '10.0',
                    'ref_kind': 'job',  # NEW FORMAT
                    'ref_id': bundle_pekerjaan.id
                }
            ]
        }

        save_url = f'/detail_project/api/project/{project.id}/detail-ahsp/{pekerjaan.id}/save/'
        client_logged.post(save_url, data=json.dumps(payload), content_type='application/json')

        # When: Request Harga Items
        list_url = f'/detail_project/api/project/{project.id}/harga-items/list/?canon=1'
        response = client_logged.get(list_url)

        # Then: Shows 3 components, NOT bundle
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['items']) == 3

        kodes = [item['kode_item'] for item in data['items']]
        assert 'L.01' in kodes  # Pekerja
        assert 'M.01' in kodes  # Kayu
        assert 'N.01' in kodes  # Paku
        assert 'Bundle - 1 m2 Bekisting' not in kodes  # Bundle NOT shown!


# ==================== TEST CASE 4: OVERRIDE BUG FIX ====================

@pytest.mark.django_db
class TestOverrideBugFixed:
    """Test that multiple bundles with same component kode don't override each other"""

    def test_multiple_bundles_same_kode_no_override(self, client_logged, project, sub_klas):
        """CRITICAL: Validate override bug is fixed"""

        # Given: Two bundles with overlapping TK.001
        bundle_a = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type='custom',
            snapshot_kode='CUST-0001',
            snapshot_uraian='Bundle A',
            snapshot_satuan='ls',
            ordering_index=1
        )

        # Bundle A components
        hip_tk = HargaItemProject.objects.create(
            project=project, kategori='TK', kode_item='TK.001',
            uraian='Pekerja', satuan='OH', harga_satuan=150000
        )
        hip_bhn1 = HargaItemProject.objects.create(
            project=project, kategori='BHN', kode_item='BHN.001',
            uraian='Bahan A', satuan='kg', harga_satuan=10000
        )

        DetailAHSPProject.objects.create(
            project=project, pekerjaan=bundle_a, harga_item=hip_tk,
            kategori='TK', kode='TK.001', uraian='Pekerja', satuan='OH', koefisien=Decimal('2.5')
        )
        DetailAHSPProject.objects.create(
            project=project, pekerjaan=bundle_a, harga_item=hip_bhn1,
            kategori='BHN', kode='BHN.001', uraian='Bahan A', satuan='kg', koefisien=Decimal('10.0')
        )
        _populate_expanded_from_raw(project, bundle_a)

        # Bundle B with same TK.001
        bundle_b = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type='custom',
            snapshot_kode='CUST-0002',
            snapshot_uraian='Bundle B',
            snapshot_satuan='ls',
            ordering_index=2
        )

        hip_bhn2 = HargaItemProject.objects.create(
            project=project, kategori='BHN', kode_item='BHN.002',
            uraian='Bahan B', satuan='kg', harga_satuan=5000
        )

        DetailAHSPProject.objects.create(
            project=project, pekerjaan=bundle_b, harga_item=hip_tk,
            kategori='TK', kode='TK.001', uraian='Pekerja', satuan='OH', koefisien=Decimal('3.0')
        )
        DetailAHSPProject.objects.create(
            project=project, pekerjaan=bundle_b, harga_item=hip_bhn2,
            kategori='BHN', kode='BHN.002', uraian='Bahan B', satuan='kg', koefisien=Decimal('5.0')
        )
        _populate_expanded_from_raw(project, bundle_b)

        # When: User adds BOTH bundles to same pekerjaan
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type='custom',
            snapshot_kode='CUST-0003',
            snapshot_uraian='Test Override',
            snapshot_satuan='ls',
            ordering_index=3
        )

        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'Bundle A',
                    'uraian': 'Bundle A',
                    'satuan': 'ls',
                    'koefisien': '2.0',
                    'ref_kind': 'job',  # NEW FORMAT
                    'ref_id': bundle_a.id
                },
                {
                    'kategori': 'LAIN',
                    'kode': 'Bundle B',
                    'uraian': 'Bundle B',
                    'satuan': 'ls',
                    'koefisien': '1.5',
                    'ref_kind': 'job',  # NEW FORMAT
                    'ref_id': bundle_b.id
                }
            ]
        }

        url = f'/detail_project/api/project/{project.id}/detail-ahsp/{pekerjaan.id}/save/'
        response = client_logged.post(url, data=json.dumps(payload), content_type='application/json')

        # Then: Save successful
        assert response.status_code in [200, 207]
        data = response.json()
        assert data['saved_raw_rows'] == 2  # 2 bundles
        assert data['saved_expanded_rows'] == 4  # 4 components total

        # Then: DetailAHSPExpanded has 4 rows (NO OVERRIDE!)
        expanded = DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan=pekerjaan
        )
        assert expanded.count() == 4

        # Then: Both TK.001 rows exist
        tk_rows = expanded.filter(kode='TK.001')
        assert tk_rows.count() == 2, "CRITICAL: Both TK.001 rows must exist!"

        # Verify koefisien values
        tk_from_a = tk_rows.get(source_bundle_kode='Bundle A')
        assert tk_from_a.koefisien == Decimal('5.0')  # 2.0 × 2.5

        tk_from_b = tk_rows.get(source_bundle_kode='Bundle B')
        assert tk_from_b.koefisien == Decimal('4.5')  # 1.5 × 3.0

        # Then: BHN rows correct
        bhn_from_a = expanded.get(kode='BHN.001', source_bundle_kode='Bundle A')
        assert bhn_from_a.koefisien == Decimal('20.0')  # 2.0 × 10.0

        bhn_from_b = expanded.get(kode='BHN.002', source_bundle_kode='Bundle B')
        assert bhn_from_b.koefisien == Decimal('7.5')  # 1.5 × 5.0


# ==================== TEST CASE 5: ERROR CASES ====================

@pytest.mark.django_db
class TestDualStorageErrorCases:
    """Test error handling in dual storage"""

    def test_lain_without_ref_pekerjaan_errors(self, client_logged, project, sub_klas):
        """Test that LAIN without ref_pekerjaan returns error"""

        # Given: Custom pekerjaan
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type='custom',
            snapshot_kode='CUST-TEST',
            snapshot_uraian='Test Error',
            snapshot_satuan='ls',
            ordering_index=1
        )

        # When: User tries to save LAIN without ref_pekerjaan_id
        payload = {
            'rows': [
                {
                    'kategori': 'LAIN',
                    'kode': 'INVALID',
                    'uraian': 'Invalid LAIN item',
                    'satuan': 'ls',
                    'koefisien': '1.0'
                    # NO ref_pekerjaan_id!
                }
            ]
        }

        url = f'/detail_project/api/project/{project.id}/detail-ahsp/{pekerjaan.id}/save/'
        response = client_logged.post(url, data=json.dumps(payload), content_type='application/json')

        # Then: Returns error
        assert response.status_code == 207  # Partial success
        data = response.json()
        assert data['ok'] is False
        assert data['saved_raw_rows'] == 1  # Raw saved
        assert data['saved_expanded_rows'] == 0  # Expanded NOT saved
        assert len(data['errors']) > 0
        assert 'tidak memiliki referensi pekerjaan' in data['errors'][0]['message']


# ==================== SUMMARY ====================

@pytest.mark.django_db
def test_dual_storage_summary(project):
    """Summary test to verify dual storage tables exist and are accessible"""

    # Verify models accessible
    assert DetailAHSPProject is not None
    assert DetailAHSPExpanded is not None

    # Verify can query (even if empty)
    raw_count = DetailAHSPProject.objects.filter(project=project).count()
    expanded_count = DetailAHSPExpanded.objects.filter(project=project).count()

    # Should be 0 at start
    assert raw_count >= 0
    assert expanded_count >= 0

    print(f"\n✅ Dual Storage Summary:")
    print(f"   - DetailAHSPProject: {raw_count} rows")
    print(f"   - DetailAHSPExpanded: {expanded_count} rows")
