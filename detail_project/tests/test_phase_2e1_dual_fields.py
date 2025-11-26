"""
Tests for Phase 2E.1 - Dual Field Independence (Planned vs Actual).

This test suite verifies that planned_proportion and actual_proportion
are truly independent and don't overwrite each other.
"""

import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse


@pytest.mark.django_db
@pytest.mark.unit
class TestDualFieldIndependence:
    """Test that planned and actual fields are independent."""

    def test_save_planned_does_not_affect_actual(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """Test that saving planned progress doesn't overwrite actual progress."""
        url = reverse('detail_project:api_v2_assign_weekly', args=[project_with_dates.id])

        # Step 1: Save ACTUAL progress = 20%
        payload_actual = {
            "mode": "actual",
            "assignments": [{
                "pekerjaan_id": pekerjaan_with_volume.id,
                "week_number": 1,
                "proportion": 20.00,
                "week_start_date": "2025-01-01",
                "week_end_date": "2025-01-07",
            }]
        }
        response = client_logged.post(url, data=payload_actual, content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["progress_mode"] == "actual"

        # Step 2: Save PLANNED progress = 30%
        payload_planned = {
            "mode": "planned",
            "assignments": [{
                "pekerjaan_id": pekerjaan_with_volume.id,
                "week_number": 1,
                "proportion": 30.00,
                "week_start_date": "2025-01-01",
                "week_end_date": "2025-01-07",
            }]
        }
        response = client_logged.post(url, data=payload_planned, content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["progress_mode"] == "planned"

        # Step 3: Verify BOTH values are preserved
        from detail_project.models import PekerjaanProgressWeekly
        wp = PekerjaanProgressWeekly.objects.get(
            pekerjaan=pekerjaan_with_volume,
            week_number=1
        )

        # Critical assertion: Both fields should retain their values
        assert wp.actual_proportion == Decimal("20.00"), \
            f"Actual proportion should be 20.00, got {wp.actual_proportion}"
        assert wp.planned_proportion == Decimal("30.00"), \
            f"Planned proportion should be 30.00, got {wp.planned_proportion}"
        assert wp.proportion == Decimal("30.00"), \
            f"Legacy proportion should sync with planned (30.00), got {wp.proportion}"

    def test_save_actual_does_not_affect_planned(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """Test that saving actual progress doesn't overwrite planned progress."""
        url = reverse('detail_project:api_v2_assign_weekly', args=[project_with_dates.id])

        # Step 1: Save PLANNED progress = 50%
        payload_planned = {
            "mode": "planned",
            "assignments": [{
                "pekerjaan_id": pekerjaan_with_volume.id,
                "week_number": 2,
                "proportion": 50.00,
                "week_start_date": "2025-01-08",
                "week_end_date": "2025-01-14",
            }]
        }
        response = client_logged.post(url, data=payload_planned, content_type="application/json")
        assert response.status_code == 200

        # Step 2: Save ACTUAL progress = 35%
        payload_actual = {
            "mode": "actual",
            "assignments": [{
                "pekerjaan_id": pekerjaan_with_volume.id,
                "week_number": 2,
                "proportion": 35.00,
                "week_start_date": "2025-01-08",
                "week_end_date": "2025-01-14",
            }]
        }
        response = client_logged.post(url, data=payload_actual, content_type="application/json")
        assert response.status_code == 200

        # Step 3: Verify BOTH values are preserved
        from detail_project.models import PekerjaanProgressWeekly
        wp = PekerjaanProgressWeekly.objects.get(
            pekerjaan=pekerjaan_with_volume,
            week_number=2
        )

        assert wp.planned_proportion == Decimal("50.00"), \
            f"Planned proportion should be 50.00, got {wp.planned_proportion}"
        assert wp.actual_proportion == Decimal("35.00"), \
            f"Actual proportion should be 35.00, got {wp.actual_proportion}"

    def test_multiple_updates_preserve_independence(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """Test that multiple updates maintain field independence."""
        url = reverse('detail_project:api_v2_assign_weekly', args=[project_with_dates.id])

        # Create initial record with both values
        payload = {
            "mode": "planned",
            "assignments": [{
                "pekerjaan_id": pekerjaan_with_volume.id,
                "week_number": 3,
                "proportion": 40.00,
                "week_start_date": "2025-01-15",
                "week_end_date": "2025-01-21",
            }]
        }
        client_logged.post(url, data=payload, content_type="application/json")

        payload["mode"] = "actual"
        payload["assignments"][0]["proportion"] = 25.00
        client_logged.post(url, data=payload, content_type="application/json")

        # Update planned again
        payload["mode"] = "planned"
        payload["assignments"][0]["proportion"] = 45.00
        client_logged.post(url, data=payload, content_type="application/json")

        # Update actual again
        payload["mode"] = "actual"
        payload["assignments"][0]["proportion"] = 30.00
        client_logged.post(url, data=payload, content_type="application/json")

        # Verify final values
        from detail_project.models import PekerjaanProgressWeekly
        wp = PekerjaanProgressWeekly.objects.get(
            pekerjaan=pekerjaan_with_volume,
            week_number=3
        )

        assert wp.planned_proportion == Decimal("45.00"), \
            "Planned should be 45.00 (last planned update)"
        assert wp.actual_proportion == Decimal("30.00"), \
            "Actual should be 30.00 (last actual update)"

    def test_get_api_returns_both_fields(self, client_logged, project_with_dates, pekerjaan_with_volume):
        """Test that GET API returns both planned and actual fields."""
        # Create a record with different planned/actual values
        from detail_project.models import PekerjaanProgressWeekly
        PekerjaanProgressWeekly.objects.create(
            pekerjaan=pekerjaan_with_volume,
            project=project_with_dates,
            week_number=4,
            week_start_date=date(2025, 1, 22),
            week_end_date=date(2025, 1, 28),
            planned_proportion=Decimal("60.00"),
            actual_proportion=Decimal("40.00"),
            proportion=Decimal("60.00")
        )

        # Get via API
        url = reverse('detail_project:api_v2_get_project_assignments', args=[project_with_dates.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

        # Find our record
        assignment = next(
            (a for a in data["assignments"] if a["week_number"] == 4),
            None
        )
        assert assignment is not None

        # Verify both fields are returned
        assert float(assignment["planned_proportion"]) == 60.00
        assert float(assignment["actual_proportion"]) == 40.00
        assert float(assignment["proportion"]) == 60.00  # Legacy field
