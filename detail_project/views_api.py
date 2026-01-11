# ================================
# detail_project/views_api.py
# ================================
import json
import csv
import logging
import math
import re
import base64
from io import BytesIO
from typing import Any, Dict, Optional, Set
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  # <-- NEW: Decimal handling
from datetime import datetime

logger = logging.getLogger(__name__)

# FASE 0.3: Monitoring Setup
from .monitoring_helpers import log_optimistic_lock_conflict

from django.http import JsonResponse, HttpRequest, HttpResponse, Http404
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.db.models import Max, F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime
from django.core.cache import cache
from .numeric import parse_any, to_dp_str, quantize_half_up, DECIMAL_SPEC
from .api_helpers import parse_kebutuhan_query_params
from referensi.models import AHSPReferensi
from .models import (
    Project,  # ADDED: Required for export_template_ahsp_json
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    DetailAHSPProject, DetailAHSPExpanded, DetailAHSPAudit,
    HargaItemProject, ItemConversionProfile, VolumeFormulaState, ProjectPricing,  # Added ItemConversionProfile
    ProjectChangeStatus, ProjectParameter,  # Added ProjectParameter for template import
)
from .services import (
    clone_ref_pekerjaan, _upsert_harga_item, compute_rekap_for_project,
    compute_kebutuhan_items, summarize_kebutuhan_rows,
    generate_custom_code, invalidate_rekap_cache, validate_bundle_reference,
    expand_bundle_to_components,  # NEW: Dual storage expansion (Pekerjaan)
    expand_ahsp_bundle_to_components,  # NEW: Dual storage expansion (AHSP)
    cascade_bundle_re_expansion,  # CRITICAL: Re-expand pekerjaan that reference modified one
    detect_orphaned_items,
    delete_orphaned_items,
    snapshot_pekerjaan_details,
    log_audit,
    touch_project_change,
    get_change_tracker,
    _populate_expanded_from_raw,
)

from .export_config import (
    ExportColors,
    ExportFonts,
    ExportLayout,
    get_level_style,
    format_currency,
    format_volume,
)
from .exports import RekapRABExporter, RekapKebutuhanExporter
from .api_helpers import rate_limit

try:
    from referensi.models import RincianReferensi  # type: ignore
except Exception:
    RincianReferensi = None  # type: ignore

# Util

# --- Kategori & Numeric Helpers (global) ---

_KAT_CODE_BY_LABEL = {
    "Tenaga Kerja": "TK", "Tenaga": "TK", "TK": "TK",
    "Bahan": "BHN", "BHN": "BHN",
    "Peralatan": "ALT", "Alat": "ALT", "ALT": "ALT",
    "Lain-lain": "LAIN", "Lainnya": "LAIN", "LAIN": "LAIN",
}


def _normalize_kategori(val):
    if val is None:
        return None
    v = str(val).strip()
    return _KAT_CODE_BY_LABEL.get(v, None)


_UNIT_AUTO_KATEGORI = {
    HargaItemProject.KATEGORI_TK,
    HargaItemProject.KATEGORI_BAHAN,
    HargaItemProject.KATEGORI_ALAT,
}
_UNIT_CODE_PREFIX = "Unit-"
_UNIT_CODE_PATTERN = re.compile(rf"^{_UNIT_CODE_PREFIX}(\d{{4}})$")


def _lock_or_create_change_status(project):
    tracker = (
        ProjectChangeStatus.objects.select_for_update()
        .filter(project=project)
        .first()
    )
    if tracker:
        return tracker
    try:
        return ProjectChangeStatus.objects.create(project=project)
    except IntegrityError:
        return (
            ProjectChangeStatus.objects.select_for_update()
            .get(project=project)
        )


def _scan_unit_code_seed(project):
    max_idx = 0
    codes = (
        HargaItemProject.objects.filter(
            project=project, kode_item__startswith=_UNIT_CODE_PREFIX
        ).values_list("kode_item", flat=True)
    )
    for kode in codes:
        if not kode:
            continue
        match = _UNIT_CODE_PATTERN.match(kode)
        if match:
            idx = int(match.group(1))
            if idx > max_idx:
                max_idx = idx
    return max_idx


def _auto_unit_code(project, state, taken_codes: Set[str]) -> str:
    tracker = state.get("tracker")
    if tracker is None:
        tracker = _lock_or_create_change_status(project)
        state["tracker"] = tracker
        state["seed_synced"] = False
    if not state.get("seed_synced"):
        seed_value = _scan_unit_code_seed(project)
        if seed_value > tracker.unit_code_sequence:
            tracker.unit_code_sequence = seed_value
        state["seed_synced"] = True
    next_value = tracker.unit_code_sequence + 1
    candidate = f"{_UNIT_CODE_PREFIX}{next_value:04d}"
    while candidate in taken_codes:
        next_value += 1
        candidate = f"{_UNIT_CODE_PREFIX}{next_value:04d}"
    tracker.unit_code_sequence = next_value
    state["dirty"] = True
    return candidate


def _commit_unit_code_state(state, *, should_persist: bool):
    tracker = state.get("tracker")
    if tracker and state.get("dirty") and should_persist:
        tracker.save(update_fields=["unit_code_sequence", "updated_at"])


def _src_to_str(val):
    return {
        Pekerjaan.SOURCE_REF: 'ref',
        Pekerjaan.SOURCE_CUSTOM: 'custom',
        Pekerjaan.SOURCE_REF_MOD: 'ref_modified',
    }.get(val, str(val))

def _err(path: str, message: str):
    return {"path": path, "message": message}


def _parse_export_attachments(request: HttpRequest):
    """
    Parse optional base64 image attachments sent via POST for export endpoints.
    
    Supports two formats:
    1. Old format (data_url): {"title": "Gantt Chart", "data_url": "data:image/png;base64,..."}
    2. New format (bytes): {"title": "Kurva S", "bytes": "iVBORw0...", "format": "png"}
    """
    if request.method != "POST":
        return []
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return []

    attachments = []
    for att in payload.get("attachments", []):
        title = att.get("title") or "Lampiran"
        
        # Try new format first (direct bytes)
        raw_bytes = att.get("bytes")
        if raw_bytes and isinstance(raw_bytes, str):
            try:
                blob = base64.b64decode(raw_bytes)
                attachments.append({"title": title, "bytes": blob})
                continue
            except Exception:
                pass
        
        # Fallback to old format (data_url)
        data_url = att.get("data_url") or att.get("dataUrl")
        if not data_url or not isinstance(data_url, str):
            continue
        if "base64," not in data_url:
            continue
        try:
            b64 = data_url.split("base64,", 1)[1]
            blob = base64.b64decode(b64)
            attachments.append({"title": title, "bytes": blob})
        except Exception:
            continue
    return attachments


def _parse_export_parameters(request: HttpRequest):
    """
    Parse export parameters from POST request.

    Expected payload:
    {
        "report_type": "full" | "monthly" | "weekly",
        "mode": "weekly" | "monthly",
        "include_dates": true | false,
        "weeks_per_month": 4,
        "attachments": [...]
    }

    Returns:
        dict: Parsed parameters with defaults
    """
    if request.method != "POST":
        return {
            'report_type': 'full',
            'mode': 'weekly',
            'include_dates': False,
            'weeks_per_month': 4
        }

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return {
            'report_type': 'full',
            'mode': 'weekly',
            'include_dates': False,
            'weeks_per_month': 4
        }

    # Parse with defaults
    report_type = payload.get('report_type', 'full')
    if report_type not in ['full', 'monthly', 'weekly']:
        report_type = 'full'

    mode = payload.get('mode', 'weekly')
    if mode not in ['weekly', 'monthly']:
        mode = 'weekly'

    include_dates = payload.get('include_dates', False)
    weeks_per_month = payload.get('weeks_per_month', 4)

    return {
        'report_type': report_type,
        'mode': mode,
        'include_dates': include_dates,
        'weeks_per_month': weeks_per_month
    }


def _warn(path: str, message: str):
    err = _err(path, message)
    err["severity"] = "warning"
    return err

def _sanitize_text(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    return escape(str(val))

def _owner_or_404(project_id, user):
    from dashboard.models import Project
    qs = Project.objects.filter(id=project_id)
    # Jika model punya field 'owner', wajib milik user yang login.
    if any(f.name == "owner" for f in Project._meta.get_fields()):
        qs = qs.filter(owner=user)
    # Jangan pakai filter is_active di sini agar tidak mengganggu test/seed.
    return get_object_or_404(qs)


def _extract_parameters_from_request(request: HttpRequest) -> dict:
    """
    Extract parameters from request query string or body
    Supports: ?params={"panjang":100,"lebar":50}
    Returns: dict of parameter values
    """
    try:
        # Try query string first
        params_str = request.GET.get('params', '')
        if params_str:
            return json.loads(params_str)
        return {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _get_or_create_pricing(project):
    """
    Defaults used by the *pricing API*:
    - markup_percent: 10.00
    - ppn_percent: 11.00 (if field exists)
    - rounding_base: 10000 (if field exists)
    Note: Rekap perhitungan tetap 0% jika belum ada row (lihat services.compute_rekap_for_project).
    """
    field_names = {f.name for f in ProjectPricing._meta.get_fields()}
    defaults = {"markup_percent": Decimal("10.00")}
    if "ppn_percent" in field_names:
        defaults["ppn_percent"] = Decimal("11.00")
    if "rounding_base" in field_names:
        defaults["rounding_base"] = 10000
    obj, _ = ProjectPricing.objects.get_or_create(project=project, defaults=defaults)
    return obj

def _safe_snap_from_ref(ref_obj, src, ov_ura=None, ov_sat=None):
    """
    Kembalikan tuple (kode, uraian, satuan) yang aman (tidak kosong) dari AHSP referensi.
    - src == ref_modified → hormati override_uraian/satuan bila diisi.
    - fallback bila data referensi kosong (mis. di test/seed).
    """
    rid  = getattr(ref_obj, "id", None)
    kode = getattr(ref_obj, "kode_ahsp", None) or (f"REF-{rid}" if rid is not None else "REF")
    ura  = (
        (ov_ura if (src == Pekerjaan.SOURCE_REF_MOD and ov_ura) else None)
        or getattr(ref_obj, "nama_ahsp", None)
        or (f"AHSP {rid}" if rid is not None else "AHSP")
    )
    sat  = (
        (ov_sat if (src == Pekerjaan.SOURCE_REF_MOD and ov_sat) else None)
        or getattr(ref_obj, "satuan", None)
    )
    return kode, ura, sat

# ---------- View 0: Search AHSP (autocomplete) ----------
@login_required
@require_GET
def api_search_ahsp(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)  # noqa: F841
    q = (request.GET.get("q") or "").strip()
    try:
        limit = int(request.GET.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))

    qs = AHSPReferensi.objects.all()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(kode_ahsp__icontains=q) | Q(nama_ahsp__icontains=q))

    qs = qs.order_by("kode_ahsp")[:limit]
    results = [{
        "id": obj.id,
        "text": f"{obj.kode_ahsp} — {obj.nama_ahsp[:80]}",
        "kode_ahsp": obj.kode_ahsp,
        "nama_ahsp": obj.nama_ahsp,
        "satuan": obj.satuan,
        "sumber": obj.sumber,  # Include source for LAIN segment display
    } for obj in qs]

    return JsonResponse({"ok": True, "results": results, "total": len(results)})

# ---------- View 1: SAVE (full-create) ----------
@login_required
@require_POST
@rate_limit(category='write')
@transaction.atomic
def api_save_list_pekerjaan(request: HttpRequest, project_id: int):
    """
    Full save (create-all). Hati-hati: panggilan berulang bisa menduplikasi data.
    Disarankan gunakan /upsert/. Endpoint ini tetap disediakan untuk kebutuhan reset penuh.
    """
    project = _owner_or_404(project_id, request.user)
    from dashboard.models import Project as _P
    _P.objects.select_for_update().filter(id=project.id).first()

    # 1) Parse JSON
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    klas_list = payload.get('klasifikasi') or []
    if not isinstance(klas_list, list):
        return JsonResponse({"ok": False, "errors": [_err("klasifikasi", "Harus berupa list")]}, status=400)

    VALID_SRC = {
        'ref': Pekerjaan.SOURCE_REF,
        'custom': Pekerjaan.SOURCE_CUSTOM,
        'ref_modified': Pekerjaan.SOURCE_REF_MOD,
    }

    id_map = {"klasifikasi": {}, "sub": {}, "pekerjaan": {}}
    errors = []

    k_counter = 0
    try:
        for ki, k in enumerate(klas_list):
            k_counter += 1
            k_name = ((k.get('name') or k.get('nama')) or f"Klasifikasi {k_counter}").strip()
            k_order = int(k.get('ordering_index') or k_counter)

            # Klasifikasi
            try:
                k_obj = Klasifikasi.objects.create(project=project, name=k_name, ordering_index=k_order)
            except IntegrityError as e:
                errors.append(_err(f"klasifikasi[{ki}]", f"Gagal membuat klasifikasi: {e}"))
                continue
            id_map['klasifikasi'][k.get('temp_id') or f"k{ki}"] = k_obj.id

            # Sub
            sub_list = (k.get('sub') or k.get('subs') or [])
            if not isinstance(sub_list, list):
                errors.append(_err(f"klasifikasi[{ki}].sub", "Harus berupa list"))
                continue

            for si, s in enumerate(sub_list):
                s_name = ((s.get('name') or s.get('nama')) or f"{ki+1}.{si+1}").strip()
                s_order = int(s.get('ordering_index') or (si+1))
                try:
                    s_obj = SubKlasifikasi.objects.create(project=project, klasifikasi=k_obj, name=s_name, ordering_index=s_order)
                except IntegrityError as e:
                    errors.append(_err(f"klasifikasi[{ki}].sub[{si}]", f"Gagal membuat sub: {e}"))
                    continue
                id_map['sub'][s.get('temp_id') or f"s{ki}_{si}"] = s_obj.id

                # Pekerjaan
                pekerjaan_list = (s.get('pekerjaan') or s.get('jobs') or [])
                if not isinstance(pekerjaan_list, list):
                    errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan", "Harus berupa list"))
                    continue

                for pi, p in enumerate(pekerjaan_list):
                    src_in = p.get('source_type')
                    src = VALID_SRC.get(src_in, src_in)
                    if src not in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_CUSTOM, Pekerjaan.SOURCE_REF_MOD]:
                        errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].source_type", "Nilai tidak valid"))
                        continue

                    order = int(p.get('ordering_index') or (pi + 1))

                    if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                        ref_id = p.get('ref_id')
                        if not ref_id:
                            errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id", "Wajib untuk source=ref/ref_modified"))
                            continue
                        try:
                            ref_obj = AHSPReferensi.objects.get(id=ref_id)
                        except AHSPReferensi.DoesNotExist:
                            errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id", f"Referensi #{ref_id} tidak ditemukan"))
                            continue
                        try:
                            # override hanya dipakai untuk ref_modified (optional)
                            ov_ura = (p.get('snapshot_uraian') or '').strip() or None
                            ov_sat = (p.get('snapshot_satuan') or '').strip() or None
                            pkj = clone_ref_pekerjaan(
                                project, s_obj, ref_obj, src,
                                ordering_index=order, auto_load_rincian=True,
                                override_uraian=ov_ura if src == Pekerjaan.SOURCE_REF_MOD else None,
                                override_satuan=ov_sat if src == Pekerjaan.SOURCE_REF_MOD else None,
                            )
                            # Safety: pastikan FK ref terisi (beberapa versi clone_ref_pekerjaan bisa belum set .ref)
                            try:
                                if getattr(pkj, "ref_id", None) is None:
                                    pkj.ref = ref_obj
                                    pkj.save(update_fields=["ref"])
                            except Exception:
                                pass

                            # >>> NEW: fallback kalau clone tidak membuat apa-apa
                            if not pkj:
                                _k, _u, _s = _safe_snap_from_ref(ref_obj, src, ov_ura, ov_sat)
                                pkj = Pekerjaan.objects.create(
                                    project=project,
                                    sub_klasifikasi=s_obj,
                                    source_type=src,
                                    ref=ref_obj,
                                    snapshot_kode=_k,
                                    snapshot_uraian=_u,
                                    snapshot_satuan=_s,
                                    ordering_index=order,
                                )

                            if not pkj:
                                raise ValueError("clone_ref_pekerjaan mengembalikan None")
                        except Exception as e:
                            errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}]", f"Gagal clone referensi: {type(e).__name__}: {e}"))
                            continue
                    else:
                        uraian = (p.get('snapshot_uraian') or '').strip()
                        satuan = (p.get('snapshot_satuan') or None)
                        if not uraian:
                            errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian", "Wajib diisi untuk custom"))
                            continue
                        try:
                            pkj = Pekerjaan.objects.create(
                                project=project, sub_klasifikasi=s_obj, source_type=src,
                                snapshot_kode=generate_custom_code(project),
                                snapshot_uraian=uraian, snapshot_satuan=satuan, ordering_index=order,
                            )
                        except IntegrityError as e:
                            errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}]", f"Gagal membuat pekerjaan custom: {e}"))
                            continue

                    id_map['pekerjaan'][p.get('temp_id') or f"p{ki}_{si}_{pi}"] = pkj.id

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse(
            {"ok": False, "errors": [_err("$", f"Server error: {type(e).__name__}: {e}")], "id_map": id_map},
            status=500
        )

    if errors:
        status_code = 207 if any(id_map.values()) else 400
        return JsonResponse({"ok": status_code == 200, "errors": errors, "id_map": id_map}, status=status_code)

    summary = {
        "klasifikasi": len(id_map['klasifikasi']),
        "sub": len(id_map['sub']),
        "pekerjaan": len(id_map['pekerjaan']),
    }

    # CACHE FIX: Invalidate cache AFTER transaction commits
    transaction.on_commit(lambda: invalidate_rekap_cache(project))

    return JsonResponse({"ok": True, "id_map": id_map, "summary": summary})

# helper untuk normalisasi source_type
def _str_to_src(s):
    m = {
        'ref': Pekerjaan.SOURCE_REF,
        'custom': Pekerjaan.SOURCE_CUSTOM,
        'ref_modified': Pekerjaan.SOURCE_REF_MOD,
    }
    return m.get(s, s)

