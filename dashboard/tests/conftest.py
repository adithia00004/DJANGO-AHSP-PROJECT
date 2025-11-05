# dashboard/tests/conftest.py
"""
Pytest fixtures for dashboard tests.

Provides reusable test fixtures for:
- Users
- Projects
- Test data
"""

import pytest
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def other_user(db):
    """Create another test user for isolation tests."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def project_data():
    """Valid project data for tests."""
    return {
        'nama': 'Test Project',
        'tahun_project': 2025,
        'sumber_dana': 'APBN',
        'lokasi_project': 'Jakarta',
        'nama_client': 'Test Client',
        'anggaran_owner': Decimal('1000000000.00'),
        'tanggal_mulai': date.today(),
        'tanggal_selesai': date.today() + timedelta(days=365),
        'durasi_hari': 365,
        'deskripsi': 'Test project description',
        'kategori': 'Infrastructure',
    }


@pytest.fixture
def minimal_project_data():
    """Minimal valid project data (only required fields)."""
    return {
        'nama': 'Minimal Project',
        'tahun_project': 2025,
        'sumber_dana': 'APBN',
        'lokasi_project': 'Jakarta',
        'nama_client': 'Test Client',
        'anggaran_owner': Decimal('500000000.00'),
    }


@pytest.fixture
def project(db, user, project_data):
    """Create a test project."""
    from dashboard.models import Project

    project_data_copy = project_data.copy()
    project_data_copy['owner'] = user

    return Project.objects.create(**project_data_copy)


@pytest.fixture
def multiple_projects(db, user):
    """Create multiple test projects."""
    from dashboard.models import Project

    projects = []
    for i in range(5):
        proj = Project.objects.create(
            owner=user,
            nama=f'Test Project {i+1}',
            tahun_project=2025,
            sumber_dana='APBN' if i % 2 == 0 else 'APBD',
            lokasi_project=f'Location {i+1}',
            nama_client=f'Client {i+1}',
            anggaran_owner=Decimal(f'{(i+1)*100000000}.00'),
            tanggal_mulai=date.today() - timedelta(days=i*10),
            tanggal_selesai=date.today() + timedelta(days=(365-i*10)),
        )
        projects.append(proj)

    return projects


@pytest.fixture
def archived_project(db, user):
    """Create an archived (soft-deleted) project."""
    from dashboard.models import Project

    return Project.objects.create(
        owner=user,
        nama='Archived Project',
        tahun_project=2024,
        sumber_dana='APBN',
        lokasi_project='Jakarta',
        nama_client='Old Client',
        anggaran_owner=Decimal('500000000.00'),
        is_active=False,  # Archived
    )


@pytest.fixture
def overdue_project(db, user):
    """Create a project that is overdue."""
    from dashboard.models import Project

    return Project.objects.create(
        owner=user,
        nama='Overdue Project',
        tahun_project=2024,
        sumber_dana='APBN',
        lokasi_project='Jakarta',
        nama_client='Test Client',
        anggaran_owner=Decimal('500000000.00'),
        tanggal_mulai=date.today() - timedelta(days=400),
        tanggal_selesai=date.today() - timedelta(days=35),  # 35 days overdue
        durasi_hari=365,
    )


@pytest.fixture
def future_project(db, user):
    """Create a project that hasn't started yet."""
    from dashboard.models import Project

    return Project.objects.create(
        owner=user,
        nama='Future Project',
        tahun_project=2025,
        sumber_dana='APBN',
        lokasi_project='Jakarta',
        nama_client='Test Client',
        anggaran_owner=Decimal('500000000.00'),
        tanggal_mulai=date.today() + timedelta(days=30),  # Starts in 30 days
        tanggal_selesai=date.today() + timedelta(days=395),
        durasi_hari=365,
    )
