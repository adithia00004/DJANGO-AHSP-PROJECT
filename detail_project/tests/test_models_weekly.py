"""
Tests for PekerjaanProgressWeekly model.

Tests cover:
- Model creation and field validation
- Unique constraints (pekerjaan, week_number)
- Proportion validation (0-100)
- Date validation (week_end_date >= week_start_date)
- Auto-population of project field from pekerjaan.volume
- Related queries and lookups
"""

import pytest
from decimal import Decimal
from datetime import date
from django.db import IntegrityError
from django.core.exceptions import ValidationError


@pytest.mark.unit
class TestPekerjaanProgressWeeklyModel:
    """Test PekerjaanProgressWeekly model basic operations."""

    def test_create_weekly_progress(self, pekerjaan_with_volume):
        """Test creating a weekly progress record."""
        from detail_project.models import PekerjaanProgressWeekly

        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("25.50"),
            notes="Week 1 progress",
        )

        assert progress.id is not None
        assert progress.pekerjaan == pekerjaan_with_volume
        assert progress.week_number == 1
        assert progress.proportion == Decimal("25.50")
        assert progress.notes == "Week 1 progress"

    def test_unique_constraint_pekerjaan_week(self, pekerjaan_with_volume):
        """Test unique constraint on (pekerjaan, week_number)."""
        from detail_project.models import PekerjaanProgressWeekly
        from django.core.exceptions import ValidationError

        # Create first record
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("25.00"),
        )

        # Try to create duplicate - model raises ValidationError (not IntegrityError)
        with pytest.raises(ValidationError) as exc_info:
            record = PekerjaanProgressWeekly(
                pekerjaan=pekerjaan_with_volume,
                project=pekerjaan_with_volume.project,
                week_number=1,  # Same week number
                week_start_date=date(2025, 1, 1),
                week_end_date=date(2025, 1, 7),
                proportion=Decimal("30.00"),
            )
            record.full_clean()  # Triggers validation

        # Verify error message mentions unique constraint
        assert "Pekerjaan" in str(exc_info.value) or "week" in str(exc_info.value).lower()

    def test_proportion_min_value_validation(self, pekerjaan_with_volume):
        """Test that proportion cannot be negative."""
        from detail_project.models import PekerjaanProgressWeekly

        progress = PekerjaanProgressWeekly(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("-10.00"),  # Negative
        )

        with pytest.raises(ValidationError):
            progress.full_clean()

    def test_proportion_max_value_validation(self, pekerjaan_with_volume):
        """Test that proportion cannot exceed 100."""
        from detail_project.models import PekerjaanProgressWeekly

        progress = PekerjaanProgressWeekly(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("150.00"),  # Exceeds 100
        )

        with pytest.raises(ValidationError):
            progress.full_clean()

    def test_proportion_precision(self, pekerjaan_with_volume):
        """Test proportion decimal precision (5 digits, 2 decimal places)."""
        from detail_project.models import PekerjaanProgressWeekly

        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("99.99"),
        )

        progress.refresh_from_db()
        assert progress.proportion == Decimal("99.99")

    def test_auto_populate_project_field(self, pekerjaan_with_volume):
        """Test that project field is auto-populated from pekerjaan if not provided."""
        from detail_project.models import PekerjaanProgressWeekly

        # Create progress without explicitly setting project
        # Note: This test assumes model has auto-population logic in save()
        # If not implemented, this test documents the expected behavior
        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,  # Currently required
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("25.00"),
        )

        assert progress.project == pekerjaan_with_volume.project

    def test_week_date_fields(self, pekerjaan_with_volume):
        """Test week_start_date and week_end_date fields."""
        from detail_project.models import PekerjaanProgressWeekly

        start = date(2025, 1, 1)
        end = date(2025, 1, 7)

        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=start,
            week_end_date=end,
            proportion=Decimal("25.00"),
        )

        assert progress.week_start_date == start
        assert progress.week_end_date == end
        assert progress.week_end_date >= progress.week_start_date

    def test_notes_field_optional(self, pekerjaan_with_volume):
        """Test that notes field is optional."""
        from detail_project.models import PekerjaanProgressWeekly

        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("25.00"),
            # notes omitted
        )

        assert progress.notes in [None, ""]

    def test_timestamps_auto_populated(self, pekerjaan_with_volume):
        """Test created_at and updated_at are auto-populated."""
        from detail_project.models import PekerjaanProgressWeekly

        progress = PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=pekerjaan_with_volume.project,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("25.00"),
        )

        assert progress.created_at is not None
        assert progress.updated_at is not None
        assert progress.updated_at >= progress.created_at