# ---------- View 1: TREE ----------
@login_required
@require_GET
def api_get_list_pekerjaan_tree(request: HttpRequest, project_id: int):
    """
    Kembalikan struktur Klasifikasi → Sub → Pekerjaan yang sudah tersimpan.

    Query params:
    - search (q): Filter pekerjaan by kode AHSP, referensi AHSP nama, atau uraian pekerjaan
    """
    project = _owner_or_404(project_id, request.user)

    # Get search query from request
    search_query = request.GET.get('search') or request.GET.get('q') or ''
    search_query = search_query.strip()

    use_cache = not search_query
    cache_key = None
    signature = None
    if use_cache:
        def _fmt_ts(val):
            return val.isoformat() if val else "0"

        signature = (
            _fmt_ts(Klasifikasi.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
            _fmt_ts(SubKlasifikasi.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
            _fmt_ts(Pekerjaan.objects.filter(project=project).aggregate(last=Max('updated_at'))['last']),
        )
        cache_key = f"list_pekerjaan_tree:{project.id}:v1"
        cached = cache.get(cache_key)
        if cached and cached.get("sig") == signature:
            return JsonResponse(cached.get("data", {"ok": True, "klasifikasi": []}))

    k_qs = (
        Klasifikasi.objects.filter(project=project)
        .order_by('ordering_index', 'id')
        .values('id', 'name', 'ordering_index')
    )
    s_qs = (
        SubKlasifikasi.objects.filter(project=project)
        .order_by('ordering_index', 'id')
        .values('id', 'klasifikasi_id', 'name', 'ordering_index')
    )
    p_qs = (
        Pekerjaan.objects.filter(project=project)
        .order_by('ordering_index', 'id')
        .values(
            'id',
            'sub_klasifikasi_id',
            'source_type',
            'ordering_index',
            'snapshot_kode',
            'snapshot_uraian',
            'snapshot_satuan',
            'ref_id',
            'budgeted_cost',
        )
    )

    # Apply search filter if provided
    if search_query:
        from django.db.models import Q
        # Search in: snapshot_kode, snapshot_uraian, and ref AHSP (kode_ahsp, nama_ahsp)
        p_qs = p_qs.filter(
            Q(snapshot_kode__icontains=search_query) |
            Q(snapshot_uraian__icontains=search_query) |
            Q(ref__kode_ahsp__icontains=search_query) |
            Q(ref__nama_ahsp__icontains=search_query)
        )

        # If search is active, we need to filter klasifikasi and subklasifikasi
        # to only show those that have matching pekerjaan
        filtered_pkj_ids = list(p_qs.values_list('id', flat=True))
        if filtered_pkj_ids:
            filtered_sub_ids = set(p_qs.values_list('sub_klasifikasi_id', flat=True))
            s_qs = s_qs.filter(id__in=filtered_sub_ids)

            filtered_klas_ids = set(s_qs.values_list('klasifikasi_id', flat=True))
            k_qs = k_qs.filter(id__in=filtered_klas_ids)
        else:
            # No matching pekerjaan found - return empty structure without echoing query
            return JsonResponse({"ok": True, "klasifikasi": [], "match_count": 0, "search_active": True})

    subs_by_klas = {}
    for s in s_qs:
        subs_by_klas.setdefault(s["klasifikasi_id"], []).append(s)

    pkj_by_sub = {}
    for p in p_qs:
        pkj_by_sub.setdefault(p["sub_klasifikasi_id"], []).append(p)

    data = []
    total_pekerjaan_count = 0
    for k in k_qs:
        k_obj = {
            "id": k["id"],
            "name": _sanitize_text(k.get("name")),
            "ordering_index": k.get("ordering_index"),
            "sub": []
        }
        for s in subs_by_klas.get(k["id"], []):
            s_obj = {
                "id": s["id"],
                "name": _sanitize_text(s.get("name")),
                "ordering_index": s.get("ordering_index"),
                "pekerjaan": []
            }
            for p in pkj_by_sub.get(s["id"], []):
                s_obj["pekerjaan"].append({
                    "id": p["id"],
                    "source_type": _src_to_str(p.get("source_type")),
                    "ordering_index": p.get("ordering_index"),
                    "snapshot_kode": _sanitize_text(p.get("snapshot_kode")),
                    "snapshot_uraian": _sanitize_text(p.get("snapshot_uraian")),
                    "snapshot_satuan": _sanitize_text(p.get("snapshot_satuan")),
                    "ref_id": p.get("ref_id"),
                    "budgeted_cost": float(p.get("budgeted_cost") or 0),
                })
                total_pekerjaan_count += 1
            k_obj["sub"].append(s_obj)
        data.append(k_obj)

    response_data = {
        "ok": True,
        "klasifikasi": data
    }

    # Add search metadata if search was performed (without echoing raw query)
    if search_query:
        response_data["search_active"] = True
        response_data["match_count"] = total_pekerjaan_count

    if use_cache and cache_key:
        cache.set(cache_key, {"sig": signature, "data": response_data}, 300)

    return JsonResponse(response_data)



# ---------- View 1: UPSERT ----------
@login_required
@require_POST
@transaction.atomic
def api_upsert_list_pekerjaan(request: HttpRequest, project_id: int):
    """
    Upsert struktur Klasifikasi → SubKlasifikasi → Pekerjaan.

    - Klasifikasi upsert-by-natural-key: (project, ordering_index)
    - SubKlasifikasi upsert-by-natural-key: (project, klasifikasi, ordering_index)
    - Pekerjaan upsert-by-natural-key: (project, ordering_index)
      * Khusus REF/REF_MOD saat REUSE: clone ke TEMP dgn temp_order aman, adopsi ke record reuse,
        pindahkan seluruh Detail dari TEMP ke record reuse, lalu hapus TEMP (hindari UniqueViolation).
    - Entitas yang tidak ada di payload akan dihapus (idempotent).
    """
    from django.db.models import Max
    from referensi.models import AHSPReferensi

    def _safe_int(x, default):
        try:
            return int(x)
        except Exception:
            return default

    project = _owner_or_404(project_id, request.user)
    from dashboard.models import Project as _P
    _P.objects.select_for_update().filter(id=project.id).first()

    # Parse payload
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({
            "ok": False,
            "success": False,
            "message": "Payload JSON tidak valid",
            "errors": [_err("$", "Payload JSON tidak valid")]
        }, status=400)

    if "klasifikasi" not in payload:
        return JsonResponse({
            "ok": False,
            "success": False,
            "message": "Field 'klasifikasi' wajib disertakan sebagai list",
            "errors": [_err("klasifikasi", "Wajib disertakan dan berupa list")]
        }, status=400)
    klas_list = payload.get("klasifikasi")
    if not isinstance(klas_list, list):
        return JsonResponse({
            "ok": False,
            "success": False,
            "message": "Field 'klasifikasi' harus berupa list",
            "errors": [_err("klasifikasi", "Harus list")]
        }, status=400)

    # ============================
    # PRE-FLIGHT VALIDATION
    # ============================
    pre_errors = []
    all_ref_ids = set()
    ref_locs = []  # simpan path + nilai untuk marking "not found"

    for ki, k in enumerate(klas_list):
        sub_list = (k.get("sub") or k.get("subs") or [])
        if not isinstance(sub_list, list):
            pre_errors.append(_err(f"klasifikasi[{ki}].sub", "Harus list"))
            continue

        for si, s in enumerate(sub_list):
            pekerjaan_list = (s.get("pekerjaan") or s.get("jobs") or [])
            if not isinstance(pekerjaan_list, list):
                pre_errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan", "Harus list"))
                continue

            for pi, p in enumerate(pekerjaan_list):
                src = _str_to_src(p.get("source_type"))
                p_id = p.get("id")  # jika ada, berarti baris existing (boleh tanpa ref_id bila tidak berubah)

                if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                    rid_raw = p.get("ref_id", None)

                    if rid_raw is None:
                        # Tanpa ref_id:
                        #  - kalau baris existing (punya id) → DIIZINKAN (artinya tidak ganti referensi)
                        #  - kalau baris baru (tanpa id)     → ERROR (ref_id tetap wajib)
                        if not p_id:
                            pre_errors.append(_err(
                                f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                                "Wajib untuk source=ref/ref_modified (baris baru)"
                            ))
                        # kalau p_id ada, tidak menambahkan ke all_ref_ids → tidak ada cek existensi (karena tak mengubah ref)
                        continue

                    # Ada ref_id → harus integer & akan dicek eksistensinya (ini kasus ganti ref atau baris baru lengkap)
                    try:
                        rid = int(rid_raw)
                    except (TypeError, ValueError):
                        pre_errors.append(_err(
                            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                            "Harus integer"
                        ))
                        continue

                    all_ref_ids.add(rid)
                    ref_locs.append((f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id", rid))


                elif src == Pekerjaan.SOURCE_CUSTOM:
                    if not (p.get("snapshot_uraian") or "").strip():
                        pre_errors.append(_err(
                            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian",
                            "Wajib untuk custom"
                        ))

                else:
                    pre_errors.append(_err(
                        f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].source_type",
                        "Nilai tidak valid"
                    ))

    # validasi eksistensi ref_id (bulk)
    if all_ref_ids:
        found = set(AHSPReferensi.objects.filter(id__in=all_ref_ids).values_list("id", flat=True))
        missing = all_ref_ids - found
        for path, rid in ref_locs:
            if rid in missing:
                pre_errors.append(_err(path, f"Referensi #{rid} tidak ditemukan"))

    source_change_state = {
        "reload_jobs": set(),
        "volume_reset_jobs": set(),
    }

    if pre_errors:
        return JsonResponse({
            "ok": False,
            "success": False,
            "message": f"{len(pre_errors)} kesalahan validasi ditemukan.",
            "errors": pre_errors
        }, status=400)

    # ============================
    # PROSES UPSERT
    # ============================
    errors = []
    keep_k = set()
    keep_all_p = set()  # global keep untuk semua pekerjaan di payload
    assigned_orders: Set[int] = set()

    existing_k = {k.id: k for k in Klasifikasi.objects.filter(project=project)}
    existing_s = {s.id: s for s in SubKlasifikasi.objects.filter(project=project)}
    pekerjaan_queryset = list(Pekerjaan.objects.filter(project=project).order_by('id'))
    existing_p = {p.id: p for p in pekerjaan_queryset}
    reuse_pool: Dict[int, list[Pekerjaan]] = {}
    for pobj in pekerjaan_queryset:
        reuse_pool.setdefault(pobj.ordering_index, []).append(pobj)

    # BUG FIX #3 (REVISED): Set temporary high ordering_index to avoid UniqueViolation
    # When deleting/reordering pekerjaan, we need to temporarily free up ordering_index values
    # to prevent constraint violations during the update process.
    # Cannot use negative values because ordering_index is PositiveIntegerField.
    # Strategy: Temporarily shift all to very high values (1,000,000+), then assign final values.
    temp_offset = 1_000_000
    for idx, pobj in enumerate(pekerjaan_queryset, start=1):
        pobj.ordering_index = temp_offset + idx  # Set to high temporary value (1000001, 1000002, ...)
        pobj.save(update_fields=['ordering_index'])

    def _get_or_reuse_pekerjaan_for_order(order: int):
        pool = reuse_pool.get(order)
        if pool:
            pobj = pool.pop(0)
            if not pool:
                reuse_pool.pop(order, None)
            return pobj
        return None

    def _allocate_order(order: int) -> int:
        actual = max(1, int(order))
        while actual in assigned_orders:
            actual += 1
        assigned_orders.add(actual)
        return actual

    def _get_safe_temp_order():
        max_order = Pekerjaan.objects.filter(project=project).aggregate(Max("ordering_index"))["ordering_index__max"] or 0
        return max_order + 1_000_000

    def _reset_pekerjaan_related_data(pobj):
        """
        Reset semua data terkait pekerjaan saat pekerjaan dimodifikasi (source_type atau ref_id berubah).

        Cascade reset:
        - DetailAHSPProject: hapus semua detail lama
        - VolumePekerjaan: reset volume jadi NULL/0
        - PekerjaanTahapan: hapus dari semua tahapan (jadwal)
        - VolumeFormulaState: hapus formula state
        - detail_ready flag: set ke False
        """
        from .models import DetailAHSPProject, VolumePekerjaan, PekerjaanTahapan, VolumeFormulaState

        # 1. Hapus semua DetailAHSPProject (template AHSP)
        DetailAHSPProject.objects.filter(project=project, pekerjaan=pobj).delete()

        # 2. Hapus VolumePekerjaan (quantity field is NOT NULL, so delete instead of update)
        VolumePekerjaan.objects.filter(project=project, pekerjaan=pobj).delete()

        # 3. Hapus dari semua tahapan (jadwal)
        PekerjaanTahapan.objects.filter(pekerjaan=pobj).delete()

        # 4. Hapus volume formula state
        VolumeFormulaState.objects.filter(project=project, pekerjaan=pobj).delete()

        # 5. Set detail_ready flag ke False
        pobj.detail_ready = False
        pobj.save(update_fields=['detail_ready'])

        logger.info(
            f"Reset all related data for pekerjaan {pobj.id} (kode: {pobj.snapshot_kode})",
            extra={'project_id': project.id, 'pekerjaan_id': pobj.id}
        )
        source_change_state["volume_reset_jobs"].add(pobj.id)

    def _adopt_tmp_into(pobj, tmp, s_obj, order: int):
        """
        Salin snapshot tmp → pobj, pindahkan seluruh detail tmp → pobj, lalu hapus tmp.

        IMPORTANT: Karena pekerjaan berubah (source_type atau ref_id), reset semua data terkait:
        - Volume, jadwal, formula state akan di-reset
        - Detail AHSP akan diganti dengan detail dari referensi baru
        """
        from .models import DetailAHSPProject

        # CRITICAL: Reset semua data terkait sebelum adopt new data
        _reset_pekerjaan_related_data(pobj)

        # Copy snapshot from tmp to pobj
        pobj.sub_klasifikasi = s_obj
        pobj.source_type = tmp.source_type
        try:
            pobj.ref_id = tmp.ref_id   # penting: FK ikut dipindah agar ref_id tampil di /tree
        except Exception:
            pass
        pobj.snapshot_kode = tmp.snapshot_kode
        pobj.snapshot_uraian = tmp.snapshot_uraian
        pobj.snapshot_satuan = tmp.snapshot_satuan
        pobj.ordering_index = final_order
        pobj.save(update_fields=[
            "sub_klasifikasi", "source_type", "ref",
            "snapshot_kode", "snapshot_uraian", "snapshot_satuan", "ordering_index"
        ])

        # Move DetailAHSPProject from tmp to pobj
        # (No dedup needed since we already deleted all old details)
        DetailAHSPProject.objects.filter(project=project, pekerjaan=tmp).update(pekerjaan=pobj)

        # Dual storage: rebuild expanded komponen supaya Harga/Rincian tetap sinkron
        _populate_expanded_from_raw(project, pobj)

        source_change_state["reload_jobs"].add(pobj.id)

        tmp.delete()

    def _format_source_label(src: str, ref_id: Optional[int]) -> str:
        label_map = {
            Pekerjaan.SOURCE_REF: "REF",
            Pekerjaan.SOURCE_REF_MOD: "REF_MOD",
            Pekerjaan.SOURCE_CUSTOM: "CUSTOM",
        }
        base = label_map.get(src, src or "UNKNOWN")
        if src in (Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD) and ref_id:
            return f"{base}#{ref_id}"
        return base

    def _log_source_change_audit(
        pobj: Pekerjaan,
        *,
        old_source: str,
        new_source: str,
        old_ref_id: Optional[int],
        new_ref_id: Optional[int],
    ):
        if old_source == new_source and (old_ref_id or None) == (new_ref_id or None):
            return
        summary = (
            f"Source change: "
            f"{_format_source_label(old_source, old_ref_id)} → {_format_source_label(new_source, new_ref_id)}"
        )
        try:
            log_audit(
                project,
                pobj,
                DetailAHSPAudit.ACTION_UPDATE,
                triggered_by="user",
                user=request.user,
                change_summary=summary,
            )
        except Exception:
            logger.exception(
                "[AUDIT] Failed to log source change for pekerjaan %s",
                getattr(pobj, "id", None),
            )

    # === Loop utama ===
    for ki, k in enumerate(klas_list):
        k_id = k.get("id")
        k_name = ((k.get("name") or k.get("nama")) or f"Klasifikasi {ki+1}").strip()
        k_order = _safe_int(k.get("ordering_index"), ki + 1)

        # Klasifikasi
        if k_id and k_id in existing_k:
            k_obj = existing_k[k_id]
            k_obj.name = k_name
            k_obj.ordering_index = k_order
            k_obj.save(update_fields=["name", "ordering_index"])
        else:
            k_obj = Klasifikasi.objects.filter(project=project, ordering_index=k_order).first()
            if k_obj:
                if k_obj.name != k_name:
                    k_obj.name = k_name
                    k_obj.save(update_fields=["name"])
            else:
                k_obj = Klasifikasi.objects.create(project=project, name=k_name, ordering_index=k_order)
        keep_k.add(k_obj.id)

        keep_s = set()
        sub_list = (k.get("sub") or k.get("subs") or [])
        if not isinstance(sub_list, list):
            errors.append(_err(f"klasifikasi[{ki}].sub", "Harus list"))
            continue

        for si, s in enumerate(sub_list):
            s_id = s.get("id")
            s_name = ((s.get("name") or s.get("nama")) or f"{k_order}.{si+1}").strip()
            s_order = _safe_int(s.get("ordering_index"), si + 1)

            # SubKlasifikasi
            if s_id and s_id in existing_s and existing_s[s_id].klasifikasi_id == k_obj.id:
                s_obj = existing_s[s_id]
                s_obj.name = s_name
                s_obj.ordering_index = s_order
                s_obj.klasifikasi = k_obj
                s_obj.save(update_fields=["name", "ordering_index", "klasifikasi"])
            else:
                s_obj = SubKlasifikasi.objects.filter(project=project, klasifikasi=k_obj, ordering_index=s_order).first()
                if s_obj:
                    if s_obj.name != s_name:
                        s_obj.name = s_name
                        s_obj.save(update_fields=["name"])
                else:
                    s_obj = SubKlasifikasi.objects.create(
                        project=project, klasifikasi=k_obj, name=s_name, ordering_index=s_order
                    )
            keep_s.add(s_obj.id)

            pekerjaan_list = (s.get("pekerjaan") or s.get("jobs") or [])
            if not isinstance(pekerjaan_list, list):
                errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan", "Harus list"))
                continue

            for pi, p in enumerate(pekerjaan_list):
                src_in = p.get("source_type")
                src = _str_to_src(src_in)
                if src not in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_CUSTOM, Pekerjaan.SOURCE_REF_MOD]:
                    errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].source_type", "Nilai tidak valid"))
                    continue

                order_requested = _safe_int(p.get("ordering_index"), pi + 1)
                final_order = _allocate_order(order_requested)
                p_id = p.get("id")

                ov_ura = (p.get("snapshot_uraian") or "").strip() or None
                ov_sat = (p.get("snapshot_satuan") or "").strip() or None

                if p_id and p_id in existing_p and existing_p[p_id].project_id == project.id:
                    # ============ UPDATE EXISTING ============
                    pobj = existing_p[p_id]

                    # CRITICAL FIX: Add to keep list IMMEDIATELY to prevent deletion
                    # even if validation fails later (before any 'continue' statements)
                    keep_all_p.add(pobj.id)

                    replace = False
                    new_ref_id = p.get("ref_id")
                    old_source_type = pobj.source_type
                    old_ref_id = getattr(pobj, "ref_id", None)
                    change_was_applied = False

                    # Ganti tipe sumber → pasti replace
                    if pobj.source_type != src:
                        # Special case: ganti ke REF/REF_MOD tapi tidak ada ref_id
                        if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and new_ref_id is None:
                            errors.append(_err(
                                f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                                "Wajib diisi saat mengganti source type ke ref/ref_modified"
                            ))
                            continue
                        replace = True
                    # Untuk REF/REF_MOD: hanya replace jika ref_id benar-benar BERBEDA
                    elif src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                        if new_ref_id is not None:
                            try:
                                replace = (int(new_ref_id) != getattr(pobj, "ref_id", None))
                            except (TypeError, ValueError):
                                # Payload anomali: fail-safe ke replace agar state konsisten
                                replace = True
                        else:
                            # Tidak ada ref_id baru → tidak dianggap replace
                            replace = False

                    if replace:
                        try:
                            if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                                # sudah dipastikan valid & exist pada preflight
                                rid = int(new_ref_id)
                                ref_obj = AHSPReferensi.objects.get(id=rid)
                                temp_order = _get_safe_temp_order()
                                tmp = clone_ref_pekerjaan(
                                    project, s_obj, ref_obj, src,
                                    ordering_index=temp_order, auto_load_rincian=True,
                                    override_uraian=ov_ura if src == Pekerjaan.SOURCE_REF_MOD else None,
                                    override_satuan=ov_sat if src == Pekerjaan.SOURCE_REF_MOD else None,
                                )

                                # Fallback bila clone mengembalikan None
                                if not tmp:
                                    _k, _u, _s = _safe_snap_from_ref(ref_obj, src, ov_ura, ov_sat)
                                    tmp = Pekerjaan.objects.create(
                                        project=project, sub_klasifikasi=s_obj, source_type=src, ref=ref_obj,
                                        snapshot_kode=_k,
                                        snapshot_uraian=_u,
                                        snapshot_satuan=_s,
                                        ordering_index=temp_order,
                                    )
                                _adopt_tmp_into(pobj, tmp, s_obj, final_order)
                                change_was_applied = True
                            else:
                                # ke CUSTOM: update in-place (ID tetap) + bersihkan FK ref
                                # CRITICAL: Reset related data karena source_type berubah
                                _reset_pekerjaan_related_data(pobj)

                                uraian = (p.get("snapshot_uraian") or "").strip()
                                if not uraian:
                                    errors.append(_err(
                                        f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian",
                                        "Wajib untuk custom baru"
                                    ))
                                    continue
                                satuan = (p.get("snapshot_satuan") or None)
                                pobj.sub_klasifikasi = s_obj
                                pobj.source_type = src
                                pobj.ref = None
                                if old_source_type != Pekerjaan.SOURCE_CUSTOM or not pobj.snapshot_kode:
                                    pobj.snapshot_kode = generate_custom_code(project)
                                pobj.snapshot_uraian = uraian
                                pobj.snapshot_satuan = satuan
                                pobj.ordering_index = final_order
                                pobj.save(update_fields=[
                                    "sub_klasifikasi", "source_type", "ref",
                                    "snapshot_kode", "snapshot_uraian", "snapshot_satuan", "ordering_index"
                                ])
                        except AHSPReferensi.DoesNotExist:
                            # Secara teori tidak terjadi karena preflight; tetap jaga-jaga
                            errors.append(_err(
                                f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                                f"Referensi #{new_ref_id} tidak ditemukan"
                            ))
                            continue
                    else:
                        # Update biasa
                        pobj.ordering_index = final_order
                        pobj.sub_klasifikasi = s_obj
                        if src == Pekerjaan.SOURCE_CUSTOM:
                            pobj.snapshot_uraian = (p.get("snapshot_uraian") or pobj.snapshot_uraian or "").strip()
                            val_sat = p.get("snapshot_satuan")
                            pobj.snapshot_satuan = (val_sat or pobj.snapshot_satuan)
                            if not pobj.snapshot_kode:
                                pobj.snapshot_kode = generate_custom_code(project)
                        elif src == Pekerjaan.SOURCE_REF_MOD:
                            if ov_ura:
                                pobj.snapshot_uraian = ov_ura
                            if ov_sat:
                                pobj.snapshot_satuan = ov_sat
                        pobj.save(update_fields=[
                            "ordering_index", "sub_klasifikasi", "snapshot_kode", "snapshot_uraian", "snapshot_satuan"
                        ])

                    source_change_state["reload_jobs"].add(pobj.id)
                    if change_was_applied:
                        _log_source_change_audit(
                            pobj,
                            old_source=old_source_type,
                            new_source=pobj.source_type,
                            old_ref_id=old_ref_id,
                            new_ref_id=getattr(pobj, "ref_id", None),
                        )

                else:
                    pobj = None
                    try:
                        if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                            rid = int(p.get("ref_id"))  # aman (preflight)
                            ref_obj = AHSPReferensi.objects.get(id=rid)

                            pobj_reuse = _get_or_reuse_pekerjaan_for_order(order_requested)
                            if pobj_reuse:
                                temp_order = _get_safe_temp_order()
                                tmp = clone_ref_pekerjaan(
                                    project, s_obj, ref_obj, src,
                                    ordering_index=temp_order, auto_load_rincian=True,
                                    override_uraian=ov_ura if src == Pekerjaan.SOURCE_REF_MOD else None,
                                    override_satuan=ov_sat if src == Pekerjaan.SOURCE_REF_MOD else None,
                                )
                                # Fallback bila clone mengembalikan None
                                if not tmp:
                                    _k, _u, _s = _safe_snap_from_ref(ref_obj, src, ov_ura, ov_sat)
                                    tmp = Pekerjaan.objects.create(
                                        project=project, sub_klasifikasi=s_obj, source_type=src, ref=ref_obj,
                                        snapshot_kode=_k,
                                        snapshot_uraian=_u,
                                        snapshot_satuan=_s,
                                        ordering_index=temp_order,
                                    )
                                pobj = pobj_reuse
                                _adopt_tmp_into(pobj, tmp, s_obj, final_order)
                            else:
                                pobj = clone_ref_pekerjaan(
                                    project, s_obj, ref_obj, src,
                                    ordering_index=final_order, auto_load_rincian=True,
                                    override_uraian=ov_ura if src == Pekerjaan.SOURCE_REF_MOD else None,
                                    override_satuan=ov_sat if src == Pekerjaan.SOURCE_REF_MOD else None,
                                )
                                # Fallback bila clone mengembalikan None
                                if not pobj:
                                    _k, _u, _s = _safe_snap_from_ref(ref_obj, src, ov_ura, ov_sat)
                                    pobj = Pekerjaan.objects.create(
                                        project=project, sub_klasifikasi=s_obj, source_type=src, ref=ref_obj,
                                        snapshot_kode=_k,
                                        snapshot_uraian=_u,
                                        snapshot_satuan=_s,
                                        ordering_index=final_order,
                                    )
                                # Safety: pastikan FK ref terisi
                                if getattr(pobj, "ref_id", None) is None:
                                    pobj.ref = ref_obj
                                    pobj.save(update_fields=["ref"])
                        else:
                            uraian = (p.get("snapshot_uraian") or "").strip()
                            if not uraian:
                                errors.append(_err(
                                    f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian",
                                    "Wajib untuk custom"
                                ))
                                continue
                            satuan = (p.get("snapshot_satuan") or None)
                            pobj = _get_or_reuse_pekerjaan_for_order(order_requested)
                            if pobj:
                                # Check if source_type is changing - if yes, reset related data
                                if pobj.source_type != src:
                                    _reset_pekerjaan_related_data(pobj)

                                pobj.sub_klasifikasi = s_obj
                                pobj.source_type = src
                                pobj.ref = None
                                if not pobj.snapshot_kode:
                                    pobj.snapshot_kode = generate_custom_code(project)
                                pobj.snapshot_uraian = uraian
                                pobj.snapshot_satuan = satuan
                                pobj.ordering_index = final_order
                                pobj.save(update_fields=[
                                    "sub_klasifikasi","source_type","ref",
                                    "snapshot_kode","snapshot_uraian","snapshot_satuan","ordering_index"
                                ])
                                change_was_applied = True
                            else:
                                pobj = Pekerjaan.objects.create(
                                    project=project, sub_klasifikasi=s_obj, source_type=src,
                                    snapshot_kode=generate_custom_code(project),
                                    snapshot_uraian=uraian, snapshot_satuan=satuan, ordering_index=final_order
                                )

                    except AHSPReferensi.DoesNotExist:
                        errors.append(_err(
                            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                            f"Referensi #{p.get('ref_id')} tidak ditemukan"
                        ))
                        continue

                    if pobj is None:
                        continue

                    source_change_state["reload_jobs"].add(pobj.id)
                    keep_all_p.add(pobj.id)

        # Hapus sub yang tidak ada lagi di Klas ini
        SubKlasifikasi.objects.filter(project=project, klasifikasi=k_obj).exclude(id__in=keep_s).delete()

    # Hapus klasifikasi yang tidak ada lagi
    Klasifikasi.objects.filter(project=project).exclude(id__in=keep_k).delete()

    # Hapus pekerjaan yang tidak ada di payload (global, setelah seluruh mutasi selesai)
    Pekerjaan.objects.filter(project=project).exclude(id__in=keep_all_p).delete()

    status = 200 if not errors else 207
    summary = {
        "klasifikasi": Klasifikasi.objects.filter(project=project).count(),
        "sub": SubKlasifikasi.objects.filter(project=project).count(),
        "pekerjaan": Pekerjaan.objects.filter(project=project).count(),
    }

    # CACHE FIX: Invalidate cache AFTER transaction commits
    transaction.on_commit(lambda: invalidate_rekap_cache(project))

    response_payload = {"ok": status == 200, "errors": errors, "summary": summary}
    if source_change_state["reload_jobs"] or source_change_state["volume_reset_jobs"]:
        response_payload["change_flags"] = {
            "reload_job_ids": sorted(source_change_state["reload_jobs"]),
            "volume_reset_job_ids": sorted(source_change_state["volume_reset_jobs"]),
        }

    return JsonResponse(response_payload, status=status)



# ---------- View 2: Volume ----------
@login_required
@require_POST
@transaction.atomic
def api_save_volume_pekerjaan(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)

    # Parse JSON
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    # Terima array langsung ATAU {items:[...]}
    rows: list | None = None
    path_prefix = ""
    if isinstance(payload, list):
        rows = payload
        path_prefix = ""                 # error path: "[0].quantity"
    elif isinstance(payload, dict):
        rows = payload.get("items")
        path_prefix = "items"            # error path: "items[0].quantity"
        if rows is None:
            rows = payload.get("volumes")
            path_prefix = "volumes"
    if not isinstance(rows, list):
        return JsonResponse({"ok": False, "errors": [_err("$", "Harus array of objek atau {items:[...]}")]}, status=400)
 

    saved = 0
    errors = []

    for idx, row in enumerate(rows):
        pid = row.get("pekerjaan_id") or row.get("id")
        raw = row.get("quantity")

        if not pid:
            key = f"{path_prefix}[{idx}].pekerjaan_id" if path_prefix else f"[{idx}].pekerjaan_id"
            errors.append(_err(key, "Wajib"))
            continue

        # Validasi kepemilikan pekerjaan supaya tidak 500 saat FK tak cocok
        try:
            from .models import Pekerjaan
            Pekerjaan.objects.get(id=pid, project=project)
        except Pekerjaan.DoesNotExist:
            key = f"{path_prefix}[{idx}].pekerjaan_id" if path_prefix else f"[{idx}].pekerjaan_id"
            errors.append(_err(key, "Pekerjaan tidak ditemukan di project ini"))
            continue

        dec = parse_any(raw)
        if dec is None:
            key = f"{path_prefix}[{idx}].quantity" if path_prefix else f"[{idx}].quantity"
            errors.append(_err(key, "Harus angka ≥ 0"))
            continue

        qty = quantize_half_up(dec, DECIMAL_SPEC["VOL"])  # 3dp HALF_UP
        if qty < 0:
            key = f"{path_prefix}[{idx}].quantity" if path_prefix else f"[{idx}].quantity"
            errors.append(_err(key, "Tidak boleh negatif"))
            continue

        VolumePekerjaan.objects.update_or_create(
            project=project,
            pekerjaan_id=pid,
            defaults={"quantity": qty},
        )
        saved += 1

    # CACHE FIX: Invalidate cache AFTER transaction commits
    if saved:
        transaction.on_commit(lambda: invalidate_rekap_cache(project))

    # Partial success → 200. Semua gagal → 400.

    status_code = 200 if saved > 0 else 400
    dp_vol = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', DECIMAL_SPEC["VOL"].dp)
    return JsonResponse({"ok": saved > 0, "saved": saved, "errors": errors, "decimal_places": dp_vol}, status=status_code)

# ---------- View 2b: Volume LIST (flat, ringan) ----------
@login_required
@require_GET
def api_list_volume_pekerjaan(request: HttpRequest, project_id: int):
    """
    Kembalikan daftar flat {pekerjaan_id, quantity} untuk seluruh pekerjaan di project.
    FE akan merge map ini ke pohon dari api_get_list_pekerjaan_tree.
    Quantity bernilai "0" (string dp-kanonik) jika belum ada record VolumePekerjaan.
    """
    project = _owner_or_404(project_id, request.user)

    # Ambil semua pekerjaan id dalam project (agar item tanpa volume pun ikut 0)
    p_ids = list(
        Pekerjaan.objects
        .filter(project=project)
        .values_list("id", flat=True)
    )

    # Ambil volume yang sudah ada
    vol_qs = VolumePekerjaan.objects.filter(project=project, pekerjaan_id__in=p_ids)\
                                    .values("pekerjaan_id", "quantity")
    vol_map = {row["pekerjaan_id"]: row["quantity"] for row in vol_qs}

    # Tentukan dp kanonik untuk wire format (ikuti spec VOL)
    dp_vol = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', DECIMAL_SPEC["VOL"].dp)

    items = [
        {
            "pekerjaan_id": pid,
            "quantity": to_dp_str(vol_map.get(pid, 0), dp_vol),  # "123,456" → kirim style kanonik "123.456"
        }
        for pid in p_ids
    ]

    return JsonResponse({"ok": True, "items": items, "decimal_places": dp_vol})


# ---------- View 3: Detail AHSP per Pekerjaan ----------
# Terdiri dari 3 endpoint:
# 3A) GET    : api_get_detail_ahsp
# 3B) SAVE   : api_save_detail_ahsp_for_pekerjaan (replace-all)
# 3C) RESET  : api_reset_detail_ahsp_to_ref (khusus ref_modified)

@login_required
@require_GET
def api_get_detail_ahsp(request: HttpRequest, project_id: int, pekerjaan_id: int):
    """
    Ambil rincian detail AHSP untuk 1 pekerjaan.

    Perilaku:
    - Selalu ambil data dari DetailAHSPProject (jika ada) apa pun source_type.
    - Jika source_type == 'ref' dan belum ada detail proyek, fallback ke RincianReferensi (read-only).
    - UI harus treat read_only=True untuk pekerjaan 'ref'.
    - Kirim 'harga_satuan' (dp mengikuti field model HargaItemProject.harga_satuan).
    """
    project = _owner_or_404(project_id, request.user)
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    dp_koef = DECIMAL_SPEC["KOEF"].dp  # biasanya 6
    source_str = ("ref" if pkj.is_ref else ("ref_modified" if pkj.is_ref_modified else "custom"))
    read_only = pkj.is_ref  # UI read-only untuk REF

    # 1) Ambil detail proyek (jika ada), sertakan harga_satuan
    qs = (DetailAHSPProject.objects
          .filter(project=project, pekerjaan=pkj)
          .select_related('harga_item')  # aman & efisien
          .order_by('kategori', 'id')
          .values('id',
                  'kategori',
                  'kode',
                  'uraian',
                  'satuan',
                  'koefisien',
                  'ref_ahsp_id',
                  'ref_pekerjaan_id',  # NEW: bundle support
                  'harga_item__harga_satuan'))

    # dp harga: fallback aman ke 2 desimal
    dp_harga = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)

    raw_details = list(qs)
    detail_ids = [row["id"] for row in raw_details if row.get("id") is not None]

    expanded_totals: dict[int, Decimal] = {}
    if detail_ids:
        value_expr = ExpressionWrapper(
            F("koefisien") * F("harga_item__harga_satuan"),
            output_field=DecimalField(max_digits=24, decimal_places=2),
        )
        expanded_rows = (
            DetailAHSPExpanded.objects
            .filter(project=project, pekerjaan=pkj, source_detail_id__in=detail_ids)
            .values("source_detail_id")
            .annotate(total=Sum(value_expr))
        )
        for row in expanded_rows:
            sd_id = row.get("source_detail_id")
            if not sd_id:
                continue
            expanded_totals[sd_id] = row.get("total") or Decimal("0")

    items = []
    for it in raw_details:
        koef_decimal = it.get("koefisien") or Decimal("0")
        harga_item = it.get("harga_item__harga_satuan")
        bundle_total = expanded_totals.get(it.get("id"), Decimal("0"))
        effective_price = harga_item
        is_bundle = (
            it.get("kategori") == HargaItemProject.KATEGORI_LAIN
            and (it.get("ref_pekerjaan_id") or it.get("ref_ahsp_id"))
        )

        # BUNDLE LOGIC (QUANTITY SEMANTIC - 2025-11-18):
        # 1. services.py menyimpan koef komponen TANPA dikali koef bundle (per 1 unit bundle)
        # 2. bundle_total = Σ(original_koef × harga komponen) → harga satuan bundle per unit
        # 3. Frontend kembali menggunakan formula umum (jumlah = koef × harga)
        # 4. Harga satuan yang dikirim API harus langsung bundle_total
        # 5. Jumlah baris dihitung di layer presentasi (tidak perlu pembagian/multiplikasi tambahan di sini).
        if is_bundle and bundle_total > Decimal("0"):
            effective_price = bundle_total

        items.append({
            "id": it["id"],
            "kategori": it["kategori"],
            "kode": it["kode"] or "",
            "uraian": it["uraian"] or "",
            "satuan": (it.get("satuan") or None),
            "koefisien": to_dp_str(koef_decimal, dp_koef),
            "ref_ahsp_id": it.get("ref_ahsp_id"),
            "ref_pekerjaan_id": it.get("ref_pekerjaan_id"),  # NEW: bundle support
            "harga_satuan": to_dp_str(effective_price, dp_harga),
        })

    # 2) Fallback (read-only) dari referensi bila pekerjaan REF & belum ada detail proyek
    if read_only and not items:
        ref_id = pkj.ref_id
        ref_obj = None

        if not ref_id and pkj.snapshot_kode:
            try:
                from referensi.models import AHSPReferensi  # lazy import
                ref_obj = AHSPReferensi.objects.filter(kode_ahsp=pkj.snapshot_kode).first()
                if ref_obj:
                    ref_id = ref_obj.id
            except Exception:
                ref_obj = None

        if ref_id:
            try:
                from referensi.models import RincianReferensi  # lazy import
                rqs = (RincianReferensi.objects
                       .filter(ahsp_id=ref_id)
                       .order_by('id')
                       .values('kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien'))

                items = [
                    {
                        "id": None,
                        "kategori": r["kategori"],
                        "kode": r.get("kode_item") or "",
                        "uraian": r.get("uraian_item") or "",
                        "satuan": (r.get("satuan_item") or None),
                        "koefisien": to_dp_str(r.get("koefisien", 0), dp_koef),
                        "ref_ahsp_id": None,         # fallback tidak mendukung bundle
                        # Tidak ada harga_satuan pada fallback; biarkan UI cari dari /harga-items/ bila perlu
                    }
                    for r in rqs
                ]
            except Exception:
                pass  # biarkan kosong jika app referensi belum siap

    kat_meta = [{"code": c, "label": l} for c, l in getattr(HargaItemProject, 'KATEGORI_CHOICES', [])]

    return JsonResponse({
        "ok": True,
        "pekerjaan": {
            "id": pkj.id,
            "kode": getattr(pkj, "snapshot_kode", None),
            "uraian": pkj.snapshot_uraian,
            "satuan": pkj.snapshot_satuan,
            "source_type": source_str,
            "detail_ready": pkj.detail_ready,
            "budgeted_cost": float(pkj.budgeted_cost or 0),
            "updated_at": pkj.updated_at.isoformat() if hasattr(pkj, 'updated_at') and pkj.updated_at else None,  # For optimistic locking
        },
        "items": items,
        "meta": {
            "kategori_opts": kat_meta,
            "read_only": read_only,
        }
    })

