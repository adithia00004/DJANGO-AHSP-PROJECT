# detail_project/tests/test_template_export_import.py
"""
Comprehensive tests for Template Export/Import v2.2 functionality.

Tests cover:
- Template export with parameters and volume_formulas (v2.2)
- Template import from file with correct data mapping
- Case-insensitive formula parameter resolution
- Pekerjaan ref mapping during template import
"""

import json
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.urls import reverse


# ================= Fixtures =================

@pytest.fixture
def project_with_template_data(db, user):
    """
    Create a project with data suitable for template export testing.
    
    Includes:
    - Klasifikasi → SubKlasifikasi → Pekerjaan
    - ProjectParameter (for formula evaluation)
    - VolumeFormulaState (raw formulas with parameter references)
    - DetailAHSPProject
    """
    from dashboard.models import Project
    from detail_project.models import (
        Klasifikasi, SubKlasifikasi, Pekerjaan,
        HargaItemProject, DetailAHSPProject, VolumePekerjaan,
        VolumeFormulaState, ProjectParameter,
    )
    
    # Create project
    project = Project.objects.create(
        owner=user,
        nama="Template Source Project",
        sumber_dana="APBN",
        lokasi_project="Jakarta",
        nama_client="Client Test",
        anggaran_owner=Decimal("500000000.00"),
        tanggal_mulai=date.today(),
        tanggal_selesai=date.today() + timedelta(days=90),
        durasi_hari=90,
    )
    
    # Create Klasifikasi
    klas = Klasifikasi.objects.create(
        project=project,
        name="Pekerjaan Pondasi",
        ordering_index=1
    )
    
    # Create SubKlasifikasi
    sub = SubKlasifikasi.objects.create(
        project=project,
        klasifikasi=klas,
        name="Galian",
        ordering_index=1
    )
    
    # Create HargaItemProject
    harga_tk = HargaItemProject.objects.create(
        project=project,
        kode_item="TK-0001",
        uraian="Pekerja",
        satuan="OH",
        kategori="TK",
        harga_satuan=Decimal("100000.00"),
    )
    
    # Create Pekerjaan
    pekerjaan1 = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type="custom",
        snapshot_kode="GAL-001",
        snapshot_uraian="Galian Tanah Biasa",
        snapshot_satuan="m3",
        ordering_index=1,
    )
    
    pekerjaan2 = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type="custom",
        snapshot_kode="GAL-002",
        snapshot_uraian="Galian Tanah Keras",
        snapshot_satuan="m3",
        ordering_index=2,
    )
    
    # Create VolumePekerjaan
    VolumePekerjaan.objects.create(
        project=project,
        pekerjaan=pekerjaan1,
        quantity=Decimal("100.00"),
    )
    VolumePekerjaan.objects.create(
        project=project,
        pekerjaan=pekerjaan2,
        quantity=Decimal("50.00"),
    )
    
    # Create DetailAHSPProject
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan1,
        harga_item=harga_tk,
        kategori="TK",
        kode="TK-0001",
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("0.75"),
    )
    
    # Create ProjectParameters (lowercase names)
    ProjectParameter.objects.create(
        project=project,
        name="panjang",
        value=Decimal("10.00"),
        label="Panjang",
        unit="m",
        description="Panjang area kerja",
    )
    ProjectParameter.objects.create(
        project=project,
        name="lebar",
        value=Decimal("5.00"),
        label="Lebar",
        unit="m",
        description="Lebar area kerja",
    )
    ProjectParameter.objects.create(
        project=project,
        name="tinggi",
        value=Decimal("2.00"),
        label="Tinggi",
        unit="m",
        description="Kedalaman galian",
    )
    
    # Create VolumeFormulaState (using mixed case to test case-insensitivity)
    VolumeFormulaState.objects.create(
        project=project,
        pekerjaan=pekerjaan1,
        raw="=Panjang*Lebar*Tinggi",  # Mixed case!
        is_fx=True,
    )
    VolumeFormulaState.objects.create(
        project=project,
        pekerjaan=pekerjaan2,
        raw="=panjang*lebar*tinggi/2",  # lowercase
        is_fx=True,
    )
    
    return project


@pytest.fixture
def target_project(db, user):
    """Empty project to import template into."""
    from dashboard.models import Project
    
    return Project.objects.create(
        owner=user,
        nama="Target Project",
        sumber_dana="APBN",
        lokasi_project="Jakarta",
        nama_client="Client Test",
        anggaran_owner=Decimal("500000000.00"),
        tanggal_mulai=date.today(),
    )


