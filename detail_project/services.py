# detail_project/services.py
from typing import Dict, List, Optional, Set, Tuple
from django.db import transaction
from django.db.models import (
    Sum,
    F as DJF,
    DecimalField,
    ExpressionWrapper,
    Max,
    Q,
    Exists,
    OuterRef,
    Case,
    When,
    Value,
)
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from collections import defaultdict
from .numeric import to_dp_str, DECIMAL_SPEC
from django.core.cache import cache
import logging
import time
import hashlib
import json
import calendar

logger = logging.getLogger(__name__)

MONTH_NAMES_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

# FASE 0.3: Monitoring Setup
from .monitoring_helpers import (
    log_operation,
    log_bundle_expansion,
    log_cascade_operation,
    log_circular_dependency_check,
)

from .models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    VolumePekerjaan,
    DetailAHSPProject,
    DetailAHSPExpanded,
    DetailAHSPAudit,
    ProjectChangeStatus,
    HargaItemProject,
    ProjectPricing,
    ProjectParameter,
    TahapPelaksanaan,
    PekerjaanTahapan,
)

def invalidate_rekap_cache(project_or_id) -> None:
    """
    Hapus cache rekap untuk 1 project.
    Terima instance Project atau angka project_id.
    """
    try:
        pid = int(getattr(project_or_id, "id", project_or_id))
    except Exception:
        return
    cache.delete(f"rekap:{pid}:v1")
    cache.delete(f"rekap:{pid}:v2")


KEBUTUHAN_CACHE_TIMEOUT = 300  # seconds
KEBUTUHAN_KATEGORI_ORDER = ('TK', 'BHN', 'ALT', 'LAIN')


def _fmt_ts(val):
    return val.isoformat() if val else "0"


def _kebutuhan_signature(project):
    """Build signature tuple untuk cache Rekap Kebutuhan."""
    raw_ts = DetailAHSPProject.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    expanded_ts = DetailAHSPExpanded.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    volume_ts = VolumePekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    pekerjaan_ts = Pekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    tahapan_ts = TahapPelaksanaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    assignment_ts = PekerjaanTahapan.objects.filter(
        Q(tahapan__project=project) | Q(pekerjaan__project=project)
    ).aggregate(last=Max('updated_at'))['last']
    return (
        _fmt_ts(raw_ts),
        _fmt_ts(expanded_ts),
        _fmt_ts(volume_ts),
        _fmt_ts(pekerjaan_ts),
        _fmt_ts(tahapan_ts),
        _fmt_ts(assignment_ts),
    )


def _normalize_int_list(values):
    if not values:
        return tuple()
    cleaned = []
    for val in values:
        if val in (None, ''):
            continue
        try:
            cleaned.append(int(val))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(set(cleaned)))


def _normalize_kebutuhan_filters(filters):
    """Canonicalize filter dict for consistent caching."""
    filters = filters or {}
    kategori_values = filters.get('kategori_items') or []
    normalized_kategori = []
    for item in kategori_values:
        if not item:
            continue
        key = str(item).strip().upper()
        if key in KEBUTUHAN_KATEGORI_ORDER:
            normalized_kategori.append(key)
    return {
        'klasifikasi_ids': _normalize_int_list(filters.get('klasifikasi_ids')),
        'sub_klasifikasi_ids': _normalize_int_list(filters.get('sub_klasifikasi_ids')),
        'kategori_items': tuple(normalized_kategori),
        'pekerjaan_ids': _normalize_int_list(filters.get('pekerjaan_ids')),
    }


def _ensure_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    if hasattr(value, "date"):
        try:
            return value.date()
        except Exception:
            return None
    return None


def get_project_period_options(project):
    tahapan_dates = TahapPelaksanaan.objects.filter(project=project).values('tanggal_mulai', 'tanggal_selesai')
    week_map = {}
    month_map = {}

    for item in tahapan_dates:
        start = _ensure_date(item.get('tanggal_mulai'))
        end = _ensure_date(item.get('tanggal_selesai')) or start
        if not start:
            continue
        if end and end < start:
            start, end = end, start
        if not end:
            end = start

        # Weeks (ISO)
        cursor = start - timedelta(days=start.weekday())
        while cursor <= end:
            iso_year, iso_week, _ = cursor.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
            if key not in week_map:
                week_end = cursor + timedelta(days=6)
                label = f"Minggu {iso_week} ({cursor.strftime('%d %b')} - {week_end.strftime('%d %b %Y')})"
                week_map[key] = {
                    'value': key,
                    'label': label,
                    'start_date': cursor.isoformat(),
                    'end_date': week_end.isoformat(),
                }
            cursor += timedelta(days=7)

        # Months
        month_cursor = date(start.year, start.month, 1)
        while month_cursor <= end:
            _, last_day = calendar.monthrange(month_cursor.year, month_cursor.month)
            month_end = date(month_cursor.year, month_cursor.month, last_day)
            key = f"{month_cursor.year}-{month_cursor.month:02d}"
            if key not in month_map:
                label = f"{MONTH_NAMES_ID.get(month_cursor.month, 'Bulan')} {month_cursor.year}"
                month_map[key] = {
                    'value': key,
                    'label': label,
                    'start_date': month_cursor.isoformat(),
                    'end_date': month_end.isoformat(),
                }
            month_cursor = month_end + timedelta(days=1)

    weeks = sorted(week_map.values(), key=lambda item: item['start_date'])
    months = sorted(month_map.values(), key=lambda item: item['start_date'])
    return {'weeks': weeks, 'months': months}


def _select_period_buckets(period_options, mode='week', start_value=None, end_value=None):
    source = period_options['weeks'] if mode == 'week' else period_options['months']
    if not source:
        return []
    index_map = {item['value']: idx for idx, item in enumerate(source)}
    if start_value in index_map:
        start_idx = index_map[start_value]
    else:
        start_idx = 0
    if end_value in index_map:
        end_idx = index_map[end_value]
    else:
        end_idx = len(source) - 1
    if end_idx < start_idx:
        start_idx, end_idx = end_idx, start_idx
    return source[start_idx:end_idx + 1]


def _parse_week_code(value: str):
    if not value or "-W" not in value:
        return None
    try:
        year_str, week_str = value.split("-W", 1)
        year = int(year_str)
        week = int(week_str)
        start = date.fromisocalendar(year, week, 1)
        end = date.fromisocalendar(year, week, 7)
        return start, end
    except Exception:
        return None


def _parse_month_code(value: str):
    if not value or "-" not in value:
        return None
    try:
        year_str, month_str = value.split("-", 1)
        year = int(year_str)
        month = int(month_str)
        if month < 1 or month > 12:
            return None
        start_day = date(year, month, 1)
        end_day = date(year, month, calendar.monthrange(year, month)[1])
        return start_day, end_day
    except Exception:
        return None


def _normalize_time_scope(scope):
    default = {
        'mode': 'all',
        'start_value': None,
        'end_value': None,
        'start_date': None,
        'end_date': None,
    }
    scope = scope or {}
    mode_raw = (scope.get('mode') or 'all').strip().lower()
    if mode_raw not in {'week', 'week_range', 'month', 'month_range'}:
        return default
    start_raw = (scope.get('start') or '').strip()
    if not start_raw:
        return default
    parser = _parse_week_code if mode_raw.startswith('week') else _parse_month_code
    start_range = parser(start_raw)
    if not start_range:
        return default
    end_raw = (scope.get('end') or '').strip()
    if mode_raw.endswith('range') and end_raw:
        end_range = parser(end_raw) or start_range
    else:
        end_range = start_range
        end_raw = start_raw
    start_begin, start_finish = start_range
    end_begin, end_finish = end_range
    start_date = min(start_begin, end_begin)
    end_date = max(start_finish, end_finish)
    return {
        'mode': mode_raw,
        'start_value': start_raw,
        'end_value': end_raw,
        'start_date': start_date,
        'end_date': end_date,
    }


def _build_time_scope_multiplier(project, pekerjaan_ids, scope):
    """
    Return map pekerjaan_id -> Decimal fraction (0-1) representing
    how much of pekerjaan volume falls inside requested time scope.
    """
    if not pekerjaan_ids or not scope or scope.get('mode') == 'all':
        return {}
    start_date = _ensure_date(scope.get('start_date'))
    end_date = _ensure_date(scope.get('end_date'))
    if not start_date or not end_date or end_date < start_date:
        return {}

    assignments = (
        PekerjaanTahapan.objects
        .filter(
            pekerjaan_id__in=pekerjaan_ids,
            tahapan__project=project
        )
        .select_related('tahapan')
    )
    totals = {pk: Decimal('0') for pk in pekerjaan_ids}
    selected = {pk: Decimal('0') for pk in pekerjaan_ids}

    for assignment in assignments:
        tahap = assignment.tahapan
        tahap_start = _ensure_date(getattr(tahap, 'tanggal_mulai', None))
        tahap_end = _ensure_date(getattr(tahap, 'tanggal_selesai', None)) or tahap_start
        if not tahap_start or not tahap_end:
            continue
        if tahap_end < tahap_start:
            tahap_start, tahap_end = tahap_end, tahap_start
        duration_days = (tahap_end - tahap_start).days + 1
        if duration_days <= 0:
            continue
        prop_fraction = Decimal(str(assignment.proporsi_volume or 0)) / Decimal('100')
        pekerjaan_id = assignment.pekerjaan_id
        totals[pekerjaan_id] = totals.get(pekerjaan_id, Decimal('0')) + prop_fraction

        overlap_start = max(tahap_start, start_date)
        overlap_end = min(tahap_end, end_date)
        if overlap_start > overlap_end:
            continue
        overlap_days = (overlap_end - overlap_start).days + 1
        overlap_fraction = prop_fraction * Decimal(overlap_days) / Decimal(duration_days)
        selected[pekerjaan_id] = selected.get(pekerjaan_id, Decimal('0')) + overlap_fraction

    result = {}
    for pk in pekerjaan_ids:
        if pk not in totals or totals[pk] == 0:
            result[pk] = Decimal('1.0')
            continue
        ratio = selected.get(pk, Decimal('0'))
        if ratio > Decimal('1.0'):
            ratio = Decimal('1.0')
        result[pk] = ratio
    return result