@login_required
@require_POST
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan(request: HttpRequest, project_id: int, pekerjaan_id: int):
    """
    Simpan detail AHSP untuk 1 pekerjaan (mode replace-all).
    - Hanya untuk 'custom' & 'ref_modified' (bukan 'ref').
    - Validasi: kategori, kode/uraian wajib, koef ≥ 0 (titik/koma), kode unik per pekerjaan.
    - Dukung bundle referensi via 'ref_ahsp_id' HANYA untuk baris kategori 'LAIN' pada pekerjaan 'custom'.
    - Koefisien disimpan HALF_UP ke dp KOEF (default 6).
    - detail_ready True bila ada baris valid.
    """
    project = _owner_or_404(project_id, request.user)

    # CRITICAL FIX: Lock pekerjaan row to prevent concurrent edit race condition
    # This ensures only one user can edit this pekerjaan at a time, preventing silent data loss
    try:
        pkj = (Pekerjaan.objects
               .select_for_update()  # Acquire row-level lock
               .get(id=pekerjaan_id, project=project))
    except Pekerjaan.DoesNotExist:
        logger.error(f"[SAVE_DETAIL_AHSP] Pekerjaan {pekerjaan_id} not found")
        return JsonResponse({
            "ok": False,
            "user_message": "Pekerjaan tidak ditemukan. Halaman mungkin sudah tidak valid.",
            "errors": [_err("pekerjaan", "Tidak ditemukan")]
        }, status=404)

    # DEBUG LOG: Start
    logger.info(f"[SAVE_DETAIL_AHSP] START - Project: {project.id}, Pekerjaan: {pkj.id} ({pkj.snapshot_kode}), Source: {pkj.source_type}")

    if pkj.source_type == Pekerjaan.SOURCE_REF:
        logger.warning(f"[SAVE_DETAIL_AHSP] REJECTED - Pekerjaan {pkj.id} is REF (read-only)")
        return JsonResponse({
            "ok": False,
            "user_message": "Pekerjaan ini bersumber dari referensi dan tidak dapat diubah. Gunakan halaman Rincian AHSP Gabungan untuk modifikasi.",
            "errors": [_err("source_type", "Pekerjaan referensi tidak bisa diubah di tahap ini (gunakan tahap Gabungan).")]
        }, status=400)

    old_snapshot = snapshot_pekerjaan_details(pkj)

    # Parse payload
    try:
        payload = json.loads(request.body.decode('utf-8'))
        logger.info(f"[SAVE_DETAIL_AHSP] Payload received: {len(payload.get('rows', []))} rows")
    except Exception as e:
        logger.error(f"[SAVE_DETAIL_AHSP] JSON parse error: {str(e)}")
        return JsonResponse({
            "ok": False,
            "user_message": "Data yang dikirim tidak valid. Silakan refresh halaman dan coba lagi.",
            "errors": [_err("$", "Payload JSON tidak valid")]
        }, status=400)

    # OPTIMISTIC LOCKING: Check client timestamp against server timestamp
    client_updated_at = payload.get('client_updated_at')
    if client_updated_at:
        from datetime import datetime
        try:
            # Parse ISO format timestamp from client
            client_dt = datetime.fromisoformat(client_updated_at.replace('Z', '+00:00'))

            # Refresh project to get latest timestamp
            project.refresh_from_db()
            server_dt = project.updated_at if hasattr(project, 'updated_at') and project.updated_at else None

            if server_dt and client_dt < server_dt:
                # Data has been modified by another user since client loaded it
                logger.warning(
                    f"[SAVE_DETAIL_AHSP] CONFLICT - Pekerjaan {pkj.id} modified by another user. "
                    f"Client: {client_dt.isoformat()}, Server: {server_dt.isoformat()}"
                )

                # FASE 0.3: Log optimistic lock conflict
                log_optimistic_lock_conflict(
                    project_id=project.id,
                    pekerjaan_id=pkj.id,
                    client_timestamp=client_updated_at,
                    server_timestamp=server_dt.isoformat()
                )

                return JsonResponse({
                    "ok": False,
                    "conflict": True,  # Special flag for conflict
                    "user_message": (
                        "⚠️ KONFLIK DATA TERDETEKSI!\n\n"
                        "Data pekerjaan ini telah diubah oleh pengguna lain sejak Anda membukanya.\n\n"
                        "Pilihan:\n"
                        "• Muat Ulang: Refresh halaman untuk melihat perubahan terbaru (data Anda akan hilang)\n"
                        "• Timpa: Simpan data Anda dan timpa perubahan pengguna lain (tidak disarankan)"
                    ),
                    "server_updated_at": server_dt.isoformat(),
                    "errors": [_err("updated_at", "Data telah berubah sejak Anda membukanya")]
                }, status=409)  # 409 Conflict
        except (ValueError, AttributeError) as e:
            logger.warning(f"[SAVE_DETAIL_AHSP] Invalid client_updated_at format: {client_updated_at}, error: {e}")
            # Continue without optimistic locking if timestamp is invalid

    rows = payload.get('rows') or []
    if not isinstance(rows, list):
        return JsonResponse({
            "ok": False,
            "user_message": "Format data tidak valid. Silakan refresh halaman dan coba lagi.",
            "errors": [_err("rows", "Harus list")]
        }, status=400)

    # Normalisasi & validasi
    errors = []
    normalized = []  # tuple: (kat, kode, uraian, satuan, koef, ref_ahsp_obj, ref_pekerjaan_obj)
    seen_kode: Set[str] = set()
    unit_code_state: Dict[str, object] = {}
    valid_kats = set(dict(HargaItemProject.KATEGORI_CHOICES).keys())

    for i, r in enumerate(rows):
        kat = _normalize_kategori(r.get('kategori'))
        if kat not in valid_kats:
            errors.append(_err(f"rows[{i}].kategori", "Kategori tidak valid")); continue

        kode = (r.get('kode') or '').strip()
        if not kode and kat in _UNIT_AUTO_KATEGORI:
            kode = _auto_unit_code(project, unit_code_state, seen_kode)
        uraian = (r.get('uraian') or '').strip()
        satuan = (r.get('satuan') or '').strip() or None
        koef = parse_any(r.get('koefisien'))  # parser robust (koma/titik, ribuan)

        # --- Validasi dasar ---
        if not uraian:
            errors.append(_err(f"rows[{i}].uraian", "Wajib")); continue
        if not kode:
            errors.append(_err(f"rows[{i}].kode", "Wajib")); continue
        if koef is None:
            errors.append(_err(f"rows[{i}].koefisien", "Harus ≥ 0 dan berupa angka yang valid")); continue
        if kode in seen_kode:
            errors.append(_err(f"rows[{i}].kode", "Kode duplikat dalam pekerjaan ini")); continue
        seen_kode.add(kode)

        # --- Bundle referensi (opsional) — 2 jenis: AHSP atau Pekerjaan ---
        ref_ahsp_obj = None
        ref_pekerjaan_obj = None

        # Check new format: ref_kind + ref_id (prioritas)
        ref_kind = r.get('ref_kind', None)
        ref_id_raw = r.get('ref_id', None)

        if ref_kind and ref_id_raw:
            # New format: ref_kind='ahsp' atau 'job'
            try:
                ref_id = int(ref_id_raw)
            except (TypeError, ValueError):
                errors.append(_err(f"rows[{i}].ref_id", "Harus integer")); continue

            # Hanya boleh pada pekerjaan custom
            if pkj.source_type != Pekerjaan.SOURCE_CUSTOM:
                errors.append(_err(f"rows[{i}].ref_kind", "Hanya boleh untuk pekerjaan custom")); continue

            # Hanya boleh pada kategori LAIN
            if kat != HargaItemProject.KATEGORI_LAIN:
                errors.append(_err(f"rows[{i}].ref_kind", "Hanya boleh pada kategori 'Lain-lain'")); continue

            # Validate bundle reference (circular dependency check)
            is_valid, error_msg = validate_bundle_reference(pkj.id, ref_kind, ref_id, project)
            if not is_valid:
                errors.append(_err(f"rows[{i}].ref_{ref_kind}", error_msg)); continue

            # Get reference object
            if ref_kind == 'ahsp':
                try:
                    ref_ahsp_obj = AHSPReferensi.objects.get(id=ref_id)
                except AHSPReferensi.DoesNotExist:
                    errors.append(_err(f"rows[{i}].ref_id", f"AHSP #{ref_id} tidak ditemukan")); continue
            elif ref_kind == 'job':
                try:
                    ref_pekerjaan_obj = Pekerjaan.objects.get(id=ref_id, project=project)

                    # VALIDATION: Bundle target must not be empty
                    target_component_count = DetailAHSPProject.objects.filter(
                        project=project,
                        pekerjaan=ref_pekerjaan_obj
                    ).count()

                    if target_component_count == 0:
                        ref_kode = ref_pekerjaan_obj.snapshot_kode or f"PKJ#{ref_pekerjaan_obj.id}"
                        errors.append(_warn(
                            f"rows[{i}].ref_id",
                            f"❌ Pekerjaan '{ref_kode}' tidak memiliki komponen AHSP. "
                            f"Bundle harus mereferensi pekerjaan yang sudah memiliki komponen. "
                            f"Silakan isi komponen pekerjaan tersebut terlebih dahulu atau pilih pekerjaan lain."
                        ))
                        continue

                except Pekerjaan.DoesNotExist:
                    errors.append(_err(f"rows[{i}].ref_id", f"Pekerjaan #{ref_id} tidak ditemukan")); continue
            else:
                errors.append(_err(f"rows[{i}].ref_kind", f"ref_kind '{ref_kind}' tidak valid (harus 'ahsp' atau 'job')")); continue

        else:
            # Old format fallback: ref_ahsp_id only
            ref_ahsp_id_raw = r.get('ref_ahsp_id', None)
            if ref_ahsp_id_raw not in (None, ''):
                try:
                    ref_ahsp_id = int(ref_ahsp_id_raw)
                except (TypeError, ValueError):
                    errors.append(_err(f"rows[{i}].ref_ahsp_id", "Harus integer")); continue

                # Hanya boleh pada pekerjaan custom
                if pkj.source_type != Pekerjaan.SOURCE_CUSTOM:
                    errors.append(_err(f"rows[{i}].ref_ahsp_id", "Hanya boleh untuk pekerjaan custom")); continue

                # Hanya boleh pada kategori LAIN
                if kat != HargaItemProject.KATEGORI_LAIN:
                    errors.append(_err(f"rows[{i}].ref_ahsp_id", "Hanya boleh pada kategori 'Lain-lain'")); continue

                # Validate & get object
                is_valid, error_msg = validate_bundle_reference(pkj.id, 'ahsp', ref_ahsp_id, project)
                if not is_valid:
                    errors.append(_err(f"rows[{i}].ref_ahsp_id", error_msg)); continue

                try:
                    ref_ahsp_obj = AHSPReferensi.objects.get(id=ref_ahsp_id)
                except AHSPReferensi.DoesNotExist:
                    errors.append(_err(f"rows[{i}].ref_ahsp_id", f"Referensi #{ref_ahsp_id} tidak ditemukan")); continue

        # --- Kumpulkan baris tervalidasi ---
        normalized.append((kat, kode, uraian, satuan, koef, ref_ahsp_obj, ref_pekerjaan_obj))

    # Bila semua baris error → fatal (400) kecuali jika seluruh error bertipe warning
    if errors and not normalized:
        all_warnings = all(err.get("severity") == "warning" for err in errors)
        allow_soft = getattr(project, "allow_bundle_soft_errors", False)
        status = 207 if (all_warnings and allow_soft) else 400
        logger.debug(
            "SAVE_DETAIL_AHSP soft_errors=%s all_warnings=%s status=%s project_id=%s",
            allow_soft, all_warnings, status, project.id
        )
        log_fn = logger.warning if status == 207 else logger.error
        log_fn(f"[SAVE_DETAIL_AHSP] No valid rows ({len(errors)} errors) – status={status}")
        error_count = len(errors)
        if all_warnings:
            user_message = (
                f"[WARN] Tidak ada baris yang disimpan. {error_count} peringatan ditemukan pada data yang dikirim."
            )
        else:
            user_message = (
                f"[ERROR] Gagal menyimpan data. {error_count} kesalahan ditemukan pada data yang dikirim."
            )
        return JsonResponse({
            "ok": False,
            "success": False,
            "user_message": user_message,
            "saved_raw_rows": 0,
            "saved_rows": 0,
            "saved_expanded_rows": 0,
            "errors": errors,
            "pekerjaan": {
                "id": pkj.id,
                "updated_at": pkj.updated_at.isoformat() if getattr(pkj, "updated_at", None) else None,
            }
        }, status=status)

    logger.info(f"[SAVE_DETAIL_AHSP] Validation passed: {len(normalized)} rows valid, {len(errors)} errors")

    # ========================================================================
    # DUAL STORAGE IMPLEMENTATION
    # ========================================================================
    # STORAGE 1: Save RAW INPUT to DetailAHSPProject (keep LAIN bundles)
    # STORAGE 2: Expand bundles to DetailAHSPExpanded (computed for rekap)
    # ========================================================================

    dp_koef = DECIMAL_SPEC["KOEF"].dp  # default 6

    # STORAGE 1: Prepare raw input (keep bundles!)
    raw_details_to_create = []
    logger.info(f"[SAVE_DETAIL_AHSP] Preparing STORAGE 1 (DetailAHSPProject - raw input)")

    # Catch ValidationError from _upsert_harga_item (kategori immutability check)
    from django.core.exceptions import ValidationError
    try:
        for kat, kode, uraian, satuan, koef, ref_ahsp_obj, ref_pekerjaan_obj in normalized:
            # Upsert HargaItemProject (create master harga record)
            # For LAIN bundles, create placeholder with harga_satuan=0
            # CRITICAL: This may raise ValidationError if kategori mismatch detected
            hip = _upsert_harga_item(project, kat, kode, uraian, satuan)

            raw_details_to_create.append(DetailAHSPProject(
            project=project,
            pekerjaan=pkj,
            harga_item=hip,
            kategori=kat,
            kode=kode,
            uraian=uraian,
            satuan=satuan,
            koefisien=quantize_half_up(koef, dp_koef),  # HALF_UP dp=6
            # Field bundle: keep refs for LAIN bundles
            ref_ahsp=(ref_ahsp_obj if (kat == HargaItemProject.KATEGORI_LAIN and pkj.source_type == Pekerjaan.SOURCE_CUSTOM) else None),
            ref_pekerjaan=(ref_pekerjaan_obj if (kat == HargaItemProject.KATEGORI_LAIN and pkj.source_type == Pekerjaan.SOURCE_CUSTOM) else None),
        ))

    except ValidationError as ve:
        # Kategori mismatch detected by _upsert_harga_item
        logger.error(f"[SAVE_DETAIL_AHSP] ValidationError during upsert: {str(ve)}")
        return JsonResponse({
            "ok": False,
            "user_message": str(ve),
            "errors": [_err("kategori", str(ve))]
        }, status=400)

    # Delete old & insert new (replace-all) for STORAGE 1
    old_count = DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).count()
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()
    logger.info(f"[SAVE_DETAIL_AHSP] Deleted {old_count} old DetailAHSPProject rows")

    if raw_details_to_create:
        created_raw = DetailAHSPProject.objects.bulk_create(raw_details_to_create, ignore_conflicts=True)
        logger.info(f"[SAVE_DETAIL_AHSP] Created {len(created_raw)} new DetailAHSPProject rows")
    else:
        created_raw = []
        logger.warning(f"[SAVE_DETAIL_AHSP] No raw details to create")

    # STORAGE 2: Expand bundles to DetailAHSPExpanded
    old_expanded_count = DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pkj).count()
    DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pkj).delete()
    logger.info(f"[SAVE_DETAIL_AHSP] STORAGE 2: Deleted {old_expanded_count} old DetailAHSPExpanded rows")

    expanded_to_create = []

    # Fetch created objects back dengan ID (untuk FK source_detail)
    saved_raw_details = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan=pkj
    ).select_related('harga_item', 'ref_pekerjaan').order_by('id')
    logger.info(f"[SAVE_DETAIL_AHSP] Processing {saved_raw_details.count()} saved raw details for expansion")

    for detail_obj in saved_raw_details:
        if detail_obj.kategori == HargaItemProject.KATEGORI_LAIN and detail_obj.ref_pekerjaan:
            # BUNDLE - Expand to components
            ref_pkj_kode = detail_obj.ref_pekerjaan.snapshot_kode if detail_obj.ref_pekerjaan else "Unknown"
            logger.info(f"[SAVE_DETAIL_AHSP] BUNDLE detected: '{detail_obj.kode}' → ref_pekerjaan={ref_pkj_kode} (ID: {detail_obj.ref_pekerjaan_id})")

            detail_dict = {
                'kategori': detail_obj.kategori,
                'kode': detail_obj.kode,
                'uraian': detail_obj.uraian,
                'satuan': detail_obj.satuan,
                'koefisien': detail_obj.koefisien,
                'ref_pekerjaan_id': detail_obj.ref_pekerjaan_id,
            }

            try:
                # Expand bundle recursively
                logger.info(f"[SAVE_DETAIL_AHSP] Expanding bundle '{detail_obj.kode}' (koef={detail_obj.koefisien})...")
                expanded_components = expand_bundle_to_components(
                    detail_data=detail_dict,
                    project=project,
                    base_koef=Decimal('1.0'),
                    depth=1,
                    visited=None
                )
                logger.info(f"[SAVE_DETAIL_AHSP] Expansion result: {len(expanded_components)} components")

                # Check if expansion returned components
                if not expanded_components:
                    # Bundle has no components (empty pekerjaan or expansion failed)
                    ref_pkj_kode = detail_obj.ref_pekerjaan.snapshot_kode if detail_obj.ref_pekerjaan else "Unknown"
                    logger.warning(
                        f"Bundle expansion returned empty for pekerjaan {pkj.id}, "
                        f"bundle '{detail_obj.kode}' (ref_pekerjaan: {ref_pkj_kode}). "
                        f"Target pekerjaan may have no details."
                    )
                    errors.append(_err(
                        f"bundle.{detail_obj.kode}",
                        f"Pekerjaan gabungan '{detail_obj.uraian}' tidak memiliki komponen. "
                        f"Pastikan pekerjaan yang direferensikan ('{ref_pkj_kode}') sudah memiliki detail AHSP."
                    ))
                    # Don't add to expanded - bundle without components is invalid

                # Add expanded components to DetailAHSPExpanded
                for comp in expanded_components:
                    # Upsert HargaItemProject for base components
                    comp_hip = _upsert_harga_item(
                        project,
                        comp['kategori'],
                        comp['kode'],
                        comp['uraian'],
                        comp['satuan']
                    )

                    expanded_to_create.append(DetailAHSPExpanded(
                        project=project,
                        pekerjaan=pkj,
                        source_detail=detail_obj,  # Link back to raw input
                        harga_item=comp_hip,
                        kategori=comp['kategori'],
                        kode=comp['kode'],
                        uraian=comp['uraian'],
                        satuan=comp['satuan'],
                        koefisien=quantize_half_up(comp['koefisien'], dp_koef),
                        source_bundle_kode=detail_obj.kode,  # Bundle kode for tracking
                        expansion_depth=comp['depth'],
                    ))

            except ValueError as e:
                # Expansion failed (circular dependency atau max depth)
                logger.error(
                    f"Bundle expansion failed for pekerjaan {pkj.id}, bundle {detail_obj.kode}: {str(e)}"
                )
                errors.append(_err(f"bundle.{detail_obj.kode}", f"Error expansion: {str(e)}"))
                # Continue - keep raw input even if expansion fails
                # User can fix and re-save

        elif detail_obj.kategori == HargaItemProject.KATEGORI_LAIN and detail_obj.ref_ahsp:
            # AHSP BUNDLE - Expand from Master AHSP
            logger.info(f"[SAVE_DETAIL_AHSP] AHSP BUNDLE detected: '{detail_obj.kode}' → ref_ahsp_id={detail_obj.ref_ahsp_id}")

            try:
                # Expand AHSP bundle recursively
                logger.info(f"[SAVE_DETAIL_AHSP] Expanding AHSP bundle '{detail_obj.kode}' (koef={detail_obj.koefisien})...")
                expanded_components = expand_ahsp_bundle_to_components(
                    ref_ahsp_id=detail_obj.ref_ahsp_id,
                    project=project,
                    base_koef=Decimal('1.0'),
                    depth=1,
                    visited=None
                )
                logger.info(f"[SAVE_DETAIL_AHSP] AHSP expansion result: {len(expanded_components)} components")

                # Check if expansion returned components
                if not expanded_components:
                    logger.warning(
                        f"AHSP bundle expansion returned empty for pekerjaan {pkj.id}, "
                        f"bundle '{detail_obj.kode}'. AHSP may have no components."
                    )
                    errors.append(_err(
                        f"bundle.{detail_obj.kode}",
                        f"AHSP '{detail_obj.uraian}' tidak memiliki komponen."
                    ))

                # Add expanded components to DetailAHSPExpanded
                for comp in expanded_components:
                    # Upsert HargaItemProject for base components
                    comp_hip = _upsert_harga_item(
                        project,
                        comp['kategori'],
                        comp['kode'],
                        comp['uraian'],
                        comp['satuan']
                    )

                    expanded_to_create.append(DetailAHSPExpanded(
                        project=project,
                        pekerjaan=pkj,
                        source_detail=detail_obj,  # Link back to raw input
                        harga_item=comp_hip,
                        kategori=comp['kategori'],
                        kode=comp['kode'],
                        uraian=comp['uraian'],
                        satuan=comp['satuan'],
                        koefisien=quantize_half_up(comp['koefisien'], dp_koef),
                        source_bundle_kode=detail_obj.kode,  # Bundle kode for tracking
                        expansion_depth=comp['depth'],
                    ))

            except ValueError as e:
                # Expansion failed (circular dependency atau max depth)
                logger.error(
                    f"AHSP bundle expansion failed for pekerjaan {pkj.id}, bundle {detail_obj.kode}: {str(e)}"
                )
                errors.append(_err(f"bundle.{detail_obj.kode}", f"Error AHSP expansion: {str(e)}"))
                # Continue - keep raw input even if expansion fails

        elif detail_obj.kategori == HargaItemProject.KATEGORI_LAIN:
            # LAIN item without ref_pekerjaan AND without ref_ahsp - invalid bundle
            logger.warning(
                f"LAIN item '{detail_obj.kode}' in pekerjaan {pkj.id} has no ref_pekerjaan or ref_ahsp. "
                f"Bundle items must reference a pekerjaan or AHSP. Skipping from expanded storage."
            )
            errors.append(_err(
                f"item.{detail_obj.kode}",
                f"Item LAIN '{detail_obj.uraian}' tidak memiliki referensi pekerjaan atau AHSP. "
                f"Untuk pekerjaan gabungan, pilih pekerjaan atau AHSP dari dropdown."
            ))
            # Don't add to expanded - invalid bundle

        else:
            # DIRECT INPUT (TK/BHN/ALT) - Pass-through to expanded
            expanded_to_create.append(DetailAHSPExpanded(
                project=project,
                pekerjaan=pkj,
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

    # Bulk create expanded components
    if expanded_to_create:
        DetailAHSPExpanded.objects.bulk_create(expanded_to_create, ignore_conflicts=True)
        logger.info(f"[SAVE_DETAIL_AHSP] Created {len(expanded_to_create)} DetailAHSPExpanded rows")
    else:
        logger.warning(f"[SAVE_DETAIL_AHSP] No expanded components to create")

    # Update pekerjaan.detail_ready dan timestamp detail
    detail_ready = len(expanded_to_create) > 0
    detail_change_ts = timezone.now()
    Pekerjaan.objects.filter(pk=pkj.pk).update(
        detail_ready=detail_ready,
        detail_last_modified=detail_change_ts,
    )
    touch_project_change(project, ahsp=True)
    _commit_unit_code_state(unit_code_state, should_persist=len(saved_raw_details) > 0)
    logger.info(f"[SAVE_DETAIL_AHSP] Updated pekerjaan.detail_ready = {detail_ready}")

    # OPSI A: Update project timestamp for optimistic locking
    if len(saved_raw_details) > 0:
        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])
        logger.info(f"[PROJECT_TIMESTAMP] Updated project {project.id} timestamp after saving {len(saved_raw_details)} detail AHSP changes")

    # CRITICAL FIX: Cascade re-expansion for bundle references
    # When this pekerjaan is modified and is referenced by other pekerjaan as bundle,
    # we must re-expand those referencing pekerjaan to prevent stale data
    def cascade_operations():
        """Execute cascade operations after transaction commits"""
        # 1. Re-expand all pekerjaan that reference this modified pekerjaan
        try:
            re_expanded_count = cascade_bundle_re_expansion(project, pkj.id)
            if re_expanded_count > 0:
                logger.info(
                    f"[SAVE_DETAIL_AHSP] CASCADE: Re-expanded {re_expanded_count} pekerjaan "
                    f"that reference pekerjaan {pkj.id}"
                )
        except Exception as e:
            logger.error(
                f"[SAVE_DETAIL_AHSP] CASCADE FAILED: Error re-expanding referencing pekerjaan: {str(e)}",
                exc_info=True
            )
            # Don't raise - cascade failure shouldn't fail the save operation

        # 2. Invalidate cache (always needed)
        invalidate_rekap_cache(project)

    transaction.on_commit(cascade_operations)

    if errors:
        status_code = 207 if len(saved_raw_details) > 0 else 400
    else:
        status_code = 200
    logger.info(f"[SAVE_DETAIL_AHSP] SUCCESS - Status: {status_code}, Raw: {len(saved_raw_details)}, Expanded: {len(expanded_to_create)}, Errors: {len(errors)}")

    # Build user-friendly message
    if status_code == 200:
        user_message = f"[OK] Data berhasil disimpan! {len(saved_raw_details)} baris komponen tersimpan."
    elif status_code == 207:
        user_message = f"[WARN] Data tersimpan sebagian. {len(saved_raw_details)} baris berhasil, {len(errors)} kesalahan ditemukan."
    else:
        user_message = f"[ERROR] Gagal menyimpan data. {len(errors)} kesalahan ditemukan."

    new_snapshot = snapshot_pekerjaan_details(pkj)
    action = DetailAHSPAudit.ACTION_UPDATE
    if not old_snapshot and new_snapshot:
        action = DetailAHSPAudit.ACTION_CREATE
    elif old_snapshot and not new_snapshot:
        action = DetailAHSPAudit.ACTION_DELETE
    if old_snapshot != new_snapshot:
        log_audit(
            project,
            pkj,
            action,
            old_data=old_snapshot,
            new_data=new_snapshot,
            triggered_by="user",
            user=request.user,
        )

    # Refresh pekerjaan to get updated timestamp
    pkj.refresh_from_db()

    return JsonResponse({
        "ok": status_code == 200,
        "success": status_code == 200,
        "user_message": user_message,
        "saved_raw_rows": len(saved_raw_details),
        "saved_rows": len(saved_raw_details),
        "saved_expanded_rows": len(expanded_to_create),
        "errors": errors,
        "pekerjaan": {
            "id": pkj.id,
            "updated_at": pkj.updated_at.isoformat() if hasattr(pkj, 'updated_at') and pkj.updated_at else None
        }
    }, status=status_code)

@login_required
@require_POST
@transaction.atomic
def api_reset_detail_ahsp_to_ref(request: HttpRequest, project_id: int, pekerjaan_id: int):
    """
    Reset isi detail untuk pekerjaan 'ref_modified' dari referensi sumbernya.
    - Hapus semua baris di DetailAHSPProject untuk pekerjaan tsb.
    - Clone ulang dari referensi (via services.clone_ref_pekerjaan) ke objek TEMP,
      lalu pindahkan detailnya ke objek asli (untuk menghindari konflik FK/unik).
    """
    project = _owner_or_404(project_id, request.user)
    from dashboard.models import Project as _P
    _P.objects.select_for_update().filter(id=project.id).first()
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    if pkj.source_type != Pekerjaan.SOURCE_REF_MOD:
        return JsonResponse({"ok": False, "errors": [_err("source_type", "Hanya ref_modified yang bisa di-reset")]}, status=400)

    ref_obj = getattr(pkj, "ref", None)
    if not ref_obj:
        return JsonResponse({"ok": False, "errors": [_err("ref", "Pointer referensi tidak ditemukan")]}, status=400)

    # Bersihkan isi lama
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()

    # Buat pekerjaan TEMP agar services dapat auto-load rincian,
    # kemudian adopsi detail TEMP ke pekerjaan asli dan hapus TEMP.
    # CRITICAL FIX: Use unique ordering_index for temp to avoid unique_together("project", "ordering_index") constraint violation
    max_ordering = Pekerjaan.objects.filter(project=project).aggregate(Max('ordering_index'))['ordering_index__max'] or 0
    temp_ordering = max_ordering + 1

    temp = clone_ref_pekerjaan(
        project, pkj.sub_klasifikasi, ref_obj, Pekerjaan.SOURCE_REF_MOD,
        ordering_index=temp_ordering, auto_load_rincian=True,
        override_uraian=pkj.snapshot_uraian or None,
        override_satuan=pkj.snapshot_satuan or None,
    )

    moved = 0
    if temp:
        # --- DEDUP saat reset (aman walau sebelumnya sudah delete) ---
        existing_kodes = set(
            DetailAHSPProject.objects
            .filter(project=project, pekerjaan=pkj)
            .values_list("kode", flat=True)
        )
        tmp_qs = DetailAHSPProject.objects.filter(project=project, pekerjaan=temp)
        if existing_kodes:
            tmp_qs = tmp_qs.exclude(kode__in=existing_kodes)
        moved = tmp_qs.update(pekerjaan=pkj)

        # CRITICAL: Re-populate expanded storage for original pekerjaan after move
        # DetailAHSPExpanded for TEMP will be CASCADE deleted with temp.delete()
        # We must re-create expanded storage for PKJ to maintain dual storage integrity
        from .services import _populate_expanded_from_raw
        _populate_expanded_from_raw(project, pkj)

        temp.delete()

    # Tandai ready bila ada baris
    detail_ready = moved > 0
    detail_change_ts = timezone.now()
    Pekerjaan.objects.filter(pk=pkj.pk).update(
        detail_ready=detail_ready,
        detail_last_modified=detail_change_ts if detail_ready else pkj.detail_last_modified,
    )
    if detail_ready:
        touch_project_change(project, ahsp=True)

    # CACHE FIX: Invalidate cache AFTER transaction commits
    transaction.on_commit(lambda: invalidate_rekap_cache(project))

    return JsonResponse({"ok": True, "cloned_count": int(moved)})

# ---------- View 4: Harga Items ----------
@login_required
@require_POST
@transaction.atomic
def api_save_harga_items(request: HttpRequest, project_id: int):
    """
    Save/update Harga Items for this project.

    DUAL STORAGE UPDATE:
    - Validates items against DetailAHSPExpanded (expanded components)
    - Only allows editing items that are actually used in expanded storage

    P0 FIXES (2025-11-11):
    - Added row-level locking to prevent concurrent edit race conditions
    - Added optimistic locking with timestamp checking
    - Fixed cache invalidation timing
    - Added user-friendly error messages
    """
    project = _owner_or_404(project_id, request.user)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({
            "ok": False,
            "user_message": "Data yang dikirim tidak valid. Silakan refresh halaman dan coba lagi.",
            "errors": [_err("$", "Payload JSON tidak valid")]
        }, status=400)

    # P0 FIX: OPTIMISTIC LOCKING - Check client timestamp against server timestamp
    client_updated_at = payload.get('client_updated_at')
    if client_updated_at:
        from datetime import datetime
        try:
            # Parse ISO format timestamp from client
            client_dt = datetime.fromisoformat(client_updated_at.replace('Z', '+00:00'))

            # Refresh project to get latest timestamp
            project.refresh_from_db()
            server_dt = project.updated_at if hasattr(project, 'updated_at') and project.updated_at else None

            if server_dt and client_dt < server_dt:
                # Data has been modified by another user since client loaded it
                logger.warning(
                    f"[SAVE_HARGA_ITEMS] CONFLICT - Project {project.id} modified by another user. "
                    f"Client: {client_dt.isoformat()}, Server: {server_dt.isoformat()}"
                )
                return JsonResponse({
                    "ok": False,
                    "conflict": True,  # Special flag for conflict
                    "user_message": (
                        "⚠️ KONFLIK DATA TERDETEKSI!\n\n"
                        "Data harga telah diubah oleh pengguna lain sejak Anda membukanya.\n\n"
                        "Pilihan:\n"
                        "• Muat Ulang: Refresh halaman untuk melihat perubahan terbaru (data Anda akan hilang)\n"
                        "• Timpa: Simpan data Anda dan timpa perubahan pengguna lain (tidak disarankan)"
                    ),
                    "server_updated_at": server_dt.isoformat(),
                    "errors": [_err("updated_at", "Data telah berubah sejak Anda membukanya")]
                }, status=409)  # 409 Conflict
        except (ValueError, AttributeError) as e:
            logger.warning(f"[SAVE_HARGA_ITEMS] Invalid client_updated_at format: {client_updated_at}, error: {e}")
            # Continue without optimistic locking if timestamp is invalid

    items = payload.get('items') or []
    errors = []
    updated = 0

    # DUAL STORAGE: Check against expanded_refs (expanded components)
    allowed_ids = set(HargaItemProject.objects
                      .filter(project=project, expanded_refs__project=project)
                      .values_list('id', flat=True)
                      .distinct())

    dp = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)

    for i, it in enumerate(items):
        item_id = it.get('id')
        harga_raw = it.get('harga_satuan')

        if item_id is None:
            errors.append(_err(f"items[{i}].id", "Wajib")); continue
        if item_id not in allowed_ids:
            errors.append(_err(f"items[{i}].id", "Item ini tidak digunakan di Detail AHSP proyek")); continue

        dec = parse_any(harga_raw)
        if dec is None:
            errors.append(_err(f"items[{i}].harga_satuan", "Harus ≥ 0 dan berupa angka yang valid")); continue

        # P0 FIX: ROW-LEVEL LOCKING - Prevent concurrent edit race condition
        try:
            # Acquire row-level lock with select_for_update()
            obj = (HargaItemProject.objects
                   .select_for_update()  # Lock this row
                   .get(project=project, id=item_id))

            # Update with lock held
            new_price = quantize_half_up(dec, dp)
            if obj.harga_satuan != new_price:
                obj.harga_satuan = new_price
                obj.save(update_fields=['harga_satuan', 'updated_at'])
                updated += 1
        except HargaItemProject.DoesNotExist:
            errors.append(_err(f"items[{i}].id", "Item tidak ditemukan"))
            continue

    # === NEW: Profit/Margin (opsional)
    pricing_saved = False
    if 'markup_percent' in (payload or {}):
        mp_raw = payload.get('markup_percent')
        if mp_raw not in (None, ''):
            val = parse_any(mp_raw)
            if val is None or val < 0 or val > 100:
                errors.append(_err("markup_percent", "Harus 0–100 dan berupa angka yang valid"))
            else:
                pricing = _get_or_create_pricing(project)
                pricing.markup_percent = quantize_half_up(val, 2)
                pricing.save(update_fields=["markup_percent", "updated_at"])
                pricing_saved = True

    # === NEW: status code partial
    if errors and (updated == 0 and not pricing_saved):
        status_code = 400
    elif errors:
        status_code = 207
    else:
        status_code = 200

    # P0 FIX: Cache invalidation AFTER transaction commits
    if updated > 0 or pricing_saved:
        # OPSI A: Update project timestamp for optimistic locking
        # This ensures project.updated_at reflects when harga items were modified
        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])
        logger.info(f"[PROJECT_TIMESTAMP] Updated project {project.id} timestamp after {updated} harga changes")

        def invalidate_harga_cache():
            invalidate_rekap_cache(project)
            logger.info(f"[CACHE] Invalidated cache for project {project.id} after harga items update")

        transaction.on_commit(invalidate_harga_cache)

    # Build user-friendly message
    if status_code == 200:
        if updated > 0 and pricing_saved:
            user_message = f"✅ Berhasil menyimpan {updated} perubahan harga dan profit/margin!"
        elif updated > 0:
            user_message = f"✅ Berhasil menyimpan {updated} perubahan harga!"
        elif pricing_saved:
            user_message = "✅ Berhasil menyimpan profit/margin!"
        else:
            user_message = "✅ Tidak ada perubahan untuk disimpan."
    else:
        user_message = f"⚠️ Data tersimpan sebagian. {len(errors)} kesalahan ditemukan."

    if status_code == 200 and (updated > 0 or pricing_saved):
        touch_project_change(project, harga=True)

    # Refresh project to get updated timestamp
    project.refresh_from_db()

    # kirim balik nilai Profit/Margin terbaru untuk sinkronisasi FE
    pricing = _get_or_create_pricing(project)
    return JsonResponse(
        {
            "ok": status_code == 200,
            "user_message": user_message,
            "updated": updated,
            "pricing_saved": pricing_saved,
            "markup_percent": to_dp_str(pricing.markup_percent, 2),
            "project_updated_at": project.updated_at.isoformat() if hasattr(project, 'updated_at') and project.updated_at else None,
            "errors": errors,
        },
        status=status_code
    )


# ---------- View: Item Conversion Profiles ----------
@login_required
@require_GET
def api_get_conversion_profiles(request: HttpRequest, project_id: int):
    """
    GET conversion profiles for all items in this project.
    Returns a dictionary keyed by item kode for easy frontend lookup.
    
    Response:
    {
        "ok": true,
        "profiles": {
            "BHN-001": {
                "id": 1,
                "market_unit": "batang",
                "market_price": "240000.00",
                "factor_to_base": "10.000000",
                "base_unit": "kg",
                "density": null,
                "capacity_m3": null,
                "capacity_ton": null,
                "method": "direct"
            },
            ...
        }
    }
    """
    from .models import ItemConversionProfile
    
    project = _owner_or_404(project_id, request.user)
    
    # Fetch all conversion profiles for this project
    profiles_qs = (ItemConversionProfile.objects
                   .filter(harga_item__project=project)
                   .select_related('harga_item'))
    
    result = {}
    for p in profiles_qs:
        result[p.harga_item.kode_item] = {
            "id": p.id,
            "harga_item_id": p.harga_item.id,
            "market_unit": p.market_unit,
            "market_price": to_dp_str(p.market_price, 2),
            "factor_to_base": to_dp_str(p.factor_to_base, 6),
            "base_unit": p.harga_item.satuan or "",
            "density": to_dp_str(p.density, 6) if p.density else None,
            "capacity_m3": to_dp_str(p.capacity_m3, 6) if p.capacity_m3 else None,
            "capacity_ton": to_dp_str(p.capacity_ton, 6) if p.capacity_ton else None,
            "method": p.method,
        }
    
    return JsonResponse({
        "ok": True,
        "profiles": result,
        "count": len(result),
    })


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def api_save_conversion_profile(request: HttpRequest, project_id: int):
    """
    POST save/update a conversion profile for a harga item.
    
    Request body:
    {
        "harga_item_id": 123,
        "market_unit": "batang",
        "market_price": "240000.00",
        "factor_to_base": "10.000000",
        "density": null,
        "capacity_m3": null,
        "capacity_ton": null,
        "method": "direct"
    }
    
    Response:
    {
        "ok": true,
        "profile_id": 1,
        "message": "Conversion profile saved"
    }
    """
    from .models import ItemConversionProfile, HargaItemProject
    from decimal import Decimal, InvalidOperation
    
    project = _owner_or_404(project_id, request.user)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    
    harga_item_id = data.get("harga_item_id")
    if not harga_item_id:
        return JsonResponse({"ok": False, "error": "harga_item_id required"}, status=400)
    
    # Verify harga item belongs to project
    try:
        harga_item = HargaItemProject.objects.get(id=harga_item_id, project=project)
    except HargaItemProject.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Harga item not found"}, status=404)
    
    # Parse decimal values
    def parse_decimal(val, default=None):
        if val is None or val == '' or val == 'null':
            return default
        try:
            # Handle Indonesian format (dot as thousands, comma as decimal)
            s = str(val).strip()
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return default
    
    market_unit = data.get("market_unit", "").strip()
    market_price = parse_decimal(data.get("market_price"), Decimal("0"))
    factor_to_base = parse_decimal(data.get("factor_to_base"), Decimal("1"))
    density = parse_decimal(data.get("density"))
    capacity_m3 = parse_decimal(data.get("capacity_m3"))
    capacity_ton = parse_decimal(data.get("capacity_ton"))
    method = data.get("method", "direct")
    
    if not market_unit:
        return JsonResponse({"ok": False, "error": "market_unit required"}, status=400)
    if factor_to_base <= 0:
        return JsonResponse({"ok": False, "error": "factor_to_base must be positive"}, status=400)
    
    # Create or update conversion profile
    profile, created = ItemConversionProfile.objects.update_or_create(
        harga_item=harga_item,
        defaults={
            "market_unit": market_unit,
            "market_price": market_price,
            "factor_to_base": factor_to_base,
            "density": density,
            "capacity_m3": capacity_m3,
            "capacity_ton": capacity_ton,
            "method": method,
        }
    )
    
    return JsonResponse({
        "ok": True,
        "profile_id": profile.id,
        "created": created,
        "message": "Conversion profile saved",
    })


# ---------- View: Project Pricing (Profit/Margin) ----------
@login_required
@require_http_methods(["GET","POST"])
def api_project_pricing(request: HttpRequest, project_id: int):
    """
    GET  -> { ok, markup_percent: "10.00", ppn_percent: "11.00", rounding_base: 10000 }
    POST -> body { markup_percent?, ppn_percent?, rounding_base? }
            - markup_percent & ppn_percent: 0..100, parser robust (koma/titik), dp=2
            - rounding_base: integer > 0 (mis. 1000 / 10000 / 100000)
    """
    if request.method == "GET":
        # GET: cek kepemilikan di awal
        project = _owner_or_404(project_id, request.user)
        obj = ProjectPricing.objects.filter(project=project).first()
        markup_default = Decimal("10.00")
        ppn_default = Decimal("11.00")
        rounding_default = 10000
        return JsonResponse({
            "ok": True,
            "markup_percent": to_dp_str(getattr(obj, "markup_percent", markup_default), 2),
            "ppn_percent": to_dp_str(getattr(obj, "ppn_percent", ppn_default), 2),
            "rounding_base": int(getattr(obj, "rounding_base", rounding_default) or rounding_default),
        })

    # === POST: VALIDASI BODY DULU (agar error → 400, bukan 404 dari cek owner) ===
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    # Validasi tiap field yang dikirim (opsional)
    if "markup_percent" in payload:
        dec = parse_any(payload.get("markup_percent"))
        if dec is None or dec < 0 or dec > 100:
            return JsonResponse({"ok": False, "errors": [_err("markup_percent", "Harus angka 0..100")]}, status=400)

    if "ppn_percent" in payload:
        dec = parse_any(payload.get("ppn_percent"))
        if dec is None or dec < 0 or dec > 100:
            return JsonResponse({"ok": False, "errors": [_err("ppn_percent", "Harus angka 0..100")]}, status=400)

    if "rounding_base" in payload:
        try:
            rb = int(payload.get("rounding_base"))
            if rb <= 0:
                raise ValueError
        except Exception:
            return JsonResponse({"ok": False, "errors": [_err("rounding_base", "Harus bilangan bulat > 0")]}, status=400)

    # Lolos validasi → baru cek kepemilikan & simpan
    project = _owner_or_404(project_id, request.user)
    with transaction.atomic():
        obj = _get_or_create_pricing(project)
        updated_fields = []

        # markup_percent (opsional)
        if "markup_percent" in payload:
            dec = parse_any(payload.get("markup_percent"))
            obj.markup_percent = quantize_half_up(dec, 2)
            updated_fields.append("markup_percent")

        # ppn_percent (opsional)
        if "ppn_percent" in payload:
            dec = parse_any(payload.get("ppn_percent"))
            obj.ppn_percent = quantize_half_up(dec, 2)
            updated_fields.append("ppn_percent")

        # rounding_base (opsional)
        if "rounding_base" in payload:
            obj.rounding_base = int(payload.get("rounding_base"))
            updated_fields.append("rounding_base")

        if updated_fields:
            updated_fields.append("updated_at")
            obj.save(update_fields=updated_fields)

            # CACHE FIX: Invalidate cache AFTER transaction commits
            # Pricing changes affect rekap calculations
            transaction.on_commit(lambda: invalidate_rekap_cache(project))

    return JsonResponse({
        "ok": True,
        "markup_percent": to_dp_str(obj.markup_percent, 2),
        "ppn_percent": to_dp_str(obj.ppn_percent, 2),
        "rounding_base": int(getattr(obj, "rounding_base", 10000) or 10000),
    })