# ================= Export Tests =================

class TestTemplateExportV22:
    """Tests for template export with v2.2 features."""
    
    def test_export_returns_project_template_type(self, client_logged, project_with_template_data):
        """Template export should return export_type=project_template."""
        url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['export_type'] == 'project_template'
        assert data['export_version'] == '2.2'
    
    def test_export_contains_parameters(self, client_logged, project_with_template_data):
        """Template export should contain parameters array."""
        url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        response = client_logged.get(url)
        data = response.json()
        
        assert 'parameters' in data
        assert len(data['parameters']) == 3  # panjang, lebar, tinggi
        
        # Check structure
        param = data['parameters'][0]
        assert 'name' in param
        assert 'value' in param
        assert 'label' in param
        assert 'unit' in param
    
    def test_export_contains_volume_formulas(self, client_logged, project_with_template_data):
        """Template export should contain volume_formulas array."""
        url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        response = client_logged.get(url)
        data = response.json()
        
        assert 'volume_formulas' in data
        assert len(data['volume_formulas']) == 2  # Two pekerjaan with formulas
        
        # Check structure
        formula = data['volume_formulas'][0]
        assert '_pekerjaan_ref' in formula
        assert 'raw' in formula
        assert 'is_fx' in formula
    
    def test_export_stats_includes_totals(self, client_logged, project_with_template_data):
        """Template export stats should include parameters and formulas counts."""
        url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        response = client_logged.get(url)
        data = response.json()
        
        stats = data.get('stats', {})
        assert stats.get('total_parameters') == 3
        assert stats.get('total_formulas') == 2


# ================= Import Tests =================

class TestTemplateImportV22:
    """Tests for template import with v2.2 features."""
    
    def test_import_creates_parameters(self, client_logged, project_with_template_data, target_project):
        """Template import should create ProjectParameter records."""
        from detail_project.models import ProjectParameter
        
        # First export
        export_url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        export_response = client_logged.get(export_url)
        export_data = export_response.json()
        
        # Count before import
        params_before = ProjectParameter.objects.filter(project=target_project).count()
        assert params_before == 0
        
        # Import
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': export_data}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get('ok') is True
        
        # Verify parameters created
        params_after = ProjectParameter.objects.filter(project=target_project)
        assert params_after.count() == 3
        
        param_names = set(p.name for p in params_after)
        assert param_names == {'panjang', 'lebar', 'tinggi'}
    
    def test_import_creates_volume_formulas(self, client_logged, project_with_template_data, target_project):
        """Template import should create VolumeFormulaState records."""
        from detail_project.models import VolumeFormulaState
        
        # First export
        export_url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        export_response = client_logged.get(export_url)
        export_data = export_response.json()
        
        # Import
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': export_data}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Verify formulas created
        formulas = VolumeFormulaState.objects.filter(project=target_project)
        assert formulas.count() == 2
        
        # Check formula content
        formula_raws = set(f.raw for f in formulas)
        assert '=Panjang*Lebar*Tinggi' in formula_raws
        assert '=panjang*lebar*tinggi/2' in formula_raws
    
    def test_import_stats_includes_parameters_and_formulas(
        self, client_logged, project_with_template_data, target_project
    ):
        """Import response stats should include parameters and formulas counts."""
        # Export
        export_url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        export_data = client_logged.get(export_url).json()
        
        # Import
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': export_data}),
            content_type='application/json'
        )
        
        data = response.json()
        stats = data.get('stats', {})
        
        assert stats.get('parameters') == 3
        assert stats.get('formulas') == 2


# ================= Case Insensitivity Tests =================

class TestFormulaCaseInsensitivity:
    """Tests for case-insensitive formula parameter resolution."""
    
    def test_formula_preserves_original_case(self, client_logged, project_with_template_data, target_project):
        """Imported formulas should preserve original case for display."""
        from detail_project.models import VolumeFormulaState
        
        # Export and import
        export_url = reverse(
            'detail_project:export_template_json',
            kwargs={'project_id': project_with_template_data.id}
        )
        export_data = client_logged.get(export_url).json()
        
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        client_logged.post(
            import_url,
            data=json.dumps({'content': export_data}),
            content_type='application/json'
        )
        
        # Check formula preserved original case
        formula = VolumeFormulaState.objects.filter(
            project=target_project,
            raw__icontains='Panjang'  # Mixed case
        ).first()
        
        assert formula is not None
        assert formula.raw == '=Panjang*Lebar*Tinggi'


