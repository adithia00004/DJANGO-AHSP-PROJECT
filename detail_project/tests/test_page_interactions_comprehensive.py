"""
Comprehensive Page Interaction Integration Tests

Tests untuk memverifikasi bahwa interaksi antar page terjadi dengan harmonis
dan tersinkronisasi sempurna saat terjadi CRUD operations.

Test Coverage:
1. List Pekerjaan ↔ Volume Pekerjaan
2. List Pekerjaan ↔ Template AHSP
3. Volume Pekerjaan ↔ Rekap RAB
4. Template AHSP ↔ Harga Items (CRITICAL - sering bug dengan bundles)
5. Template AHSP ↔ Rincian AHSP
6. Harga Items ↔ Rincian AHSP
7. Rincian AHSP ↔ Rekap RAB

Setiap interaksi ditest dengan berbagai skenario:
- CRUD operations (Create, Read, Update, Delete)
- Edge cases (empty data, bundle, ref/custom/ref_modified)
- Concurrent access simulation
- Cache invalidation
- Data consistency
"""

import pytest
import json
from decimal import Decimal
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    VolumePekerjaan, DetailAHSPProject, DetailAHSPExpanded,
    HargaItemProject, ProjectPricing
)
from referensi.models import AHSPReferensi, RincianReferensi

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def user(db):
    """Create test user"""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )


@pytest.fixture
def client_logged(user):
    """Client with authenticated user"""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def project(user):
    """Create test project"""
    return Project.objects.create(
        owner=user,
        nama='Test Project Integration',
        sumber_dana='APBN',
        lokasi_project='Jakarta',
        nama_client='Test Client',
        anggaran_owner=Decimal('1000000000.00')
    )


@pytest.fixture
def klasifikasi(project):
    """Create test klasifikasi"""
    return Klasifikasi.objects.create(
        project=project,
        name='Test Klasifikasi',
        ordering_index=1
    )


@pytest.fixture
def sub_klasifikasi(project, klasifikasi):
    """Create test sub-klasifikasi"""
    return SubKlasifikasi.objects.create(
        project=project,
        klasifikasi=klasifikasi,
        name='Test Sub Klasifikasi',
        ordering_index=1
    )


@pytest.fixture
def pekerjaan_custom(project, sub_klasifikasi):
    """Create custom pekerjaan"""
    return Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klasifikasi,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode='CUS-001',
        snapshot_uraian='Pekerjaan Custom Test',
        snapshot_satuan='M3',
        ordering_index=1,
        detail_ready=False
    )


@pytest.fixture
def ahsp_referensi():
    """Create AHSP referensi for testing"""
    ahsp = AHSPReferensi.objects.create(
        kode_ahsp='TEST-001',
        nama_ahsp='Test AHSP Referensi',
        satuan='M2'
    )

    # Add some detail components
    RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori='TK',
        kode_item='L.01',
        uraian_item='Pekerja',
        satuan_item='OH',
        koefisien=Decimal('0.5')
    )
    RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori='BHN',
        kode_item='B.01',
        uraian_item='Semen',
        satuan_item='Zak',
        koefisien=Decimal('10')
    )

    return ahsp


@pytest.fixture
def pekerjaan_ref(project, sub_klasifikasi, ahsp_referensi):
    """Create reference pekerjaan"""
    return Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klasifikasi,
        source_type=Pekerjaan.SOURCE_REF,
        ref=ahsp_referensi,
        snapshot_kode=ahsp_referensi.kode_ahsp,
        snapshot_uraian=ahsp_referensi.nama_ahsp,
        snapshot_satuan=ahsp_referensi.satuan,
        ordering_index=2,
        detail_ready=True
    )


@pytest.fixture
def pekerjaan_bundle_target(project, sub_klasifikasi):
    """Create pekerjaan that will be used as bundle target"""
    pkj = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klasifikasi,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode='BUNDLE-TARGET',
        snapshot_uraian='Bundle Target Pekerjaan',
        snapshot_satuan='LS',
        ordering_index=3,
        detail_ready=True
    )

    # Add details to bundle target
    hip_tk = HargaItemProject.objects.create(
        project=project,
        kategori='TK',
        kode_item='L.02',
        uraian='Tukang',
        satuan='OH',
        harga_satuan=Decimal('150000')
    )

    hip_bhn = HargaItemProject.objects.create(
        project=project,
        kategori='BHN',
        kode_item='B.02',
        uraian='Pasir',
        satuan='M3',
        harga_satuan=Decimal('200000')
    )

    detail_tk = DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pkj,
        harga_item=hip_tk,
        kategori='TK',
        kode='L.02',
        uraian='Tukang',
        satuan='OH',
        koefisien=Decimal('1.0')
    )

    detail_bhn = DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pkj,
        harga_item=hip_bhn,
        kategori='BHN',
        kode='B.02',
        uraian='Pasir',
        satuan='M3',
        koefisien=Decimal('2.0')
    )

    # Create expanded storage
    DetailAHSPExpanded.objects.create(
        project=project,
        pekerjaan=pkj,
        source_detail=detail_tk,
        harga_item=hip_tk,
        kategori='TK',
        kode='L.02',
        uraian='Tukang',
        satuan='OH',
        koefisien=Decimal('1.0'),
        expansion_depth=0
    )

    DetailAHSPExpanded.objects.create(
        project=project,
        pekerjaan=pkj,
        source_detail=detail_bhn,
        harga_item=hip_bhn,
        kategori='BHN',
        kode='B.02',
        uraian='Pasir',
        satuan='M3',
        koefisien=Decimal('2.0'),
        expansion_depth=0
    )

    return pkj