# ========== API: Project Parameters (for volume formula calculations) ==========

@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def api_project_parameters(request: HttpRequest, project_id: int):
    """
    GET  -> List all parameters for project
           Returns: { ok: true, parameters: [...] }
    
    POST -> Create new parameter
            Body: { name, value, label?, unit?, description? }
            Returns: { ok: true, parameter: {...}, created: true }
    """
    from .models import ProjectParameter
    
    project = _owner_or_404(project_id, request.user)
    
    if request.method == "GET":
        params = ProjectParameter.objects.filter(project=project).order_by('name')
        return JsonResponse({
            "ok": True,
            "parameters": [
                {
                    "id": p.id,
                    "name": p.name,
                    "value": str(p.value),
                    "label": p.label or p.name,
                    "unit": p.unit or "",
                    "description": p.description or "",
                }
                for p in params
            ]
        })
    
    # POST: Create new parameter
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)
    
    name = str(payload.get("name", "")).strip().lower()
    if not name:
        return JsonResponse({"ok": False, "errors": [_err("name", "Nama parameter wajib diisi")]}, status=400)
    
    # Validate name format (no spaces, alphanumeric + underscore)
    import re
    if not re.match(r'^[a-z_][a-z0-9_]*$', name):
        return JsonResponse({
            "ok": False, 
            "errors": [_err("name", "Nama harus huruf kecil, angka, underscore saja (awali huruf/underscore)")]
        }, status=400)
    
    # Check duplicate
    if ProjectParameter.objects.filter(project=project, name=name).exists():
        return JsonResponse({
            "ok": False, 
            "errors": [_err("name", f"Parameter '{name}' sudah ada")]
        }, status=400)
    
    # Parse value
    value = parse_any(payload.get("value", 0))
    if value is None:
        value = Decimal("0")
    
    param = ProjectParameter.objects.create(
        project=project,
        name=name,
        value=value,
        label=payload.get("label", "") or name,
        unit=payload.get("unit", "") or "",
        description=payload.get("description", "") or "",
    )
    
    return JsonResponse({
        "ok": True,
        "created": True,
        "parameter": {
            "id": param.id,
            "name": param.name,
            "value": str(param.value),
            "label": param.label,
            "unit": param.unit,
            "description": param.description,
        }
    }, status=201)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
@transaction.atomic
def api_project_parameter_detail(request: HttpRequest, project_id: int, param_id: int):
    """
    GET    -> Get single parameter
    PUT    -> Update parameter (value, label, unit, description)
    DELETE -> Delete parameter
    """
    from .models import ProjectParameter
    
    project = _owner_or_404(project_id, request.user)
    param = get_object_or_404(ProjectParameter, id=param_id, project=project)
    
    if request.method == "GET":
        return JsonResponse({
            "ok": True,
            "parameter": {
                "id": param.id,
                "name": param.name,
                "value": str(param.value),
                "label": param.label,
                "unit": param.unit,
                "description": param.description,
            }
        })
    
    if request.method == "DELETE":
        name = param.name
        param.delete()
        return JsonResponse({"ok": True, "deleted": True, "name": name})
    
    # PUT: Update parameter
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)
    
    updated_fields = []
    
    if "value" in payload:
        value = parse_any(payload.get("value"))
        if value is not None:
            param.value = value
            updated_fields.append("value")
    
    if "label" in payload:
        param.label = str(payload.get("label", "")).strip() or param.name
        updated_fields.append("label")
    
    if "unit" in payload:
        param.unit = str(payload.get("unit", "")).strip()
        updated_fields.append("unit")
    
    if "description" in payload:
        param.description = str(payload.get("description", "")).strip()
        updated_fields.append("description")
    
    if updated_fields:
        updated_fields.append("updated_at")
        param.save(update_fields=updated_fields)
    
    return JsonResponse({
        "ok": True,
        "updated": True,
        "parameter": {
            "id": param.id,
            "name": param.name,
            "value": str(param.value),
            "label": param.label,
            "unit": param.unit,
            "description": param.description,
        }
    })


@login_required
@require_POST
@transaction.atomic
def api_project_parameters_sync(request: HttpRequest, project_id: int):
    """
    Bulk sync parameters from localStorage to database.
    
    POST body: {
        "parameters": {
            "code1": { "value": 10, "label": "Label 1" },
            "code2": { "value": 20, "label": "Label 2" },
            ...
        },
        "mode": "merge" | "replace"  // default: merge
    }
    
    - merge: Update existing, create new, keep others
    - replace: Delete all existing, create from payload
    
    Returns: { ok: true, created: N, updated: N, deleted: N }
    """
    from .models import ProjectParameter
    
    project = _owner_or_404(project_id, request.user)
    
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)
    
    params_data = payload.get("parameters", {})
    mode = payload.get("mode", "merge")
    
    if not isinstance(params_data, dict):
        return JsonResponse({"ok": False, "errors": [_err("parameters", "Harus berupa object/dictionary")]}, status=400)
    
    created_count = 0
    updated_count = 0
    deleted_count = 0
    
    import re
    
    if mode == "replace":
        # Delete all existing parameters
        deleted_count = ProjectParameter.objects.filter(project=project).delete()[0]
        
        # Create all from payload
        for code, data in params_data.items():
            name = str(code).strip().lower()
            if not re.match(r'^[a-z_][a-z0-9_]*$', name):
                continue  # Skip invalid names
            
            value = parse_any(data.get("value", 0)) if isinstance(data, dict) else parse_any(data)
            if value is None:
                value = Decimal("0")
            
            label = data.get("label", name) if isinstance(data, dict) else name
            unit = data.get("unit", "") if isinstance(data, dict) else ""
            
            ProjectParameter.objects.create(
                project=project,
                name=name,
                value=value,
                label=label or name,
                unit=unit,
            )
            created_count += 1
    else:
        # Merge mode: update existing, create new
        existing = {p.name: p for p in ProjectParameter.objects.filter(project=project)}
        
        for code, data in params_data.items():
            name = str(code).strip().lower()
            if not re.match(r'^[a-z_][a-z0-9_]*$', name):
                continue  # Skip invalid names
            
            value = parse_any(data.get("value", 0)) if isinstance(data, dict) else parse_any(data)
            if value is None:
                value = Decimal("0")
            
            label = data.get("label", name) if isinstance(data, dict) else name
            unit = data.get("unit", "") if isinstance(data, dict) else ""
            
            if name in existing:
                # Update existing
                param = existing[name]
                param.value = value
                param.label = label or name
                if unit:
                    param.unit = unit
                param.save(update_fields=["value", "label", "unit", "updated_at"])
                updated_count += 1
            else:
                # Create new
                ProjectParameter.objects.create(
                    project=project,
                    name=name,
                    value=value,
                    label=label or name,
                    unit=unit,
                )
                created_count += 1
    
    return JsonResponse({
        "ok": True,
        "created": created_count,
        "updated": updated_count,
        "deleted": deleted_count,
        "mode": mode,
    })


# ---------- View 5: Detail Gabungan ----------
@login_required
@require_POST
@transaction.atomic
def api_save_detail_ahsp_gabungan(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    items = payload.get('items') or []
    total_saved = 0
    all_errors = []

    for i, it in enumerate(items):
        pkj_id = it.get('pekerjaan_id')
        rows = it.get('rows') or []
        if not pkj_id:
            all_errors.append(_err(f"items[{i}].pekerjaan_id", "Wajib")); continue
        pkj = get_object_or_404(Pekerjaan, id=pkj_id, project=project)

        DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()

        to_create = []
        saved_here = 0
        for j, r in enumerate(rows):
            kat = r.get('kategori')
            if kat not in dict(HargaItemProject.KATEGORI_CHOICES):
                all_errors.append(_err(f"items[{i}].rows[{j}].kategori", "Kategori tidak valid")); continue
            kode = (r.get('kode') or '').strip()
            uraian = (r.get('uraian') or '').strip()
            satuan = (r.get('satuan') or '').strip() or None
            koef_dec = parse_any(r.get('koefisien'))
            if koef_dec is None or koef_dec < 0:
                all_errors.append(_err(f"items[{i}].rows[{j}].koefisien", "Harus ≥ 0 dan berupa angka yang valid")); continue
            dp_koef = DECIMAL_SPEC["KOEF"].dp
            koef_q = quantize_half_up(koef_dec, dp_koef)
            if not uraian or not kode:
                all_errors.append(_err(f"items[{i}].rows[{j}]", "kode & uraian wajib")); continue
            hip = _upsert_harga_item(project, kat, kode, uraian, satuan)
            to_create.append(DetailAHSPProject(
                project=project, pekerjaan=pkj, harga_item=hip,
                kategori=kat, kode=kode, uraian=uraian, satuan=satuan, koefisien=koef_q
            ))
            saved_here += 1
        if to_create:
            DetailAHSPProject.objects.bulk_create(to_create, ignore_conflicts=True)
        total_saved += saved_here

    # CACHE FIX: Invalidate cache AFTER transaction commits
    if total_saved > 0:
        transaction.on_commit(lambda: invalidate_rekap_cache(project))

    status_code = 200 if not all_errors else (207 if total_saved > 0 else 400)
    return JsonResponse({"ok": status_code == 200, "saved_rows": total_saved, "errors": all_errors}, status=status_code)



# ---------- View 5.1: Rincian RAB (helper + endpoint) ----------
# Helper: hitung rincian baris per (pekerjaan × item) dengan subtotal = koef × volume × harga
def _compute_rincian_rab(project):
    """
    Return:
      rows: list of dict(
        pekerjaan_id, pekerjaan_kode, pekerjaan_uraian,
        kategori, kode, uraian, satuan,
        koefisien(Decimal), volume(Decimal), harga_satuan(Decimal), subtotal(Decimal)
      )
      totals: dict(total_per_kategori, total_langsung_D)
    """
    dp_harga = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)
    dp_vol   = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', DECIMAL_SPEC["VOL"].dp)

    # Ambil semua baris detail + join harga_item + join pekerjaan (+volume OneToOne) secara efisien.
    qs = (DetailAHSPProject.objects
          .filter(project=project)
          .select_related('harga_item', 'pekerjaan', 'pekerjaan__volume')
          .order_by('pekerjaan__ordering_index', 'kategori', 'id'))

    rows = []
    totals_per_kat = {"TK": Decimal("0"), "BHN": Decimal("0"), "ALT": Decimal("0"), "LAIN": Decimal("0")}

    for d in qs:
        pkj = d.pekerjaan
        hip = d.harga_item
        vol = getattr(getattr(pkj, 'volume', None), 'quantity', Decimal("0"))
        harga = hip.harga_satuan or Decimal("0")
        koef = d.koefisien or Decimal("0")

        subtotal = (koef * vol * harga).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        rows.append({
            "pekerjaan_id": pkj.id,
            "pekerjaan_kode": getattr(pkj, "snapshot_kode", None),
            "pekerjaan_uraian": pkj.snapshot_uraian,
            "kategori": d.kategori,
            "kode": d.kode,
            "uraian": d.uraian,
            "satuan": d.satuan,
            "koefisien": koef,
            "volume": vol,
            "harga_satuan": harga,
            "subtotal": subtotal,
        })
        if d.kategori in totals_per_kat:
            totals_per_kat[d.kategori] += subtotal

    total_langsung = sum(totals_per_kat.values(), Decimal("0"))
    return rows, {"per_kategori": totals_per_kat, "total_langsung": total_langsung}


@login_required
@require_GET
def api_get_rincian_rab(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)

    rows, totals = _compute_rincian_rab(project)

    # Ambil Profit/Margin proyek
    pricing = _get_or_create_pricing(project)
    mp = pricing.markup_percent or Decimal("10.00")   # Decimal

    D = totals["total_langsung"]                      # biaya langsung
    E = (D * (mp / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # Profit/Margin
    grand_total = (D + E).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # dp konversi string
    dp_harga = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)
    dp_koef  = DECIMAL_SPEC["KOEF"].dp
    dp_vol   = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', DECIMAL_SPEC["VOL"].dp)

    def _row_to_wire(r):
        return {
            "pekerjaan_id": r["pekerjaan_id"],
            "pekerjaan_kode": r["pekerjaan_kode"],
            "pekerjaan_uraian": r["pekerjaan_uraian"],
            "kategori": r["kategori"],
            "kode": r["kode"],
            "uraian": r["uraian"],
            "satuan": r["satuan"],
            "koefisien": to_dp_str(r["koefisien"], dp_koef),
            "volume": to_dp_str(r["volume"], dp_vol),
            "harga_satuan": to_dp_str(r["harga_satuan"], dp_harga),
            "subtotal": to_dp_str(r["subtotal"], 2),
        }
    wire_rows = [_row_to_wire(r) for r in rows]

    per_kat_str = {k: to_dp_str(v, 2) for k, v in totals["per_kategori"].items()}
    meta = {
        "total_per_kategori": per_kat_str,
        "total_langsung": to_dp_str(D, 2),           # D
        "markup_percent": to_dp_str(mp, 2),          # %
        "buk_amount": to_dp_str(E, 2),               # E
        "grand_total": to_dp_str(grand_total, 2),    # D+E
    }
    return JsonResponse({"ok": True, "rows": wire_rows, "meta": meta})

@login_required
@require_GET
def api_export_rincian_rab_csv(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)
    rows, totals = _compute_rincian_rab(project)
    pricing = _get_or_create_pricing(project)
    mp = pricing.markup_percent or Decimal("10.00")

    def q(v):
        return (str(v or "")
                .replace(";", ",")
                .replace("\r", " ")
                .replace("\n", " "))

    lines = ["pekerjaan_kode;pekerjaan_uraian;kategori;kode;uraian;satuan;koefisien;volume;harga_satuan;subtotal"]
    use_canon = (request.GET.get("canon") == "1")
    if use_canon:
        dp_harga = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)
        dp_koef  = DECIMAL_SPEC["KOEF"].dp
        dp_vol   = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', DECIMAL_SPEC["VOL"].dp)
    for r in rows:
        if use_canon:
            row = [
                q(r["pekerjaan_kode"]),
                q(r["pekerjaan_uraian"]),
                q(r["kategori"]),
                q(r["kode"]),
                q(r["uraian"]),
                q(r["satuan"]),
                q(to_dp_str(r["koefisien"], dp_koef)),
                q(to_dp_str(r["volume"], dp_vol)),
                q(to_dp_str(r["harga_satuan"], dp_harga)),
                q(to_dp_str(r["subtotal"], 2)),
            ]
        else:
            row = [
                q(r["pekerjaan_kode"]),
                q(r["pekerjaan_uraian"]),
                q(r["kategori"]),
                q(r["kode"]),
                q(r["uraian"]),
                q(r["satuan"]),
                q(r["koefisien"]),
                q(r["volume"]),
                q(r["harga_satuan"]),
                q(r["subtotal"]),
            ]
        lines.append(";".join(row))

    # Footer ringkas (opsional): total & Profit/Margin
    D = totals["total_langsung"]
    E = (D * (mp / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    G = (D + E).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lines += [
        "",
        f"TOTAL LANGSUNG (D);{D}",
        f"Profit/Margin %;{mp}",
        f"Profit/Margin (E);{E}",
        f"GRAND TOTAL (D+E);{G}",
    ]

    csv = "\n".join(lines)
    resp = HttpResponse(csv, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename=\"rincian_rab_{project.id}.csv\"'
    return resp

# ---------- View 6: Rekap ----------

@login_required
def api_list_harga_items(request: HttpRequest, project_id: int):
    """
    List all Harga Items in this project.

    UPDATED (2026-01-09):
    - Shows items that are USED in DetailAHSPExpanded (excludes bundle items)
    - ALSO shows standalone items (no expanded refs AND no detail refs) for import support
    - This ensures imported items appear while bundle items are excluded

    P0 FIX (2025-11-11):
    - Added project_updated_at for optimistic locking
    """
    from django.db.models import Q, Exists, OuterRef
    from .models import DetailAHSPExpanded, DetailAHSPProject
    
    project = _owner_or_404(project_id, request.user)
    
    # Items used in DetailAHSPExpanded (expanded components)
    used_in_expanded = Q(expanded_refs__project=project)
    
    # Standalone items: not referenced anywhere (for import support)
    # These are items created by import that aren't yet linked to any AHSP
    has_expanded_refs = Exists(
        DetailAHSPExpanded.objects.filter(harga_item=OuterRef('pk'))
    )
    has_detail_refs = Exists(
        DetailAHSPProject.objects.filter(harga_item=OuterRef('pk'))
    )
    standalone = ~has_expanded_refs & ~has_detail_refs
    
    qs = (HargaItemProject.objects
          .filter(project=project)
          .filter(used_in_expanded | standalone)
          .distinct()
          .order_by('kode_item'))
    items = list(qs.values('id','kode_item','kategori','uraian','satuan','harga_satuan'))

    if request.GET.get('canon') == '1':
        dp = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)
        for it in items:
            it['harga_satuan'] = to_dp_str(it.get('harga_satuan'), dp)  # "12345.67" atau None

    # === NEW: expose Profit/Margin default 10.00% sebagai string "10.00"
    pricing = _get_or_create_pricing(project)
    meta = {
        "markup_percent": to_dp_str(pricing.markup_percent, 2),
        "project_updated_at": project.updated_at.isoformat() if hasattr(project, 'updated_at') and project.updated_at else None
    }

    return JsonResponse({"ok": True, "items": items, "meta": meta})


@login_required
@require_GET
def api_list_orphaned_harga_items(request: HttpRequest, project_id: int):
    """
    Kembalikan daftar HargaItemProject yang tidak digunakan di DetailAHSP manapun.
    """
    project = _owner_or_404(project_id, request.user)
    items, total_value = detect_orphaned_items(project)
    dp = getattr(
        HargaItemProject._meta.get_field("harga_satuan"),
        "decimal_places",
        DECIMAL_SPEC["HARGA"].dp,
    )

    def _serialize(item):
        last_used = item.get("last_used")
        return {
            "id": item["id"],
            "kode": item["kode"],
            "uraian": item["uraian"],
            "kategori": item["kategori"],
            "satuan": item["satuan"],
            "harga_satuan": to_dp_str(item["harga_satuan"], dp),
            "last_used": last_used.isoformat() if last_used else None,
            "can_delete": item["can_delete"],
            "safety_note": item["safety_note"],
        }

    response_items = [_serialize(item) for item in items]
    meta = {
        "project_updated_at": project.updated_at.isoformat()
        if hasattr(project, "updated_at") and project.updated_at
        else None
    }

    return JsonResponse(
        {
            "ok": True,
            "orphaned_count": len(response_items),
            "total_value": to_dp_str(total_value, 2),
            "orphaned_items": response_items,
            "meta": meta,
        }
    )


@login_required
@require_POST
def api_cleanup_orphaned_harga_items(request: HttpRequest, project_id: int):
    """
    Delete orphaned HargaItemProject berdasarkan daftar item_ids.
    """
    project = _owner_or_404(project_id, request.user)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "ok": False,
                "user_message": "Payload tidak valid. Harap kirim JSON yang benar.",
                "errors": [_err("$", "JSON payload tidak bisa diparsing")],
            },
            status=400,
        )

    item_ids = payload.get("item_ids")
    confirm = payload.get("confirm")

    if not isinstance(item_ids, list) or not item_ids:
        return JsonResponse(
            {
                "ok": False,
                "user_message": "Pilih minimal satu item untuk dihapus.",
                "errors": [_err("item_ids", "Harus berupa list id item")],
            },
            status=400,
        )

    try:
        normalized_ids = [int(item_id) for item_id in item_ids]
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "ok": False,
                "user_message": "Daftar item tidak valid.",
                "errors": [_err("item_ids", "Semua item id harus berupa angka")],
            },
            status=400,
        )

    if not confirm:
        return JsonResponse(
            {
                "ok": False,
                "user_message": "Konfirmasi penghapusan diperlukan.",
                "errors": [_err("confirm", "Set confirm=true untuk melanjutkan")],
            },
            status=400,
        )

    deleted_count, total_value, skipped_ids = delete_orphaned_items(
        project, normalized_ids
    )

    if deleted_count == 0 and not skipped_ids:
        user_message = "Tidak ada orphaned item yang dihapus."
    elif deleted_count == 0 and skipped_ids:
        user_message = (
            "Tidak ada orphaned item yang cocok dengan pilihan Anda. "
            "Kemungkinan sudah dipakai ulang."
        )
    else:
        user_message = f"{deleted_count} orphaned item berhasil dihapus."
        touch_project_change(project, harga=True)

    return JsonResponse(
        {
            "ok": True,
            "deleted_count": deleted_count,
            "total_value_deleted": to_dp_str(total_value, 2),
            "skipped_ids": skipped_ids,
            "message": user_message,
        }
    )


@login_required
@require_GET
def api_get_change_status(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)

    def _parse_dt(name):
        value = request.GET.get(name)
        if not value:
            return None
        dt = parse_datetime(value)
        if dt is None:
            raise ValueError(name)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt

    try:
        since_ahsp = _parse_dt("since_ahsp")
        since_harga = _parse_dt("since_harga")
        pekerjaan_since = _parse_dt("pekerjaan_since")
    except ValueError as exc:
        return JsonResponse(
            {
                "ok": False,
                "errors": [_err(exc.args[0], "Format tanggal tidak valid (ISO8601).")],
            },
            status=400,
        )

    tracker = get_change_tracker(project)
    ahsp_changed_at = (
        tracker.last_ahsp_change.isoformat() if tracker and tracker.last_ahsp_change else None
    )
    harga_changed_at = (
        tracker.last_harga_change.isoformat() if tracker and tracker.last_harga_change else None
    )

    # Get latest pekerjaan change timestamp
    pekerjaan_latest = Pekerjaan.objects.filter(
        project=project,
    ).order_by('-updated_at').values_list('updated_at', flat=True).first()
    pekerjaan_changed_at = pekerjaan_latest.isoformat() if pekerjaan_latest else None

    # Get latest volume change timestamp (VolumePekerjaan)
    volume_changed_at = None
    try:
        from detail_project.models import VolumePekerjaan
        volume_latest = VolumePekerjaan.objects.filter(
            pekerjaan__project=project,
        ).order_by('-updated_at').values_list('updated_at', flat=True).first()
        volume_changed_at = volume_latest.isoformat() if volume_latest else None
    except Exception:
        pass

    # Jadwal tracking - placeholder for future implementation
    jadwal_changed_at = None

    pekerjaan_qs = Pekerjaan.objects.filter(
        project=project,
        detail_last_modified__isnull=False,
    )
    if pekerjaan_since:
        pekerjaan_qs = pekerjaan_qs.filter(detail_last_modified__gt=pekerjaan_since)

    affected_count = pekerjaan_qs.count()
    recent = [
        {
            "id": pkj.id,
            "kode": pkj.snapshot_kode,
            "uraian": pkj.snapshot_uraian,
            "last_modified": pkj.detail_last_modified.isoformat() if pkj.detail_last_modified else None,
        }
        for pkj in pekerjaan_qs.order_by("-detail_last_modified")[:10]
    ]

    return JsonResponse(
        {
            "ok": True,
            "ahsp_changed_at": ahsp_changed_at,
            "harga_changed_at": harga_changed_at,
            "pekerjaan_changed_at": pekerjaan_changed_at,
            "volume_changed_at": volume_changed_at,
            "jadwal_changed_at": jadwal_changed_at,
            "affected_pekerjaan_count": affected_count,
            "recent_pekerjaan": recent,
        }
    )


@login_required
@require_GET
def api_get_audit_trail(request: HttpRequest, project_id: int):
    """
    Return audit trail entries with filters + pagination.
    """
    project = _owner_or_404(project_id, request.user)

    def _parse_bool(value, default=True):
        if value is None:
            return default
        return str(value).strip().lower() not in ("0", "false", "no", "off", "")

    def _serialize_entry(entry, include_diff):
        pekerjaan_data = {
            "id": entry.pekerjaan_id,
            "kode": entry.pekerjaan.snapshot_kode if entry.pekerjaan else None,
            "uraian": entry.pekerjaan.snapshot_uraian if entry.pekerjaan else None,
        }
        user_data = None
        if entry.user:
            user_data = {"id": entry.user_id, "username": entry.user.get_username()}

        payload = {
            "id": entry.id,
            "action": entry.action,
            "triggered_by": entry.triggered_by,
            "change_summary": entry.change_summary,
            "created_at": entry.created_at.isoformat(),
            "pekerjaan": pekerjaan_data,
            "user": user_data,
        }
        if include_diff:
            payload["old_data"] = entry.old_data
            payload["new_data"] = entry.new_data
        return payload

    include_diff = _parse_bool(request.GET.get("include_diff"), default=True)
    entry_id = request.GET.get("entry_id")

    base_qs = DetailAHSPAudit.objects.filter(project=project)
    if entry_id:
        try:
            entry_id = int(entry_id)
        except ValueError:
            return JsonResponse(
                {"ok": False, "errors": [_err("entry_id", "Harus angka")]},
                status=400,
            )
        entry = (
            base_qs.select_related("pekerjaan", "user")
            .filter(id=entry_id)
            .first()
        )
        if not entry:
            return JsonResponse(
                {"ok": False, "errors": [_err("entry_id", "Tidak ditemukan")]},
                status=404,
            )
        return JsonResponse({"ok": True, "result": _serialize_entry(entry, include_diff=True)})

    qs = base_qs

    action = request.GET.get("action")
    if action:
        qs = qs.filter(action=action.upper())

    triggered_by = request.GET.get("triggered_by")
    if triggered_by:
        qs = qs.filter(triggered_by=triggered_by)

    pekerjaan_id = request.GET.get("pekerjaan_id")
    if pekerjaan_id:
        try:
            qs = qs.filter(pekerjaan_id=int(pekerjaan_id))
        except ValueError:
            return JsonResponse(
                {
                    "ok": False,
                    "errors": [_err("pekerjaan_id", "Harus angka")],
                },
                status=400,
            )

    date_from = request.GET.get("date_from")
    if date_from:
        try:
            qs = qs.filter(created_at__gte=datetime.fromisoformat(date_from))
        except ValueError:
            return JsonResponse(
                {
                    "ok": False,
                    "errors": [_err("date_from", "Format tanggal tidak valid (YYYY-MM-DD)")],
                },
                status=400,
            )

    date_to = request.GET.get("date_to")
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            qs = qs.filter(created_at__lte=dt_to.replace(hour=23, minute=59, second=59))
        except ValueError:
            return JsonResponse(
                {
                    "ok": False,
                    "errors": [_err("date_to", "Format tanggal tidak valid (YYYY-MM-DD)")],
                },
                status=400,
            )

    page = max(1, int(request.GET.get("page", 1)))
    page_size = max(1, min(100, int(request.GET.get("page_size", 20))))
    total = qs.count()
    start = (page - 1) * page_size
    results = []

    if include_diff:
        entries = list(
            qs.select_related("pekerjaan", "user")[start:start + page_size]
        )
        for entry in entries:
            results.append(_serialize_entry(entry, include_diff=True))
    else:
        entries = list(
            qs.values(
                "id",
                "action",
                "triggered_by",
                "change_summary",
                "created_at",
                "pekerjaan_id",
                "pekerjaan__snapshot_kode",
                "pekerjaan__snapshot_uraian",
                "user_id",
                "user__username",
            )[start:start + page_size]
        )
        for entry in entries:
            pekerjaan_data = {
                "id": entry.get("pekerjaan_id"),
                "kode": entry.get("pekerjaan__snapshot_kode"),
                "uraian": entry.get("pekerjaan__snapshot_uraian"),
            }
            user_data = None
            if entry.get("user_id"):
                user_data = {
                    "id": entry.get("user_id"),
                    "username": entry.get("user__username"),
                }
            results.append(
                {
                    "id": entry.get("id"),
                    "action": entry.get("action"),
                    "triggered_by": entry.get("triggered_by"),
                    "change_summary": entry.get("change_summary"),
                    "created_at": entry.get("created_at").isoformat()
                    if entry.get("created_at")
                    else None,
                    "pekerjaan": pekerjaan_data,
                    "user": user_data,
                }
            )

    pagination = {
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "total_pages": math.ceil(total / page_size) if page_size else 1,
        "has_next": start + page_size < total,
    }

    return JsonResponse({"ok": True, "results": results, "pagination": pagination})

@login_required
def api_get_rekap_rab(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)

    # Ambil hasil penuh dari services (A..G, total = G×volume)
    data = compute_rekap_for_project(project)

    # Ambil pricing JIKA ADA (jangan create default row agar kompatibel dgn test stub)
    pp = None
    try:
        pid = getattr(project, "id", None)
        if pid is not None:
            pp = ProjectPricing.objects.filter(project_id=pid).first()
    except Exception:
        pp = None

    default_proj_mp = Decimal("10.00")  # default yang diharapkan test bila row pricing belum ada

    # Peta override per pekerjaan (hanya jika diperlukan)
    ov_map = {}
    needs_override = any(r.get("markup_eff") in (None, "", 0, 0.0) for r in data)
    if needs_override:
        pids = [r.get("pekerjaan_id") for r in data if r.get("pekerjaan_id")]
        if pids:
            ov_map = dict(
                Pekerjaan.objects
                .filter(project=project, id__in=pids)
                .values_list("id", "markup_override_percent")
            )

    # Suntik markup_eff bila kosong/0; lengkapi F/G/total hanya jika belum ada
    for r in data:
        curr = r.get("markup_eff")
        if curr in (None, "", 0, 0.0):
            ov = ov_map.get(r.get("pekerjaan_id"))
            proj_mp = pp.markup_percent if pp and pp.markup_percent is not None else default_proj_mp
            eff = ov if ov is not None else proj_mp
            r["markup_eff"] = float(eff)

        # FIXED: JANGAN overwrite HSP! HSP sudah diset oleh services = E_base (A+B+C+LAIN tanpa markup)
        # Untuk backward compatibility, tambahkan field terpisah untuk biaya langsung
        try:
            d_direct = float(r.get("D") or 0.0)
        except Exception:
            d_direct = 0.0
        r["biaya_langsung"] = d_direct  # Biaya langsung (A+B+C saja, tanpa LAIN)

        # HSP tetap dipertahankan dari services (E_base = A+B+C+LAIN tanpa markup)
        # Jika HSP belum ada (data lama), gunakan E_base
        if "HSP" not in r or r["HSP"] is None:
            lain = float(r.get("LAIN") or 0.0)
            r["HSP"] = d_direct + lain  # E_base = A+B+C+LAIN

        # Lengkapi F/G/total hanya kalau belum disediakan oleh services
        lain = float(r.get("LAIN") or 0.0)
        e_base = float(r.get("E_base") or (d_direct + lain))
        mp = float(r.get("markup_eff") or 0.0)
        if "F" not in r:
            r["F"] = e_base * (mp / 100.0)
        if "G" not in r:
            r["G"] = e_base + r["F"]
        if "total" not in r:
            vol = float(r.get("volume") or 0.0)
            r["total"] = r["G"] * vol

    # Meta untuk UI: tampilkan default bila row pricing belum ada
    mp_meta = pp.markup_percent if pp and pp.markup_percent is not None else default_proj_mp
    ppn_meta = pp.ppn_percent if pp and pp.ppn_percent is not None else Decimal("11.00")
    rb_meta = int(pp.rounding_base) if pp and getattr(pp, "rounding_base", None) else 10000

    return JsonResponse({
        "ok": True,
        "rows": data,
        "meta": {
            "markup_percent": to_dp_str(mp_meta, 2),
            "ppn_percent": to_dp_str(ppn_meta, 2),
            "rounding_base": rb_meta,
        }
    })

@login_required
@require_GET
def api_get_rekap_kebutuhan(request: HttpRequest, project_id: int):
    """
    Kembalikan rows rekap kebutuhan (agregasi seluruh pekerjaan dalam project).
    Plus meta: counts_per_kategori, n_rows, generated_at.
    """
    project = _owner_or_404(project_id, request.user)
    params = parse_kebutuhan_query_params(request.GET)
    mode = params['mode']
    tahapan_id = params['tahapan_id']
    filters = params['filters']
    search = params['search']
    time_scope = params.get('time_scope')

    try:
        raw_rows = compute_kebutuhan_items(
            project,
            mode=mode,
            tahapan_id=tahapan_id,
            filters=filters,
            time_scope=time_scope,
        )
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    rows, summary = summarize_kebutuhan_rows(raw_rows, search=search)
    scope_active = bool(time_scope and time_scope.get('mode') not in ('', 'all'))
    filters_applied = bool(
        search
        or filters['klasifikasi_ids']
        or filters['sub_klasifikasi_ids']
        or filters['kategori_items']
        or filters['pekerjaan_ids']
        or scope_active
        or (mode == 'tahapan' and tahapan_id)
    )

    summary.update({
        "mode": mode,
        "tahapan_id": tahapan_id,
        "filters": filters,
        "filters_applied": filters_applied,
        "search": search,
        "time_scope": time_scope,
        "time_scope_active": scope_active,
    })

    return JsonResponse({"ok": True, "rows": rows, "meta": summary})




# PHASE 5 TRACK 2.1: DATA VALIDATION ENDPOINT
# ============================================================================

