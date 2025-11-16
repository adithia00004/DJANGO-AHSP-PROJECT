import logging
from datetime import date
from decimal import Decimal

import pytest

from detail_project import monitoring_helpers as mh
from detail_project import progress_utils as pu
from detail_project.models import (
    Pekerjaan,
    PekerjaanProgressWeekly,
)


def test_log_operation_formats_decimal(caplog):
    caplog.set_level(logging.INFO, mh.logger.name)
    mh.log_operation("bundle_test", duration=Decimal("1.23"), attempts=2)
    assert "[BUNDLE_TEST]" in caplog.text
    assert "duration=1.23" in caplog.text
    assert "attempts=2" in caplog.text


def test_log_error_includes_exception(caplog):
    caplog.set_level(logging.ERROR, mh.logger.name)

    try:
        raise ValueError("boom")
    except ValueError as exc:
        mh.log_error("failing_operation", exc, pekerjaan_id=99)

    assert "ValueError" in caplog.text
    assert "pekerjaan_id=99" in caplog.text


def test_monitor_decorator_logs_start_and_complete(caplog):
    caplog.set_level(logging.INFO, mh.logger.name)

    class Dummy:
        def __init__(self, ident):
            self.id = ident

    @mh.monitor("demo_op")
    def dummy_fn(project, pekerjaan):
        return project.id + pekerjaan.id

    result = dummy_fn(Dummy(1), Dummy(2))
    assert result == 3
    assert "[DEMO_OP_START]" in caplog.text
    assert "[DEMO_OP_COMPLETE]" in caplog.text


def test_collect_metric_summary_and_reset():
    mh.reset_metrics()
    mh.collect_metric("custom_metric", 5, project_id=1)
    summary = mh.get_metrics_summary()
    assert summary["custom_metric"]["count"] == 1
    recent = summary["custom_metric"]["recent"]
    assert len(recent) == 1
    assert recent[0]["value"] == 5
    assert recent[0]["project_id"] == 1
    mh.reset_metrics()
    assert mh.get_metrics_summary().get("custom_metric", {}).get("count") == 0


def test_log_bundle_expansion_records_metric(caplog):
    caplog.set_level(logging.INFO, mh.logger.name)
    mh.reset_metrics()
    mh.log_bundle_expansion(
        project_id=1,
        pekerjaan_id=2,
        bundle_kode="LAIN.001",
        ref_kind="job",
        ref_id=5,
        component_count=3,
        duration_ms=50,
    )
    summary = mh.get_metrics_summary()
    assert summary["bundle_expansions"]["count"] == 1
    assert "component_count=3" in caplog.text


def test_log_cascade_and_orphan_helpers_capture_metrics():
    mh.reset_metrics()
    mh.log_cascade_operation(
        project_id=1,
        modified_pekerjaan_id=2,
        referencing_pekerjaan_ids=[3, 4],
        cascade_depth=2,
        re_expanded_count=1,
        duration_ms=10,
    )
    mh.log_orphan_detection(project_id=1, orphan_count=2, total_items=10)
    summary = mh.get_metrics_summary()
    assert summary["cascade_operations"]["count"] == 1
    assert summary["orphan_detections"]["count"] == 1


def test_log_circular_and_lock_conflict(caplog):
    caplog.set_level(logging.WARNING, mh.logger.name)
    mh.reset_metrics()
    mh.log_circular_dependency_check(1, 2, 3, is_circular=True)
    mh.log_optimistic_lock_conflict(
        project_id=1,
        pekerjaan_id=5,
        client_timestamp="2025-01-01T00:00:00Z",
        server_timestamp="2025-01-02T00:00:00Z",
    )
    summary = mh.get_metrics_summary()
    assert summary["circular_dependencies"]["count"] == 1
    assert summary["lock_conflicts"]["count"] == 1
    assert "CIRCULAR_DEPENDENCY_CHECK" in caplog.text
    assert "OPTIMISTIC_LOCK_CONFLICT" in caplog.text


def test_get_monitoring_health_returns_summary():
    mh.reset_metrics()
    mh.collect_metric("bundle_expansions", 1)
    health = mh.get_monitoring_health()
    assert health["is_healthy"] is True
    assert health["metrics_count"] >= 1
    assert "bundle_expansions" in health["summary"]


def test_calculate_week_number_and_range():
    project_start = date(2025, 1, 1)  # Wednesday
    assert pu.calculate_week_number(date(2025, 1, 1), project_start, week_end_day=6) == 1
    assert pu.calculate_week_number(date(2025, 1, 10), project_start, week_end_day=6) == 2
    week_start, week_end = pu.get_week_date_range(1, project_start, week_end_day=6)
    assert week_start == date(2025, 1, 1)
    assert week_end == date(2025, 1, 5)


@pytest.mark.django_db
def test_get_weekly_progress_for_daily_view(project, sub_klas):
    project.tanggal_mulai = date(2025, 1, 1)
    project.save(update_fields=["tanggal_mulai"])
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="WK-001",
        snapshot_uraian="Weekly Item",
        snapshot_satuan="m2",
        ordering_index=1,
    )
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan,
        project=project,
        week_number=1,
        week_start_date=date(2025, 1, 1),
        week_end_date=date(2025, 1, 5),
        proportion=Decimal("10.00"),
    )

    result = pu.get_weekly_progress_for_daily_view(
        pekerjaan.id,
        date(2025, 1, 2),
        project_start=project.tanggal_mulai,
        week_end_day=6,
    )
    assert result == Decimal("2.00")


@pytest.mark.django_db
def test_get_weekly_progress_for_monthly_view(project, sub_klas):
    project.tanggal_mulai = date(2025, 1, 1)
    project.save(update_fields=["tanggal_mulai"])
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="WK-002",
        snapshot_uraian="Weekly Item 2",
        snapshot_satuan="m2",
        ordering_index=2,
    )
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan,
        project=project,
        week_number=1,
        week_start_date=date(2025, 1, 1),
        week_end_date=date(2025, 1, 5),
        proportion=Decimal("5.00"),
    )
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan,
        project=project,
        week_number=2,
        week_start_date=date(2025, 1, 6),
        week_end_date=date(2025, 1, 12),
        proportion=Decimal("7.00"),
    )

    total = pu.get_weekly_progress_for_monthly_view(
        pekerjaan.id,
        month_start=date(2025, 1, 1),
        month_end=date(2025, 1, 31),
        project_start=project.tanggal_mulai,
    )
    assert total == Decimal("12.00")