def _kebutuhan_entry_key(mode, tahapan_id, filters, time_scope=None):
    payload = {
        'mode': mode or 'all',
        'tahapan_id': int(tahapan_id) if tahapan_id is not None else None,
        'klasifikasi_ids': filters['klasifikasi_ids'],
        'sub_klasifikasi_ids': filters['sub_klasifikasi_ids'],
        'kategori_items': filters['kategori_items'],
        'pekerjaan_ids': filters.get('pekerjaan_ids') or (),
    }
    if time_scope and time_scope.get('mode') != 'all':
        payload['time_scope'] = {
            'mode': time_scope.get('mode'),
            'start': time_scope.get('start_value'),
            'end': time_scope.get('end_value'),
        }
    raw = json.dumps(payload, sort_keys=True, default=list)
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def _format_decimal(value: Decimal) -> str:
    if value is None:
        return "0"
    quant = value.normalize()
    text = format(quant, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or "0"


def summarize_kebutuhan_rows(rows, search: str = ""):
    """
    Apply optional search filter and produce counts/totals metadata.

    Returns tuple: (filtered_rows, meta_dict)
    """
    search_term = (search or '').strip().lower()
    if search_term:
        filtered = [
            row for row in rows
            if search_term in (row.get('kode') or '').lower()
            or search_term in (row.get('uraian') or '').lower()
        ]
    else:
        filtered = list(rows)

    counts = {k: 0 for k in KEBUTUHAN_KATEGORI_ORDER}
    qty_totals = {k: Decimal('0') for k in KEBUTUHAN_KATEGORI_ORDER}
    cost_totals = {k: Decimal('0') for k in KEBUTUHAN_KATEGORI_ORDER}

    for row in filtered:
        kategori = row.get('kategori')
        qty = row.get('quantity_decimal')
        cost_val = row.get('harga_total_decimal')
        if kategori in counts:
            counts[kategori] += 1
            try:
                qty_totals[kategori] += Decimal(str(qty or 0))
            except (InvalidOperation, TypeError):
                qty_totals[kategori] += Decimal('0')
            try:
                cost_totals[kategori] += Decimal(str(cost_val or 0))
            except (InvalidOperation, TypeError):
                cost_totals[kategori] += Decimal('0')

    meta = {
        "counts_per_kategori": counts,
        "n_rows": len(filtered),
        "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quantity_totals": {k: _format_decimal(v) for k, v in qty_totals.items()},
        "cost_totals": {k: _format_decimal(v) for k, v in cost_totals.items()},
        "grand_total_cost": _format_decimal(sum(cost_totals.values())),
    }

    return filtered, meta


# Import model referensi untuk cloning (aman bila app referensi belum siap saat makemigrations)
try:
    from referensi.models import AHSPReferensi, RincianReferensi  # type: ignore
except Exception:
    AHSPReferensi = None  # type: ignore
    RincianReferensi = None  # type: ignore


def _orphaned_items_queryset(project):
    """
    Base queryset untuk HargaItemProject yang tidak direferensikan oleh
    DetailAHSPProject maupun DetailAHSPExpanded.
    """
    raw_exists = DetailAHSPProject.objects.filter(
        project=project,
        harga_item_id=OuterRef("pk"),
    )
    expanded_exists = DetailAHSPExpanded.objects.filter(
        project=project,
        harga_item_id=OuterRef("pk"),
    )

    return (
        HargaItemProject.objects.filter(project=project)
        .annotate(
            used_in_raw=Exists(raw_exists),
            used_in_expanded=Exists(expanded_exists),
            last_used_raw=Max("detail_refs__updated_at"),
            last_used_expanded=Max("expanded_refs__updated_at"),
        )
        .filter(used_in_raw=False, used_in_expanded=False)
        .order_by("kode_item")
    )


def detect_orphaned_items(project):
    """
    Return list orphaned HargaItemProject beserta total nilainya.
    """
    queryset = _orphaned_items_queryset(project)
    items = []
    total_value = Decimal("0")

    for item in queryset:
        harga = item.harga_satuan or Decimal("0")
        total_value += harga
        last_used = (
            item.last_used_expanded
            or item.last_used_raw
            or item.updated_at
            or item.created_at
        )
        items.append(
            {
                "id": item.id,
                "kode": item.kode_item,
                "kode_item": item.kode_item,
                "uraian": item.uraian,
                "kategori": item.kategori,
                "satuan": item.satuan,
                "harga_satuan": harga,
                "last_used": last_used,
                "can_delete": True,
                "safety_note": "Item ini tidak digunakan di DetailAHSP manapun",
            }
        )

    return items, total_value


def delete_orphaned_items(project, item_ids: List[int]):
    """
    Delete orphaned HargaItemProject yang id-nya termasuk item_ids.
    Returns (deleted_count, total_value_deleted, skipped_ids).
    """
    if not item_ids:
        return 0, Decimal("0"), item_ids

    queryset = _orphaned_items_queryset(project).filter(id__in=item_ids)
    to_delete = list(
        queryset.values("id", "harga_satuan")
    )  # evaluate before deletion

    if not to_delete:
        return 0, Decimal("0"), item_ids

    orphan_ids = [row["id"] for row in to_delete]
    total_value = sum((row["harga_satuan"] or Decimal("0")) for row in to_delete)

    with transaction.atomic():
        queryset.delete()

    skipped = [pk for pk in item_ids if pk not in orphan_ids]
    return len(orphan_ids), total_value, skipped


def cleanup_orphaned_items(
    project,
    *,
    older_than_days: Optional[int] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
):
    """
    High-level helper untuk membersihkan HargaItemProject orphaned.

    Returns dict dengan ringkasan operasi sehingga dapat dipakai cron/command.
    """
    items, _ = detect_orphaned_items(project)
    cutoff = None
    if older_than_days and older_than_days > 0:
        cutoff = timezone.now() - timedelta(days=older_than_days)

    def _passes_cutoff(item):
        if not cutoff:
            return True
        last_used = item.get("last_used")
        if last_used is None:
            return True
        return last_used < cutoff

    filtered = [item for item in items if _passes_cutoff(item)]

    if limit and limit > 0:
        filtered = filtered[:limit]

    candidate_ids = [item["id"] for item in filtered]
    candidate_value = sum(
        (item["harga_satuan"] or Decimal("0")) for item in filtered
    )

    result = {
        "candidate_count": len(filtered),
        "candidate_value": candidate_value,
        "target_ids": candidate_ids,
        "dry_run": dry_run,
    }

    if dry_run or not candidate_ids:
        result.update(
            {
                "deleted_count": 0,
                "deleted_value": Decimal("0"),
                "skipped_ids": [],
            }
        )
        return result

    deleted_count, deleted_value, skipped_ids = delete_orphaned_items(
        project, candidate_ids
    )
    if deleted_count > 0:
        touch_project_change(project, harga=True)
    result.update(
        {
            "deleted_count": deleted_count,
            "deleted_value": deleted_value,
            "skipped_ids": skipped_ids,
        }
    )
    return result


def snapshot_pekerjaan_details(pekerjaan) -> List[dict]:
    """
    Serialize DetailAHSPProject rows for auditing diff.
    """
    if pekerjaan is None:
        return []

    rows = (
        DetailAHSPProject.objects.filter(
            project=pekerjaan.project,
            pekerjaan=pekerjaan,
        )
        .order_by("id")
        .values(
            "id",
            "kategori",
            "kode",
            "uraian",
            "satuan",
            "koefisien",
            "ref_ahsp_id",
            "ref_pekerjaan_id",
        )
    )

    snapshot = []
    for row in rows:
        snapshot.append(
            {
                "id": row["id"],
                "kategori": row["kategori"],
                "kode": row["kode"],
                "uraian": row["uraian"],
                "satuan": row["satuan"],
                "koefisien": str(row["koefisien"]),
                "ref_kind": (
                    "ahsp"
                    if row["ref_ahsp_id"]
                    else ("job" if row["ref_pekerjaan_id"] else None)
                ),
                "ref_id": row["ref_ahsp_id"] or row["ref_pekerjaan_id"],
            }
        )
    return snapshot


def _build_change_summary(old_data, new_data, action) -> str:
    old_map = {item["kode"]: item for item in (old_data or [])}
    new_map = {item["kode"]: item for item in (new_data or [])}
    old_codes = set(old_map.keys())
    new_codes = set(new_map.keys())

    added = sorted(new_codes - old_codes)
    removed = sorted(old_codes - new_codes)
    changed = []
    for kode in sorted(old_codes & new_codes):
        if old_map[kode].get("koefisien") != new_map[kode].get("koefisien") or (
            old_map[kode].get("kategori") != new_map[kode].get("kategori")
        ):
            changed.append(kode)

    parts = []
    if added:
        parts.append(
            f"added {len(added)} ({', '.join(added[:3])}"
            f"{'…' if len(added) > 3 else ''})"
        )
    if removed:
        parts.append(
            f"removed {len(removed)} ({', '.join(removed[:3])}"
            f"{'…' if len(removed) > 3 else ''})"
        )
    if changed:
        parts.append(
            f"updated {len(changed)} ({', '.join(changed[:3])}"
            f"{'…' if len(changed) > 3 else ''})"
        )

    if not parts:
        return f"{action.title()} - no material changes"
    return "; ".join(parts)


def log_audit(
    project,
    pekerjaan,
    action=DetailAHSPAudit.ACTION_UPDATE,
    *,
    old_data=None,
    new_data=None,
    triggered_by="user",
    user=None,
    change_summary: Optional[str] = None,
):
    """
    Create audit log entry; fail-safe (never raises).
    """
    if project is None or pekerjaan is None:
        return

    summary = change_summary or _build_change_summary(old_data, new_data, action)

    try:
        DetailAHSPAudit.objects.create(
            project=project,
            pekerjaan=pekerjaan,
            action=action,
            old_data=old_data,
            new_data=new_data,
            triggered_by=triggered_by,
            user=user if getattr(user, "id", None) else None,
            change_summary=summary,
        )
    except Exception:
        logger.exception(
            "[AUDIT] Failed to log audit entry for project=%s pekerjaan=%s",
            getattr(project, "id", None),
            getattr(pekerjaan, "id", None),
        )


def get_change_tracker(project, *, create=False) -> Optional[ProjectChangeStatus]:
    try:
        return project.change_status
    except ProjectChangeStatus.DoesNotExist:
        if create:
            return ProjectChangeStatus.objects.create(project=project)
        return None


def touch_project_change(project, *, ahsp=False, harga=False):
    if not (ahsp or harga):
        return None
    tracker = get_change_tracker(project, create=True)
    now_ts = timezone.now()
    update_fields = []
    if ahsp:
        tracker.last_ahsp_change = now_ts
        update_fields.append("last_ahsp_change")
    if harga:
        tracker.last_harga_change = now_ts
        update_fields.append("last_harga_change")
    if update_fields:
        update_fields.append("updated_at")
        tracker.save(update_fields=update_fields)
    return now_ts


def validate_project_data(project, *, orphan_threshold: int = 0) -> Dict[str, object]:
    """
    Run validation checks for legacy data. Returns issue summary.
    """
    report: Dict[str, object] = {
        "project_id": project.id,
        "project_name": getattr(project, "nama", ""),
        "invalid_bundles": [],
        "circular_dependencies": [],
        "expansion_issues": [],
        "orphan_items": [],
        "orphan_count": 0,
        "orphan_threshold": orphan_threshold,
    }

    bundles = (
        DetailAHSPProject.objects.filter(project=project, kategori=HargaItemProject.KATEGORI_LAIN)
        .select_related("ref_pekerjaan")
        .order_by("pekerjaan_id", "id")
    )
    for bundle in bundles:
        issue = None
        if bundle.ref_pekerjaan_id:
            if not bundle.ref_pekerjaan:
                issue = "Referensi pekerjaan hilang"
            elif bundle.ref_pekerjaan.project_id != project.id:
                issue = "Referensi pekerjaan beda project"
        elif bundle.ref_ahsp_id:
            # diasumsikan referensi AHSP tetap valid
            pass
        else:
            issue = "LAIN item tanpa referensi"

        if issue:
            report["invalid_bundles"].append(
                {
                    "pekerjaan_id": bundle.pekerjaan_id,
                    "bundle_id": bundle.id,
                    "kode": bundle.kode,
                    "issue": issue,
                }
            )

        if bundle.ref_pekerjaan_id:
            is_circular, path = check_circular_dependency_pekerjaan(
                bundle.pekerjaan_id,
                bundle.ref_pekerjaan_id,
                project,
            )
            if is_circular:
                report["circular_dependencies"].append(
                    {
                        "bundle_id": bundle.id,
                        "path": path,
                    }
                )

    for pkj in Pekerjaan.objects.filter(project=project).order_by("id"):
        raw_count = DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).count()
        expanded_count = DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pkj).count()
        if raw_count > 0 and expanded_count == 0:
            report["expansion_issues"].append(
                {
                    "pekerjaan_id": pkj.id,
                    "snapshot_kode": pkj.snapshot_kode,
                    "raw_count": raw_count,
                    "expanded_count": expanded_count,
                }
            )

    orphan_items, _ = detect_orphaned_items(project)
    report["orphan_items"] = [
        {"id": item["id"], "kode": item["kode"], "uraian": item["uraian"]} for item in orphan_items
    ]
    report["orphan_count"] = len(orphan_items)
    report["orphan_threshold_exceeded"] = (
        orphan_threshold > 0 and len(orphan_items) > orphan_threshold
    )
    report["passed"] = (
        not report["invalid_bundles"]
        and not report["circular_dependencies"]
        and not report["expansion_issues"]
        and not report["orphan_threshold_exceeded"]
    )
    return report


def reexpand_project_data(project) -> int:
    """
    Re-create DetailAHSPExpanded for seluruh pekerjaan di project.
    """
    count = 0
    now_ts = timezone.now()
    for pkj in Pekerjaan.objects.filter(project=project).order_by("id"):
        _populate_expanded_from_raw(project, pkj)
        Pekerjaan.objects.filter(pk=pkj.pk).update(detail_last_modified=now_ts)
        count += 1
    touch_project_change(project, ahsp=True)
    return count


def fix_project_data(
    project,
    *,
    reexpand: bool = True,
    cleanup_orphans: bool = True,
    older_than_days: Optional[int] = None,
    dry_run: bool = True,
    orphan_limit: Optional[int] = None,
) -> Dict[str, object]:
    """
    Perform fix routines (re-expand & orphan cleanup). Respects dry_run flag.
    """
    summary = {
        "project_id": project.id,
        "reexpanded": 0,
        "cleanup": None,
        "dry_run": dry_run,
    }

    if reexpand:
        if dry_run:
            summary["reexpanded"] = Pekerjaan.objects.filter(project=project).count()
        else:
            summary["reexpanded"] = reexpand_project_data(project)

    if cleanup_orphans:
        cleanup_result = cleanup_orphaned_items(
            project,
            older_than_days=older_than_days,
            dry_run=dry_run,
            limit=orphan_limit,
        )
        summary["cleanup"] = cleanup_result

    return summary


def _upsert_harga_item(project, kategori: str, kode_item: str, uraian: str, satuan: str | None):
    """
    Upsert master harga unik per proyek (tanpa mengubah harga_satuan).

    CRITICAL FIX: kategori is now IMMUTABLE to prevent data inconsistency.
    If kode_item already exists with different kategori, raises ValidationError.
    Uses select_for_update() to prevent race conditions.
    """
    from django.core.exceptions import ValidationError

    try:
        # Try to get existing with row-level lock
        obj = HargaItemProject.objects.select_for_update().get(
            project=project,
            kode_item=kode_item
        )

        # CRITICAL: kategori is IMMUTABLE - cannot be changed once set
        if obj.kategori != kategori:
            raise ValidationError(
                f"Kode '{kode_item}' sudah terdaftar dengan kategori '{obj.kategori}'. "
                f"Tidak dapat diubah ke kategori '{kategori}'. "
                f"Gunakan kode yang berbeda atau periksa kembali data Anda."
            )

        # Update metadata only (uraian, satuan)
        changed = False
        if uraian and obj.uraian != uraian:
            obj.uraian = uraian
            changed = True
        if (satuan or None) != obj.satuan:
            obj.satuan = satuan or None
            changed = True

        if changed:
            obj.save(update_fields=["uraian", "satuan", "updated_at"])

        return obj

    except HargaItemProject.DoesNotExist:
        # Create new - kategori set here and becomes immutable
        obj = HargaItemProject.objects.create(
            project=project,
            kode_item=kode_item,
            kategori=kategori,
            uraian=uraian,
            satuan=satuan
        )
        logger.info(f"[UPSERT_HARGA] Created new HargaItemProject: {kode_item} ({kategori})")
        return obj


def check_circular_dependency_pekerjaan(pekerjaan_id: int, ref_pekerjaan_id: int, project) -> tuple[bool, list[int]]:
    """
    Check apakah reference ke ref_pekerjaan_id akan create circular dependency.

    Returns:
        (is_circular, path):
            - is_circular: True jika circular dependency detected
            - path: List pekerjaan_id yang membentuk cycle (jika circular)

    Examples:
        >>> check_circular_dependency_pekerjaan(1, 2, project)
        (False, [])  # OK, tidak circular

        >>> # Pekerjaan 1 → 2 → 3 → 1 (circular!)
        >>> check_circular_dependency_pekerjaan(1, 2, project)
        (True, [1, 2, 3, 1])
    """
    # Self-reference adalah circular paling simple
    if pekerjaan_id == ref_pekerjaan_id:
        # FASE 0.3: Log circular dependency detection
        log_circular_dependency_check(
            project_id=project.id,
            source_pekerjaan_id=pekerjaan_id,
            target_pekerjaan_id=ref_pekerjaan_id,
            is_circular=True
        )
        return (True, [pekerjaan_id, ref_pekerjaan_id])

    # BFS untuk detect cycle
    visited = set()
    path = [pekerjaan_id]
    queue = [(ref_pekerjaan_id, [pekerjaan_id, ref_pekerjaan_id])]

    while queue:
        current_id, current_path = queue.pop(0)

        if current_id in visited:
            continue
        visited.add(current_id)

        # Check apakah current_id references back ke pekerjaan_id
        refs = DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan_id=current_id,
            kategori='LAIN',
            ref_pekerjaan__isnull=False
        ).values_list('ref_pekerjaan_id', flat=True)

        for next_id in refs:
            if next_id == pekerjaan_id:
                # Found cycle!
                # FASE 0.3: Log circular dependency detection
                log_circular_dependency_check(
                    project_id=project.id,
                    source_pekerjaan_id=pekerjaan_id,
                    target_pekerjaan_id=ref_pekerjaan_id,
                    is_circular=True
                )
                return (True, current_path + [pekerjaan_id])

            if next_id not in visited:
                queue.append((next_id, current_path + [next_id]))

    # FASE 0.3: Log successful check (no circular dependency)
    log_circular_dependency_check(
        project_id=project.id,
        source_pekerjaan_id=pekerjaan_id,
        target_pekerjaan_id=ref_pekerjaan_id,
        is_circular=False
    )

    return (False, [])


def validate_bundle_reference(pekerjaan_id: int, ref_kind: str, ref_id: int, project) -> tuple[bool, str]:
    """
    Validate bundle reference untuk prevent circular dependency dan invalid reference.

    Returns:
        (is_valid, error_message):
            - is_valid: True jika valid
            - error_message: Pesan error jika tidak valid, empty string jika valid

    Validations:
        1. Self-reference (Pekerjaan tidak boleh reference ke diri sendiri)
        2. Circular dependency (A → B → C → A)
        3. Reference exists
        4. Reference dalam project yang sama (untuk ref_kind='job')
    """
    if ref_kind == 'job':
        ref_pekerjaan_id = ref_id

        # Validation 1: Self-reference
        if pekerjaan_id == ref_pekerjaan_id:
            return (False, "Pekerjaan tidak boleh mereferensi diri sendiri")

        # Validation 2: Check existence & same project
        try:
            ref_pekerjaan = Pekerjaan.objects.get(id=ref_pekerjaan_id, project=project)
        except Pekerjaan.DoesNotExist:
            return (False, f"Pekerjaan reference #{ref_pekerjaan_id} tidak ditemukan dalam project ini")

        # Validation 3: Circular dependency
        is_circular, cycle_path = check_circular_dependency_pekerjaan(pekerjaan_id, ref_pekerjaan_id, project)
        if is_circular:
            # Build readable error message
            pekerjaan_codes = []
            for pid in cycle_path:
                try:
                    p = Pekerjaan.objects.get(id=pid)
                    pekerjaan_codes.append(f"{p.snapshot_kode or pid}")
                except Pekerjaan.DoesNotExist:
                    pekerjaan_codes.append(str(pid))

            cycle_str = " → ".join(pekerjaan_codes)
            return (False, f"Circular dependency detected: {cycle_str}")

    elif ref_kind == 'ahsp':
        # AHSP reference validation (existing logic)
        try:
            if AHSPReferensi:
                AHSPReferensi.objects.get(id=ref_id)
        except Exception:
            return (False, f"AHSP reference #{ref_id} tidak ditemukan")

    return (True, "")


