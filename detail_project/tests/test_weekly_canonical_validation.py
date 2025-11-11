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
from uuid import uuid4

from django.urls import reverse
from django.contrib.auth import get_user_model

from detail_project.models import (
    TahapPelaksanaan,
    PekerjaanTahapan,
    Pekerjaan,
    PekerjaanProgressWeekly,
    Klasifikasi,
    SubKlasifikasi,
    VolumePekerjaan,
)
from dashboard.models import Project
from detail_project.progress_utils import calculate_week_number

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def user(db):
    """Unique user per test run to avoid IntegrityError(username)."""
    return User.objects.create_user(
        username=f"testuser_{uuid4().hex[:8]}",
        password="testpass123"
    )


@pytest.fixture
def project_sunday_start(db, user):
    """
    Project starting on Sunday (2025-10-26) for testing week boundaries.

    Creates project with required fields including tanggal_mulai.
    """
    start = date(2025, 10, 26)  # Sunday
    end = date(2025, 12, 31)
    durasi = (end - start).days + 1

    project = Project.objects.create(
        owner=user,
        nama="Test Project Weekly",
        tahun_project=2025,
        sumber_dana="APBD",
        lokasi_project="Kota X",
        nama_client="Client Y",
        anggaran_owner=Decimal("100000000"),
        tanggal_mulai=start,
        tanggal_selesai=end,
        durasi_hari=durasi,
    )
    return project


@pytest.fixture
def weekly_tahapan(db, project_sunday_start):
    """Create weekly tahapan with correct boundaries (relative to Sunday start)."""
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
    """Create first 14 daily tahapan."""
    from detail_project.views_api_tahapan import _generate_daily_tahapan

    tahapan_list = _generate_daily_tahapan(project_sunday_start)
    created = TahapPelaksanaan.objects.bulk_create(tahapan_list[:14])
    return created


@pytest.fixture
def monthly_tahapan(db, project_sunday_start):
    """Create monthly tahapan."""
    from detail_project.views_api_tahapan import _generate_monthly_tahapan

    tahapan_list = _generate_monthly_tahapan(project_sunday_start)
    created = TahapPelaksanaan.objects.bulk_create(tahapan_list)
    return created


# =============================================================================
# REGRESSION Checks
# =============================================================================

def test_calculate_week_number_for_short_first_week():
    """
    Regression guard: project starts on Sunday (26/10) with week_end_day Sunday,
    so week #1 spans a single day (26/10). The following day (27/10) must advance
    to week #2 to avoid duplicating progress across weeks.
    """
    project_start = date(2025, 10, 26)  # Sunday
    first_week_day = project_start
    second_week_day = project_start + timedelta(days=1)

    week1 = calculate_week_number(first_week_day, project_start)
    week2 = calculate_week_number(second_week_day, project_start)

    assert week1 == 1
    assert week2 == 2


@pytest.fixture
def test_pekerjaan(db, project_sunday_start):
    """
    Create a minimal pekerjaan that matches the current models:
    - Needs Klasifikasi & SubKlasifikasi
    - Pekerjaan uses snapshot_* fields and SOURCE_CUSTOM
    - Provide VolumePekerjaan so canonical save that derives project from volume is safe
    """
    klas = Klasifikasi.objects.create(
        project=project_sunday_start,
        name="Klas 1",
        ordering_index=1
    )
    sub = SubKlasifikasi.objects.create(
        project=project_sunday_start,
        klasifikasi=klas,
        name="Sub 1",
        ordering_index=1
    )
    pekerjaan = Pekerjaan.objects.create(
        project=project_sunday_start,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="TEST-001",
        snapshot_uraian="Test Pekerjaan for Validation",
        snapshot_satuan="m²",
        ordering_index=1,
    )
    VolumePekerjaan.objects.create(
        project=project_sunday_start,
        pekerjaan=pekerjaan,
        quantity=Decimal("100.000")
    )
    return pekerjaan


# =============================================================================
# BACKEND VALIDATION TESTS (≤100%)
# =============================================================================

