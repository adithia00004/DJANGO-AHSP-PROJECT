"""Canonical serialization and transfer helpers for weekly Jadwal progress."""

from decimal import Decimal

from detail_project.models import PekerjaanProgressWeekly
from detail_project.progress_utils import build_week_buckets
from detail_project.timeline_utils import expected_week_count


def serialize_weekly_rows(project, pekerjaan_ref_by_id):
    """Serialize every canonical progress field with the caller's work refs."""
    rows = PekerjaanProgressWeekly.objects.filter(project=project).order_by(
        "pekerjaan_id", "week_number"
    )
    return [
        {
            "_pekerjaan_ref": pekerjaan_ref_by_id.get(row.pekerjaan_id),
            "week_number": row.week_number,
            "week_start_date": row.week_start_date.isoformat() if row.week_start_date else None,
            "week_end_date": row.week_end_date.isoformat() if row.week_end_date else None,
            "planned_proportion": str(row.planned_proportion or 0),
            "actual_proportion": str(row.actual_proportion or 0),
            "actual_cost": str(row.actual_cost) if row.actual_cost is not None else None,
            "notes": row.notes or "",
        }
        for row in rows
        if pekerjaan_ref_by_id.get(row.pekerjaan_id) is not None
    ]


def _canonical_week_dates(project):
    start = getattr(project, "tanggal_mulai", None)
    end = getattr(project, "tanggal_selesai", None)
    if not start or not end:
        return {}
    week_end_day = getattr(project, "week_end_day", 6)
    week_end_day = week_end_day if week_end_day is not None else 6
    week_count = expected_week_count(start, end, week_end_day)
    if not week_count:
        return {}
    return {
        number: (week_start, week_end)
        for number, week_start, week_end in build_week_buckets(
            start, end, week_end_day, max_weeks=week_count
        )
    }


def _decimal(value, default="0"):
    if value in (None, ""):
        value = default
    return Decimal(str(value))


def _weekly_row(*, project, pekerjaan_id, week_number, week_start, week_end,
                planned, actual, actual_cost, notes):
    return PekerjaanProgressWeekly(
        project=project,
        pekerjaan_id=pekerjaan_id,
        week_number=week_number,
        week_start_date=week_start,
        week_end_date=week_end,
        planned_proportion=planned,
        actual_proportion=actual,
        actual_cost=actual_cost,
        notes=notes or "",
    )


def restore_weekly_rows(project, rows, pekerjaan_map):
    """Restore backup rows, falling back to canonical dates for older backups.

    Returns counts so the caller can report records that did not fit the target
    project timeline or could not be mapped to an imported pekerjaan.
    """
    week_dates = _canonical_week_dates(project)
    pending = []
    skipped = 0
    seen = set()
    for data in rows or []:
        try:
            ref = data.get("_pekerjaan_ref")
            pekerjaan_id = pekerjaan_map.get(ref)
            week_number = int(data.get("week_number"))
        except (AttributeError, TypeError, ValueError):
            skipped += 1
            continue
        key = (pekerjaan_id, week_number)
        if not pekerjaan_id or week_number not in week_dates or key in seen:
            skipped += 1
            continue
        seen.add(key)
        canonical_start, canonical_end = week_dates[week_number]
        week_start = data.get("week_start_date")
        week_end = data.get("week_end_date")
        if week_start and week_end:
            try:
                from datetime import date
                week_start = date.fromisoformat(week_start)
                week_end = date.fromisoformat(week_end)
            except (TypeError, ValueError):
                week_start, week_end = canonical_start, canonical_end
        else:
            week_start, week_end = canonical_start, canonical_end

        raw_cost = data.get("actual_cost")
        actual_cost = None if raw_cost in (None, "") else _decimal(raw_cost)
        pending.append(_weekly_row(
            project=project,
            pekerjaan_id=pekerjaan_id,
            week_number=week_number,
            week_start=week_start,
            week_end=week_end,
            planned=_decimal(data.get("planned_proportion", 0)),
            actual=_decimal(data.get("actual_proportion", 0)),
            actual_cost=actual_cost,
            notes=data.get("notes", ""),
        ))
    if pending:
        PekerjaanProgressWeekly.objects.bulk_create(pending, batch_size=500)
    return {"imported": len(pending), "skipped": skipped}


def copy_weekly_rows(source, target, pekerjaan_map):
    """Copy canonical rows by week ordinal, rebuilding dates for target start.

    Weeks beyond a shorter target timeline are omitted and counted. A changed
    start date does not shift values to a different week number.
    """
    target_dates = _canonical_week_dates(target)
    pending = []
    skipped_rows = []
    for row in PekerjaanProgressWeekly.objects.filter(project=source).order_by(
        "pekerjaan_id", "week_number"
    ):
        pekerjaan_id = pekerjaan_map.get(row.pekerjaan_id)
        target_bucket = target_dates.get(row.week_number)
        if not pekerjaan_id:
            skipped_rows.append({
                "pekerjaan_id": row.pekerjaan_id,
                "week_number": row.week_number,
                "reason": "pekerjaan_not_copied",
            })
            continue
        if target_bucket is None:
            skipped_rows.append({
                "pekerjaan_id": row.pekerjaan_id,
                "week_number": row.week_number,
                "reason": "week_outside_target_timeline",
            })
            continue
        pending.append(_weekly_row(
            project=target,
            pekerjaan_id=pekerjaan_id,
            week_number=row.week_number,
            week_start=target_bucket[0],
            week_end=target_bucket[1],
            planned=row.planned_proportion,
            actual=row.actual_proportion,
            actual_cost=row.actual_cost,
            notes=row.notes,
        ))
    if pending:
        PekerjaanProgressWeekly.objects.bulk_create(pending, batch_size=500)
    return {
        "copied": len(pending),
        "skipped": len(skipped_rows),
        "skipped_rows": skipped_rows,
    }