def expand_bundle_to_components(
    detail_data: dict,
    project,
    base_koef: Decimal = Decimal('1.0'),
    depth: int = 0,
    visited: Optional[Set[int]] = None
) -> List[dict]:
    """
    Expand bundle (LAIN dengan ref_pekerjaan) menjadi list komponen base (TK/BHN/ALT).

    Supports nested bundles (multi-level) dengan recursive expansion.
    Koefisien dikalikan secara hierarkis: Koef_Final = Koef_Bundle × Koef_Component.

    Args:
        detail_data: Dict dengan keys: kategori, kode, koefisien, ref_pekerjaan_id
        project: Project instance
        base_koef: Accumulated koefisien dari parent levels (untuk nested bundle)
        depth: Current expansion depth (untuk tracking & limit)
        visited: Set of pekerjaan_id untuk prevent infinite recursion

    Returns:
        List of dicts:
        [{
            'kategori': 'TK',
            'kode': 'TK.001',
            'uraian': 'Pekerja',
            'satuan': 'OH',
            'koefisien': Decimal('40.000000'),  # Already multiplied
            'harga_item': HargaItemProject instance,
            'depth': 1
        }, ...]

    Example:
        detail_data = {
            'kategori': 'LAIN',
            'kode': 'PG_A',
            'koefisien': Decimal('20.0'),
            'ref_pekerjaan_id': 123
        }

        # Pekerjaan 123 (PG_A) has:
        # - Bahan A (koef=1)
        # - Tenaga A (koef=2)

        Result:
        [
            {'kode': 'Bahan_A', 'koefisien': Decimal('20.0')},  # 1 × 20
            {'kode': 'Tenaga_A', 'koefisien': Decimal('40.0')}, # 2 × 20
        ]

    Raises:
        ValueError: Jika max depth exceeded atau circular dependency detected
    """
    MAX_DEPTH = 2  # Depth starts at 1, so 2 === 3 actual bundle levels

    # Check max depth
    if depth > MAX_DEPTH:
        raise ValueError(f"Maksimum kedalaman bundle expansion terlampaui (max {MAX_DEPTH})")

    # Initialize visited set
    if visited is None:
        visited = set()

    # Get bundle reference
    ref_pekerjaan_id = detail_data.get('ref_pekerjaan_id')
    if not ref_pekerjaan_id:
        # Not a bundle - shouldn't happen, but return empty to be safe
        logger.warning(f"[EXPAND_BUNDLE] Called for non-bundle detail (no ref_pekerjaan_id): {detail_data}")
        return []

    logger.info(f"[EXPAND_BUNDLE] Depth={depth}, Bundle='{detail_data.get('kode')}', Ref_Pekerjaan_ID={ref_pekerjaan_id}, Koef={detail_data.get('koefisien')}, Base_Koef={base_koef}")

    # Check circular dependency
    if ref_pekerjaan_id in visited:
        visited_codes = []
        for pid in visited:
            try:
                p = Pekerjaan.objects.get(id=pid)
                visited_codes.append(p.snapshot_kode or str(pid))
            except Pekerjaan.DoesNotExist:
                visited_codes.append(str(pid))

        cycle_str = " → ".join(visited_codes)
        logger.error(f"[EXPAND_BUNDLE] Circular dependency detected: {cycle_str}")
        raise ValueError(f"Circular dependency detected in bundle expansion: {cycle_str}")

    # Add to visited
    visited.add(ref_pekerjaan_id)

    # Get bundle koefisien (treated as quantity, not multiplier)
    detail_koef = detail_data.get('koefisien')
    if isinstance(detail_koef, Decimal):
        bundle_koef = detail_koef
    else:
        bundle_koef = Decimal(str(detail_koef or '1.0'))

    # Fetch components dari ref_pekerjaan
    try:
        ref_pekerjaan = Pekerjaan.objects.get(id=ref_pekerjaan_id, project=project)
        logger.info(f"[EXPAND_BUNDLE] Found ref_pekerjaan: {ref_pekerjaan.snapshot_kode} (ID: {ref_pekerjaan.id})")
    except Pekerjaan.DoesNotExist:
        logger.error(f"[EXPAND_BUNDLE] Reference pekerjaan #{ref_pekerjaan_id} not found")
        raise ValueError(f"Reference pekerjaan #{ref_pekerjaan_id} tidak ditemukan")

    components = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan=ref_pekerjaan
    ).select_related('harga_item').order_by('id')

    comp_count = components.count()
    logger.info(f"[EXPAND_BUNDLE] Found {comp_count} components in ref_pekerjaan")

    if comp_count == 0:
        logger.warning(f"[EXPAND_BUNDLE] No components found in ref_pekerjaan {ref_pekerjaan.snapshot_kode} - returning empty")
        # Remove from visited before returning
        visited.discard(ref_pekerjaan_id)
        return []

    result = []

    for comp in components:
        if comp.kategori == 'LAIN' and comp.ref_pekerjaan_id:
            # Nested bundle - recursive expansion
            nested_data = {
                'kategori': comp.kategori,
                'kode': comp.kode,
                'koefisien': comp.koefisien,
                'ref_pekerjaan_id': comp.ref_pekerjaan_id,
            }

            # Multiply base_koef ONLY with nested bundle koef (per-unit composition)
            nested_multiplier = Decimal(str(comp.koefisien or '1.0'))
            nested_components = expand_bundle_to_components(
                detail_data=nested_data,
                project=project,
                base_koef=base_koef * nested_multiplier,
                depth=depth + 1,
                visited=visited.copy()  # Copy to avoid mutation in sibling branches
            )

            result.extend(nested_components)

        else:
            # Base component (TK/BHN/ALT) - store ORIGINAL koefisien (per 1 unit bundle)
            final_koef = comp.koefisien * base_koef

            result.append({
                'kategori': comp.kategori,
                'kode': comp.kode,
                'uraian': comp.uraian,
                'satuan': comp.satuan,
                'koefisien': final_koef,
                'bundle_multiplier': bundle_koef,
                'harga_item': comp.harga_item,
                'depth': depth
            })

    # Remove from visited after processing (for backtracking)
    visited.discard(ref_pekerjaan_id)

    logger.info(f"[EXPAND_BUNDLE] Expansion complete: {len(result)} base components returned")

    return result


def expand_ahsp_bundle_to_components(
    ref_ahsp_id: int,
    project,
    base_koef: Decimal = Decimal('1.0'),
    depth: int = 0,
    visited: Optional[Set[str]] = None
) -> List[dict]:
    """
    Expand bundle dari AHSPReferensi (Master AHSP) menjadi list komponen base (TK/BHN/ALT).

    Similar to expand_bundle_to_components, tapi:
    - Fetch dari RincianReferensi (bukan DetailAHSPProject)
    - LAIN items reference other AHSP by kode_ahsp (string match)
    - Create HargaItemProject on-the-fly untuk components
    - Support nested AHSP bundles (recursive)

    Args:
        ref_ahsp_id: ID dari AHSPReferensi yang akan di-expand
        project: Project instance (untuk create HargaItemProject)
        base_koef: Accumulated koefisien dari parent levels
        depth: Current expansion depth
        visited: Set of ahsp kode_ahsp untuk prevent circular dependency

    Returns:
        List of dicts dengan struktur yang sama seperti expand_bundle_to_components:
        [{
            'kategori': 'TK',
            'kode': 'TK-0001',
            'uraian': 'Mandor',
            'satuan': 'OH',
            'koefisien': Decimal('0.013000'),
            'harga_item': HargaItemProject instance,
            'depth': 1
        }, ...]

    Raises:
        ValueError: Jika max depth exceeded atau circular dependency detected
    """
    MAX_DEPTH = 2  # Depth starts at 1, so 2 === 3 actual bundle levels

    # Check max depth
    if depth > MAX_DEPTH:
        raise ValueError(f"Maksimum kedalaman AHSP bundle expansion terlampaui (max {MAX_DEPTH})")

    # Initialize visited set (track by kode_ahsp string, not ID)
    if visited is None:
        visited = set()

    # Fetch AHSP Referensi
    if not AHSPReferensi:
        raise ValueError("AHSPReferensi model not available")

    try:
        ahsp = AHSPReferensi.objects.get(id=ref_ahsp_id)
        logger.info(f"[EXPAND_AHSP_BUNDLE] Depth={depth}, AHSP='{ahsp.kode_ahsp}', ID={ref_ahsp_id}")
    except AHSPReferensi.DoesNotExist:
        logger.error(f"[EXPAND_AHSP_BUNDLE] AHSP Referensi #{ref_ahsp_id} not found")
        raise ValueError(f"AHSP Referensi #{ref_ahsp_id} tidak ditemukan")

    # Check circular dependency
    if ahsp.kode_ahsp in visited:
        visited_codes = list(visited)
        cycle_str = " → ".join(visited_codes)
        logger.error(f"[EXPAND_AHSP_BUNDLE] Circular dependency detected: {cycle_str}")
        raise ValueError(f"Circular dependency detected in AHSP bundle expansion: {cycle_str}")

    visited.add(ahsp.kode_ahsp)

    # Fetch components from RincianReferensi
    if not RincianReferensi:
        raise ValueError("RincianReferensi model not available")

    components = RincianReferensi.objects.filter(ahsp=ahsp).order_by('id')
    comp_count = components.count()
    logger.info(f"[EXPAND_AHSP_BUNDLE] Found {comp_count} components in AHSP '{ahsp.kode_ahsp}'")

    if comp_count == 0:
        logger.warning(f"[EXPAND_AHSP_BUNDLE] No components found in AHSP '{ahsp.kode_ahsp}' - returning empty")
        visited.discard(ahsp.kode_ahsp)
        return []

    result = []

    for comp in components:
        if comp.kategori == 'LAIN':
            # Nested AHSP bundle - lookup by kode_item (should match another kode_ahsp)
            logger.info(f"[EXPAND_AHSP_BUNDLE] LAIN item detected: '{comp.kode_item}' (koef={comp.koefisien})")

            try:
                # Try to find AHSP by kode_ahsp matching kode_item
                nested_ahsp = AHSPReferensi.objects.get(kode_ahsp=comp.kode_item)

                # Recursive expansion
                nested_components = expand_ahsp_bundle_to_components(
                    ref_ahsp_id=nested_ahsp.id,
                    project=project,
                    base_koef=base_koef * comp.koefisien,
                    depth=depth + 1,
                    visited=visited.copy()  # Copy to avoid mutation in sibling branches
                )

                result.extend(nested_components)

            except AHSPReferensi.DoesNotExist:
                # LAIN item doesn't reference another AHSP - treat as base component
                logger.warning(
                    f"[EXPAND_AHSP_BUNDLE] LAIN item '{comp.kode_item}' doesn't match any AHSP kode. "
                    f"Treating as base component."
                )

                # Treat as base component
                final_koef = comp.koefisien * base_koef

                result.append({
                    'kategori': comp.kategori,
                    'kode': comp.kode_item,
                    'uraian': comp.uraian_item,
                    'satuan': comp.satuan_item,
                    'koefisien': final_koef,
                    'harga_item': None,  # Will be created by caller
                    'depth': depth
                })

        else:
            # Base component (TK/BHN/ALT)
            final_koef = comp.koefisien * base_koef

            result.append({
                'kategori': comp.kategori,
                'kode': comp.kode_item,
                'uraian': comp.uraian_item,
                'satuan': comp.satuan_item,
                'koefisien': final_koef,
                'harga_item': None,  # Will be created by caller
                'depth': depth
            })

    # Remove from visited after processing (backtracking)
    visited.discard(ahsp.kode_ahsp)

    logger.info(f"[EXPAND_AHSP_BUNDLE] Expansion complete: {len(result)} base components returned")

    return result


def generate_custom_code(project) -> str:
    """
    Hasilkan kode otomatis untuk pekerjaan kustom: CUST-0001, CUST-0002, ...
    Unik 'secara praktis' per proyek (berbasis jumlah yang ada).
    """
    # Hitung yang sudah ada; +1 untuk nomor berikutnya
    n = Pekerjaan.objects.filter(project=project, source_type=Pekerjaan.SOURCE_CUSTOM).count() + 1
    return f"CUST-{n:04d}"


def _populate_expanded_from_raw(project, pekerjaan):
    """
    DUAL STORAGE HELPER: Populate DetailAHSPExpanded from DetailAHSPProject.

    BUG FIX #2: Now handles bundle expansion for LAIN items with ref_ahsp or ref_pekerjaan.
    Previously, this function only passed through items without expansion, causing bundle
    items to show 0 value in rekap calculations.

    This is called after:
    - clone_ref_pekerjaan() creates DetailAHSPProject from referensi
    - User manually edits REF_MODIFIED details

    Args:
        project: Project instance
        pekerjaan: Pekerjaan instance
    """
    from .models import DetailAHSPProject, DetailAHSPExpanded
    from .numeric import quantize_half_up, DECIMAL_SPEC

    logger.info(f"[POPULATE_EXPANDED] START - Project: {project.id}, Pekerjaan: {pekerjaan.id} ({pekerjaan.snapshot_kode})")

    # Delete old expanded data
    old_count = DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).count()
    DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).delete()
    logger.info(f"[POPULATE_EXPANDED] Deleted {old_count} old expanded rows")

    # Read from raw storage
    raw_details = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan=pekerjaan
    ).select_related('harga_item', 'ref_ahsp', 'ref_pekerjaan').order_by('id')
    logger.info(f"[POPULATE_EXPANDED] Found {raw_details.count()} raw details")

    dp_koef = DECIMAL_SPEC["KOEF"].dp

    # Process each item: expand bundles or pass-through direct items
    expanded_to_create = []
    for detail_obj in raw_details:
        if detail_obj.kategori == 'LAIN' and detail_obj.ref_ahsp_id:
            # AHSP BUNDLE - expand from master AHSP
            logger.info(f"[POPULATE_EXPANDED] AHSP bundle detected: '{detail_obj.kode}' → ref_ahsp_id={detail_obj.ref_ahsp_id}")

            try:
                expansion_start = time.time()
                expanded_components = expand_ahsp_bundle_to_components(
                    ref_ahsp_id=detail_obj.ref_ahsp_id,
                    project=project,
                    base_koef=Decimal('1.0'),
                    depth=1,
                    visited=None
                )
                duration_ms = (time.time() - expansion_start) * 1000
                component_count = len(expanded_components)
                logger.info(f"[POPULATE_EXPANDED] AHSP expansion: {len(expanded_components)} components")

                log_bundle_expansion(
                    project_id=project.id,
                    pekerjaan_id=pekerjaan.id,
                    bundle_kode=detail_obj.kode,
                    ref_kind='ahsp',
                    ref_id=detail_obj.ref_ahsp_id,
                    component_count=component_count,
                    duration_ms=round(duration_ms, 2)
                )

                # Add expanded components
                for comp in expanded_components:
                    comp_hip = _upsert_harga_item(
                        project,
                        comp['kategori'],
                        comp['kode'],
                        comp['uraian'],
                        comp['satuan']
                    )

                    expanded_to_create.append(DetailAHSPExpanded(
                        project=project,
                        pekerjaan=pekerjaan,
                        source_detail=detail_obj,
                        harga_item=comp_hip,
                        kategori=comp['kategori'],
                        kode=comp['kode'],
                        uraian=comp['uraian'],
                        satuan=comp['satuan'],
                        koefisien=quantize_half_up(comp['koefisien'], dp_koef),
                        source_bundle_kode=detail_obj.kode,
                        expansion_depth=comp['depth'],
                    ))

            except ValueError as e:
                logger.error(f"[POPULATE_EXPANDED] AHSP bundle expansion failed for '{detail_obj.kode}': {e}")
                # Continue - don't crash the entire populate process

        elif detail_obj.kategori == 'LAIN' and detail_obj.ref_pekerjaan_id:
            # PEKERJAAN BUNDLE - expand from another pekerjaan
            logger.info(f"[POPULATE_EXPANDED] Pekerjaan bundle detected: '{detail_obj.kode}' → ref_pekerjaan_id={detail_obj.ref_pekerjaan_id}")

            detail_dict = {
                'kategori': detail_obj.kategori,
                'kode': detail_obj.kode,
                'uraian': detail_obj.uraian,
                'satuan': detail_obj.satuan,
                'koefisien': detail_obj.koefisien,
                'ref_pekerjaan_id': detail_obj.ref_pekerjaan_id,
            }

            try:
                expansion_start = time.time()
                expanded_components = expand_bundle_to_components(
                    detail_data=detail_dict,
                    project=project,
                    base_koef=Decimal('1.0'),
                    depth=1,
                    visited=None
                )
                duration_ms = (time.time() - expansion_start) * 1000
                component_count = len(expanded_components)
                logger.info(f"[POPULATE_EXPANDED] Pekerjaan expansion: {len(expanded_components)} components")

                log_bundle_expansion(
                    project_id=project.id,
                    pekerjaan_id=pekerjaan.id,
                    bundle_kode=detail_obj.kode,
                    ref_kind='job',
                    ref_id=detail_obj.ref_pekerjaan_id,
                    component_count=component_count,
                    duration_ms=round(duration_ms, 2)
                )

                # Add expanded components
                for comp in expanded_components:
                    comp_hip = _upsert_harga_item(
                        project,
                        comp['kategori'],
                        comp['kode'],
                        comp['uraian'],
                        comp['satuan']
                    )

                    expanded_to_create.append(DetailAHSPExpanded(
                        project=project,
                        pekerjaan=pekerjaan,
                        source_detail=detail_obj,
                        harga_item=comp_hip,
                        kategori=comp['kategori'],
                        kode=comp['kode'],
                        uraian=comp['uraian'],
                        satuan=comp['satuan'],
                        koefisien=quantize_half_up(comp['koefisien'], dp_koef),
                        source_bundle_kode=detail_obj.kode,
                        expansion_depth=comp['depth'],
                    ))

            except ValueError as e:
                logger.error(f"[POPULATE_EXPANDED] Pekerjaan bundle expansion failed for '{detail_obj.kode}': {e}")
                # Continue - don't crash the entire populate process

        else:
            # DIRECT INPUT (TK/BHN/ALT or LAIN without ref) - pass through
            expanded_to_create.append(DetailAHSPExpanded(
                project=project,
                pekerjaan=pekerjaan,
                source_detail=detail_obj,
                harga_item=detail_obj.harga_item,
                kategori=detail_obj.kategori,
                kode=detail_obj.kode,
                uraian=detail_obj.uraian,
                satuan=detail_obj.satuan,
                koefisien=detail_obj.koefisien,
                source_bundle_kode=None,  # Not from bundle
                expansion_depth=0,  # Direct input
            ))

    # Bulk create
    if expanded_to_create:
        DetailAHSPExpanded.objects.bulk_create(expanded_to_create, ignore_conflicts=True)
        logger.info(f"[POPULATE_EXPANDED] SUCCESS - Created {len(expanded_to_create)} expanded rows")
    else:
        logger.warning(f"[POPULATE_EXPANDED] No expanded rows to create")


