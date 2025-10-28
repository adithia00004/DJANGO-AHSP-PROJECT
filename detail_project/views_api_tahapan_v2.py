"""
API v2 for Tahapan Management with Weekly Canonical Storage.

This module provides updated API endpoints that use PekerjaanProgressWeekly
as the canonical storage (single source of truth).

Key differences from v1:
- Progress is always stored in weekly units
- Daily/monthly are calculated views (not stored)
- Mode switching does NOT cause data loss
- No rounding errors from repeated conversions
"""

import json
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, date

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Q

from detail_project.models import (
    TahapPelaksanaan,
    PekerjaanTahapan,
    PekerjaanProgressWeekly,
    Pekerjaan
)
from detail_project.progress_utils import (
    get_week_date_range,
    sync_weekly_to_tahapan,
    get_weekly_progress_for_daily_view,
    get_weekly_progress_for_monthly_view
)

# Import helper from original views
from detail_project.views_api_tahapan import _owner_or_404


@login_required
@require_POST
@transaction.atomic
def api_assign_pekerjaan_weekly(request, project_id):
    """
    Assign pekerjaan progress in WEEKLY units (canonical storage).

    This is the NEW canonical API for saving progress data.
    All progress should be saved through this endpoint in weekly units.

    POST Body:
        {
            "assignments": [
                {
                    "pekerjaan_id": 322,
                    "week_number": 1,
                    "proportion": 25.50,
                    "notes": "Optional notes"
                },
                {
                    "pekerjaan_id": 322,
                    "week_number": 2,
                    "proportion": 50.00
                }
            ]
        }

    Returns:
        {
            "ok": true,
            "message": "2 weekly progress records saved",
            "assignments": [...]
        }
    """
    project = _owner_or_404(project_id, request.user)

    if not project.tanggal_mulai:
        return JsonResponse({
            'ok': False,
            'error': 'Project must have tanggal_mulai set'
        }, status=400)

    try:
        data = json.loads(request.body)
        assignments = data.get('assignments', [])
        mode = (data.get('mode') or 'weekly').lower()
        if mode not in {'daily', 'weekly', 'monthly', 'custom'}:
            mode = 'weekly'

        week_end_day = data.get('week_end_day', 6)
        try:
            week_end_day = int(week_end_day)
        except (TypeError, ValueError):
            week_end_day = 6

        if not isinstance(assignments, list):
            return JsonResponse({
                'ok': False,
                'error': 'assignments must be an array'
            }, status=400)

        created_count = 0
        updated_count = 0
        saved_assignments = []
        errors = []

        for item in assignments:
            pekerjaan_id = item.get('pekerjaan_id')
            week_number = item.get('week_number')
            proportion = item.get('proportion')
            notes = item.get('notes', '')

            # Validation
            if not pekerjaan_id:
                errors.append({'error': 'pekerjaan_id required', 'item': item})
                continue

            if not week_number or week_number < 1:
                errors.append({'error': 'week_number must be >= 1', 'item': item})
                continue

            if proportion is None:
                errors.append({'error': 'proportion required', 'item': item})
                continue

            try:
                proportion_decimal = Decimal(str(proportion))
                if proportion_decimal < Decimal('0.01') or proportion_decimal > Decimal('100'):
                    errors.append({
                        'error': f'Proportion must be 0.01-100, got {proportion}',
                        'pekerjaan_id': pekerjaan_id
                    })
                    continue
            except (InvalidOperation, ValueError):
                errors.append({
                    'error': f'Invalid proportion: {proportion}',
                    'pekerjaan_id': pekerjaan_id
                })
                continue

            # Get pekerjaan
            try:
                pekerjaan = Pekerjaan.objects.get(id=pekerjaan_id)
                # Verify project ownership
                if pekerjaan.project_id != project.id:
                    errors.append({
                        'error': f'Pekerjaan {pekerjaan_id} does not belong to this project',
                        'pekerjaan_id': pekerjaan_id
                    })
                    continue
            except Pekerjaan.DoesNotExist:
                errors.append({
                    'error': f'Pekerjaan {pekerjaan_id} not found',
                    'pekerjaan_id': pekerjaan_id
                })
                continue

            # Get week date range from corresponding tahapan for consistency
            # Look for weekly tahapan with matching week number (inferred from urutan)
            try:
                weekly_tahapan = TahapPelaksanaan.objects.filter(
                    project=project,
                    is_auto_generated=True,
                    generation_mode='weekly',
                    urutan=week_number - 1  # urutan is 0-indexed
                ).first()

                if weekly_tahapan:
                    week_start = weekly_tahapan.tanggal_mulai
                    week_end = weekly_tahapan.tanggal_selesai
                else:
                    # Fallback: calculate from project start if tahapan not found
                    week_start, week_end = get_week_date_range(
                        week_number,
                        project.tanggal_mulai,
                        week_end_day=6  # Sunday
                    )
            except Exception:
                # Fallback: calculate from project start
                week_start, week_end = get_week_date_range(
                    week_number,
                    project.tanggal_mulai,
                    week_end_day=6  # Sunday
                )

            # Create or update weekly progress (CANONICAL STORAGE)
            wp, created = PekerjaanProgressWeekly.objects.update_or_create(
                pekerjaan=pekerjaan,
                week_number=week_number,
                defaults={
                    'project': project,
                    'week_start_date': week_start,
                    'week_end_date': week_end,
                    'proportion': proportion_decimal,
                    'notes': notes
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            saved_assignments.append({
                'pekerjaan_id': pekerjaan_id,
                'week_number': week_number,
                'week_start_date': week_start.isoformat(),
                'week_end_date': week_end.isoformat(),
                'proportion': float(proportion_decimal),
                'notes': notes
            })

        # STEP 2: Validate total progress per pekerjaan ≤ 100%
        # Group new assignments by pekerjaan_id
        from collections import defaultdict
        pekerjaan_totals = defaultdict(Decimal)

        for item in assignments:
            pekerjaan_id = item.get('pekerjaan_id')
            proportion = item.get('proportion')

            if pekerjaan_id and proportion is not None:
                try:
                    pekerjaan_totals[pekerjaan_id] += Decimal(str(proportion))
                except (InvalidOperation, ValueError):
                    pass  # Already handled in validation above

        # Check if any pekerjaan exceeds 100%
        validation_errors = []
        for pekerjaan_id, total in pekerjaan_totals.items():
            if total > Decimal('100.00'):
                validation_errors.append({
                    'error': f'Total progress {float(total):.2f}% exceeds 100%',
                    'pekerjaan_id': pekerjaan_id,
                    'total': float(total),
                    'max_allowed': 100.0
                })

        if validation_errors:
            return JsonResponse({
                'ok': False,
                'error': 'Validation failed: Total progress exceeds 100%',
                'validation_errors': validation_errors
            }, status=400)

        # If errors, return them
        if errors:
            return JsonResponse({
                'ok': False,
                'error': 'Some assignments failed',
                'errors': errors,
                'saved': saved_assignments
            }, status=400)

        # Success: keep PekerjaanTahapan (view layer) in sync so legacy reads stay accurate.
        try:
            synced_count = sync_weekly_to_tahapan(project.id, mode=mode, week_end_day=week_end_day)
        except Exception as sync_error:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Assignments saved, but failed to sync view layer: {sync_error}',
                'created_count': created_count,
                'updated_count': updated_count,
                'assignments': saved_assignments
            }, status=500)

        return JsonResponse({
            'ok': True,
            'message': f'{created_count} created, {updated_count} updated',
            'created_count': created_count,
            'updated_count': updated_count,
            'assignments': saved_assignments,
            'synced_assignments': synced_count,
            'synced_mode': mode
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_GET
def api_get_pekerjaan_weekly_progress(request, project_id, pekerjaan_id):
    """
    Get weekly progress for a pekerjaan (canonical storage).

    Returns the raw weekly progress data without conversion.

    Returns:
        {
            "ok": true,
            "pekerjaan_id": 322,
            "weekly_progress": [
                {
                    "week_number": 1,
                    "week_start_date": "2025-10-26",
                    "week_end_date": "2025-11-01",
                    "proportion": 25.50,
                    "notes": "..."
                },
                ...
            ],
            "total_proportion": 100.00
        }
    """
    project = _owner_or_404(project_id, request.user)
    pekerjaan = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    weekly_progress = PekerjaanProgressWeekly.objects.filter(
        pekerjaan=pekerjaan
    ).order_by('week_number')

    total_proportion = weekly_progress.aggregate(
        total=Sum('proportion')
    )['total'] or Decimal('0.00')

    return JsonResponse({
        'ok': True,
        'pekerjaan_id': pekerjaan.id,
        'weekly_progress': [
            {
                'week_number': wp.week_number,
                'week_start_date': wp.week_start_date.isoformat(),
                'week_end_date': wp.week_end_date.isoformat(),
                'proportion': float(wp.proportion),
                'notes': wp.notes,
                'created_at': wp.created_at.isoformat(),
                'updated_at': wp.updated_at.isoformat()
            }
            for wp in weekly_progress
        ],
        'total_proportion': float(total_proportion),
        'is_complete': abs(float(total_proportion) - 100.0) < 0.01
    })


@login_required
@require_GET
def api_get_pekerjaan_assignments_v2(request, project_id, pekerjaan_id):
    """
    Get pekerjaan assignments in current time scale mode (daily/weekly/monthly).

    This endpoint converts weekly canonical storage to the requested view mode.

    Query params:
        ?mode=daily|weekly|monthly|custom (optional, defaults to weekly)

    Returns:
        {
            "ok": true,
            "pekerjaan_id": 322,
            "mode": "weekly",
            "assignments": [
                {
                    "tahapan_id": 855,
                    "tahapan_nama": "Week 1",
                    "proporsi": 25.50,
                    "urutan": 1
                },
                ...
            ],
            "total_proporsi": 100.00
        }
    """
    project = _owner_or_404(project_id, request.user)
    pekerjaan = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    mode = request.GET.get('mode', 'weekly')

    if mode not in ['daily', 'weekly', 'monthly', 'custom']:
        return JsonResponse({
            'ok': False,
            'error': 'Invalid mode. Must be: daily, weekly, monthly, or custom'
        }, status=400)

    # Get tahapan list for this project in the requested mode
    tahapan_list = TahapPelaksanaan.objects.filter(
        project=project
    ).order_by('urutan')

    if mode != 'custom':
        # Filter by generation_mode
        tahapan_list = tahapan_list.filter(
            is_auto_generated=True,
            generation_mode=mode
        )

    # Get weekly progress (canonical)
    weekly_progress = list(PekerjaanProgressWeekly.objects.filter(
        pekerjaan=pekerjaan
    ).order_by('week_number'))

    # Convert to assignments based on mode
    assignments = []
    total_proporsi = Decimal('0.00')

    for tahap in tahapan_list:
        if not tahap.tanggal_mulai or not tahap.tanggal_selesai:
            continue

        if mode == 'daily':
            # Daily: Get proportion for this day
            proporsi = get_weekly_progress_for_daily_view(
                pekerjaan.id,
                tahap.tanggal_mulai,
                project.tanggal_mulai
            )
        elif mode == 'weekly':
            # Weekly: Direct from canonical
            urutan_index = tahap.urutan if tahap.urutan is not None else 0
            week_num = urutan_index + 1
            try:
                wp = next(w for w in weekly_progress if w.week_number == week_num)
                proporsi = wp.proportion
            except StopIteration:
                proporsi = Decimal('0.00')
        else:
            # Monthly / Custom: Sum weeks in range
            proporsi = get_weekly_progress_for_monthly_view(
                pekerjaan.id,
                tahap.tanggal_mulai,
                tahap.tanggal_selesai,
                project.tanggal_mulai
            )

        if proporsi > Decimal('0.00'):
            assignments.append({
                'tahapan_id': tahap.id,
                'tahapan_nama': tahap.nama,
                'proporsi': float(proporsi),
                'urutan': tahap.urutan
            })
            total_proporsi += proporsi

    return JsonResponse({
        'ok': True,
        'pekerjaan_id': pekerjaan.id,
        'mode': mode,
        'assignments': assignments,
        'total_proporsi': float(total_proporsi)
    })


@login_required
@require_POST
@transaction.atomic
def api_regenerate_tahapan_v2(request, project_id):
    """
    Regenerate tahapan structure and sync from weekly canonical storage.

    This NEW version does NOT convert assignments - it preserves weekly canonical data
    and only regenerates the tahapan structure, then syncs assignments from canonical.

    POST Body:
        {
            "mode": "daily" | "weekly" | "monthly" | "custom",
            "week_end_day": 0-6 (optional, default 0=Sunday)
        }

    Process:
        1. Delete old auto-generated tahapan (preserves custom tahapan)
        2. Generate new tahapan based on mode
        3. Sync assignments from PekerjaanProgressWeekly canonical storage
        4. NO DATA LOSS - weekly canonical storage is never touched

    Returns:
        {
            "ok": true,
            "mode": "weekly",
            "tahapan_deleted": 10,
            "tahapan_created": 11,
            "assignments_synced": 50
        }
    """
    from detail_project.views_api_tahapan import (
        _generate_daily_tahapan,
        _generate_weekly_tahapan,
        _generate_monthly_tahapan
    )

    project = _owner_or_404(project_id, request.user)

    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'custom')

        # Week boundary configuration (Python weekday: 0=Monday, 6=Sunday)
        week_start_day = data.get('week_start_day', 0)  # Default: 0 = Monday (Senin)
        week_end_day = data.get('week_end_day', 6)     # Default: 6 = Sunday (Minggu)

        # Validate mode
        if mode not in ['daily', 'weekly', 'monthly', 'custom']:
            return JsonResponse({
                'ok': False,
                'error': 'Invalid mode. Must be: daily, weekly, monthly, or custom'
            }, status=400)

        # Validate project timeline
        if not project.tanggal_mulai or not project.tanggal_selesai:
            return JsonResponse({
                'ok': False,
                'error': 'Project timeline not set. Please set tanggal_mulai and tanggal_selesai first.'
            }, status=400)

        # For custom mode, keep existing tahapan
        if mode == 'custom':
            existing_tahapan = TahapPelaksanaan.objects.filter(
                project=project
            ).order_by('urutan')

            # Sync assignments from canonical storage
            synced_count = sync_weekly_to_tahapan(project.id, mode, week_end_day)

            return JsonResponse({
                'ok': True,
                'mode': 'custom',
                'message': 'Custom mode - using existing tahapan',
                'tahapan_count': existing_tahapan.count(),
                'assignments_synced': synced_count
            })

        # STEP 1: Delete old auto-generated tahapan ONLY
        # (Preserves custom tahapan and PekerjaanProgressWeekly canonical data)
        deleted_count, _ = TahapPelaksanaan.objects.filter(
            project=project,
            is_auto_generated=True
        ).delete()

        # STEP 2: Generate new tahapan structure
        new_tahapan = []

        if mode == 'daily':
            new_tahapan = _generate_daily_tahapan(project)
        elif mode == 'weekly':
            new_tahapan = _generate_weekly_tahapan(project, week_start_day, week_end_day)
        elif mode == 'monthly':
            new_tahapan = _generate_monthly_tahapan(project)

        # Bulk create tahapan
        created_tahapan = TahapPelaksanaan.objects.bulk_create(new_tahapan)

        # STEP 3: Sync assignments from weekly canonical storage
        # This reads PekerjaanProgressWeekly and creates PekerjaanTahapan assignments
        synced_count = sync_weekly_to_tahapan(project.id, mode, week_end_day)

        return JsonResponse({
            'ok': True,
            'mode': mode,
            'message': f'Successfully generated {len(created_tahapan)} tahapan and synced {synced_count} assignments',
            'tahapan_deleted': deleted_count,
            'tahapan_created': len(created_tahapan),
            'assignments_synced': synced_count,
            'tahapan': [
                {
                    'tahapan_id': t.id,
                    'nama': t.nama,
                    'urutan': t.urutan,
                    'tanggal_mulai': t.tanggal_mulai.isoformat() if t.tanggal_mulai else None,
                    'tanggal_selesai': t.tanggal_selesai.isoformat() if t.tanggal_selesai else None,
                    'is_auto_generated': t.is_auto_generated,
                    'generation_mode': t.generation_mode
                }
                for t in created_tahapan
            ]
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@transaction.atomic
def api_reset_progress(request, project_id):
    """
    Reset all pekerjaan progress to 0 by deleting all weekly canonical storage.

    This operation:
    1. Deletes all PekerjaanProgressWeekly records for this project
    2. Deletes all PekerjaanTahapan assignments for this project
    3. Cannot be undone!

    POST Body: {} (empty)

    Returns:
        {
            "ok": true,
            "deleted_count": 30,
            "assignments_deleted": 42,
            "message": "Progress reset successful"
        }
    """
    try:
        from detail_project.models import PekerjaanProgressWeekly, PekerjaanTahapan
        from dashboard.models import Project

        # Get project
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Project not found'}, status=404)

        # Delete all weekly canonical storage for this project
        weekly_deleted, _ = PekerjaanProgressWeekly.objects.filter(project=project).delete()

        # Delete all pekerjaan tahapan assignments for this project
        assignments_deleted, _ = PekerjaanTahapan.objects.filter(tahapan__project=project).delete()

        return JsonResponse({
            'ok': True,
            'deleted_count': weekly_deleted,
            'assignments_deleted': assignments_deleted,
            'message': f'Progress reset successful: {weekly_deleted} weekly records and {assignments_deleted} assignments deleted'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
