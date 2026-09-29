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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta, date

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Q, Max
from django.core.cache import cache
from dashboard.models import Project as DashboardProject

from detail_project.models import (
    TahapPelaksanaan,
    PekerjaanTahapan,
    PekerjaanProgressWeekly,
    Pekerjaan,
    VolumePekerjaan
)
from detail_project.progress_utils import (
    calculate_week_number,
    get_week_date_range,
    sync_weekly_to_tahapan,
)
from detail_project.timeline_utils import (
    ALL_RESOLUTIONS,
    TimelineChangeError,
    analyze_project_timeline_change,
    apply_project_timeline_change,
    build_resolution_preview,
    expected_week_count,
    invalidate_schedule_caches,
    work_period_end,
)
from detail_project.progress_write_service import write_progress

# Import helper from original views
from detail_project.views_api_tahapan import _owner_or_404
from detail_project.api_helpers import atomic_error_response, limit_request_body, rate_limit

import logging
logger = logging.getLogger(__name__)


def _require_schedule_revision(project, data, *, required=False):
    """Reject writes originating from a stale Jadwal page."""
    raw_revision = data.get('schedule_revision')
    if raw_revision is None:
        if not required:
            # Compatibility for deprecated/non-browser callers. The active
            # page always sends the revision, so stale browser writes remain
            # protected while old integrations can migrate without outage.
            return None
        return JsonResponse({
            'ok': False,
            'error': 'schedule_revision wajib dikirim. Muat ulang halaman Jadwal.',
            'code': 'schedule_revision_required',
            'schedule_revision': project.schedule_revision,
        }, status=409)
    try:
        client_revision = int(raw_revision)
    except (TypeError, ValueError):
        return JsonResponse({
            'ok': False,
            'error': 'schedule_revision tidak valid. Muat ulang halaman Jadwal.',
            'code': 'schedule_revision_invalid',
            'schedule_revision': project.schedule_revision,
        }, status=409)
    if client_revision != project.schedule_revision:
        return JsonResponse({
            'ok': False,
            'error': 'Struktur jadwal sudah berubah. Muat ulang halaman sebelum menyimpan.',
            'code': 'schedule_revision_conflict',
            'schedule_revision': project.schedule_revision,
        }, status=409)
    return None


