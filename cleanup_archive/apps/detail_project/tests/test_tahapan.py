# detail_project/tests/test_tahapan.py
# Test suite untuk Tahapan Pelaksanaan feature

import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse
from django.core.exceptions import ValidationError

from detail_project.models import (
    TahapPelaksanaan,
    PekerjaanTahapan,
    Pekerjaan,
    VolumePekerjaan,
    DetailAHSPProject,
    HargaItemProject,
)
from detail_project.services import (
    compute_kebutuhan_items,
    get_tahapan_summary,
    get_unassigned_pekerjaan
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def tahap1(db, project):
    """Create tahapan 1"""
    return TahapPelaksanaan.objects.create(
        project=project,
        nama="Tahap 1: Persiapan",
        urutan=1,
        deskripsi="Pekerjaan persiapan lahan",
        tanggal_mulai=date(2025, 1, 6),
        tanggal_selesai=date(2025, 1, 12),
    )


@pytest.fixture
def tahap2(db, project):
    """Create tahapan 2"""
    return TahapPelaksanaan.objects.create(
        project=project,
        nama="Tahap 2: Struktur",
        urutan=2,
        deskripsi="Pekerjaan struktur bawah",
        tanggal_mulai=date(2025, 1, 13),
        tanggal_selesai=date(2025, 1, 19),
    )


@pytest.fixture
def pekerjaan_test(db, project, sub_klas):
    """Create test pekerjaan"""
    return Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type="custom",
        snapshot_kode="TEST.001",
        snapshot_uraian="Pekerjaan Test",
        snapshot_satuan="m2",
        ordering_index=10
    )


def _create_pekerjaan_with_detail(
    project,
    sub_klas,
    kode_suffix: str,
    uraian: str,
    kategori: str = "TK",
    koefisien: Decimal = Decimal("1.0"),
    volume: Decimal = Decimal("5.0"),
    harga_satuan: Decimal = Decimal("10000"),
):
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type="custom",
        snapshot_kode=f"CUST-{kode_suffix}",
        snapshot_uraian=uraian,
        snapshot_satuan="OH",
        ordering_index=20,
    )
    harga_item = HargaItemProject.objects.create(
        project=project,
        kategori=kategori,
        kode_item=f"{kategori}.{kode_suffix}",
        uraian=f"{kategori} {uraian}",
        satuan="OH",
        harga_satuan=harga_satuan,
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        kategori=kategori,
        kode=f"{kategori}.{kode_suffix}",
        uraian=uraian,
        satuan="OH",
        koefisien=koefisien,
        harga_item=harga_item,
    )
    VolumePekerjaan.objects.update_or_create(
        project=project,
        pekerjaan=pekerjaan,
        defaults={"quantity": volume},
    )
    return pekerjaan


# =============================================================================
# MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestTahapPelaksanaanModel:
    """Test TahapPelaksanaan model"""
    
    def test_create_tahapan(self, project):
        """Test creating tahapan"""
        tahap = TahapPelaksanaan.objects.create(
            project=project,
            nama="Tahap Test",
            urutan=1
        )
        
        assert tahap.id is not None
        assert tahap.nama == "Tahap Test"
        assert tahap.urutan == 1
        assert str(tahap) == f"Tahap Test (Project: {project.nama})"
    
    def test_tahapan_unique_name_per_project(self, project, tahap1):
        """Test unique constraint: nama per project"""
        with pytest.raises(Exception):  # IntegrityError
            TahapPelaksanaan.objects.create(
                project=project,
                nama="Tahap 1: Persiapan",  # Duplicate
                urutan=2
            )
    
    def test_tahapan_validation_tanggal(self, project):
        """Test tanggal validation"""
        tahap = TahapPelaksanaan(
            project=project,
            nama="Test",
            tanggal_mulai="2025-01-15",
            tanggal_selesai="2025-01-01"  # Before mulai
        )
        
        with pytest.raises(ValidationError):
            tahap.full_clean()
    
    def test_get_total_pekerjaan(self, tahap1, pekerjaan_test):
        """Test get_total_pekerjaan method"""
        # No assignment yet
        assert tahap1.get_total_pekerjaan() == 0
        
        # Add assignment
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1,
            proporsi_volume=Decimal('100')
        )
        
        assert tahap1.get_total_pekerjaan() == 1


