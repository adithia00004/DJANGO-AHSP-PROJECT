# dashboard/tests/test_integration.py
"""
Integration tests for dashboard workflows.

Coverage:
- Full CRUD workflow (create → read → update → delete)
- Excel upload workflow
- Duplicate workflow
- User isolation scenarios
"""

import pytest
from django.urls import reverse
from decimal import Decimal


@pytest.mark.django_db
class TestFullCRUDWorkflow:
    """Integration test for complete CRUD workflow."""

    def test_full_project_lifecycle(self, client, user):
        """Test creating, viewing, editing, duplicating, and deleting a project."""
        from dashboard.models import Project

        client.force_login(user)

        # 1. CREATE via formset
        url = reverse('dashboard:dashboard')
        create_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-nama': 'Integration Test Project',
            'form-0-tahun_project': '2025',
            'form-0-sumber_dana': 'APBN',
            'form-0-lokasi_project': 'Jakarta',
            'form-0-nama_client': 'Test Client',
            'form-0-anggaran_owner': '1000000000',
            'form-0-tanggal_mulai': '2025-01-01',
            'form-0-tanggal_selesai': '2025-12-31',
        }

        response = client.post(url, create_data)
        assert response.status_code == 302

        # Verify creation
        project = Project.objects.filter(nama='Integration Test Project').first()
        assert project is not None
        assert project.owner == user

        # 2. READ - View in dashboard
        response = client.get(url)
        assert response.status_code == 200
        assert project in response.context['projects']

        # 3. READ - View detail
        detail_url = reverse('dashboard:project_detail', kwargs={'pk': project.pk})
        response = client.get(detail_url)
        assert response.status_code == 200
        assert response.context['project'] == project

        # 4. UPDATE
        edit_url = reverse('dashboard:project_edit', kwargs={'pk': project.pk})
        update_data = {
            'nama': 'Updated Integration Project',
            'tahun_project': '2025',
            'sumber_dana': 'APBD',  # Changed
            'lokasi_project': 'Bandung',  # Changed
            'nama_client': 'Updated Client',
            'anggaran_owner': '2000000000',  # Changed
            'tanggal_mulai': '2025-01-01',
            'tanggal_selesai': '2025-12-31',
        }

        response = client.post(edit_url, update_data)
        assert response.status_code == 302

        # Verify update
        project.refresh_from_db()
        assert project.nama == 'Updated Integration Project'
        assert project.sumber_dana == 'APBD'
        assert project.lokasi_project == 'Bandung'
        assert project.anggaran_owner == Decimal('2000000000')

        # 5. DUPLICATE
        duplicate_url = reverse('dashboard:project_duplicate', kwargs={'pk': project.pk})
        duplicate_data = {
            'nama': 'Duplicated Project',
            'tahun_project': '2025',
            'sumber_dana': 'APBD',
            'lokasi_project': 'Bandung',
            'nama_client': 'Updated Client',
            'anggaran_owner': '2000000000',
        }

        original_count = Project.objects.count()
        response = client.post(duplicate_url, duplicate_data)
        assert response.status_code == 302

        # Verify duplication
        assert Project.objects.count() == original_count + 1
        duplicated = Project.objects.filter(nama='Duplicated Project').first()
        assert duplicated is not None
        assert duplicated.pk != project.pk
        assert duplicated.sumber_dana == project.sumber_dana

        # 6. SOFT DELETE (original project)
        delete_url = reverse('dashboard:project_delete', kwargs={'pk': project.pk})
        response = client.post(delete_url)
        assert response.status_code == 302

        # Verify soft delete
        project.refresh_from_db()
        assert project.is_active is False

        # 7. Verify archived project not in active list
        response = client.get(url)
        active_projects = response.context['projects']
        assert project not in active_projects
        assert duplicated in active_projects  # Duplicate should still be active


