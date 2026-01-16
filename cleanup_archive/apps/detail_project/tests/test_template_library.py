# detail_project/tests/test_template_library.py
"""
Tests for Template Library feature.

Tests cover:
- Template creation (api_create_template)
- Template listing (api_list_templates)
- Template detail (api_get_template_detail)
- Template import (api_import_template)
- Template export JSON download (export_template_json)
- Unified export/import helpers (_build_export_data, _import_template_data)
"""

import json
import pytest
from decimal import Decimal

from django.urls import reverse


# ================= Fixtures =================

@pytest.fixture
def project_with_detail_ahsp(db, user):
    """
    Create project with Klasifikasi → Sub → Pekerjaan(custom) → DetailAHSP.
    
    Includes:
    - 2 Klasifikasi
    - 2 SubKlasifikasi per Klasifikasi
    - 2 Pekerjaan(custom) per Sub with DetailAHSP
    """
    from dashboard.models import Project
    from detail_project.models import (
        Klasifikasi, SubKlasifikasi, Pekerjaan, 
        HargaItemProject, DetailAHSPProject
    )
    
    project = Project.objects.create(
        owner=user,
        nama='Test Template Project',
        sumber_dana='APBD',
        lokasi_project='Jakarta',
        nama_client='Test Client',
    )
    
    # Create hierarchy
    for ki in range(2):
        klas = Klasifikasi.objects.create(
            project=project,
            name=f'Klasifikasi {ki+1}',
            ordering_index=ki+1
        )
        
        for si in range(2):
            sub = SubKlasifikasi.objects.create(
                project=project,
                klasifikasi=klas,
                name=f'Sub {ki+1}.{si+1}',
                ordering_index=si+1
            )
            
            for pi in range(2):
                pkj = Pekerjaan.objects.create(
                    project=project,
                    sub_klasifikasi=sub,
                    source_type=Pekerjaan.SOURCE_CUSTOM,
                    snapshot_kode=f'CUST-{ki+1}{si+1}{pi+1}',
                    snapshot_uraian=f'Pekerjaan Custom {ki+1}.{si+1}.{pi+1}',
                    snapshot_satuan='m2',
                    ordering_index=(ki*4 + si*2 + pi + 1)
                )
                
                # Add DetailAHSP for each pekerjaan
                for cat, kode_prefix in [('TK', 'L'), ('BHN', 'B'), ('ALT', 'A')]:
                    harga, _ = HargaItemProject.objects.get_or_create(
                        project=project,
                        kode_item=f'{kode_prefix}.{ki+1}{si+1}{pi+1}',
                        defaults={
                            'uraian': f'Item {cat} {ki+1}.{si+1}.{pi+1}',
                            'satuan': 'unit',
                            'kategori': cat,
                            'harga_satuan': Decimal('10000'),
                        }
                    )
                    
                    DetailAHSPProject.objects.create(
                        project=project,
                        pekerjaan=pkj,
                        harga_item=harga,
                        kategori=cat,
                        kode=harga.kode_item,
                        uraian=harga.uraian,
                        satuan='unit',
                        koefisien=Decimal('0.5'),
                    )
    
    return project


@pytest.fixture
def pekerjaan_template(db, user, project_with_detail_ahsp):
    """
    Create a PekerjaanTemplate from existing project.
    """
    from detail_project.models import PekerjaanTemplate
    from detail_project.views_api import _build_export_data
    
    project = project_with_detail_ahsp
    
    template_meta = {
        "name": "Test Template",
        "description": "Template for testing",
        "category": "lainnya",
        "source_project": project.nama,
    }
    
    content = _build_export_data(project, mode='template', template_meta=template_meta)
    
    template = PekerjaanTemplate.objects.create(
        name="Test Template",
        description="Template for testing",
        category='lainnya',
        content=content,
        created_by=user,
        is_public=True,
    )
    
    return template


