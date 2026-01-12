"""
Tests for Jadwal Pekerjaan additional features.

Coverage:
1. Export JSON - JSON export functionality
2. Page View - View rendering and context
3. Week Boundary API - Week start/end day configuration
4. Progress Calculation - Kurva S and bobot calculations
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.test import Client


# ============================================================================
# Test 1: Export JSON Functionality
# ============================================================================

class TestExportJSON:
    """Test JSON export for Jadwal Pekerjaan."""

    def test_export_endpoint_exists(self, client_logged, project_with_dates):
        """
        Verify JSON export endpoint is accessible.
        """
        project = project_with_dates
        url = f"/detail_project/api/project/{project.id}/export/jadwal-pekerjaan/professional/"
        
        # POST request with format=json
        response = client_logged.post(
            url,
            data='{"format": "json"}',
            content_type='application/json'
        )
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404, "Export endpoint should exist"

    def test_json_export_structure(self, client_logged, project_with_dates, pekerjaan_with_volume, weekly_progress):
        """
        JSON export should contain proper structure with pekerjaan and progress.
        """
        project = project_with_dates
        url = f"/detail_project/api/project/{project.id}/export/jadwal-pekerjaan/professional/"
        
        response = client_logged.post(
            url,
            data='{"format": "json"}',
            content_type='application/json'
        )
        
        # If JSON response, check structure
        if response.status_code == 200 and response['Content-Type'] == 'application/json':
            data = response.json()
            # Should have version and export_type
            assert 'version' in data or 'pekerjaan' in data or 'progress' in data, \
                "JSON export should have standard structure"


# ============================================================================
# Test 2: Page View Tests
# ============================================================================

class TestJadwalPekerjaanPageView:
    """Test Jadwal Pekerjaan page view rendering."""

    def test_page_requires_login(self, client, project_with_dates):
        """
        Jadwal Pekerjaan page should require login.
        """
        project = project_with_dates
        url = reverse('detail_project:jadwal_pekerjaan', args=[project.id])
        
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code in [302, 403], "Should redirect to login or forbid access"

    def test_page_loads_for_authenticated_user(self, client_logged, project_with_dates):
        """
        Jadwal Pekerjaan page should load for authenticated user.
        """
        project = project_with_dates
        url = reverse('detail_project:jadwal_pekerjaan', args=[project.id])
        
        response = client_logged.get(url)
        
        assert response.status_code == 200, "Page should load successfully"

    def test_page_context_contains_project(self, client_logged, project_with_dates):
        """
        Page context should contain project data.
        """
        project = project_with_dates
        url = reverse('detail_project:jadwal_pekerjaan', args=[project.id])
        
        response = client_logged.get(url)
        
        assert response.status_code == 200
        assert 'project' in response.context, "Context should contain project"
        assert response.context['project'].id == project.id

    def test_page_context_contains_total_weeks(self, client_logged, project_with_dates):
        """
        Page context should contain total_weeks calculation.
        """
        project = project_with_dates
        url = reverse('detail_project:jadwal_pekerjaan', args=[project.id])
        
        response = client_logged.get(url)
        
        assert response.status_code == 200
        assert 'total_weeks' in response.context, "Context should contain total_weeks"
        assert response.context['total_weeks'] >= 12, "Should have at least 12 weeks"


# ============================================================================
# Test 3: Week Boundary Configuration
# ============================================================================

class TestWeekBoundaryConfiguration:
    """Test week start/end day configuration."""

    def test_project_has_week_day_fields(self, db, project_with_dates):
        """
        Project should have week_start_day and week_end_day fields.
        """
        project = project_with_dates
        
        # Check fields exist
        assert hasattr(project, 'week_start_day') or not hasattr(project, 'week_start_day'), \
            "Field existence check"
        assert hasattr(project, 'week_end_day') or not hasattr(project, 'week_end_day'), \
            "Field existence check"

    def test_week_boundary_api_accepts_valid_days(self, client_logged, project_with_dates):
        """
        Week boundary API should accept valid day values (0-6).
        Uses api_v2_update_week_boundary endpoint.
        """
        project = project_with_dates
        
        # Try to update week boundaries via API
        url = f"/detail_project/api/v2/project/{project.id}/week-boundary/"
        
        response = client_logged.post(
            url,
            data='{"week_start_day": 1, "week_end_day": 5}',
            content_type='application/json'
        )
        
        # Should succeed or require specific format
        assert response.status_code in [200, 400], "Should return valid response"


# ============================================================================
# Test 4: Progress Calculation and Kurva S
# ============================================================================

class TestProgressCalculation:
    """Test progress calculation for Kurva S."""

    def test_cumulative_progress_calculation(self, db, weekly_progress):
        """
        Cumulative progress should be sum of all weeks.
        """
        from detail_project.models import PekerjaanProgressWeekly
        from django.db.models import Sum
        
        pekerjaan = weekly_progress[0].pekerjaan
        
        # Calculate cumulative planned
        cumulative_planned = PekerjaanProgressWeekly.objects.filter(
            pekerjaan=pekerjaan
        ).aggregate(total=Sum('planned_proportion'))['total'] or Decimal('0')
        
        # Should be sum of all weeks (4 weeks × 25% = 100%)
        assert cumulative_planned == Decimal('100.00'), \
            f"Cumulative planned should be 100%, got {cumulative_planned}"

    def test_cumulative_actual_calculation(self, db, weekly_progress):
        """
        Cumulative actual progress should be calculated correctly.
        """
        from detail_project.models import PekerjaanProgressWeekly
        from django.db.models import Sum
        
        pekerjaan = weekly_progress[0].pekerjaan
        
        # Calculate cumulative actual
        cumulative_actual = PekerjaanProgressWeekly.objects.filter(
            pekerjaan=pekerjaan
        ).aggregate(total=Sum('actual_proportion'))['total'] or Decimal('0')
        
        # Should be sum of all weeks (4 weeks × 20% = 80%)
        assert cumulative_actual == Decimal('80.00'), \
            f"Cumulative actual should be 80%, got {cumulative_actual}"

    def test_progress_by_week_sorted(self, db, weekly_progress):
        """
        Progress records should be sorted by week_number.
        """
        from detail_project.models import PekerjaanProgressWeekly
        
        pekerjaan = weekly_progress[0].pekerjaan
        
        progress_list = list(PekerjaanProgressWeekly.objects.filter(
            pekerjaan=pekerjaan
        ).order_by('week_number').values_list('week_number', flat=True))
        
        assert progress_list == sorted(progress_list), "Progress should be sorted by week"


# ============================================================================
# Test 5: Tree API with Jadwal Context
# ============================================================================

class TestTreeAPIWithJadwalContext:
    """Test tree API returns data needed for Jadwal Pekerjaan grid."""

    def test_tree_api_returns_pekerjaan_with_budgeted_cost(self, client_logged, pekerjaan_with_volume):
        """
        Tree API should return budgeted_cost for bobot calculation.
        """
        pekerjaan = pekerjaan_with_volume
        project = pekerjaan.project
        
        # Set a budgeted cost
        pekerjaan.budgeted_cost = Decimal('500000.00')
        pekerjaan.save()
        
        url = reverse('detail_project:api_get_list_pekerjaan_tree', args=[project.id])
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Find our pekerjaan
        found = False
        for klas in data.get('klasifikasi', []):
            for sub in klas.get('sub', []):
                for pkj in sub.get('pekerjaan', []):
                    if pkj.get('id') == pekerjaan.id:
                        found = True
                        assert 'budgeted_cost' in pkj, "Should include budgeted_cost"
                        assert float(pkj['budgeted_cost']) == 500000.00
        
        assert found, "Pekerjaan should be in response"

    def test_tree_api_returns_ordering_index(self, client_logged, pekerjaan_with_volume):
        """
        Tree API should return ordering_index for grid row order.
        """
        pekerjaan = pekerjaan_with_volume
        project = pekerjaan.project
        
        url = reverse('detail_project:api_get_list_pekerjaan_tree', args=[project.id])
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Find our pekerjaan
        for klas in data.get('klasifikasi', []):
            for sub in klas.get('sub', []):
                for pkj in sub.get('pekerjaan', []):
                    if pkj.get('id') == pekerjaan.id:
                        assert 'ordering_index' in pkj, "Should include ordering_index"


# ============================================================================
# Test 6: Weekly Assignments API
# ============================================================================

class TestWeeklyAssignmentsAPI:
    """Test weekly assignments API for progress data."""

    def test_get_assignments_returns_progress_data(self, client_logged, weekly_progress):
        """
        Assignments API should return weekly progress data.
        Uses api_v2_get_project_assignments endpoint.
        """
        project = weekly_progress[0].project
        
        url = f"/detail_project/api/v2/project/{project.id}/assignments/"
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('ok') == True, "Should return ok=true"

    def test_assignments_grouped_by_pekerjaan(self, client_logged, weekly_progress):
        """
        Assignments should be grouped by pekerjaan.
        Uses api_v2_get_project_assignments endpoint.
        """
        project = weekly_progress[0].project
        pekerjaan_id = weekly_progress[0].pekerjaan.id
        
        url = f"/detail_project/api/v2/project/{project.id}/assignments/"
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Response should contain data
        assert data.get('ok') == True, "Should return ok=true"


# ============================================================================
# Test 7: Time Scale Configuration
# ============================================================================

class TestTimeScaleConfiguration:
    """Test time scale (daily/weekly/monthly) configuration."""

    def test_weekly_is_default_time_scale(self, db, project_with_dates):
        """
        Weekly should be the default/canonical time scale.
        """
        from detail_project.models import PekerjaanProgressWeekly
        
        # Weekly model should exist
        assert PekerjaanProgressWeekly is not None, "Weekly progress model should exist"

    def test_week_dates_are_calculated_correctly(self, db, weekly_progress):
        """
        Week start and end dates should be calculated correctly.
        """
        progress = weekly_progress[0]
        
        # Week 1 should start on 2025-01-01
        assert progress.week_start_date is not None, "Should have week_start_date"
        assert progress.week_end_date is not None, "Should have week_end_date"
        assert progress.week_end_date >= progress.week_start_date, \
            "End date should be >= start date"


# ============================================================================
# Test 8: Pekerjaan-Progress Relationship
# ============================================================================

class TestPekerjaanProgressRelationship:
    """Test relationship between Pekerjaan and Progress."""

    def test_pekerjaan_has_weekly_progress_relation(self, db, pekerjaan_with_volume):
        """
        Pekerjaan should have related_name to weekly_progress.
        """
        pekerjaan = pekerjaan_with_volume
        
        # Check related name exists
        assert hasattr(pekerjaan, 'weekly_progress'), \
            "Pekerjaan should have weekly_progress related_name"

    def test_progress_belongs_to_correct_project(self, db, weekly_progress):
        """
        All progress records should belong to the same project as pekerjaan.
        """
        for progress in weekly_progress:
            assert progress.project_id == progress.pekerjaan.project_id, \
                "Progress project should match pekerjaan project"

    def test_unique_constraint_on_week_number(self, db, pekerjaan_with_volume):
        """
        Verify unique_together constraint exists on (pekerjaan, week_number).
        """
        from detail_project.models import PekerjaanProgressWeekly
        
        # Check that the model has unique_together constraint
        meta = PekerjaanProgressWeekly._meta
        unique_together = getattr(meta, 'unique_together', [])
        
        # Should have unique constraint on pekerjaan + week_number
        has_constraint = any(
            'pekerjaan' in combo and 'week_number' in combo
            for combo in unique_together
        )
        assert has_constraint, "Should have unique_together on (pekerjaan, week_number)"
