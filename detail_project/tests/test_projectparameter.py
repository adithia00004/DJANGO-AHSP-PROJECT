# detail_project/tests/test_projectparameter.py
"""
Tests for ProjectParameter model.

Run with:
    pytest detail_project/tests/test_projectparameter.py -v
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from detail_project.models import ProjectParameter
from dashboard.models import Project


@pytest.mark.django_db
class TestProjectParameterModel:
    """Test suite for ProjectParameter model."""

    def test_create_parameter_success(self, user):
        """Test creating a parameter with all fields."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='panjang',
            value=Decimal('10.500'),
            label='Panjang (m)',
            unit='meter',
            description='Parameter panjang untuk perhitungan volume'
        )

        assert param.id is not None
        assert param.project == project
        assert param.name == 'panjang'
        assert param.value == Decimal('10.500')
        assert param.label == 'Panjang (m)'
        assert param.unit == 'meter'
        assert param.description == 'Parameter panjang untuk perhitungan volume'
        assert param.created_at is not None
        assert param.updated_at is not None

    def test_create_parameter_minimal_fields(self, user):
        """Test creating parameter with only required fields."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='koef',
            value=Decimal('1.200')
        )

        assert param.id is not None
        assert param.label == ''
        assert param.unit == ''
        assert param.description == ''

    def test_parameter_str_representation(self, user):
        """Test __str__ method."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='lebar',
            value=Decimal('5.000'),
            unit='meter'
        )

        expected = f"{project.index_project} - lebar = 5.000 meter"
        assert str(param) == expected

    def test_unique_constraint_project_name(self, user):
        """Test that (project, name) must be unique."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        # Create first parameter
        ProjectParameter.objects.create(
            project=project,
            name='panjang',
            value=Decimal('10.000')
        )

        # Try to create duplicate (should fail)
        with pytest.raises(IntegrityError):
            ProjectParameter.objects.create(
                project=project,
                name='panjang',  # Same name!
                value=Decimal('20.000')
            )

    def test_same_name_different_projects_allowed(self, user, other_user):
        """Test that same parameter name is allowed for different projects."""
        from datetime import date

        project1 = Project.objects.create(
            owner=user,
            nama='Project 1',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        project2 = Project.objects.create(
            owner=other_user,
            nama='Project 2',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        # Create parameter with same name for different projects (should succeed)
        param1 = ProjectParameter.objects.create(
            project=project1,
            name='panjang',
            value=Decimal('10.000')
        )

        param2 = ProjectParameter.objects.create(
            project=project2,
            name='panjang',  # Same name, different project
            value=Decimal('15.000')
        )

        assert param1.id != param2.id
        assert param1.name == param2.name
        assert param1.project != param2.project

    def test_name_auto_lowercase(self, user):
        """Test that name is automatically converted to lowercase."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='PANJANG',  # Uppercase
            value=Decimal('10.000')
        )

        param.refresh_from_db()
        assert param.name == 'panjang'  # Should be lowercase

    def test_name_with_space_validation(self, user):
        """Test that name cannot contain spaces."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter(
            project=project,
            name='koef beton',  # Has space!
            value=Decimal('1.200')
        )

        with pytest.raises(ValidationError) as exc_info:
            param.save()

        assert 'name' in exc_info.value.message_dict
        assert 'cannot contain spaces' in exc_info.value.message_dict['name'][0]

    def test_parameter_ordering(self, user):
        """Test that parameters are ordered by name."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        # Create parameters in random order
        ProjectParameter.objects.create(project=project, name='z_param', value=Decimal('1'))
        ProjectParameter.objects.create(project=project, name='a_param', value=Decimal('2'))
        ProjectParameter.objects.create(project=project, name='m_param', value=Decimal('3'))

        # Fetch all parameters
        params = list(ProjectParameter.objects.filter(project=project))

        # Should be ordered by name
        assert params[0].name == 'a_param'
        assert params[1].name == 'm_param'
        assert params[2].name == 'z_param'

    def test_parameter_cascade_delete_on_project_delete(self, user):
        """Test that parameters are deleted when project is deleted."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        # Create multiple parameters
        ProjectParameter.objects.create(project=project, name='panjang', value=Decimal('10'))
        ProjectParameter.objects.create(project=project, name='lebar', value=Decimal('5'))
        ProjectParameter.objects.create(project=project, name='tinggi', value=Decimal('3'))

        assert ProjectParameter.objects.filter(project=project).count() == 3

        # Delete project
        project_id = project.id
        project.delete()

        # Parameters should be deleted (CASCADE)
        assert ProjectParameter.objects.filter(project_id=project_id).count() == 0

    def test_update_parameter_value(self, user):
        """Test updating parameter value."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='koef',
            value=Decimal('1.000')
        )

        original_id = param.id
        original_created = param.created_at

        # Update value
        param.value = Decimal('1.500')
        param.save()

        param.refresh_from_db()

        assert param.id == original_id  # ID unchanged
        assert param.created_at == original_created  # created_at unchanged
        assert param.updated_at > original_created  # updated_at changed
        assert param.value == Decimal('1.500')  # Value updated

    def test_parameter_with_zero_value(self, user):
        """Test parameter can have zero value (edge case)."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='offset',
            value=Decimal('0.000')
        )

        assert param.value == Decimal('0.000')

    def test_parameter_with_large_decimal(self, user):
        """Test parameter with large decimal value."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        param = ProjectParameter.objects.create(
            project=project,
            name='big_value',
            value=Decimal('999999999999999.999')
        )

        assert param.value == Decimal('999999999999999.999')

    def test_get_parameters_for_project(self, user):
        """Test retrieving all parameters for a project."""
        from datetime import date
        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        # Create parameters
        ProjectParameter.objects.create(project=project, name='panjang', value=Decimal('10'))
        ProjectParameter.objects.create(project=project, name='lebar', value=Decimal('5'))
        ProjectParameter.objects.create(project=project, name='tinggi', value=Decimal('3'))

        # Retrieve via reverse relationship
        params = project.parameters.all()

        assert params.count() == 3
        param_names = {p.name for p in params}
        assert param_names == {'panjang', 'lebar', 'tinggi'}


@pytest.mark.django_db
class TestProjectParameterQueryPerformance:
    """Test query performance and indexing."""

    def test_index_on_project_and_name(self, user):
        """Test that index exists for efficient lookups."""
        from datetime import date
        from django.db import connection

        project = Project.objects.create(
            owner=user,
            nama='Test Project',
            tanggal_mulai=date.today(),
            sumber_dana='APBN',
            lokasi_project='Jakarta',
            nama_client='Client',
            anggaran_owner=Decimal('1000000000')
        )

        # Create many parameters
        for i in range(100):
            ProjectParameter.objects.create(
                project=project,
                name=f'param_{i:03d}',
                value=Decimal(str(i))
            )

        # Query should use index (verify no full table scan)
        with connection.cursor() as cursor:
            cursor.execute("""
                EXPLAIN
                SELECT * FROM detail_project_projectparameter
                WHERE project_id = %s AND name = %s
            """, [project.id, 'param_050'])

            explain_output = cursor.fetchall()
            explain_text = ' '.join([str(row) for row in explain_output])

            # Should use index, not Seq Scan
            assert 'Index' in explain_text or 'index' in explain_text.lower()
