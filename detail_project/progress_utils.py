"""
Utility functions for progress calculation and conversion.

This module handles conversion between weekly canonical storage and
daily/monthly views for the Jadwal Pekerjaan feature.

CANONICAL STORAGE: Weekly (PekerjaanProgressWeekly)
DERIVED VIEWS: Daily, Monthly (calculated on-the-fly)
"""

from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from django.db import transaction
from django.db.models import Q


def calculate_week_number(target_date: date, project_start: date, week_end_day: int = 6) -> int:
    """
    Calculate week number relative to project start date.

    Args:
        target_date: The date to calculate week number for
        project_start: Project start date
        week_end_day: Day of week marking the end of the week (0=Monday .. 6=Sunday)

    Returns:
        Week number starting from 1

    Example:
        project_start = 2025-01-01
        target_date = 2025-01-08
        returns: 2 (second week)
    """
    if target_date < project_start:
        return 1

    if week_end_day not in range(7):
        week_end_day = 6

    # Determine the end date of the first (possibly partial) week
    offset_to_end = (week_end_day - project_start.weekday() + 7) % 7
    first_week_end = project_start + timedelta(days=offset_to_end)

    if target_date <= first_week_end:
        return 1

    days_after_first = (target_date - first_week_end).days
    # Each subsequent week spans 7 days
    week_num = 1 + ((days_after_first + 6) // 7)
    return week_num


def get_week_date_range(week_number: int, project_start: date, week_end_day: int = 6) -> Tuple[date, date]:
    """
    Get start and end date for a given week number.

    Args:
        week_number: Week number (1-indexed)
        project_start: Project start date
        week_end_day: Day of week for week boundary (Python weekday: 0=Monday, 6=Sunday)

    Returns:
        Tuple of (week_start_date, week_end_date)

    Example:
        week_number = 1, project_start = 2025-01-01 (Wednesday)
        week_end_day = 6 (Sunday)
        returns: (2025-01-01, 2025-01-05) - Wed to Sun
    """
    # Calculate week start (first day of the week)
    days_offset = (week_number - 1) * 7
    week_start = project_start + timedelta(days=days_offset)

    # Calculate week end based on week_end_day
    days_until_week_end = (week_end_day - week_start.weekday() + 7) % 7

    if days_until_week_end == 0 and week_start.weekday() == week_end_day:
        # Already on week end day
        week_end = week_start
    else:
        week_end = week_start + timedelta(days=days_until_week_end)

    return week_start, week_end


def get_weekly_progress_for_daily_view(
    pekerjaan_id: int,
    target_date: date,
    project_start: date,
    week_end_day: int = 6
) -> Decimal:
    """
    Calculate daily progress from weekly canonical storage.

    Daily view = Weekly proportion / 7 days (equal distribution)

    Args:
        pekerjaan_id: Pekerjaan ID
        target_date: The date to get progress for
        project_start: Project start date
        week_end_day: Day of week marking the end of the week (0=Monday .. 6=Sunday)

    Returns:
        Progress proportion for that day (Decimal)
    """
    from detail_project.models import PekerjaanProgressWeekly

    week_num = calculate_week_number(target_date, project_start, week_end_day)

    try:
        weekly_progress = PekerjaanProgressWeekly.objects.get(
            pekerjaan_id=pekerjaan_id,
            week_number=week_num
        )

        # Distribute weekly proportion equally across 7 days
        # NOTE: This is a simplified distribution. In reality, weeks might have different lengths.
        # For accurate distribution, we need to count actual days in the week.
        week_start, week_end = weekly_progress.week_start_date, weekly_progress.week_end_date
        days_in_week = (week_end - week_start).days + 1

        daily_proportion = weekly_progress.proportion / Decimal(days_in_week)

        return daily_proportion.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    except PekerjaanProgressWeekly.DoesNotExist:
        return Decimal('0.00')


def get_weekly_progress_for_monthly_view(
    pekerjaan_id: int,
    month_start: date,
    month_end: date,
    project_start: date
) -> Decimal:
    """
    Calculate monthly progress from weekly canonical storage.

    Monthly view = Sum of all weekly proportions that fall within the month

    Args:
        pekerjaan_id: Pekerjaan ID
        month_start: Start date of month
        month_end: End date of month
        project_start: Project start date

    Returns:
        Total progress proportion for that month (Decimal)
    """
    from detail_project.models import PekerjaanProgressWeekly

    # Get all weekly progress records that overlap with this month
    weekly_records = PekerjaanProgressWeekly.objects.filter(
        pekerjaan_id=pekerjaan_id,
        week_start_date__lte=month_end,
        week_end_date__gte=month_start
    )

    total_proportion = Decimal('0.00')

    for weekly in weekly_records:
        # Calculate overlap between week and month
        overlap_start = max(weekly.week_start_date, month_start)
        overlap_end = min(weekly.week_end_date, month_end)
        overlap_days = (overlap_end - overlap_start).days + 1

        # Calculate proportion for this week within the month
        week_days = (weekly.week_end_date - weekly.week_start_date).days + 1
        proportion_in_month = (weekly.proportion * Decimal(overlap_days)) / Decimal(week_days)

        total_proportion += proportion_in_month

    return total_proportion.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def sync_weekly_to_tahapan(
    project_id: int,
    mode: str = 'weekly',
    week_end_day: int = 6
) -> int:
    """
    Synchronize PekerjaanProgressWeekly (canonical) to PekerjaanTahapan (view layer).

    This function regenerates PekerjaanTahapan assignments based on current mode,
    deriving values from the weekly canonical storage.

    Process:
    1. Delete all existing PekerjaanTahapan for this project
    2. For each TahapPelaksanaan (based on current mode):
       - Calculate proportion from weekly canonical data
       - Create PekerjaanTahapan record

    Args:
        project_id: Project ID
        mode: Time scale mode ('daily', 'weekly', 'monthly', 'custom')
        week_end_day: Week boundary day (Python weekday: 0=Monday, 6=Sunday)

    Returns:
        Number of PekerjaanTahapan records created
    """
    from detail_project.models import PekerjaanProgressWeekly, PekerjaanTahapan, TahapPelaksanaan
    from dashboard.models import Project

    project = Project.objects.get(id=project_id)

    # Step 1: Delete old PekerjaanTahapan assignments
    PekerjaanTahapan.objects.filter(tahapan__project=project).delete()

    # Step 2: Get all tahapan for this project (should match the mode)
    tahapan_list = TahapPelaksanaan.objects.filter(
        project=project
    ).order_by('urutan')

    if not tahapan_list.exists():
        return 0

    # Step 3: Get all weekly progress for this project
    weekly_progress_qs = PekerjaanProgressWeekly.objects.filter(
        project=project
    ).select_related('pekerjaan')

    # Group by pekerjaan
    pekerjaan_progress = defaultdict(list)
    for wp in weekly_progress_qs:
        pekerjaan_progress[wp.pekerjaan_id].append(wp)

    # Step 4: For each pekerjaan, calculate proportions for each tahapan
    assignments_to_create = []

    for pekerjaan_id, weekly_records in pekerjaan_progress.items():
        for tahap in tahapan_list:
            if not tahap.tanggal_mulai or not tahap.tanggal_selesai:
                continue

            # Calculate proportion for this tahapan based on mode
            if mode == 'daily':
                # Daily: Each tahapan is 1 day, get daily proportion
                proportion = get_weekly_progress_for_daily_view(
                    pekerjaan_id,
                    tahap.tanggal_mulai,
                    project.tanggal_mulai,
                    week_end_day
                )
            elif mode == 'weekly':
                # Weekly: Direct mapping from canonical storage
                urutan_index = tahap.urutan if tahap.urutan is not None else 0
                week_num = urutan_index + 1
                try:
                    weekly_rec = next(w for w in weekly_records if w.week_number == week_num)
                    proportion = weekly_rec.proportion
                except StopIteration:
                    proportion = Decimal('0.00')
            elif mode == 'monthly':
                # Monthly: Sum all weeks in this month
                proportion = get_weekly_progress_for_monthly_view(
                    pekerjaan_id,
                    tahap.tanggal_mulai,
                    tahap.tanggal_selesai,
                    project.tanggal_mulai
                )
            else:
                # Custom: Sum all weeks that overlap with tahapan date range
                proportion = get_weekly_progress_for_monthly_view(
                    pekerjaan_id,
                    tahap.tanggal_mulai,
                    tahap.tanggal_selesai,
                    project.tanggal_mulai
                )

            # Only create assignment if proportion > 0
            if proportion > Decimal('0.01'):
                assignments_to_create.append(
                    PekerjaanTahapan(
                        pekerjaan_id=pekerjaan_id,
                        tahapan=tahap,
                        proporsi_volume=proportion,
                        catatan='Synced from weekly canonical storage'
                    )
                )

    # Bulk create
    if assignments_to_create:
        PekerjaanTahapan.objects.bulk_create(assignments_to_create)

    return len(assignments_to_create)


def _build_weekly_tahapan_instances(project, week_start_day=0, week_end_day=6):
    """
    Create TahapPelaksanaan instances for weekly mode based on project timeline.
    """
    from detail_project.models import TahapPelaksanaan

    if not project.tanggal_mulai or not project.tanggal_selesai:
        return []

    week_start_day %= 7
    week_end_day %= 7

    tahapan_list = []
    current_start = project.tanggal_mulai
    week_num = 1
    day_names_id = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']

    while current_start <= project.tanggal_selesai:
        days_until_end = (week_end_day - current_start.weekday()) % 7
        current_end = current_start + timedelta(days=days_until_end)

        if current_end > project.tanggal_selesai:
            current_end = project.tanggal_selesai

        days_in_week = (current_end - current_start).days + 1
        start_str = current_start.strftime("%d/%m")
        end_str = current_end.strftime("%d/%m")
        start_day_name = day_names_id[current_start.weekday()]
        end_day_name = day_names_id[current_end.weekday()]

        label = f"Week {week_num}: {start_str} ({start_day_name}) - {end_str} ({end_day_name})"

        tahapan_list.append(
            TahapPelaksanaan(
                project=project,
                nama=label,
                urutan=week_num - 1,
                tanggal_mulai=current_start,
                tanggal_selesai=current_end,
                is_auto_generated=True,
                generation_mode='weekly',
                deskripsi=f"{days_in_week} hari"
            )
        )

        current_start = current_end + timedelta(days=1)
        week_num += 1

        if week_num > 100:
            break

    return tahapan_list


@transaction.atomic
def reset_project_progress(project, regenerate_weekly=True):
    """
    Delete canonical progress, assignments, and autogenerated tahapan for the project.
    Optionally regenerate weekly tahapan structure using current timeline.
    """
    from detail_project.models import (
        PekerjaanProgressWeekly,
        PekerjaanTahapan,
        TahapPelaksanaan,
    )

    if project is None:
        raise ValueError("Project instance is required to reset progress")

    weekly_deleted, _ = PekerjaanProgressWeekly.objects.filter(project=project).delete()
    assignments_deleted, _ = PekerjaanTahapan.objects.filter(tahapan__project=project).delete()
    tahapan_deleted, _ = TahapPelaksanaan.objects.filter(project=project, is_auto_generated=True).delete()

    tahapan_created = 0
    if regenerate_weekly and project.tanggal_mulai and project.tanggal_selesai:
        week_start = project.week_start_day if project.week_start_day is not None else 0
        week_end = project.week_end_day if project.week_end_day is not None else ((week_start + 6) % 7)
        new_tahapan = _build_weekly_tahapan_instances(project, week_start, week_end)
        if new_tahapan:
            TahapPelaksanaan.objects.bulk_create(new_tahapan)
            tahapan_created = len(new_tahapan)

    return {
        'weekly_deleted': weekly_deleted,
        'assignments_deleted': assignments_deleted,
        'tahapan_deleted': tahapan_deleted,
        'tahapan_created': tahapan_created,
    }


@transaction.atomic
def migrate_existing_data_to_weekly_canonical(project_id: int) -> Dict[str, int]:
    """
    Migrate existing PekerjaanTahapan data to PekerjaanProgressWeekly (canonical storage).

    This is a ONE-TIME data migration function to be run after deploying the new model.

    Strategy:
    1. Read all existing PekerjaanTahapan records
    2. Convert to weekly canonical format using daily distribution method
    3. Save to PekerjaanProgressWeekly
    4. Preserve total proportions

    Args:
        project_id: Project ID to migrate

    Returns:
        Dict with migration stats: {'weekly_created': N, 'old_assignments': M}
    """
    from detail_project.models import PekerjaanProgressWeekly, PekerjaanTahapan, TahapPelaksanaan
    from dashboard.models import Project

    project = Project.objects.get(id=project_id)

    if not project.tanggal_mulai:
        raise ValueError("Project must have tanggal_mulai set")

    # Step 1: Get all existing assignments
    old_assignments = PekerjaanTahapan.objects.filter(
        tahapan__project=project
    ).select_related('pekerjaan', 'tahapan').values(
        'pekerjaan_id',
        'tahapan__tanggal_mulai',
        'tahapan__tanggal_selesai',
        'proporsi_volume'
    )

    if not old_assignments:
        return {'weekly_created': 0, 'old_assignments': 0}

    # Step 2: Build daily distribution map per pekerjaan
    pekerjaan_daily_map = defaultdict(lambda: defaultdict(Decimal))

    for assignment in old_assignments:
        pekerjaan_id = assignment['pekerjaan_id']
        start_date = assignment['tahapan__tanggal_mulai']
        end_date = assignment['tahapan__tanggal_selesai']
        proportion = Decimal(str(assignment['proporsi_volume']))

        if not start_date or not end_date:
            continue

        # Distribute proportion equally across days
        num_days = (end_date - start_date).days + 1
        daily_prop = proportion / Decimal(num_days)

        current_date = start_date
        while current_date <= end_date:
            pekerjaan_daily_map[pekerjaan_id][current_date] += daily_prop
            current_date += timedelta(days=1)

    # Step 3: Aggregate daily map into weekly canonical format
    weekly_records_to_create = []

    week_end_day = 6  # Default week boundary (Sunday); adjust if project stores a custom value

    for pekerjaan_id, daily_map in pekerjaan_daily_map.items():
        # Group daily data by week
        week_proportions = defaultdict(Decimal)
        week_dates = {}  # week_num -> (start, end)

        for day, prop in daily_map.items():
            week_num = calculate_week_number(day, project.tanggal_mulai, week_end_day=week_end_day)
            week_proportions[week_num] += prop

            # Track week date range
            if week_num not in week_dates:
                week_start, week_end = get_week_date_range(week_num, project.tanggal_mulai, week_end_day)
                week_dates[week_num] = (week_start, week_end)

        # Create weekly records
        for week_num, total_prop in week_proportions.items():
            if total_prop > Decimal('0.01'):
                week_start, week_end = week_dates[week_num]

                weekly_records_to_create.append(
                    PekerjaanProgressWeekly(
                        pekerjaan_id=pekerjaan_id,
                        project=project,
                        week_number=week_num,
                        week_start_date=week_start,
                        week_end_date=week_end,
                        proportion=total_prop.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                        notes='Migrated from existing PekerjaanTahapan data'
                    )
                )

    # Step 4: Bulk create
    if weekly_records_to_create:
        PekerjaanProgressWeekly.objects.bulk_create(
            weekly_records_to_create,
            ignore_conflicts=True  # Skip if already exists
        )

    return {
        'weekly_created': len(weekly_records_to_create),
        'old_assignments': len(old_assignments)
    }
