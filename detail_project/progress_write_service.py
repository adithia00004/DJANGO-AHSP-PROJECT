"""Single persistence path for canonical weekly progress writes."""

from decimal import Decimal

from django.db import transaction

from detail_project.models import PekerjaanProgressWeekly


WRITE_KINDS = frozenset({"planned_new", "actual", "historical", "user_move"})


@transaction.atomic
def write_progress(project, cells, *, kind):
    """Create/update canonical weekly rows while preserving unrelated fields.

    ``kind`` describes which side of the weekly row the caller is allowed to
    write. Timeline/ownership/range and cumulative-total validation remain with
    the calling API; contract-specific rules can be added here in step 1.3.
    """
    if kind not in WRITE_KINDS:
        raise ValueError(f"Unknown progress write kind: {kind}")

    results = []
    for cell in cells:
        pekerjaan_id = cell["pekerjaan_id"]
        week_number = int(cell["week_number"])
        week_start = cell["week_start_date"]
        week_end = cell["week_end_date"]
        notes = cell.get("notes", "") or ""

        planned = Decimal(str(cell.get("planned_proportion", 0) or 0))
        actual = Decimal(str(cell.get("actual_proportion", 0) or 0))
        has_actual_cost = cell.get("has_actual_cost", "actual_cost" in cell)
        clear_actual_cost = cell.get("clear_actual_cost", False)
        actual_cost = cell.get("actual_cost")
        if has_actual_cost and actual_cost is not None:
            actual_cost = Decimal(str(actual_cost))

        if kind == "planned_new":
            actual = Decimal("0")
            actual_cost = None
        elif kind == "actual":
            planned = Decimal("0")
            if not has_actual_cost or clear_actual_cost:
                actual_cost = None
        elif kind == "user_move":
            actual = Decimal("0")
            actual_cost = None

        defaults = {
            "project": project,
            "week_start_date": week_start,
            "week_end_date": week_end,
            "planned_proportion": planned,
            "actual_proportion": actual,
            "actual_cost": actual_cost,
            "notes": notes,
        }
        row, created = PekerjaanProgressWeekly.objects.get_or_create(
            pekerjaan_id=pekerjaan_id,
            week_number=week_number,
            defaults=defaults,
        )

        if not created:
            row.project = project
            row.week_start_date = week_start
            row.week_end_date = week_end
            if kind in {"planned_new", "historical", "user_move"}:
                row.planned_proportion = planned
            if kind in {"actual", "historical"}:
                row.actual_proportion = actual
            if kind == "historical":
                row.actual_cost = actual_cost
                row.notes = notes
            elif kind == "actual":
                row.notes = notes
                if clear_actual_cost:
                    row.actual_cost = None
                elif has_actual_cost:
                    row.actual_cost = actual_cost
            elif kind == "planned_new":
                row.notes = notes
            row.save()

        results.append({"record": row, "created": created})
    return results