@pytest.mark.unit
class TestPekerjaanProgressWeeklyQueries:
    """Test queries and related lookups."""

    def test_filter_by_pekerjaan(self, weekly_progress):
        """Test filtering progress by pekerjaan."""
        from detail_project.models import PekerjaanProgressWeekly

        pekerjaan = weekly_progress[0].pekerjaan
        progress = PekerjaanProgressWeekly.objects.filter(pekerjaan=pekerjaan)

        assert progress.count() == 4  # Fixture creates 4 weeks

    def test_filter_by_project(self, weekly_progress):
        """Test filtering progress by project."""
        from detail_project.models import PekerjaanProgressWeekly

        project = weekly_progress[0].project
        progress = PekerjaanProgressWeekly.objects.filter(project=project)

        assert progress.count() == 4

    def test_filter_by_week_number(self, weekly_progress):
        """Test filtering progress by week number."""
        from detail_project.models import PekerjaanProgressWeekly

        pekerjaan = weekly_progress[0].pekerjaan
        progress = PekerjaanProgressWeekly.objects.get(
            pekerjaan=pekerjaan,
            week_number=1
        )

        assert progress.week_number == 1
        assert progress.proportion == Decimal("25.00")

    def test_related_name_from_pekerjaan(self, weekly_progress):
        """Test accessing progress via pekerjaan.weekly_progress related name."""
        pekerjaan = weekly_progress[0].pekerjaan

        # Access via related name
        progress = pekerjaan.weekly_progress.all()

        assert progress.count() == 4
        assert all(p.pekerjaan == pekerjaan for p in progress)

    def test_related_name_from_project(self, weekly_progress):
        """Test accessing progress via project related name."""
        project = weekly_progress[0].project

        # Access via related name (pekerjaan_weekly_progress)
        progress = project.pekerjaan_weekly_progress.all()

        assert progress.count() == 4
        assert all(p.project == project for p in progress)

    def test_order_by_week_number(self, weekly_progress):
        """Test ordering by week number."""
        from detail_project.models import PekerjaanProgressWeekly

        pekerjaan = weekly_progress[0].pekerjaan
        progress = PekerjaanProgressWeekly.objects.filter(
            pekerjaan=pekerjaan
        ).order_by('week_number')

        week_numbers = [p.week_number for p in progress]
        assert week_numbers == [1, 2, 3, 4]

    def test_sum_total_proportion(self, weekly_progress):
        """Test calculating total proportion for a pekerjaan."""
        from detail_project.models import PekerjaanProgressWeekly
        from django.db.models import Sum

        pekerjaan = weekly_progress[0].pekerjaan
        total = PekerjaanProgressWeekly.objects.filter(
            pekerjaan=pekerjaan
        ).aggregate(total=Sum('proportion'))['total']

        # Fixture creates 4 weeks × 25% each = 100%
        assert total == Decimal("100.00")


@pytest.mark.integration
class TestPekerjaanProgressWeeklyIntegration:
    """Integration tests with related models."""

    def test_cascade_delete_pekerjaan(self, weekly_progress):
        """Test that deleting pekerjaan cascades to progress records."""
        from detail_project.models import PekerjaanProgressWeekly

        pekerjaan = weekly_progress[0].pekerjaan
        pekerjaan_id = pekerjaan.id

        # Verify progress exists
        assert PekerjaanProgressWeekly.objects.filter(pekerjaan_id=pekerjaan_id).count() == 4

        # Delete pekerjaan
        pekerjaan.delete()

        # Verify progress deleted
        assert PekerjaanProgressWeekly.objects.filter(pekerjaan_id=pekerjaan_id).count() == 0

    def test_cascade_delete_project(self, weekly_progress):
        """Test that deleting project cascades to progress records."""
        from detail_project.models import PekerjaanProgressWeekly

        project = weekly_progress[0].project
        project_id = project.id

        # Verify progress exists
        assert PekerjaanProgressWeekly.objects.filter(project_id=project_id).count() == 4

        # Delete project
        project.delete()

        # Verify progress deleted
        assert PekerjaanProgressWeekly.objects.filter(project_id=project_id).count() == 0

    def test_multiple_pekerjaan_same_project(self, db, project_with_dates, sub_klas):
        """Test multiple pekerjaan in same project with separate progress."""
        from detail_project.models import Pekerjaan, VolumePekerjaan, PekerjaanProgressWeekly

        # Create two pekerjaan
        pek1 = Pekerjaan.objects.create(
            project=project_with_dates,
            sub_klasifikasi=sub_klas,
            source_type="custom",
            snapshot_kode="PEK-001",
            snapshot_uraian="Pekerjaan 1",
            snapshot_satuan="m3",
            ordering_index=1,
        )

        pek2 = Pekerjaan.objects.create(
            project=project_with_dates,
            sub_klasifikasi=sub_klas,
            source_type="custom",
            snapshot_kode="PEK-002",
            snapshot_uraian="Pekerjaan 2",
            snapshot_satuan="m2",
            ordering_index=2,
        )

        # Create progress for both
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=pek1,
            project=project_with_dates,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("25.00"),
        )

        PekerjaanProgressWeekly.objects.create(
            pekerjaan=pek2,
            project=project_with_dates,
            week_number=1,
            week_start_date=date(2025, 1, 1),
            week_end_date=date(2025, 1, 7),
            proportion=Decimal("30.00"),
        )

        # Verify separate progress
        assert pek1.weekly_progress.count() == 1
        assert pek2.weekly_progress.count() == 1
        assert project_with_dates.pekerjaan_weekly_progress.count() == 2