@transaction.atomic
def cascade_bundle_re_expansion(project, modified_pekerjaan_id: int, visited: Optional[Set[int]] = None) -> int:
    """
    CASCADE RE-EXPANSION: When a pekerjaan is modified, re-expand all pekerjaan that reference it.

    CRITICAL FIX for stale data bug:
    - When user edits Pekerjaan B that is referenced by Pekerjaan A as a bundle
    - Pekerjaan A's DetailAHSPExpanded becomes stale (contains old values)
    - This function finds all referencing pekerjaan and re-expands them
    - Supports recursive re-expansion (A → B → C chain)

    Args:
        project: Project instance
        modified_pekerjaan_id: ID of pekerjaan that was just modified
        visited: Set of pekerjaan IDs already processed (prevent infinite loop)

    Returns:
        int: Total number of pekerjaan re-expanded (including recursive)

    Example:
        Pekerjaan A: LAIN Bundle_B (ref_pekerjaan=B)
        Pekerjaan B: TK L.01 (koef=5.0)

        User edits Pekerjaan B: L.01 koef 5.0 → 8.0

        Without cascade:
            Pekerjaan A still shows L.01 with koef=15.0 (STALE!)

        With cascade:
            1. Detect Pekerjaan A references B
            2. Re-expand Pekerjaan A → L.01 now shows koef=24.0 (CORRECT!)
    """
    # FASE 0.3: Start timing for performance monitoring
    start_time = time.time()

    if visited is None:
        visited = set()

    cascade_depth = len(visited)

    # Prevent infinite loop
    if modified_pekerjaan_id in visited:
        logger.warning(
            f"[CASCADE_RE_EXPANSION] Already visited pekerjaan {modified_pekerjaan_id}, skipping to prevent loop"
        )
        return 0

    visited.add(modified_pekerjaan_id)

    logger.info(
        f"[CASCADE_RE_EXPANSION] START - Modified pekerjaan: {modified_pekerjaan_id}, "
        f"Visited: {len(visited)}, Depth: {cascade_depth}"
    )

    # Find all pekerjaan that reference this modified pekerjaan as a bundle
    referencing_details = DetailAHSPProject.objects.filter(
        project=project,
        kategori='LAIN',
        ref_pekerjaan_id=modified_pekerjaan_id
    ).select_related('pekerjaan').distinct()

    referencing_pekerjaan_ids = list(
        referencing_details.values_list('pekerjaan_id', flat=True).distinct()
    )

    if not referencing_pekerjaan_ids:
        logger.info(
            f"[CASCADE_RE_EXPANSION] No pekerjaan references #{modified_pekerjaan_id}, done"
        )
        return 0

    logger.info(
        f"[CASCADE_RE_EXPANSION] Found {len(referencing_pekerjaan_ids)} pekerjaan referencing "
        f"#{modified_pekerjaan_id}: {referencing_pekerjaan_ids}"
    )

    re_expanded_count = 0

    # Re-expand each referencing pekerjaan
    for pkj_id in referencing_pekerjaan_ids:
        try:
            pkj = Pekerjaan.objects.get(id=pkj_id, project=project)
            pkj_kode = pkj.snapshot_kode or f"PKJ#{pkj.id}"

            logger.info(
                f"[CASCADE_RE_EXPANSION] Re-expanding pekerjaan {pkj_kode} (ID: {pkj.id}) "
                f"which references #{modified_pekerjaan_id}"
            )

            # Re-populate expanded data
            _populate_expanded_from_raw(project, pkj)
            re_expanded_count += 1

            logger.info(f"[CASCADE_RE_EXPANSION] Successfully re-expanded {pkj_kode}")

            # RECURSIVE: This pekerjaan might also be referenced by others!
            # Example: A → B → C, if C modified, must re-expand B then A
            recursive_count = cascade_bundle_re_expansion(
                project=project,
                modified_pekerjaan_id=pkj.id,
                visited=visited.copy()  # Pass copy to avoid mutation in sibling branches
            )

            re_expanded_count += recursive_count

            if recursive_count > 0:
                logger.info(
                    f"[CASCADE_RE_EXPANSION] Recursive re-expansion from {pkj_kode}: "
                    f"{recursive_count} pekerjaan"
                )

        except Pekerjaan.DoesNotExist:
            logger.error(
                f"[CASCADE_RE_EXPANSION] Pekerjaan {pkj_id} not found, skipping"
            )
            continue
        except Exception as e:
            logger.error(
                f"[CASCADE_RE_EXPANSION] Failed to re-expand pekerjaan {pkj_id}: {str(e)}",
                exc_info=True
            )
            # Continue with other pekerjaan, don't fail entire cascade
            continue

    # FASE 0.3: Calculate duration and log structured metrics
    duration_ms = (time.time() - start_time) * 1000

    change_ts = timezone.now()

    if referencing_pekerjaan_ids:
        Pekerjaan.objects.filter(
            id__in=referencing_pekerjaan_ids
        ).update(detail_last_modified=change_ts)

    logger.info(
        f"[CASCADE_RE_EXPANSION] COMPLETE - Re-expanded {re_expanded_count} pekerjaan total "
        f"(direct + recursive), Duration: {duration_ms:.2f}ms"
    )

    # Log structured metrics
    log_cascade_operation(
        project_id=project.id,
        modified_pekerjaan_id=modified_pekerjaan_id,
        referencing_pekerjaan_ids=referencing_pekerjaan_ids,
        cascade_depth=cascade_depth,
        re_expanded_count=re_expanded_count,
        duration_ms=round(duration_ms, 2)
    )

    if referencing_pekerjaan_ids:
        touch_project_change(project, ahsp=True)
        summary = (
            f"Cascade re-expansion from pekerjaan {modified_pekerjaan_id} "
            f"(depth={cascade_depth}) affecting {len(referencing_pekerjaan_ids)} pekerjaan."
        )
        for target_id in referencing_pekerjaan_ids:
            try:
                target = Pekerjaan.objects.get(id=target_id, project=project)
            except Pekerjaan.DoesNotExist:
                continue
            log_audit(
                project,
                target,
                DetailAHSPAudit.ACTION_CASCADE,
                triggered_by="cascade",
                user=None,
                change_summary=summary,
            )

    return re_expanded_count


@transaction.atomic
def clone_ref_pekerjaan(
    project,
    sub: SubKlasifikasi,
    ref_obj,
    source_type: str,
    ordering_index: int,
    auto_load_rincian: bool = True,
    *,
    override_uraian: Optional[str] = None,
    override_satuan: Optional[str] = None,
) -> Pekerjaan:
    """
    Clone snapshot identitas pekerjaan dari AHSP referensi dan,
    bila auto_load_rincian=True, clone semua rincian ke DetailAHSPProject.

    Penyesuaian:
    - source_type == ref          → snapshot_kode = <kode_ref>
    - source_type == ref_modified → snapshot_kode = "mod.X-<kode_ref>" (X bertambah per proyek)
      dan boleh override uraian/satuan dari parameter.
    """
    logger.info(f"[CLONE_REF_PKJ] START - Project: {project.id}, Source_Type: {source_type}, Auto_Load: {auto_load_rincian}")

    # Siapkan snapshot_kode sesuai mode
    rid = getattr(ref_obj, 'id', None)
    kode_ref   = getattr(ref_obj, 'kode_ahsp', None) or (f"REF-{rid}" if rid is not None else "REF")
    uraian_ref = getattr(ref_obj, 'nama_ahsp', None) or (f"AHSP {rid}" if rid is not None else "AHSP")
    satuan_ref = getattr(ref_obj, 'satuan', None)

    logger.info(f"[CLONE_REF_PKJ] Ref_Obj: ID={rid}, Kode={kode_ref}, Uraian={uraian_ref}")

    if source_type == Pekerjaan.SOURCE_REF_MOD:
        # nomor bertambah per proyek berdasarkan jumlah ref_modified yang sudah ada
        x = Pekerjaan.objects.filter(project=project, source_type=Pekerjaan.SOURCE_REF_MOD).count() + 1
        snap_kode = f"mod.{x}-{kode_ref}" if kode_ref else None
    else:
        snap_kode = kode_ref

    snap_uraian = override_uraian if (source_type == Pekerjaan.SOURCE_REF_MOD and override_uraian) else uraian_ref
    snap_satuan = override_satuan if (source_type == Pekerjaan.SOURCE_REF_MOD and override_satuan) else satuan_ref

    # Snapshot identitas pekerjaan dari referensi
    pkj = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=source_type,
        ref=ref_obj if AHSPReferensi is not None else None,
        snapshot_kode=snap_kode,
        snapshot_uraian=snap_uraian,
        snapshot_satuan=snap_satuan,
        auto_load_rincian=auto_load_rincian,
        ordering_index=ordering_index,
    )
    logger.info(f"[CLONE_REF_PKJ] Created Pekerjaan: ID={pkj.id}, Kode={snap_kode}, Source={source_type}")

    # Muat rincian dari referensi jika diminta
    if auto_load_rincian and RincianReferensi is not None:
        rincian_qs = RincianReferensi.objects.filter(ahsp=ref_obj).order_by('id')
        logger.info(f"[CLONE_REF_PKJ] Loading rincian: Found {rincian_qs.count()} rows")
        bulk_details: List[DetailAHSPProject] = []
        for rr in rincian_qs:
            # Kategori sinkron dengan app referensi: TK/BHN/ALT/LAIN
            kategori = rr.kategori
            kode = rr.kode_item
            uraian = rr.uraian_item
            satuan = rr.satuan_item
            koef = rr.koefisien

            # BUG FIX #2: For LAIN items (bundles), resolve ref_ahsp from kode_item
            # In RincianReferensi, LAIN items store the referenced AHSP's kode_ahsp in kode_item field
            ref_ahsp_obj = None
            if kategori == 'LAIN' and AHSPReferensi is not None:
                try:
                    # Try to find AHSP by kode_ahsp matching kode_item
                    ref_ahsp_obj = AHSPReferensi.objects.filter(kode_ahsp=kode).first()
                    if ref_ahsp_obj:
                        logger.info(f"[CLONE_REF_PKJ] LAIN item '{kode}' resolved to AHSP '{ref_ahsp_obj.kode_ahsp}' (ID: {ref_ahsp_obj.id})")
                    else:
                        logger.warning(f"[CLONE_REF_PKJ] LAIN item '{kode}' doesn't match any AHSP - treating as non-bundle LAIN")
                except Exception as e:
                    logger.warning(f"[CLONE_REF_PKJ] Error resolving AHSP for LAIN item '{kode}': {e}")

            hip = _upsert_harga_item(project, kategori, kode, uraian, satuan)
            bulk_details.append(DetailAHSPProject(
                project=project,
                pekerjaan=pkj,
                harga_item=hip,
                kategori=kategori,
                kode=kode,
                uraian=uraian,
                satuan=satuan,
                koefisien=koef,
                ref_ahsp=ref_ahsp_obj,  # Set ref_ahsp for LAIN items
            ))
        if bulk_details:
            DetailAHSPProject.objects.bulk_create(bulk_details, ignore_conflicts=True)
            logger.info(f"[CLONE_REF_PKJ] Created {len(bulk_details)} DetailAHSPProject rows")

            # DUAL STORAGE: Also populate DetailAHSPExpanded for REF/REF_MODIFIED
            # Items from referensi are direct input (TK/BHN/ALT), not bundles
            # So we pass-through to expanded storage
            logger.info(f"[CLONE_REF_PKJ] Calling _populate_expanded_from_raw for dual storage...")
            _populate_expanded_from_raw(project, pkj)
    logger.info(f"[CLONE_REF_PKJ] COMPLETE - Pekerjaan ID: {pkj.id}")
    return pkj

def expand_bundle_recursive(
    detail_dict: dict,
    base_koefisien: Decimal,
    project,
    depth: int = 0,
    visited: Optional[Set[tuple]] = None
) -> list[tuple]:
    """
    Recursively expand bundle item ke unit terkecil (TK/BHN/ALT).

    Args:
        detail_dict: Dict containing kategori, ref_ahsp_id, ref_pekerjaan_id, koefisien
        base_koefisien: Koefisien multiplier dari parent (accumulated)
        project: Project instance
        depth: Current recursion depth (untuk prevent infinite loop)
        visited: Set of visited (ref_kind, ref_id) untuk circular detection

    Returns:
        List of tuples: (kategori, kode, uraian, satuan, koefisien_total)

    Raises:
        ValueError: Jika circular dependency detected atau max depth exceeded
    """
    if visited is None:
        visited = set()

    MAX_DEPTH = 10  # Safety limit
    if depth > MAX_DEPTH:
        logger.error(
            f"Max recursion depth {MAX_DEPTH} exceeded during bundle expansion",
            extra={'detail': detail_dict, 'project_id': project.id}
        )
        raise ValueError(f"Maksimum kedalaman bundle ({MAX_DEPTH} level) terlampaui. Periksa struktur pekerjaan gabungan Anda.")

    hasil = []
    detail_koef = Decimal(str(detail_dict.get('koefisien', 0)))
    total_koef = base_koefisien * detail_koef

    # Case 1: Reference ke AHSPReferensi
    ref_ahsp_id = detail_dict.get('ref_ahsp_id')
    if ref_ahsp_id and RincianReferensi:
        bundle_key = ('ahsp', ref_ahsp_id)

        # Circular dependency check
        if bundle_key in visited:
            logger.error(
                f"Circular dependency detected: AHSP #{ref_ahsp_id}",
                extra={'visited': list(visited), 'project_id': project.id}
            )
            raise ValueError(f"Circular dependency detected pada AHSP Referensi #{ref_ahsp_id}")

        visited.add(bundle_key)

        try:
            # Get rincian dari AHSP Referensi
            ref_items = RincianReferensi.objects.filter(ahsp_id=ref_ahsp_id).values(
                'kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien'
            )

            for ref_item in ref_items:
                if ref_item['kategori'] in ['TK', 'BHN', 'ALT']:
                    # Base case: sudah level terkecil
                    ref_koef = Decimal(str(ref_item['koefisien']))
                    final_koef = total_koef * ref_koef
                    hasil.append((
                        ref_item['kategori'],
                        ref_item['kode_item'],
                        ref_item['uraian_item'],
                        ref_item['satuan_item'],
                        final_koef
                    ))
                # Note: RincianReferensi biasanya tidak memiliki kategori LAIN yang recursive
        finally:
            visited.remove(bundle_key)

    # Case 2: Reference ke Pekerjaan dalam project (NEW!)
    ref_pekerjaan_id = detail_dict.get('ref_pekerjaan_id')
    if ref_pekerjaan_id:
        bundle_key = ('job', ref_pekerjaan_id)

        # Circular dependency check
        if bundle_key in visited:
            # Get pekerjaan codes for better error message
            try:
                pkj = Pekerjaan.objects.get(id=ref_pekerjaan_id)
                pkj_code = pkj.snapshot_kode or f"#{ref_pekerjaan_id}"
            except Pekerjaan.DoesNotExist:
                pkj_code = f"#{ref_pekerjaan_id}"

            logger.error(
                f"Circular dependency detected: Pekerjaan {pkj_code}",
                extra={'visited': list(visited), 'project_id': project.id}
            )
            raise ValueError(f"Circular dependency detected pada Pekerjaan {pkj_code}")

        visited.add(bundle_key)

        try:
            # Get detail dari Pekerjaan yang di-reference
            ref_details = DetailAHSPProject.objects.filter(
                project=project,
                pekerjaan_id=ref_pekerjaan_id
            ).values('kategori', 'kode', 'uraian', 'satuan', 'koefisien', 'ref_ahsp_id', 'ref_pekerjaan_id')

            for ref_detail in ref_details:
                if ref_detail['kategori'] in ['TK', 'BHN', 'ALT']:
                    # Base case: sudah level terkecil
                    ref_koef = Decimal(str(ref_detail['koefisien']))
                    final_koef = total_koef * ref_koef
                    hasil.append((
                        ref_detail['kategori'],
                        ref_detail['kode'],
                        ref_detail['uraian'],
                        ref_detail['satuan'],
                        final_koef
                    ))
                elif ref_detail['kategori'] == 'LAIN':
                    # Recursive case: expand lagi
                    if ref_detail['ref_ahsp_id'] or ref_detail['ref_pekerjaan_id']:
                        sub_items = expand_bundle_recursive(
                            ref_detail,
                            total_koef,
                            project,
                            depth + 1,
                            visited
                        )
                        hasil.extend(sub_items)
        finally:
            visited.remove(bundle_key)

    return hasil


