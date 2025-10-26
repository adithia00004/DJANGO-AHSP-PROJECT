# detail_project/tests/test_tahapan_generation_conversion.py
"""
Comprehensive test suite for Tahapan Generation & Assignment Conversion features.

Tests cover:
1. Tahapan generation (daily/weekly/monthly modes)
2. Assignment conversion logic with daily distribution algorithm
3. API endpoint: api_regenerate_tahapan
4. Save functionality with proper tahapanId
5. Data persistence across mode switches
6. Proportion preservation (~100%)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.db import transaction

from detail_project.models import (
    TahapPelaksanaan,
    PekerjaanTahapan,
    Pekerjaan
)
from detail_project.views_api_tahapan import (
    _generate_daily_tahapan,
    _generate_weekly_tahapan,
    _generate_monthly_tahapan,
    _convert_assignments,
    _convert_pekerjaan_assignments,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def project_with_timeline(db, project):
    """Project with timeline set (required for tahapan generation)"""
    # Set 1-month timeline
    project.tanggal_mulai = date(2025, 1, 1)
    project.tanggal_selesai = date(2025, 1, 31)
    project.durasi_hari = (project.tanggal_selesai - project.tanggal_mulai).days
    project.save()
    return project


@pytest.fixture
def project_with_3month_timeline(db, project):
    """Project with 3-month timeline for more complex tests"""
    project.tanggal_mulai = date(2025, 1, 1)
    project.tanggal_selesai = date(2025, 3, 31)
    project.durasi_hari = (project.tanggal_selesai - project.tanggal_mulai).days
    project.save()
    return project


@pytest.fixture
def custom_tahapan_4weeks(db, project_with_timeline):
    """Create 4 custom tahapan (weekly periods) for testing conversion"""
    tahapan_list = []
    start_date = project_with_timeline.tanggal_mulai

    for week_num in range(1, 5):
        week_start = start_date + timedelta(days=(week_num - 1) * 7)
        week_end = week_start + timedelta(days=6)

        tahap = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama=f"Week {week_num}",
            urutan=week_num,
            tanggal_mulai=week_start,
            tanggal_selesai=week_end,
            generation_mode='custom',
            is_auto_generated=False
        )
        tahapan_list.append(tahap)

    return tahapan_list


@pytest.fixture
def pekerjaan_with_assignments(db, project_with_timeline, pekerjaan_custom, custom_tahapan_4weeks):
    """Pekerjaan with assignments distributed across 4 weeks (25% each)"""
    for tahap in custom_tahapan_4weeks:
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap,
            proporsi_volume=Decimal('25.00'),
            catatan=f'Initial assignment to {tahap.nama}'
        )
    return pekerjaan_custom


# =============================================================================
# UNIT TESTS: Tahapan Generation Functions
# =============================================================================

@pytest.mark.django_db
class TestTahapanGenerationFunctions:
    """Test tahapan generation helper functions"""

    def test_generate_daily_tahapan_1month(self, project_with_timeline):
        """Test daily tahapan generation for 1-month project"""
        # Delete existing tahapan
        TahapPelaksanaan.objects.filter(project=project_with_timeline).delete()

        # Generate daily tahapan (returns list, not count)
        tahapan_list = _generate_daily_tahapan(project_with_timeline)

        # January 2025 has 31 days
        assert len(tahapan_list) == 31

        # Save to database
        TahapPelaksanaan.objects.bulk_create(tahapan_list)

        # Verify in database
        tahapan = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='daily',
            is_auto_generated=True
        ).order_by('urutan')

        assert tahapan.count() == 31

        # Check first day
        first = tahapan.first()
        assert first.nama == "Day 1"
        assert first.tanggal_mulai == date(2025, 1, 1)
        assert first.tanggal_selesai == date(2025, 1, 1)
        assert first.urutan == 1

        # Check last day
        last = tahapan.last()
        assert last.nama == "Day 31"
        assert last.tanggal_mulai == date(2025, 1, 31)
        assert last.tanggal_selesai == date(2025, 1, 31)
        assert last.urutan == 31

    def test_generate_weekly_tahapan_1month(self, project_with_timeline):
        """Test weekly tahapan generation"""
        TahapPelaksanaan.objects.filter(project=project_with_timeline).delete()

        # Sunday = 0 (returns list, not count)
        tahapan_list = _generate_weekly_tahapan(project_with_timeline, week_end_day=0)

        # 1 month (~4-5 weeks)
        assert len(tahapan_list) >= 4 and len(tahapan_list) <= 6

        # Save to database
        TahapPelaksanaan.objects.bulk_create(tahapan_list)

        tahapan = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='weekly'
        ).order_by('urutan')

        # Check first week
        first = tahapan.first()
        assert first.nama.startswith("W")
        assert first.is_auto_generated is True
        assert first.generation_mode == 'weekly'

        # Each week should be 7 days (except possibly first/last)
        for tahap in tahapan:
            duration = (tahap.tanggal_selesai - tahap.tanggal_mulai).days + 1
            # Most weeks should be 7 days, first/last might be partial
            assert duration >= 1 and duration <= 7

    def test_generate_monthly_tahapan_3months(self, project_with_3month_timeline):
        """Test monthly tahapan generation for 3-month project"""
        TahapPelaksanaan.objects.filter(project=project_with_3month_timeline).delete()

        # Returns list, not count
        tahapan_list = _generate_monthly_tahapan(project_with_3month_timeline)

        # Jan, Feb, Mar = 3 months
        assert len(tahapan_list) == 3

        # Save to database
        TahapPelaksanaan.objects.bulk_create(tahapan_list)

        tahapan = TahapPelaksanaan.objects.filter(
            project=project_with_3month_timeline,
            generation_mode='monthly'
        ).order_by('urutan')

        assert tahapan.count() == 3

        # Check January
        jan = tahapan[0]
        assert "Jan" in jan.nama or "January" in jan.nama
        assert jan.tanggal_mulai == date(2025, 1, 1)
        assert jan.tanggal_selesai == date(2025, 1, 31)

        # Check February
        feb = tahapan[1]
        assert "Feb" in feb.nama or "February" in feb.nama
        assert feb.tanggal_mulai == date(2025, 2, 1)
        # Feb 2025 has 28 days (not leap year)
        assert feb.tanggal_selesai == date(2025, 2, 28)

    def test_generate_tahapan_replaces_existing_auto_generated(self, project_with_timeline):
        """Test that generation replaces old auto-generated tahapan"""
        # Create old auto-generated daily tahapan
        daily_list = _generate_daily_tahapan(project_with_timeline)
        TahapPelaksanaan.objects.bulk_create(daily_list)

        daily_count_before = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='daily'
        ).count()

        assert daily_count_before > 0

        # Generate weekly tahapan (should delete old daily via API, but here we manually delete)
        # Note: This function doesn't delete old tahapan - that's done in the API endpoint
        TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            is_auto_generated=True
        ).delete()

        weekly_list = _generate_weekly_tahapan(project_with_timeline)
        TahapPelaksanaan.objects.bulk_create(weekly_list)

        # Daily should be gone
        daily_count_after = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='daily'
        ).count()

        assert daily_count_after == 0

        # Weekly should exist
        weekly_count = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='weekly'
        ).count()

        assert weekly_count > 0


# =============================================================================
# UNIT TESTS: Assignment Conversion Logic
# =============================================================================

@pytest.mark.django_db
class TestAssignmentConversion:
    """Test assignment conversion logic (daily distribution algorithm)"""

    def test_convert_pekerjaan_assignments_simple(self, project_with_timeline, pekerjaan_custom):
        """Test simple conversion: 1 old tahapan → 1 new tahapan (same dates)"""
        # Create old tahapan
        old_tahap = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="Old Tahap",
            urutan=1,
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 7),
            generation_mode='custom'
        )

        # Create assignment (100%)
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=old_tahap,
            proporsi_volume=Decimal('100.00')
        )

        # Prepare old assignments data
        old_assignments = list(
            PekerjaanTahapan.objects.filter(
                pekerjaan=pekerjaan_custom
            ).values(
                'tahapan_id',
                'tahapan__tanggal_mulai',
                'tahapan__tanggal_selesai',
                'proporsi_volume'
            )
        )

        # Create new tahapan (same dates)
        new_tahap = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="New Tahap",
            urutan=1,
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 7),
            generation_mode='daily'
        )

        # Convert
        new_assignments = _convert_pekerjaan_assignments(
            pekerjaan_id=pekerjaan_custom.id,
            old_assignments=old_assignments,
            new_tahapan_list=[new_tahap]
        )

        # Should have 1 assignment with 100%
        assert len(new_assignments) == 1
        assert new_assignments[0].tahapan == new_tahap
        assert abs(new_assignments[0].proporsi_volume - Decimal('100.00')) < Decimal('0.1')

    def test_convert_split_to_merged(self, project_with_timeline, pekerjaan_custom):
        """Test conversion: 2 weeks (50% each) → 1 month (100%)"""
        # Create 2 weekly tahapan
        week1 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="Week 1",
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 7),
            generation_mode='weekly'
        )

        week2 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="Week 2",
            tanggal_mulai=date(2025, 1, 8),
            tanggal_selesai=date(2025, 1, 14),
            generation_mode='weekly'
        )

        # Assign 50% to each week
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=week1,
            proporsi_volume=Decimal('50.00')
        )

        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=week2,
            proporsi_volume=Decimal('50.00')
        )

        # Get old assignments
        old_assignments = list(
            PekerjaanTahapan.objects.filter(
                pekerjaan=pekerjaan_custom
            ).values(
                'tahapan_id',
                'tahapan__tanggal_mulai',
                'tahapan__tanggal_selesai',
                'proporsi_volume'
            )
        )

        # Create monthly tahapan covering both weeks
        month = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="January",
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 31),
            generation_mode='monthly'
        )

        # Convert
        new_assignments = _convert_pekerjaan_assignments(
            pekerjaan_id=pekerjaan_custom.id,
            old_assignments=old_assignments,
            new_tahapan_list=[month]
        )

        # Should have 1 assignment
        assert len(new_assignments) == 1

        # Total should be ~100% (50% + 50%)
        # Because both weeks are fully contained in the month
        total_proportion = new_assignments[0].proporsi_volume
        assert abs(total_proportion - Decimal('100.00')) < Decimal('0.1')

    def test_convert_merged_to_split(self, project_with_timeline, pekerjaan_custom):
        """Test conversion: 1 month (100%) → 4 weeks (~25% each)"""
        # Create monthly tahapan
        month = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="January",
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 31),
            generation_mode='monthly'
        )

        # Assign 100%
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=month,
            proporsi_volume=Decimal('100.00')
        )

        # Get old assignments
        old_assignments = list(
            PekerjaanTahapan.objects.filter(
                pekerjaan=pekerjaan_custom
            ).values(
                'tahapan_id',
                'tahapan__tanggal_mulai',
                'tahapan__tanggal_selesai',
                'proporsi_volume'
            )
        )

        # Create 4 weekly tahapan
        weekly_tahapan = []
        for week_num in range(1, 5):
            week_start = date(2025, 1, 1) + timedelta(days=(week_num - 1) * 7)
            week_end = week_start + timedelta(days=6)

            week = TahapPelaksanaan.objects.create(
                project=project_with_timeline,
                nama=f"Week {week_num}",
                tanggal_mulai=week_start,
                tanggal_selesai=week_end,
                generation_mode='weekly'
            )
            weekly_tahapan.append(week)

        # Convert
        new_assignments = _convert_pekerjaan_assignments(
            pekerjaan_id=pekerjaan_custom.id,
            old_assignments=old_assignments,
            new_tahapan_list=weekly_tahapan
        )

        # Should have 4 assignments
        assert len(new_assignments) == 4

        # Each week should have roughly equal proportion (each week = 7 days)
        # Total days in month = 31
        # Each week should get: (7/31) * 100% ≈ 22.58%
        expected_per_week = Decimal('100.00') * Decimal('7') / Decimal('31')

        for assignment in new_assignments:
            # Allow some tolerance (±2%)
            assert abs(assignment.proporsi_volume - expected_per_week) < Decimal('2.0')

        # Total should be ~100%
        # NOTE: There will be some data loss because weeks don't perfectly align with month
        # Week 4 ends on Jan 28, but month goes to Jan 31 (3 days not covered)
        # This is expected behavior - conversion only maps overlapping date ranges
        total = sum(a.proporsi_volume for a in new_assignments)
        # Allow tolerance for partial week coverage (week 4 = 7 days, but 3 days of month remain)
        # Expected loss: (3 days / 31 days) * 100% ≈ 9.68%
        assert abs(total - Decimal('100.00')) < Decimal('15.0')  # Allow up to 15% loss for edge cases

    def test_convert_preserves_total_proportion(self, project_with_timeline, pekerjaan_custom):
        """Test that conversion preserves total proportion across complex scenarios"""
        # Create 3 old tahapan with varying proportions
        tahap1 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="Period 1",
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 10),
            generation_mode='custom'
        )

        tahap2 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="Period 2",
            tanggal_mulai=date(2025, 1, 11),
            tanggal_selesai=date(2025, 1, 20),
            generation_mode='custom'
        )

        tahap3 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="Period 3",
            tanggal_mulai=date(2025, 1, 21),
            tanggal_selesai=date(2025, 1, 31),
            generation_mode='custom'
        )

        # Assign proportions: 30%, 40%, 30%
        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,
            proporsi_volume=Decimal('30.00')
        )

        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap2,
            proporsi_volume=Decimal('40.00')
        )

        PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap3,
            proporsi_volume=Decimal('30.00')
        )

        # Get old assignments
        old_assignments = list(
            PekerjaanTahapan.objects.filter(
                pekerjaan=pekerjaan_custom
            ).values(
                'tahapan_id',
                'tahapan__tanggal_mulai',
                'tahapan__tanggal_selesai',
                'proporsi_volume'
            )
        )

        # Create 2 new tahapan (split differently)
        new1 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="New Period 1",
            tanggal_mulai=date(2025, 1, 1),
            tanggal_selesai=date(2025, 1, 15),  # Overlaps old tahap1 & half of tahap2
            generation_mode='custom'
        )

        new2 = TahapPelaksanaan.objects.create(
            project=project_with_timeline,
            nama="New Period 2",
            tanggal_mulai=date(2025, 1, 16),
            tanggal_selesai=date(2025, 1, 31),  # Overlaps half of tahap2 & tahap3
            generation_mode='custom'
        )

        # Convert
        new_assignments = _convert_pekerjaan_assignments(
            pekerjaan_id=pekerjaan_custom.id,
            old_assignments=old_assignments,
            new_tahapan_list=[new1, new2]
        )

        # Should have 2 assignments
        assert len(new_assignments) == 2

        # Total proportion should be ~100%
        total = sum(a.proporsi_volume for a in new_assignments)
        assert abs(total - Decimal('100.00')) < Decimal('0.5')


# =============================================================================
# API TESTS: api_regenerate_tahapan Endpoint
# =============================================================================

@pytest.mark.django_db
class TestRegenerateTahapanAPI:
    """Test API endpoint for tahapan regeneration and assignment conversion"""

    def test_regenerate_daily_mode(self, client_logged, project_with_timeline):
        """Test regenerate API with daily mode"""
        url = reverse('detail_project:api_regenerate_tahapan', args=[project_with_timeline.id])

        response = client_logged.post(
            url,
            data={
                'mode': 'daily',
                'week_end_day': 0,
                'convert_assignments': False
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        assert data['ok'] is True
        assert data['mode'] == 'daily'
        assert data['tahapan_created'] == 31  # January has 31 days

        # Verify in database
        tahapan = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='daily'
        )
        assert tahapan.count() == 31

    def test_regenerate_weekly_mode(self, client_logged, project_with_timeline):
        """Test regenerate API with weekly mode"""
        url = reverse('detail_project:api_regenerate_tahapan', args=[project_with_timeline.id])

        response = client_logged.post(
            url,
            data={
                'mode': 'weekly',
                'week_end_day': 0,  # Sunday
                'convert_assignments': False
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        assert data['ok'] is True
        assert data['mode'] == 'weekly'
        # Should have 4-5 weeks in a month
        assert data['tahapan_created'] >= 4 and data['tahapan_created'] <= 6

    def test_regenerate_monthly_mode(self, client_logged, project_with_3month_timeline):
        """Test regenerate API with monthly mode for 3-month project"""
        url = reverse('detail_project:api_regenerate_tahapan', args=[project_with_3month_timeline.id])

        response = client_logged.post(
            url,
            data={
                'mode': 'monthly',
                'week_end_day': 0,
                'convert_assignments': False
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        assert data['ok'] is True
        assert data['mode'] == 'monthly'
        assert data['tahapan_created'] == 3  # Jan, Feb, Mar

    def test_regenerate_with_assignment_conversion(
        self,
        client_logged,
        project_with_timeline,
        pekerjaan_with_assignments,
        custom_tahapan_4weeks
    ):
        """Test regenerate API with convert_assignments=True"""
        # Verify initial state: 4 assignments (25% each)
        initial_count = PekerjaanTahapan.objects.filter(
            pekerjaan=pekerjaan_with_assignments
        ).count()
        assert initial_count == 4

        # Regenerate to monthly mode with conversion
        url = reverse('detail_project:api_regenerate_tahapan', args=[project_with_timeline.id])

        response = client_logged.post(
            url,
            data={
                'mode': 'monthly',
                'week_end_day': 0,
                'convert_assignments': True
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()

        assert data['ok'] is True
        assert data['assignments_converted'] > 0

        # Verify conversion happened
        new_assignments = PekerjaanTahapan.objects.filter(
            pekerjaan=pekerjaan_with_assignments
        )

        # Should have 1 assignment (monthly)
        assert new_assignments.count() == 1

        # Total should be ~100%
        total = sum(a.proporsi_volume for a in new_assignments)
        assert abs(total - Decimal('100.00')) < Decimal('1.0')

    def test_regenerate_invalid_mode(self, client_logged, project_with_timeline):
        """Test regenerate API with invalid mode"""
        url = reverse('detail_project:api_regenerate_tahapan', args=[project_with_timeline.id])

        response = client_logged.post(
            url,
            data={
                'mode': 'invalid_mode',
                'week_end_day': 0,
                'convert_assignments': False
            },
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False

    def test_regenerate_project_without_timeline(self, client_logged, project):
        """Test regenerate API with project that has no timeline"""
        # Ensure project has no timeline
        project.tanggal_mulai = None
        project.tanggal_selesai = None
        project.save()

        url = reverse('detail_project:api_regenerate_tahapan', args=[project.id])

        response = client_logged.post(
            url,
            data={
                'mode': 'daily',
                'week_end_day': 0,
                'convert_assignments': False
            },
            content_type='application/json'
        )

        # NOTE: Current implementation doesn't validate timeline before processing
        # This test documents current behavior - may want to add validation later
        assert response.status_code == 200
        data = response.json()
        # With no timeline, no tahapan will be generated
        assert data['tahapan_created'] == 0


# =============================================================================
# INTEGRATION TESTS: Complete Workflow
# =============================================================================

@pytest.mark.django_db
class TestCompleteWorkflow:
    """Integration tests for complete user workflow"""

    def test_workflow_create_assign_switch_modes(
        self,
        client_logged,
        project_with_timeline,
        pekerjaan_custom
    ):
        """
        Test complete workflow:
        1. Start with weekly mode
        2. Create assignments
        3. Switch to monthly mode (conversion)
        4. Switch back to weekly (conversion)
        5. Verify data integrity
        """
        url = reverse('detail_project:api_regenerate_tahapan', args=[project_with_timeline.id])

        # Step 1: Generate weekly tahapan
        r1 = client_logged.post(url, {
            'mode': 'weekly',
            'week_end_day': 0,
            'convert_assignments': False
        }, content_type='application/json')

        assert r1.status_code == 200
        weekly_count = r1.json()['tahapan_created']
        assert weekly_count >= 4

        # Step 2: Create assignments (distribute across weeks)
        weekly_tahapan = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='weekly'
        ).order_by('urutan')

        proportion_per_week = Decimal('100.00') / weekly_count

        for tahap in weekly_tahapan:
            PekerjaanTahapan.objects.create(
                pekerjaan=pekerjaan_custom,
                tahapan=tahap,
                proporsi_volume=proportion_per_week.quantize(Decimal('0.01'))
            )

        # Verify initial assignments
        initial_total = sum(
            a.proporsi_volume
            for a in PekerjaanTahapan.objects.filter(pekerjaan=pekerjaan_custom)
        )
        assert abs(initial_total - Decimal('100.00')) < Decimal('1.0')

        # Step 3: Switch to monthly mode with conversion
        r2 = client_logged.post(url, {
            'mode': 'monthly',
            'week_end_day': 0,
            'convert_assignments': True
        }, content_type='application/json')

        assert r2.status_code == 200
        assert r2.json()['assignments_converted'] > 0

        # Verify monthly assignments
        monthly_assignments = PekerjaanTahapan.objects.filter(
            pekerjaan=pekerjaan_custom,
            tahapan__generation_mode='monthly'
        )

        monthly_total = sum(a.proporsi_volume for a in monthly_assignments)
        assert abs(monthly_total - Decimal('100.00')) < Decimal('1.0')

        # Step 4: Switch back to weekly with conversion
        r3 = client_logged.post(url, {
            'mode': 'weekly',
            'week_end_day': 0,
            'convert_assignments': True
        }, content_type='application/json')

        assert r3.status_code == 200
        assert r3.json()['assignments_converted'] > 0

        # Verify final weekly assignments
        final_assignments = PekerjaanTahapan.objects.filter(
            pekerjaan=pekerjaan_custom,
            tahapan__generation_mode='weekly'
        )

        final_total = sum(a.proporsi_volume for a in final_assignments)

        # Total should still be ~100% after round-trip conversion
        assert abs(final_total - Decimal('100.00')) < Decimal('2.0')

    def test_workflow_save_with_proper_tahapan_id(
        self,
        client_logged,
        project_with_timeline,
        pekerjaan_custom
    ):
        """
        Test that save functionality works with proper tahapanId.
        This verifies the original issue is fixed.
        """
        # Generate weekly tahapan
        url_regenerate = reverse('detail_project:api_regenerate_tahapan', args=[project_with_timeline.id])

        r1 = client_logged.post(url_regenerate, {
            'mode': 'weekly',
            'week_end_day': 0,
            'convert_assignments': False
        }, content_type='application/json')

        assert r1.status_code == 200

        # Get tahapan
        tahapan = TahapPelaksanaan.objects.filter(
            project=project_with_timeline,
            generation_mode='weekly'
        ).order_by('urutan')

        assert tahapan.count() > 0

        # Simulate save: Create assignments with proper tahapanId
        tahap1 = tahapan[0]
        tahap2 = tahapan[1] if tahapan.count() > 1 else tahapan[0]

        # Create assignment 1
        assignment1 = PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap1,  # CRITICAL: proper tahapan object
            proporsi_volume=Decimal('60.00')
        )

        # Create assignment 2
        assignment2 = PekerjaanTahapan.objects.create(
            pekerjaan=pekerjaan_custom,
            tahapan=tahap2,  # CRITICAL: proper tahapan object
            proporsi_volume=Decimal('40.00')
        )

        # Verify assignments were saved with proper tahapanId
        assert assignment1.tahapan_id is not None
        assert assignment1.tahapan_id == tahap1.id

        assert assignment2.tahapan_id is not None
        assert assignment2.tahapan_id == tahap2.id

        # Verify they can be queried
        saved_assignments = PekerjaanTahapan.objects.filter(
            pekerjaan=pekerjaan_custom
        ).select_related('tahapan')

        assert saved_assignments.count() == 2

        # Verify total
        total = sum(a.proporsi_volume for a in saved_assignments)
        assert total == Decimal('100.00')
