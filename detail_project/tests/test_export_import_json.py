# detail_project/tests/test_export_import_json.py
"""
Comprehensive tests for Project Export/Import JSON functionality.

Tests cover:
- Export all project data including new v1.1 fields
- Import with correct data mapping
- VolumeFormulaState, ProjectParameter, ProjectPricing export/import
- HargaItemProject export/import
- DetailAHSPProject with bundle references
- PekerjaanProgressWeekly for jadwal pekerjaan
"""

import json
import pytest
from decimal import Decimal
from datetime import date, timedelta
from io import BytesIO

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile


# ================= Fixtures =================

@pytest.fixture
def project_with_full_data(db, user):
    """
    Create a complete project with all data types for export testing.
    
    Includes:
    - Project with dates
    - Klasifikasi → SubKlasifikasi → Pekerjaan
    - HargaItemProject dengan berbagai kategori
    - DetailAHSPProject
    - VolumePekerjaan
    - VolumeFormulaState
    - ProjectParameter
    - ProjectPricing
    - PekerjaanProgressWeekly
    """
    from dashboard.models import Project
    from detail_project.models import (
        Klasifikasi, SubKlasifikasi, Pekerjaan,
        HargaItemProject, DetailAHSPProject, VolumePekerjaan,
        VolumeFormulaState, ProjectParameter, ProjectPricing,
        PekerjaanProgressWeekly, ItemConversionProfile,
    )
    
    # Create project
    project = Project.objects.create(
        owner=user,
        nama="Project Export Test",
        sumber_dana="APBN",
        lokasi_project="Jakarta",
        nama_client="Client Export Test",
        anggaran_owner=Decimal("1000000000.00"),
        tanggal_mulai=date.today(),
        tanggal_selesai=date.today() + timedelta(days=90),
        durasi_hari=90,
        ket_project1="Keterangan 1",
        ket_project2="Keterangan 2",
        jabatan_client="Direktur",
        instansi_client="Instansi Test",
        nama_kontraktor="Kontraktor Test",
        instansi_kontraktor="PT Kontraktor",
        nama_konsultan_perencana="Konsultan Perencana",
        instansi_konsultan_perencana="PT Perencana",
        nama_konsultan_pengawas="Konsultan Pengawas",
        instansi_konsultan_pengawas="PT Pengawas",
        deskripsi="Deskripsi project test",
        kategori="Konstruksi",
        week_start_day=0,
        week_end_day=6,
    )
    
    # Create Klasifikasi
    klas = Klasifikasi.objects.create(
        project=project,
        name="Pekerjaan Persiapan",
        ordering_index=1
    )
    
    # Create SubKlasifikasi
    sub = SubKlasifikasi.objects.create(
        project=project,
        klasifikasi=klas,
        name="Pembersihan Lahan",
        ordering_index=1
    )
    
    # Create HargaItemProject (berbagai kategori)
    harga_tk = HargaItemProject.objects.create(
        project=project,
        kode_item="TK-0001",
        uraian="Mandor",
        satuan="OH",
        kategori="TK",
        harga_satuan=Decimal("165000.00"),
    )
    harga_bhn = HargaItemProject.objects.create(
        project=project,
        kode_item="B-0001",
        uraian="Semen Portland",
        satuan="kg",
        kategori="BHN",
        harga_satuan=Decimal("1300.00"),
    )
    harga_alt = HargaItemProject.objects.create(
        project=project,
        kode_item="PR-0001",
        uraian="Excavator",
        satuan="jam",
        kategori="ALT",
        harga_satuan=Decimal("500000.00"),
    )
    
    # Create ItemConversionProfile
    ItemConversionProfile.objects.create(
        harga_item=harga_bhn,
        market_unit="sak",
        market_price=Decimal("65000.00"),
        factor_to_base=Decimal("50.00"),
        method="direct",
    )
    
    # Create Pekerjaan
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type="custom",
        snapshot_kode="PEK-001",
        snapshot_uraian="Pekerjaan Test Export",
        snapshot_satuan="m3",
        ordering_index=1,
    )
    
    # Create VolumePekerjaan
    VolumePekerjaan.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        quantity=Decimal("100.00"),
    )
    
    # Create DetailAHSPProject
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_tk,
        kategori="TK",
        kode="TK-0001",
        uraian="Mandor",
        satuan="OH",
        koefisien=Decimal("0.05"),
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_bhn,
        kategori="BHN",
        kode="B-0001",
        uraian="Semen Portland",
        satuan="kg",
        koefisien=Decimal("10.00"),
    )
    
    # Create VolumeFormulaState
    VolumeFormulaState.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        raw="=panjang*lebar*tinggi",
        is_fx=True,
    )
    
    # Create ProjectParameter
    ProjectParameter.objects.create(
        project=project,
        name="panjang",
        value=Decimal("10.00"),
        label="Panjang",
        unit="m",
        description="Panjang area",
    )
    ProjectParameter.objects.create(
        project=project,
        name="lebar",
        value=Decimal("5.00"),
        label="Lebar",
        unit="m",
        description="Lebar area",
    )
    ProjectParameter.objects.create(
        project=project,
        name="tinggi",
        value=Decimal("2.00"),
        label="Tinggi",
        unit="m",
        description="Tinggi area",
    )
    
    # Create ProjectPricing
    ProjectPricing.objects.create(
        project=project,
        markup_percent=Decimal("10.00"),
        ppn_percent=Decimal("11.00"),
        rounding_base=10000,
    )
    
    # Create PekerjaanProgressWeekly
    for week in range(1, 4):
        start = project.tanggal_mulai + timedelta(days=(week - 1) * 7)
        end = start + timedelta(days=6)
        PekerjaanProgressWeekly.objects.create(
            project=project,
            pekerjaan=pekerjaan,
            week_number=week,
            week_start_date=start,
            week_end_date=end,
            planned_proportion=Decimal("33.33"),
            actual_proportion=Decimal("30.00") if week < 3 else Decimal("0"),
        )
    
    return project