@pytest.mark.django_db
class TestExcelUploadWorkflow:
    """Integration test for Excel upload workflow."""

    def test_excel_upload_full_workflow(self, client, user):
        """Test uploading Excel file and verifying imported projects."""
        import openpyxl
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from dashboard.models import Project

        client.force_login(user)

        # 1. Create Excel file with multiple projects
        wb = openpyxl.Workbook()
        ws = wb.active

        headers = [
            'nama', 'tahun_project', 'sumber_dana', 'lokasi_project',
            'nama_client', 'anggaran_owner', 'tanggal_mulai', 'tanggal_selesai',
            'durasi_hari', 'ket_project1', 'ket_project2', 'jabatan_client',
            'instansi_client', 'nama_kontraktor', 'instansi_kontraktor',
            'nama_konsultan_perencana', 'instansi_konsultan_perencana',
            'nama_konsultan_pengawas', 'instansi_konsultan_pengawas',
            'deskripsi', 'kategori'
        ]
        ws.append(headers)

        # Add 3 projects
        for i in range(1, 4):
            ws.append([
                f'Excel Project {i}', 2025, 'APBN', f'Location {i}',
                f'Client {i}', i * 1000000000, '2025-01-01', '2025-12-31', 365,
                '', '', '', '', '', '', '', '', '', '',
                f'Description {i}', 'Infrastructure'
            ])

        # Save to BytesIO and wrap in SimpleUploadedFile
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        # Create SimpleUploadedFile with proper content type
        excel_file = SimpleUploadedFile(
            'test_projects.xlsx',
            excel_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # 2. Upload Excel file
        upload_url = reverse('dashboard:project_upload')
        original_count = Project.objects.filter(owner=user).count()

        response = client.post(upload_url, {'file': excel_file})

        # Should redirect on success
        assert response.status_code == 302

        # 3. Verify all projects were created
        new_count = Project.objects.filter(owner=user).count()
        assert new_count == original_count + 3

        # 4. Verify project details
        for i in range(1, 4):
            project = Project.objects.filter(nama=f'Excel Project {i}').first()
            assert project is not None
            assert project.owner == user
            assert project.tahun_project == 2025
            assert project.sumber_dana == 'APBN'
            assert project.anggaran_owner == Decimal(i * 1000000000)

        # 5. Verify they appear in dashboard
        dashboard_url = reverse('dashboard:dashboard')
        response = client.get(dashboard_url)
        assert response.status_code == 200

        projects = response.context['projects']
        assert any('Excel Project 1' in p.nama for p in projects)
        assert any('Excel Project 2' in p.nama for p in projects)
        assert any('Excel Project 3' in p.nama for p in projects)


@pytest.mark.django_db
class TestUserIsolationWorkflow:
    """Integration test for user isolation scenarios."""

    def test_complete_user_isolation(self, client, user, other_user):
        """Test that users are completely isolated from each other's data."""
        from dashboard.models import Project

        # 1. User creates a project
        client.force_login(user)
        url = reverse('dashboard:dashboard')

        create_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-nama': 'User Private Project',
            'form-0-tahun_project': '2025',
            'form-0-sumber_dana': 'APBN',
            'form-0-lokasi_project': 'Jakarta',
            'form-0-nama_client': 'Client',
            'form-0-anggaran_owner': '1000000000',
        }

        response = client.post(url, create_data)
        assert response.status_code == 302

        user_project = Project.objects.filter(nama='User Private Project').first()
        assert user_project.owner == user

        # 2. Other user cannot see it in dashboard
        client.force_login(other_user)
        response = client.get(url)
        assert response.status_code == 200

        other_user_projects = response.context['projects']
        assert user_project not in other_user_projects

        # 3. Other user cannot view detail
        detail_url = reverse('dashboard:project_detail', kwargs={'pk': user_project.pk})
        response = client.get(detail_url)
        assert response.status_code == 404

        # 4. Other user cannot edit
        edit_url = reverse('dashboard:project_edit', kwargs={'pk': user_project.pk})
        response = client.get(edit_url)
        assert response.status_code == 404

        # 5. Other user cannot delete
        delete_url = reverse('dashboard:project_delete', kwargs={'pk': user_project.pk})
        response = client.post(delete_url)
        assert response.status_code == 404

        # Verify project still exists and is active
        user_project.refresh_from_db()
        assert user_project.is_active is True

        # 6. Other user cannot duplicate
        duplicate_url = reverse('dashboard:project_duplicate', kwargs={'pk': user_project.pk})
        response = client.get(duplicate_url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestFilteringSortingPaginationWorkflow:
    """Integration test for filtering, sorting, and pagination."""

    def test_advanced_filtering_and_sorting(self, client, user):
        """Test filtering and sorting combinations."""
        from dashboard.models import Project
        from datetime import date, timedelta

        client.force_login(user)

        # Create diverse projects
        projects_data = [
            {'nama': 'Alpha APBN 2024', 'tahun': 2024, 'sumber': 'APBN', 'anggaran': 1000000000},
            {'nama': 'Beta APBD 2024', 'tahun': 2024, 'sumber': 'APBD', 'anggaran': 2000000000},
            {'nama': 'Gamma APBN 2025', 'tahun': 2025, 'sumber': 'APBN', 'anggaran': 3000000000},
            {'nama': 'Delta APBD 2025', 'tahun': 2025, 'sumber': 'APBD', 'anggaran': 4000000000},
            {'nama': 'Epsilon APBN 2025', 'tahun': 2025, 'sumber': 'APBN', 'anggaran': 5000000000},
        ]

        for data in projects_data:
            Project.objects.create(
                owner=user,
                nama=data['nama'],
                tahun_project=data['tahun'],
                sumber_dana=data['sumber'],
                lokasi_project='Jakarta',
                nama_client='Client',
                anggaran_owner=Decimal(data['anggaran']),
            )

        url = reverse('dashboard:dashboard')

        # 1. Filter by search
        response = client.get(url, {'search': 'APBN'})
        assert response.status_code == 200
        projects = response.context['projects']
        assert all('APBN' in p.nama for p in projects)

        # 2. Sort by name A-Z
        response = client.get(url, {'sort_by': 'nama'})
        projects = list(response.context['projects'])
        names = [p.nama for p in projects]
        assert names == sorted(names)

        # 3. Sort by name Z-A
        response = client.get(url, {'sort_by': '-nama'})
        projects = list(response.context['projects'])
        names = [p.nama for p in projects]
        assert names == sorted(names, reverse=True)

        # 4. Combine search + sort
        response = client.get(url, {'search': '2025', 'sort_by': 'nama'})
        projects = list(response.context['projects'])
        assert len(projects) == 3  # Only 2025 projects
        names = [p.nama for p in projects]
        assert names == sorted(names)


@pytest.mark.django_db
class TestTimelineWorkflow:
    """Integration test for timeline-related features."""

    def test_timeline_status_transitions(self, client, user):
        """Test project status changes based on timeline."""
        from dashboard.models import Project
        from datetime import date, timedelta

        client.force_login(user)

        # 1. Create future project (not started)
        future_start = date.today() + timedelta(days=30)
        future_end = date.today() + timedelta(days=395)

        future_project = Project.objects.create(
            owner=user,
            nama='Future Project',
            tahun_project=2025,
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000'),
            tanggal_mulai=future_start,
            tanggal_selesai=future_end,
        )

        # 2. Create active project (ongoing)
        active_start = date.today() - timedelta(days=30)
        active_end = date.today() + timedelta(days=335)

        active_project = Project.objects.create(
            owner=user,
            nama='Active Project',
            tahun_project=2025,
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('2000000000'),
            tanggal_mulai=active_start,
            tanggal_selesai=active_end,
        )

        # 3. Create overdue project
        overdue_start = date.today() - timedelta(days=400)
        overdue_end = date.today() - timedelta(days=35)

        overdue_project = Project.objects.create(
            owner=user,
            nama='Overdue Project',
            tahun_project=2024,
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('3000000000'),
            tanggal_mulai=overdue_start,
            tanggal_selesai=overdue_end,
        )

        # 4. View dashboard and verify all projects visible
        url = reverse('dashboard:dashboard')
        response = client.get(url)
        assert response.status_code == 200

        projects = response.context['projects']
        assert future_project in projects
        assert active_project in projects
        assert overdue_project in projects

        # 5. View each project detail and verify timeline info
        for project in [future_project, active_project, overdue_project]:
            detail_url = reverse('dashboard:project_detail', kwargs={'pk': project.pk})
            response = client.get(detail_url)
            assert response.status_code == 200
            assert 'project' in response.context
            assert response.context['project'].tanggal_mulai is not None
            assert response.context['project'].tanggal_selesai is not None