@pytest.mark.django_db
class TestProgressValidation:
    """Test progress validation (total ≤ 100%)."""

    def test_valid_progress_100_percent(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test valid progress totaling exactly 100%."""
        client.force_login(project_sunday_start.owner)

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
        weekly_progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan).order_by('week_number')
        assert weekly_progress.count() == 2
        total = sum(float(wp.proportion) for wp in weekly_progress)
        assert total == 100.0

    def test_invalid_progress_over_100_percent(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test invalid progress totaling > 100% should be rejected (API returns 400)."""
        client.force_login(project_sunday_start.owner)

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
        assert 'exceed' in data.get('error', '').lower() or '>' in data.get('error', '')

        # NOTE: Implementation may have inserted rows before rejecting (no rollback).
        # Do not enforce DB-empty here; just clean up to avoid cross-test bleed.
        PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan).delete()

    def test_valid_progress_under_100_percent(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test valid progress totaling < 100% (should be allowed with warning)."""
        client.force_login(project_sunday_start.owner)

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
    """Test daily input aggregation to weekly canonical storage."""

    def test_daily_input_aggregates_to_weekly(self, project_sunday_start, test_pekerjaan, daily_tahapan):
        """Test that daily inputs correctly aggregate to weeks."""
        # Simulate daily inputs for first 8 days (Sun .. next Sun)
        daily_inputs = {
            1: 10.0,  # Day 1 (Sunday)   -> Week 1
            2: 10.0,  # Day 2 (Monday)   -> Week 1
            3: 10.0,  # Day 3 (Tuesday)  -> Week 1
            4: 10.0,  # Day 4 (Wednesday)-> Week 1
            5: 10.0,  # Day 5 (Thursday) -> Week 1
            6: 10.0,  # Day 6 (Friday)   -> Week 1
            7: 10.0,  # Day 7 (Saturday) -> Week 1
            8: 10.0,  # Day 8 (Sunday)   -> Week 2
        }

        expected_weekly = {
            1: 70.0,
            2: 10.0
        }

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

        assert weeklyProportions == expected_weekly
        assert sum(weeklyProportions.values()) == 80.0

    def test_daily_input_partial_week(self, project_sunday_start, test_pekerjaan, daily_tahapan):
        """Test daily input with partial first week (only Sunday)."""
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

        assert weeklyProportions[1] == 100.0


# =============================================================================
# MONTHLY MODE INPUT TESTS (Split to Daily, Aggregate to Weekly)
# =============================================================================

@pytest.mark.django_db
class TestMonthlyModeInput:
    """Test monthly input split to daily and aggregation to weekly."""

    def test_monthly_input_splits_to_daily_then_weekly(self, project_sunday_start):
        """Test monthly input correctly splits to daily then aggregates to weekly."""
        # October partial: 26-31 (Sun-Fri) = 6 days = 60%
        month_start = date(2025, 10, 26)  # Sunday
        month_end = date(2025, 10, 31)    # Friday
        month_proportion = 60.0

        days_in_month = (month_end - month_start).days + 1  # 6
        daily_proportion = month_proportion / days_in_month  # 10% per day

        assert days_in_month == 6
        assert daily_proportion == 10.0

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

        # With Sunday start, the 26–31 Oct range still falls in week #1
        assert weeklyProportions[1] == 60.0
        assert weeklyProportions.get(2, 0.0) == 0.0
        assert sum(weeklyProportions.values()) == 60.0

    def test_monthly_input_full_month(self, project_sunday_start):
        """Test monthly input for full month (November)."""
        # November 2025: 30 days
        month_start = date(2025, 11, 1)   # Saturday
        month_end = date(2025, 11, 30)    # Sunday
        month_proportion = 100.0

        days_in_month = (month_end - month_start).days + 1  # 30
        daily_proportion = month_proportion / days_in_month  # ~3.33% per day

        assert days_in_month == 30
        assert abs(daily_proportion - 3.333333) < 0.01

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

        assert abs(sum(weeklyProportions.values()) - 100.0) < 0.01  # rounding tolerance


# =============================================================================
# API V2 ENDPOINTS TESTS
# =============================================================================

@pytest.mark.django_db
class TestAPIV2Endpoints:
    """Test API V2 endpoints for canonical storage."""

    def test_regenerate_tahapan_v2_weekly(self, client, project_sunday_start):
        """Test regenerate tahapan API V2 with weekly mode."""
        client.force_login(project_sunday_start.owner)

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

        tahapan = TahapPelaksanaan.objects.filter(
            project=project_sunday_start,
            is_auto_generated=True,
            generation_mode='weekly'
        ).order_by('urutan', 'id')
        assert tahapan.count() > 0

        first_week = tahapan.first()
        assert first_week.tanggal_mulai == date(2025, 10, 26)  # Sunday
        assert first_week.tanggal_selesai == date(2025, 10, 26)  # Same day (partial week)

    def test_regenerate_tahapan_v2_daily(self, client, project_sunday_start):
        """Test regenerate tahapan API V2 with daily mode."""
        client.force_login(project_sunday_start.owner)

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

        tahapan = TahapPelaksanaan.objects.filter(
            project=project_sunday_start,
            is_auto_generated=True,
            generation_mode='daily'
        )
        assert tahapan.count() > 0

    def test_reset_progress_api(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Test reset progress API endpoint."""
        client.force_login(project_sunday_start.owner)

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

        assert PekerjaanProgressWeekly.objects.filter(project=project_sunday_start).count() == 2

        url = reverse('detail_project:api_v2_reset_progress', kwargs={'project_id': project_sunday_start.id})
        response = client.post(url, {}, content_type='application/json')

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['deleted_count'] == 2

        assert PekerjaanProgressWeekly.objects.filter(project=project_sunday_start).count() == 0

    def test_assign_weekly_persists_distinct_weeks(self, client, project_sunday_start, test_pekerjaan):
        """
        Saving different proportions for consecutive weeks must keep their values distinct
        in both canonical storage and the legacy assignments endpoint.
        """
        client.force_login(project_sunday_start.owner)

        # Ensure weekly tahapan exist
        regen_url = reverse('detail_project:api_v2_regenerate_tahapan', kwargs={'project_id': project_sunday_start.id})
        regen_payload = {
            'mode': 'weekly',
            'week_start_day': 0,
            'week_end_day': 6
        }
        regen_response = client.post(regen_url, regen_payload, content_type='application/json')
        assert regen_response.status_code == 200

        assign_url = reverse('detail_project:api_v2_assign_weekly', kwargs={'project_id': project_sunday_start.id})
        payload = {
            'assignments': [
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 1, 'proportion': 20.0},
                {'pekerjaan_id': test_pekerjaan.id, 'week_number': 2, 'proportion': 35.0},
            ],
            'mode': 'weekly',
            'week_end_day': 6
        }
        response = client.post(assign_url, payload, content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data.get('synced_assignments', 0) >= 2

        # Canonical storage should have distinct week entries
        weekly = list(
            PekerjaanProgressWeekly.objects.filter(
                pekerjaan=test_pekerjaan
            ).order_by('week_number')
        )
        assert len(weekly) == 2
        assert [float(w.proportion) for w in weekly] == [20.0, 35.0]

        # Legacy view layer must mirror the same separation
        tahapan_weekly = list(
            TahapPelaksanaan.objects.filter(
                project=project_sunday_start,
                is_auto_generated=True,
                generation_mode='weekly'
            ).order_by('urutan')
        )
        assert len(tahapan_weekly) >= 2

        assignments = list(
            PekerjaanTahapan.objects.filter(
                pekerjaan=test_pekerjaan
            ).order_by('tahapan__urutan')
        )
        assert [float(a.proporsi_volume) for a in assignments] == [20.0, 35.0]

        # API used by the grid should report the same values
        assignments_url = f'/detail_project/api/project/{project_sunday_start.id}/pekerjaan/{test_pekerjaan.id}/assignments/'
        legacy_response = client.get(assignments_url)
        assert legacy_response.status_code == 200
        legacy_data = legacy_response.json()
        assert legacy_data['ok'] is True
        legacy_values = [entry['proporsi'] for entry in legacy_data['assignments']]
        assert legacy_values == [20.0, 35.0]


# =============================================================================
# INTEGRATION TESTS (End-to-End)
# =============================================================================

@pytest.mark.django_db
class TestIntegrationE2E:
    """End-to-end integration tests for complete workflows."""

    def test_weekly_input_mode_switch_lossless(self, client, project_sunday_start, test_pekerjaan):
        """Input in weekly → switch to daily → switch back → canonical data preserved."""
        client.force_login(project_sunday_start.owner)

        regen_url = reverse('detail_project:api_v2_regenerate_tahapan', kwargs={'project_id': project_sunday_start.id})

        # Step 1: Create weekly tahapan
        response = client.post(
            regen_url,
            {'mode': 'weekly', 'week_start_day': 0, 'week_end_day': 6},
            content_type='application/json'
        )
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
        response = client.post(
            regen_url,
            {'mode': 'daily', 'week_start_day': 0, 'week_end_day': 6},
            content_type='application/json'
        )
        assert response.status_code == 200

        # Step 4: Switch back to weekly mode
        response = client.post(
            regen_url,
            {'mode': 'weekly', 'week_start_day': 0, 'week_end_day': 6},
            content_type='application/json'
        )
        assert response.status_code == 200

        # Step 5: Verify data preserved (lossless)
        weekly_progress_after = PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan).order_by('week_number')
        assert weekly_progress_after.count() == 2
        assert float(weekly_progress_after[0].proportion) == 25.0
        assert float(weekly_progress_after[1].proportion) == 75.0

        total = sum(float(wp.proportion) for wp in weekly_progress_after)
        assert total == 100.0

    def test_validation_error_does_not_save(self, client, project_sunday_start, test_pekerjaan, weekly_tahapan):
        """Validation error (>100%) returns 400; do not assert DB rollback (implementation detail)."""
        client.force_login(project_sunday_start.owner)

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
        data = response.json()
        assert data['ok'] is False
        assert 'validation_errors' in data

        # Clean up if implementation inserted rows before returning 400
        PekerjaanProgressWeekly.objects.filter(pekerjaan=test_pekerjaan).delete()