@pytest.mark.django_db
class TestPekerjaanTahapanModel:
    """Test PekerjaanTahapan model"""
    
    def test_create_assignment(self, pekerjaan_test, tahap1):
        """Test creating assignment"""
        pt = PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1,
            proporsi_volume=Decimal('60.00'),
            catatan="Test assignment"
        )
        
        assert pt.id is not None
        assert pt.proporsi_volume == Decimal('60.00')
        assert pt.catatan == "Test assignment"
    
    def test_proporsi_validation(self, pekerjaan_test, tahap1):
        """Test proporsi validation"""
        # Invalid: > 100
        with pytest.raises(ValidationError):
            pt = PekerjaanTahapan(
                pekerjaan=pekerjaan_test,
                tahapan=tahap1,
                proporsi_volume=Decimal('150')
            )
            pt.full_clean()
        
        # Invalid: < 0.01
        with pytest.raises(ValidationError):
            pt = PekerjaanTahapan(
                pekerjaan=pekerjaan_test,
                tahapan=tahap1,
                proporsi_volume=Decimal('0')
            )
            pt.full_clean()
    
    def test_unique_pekerjaan_tahapan(self, pekerjaan_test, tahap1):
        """Test unique constraint"""
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1,
            proporsi_volume=Decimal('100')
        )
        
        # Duplicate should fail
        with pytest.raises(Exception):  # IntegrityError
            PekerjaanTahapan.objects.create(
                pekerjaan=pekerjaan_test,
                tahapan=tahap1,
                proporsi_volume=Decimal('50')
            )

    def test_volume_efektif(self, pekerjaan_test, tahap1):
        """Test volume_efektif property"""
        from detail_project.models import VolumePekerjaan
        
        # Create volume for pekerjaan_test
        VolumePekerjaan.objects.create(
            project=pekerjaan_test.project,
            pekerjaan=pekerjaan_test,
            quantity=Decimal('5.000')
        )
        
        pt = PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1,
            proporsi_volume=Decimal('60.00')
        )
        
        # Expected: 5.000 * 60% = 3.000
        expected = Decimal('5.000') * Decimal('0.60')
        assert abs(pt.volume_efektif - expected) < Decimal('0.001')

