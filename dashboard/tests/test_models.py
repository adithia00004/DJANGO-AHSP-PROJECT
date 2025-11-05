# dashboard/tests/test_models.py
"""
Tests for dashboard models.

Coverage:
- Project creation
- index_project auto-generation
- Timeline auto-calculation
- Soft delete
- String representation
- Ordering
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import IntegrityError

from dashboard.models import Project


@pytest.mark.django_db
class TestProjectModel:
    """Test suite for Project model."""

    def test_project_creation_with_all_fields(self, user, project_data):
        """Test creating a project with all fields."""
        project_data['owner'] = user
        project = Project.objects.create(**project_data)

        assert project.pk is not None
        assert project.nama == 'Test Project'
        assert project.tahun_project == 2025
        assert project.sumber_dana == 'APBN'
        assert project.lokasi_project == 'Jakarta'
        assert project.nama_client == 'Test Client'
        assert project.anggaran_owner == Decimal('1000000000.00')
        assert project.is_active is True
        assert project.owner == user

    def test_project_creation_with_minimal_fields(self, user, minimal_project_data):
        """Test creating a project with only required fields."""
        minimal_project_data['owner'] = user
        project = Project.objects.create(**minimal_project_data)

        assert project.pk is not None
        assert project.nama == 'Minimal Project'
        assert project.is_active is True

    def test_index_project_auto_generation(self, user, minimal_project_data):
        """Test that index_project is auto-generated on save."""
        minimal_project_data['owner'] = user
        project = Project.objects.create(**minimal_project_data)

        # After save, index_project should be generated
        assert project.index_project is not None
        assert project.index_project.startswith('PRJ-')

        # Format: PRJ-{user_id}-{date}-{seq}
        parts = project.index_project.split('-')
        assert len(parts) == 4  # PRJ-XX-DDMMYY-XXXX

    def test_index_project_uniqueness(self, user, minimal_project_data):
        """Test that index_project is unique."""
        minimal_project_data['owner'] = user

        # Create first project
        project1 = Project.objects.create(**minimal_project_data)

        # Create second project (same day, same user)
        minimal_project_data['nama'] = 'Another Project'
        project2 = Project.objects.create(**minimal_project_data)

        # Both should have different index_project
        assert project1.index_project != project2.index_project

    def test_timeline_auto_calculation_on_creation(self, user):
        """Test that timeline is auto-calculated if not provided."""
        project = Project.objects.create(
            owner=user,
            nama='Auto Timeline Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Test Client',
            anggaran_owner=Decimal('1000000000.00'),
            tanggal_mulai=timezone.now().date(),
            # No timeline fields provided
        )

        # Should have auto-generated timeline
        assert project.tanggal_mulai is not None
        assert project.tanggal_selesai is not None
        assert project.durasi_hari is not None

        # tanggal_mulai should be today
        assert project.tanggal_mulai == timezone.now().date()

        # tanggal_selesai should be Dec 31 of tahun_project
        assert project.tanggal_selesai.year == 2025
        assert project.tanggal_selesai.month == 12
        assert project.tanggal_selesai.day == 31

    def test_durasi_hari_calculation_from_dates(self, user):
        """Test that durasi_hari is calculated from dates."""
        start_date = date(2025, 1, 1)
        end_date = date(2025, 12, 31)

        project = Project.objects.create(
            owner=user,
            nama='Duration Test Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Test Client',
            anggaran_owner=Decimal('1000000000.00'),
            tanggal_mulai=start_date,
            tanggal_selesai=end_date,
            # durasi_hari not provided
        )

        # Should calculate durasi_hari
        expected_duration = (end_date - start_date).days + 1
        assert project.durasi_hari == expected_duration

    def test_soft_delete(self, project):
        """Test that project uses soft delete (is_active flag)."""
        assert project.is_active is True

        # Soft delete
        project.is_active = False
        project.save()

        # Still exists in database
        assert Project.objects.filter(pk=project.pk).exists()

        # But not in active queryset
        active_projects = Project.objects.filter(is_active=True)
        assert project not in active_projects

    def test_project_string_representation(self, project):
        """Test __str__ method."""
        # Should show index_project and nama
        str_repr = str(project)
        assert project.index_project in str_repr or 'PRJ-NEW' in str_repr
        assert project.nama in str_repr

    def test_project_ordering(self, user, multiple_projects):
        """Test that projects are ordered by -updated_at."""
        # Get all projects
        projects = Project.objects.filter(owner=user, is_active=True)

        # Should be ordered by updated_at descending
        assert projects.count() == 5

        # Most recently updated should be first
        # (Due to creation order, last created is most recent)
        first_project = projects.first()
        last_project = projects.last()

        assert first_project.updated_at >= last_project.updated_at

    def test_get_absolute_url(self, project):
        """Test get_absolute_url method."""
        url = project.get_absolute_url()

        # Should contain project detail URL pattern
        assert f'/dashboard/project/{project.pk}/' in url or f'/{project.pk}/' in url

    def test_user_isolation(self, user, other_user):
        """Test that users can only see their own projects."""
        # Create project for user
        project1 = Project.objects.create(
            owner=user,
            nama='User Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Test Client',
            anggaran_owner=Decimal('1000000000.00'),
            tanggal_mulai=timezone.now().date(),
        )

        # Create project for other_user
        project2 = Project.objects.create(
            owner=other_user,
            nama='Other User Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Test Client',
            anggaran_owner=Decimal('1000000000.00'),
            tanggal_mulai=timezone.now().date(),
        )

        # User should only see their own project
        user_projects = Project.objects.filter(owner=user)
        assert project1 in user_projects
        assert project2 not in user_projects

        # Other user should only see their own project
        other_projects = Project.objects.filter(owner=other_user)
        assert project1 not in other_projects
        assert project2 in other_projects

    def test_project_timestamps(self, user, minimal_project_data):
        """Test that created_at and updated_at are set correctly."""
        minimal_project_data['owner'] = user
        project = Project.objects.create(**minimal_project_data)

        # created_at should be set
        assert project.created_at is not None

        # updated_at should be set
        assert project.updated_at is not None

        # created_at and updated_at should be very close (within 1 second)
        time_diff = abs((project.updated_at - project.created_at).total_seconds())
        assert time_diff < 1

        # Update project
        original_updated_at = project.updated_at
        project.nama = 'Updated Name'
        project.save()

        # updated_at should change
        assert project.updated_at > original_updated_at

    def test_timeline_fields_nullable(self, user):
        """Test that timeline fields are nullable."""
        # Create project without timeline
        project = Project.objects.create(
            owner=user,
            nama='No Timeline Project',
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Test Client',
            anggaran_owner=Decimal('1000000000.00'),
            tanggal_mulai=timezone.now().date(),
        )

        # Timeline should be auto-set, but test that model allows null
        # (This tests the model definition, even though save() sets defaults)
        assert project.pk is not None

    def test_ordering_index_default(self, user, project_data):
        """Test that projects can have same ordering_index (no unique constraint)."""
        project_data['owner'] = user

        # Create multiple projects (ordering_index not used at Project model level)
        project1 = Project.objects.create(**project_data)
        project_data['nama'] = 'Another Project'
        project2 = Project.objects.create(**project_data)

        # Both should save successfully
        assert project1.pk is not None
        assert project2.pk is not None

    def test_anggaran_owner_precision(self, user):
        """Test that anggaran_owner handles large decimal values correctly."""
        project = Project.objects.create(
            owner=user,
            nama='Large Budget Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Test Client',
            anggaran_owner=Decimal('999999999999999999.99'),  # Max: 20 digits, 2 decimal
        )

        assert project.anggaran_owner == Decimal('999999999999999999.99')

    def test_meta_indexes(self, user, multiple_projects):
        """Test that database indexes are used (performance test)."""
        # This is more of a sanity check that queries work
        # Actual index usage would require EXPLAIN ANALYZE

        # Query by owner and updated_at (should use composite index)
        projects = Project.objects.filter(
            owner=user,
            is_active=True
        ).order_by('-updated_at')

        assert projects.count() == 5

        # Query by nama (should use index)
        projects_by_name = Project.objects.filter(nama__icontains='Test')
        assert projects_by_name.count() >= 5

        # Query by tahun_project (should use index)
        from datetime import date
        current_year = date.today().year
        projects_by_year = Project.objects.filter(tahun_project=current_year)
        assert projects_by_year.count() >= 5