@login_required
@require_GET
def api_validate_rekap_kebutuhan(request, project_id: int):
    """
    Validate data consistency between snapshot and timeline views.

    GET /api/project/<project_id>/rekap-kebutuhan/validate/

    Query params:
    - mode: 'all', 'tahapan', etc.
    - tahapan_id: Optional tahapan filter
    - kategori: Comma-separated list
    - klasifikasi, sub_klasifikasi, pekerjaan_ids: Optional filters
    - period_mode, period_start, period_end: Time scope filters

    Returns JSON:
    {
        "status": "success",
        "validation": {
            "valid": bool,
            "snapshot_total": float,
            "timeline_total": float,
            "difference": float,
            "tolerance": float,
            "snapshot_count": int,
            "timeline_count": int,
            "kategori_breakdown": {...},
            "warnings": [...],
            "timestamp": "2025-12-03T..."
        }
    }
    """
    try:
        project = _owner_or_404(project_id, request.user)
        params = parse_kebutuhan_query_params(request.GET)

        from .services import validate_kebutuhan_data

        validation_result = validate_kebutuhan_data(
            project,
            mode=params['mode'],
            tahapan_id=params['tahapan_id'],
            filters=params['filters'],
            time_scope=params.get('time_scope'),
        )

        return JsonResponse({
            'status': 'success',
            'validation': validation_result,
        })

    except Exception as e:
        logger.exception("[Rekap Kebutuhan] Validation failed for project %s", project_id)
        return JsonResponse({
            'status': 'error',
            'message': f'Validation failed: {str(e)}'
        }, status=500)


# ============== FUNCTION 2: PDF EXPORT (NEW!) ==============
# TAMBAHKAN function baru ini (setelah CSV function di atas):

@login_required
@require_GET
def export_rekap_kebutuhan_pdf(request: HttpRequest, project_id: int):
    """
    Export Rekap Kebutuhan ke format PDF.
    
    Thin controller - delegasi ke RekapKebutuhanExporter.
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)
        
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        params = parse_kebutuhan_query_params(request.GET)
        unit_mode = request.GET.get('unit_mode', 'base')  # 'base' or 'market'
        return manager.export_rekap_kebutuhan(
            'pdf',
            mode=params['mode'],
            tahapan_id=params['tahapan_id'],
            filters=params['filters'],
            search=params['search'],
            time_scope=params.get('time_scope'),
            unit_mode=unit_mode,
        )
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export PDF gagal: {str(e)}'
        }, status=500)


# ============== FUNCTION 3: WORD EXPORT (NEW!) ==============
# TAMBAHKAN function baru ini (setelah PDF function di atas):

@login_required
@require_GET
def export_rekap_kebutuhan_word(request: HttpRequest, project_id: int):
    """
    Export Rekap Kebutuhan ke format Word.
    
    Thin controller - delegasi ke RekapKebutuhanExporter.
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)
        
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        params = parse_kebutuhan_query_params(request.GET)
        unit_mode = request.GET.get('unit_mode', 'base')  # 'base' or 'market'
        return manager.export_rekap_kebutuhan(
            'word',
            mode=params['mode'],
            tahapan_id=params['tahapan_id'],
            filters=params['filters'],
            search=params['search'],
            time_scope=params.get('time_scope'),
            unit_mode=unit_mode,
        )
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export Word gagal: {str(e)}'
        }, status=500)


@login_required
@require_GET
def export_rekap_kebutuhan_json(request: HttpRequest, project_id: int):
    """
    Export Rekap Kebutuhan ke format JSON.

    Thin controller - delegasi ke ExportManager.
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)

        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        params = parse_kebutuhan_query_params(request.GET)
        return manager.export_rekap_kebutuhan(
            'json',
            mode=params['mode'],
            tahapan_id=params['tahapan_id'],
            filters=params['filters'],
            search=params['search'],
            time_scope=params.get('time_scope'),
        )

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export JSON gagal: {str(e)}'
        }, status=500)


@login_required
@require_GET
def export_rekap_kebutuhan_xlsx(request: HttpRequest, project_id: int):
    """
    Export Rekap Kebutuhan ke format Excel (XLSX).
    
    Thin controller - delegasi ke ExportManager.
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)
        
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        params = parse_kebutuhan_query_params(request.GET)
        unit_mode = request.GET.get('unit_mode', 'base')  # 'base' or 'market'
        return manager.export_rekap_kebutuhan(
            'xlsx',
            mode=params['mode'],
            tahapan_id=params['tahapan_id'],
            filters=params['filters'],
            search=params['search'],
            time_scope=params.get('time_scope'),
            unit_mode=unit_mode,
        )
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export Excel gagal: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def api_pekerjaan_pricing(request: HttpRequest, project_id: int, pekerjaan_id: int):
    """
    GET  → kembalikan {project_markup, override_markup, effective_markup}
    POST → terima {"override_markup": "12,5"} atau null untuk clear
    """
    from .numeric import parse_any, to_dp_str

    project = _owner_or_404(project_id, request.user)
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    # Dapatkan default proyek
    try:
        from .models import ProjectPricing
        pp = ProjectPricing.objects.filter(project=project).first()
        proj_mp = pp.markup_percent if pp else Decimal("10")
    except Exception:
        proj_mp = Decimal("10")

    if request.method == "GET":
        ov = getattr(pkj, "markup_override_percent", None)
        eff = ov if ov is not None else proj_mp
        return JsonResponse({
            "ok": True,
            "project_markup": to_dp_str(proj_mp, 2),
            "override_markup": (to_dp_str(ov, 2) if ov is not None else None),
            "effective_markup": to_dp_str(eff, 2),
        })

    # POST
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$","Payload JSON tidak valid")]}, status=400)

    raw = payload.get("override_markup", None)
    if raw in (None, ""):
        # clear override
        Pekerjaan.objects.filter(pk=pkj.pk).update(markup_override_percent=None)

        # CACHE FIX: Invalidate cache AFTER transaction commits
        # Rekap berubah bila ada override
        transaction.on_commit(lambda: invalidate_rekap_cache(project))

        # Return updated effective_markup after clearing
        eff = proj_mp
        return JsonResponse({
            "ok": True,
            "cleared": True,
            "project_markup": to_dp_str(proj_mp, 2),
            "override_markup": None,
            "effective_markup": to_dp_str(eff, 2)
        })

    # TIER 1 FIX: Robust validation for override BUK
    try:
        dec = parse_any(raw)
    except Exception:
        return JsonResponse({
            "ok": False,
            "errors": [_err("override_markup", "Format angka tidak valid")]
        }, status=400)

    # Validate range 0-100 with clear error message
    if dec is None:
        return JsonResponse({
            "ok": False,
            "errors": [_err("override_markup", "Format angka tidak valid")]
        }, status=400)

    if dec < 0:
        return JsonResponse({
            "ok": False,
            "errors": [_err("override_markup", "Profit/Margin (BUK) tidak boleh negatif. Masukkan nilai 0–100")]
        }, status=400)

    if dec > 100:
        return JsonResponse({
            "ok": False,
            "errors": [_err("override_markup", "Profit/Margin (BUK) maksimal 100%. Masukkan nilai 0–100")]
        }, status=400)

    # Save and return updated values
    Pekerjaan.objects.filter(pk=pkj.pk).update(markup_override_percent=dec)

    # CACHE FIX: Invalidate cache AFTER transaction commits
    transaction.on_commit(lambda: invalidate_rekap_cache(project))

    eff = dec  # override becomes effective
    return JsonResponse({
        "ok": True,
        "saved": True,
        "project_markup": to_dp_str(proj_mp, 2),
        "override_markup": to_dp_str(dec, 2),
        "effective_markup": to_dp_str(eff, 2)
    })


# ---------- View 7 Volume Formula State (GET/POST di endpoint yang sama) ----------
@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def api_volume_formula_state(request: HttpRequest, project_id: int):
    """
    GET  → kembalikan daftar formula state yang ada untuk project.
            { ok: true, items: [{pekerjaan_id, raw, is_fx}] }
    POST → upsert ringan: body {items:[{pekerjaan_id, raw, is_fx}]}
            - Validasi: pekerjaan milik project & owner
            - Hanya simpan subset yang dikirim
            - Tidak mengubah nilai Volume (quantity)
    """
    project = _owner_or_404(project_id, request.user)

    if request.method == "GET":
        rows = list(
            VolumeFormulaState.objects
            .filter(project=project)
            .values("pekerjaan_id", "raw", "is_fx")
        )
        return JsonResponse({"ok": True, "items": rows})

    # POST
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    items = payload.get("items") or []
    if not isinstance(items, list):
        return JsonResponse({"ok": False, "errors": [_err("items", "Harus berupa list")]}, status=400)

    created = 0
    updated = 0
    errors  = []

    for i, it in enumerate(items):
        pkj_id = it.get("pekerjaan_id")
        raw    = (it.get("raw") or "").strip()
        is_fx  = bool(it.get("is_fx", True))

        if not pkj_id:
            errors.append(_err(f"items[{i}].pekerjaan_id", "Wajib")); continue

        try:
            pkj = Pekerjaan.objects.get(id=pkj_id, project=project)
        except Pekerjaan.DoesNotExist:
            errors.append(_err(f"items[{i}].pekerjaan_id", "Pekerjaan tidak ditemukan di project ini")); continue

        obj, was_created = VolumeFormulaState.objects.update_or_create(
            project=project, pekerjaan=pkj,
            defaults=dict(raw=raw, is_fx=is_fx)
        )
        if was_created: created += 1
        else: updated += 1

    status_code = 400 if errors and (created + updated == 0) else 200
    return JsonResponse(
        {"ok": status_code == 200, "created": created, "updated": updated, "errors": errors},
        status=status_code
    )



# Library untuk PDF (install: pip install reportlab)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Library untuk Word (install: pip install python-docx)
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


# ============== FUNCTION 1: CSV EXPORT (REFACTORED) ==============
# REPLACE function export_rekap_rab_csv() yang lama (line ~1146-1228)
# dengan function ini:

@login_required
@require_GET
def export_rekap_rab_csv(request: HttpRequest, project_id: int):
    """
    Export Rekap RAB ke format CSV.
    
    Thin controller - delegasi ke ExportManager (pilot v2).
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)
        
        # 2. Export via ExportManager (builds 2-page payload)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_rekap_rab('csv')
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export CSV gagal: {str(e)}'
        }, status=500)


# ============== FUNCTION 2: PDF EXPORT (REFACTORED) ==============
# REPLACE function export_rekap_rab_pdf() yang lama (line ~1231-1405)
# dengan function ini:

@login_required
@require_GET
def export_rekap_rab_pdf(request: HttpRequest, project_id: int):
    """
    Export Rekap RAB ke format PDF.
    
    Thin controller - delegasi ke ExportManager (pilot v2).
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)
        
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_rekap_rab('pdf')
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export PDF gagal: {str(e)}'
        }, status=500)


# ============== FUNCTION 3: WORD EXPORT (REFACTORED) ==============
# REPLACE function export_rekap_rab_word() yang lama (line ~1408-1605)
# dengan function ini:

@login_required
@require_GET
def export_rekap_rab_word(request: HttpRequest, project_id: int):
    """
    Export Rekap RAB ke format Word.

    Thin controller - delegasi ke ExportManager (pilot v2).
    """
    try:
        # 1. Auth & get project
        project = _owner_or_404(project_id, request.user)

        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_rekap_rab('word')

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export Word gagal: {str(e)}'
        }, status=500)


@login_required
@require_GET
def export_rekap_rab_xlsx(request: HttpRequest, project_id: int):
    """
    Export Rekap RAB ke format XLSX (Excel).
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_rekap_rab('xlsx')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export XLSX gagal: {str(e)}'
        }, status=500)


@login_required
@require_GET
def export_rekap_rab_json(request: HttpRequest, project_id: int):
    """
    Export Rekap RAB ke format JSON.
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_rekap_rab('json')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export JSON gagal: {str(e)}'
        }, status=500)


# ============================================================================
# EXPORT: VOLUME PEKERJAAN (CSV / PDF / WORD)
# ============================================================================

@login_required
@require_GET
def export_volume_pekerjaan_xlsx(request: HttpRequest, project_id: int):
    """Export Volume Pekerjaan to Excel (xlsx) with formula references"""
    try:
        project = _owner_or_404(project_id, request.user)
        # Extract parameters from query string (optional: ?params={"panjang":100,"lebar":50})
        parameters = _extract_parameters_from_request(request)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_volume_pekerjaan('xlsx', parameters=parameters)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export Excel gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_volume_pekerjaan_pdf(request: HttpRequest, project_id: int):
    """Export Volume Pekerjaan to PDF"""
    try:
        project = _owner_or_404(project_id, request.user)
        # Extract parameters from query string
        parameters = _extract_parameters_from_request(request)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_volume_pekerjaan('pdf', parameters=parameters)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export PDF gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_volume_pekerjaan_word(request: HttpRequest, project_id: int):
    """Export Volume Pekerjaan to Word"""
    try:
        project = _owner_or_404(project_id, request.user)
        # Extract parameters from query string
        parameters = _extract_parameters_from_request(request)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_volume_pekerjaan('word', parameters=parameters)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export Word gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_volume_pekerjaan_json(request: HttpRequest, project_id: int):
    """Export Volume Pekerjaan to JSON"""
    try:
        project = _owner_or_404(project_id, request.user)
        # Extract parameters from query string
        parameters = _extract_parameters_from_request(request)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_volume_pekerjaan('json', parameters=parameters)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export JSON gagal: {str(e)}'}, status=500)


# ============================================================================
# EXPORT: HARGA ITEMS (CSV / PDF / WORD)
# ============================================================================

@login_required
@require_GET
def export_harga_items_csv(request: HttpRequest, project_id: int):
    """Export Harga Items to CSV"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_harga_items('csv')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export CSV gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_harga_items_pdf(request: HttpRequest, project_id: int):
    """Export Harga Items to PDF"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_harga_items('pdf')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export PDF gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_harga_items_word(request: HttpRequest, project_id: int):
    """Export Harga Items to Word"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_harga_items('word')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export Word gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_harga_items_xlsx(request: HttpRequest, project_id: int):
    """Export Harga Items to Excel XLSX"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_harga_items('xlsx')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export XLSX gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_harga_items_json(request: HttpRequest, project_id: int):
    """Export Harga Items to JSON file"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .models import HargaItemProject, ItemConversionProfile
        from decimal import Decimal
        import json
        from datetime import datetime
        
        # Fetch harga items with conversion profiles
        items_qs = (
            HargaItemProject.objects
            .filter(project=project, expanded_refs__project=project)
            .distinct()
            .select_related('conversion_profile')
            .order_by('kategori', 'kode_item')
        )
        
        # Kategori labels
        kategori_labels = {
            'TK': 'Tenaga Kerja',
            'BHN': 'Bahan',
            'ALT': 'Alat',
            'LAIN': 'Lainnya'
        }
        
        items_data = []
        for item in items_qs:
            item_dict = {
                'id': item.id,
                'kode_item': item.kode_item,
                'uraian': item.uraian,
                'satuan': item.satuan,
                'kategori': item.kategori,
                'kategori_label': kategori_labels.get(item.kategori, item.kategori),
                'harga_satuan': float(item.harga_satuan) if item.harga_satuan else None,
            }
            
            # Add conversion profile if exists
            try:
                if hasattr(item, 'conversion_profile') and item.conversion_profile:
                    conv = item.conversion_profile
                    item_dict['conversion'] = {
                        'market_unit': conv.market_unit,
                        'market_price': float(conv.market_price) if conv.market_price else None,
                        'factor_to_base': float(conv.factor_to_base) if conv.factor_to_base else None,
                        'density': float(conv.density) if conv.density else None,
                        'capacity_m3': float(conv.capacity_m3) if conv.capacity_m3 else None,
                        'capacity_ton': float(conv.capacity_ton) if conv.capacity_ton else None,
                        'method': conv.method,
                    }
            except Exception:
                pass
            
            items_data.append(item_dict)
        
        # Build export data
        export_data = {
            'export_info': {
                'type': 'harga_items',
                'project_id': project.id,
                'project_name': project.nama_proyek if hasattr(project, 'nama_proyek') else str(project),
                'exported_at': datetime.now().isoformat(),
                'total_items': len(items_data),
            },
            'items': items_data,
        }
        
        # Create response
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        response = HttpResponse(json_content, content_type='application/json')
        filename = f"harga_items_{project.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export JSON gagal: {str(e)}'}, status=500)


# ============================================================================
# EXPORT: RINCIAN AHSP (CSV / PDF / WORD)
# ============================================================================

@login_required
@require_GET
def export_rincian_ahsp_csv(request: HttpRequest, project_id: int):
    """Export Rincian AHSP to CSV"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_rincian_ahsp('csv')
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export CSV gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_rincian_ahsp_pdf(request: HttpRequest, project_id: int):
    """Export Rincian AHSP to PDF"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        orientation = request.GET.get('orientation')
        return manager.export_rincian_ahsp('pdf', orientation=orientation)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export PDF gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_rincian_ahsp_word(request: HttpRequest, project_id: int):
    """Export Rincian AHSP to Word"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        orientation = request.GET.get('orientation')
        return manager.export_rincian_ahsp('word', orientation=orientation)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export Word gagal: {str(e)}'}, status=500)


@login_required
@require_GET
def export_rincian_ahsp_xlsx(request: HttpRequest, project_id: int):
    """Export Rincian AHSP to Excel XLSX"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        orientation = request.GET.get('orientation')
        return manager.export_rincian_ahsp('xlsx', orientation=orientation)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export XLSX gagal: {str(e)}'}, status=500)


# ============================================================================
# EXPORT: JADWAL PEKERJAAN (CSV / PDF / WORD / XLSX)
# ============================================================================


@login_required
@require_http_methods(["GET", "POST"])
def export_jadwal_pekerjaan_csv(request: HttpRequest, project_id: int):
    """
    Export Jadwal Pekerjaan to CSV.

    Supports 3 report types:
    - full: Rekap Laporan (all weeks)
    - monthly: Laporan Bulanan (monthly aggregation)
    - weekly: Laporan Mingguan (weekly with date ranges)
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        attachments = _parse_export_attachments(request)
        parameters = _parse_export_parameters(request)
        return manager.export_jadwal_pekerjaan('csv', attachments=attachments, parameters=parameters)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export CSV gagal: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def export_jadwal_pekerjaan_pdf(request: HttpRequest, project_id: int):
    """
    Export Jadwal Pekerjaan to PDF.

    Supports 3 report types:
    - full: Rekap Laporan (Grid + Gantt + Kurva S, all weeks)
    - monthly: Laporan Bulanan (Grid monthly + Kurva S monthly)
    - weekly: Laporan Mingguan (Grid weekly + Kurva S weekly with date ranges)
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        attachments = _parse_export_attachments(request)
        parameters = _parse_export_parameters(request)
        return manager.export_jadwal_pekerjaan('pdf', attachments=attachments, parameters=parameters)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export PDF gagal: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def export_jadwal_pekerjaan_word(request: HttpRequest, project_id: int):
    """
    Export Jadwal Pekerjaan to Word.

    Supports 3 report types:
    - full: Rekap Laporan (Grid + Gantt + Kurva S, all weeks)
    - monthly: Laporan Bulanan (Grid monthly + Kurva S monthly)
    - weekly: Laporan Mingguan (Grid weekly + Kurva S weekly with date ranges)
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        attachments = _parse_export_attachments(request)
        parameters = _parse_export_parameters(request)
        return manager.export_jadwal_pekerjaan('word', attachments=attachments, parameters=parameters)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export Word gagal: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def export_jadwal_pekerjaan_xlsx(request: HttpRequest, project_id: int):
    """
    Export Jadwal Pekerjaan to XLSX.

    Supports 3 report types:
    - full: Rekap Laporan (Grid + Gantt + Kurva S, all weeks)
    - monthly: Laporan Bulanan (Grid monthly + Kurva S monthly)
    - weekly: Laporan Mingguan (Grid weekly + Kurva S weekly with date ranges)
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        attachments = _parse_export_attachments(request)
        parameters = _parse_export_parameters(request)
        return manager.export_jadwal_pekerjaan('xlsx', attachments=attachments, parameters=parameters)
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export XLSX gagal: {str(e)}'}, status=500)


# ============================================================================
# EXPORT: JADWAL PEKERJAAN PROFESSIONAL (Laporan Tertulis)
# ============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def export_jadwal_pekerjaan_professional(request: HttpRequest, project_id: int):
    """
    Export Jadwal Pekerjaan sebagai Laporan Tertulis profesional.

    Generates formal written reports with:
    - Cover page
    - Executive summary (for monthly/weekly)
    - Comparison tables (this period vs previous)
    - Separated Planned/Actual sections (for rekap)
    - Kurva S and Gantt charts
    - Signature section

    Query/Body Parameters:
    - report_type: 'rekap' | 'monthly' | 'weekly' (default: 'rekap')
    - period: Month number (1-based) for monthly, Week number for weekly
    - format: 'pdf' | 'word' (default: 'pdf')
    - attachments: Chart attachments (POST only)
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)

        # Parse parameters
        if request.method == 'POST':
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                payload = {}
        else:
            payload = {}

        # Get parameters from query or payload
        report_type = request.GET.get('report_type') or payload.get('report_type', 'rekap')
        period_str = request.GET.get('period') or payload.get('period')
        format_type = request.GET.get('format') or payload.get('format', 'pdf')
        
        # DEBUG: Trace period parameter from frontend
        print(f"[views_api] DEBUG export_jadwal_pekerjaan_professional called:")
        print(f"  - report_type: {report_type}")
        print(f"  - period_str (raw): {period_str}")
        print(f"  - format_type: {format_type}")
        print(f"  - payload keys: {list(payload.keys()) if payload else 'empty'}")
        
        # Parse months parameter for multi-month export (NEW)
        months_raw = request.GET.get('months') or payload.get('months')
        months = None
        if months_raw:
            try:
                if isinstance(months_raw, list):
                    months = [int(m) for m in months_raw]
                elif isinstance(months_raw, str):
                    months = [int(m.strip()) for m in months_raw.split(',') if m.strip()]
                # Validate months are positive integers
                if months and any(m < 1 for m in months):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid months: all values must be positive integers.'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'status': 'error',
                    'message': f"Invalid months format: {months_raw}. Must be comma-separated integers or list."
                }, status=400)

        # Validate report_type
        if report_type not in ('rekap', 'monthly', 'weekly'):
            return JsonResponse({
                'status': 'error',
                'message': f"Invalid report_type: {report_type}. Must be 'rekap', 'monthly', or 'weekly'."
            }, status=400)

        # Validate format
        if format_type not in ('pdf', 'word', 'xlsx'):
            return JsonResponse({
                'status': 'error',
                'message': f"Invalid format: {format_type}. Must be 'pdf', 'word', or 'xlsx'."
            }, status=400)

        # Parse period for monthly/weekly (backward compatibility for single month/week)
        period = None
        if period_str:
            try:
                period = int(period_str)
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Invalid period: {period_str}. Must be an integer."
                }, status=400)

        # Parse weeks parameter for multi-week export (NEW)
        weeks_raw = request.GET.get('weeks') or payload.get('weeks')
        weeks = None
        if weeks_raw:
            try:
                if isinstance(weeks_raw, list):
                    weeks = [int(w) for w in weeks_raw]
                elif isinstance(weeks_raw, str):
                    weeks = [int(w.strip()) for w in weeks_raw.split(',') if w.strip()]
                # Validate weeks are positive integers
                if weeks and any(w < 1 for w in weeks):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid weeks: all values must be positive integers.'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'status': 'error',
                    'message': f"Invalid weeks format: {weeks_raw}. Must be comma-separated integers or list."
                }, status=400)

        # Parse attachments (for POST)
        attachments = _parse_export_attachments(request)
        
        # Parse gantt_data (structured data for backend Gantt rendering)
        gantt_data = None
        if request.method == 'POST' and request.body:
            try:
                # json module already imported at top of file
                body = json.loads(request.body.decode('utf-8'))
                gantt_data = body.get('gantt_data')
            except (ValueError, KeyError, UnicodeDecodeError):
                pass

        return manager.export_jadwal_professional(
            format_type=format_type,
            report_type=report_type,
            period=period,
            months=months,  # NEW: pass months list
            weeks=weeks,    # NEW: pass weeks list
            attachments=attachments,
            gantt_data=gantt_data
        )
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export Professional gagal: {str(e)}'
        }, status=500)


# ============================================================================
# DEEP COPY PROJECT (FASE 3.1.1 - Enhanced Error Handling)
# ============================================================================

@login_required
@require_POST
def api_deep_copy_project(request: HttpRequest, project_id: int):
    """
    Deep copy a project with all related data (Enhanced with detailed error handling).

    POST /api/project/<project_id>/deep-copy/

    Body (JSON):
    {
        "new_name": "Project Copy Name",
        "new_tanggal_mulai": "2025-06-01" (optional),
        "copy_jadwal": true (optional, default: true)
    }

    Success Response (201):
    {
        "ok": true,
        "new_project": {...},
        "stats": {...},
        "warnings": [...] (if any),
        "skipped_items": {...} (if any)
    }

    Error Response (400/403/500):
    {
        "ok": false,
        "error_code": 1001,
        "error": "User-friendly error message",
        "error_type": "EMPTY_PROJECT_NAME",
        "details": {...} (optional),
        "support_message": "..." (for critical errors),
        "error_id": "ERR-1234567890" (for support tracking)
    }
    """
    import logging
    import time
    from datetime import datetime
    from .services import DeepCopyService
    from .exceptions import (
        DeepCopyError,
        DeepCopyValidationError,
        DeepCopyPermissionError,
        DeepCopyBusinessError,
        DeepCopyDatabaseError,
        DeepCopySystemError,
        get_error_response,
    )

    logger = logging.getLogger(__name__)

    # Log incoming request
    logger.info(
        f"Deep copy API request received",
        extra={
            'user_id': request.user.id,
            'username': request.user.username,
            'project_id': project_id,
            'ip': request.META.get('REMOTE_ADDR')
        }
    )

    # Verify ownership of source project
    try:
        source_project = _owner_or_404(project_id, request.user)
    except Http404:
        logger.warning(
            f"Project not found or access denied",
            extra={
                'user_id': request.user.id,
                'project_id': project_id
            }
        )
        return JsonResponse({
            "ok": False,
            "error_code": 2001,
            "error": "Project tidak ditemukan atau Anda tidak memiliki akses.",
            "error_type": "PROJECT_NOT_FOUND"
        }, status=404)

    # Parse JSON body
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.warning(
            f"Invalid JSON payload",
            extra={'user_id': request.user.id, 'error': str(e)}
        )
        return JsonResponse({
            "ok": False,
            "error_code": 1008,
            "error": "Format data tidak valid. Pastikan data dikirim dalam format JSON yang benar.",
            "error_type": "INVALID_JSON_PAYLOAD",
            "details": {"json_error": str(e)}
        }, status=400)

    # Basic validation (detailed validation in service layer)
    new_name = payload.get("new_name", "").strip() if payload.get("new_name") else ""

    # Parse optional parameters
    new_tanggal_mulai = None
    if payload.get("new_tanggal_mulai"):
        try:
            new_tanggal_mulai = datetime.strptime(
                payload["new_tanggal_mulai"],
                "%Y-%m-%d"
            ).date()
        except ValueError as e:
            return JsonResponse({
                "ok": False,
                "error_code": 1002,
                "error": "Format tanggal tidak valid. Gunakan format YYYY-MM-DD (contoh: 2025-06-15).",
                "error_type": "INVALID_DATE_FORMAT",
                "details": {"date_value": payload["new_tanggal_mulai"]}
            }, status=400)

    copy_jadwal = payload.get("copy_jadwal", True)
    if not isinstance(copy_jadwal, bool):
        return JsonResponse({
            "ok": False,
            "error_code": 1005,
            "error": "Nilai copy_jadwal harus berupa true atau false.",
            "error_type": "INVALID_BOOLEAN_VALUE"
        }, status=400)

    # Perform deep copy with comprehensive error handling
    try:
        service = DeepCopyService(source_project)

        new_project = service.copy(
            new_owner=request.user,
            new_name=new_name,
            new_tanggal_mulai=new_tanggal_mulai,
            copy_jadwal=copy_jadwal,
        )

        stats = service.get_stats()
        warnings = service.get_warnings()
        skipped = service.get_skipped_items()

        # Log success
        logger.info(
            f"Deep copy successful",
            extra={
                'user_id': request.user.id,
                'source_project_id': project_id,
                'new_project_id': new_project.id,
                'new_project_name': new_project.nama,
                'stats': stats,
                'warnings_count': len(warnings),
                'skipped_count': sum(len(v) for v in skipped.values())
            }
        )

        response_data = {
            "ok": True,
            "new_project": {
                "id": new_project.id,
                "nama": new_project.nama,
                "owner_id": new_project.owner_id,
                "lokasi_project": new_project.lokasi_project,
                "sumber_dana": new_project.sumber_dana,
                "nama_client": new_project.nama_client,
                "tanggal_mulai": new_project.tanggal_mulai.isoformat() if new_project.tanggal_mulai else None,
                "tanggal_selesai": new_project.tanggal_selesai.isoformat() if hasattr(new_project, 'tanggal_selesai') and new_project.tanggal_selesai else None,
                "durasi_hari": new_project.durasi_hari if hasattr(new_project, 'durasi_hari') else None,
                "is_active": new_project.is_active,
            },
            "stats": stats,
        }

        # Add warnings if any
        if warnings:
            response_data["warnings"] = warnings

        # Add skipped items summary if any
        if skipped:
            response_data["skipped_items"] = {
                k: len(v) for k, v in skipped.items()
            }

        return JsonResponse(response_data, status=201)

    # Handle custom exceptions with detailed error responses
    except (DeepCopyValidationError, DeepCopyBusinessError) as e:
        logger.warning(
            f"Validation/Business error during copy",
            extra={
                'user_id': request.user.id,
                'project_id': project_id,
                'error_code': e.code,
                'error_message': e.message
            }
        )
        response, status = get_error_response(e)
        return JsonResponse(response, status=status)

    except DeepCopyPermissionError as e:
        logger.warning(
            f"Permission error during copy",
            extra={
                'user_id': request.user.id,
                'project_id': project_id,
                'error_code': e.code
            }
        )
        response, status = get_error_response(e)
        return JsonResponse(response, status=status)

    except (DeepCopyDatabaseError, DeepCopySystemError) as e:
        # Generate unique error ID for support tracking
        error_id = f"ERR-{int(time.time())}"

        logger.error(
            f"Critical error during copy",
            extra={
                'user_id': request.user.id,
                'project_id': project_id,
                'error_code': e.code,
                'error_id': error_id,
                'error_message': e.message
            },
            exc_info=True
        )

        response, status = get_error_response(e, error_id=error_id)
        return JsonResponse(response, status=status)

    except DeepCopyError as e:
        # Generic deep copy error
        error_id = f"ERR-{int(time.time())}"

        logger.exception(
            f"Deep copy error",
            extra={
                'user_id': request.user.id,
                'project_id': project_id,
                'error_code': e.code,
                'error_id': error_id
            }
        )

        response, status = get_error_response(e, error_id=error_id)
        return JsonResponse(response, status=status)

    # Fallback for truly unexpected errors
    except Exception as e:
        error_id = f"ERR-{int(time.time())}"

        logger.exception(
            f"Unexpected error during copy",
            extra={
                'user_id': request.user.id,
                'project_id': project_id,
                'error_id': error_id,
                'error_type': type(e).__name__
            }
        )

        return JsonResponse({
            "ok": False,
            "error_code": 9999,
            "error": "Terjadi kesalahan tidak terduga. Silakan hubungi administrator dengan kode error dan waktu kejadian.",
            "error_type": "UNKNOWN_ERROR",
            "error_id": error_id,
            "support_message": f"Hubungi support dengan error_id: {error_id}",
            "details": {
                "error_class": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
        }, status=500)


# ============================================================================
# BATCH COPY PROJECT (FASE 3.2)
# ============================================================================

@login_required
@require_POST
def api_batch_copy_project(request: HttpRequest, project_id: int):
    """
    Create multiple copies of a project in one operation (FASE 3.2).

    POST /api/project/<project_id>/batch-copy/

    Body (JSON):
    {
        "base_name": "Project Template",
        "count": 3,
        "new_tanggal_mulai": "2025-06-01" (optional),
        "copy_jadwal": true (optional, default: true)
    }

    Response:
    {
        "ok": true,
        "projects": [
            {
                "id": 123,
                "nama": "Project Template - Copy 1",
                "owner_id": 1,
                ...
            },
            {
                "id": 124,
                "nama": "Project Template - Copy 2",
                "owner_id": 1,
                ...
            },
            ...
        ],
        "summary": {
            "requested": 3,
            "successful": 3,
            "failed": 0,
            "errors": []
        }
    }
    """
    from datetime import datetime
    from .services import DeepCopyService

    # Verify ownership of source project
    source_project = _owner_or_404(project_id, request.user)

    # Parse JSON body
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({
            "ok": False,
            "error": "Invalid JSON payload"
        }, status=400)

    # Validate required fields
    base_name = payload.get("base_name", "").strip()
    if not base_name:
        return JsonResponse({
            "ok": False,
            "error": "Field 'base_name' is required and cannot be empty"
        }, status=400)

    count = payload.get("count")
    if not isinstance(count, int) or count < 1:
        return JsonResponse({
            "ok": False,
            "error": "Field 'count' must be a positive integer"
        }, status=400)

    if count > 50:
        return JsonResponse({
            "ok": False,
            "error": "Maximum 50 copies allowed in one batch (count <= 50)"
        }, status=400)

    # Parse optional parameters
    new_tanggal_mulai = None
    if payload.get("new_tanggal_mulai"):
        try:
            new_tanggal_mulai = datetime.strptime(
                payload["new_tanggal_mulai"],
                "%Y-%m-%d"
            ).date()
        except ValueError:
            return JsonResponse({
                "ok": False,
                "error": "Field 'new_tanggal_mulai' must be in YYYY-MM-DD format"
            }, status=400)

    copy_jadwal = payload.get("copy_jadwal", True)
    if not isinstance(copy_jadwal, bool):
        return JsonResponse({
            "ok": False,
            "error": "Field 'copy_jadwal' must be a boolean"
        }, status=400)

    # Perform batch copy
    try:
        service = DeepCopyService(source_project)

        # Use batch_copy method
        projects = service.batch_copy(
            new_owner=request.user,
            base_name=base_name,
            count=count,
            new_tanggal_mulai=new_tanggal_mulai,
            copy_jadwal=copy_jadwal,
        )

        # Calculate summary
        successful_count = len(projects)
        failed_count = count - successful_count

        # Build response
        projects_data = []
        for proj in projects:
            projects_data.append({
                "id": proj.id,
                "nama": proj.nama,
                "owner_id": proj.owner_id,
                "lokasi_project": proj.lokasi_project,
                "sumber_dana": proj.sumber_dana,
                "nama_client": proj.nama_client,
                "tanggal_mulai": proj.tanggal_mulai.isoformat() if proj.tanggal_mulai else None,
                "tanggal_selesai": proj.tanggal_selesai.isoformat() if proj.tanggal_selesai else None,
                "durasi_hari": proj.durasi_hari,
                "is_active": proj.is_active,
            })

        return JsonResponse({
            "ok": True,
            "projects": projects_data,
            "summary": {
                "requested": count,
                "successful": successful_count,
                "failed": failed_count,
                "errors": [] if failed_count == 0 else ["Some copies failed - check server logs"]
            }
        }, status=201)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            "ok": False,
            "error": f"Batch copy failed: {str(e)}"
        }, status=500)