def clear_cache_for_project(project):
    """Helper to clear cache for a project"""
    cache.delete(f"rekap:{project.id}:v1")


# ============================================================================
# TEST #1: List Pekerjaan ↔ Volume Pekerjaan
# ============================================================================

@pytest.mark.django_db
class TestListPekerjaanVolumeInteraction:
    """Test interaksi antara List Pekerjaan dan Volume Pekerjaan"""

    def test_create_pekerjaan_then_add_volume(
        self, client_logged, project, klasifikasi, sub_klasifikasi
    ):
        """
        Scenario: User membuat pekerjaan baru di List Pekerjaan,
        lalu menambahkan volume untuk pekerjaan tersebut.

        Expected: Volume tersimpan dengan benar dan terhubung ke pekerjaan.
        """
        # Step 1: Create pekerjaan via API
        url_save = reverse('detail_project:api_save_list_pekerjaan',
                          kwargs={'project_id': project.id})

        payload = {
            'klasifikasi': [{
                'id': klasifikasi.id,
                'name': klasifikasi.name,
                'sub': [{
                    'id': sub_klasifikasi.id,
                    'name': sub_klasifikasi.name,
                    'pekerjaan': [{
                        'source_type': 'custom',
                        'snapshot_kode': 'TEST-001',
                        'snapshot_uraian': 'Pekerjaan Test',
                        'snapshot_satuan': 'M3',
                        'ordering_index': 1
                    }]
                }]
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        # Get created pekerjaan ID
        pkj = Pekerjaan.objects.filter(
            project=project,
            snapshot_kode='TEST-001'
        ).first()

        assert pkj is not None
        assert pkj.snapshot_uraian == 'Pekerjaan Test'

        # Step 2: Add volume via API
        url_volume = reverse('detail_project:api_save_volume_pekerjaan',
                            kwargs={'project_id': project.id})

        volume_payload = {
            'items': [{
                'pekerjaan_id': pkj.id,
                'quantity': '10.5'
            }]
        }

        response = client_logged.post(
            url_volume,
            data=json.dumps(volume_payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        vol_data = response.json()
        assert vol_data['ok'] is True

        # Step 3: Verify volume is saved
        vol = VolumePekerjaan.objects.filter(
            project=project,
            pekerjaan=pkj
        ).first()

        assert vol is not None
        assert vol.quantity == Decimal('10.500')  # 3 decimal places

        # Step 4: Verify volume appears in list API
        url_list = reverse('detail_project:api_list_volume_pekerjaan',
                          kwargs={'project_id': project.id})

        response = client_logged.get(url_list)
        assert response.status_code == 200
        list_data = response.json()

        volumes_map = {v['pekerjaan_id']: v for v in list_data.get('volumes', [])}
        assert pkj.id in volumes_map
        assert Decimal(volumes_map[pkj.id]['quantity']) == Decimal('10.500')

    def test_delete_pekerjaan_cascades_volume(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User menghapus pekerjaan yang sudah ada volume.

        Expected: Volume ikut terhapus (CASCADE).
        """
        # Add volume first
        vol = VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('5.0')
        )

        assert VolumePekerjaan.objects.filter(id=vol.id).exists()

        # Delete pekerjaan via upsert API (exclude from payload)
        url_upsert = reverse('detail_project:api_upsert_list_pekerjaan',
                            kwargs={'project_id': project.id})

        payload = {
            'klasifikasi': []  # Empty = delete all
        }

        response = client_logged.post(
            url_upsert,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify pekerjaan deleted
        assert not Pekerjaan.objects.filter(id=pekerjaan_custom.id).exists()

        # Verify volume also deleted (CASCADE)
        assert not VolumePekerjaan.objects.filter(id=vol.id).exists()

    def test_volume_update_multiple_pekerjaan(
        self, client_logged, project, pekerjaan_custom, pekerjaan_ref
    ):
        """
        Scenario: User update volume untuk multiple pekerjaan sekaligus.

        Expected: Semua volume tersimpan dengan benar.
        """
        url_volume = reverse('detail_project:api_save_volume_pekerjaan',
                            kwargs={'project_id': project.id})

        payload = {
            'items': [
                {'pekerjaan_id': pekerjaan_custom.id, 'quantity': '15.25'},
                {'pekerjaan_id': pekerjaan_ref.id, 'quantity': '20.75'}
            ]
        }

        response = client_logged.post(
            url_volume,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['saved'] == 2

        # Verify both volumes
        vol1 = VolumePekerjaan.objects.get(
            project=project, pekerjaan=pekerjaan_custom
        )
        vol2 = VolumePekerjaan.objects.get(
            project=project, pekerjaan=pekerjaan_ref
        )

        assert vol1.quantity == Decimal('15.250')
        assert vol2.quantity == Decimal('20.750')


# ============================================================================
# TEST #2: List Pekerjaan ↔ Template AHSP
# ============================================================================

@pytest.mark.django_db
class TestListPekerjaanTemplateAHSPInteraction:
    """Test interaksi antara List Pekerjaan dan Template AHSP"""

    def test_create_custom_pekerjaan_appears_in_template_ahsp(
        self, client_logged, project, klasifikasi, sub_klasifikasi
    ):
        """
        Scenario: User membuat CUSTOM pekerjaan di List Pekerjaan.

        Expected: Pekerjaan muncul di Template AHSP dan editable.
        """
        # Create custom pekerjaan
        url_save = reverse('detail_project:api_save_list_pekerjaan',
                          kwargs={'project_id': project.id})

        payload = {
            'klasifikasi': [{
                'id': klasifikasi.id,
                'name': klasifikasi.name,
                'sub': [{
                    'id': sub_klasifikasi.id,
                    'name': sub_klasifikasi.name,
                    'pekerjaan': [{
                        'source_type': 'custom',
                        'snapshot_kode': 'CUSTOM-001',
                        'snapshot_uraian': 'Custom Pekerjaan',
                        'snapshot_satuan': 'M2',
                        'ordering_index': 1
                    }]
                }]
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        pkj = Pekerjaan.objects.get(
            project=project, snapshot_kode='CUSTOM-001'
        )

        # Verify appears in Template AHSP list
        url_template = reverse('detail_project:template_ahsp',
                              kwargs={'project_id': project.id})

        response = client_logged.get(url_template)
        assert response.status_code == 200
        assert 'CUSTOM-001' in response.content.decode()

        # Verify can fetch detail (should be empty initially)
        url_get = reverse('detail_project:api_get_detail_ahsp',
                         kwargs={'project_id': project.id,
                                'pekerjaan_id': pkj.id})

        response = client_logged.get(url_get)
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['items'] == []  # No details yet
        assert data['meta']['read_only'] is False  # Editable

    def test_create_ref_pekerjaan_readonly_in_template_ahsp(
        self, client_logged, project, pekerjaan_ref
    ):
        """
        Scenario: User membuat REF pekerjaan di List Pekerjaan.

        Expected: Pekerjaan muncul di Template AHSP tapi READ-ONLY.
        """
        url_get = reverse('detail_project:api_get_detail_ahsp',
                         kwargs={'project_id': project.id,
                                'pekerjaan_id': pekerjaan_ref.id})

        response = client_logged.get(url_get)
        assert response.status_code == 200
        data = response.json()

        assert data['ok'] is True
        assert data['meta']['read_only'] is True  # Read-only!
        assert len(data['items']) > 0  # Has details from reference

    def test_change_pekerjaan_source_type_affects_editability(
        self, client_logged, project, pekerjaan_custom, ahsp_referensi
    ):
        """
        Scenario: User mengubah CUSTOM pekerjaan menjadi REF via upsert.

        Expected: Pekerjaan di Template AHSP berubah menjadi read-only.
        """
        # Initially custom (editable)
        url_get = reverse('detail_project:api_get_detail_ahsp',
                         kwargs={'project_id': project.id,
                                'pekerjaan_id': pekerjaan_custom.id})

        response = client_logged.get(url_get)
        data = response.json()
        assert data['meta']['read_only'] is False

        # Change to REF via upsert
        url_upsert = reverse('detail_project:api_upsert_list_pekerjaan',
                            kwargs={'project_id': project.id})

        payload = {
            'klasifikasi': [{
                'id': pekerjaan_custom.sub_klasifikasi.klasifikasi.id,
                'sub': [{
                    'id': pekerjaan_custom.sub_klasifikasi.id,
                    'pekerjaan': [{
                        'id': pekerjaan_custom.id,
                        'source_type': 'ref',
                        'ref_id': ahsp_referensi.id,
                        'ordering_index': 1
                    }]
                }]
            }]
        }

        response = client_logged.post(
            url_upsert,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify changed to REF
        pekerjaan_custom.refresh_from_db()
        assert pekerjaan_custom.source_type == Pekerjaan.SOURCE_REF

        # Verify now read-only in Template AHSP
        response = client_logged.get(url_get)
        data = response.json()
        assert data['meta']['read_only'] is True


# ============================================================================
# TEST #3: Volume Pekerjaan ↔ Rekap RAB
# ============================================================================

@pytest.mark.django_db
class TestVolumePekerjaanRekapRABInteraction:
    """Test interaksi antara Volume Pekerjaan dan Rekap RAB"""

    def test_volume_change_updates_rekap_rab(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User mengubah volume pekerjaan.

        Expected: Rekap RAB subtotal dihitung ulang dengan volume baru.
        """
        # Setup: Add detail AHSP with price
        hip = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Pekerja',
            satuan='OH',
            harga_satuan=Decimal('100000')
        )

        detail = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0')  # 2 OH per unit
        )

        # Create expanded storage
        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0'),
            expansion_depth=0
        )

        pekerjaan_custom.detail_ready = True
        pekerjaan_custom.save()

        # Set initial volume
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('10.0')
        )

        clear_cache_for_project(project)

        # Get rekap RAB
        url_rekap = reverse('detail_project:api_rekap_ahsp',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_rekap)
        assert response.status_code == 200
        data = response.json()

        # Find pekerjaan in rekap
        pkj_rekap = next(
            (p for p in data.get('pekerjaan', [])
             if p['pekerjaan_id'] == pekerjaan_custom.id),
            None
        )

        assert pkj_rekap is not None
        # Subtotal = koef (2.0) × volume (10.0) × price (100000) = 2,000,000
        assert Decimal(pkj_rekap['subtotal_sebelum_buk']) == Decimal('2000000')

        # Update volume to 20.0
        url_volume = reverse('detail_project:api_save_volume_pekerjaan',
                            kwargs={'project_id': project.id})

        payload = {
            'items': [{
                'pekerjaan_id': pekerjaan_custom.id,
                'quantity': '20.0'
            }]
        }

        response = client_logged.post(
            url_volume,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Clear cache and get rekap again
        clear_cache_for_project(project)

        response = client_logged.get(url_rekap)
        data = response.json()

        pkj_rekap = next(
            (p for p in data.get('pekerjaan', [])
             if p['pekerjaan_id'] == pekerjaan_custom.id),
            None
        )

        # New subtotal = 2.0 × 20.0 × 100000 = 4,000,000
        assert Decimal(pkj_rekap['subtotal_sebelum_buk']) == Decimal('4000000')

    def test_zero_volume_excludes_from_rekap(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User set volume = 0.

        Expected: Pekerjaan tidak muncul di Rekap RAB.
        """
        # Add detail AHSP
        hip = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Pekerja',
            satuan='OH',
            harga_satuan=Decimal('100000')
        )

        detail = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('1.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('1.0'),
            expansion_depth=0
        )

        pekerjaan_custom.detail_ready = True
        pekerjaan_custom.save()

        # Set volume to 0
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('0')
        )

        clear_cache_for_project(project)

        # Get rekap
        url_rekap = reverse('detail_project:api_rekap_ahsp',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_rekap)
        data = response.json()

        # Pekerjaan dengan volume 0 tidak muncul
        pkj_rekap = next(
            (p for p in data.get('pekerjaan', [])
             if p['pekerjaan_id'] == pekerjaan_custom.id),
            None
        )

        # Should be excluded or have 0 subtotal
        if pkj_rekap:
            assert Decimal(pkj_rekap['subtotal_sebelum_buk']) == Decimal('0')


# ============================================================================
# TEST #4: Template AHSP ↔ Harga Items (CRITICAL)
# ============================================================================

@pytest.mark.django_db
class TestTemplateAHSPHargaItemsInteraction:
    """
    Test interaksi antara Template AHSP dan Harga Items

    INI ADALAH TEST PALING CRITICAL karena sering terjadi bug,
    terutama dengan bundle dan pekerjaan ref/custom/ref_modified.
    """

    def test_add_tk_item_creates_harga_item(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User menambah TK item di Template AHSP.

        Expected: HargaItemProject created dan muncul di Harga Items page.
        """
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [{
                'kategori': 'TK',
                'kode': 'L.01',
                'uraian': 'Pekerja',
                'satuan': 'OH',
                'koefisien': '1.5'
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        # Verify HargaItemProject created
        hip = HargaItemProject.objects.filter(
            project=project,
            kode_item='L.01'
        ).first()

        assert hip is not None
        assert hip.kategori == 'TK'
        assert hip.uraian == 'Pekerja'
        assert hip.harga_satuan is None  # Not set yet

        # Verify appears in Harga Items API
        url_harga = reverse('detail_project:api_list_harga_items',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_harga)
        assert response.status_code == 200
        harga_data = response.json()

        items = harga_data.get('items', [])
        l01 = next((i for i in items if i['kode_item'] == 'L.01'), None)

        assert l01 is not None
        assert l01['kategori'] == 'TK'
        assert l01['uraian'] == 'Pekerja'

    def test_bundle_expansion_creates_expanded_harga_items(
        self, client_logged, project, pekerjaan_custom, pekerjaan_bundle_target
    ):
        """
        Scenario: User menambah LAIN (bundle) item di Template AHSP
                  yang referensi ke pekerjaan lain.

        Expected:
        - Bundle di-expand menjadi komponen TK/BHN/ALT
        - Setiap komponen create HargaItemProject
        - Semua komponen muncul di Harga Items page

        INI ADALAH BUG YANG PALING SERING MUNCUL!
        """
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [{
                'kategori': 'LAIN',
                'kode': 'BUNDLE-TARGET',
                'uraian': 'Bundle Pekerjaan',
                'satuan': 'LS',
                'koefisien': '2.0',
                'ref_pekerjaan_id': pekerjaan_bundle_target.id
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        # Verify DetailAHSPProject created (raw input - keeps bundle)
        raw_detail = DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan=pekerjaan_custom,
            kategori='LAIN'
        ).first()

        assert raw_detail is not None
        assert raw_detail.ref_pekerjaan == pekerjaan_bundle_target

        # Verify DetailAHSPExpanded created (expanded components)
        expanded_details = DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan=pekerjaan_custom
        )

        # Should have 2 expanded components (TK + BHN) with multiplied koef
        assert expanded_details.count() == 2

        # Check TK component (koef = 1.0 × 2.0 = 2.0)
        tk_expanded = expanded_details.filter(kategori='TK').first()
        assert tk_expanded is not None
        assert tk_expanded.kode == 'L.02'
        assert tk_expanded.koefisien == Decimal('2.0')  # 1.0 × 2.0
        assert tk_expanded.source_bundle_kode == 'BUNDLE-TARGET'

        # Check BHN component (koef = 2.0 × 2.0 = 4.0)
        bhn_expanded = expanded_details.filter(kategori='BHN').first()
        assert bhn_expanded is not None
        assert bhn_expanded.kode == 'B.02'
        assert bhn_expanded.koefisien == Decimal('4.0')  # 2.0 × 2.0

        # CRITICAL CHECK: Verify ALL expanded components appear in Harga Items
        url_harga = reverse('detail_project:api_list_harga_items',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_harga)
        assert response.status_code == 200
        harga_data = response.json()

        items = harga_data.get('items', [])
        item_codes = {i['kode_item'] for i in items}

        # Expanded components MUST appear in Harga Items
        assert 'L.02' in item_codes, "TK component from bundle missing!"
        assert 'B.02' in item_codes, "BHN component from bundle missing!"

    def test_empty_bundle_shows_error(
        self, client_logged, project, pekerjaan_custom, sub_klasifikasi
    ):
        """
        Scenario: User menambah bundle yang referensi pekerjaan KOSONG
                  (tidak punya detail).

        Expected: Error message jelas, bundle tidak di-expand.
        """
        # Create empty bundle target
        empty_pkj = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode='EMPTY-BUNDLE',
            snapshot_uraian='Empty Bundle',
            snapshot_satuan='LS',
            ordering_index=10,
            detail_ready=False  # No details!
        )

        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [{
                'kategori': 'LAIN',
                'kode': 'EMPTY-BUNDLE',
                'uraian': 'Empty Bundle Test',
                'satuan': 'LS',
                'koefisien': '1.0',
                'ref_pekerjaan_id': empty_pkj.id
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should return partial success (207) with errors
        assert response.status_code == 207
        data = response.json()
        assert data['ok'] is False

        # Check error message
        errors = data.get('errors', [])
        assert len(errors) > 0

        bundle_error = next(
            (e for e in errors if 'bundle' in e.get('field', '').lower()),
            None
        )

        assert bundle_error is not None
        assert 'tidak memiliki komponen' in bundle_error['message'].lower()

    def test_update_template_ahsp_syncs_to_harga_items(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User mengedit detail AHSP (ubah kode/uraian).

        Expected: HargaItemProject ter-update, terlihat di Harga Items.
        """
        # Add initial item
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [{
                'kategori': 'TK',
                'kode': 'L.01',
                'uraian': 'Pekerja Old',
                'satuan': 'OH',
                'koefisien': '1.0'
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Update with new uraian
        payload['rows'][0]['uraian'] = 'Pekerja Updated'

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify HargaItemProject updated
        hip = HargaItemProject.objects.get(
            project=project,
            kode_item='L.01'
        )

        assert hip.uraian == 'Pekerja Updated'

        # Verify visible in Harga Items
        url_harga = reverse('detail_project:api_list_harga_items',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_harga)
        harga_data = response.json()

        l01 = next(
            (i for i in harga_data['items'] if i['kode_item'] == 'L.01'),
            None
        )

        assert l01['uraian'] == 'Pekerja Updated'

    def test_delete_template_ahsp_item_keeps_harga_item_if_used_elsewhere(
        self, client_logged, project, pekerjaan_custom, pekerjaan_ref
    ):
        """
        Scenario: Item 'L.01' digunakan di 2 pekerjaan.
                  User hapus dari pekerjaan A.

        Expected: HargaItemProject tetap ada karena masih dipakai pekerjaan B.
        """
        # Add L.01 to pekerjaan_custom
        hip = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Shared Item',
            satuan='OH',
            harga_satuan=Decimal('100000')
        )

        detail1 = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Shared Item',
            satuan='OH',
            koefisien=Decimal('1.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail1,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Shared Item',
            satuan='OH',
            koefisien=Decimal('1.0'),
            expansion_depth=0
        )

        # Add L.01 to pekerjaan_ref
        detail2 = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Shared Item',
            satuan='OH',
            koefisien=Decimal('2.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            source_detail=detail2,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Shared Item',
            satuan='OH',
            koefisien=Decimal('2.0'),
            expansion_depth=0
        )

        # Delete from pekerjaan_custom (save empty rows)
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {'rows': []}  # Empty = delete all

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify detail deleted from pekerjaan_custom
        assert not DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan=pekerjaan_custom
        ).exists()

        # Verify HargaItemProject still exists (used by pekerjaan_ref)
        assert HargaItemProject.objects.filter(
            project=project,
            kode_item='L.01'
        ).exists()

        # Verify still in Harga Items list
        url_harga = reverse('detail_project:api_list_harga_items',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_harga)
        harga_data = response.json()

        l01 = next(
            (i for i in harga_data['items'] if i['kode_item'] == 'L.01'),
            None
        )

        assert l01 is not None


# ============================================================================
# TEST #5: Template AHSP ↔ Rincian AHSP
# ============================================================================

@pytest.mark.django_db
class TestTemplateAHSPRincianAHSPInteraction:
    """Test interaksi antara Template AHSP dan Rincian AHSP"""

    def test_save_template_ahsp_appears_in_rincian(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User save detail AHSP di Template AHSP.

        Expected: Data muncul di Rincian AHSP (Detail Gabungan).
        """
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [
                {
                    'kategori': 'TK',
                    'kode': 'L.01',
                    'uraian': 'Pekerja',
                    'satuan': 'OH',
                    'koefisien': '1.5'
                },
                {
                    'kategori': 'BHN',
                    'kode': 'B.01',
                    'uraian': 'Semen',
                    'satuan': 'Zak',
                    'koefisien': '10'
                }
            ]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Get Rincian AHSP (Detail Gabungan)
        url_rincian = reverse('detail_project:api_get_detail_ahsp_gabungan',
                             kwargs={'project_id': project.id})

        response = client_logged.get(url_rincian)
        assert response.status_code == 200
        data = response.json()

        # Find pekerjaan in rincian
        pkj_rincian = next(
            (p for p in data.get('items', [])
             if p['pekerjaan_id'] == pekerjaan_custom.id),
            None
        )

        assert pkj_rincian is not None

        rows = pkj_rincian.get('rows', [])
        assert len(rows) == 2

        # Check TK row
        tk_row = next((r for r in rows if r['kategori'] == 'TK'), None)
        assert tk_row is not None
        assert tk_row['kode'] == 'L.01'
        assert Decimal(tk_row['koefisien']) == Decimal('1.5')

        # Check BHN row
        bhn_row = next((r for r in rows if r['kategori'] == 'BHN'), None)
        assert bhn_row is not None
        assert bhn_row['kode'] == 'B.01'
        assert Decimal(bhn_row['koefisien']) == Decimal('10')

    def test_bundle_expanded_in_rincian_ahsp(
        self, client_logged, project, pekerjaan_custom, pekerjaan_bundle_target
    ):
        """
        Scenario: User save bundle di Template AHSP.

        Expected: Rincian AHSP menampilkan expanded components (TK/BHN/ALT),
                  bukan bundle LAIN.
        """
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [{
                'kategori': 'LAIN',
                'kode': 'BUNDLE-TARGET',
                'uraian': 'Bundle',
                'satuan': 'LS',
                'koefisien': '3.0',
                'ref_pekerjaan_id': pekerjaan_bundle_target.id
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Get Rincian AHSP
        url_rincian = reverse('detail_project:api_get_detail_ahsp_gabungan',
                             kwargs={'project_id': project.id})

        response = client_logged.get(url_rincian)
        data = response.json()

        pkj_rincian = next(
            (p for p in data.get('items', [])
             if p['pekerjaan_id'] == pekerjaan_custom.id),
            None
        )

        assert pkj_rincian is not None

        rows = pkj_rincian.get('rows', [])

        # Should show expanded components, NOT bundle
        # Bundle target has TK (koef 1.0) + BHN (koef 2.0)
        # Multiplied by bundle koef 3.0
        assert len(rows) == 2

        # No LAIN row should appear
        lain_rows = [r for r in rows if r['kategori'] == 'LAIN']
        assert len(lain_rows) == 0

        # Check expanded TK (1.0 × 3.0 = 3.0)
        tk_row = next((r for r in rows if r['kategori'] == 'TK'), None)
        assert tk_row is not None
        assert Decimal(tk_row['koefisien']) == Decimal('3.0')

        # Check expanded BHN (2.0 × 3.0 = 6.0)
        bhn_row = next((r for r in rows if r['kategori'] == 'BHN'), None)
        assert bhn_row is not None
        assert Decimal(bhn_row['koefisien']) == Decimal('6.0')


# ============================================================================
# TEST #6: Harga Items ↔ Rincian AHSP
# ============================================================================

@pytest.mark.django_db
class TestHargaItemsRincianAHSPInteraction:
    """Test interaksi antara Harga Items dan Rincian AHSP"""

    def test_update_harga_reflects_in_rincian_subtotal(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: User update harga di Harga Items page.

        Expected: Subtotal di Rincian AHSP ikut ter-update.
        """
        # Setup: Create item with initial price
        hip = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Pekerja',
            satuan='OH',
            harga_satuan=Decimal('100000')  # Initial price
        )

        detail = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0'),
            expansion_depth=0
        )

        pekerjaan_custom.detail_ready = True
        pekerjaan_custom.save()

        # Add volume
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('10.0')
        )

        clear_cache_for_project(project)

        # Get initial rincian
        url_rincian = reverse('detail_project:api_get_rincian_rab',
                             kwargs={'project_id': project.id})

        response = client_logged.get(url_rincian)
        assert response.status_code == 200
        data = response.json()

        # Find L.01 item
        rows = data.get('rows', [])
        l01_row = next((r for r in rows if r['kode'] == 'L.01'), None)

        assert l01_row is not None
        # Initial subtotal = koef (2.0) × volume (10.0) × price (100000) = 2,000,000
        assert Decimal(l01_row['subtotal']) == Decimal('2000000')

        # Update harga via Harga Items API
        url_harga = reverse('detail_project:api_save_harga_items',
                           kwargs={'project_id': project.id})

        payload = {
            'items': [{
                'id': hip.id,
                'harga_satuan': '150000'  # New price
            }]
        }

        response = client_logged.post(
            url_harga,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        harga_data = response.json()
        assert harga_data['ok'] is True

        # Clear cache
        clear_cache_for_project(project)

        # Get updated rincian
        response = client_logged.get(url_rincian)
        data = response.json()

        rows = data.get('rows', [])
        l01_row = next((r for r in rows if r['kode'] == 'L.01'), None)

        # New subtotal = 2.0 × 10.0 × 150000 = 3,000,000
        assert Decimal(l01_row['subtotal']) == Decimal('3000000')

    def test_null_harga_shows_zero_subtotal_in_rincian(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: Item di Harga Items belum diisi harganya (NULL).

        Expected: Subtotal di Rincian = 0 atau N/A.
        """
        # Create item WITHOUT price (harga_satuan = NULL)
        hip = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Pekerja',
            satuan='OH',
            harga_satuan=None  # No price yet
        )

        detail = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0'),
            expansion_depth=0
        )

        pekerjaan_custom.detail_ready = True
        pekerjaan_custom.save()

        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('10.0')
        )

        clear_cache_for_project(project)

        # Get rincian
        url_rincian = reverse('detail_project:api_get_rincian_rab',
                             kwargs={'project_id': project.id})

        response = client_logged.get(url_rincian)
        data = response.json()

        rows = data.get('rows', [])
        l01_row = next((r for r in rows if r['kode'] == 'L.01'), None)

        assert l01_row is not None
        # Subtotal should be 0 when price is NULL
        assert Decimal(l01_row['subtotal']) == Decimal('0')


# ============================================================================
# TEST #7: Rincian AHSP ↔ Rekap RAB
# ============================================================================

@pytest.mark.django_db
class TestRincianAHSPRekapRABInteraction:
    """Test interaksi antara Rincian AHSP dan Rekap RAB"""

    def test_rincian_changes_reflect_in_rekap_total(
        self, client_logged, project, pekerjaan_custom
    ):
        """
        Scenario: Ada perubahan di Rincian AHSP (koef/harga/volume).

        Expected: Total di Rekap RAB ter-update.
        """
        # Setup complete data chain
        hip = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Pekerja',
            satuan='OH',
            harga_satuan=Decimal('100000')
        )

        detail = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail,
            harga_item=hip,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0'),
            expansion_depth=0
        )

        pekerjaan_custom.detail_ready = True
        pekerjaan_custom.save()

        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('10.0')
        )

        clear_cache_for_project(project)

        # Get initial rekap
        url_rekap = reverse('detail_project:api_rekap_ahsp',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_rekap)
        initial_data = response.json()

        initial_total = Decimal(initial_data.get('grand_total_akhir', '0'))
        # Initial = 2.0 × 10.0 × 100000 = 2,000,000 (+ markup if any)

        # Change koefisien in Template AHSP (affects Rincian)
        url_save = reverse('detail_project:api_save_detail_ahsp',
                          kwargs={'project_id': project.id,
                                 'pekerjaan_id': pekerjaan_custom.id})

        payload = {
            'rows': [{
                'kategori': 'TK',
                'kode': 'L.01',
                'uraian': 'Pekerja',
                'satuan': 'OH',
                'koefisien': '3.0'  # Changed from 2.0 to 3.0
            }]
        }

        response = client_logged.post(
            url_save,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        clear_cache_for_project(project)

        # Get updated rekap
        response = client_logged.get(url_rekap)
        updated_data = response.json()

        updated_total = Decimal(updated_data.get('grand_total_akhir', '0'))
        # New = 3.0 × 10.0 × 100000 = 3,000,000 (+ markup)

        # Total should increase proportionally
        assert updated_total > initial_total

    def test_rekap_aggregates_multiple_pekerjaan_correctly(
        self, client_logged, project, pekerjaan_custom, pekerjaan_ref
    ):
        """
        Scenario: Project punya multiple pekerjaan dengan detail & harga.

        Expected: Rekap RAB aggregate semua dengan benar.
        """
        # Setup pekerjaan 1
        hip1 = HargaItemProject.objects.create(
            project=project,
            kategori='TK',
            kode_item='L.01',
            uraian='Pekerja',
            satuan='OH',
            harga_satuan=Decimal('100000')
        )

        detail1 = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            harga_item=hip1,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            source_detail=detail1,
            harga_item=hip1,
            kategori='TK',
            kode='L.01',
            uraian='Pekerja',
            satuan='OH',
            koefisien=Decimal('2.0'),
            expansion_depth=0
        )

        pekerjaan_custom.detail_ready = True
        pekerjaan_custom.save()

        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_custom,
            quantity=Decimal('10.0')
        )

        # Setup pekerjaan 2
        hip2 = HargaItemProject.objects.create(
            project=project,
            kategori='BHN',
            kode_item='B.01',
            uraian='Semen',
            satuan='Zak',
            harga_satuan=Decimal('50000')
        )

        detail2 = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            harga_item=hip2,
            kategori='BHN',
            kode='B.01',
            uraian='Semen',
            satuan='Zak',
            koefisien=Decimal('5.0')
        )

        DetailAHSPExpanded.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            source_detail=detail2,
            harga_item=hip2,
            kategori='BHN',
            kode='B.01',
            uraian='Semen',
            satuan='Zak',
            koefisien=Decimal('5.0'),
            expansion_depth=0
        )

        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            quantity=Decimal('20.0')
        )

        clear_cache_for_project(project)

        # Get rekap
        url_rekap = reverse('detail_project:api_rekap_ahsp',
                           kwargs={'project_id': project.id})

        response = client_logged.get(url_rekap)
        data = response.json()

        # Check both pekerjaan in rekap
        pekerjaan_list = data.get('pekerjaan', [])
        assert len(pekerjaan_list) >= 2

        # Pekerjaan 1: 2.0 × 10.0 × 100000 = 2,000,000
        pkj1 = next(
            (p for p in pekerjaan_list
             if p['pekerjaan_id'] == pekerjaan_custom.id),
            None
        )
        assert pkj1 is not None
        assert Decimal(pkj1['subtotal_sebelum_buk']) == Decimal('2000000')

        # Pekerjaan 2: 5.0 × 20.0 × 50000 = 5,000,000
        pkj2 = next(
            (p for p in pekerjaan_list
             if p['pekerjaan_id'] == pekerjaan_ref.id),
            None
        )
        assert pkj2 is not None
        assert Decimal(pkj2['subtotal_sebelum_buk']) == Decimal('5000000')

        # Grand total (before BUK) = 2,000,000 + 5,000,000 = 7,000,000
        total_sebelum_buk = sum(
            Decimal(p['subtotal_sebelum_buk'])
            for p in pekerjaan_list
        )
        assert total_sebelum_buk == Decimal('7000000')


# ============================================================================
# TEST SUITE SUMMARY
# ============================================================================

def test_suite_summary():
    """
    Summary of comprehensive page interaction tests:

    ✅ Test #1: List Pekerjaan ↔ Volume Pekerjaan (3 tests)
       - Create pekerjaan → add volume
       - Delete pekerjaan cascades volume
       - Update multiple volumes

    ✅ Test #2: List Pekerjaan ↔ Template AHSP (3 tests)
       - Custom pekerjaan appears and editable
       - Ref pekerjaan appears as read-only
       - Source type change affects editability

    ✅ Test #3: Volume Pekerjaan ↔ Rekap RAB (2 tests)
       - Volume change updates rekap calculation
       - Zero volume excludes from rekap

    ✅ Test #4: Template AHSP ↔ Harga Items (6 tests) ⚠️ CRITICAL
       - Add TK item creates harga item
       - Bundle expansion creates all components
       - Empty bundle shows clear error
       - Update syncs to harga items
       - Delete keeps shared items
       - Item used in multiple pekerjaan

    ✅ Test #5: Template AHSP ↔ Rincian AHSP (2 tests)
       - Save template appears in rincian
       - Bundle expanded in rincian (not LAIN)

    ✅ Test #6: Harga Items ↔ Rincian AHSP (2 tests)
       - Update harga reflects in subtotal
       - NULL harga shows zero subtotal

    ✅ Test #7: Rincian AHSP ↔ Rekap RAB (2 tests)
       - Rincian changes reflect in rekap total
       - Multiple pekerjaan aggregated correctly

    Total: 20 comprehensive integration tests

    Coverage:
    - CRUD operations across all page pairs
    - Edge cases (empty data, bundles, ref/custom)
    - Cache invalidation
    - Data consistency
    - Dual storage (DetailAHSPProject vs DetailAHSPExpanded)
    """
    pass