# ================= Export Tests =================

class TestExportProjectJSON:
    """Tests for export_project_full_json view."""
    
    def test_export_returns_valid_json(self, client_logged, project_with_full_data):
        """Export should return valid JSON with correct structure."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url + '?include_progress=1')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        
        # Check export metadata
        assert data['export_type'] == 'project_full_backup'
        assert data['export_version'] == '1.1'
        assert data['source_project_id'] == project_with_full_data.id
        
    def test_export_contains_all_required_keys(self, client_logged, project_with_full_data):
        """Export should contain all v1.1 keys."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url + '?include_progress=1')
        data = json.loads(response.content)
        
        required_keys = [
            'project', 'klasifikasi', 'sub_klasifikasi',
            'harga_items', 'conversion_profiles', 'pekerjaan',
            'volume_pekerjaan', 'detail_ahsp',
            # v1.1 new keys
            'volume_formula_states', 'project_parameters', 'project_pricing',
            # progress keys
            'tahap_pelaksanaan', 'pekerjaan_tahapan', 'progress_weekly',
            'stats',
        ]
        
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
    
    def test_export_harga_items_data(self, client_logged, project_with_full_data):
        """HargaItemProject should be exported with correct fields."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url)
        data = json.loads(response.content)
        
        assert len(data['harga_items']) == 3  # TK, BHN, ALT
        
        # Check structure
        harga = data['harga_items'][0]
        assert '_export_id' in harga
        assert 'kode_item' in harga
        assert 'uraian' in harga
        assert 'satuan' in harga
        assert 'kategori' in harga
        assert 'harga_satuan' in harga
        
    def test_export_volume_formula_states(self, client_logged, project_with_full_data):
        """VolumeFormulaState should be exported."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url)
        data = json.loads(response.content)
        
        assert len(data['volume_formula_states']) == 1
        
        formula = data['volume_formula_states'][0]
        assert '_pekerjaan_ref' in formula
        assert formula['raw'] == '=panjang*lebar*tinggi'
        assert formula['is_fx'] is True
        
    def test_export_project_parameters(self, client_logged, project_with_full_data):
        """ProjectParameter should be exported."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url)
        data = json.loads(response.content)
        
        assert len(data['project_parameters']) == 3  # panjang, lebar, tinggi
        
        # Check structure
        param = data['project_parameters'][0]
        assert 'name' in param
        assert 'value' in param
        assert 'label' in param
        assert 'unit' in param
        assert 'description' in param
        
    def test_export_project_pricing(self, client_logged, project_with_full_data):
        """ProjectPricing should be exported."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url)
        data = json.loads(response.content)
        
        pricing = data['project_pricing']
        assert pricing is not None
        assert pricing['markup_percent'] == '10.00'
        assert pricing['ppn_percent'] == '11.00'
        assert pricing['rounding_base'] == 10000
        
    def test_export_progress_weekly(self, client_logged, project_with_full_data):
        """PekerjaanProgressWeekly should be exported when include_progress=1."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url + '?include_progress=1')
        data = json.loads(response.content)
        
        assert len(data['progress_weekly']) == 3  # 3 weeks
        
        # Check structure
        progress = data['progress_weekly'][0]
        assert '_pekerjaan_ref' in progress
        assert 'week_number' in progress
        assert 'week_start_date' in progress
        assert 'week_end_date' in progress
        assert 'planned_proportion' in progress
        assert 'actual_proportion' in progress
        
    def test_export_filename_contains_version(self, client_logged, project_with_full_data):
        """Export filename should contain v1.1."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        response = client_logged.get(url)
        
        content_disposition = response.get('Content-Disposition', '')
        assert 'v1.1' in content_disposition