# ===== CRITICAL FIX: Bundle Expansion Detail Visibility =====
@login_required
@require_GET
def api_get_bundle_expansion(request: HttpRequest, project_id: int, pekerjaan_id: int, bundle_id: int):
    """
    Get expanded components for a bundle (LAIN item with ref_pekerjaan or ref_ahsp).

    Returns DetailAHSPExpanded records for the specified bundle,
    showing all base components (TK/BHN/ALT) with final koefisien (already multiplied).

    Used by Rincian AHSP page to show bundle breakdown on click.

    CRITICAL FIX for: "No Expansion Detail Visibility" issue
    """
    project = _owner_or_404(project_id, request.user)

    # Validate pekerjaan belongs to project
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    # Validate bundle (DetailAHSPProject) belongs to pekerjaan
    bundle = get_object_or_404(
        DetailAHSPProject,
        id=bundle_id,
        project=project,
        pekerjaan=pkj,
        kategori=HargaItemProject.KATEGORI_LAIN
    )

    # Fetch expanded components from DetailAHSPExpanded
    expanded_qs = (
        DetailAHSPExpanded.objects
        .filter(project=project, pekerjaan=pkj, source_detail=bundle)
        .select_related('harga_item')
        .order_by('kategori', 'kode')
    )

    dp_koef = DECIMAL_SPEC["KOEF"].dp
    dp_harga = getattr(
        HargaItemProject._meta.get_field('harga_satuan'),
        'decimal_places',
        DECIMAL_SPEC["HARGA"].dp
    )

    components = []
    for exp in expanded_qs:
        components.append({
            "kategori": exp.kategori,
            "kode": exp.kode,
            "uraian": exp.uraian,
            "satuan": exp.satuan or "",
            "koefisien": to_dp_str(exp.koefisien or Decimal("0"), dp_koef),
            "harga_satuan": to_dp_str(
                exp.harga_item.harga_satuan or Decimal("0"),
                dp_harga
            ),
            "source_bundle_kode": exp.source_bundle_kode,
            "expansion_depth": exp.expansion_depth,
        })

    # Calculate total for verification
    total = sum(
        (exp.koefisien or Decimal("0")) * (exp.harga_item.harga_satuan or Decimal("0"))
        for exp in expanded_qs
    )

    return JsonResponse({
        "ok": True,
        "bundle": {
            "id": bundle.id,
            "kode": bundle.kode,
            "uraian": bundle.uraian,
            "koefisien": to_dp_str(bundle.koefisien or Decimal("0"), dp_koef),
            "ref_pekerjaan_id": bundle.ref_pekerjaan_id,
            "ref_ahsp_id": bundle.ref_ahsp_id,
        },
        "components": components,
        "total": to_dp_str(total, dp_harga),
        "component_count": len(components),
    })


# ============================================================================
# API: KURVA S DATA (Phase 2F.0)
# ============================================================================

@login_required
@require_GET
def api_kurva_s_data(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    API untuk data Kurva S - mengirim harga map dan total biaya project.

    Phase 2F.0: Fix Kurva S calculation to use HARGA (cost) instead of VOLUME.

    Response format:
    {
        "hargaMap": {
            "123": 38500000.00,  // pekerjaan_id → total harga (G × volume)
            "456": 120000000.00,
            ...
        },
        "totalBiayaProject": 250000000.00,  // Sum of all totals (sebelum pajak)
        "volumeMap": {  // Keep for backward compatibility
            "123": 100.0,
            "456": 200.0,
            ...
        },
        "pekerjaanMeta": {  // Additional metadata for debugging/tooltips
            "123": {
                "kode": "A.1.1",
                "uraian": "Pekerjaan Galian",
                "satuan": "m³",
                "harga_satuan": 385000.00,  // G (with markup)
                "volume": 100.0,
                "total": 38500000.00,
                "komponen": {
                    "TK": 100000.00,
                    "BHN": 200000.00,
                    "ALT": 50000.00,
                    "LAIN": 0.00
                }
            },
            ...
        },
        "cached": false
    }

    URL: /detail-project/api/v2/project/<project_id>/kurva-s-data/
    Method: GET
    Auth: login_required
    """
    try:
        from dashboard.models import Project
        project = get_object_or_404(Project, id=project_id)
    except Exception as e:
        logger.error(f"[Kurva S API] Project not found: {project_id}", exc_info=True)
        return JsonResponse({'error': 'Project not found'}, status=404)

    # Check permission (reuse existing pattern from other APIs)
    # TODO: Add proper permission check if needed
    # For now, login_required is sufficient

    # Get rekap data (uses existing compute_rekap_for_project)
    # This already has caching built-in (5 minutes)
    try:
        rekap_rows = compute_rekap_for_project(project)
    except Exception as e:
        logger.error(
            f"[Kurva S API] Failed to compute rekap for project {project_id}",
            exc_info=True
        )
        return JsonResponse({
            'error': 'Failed to compute rekap data',
            'detail': str(e)
        }, status=500)

    # Build response data
    harga_map = {}
    volume_map = {}
    pekerjaan_meta = {}
    total_biaya = Decimal('0.00')

    for row in rekap_rows:
        pkj_id = str(row['pekerjaan_id'])

        # Total harga = G × volume (already calculated in compute_rekap_for_project)
        total_harga = Decimal(str(row.get('total', 0)))

        # Store in maps
        harga_map[pkj_id] = float(total_harga)
        volume_map[pkj_id] = float(row.get('volume', 0))
        total_biaya += total_harga

        # Metadata for tooltips/debugging
        pekerjaan_meta[pkj_id] = {
            'kode': row.get('kode', ''),
            'uraian': row.get('uraian', ''),
            'satuan': row.get('satuan', ''),
            'harga_satuan': float(row.get('G', 0)),  # Unit price with markup
            'harga_satuan_base': float(row.get('E_base', 0)),  # Unit price before markup
            'volume': float(row.get('volume', 0)),
            'total': float(total_harga),
            'markup_percent': float(row.get('markup_eff', 0)),
            'komponen': {
                'TK': float(row.get('A', 0)),
                'BHN': float(row.get('B', 0)),
                'ALT': float(row.get('C', 0)),
                'LAIN': float(row.get('LAIN', 0)),
            }
        }

    response_data = {
        'hargaMap': harga_map,
        'totalBiayaProject': float(total_biaya),
        'volumeMap': volume_map,  # Backward compatibility
        'pekerjaanMeta': pekerjaan_meta,
        'cached': False,  # compute_rekap_for_project handles caching internally
        'timestamp': datetime.now().isoformat(),
        'count': len(rekap_rows),
    }

    logger.info(
        f"[Kurva S API] Served data for project {project_id}: "
        f"{len(harga_map)} pekerjaan, total biaya Rp {total_biaya:,.2f}"
    )

    return JsonResponse(response_data)


@require_GET
@login_required
def api_kurva_s_harga_data(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    API untuk data Kurva S Harga - cost-based S-curve dengan breakdown per minggu.

    Phase 1: Kurva S Harga - Calculate weekly cost progression.

    Formula:
        Weekly Cost = (Total Harga Pekerjaan × Proportion %) / 100
        Where Total Harga = Volume × G (unit price with markup)

    Response format:
    {
        "weeklyData": {
            "planned": [
                {
                    "week_number": 1,
                    "week_start": "2024-01-01",
                    "week_end": "2024-01-07",
                    "cost": 15000000.00,
                    "cumulative_cost": 15000000.00,
                    "cumulative_percent": 6.0,
                    "pekerjaan_breakdown": {
                        "123": 10000000.00,
                        "456": 5000000.00
                    }
                },
                ...
            ],
            "actual": [
                // Same structure as planned
            ]
        },
        "summary": {
            "total_project_cost": 250000000.00,
            "total_weeks": 20,
            "planned_cost": 250000000.00,
            "actual_cost": 180000000.00,
            "actual_vs_planned_percent": 72.0
        },
        "pekerjaanMeta": {
            "123": {
                "kode": "A.1.1",
                "uraian": "Pekerjaan Galian",
                "total_cost": 38500000.00,
                "volume": 100.0,
                "unit_price": 385000.00
            }
        }
    }

    URL: /detail-project/api/v2/project/<project_id>/kurva-s-harga/
    Method: GET
    Auth: login_required
    """
    try:
        from dashboard.models import Project
        project = get_object_or_404(Project, id=project_id)
    except Exception as e:
        logger.error(f"[Kurva S Harga API] Project not found: {project_id}", exc_info=True)
        return JsonResponse({'error': 'Project not found'}, status=404)

    # Step 1: Get rekap data (total cost per pekerjaan) and existing pekerjaan list
    try:
        rekap_rows = compute_rekap_for_project(project)
    except Exception as e:
        logger.error(
            f"[Kurva S Harga API] Failed to compute rekap for project {project_id}",
            exc_info=True
        )
        return JsonResponse({
            'error': 'Failed to compute rekap data',
            'detail': str(e)
        }, status=500)

    rekap_lookup = {row['pekerjaan_id']: row for row in rekap_rows}

    pekerjaan_qs = (
        Pekerjaan.objects
        .filter(project=project)
        .select_related('sub_klasifikasi')
        .order_by('ordering_index')
    )

    # Build pekerjaan cost map: pekerjaan_id → budgeted_cost (fallback ke rekap)
    pekerjaan_costs = {}
    pekerjaan_meta = {}
    total_project_cost = Decimal('0.00')

    for pkj in pekerjaan_qs:
        fallback_row = rekap_lookup.get(pkj.id)
        fallback_data = fallback_row or {}
        fallback_total = Decimal(str(fallback_data.get('total', 0)))
        cost_value = pkj.budgeted_cost if pkj.budgeted_cost and pkj.budgeted_cost > 0 else fallback_total

        pekerjaan_costs[pkj.id] = cost_value
        total_project_cost += cost_value

        pekerjaan_meta[str(pkj.id)] = {
            'kode': fallback_data.get('kode', pkj.snapshot_kode or ''),
            'uraian': fallback_data.get('uraian', pkj.snapshot_uraian or ''),
            'total_cost': float(cost_value),
            'budgeted_cost': float(cost_value),
            'volume': float(fallback_data.get('volume', 0)) if fallback_row else None,
            'unit_price': float(fallback_data.get('G', 0)) if fallback_row else None,
            'satuan': fallback_data.get('satuan', pkj.snapshot_satuan or ''),
        }

    # Fallback: jika total proyek = 0 (belum ada data rekap/harga), gunakan biaya normalisasi
    if total_project_cost <= Decimal('0.00') and pekerjaan_costs:
        logger.warning(
            "[Kurva S Harga API] total_project_cost=0 untuk project %s; "
            "menggunakan biaya normalisasi agar kurva tidak kosong.",
            project_id
        )
        normalized_value = Decimal('1.00')
        total_project_cost = normalized_value * Decimal(len(pekerjaan_costs))
        for pkj in pekerjaan_qs:
            pekerjaan_costs[pkj.id] = normalized_value
            meta = pekerjaan_meta.get(str(pkj.id))
            if meta:
                meta['total_cost'] = float(normalized_value)
                meta['budgeted_cost'] = float(normalized_value)

    # Step 2: Get weekly progress data
    from .models import PekerjaanProgressWeekly

    weekly_progress = PekerjaanProgressWeekly.objects.filter(
        project=project
    ).select_related('pekerjaan').order_by('week_number')

    # Step 3: Aggregate cost per week
    planned_weeks = {}
    actual_weeks = {}
    earned_weeks = {}

    for progress in weekly_progress:
        pkj_id = progress.pekerjaan_id
        week_num = progress.week_number

        if pkj_id not in pekerjaan_costs:
            continue

        total_cost = pekerjaan_costs[pkj_id] or Decimal('0.00')

        planned_cost = total_cost * Decimal(str(progress.planned_proportion)) / Decimal('100')
        earned_cost = total_cost * Decimal(str(progress.actual_proportion)) / Decimal('100')

        if progress.actual_cost is not None:
            actual_cost_value = Decimal(str(progress.actual_cost))
        else:
            actual_cost_value = earned_cost

        if actual_cost_value < Decimal('0.00'):
            actual_cost_value = Decimal('0.00')

        for bucket in (planned_weeks, actual_weeks, earned_weeks):
            if week_num not in bucket:
                bucket[week_num] = {
                    'week_number': week_num,
                    'week_start': progress.week_start_date.isoformat() if progress.week_start_date else None,
                    'week_end': progress.week_end_date.isoformat() if progress.week_end_date else None,
                    'cost': Decimal('0.00'),
                    'pekerjaan_breakdown': {}
                }

        planned_weeks[week_num]['cost'] += planned_cost
        planned_weeks[week_num]['pekerjaan_breakdown'][str(pkj_id)] = float(planned_cost)

        earned_weeks[week_num]['cost'] += earned_cost
        earned_weeks[week_num]['pekerjaan_breakdown'][str(pkj_id)] = float(earned_cost)

        actual_weeks[week_num]['cost'] += actual_cost_value
        actual_weeks[week_num]['pekerjaan_breakdown'][str(pkj_id)] = float(actual_cost_value)

    # Step 4: Calculate cumulative cost
    # Step 4: Calculate cumulative cost
    def calculate_cumulative(weeks_dict):
        weeks_list = sorted(weeks_dict.values(), key=lambda x: x['week_number'])
        cumulative_cost = Decimal('0.00')

        for week in weeks_list:
            cumulative_cost += week['cost']
            week['cumulative_cost'] = float(cumulative_cost)
            week['cumulative_percent'] = float(
                (cumulative_cost / total_project_cost * Decimal('100'))
                if total_project_cost > 0 else Decimal('0')
            )
            # Convert weekly cost to float
            week['cost'] = float(week['cost'])

        return weeks_list

    def _build_evm_dataset(planned_weeks_list, earned_weeks_list, actual_weeks_list, bac_value):
        week_numbers = sorted({
            *(week['week_number'] for week in planned_weeks_list),
            *(week['week_number'] for week in earned_weeks_list),
            *(week['week_number'] for week in actual_weeks_list),
        })

        bac_decimal = bac_value or Decimal('0.00')
        if not week_numbers:
            return {
                'labels': [],
                'pv': [],
                'ev': [],
                'ac': [],
                'pv_percent': [],
                'ev_percent': [],
                'ac_percent': [],
                'spi': [],
                'cpi': [],
                'summary': {
                    'bac': 0.0,
                    'planned_cost': 0.0,
                    'earned_value': 0.0,
                    'actual_cost': 0.0,
                    'eac': 0.0,
                    'etc': 0.0,
                    'vac': 0.0,
                },
            }

        def build_map(weeks_list, key):
            mapping = {}
            last = Decimal('0.00')
            for week in weeks_list:
                value = Decimal(str(week.get(key, 0)))
                last = value
                mapping[week['week_number']] = value
            return mapping, last

        pv_map, _ = build_map(planned_weeks_list, 'cumulative_cost')
        pv_percent_map, _ = build_map(planned_weeks_list, 'cumulative_percent')
        ev_map, _ = build_map(earned_weeks_list, 'cumulative_cost')
        ev_percent_map, _ = build_map(earned_weeks_list, 'cumulative_percent')
        ac_map, _ = build_map(actual_weeks_list, 'cumulative_cost')
        ac_percent_map, _ = build_map(actual_weeks_list, 'cumulative_percent')

        labels = []
        pv_series = []
        ev_series = []
        ac_series = []
        pv_percent_series = []
        ev_percent_series = []
        ac_percent_series = []
        spi_series = []
        cpi_series = []

        last_pv = Decimal('0.00')
        last_ev = Decimal('0.00')
        last_ac = Decimal('0.00')
        last_pv_percent = Decimal('0.00')
        last_ev_percent = Decimal('0.00')
        last_ac_percent = Decimal('0.00')

        for week in week_numbers:
            labels.append(f"W{week}")

            last_pv = pv_map.get(week, last_pv)
            last_ev = ev_map.get(week, last_ev)
            last_ac = ac_map.get(week, last_ac)
            last_pv_percent = pv_percent_map.get(week, last_pv_percent)
            last_ev_percent = ev_percent_map.get(week, last_ev_percent)
            last_ac_percent = ac_percent_map.get(week, last_ac_percent)

            pv_series.append(float(last_pv))
            ev_series.append(float(last_ev))
            ac_series.append(float(last_ac))
            pv_percent_series.append(float(last_pv_percent))
            ev_percent_series.append(float(last_ev_percent))
            ac_percent_series.append(float(last_ac_percent))

            spi = float(last_ev / last_pv) if last_pv > 0 else 0.0
            cpi = float(last_ev / last_ac) if last_ac > 0 else 0.0

            spi_series.append(spi)
            cpi_series.append(cpi)

        actual_total = ac_series[-1] if ac_series else 0.0
        planned_total = pv_series[-1] if pv_series else 0.0
        earned_total = ev_series[-1] if ev_series else 0.0

        current_cpi = cpi_series[-1] if cpi_series else 0.0
        if current_cpi > 0:
            eac_decimal = bac_decimal / Decimal(str(current_cpi))
        else:
            eac_decimal = bac_decimal

        actual_total_decimal = Decimal(str(actual_total))
        etc_decimal = max(Decimal('0.00'), eac_decimal - actual_total_decimal)
        vac_decimal = bac_decimal - eac_decimal

        return {
            'labels': labels,
            'pv': pv_series,
            'ev': ev_series,
            'ac': ac_series,
            'pv_percent': pv_percent_series,
            'ev_percent': ev_percent_series,
            'ac_percent': ac_percent_series,
            'spi': spi_series,
            'cpi': cpi_series,
            'summary': {
                'bac': float(bac_decimal),
                'planned_cost': float(planned_total),
                'earned_value': float(earned_total),
                'actual_cost': float(actual_total),
                'eac': float(eac_decimal),
                'etc': float(etc_decimal),
                'vac': float(vac_decimal),
            }
        }

    planned_list = calculate_cumulative(planned_weeks)
    actual_list = calculate_cumulative(actual_weeks)
    earned_list = calculate_cumulative(earned_weeks)

    # Step 5: Calculate summary
    total_planned_cost = sum(w['cost'] for w in planned_list)
    total_actual_cost = sum(w['cost'] for w in actual_list)

    evm_data = _build_evm_dataset(planned_list, earned_list, actual_list, total_project_cost)

    response_data = {
        'weeklyData': {
            'planned': planned_list,
            'actual': actual_list,
            'earned': earned_list,
        },
        'summary': {
            'total_project_cost': float(total_project_cost),
            'total_weeks': len(planned_weeks),
            'planned_cost': total_planned_cost,
            'actual_cost': total_actual_cost,
            'actual_vs_planned_percent': (
                (total_actual_cost / total_planned_cost * 100.0)
                if total_planned_cost > 0 else 0.0
            )
        },
        'pekerjaanMeta': pekerjaan_meta,
        'timestamp': datetime.now().isoformat(),
        'evm': evm_data,
    }

    logger.info(
        f"[Kurva S Harga API] Served cost data for project {project_id}: "
        f"{len(pekerjaan_costs)} pekerjaan, {len(planned_weeks)} weeks, "
        f"total cost Rp {total_project_cost:,.2f}"
    )

    return JsonResponse(response_data)


@require_GET
@login_required
def api_rekap_kebutuhan_weekly(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    API untuk Rekap Kebutuhan per minggu - resource requirements breakdown by period.

    Phase 1: Rekap Kebutuhan - Calculate weekly resource requirements for procurement planning.

    Formula:
        Weekly Requirement = Item Quantity × (Weekly Proportion / 100)

    Response format:
    {
        "weeklyData": [
            {
                "week_number": 1,
                "week_start": "2024-01-01",
                "week_end": "2024-01-07",
                "items": {
                    "TK": [
                        {
                            "kode": "TK.001",
                            "uraian": "Mandor",
                            "satuan": "OH",
                            "quantity": 5.0,
                            "pekerjaan_breakdown": {"123": 3.0, "456": 2.0}
                        }
                    ],
                    "BHN": [...],
                    "ALT": [...],
                    "LAIN": [...]
                },
                "summary": {
                    "TK": 10,
                    "BHN": 50,
                    "ALT": 5,
                    "LAIN": 2
                }
            }
        ],
        "summary": {
            "total_weeks": 20,
            "total_items": {"TK": 150, "BHN": 1200, "ALT": 80, "LAIN": 30},
            "total_quantity_by_kategori": {
                "TK": 250.5,
                "BHN": 15000.0,
                "ALT": 100.0,
                "LAIN": 50.0
            }
        },
        "metadata": {
            "project_name": "Proyek ABC",
            "generated_at": "2025-11-27T12:00:00"
        }
    }

    URL: /detail-project/api/v2/project/<project_id>/rekap-kebutuhan-weekly/
    Method: GET
    Auth: login_required
    """
    try:
        from dashboard.models import Project
        project = get_object_or_404(Project, id=project_id)
    except Exception as e:
        logger.error(f"[Rekap Kebutuhan API] Project not found: {project_id}", exc_info=True)
        return JsonResponse({'error': 'Project not found'}, status=404)

    from django.core.cache import cache
    from django.db.models import Max
    from .models import PekerjaanProgressWeekly, VolumePekerjaan
    from .services import compute_kebutuhan_items, _kebutuhan_signature

    cache_key = f"rekap_kebutuhan_weekly:{project.id}:v1"
    signature = None
    try:
        base_sig = _kebutuhan_signature(project)
        weekly_ts = PekerjaanProgressWeekly.objects.filter(
            project=project
        ).aggregate(last=Max("updated_at"))["last"]
        signature = tuple(list(base_sig) + [weekly_ts.isoformat() if weekly_ts else "0"])
        cached = cache.get(cache_key)
        if cached and cached.get("sig") == signature:
            return JsonResponse(cached.get("data", {}))
    except Exception:
        logger.warning(
            f"[Rekap Kebutuhan API] Cache precheck failed for project {project_id}",
            exc_info=True
        )

    # Step 1: Get all kebutuhan items (material/tenaga requirements)
    try:
        kebutuhan_items = compute_kebutuhan_items(project)
    except Exception as e:
        logger.error(
            f"[Rekap Kebutuhan API] Failed to compute kebutuhan for project {project_id}",
            exc_info=True
        )
        return JsonResponse({
            'error': 'Failed to compute resource requirements',
            'detail': str(e)
        }, status=500)

    # Build item index: (kategori, kode) → item data
    item_index = {}
    for item in kebutuhan_items:
        key = (item['kategori'], item['kode'])
        item_index[key] = {
            'uraian': item['uraian'],
            'satuan': item['satuan'],
            'total_quantity': Decimal(str(item.get('quantity', 0)))
        }

    # Step 2: Get weekly progress data

    # PERFORMANCE OPTIMIZATION: Prefetch related data to avoid N+1 queries
    # Before: 1000+ queries (N pekerjaan × M components × volume lookups)
    # After: 3-5 queries total
    weekly_progress = PekerjaanProgressWeekly.objects.filter(
        project=project
    ).select_related(
        'pekerjaan'
    ).prefetch_related(
        'pekerjaan__detail_list__harga_item',  # Prefetch components and their items
        'pekerjaan__volume'                     # Prefetch volumes
    ).order_by('week_number')

    # OPTIMIZATION: Build volume lookup dictionary (single query, fast access)
    volume_lookup = {}
    for vol in VolumePekerjaan.objects.filter(
        pekerjaan__project=project
    ).select_related('pekerjaan'):
        volume_lookup[vol.pekerjaan_id] = vol.quantity

    # Step 3: Build week-by-week requirements
    weekly_data = {}

    for progress in weekly_progress:
        week_num = progress.week_number
        pkj = progress.pekerjaan  # Already loaded via select_related
        pkj_id = pkj.id
        proportion = progress.planned_proportion  # Use planned proportion

        # Initialize week data if not exists
        if week_num not in weekly_data:
            weekly_data[week_num] = {
                'week_number': week_num,
                'week_start': progress.week_start_date.isoformat(),
                'week_end': progress.week_end_date.isoformat(),
                'items_by_kategori': {
                    'TK': {},
                    'BHN': {},
                    'ALT': {},
                    'LAIN': {}
                }
            }

        # OPTIMIZATION: Use prefetched components (NO additional query!)
        components = pkj.detail_list.all()  # Already loaded via prefetch_related

        # OPTIMIZATION: Get volume from lookup dict (NO query!)
        volume = Decimal(str(volume_lookup.get(pkj_id, 1.0)))

        for comp in components:
            harga_item = comp.harga_item  # Already loaded via prefetch
            kategori = harga_item.kategori
            kode = harga_item.kode_item or harga_item.uraian
            koefisien = Decimal(str(comp.koefisien))

            # Calculate weekly requirement: volume × koefisien × proportion / 100
            weekly_qty = volume * koefisien * Decimal(str(proportion)) / Decimal('100')

            # Aggregate by item
            items_dict = weekly_data[week_num]['items_by_kategori'][kategori]
            key = kode

            if key not in items_dict:
                items_dict[key] = {
                    'kode': kode,
                    'uraian': harga_item.uraian,
                    'satuan': harga_item.satuan,
                    'quantity': Decimal('0'),
                    'pekerjaan_breakdown': {}
                }

            items_dict[key]['quantity'] += weekly_qty
            items_dict[key]['pekerjaan_breakdown'][str(pkj_id)] = float(weekly_qty)

    # Step 4: Convert to list format and calculate summaries
    weekly_list = []
    total_items_count = {'TK': 0, 'BHN': 0, 'ALT': 0, 'LAIN': 0}
    total_quantity = {'TK': Decimal('0'), 'BHN': Decimal('0'), 'ALT': Decimal('0'), 'LAIN': Decimal('0')}

    for week_num in sorted(weekly_data.keys()):
        week = weekly_data[week_num]

        # Convert items dict to list
        items_by_kategori = {}
        week_summary = {'TK': 0, 'BHN': 0, 'ALT': 0, 'LAIN': 0}

        for kategori in ['TK', 'BHN', 'ALT', 'LAIN']:
            items_list = []
            for item_data in week['items_by_kategori'][kategori].values():
                items_list.append({
                    'kode': item_data['kode'],
                    'uraian': item_data['uraian'],
                    'satuan': item_data['satuan'],
                    'quantity': float(item_data['quantity']),
                    'pekerjaan_breakdown': item_data['pekerjaan_breakdown']
                })

                # Update totals
                total_quantity[kategori] += item_data['quantity']

            items_by_kategori[kategori] = sorted(items_list, key=lambda x: x['kode'])
            week_summary[kategori] = len(items_list)
            total_items_count[kategori] += len(items_list)

        weekly_list.append({
            'week_number': week['week_number'],
            'week_start': week['week_start'],
            'week_end': week['week_end'],
            'items': items_by_kategori,
            'summary': week_summary
        })

    # Step 5: Build response
    response_data = {
        'weeklyData': weekly_list,
        'summary': {
            'total_weeks': len(weekly_list),
            'total_items': total_items_count,
            'total_quantity_by_kategori': {
                'TK': float(total_quantity['TK']),
                'BHN': float(total_quantity['BHN']),
                'ALT': float(total_quantity['ALT']),
                'LAIN': float(total_quantity['LAIN'])
            }
        },
        'metadata': {
            'project_name': project.nama,
            'generated_at': datetime.now().isoformat()
        }
    }

    logger.info(
        f"[Rekap Kebutuhan API] Served data for project {project_id}: "
        f"{len(weekly_list)} weeks, "
        f"TK: {total_items_count['TK']}, BHN: {total_items_count['BHN']}, "
        f"ALT: {total_items_count['ALT']}, LAIN: {total_items_count['LAIN']}"
    )

    if signature is not None:
        cache.set(cache_key, {"sig": signature, "data": response_data}, 300)

    return JsonResponse(response_data)


# ============================================================================
# API: CHART DATA (Single Source of Truth for Grid, Gantt, Kurva S)
# ============================================================================

@require_GET
@login_required
def api_chart_data(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    Unified Chart Data API - Single Source of Truth for all chart views.
    
    This endpoint provides consistent data for:
    - Grid View (columns + rows)
    - Gantt Chart (bar data with progress values)
    - Kurva S (weighted curve data)
    
    Uses JadwalPekerjaanExportAdapter for consistency with PDF/Word export.
    
    Query Parameters:
        timescale: 'weekly' (default) | 'monthly'
        mode: 'planned' | 'actual' | 'both' (default)
    
    Response:
    {
        "timescale": "weekly",
        "columns": [
            {"id": "week_1", "label": "W1", "weekNumber": 1, "startDate": "...", "endDate": "..."}
        ],
        "rows": [
            {"pekerjaanId": 123, "name": "Task A", "type": "pekerjaan", "bobot": 30.5,
             "cells": {"week_1": {"planned": 10, "actual": 8}}}
        ],
        "curveData": {
            "planned": [{"weekNumber": 1, "cumulative": 4.5, "weekly": 4.5, "label": "W1"}],
            "actual": [{"weekNumber": 1, "cumulative": 3.2, "weekly": 3.2, "label": "W1"}]
        },
        "summary": {
            "totalPlanned": 45.5,
            "totalActual": 38.2,
            "variance": -7.3,
            "totalPekerjaan": 88,
            "totalWeeks": 20
        }
    }
    
    URL: /detail-project/api/v2/project/<project_id>/chart-data/
    Method: GET
    Auth: login_required
    """
    from dashboard.models import Project
    from .exports.jadwal_pekerjaan_adapter import JadwalPekerjaanExportAdapter
    from decimal import Decimal
    
    # Get project
    try:
        project = get_object_or_404(Project, id=project_id)
    except Exception:
        return JsonResponse({'error': 'Project not found'}, status=404)
    
    # Parse query parameters
    timescale = request.GET.get('timescale', 'weekly').lower()
    if timescale not in ('weekly', 'monthly'):
        timescale = 'weekly'
    
    mode = request.GET.get('mode', 'both').lower()
    if mode not in ('planned', 'actual', 'both'):
        mode = 'both'
    
    try:
        # Use the export adapter for consistency with PDF/Word export.
        # Avoid full report generation; build only what this API needs.
        adapter = JadwalPekerjaanExportAdapter(project)
        weekly_tahapan = adapter._fetch_weekly_tahapan()
        progress_map, progress_meta = adapter._build_progress_map()
        actual_map = adapter._build_actual_progress_map()

        adapter.project_start, adapter.project_end = adapter._resolve_project_dates(
            weekly_tahapan,
            progress_meta.get("earliest_start"),
            progress_meta.get("latest_end"),
        )

        weekly_columns = adapter._build_weekly_columns(
            weekly_tahapan, progress_meta.get("max_week_number", 0)
        )
        monthly_columns = adapter._build_monthly_columns(weekly_columns)

        # Get base rows with hierarchy info
        base_rows, hierarchy = adapter._build_base_rows()

        kurva_s_raw = adapter._calculate_kurva_s_data(
            progress_map, actual_map, base_rows, weekly_columns
        )
        summary_raw = adapter._calculate_project_summary(
            progress_map, actual_map, base_rows, weekly_columns
        )
        meta = {
            "total_weeks": len(weekly_columns),
            "total_months": len(monthly_columns),
            "total_pekerjaan": len([r for r in base_rows if r.get("type") == "pekerjaan"]),
        }
        
        # Build columns based on timescale
        if timescale == 'monthly':
            columns_raw = monthly_columns
        else:
            columns_raw = weekly_columns
        
        # Transform columns to API format
        columns = []
        for col in columns_raw:
            col_data = {
                'id': f"week_{col.get('week_number', 0)}" if timescale == 'weekly' else f"month_{col.get('month_number', 0)}",
                'label': col.get('label', ''),
                'startDate': col.get('range', '').split(' - ')[0] if col.get('range') else None,
                'endDate': col.get('range', '').split(' - ')[-1] if col.get('range') else None,
            }
            if timescale == 'weekly':
                col_data['weekNumber'] = col.get('week_number', 0)
            else:
                col_data['monthNumber'] = col.get('month_number', 0)
                col_data['childWeeks'] = col.get('child_weeks', [])
            columns.append(col_data)
        
        # Build rows with cell values
        # Cache harga once for bobot calculation
        rekap_cache = adapter._rekap_harga_cache
        if rekap_cache is None:
            rekap_cache = adapter._build_rekap_harga_cache()
            adapter._rekap_harga_cache = rekap_cache
        total_harga = sum(rekap_cache.values()) if rekap_cache else Decimal('1')

        rows = []
        for row in base_rows:
            row_type = row.get('type', 'unknown')
            pekerjaan_id = row.get('pekerjaan_id')
            
            row_data = {
                'id': pekerjaan_id or row.get('id'),
                'name': row.get('uraian', ''),
                'type': row_type,
                'level': hierarchy.get(pekerjaan_id, 0) if pekerjaan_id else 0,
                'volume': row.get('volume_display', ''),
                'unit': row.get('unit', ''),
            }
            
            # Add bobot for pekerjaan rows
            if row_type == 'pekerjaan' and pekerjaan_id:
                harga = rekap_cache.get(int(pekerjaan_id), Decimal("0"))
                bobot = float((harga / total_harga * 100) if total_harga > 0 else 0)
                row_data['bobot'] = round(bobot, 2)
                row_data['pekerjaanId'] = pekerjaan_id
            
            # Build cells with progress values
            cells = {}
            if row_type == 'pekerjaan' and pekerjaan_id:
                for col in columns_raw:
                    if timescale == 'weekly':
                        week_num = col.get('week_number', 0)
                        planned_val = float(progress_map.get((pekerjaan_id, week_num), Decimal('0')))
                        actual_val = float(actual_map.get((pekerjaan_id, week_num), Decimal('0')))
                        col_id = f"week_{week_num}"
                    else:
                        # Monthly: aggregate child weeks
                        child_weeks = col.get('child_weeks', [])
                        planned_val = sum(
                            float(progress_map.get((pekerjaan_id, wk), Decimal('0')))
                            for wk in child_weeks
                        )
                        actual_val = sum(
                            float(actual_map.get((pekerjaan_id, wk), Decimal('0')))
                            for wk in child_weeks
                        )
                        col_id = f"month_{col.get('month_number', 0)}"
                    
                    if mode == 'planned':
                        cells[col_id] = {'planned': planned_val}
                    elif mode == 'actual':
                        cells[col_id] = {'actual': actual_val}
                    else:
                        cells[col_id] = {'planned': planned_val, 'actual': actual_val}
            
            row_data['cells'] = cells
            rows.append(row_data)
        
        # Transform curve data
        curve_data = {'planned': [], 'actual': []}
        
        if timescale == 'weekly':
            # Weekly curve points from adapter
            for point in kurva_s_raw:
                curve_data['planned'].append({
                    'weekNumber': point.get('week', 0),
                    'cumulative': point.get('planned', 0),
                    'label': point.get('label', f"W{point.get('week', 0)}"),
                })
                curve_data['actual'].append({
                    'weekNumber': point.get('week', 0),
                    'cumulative': point.get('actual', 0),
                    'label': point.get('label', f"W{point.get('week', 0)}"),
                })
        else:
            # Monthly: aggregate curve data by month
            month_cols = monthly_columns
            from collections import defaultdict
            monthly_planned = defaultdict(float)
            monthly_actual = defaultdict(float)
            
            for point in kurva_s_raw:
                week_num = point.get('week', 0)
                # Find which month this week belongs to
                for mcol in month_cols:
                    if week_num in mcol.get('child_weeks', []):
                        month_num = mcol.get('month_number', 0)
                        # For cumulative, take the max week's cumulative value
                        if week_num == max(mcol.get('child_weeks', [week_num])):
                            monthly_planned[month_num] = point.get('planned', 0)
                            monthly_actual[month_num] = point.get('actual', 0)
                        break
            
            for mcol in month_cols:
                month_num = mcol.get('month_number', 0)
                curve_data['planned'].append({
                    'monthNumber': month_num,
                    'cumulative': monthly_planned.get(month_num, 0),
                    'label': mcol.get('label', f"M{month_num}"),
                })
                curve_data['actual'].append({
                    'monthNumber': month_num,
                    'cumulative': monthly_actual.get(month_num, 0),
                    'label': mcol.get('label', f"M{month_num}"),
                })
        
        # Build summary
        summary = {
            'totalPlanned': summary_raw.get('total_planned', 0),
            'totalActual': summary_raw.get('total_actual', 0),
            'variance': summary_raw.get('variance', 0),
            'totalPekerjaan': meta.get('total_pekerjaan', len([r for r in base_rows if r.get('type') == 'pekerjaan'])),
            'totalWeeks': meta.get('total_weeks', len(weekly_columns)),
            'totalMonths': meta.get('total_months', len(monthly_columns)),
        }
        
        response_data = {
            'timescale': timescale,
            'columns': columns,
            'rows': rows,
            'curveData': curve_data,
            'summary': summary,
            'timestamp': datetime.now().isoformat(),
        }
        
        logger.info(
            f"[Chart Data API] Served {timescale} data for project {project_id}: "
            f"{len(columns)} columns, {len(rows)} rows"
        )
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(
            f"[Chart Data API] Error for project {project_id}: {str(e)}",
            exc_info=True
        )
        return JsonResponse({
            'error': 'Failed to generate chart data',
            'detail': str(e)
        }, status=500)


# ============================================================================
# EXPORT: LIST PEKERJAAN JSON (for backup/import)
# ============================================================================

@login_required
@require_GET
def export_list_pekerjaan_json(request: HttpRequest, project_id: int):
    """
    Export List Pekerjaan to JSON format for backup/import.
    
    Returns hierarchical structure: Klasifikasi → Sub → Pekerjaan
    """
    try:
        project = _owner_or_404(project_id, request.user)
        
        # Get all data
        k_qs = Klasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')
        s_qs = SubKlasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')
        p_qs = Pekerjaan.objects.filter(project=project).order_by('ordering_index', 'id')
        
        # Build maps
        subs_by_klas = {}
        for s in s_qs:
            subs_by_klas.setdefault(s.klasifikasi_id, []).append(s)
        
        pkj_by_sub = {}
        for p in p_qs:
            pkj_by_sub.setdefault(p.sub_klasifikasi_id, []).append(p)
        
        # Build hierarchical structure
        klasifikasi_data = []
        for k in k_qs:
            k_obj = {
                "name": k.name,
                "ordering_index": k.ordering_index,
                "sub": []
            }
            for s in subs_by_klas.get(k.id, []):
                s_obj = {
                    "name": s.name,
                    "ordering_index": s.ordering_index,
                    "pekerjaan": []
                }
                for p in pkj_by_sub.get(s.id, []):
                    s_obj["pekerjaan"].append({
                        "source_type": _src_to_str(p.source_type),
                        "snapshot_kode": getattr(p, "snapshot_kode", None) or "",
                        "snapshot_uraian": p.snapshot_uraian or "",
                        "snapshot_satuan": p.snapshot_satuan or "",
                        "ordering_index": p.ordering_index,
                        "budgeted_cost": str(p.budgeted_cost or 0),
                        "ref_ahsp_id": p.ref_id if p.source_type == Pekerjaan.SOURCE_REF else None,
                    })
                k_obj["sub"].append(s_obj)
            klasifikasi_data.append(k_obj)
        
        export_data = {
            "export_type": "list_pekerjaan",
            "export_version": "1.0",
            "project_id": project_id,
            "project_name": project.nama,
            "export_date": timezone.now().isoformat(),
            "klasifikasi": klasifikasi_data,
            "stats": {
                "total_klasifikasi": len(klasifikasi_data),
                "total_sub": sum(len(k["sub"]) for k in klasifikasi_data),
                "total_pekerjaan": sum(len(s["pekerjaan"]) for k in klasifikasi_data for s in k["sub"]),
            }
        }
        
        response = JsonResponse(export_data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
        filename = f"list_pekerjaan_{project.nama.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Export List Pekerjaan JSON error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Export JSON gagal: {str(e)}'
        }, status=500)


# ============================================================================
# EXPORT: TEMPLATE AHSP JSON (for backup/import)
# ============================================================================

@login_required
@require_GET
def export_template_ahsp_json(request: HttpRequest, project_id: int):
    """
    Export Template AHSP (all pekerjaan with their AHSP items) to JSON format.

    Returns all pekerjaan with their DetailAHSPProject items for backup/import.
    """
    def sanitize_str(s):
        """Remove unicode replacement characters and ensure valid string"""
        if s is None:
            return ""
        # Replace unicode replacement character (U+FFFD) with empty string
        # Also handle potential encoding issues
        try:
            result = str(s).replace('\ufffd', '').replace('�', '')
            # Ensure the string can be JSON serialized
            result.encode('utf-8')
            return result
        except (UnicodeDecodeError, UnicodeEncodeError):
            # If encoding fails, return ASCII-safe version
            return str(s).encode('ascii', 'ignore').decode('ascii')

    try:
        # Get project with permission check
        project = get_object_or_404(Project, id=project_id, owner=request.user)

        # PERFORMANCE OPTIMIZATION: Use prefetch_related to avoid N+1 queries
        # This loads all pekerjaan and their detail_list in 2 queries instead of N+1
        from django.db.models import Prefetch

        # Prefetch detail AHSP items with ordering
        detail_prefetch = Prefetch(
            'detail_list',
            queryset=DetailAHSPProject.objects.order_by('id')
        )

        # OPTIMIZATION: Add only() to load only required fields, reducing memory
        # Get all pekerjaan with prefetched details
        p_qs = Pekerjaan.objects.filter(
            project=project
        ).only(
            'id', 'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan',
            'source_type', 'ordering_index'
        ).prefetch_related(
            detail_prefetch
        ).order_by('ordering_index', 'id')[:1000]  # LIMIT to first 1000 pekerjaan for safety

        # Build pekerjaan list with items
        pekerjaan_list = []
        for p in p_qs:
            items = []
            # OPTIMIZATION: Use prefetched detail_list instead of dict lookup
            for d in p.detail_list.all():
                try:
                    # Safely convert koefisien to float to ensure JSON serialization
                    koefisien_val = float(d.koefisien) if d.koefisien is not None else 0.0
                except (ValueError, TypeError):
                    koefisien_val = 0.0

                items.append({
                    "kategori": sanitize_str(d.kategori),
                    "kode": sanitize_str(d.kode),
                    "uraian": sanitize_str(d.uraian),
                    "satuan": sanitize_str(d.satuan),
                    "koefisien": koefisien_val,
                })

            pekerjaan_list.append({
                "kode": sanitize_str(getattr(p, "snapshot_kode", None)),
                "uraian": sanitize_str(p.snapshot_uraian),
                "satuan": sanitize_str(p.snapshot_satuan),
                "source_type": _src_to_str(p.source_type),
                "ordering_index": p.ordering_index,
                "items": items,
            })

        # Check total count for limit warning
        total_pekerjaan_count = Pekerjaan.objects.filter(project=project).count()
        is_limited = total_pekerjaan_count > 1000

        export_data = {
            "export_type": "template_ahsp",
            "export_version": "1.0",
            "project_id": project_id,
            "project_name": sanitize_str(project.nama),
            "export_date": timezone.now().isoformat(),
            "pekerjaan_list": pekerjaan_list,
            "stats": {
                "total_pekerjaan": len(pekerjaan_list),
                "total_items": sum(len(p["items"]) for p in pekerjaan_list),
                "is_limited": is_limited,
                "limit": 1000 if is_limited else None,
                "total_in_project": total_pekerjaan_count,
            }
        }

        if is_limited:
            export_data["warning"] = f"Export limited to first 1000 pekerjaan (total: {total_pekerjaan_count})"

        response = JsonResponse(export_data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
        # Sanitize filename: remove special characters, keep only alphanumeric, underscore, dash
        import re
        safe_project_name = re.sub(r'[^\w\-]', '_', sanitize_str(project.nama))
        filename = f"template_ahsp_{safe_project_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        # Use ASCII-only filename in header to avoid encoding issues
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Export Template AHSP JSON error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Export JSON gagal: {str(e)}'
        }, status=500)