def _get_markup_percent(project) -> Decimal:
    # ⬇️ Tambahkan import lokal ini
    from .models import ProjectPricing
    obj = ProjectPricing.objects.filter(project=project).first()
    if obj and obj.markup_percent is not None:
        return Decimal(str(obj.markup_percent))
    return Decimal("0.00")

def compute_rekap_for_project(project):
    raw_ts = DetailAHSPProject.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    expanded_ts = DetailAHSPExpanded.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    volume_ts = VolumePekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    pekerjaan_ts = Pekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']
    pricing_ts = ProjectPricing.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']

    def _ts(val):
        return val.isoformat() if val else "0"

    cache_key = f"rekap:{project.id}:v2"
    signature = (
        _ts(raw_ts),
        _ts(expanded_ts),
        _ts(volume_ts),
        _ts(pekerjaan_ts),
        _ts(pricing_ts),
    )
    cached = cache.get(cache_key)
    if cached and cached.get("sig") == signature:
        return cached.get("data", [])
    """
    Hitung komponen biaya per pekerjaan (pakai override Profit/Margin per-pekerjaan jika ada):
      A = Σ(TK), B = Σ(BHN), C = Σ(ALT), LAIN = Σ(LAIN)
      D = A+B+C  (kompat historis)
      E_base = A+B+C+LAIN
      F = E_base × markup_eff   (markup_eff = override% jika ada, else project Profit/Margin %)
      G = E_base + F            (HSP/unit sesudah markup)
      total = G × volume
    Nilai kompat:
      E (lama) diisi = F (margin) agar test lama tetap lolos,
      HSP = E_base (pra-markup) untuk konsistensi dengan halaman Volume & test.
    """
    # --- Ambil Profit/Margin default proyek (fallback 10.00)
    proj_markup = Decimal("0")
    try:
        pp = ProjectPricing.objects.filter(project=project).first()
        if pp and pp.markup_percent is not None:
            proj_markup = Decimal(pp.markup_percent)
    except Exception:
        pass

    # --- Agregasi nilai per kategori
    # NEW: Read from DetailAHSPExpanded (dual storage - already expanded!).
    # If expanded storage kosong (mis. data dibuat langsung via fixtures),
    # fallback ke DetailAHSPProject agar test lama tetap berjalan.
    price = DJF('harga_item__harga_satuan')
    coef = DJF('koefisien')
    nilai_expr = ExpressionWrapper(coef * price, output_field=DecimalField(max_digits=20, decimal_places=2))

    kategori_keys = ['TK', 'BHN', 'ALT', 'LAIN']

    def _aggregate_components(model, apply_bundle_multiplier=False):
        data: Dict[int, Dict[str, float]] = {}
        qs = model.objects.filter(project=project)

        effective_coef = DJF('koefisien')
        if apply_bundle_multiplier:
            # DetailAHSPExpanded menyimpan koef komponen per 1 unit bundle.
            # Kalikan kembali dengan DetailAHSPProject.koefisien (source_detail)
            # agar agregasi TK/BHN/ALT mencerminkan jumlah bundle aktual.
            bundle_multiplier = Case(
                When(
                    Q(source_detail__kategori='LAIN')
                    & (Q(source_detail__ref_pekerjaan__isnull=False) | Q(source_detail__ref_ahsp__isnull=False)),
                    then=DJF('source_detail__koefisien'),
                ),
                default=Value(Decimal('1.0')),
                output_field=DecimalField(max_digits=18, decimal_places=6),
            )
            effective_coef = ExpressionWrapper(
                effective_coef * bundle_multiplier,
                output_field=DecimalField(max_digits=24, decimal_places=6),
            )

        value_expr = ExpressionWrapper(
            effective_coef * price,
            output_field=DecimalField(max_digits=24, decimal_places=2),
        )

        qs = qs.values('pekerjaan_id', 'kategori').annotate(jumlah=Sum(value_expr))
        for row in qs:
            pkj_id = row['pekerjaan_id']
            kat = row['kategori']
            if kat not in kategori_keys:
                continue
            data.setdefault(pkj_id, {k: 0.0 for k in kategori_keys})
            data[pkj_id][kat] = float(row['jumlah'] or 0.0)
        return data

    agg = _aggregate_components(DetailAHSPExpanded, apply_bundle_multiplier=True)
    if not agg:
        agg = _aggregate_components(DetailAHSPProject)

    # --- Volume map
    vol_map = dict(VolumePekerjaan.objects
                   .filter(project=project)
                   .values_list('pekerjaan_id', 'quantity'))

    # --- Iterasi pekerjaan sekalian baca override
    result = []
    for p in (Pekerjaan.objects
              .filter(project=project)
              .order_by('ordering_index', 'id')
              .values('id', 'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan', 'markup_override_percent')):
        pkj_id   = p['id']
        A        = agg.get(pkj_id, {}).get('TK', 0.0)  or 0.0
        B        = agg.get(pkj_id, {}).get('BHN', 0.0) or 0.0
        C        = agg.get(pkj_id, {}).get('ALT', 0.0) or 0.0
        LAIN     = agg.get(pkj_id, {}).get('LAIN', 0.0) or 0.0

        D        = A + B + C
        E_base   = D + LAIN

        # --- effective markup: override jika ada, else project
        ov = p.get('markup_override_percent', None)
        mp = float(ov if ov is not None else proj_markup)   # persen (mis. 12.5)
        mp_frac = mp / 100.0

        F      = E_base * mp_frac
        G      = E_base + F
        volume = float(vol_map.get(pkj_id) or 0.0)
        total  = float(G) * volume

        result.append(dict(
            pekerjaan_id = pkj_id,
            kode         = p['snapshot_kode'],
            uraian       = p['snapshot_uraian'],
            satuan       = p['snapshot_satuan'],

            A=A, B=B, C=C, D=D,
            LAIN=LAIN,
            E_base=E_base,

            E=F,          # margin (kompat lama)
            F=F,          # margin eksplisit
            G=G,          # unit price sesudah markup

            HSP=E_base,       # ★ unit price pra-markup (dipakai beberapa test/halaman)
            unit_price=E_base,# alias aman untuk FE

            markup_eff=mp,    # persen efektif
            volume=volume,
            total=total,      # = G * volume
        ))
    cache.set(cache_key, {"sig": signature, "data": result}, 300)  # 5 menit (atau sesuai kebutuhan)
    return result


def compute_kebutuhan_items(
    project,
    mode='all',
    tahapan_id=None,
    filters=None,
    time_scope=None,
):
    """
    Compute rekap kebutuhan dengan support split volume dan filtering.
    Menggunakan caching berdasarkan kombinasi filter untuk respon lebih cepat.

    Args:
        project: Project instance
        mode: 'all' atau 'tahapan'
        tahapan_id: ID tahapan saat mode='tahapan'
        filters: dict filter klasifikasi/sub/kategori/pekerjaan
        time_scope: dict rentang waktu {'mode','start','end'} untuk scope mingguan/bulanan
    """
    import time
    import logging

    logger = logging.getLogger(__name__)
    start_time = time.perf_counter()

    mode_flag = 'tahapan' if (mode == 'tahapan' and tahapan_id) else 'all'
    normalized_filters = _normalize_kebutuhan_filters(filters)
    normalized_time_scope = _normalize_time_scope(time_scope)
    cache_namespace = f"rekap_kebutuhan:{project.id}"
    entry_key = _kebutuhan_entry_key(
        mode_flag,
        tahapan_id if mode_flag == 'tahapan' else None,
        normalized_filters,
        normalized_time_scope,
    )
    signature = _kebutuhan_signature(project)

    bucket = cache.get(cache_namespace)
    if bucket:
        cached_entry = bucket.get(entry_key)
        if cached_entry and cached_entry.get('sig') == signature:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"Rekap Kebutuhan CACHE HIT - project={project.id}, elapsed={elapsed:.2f}ms, rows={len(cached_entry.get('data', []))}")
            return cached_entry.get('data', [])

    # ========================================================================
    # STEP 1: Determine scope - pekerjaan mana yang akan di-aggregate
    # ========================================================================
    if mode_flag == 'tahapan':
        pt_qs = PekerjaanTahapan.objects.filter(
            tahapan_id=tahapan_id
        ).select_related('pekerjaan', 'tahapan')
        pekerjaan_proporsi = {
            pt.pekerjaan_id: pt.proporsi_volume / Decimal('100')
        for pt in pt_qs
        }
        pekerjaan_ids = list(pekerjaan_proporsi.keys())
    else:
        pekerjaan_ids = list(
            Pekerjaan.objects.filter(project=project).values_list('id', flat=True)
        )
        pekerjaan_proporsi = {pk: Decimal('1.0') for pk in pekerjaan_ids}

    # ========================================================================
    # STEP 2: Apply additional filters (klasifikasi, sub-klasifikasi)
    # ========================================================================
    if normalized_filters['klasifikasi_ids'] or normalized_filters['sub_klasifikasi_ids']:
        queryset = Pekerjaan.objects.filter(id__in=pekerjaan_ids)
        if normalized_filters['klasifikasi_ids']:
            queryset = queryset.filter(
                sub_klasifikasi__klasifikasi_id__in=normalized_filters['klasifikasi_ids']
        )
        if normalized_filters['sub_klasifikasi_ids']:
            queryset = queryset.filter(
                sub_klasifikasi_id__in=normalized_filters['sub_klasifikasi_ids']
            )
        pekerjaan_ids = list(queryset.values_list('id', flat=True))
        pekerjaan_proporsi = {
            pk: pekerjaan_proporsi.get(pk, Decimal('1.0'))
            for pk in pekerjaan_ids
        }

    if normalized_filters['pekerjaan_ids']:
        allowed = set(normalized_filters['pekerjaan_ids'])
        pekerjaan_ids = [pk for pk in pekerjaan_ids if pk in allowed]
        pekerjaan_proporsi = {
            pk: pekerjaan_proporsi.get(pk, Decimal('1.0')) for pk in pekerjaan_ids
        }

    if not pekerjaan_ids:
        rows = []
        # Cache empty result
        new_bucket = bucket or {}
        new_bucket[entry_key] = {"sig": signature, "data": rows}
        cache.set(cache_namespace, new_bucket, KEBUTUHAN_CACHE_TIMEOUT)
        return rows

    apply_time_scope = (
        mode_flag == 'all' and normalized_time_scope.get('mode') != 'all'
    )
    time_scope_multiplier = {}
    if apply_time_scope:
        time_scope_multiplier = _build_time_scope_multiplier(
            project,
            pekerjaan_ids,
            normalized_time_scope
        )

    # ========================================================================
    # STEP 3: Get volume map untuk semua pekerjaan dalam scope
    # ========================================================================
    vol_map = dict(
        VolumePekerjaan.objects
        .filter(project=project, pekerjaan_id__in=pekerjaan_ids)
        .values_list('pekerjaan_id', 'quantity')
    )

    # ========================================================================
    # STEP 4: Aggregate items dengan proporsi volume
    # ========================================================================
    aggregated = defaultdict(Decimal)
    cost_map = defaultdict(Decimal)
    price_seed = {}

    # Batch processing untuk large pekerjaan lists (optimization)
    BATCH_SIZE = 500
    all_details = []

    if len(pekerjaan_ids) > BATCH_SIZE:
        # Process in batches to prevent query timeout
        for i in range(0, len(pekerjaan_ids), BATCH_SIZE):
            batch = pekerjaan_ids[i:i+BATCH_SIZE]
            batch_details = list(
                DetailAHSPExpanded.objects.filter(
                    project=project,
                    pekerjaan_id__in=batch
                ).select_related('harga_item', 'source_detail').values(
                    'pekerjaan_id',
                    'kategori',
                    'kode',
                    'uraian',
                    'satuan',
                    'koefisien',
                    'source_detail__kategori',
                    'source_detail__ref_pekerjaan_id',
                    'source_detail__ref_ahsp_id',
                    'source_detail__koefisien',
                    'harga_item__harga_satuan',
                )
            )
            all_details.extend(batch_details)
        details = all_details
    else:
        # Standard query with select_related optimization
        details = list(
            DetailAHSPExpanded.objects.filter(
                project=project,
                pekerjaan_id__in=pekerjaan_ids
            ).select_related('harga_item', 'source_detail').values(
                'pekerjaan_id',
                'kategori',
                'kode',
                'uraian',
                'satuan',
                'koefisien',
                'source_detail__kategori',
                'source_detail__ref_pekerjaan_id',
                'source_detail__ref_ahsp_id',
                'source_detail__koefisien',
                'harga_item__harga_satuan',
            )
        )

    if not details:
        details = list(
            DetailAHSPProject.objects.filter(
                project=project,
                pekerjaan_id__in=pekerjaan_ids
            ).values(
                'pekerjaan_id',
                'kategori',
                'kode',
                'uraian',
                'satuan',
                'koefisien',
                'harga_item__harga_satuan',
            )
        )

    for detail in details:
        pekerjaan_id = detail['pekerjaan_id']
        volume_total = Decimal(str(vol_map.get(pekerjaan_id, 0) or 0))
        proporsi = pekerjaan_proporsi.get(pekerjaan_id, Decimal('1.0'))
        if apply_time_scope:
            ratio = time_scope_multiplier.get(pekerjaan_id, Decimal('0'))
            if ratio <= 0:
                continue
            if ratio > Decimal('1.0'):
                ratio = Decimal('1.0')
            volume_efektif = volume_total * proporsi * ratio
        else:
            volume_efektif = volume_total * proporsi
        if volume_efektif == 0:
            continue

        kategori = detail['kategori']
        koefisien = Decimal(str(detail['koefisien'] or 0))

        is_bundle_detail = (
            detail.get('source_detail__kategori') == 'LAIN'
            and (
                detail.get('source_detail__ref_pekerjaan_id')
                or detail.get('source_detail__ref_ahsp_id')
            )
        )
        if is_bundle_detail:
            multiplier = Decimal(str(detail.get('source_detail__koefisien') or 0))
            koefisien *= multiplier

        key = (
            kategori,
            detail['kode'],
            detail['uraian'],
            detail['satuan']
        )
        qty = koefisien * volume_efektif
        aggregated[key] += qty
        price_raw = detail.get('harga_item__harga_satuan')
        price_val = Decimal(str(price_raw or 0))
        if price_val:
            cost_map[key] += price_val * qty
            price_seed.setdefault(key, price_val)

    # ========================================================================
    # STEP 5: Apply kategori filter (jika ada)
    # ========================================================================
    if normalized_filters['kategori_items']:
        allowed_kat = set(normalized_filters['kategori_items'])
        aggregated = {
            k: v for k, v in aggregated.items()
            if k[0] in allowed_kat
        }

    # ========================================================================
    # STEP 6: Format output
    # ========================================================================
    rows = []
    for (kategori, kode, uraian, satuan), quantity in aggregated.items():
        qty_str = f"{quantity:.6f}".rstrip('0').rstrip('.')
        total_cost = cost_map.get((kategori, kode, uraian, satuan), Decimal('0'))
        if quantity and quantity != 0:
            unit_price = total_cost / quantity
        else:
            unit_price = price_seed.get((kategori, kode, uraian, satuan), Decimal('0'))
        rows.append({
            'kategori': kategori,
            'kode': kode or '-',
            'uraian': uraian or '-',
            'satuan': satuan or '-',
            'quantity': qty_str,
            'quantity_decimal': quantity,
            'harga_satuan': _format_decimal(unit_price),
            'harga_satuan_decimal': unit_price,
            'harga_total': _format_decimal(total_cost),
            'harga_total_decimal': total_cost,
        })

    kategori_order = {k: i for i, k in enumerate(KEBUTUHAN_KATEGORI_ORDER, start=1)}
    rows.sort(key=lambda x: (
        kategori_order.get(x['kategori'], 99),
        x['kode'] or '',
        x['uraian'] or ''
    ))

    new_bucket = bucket or {}
    new_bucket[entry_key] = {"sig": signature, "data": rows}
    cache.set(cache_namespace, new_bucket, KEBUTUHAN_CACHE_TIMEOUT)

    # Performance logging
    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"Rekap Kebutuhan COMPUTED - project={project.id}, "
        f"elapsed={elapsed:.2f}ms, rows={len(rows)}, "
        f"pekerjaan={len(pekerjaan_ids)}, details={len(details)}"
    )

    return rows