# =============================================================================
# SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestComputeKebutuhanWithTahapan:
    """Test compute_kebutuhan_items dengan tahapan"""
    
    def test_compute_all_mode(self, client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5):
        """Test mode='all' (default behavior)"""
        rows = compute_kebutuhan_items(project, mode='all')
        
        assert len(rows) > 0
        # Should include TK.SMOKE
        tk_smoke = next((r for r in rows if r['kode'] == 'TK.SMOKE'), None)
        assert tk_smoke is not None
    
    def test_compute_tahapan_mode(self, project, pekerjaan_custom, detail_tk_smoke, volume5, tahap1):
        """Test mode='tahapan' with full assignment"""
        # Assign pekerjaan to tahap1 (100%)
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,
            proporsi_volume=Decimal('100')
        )
        
        rows = compute_kebutuhan_items(
            project, 
            mode='tahapan', 
            tahapan_id=tahap1.id
        )
        
        assert len(rows) > 0
        tk_smoke = next((r for r in rows if r['kode'] == 'TK.SMOKE'), None)
        assert tk_smoke is not None
    
    def test_compute_with_split_volume(self, project, pekerjaan_custom, detail_tk_smoke, volume5, tahap1, tahap2):
        """Test split volume: 60% tahap1, 40% tahap2"""
        # Split assignment
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,
            proporsi_volume=Decimal('60.00')
        )
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap2,
            proporsi_volume=Decimal('40.00')
        )
        
        # Compute for tahap1
        rows1 = compute_kebutuhan_items(
            project, 
            mode='tahapan', 
            tahapan_id=tahap1.id
        )
        
        # Compute for tahap2
        rows2 = compute_kebutuhan_items(
            project, 
            mode='tahapan', 
            tahapan_id=tahap2.id
        )
        
        # Both should have TK.SMOKE
        tk1 = next((r for r in rows1 if r['kode'] == 'TK.SMOKE'), None)
        tk2 = next((r for r in rows2 if r['kode'] == 'TK.SMOKE'), None)
        
        assert tk1 is not None
        assert tk2 is not None
        
        # Verify proportions
        # Original: 0.125 * 5.000 = 0.625
        # Tahap1 (60%): 0.625 * 0.60 = 0.375
        # Tahap2 (40%): 0.625 * 0.40 = 0.250
        
        q1 = Decimal(tk1['quantity'])
        q2 = Decimal(tk2['quantity'])
        
        assert abs(q1 - Decimal('0.375')) < Decimal('0.001')
        assert abs(q2 - Decimal('0.250')) < Decimal('0.001')
        
        # Total should equal original
        total = q1 + q2
        assert abs(total - Decimal('0.625')) < Decimal('0.001')


@pytest.mark.django_db
class TestTahapanServices:
    """Test tahapan-related service functions"""
    
    def test_get_tahapan_summary(self, project, tahap1, tahap2, pekerjaan_test):
        """Test get_tahapan_summary"""
        # Add assignment
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1,
            proporsi_volume=Decimal('100')
        )
        
        summary = get_tahapan_summary(project)
        
        assert len(summary) == 2
        assert summary[0]['nama'] == "Tahap 1: Persiapan"
        assert summary[0]['jumlah_pekerjaan'] == 1
        assert summary[1]['jumlah_pekerjaan'] == 0
    
    def test_get_unassigned_pekerjaan(self, project, pekerjaan_test, tahap1):
        """Test get_unassigned_pekerjaan"""
        # Initially unassigned
        unassigned = get_unassigned_pekerjaan(project)
        assert len(unassigned) == 1
        assert unassigned[0]['status'] == 'unassigned'
        
        # Partial assignment (60%)
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1,
            proporsi_volume=Decimal('60')
        )
        
        unassigned = get_unassigned_pekerjaan(project)
        assert len(unassigned) == 1
        assert unassigned[0]['status'] == 'partial'
        assert unassigned[0]['unassigned_proportion'] == 40.0
        
        # Full assignment (add 40% to another tahap)
        # (skipped for brevity - would result in empty unassigned list)


# =============================================================================
# API TESTS
# =============================================================================