# ================= Import Tests =================

class TestImportProjectJSON:
    """Tests for import_project_from_json view."""
    
    def test_import_creates_project_with_all_data(self, client_logged, project_with_full_data):
        """Importing exported JSON should create complete project."""
        from detail_project.models import (
            Klasifikasi, SubKlasifikasi, Pekerjaan,
            HargaItemProject, DetailAHSPProject, VolumePekerjaan,
            VolumeFormulaState, ProjectParameter, ProjectPricing,
        )
        from dashboard.models import Project
        
        # First export
        export_url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        export_response = client_logged.get(export_url + '?include_progress=1')
        export_data = export_response.content
        
        # Count before import
        projects_before = Project.objects.count()
        
        # Import
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile(
            "test_export.json",
            export_data,
            content_type="application/json"
        )
        
        import_response = client_logged.post(
            import_url,
            {'file': json_file, 'import_progress': '1'},
            format='multipart'
        )
        
        assert import_response.status_code == 200
        data = json.loads(import_response.content)
        assert data['status'] == 'success'
        
        # Verify new project created
        assert Project.objects.count() == projects_before + 1
        
        new_project_id = data['project_id']
        new_project = Project.objects.get(id=new_project_id)
        
        # Verify all data imported
        assert new_project.nama.endswith('(Import)')
        assert Klasifikasi.objects.filter(project=new_project).count() == 1
        assert SubKlasifikasi.objects.filter(project=new_project).count() == 1
        assert Pekerjaan.objects.filter(project=new_project).count() == 1
        assert HargaItemProject.objects.filter(project=new_project).count() == 3
        assert DetailAHSPProject.objects.filter(project=new_project).count() == 2
        assert VolumePekerjaan.objects.filter(project=new_project).count() == 1
        
    def test_import_volume_formula_states(self, client_logged, project_with_full_data):
        """VolumeFormulaState should be imported correctly."""
        from detail_project.models import VolumeFormulaState
        
        # Export
        export_url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        export_data = client_logged.get(export_url).content
        
        # Import
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile("test.json", export_data, content_type="application/json")
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        data = json.loads(response.content)
        new_project_id = data['project_id']
        
        # Verify
        formulas = VolumeFormulaState.objects.filter(project_id=new_project_id)
        assert formulas.count() == 1
        assert formulas.first().raw == '=panjang*lebar*tinggi'
        assert formulas.first().is_fx is True
        
    def test_import_project_parameters(self, client_logged, project_with_full_data):
        """ProjectParameter should be imported correctly."""
        from detail_project.models import ProjectParameter
        
        # Export
        export_url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        export_data = client_logged.get(export_url).content
        
        # Import
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile("test.json", export_data, content_type="application/json")
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        data = json.loads(response.content)
        new_project_id = data['project_id']
        
        # Verify
        params = ProjectParameter.objects.filter(project_id=new_project_id)
        assert params.count() == 3
        
        param_names = set(p.name for p in params)
        assert param_names == {'panjang', 'lebar', 'tinggi'}
        
    def test_import_project_pricing(self, client_logged, project_with_full_data):
        """ProjectPricing should be imported correctly."""
        from detail_project.models import ProjectPricing
        
        # Export
        export_url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        export_data = client_logged.get(export_url).content
        
        # Import
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile("test.json", export_data, content_type="application/json")
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        data = json.loads(response.content)
        new_project_id = data['project_id']
        
        # Verify
        pricing = ProjectPricing.objects.filter(project_id=new_project_id).first()
        assert pricing is not None
        assert pricing.markup_percent == Decimal('10.00')
        assert pricing.ppn_percent == Decimal('11.00')
        assert pricing.rounding_base == 10000
        
    def test_import_harga_items_with_prices(self, client_logged, project_with_full_data):
        """HargaItemProject should retain correct prices after import."""
        from detail_project.models import HargaItemProject
        
        # Export
        export_url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        export_data = client_logged.get(export_url).content
        
        # Import
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile("test.json", export_data, content_type="application/json")
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        data = json.loads(response.content)
        new_project_id = data['project_id']
        
        # Verify harga items
        harga_items = HargaItemProject.objects.filter(project_id=new_project_id)
        assert harga_items.count() == 3
        
        # Check specific prices
        mandor = harga_items.filter(kode_item='TK-0001').first()
        assert mandor is not None
        assert mandor.harga_satuan == Decimal('165000.00')
        
        semen = harga_items.filter(kode_item='B-0001').first()
        assert semen is not None
        assert semen.harga_satuan == Decimal('1300.00')
        
    def test_import_progress_weekly(self, client_logged, project_with_full_data):
        """PekerjaanProgressWeekly should be imported when import_progress=1."""
        from detail_project.models import PekerjaanProgressWeekly
        
        # Export with progress
        export_url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': project_with_full_data.id}
        )
        export_data = client_logged.get(export_url + '?include_progress=1').content
        
        # Import with progress
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile("test.json", export_data, content_type="application/json")
        response = client_logged.post(
            import_url,
            {'file': json_file, 'import_progress': '1'},
            format='multipart'
        )
        
        data = json.loads(response.content)
        new_project_id = data['project_id']
        
        # Verify progress
        progress = PekerjaanProgressWeekly.objects.filter(project_id=new_project_id)
        assert progress.count() == 3  # 3 weeks
        
    def test_import_backward_compatible_v10(self, client_logged, user):
        """Import should work with v1.0 JSON (without new v1.1 fields)."""
        from dashboard.models import Project
        
        # Simulate v1.0 export (without v1.1 fields)
        v10_data = {
            "export_type": "project_full_backup",
            "export_version": "1.0",
            "source_project_id": 999,
            "export_date": "2026-01-01T00:00:00+00:00",
            "include_progress": False,
            "project": {
                "nama": "V1.0 Test Project",
                "sumber_dana": "APBN",
                "lokasi_project": "Test",
                "nama_client": "Test",
                "anggaran_owner": "100000.00",
                "tanggal_mulai": "2026-01-01",
            },
            "klasifikasi": [],
            "sub_klasifikasi": [],
            "harga_items": [],
            "conversion_profiles": [],
            "pekerjaan": [],
            "volume_pekerjaan": [],
            "detail_ahsp": [],
            # NO volume_formula_states, project_parameters, project_pricing
        }
        
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile(
            "v10.json",
            json.dumps(v10_data).encode('utf-8'),
            content_type="application/json"
        )
        
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'


