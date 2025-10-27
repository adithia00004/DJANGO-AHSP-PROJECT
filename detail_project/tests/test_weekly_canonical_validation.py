"""
Test suite for Weekly Canonical Storage validation and input modes.

Tests cover:
1. Backend validation (total progress ≤ 100%)
2. Daily mode: aggregate days to weeks
3. Monthly mode: split to daily, aggregate to weeks
4. API V2 endpoints
5. Visual feedback scenarios
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model

from detail_project.models import (
    TahapPelaksanaan,
    PekerjaanTahapan,
    Pekerjaan,
    PekerjaanProgressWeekly
)
from dashboard.models import Project

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def project_sunday_start(db):
    """Project starting on Sunday (2025-10-26) for testing week boundaries"""
    user = User.objects.create_user(username='testuser', password='testpass123')
    project = Project.objects.create(
        nama='Test Project Weekly',
        tanggal_mulai=date(2025, 10, 26),  # Sunday
        tanggal_selesai=date(2025, 12, 31),
        created_by=user
    )
    return project


@pytest.fixture
def weekly_tahapan(db, project_sunday_start):
    """Create weekly tahapan with correct boundaries"""
    from detail_project.views_api_tahapan import _generate_weekly_tahapan

    tahapan_list = _generate_weekly_tahapan(
        project_sunday_start,
        week_start_day=0,  # Monday
        week_end_day=6     # Sunday
    )
    created = TahapPelaksanaan.objects.bulk_create(tahapan_list)
    return created


@pytest.fixture
def daily_tahapan(db, project_sunday_start):
    """Create daily tahapan"""
    from detail_project.views_api_tahapan import _generate_daily_tahapan

    tahapan_list = _generate_daily_tahapan(project_sunday_start)
    # Only create first 14 days for testing
    created = TahapPelaksanaan.objects.bulk_create(tahapan_list[:14])
    return created


@pytest.fixture
def monthly_tahapan(db, project_sunday_start):
    """Create monthly tahapan"""
    from detail_project.views_api_tahapan import _generate_monthly_tahapan

    tahapan_list = _generate_monthly_tahapan(project_sunday_start)
    created = TahapPelaksanaan.objects.bulk_create(tahapan_list)
    return created


@pytest.fixture
def test_pekerjaan(db, project_sunday_start):
    """Create a test pekerjaan"""
    pekerjaan = Pekerjaan.objects.create(
        project=project_sunday_start,
        kode='TEST-001',
        nama='Test Pekerjaan for Validation',
        volume=100,
        satuan='m²'
    )
    return pekerjaan


# =============================================================================
# BACKEND VALIDATION TESTS (≤100%)
# =============================================================================

@pytest.mark.django_db
class TestProgressValidation:
    """Test progress validation (total ≤ 100%)"""

    def test_valid_progress_100_percent(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test valid progress totaling exactly 100%"""
        client.force_login(project_sunday_start.created_by)

        url = reverse('detail_project:api_v2_assign_weekly', kwargs={'project_id': project_sunday_start.id})

        payload = {
            'assignments': [
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 1, 'proportion': 50.00},
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 2, 'proportion': 50.00},
            ]
        }

        response = client.post(url, payload, content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['created_count'] == 2

        # Verify saved to canonical storage
        weekly_progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan)
        assert weekly_progress.count() == 2
        total = sum(float(wp.proportion) for wp in weekly_progress)
        assert total == 100.0

    def test_invalid_progress_over_100_percent(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test invalid progress totaling > 100% should be rejected"""
        client.force_login(project_sunday_start.created_by)

        url = reverse('detail_project:api_v2_assign_weekly', kwargs={'project_id': project_sunday_start.id})

        payload = {
            'assignments': [
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 1, 'proportion': 60.00},
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 2, 'proportion': 50.00},
            ]
        }

        response = client.post(url, payload, content_type='application/json')

        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        assert 'validation_errors' in data
        assert 'exceeds 100%' in data['error']

        # Verify NOT saved to canonical storage
        weekly_progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan)
        assert weekly_progress.count() == 0

    def test_valid_progress_under_100_percent(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test valid progress totaling < 100% (should be allowed with warning)"""
        client.force_login(project_sunday_start.created_by)

        url = reverse('detail_project:api_v2_assign_weekly', kwargs={'project_id': project_sunday_start.id})

        payload = {
            'assignments': [
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 1, 'proportion': 30.00},
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 2, 'proportion': 40.00},
            ]
        }

        response = client.post(url, payload, content_type='application/json')

        # Should succeed (warnings don't block save)
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        # Verify saved to canonical storage
        weekly_progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan)
        assert weekly_progress.count() == 2
        total = sum(float(wp.proportion) for wp in weekly_progress)
        assert total == 70.0


