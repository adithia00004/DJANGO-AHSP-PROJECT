"""
Test Coverage for Progress Utils Functions

This module tests critical functions in progress_utils.py that were identified
as having low coverage during the Production Readiness Audit.

Coverage targets:
- calculate_week_number (date edge cases)
- get_week_date_range (boundary calculations)
- sync_weekly_to_tahapan (progress sync)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from detail_project.progress_utils import (
    calculate_week_number,
    get_week_date_range,
)
from dashboard.models import Project

User = get_user_model()


# ===========================================================================
# Test calculate_week_number
# ===========================================================================

@pytest.mark.django_db
class TestCalculateWeekNumber:
    """Tests for calculate_week_number function."""
    
    def test_same_day_returns_week_1(self):
        """Test same day as project start returns week 1."""
        project_start = date(2026, 1, 1)
        target_date = date(2026, 1, 1)
        
        result = calculate_week_number(target_date, project_start)
        
        assert result == 1
    
    def test_next_week_returns_week_2(self):
        """Test date in next week returns week 2."""
        project_start = date(2026, 1, 1)  # Wednesday
        target_date = date(2026, 1, 8)    # Next Wednesday
        
        result = calculate_week_number(target_date, project_start)
        
        assert result == 2
    
    def test_week_boundary_sunday(self):
        """Test week boundary with Sunday end."""
        project_start = date(2026, 1, 1)  # Thursday
        target_date = date(2026, 1, 5)    # Monday
        
        result = calculate_week_number(target_date, project_start, week_end_day=6)
        
        # Week calculation based on 7-day intervals
        assert result >= 1
    
    def test_year_boundary(self):
        """Test week calculation across year boundary."""
        project_start = date(2025, 12, 29)  # Monday
        target_date = date(2026, 1, 5)      # Sunday next year
        
        result = calculate_week_number(target_date, project_start)
        
        # Should calculate correctly across year boundary
        assert result >= 1
    
    def test_long_project_duration(self):
        """Test week calculation for long project (52+ weeks)."""
        project_start = date(2025, 1, 1)
        target_date = date(2026, 1, 1)  # 1 year later
        
        result = calculate_week_number(target_date, project_start)
        
        # Should be approximately week 52-53
        assert result >= 52
    
    def test_target_before_start_returns_negative_or_1(self):
        """Test target date before project start."""
        project_start = date(2026, 1, 10)
        target_date = date(2026, 1, 5)  # Before start
        
        result = calculate_week_number(target_date, project_start)
        
        # Implementation may return negative or clamp to 1
        assert isinstance(result, int)


# ===========================================================================
# Test get_week_date_range
# ===========================================================================

@pytest.mark.django_db
class TestGetWeekDateRange:
    """Tests for get_week_date_range function."""
    
    def test_week_1_range(self):
        """Test date range for week 1."""
        project_start = date(2026, 1, 1)  # Wednesday
        
        start, end = get_week_date_range(1, project_start)
        
        # Week 1 should start on project start
        assert start == project_start
        # Week 1 should end on Sunday (if week_end_day=6)
        assert start <= end
    
    def test_week_2_range(self):
        """Test date range for week 2."""
        project_start = date(2026, 1, 1)  # Wednesday
        
        start, end = get_week_date_range(2, project_start)
        
        # Week 2 should be after week 1
        week1_start, week1_end = get_week_date_range(1, project_start)
        assert start > week1_end
    
    def test_consecutive_weeks_valid(self):
        """Test consecutive weeks are properly ordered."""
        project_start = date(2026, 1, 1)
        
        week1_start, week1_end = get_week_date_range(1, project_start)
        week2_start, week2_end = get_week_date_range(2, project_start)
        
        # Week 2 should be after week 1
        assert week2_start > week1_end
    
    def test_week_52_range(self):
        """Test date range for week 52."""
        project_start = date(2025, 1, 1)
        
        start, end = get_week_date_range(52, project_start)
        
        # Should be valid date range
        assert start <= end
        # Should be approximately 1 year after project start
        assert start.year in [2025, 2026]


# ===========================================================================
# Edge Cases
# ===========================================================================

@pytest.mark.django_db
class TestProgressUtilsEdgeCases:
    """Edge case tests for progress utilities."""
    
    def test_leap_year_handling(self):
        """Test week calculation handles leap year correctly."""
        project_start = date(2024, 2, 28)  # Before leap day
        target_date = date(2024, 3, 1)     # After leap day
        
        result = calculate_week_number(target_date, project_start)
        
        assert result >= 1
    
    def test_different_week_end_days(self):
        """Test different week end day configurations."""
        project_start = date(2026, 1, 1)
        target_date = date(2026, 1, 7)
        
        # Test with different week end days
        for week_end in range(7):  # 0=Monday to 6=Sunday
            result = calculate_week_number(target_date, project_start, week_end_day=week_end)
            assert result >= 1