# ============================================================================
# PHASE 5 TRACK 2.1: DATA VALIDATION
# ============================================================================

def validate_kebutuhan_data(project, mode='all', tahapan_id=None, filters=None, time_scope=None):
    """
    Validate that snapshot and timeline data are consistent.

    Returns dict with validation results comparing:
    - Total costs between snapshot and timeline
    - Item counts per kategori
    - Potential data integrity issues

    Args:
        project: Project instance
        mode: 'all', 'tahapan', etc.
        tahapan_id: Optional tahapan filter
        filters: Dict with kategori, klasifikasi, etc.
        time_scope: Optional time scope filter

    Returns:
        {
            'valid': bool,
            'snapshot_total': Decimal,
            'timeline_total': Decimal,
            'difference': Decimal,
            'tolerance': Decimal,
            'snapshot_count': int,
            'timeline_count': int,
            'kategori_breakdown': dict,
            'warnings': list,
            'timestamp': str,
        }
    """
    from decimal import Decimal
    from datetime import datetime

    warnings = []

    # Get snapshot data
    snapshot_data = compute_kebutuhan_items(
        project,
        mode=mode,
        tahapan_id=tahapan_id,
        filters=filters or {},
        time_scope=time_scope,
    )

    # Get timeline data
    timeline_data = compute_kebutuhan_timeline(
        project,
        mode=mode,
        tahapan_id=tahapan_id,
        filters=filters or {},
        time_scope=time_scope,
    )

    # Calculate snapshot totals
    snapshot_total = Decimal('0')
    snapshot_count = len(snapshot_data)
    snapshot_by_kategori = {}

    for item in snapshot_data:
        cost = Decimal(str(item.get('harga_total') or 0))
        snapshot_total += cost

        kategori = item.get('kategori', 'UNKNOWN')
        if kategori not in snapshot_by_kategori:
            snapshot_by_kategori[kategori] = {'count': 0, 'total': Decimal('0')}
        snapshot_by_kategori[kategori]['count'] += 1
        snapshot_by_kategori[kategori]['total'] += cost

    # Calculate timeline totals
    timeline_total = Decimal('0')
    timeline_items_seen = set()
    timeline_by_kategori = {}

    for period in timeline_data.get('periods', []):
        for item in period.get('items', []):
            # Track unique items
            item_key = f"{item.get('kategori')}_{item.get('kode')}"
            timeline_items_seen.add(item_key)

            cost = Decimal(str(item.get('harga_total') or 0))
            timeline_total += cost

            kategori = item.get('kategori', 'UNKNOWN')
            if kategori not in timeline_by_kategori:
                timeline_by_kategori[kategori] = {'count': 0, 'total': Decimal('0')}
            # Don't double-count items across periods
            if item_key not in [f"{k.get('kategori')}_{k.get('kode')}" for k in period.get('items', [])[:period.get('items', []).index(item)]]:
                timeline_by_kategori[kategori]['count'] += 1
            timeline_by_kategori[kategori]['total'] += cost

    timeline_count = len(timeline_items_seen)

    # Calculate difference
    diff = abs(snapshot_total - timeline_total)
    tolerance = Decimal('0.01')  # 1 cent tolerance for rounding

    is_valid = diff <= tolerance

    # Check for warnings
    if snapshot_count != timeline_count:
        warnings.append(
            f"Item count mismatch: {snapshot_count} in snapshot vs {timeline_count} unique in timeline"
        )

    # Compare kategori breakdowns
    kategori_breakdown = {}
    all_kategori = set(snapshot_by_kategori.keys()) | set(timeline_by_kategori.keys())

    for kategori in all_kategori:
        snap = snapshot_by_kategori.get(kategori, {'count': 0, 'total': Decimal('0')})
        time = timeline_by_kategori.get(kategori, {'count': 0, 'total': Decimal('0')})

        kategori_diff = abs(snap['total'] - time['total'])
        kategori_breakdown[kategori] = {
            'snapshot': {
                'count': snap['count'],
                'total': float(snap['total']),
            },
            'timeline': {
                'count': time['count'],
                'total': float(time['total']),
            },
            'difference': float(kategori_diff),
            'match': kategori_diff <= tolerance,
        }

        if kategori_diff > tolerance:
            warnings.append(
                f"{kategori}: Rp {kategori_diff:,.2f} difference between snapshot and timeline"
            )

    # If total doesn't match but no kategori warnings, it's likely timing/period issue
    if not is_valid and not any('difference between' in w for w in warnings):
        warnings.append(
            "Total mismatch may be due to items not assigned to tahapan/jadwal"
        )

    return {
        'valid': is_valid,
        'snapshot_total': float(snapshot_total),
        'timeline_total': float(timeline_total),
        'difference': float(diff),
        'tolerance': float(tolerance),
        'snapshot_count': snapshot_count,
        'timeline_count': timeline_count,
        'kategori_breakdown': kategori_breakdown,
        'warnings': warnings,
        'timestamp': datetime.now().isoformat(),
    }


def _calculate_overlap_days(start_a, end_a, start_b, end_b):
    start = max(start_a, start_b)
    end = min(end_a, end_b)
    if start > end:
        return 0
    return (end - start).days + 1


def compute_kebutuhan_timeline(
    project,
    mode='all',
    tahapan_id=None,
    filters=None,
    time_scope=None,
):
    """
    Compute kebutuhan items dan distribusi per periode (mingguan/bulanan).
    """
    period_options = get_project_period_options(project)
    normalized_scope = _normalize_time_scope(time_scope)
    scope_mode = normalized_scope.get('mode', 'all')

    if scope_mode.startswith('month'):
        bucket_mode = 'month'
    else:
        bucket_mode = 'week'

    start_value = normalized_scope.get('start_value') or None
    end_value = normalized_scope.get('end_value') or start_value

    buckets = _select_period_buckets(period_options, bucket_mode, start_value, end_value)
    if not buckets:
        buckets = period_options['weeks' if bucket_mode == 'week' else 'months']

    if not buckets:
        return {
            'periods': [],
            'meta': {
                'reason': 'no_schedule',
                'bucket_mode': bucket_mode,
                'quantity_totals': {},
                'grand_total_cost': '0',
            }
        }

    bucket_map = {}
    for bucket in buckets:
        start_date = _ensure_date(bucket['start_date'])
        end_date = _ensure_date(bucket['end_date']) or start_date
        bucket_map[bucket['value']] = {
            'start': start_date,
            'end': end_date,
            'meta': bucket,
            'rows': {},
            'qty_totals': defaultdict(Decimal),
            'cost_totals': defaultdict(Decimal),
        }

    mode_flag = 'tahapan' if (mode == 'tahapan' and tahapan_id) else 'all'
    normalized_filters = _normalize_kebutuhan_filters(filters)
    normalized_time_scope = _normalize_time_scope(time_scope)

    if mode_flag == 'tahapan':
        pt_qs = PekerjaanTahapan.objects.filter(
            tahapan_id=tahapan_id
        ).select_related('pekerjaan', 'tahapan')
        pekerjaan_proporsi = {
            pt.pekerjaan_id: pt.proporsi_volume / Decimal('100')
            for pt in pt_qs
        }
        pekerjaan_ids = list(pekerjaan_proporsi.keys())
    else:
        pekerjaan_ids = list(
            Pekerjaan.objects.filter(project=project).values_list('id', flat=True)
        )
        pekerjaan_proporsi = {pk: Decimal('1.0') for pk in pekerjaan_ids}

    if normalized_filters['klasifikasi_ids'] or normalized_filters['sub_klasifikasi_ids']:
        queryset = Pekerjaan.objects.filter(id__in=pekerjaan_ids)
        if normalized_filters['klasifikasi_ids']:
            queryset = queryset.filter(
                sub_klasifikasi__klasifikasi_id__in=normalized_filters['klasifikasi_ids']
            )
        if normalized_filters['sub_klasifikasi_ids']:
            queryset = queryset.filter(
                sub_klasifikasi_id__in=normalized_filters['sub_klasifikasi_ids']
            )
        pekerjaan_ids = list(queryset.values_list('id', flat=True))
        pekerjaan_proporsi = {
            pk: pekerjaan_proporsi.get(pk, Decimal('1.0'))
            for pk in pekerjaan_ids
        }

    if normalized_filters['pekerjaan_ids']:
        allowed = set(normalized_filters['pekerjaan_ids'])
        pekerjaan_ids = [pk for pk in pekerjaan_ids if pk in allowed]
        pekerjaan_proporsi = {
            pk: pekerjaan_proporsi.get(pk, Decimal('1.0')) for pk in pekerjaan_ids
        }

    if not pekerjaan_ids:
        return {
            'periods': [],
            'meta': {
                'reason': 'no_scope',
                'bucket_mode': bucket_mode,
                'quantity_totals': {},
                'grand_total_cost': '0',
            }
        }

    vol_map = dict(
        VolumePekerjaan.objects
        .filter(project=project, pekerjaan_id__in=pekerjaan_ids)
        .values_list('pekerjaan_id', 'quantity')
    )

    details = list(
        DetailAHSPExpanded.objects.filter(
            project=project,
            pekerjaan_id__in=pekerjaan_ids
        ).values(
            'pekerjaan_id',
            'kategori',
            'kode',
            'uraian',
            'satuan',
            'koefisien',
            'source_detail__kategori',
            'source_detail__ref_pekerjaan_id',
            'source_detail__ref_ahsp_id',
            'source_detail__koefisien',
            'harga_item__harga_satuan',
        )
    )

    if not details:
        details = list(
            DetailAHSPProject.objects.filter(
                project=project,
                pekerjaan_id__in=pekerjaan_ids
            ).values(
                'pekerjaan_id',
                'kategori',
                'kode',
                'uraian',
                'satuan',
                'koefisien',
                'harga_item__harga_satuan',
            )
        )

    assignment_qs = PekerjaanTahapan.objects.filter(
        pekerjaan_id__in=pekerjaan_ids
    ).select_related('tahapan')
    if mode_flag == 'tahapan' and tahapan_id:
        assignment_qs = assignment_qs.filter(tahapan_id=tahapan_id)

    assignment_map = defaultdict(list)
    for assignment in assignment_qs:
        start_date = _ensure_date(getattr(assignment.tahapan, 'tanggal_mulai', None))
        end_date = _ensure_date(getattr(assignment.tahapan, 'tanggal_selesai', None)) or start_date
        if not start_date or not end_date:
            continue
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        duration = (end_date - start_date).days + 1
        if duration <= 0:
            continue
        assignment_map[assignment.pekerjaan_id].append({
            'start': start_date,
            'end': end_date,
            'duration': duration,
            'proporsi': Decimal(str(assignment.proporsi_volume or 0)),
        })

    def accumulate(target_rows, kategori, kode, uraian, satuan, qty_val, price_val):
        key = (kategori, kode, uraian, satuan)
        row = target_rows.get(key)
        if not row:
            row = {
                'kategori': kategori,
                'kode': kode or '-',
                'uraian': uraian or '-',
                'satuan': satuan or '-',
                'quantity': Decimal('0'),
                'harga_satuan': price_val,
                'total_cost': Decimal('0'),
            }
            target_rows[key] = row
        row['quantity'] += qty_val
        if price_val:
            row['total_cost'] += price_val * qty_val

    unscheduled_rows = {}
    bucket_totals = {key: Decimal('0') for key in KEBUTUHAN_KATEGORI_ORDER}
    grand_total_cost = Decimal('0')

    for detail in details:
        pekerjaan_id = detail['pekerjaan_id']
        if pekerjaan_id not in pekerjaan_ids:
            continue
        volume_total = Decimal(str(vol_map.get(pekerjaan_id, 0) or 0))
        proporsi_multiplier = pekerjaan_proporsi.get(pekerjaan_id, Decimal('1.0'))
        koefisien = Decimal(str(detail['koefisien'] or 0))
        if koefisien == 0 or volume_total == 0:
            continue
        is_bundle_detail = (
            detail.get('source_detail__kategori') == 'LAIN'
            and (
                detail.get('source_detail__ref_pekerjaan_id')
                or detail.get('source_detail__ref_ahsp_id')
            )
        )
        if is_bundle_detail:
            multiplier = Decimal(str(detail.get('source_detail__koefisien') or 0))
            koefisien *= multiplier
        base_quantity = koefisien * volume_total * proporsi_multiplier
        if base_quantity == 0:
            continue
        price_val = Decimal(str(detail.get('harga_item__harga_satuan') or 0))
        kategori = detail['kategori']
        kode = detail['kode']
        uraian = detail['uraian']
        satuan = detail['satuan']

        assignments = assignment_map.get(pekerjaan_id)
        if not assignments:
            accumulate(unscheduled_rows, kategori, kode, uraian, satuan, base_quantity, price_val)
            continue

        for assignment in assignments:
            if assignment['proporsi'] <= 0:
                continue
            assignment_fraction = assignment['proporsi'] / Decimal('100')
            assignment_quantity = base_quantity * assignment_fraction
            if assignment_quantity == 0:
                continue
            duration_days = assignment['duration']
            for bucket_key, bucket in bucket_map.items():
                start = bucket['start']
                end = bucket['end']
                if not start or not end:
                    continue
                overlap_days = _calculate_overlap_days(start, end, assignment['start'], assignment['end'])
                if overlap_days <= 0:
                    continue
                ratio = Decimal(overlap_days) / Decimal(duration_days)
                qty_val = assignment_quantity * ratio
                if qty_val == 0:
                    continue
                accumulate(bucket['rows'], kategori, kode, uraian, satuan, qty_val, price_val)
                bucket['qty_totals'][kategori] += qty_val
                if price_val:
                    bucket['cost_totals'][kategori] += price_val * qty_val

    periods_payload = []
    for bucket_key, bucket in bucket_map.items():
        rows = bucket['rows']
        if not rows:
            continue
        items = []
        for (kategori, kode, uraian, satuan), info in rows.items():
            quantity = info['quantity']
            items.append({
                'kategori': kategori,
                'kode': kode,
                'uraian': uraian,
                'satuan': satuan,
                'quantity': _format_decimal(quantity),
                'quantity_decimal': quantity,
                'harga_satuan': _format_decimal(info['harga_satuan']),
                'harga_satuan_decimal': info['harga_satuan'],
                'harga_total': _format_decimal(info['total_cost']),
                'harga_total_decimal': info['total_cost'],
            })
        items.sort(key=lambda x: (x['kategori'], x['kode'], x['uraian']))
        totals = {k: _format_decimal(v) for k, v in bucket['qty_totals'].items()}
        bucket_cost = sum(bucket['cost_totals'].values())
        grand_total_cost += bucket_cost
        for cat in KEBUTUHAN_KATEGORI_ORDER:
            bucket_totals[cat] += bucket['qty_totals'].get(cat, Decimal('0'))
        periods_payload.append({
            'value': bucket['meta']['value'],
            'label': bucket['meta']['label'],
            'start_date': bucket['meta']['start_date'],
            'end_date': bucket['meta']['end_date'],
            'items': items,
            'quantity_totals': totals,
            'total_cost': _format_decimal(bucket_cost),
            'total_cost_decimal': bucket_cost,
        })

    if unscheduled_rows:
        items = []
        cost_totals = Decimal('0')
        qty_totals_unscheduled = {k: Decimal('0') for k in KEBUTUHAN_KATEGORI_ORDER}
        for (kategori, kode, uraian, satuan), info in unscheduled_rows.items():
            items.append({
                'kategori': kategori,
                'kode': kode,
                'uraian': uraian,
                'satuan': satuan,
                'quantity': _format_decimal(info['quantity']),
                'quantity_decimal': info['quantity'],
                'harga_satuan': _format_decimal(info['harga_satuan']),
                'harga_satuan_decimal': info['harga_satuan'],
                'harga_total': _format_decimal(info['total_cost']),
                'harga_total_decimal': info['total_cost'],
            })
            qty_totals_unscheduled[kategori] += info['quantity']
            cost_totals += info['total_cost']
        items.sort(key=lambda x: (x['kategori'], x['kode'], x['uraian']))
        grand_total_cost += cost_totals
        for cat in KEBUTUHAN_KATEGORI_ORDER:
            bucket_totals[cat] += qty_totals_unscheduled.get(cat, Decimal('0'))
        periods_payload.append({
            'value': 'unscheduled',
            'label': 'Di luar jadwal',
            'start_date': None,
            'end_date': None,
            'items': items,
            'quantity_totals': {k: _format_decimal(v) for k, v in qty_totals_unscheduled.items()},
            'total_cost': _format_decimal(cost_totals),
            'total_cost_decimal': cost_totals,
        })

    periods_payload.sort(key=lambda item: (
        item['start_date'] or '9999-99-99',
        item['value']
    ))

    meta = {
        'mode': mode_flag,
        'tahapan_id': tahapan_id,
        'bucket_mode': bucket_mode,
        'time_scope': normalized_time_scope,
        'period_count': len(periods_payload),
        'quantity_totals': {k: _format_decimal(v) for k, v in bucket_totals.items()},
        'grand_total_cost': _format_decimal(grand_total_cost),
    }

    return {
        'periods': periods_payload,
        'meta': meta,
    }