# ============================================================================
# EXPORT: FULL PROJECT BACKUP (for migration/restore)
# ============================================================================

def _build_export_data(project, mode='full', template_meta=None, include_progress=False):
    """
    Build export data structure based on mode.
    
    Args:
        project: Project instance
        mode: 'full' or 'template'
            - full: Export everything (project metadata, harga, volume, jadwal)
            - template: Export hierarchy + DetailAHSP only (no prices/volume)
        template_meta: dict with name, description, category for template mode
        include_progress: Include jadwal/progress data (full mode only)
    
    Returns:
        dict: Complete export data structure
    """
    from .models import (
        VolumeFormulaState, ProjectParameter, ProjectPricing,
        TahapPelaksanaan, PekerjaanTahapan, PekerjaanProgressWeekly
    )
    
    is_full = mode == 'full'
    
    # ========== Export Klasifikasi ==========
    klasifikasi_list = []
    klas_map = {}  # old_id -> export_id
    for idx, k in enumerate(Klasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')):
        klas_map[k.id] = idx + 1
        klasifikasi_list.append({
            "_export_id": idx + 1,
            "name": k.name,
            "ordering_index": k.ordering_index,
        })
    
    # ========== Export SubKlasifikasi ==========
    sub_list = []
    sub_map = {}  # old_id -> export_id
    for idx, s in enumerate(SubKlasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')):
        sub_map[s.id] = idx + 1
        sub_list.append({
            "_export_id": idx + 1,
            "_klasifikasi_ref": klas_map.get(s.klasifikasi_id),
            "name": s.name,
            "ordering_index": s.ordering_index,
        })
    
    # ========== Export HargaItemProject (FULL mode only) ==========
    harga_list = []
    harga_map = {}  # old_id -> export_id
    if is_full:
        harga_items = HargaItemProject.objects.filter(project=project).order_by('id')
        for idx, h in enumerate(harga_items):
            harga_map[h.id] = idx + 1
            harga_list.append({
                "_export_id": idx + 1,
                "kode_item": h.kode_item,
                "uraian": h.uraian or "",
                "satuan": h.satuan or "",
                "kategori": h.kategori,
                "harga_satuan": str(h.harga_satuan or 0),
            })
    else:
        # Template mode: build harga_map for DetailAHSP ref but don't export prices
        for h in HargaItemProject.objects.filter(project=project):
            harga_map[h.id] = h.kode_item  # Use kode as reference instead of export_id
    
    # ========== Export ItemConversionProfile (FULL mode only) ==========
    conversion_list = []
    if is_full:
        for cp in ItemConversionProfile.objects.filter(harga_item__project=project).select_related('harga_item'):
            conversion_list.append({
                "_harga_item_ref": harga_map.get(cp.harga_item_id),
                "market_unit": cp.market_unit,
                "market_price": str(cp.market_price or 0),
                "factor_to_base": str(cp.factor_to_base or 1),
                "density": str(cp.density) if cp.density else None,
                "capacity_m3": str(cp.capacity_m3) if cp.capacity_m3 else None,
                "capacity_ton": str(cp.capacity_ton) if cp.capacity_ton else None,
                "method": cp.method,
            })
    
    # ========== Export Pekerjaan ==========
    pekerjaan_list = []
    pekerjaan_map = {}  # old_id -> export_id
    pekerjaan_snapshot_map = {}  # old_id -> snapshot_kode (for template mode bundle refs)
    pekerjaan_qs = Pekerjaan.objects.filter(project=project).order_by('ordering_index', 'id')
    for idx, p in enumerate(pekerjaan_qs):
        pekerjaan_map[p.id] = idx + 1
        pekerjaan_snapshot_map[p.id] = p.snapshot_kode or f"PKJ-{idx+1}"
        
        pekerjaan_data = {
            "_export_id": idx + 1,
            "_sub_klasifikasi_ref": sub_map.get(p.sub_klasifikasi_id),
            "source_type": _src_to_str(p.source_type),
            "snapshot_kode": getattr(p, "snapshot_kode", None) or "",
            "snapshot_uraian": p.snapshot_uraian or "",
            "snapshot_satuan": p.snapshot_satuan or "",
            "ordering_index": p.ordering_index,
            "ref_id": p.ref_id,  # Direct reference to AHSPReferensi
        }
        
        # Full mode includes budgeted_cost
        if is_full:
            pekerjaan_data["budgeted_cost"] = str(p.budgeted_cost or 0)
        
        pekerjaan_list.append(pekerjaan_data)
    
    # ========== Export VolumePekerjaan (FULL mode only) ==========
    volume_list = []
    if is_full:
        for v in VolumePekerjaan.objects.filter(project=project).select_related('pekerjaan'):
            volume_list.append({
                "_pekerjaan_ref": pekerjaan_map.get(v.pekerjaan_id),
                "quantity": str(v.quantity or 0),
            })
    
    # ========== Export DetailAHSPProject ==========
    detail_list = []
    detail_map = {}
    details = DetailAHSPProject.objects.filter(project=project).select_related(
        'harga_item', 'ref_pekerjaan'
    ).order_by('pekerjaan_id', 'id')
    
    for idx, d in enumerate(details):
        detail_map[d.id] = idx + 1
        
        detail_data = {
            "_export_id": idx + 1,
            "_pekerjaan_ref": pekerjaan_map.get(d.pekerjaan_id),
            "kategori": d.kategori,
            "kode": d.kode,
            "uraian": d.uraian or "",
            "satuan": d.satuan or "",
            "koefisien": str(d.koefisien or 0),
        }
        
        if is_full:
            # Full mode: use export_id reference
            detail_data["_harga_item_ref"] = harga_map.get(d.harga_item_id)
            detail_data["ref_ahsp_id"] = d.ref_ahsp_id
            detail_data["_ref_pekerjaan_ref"] = pekerjaan_map.get(d.ref_pekerjaan_id) if d.ref_pekerjaan_id else None
        else:
            # Template mode: use kode as harga reference, snapshot_kode for bundle
            detail_data["harga_item_kode"] = harga_map.get(d.harga_item_id)  # This is the kode string
            
            # Bundle reference for LAIN category
            if d.kategori == 'LAIN':
                if d.ref_pekerjaan_id:
                    detail_data["bundle_type"] = "pekerjaan"
                    detail_data["bundle_ref_snapshot_kode"] = pekerjaan_snapshot_map.get(d.ref_pekerjaan_id)
                elif d.ref_ahsp_id:
                    detail_data["bundle_type"] = "ahsp"
                    detail_data["bundle_ref_ahsp_id"] = d.ref_ahsp_id
    
        detail_list.append(detail_data)
    
    # ========== Build Export Data ==========
    if is_full:
        # Full mode - complete project backup
        
        # Export VolumeFormulaState
        formula_list = []
        for vf in VolumeFormulaState.objects.filter(project=project):
            formula_list.append({
                "_pekerjaan_ref": pekerjaan_map.get(vf.pekerjaan_id),
                "raw": vf.raw,
                "is_fx": vf.is_fx,
            })
        
        # Export ProjectParameter
        parameter_list = []
        for pp in ProjectParameter.objects.filter(project=project):
            parameter_list.append({
                "name": pp.name,
                "value": str(pp.value),
                "label": pp.label or "",
                "unit": pp.unit or "",
                "description": pp.description or "",
            })
        
        # Export ProjectPricing
        pricing_data = None
        try:
            pricing = project.pricing
            pricing_data = {
                "markup_percent": str(pricing.markup_percent),
                "ppn_percent": str(pricing.ppn_percent),
                "rounding_base": pricing.rounding_base,
            }
        except ProjectPricing.DoesNotExist:
            pass
        
        # Project metadata
        project_data = {
            "nama": project.nama,
            "sumber_dana": project.sumber_dana,
            "lokasi_project": project.lokasi_project,
            "nama_client": project.nama_client,
            "anggaran_owner": str(project.anggaran_owner or 0),
            "tanggal_mulai": project.tanggal_mulai.isoformat() if project.tanggal_mulai else None,
            "tanggal_selesai": project.tanggal_selesai.isoformat() if project.tanggal_selesai else None,
            "durasi_hari": project.durasi_hari,
            "ket_project1": project.ket_project1 or "",
            "ket_project2": project.ket_project2 or "",
            "jabatan_client": project.jabatan_client or "",
            "instansi_client": project.instansi_client or "",
            "nama_kontraktor": project.nama_kontraktor or "",
            "instansi_kontraktor": project.instansi_kontraktor or "",
            "nama_konsultan_perencana": project.nama_konsultan_perencana or "",
            "instansi_konsultan_perencana": project.instansi_konsultan_perencana or "",
            "nama_konsultan_pengawas": project.nama_konsultan_pengawas or "",
            "instansi_konsultan_pengawas": project.instansi_konsultan_pengawas or "",
            "deskripsi": project.deskripsi or "",
            "kategori": project.kategori or "",
            "week_start_day": project.week_start_day,
            "week_end_day": project.week_end_day,
        }
        
        export_data = {
            "export_type": "project_full_backup",
            "export_version": "2.0",
            "export_date": timezone.now().isoformat(),
            "include_progress": include_progress,
            "project": project_data,
            "klasifikasi": klasifikasi_list,
            "sub_klasifikasi": sub_list,
            "harga_items": harga_list,
            "conversion_profiles": conversion_list,
            "pekerjaan": pekerjaan_list,
            "volume": volume_list,
            "detail_ahsp": detail_list,
            "volume_formulas": formula_list,
            "parameters": parameter_list,
            "pricing": pricing_data,
        }
        
        # Optional: Include progress/jadwal data
        if include_progress:
            tahapan_list = []
            tahapan_map = {}
            for idx, t in enumerate(TahapPelaksanaan.objects.filter(project=project).order_by('urutan', 'id')):
                tahapan_map[t.id] = idx + 1
                tahapan_list.append({
                    "_export_id": idx + 1,
                    "nama": t.nama,
                    "urutan": t.urutan,
                })
            
            pekerjaan_tahapan_list = []
            for pt in PekerjaanTahapan.objects.filter(tahap__project=project).select_related('tahap', 'pekerjaan'):
                pekerjaan_tahapan_list.append({
                    "_tahap_ref": tahapan_map.get(pt.tahap_id),
                    "_pekerjaan_ref": pekerjaan_map.get(pt.pekerjaan_id),
                    "bobot": str(pt.bobot or 0),
                })
            
            progress_list = []
            for pw in PekerjaanProgressWeekly.objects.filter(project=project):
                progress_list.append({
                    "_pekerjaan_ref": pekerjaan_map.get(pw.pekerjaan_id),
                    "week_number": pw.week_number,
                    "week_start_date": pw.week_start_date.isoformat() if pw.week_start_date else None,
                    "week_end_date": pw.week_end_date.isoformat() if pw.week_end_date else None,
                    "planned_proportion": str(pw.planned_proportion or 0),
                    "actual_proportion": str(pw.actual_proportion or 0),
                })
            
            export_data["jadwal"] = {
                "tahapan": tahapan_list,
                "pekerjaan_tahapan": pekerjaan_tahapan_list,
                "progress_weekly": progress_list,
            }
    
    else:
        # Template mode - hierarchy + DetailAHSP + Parameters
        
        # Export ProjectParameter for template (reusable across projects)
        parameter_list = []
        for pp in ProjectParameter.objects.filter(project=project):
            parameter_list.append({
                "name": pp.name,
                "value": str(pp.value),
                "label": pp.label or "",
                "unit": pp.unit or "",
                "description": pp.description or "",
            })
        
        # Export VolumeFormulaState for template (reusable formulas)
        formula_list = []
        for vf in VolumeFormulaState.objects.filter(project=project):
            # Only export if pekerjaan was exported
            pkj_ref = pekerjaan_map.get(vf.pekerjaan_id)
            if pkj_ref:
                formula_list.append({
                    "_pekerjaan_ref": pkj_ref,
                    "raw": vf.raw,
                    "is_fx": vf.is_fx,
                })
        
        export_data = {
            "export_type": "project_template",
            "export_version": "2.2",  # Bumped version for formulas
            "export_date": timezone.now().isoformat(),
            "template_meta": template_meta or {
                "name": f"Template dari {project.nama}",
                "description": "",
                "category": "lainnya",
                "source_project": project.nama,
            },
            "klasifikasi": klasifikasi_list,
            "sub_klasifikasi": sub_list,
            "pekerjaan": pekerjaan_list,
            "detail_ahsp": detail_list,
            "parameters": parameter_list,
            "volume_formulas": formula_list,  # NEW v2.2: Volume formulas
            "stats": {
                "total_klasifikasi": len(klasifikasi_list),
                "total_sub": len(sub_list),
                "total_pekerjaan": len(pekerjaan_list),
                "total_detail": len(detail_list),
                "total_parameters": len(parameter_list),
                "total_formulas": len(formula_list),
            }
        }
    
    return export_data


@login_required
@require_GET
def export_project_full_json(request: HttpRequest, project_id: int):
    """
    Export complete project data to JSON format for backup/migration.
    
    Query params:
    - include_progress: 1/0 - Include TahapPelaksanaan and progress data (default: 0)
    
    Returns all project data:
    - Project metadata
    - Klasifikasi → SubKlasifikasi → Pekerjaan
    - HargaItemProject + ItemConversionProfile
    - VolumePekerjaan
    - DetailAHSPProject
    - (Optional) TahapPelaksanaan, PekerjaanTahapan, PekerjaanProgressWeekly
    """
    try:
        project = _owner_or_404(project_id, request.user)
        include_progress = request.GET.get('include_progress', '0') == '1'
        
        # ========== Export Project Metadata ==========
        project_data = {
            "nama": project.nama,
            "sumber_dana": project.sumber_dana,
            "lokasi_project": project.lokasi_project,
            "nama_client": project.nama_client,
            "anggaran_owner": str(project.anggaran_owner or 0),
            "tanggal_mulai": project.tanggal_mulai.isoformat() if project.tanggal_mulai else None,
            "tanggal_selesai": project.tanggal_selesai.isoformat() if project.tanggal_selesai else None,
            "durasi_hari": project.durasi_hari,
            "ket_project1": project.ket_project1 or "",
            "ket_project2": project.ket_project2 or "",
            "jabatan_client": project.jabatan_client or "",
            "instansi_client": project.instansi_client or "",
            "nama_kontraktor": project.nama_kontraktor or "",
            "instansi_kontraktor": project.instansi_kontraktor or "",
            "nama_konsultan_perencana": project.nama_konsultan_perencana or "",
            "instansi_konsultan_perencana": project.instansi_konsultan_perencana or "",
            "nama_konsultan_pengawas": project.nama_konsultan_pengawas or "",
            "instansi_konsultan_pengawas": project.instansi_konsultan_pengawas or "",
            "deskripsi": project.deskripsi or "",
            "kategori": project.kategori or "",
            "week_start_day": project.week_start_day,
            "week_end_day": project.week_end_day,
        }
        
        # ========== Export Klasifikasi ==========
        klasifikasi_list = []
        klas_map = {}  # old_id -> export_id
        for idx, k in enumerate(Klasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')):
            klas_map[k.id] = idx + 1
            klasifikasi_list.append({
                "_export_id": idx + 1,
                "name": k.name,
                "ordering_index": k.ordering_index,
            })
        
        # ========== Export SubKlasifikasi ==========
        sub_list = []
        sub_map = {}  # old_id -> export_id
        for idx, s in enumerate(SubKlasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')):
            sub_map[s.id] = idx + 1
            sub_list.append({
                "_export_id": idx + 1,
                "_klasifikasi_ref": klas_map.get(s.klasifikasi_id),
                "name": s.name,
                "ordering_index": s.ordering_index,
            })
        
        # ========== Export HargaItemProject ==========
        harga_list = []
        harga_map = {}  # old_id -> export_id
        harga_items = HargaItemProject.objects.filter(project=project).order_by('id')
        for idx, h in enumerate(harga_items):
            harga_map[h.id] = idx + 1
            harga_list.append({
                "_export_id": idx + 1,
                "kode_item": h.kode_item,
                "uraian": h.uraian or "",
                "satuan": h.satuan or "",
                "kategori": h.kategori,
                "harga_satuan": str(h.harga_satuan or 0),
            })
        
        # ========== Export ItemConversionProfile ==========
        conversion_list = []
        for cp in ItemConversionProfile.objects.filter(harga_item__project=project).select_related('harga_item'):
            conversion_list.append({
                "_harga_item_ref": harga_map.get(cp.harga_item_id),
                "market_unit": cp.market_unit,
                "market_price": str(cp.market_price or 0),
                "factor_to_base": str(cp.factor_to_base or 1),
                "density": str(cp.density) if cp.density else None,
                "capacity_m3": str(cp.capacity_m3) if cp.capacity_m3 else None,
                "capacity_ton": str(cp.capacity_ton) if cp.capacity_ton else None,
                "method": cp.method,
            })
        
        # ========== Export Pekerjaan ==========
        pekerjaan_list = []
        pekerjaan_map = {}  # old_id -> export_id
        pekerjaan_qs = Pekerjaan.objects.filter(project=project).order_by('ordering_index', 'id')
        for idx, p in enumerate(pekerjaan_qs):
            pekerjaan_map[p.id] = idx + 1
            pekerjaan_list.append({
                "_export_id": idx + 1,
                "_sub_klasifikasi_ref": sub_map.get(p.sub_klasifikasi_id),
                "source_type": _src_to_str(p.source_type),
                "snapshot_kode": getattr(p, "snapshot_kode", None) or "",
                "snapshot_uraian": p.snapshot_uraian or "",
                "snapshot_satuan": p.snapshot_satuan or "",
                "ordering_index": p.ordering_index,
                "budgeted_cost": str(p.budgeted_cost or 0),
                "ref_id": p.ref_id,  # Direct reference to AHSPReferensi
            })
        
        # ========== Export VolumePekerjaan ==========
        volume_list = []
        for v in VolumePekerjaan.objects.filter(project=project).select_related('pekerjaan'):
            volume_list.append({
                "_pekerjaan_ref": pekerjaan_map.get(v.pekerjaan_id),
                "quantity": str(v.quantity or 0),
            })
        
        # ========== Export DetailAHSPProject ==========
        detail_list = []
        detail_map = {}
        details = DetailAHSPProject.objects.filter(project=project).order_by('pekerjaan_id', 'id')
        for idx, d in enumerate(details):
            detail_map[d.id] = idx + 1
            detail_list.append({
                "_export_id": idx + 1,
                "_pekerjaan_ref": pekerjaan_map.get(d.pekerjaan_id),
                "_harga_item_ref": harga_map.get(d.harga_item_id),
                "kategori": d.kategori,
                "kode": d.kode,
                "uraian": d.uraian or "",
                "satuan": d.satuan or "",
                "koefisien": str(d.koefisien or 0),
                "ref_ahsp_id": d.ref_ahsp_id,  # Direct reference
                "_ref_pekerjaan_ref": pekerjaan_map.get(d.ref_pekerjaan_id) if d.ref_pekerjaan_id else None,
            })
        
        # ========== Export VolumeFormulaState ==========
        from .models import VolumeFormulaState, ProjectParameter, ProjectPricing
        formula_list = []
        for vf in VolumeFormulaState.objects.filter(project=project):
            formula_list.append({
                "_pekerjaan_ref": pekerjaan_map.get(vf.pekerjaan_id),
                "raw": vf.raw,
                "is_fx": vf.is_fx,
            })
        
        # ========== Export ProjectParameter ==========
        parameter_list = []
        for pp in ProjectParameter.objects.filter(project=project):
            parameter_list.append({
                "name": pp.name,
                "value": str(pp.value),
                "label": pp.label or "",
                "unit": pp.unit or "",
                "description": pp.description or "",
            })
        
        # ========== Export ProjectPricing ==========
        pricing_data = None
        try:
            pricing = project.pricing
            pricing_data = {
                "markup_percent": str(pricing.markup_percent),
                "ppn_percent": str(pricing.ppn_percent),
                "rounding_base": pricing.rounding_base,
            }
        except ProjectPricing.DoesNotExist:
            pass
        
        # Build export data
        export_data = {
            "export_type": "project_full_backup",
            "export_version": "1.1",  # Bumped version for new fields
            "source_project_id": project_id,
            "export_date": timezone.now().isoformat(),
            "include_progress": include_progress,
            "project": project_data,
            "klasifikasi": klasifikasi_list,
            "sub_klasifikasi": sub_list,
            "harga_items": harga_list,
            "conversion_profiles": conversion_list,
            "pekerjaan": pekerjaan_list,
            "volume_pekerjaan": volume_list,
            "detail_ahsp": detail_list,
            # NEW in v1.1
            "volume_formula_states": formula_list,
            "project_parameters": parameter_list,
            "project_pricing": pricing_data,
        }
        
        # ========== Optional: Export Progress Data ==========
        if include_progress:
            from .models import TahapPelaksanaan, PekerjaanTahapan, PekerjaanProgressWeekly
            
            # TahapPelaksanaan
            tahap_list = []
            tahap_map = {}
            for idx, t in enumerate(TahapPelaksanaan.objects.filter(project=project).order_by('urutan', 'id')):
                tahap_map[t.id] = idx + 1
                tahap_list.append({
                    "_export_id": idx + 1,
                    "nama": t.nama,
                    "urutan": t.urutan,
                    "warna": getattr(t, 'warna', None) or "",
                })
            
            # PekerjaanTahapan
            assignment_list = []
            for a in PekerjaanTahapan.objects.filter(tahapan__project=project):
                assignment_list.append({
                    "_tahap_ref": tahap_map.get(a.tahapan_id),
                    "_pekerjaan_ref": pekerjaan_map.get(a.pekerjaan_id),
                    "proporsi_volume": str(getattr(a, 'proporsi_volume', 0) or 0),
                })
            
            # PekerjaanProgressWeekly
            progress_list = []
            for pw in PekerjaanProgressWeekly.objects.filter(project=project):
                progress_list.append({
                    "_pekerjaan_ref": pekerjaan_map.get(pw.pekerjaan_id),
                    "week_number": pw.week_number,
                    "week_start_date": pw.week_start_date.isoformat() if pw.week_start_date else None,
                    "week_end_date": pw.week_end_date.isoformat() if pw.week_end_date else None,
                    "planned_proportion": str(getattr(pw, 'planned_proportion', 0) or 0),
                    "actual_proportion": str(getattr(pw, 'actual_proportion', 0) or 0),
                })
            
            export_data["tahap_pelaksanaan"] = tahap_list
            export_data["pekerjaan_tahapan"] = assignment_list
            export_data["progress_weekly"] = progress_list
        
        # Stats
        export_data["stats"] = {
            "total_klasifikasi": len(klasifikasi_list),
            "total_sub": len(sub_list),
            "total_pekerjaan": len(pekerjaan_list),
            "total_harga_items": len(harga_list),
            "total_detail_ahsp": len(detail_list),
            "total_volume": len(volume_list),
        }
        if include_progress:
            export_data["stats"]["total_tahap"] = len(tahap_list)
            export_data["stats"]["total_progress"] = len(progress_list)
            # Calculate total project weeks for import comparison
            if project.tanggal_mulai and project.tanggal_selesai:
                from math import ceil
                days = (project.tanggal_selesai - project.tanggal_mulai).days
                export_data["stats"]["total_project_weeks"] = ceil(days / 7) if days > 0 else 0
            else:
                export_data["stats"]["total_project_weeks"] = 0
            # Max week number in progress data
            if progress_list:
                export_data["stats"]["max_week_exported"] = max(p["week_number"] for p in progress_list)
        
        response = JsonResponse(export_data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
        safe_name = project.nama.replace(' ', '_').replace('/', '-')[:50]
        filename = f"project_backup_v1.1_{safe_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Export Project Full JSON error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Export JSON gagal: {str(e)}'
        }, status=500)


# ============================================================================
# IMPORT: PROJECT FROM JSON BACKUP
# ============================================================================

@login_required
@require_POST
@transaction.atomic
def import_project_from_json(request: HttpRequest):
    """
    Import complete project from JSON backup file.
    
    Creates a new project with all related data.
    Uses _export_id references for ID remapping.
    """
    from dashboard.models import Project
    from .models import (
        TahapPelaksanaan, PekerjaanTahapan, PekerjaanProgressWeekly
    )
    from decimal import Decimal
    from datetime import date
    
    try:
        # Parse JSON from request body or file upload
        content_type = request.content_type or ''
        
        if 'multipart' in content_type:
            # Multipart form data - expect file upload
            if not request.FILES.get('file'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'No file uploaded'
                }, status=400)
            import_file = request.FILES['file']
            try:
                data = json.load(import_file)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Invalid JSON file: {str(e)}'
                }, status=400)
        else:
            # Direct JSON body
            try:
                body = request.body
                if not body:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'No file or JSON body provided'
                    }, status=400)
                data = json.loads(body)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Invalid JSON: {str(e)}'
                }, status=400)
        
        # Validate export type
        if data.get('export_type') != 'project_full_backup':
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid export type. Expected "project_full_backup".'
            }, status=400)
        
        import_progress = request.POST.get('import_progress', '0') == '1' or data.get('include_progress', False)
        
        # ========== Create Project ==========
        proj_data = data.get('project', {})
        
        new_project = Project(
            owner=request.user,
            nama=f"{proj_data.get('nama', 'Imported Project')} (Import)",
            sumber_dana=proj_data.get('sumber_dana', 'N/A'),
            lokasi_project=proj_data.get('lokasi_project', 'N/A'),
            nama_client=proj_data.get('nama_client', 'N/A'),
            anggaran_owner=Decimal(proj_data.get('anggaran_owner', '0')),
            ket_project1=proj_data.get('ket_project1', ''),
            ket_project2=proj_data.get('ket_project2', ''),
            jabatan_client=proj_data.get('jabatan_client', ''),
            instansi_client=proj_data.get('instansi_client', ''),
            nama_kontraktor=proj_data.get('nama_kontraktor', ''),
            instansi_kontraktor=proj_data.get('instansi_kontraktor', ''),
            nama_konsultan_perencana=proj_data.get('nama_konsultan_perencana', ''),
            instansi_konsultan_perencana=proj_data.get('instansi_konsultan_perencana', ''),
            nama_konsultan_pengawas=proj_data.get('nama_konsultan_pengawas', ''),
            instansi_konsultan_pengawas=proj_data.get('instansi_konsultan_pengawas', ''),
            deskripsi=proj_data.get('deskripsi', ''),
            kategori=proj_data.get('kategori', ''),
            week_start_day=proj_data.get('week_start_day', 0),
            week_end_day=proj_data.get('week_end_day', 6),
        )
        
        if proj_data.get('tanggal_mulai'):
            new_project.tanggal_mulai = date.fromisoformat(proj_data['tanggal_mulai'])
        if proj_data.get('tanggal_selesai'):
            new_project.tanggal_selesai = date.fromisoformat(proj_data['tanggal_selesai'])
        if proj_data.get('durasi_hari'):
            new_project.durasi_hari = proj_data['durasi_hari']
        
        new_project.save()
        
        # ========== Import Klasifikasi ==========
        klas_map = {}  # export_id -> new_id
        for k in data.get('klasifikasi', []):
            new_k = Klasifikasi.objects.create(
                project=new_project,
                name=k['name'],
                ordering_index=k['ordering_index'],
            )
            klas_map[k['_export_id']] = new_k.id
        
        # ========== Import SubKlasifikasi ==========
        sub_map = {}  # export_id -> new_id
        for s in data.get('sub_klasifikasi', []):
            new_s = SubKlasifikasi.objects.create(
                project=new_project,
                klasifikasi_id=klas_map.get(s['_klasifikasi_ref']),
                name=s['name'],
                ordering_index=s['ordering_index'],
            )
            sub_map[s['_export_id']] = new_s.id
        
        # ========== Import HargaItemProject ==========
        harga_map = {}  # export_id -> new_id
        harga_items_data = data.get('harga_items', [])
        logger.info(f"[IMPORT] Starting harga_items import: {len(harga_items_data)} items in JSON")
        
        for h in harga_items_data:
            try:
                new_h = HargaItemProject.objects.create(
                    project=new_project,
                    kode_item=h['kode_item'],
                    uraian=h['uraian'],
                    satuan=h.get('satuan', ''),
                    kategori=h['kategori'],
                    harga_satuan=Decimal(h.get('harga_satuan', '0')),
                )
                harga_map[h['_export_id']] = new_h.id
            except Exception as e:
                logger.error(f"[IMPORT] Failed to import harga_item {h.get('kode_item')}: {e}")
        
        logger.info(f"[IMPORT] Completed harga_items import: {len(harga_map)} items created")
        
        # ========== Import ItemConversionProfile ==========
        for cp in data.get('conversion_profiles', []):
            harga_id = harga_map.get(cp['_harga_item_ref'])
            if harga_id:
                ItemConversionProfile.objects.create(
                    harga_item_id=harga_id,
                    market_unit=cp['market_unit'],
                    market_price=Decimal(cp.get('market_price', '0')),
                    factor_to_base=Decimal(cp.get('factor_to_base', '1')),
                    density=Decimal(cp['density']) if cp.get('density') else None,
                    capacity_m3=Decimal(cp['capacity_m3']) if cp.get('capacity_m3') else None,
                    capacity_ton=Decimal(cp['capacity_ton']) if cp.get('capacity_ton') else None,
                    method=cp.get('method', 'direct'),
                )
        
        # ========== Import Pekerjaan ==========
        pekerjaan_map = {}  # export_id -> new_id
        for p in data.get('pekerjaan', []):
            sub_id = sub_map.get(p['_sub_klasifikasi_ref'])
            if not sub_id:
                continue  # Skip if sub not found
            
            source_type = p.get('source_type', 'custom')
            if source_type == 'ref':
                src = Pekerjaan.SOURCE_REF
            elif source_type == 'ref_modified':
                src = Pekerjaan.SOURCE_REF_MOD
            else:
                src = Pekerjaan.SOURCE_CUSTOM
            
            new_p = Pekerjaan.objects.create(
                project=new_project,
                sub_klasifikasi_id=sub_id,
                source_type=src,
                snapshot_kode=p.get('snapshot_kode', ''),
                snapshot_uraian=p.get('snapshot_uraian', ''),
                snapshot_satuan=p.get('snapshot_satuan', ''),
                ordering_index=p['ordering_index'],
                budgeted_cost=Decimal(p.get('budgeted_cost', '0')),
                ref_id=p.get('ref_id'),  # Direct FK to AHSPReferensi
            )
            pekerjaan_map[p['_export_id']] = new_p.id
        
        # ========== Import VolumePekerjaan ==========
        for v in data.get('volume_pekerjaan', []):
            pkj_id = pekerjaan_map.get(v['_pekerjaan_ref'])
            if pkj_id:
                VolumePekerjaan.objects.create(
                    project=new_project,
                    pekerjaan_id=pkj_id,
                    quantity=Decimal(v.get('quantity', '0')),
                )
        
        # ========== Import DetailAHSPProject ==========
        for d in data.get('detail_ahsp', []):
            pkj_id = pekerjaan_map.get(d['_pekerjaan_ref'])
            harga_id = harga_map.get(d['_harga_item_ref'])
            if not pkj_id or not harga_id:
                continue
            
            ref_pkj_id = pekerjaan_map.get(d.get('_ref_pekerjaan_ref')) if d.get('_ref_pekerjaan_ref') else None
            
            DetailAHSPProject.objects.create(
                project=new_project,
                pekerjaan_id=pkj_id,
                harga_item_id=harga_id,
                kategori=d['kategori'],
                kode=d['kode'],
                uraian=d.get('uraian', ''),
                satuan=d.get('satuan', ''),
                koefisien=Decimal(d.get('koefisien', '0')),
                ref_ahsp_id=d.get('ref_ahsp_id'),  # Direct FK
                ref_pekerjaan_id=ref_pkj_id,
            )
        
        # ========== Import VolumeFormulaState (NEW in v1.1) ==========
        from .models import VolumeFormulaState, ProjectParameter, ProjectPricing
        for vf in data.get('volume_formula_states', []):
            pkj_id = pekerjaan_map.get(vf.get('_pekerjaan_ref'))
            if pkj_id:
                VolumeFormulaState.objects.create(
                    project=new_project,
                    pekerjaan_id=pkj_id,
                    raw=vf.get('raw', ''),
                    is_fx=vf.get('is_fx', True),
                )
        
        # ========== Import ProjectParameter (NEW in v1.1) ==========
        for pp in data.get('project_parameters', []):
            ProjectParameter.objects.create(
                project=new_project,
                name=pp['name'],
                value=Decimal(pp.get('value', '0')),
                label=pp.get('label', ''),
                unit=pp.get('unit', ''),
                description=pp.get('description', ''),
            )
        
        # ========== Import ProjectPricing (NEW in v1.1) ==========
        if data.get('project_pricing'):
            pp = data['project_pricing']
            ProjectPricing.objects.create(
                project=new_project,
                markup_percent=Decimal(pp.get('markup_percent', '10')),
                ppn_percent=Decimal(pp.get('ppn_percent', '11')),
                rounding_base=int(pp.get('rounding_base', 10000)),
            )
        
        # ========== Optional: Import Progress Data ==========
        # NOTE: We SKIP importing TahapPelaksanaan and PekerjaanTahapan
        # because they are DERIVED DATA that will be auto-regenerated from
        # PekerjaanProgressWeekly (canonical storage) when user opens the
        # Jadwal Pekerjaan page. This avoids duplicate key conflicts.
        # The exported data still contains these for reference/debugging.
        
        if import_progress and data.get('progress_weekly'):
            # ========== Smart Week Adjustment ==========
            # Calculate actual project weeks from new project dates
            from math import ceil
            actual_project_weeks = 0
            if new_project.tanggal_mulai and new_project.tanggal_selesai:
                days = (new_project.tanggal_selesai - new_project.tanggal_mulai).days
                actual_project_weeks = ceil(days / 7) if days > 0 else 0
            
            # Track stats for response
            imported_weeks = 0
            skipped_weeks = 0
            
            for pw in data.get('progress_weekly', []):
                pkj_id = pekerjaan_map.get(pw['_pekerjaan_ref'])
                week_num = pw['week_number']
                
                if pkj_id:
                    # Skip weeks that don't fit in the new project duration
                    if actual_project_weeks > 0 and week_num > actual_project_weeks:
                        skipped_weeks += 1
                        continue  # Skip this week - it's beyond project scope
                    
                    # Get or calculate week dates
                    if pw.get('week_start_date') and pw.get('week_end_date'):
                        # Use dates from export
                        week_start = date.fromisoformat(pw['week_start_date'])
                        week_end = date.fromisoformat(pw['week_end_date'])
                    else:
                        # Calculate from project start date + week_number
                        from datetime import timedelta
                        if new_project.tanggal_mulai:
                            week_start = new_project.tanggal_mulai + timedelta(days=(week_num - 1) * 7)
                            week_end = week_start + timedelta(days=6)
                        else:
                            # Fallback: use today as base
                            from datetime import date as date_today
                            base = date_today.today()
                            week_start = base + timedelta(days=(week_num - 1) * 7)
                            week_end = week_start + timedelta(days=6)
                    
                    PekerjaanProgressWeekly.objects.create(
                        project=new_project,
                        pekerjaan_id=pkj_id,
                        week_number=week_num,
                        week_start_date=week_start,
                        week_end_date=week_end,
                        planned_proportion=Decimal(pw.get('planned_proportion', '0')),
                        actual_proportion=Decimal(pw.get('actual_proportion', '0')),
                    )
                    imported_weeks += 1
            
            # Log adjustment info
            if skipped_weeks > 0:
                logger.info(f"Import jadwal: {imported_weeks} progress records imported, {skipped_weeks} skipped (beyond week {actual_project_weeks})")
        
        # Trigger bundle expansion for imported project
        for pkj_id in pekerjaan_map.values():
            try:
                pekerjaan = Pekerjaan.objects.get(id=pkj_id)
                expand_bundle_to_components(pekerjaan)
            except Exception:
                pass  # Non-critical
        
        return JsonResponse({
            'status': 'success',
            'message': f'Project berhasil diimport: {new_project.nama}',
            'project_id': new_project.id,
            'project_index': new_project.index_project,
            'stats': {
                'klasifikasi': len(klas_map),
                'sub_klasifikasi': len(sub_map),
                'pekerjaan': len(pekerjaan_map),
                'harga_items': len(harga_map),
            }
        })
        
    except Exception as e:
        logger.error(f"Import Project JSON error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Import gagal: {str(e)}'
        }, status=500)