@login_required
@require_POST
@rate_limit(category='sync_frequent')  # Jadwal grid save can be frequent; still guard runaway writes.
@limit_request_body()
@transaction.atomic
def api_assign_pekerjaan_weekly(request, project_id):
    """
    Assign pekerjaan progress in WEEKLY units (canonical storage).

    This is the NEW canonical API for saving progress data.
    All progress should be saved through this endpoint in weekly units.

    POST Body:
        {
            "mode": "planned",  # or "actual" - determines which field to update
            "assignments": [
                {
                    "pekerjaan_id": 322,
                    "week_number": 1,
                    "proportion": 25.50,  # Will update planned_proportion or actual_proportion based on mode
                    "notes": "Optional notes"
                },
                {
                    "pekerjaan_id": 322,
                    "week_number": 2,
                    "proportion": 50.00
                }
            ]
        }

        # Legacy format (backward compatible - assumes planned):
        {
            "assignments": [
                {
                    "pekerjaan_id": 322,
                    "week_number": 1,
                    "proportion": 25.50
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
    project = DashboardProject.objects.select_for_update().get(pk=project.pk)

    if not project.tanggal_mulai or not project.tanggal_selesai:
        return JsonResponse({
            'ok': False,
            'error': 'Project harus memiliki tanggal_mulai dan tanggal_selesai sebelum progress disimpan.',
            'code': 'incomplete_timeline',
        }, status=400)

    try:
        data = json.loads(request.body)
        revision_error = _require_schedule_revision(project, data)
        if revision_error:
            return revision_error
        assignments = data.get('assignments', [])

        # Determine which field to update: planned_proportion or actual_proportion
        progress_mode = (data.get('mode') or 'planned').lower()
        if progress_mode not in {'planned', 'actual'}:
            return JsonResponse({
                'ok': False,
                'error': 'mode harus planned atau actual',
                'code': 'invalid_progress_mode',
            }, status=400)

        week_end_day = data.get('week_end_day', 6)
        try:
            week_end_day = int(week_end_day)
        except (TypeError, ValueError):
            week_end_day = 6

        # JDW-02: batas minggu fallback HARUS mengikuti konfigurasi project (SSOT),
        # bukan hardcode Minggu(6). Pakai project.week_end_day; bila null pakai payload.
        effective_week_end_day = project.week_end_day if project.week_end_day is not None else week_end_day
        effective_end = work_period_end(project)
        max_week_number = expected_week_count(
            project.tanggal_mulai,
            effective_end,
            effective_week_end_day,
        )

        if not isinstance(assignments, list):
            return JsonResponse({
                'ok': False,
                'error': 'assignments must be an array'
            }, status=400)

        created_count = 0
        updated_count = 0
        saved_assignments = []
        errors = []

        payload_field = 'actual_proportion' if progress_mode == 'actual' else 'planned_proportion'

        for item in assignments:
            pekerjaan_id = item.get('pekerjaan_id')
            week_number = item.get('week_number')
            # JDW-06: fitur catatan DIHAPUS (keputusan 14-Juni). Abaikan input notes dari
            # client; save baru menulis string kosong (kolom DB di-drop di Fase 3).
            notes = ''

            proportion = item.get(payload_field)
            if proportion is None:
                # Backward compatibility with legacy payload
                proportion = item.get('proportion')

            has_actual_cost = 'actual_cost' in item
            actual_cost_value = item.get('actual_cost')
            clear_actual_cost = has_actual_cost and actual_cost_value is None
            actual_cost_decimal = None

            # Validation
            if not pekerjaan_id:
                errors.append({'error': 'pekerjaan_id required', 'item': item})
                continue

            try:
                week_number = int(week_number)
            except (TypeError, ValueError):
                week_number = 0
            if week_number < 1 or week_number > max_week_number:
                errors.append({
                    'error': f'week_number harus berada pada rentang 1-{max_week_number}',
                    'item': item,
                    'code': 'week_out_of_range',
                })
                continue

            if proportion is None:
                errors.append({'error': f'{payload_field} required', 'item': item})
                continue

            try:
                proportion_decimal = Decimal(str(proportion))
                if proportion_decimal < Decimal('0') or proportion_decimal > Decimal('100'):
                    errors.append({
                        'error': f'Proportion must be 0-100, got {proportion}',
                        'pekerjaan_id': pekerjaan_id
                    })
                    continue
            except (InvalidOperation, ValueError):
                errors.append({
                    'error': f'Invalid proportion: {proportion}',
                    'pekerjaan_id': pekerjaan_id
                })
                continue

            if clear_actual_cost and progress_mode != 'actual':
                errors.append({
                    'error': 'actual_cost hanya dapat dikosongkan pada mode actual',
                    'pekerjaan_id': pekerjaan_id,
                })
                continue
            if actual_cost_value is not None:
                try:
                    actual_cost_decimal = Decimal(str(actual_cost_value))
                    if actual_cost_decimal < Decimal('0'):
                        errors.append({
                            'error': f'Actual cost must be >= 0, got {actual_cost_value}',
                            'pekerjaan_id': pekerjaan_id
                        })
                        actual_cost_decimal = None
                except (InvalidOperation, ValueError):
                    errors.append({
                        'error': f'Invalid actual_cost: {actual_cost_value}',
                        'pekerjaan_id': pekerjaan_id
                    })
                    actual_cost_decimal = None

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
                        week_end_day=effective_week_end_day  # JDW-02: konfigurasi project
                    )
                    week_end = min(week_end, work_period_end(project))
            except Exception:
                # Fallback: calculate from project start
                week_start, week_end = get_week_date_range(
                    week_number,
                    project.tanggal_mulai,
                    week_end_day=effective_week_end_day  # JDW-02: konfigurasi project
                )
                week_end = min(week_end, work_period_end(project))

            saved = write_progress(
                project,
                [{
                    'pekerjaan_id': pekerjaan.id,
                    'week_number': week_number,
                    'week_start_date': week_start,
                    'week_end_date': week_end,
                    'planned_proportion': proportion_decimal if progress_mode == 'planned' else Decimal('0'),
                    'actual_proportion': proportion_decimal if progress_mode == 'actual' else Decimal('0'),
                    'actual_cost': actual_cost_decimal,
                    'has_actual_cost': has_actual_cost if progress_mode == 'actual' else False,
                    'clear_actual_cost': clear_actual_cost if progress_mode == 'actual' else False,
                    'notes': notes,
                }],
                kind='planned_new' if progress_mode == 'planned' else 'actual',
            )[0]
            wp = saved['record']
            created = saved['created']

            if created:
                created_count += 1
            else:
                updated_count += 1

            # Phase 2E.1: Return mode-specific proportion in response
            response_item = {
                'pekerjaan_id': pekerjaan_id,
                'week_number': week_number,
                'week_start_date': week_start.isoformat(),
                'week_end_date': week_end.isoformat(),
                'proportion': float(proportion_decimal),  # Generic field for frontend compatibility
                'notes': notes,
                'actual_cost': float(wp.actual_cost) if wp.actual_cost is not None else None,
            }
            # Also include mode-specific field for clarity
            if progress_mode == 'actual':
                response_item['actual_proportion'] = float(proportion_decimal)
            else:
                response_item['planned_proportion'] = float(proportion_decimal)

            saved_assignments.append(response_item)

        # STEP 2: Validate total progress per pekerjaan ≤ 100%
        # Group new assignments by pekerjaan_id
        from collections import defaultdict
        pekerjaan_totals = defaultdict(Decimal)

        for item in assignments:
            pekerjaan_id = item.get('pekerjaan_id')
            proportion = item.get(payload_field)
            if proportion is None:
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

        touched_pekerjaan_ids = {item.get('pekerjaan_id') for item in assignments if item.get('pekerjaan_id')}
        if touched_pekerjaan_ids:
            # Phase 2E.1: Sum the appropriate proportion field based on mode
            proportion_field = 'actual_proportion' if progress_mode == 'actual' else 'planned_proportion'
            weekly_totals = (
                PekerjaanProgressWeekly.objects.filter(pekerjaan_id__in=touched_pekerjaan_ids)
                .values('pekerjaan_id')
                .annotate(total=Sum(proportion_field))
            )
            volume_map = {
                vp.pekerjaan_id: vp.quantity
                for vp in VolumePekerjaan.objects.filter(pekerjaan_id__in=touched_pekerjaan_ids)
            }
            percent_tolerance = Decimal('0.01')
            base_volume_tolerance = Decimal('0.001')

            for entry in weekly_totals:
                pekerjaan_id = entry['pekerjaan_id']
                total_percent = entry['total'] or Decimal('0')
                if total_percent > Decimal('100.00') + percent_tolerance:
                    validation_errors.append({
                        'error': f'Total progress {float(total_percent):.2f}% exceeds 100% (existing + baru)',
                        'pekerjaan_id': pekerjaan_id,
                        'total': float(total_percent),
                        'max_allowed': 100.0,
                        'type': 'percent_total'
                    })
                    continue

                raw_capacity = volume_map.get(pekerjaan_id)
                capacity = Decimal(str(raw_capacity)) if raw_capacity is not None else Decimal('0')
                if capacity <= 0 and total_percent > percent_tolerance:
                    validation_errors.append({
                        'error': 'Volume master belum diisi tetapi progres > 0%',
                        'pekerjaan_id': pekerjaan_id,
                        'total': float(total_percent),
                        'type': 'missing_capacity'
                    })
                    continue

                if capacity > 0:
                    total_volume = (capacity * total_percent) / Decimal('100')
                    volume_tolerance = max(capacity * Decimal('0.001'), base_volume_tolerance)
                    if total_volume > capacity + volume_tolerance:
                        validation_errors.append({
                            'error': f'Total volume {float(total_volume):.3f} melampaui kapasitas {float(capacity):.3f}',
                            'pekerjaan_id': pekerjaan_id,
                            'total': float(total_volume),
                            'capacity': float(capacity),
                            'type': 'volume'
                        })

        if validation_errors:
            transaction.set_rollback(True)
            return JsonResponse({
                'ok': False,
                'error': 'Validation failed: Total progress exceeds 100%',
                'validation_errors': validation_errors
            }, status=400)

        # WP-B3 / JDW-01: atomic all-or-nothing — roll back, no partial save, no 207.
        if errors:
            return atomic_error_response(
                errors=errors,
                status=400,
                message='Sebagian perubahan tidak valid. Tidak ada perubahan yang disimpan.',
            )

        # Success: keep PekerjaanTahapan (view layer) in sync so legacy reads stay accurate.
        # Note: mode here refers to time scale mode ('weekly'), not progress mode ('planned'/'actual')
        try:
            synced_count = sync_weekly_to_tahapan(project.id, mode='weekly', week_end_day=effective_week_end_day)
        except Exception:
            # WP-B3 / JDW-03: sync is part of the save contract. On failure roll
            # back the weekly writes too (no canonical/projection drift) and do
            # not leak the exception detail (A-3).
            logger.exception(
                "assign_weekly: sync_weekly_to_tahapan failed",
                extra={'project_id': project.id},
            )
            return atomic_error_response(
                status=500,
                message='Gagal menyimpan jadwal. Tidak ada perubahan yang disimpan.',
            )

        # Invalidate all schedule-related caches through one helper so future
        # cache families cannot be forgotten by a write endpoint.
        affected_pekerjaan_ids = {item.get('pekerjaan_id') for item in assignments if item.get('pekerjaan_id')}
        invalidate_schedule_caches(project.id, affected_pekerjaan_ids)

        # Progress writes also invalidate an already-open browser. The next
        # save must carry this new revision, preventing last-write-wins across
        # tabs while keeping the canonical batch atomic.
        project.schedule_revision = (project.schedule_revision or 1) + 1
        project.save(update_fields=['schedule_revision', 'updated_at'])

        return JsonResponse({
            'ok': True,
            'message': f'{created_count} created, {updated_count} updated',
            'created_count': created_count,
            'updated_count': updated_count,
            'assignments': saved_assignments,
            'saved_assignments': saved_assignments,
            'synced_assignments': synced_count,
            'synced_mode': 'weekly',  # Time scale mode used for sync
            'progress_mode': progress_mode,  # Progress mode (planned/actual) used for save
            'schedule_revision': project.schedule_revision,
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Http404:
        return JsonResponse({'ok': False, 'error': 'Project not found'}, status=404)

    except Exception:
        # WP-P7 Batch A hardening: do not leak internal exception text to the client.
        logger.exception("[ASSIGN_WEEKLY] gagal menyimpan progress mingguan project %s", project_id)
        return JsonResponse({'ok': False, 'error': 'Gagal menyimpan progress mingguan. Silakan coba lagi.'}, status=500)


@login_required
@require_POST
@rate_limit(category='write')
@limit_request_body()
@transaction.atomic
def api_update_week_boundaries(request, project_id):
    """
    Persist user preference for week start/end day per project.
    Accepts Python weekday numbers (0=Monday .. 6=Sunday). Week end day will be
    normalized untuk memastikan selisih 6 hari dari week start.
    """
    project = _owner_or_404(project_id, request.user)
    project = DashboardProject.objects.select_for_update().get(pk=project.pk)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    revision_error = _require_schedule_revision(project, data)
    if revision_error:
        return revision_error

    def _normalize(value, fallback):
        try:
            return int(value) % 7
        except (TypeError, ValueError):
            return fallback % 7

    current_start = project.week_start_day if project.week_start_day is not None else 0
    week_start_day = _normalize(data.get('week_start_day', current_start), current_start)

    provided_end = data.get('week_end_day')
    if provided_end is None:
        week_end_day = (week_start_day + 6) % 7
    else:
        normalized_end = _normalize(provided_end, (week_start_day + 6) % 7)
        if (normalized_end - week_start_day) % 7 != 6:
            normalized_end = (week_start_day + 6) % 7
        week_end_day = normalized_end

    project.week_start_day = week_start_day
    project.week_end_day = week_end_day
    project.save(update_fields=['week_start_day', 'week_end_day', 'updated_at'])
    invalidate_schedule_caches(project.id)

    return JsonResponse({
        'ok': True,
        'week_start_day': week_start_day,
        'week_end_day': week_end_day,
        'schedule_revision': project.schedule_revision,
    })


def _parse_timeline_date(value):
    if value in (None, ''):
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _serialize_resolution_preview(preview):
    """JSON-kan proyeksi resolusi: tanggal jadi ISO, Decimal jadi string.

    String desimal kanonik, bukan float — konsisten dengan kebijakan presisi
    export (doc 30) supaya angka yang dilihat user tidak bergeser di klien.
    """
    return {
        'resolution': preview['resolution'],
        'label': preview['label'],
        'help': preview['help'],
        'old_week_count': preview['old_week_count'],
        'new_week_count': preview['new_week_count'],
        'total_planned_before': str(preview['total_planned_before']),
        'total_planned_after': str(preview['total_planned_after']),
        'planned_lost': str(preview['planned_lost']),
        'weeks': [
            {
                'week_number': week['week_number'],
                'old_start': week['old_start'].isoformat() if week['old_start'] else None,
                'old_end': week['old_end'].isoformat() if week['old_end'] else None,
                'new_start': week['new_start'].isoformat() if week['new_start'] else None,
                'new_end': week['new_end'].isoformat() if week['new_end'] else None,
                'exists_after': week['exists_after'],
                'planned_before': str(week['planned_before']),
                'planned_after': str(week['planned_after']),
                'changed': week['changed'],
            }
            for week in preview['weeks']
        ],
    }


@login_required
@require_POST
@rate_limit(category='write')
@limit_request_body()
def api_preview_project_timeline(request, project_id):
    """Return timeline impact without changing project or progress data."""
    project = _owner_or_404(project_id, request.user)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    revision_error = _require_schedule_revision(project, data, required=True)
    if revision_error:
        return revision_error
    new_start = _parse_timeline_date(data.get('tanggal_mulai'))
    target_field = data.get('target_field') or 'tanggal_selesai'
    if target_field not in {'tanggal_selesai', 'tanggal_akhir_tambahan'}:
        return JsonResponse({'ok': False, 'error': 'target_field tidak valid'}, status=400)
    if target_field == 'tanggal_akhir_tambahan':
        if data.get('hapus_tambahan'):
            new_end = None
        else:
            raw_end = data.get('tanggal_akhir_tambahan')
            new_end = _parse_timeline_date(raw_end)
            if raw_end and new_end is None:
                return JsonResponse({'ok': False, 'error': 'tanggal_akhir_tambahan tidak valid'}, status=400)
            if not raw_end:
                return JsonResponse({'ok': False, 'error': 'tanggal_akhir_tambahan wajib diisi'}, status=400)
    else:
        new_end = _parse_timeline_date(data.get('tanggal_selesai'))
    try:
        impact = analyze_project_timeline_change(
            project, new_start, new_end, target_field=target_field
        )
    except TimelineChangeError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
            'impact': exc.impact,
        }, status=400)
    # Proyeksi tiap opsi yang sah, dari planner yang sama dengan yang nanti
    # melakukan commit — sehingga dialog di halaman Jadwal menampilkan angka
    # yang identik dengan dialog di form edit project.
    previews = [
        _serialize_resolution_preview(
            build_resolution_preview(
                project, new_start, new_end, option, target_field=target_field
            )
        )
        for option in impact.get('allowed_resolutions', [])
    ]

    return JsonResponse({
        'ok': True,
        'impact': impact,
        'previews': previews,
        'schedule_revision': project.schedule_revision,
    })


@login_required
@require_POST
@rate_limit(category='write')
@limit_request_body()
def api_commit_project_timeline(request, project_id):
    """Commit a timeline change after recomputing its impact server-side."""
    project = _owner_or_404(project_id, request.user)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    revision_error = _require_schedule_revision(project, data, required=True)
    if revision_error:
        return revision_error
    new_start = _parse_timeline_date(data.get('tanggal_mulai'))
    target_field = data.get('target_field') or 'tanggal_selesai'
    if target_field not in {'tanggal_selesai', 'tanggal_akhir_tambahan'}:
        return JsonResponse({'ok': False, 'error': 'target_field tidak valid'}, status=400)
    if target_field == 'tanggal_akhir_tambahan':
        if data.get('hapus_tambahan'):
            new_end = None
        else:
            raw_end = data.get('tanggal_akhir_tambahan')
            new_end = _parse_timeline_date(raw_end)
            if raw_end and new_end is None:
                return JsonResponse({'ok': False, 'error': 'tanggal_akhir_tambahan tidak valid'}, status=400)
            if not raw_end:
                return JsonResponse({'ok': False, 'error': 'tanggal_akhir_tambahan wajib diisi'}, status=400)
    else:
        new_end = _parse_timeline_date(data.get('tanggal_selesai'))
    resolution = data.get('resolution') or 'none'
    if resolution not in ALL_RESOLUTIONS:
        return JsonResponse({'ok': False, 'error': 'resolution tidak valid'}, status=400)

    try:
        result = apply_project_timeline_change(
            project,
            new_start,
            new_end,
            resolution=resolution,
            user=request.user,
            expected_revision=int(data.get('schedule_revision')),
            target_field=target_field,
        )
    except TimelineChangeError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
            'impact': exc.impact,
        }, status=400)
    return JsonResponse({'ok': True, **result})


@login_required
@require_GET
def api_get_pekerjaan_weekly_progress(request, project_id, pekerjaan_id):
    """
    Get weekly progress for a pekerjaan (canonical storage).

    Returns the raw weekly progress data without conversion.
    
    OPTIMIZED: Redis caching with signature validation (5 min TTL).

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

    # Helper for timestamp formatting
    def _fmt_ts(val):
        return val.isoformat() if val else "0"

    # Cache key
    cache_key = f"v2_weekly_progress:{project.id}:{pekerjaan.id}:v1"
    cached = cache.get(cache_key)
    
    # Check cache with signature validation
    if cached:
        current_signature = (
            project.schedule_revision,
            _fmt_ts(PekerjaanProgressWeekly.objects.filter(pekerjaan=pekerjaan)
                .aggregate(last=Max('updated_at'))['last']),
            _fmt_ts(pekerjaan.updated_at)
        )
        if cached.get("sig") == current_signature:
            return JsonResponse(cached.get("data"))

    # Cache miss or stale - fetch fresh data
    weekly_progress = PekerjaanProgressWeekly.objects.filter(
        pekerjaan=pekerjaan
    ).order_by('week_number')

    # Phase 2E.1: Calculate totals for both planned and actual
    total_planned = weekly_progress.aggregate(
        total=Sum('planned_proportion')
    )['total'] or Decimal('0.00')

    total_actual = weekly_progress.aggregate(
        total=Sum('actual_proportion')
    )['total'] or Decimal('0.00')

    response_data = {
        'ok': True,
        'schedule_revision': project.schedule_revision,
        'pekerjaan_id': pekerjaan.id,
        'weekly_progress': [
            {
                'week_number': wp.week_number,
                'week_start_date': wp.week_start_date.isoformat(),
                'week_end_date': wp.week_end_date.isoformat(),
                'planned_proportion': float(wp.planned_proportion),
                'actual_proportion': float(wp.actual_proportion),
                'notes': wp.notes,
                'created_at': wp.created_at.isoformat(),
                'updated_at': wp.updated_at.isoformat()
            }
            for wp in weekly_progress
        ],
        'total_planned_proportion': float(total_planned),
        'total_actual_proportion': float(total_actual),
        # Phase 2E.1: Check completion based on planned proportion
        'is_complete': abs(float(total_planned) - 100.0) < 0.01
    }
    
    # Update cache with new signature
    new_signature = (
        project.schedule_revision,
        _fmt_ts(PekerjaanProgressWeekly.objects.filter(pekerjaan=pekerjaan)
            .aggregate(last=Max('updated_at'))['last']),
        _fmt_ts(pekerjaan.updated_at)
    )
    cache.set(cache_key, {"sig": new_signature, "data": response_data}, 300)  # 5 min TTL

    return JsonResponse(response_data)