def get_tahapan_summary(project):
    """
    Get summary info untuk semua tahapan dalam project.
    
    Args:
        project: Project instance
    
    Returns:
        list of dict: Summary info per tahapan
        
    Example:
        [
            {
                'tahapan_id': 1,
                'nama': 'Tahap 1: Persiapan',
                'urutan': 1,
                'jumlah_pekerjaan': 3,
                'total_assigned_proportion': 300.00,  # 3 pekerjaan @ 100%
                'tanggal_mulai': '2025-01-01',
                'tanggal_selesai': '2025-01-15'
            },
            ...
        ]
    """
    tahapan_list = TahapPelaksanaan.objects.filter(
        project=project
    ).prefetch_related('pekerjaan_items').order_by('urutan', 'id')
    
    result = []
    for tahap in tahapan_list:
        # Count pekerjaan dan total proporsi
        assignments = tahap.pekerjaan_items.all()
        jumlah_pekerjaan = assignments.values('pekerjaan').distinct().count()
        total_proporsi = sum(a.proporsi_volume for a in assignments)
        
        result.append({
            'tahapan_id': tahap.id,
            'nama': tahap.nama,
            'urutan': tahap.urutan,
            'deskripsi': tahap.deskripsi,
            'jumlah_pekerjaan': jumlah_pekerjaan,
            'total_assigned_proportion': float(total_proporsi),
            'tanggal_mulai': tahap.tanggal_mulai.isoformat() if tahap.tanggal_mulai else None,
            'tanggal_selesai': tahap.tanggal_selesai.isoformat() if tahap.tanggal_selesai else None,
            'created_at': tahap.created_at.isoformat() if tahap.created_at else None,
            'is_auto_generated': tahap.is_auto_generated,
            'generation_mode': tahap.generation_mode,
        })
    
    return result


def get_unassigned_pekerjaan(project):
    """
    Get list pekerjaan yang belum fully assigned ke tahapan.
    
    Args:
        project: Project instance
    
    Returns:
        list of dict: Pekerjaan yang belum/partial assigned
        
    Example:
        [
            {
                'pekerjaan_id': 5,
                'kode': '1.1.1',
                'uraian': 'Galian Tanah',
                'assigned_proportion': 60.00,
                'unassigned_proportion': 40.00,
                'status': 'partial'  # 'unassigned' | 'partial'
            },
            ...
        ]
    """
    from django.db.models import Sum, F
    
    # Get all pekerjaan dengan total assigned proportion
    pekerjaan_qs = Pekerjaan.objects.filter(
        project=project
    ).annotate(
        total_assigned=Sum('tahapan_assignments__proporsi_volume')
    ).order_by('ordering_index', 'id')
    
    result = []
    for pkj in pekerjaan_qs:
        assigned = float(pkj.total_assigned or 0)
        unassigned = 100.0 - assigned
        
        # Skip jika fully assigned
        if abs(unassigned) < 0.01:
            continue
        
        # Determine status
        if assigned < 0.01:
            status = 'unassigned'
        else:
            status = 'partial'
        
        result.append({
            'pekerjaan_id': pkj.id,
            'kode': pkj.snapshot_kode,
            'uraian': pkj.snapshot_uraian,
            'assigned_proportion': assigned,
            'unassigned_proportion': unassigned,
            'status': status,
            'klasifikasi': (pkj.sub_klasifikasi.klasifikasi.name 
                        if pkj.sub_klasifikasi and pkj.sub_klasifikasi.klasifikasi 
                        else None),
            'sub_klasifikasi': (pkj.sub_klasifikasi.name
                            if pkj.sub_klasifikasi
                            else None),
        })

    return result


# ==============================================================================
# Deep Copy Service - FASE 3.1 (Enhanced with Error Handling)
# ==============================================================================

import logging
from .exceptions import (
    DeepCopyValidationError,
    DeepCopyBusinessError,
    DeepCopyDatabaseError,
    DeepCopySystemError,
    classify_database_error,
    classify_system_error,
)

logger = logging.getLogger(__name__)