# =====================================================
# TEMPLATE LIBRARY API ENDPOINTS
# Lightweight import/export for Klasifikasi/Sub/Pekerjaan
# =====================================================

from .models import PekerjaanTemplate


@login_required
@require_GET
def api_list_templates(request: HttpRequest):
    """
    List all available templates.
    
    Query params:
    - category: filter by category (rumah, ruko, infrastruktur, utilitas, lainnya)
    - q: search by name
    
    Returns list of templates with basic info (no content).
    """
    qs = PekerjaanTemplate.objects.filter(is_public=True)
    
    # Filter by category
    category = request.GET.get('category', '').strip()
    if category:
        qs = qs.filter(category=category)
    
    # Search by name
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(name__icontains=q)
    
    templates = []
    for t in qs[:50]:  # Limit to 50
        templates.append({
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'category': t.category,
            'category_display': t.get_category_display(),
            'total_klasifikasi': t.total_klasifikasi,
            'total_sub': t.total_sub,
            'total_pekerjaan': t.total_pekerjaan,
            'usage_count': t.usage_count,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        })
    
    return JsonResponse({
        'ok': True,
        'templates': templates,
        'total': len(templates)
    })


@login_required
@require_GET
def api_get_template_detail(request: HttpRequest, template_id: int):
    """
    Get full template detail including content.
    
    Returns hierarchical structure for preview/import.
    """
    try:
        template = PekerjaanTemplate.objects.get(id=template_id)
    except PekerjaanTemplate.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'message': 'Template tidak ditemukan'
        }, status=404)
    
    return JsonResponse({
        'ok': True,
        'template': {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category,
            'category_display': template.get_category_display(),
            'total_klasifikasi': template.total_klasifikasi,
            'total_sub': template.total_sub,
            'total_pekerjaan': template.total_pekerjaan,
            'usage_count': template.usage_count,
            'content': template.content,  # Full hierarchical data
            'created_at': template.created_at.isoformat() if template.created_at else None,
        }
    })


@login_required
@require_POST
@transaction.atomic
def api_create_template(request: HttpRequest, project_id: int):
    """
    Create a new template from current project's List Pekerjaan.
    
    Payload:
    {
        "name": "Template Rumah Sederhana",
        "description": "Template RAB untuk rumah tipe 36",
        "category": "rumah"  // optional, default "lainnya"
    }
    
    Exports current Klasifikasi → Sub → Pekerjaan → DetailAHSP structure to template.
    Uses unified _build_export_data helper with 'template' mode.
    """
    project = _owner_or_404(project_id, request.user)
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({
            'ok': False,
            'message': 'Payload JSON tidak valid'
        }, status=400)
    
    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({
            'ok': False,
            'message': 'Nama template wajib diisi'
        }, status=400)
    
    # Check duplicate name
    if PekerjaanTemplate.objects.filter(name=name).exists():
        return JsonResponse({
            'ok': False,
            'message': f'Template dengan nama "{name}" sudah ada'
        }, status=400)
    
    description = (payload.get('description') or '').strip()
    category = payload.get('category', 'lainnya')
    if category not in dict(PekerjaanTemplate.CATEGORY_CHOICES):
        category = 'lainnya'
    
    # Build content using unified helper with template mode
    template_meta = {
        "name": name,
        "description": description,
        "category": category,
        "source_project": project.nama,
    }
    content = _build_export_data(project, mode='template', template_meta=template_meta)
    
    # Check if there's data to export
    if not content.get('pekerjaan'):
        return JsonResponse({
            'ok': False,
            'message': 'Project tidak memiliki data Pekerjaan untuk di-export'
        }, status=400)
    
    # Create template - store the full export data as content
    template = PekerjaanTemplate.objects.create(
        name=name,
        description=description,
        category=category,
        content=content,  # Now includes klasifikasi, sub, pekerjaan, detail_ahsp
        created_by=request.user,
        is_public=True,
    )
    
    return JsonResponse({
        'ok': True,
        'message': f'Template "{name}" berhasil dibuat',
        'template_id': template.id,
        'stats': content.get('stats', {})
    })


@login_required
@require_POST
@transaction.atomic
def api_delete_template(request: HttpRequest, template_id: int):
    """Delete a template (only creator or superuser can delete)."""
    try:
        template = PekerjaanTemplate.objects.get(id=template_id)
    except PekerjaanTemplate.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'message': 'Template tidak ditemukan'
        }, status=404)
    
    # Check permission
    if template.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({
            'ok': False,
            'message': 'Anda tidak memiliki izin untuk menghapus template ini'
        }, status=403)
    
    name = template.name
    template.delete()
    
    return JsonResponse({
        'ok': True,
        'message': f'Template "{name}" berhasil dihapus'
    })


def _import_template_data(project, data, user=None):
    """
    Import template data into existing project.
    
    Supports both new flat format (from _build_export_data) and legacy nested format.
    
    Args:
        project: Target project (must exist)
        data: Template content dict
        user: Request user (optional, for logging)
    
    Returns:
        tuple: (stats dict, errors list)
    """
    from decimal import Decimal
    
    stats = {'klasifikasi': 0, 'sub': 0, 'pekerjaan': 0, 'detail': 0}
    errors = []
    
    # Get next ordering indices
    max_k = Klasifikasi.objects.filter(project=project).aggregate(Max('ordering_index'))['ordering_index__max'] or 0
    max_p = Pekerjaan.objects.filter(project=project).aggregate(Max('ordering_index'))['ordering_index__max'] or 0
    
    # Detect format: new (flat arrays) or legacy (nested)
    is_new_format = 'sub_klasifikasi' in data and isinstance(data.get('sub_klasifikasi'), list)
    
    # Maps for ID remapping
    klas_map = {}   # export_id -> new_id
    sub_map = {}    # export_id -> new_id
    pkj_map = {}    # export_id -> new_id
    pkj_snapshot_map = {}  # snapshot_kode -> new_id
    
    if is_new_format:
        # ========== New Format (flat arrays) ==========
        
        # Pass 1: Import Klasifikasi
        for k_data in data.get('klasifikasi', []):
            max_k += 1
            try:
                k_obj = Klasifikasi.objects.create(
                    project=project,
                    name=k_data.get('name', f'Klasifikasi {max_k}'),
                    ordering_index=max_k
                )
                klas_map[k_data.get('_export_id')] = k_obj.id
                stats['klasifikasi'] += 1
            except IntegrityError as e:
                errors.append(f"Gagal membuat klasifikasi: {e}")
        
        # Pass 2: Import SubKlasifikasi
        for s_data in data.get('sub_klasifikasi', []):
            klas_id = klas_map.get(s_data.get('_klasifikasi_ref'))
            if not klas_id:
                errors.append(f"Sub '{s_data.get('name')}' skip: klasifikasi tidak ditemukan")
                continue
            try:
                s_obj = SubKlasifikasi.objects.create(
                    project=project,
                    klasifikasi_id=klas_id,
                    name=s_data.get('name', 'Sub'),
                    ordering_index=s_data.get('ordering_index', 1)
                )
                sub_map[s_data.get('_export_id')] = s_obj.id
                stats['sub'] += 1
            except IntegrityError as e:
                errors.append(f"Gagal membuat sub: {e}")
        
        # Pass 3: Import Pekerjaan
        for p_data in data.get('pekerjaan', []):
            max_p += 1
            sub_id = sub_map.get(p_data.get('_sub_klasifikasi_ref'))
            if not sub_id:
                errors.append(f"Pekerjaan skip: sub tidak ditemukan")
                continue
            
            src_str = p_data.get('source_type', 'custom')
            src = {
                'ref': Pekerjaan.SOURCE_REF,
                'ref_modified': Pekerjaan.SOURCE_REF_MOD,
                'custom': Pekerjaan.SOURCE_CUSTOM,
            }.get(src_str, Pekerjaan.SOURCE_CUSTOM)
            
            ref_obj = None
            ref_id = p_data.get('ref_id')
            if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and ref_id:
                try:
                    ref_obj = AHSPReferensi.objects.get(id=ref_id)
                except AHSPReferensi.DoesNotExist:
                    src = Pekerjaan.SOURCE_CUSTOM
            
            kode = p_data.get('snapshot_kode') or ''
            if src == Pekerjaan.SOURCE_CUSTOM and not kode:
                kode = generate_custom_code(project)
            
            try:
                pkj = Pekerjaan.objects.create(
                    project=project,
                    sub_klasifikasi_id=sub_id,
                    source_type=src,
                    ref=ref_obj,
                    snapshot_kode=kode,
                    snapshot_uraian=p_data.get('snapshot_uraian', ''),
                    snapshot_satuan=p_data.get('snapshot_satuan', ''),
                    ordering_index=max_p
                )
                pkj_map[p_data.get('_export_id')] = pkj.id
                pkj_snapshot_map[kode] = pkj.id
                stats['pekerjaan'] += 1
                
                # Auto-expand bundle for REF types (if no custom detail_ahsp provided)
                if ref_obj and src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                    try:
                        expand_bundle_to_components(pkj)
                    except Exception:
                        pass
                        
            except IntegrityError as e:
                errors.append(f"Gagal membuat pekerjaan: {e}")
        
        # Pass 4: Import DetailAHSPProject (for custom/ref_modified)
        for d_data in data.get('detail_ahsp', []):
            pkj_id = pkj_map.get(d_data.get('_pekerjaan_ref'))
            if not pkj_id:
                continue  # Skip if pekerjaan wasn't created
            
            # Get or create HargaItem
            harga_kode = d_data.get('harga_item_kode') or d_data.get('kode')
            if not harga_kode:
                continue
            
            try:
                harga_item, _ = HargaItemProject.objects.get_or_create(
                    project=project,
                    kode_item=harga_kode,
                    defaults={
                        'uraian': d_data.get('uraian', ''),
                        'satuan': d_data.get('satuan', ''),
                        'kategori': d_data.get('kategori', 'LAIN'),
                        'harga_satuan': Decimal('0'),  # Price not imported in template mode
                    }
                )
                
                # Handle bundle references for LAIN category
                ref_pekerjaan = None
                ref_ahsp = None
                
                if d_data.get('kategori') == 'LAIN':
                    bundle_type = d_data.get('bundle_type')
                    if bundle_type == 'pekerjaan':
                        ref_kode = d_data.get('bundle_ref_snapshot_kode')
                        if ref_kode and ref_kode in pkj_snapshot_map:
                            ref_pekerjaan = Pekerjaan.objects.filter(id=pkj_snapshot_map[ref_kode]).first()
                    elif bundle_type == 'ahsp':
                        ref_ahsp_id = d_data.get('bundle_ref_ahsp_id')
                        if ref_ahsp_id:
                            try:
                                ref_ahsp = AHSPReferensi.objects.get(id=ref_ahsp_id)
                            except AHSPReferensi.DoesNotExist:
                                pass
                
                # Create DetailAHSP
                DetailAHSPProject.objects.create(
                    project=project,
                    pekerjaan_id=pkj_id,
                    harga_item=harga_item,
                    kategori=d_data.get('kategori', 'LAIN'),
                    kode=d_data.get('kode', ''),
                    uraian=d_data.get('uraian', ''),
                    satuan=d_data.get('satuan', ''),
                    koefisien=Decimal(d_data.get('koefisien', '0')),
                    ref_ahsp=ref_ahsp,
                    ref_pekerjaan=ref_pekerjaan,
                )
                stats['detail'] += 1
                
            except Exception as e:
                errors.append(f"Gagal import detail: {e}")
    
    else:
        # ========== Legacy Format (nested) ==========
        # For backward compatibility with old templates
        
        klasifikasi_list = data.get('klasifikasi', [])
        k_counter = max_k
        p_counter = max_p
        
        for k_data in klasifikasi_list:
            k_counter += 1
            k_name = (k_data.get('name') or f"Klasifikasi {k_counter}").strip()
            
            try:
                k_obj = Klasifikasi.objects.create(
                    project=project,
                    name=k_name,
                    ordering_index=k_counter
                )
                stats['klasifikasi'] += 1
            except IntegrityError as e:
                errors.append(f"Gagal membuat klasifikasi '{k_name}': {e}")
                continue
            
            for si, s_data in enumerate(k_data.get('sub', [])):
                s_name = (s_data.get('name') or f"{k_counter}.{si+1}").strip()
                
                try:
                    s_obj = SubKlasifikasi.objects.create(
                        project=project,
                        klasifikasi=k_obj,
                        name=s_name,
                        ordering_index=s_data.get('ordering_index', si + 1)
                    )
                    stats['sub'] += 1
                except IntegrityError as e:
                    errors.append(f"Gagal membuat sub '{s_name}': {e}")
                    continue
                
                for p_data in s_data.get('pekerjaan', []):
                    p_counter += 1
                    src_str = p_data.get('source_type', 'custom')
                    src = {
                        'ref': Pekerjaan.SOURCE_REF,
                        'ref_modified': Pekerjaan.SOURCE_REF_MOD,
                        'custom': Pekerjaan.SOURCE_CUSTOM,
                    }.get(src_str, Pekerjaan.SOURCE_CUSTOM)
                    
                    ref_obj = None
                    ref_id = p_data.get('ref_ahsp_id') or p_data.get('ref_id')
                    if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and ref_id:
                        try:
                            ref_obj = AHSPReferensi.objects.get(id=ref_id)
                        except AHSPReferensi.DoesNotExist:
                            src = Pekerjaan.SOURCE_CUSTOM
                    
                    kode = p_data.get('snapshot_kode') or ''
                    if src == Pekerjaan.SOURCE_CUSTOM and not kode:
                        kode = generate_custom_code(project)
                    
                    try:
                        pkj = Pekerjaan.objects.create(
                            project=project,
                            sub_klasifikasi=s_obj,
                            source_type=src,
                            ref=ref_obj,
                            snapshot_kode=kode,
                            snapshot_uraian=p_data.get('snapshot_uraian', ''),
                            snapshot_satuan=p_data.get('snapshot_satuan', ''),
                            ordering_index=p_counter
                        )
                        stats['pekerjaan'] += 1
                        
                        if ref_obj and src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                            try:
                                expand_bundle_to_components(pkj)
                            except Exception:
                                pass
                                
                    except IntegrityError as e:
                        errors.append(f"Gagal membuat pekerjaan: {e}")
    
    # ========== Import Parameters (v2.1+) ==========
    stats['parameters'] = 0
    for param_data in data.get('parameters', []):
        param_name = param_data.get('name', '').strip()
        if not param_name:
            continue
        
        try:
            param, created = ProjectParameter.objects.update_or_create(
                project=project,
                name=param_name,
                defaults={
                    'value': Decimal(param_data.get('value', '0')),
                    'label': param_data.get('label', ''),
                    'unit': param_data.get('unit', ''),
                    'description': param_data.get('description', ''),
                }
            )
            if created:
                stats['parameters'] += 1
        except Exception as e:
            errors.append(f"Gagal import parameter '{param_name}': {e}")
    
    # ========== Import Volume Formulas (v2.2+) ==========
    stats['formulas'] = 0
    for formula_data in data.get('volume_formulas', []):
        pkj_ref = formula_data.get('_pekerjaan_ref')
        pkj_id = pkj_map.get(pkj_ref)
        if not pkj_id:
            continue  # Skip if pekerjaan wasn't imported
        
        raw_formula = formula_data.get('raw', '')
        if not raw_formula:
            continue
        
        try:
            formula, created = VolumeFormulaState.objects.update_or_create(
                project=project,
                pekerjaan_id=pkj_id,
                defaults={
                    'raw': raw_formula,
                    'is_fx': formula_data.get('is_fx', False),
                }
            )
            if created:
                stats['formulas'] += 1
        except Exception as e:
            errors.append(f"Gagal import formula: {e}")
    
    return stats, errors


@login_required
@require_POST
@transaction.atomic
def api_import_template(request: HttpRequest, project_id: int, template_id: int):
    """
    Import template into project's List Pekerjaan.
    
    Uses unified _import_template_data helper.
    Adds Klasifikasi/Sub/Pekerjaan/DetailAHSP from template to existing data (no overwrite).
    Increments template's usage count.
    """
    project = _owner_or_404(project_id, request.user)
    
    try:
        template = PekerjaanTemplate.objects.get(id=template_id)
    except PekerjaanTemplate.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'message': 'Template tidak ditemukan'
        }, status=404)
    
    content = template.content
    if not content or not isinstance(content, dict):
        return JsonResponse({
            'ok': False,
            'message': 'Template tidak memiliki konten yang valid'
        }, status=400)
    
    # Check for pekerjaan data (new format) or klasifikasi (legacy format)
    has_pekerjaan = content.get('pekerjaan') or content.get('klasifikasi')
    if not has_pekerjaan:
        return JsonResponse({
            'ok': False,
            'message': 'Template tidak memiliki data pekerjaan'
        }, status=400)
    
    # Use unified import helper
    stats, errors = _import_template_data(project, content, user=request.user)
    
    # Increment usage count
    template.increment_usage()
    
    # Invalidate cache
    transaction.on_commit(lambda: invalidate_rekap_cache(project))
    
    response_data = {
        'ok': True,
        'message': f'Template "{template.name}" berhasil diimport',
        'stats': stats
    }
    
    if errors:
        response_data['warnings'] = errors
    
    return JsonResponse(response_data)


@login_required
@require_POST
@transaction.atomic
def api_import_template_from_file(request: HttpRequest, project_id: int):
    """
    Import template content directly from JSON file upload.
    
    Payload:
    {
        "content": { ... template JSON content ... }
    }
    
    Uses unified _import_template_data helper.
    """
    project = _owner_or_404(project_id, request.user)
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
        print(f"[IMPORT DEBUG] Received payload, content keys: {list(payload.keys())}")
    except Exception as e:
        print(f"[IMPORT ERROR] Failed to parse JSON: {e}")
        return JsonResponse({
            'ok': False,
            'message': 'Payload JSON tidak valid'
        }, status=400)
    
    content = payload.get('content')
    if not content or not isinstance(content, dict):
        print(f"[IMPORT ERROR] Invalid content: {type(content)}")
        return JsonResponse({
            'ok': False,
            'message': 'Content template tidak valid'
        }, status=400)
    
    print(f"[IMPORT DEBUG] Content keys: {list(content.keys())}")
    print(f"[IMPORT DEBUG] export_type: {content.get('export_type')}, version: {content.get('export_version')}")
    print(f"[IMPORT DEBUG] klasifikasi: {len(content.get('klasifikasi', []))}, sub: {len(content.get('sub_klasifikasi', []))}")
    print(f"[IMPORT DEBUG] pekerjaan: {len(content.get('pekerjaan', []))}, detail: {len(content.get('detail_ahsp', []))}")
    print(f"[IMPORT DEBUG] parameters: {len(content.get('parameters', []))}")
    
    # Check for data
    has_data = content.get('pekerjaan') or content.get('klasifikasi')
    if not has_data:
        print(f"[IMPORT ERROR] No pekerjaan or klasifikasi found")
        return JsonResponse({
            'ok': False,
            'message': 'Template tidak memiliki data pekerjaan'
        }, status=400)
    
    print(f"[IMPORT DEBUG] Starting import to project {project.id} ({project.nama})")
    
    # Use unified import helper
    try:
        stats, errors = _import_template_data(project, content, user=request.user)
        print(f"[IMPORT DEBUG] Import completed. Stats: {stats}")
        if errors:
            print(f"[IMPORT WARN] Errors during import: {errors}")
    except Exception as e:
        print(f"[IMPORT ERROR] Exception during _import_template_data: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'message': f'Error saat import: {str(e)}'
        }, status=500)
    
    # Invalidate cache
    transaction.on_commit(lambda: invalidate_rekap_cache(project))
    
    response_data = {
        'ok': True,
        'message': f'Import dari file berhasil!',
        'stats': stats
    }
    
    if errors:
        response_data['warnings'] = errors
    
    print(f"[IMPORT DEBUG] Returning success response: {response_data}")
    return JsonResponse(response_data)


@login_required
@require_GET
def export_template_json(request: HttpRequest, project_id: int):
    """
    Export current project's List Pekerjaan as template JSON file.
    
    Uses unified _build_export_data helper with 'template' mode.
    Returns downloadable JSON file.
    """
    project = _owner_or_404(project_id, request.user)
    
    template_name = request.GET.get('name', f'Template dari {project.nama}')
    template_desc = request.GET.get('description', '')
    template_cat = request.GET.get('category', 'lainnya')
    
    template_meta = {
        "name": template_name,
        "description": template_desc,
        "category": template_cat,
        "source_project": project.nama,
    }
    
    export_data = _build_export_data(project, mode='template', template_meta=template_meta)
    
    if not export_data.get('pekerjaan'):
        return JsonResponse({
            'ok': False,
            'message': 'Project tidak memiliki data pekerjaan untuk di-export'
        }, status=400)
    
    response = JsonResponse(export_data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
    filename = f"template_{project.nama.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