@pytest.fixture
def empty_project(db, user):
    """Create empty project for template import testing."""
    from dashboard.models import Project
    
    return Project.objects.create(
        owner=user,
        nama='Empty Test Project',
        sumber_dana='APBD',
        lokasi_project='Jakarta',
        nama_client='Test Client',
    )


# ================= Helper Export/Import Tests =================

class TestBuildExportData:
    """Tests for _build_export_data helper function."""
    
    def test_full_mode_includes_all_data(self, db, project_with_detail_ahsp):
        """Full mode should include harga_items, volume, etc."""
        from detail_project.views_api import _build_export_data
        
        project = project_with_detail_ahsp
        data = _build_export_data(project, mode='full')
        
        assert data['export_type'] == 'project_full_backup'
        assert 'project' in data
        assert 'harga_items' in data
        assert 'klasifikasi' in data
        assert 'sub_klasifikasi' in data
        assert 'pekerjaan' in data
        assert 'detail_ahsp' in data
    
    def test_template_mode_excludes_prices(self, db, project_with_detail_ahsp):
        """Template mode should NOT include harga_items list."""
        from detail_project.views_api import _build_export_data
        
        project = project_with_detail_ahsp
        data = _build_export_data(project, mode='template')
        
        assert data['export_type'] == 'project_template'
        assert 'harga_items' not in data
        assert 'volume' not in data
        assert 'project' not in data  # No project metadata in template
        assert 'klasifikasi' in data
        assert 'pekerjaan' in data
        assert 'detail_ahsp' in data
    
    def test_template_mode_includes_stats(self, db, project_with_detail_ahsp):
        """Template mode should include stats."""
        from detail_project.views_api import _build_export_data
        
        project = project_with_detail_ahsp
        data = _build_export_data(project, mode='template')
        
        assert 'stats' in data
        assert data['stats']['total_klasifikasi'] == 2
        assert data['stats']['total_sub'] == 4
        assert data['stats']['total_pekerjaan'] == 8
    
    def test_template_has_detail_ahsp_with_koefisien(self, db, project_with_detail_ahsp):
        """Template mode should export DetailAHSP with koefisien."""
        from detail_project.views_api import _build_export_data
        
        project = project_with_detail_ahsp
        data = _build_export_data(project, mode='template')
        
        assert len(data['detail_ahsp']) > 0
        
        for detail in data['detail_ahsp']:
            assert 'koefisien' in detail
            assert 'kategori' in detail
            assert 'kode' in detail