class DeepCopyService:
    """
    Service for deep copying projects with all related data.

    Implements a 12-step dependency-ordered copy process with ID mapping
    to handle foreign key relationships correctly.

    Enhanced Features (FASE 3.1.1):
        - Comprehensive input validation
        - Skip tracking for orphaned data
        - Warnings collection for user feedback
        - Detailed error classification
        - Structured logging

    Usage:
        service = DeepCopyService(source_project)
        new_project = service.copy(
            new_owner=request.user,
            new_name="Project Copy",
            new_tanggal_mulai=date(2025, 1, 1),
            copy_jadwal=True
        )

        # Check warnings
        warnings = service.get_warnings()
        skipped = service.get_skipped_items()

    Architecture:
        1. Uses transaction.atomic for data integrity
        2. Maintains ID mappings to remap FKs correctly
        3. Follows dependency order to avoid FK constraint violations
        4. Validates all copied data before saving
        5. Tracks skipped items and generates warnings
    """

    def __init__(self, source_project):
        """
        Initialize the service with source project.

        Args:
            source_project: The project to copy from

        Raises:
            DeepCopyValidationError: If source_project is invalid
            DeepCopyBusinessError: If project is too large (warning only)
        """
        # Validate source project exists
        if not source_project:
            raise DeepCopyValidationError(
                code=3002,
                message="Source project is None",
                details={"project": None}
            )

        if not source_project.id:
            raise DeepCopyValidationError(
                code=3002,
                message="Source project is not saved (no ID)",
                details={"project": str(source_project)}
            )

        self.source = source_project

        # Validate project size and log warning for large projects
        from .models import Pekerjaan
        pekerjaan_count = Pekerjaan.objects.filter(project=source_project).count()

        if pekerjaan_count > 1000:
            logger.warning(
                f"Large project copy initiated: {pekerjaan_count} pekerjaan",
                extra={
                    'project_id': source_project.id,
                    'pekerjaan_count': pekerjaan_count,
                    'source': 'DeepCopyService.__init__'
                }
            )
            # Don't block, just warn - business decides if this is acceptable

        # Initialize tracking structures
        self.warnings = []
        self.skipped_items = {
            'subklasifikasi': [],
            'pekerjaan': [],
            'volume': [],
            'ahsp_template': [],
        }

        # ID mapping dictionaries for FK remapping
        # Format: {old_id: new_id}
        self.mappings = {
            'project': {},
            'pricing': {},
            'parameter': {},
            'klasifikasi': {},
            'subklasifikasi': {},
            'pekerjaan': {},
            'volume': {},
            'harga_item': {},
            'ahsp_template': {},
            'rincian_ahsp': {},
            'tahapan': {},
            'jadwal': {},
        }

        self.stats = {
            'klasifikasi_copied': 0,
            'subklasifikasi_copied': 0,
            'pekerjaan_copied': 0,
            'volume_copied': 0,
            'harga_item_copied': 0,
            'ahsp_template_copied': 0,
            'rincian_ahsp_copied': 0,
            'parameter_copied': 0,
            'tahapan_copied': 0,
            'jadwal_copied': 0,
        }

    @transaction.atomic
    def copy(
        self,
        new_owner,
        new_name,
        new_tanggal_mulai=None,
        copy_jadwal=True
    ):
        """
        Perform deep copy of project with all related data (Enhanced).

        Args:
            new_owner: User who will own the copied project
            new_name: Name for the new project
            new_tanggal_mulai: Start date for new project (optional)
            copy_jadwal: Whether to copy schedule data (default: True)

        Returns:
            The newly created project instance

        Raises:
            DeepCopyValidationError: If input validation fails
            DeepCopyBusinessError: If business rules violated
            DeepCopyDatabaseError: If database operation fails
            DeepCopySystemError: If system resource error occurs
        """
        from dashboard.models import Project
        from django.db import IntegrityError, OperationalError, ProgrammingError
        import re

        # ===== INPUT VALIDATION =====

        # Validate new_name is not empty
        if not new_name or not new_name.strip():
            raise DeepCopyValidationError(
                code=1001,
                message="Project name is empty",
                details={'new_name': new_name}
            )

        new_name = new_name.strip()

        # Validate name length
        if len(new_name) > 200:
            raise DeepCopyValidationError(
                code=1004,
                message=f"Project name too long: {len(new_name)} characters",
                details={'length': len(new_name), 'max': 200, 'name': new_name}
            )

        # XSS prevention - check for HTML tags
        if re.search(r'[<>]', new_name):
            raise DeepCopyValidationError(
                code=1007,
                message=f"Project name contains invalid characters: {new_name}",
                details={'name': new_name, 'invalid_chars': '<>'}
            )

        # Validate date range if provided
        if new_tanggal_mulai:
            if new_tanggal_mulai.year > 2100 or new_tanggal_mulai.year < 1900:
                raise DeepCopyValidationError(
                    code=1003,
                    message=f"Invalid date range: {new_tanggal_mulai}",
                    details={'date': str(new_tanggal_mulai), 'valid_range': '1900-2100'}
                )

        # ===== BUSINESS RULE VALIDATION =====

        # Check for duplicate project name
        if Project.objects.filter(owner=new_owner, nama=new_name).exists():
            raise DeepCopyBusinessError(
                code=3001,
                message=f"Project with name '{new_name}' already exists for user {new_owner.id}",
                details={
                    'owner_id': new_owner.id,
                    'owner_username': new_owner.username,
                    'project_name': new_name
                }
            )

        # Log copy initiation
        logger.info(
            f"Starting deep copy of project {self.source.id}",
            extra={
                'source_project_id': self.source.id,
                'source_project_name': self.source.nama,
                'new_owner_id': new_owner.id,
                'new_project_name': new_name,
                'copy_jadwal': copy_jadwal
            }
        )

        # ===== EXECUTE COPY WITH ERROR HANDLING =====

        try:
            # Step 1: Copy Project
            new_project = self._copy_project(new_owner, new_name, new_tanggal_mulai)

            # Step 2: Copy ProjectPricing
            self._copy_project_pricing(new_project)

            # Step 3: Copy ProjectParameter
            self._copy_project_parameters(new_project)

            # Step 4: Copy Klasifikasi
            self._copy_klasifikasi(new_project)

            # Step 5: Copy SubKlasifikasi
            self._copy_subklasifikasi(new_project)

            # Step 6: Copy Pekerjaan
            self._copy_pekerjaan(new_project)

            # Step 7: Copy VolumePekerjaan
            self._copy_volume_pekerjaan(new_project)

            # Step 8: Copy HargaItem
            self._copy_harga_item(new_project)

            # Step 9: Copy AhspTemplate (using existing model)
            self._copy_ahsp_template(new_project)

            # Step 10: Copy RincianAhsp (using DetailAHSPProject model)
            self._copy_rincian_ahsp(new_project)

            # Step 11: Copy Tahapan (if copy_jadwal=True)
            if copy_jadwal:
                self._copy_tahapan(new_project)

                # Step 12: Copy JadwalPekerjaan (if copy_jadwal=True)
                self._copy_jadwal_pekerjaan(new_project)

            # Check if any items were skipped and generate warnings
            if any(self.skipped_items.values()):
                skipped_summary = {k: len(v) for k, v in self.skipped_items.items() if v}
                logger.warning(
                    f"Some items were skipped during copy",
                    extra={
                        'source_project_id': self.source.id,
                        'new_project_id': new_project.id,
                        'skipped_summary': skipped_summary
                    }
                )

                self.warnings.append({
                    'code': 3005,
                    'message': f"Beberapa data tidak lengkap: {', '.join([f'{k}: {v}' for k, v in skipped_summary.items()])}",
                    'details': skipped_summary
                })

            # Log success
            stats = self.get_stats()
            logger.info(
                f"Deep copy completed successfully",
                extra={
                    'source_project_id': self.source.id,
                    'new_project_id': new_project.id,
                    'new_project_name': new_project.nama,
                    'stats': stats,
                    'warnings_count': len(self.warnings)
                }
            )

            return new_project

        except (IntegrityError, OperationalError, ProgrammingError) as e:
            # Classify database errors
            logger.error(
                f"Database error during copy",
                extra={
                    'source_project_id': self.source.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise classify_database_error(e)

        except (MemoryError, TimeoutError, OSError) as e:
            # Classify system errors
            logger.critical(
                f"System error during copy",
                extra={
                    'source_project_id': self.source.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise classify_system_error(e)

        except (DeepCopyValidationError, DeepCopyBusinessError, DeepCopyDatabaseError, DeepCopySystemError):
            # Re-raise our custom exceptions as-is
            raise

        except Exception as e:
            # Unknown error - log and convert to DeepCopyError
            logger.exception(
                f"Unexpected error during copy",
                extra={
                    'source_project_id': self.source.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )

            from .exceptions import DeepCopyError, USER_MESSAGES
            raise DeepCopyError(
                code=9999,
                message=f"Unknown error during copy: {str(e)}",
                user_message=USER_MESSAGES[9999],
                details={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'source_project_id': self.source.id
                }
            )

    def batch_copy(
        self,
        new_owner,
        base_name,
        count,
        new_tanggal_mulai=None,
        copy_jadwal=True,
        progress_callback=None
    ):
        """
        Copy project multiple times in one operation (FASE 3.2).

        Creates multiple copies with auto-incrementing names.
        Each copy is independent and uses a fresh DeepCopyService instance
        to avoid ID mapping conflicts.

        Args:
            new_owner: User who will own the copied projects
            base_name: Base name for projects (will append " - Copy 1", " - Copy 2", etc.)
            count: Number of copies to create (1-50)
            new_tanggal_mulai: Start date for new projects (optional)
            copy_jadwal: Whether to copy schedule data (default: True)
            progress_callback: Optional callback function(current, total, project_name)

        Returns:
            List of newly created project instances

        Raises:
            ValueError: If count is invalid
            ValidationError: If any validation fails

        Example:
            service = DeepCopyService(source_project)
            projects = service.batch_copy(
                new_owner=request.user,
                base_name="Monthly Project Template",
                count=3,
                copy_jadwal=True
            )
            # Creates:
            #   - "Monthly Project Template - Copy 1"
            #   - "Monthly Project Template - Copy 2"
            #   - "Monthly Project Template - Copy 3"
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        # Validate count
        if not isinstance(count, int) or count < 1:
            raise DjangoValidationError("Count must be a positive integer")
        if count > 50:
            raise DjangoValidationError("Maximum 50 copies allowed in one batch")

        projects = []
        errors = []

        for i in range(1, count + 1):
            # Generate unique name for this copy
            copy_name = f"{base_name} - Copy {i}"

            # Report progress
            if progress_callback:
                progress_callback(i, count, copy_name)

            try:
                # Create fresh service instance for each copy to avoid ID mapping conflicts
                service = DeepCopyService(self.source)

                # Perform the copy
                new_project = service.copy(
                    new_owner=new_owner,
                    new_name=copy_name,
                    new_tanggal_mulai=new_tanggal_mulai,
                    copy_jadwal=copy_jadwal
                )

                projects.append(new_project)

            except Exception as e:
                # Record error but continue with remaining copies
                error_msg = f"Failed to create copy {i} '{copy_name}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # If all copies failed, raise an error
        if len(projects) == 0:
            raise DjangoValidationError(
                f"All {count} copies failed. Errors: {'; '.join(errors)}"
            )

        # If some copies failed, log warning
        if errors:
            logger.warning(
                f"Batch copy completed with {len(projects)}/{count} successes. "
                f"Errors: {'; '.join(errors)}"
            )

        return projects

    def _copy_project(
        self,
        new_owner,
        new_name,
        new_tanggal_mulai
    ):
        """
        Step 1: Copy the Project instance.

        Args:
            new_owner: User who will own the copied project
            new_name: Name for the new project
            new_tanggal_mulai: Start date for new project

        Returns:
            The newly created project instance
        """
        from dashboard.models import Project

        old_id = self.source.id

        # Create new project instance with required fields
        new_project = Project(
            owner=new_owner,
            nama=new_name,
            sumber_dana=self.source.sumber_dana,
            lokasi_project=self.source.lokasi_project,
            nama_client=self.source.nama_client,
            anggaran_owner=self.source.anggaran_owner,
            tanggal_mulai=new_tanggal_mulai or self.source.tanggal_mulai,
            is_active=self.source.is_active,
        )

        # Copy optional fields if they exist
        if hasattr(self.source, 'durasi_hari') and self.source.durasi_hari:
            new_project.durasi_hari = self.source.durasi_hari
        if hasattr(self.source, 'deskripsi') and self.source.deskripsi:
            new_project.deskripsi = self.source.deskripsi
        if hasattr(self.source, 'kategori') and self.source.kategori:
            new_project.kategori = self.source.kategori

        # Copy additional optional fields
        optional_fields = [
            'ket_project1', 'ket_project2', 'jabatan_client', 'instansi_client',
            'nama_kontraktor', 'instansi_kontraktor', 'nama_konsultan_perencana',
            'instansi_konsultan_perencana', 'nama_konsultan_pengawas',
            'instansi_konsultan_pengawas'
        ]
        for field in optional_fields:
            if hasattr(self.source, field):
                value = getattr(self.source, field)
                if value:
                    setattr(new_project, field, value)

        new_project.save()

        # Map IDs
        self.mappings['project'][old_id] = new_project.id

        return new_project

    def _copy_project_pricing(self, new_project):
        """
        Step 2: Copy ProjectPricing (OneToOne with Project).

        Args:
            new_project: The newly created project
        """
        try:
            old_pricing = ProjectPricing.objects.get(project=self.source)
            old_id = old_pricing.id

            new_pricing = ProjectPricing(
                project=new_project,
                ppn_percent=old_pricing.ppn_percent,
                markup_percent=old_pricing.markup_percent,
                rounding_base=old_pricing.rounding_base,
            )
            new_pricing.save()

            self.mappings['pricing'][old_id] = new_pricing.id

        except ProjectPricing.DoesNotExist:
            # If no pricing exists, skip
            pass

    def _copy_project_parameters(self, new_project):
        """
        Step 3: Copy ProjectParameter instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        parameters = ProjectParameter.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []
        for old_param in parameters:
            new_param = ProjectParameter(
                project=new_project,
                name=old_param.name,
                value=old_param.value,
                label=old_param.label,
                unit=old_param.unit,
                description=old_param.description,
            )
            items_to_create.append((old_param.id, new_param))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            ProjectParameter,
            items_to_create,
            'parameter',
            batch_size=500
        )

        self.stats['parameter_copied'] = len(created)

    def _copy_klasifikasi(self, new_project):
        """
        Step 4: Copy Klasifikasi instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        klasifikasi_list = Klasifikasi.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []
        for old_klas in klasifikasi_list:
            new_klas = Klasifikasi(
                project=new_project,
                name=old_klas.name,
                ordering_index=old_klas.ordering_index,  # Preserve ordering
            )
            items_to_create.append((old_klas.id, new_klas))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            Klasifikasi,
            items_to_create,
            'klasifikasi',
            batch_size=500
        )

        self.stats['klasifikasi_copied'] = len(created)

    def _copy_subklasifikasi(self, new_project):
        """
        Step 5: Copy SubKlasifikasi instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        subklas_list = SubKlasifikasi.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_subklas in subklas_list:
            old_id = old_subklas.id
            old_klasifikasi_id = old_subklas.klasifikasi_id

            # Remap FK
            new_klasifikasi_id = self.mappings['klasifikasi'].get(old_klasifikasi_id)

            if new_klasifikasi_id:
                new_subklas = SubKlasifikasi(
                    project=new_project,
                    klasifikasi_id=new_klasifikasi_id,
                    name=old_subklas.name,
                    ordering_index=old_subklas.ordering_index,  # Preserve ordering
                )
                items_to_create.append((old_id, new_subklas))
            else:
                # Track skipped item - parent Klasifikasi not found or not copied
                skipped_item = {
                    'id': old_id,
                    'name': old_subklas.name,
                    'reason': 'Parent Klasifikasi not found or not copied',
                    'missing_parent_id': old_klasifikasi_id
                }
                skipped.append(skipped_item)

                logger.warning(
                    f"Skipped SubKlasifikasi during copy - parent missing",
                    extra={
                        'source_project_id': self.source.id,
                        'subklasifikasi_id': old_id,
                        'subklasifikasi_name': old_subklas.name,
                        'missing_klasifikasi_id': old_klasifikasi_id
                    }
                )

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            SubKlasifikasi,
            items_to_create,
            'subklasifikasi',
            batch_size=500
        )

        self.stats['subklasifikasi_copied'] = len(created)
        self.skipped_items['subklasifikasi'].extend(skipped)

    def _copy_pekerjaan(self, new_project):
        """
        Step 6: Copy Pekerjaan instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        pekerjaan_list = Pekerjaan.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_pekerjaan in pekerjaan_list:
            old_id = old_pekerjaan.id
            old_subklas_id = old_pekerjaan.sub_klasifikasi_id

            # Remap FK
            new_subklas_id = self.mappings['subklasifikasi'].get(old_subklas_id)

            if new_subklas_id:
                new_pekerjaan = Pekerjaan(
                    project=new_project,
                    sub_klasifikasi_id=new_subklas_id,
                    snapshot_kode=old_pekerjaan.snapshot_kode,
                    snapshot_uraian=old_pekerjaan.snapshot_uraian,
                    snapshot_satuan=old_pekerjaan.snapshot_satuan,
                    source_type=old_pekerjaan.source_type,
                    ordering_index=old_pekerjaan.ordering_index,
                )
                # Copy optional fields if they exist
                if hasattr(old_pekerjaan, 'ref') and old_pekerjaan.ref:
                    new_pekerjaan.ref = old_pekerjaan.ref
                if hasattr(old_pekerjaan, 'auto_load_rincian'):
                    new_pekerjaan.auto_load_rincian = old_pekerjaan.auto_load_rincian
                if hasattr(old_pekerjaan, 'markup_override_percent') and old_pekerjaan.markup_override_percent:
                    new_pekerjaan.markup_override_percent = old_pekerjaan.markup_override_percent

                items_to_create.append((old_id, new_pekerjaan))
            else:
                # Track skipped item - parent SubKlasifikasi not found or not copied
                skipped_item = {
                    'id': old_id,
                    'kode': old_pekerjaan.snapshot_kode,
                    'uraian': old_pekerjaan.snapshot_uraian,
                    'reason': 'Parent SubKlasifikasi not found or not copied',
                    'missing_parent_id': old_subklas_id
                }
                skipped.append(skipped_item)

                logger.warning(
                    f"Skipped Pekerjaan during copy - parent missing",
                    extra={
                        'source_project_id': self.source.id,
                        'pekerjaan_id': old_id,
                        'pekerjaan_kode': old_pekerjaan.snapshot_kode,
                        'pekerjaan_uraian': old_pekerjaan.snapshot_uraian,
                        'missing_subklasifikasi_id': old_subklas_id
                    }
                )

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            Pekerjaan,
            items_to_create,
            'pekerjaan',
            batch_size=500
        )

        self.stats['pekerjaan_copied'] = len(created)
        self.skipped_items['pekerjaan'].extend(skipped)

    def _copy_volume_pekerjaan(self, new_project):
        """
        Step 7: Copy VolumePekerjaan instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        volume_list = VolumePekerjaan.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_volume in volume_list:
            old_id = old_volume.id
            old_pekerjaan_id = old_volume.pekerjaan_id

            # Remap FK
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)

            if new_pekerjaan_id:
                new_volume = VolumePekerjaan(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                    quantity=old_volume.quantity,
                )
                items_to_create.append((old_id, new_volume))
            else:
                # Track skipped item - parent Pekerjaan not found
                skipped.append({
                    'id': old_id,
                    'reason': 'Parent Pekerjaan not found or not copied',
                    'missing_parent_id': old_pekerjaan_id
                })

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            VolumePekerjaan,
            items_to_create,
            'volume',
            batch_size=500
        )

        self.stats['volume_copied'] = len(created)
        self.skipped_items['volume'].extend(skipped)

    def _copy_harga_item(self, new_project):
        """
        Step 8: Copy HargaItem using HargaItemProject model (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        harga_list = HargaItemProject.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []
        for old_harga in harga_list:
            new_harga = HargaItemProject(
                project=new_project,
                kode_item=old_harga.kode_item,
                kategori=old_harga.kategori,
                uraian=old_harga.uraian,
                satuan=old_harga.satuan,
                harga_satuan=old_harga.harga_satuan,
            )
            items_to_create.append((old_harga.id, new_harga))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            HargaItemProject,
            items_to_create,
            'harga_item',
            batch_size=500
        )

        self.stats['harga_item_copied'] = len(created)

    def _copy_ahsp_template(self, new_project):
        """
        Step 9: Copy DetailAHSPProject instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.
        Critical: This is usually the largest data volume (5-10x pekerjaan count).

        Args:
            new_project: The newly created project
        """
        ahsp_list = DetailAHSPProject.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_ahsp in ahsp_list:
            old_id = old_ahsp.id
            old_pekerjaan_id = old_ahsp.pekerjaan_id
            old_harga_item_id = old_ahsp.harga_item_id

            # Remap FKs
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)
            new_harga_item_id = self.mappings['harga_item'].get(old_harga_item_id)

            if new_pekerjaan_id and new_harga_item_id:
                new_ahsp = DetailAHSPProject(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                    harga_item_id=new_harga_item_id,
                    kategori=old_ahsp.kategori,
                    kode=old_ahsp.kode,
                    uraian=old_ahsp.uraian,
                    satuan=old_ahsp.satuan,
                    koefisien=old_ahsp.koefisien,
                )
                # Copy ref_ahsp_id if exists (for bundle items)
                if hasattr(old_ahsp, 'ref_ahsp_id') and old_ahsp.ref_ahsp_id:
                    new_ahsp.ref_ahsp_id = old_ahsp.ref_ahsp_id

                items_to_create.append((old_id, new_ahsp))
            else:
                # Track skipped item - parent FK not found
                skipped.append({
                    'id': old_id,
                    'kode': old_ahsp.kode,
                    'uraian': old_ahsp.uraian,
                    'reason': 'Parent Pekerjaan or HargaItem not found',
                    'missing_pekerjaan_id': old_pekerjaan_id if not new_pekerjaan_id else None,
                    'missing_harga_item_id': old_harga_item_id if not new_harga_item_id else None
                })

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            DetailAHSPProject,
            items_to_create,
            'ahsp_template',
            batch_size=500
        )

        self.stats['ahsp_template_copied'] = len(created)
        self.skipped_items['ahsp_template'].extend(skipped)

    def _copy_rincian_ahsp(self, new_project):
        """
        Step 10: Copy RincianAhsp instances (placeholder - model structure TBD).

        Args:
            new_project: The newly created project
        """
        # Note: RincianAhsp model structure not clear from existing code
        # This is a placeholder implementation
        # Will need to be updated based on actual model structure
        pass

    def _copy_tahapan(self, new_project):
        """
        Step 11: Copy TahapanPelaksanaan instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        tahapan_list = TahapPelaksanaan.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []

        for old_tahapan in tahapan_list:
            new_tahapan = TahapPelaksanaan(
                project=new_project,
                nama=old_tahapan.nama,
                urutan=old_tahapan.urutan,
            )
            # Copy optional fields if they exist
            if hasattr(old_tahapan, 'deskripsi') and old_tahapan.deskripsi:
                new_tahapan.deskripsi = old_tahapan.deskripsi
            if hasattr(old_tahapan, 'tanggal_mulai'):
                new_tahapan.tanggal_mulai = old_tahapan.tanggal_mulai
            if hasattr(old_tahapan, 'tanggal_selesai'):
                new_tahapan.tanggal_selesai = old_tahapan.tanggal_selesai
            if hasattr(old_tahapan, 'is_auto_generated'):
                new_tahapan.is_auto_generated = old_tahapan.is_auto_generated
            if hasattr(old_tahapan, 'generation_mode') and old_tahapan.generation_mode:
                new_tahapan.generation_mode = old_tahapan.generation_mode

            items_to_create.append((old_tahapan.id, new_tahapan))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            TahapPelaksanaan,
            items_to_create,
            'tahapan',
            batch_size=500
        )

        self.stats['tahapan_copied'] = len(created)

    def _copy_jadwal_pekerjaan(self, new_project):
        """
        Step 12: Copy PekerjaanTahapan instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        # Filter by tahapan__project since PekerjaanTahapan doesn't have project field
        jadwal_list = PekerjaanTahapan.objects.filter(tahapan__project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []

        for old_jadwal in jadwal_list:
            old_id = old_jadwal.id
            old_pekerjaan_id = old_jadwal.pekerjaan_id
            old_tahapan_id = old_jadwal.tahapan_id

            # Remap FKs
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)
            new_tahapan_id = self.mappings['tahapan'].get(old_tahapan_id)

            if new_pekerjaan_id and new_tahapan_id:
                new_jadwal = PekerjaanTahapan(
                    pekerjaan_id=new_pekerjaan_id,
                    tahapan_id=new_tahapan_id,
                    proporsi_volume=old_jadwal.proporsi_volume,
                )
                # Copy optional fields if they exist
                if hasattr(old_jadwal, 'catatan') and old_jadwal.catatan:
                    new_jadwal.catatan = old_jadwal.catatan

                items_to_create.append((old_id, new_jadwal))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            PekerjaanTahapan,
            items_to_create,
            'jadwal',
            batch_size=500
        )

        self.stats['jadwal_copied'] = len(created)

    # =========================================================================
    # PERFORMANCE OPTIMIZATION HELPERS (FASE 4.1)
    # =========================================================================

    def _bulk_create_with_mapping(
        self,
        model_class,
        items_data,
        mapping_key,
        batch_size=500
    ):
        """
        Bulk create items and update ID mappings efficiently.

        This method provides 10-50x performance improvement over individual save()
        calls by using Django's bulk_create() operation.

        Args:
            model_class: Django model class to create instances of
            items_data: List of (old_id, new_instance) tuples
            mapping_key: Key in self.mappings dict to store ID mappings
            batch_size: Number of objects to create per batch (default 500)

        Returns:
            List of created instances with IDs populated

        Example:
            items_to_create = [
                (old_klas.id, Klasifikasi(project=new_project, name="Klas 1")),
                (old_klas2.id, Klasifikasi(project=new_project, name="Klas 2")),
            ]
            created = self._bulk_create_with_mapping(
                Klasifikasi, items_to_create, 'klasifikasi'
            )

        Performance:
            - Before: N queries for N items
            - After: ceil(N/batch_size) queries
            - Example: 1000 items = 1000 queries → 2 queries (500+500)
        """
        if not items_data:
            return []

        # Extract old IDs and new instances
        old_ids = [old_id for old_id, _ in items_data]
        new_instances = [instance for _, instance in items_data]

        # Bulk create all instances
        # Note: bulk_create returns instances with IDs populated (Django 1.10+)
        created = model_class.objects.bulk_create(
            new_instances,
            batch_size=batch_size
        )

        # Update mappings: old_id -> new_id
        for old_id, new_instance in zip(old_ids, created):
            self.mappings[mapping_key][old_id] = new_instance.id

        logger.info(
            f"Bulk created {len(created)} {model_class.__name__} instances",
            extra={
                'model': model_class.__name__,
                'count': len(created),
                'batch_size': batch_size,
                'batches': (len(created) + batch_size - 1) // batch_size
            }
        )

        return created

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_stats(self):
        """
        Get copy statistics.

        Returns:
            Dictionary with counts of copied objects
        """
        return self.stats.copy()

    def get_warnings(self):
        """
        Get warnings collected during copy operation.

        Warnings indicate non-fatal issues that occurred during copy,
        such as skipped items due to missing parent references.

        Returns:
            List of warning dictionaries with code, message, and details
        """
        return self.warnings.copy()

    def get_skipped_items(self):
        """
        Get detailed information about items that were skipped during copy.

        Returns:
            Dictionary mapping item type to list of skipped items with details:
            {
                'subklasifikasi': [{'id': 1, 'name': '...', 'reason': '...'}],
                'pekerjaan': [{'id': 2, 'name': '...', 'reason': '...'}],
                ...
            }
        """
        return {
            k: v.copy() for k, v in self.skipped_items.items() if v
        }
