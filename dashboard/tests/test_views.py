# dashboard/tests/test_views.py
"""
Tests for dashboard views.

Coverage:
- Dashboard view (list)
- Project CRUD operations
- Formset submission
- Excel upload
- User isolation
- Permissions
- Filtering & sorting
- Pagination
"""

import pytest
from django.urls import reverse
from django.test import Client
from django.utils import timezone
from decimal import Decimal
from datetime import date
from io import BytesIO
import openpyxl


@pytest.mark.django_db
class TestDashboardView:
    """Test suite for dashboard view."""

    def test_dashboard_view_authenticated(self, client, user, project):
        """Test dashboard view with authenticated user."""
        client.force_login(user)
        url = reverse('dashboard:dashboard')
        response = client.get(url)

        assert response.status_code == 200
        assert 'projects' in response.context
        assert project in response.context['projects']

    def test_dashboard_view_anonymous_redirect(self, client):
        """Test that anonymous users are redirected to login."""
        url = reverse('dashboard:dashboard')
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url or 'login' in response.url

    def test_dashboard_shows_own_projects_only(self, client, user, other_user):
        """Test that dashboard only shows user's own projects."""
        from dashboard.models import Project

        # Create project for user
        user_project = Project.objects.create(
            owner=user,
            nama='User Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000'),
            tanggal_mulai=timezone.now().date(),
        )

        # Create project for other_user
        other_project = Project.objects.create(
            owner=other_user,
            nama='Other Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000'),
            tanggal_mulai=timezone.now().date(),
        )

        client.force_login(user)
        url = reverse('dashboard:dashboard')
        response = client.get(url)

        projects = response.context['projects']
        assert user_project in projects
        assert other_project not in projects

    def test_dashboard_excludes_archived_projects(self, client, user, project, archived_project):
        """Test that archived projects are not shown by default."""
        client.force_login(user)
        url = reverse('dashboard:dashboard')
        response = client.get(url)

        projects = response.context['projects']
        assert project in projects  # Active
        assert archived_project not in projects  # Archived

    def test_dashboard_with_search_filter(self, client, user, multiple_projects):
        """Test dashboard with search filter."""
        client.force_login(user)
        url = reverse('dashboard:dashboard')

        # Search for "Project 1"
        response = client.get(url, {'search': 'Project 1'})

        assert response.status_code == 200
        projects = response.context['projects']

        # Should find "Test Project 1"
        assert any('Project 1' in p.nama for p in projects)

    def test_dashboard_with_sort_by(self, client, user, multiple_projects):
        """Test dashboard with sort_by option."""
        client.force_login(user)
        url = reverse('dashboard:dashboard')

        # Sort by name A-Z
        response = client.get(url, {'sort_by': 'nama'})

        assert response.status_code == 200
        projects = list(response.context['projects'])

        # Verify sorting
        names = [p.nama for p in projects]
        assert names == sorted(names)

    def test_dashboard_pagination(self, client, user):
        """Test dashboard pagination (10 items per page)."""
        from dashboard.models import Project

        # Create 15 projects (more than 1 page)
        for i in range(15):
            Project.objects.create(
                owner=user,
                nama=f'Project {i:02d}',
                sumber_dana='APBN',
                lokasi_project='Jakarta',
                nama_client='Client',
                anggaran_owner=Decimal('1000000000'),
                tanggal_mulai=timezone.now().date(),
            )

        client.force_login(user)
        url = reverse('dashboard:dashboard')

        # Page 1
        response = client.get(url)
        assert len(response.context['projects']) == 10

        # Page 2
        response = client.get(url, {'page': 2})
        assert len(response.context['projects']) == 5