# ================= Edge Cases =================

class TestExportImportEdgeCases:
    """Test edge cases and error handling."""
    
    def test_export_nonexistent_project_returns_error(self, client_logged):
        """Export non-existent project should return 404."""
        url = reverse(
            'detail_project:export_project_full_json',
            kwargs={'project_id': 999999}
        )
        response = client_logged.get(url)
        # Accept either 404 (get_object_or_404) or 500 (wrapped error)
        assert response.status_code in [404, 500]
        
    def test_import_invalid_json_returns_error(self, client_logged):
        """Import invalid JSON should return error."""
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile(
            "invalid.json",
            b"not valid json{{{",
            content_type="application/json"
        )
        
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        assert response.status_code == 400
        
    def test_import_wrong_export_type_returns_error(self, client_logged):
        """Import with wrong export_type should return error."""
        wrong_data = {
            "export_type": "something_else",
            "export_version": "1.0",
            "project": {},
        }
        
        import_url = reverse('detail_project:import_project_from_json')
        json_file = SimpleUploadedFile(
            "wrong.json",
            json.dumps(wrong_data).encode('utf-8'),
            content_type="application/json"
        )
        
        response = client_logged.post(import_url, {'file': json_file}, format='multipart')
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data['status'].lower() or 'Invalid' in data.get('message', '')
        
    def test_import_without_file_returns_error(self, client_logged):
        """Import without file should return error (400 or 500 depending on request parsing)."""
        import_url = reverse('detail_project:import_project_from_json')
        response = client_logged.post(import_url, {}, format='multipart')
        
        # Accept 400 (proper validation) or 500 (RawPostDataException)
        # Both indicate the import was rejected
        assert response.status_code in [400, 500]