@login_required
@require_GET
def api_get_pekerjaan_assignments_v2(request, project_id, pekerjaan_id):
    """
    Get pekerjaan assignments in current time scale mode (daily/weekly/monthly).

    This endpoint converts weekly canonical storage to the requested view mode.
    
    OPTIMIZED: Redis caching with mode-specific keys (5 min TTL).

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

    # Helper for timestamp formatting
    def _fmt_ts(val):
        return val.isoformat() if val else "0"

    # Cache key (mode-specific)
    cache_key = f"v2_pekerjaan_assignments:{project.id}:{pekerjaan.id}:{mode}:v1"
    cached = cache.get(cache_key)
    
    # Check cache with signature validation
    if cached:
        current_signature = (
            mode,
            project.schedule_revision,
            _fmt_ts(PekerjaanProgressWeekly.objects.filter(pekerjaan=pekerjaan)
                .aggregate(last=Max('updated_at'))['last']),
            _fmt_ts(pekerjaan.updated_at),
            project.week_start_day,
            project.week_end_day
        )
        if cached.get("sig") == current_signature:
            return JsonResponse(cached.get("data"))

    # Cache miss or stale - compute fresh data

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
    weekly_by_num = {wp.week_number: wp for wp in weekly_progress}
    project_start = project.tanggal_mulai or date.today()
    week_end_day = getattr(project, "week_end_day", 6)

    # Convert to assignments based on mode
    assignments = []
    total_proporsi = Decimal('0.00')

    for tahap in tahapan_list:
        if not tahap.tanggal_mulai or not tahap.tanggal_selesai:
            continue

        if mode == 'daily':
            # Daily: derive from weekly canonical data without extra queries
            week_num = calculate_week_number(tahap.tanggal_mulai, project_start, week_end_day)
            weekly_record = weekly_by_num.get(week_num)
            if weekly_record and weekly_record.week_start_date and weekly_record.week_end_date:
                days_in_week = (weekly_record.week_end_date - weekly_record.week_start_date).days + 1
                weekly_value = weekly_record.planned_proportion
                proporsi = (weekly_value / Decimal(days_in_week)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                proporsi = Decimal('0.00')
        elif mode == 'weekly':
            # Weekly: Direct from canonical
            urutan_index = tahap.urutan if tahap.urutan is not None else 0
            week_num = urutan_index + 1
            weekly_record = weekly_by_num.get(week_num)
            # Phase 2E.1: Default to planned_proportion (TODO: support mode parameter)
            proporsi = weekly_record.planned_proportion if weekly_record else Decimal('0.00')
        else:
            # Monthly / Custom: Sum weeks in range
            month_start = tahap.tanggal_mulai
            month_end = tahap.tanggal_selesai
            total_prop = Decimal('0.00')
            for weekly_record in weekly_progress:
                if not weekly_record.week_start_date or not weekly_record.week_end_date:
                    continue
                if weekly_record.week_start_date <= month_end and weekly_record.week_end_date >= month_start:
                    overlap_start = max(weekly_record.week_start_date, month_start)
                    overlap_end = min(weekly_record.week_end_date, month_end)
                    overlap_days = (overlap_end - overlap_start).days + 1
                    week_days = (weekly_record.week_end_date - weekly_record.week_start_date).days + 1
                    total_prop += (weekly_record.planned_proportion * Decimal(overlap_days)) / Decimal(week_days)
            proporsi = total_prop.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if proporsi > Decimal('0.00'):
            assignments.append({
                'tahapan_id': tahap.id,
                'tahapan_nama': tahap.nama,
                'proporsi': float(proporsi),
                'urutan': tahap.urutan
            })
            total_proporsi += proporsi

    response_data = {
        'ok': True,
        'schedule_revision': project.schedule_revision,
        'pekerjaan_id': pekerjaan.id,
        'mode': mode,
        'assignments': assignments,
        'total_proporsi': float(total_proporsi)
    }
    
    # Update cache with new signature
    new_signature = (
        mode,
        project.schedule_revision,
        _fmt_ts(PekerjaanProgressWeekly.objects.filter(pekerjaan=pekerjaan)
            .aggregate(last=Max('updated_at'))['last']),
        _fmt_ts(pekerjaan.updated_at),
        project.week_start_day,
        project.week_end_day
    )
    cache.set(cache_key, {"sig": new_signature, "data": response_data}, 300)  # 5 min TTL

    return JsonResponse(response_data)


@login_required
@require_GET
def api_get_project_assignments_v2(request, project_id):
    """
    Get weekly canonical assignments for all pekerjaan in a single payload.

    Returns:
        {
            "ok": true,
            "count": 120,
            "assignments": [
                {
                    "pekerjaan_id": 1101,
                    "week_number": 1,
                    "planned_proportion": 25.5,      # NEW: Planned progress
                    "actual_proportion": 20.0,        # NEW: Actual progress
                    "proportion": 25.5,               # Legacy field (=planned for compatibility)
                    "week_start_date": "2026-01-01",
                    "week_end_date": "2026-01-07",
                    "updated_at": "2026-01-08T12:00:00Z",
                    "notes": ""
                },
                ...
            ]
        }
    """
    project = _owner_or_404(project_id, request.user)

    def _fmt_ts(val):
        return val.isoformat() if val else "0"

    cache_key = f"v2_assignments:{project.id}:v1"
    cached = cache.get(cache_key)
    signature = None
    if cached:
        signature = (
            project.schedule_revision,
            _fmt_ts(PekerjaanProgressWeekly.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
            _fmt_ts(Pekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
        )
        if cached.get("sig") == signature:
            return JsonResponse(cached.get("data", {"ok": True, "count": 0, "assignments": []}))

    weekly_rows = (
        PekerjaanProgressWeekly.objects
        .filter(project=project)
        .order_by('pekerjaan_id', 'week_number')
        .values(
            'pekerjaan_id',
            'week_number',
            'planned_proportion',
            'actual_proportion',
            'actual_cost',
            'week_start_date',
            'week_end_date',
            'updated_at',
            'notes',
            'pekerjaan__budgeted_cost',
        )
    )

    assignments = []
    for row in weekly_rows:
        planned = row.get('planned_proportion') or 0
        actual = row.get('actual_proportion') or 0
        assignments.append({
            'pekerjaan_id': row.get('pekerjaan_id'),
            'week_number': row.get('week_number'),
            # Phase 2E.1: Dual mode fields
            'planned_proportion': float(planned),
            'actual_proportion': float(actual),
            'proportion': float(planned),  # Legacy field for compatibility
            'actual_cost': float(row.get('actual_cost') or 0),
            'budgeted_cost': float(row.get('pekerjaan__budgeted_cost') or 0),
            'week_start_date': row.get('week_start_date').isoformat() if row.get('week_start_date') else None,
            'week_end_date': row.get('week_end_date').isoformat() if row.get('week_end_date') else None,
            'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
            # JDW-07: `actual_updated_at` (timestamp realisasi) dihapus dari API — fitur
            # timestamp tidak diperlukan (keputusan 14-Juni) & field tak pernah ditulis.
            'notes': row.get('notes'),
        })

    response_data = {
        'ok': True,
        'schedule_revision': project.schedule_revision,
        'count': len(assignments),
        'assignments': assignments,
    }

    new_bucket = cached or {}
    if signature is None:
        signature = (
            project.schedule_revision,
            _fmt_ts(PekerjaanProgressWeekly.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
            _fmt_ts(Pekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
        )
    new_bucket["sig"] = signature
    new_bucket["data"] = response_data
    cache.set(cache_key, new_bucket, 300)

    return JsonResponse(response_data)


@login_required
@require_POST
@rate_limit(category='write')
@limit_request_body()
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
    project = DashboardProject.objects.select_for_update().get(pk=project.pk)

    try:
        data = json.loads(request.body)
        revision_error = _require_schedule_revision(project, data)
        if revision_error:
            return revision_error
        mode = data.get('mode', 'custom')

        # Week boundary configuration (Python weekday: 0=Monday, 6=Sunday)
        week_end_day_raw = data.get('week_end_day', 6)
        week_start_day_raw = data.get('week_start_day')

        try:
            week_end_day = int(week_end_day_raw)
        except (TypeError, ValueError):
            week_end_day = 6

        week_end_day %= 7

        if week_start_day_raw is None:
            week_start_day = (week_end_day + 1) % 7
        else:
            try:
                week_start_day = int(week_start_day_raw) % 7
            except (TypeError, ValueError):
                week_start_day = (week_end_day + 1) % 7

        # Validate mode
        if mode not in ['daily', 'weekly', 'monthly', 'custom']:
            return JsonResponse({
                'ok': False,
                'error': 'Invalid mode. Must be: daily, weekly, monthly, or custom'
            }, status=400)

        # Validate before mutating week boundary settings. Returning a 400 from
        # inside transaction.atomic does not roll back ordinary model saves.
        if not project.tanggal_mulai or not project.tanggal_selesai:
            return JsonResponse({
                'ok': False,
                'error': 'Project timeline belum lengkap. Isi tanggal_mulai dan tanggal_selesai terlebih dahulu.',
                'code': 'incomplete_timeline',
            }, status=400)

        # WP-P7b (audit-gap): catat perubahan konfigurasi batas minggu (memengaruhi
        # interpretasi seluruh minggu) — project-level, hanya bila benar berubah.
        _old_wsd, _old_wed = project.week_start_day, project.week_end_day
        project.week_start_day = week_start_day
        project.week_end_day = week_end_day
        boundary_changed = (_old_wsd, _old_wed) != (week_start_day, week_end_day)
        if boundary_changed:
            # Project.save() increments the revision exactly once for a
            # structural field change.
            project.save(update_fields=['week_start_day', 'week_end_day', 'updated_at'])
        else:
            # Regeneration itself is still a structural write even when the
            # selected boundaries are unchanged.
            project.schedule_revision = (project.schedule_revision or 1) + 1
            project.save(update_fields=['schedule_revision', 'updated_at'])
        if boundary_changed:
            try:
                from detail_project.models import DetailAHSPAudit
                DetailAHSPAudit.objects.create(
                    project=project, pekerjaan=None, action=DetailAHSPAudit.ACTION_UPDATE,
                    old_data={"week_start_day": _old_wsd, "week_end_day": _old_wed},
                    new_data={"week_start_day": week_start_day, "week_end_day": week_end_day},
                    triggered_by="user",
                    user=request.user if getattr(request.user, "id", None) else None,
                    change_summary=f"Regenerate struktur waktu (mode={mode}); batas minggu "
                                   f"{_old_wsd}/{_old_wed} → {week_start_day}/{week_end_day}",
                )
            except Exception:
                logger.exception("[PROGRESS_AUDIT] gagal mencatat regenerate project %s", project.id)

        # For custom mode, keep existing tahapan
        if mode == 'custom':
            existing_tahapan = TahapPelaksanaan.objects.filter(
                project=project
            ).order_by('urutan')

            # Sync assignments from canonical storage
            synced_count = sync_weekly_to_tahapan(project.id, mode, week_end_day)
            invalidate_schedule_caches(project.id)

            return JsonResponse({
                'ok': True,
                'mode': 'custom',
                'message': 'Custom mode - using existing tahapan',
                'tahapan_count': existing_tahapan.count(),
                'assignments_synced': synced_count,
                'schedule_revision': project.schedule_revision,
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
        invalidate_schedule_caches(project.id)

        return JsonResponse({
            'ok': True,
            'mode': mode,
            'message': f'Successfully generated {len(created_tahapan)} tahapan and synced {synced_count} assignments',
            'tahapan_deleted': deleted_count,
            'tahapan_created': len(created_tahapan),
            'assignments_synced': synced_count,
            'schedule_revision': project.schedule_revision,
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
    except Exception:
        # WP-P7 Batch A hardening: do not leak internal exception text to the client.
        logger.exception("[REGENERATE_TAHAPAN] gagal regenerate project %s", project_id)
        return JsonResponse({'ok': False, 'error': 'Gagal memperbarui struktur waktu. Silakan coba lagi.'}, status=500)


@login_required
@require_POST
@rate_limit(category='write')
@limit_request_body()
@transaction.atomic
def api_reset_progress(request, project_id):
    """
    Reset pekerjaan progress to 0 for a specific mode (planned or actual).

    Phase 2E.1: Now supports mode-specific reset to preserve independence.

    This operation:
    1. Sets planned_proportion OR actual_proportion to 0 (based on mode)
    2. Keeps the other field intact
    3. Can be undone by re-entering data

    POST Body:
        {
            "mode": "planned"  // or "actual" - determines which field to reset
        }

    Returns:
        {
            "ok": true,
            "updated_count": 30,
            "mode": "planned",
            "message": "Planned progress reset to 0"
        }
    """
    try:
        from detail_project.models import PekerjaanProgressWeekly
        import json

        # Ownership check (same policy as other V2 endpoints)
        project = _owner_or_404(project_id, request.user)
        project = DashboardProject.objects.select_for_update().get(pk=project.pk)

        # Parse request body for mode
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

        progress_mode = (data.get('mode') or '').lower()
        if progress_mode not in {'planned', 'actual'}:
            return JsonResponse({
                'ok': False,
                'error': 'mode wajib planned atau actual',
                'code': 'invalid_progress_mode',
            }, status=400)

        # Reset only the relevant field
        records = PekerjaanProgressWeekly.objects.filter(project=project)
        updated_count = 0

        for record in records:
            if progress_mode == 'actual':
                # WP-B10 (JDW-05): clearing actual realization must also clear the
                # actual cost projection — actual_cost is an actual-side field, so
                # leaving it behind orphans a cost with no realization. Planned
                # fields (planned_proportion / planned cost basis) are untouched.
                record.actual_proportion = Decimal('0')
                record.actual_cost = None
                record.save(update_fields=['actual_proportion', 'actual_cost', 'updated_at'])
            else:  # planned
                record.planned_proportion = Decimal('0')
                record.save(update_fields=['planned_proportion', 'updated_at'])

            updated_count += 1

        # PekerjaanTahapan is a derived projection. Keep it consistent with
        # the canonical weekly rows before returning success.
        synced_count = sync_weekly_to_tahapan(
            project.id,
            mode='weekly',
            week_end_day=project.week_end_day if project.week_end_day is not None else 6,
        )
        invalidate_schedule_caches(project.id)
        project.schedule_revision = (project.schedule_revision or 1) + 1
        project.save(update_fields=['schedule_revision', 'updated_at'])

        mode_label = 'Planned' if progress_mode == 'planned' else 'Actual'

        # WP-P7b (audit-gap): catat reset progress berskala project (timestamp + ringkas),
        # konsisten pola project-level RR-10 (DetailAHSPAudit pekerjaan=None). Hanya saat
        # ada record yang berubah; fail-safe (audit tak boleh menggagalkan reset).
        if updated_count:
            try:
                from detail_project.models import DetailAHSPAudit
                DetailAHSPAudit.objects.create(
                    project=project,
                    pekerjaan=None,
                    action=DetailAHSPAudit.ACTION_UPDATE,
                    old_data=None,
                    new_data={"reset_mode": progress_mode, "records": updated_count},
                    triggered_by="user",
                    user=request.user if getattr(request.user, "id", None) else None,
                    change_summary=f"Reset progress {mode_label} → 0 ({updated_count} pekerjaan)",
                )
            except Exception:
                logger.exception("[PROGRESS_AUDIT] gagal mencatat reset progress project %s", project.id)

        return JsonResponse({
            'ok': True,
            'updated_count': updated_count,
            'synced_count': synced_count,
            'mode': progress_mode,
            'message': f'{mode_label} progress reset to 0 for {updated_count} records'
        })

    except Http404:
        return JsonResponse({'ok': False, 'error': 'Project not found'}, status=404)

    except Exception:
        # JDW (security): jangan bocorkan detail exception ke client.
        logger.exception("[RESET_PROGRESS] gagal reset progress project %s", project_id)
        return JsonResponse({'ok': False, 'error': 'Gagal mereset progress. Silakan coba lagi.'}, status=500)