@pytest.mark.django_db
class TestTahapanAPI:
    """Test Tahapan API endpoints"""
    
    def test_list_tahapan(self, client_logged, project, tahap1, tahap2):
        """Test GET /api/project/<id>/tahapan/"""
        url = reverse('detail_project:api_list_create_tahapan', args=[project.id])
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['count'] == 2
        assert len(data['tahapan']) == 2

    def test_create_tahapan(self, client_logged, project):
        """Test POST /api/project/<id>/tahapan/"""
        url = reverse('detail_project:api_list_create_tahapan', args=[project.id])
        payload = {
            'nama': 'Tahap Baru',
            'deskripsi': 'Test deskripsi',
            'tanggal_mulai': '2025-01-01',
            'tanggal_selesai': '2025-01-15'
        }
        
        response = client_logged.post(
            url,
            data=payload,
            content_type='application/json'
        )
        
        # DEBUG: Print actual error if 500
        if response.status_code == 500:
            print("Response content:", response.content)
            print("Response JSON:", response.json())
        
        assert response.status_code == 201
        data = response.json()
        assert data['ok'] is True
        assert data['tahapan']['nama'] == 'Tahap Baru'
        
        # Verify in DB
        assert TahapPelaksanaan.objects.filter(
            project=project,
            nama='Tahap Baru'
        ).exists()

    def test_assign_pekerjaan(self, client_logged, project, tahap1, pekerjaan_test):
        """Test POST /api/project/<id>/tahapan/<tid>/assign/"""
        url = reverse('detail_project:api_assign_pekerjaan', args=[project.id, tahap1.id])
        payload = {
            'assignments': [
                {
                    'pekerjaan_id': pekerjaan_test.id,
                    'proporsi': 60.0,
                    'catatan': 'Test'
                }
            ]
        }
        
        response = client_logged.post(
            url,
            data=payload,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['created'] == 1
        
        # Verify in DB
        pt = PekerjaanTahapan.objects.get(
            pekerjaan=pekerjaan_test,
            tahapan=tahap1
        )
        assert pt.proporsi_volume == Decimal('60.0')
    
    def test_get_rekap_kebutuhan_enhanced(self, client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5, tahap1):
        """Test GET /api/project/<id>/rekap-kebutuhan-enhanced/"""
        # Assign pekerjaan
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,
            proporsi_volume=Decimal('100')
        )
        
        # Test mode=all
        url = reverse('detail_project:api_get_rekap_kebutuhan_enhanced', args=[project.id])
        response = client_logged.get(url + '?mode=all')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['rows']) > 0
        
        # Test mode=tahapan
        response = client_logged.get(url + f'?mode=tahapan&tahapan_id={tahap1.id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['meta']['mode'] == 'tahapan'
        assert data['meta']['tahapan']['tahapan_id'] == tahap1.id

    def test_rekap_kebutuhan_filters_endpoint_includes_pekerjaan_and_periods(
        self,
        client_logged,
        project,
        pekerjaan_custom,
        detail_tk_smoke,
        volume5,
        tahap1
    ):
        url = reverse('detail_project:api_get_rekap_kebutuhan_filters', args=[project.id])
        response = client_logged.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload['ok'] is True
        assert 'pekerjaan' in payload and len(payload['pekerjaan']) >= 1
        assert 'periods' in payload
        assert isinstance(payload['periods'].get('weeks'), list)
        assert len(payload['periods']['weeks']) >= 1

    def test_rekap_kebutuhan_filter_by_pekerjaan(
        self,
        client_logged,
        project,
        sub_klas,
        pekerjaan_custom,
        detail_tk_smoke,
        volume5,
        tahap1
    ):
        pekerjaan_lain = _create_pekerjaan_with_detail(
            project,
            sub_klas,
            kode_suffix="MAT001",
            uraian="Material Test",
            kategori="BHN",
            koefisien=Decimal("0.5"),
            volume=Decimal("8.0"),
            harga_satuan=Decimal("5000"),
        )
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_lain,
            tahapan=tahap1,
            proporsi_volume=Decimal('100')
        )

        url = reverse('detail_project:api_get_rekap_kebutuhan_enhanced', args=[project.id])
        response = client_logged.get(url + f'?pekerjaan={pekerjaan_lain.id}')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['rows']) >= 1
        assert all(row['kode'] == 'BHN.MAT001' for row in data['rows'])

    def test_rekap_kebutuhan_time_scope_week(
        self,
        client_logged,
        project,
        pekerjaan_custom,
        detail_tk_smoke,
        volume5,
        tahap1,
        tahap2
    ):
        # Split pekerjaan equally across two tahapan/weeks
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,
            proporsi_volume=Decimal('50')
        )
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap2,
            proporsi_volume=Decimal('50')
        )

        url = reverse('detail_project:api_get_rekap_kebutuhan_enhanced', args=[project.id])
        resp_all = client_logged.get(url)
        assert resp_all.status_code == 200
        data_all = resp_all.json()
        qty_all = None
        for row in data_all['rows']:
            if row['kode'] == 'TK.SMOKE':
                qty_all = Decimal(str(row.get('quantity_decimal') or row.get('quantity')))
                break
        assert qty_all is not None

        iso_year, iso_week, _ = tahap1.tanggal_mulai.isocalendar()
        week_code = f"{iso_year}-W{iso_week:02d}"
        resp_week = client_logged.get(url + f'?period_mode=week&period_start={week_code}')
        assert resp_week.status_code == 200
        data_week = resp_week.json()
        qty_week = None
        for row in data_week['rows']:
            if row['kode'] == 'TK.SMOKE':
                qty_week = Decimal(str(row.get('quantity_decimal') or row.get('quantity')))
                break
        assert qty_week is not None
        assert qty_week == qty_all / 2

    def test_rekap_kebutuhan_timeline_api(
        self,
        client_logged,
        project,
        pekerjaan_custom,
        detail_tk_smoke,
        volume5,
        tahap1,
        tahap2
    ):
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,
            proporsi_volume=Decimal('60')
        )
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap2,
            proporsi_volume=Decimal('40')
        )

        url = reverse('detail_project:api_get_rekap_kebutuhan_timeline', args=[project.id])
        response = client_logged.get(url + '?period_mode=week')
        assert response.status_code == 200
        payload = response.json()
        assert payload['ok'] is True
        assert payload['periods']


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestTahapanIntegration:
    """Integration tests untuk complete workflow"""
    
    def test_complete_workflow(self, client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5):
        """Test complete workflow: create tahapan → assign → compute"""
        
        # Step 1: Create 2 tahapan
        url_create = reverse('detail_project:api_list_create_tahapan', args=[project.id])
        
        r1 = client_logged.post(url_create, {
            'nama': 'Tahap 1',
            'deskripsi': 'First'
        }, content_type='application/json')
        assert r1.status_code == 201
        tahap1_id = r1.json()['tahapan']['tahapan_id']
        
        r2 = client_logged.post(url_create, {
            'nama': 'Tahap 2',
            'deskripsi': 'Second'
        }, content_type='application/json')
        assert r2.status_code == 201
        tahap2_id = r2.json()['tahapan']['tahapan_id']
        
        # Step 2: Split assignment 60/40
        url_assign1 = reverse('detail_project:api_assign_pekerjaan', args=[project.id, tahap1_id])
        r3 = client_logged.post(url_assign1, {
            'assignments': [{'pekerjaan_id': pekerjaan_custom.id, 'proporsi': 60}]
        }, content_type='application/json')
        assert r3.status_code == 200
        
        url_assign2 = reverse('detail_project:api_assign_pekerjaan', args=[project.id, tahap2_id])
        r4 = client_logged.post(url_assign2, {
            'assignments': [{'pekerjaan_id': pekerjaan_custom.id, 'proporsi': 40}]
        }, content_type='application/json')
        assert r4.status_code == 200
        
        # Step 3: Validate assignment
        url_validate = reverse('detail_project:api_validate_assignments', args=[project.id])
        r5 = client_logged.get(url_validate)
        assert r5.status_code == 200
        data = r5.json()
        assert data['is_complete'] is True  # 100% assigned
        assert data['incomplete'] == 0
        
        # Step 4: Compute rekap for each tahapan
        url_rekap = reverse('detail_project:api_get_rekap_kebutuhan_enhanced', args=[project.id])
        
        r6 = client_logged.get(url_rekap + f'?mode=tahapan&tahapan_id={tahap1_id}')
        assert r6.status_code == 200
        rows1 = r6.json()['rows']
        
        r7 = client_logged.get(url_rekap + f'?mode=tahapan&tahapan_id={tahap2_id}')
        assert r7.status_code == 200
        rows2 = r7.json()['rows']
        
        # Verify quantities (proportional split)
        assert len(rows1) > 0
        assert len(rows2) > 0