# ================= Edge Cases =================

class TestTemplateImportEdgeCases:
    """Test edge cases for template import."""
    
    def test_import_with_empty_template_fails_validation(self, client_logged, target_project):
        """Import with completely empty template should return 400 (validation error)."""
        template_data = {
            'export_type': 'project_template',
            'export_version': '2.2',
            'klasifikasi': [],
            'sub_klasifikasi': [],
            'pekerjaan': [],  # Empty -> fails validation
            'detail_ahsp': [],
            'parameters': [],
            'volume_formulas': [],
        }
        
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': template_data}),
            content_type='application/json'
        )
        
        # API requires at least pekerjaan or klasifikasi data
        assert response.status_code == 400
        data = response.json()
        assert data.get('ok') is False
    
    def test_import_v21_without_formulas(self, client_logged, target_project):
        """Import v2.1 template (without volume_formulas) should work."""
        from detail_project.models import ProjectParameter, Klasifikasi
        
        # Need minimal klasifikasi to pass validation
        template_data = {
            'export_type': 'project_template',
            'export_version': '2.1',  # Old version
            'klasifikasi': [
                {'_export_id': 1, 'name': 'Test Klasifikasi', 'ordering_index': 1}
            ],
            'sub_klasifikasi': [],
            'pekerjaan': [],
            'detail_ahsp': [],
            'parameters': [
                {'name': 'test_param', 'value': '10.00', 'label': 'Test', 'unit': 'm', 'description': ''}
            ],
            # NO volume_formulas key (v2.1 didn't have it)
        }
        
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': template_data}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Parameters should still be imported
        params = ProjectParameter.objects.filter(project=target_project)
        assert params.count() == 1
        assert params.first().name == 'test_param'
        
        # Klasifikasi should also be imported
        assert Klasifikasi.objects.filter(project=target_project).count() == 1
    
    def test_import_formula_without_matching_pekerjaan_skipped(self, client_logged, target_project):
        """Formula referencing non-existent pekerjaan should be skipped."""
        from detail_project.models import VolumeFormulaState, Klasifikasi
        
        # Need minimal klasifikasi to pass validation, formula refs orphan pekerjaan
        template_data = {
            'export_type': 'project_template',
            'export_version': '2.2',
            'klasifikasi': [
                {'_export_id': 1, 'name': 'Test Klasifikasi', 'ordering_index': 1}
            ],
            'sub_klasifikasi': [],
            'pekerjaan': [],  # No pekerjaan, but klasifikasi passes validation
            'detail_ahsp': [],
            'parameters': [],
            'volume_formulas': [
                {'_pekerjaan_ref': 999, 'raw': '=test*2', 'is_fx': True}  # No matching pekerjaan
            ],
        }
        
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': template_data}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # No formulas should be created (orphan ref skipped)
        formulas = VolumeFormulaState.objects.filter(project=target_project)
        assert formulas.count() == 0
        
        # But klasifikasi should be created
        assert Klasifikasi.objects.filter(project=target_project).count() == 1
    
    def test_import_duplicate_parameter_updates_existing(self, client_logged, target_project):
        """Import parameter with existing name should update, not duplicate."""
        from detail_project.models import ProjectParameter
        
        # Create existing parameter
        ProjectParameter.objects.create(
            project=target_project,
            name='existing_param',
            value=Decimal('5.00'),
            label='Existing',
            unit='m',
        )
        
        # Need minimal klasifikasi to pass validation
        template_data = {
            'export_type': 'project_template',
            'export_version': '2.2',
            'klasifikasi': [
                {'_export_id': 1, 'name': 'Test Klasifikasi', 'ordering_index': 1}
            ],
            'sub_klasifikasi': [],
            'pekerjaan': [],
            'detail_ahsp': [],
            'parameters': [
                {'name': 'existing_param', 'value': '99.00', 'label': 'Updated', 'unit': 'cm', 'description': 'new'}
            ],
            'volume_formulas': [],
        }
        
        import_url = reverse(
            'detail_project:api_import_template_from_file',
            kwargs={'project_id': target_project.id}
        )
        response = client_logged.post(
            import_url,
            data=json.dumps({'content': template_data}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Should still be 1 parameter (updated, not duplicated)
        params = ProjectParameter.objects.filter(project=target_project)
        assert params.count() == 1
        
        param = params.first()
        assert param.value == Decimal('99.00')
        assert param.label == 'Updated'
        assert param.unit == 'cm'