# =============================================================================
# DAILY MODE INPUT TESTS (Aggregate to Weekly)
# =============================================================================

@pytest.mark.django_db
class TestDailyModeInput:
    """Test daily input aggregation to weekly canonical storage"""

    def test_daily_input_aggregates_to_weekly(self, project_sunday_start, test_pekerjaan, daily_tahapan):
        """Test that daily inputs correctly aggregate to weeks"""
        # Simulate daily inputs
        # Week 1 (Sun): Day 1 = 10%
        # Week 2 (Mon-Sun): Day 2-8 = 10% each = 70%

        # Create daily assignments
        daily_inputs = {
            1: 10.0,   # Day 1 (Sunday) - Week 1
            2: 10.0,   # Day 2 (Monday) - Week 2
            3: 10.0,   # Day 3 (Tuesday) - Week 2
            4: 10.0,   # Day 4 (Wednesday) - Week 2
            5: 10.0,   # Day 5 (Thursday) - Week 2
            6: 10.0,   # Day 6 (Friday) - Week 2
            7: 10.0,   # Day 7 (Saturday) - Week 2
            8: 10.0,   # Day 8 (Sunday) - Week 2
        }

        # Expected weekly aggregation
        # Week 1: 10% (1 day)
        # Week 2: 70% (7 days)
        expected_weekly = {
            1: 10.0,
            2: 70.0
        }

        # Simulate the aggregation logic from frontend
        weeklyProportions = {}
        project_start = project_sunday_start.tanggal_mulai

        for day_num, proportion in daily_inputs.items():
            tahap = daily_tahapan[day_num - 1]
            day_date = tahap.tanggal_mulai
            diff_days = (day_date - project_start).days
            week_number = (diff_days // 7) + 1

            if week_number not in weeklyProportions:
                weeklyProportions[week_number] = 0
            weeklyProportions[week_number] += proportion

        # Verify aggregation
        assert weeklyProportions == expected_weekly

        # Total should be 80%
        total = sum(weeklyProportions.values())
        assert total == 80.0

    def test_daily_input_partial_week(self, project_sunday_start, test_pekerjaan, daily_tahapan):
        """Test daily input with partial first week"""
        # First week only has Sunday (1 day)
        # Input: Day 1 (Sunday) = 100%

        daily_inputs = {1: 100.0}

        weeklyProportions = {}
        project_start = project_sunday_start.tanggal_mulai

        for day_num, proportion in daily_inputs.items():
            tahap = daily_tahapan[day_num - 1]
            day_date = tahap.tanggal_mulai
            diff_days = (day_date - project_start).days
            week_number = (diff_days // 7) + 1

            if week_number not in weeklyProportions:
                weeklyProportions[week_number] = 0
            weeklyProportions[week_number] += proportion

        # Week 1 should have 100%
        assert weeklyProportions[1] == 100.0


# =============================================================================
# MONTHLY MODE INPUT TESTS (Split to Daily, Aggregate to Weekly)
# =============================================================================

@pytest.mark.django_db
class TestMonthlyModeInput:
    """Test monthly input split to daily and aggregation to weekly"""

    def test_monthly_input_splits_to_daily_then_weekly(self, project_sunday_start):
        """Test monthly input correctly splits to daily then aggregates to weekly"""
        # Simulate: October (partial, 26-31) = 6 days = 60%
        month_start = date(2025, 10, 26)  # Sunday
        month_end = date(2025, 10, 31)    # Friday
        month_proportion = 60.0

        days_in_month = (month_end - month_start).days + 1  # 6 days
        daily_proportion = month_proportion / days_in_month  # 10% per day

        assert days_in_month == 6
        assert daily_proportion == 10.0

        # Aggregate to weekly
        weeklyProportions = {}
        project_start = project_sunday_start.tanggal_mulai

        current_date = month_start
        while current_date <= month_end:
            diff_days = (current_date - project_start).days
            week_number = (diff_days // 7) + 1

            if week_number not in weeklyProportions:
                weeklyProportions[week_number] = 0
            weeklyProportions[week_number] += daily_proportion

            current_date += timedelta(days=1)

        # Expected:
        # Week 1 (26 Oct - Sun): 1 day = 10%
        # Week 2 (27-31 Oct - Mon-Fri): 5 days = 50%
        assert weeklyProportions[1] == 10.0
        assert weeklyProportions[2] == 50.0

        # Total should equal month_proportion
        total = sum(weeklyProportions.values())
        assert total == 60.0

    def test_monthly_input_full_month(self, project_sunday_start):
        """Test monthly input for full month (November)"""
        # November 2025: 30 days
        month_start = date(2025, 11, 1)   # Saturday
        month_end = date(2025, 11, 30)    # Sunday
        month_proportion = 100.0

        days_in_month = (month_end - month_start).days + 1  # 30 days
        daily_proportion = month_proportion / days_in_month  # 3.33% per day

        assert days_in_month == 30
        assert abs(daily_proportion - 3.333333) < 0.01

        # Aggregate to weekly
        weeklyProportions = {}
        project_start = project_sunday_start.tanggal_mulai

        current_date = month_start
        while current_date <= month_end:
            diff_days = (current_date - project_start).days
            week_number = (diff_days // 7) + 1

            if week_number not in weeklyProportions:
                weeklyProportions[week_number] = 0
            weeklyProportions[week_number] += daily_proportion

            current_date += timedelta(days=1)

        # November spans multiple weeks
        # Total should equal month_proportion (with rounding)
        total = sum(weeklyProportions.values())
        assert abs(total - 100.0) < 0.01  # Allow small rounding error


# =============================================================================
# API V2 ENDPOINTS TESTS
# =============================================================================

@pytest.mark.django_db
class TestAPIV2Endpoints:
    """Test API V2 endpoints for canonical storage"""

    def test_regenerate_tahapan_v2_weekly(self, client, project_sunday_start):
        """Test regenerate tahapan API V2 with weekly mode"""
        client.force_login(project_sunday_start.created_by)

        url = reverse('detail_project:api_v2_regenerate_tahapan', kwargs={'project_id': project_sunday_start.id})

        payload = {
            'mode': 'weekly',
            'week_start_day': 0,  # Monday
            'week_end_day': 6     # Sunday
        }

        response = client.post(url, payload, content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['mode'] == 'weekly'
        assert 'tahapan_created' in data

        # Verify tahapan created
        tahapan = TahapPelaksanaan.objects.filter(
            project=project_sunday_start,
            is_auto_generated=True,
            generation_mode='weekly'
        )
        assert tahapan.count() > 0

        # First week should start on Sunday (project start)
        first_week = tahapan.first()
        assert first_week.tanggal_mulai == date(2025, 10, 26)  # Sunday
        assert first_week.tanggal_selesai == date(2025, 10, 26)  # Same day (partial week)

    def test_regenerate_tahapan_v2_daily(self, client, project_sunday_start):
        """Test regenerate tahapan API V2 with daily mode"""
        client.force_login(project_sunday_start.created_by)

        url = reverse('detail_project:api_v2_regenerate_tahapan', kwargs={'project_id': project_sunday_start.id})

        payload = {
            'mode': 'daily',
            'week_start_day': 0,
            'week_end_day': 6
        }

        response = client.post(url, payload, content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['mode'] == 'daily'

        # Verify daily tahapan created
        tahapan = TahapPelaksanaan.objects.filter(
            project=project_sunday_start,
            is_auto_generated=True,
            generation_mode='daily'
        )
        assert tahapan.count() > 0

    def test_reset_progress_api(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test reset progress API endpoint"""
        client.force_login(project_sunday_start.created_by)

        # First, create some progress
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=test_pekerjaan,
            project=project_sunday_start,
            week_number=1,
            week_start_date=date(2025, 10, 26),
            week_end_date=date(2025, 10, 26),
            proportion=Decimal('50.00')
        )
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=test_pekerjaan,
            project=project_sunday_start,
            week_number=2,
            week_start_date=date(2025, 10, 27),
            week_end_date=date(2025, 11, 2),
            proportion=Decimal('50.00')
        )

        # Verify created
        assert PekerjaanProgressWeekly.objects.filter(project=project_sunday_start).count() == 2

        # Reset
        url = reverse('detail_project:api_v2_reset_progress', kwargs={'project_id': project_sunday_start.id})
        response = client.post(url, {}, content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['deleted_count'] == 2

        # Verify deleted
        assert PekerjaanProgressWeekly.objects.filter(project=project_sunday_start).count() == 0


# =============================================================================
# INTEGRATION TESTS (End-to-End)
# =============================================================================

@pytest.mark.django_db
class TestIntegrationE2E:
    """End-to-end integration tests for complete workflows"""

    def test_weekly_input_mode_switch_lossless(self, client, project_sunday_start, test_pekerjaan):
        """Test: Input in weekly → switch to daily → switch back → data preserved"""
        client.force_login(project_sunday_start.created_by)

        # Step 1: Create weekly tahapan
        regen_url = reverse('detail_project:api_v2_regenerate_tahapan', kwargs={'project_id': project_sunday_start.id})
        response = client.post(regen_url, {'mode': 'weekly', 'week_start_day': 0, 'week_end_day': 6}, content_type='application/json')
        assert response.status_code == 200

        # Step 2: Input progress in weekly mode
        assign_url = reverse('detail_project:api_v2_assign_weekly', kwargs={'project_id': project_sunday_start.id})
        payload = {
            'assignments': [
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 1, 'proportion': 25.00},
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 2, 'proportion': 75.00},
            ]
        }
        response = client.post(assign_url, payload, content_type='application/json')
        assert response.status_code == 200

        # Verify canonical storage
        weekly_progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan).order_by('week_number')
        assert weekly_progress.count() == 2
        assert float(weekly_progress[0].proportion) == 25.0
        assert float(weekly_progress[1].proportion) == 75.0

        # Step 3: Switch to daily mode
        response = client.post(regen_url, {'mode': 'daily', 'week_start_day': 0, 'week_end_day': 6}, content_type='application/json')
        assert response.status_code == 200

        # Step 4: Switch back to weekly mode
        response = client.post(regen_url, {'mode': 'weekly', 'week_start_day': 0, 'week_end_day': 6}, content_type='application/json')
        assert response.status_code == 200

        # Step 5: Verify data preserved (lossless)
        weekly_progress_after = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan).order_by('week_number')
        assert weekly_progress_after.count() == 2
        assert float(weekly_progress_after[0].proportion) == 25.0
        assert float(weekly_progress_after[1].proportion) == 75.0

        # Total unchanged
        total = sum(float(wp.proportion) for wp in weekly_progress_after)
        assert total == 100.0

    def test_validation_error_does_not_save(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test: Validation error prevents save to canonical storage"""
        client.force_login(project_sunday_start.created_by)

        # Try to save progress > 100%
        url = reverse('detail_project:api_v2_assign_weekly', kwargs={'project_id': project_sunday_start.id})
        payload = {
            'assignments': [
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 1, 'proportion': 60.00},
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 2, 'proportion': 55.00},  # Total 115%
            ]
        }
        response = client.post(url, payload, content_type='application/json')

        # Should be rejected
        assert response.status_code == 400

        # Verify nothing saved
        weekly_progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan)
        assert weekly_progress.count() == 0