@pytest.mark.django_db
class TestProjectDetailView:
    """Test suite for project detail view."""

    def test_project_detail_view(self, client, user, project):
        """Test project detail view."""
        client.force_login(user)
        url = reverse('dashboard:project_detail', kwargs={'pk': project.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['project'] == project

    def test_project_detail_view_not_owner(self, client, other_user, project):
        """Test that non-owner cannot access project detail."""
        client.force_login(other_user)
        url = reverse('dashboard:project_detail', kwargs={'pk': project.pk})
        response = client.get(url)

        # Should get 404 (project not found for this user)
        assert response.status_code == 404

    def test_project_detail_view_archived(self, client, user, archived_project):
        """Test that archived project detail shows 404."""
        client.force_login(user)
        url = reverse('dashboard:project_detail', kwargs={'pk': archived_project.pk})
        response = client.get(url)

        # Should get 404 (filtered by is_active=True)
        assert response.status_code == 404


@pytest.mark.django_db
class TestProjectEditView:
    """Test suite for project edit view."""

    def test_project_edit_get(self, client, user, project):
        """Test GET request to project edit view."""
        client.force_login(user)
        url = reverse('dashboard:project_edit', kwargs={'pk': project.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['project'] == project

    def test_project_edit_post_valid(self, client, user, project):
        """Test POST request to edit project with valid data."""
        client.force_login(user)
        url = reverse('dashboard:project_edit', kwargs={'pk': project.pk})

        data = {
            'nama': 'Updated Project Name',
            'tanggal_mulai': '2025-01-01',
            'sumber_dana': 'APBD',  # Changed
            'lokasi_project': 'Bandung',  # Changed
            'nama_client': 'Updated Client',
            'anggaran_owner': '2000000000',  # Changed
            'week_start_day': '0',
            'week_end_day': '6',
        }

        response = client.post(url, data)

        # Should redirect
        assert response.status_code == 302

        # Check updates
        project.refresh_from_db()
        assert project.nama == 'Updated Project Name'
        assert project.sumber_dana == 'APBD'
        assert project.lokasi_project == 'Bandung'

    def test_project_edit_not_owner(self, client, other_user, project):
        """Test that non-owner cannot edit project."""
        client.force_login(other_user)
        url = reverse('dashboard:project_edit', kwargs={'pk': project.pk})
        response = client.get(url)

        # Should get 404
        assert response.status_code == 404

    def test_project_edit_start_change_resets_progress(self, client, user, project):
        """Changing project start date should reset weekly progress and regenerate tahapan."""
        from detail_project.models import (
            Klasifikasi,
            SubKlasifikasi,
            Pekerjaan,
            TahapPelaksanaan,
            PekerjaanTahapan,
            PekerjaanProgressWeekly,
        )
        from datetime import timedelta

        project.owner = user
        project.tanggal_mulai = date(2025, 1, 1)
        project.tanggal_selesai = date(2025, 3, 1)
        project.week_start_day = 0
        project.week_end_day = 6
        project.save()

        klas = Klasifikasi.objects.create(project=project, name='K', ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name='Sub', ordering_index=1)
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode='PK-1',
            snapshot_uraian='Pekerjaan Uji',
            snapshot_satuan='m2',
            ordering_index=1,
        )

        week_start = project.tanggal_mulai
        week_end = week_start + timedelta(days=6)
        tahapan = TahapPelaksanaan.objects.create(
            project=project,
            nama='Week 1',
            urutan=0,
            tanggal_mulai=week_start,
            tanggal_selesai=week_end,
            is_auto_generated=True,
            generation_mode='weekly',
        )
        PekerjaanTahapan.objects.create(pekerjaan=pekerjaan, tahapan=tahapan, proporsi_volume=Decimal('50.0'))
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan,
            project=project,
            week_number=1,
            week_start_date=week_start,
            week_end_date=week_end,
            proportion=Decimal('50.0'),
        )

        client.force_login(user)
        url = reverse('dashboard:project_edit', kwargs={'pk': project.pk})
        new_start = date(2025, 2, 1)
        response = client.post(
            url,
            {
                'nama': project.nama,
                'tanggal_mulai': new_start.strftime('%Y-%m-%d'),
                'tanggal_selesai': project.tanggal_selesai.strftime('%Y-%m-%d'),
                'sumber_dana': project.sumber_dana,
                'lokasi_project': project.lokasi_project,
                'nama_client': project.nama_client,
                'anggaran_owner': str(project.anggaran_owner),
                'week_start_day': str(project.week_start_day or 0),
                'week_end_day': str(project.week_end_day or 6),
            },
        )

        assert response.status_code == 302
        project.refresh_from_db()
        assert project.tanggal_mulai == new_start

        assert PekerjaanProgressWeekly.objects.filter(project=project).count() == 0
        assert PekerjaanTahapan.objects.filter(tahapan__project=project).count() == 0

        auto_tahapan = TahapPelaksanaan.objects.filter(project=project, is_auto_generated=True).order_by('urutan')
        assert auto_tahapan.exists()
        assert auto_tahapan.first().tanggal_mulai == new_start


@pytest.mark.django_db
class TestProjectDeleteView:
    """Test suite for project delete view (soft delete)."""

    def test_project_delete_get(self, client, user, project):
        """Test GET request shows delete confirmation."""
        client.force_login(user)
        url = reverse('dashboard:project_delete', kwargs={'pk': project.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'project' in response.context

    def test_project_delete_post(self, client, user, project):
        """Test POST request performs soft delete."""
        client.force_login(user)
        url = reverse('dashboard:project_delete', kwargs={'pk': project.pk})

        response = client.post(url)

        # Should redirect
        assert response.status_code == 302

        # Check soft delete (is_active=False)
        project.refresh_from_db()
        assert project.is_active is False

        # Project still exists in database
        from dashboard.models import Project
        assert Project.objects.filter(pk=project.pk).exists()

    def test_project_delete_not_owner(self, client, other_user, project):
        """Test that non-owner cannot delete project."""
        client.force_login(other_user)
        url = reverse('dashboard:project_delete', kwargs={'pk': project.pk})
        response = client.post(url)

        # Should get 404
        assert response.status_code == 404

        # Project should still be active
        project.refresh_from_db()
        assert project.is_active is True


@pytest.mark.django_db
class TestProjectDuplicateView:
    """Test suite for project duplicate view."""

    def test_project_duplicate_get(self, client, user, project):
        """Test GET request shows duplicate form."""
        client.force_login(user)
        url = reverse('dashboard:project_duplicate', kwargs={'pk': project.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert 'original_project' in response.context

    def test_project_duplicate_post_valid(self, client, user, project):
        """Test POST request creates duplicate."""
        from dashboard.models import Project

        original_count = Project.objects.count()

        client.force_login(user)
        url = reverse('dashboard:project_duplicate', kwargs={'pk': project.pk})

        data = {
            'nama': 'Duplicated Project',
            'tanggal_mulai': str(project.tanggal_mulai),
            'sumber_dana': project.sumber_dana,
            'lokasi_project': project.lokasi_project,
            'nama_client': project.nama_client,
            'anggaran_owner': str(project.anggaran_owner),
        }

        response = client.post(url, data)

        # Should redirect
        assert response.status_code == 302

        # Should create new project
        assert Project.objects.count() == original_count + 1

        # Find the new project
        new_project = Project.objects.filter(nama='Duplicated Project').first()
        assert new_project is not None
        assert new_project.pk != project.pk
        assert new_project.owner == user

    def test_project_duplicate_not_owner(self, client, other_user, project):
        """Test that non-owner cannot duplicate project."""
        client.force_login(other_user)
        url = reverse('dashboard:project_duplicate', kwargs={'pk': project.pk})
        response = client.get(url)

        # Should get 404
        assert response.status_code == 404


@pytest.mark.django_db
class TestFormsetSubmission:
    """Test suite for dashboard formset submission."""

    def test_formset_create_single_project(self, client, user):
        """Test creating a project via formset."""
        from dashboard.models import Project

        client.force_login(user)
        url = reverse('dashboard:dashboard')

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-nama': 'Formset Project',
            'form-0-tanggal_mulai': '2025-01-01',
            'form-0-sumber_dana': 'APBN',
            'form-0-lokasi_project': 'Jakarta',
            'form-0-nama_client': 'Client',
            'form-0-anggaran_owner': '1000000000',
        }

        response = client.post(url, data)

        # Should redirect
        assert response.status_code == 302

        # Should create project
        project = Project.objects.filter(nama='Formset Project').first()
        assert project is not None
        assert project.owner == user

    def test_formset_create_multiple_projects(self, client, user):
        """Test creating multiple projects via formset."""
        from dashboard.models import Project

        original_count = Project.objects.count()

        client.force_login(user)
        url = reverse('dashboard:dashboard')

        data = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            # Project 1
            'form-0-nama': 'Project A',
            'form-0-tanggal_mulai': '2025-01-01',
            'form-0-sumber_dana': 'APBN',
            'form-0-lokasi_project': 'Jakarta',
            'form-0-nama_client': 'Client A',
            'form-0-anggaran_owner': '1000000000',
            # Project 2
            'form-1-nama': 'Project B',
            'form-1-tanggal_mulai': '2025-01-01',
            'form-1-sumber_dana': 'APBD',
            'form-1-lokasi_project': 'Bandung',
            'form-1-nama_client': 'Client B',
            'form-1-anggaran_owner': '2000000000',
            # Project 3
            'form-2-nama': 'Project C',
            'form-2-tanggal_mulai': '2025-01-01',
            'form-2-sumber_dana': 'APBN',
            'form-2-lokasi_project': 'Surabaya',
            'form-2-nama_client': 'Client C',
            'form-2-anggaran_owner': '3000000000',
        }

        response = client.post(url, data)

        # Should redirect
        assert response.status_code == 302

        # Should create 3 projects
        assert Project.objects.count() == original_count + 3

    def test_formset_validation_error(self, client, user):
        """Test formset with validation errors."""
        client.force_login(user)
        url = reverse('dashboard:dashboard')

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            # Missing required fields
            'form-0-nama': 'AB',  # Too short (min 3 chars)
            'form-0-tahun_project': '1800',  # Out of range
        }

        response = client.post(url, data)

        # Should show form with errors (not redirect)
        assert response.status_code == 200
        assert 'formset' in response.context


@pytest.mark.django_db
class TestExcelUpload:
    """Test suite for Excel upload functionality."""

    def test_excel_upload_valid_file(self, client, user):
        """Test uploading a valid Excel file."""
        from dashboard.models import Project
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create Excel file in memory
        wb = openpyxl.Workbook()
        ws = wb.active

        # Headers
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

        # Data row
        ws.append([
            'Excel Project', 2025, 'APBN', 'Jakarta', 'Client',
            1000000000, '2025-01-01', '2025-12-31', 365,
            '', '', '', '', '', '', '', '', '', '', 'Test', 'Infra'
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

        client.force_login(user)
        url = reverse('dashboard:project_upload')

        response = client.post(url, {'file': excel_file})

        # Should redirect (success)
        assert response.status_code == 302

        # Should create project
        project = Project.objects.filter(nama='Excel Project').first()
        assert project is not None
        assert project.owner == user

    def test_excel_upload_invalid_extension(self, client, user):
        """Test uploading file with wrong extension."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create fake .txt file
        txt_file = SimpleUploadedFile('file.txt', b'test', content_type='text/plain')

        client.force_login(user)
        url = reverse('dashboard:project_upload')

        response = client.post(url, {'file': txt_file})

        # Should show form with error
        assert response.status_code == 200
        # Check for error in messages or form

    def test_excel_upload_missing_headers(self, client, user):
        """Test uploading Excel with missing required headers."""
        # Create Excel with incomplete headers
        wb = openpyxl.Workbook()
        ws = wb.active

        # Only partial headers
        ws.append(['nama', 'tahun_project'])
        ws.append(['Project', 2025])

        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        client.force_login(user)
        url = reverse('dashboard:project_upload')

        response = client.post(url, {'file': excel_file})

        # Should show error message
        assert response.status_code == 200
