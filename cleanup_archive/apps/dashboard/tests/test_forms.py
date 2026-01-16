# dashboard/tests/test_forms.py
"""
Tests for dashboard forms.

Coverage:
- ProjectForm validation
- Required fields
- Anggaran parsing (various formats)
- Timeline validation
- Kategori validation
- Clean methods
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from dashboard.forms import ProjectForm, ProjectFilterForm, UploadProjectForm


@pytest.mark.django_db
class TestProjectForm:
    """Test suite for ProjectForm."""

    def test_form_with_valid_data(self, project_data):
        """Test form with all valid data."""
        form = ProjectForm(data=project_data)

        assert form.is_valid(), form.errors
        project = form.save(commit=False)
        assert project.nama == 'Test Project'

    def test_form_with_minimal_required_fields(self, minimal_project_data):
        """Test form with only required fields."""
        form = ProjectForm(data=minimal_project_data)

        assert form.is_valid(), form.errors

    def test_required_fields_validation(self):
        """Test that required fields are enforced."""
        # Empty form should be invalid
        form = ProjectForm(data={})

        assert not form.is_valid()

        # Check that required fields have errors
        required_fields = [
            'nama', 'tanggal_mulai', 'sumber_dana',
            'lokasi_project', 'nama_client', 'anggaran_owner'
        ]

        for field in required_fields:
            assert field in form.errors, f"{field} should have error"

    def test_nama_min_length_validation(self, minimal_project_data):
        """Test nama must be at least 3 characters."""
        # Valid: 3 characters
        data = minimal_project_data.copy()
        data['nama'] = 'ABC'
        form = ProjectForm(data=data)
        assert form.is_valid()

        # Invalid: 2 characters
        data['nama'] = 'AB'
        form = ProjectForm(data=data)
        assert not form.is_valid()
        assert 'nama' in form.errors

        # Invalid: 1 character
        data['nama'] = 'A'
        form = ProjectForm(data=data)
        assert not form.is_valid()

    def test_tahun_project_auto_calculated(self, minimal_project_data, user):
        """Test that tahun_project is auto-calculated from tanggal_mulai."""
        # Note: tahun_project is now auto-calculated in model save(), not in form
        # This test validates that form accepts tanggal_mulai and model handles tahun_project
        from dashboard.models import Project

        data = minimal_project_data.copy()
        data['tanggal_mulai'] = date(2023, 6, 15)

        form = ProjectForm(data=data)
        assert form.is_valid(), form.errors

        # Save the project through the model
        project = form.save(commit=False)
        project.owner = user
        project.save()

        # Verify tahun_project was auto-calculated
        assert project.tahun_project == 2023

    def test_anggaran_parsing_numeric(self, minimal_project_data):
        """Test anggaran parsing with plain numbers."""
        data = minimal_project_data.copy()

        # Plain number
        data['anggaran_owner'] = '1000000000'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('1000000000')

    def test_anggaran_parsing_with_rp_prefix(self, minimal_project_data):
        """Test anggaran parsing with 'Rp' prefix."""
        data = minimal_project_data.copy()

        # With Rp prefix
        data['anggaran_owner'] = 'Rp 1000000000'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('1000000000')

    def test_anggaran_parsing_with_thousands_separator(self, minimal_project_data):
        """Test anggaran parsing with thousands separator."""
        data = minimal_project_data.copy()

        # Dot as thousands separator
        data['anggaran_owner'] = '1.000.000.000'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('1000000000')

        # Comma as thousands separator
        data['anggaran_owner'] = '1,000,000,000'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('1000000000')

    def test_anggaran_parsing_with_decimal(self, minimal_project_data):
        """Test anggaran parsing with decimal places."""
        data = minimal_project_data.copy()

        # Comma as decimal separator (European style)
        data['anggaran_owner'] = '1.000.000,50'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('1000000.50')

        # Dot as decimal separator (US style)
        data['anggaran_owner'] = '1000000.50'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('1000000.50')

    def test_anggaran_parsing_with_full_formatting(self, minimal_project_data):
        """Test anggaran parsing with full formatting (Rp + thousands + decimals)."""
        data = minimal_project_data.copy()

        data['anggaran_owner'] = 'Rp 15.000.000,00'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('15000000.00')

    def test_anggaran_negative_value_invalid(self, minimal_project_data):
        """Test that negative anggaran is invalid."""
        data = minimal_project_data.copy()

        data['anggaran_owner'] = '-1000000'
        form = ProjectForm(data=data)
        assert not form.is_valid()
        assert 'anggaran_owner' in form.errors

    def test_anggaran_zero_value(self, minimal_project_data):
        """Test that zero anggaran is allowed."""
        data = minimal_project_data.copy()

        data['anggaran_owner'] = '0'
        form = ProjectForm(data=data)
        assert form.is_valid()
        assert form.cleaned_data['anggaran_owner'] == Decimal('0')

    def test_kategori_alphanumeric_validation(self, minimal_project_data):
        """Test kategori only allows alphanumeric characters."""
        data = minimal_project_data.copy()

        # Valid: alphanumeric
        data['kategori'] = 'Infrastructure123'
        form = ProjectForm(data=data)
        assert form.is_valid()

        # Invalid: special characters
        data['kategori'] = 'Infrastructure@#$'
        form = ProjectForm(data=data)
        assert not form.is_valid()
        assert 'kategori' in form.errors

    def test_timeline_validation_end_after_start(self, minimal_project_data):
        """Test that tanggal_selesai must be after tanggal_mulai."""
        data = minimal_project_data.copy()

        # Valid: end after start
        data['tanggal_mulai'] = date(2025, 1, 1)
        data['tanggal_selesai'] = date(2025, 12, 31)
        form = ProjectForm(data=data)
        assert form.is_valid()

        # Invalid: end before start
        data['tanggal_mulai'] = date(2025, 12, 31)
        data['tanggal_selesai'] = date(2025, 1, 1)
        form = ProjectForm(data=data)
        assert not form.is_valid()
        assert 'tanggal_selesai' in form.errors

    def test_timeline_durasi_auto_calculation(self, minimal_project_data):
        """Test that durasi_hari is auto-calculated from dates."""
        data = minimal_project_data.copy()

        start = date(2025, 1, 1)
        end = date(2025, 1, 10)
        data['tanggal_mulai'] = start
        data['tanggal_selesai'] = end
        # Don't provide durasi_hari

        form = ProjectForm(data=data)
        assert form.is_valid()

        # Should calculate durasi_hari
        expected_duration = (end - start).days + 1
        assert form.cleaned_data['durasi_hari'] == expected_duration

    def test_timeline_tanggal_selesai_from_durasi(self, minimal_project_data):
        """Test that tanggal_selesai is calculated from tanggal_mulai + durasi."""
        data = minimal_project_data.copy()

        start = date(2025, 1, 1)
        data['tanggal_mulai'] = start
        data['durasi_hari'] = 365
        # Don't provide tanggal_selesai

        form = ProjectForm(data=data)
        assert form.is_valid()

        # Should calculate tanggal_selesai
        expected_end = start + timedelta(days=364)  # 365 days including start
        assert form.cleaned_data['tanggal_selesai'] == expected_end

    def test_timeline_tanggal_selesai_from_durasi(self, minimal_project_data):
        """Test that tanggal_selesai is calculated from tanggal_mulai + durasi."""
        data = minimal_project_data.copy()

        start = date(2025, 1, 1)
        data['tanggal_mulai'] = start
        data['durasi_hari'] = 365
        # Don't provide tanggal_selesai

        form = ProjectForm(data=data)
        assert form.is_valid()

        # Should calculate tanggal_selesai (durasi - 1 because day 1 is included)
        expected_end = start + timedelta(days=364)
        assert form.cleaned_data['tanggal_selesai'] == expected_end

    def test_form_strips_whitespace(self, minimal_project_data):
        """Test that form strips whitespace from text fields."""
        data = minimal_project_data.copy()

        # Add whitespace
        data['nama'] = '  Test Project  '
        data['sumber_dana'] = '  APBN  '
        data['lokasi_project'] = '  Jakarta  '

        form = ProjectForm(data=data)
        assert form.is_valid()

        # Should be stripped
        assert form.cleaned_data['nama'] == 'Test Project'
        assert form.cleaned_data['sumber_dana'] == 'APBN'
        assert form.cleaned_data['lokasi_project'] == 'Jakarta'


@pytest.mark.django_db
class TestProjectFilterForm:
    """Test suite for ProjectFilterForm."""

    def test_filter_form_all_empty(self):
        """Test filter form with no filters."""
        form = ProjectFilterForm(data={})

        assert form.is_valid()
        assert form.cleaned_data['search'] == ''
        assert form.cleaned_data['sort_by'] is None or form.cleaned_data['sort_by'] == ''

    def test_filter_form_with_search(self):
        """Test filter form with search query."""
        form = ProjectFilterForm(data={'search': 'test project'})

        assert form.is_valid()
        assert form.cleaned_data['search'] == 'test project'

    def test_filter_form_with_sort_by(self):
        """Test filter form with sort_by option."""
        form = ProjectFilterForm(data={'sort_by': '-updated_at'})

        assert form.is_valid()
        assert form.cleaned_data['sort_by'] == '-updated_at'

    def test_filter_form_invalid_sort_by(self):
        """Test filter form with invalid sort_by value."""
        form = ProjectFilterForm(data={'sort_by': 'invalid_field'})

        # Should still be valid (choice validation)
        # But the value won't match any choice
        assert not form.is_valid()


@pytest.mark.django_db
class TestUploadProjectForm:
    """Test suite for UploadProjectForm."""

    def test_upload_form_with_xlsx_file(self):
        """Test upload form with .xlsx file."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a fake .xlsx file
        file_content = b'fake excel content'
        uploaded_file = SimpleUploadedFile(
            'projects.xlsx',
            file_content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        form = UploadProjectForm(files={'file': uploaded_file})

        assert form.is_valid()

    def test_upload_form_with_invalid_extension(self):
        """Test upload form with non-.xlsx file."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a file with wrong extension
        file_content = b'fake content'
        uploaded_file = SimpleUploadedFile(
            'projects.txt',
            file_content,
            content_type='text/plain'
        )

        form = UploadProjectForm(files={'file': uploaded_file})

        assert not form.is_valid()
        assert 'file' in form.errors

    def test_upload_form_no_file(self):
        """Test upload form without file."""
        form = UploadProjectForm(files={})

        assert not form.is_valid()
        assert 'file' in form.errors
