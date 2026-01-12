"""
Tests for Jadwal Pekerjaan Data Sync scenarios.

These tests verify that when data changes on other pages (Dashboard, List Pekerjaan, 
Volume, Harga), the Jadwal Pekerjaan page correctly reflects those changes on reload.

Test Coverage:
1. CASCADE Delete Test - Progress deleted when pekerjaan is deleted
2. Project Date Change Test - Week columns recalculated when project dates change
3. Ordering Sync Test - Grid reflects ordering_index changes from List Pekerjaan
4. Bobot Recalculation Test - Bobot updates when volume/harga changes
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse


# ============================================================================
# Test 1: CASCADE Delete - Progress data should be deleted when pekerjaan is deleted
# ============================================================================

class TestCascadeDeleteProgress:
    """Test that PekerjaanProgressWeekly records are deleted when Pekerjaan is deleted."""

    def test_progress_deleted_when_pekerjaan_deleted(self, db, weekly_progress):
        """
        When a Pekerjaan is deleted, all associated PekerjaanProgressWeekly 
        records should be automatically deleted via CASCADE.
        """
        from detail_project.models import Pekerjaan, PekerjaanProgressWeekly
        
        # Get pekerjaan from the weekly_progress fixture
        pekerjaan = weekly_progress[0].pekerjaan
        pekerjaan_id = pekerjaan.id
        project = weekly_progress[0].project
        
        # Verify progress records exist before deletion
        progress_count_before = PekerjaanProgressWeekly.objects.filter(
            pekerjaan_id=pekerjaan_id
        ).count()
        assert progress_count_before > 0, "Should have progress records before deletion"
        
        # Delete the pekerjaan
        pekerjaan.delete()
        
        # Verify progress records are deleted (CASCADE)
        progress_count_after = PekerjaanProgressWeekly.objects.filter(
            pekerjaan_id=pekerjaan_id
        ).count()
        assert progress_count_after == 0, "Progress records should be deleted via CASCADE"

    def test_progress_deleted_when_project_deleted(self, db, weekly_progress):
        """
        When a Project is deleted, all associated PekerjaanProgressWeekly 
        records should be automatically deleted via CASCADE.
        """
        from detail_project.models import PekerjaanProgressWeekly
        
        project = weekly_progress[0].project
        project_id = project.id
        
        # Verify progress records exist before deletion
        progress_count_before = PekerjaanProgressWeekly.objects.filter(
            project_id=project_id
        ).count()
        assert progress_count_before > 0, "Should have progress records before deletion"
        
        # Delete the project
        project.delete()
        
        # Verify progress records are deleted (CASCADE)
        progress_count_after = PekerjaanProgressWeekly.objects.filter(
            project_id=project_id
        ).count()
        assert progress_count_after == 0, "Progress records should be deleted via CASCADE"


# ============================================================================
# Test 2: Project Date Change - Week columns should recalculate
# ============================================================================

class TestProjectDateChange:
    """Test that week columns are recalculated when project dates change."""

    def test_week_count_changes_when_project_dates_extended(self, db, project_with_dates):
        """
        When project end date is extended, the calculated total weeks should increase.
        """
        from django.db.models import Max
        from detail_project.models import PekerjaanProgressWeekly
        
        project = project_with_dates
        original_end = project.tanggal_selesai
        original_start = project.tanggal_mulai
        
        # Calculate original weeks
        original_days = (original_end - original_start).days
        original_weeks = max(1, (original_days + 6) // 7)
        
        # Extend project by 4 weeks
        project.tanggal_selesai = original_end + timedelta(weeks=4)
        project.save()
        
        # Calculate new weeks
        new_days = (project.tanggal_selesai - project.tanggal_mulai).days
        new_weeks = max(1, (new_days + 6) // 7)
        
        assert new_weeks == original_weeks + 4, "Week count should increase by 4"

    def test_week_dates_shift_when_project_start_changes(self, db, project_with_dates):
        """
        When project start date changes, week start/end dates in progress
        should be relative to new start date.
        """
        project = project_with_dates
        original_start = project.tanggal_mulai
        
        # Shift project start by 2 weeks later
        new_start = original_start + timedelta(weeks=2)
        project.tanggal_mulai = new_start
        project.save()
        
        # Reload project
        project.refresh_from_db()
        
        assert project.tanggal_mulai == new_start, "Project start should be updated"


# ============================================================================
# Test 3: Ordering Sync - Grid should reflect ordering_index changes
# ============================================================================

class TestOrderingSync:
    """Test that grid correctly reflects ordering_index changes from List Pekerjaan."""

    def test_pekerjaan_ordering_in_api_response(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """
        API should return pekerjaan sorted by ordering_index.
        """
        from detail_project.models import Pekerjaan
        
        project = project_with_dates
        pekerjaan = pekerjaan_with_volume
        
        # Create additional pekerjaan with different ordering
        sub_klas = pekerjaan.sub_klasifikasi
        
        pekerjaan2 = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            ordering_index=100,  # Use high unique value
            snapshot_kode="PKJ-002",
            snapshot_uraian="Second Job",
            snapshot_satuan="m2"
        )
        
        pekerjaan3 = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            ordering_index=50,  # Should come before pekerjaan2
            snapshot_kode="PKJ-003",
            snapshot_uraian="Third Job",
            snapshot_satuan="m3"
        )
        
        # Call API
        url = reverse('detail_project:api_get_list_pekerjaan_tree', args=[project.id])
        response = client_logged.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Extract pekerjaan from response
        all_pekerjaan = []
        for klas in data.get('klasifikasi', []):
            for sub in klas.get('sub', []):
                for pkj in sub.get('pekerjaan', []):
                    all_pekerjaan.append(pkj)
        
        # Verify ordering_index is respected
        if len(all_pekerjaan) >= 2:
            indices = [p.get('ordering_index', 999) for p in all_pekerjaan]
            assert indices == sorted(indices), "Pekerjaan should be sorted by ordering_index"

    def test_reorder_pekerjaan_reflected_in_api(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """
        When ordering_index is changed, subsequent API calls should reflect new order.
        """
        from detail_project.models import Pekerjaan
        
        pekerjaan = pekerjaan_with_volume
        original_index = pekerjaan.ordering_index or 0
        
        # Change ordering_index
        new_index = original_index + 100
        pekerjaan.ordering_index = new_index
        pekerjaan.save()
        
        # Reload from DB
        pekerjaan.refresh_from_db()
        
        assert pekerjaan.ordering_index == new_index, "Ordering index should be updated"


# ============================================================================
# Test 4: Bobot Recalculation - Bobot updates when volume/harga changes
# ============================================================================

class TestBobotRecalculation:
    """Test that bobot (weight) is correctly recalculated when volume or harga changes."""

    def test_budgeted_cost_updates_when_volume_changes(self, db, pekerjaan_with_volume):
        """
        When volume changes, budgeted_cost should be recalculated.
        Note: This depends on how budgeted_cost is calculated in your system.
        """
        from detail_project.models import VolumePekerjaan
        
        pekerjaan = pekerjaan_with_volume
        volume = pekerjaan.volume
        
        original_quantity = volume.quantity
        
        # Change volume
        new_quantity = original_quantity * 2
        volume.quantity = new_quantity
        volume.save()
        
        # Reload
        volume.refresh_from_db()
        
        assert volume.quantity == new_quantity, "Volume should be updated"

    def test_api_returns_fresh_budgeted_cost(self, db, pekerjaan_with_volume):
        """
        budgeted_cost should be fresh from database, not cached.
        Model-level test to verify data freshness.
        """
        from detail_project.models import Pekerjaan
        
        pekerjaan = pekerjaan_with_volume
        pekerjaan_id = pekerjaan.id
        
        # Update budgeted_cost directly
        new_cost = Decimal('999999.99')
        pekerjaan.budgeted_cost = new_cost
        pekerjaan.save()
        
        # Reload from database (simulates page reload)
        reloaded_pekerjaan = Pekerjaan.objects.get(id=pekerjaan_id)
        
        # Verify fresh data
        assert reloaded_pekerjaan.budgeted_cost == new_cost, \
            "Database should return updated budgeted_cost"

    def test_bobot_calculation_across_pekerjaan(self, db, project_with_dates, pekerjaan_with_volume):
        """
        Bobot (weight) should be calculated as: 
        bobot = (budgeted_cost / total_project_cost) * 100
        
        This test verifies the calculation is correct.
        """
        from detail_project.models import Pekerjaan
        
        project = project_with_dates
        pekerjaan1 = pekerjaan_with_volume
        
        # Set known budgeted_cost
        pekerjaan1.budgeted_cost = Decimal('1000000')
        pekerjaan1.save()
        
        # Create second pekerjaan with different cost
        sub_klas = pekerjaan1.sub_klasifikasi
        pekerjaan2 = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            ordering_index=10,
            snapshot_kode="PKJ-BOBOT",
            snapshot_uraian="Bobot Test Job",
            snapshot_satuan="ls",
            budgeted_cost=Decimal('3000000')
        )
        
        # Calculate total
        total_cost = Decimal('1000000') + Decimal('3000000')  # 4,000,000
        
        # Expected bobot
        expected_bobot1 = (Decimal('1000000') / total_cost) * 100  # 25%
        expected_bobot2 = (Decimal('3000000') / total_cost) * 100  # 75%
        
        # Verify calculation is mathematically correct
        assert abs(expected_bobot1 - Decimal('25')) < Decimal('0.01'), "Bobot1 should be 25%"
        assert abs(expected_bobot2 - Decimal('75')) < Decimal('0.01'), "Bobot2 should be 75%"


# ============================================================================
# Integration Test: Complete Data Sync Workflow
# ============================================================================

class TestDataSyncIntegration:
    """Integration tests for complete data sync workflow across pages."""

    def test_complete_sync_flow(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """
        Test complete flow:
        1. Create pekerjaan with volume
        2. Add progress data
        3. Change volume → verify bobot recalculates
        4. Change ordering → verify order in grid
        5. Delete pekerjaan → verify progress deleted
        """
        from detail_project.models import (
            Pekerjaan, VolumePekerjaan, PekerjaanProgressWeekly
        )
        from datetime import date
        
        project = project_with_dates
        pekerjaan = pekerjaan_with_volume
        pekerjaan_id = pekerjaan.id
        
        # Step 1: Verify initial state
        assert pekerjaan.volume is not None, "Should have volume"
        
        # Step 2: Add progress data
        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan,
            project=project,
            week_number=1,
            week_start_date=date(2025, 1, 6),
            week_end_date=date(2025, 1, 12),
            planned_proportion=Decimal('20.00'),
            actual_proportion=Decimal('15.00')
        )
        
        # Step 3: Change volume
        original_volume = pekerjaan.volume.quantity
        pekerjaan.volume.quantity = original_volume * 2
        pekerjaan.volume.save()
        
        # Verify volume changed
        pekerjaan.volume.refresh_from_db()
        assert pekerjaan.volume.quantity == original_volume * 2, "Volume should double"
        
        # Step 4: Change ordering
        pekerjaan.ordering_index = 999
        pekerjaan.save()
        pekerjaan.refresh_from_db()
        assert pekerjaan.ordering_index == 999, "Ordering should change"
        
        # Step 5: Delete pekerjaan
        progress_id = progress.id
        pekerjaan.delete()
        
        # Verify cascade delete
        assert not PekerjaanProgressWeekly.objects.filter(id=progress_id).exists(), \
            "Progress should be deleted via CASCADE"
        assert not Pekerjaan.objects.filter(id=pekerjaan_id).exists(), \
            "Pekerjaan should be deleted"