class TestImportTemplateData:
    """Tests for _import_template_data helper function."""
    
    def test_import_new_format(self, db, project_with_detail_ahsp, empty_project):
        """Import new format (flat arrays) should create all entities."""
        from detail_project.views_api import _build_export_data, _import_template_data
        from detail_project.models import Klasifikasi, SubKlasifikasi, Pekerjaan
        
        # Export from source
        source = project_with_detail_ahsp
        data = _build_export_data(source, mode='template')
        
        # Import to target
        target = empty_project
        stats, errors = _import_template_data(target, data)
        
        assert stats['klasifikasi'] == 2
        assert stats['sub'] == 4
        assert stats['pekerjaan'] == 8
        assert len(errors) == 0
        
        # Verify database
        assert Klasifikasi.objects.filter(project=target).count() == 2
        assert SubKlasifikasi.objects.filter(project=target).count() == 4
        assert Pekerjaan.objects.filter(project=target).count() == 8
    
    def test_import_creates_detail_ahsp(self, db, project_with_detail_ahsp, empty_project):
        """Import should create DetailAHSPProject records."""
        from detail_project.views_api import _build_export_data, _import_template_data
        from detail_project.models import DetailAHSPProject
        
        source = project_with_detail_ahsp
        data = _build_export_data(source, mode='template')
        
        target = empty_project
        stats, errors = _import_template_data(target, data)
        
        assert stats['detail'] > 0
        assert DetailAHSPProject.objects.filter(project=target).count() > 0
    
    def test_import_legacy_format(self, db, empty_project):
        """Import legacy nested format should still work."""
        from detail_project.views_api import _import_template_data
        from detail_project.models import Klasifikasi, SubKlasifikasi, Pekerjaan
        
        # Legacy format (nested)
        legacy_data = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "sub": [
                        {
                            "name": "Sub 1.1",
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "snapshot_uraian": "Pekerjaan 1",
                                    "snapshot_satuan": "m2"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        stats, errors = _import_template_data(empty_project, legacy_data)
        
        assert stats['klasifikasi'] == 1
        assert stats['sub'] == 1
        assert stats['pekerjaan'] == 1
        
        assert Klasifikasi.objects.filter(project=empty_project).count() == 1
        assert Pekerjaan.objects.filter(project=empty_project).count() == 1


# ================= API Tests =================

class TestCreateTemplateAPI:
    """Tests for api_create_template endpoint."""
    
    def test_create_template_success(self, client_logged, project_with_detail_ahsp):
        """Creating template should succeed with valid data."""
        project = project_with_detail_ahsp
        url = reverse('detail_project:api_create_template', args=[project.id])
        
        response = client_logged.post(
            url,
            data=json.dumps({
                'name': 'My Test Template',
                'description': 'Test description',
                'category': 'rumah'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert 'template_id' in data
    
    def test_create_template_duplicate_name(self, client_logged, project_with_detail_ahsp, pekerjaan_template):
        """Creating template with duplicate name should fail."""
        project = project_with_detail_ahsp
        url = reverse('detail_project:api_create_template', args=[project.id])
        
        response = client_logged.post(
            url,
            data=json.dumps({
                'name': 'Test Template',  # Same name as pekerjaan_template fixture
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False


class TestListTemplatesAPI:
    """Tests for api_list_templates endpoint."""
    
    def test_list_templates(self, client_logged, pekerjaan_template):
        """Listing templates should return created templates."""
        url = reverse('detail_project:api_list_templates')
        
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['templates']) >= 1
    
    def test_list_templates_with_search(self, client_logged, pekerjaan_template):
        """Listing templates with search should filter results."""
        url = reverse('detail_project:api_list_templates')
        
        response = client_logged.get(url, {'q': 'Test'})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['templates']) >= 1


class TestImportTemplateAPI:
    """Tests for api_import_template endpoint."""
    
    def test_import_template_success(self, client_logged, pekerjaan_template, empty_project):
        """Importing template should add data to project."""
        from detail_project.models import Klasifikasi, Pekerjaan
        
        url = reverse('detail_project:api_import_template', args=[empty_project.id, pekerjaan_template.id])
        
        response = client_logged.post(url, content_type='application/json')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['stats']['klasifikasi'] > 0
        assert data['stats']['pekerjaan'] > 0
        
        # Verify data imported
        assert Klasifikasi.objects.filter(project=empty_project).count() > 0
        assert Pekerjaan.objects.filter(project=empty_project).count() > 0
    
    def test_import_template_increments_usage(self, client_logged, pekerjaan_template, empty_project):
        """Importing template should increment usage count."""
        initial_usage = pekerjaan_template.usage_count
        
        url = reverse('detail_project:api_import_template', args=[empty_project.id, pekerjaan_template.id])
        client_logged.post(url, content_type='application/json')
        
        pekerjaan_template.refresh_from_db()
        assert pekerjaan_template.usage_count == initial_usage + 1


class TestExportTemplateJSON:
    """Tests for export_template_json endpoint."""
    
    def test_export_template_json(self, client_logged, project_with_detail_ahsp):
        """Export template JSON should return downloadable file."""
        project = project_with_detail_ahsp
        url = reverse('detail_project:export_template_json', args=[project.id])
        
        response = client_logged.get(url)
        
        assert response.status_code == 200
        assert 'attachment' in response.get('Content-Disposition', '')
        
        data = response.json()
        assert data['export_type'] == 'project_template'
        assert 'klasifikasi' in data
        assert 'pekerjaan' in data
        assert 'detail_ahsp' in data
