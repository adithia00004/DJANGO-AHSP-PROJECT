# ================================
# detail_project/views_api.py
# ================================
import json
import csv
import logging
from io import BytesIO
from typing import Any
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  # <-- NEW: Decimal handling

logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.db.models import Max, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils.timezone import now
from .numeric import parse_any, to_dp_str, quantize_half_up, DECIMAL_SPEC
from referensi.models import AHSPReferensi
from .models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    DetailAHSPProject, DetailAHSPExpanded, HargaItemProject,VolumeFormulaState, ProjectPricing, # NEW
)
from .services import (
    clone_ref_pekerjaan, _upsert_harga_item, compute_rekap_for_project,
    generate_custom_code, invalidate_rekap_cache, validate_bundle_reference,
    expand_bundle_to_components,  # NEW: Dual storage expansion (Pekerjaan)
    expand_ahsp_bundle_to_components,  # NEW: Dual storage expansion (AHSP)
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


def _src_to_str(val):
    return {
        Pekerjaan.SOURCE_REF: 'ref',
        Pekerjaan.SOURCE_CUSTOM: 'custom',
        Pekerjaan.SOURCE_REF_MOD: 'ref_modified',
    }.get(val, str(val))

def _err(path: str, message: str):
    return {"path": path, "message": message}

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
    } for obj in qs]

    return JsonResponse({"ok": True, "results": results, "total": len(results)})

# ---------- View 1: SAVE (full-create) ----------
@login_required
@require_POST
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
    invalidate_rekap_cache(project)  # NEW
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

    k_qs = Klasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')
    s_qs = SubKlasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')
    p_qs = Pekerjaan.objects.filter(project=project).order_by('ordering_index', 'id')

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
            # No matching pekerjaan found - return empty structure
            return JsonResponse({"ok": True, "klasifikasi": [], "search_query": search_query, "match_count": 0})

    subs_by_klas = {}
    for s in s_qs:
        subs_by_klas.setdefault(s.klasifikasi_id, []).append(s)

    pkj_by_sub = {}
    for p in p_qs:
        pkj_by_sub.setdefault(p.sub_klasifikasi_id, []).append(p)

    data = []
    total_pekerjaan_count = 0
    for k in k_qs:
        k_obj = {
            "id": k.id,
            "name": k.name,
            "ordering_index": k.ordering_index,
            "sub": []
        }
        for s in subs_by_klas.get(k.id, []):
            s_obj = {
                "id": s.id,
                "name": s.name,
                "ordering_index": s.ordering_index,
                "pekerjaan": []
            }
            for p in pkj_by_sub.get(s.id, []):
                s_obj["pekerjaan"].append({
                    "id": p.id,
                    "source_type": _src_to_str(p.source_type),
                    "ordering_index": p.ordering_index,
                    "snapshot_kode": getattr(p, "snapshot_kode", None),
                    "snapshot_uraian": p.snapshot_uraian,
                    "snapshot_satuan": p.snapshot_satuan,
                    "ref_id": getattr(p, "ref_id", None),
                })
                total_pekerjaan_count += 1
            k_obj["sub"].append(s_obj)
        data.append(k_obj)

    response_data = {
        "ok": True,
        "klasifikasi": data
    }

    # Add search metadata if search was performed
    if search_query:
        response_data["search_query"] = search_query
        response_data["match_count"] = total_pekerjaan_count

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
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    klas_list = payload.get("klasifikasi") or []
    if not isinstance(klas_list, list):
        return JsonResponse({"ok": False, "errors": [_err("klasifikasi", "Harus list")]}, status=400)

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

    if pre_errors:
        return JsonResponse({"ok": False, "errors": pre_errors}, status=400)

    # ============================
    # PROSES UPSERT
    # ============================
    errors = []
    keep_k = set()
    keep_all_p = set()  # global keep untuk semua pekerjaan di payload

    existing_k = {k.id: k for k in Klasifikasi.objects.filter(project=project)}
    existing_s = {s.id: s for s in SubKlasifikasi.objects.filter(project=project)}
    existing_p = {p.id: p for p in Pekerjaan.objects.filter(project=project)}

    def _get_or_reuse_pekerjaan_for_order(order: int):
        return Pekerjaan.objects.filter(project=project, ordering_index=order).first()

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
        pobj.ordering_index = order
        pobj.save(update_fields=[
            "sub_klasifikasi", "source_type", "ref",
            "snapshot_kode", "snapshot_uraian", "snapshot_satuan", "ordering_index"
        ])

        # Move DetailAHSPProject from tmp to pobj
        # (No dedup needed since we already deleted all old details)
        DetailAHSPProject.objects.filter(project=project, pekerjaan=tmp).update(pekerjaan=pobj)

        tmp.delete()

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

                order = _safe_int(p.get("ordering_index"), pi + 1)
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
                                _adopt_tmp_into(pobj, tmp, s_obj, order)
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
                                if not pobj.snapshot_kode:
                                    pobj.snapshot_kode = generate_custom_code(project)
                                pobj.snapshot_uraian = uraian
                                pobj.snapshot_satuan = satuan
                                pobj.ordering_index = order
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
                        pobj.ordering_index = order
                        pobj.sub_klasifikasi = s_obj
                        if src == Pekerjaan.SOURCE_CUSTOM:
                            pobj.snapshot_uraian = (p.get("snapshot_uraian") or pobj.snapshot_uraian or "").strip()
                            val_sat = p.get("snapshot_satuan")
                            pobj.snapshot_satuan = (val_sat or pobj.snapshot_satuan)
                            if not pobj.snapshot_kode:
                                pobj.snapshot_kode = generate_custom_code(project)
                        elif src == Pekerjaan.SOURCE_REF_MOD:
                            if ov_ura: pobj.snapshot_uraian = ov_ura
                            if ov_sat: pobj.snapshot_satuan = ov_sat
                        pobj.save(update_fields=[
                            "ordering_index", "sub_klasifikasi", "snapshot_kode", "snapshot_uraian", "snapshot_satuan"
                        ])

                    # NOTE: pobj.id already added to keep_all_p at line 709
                    # (moved there to prevent deletion even if validation fails)

                else:
                    # ============ CREATE / REUSE ============

                    try:
                        if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                            rid = int(p.get("ref_id"))  # aman (preflight)
                            ref_obj = AHSPReferensi.objects.get(id=rid)

                            pobj_reuse = _get_or_reuse_pekerjaan_for_order(order)
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
                                _adopt_tmp_into(pobj, tmp, s_obj, order)
                            else:
                                pobj = clone_ref_pekerjaan(
                                    project, s_obj, ref_obj, src,
                                    ordering_index=order, auto_load_rincian=True,
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
                                        ordering_index=order,
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
                            pobj = _get_or_reuse_pekerjaan_for_order(order)
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
                                pobj.ordering_index = order
                                pobj.save(update_fields=[
                                    "sub_klasifikasi","source_type","ref",
                                    "snapshot_kode","snapshot_uraian","snapshot_satuan","ordering_index"
                                ])
                            else:
                                pobj = Pekerjaan.objects.create(
                                    project=project, sub_klasifikasi=s_obj, source_type=src,
                                    snapshot_kode=generate_custom_code(project),
                                    snapshot_uraian=uraian, snapshot_satuan=satuan, ordering_index=order
                                )
                            
                    except AHSPReferensi.DoesNotExist:
                        errors.append(_err(
                            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                            f"Referensi #{p.get('ref_id')} tidak ditemukan"
                        ))
                        continue

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
    invalidate_rekap_cache(project)  # NEW
    return JsonResponse({"ok": status == 200, "errors": errors, "summary": summary}, status=status)



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

    if saved:
        invalidate_rekap_cache(project)

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

    items = [
        {
            "id": it["id"],
            "kategori": it["kategori"],
            "kode": it["kode"] or "",
            "uraian": it["uraian"] or "",
            "satuan": (it.get("satuan") or None),
            "koefisien": to_dp_str(it.get("koefisien"), dp_koef),
            "ref_ahsp_id": it.get("ref_ahsp_id"),
            "ref_pekerjaan_id": it.get("ref_pekerjaan_id"),  # NEW: bundle support
            "harga_satuan": to_dp_str(it.get("harga_item__harga_satuan"), dp_harga),
        }
        for it in qs
    ]

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
            server_dt = pkj.updated_at if hasattr(pkj, 'updated_at') and pkj.updated_at else None

            if server_dt and client_dt < server_dt:
                # Data has been modified by another user since client loaded it
                logger.warning(
                    f"[SAVE_DETAIL_AHSP] CONFLICT - Pekerjaan {pkj.id} modified by another user. "
                    f"Client: {client_dt.isoformat()}, Server: {server_dt.isoformat()}"
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
    normalized = []  # tuple: (kat, kode, uraian, satuan, koef, ref_ahsp_obj)
    seen_kode = set()
    valid_kats = set(dict(HargaItemProject.KATEGORI_CHOICES).keys())

    for i, r in enumerate(rows):
        kat = _normalize_kategori(r.get('kategori'))
        if kat not in valid_kats:
            errors.append(_err(f"rows[{i}].kategori", "Kategori tidak valid")); continue

        kode = (r.get('kode') or '').strip()
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

    # Bila semua baris error → 400
    if errors and not normalized:
        logger.error(f"[SAVE_DETAIL_AHSP] All rows invalid: {len(errors)} errors")
        # Create user-friendly message
        error_count = len(errors)
        error_summary = f"Ditemukan {error_count} kesalahan pada data yang Anda masukkan. Mohon perbaiki dan coba lagi."
        return JsonResponse({
            "ok": False,
            "user_message": error_summary,
            "errors": errors
        }, status=400)

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
                    depth=0,
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
                    depth=0,
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

    # Update pekerjaan.detail_ready (based on expanded components count)
    detail_ready = len(expanded_to_create) > 0
    Pekerjaan.objects.filter(pk=pkj.pk).update(detail_ready=detail_ready)
    logger.info(f"[SAVE_DETAIL_AHSP] Updated pekerjaan.detail_ready = {detail_ready}")

    # CRITICAL FIX: Invalidate cache AFTER transaction commits to avoid race condition
    # This ensures cache is invalidated only when data is actually committed to DB
    transaction.on_commit(lambda: invalidate_rekap_cache(project))

    status_code = 207 if errors else 200
    logger.info(f"[SAVE_DETAIL_AHSP] SUCCESS - Status: {status_code}, Raw: {len(saved_raw_details)}, Expanded: {len(expanded_to_create)}, Errors: {len(errors)}")

    # Build user-friendly message
    if status_code == 200:
        user_message = f"✅ Data berhasil disimpan! {len(saved_raw_details)} baris komponen tersimpan."
    else:
        user_message = f"⚠️ Data tersimpan sebagian. {len(saved_raw_details)} baris berhasil, {len(errors)} kesalahan ditemukan."

    # Refresh pekerjaan to get updated timestamp
    pkj.refresh_from_db()

    return JsonResponse({
        "ok": status_code == 200,
        "user_message": user_message,
        "saved_raw_rows": len(saved_raw_details),
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
        temp.delete()

    # Tandai ready bila ada baris
    Pekerjaan.objects.filter(pk=pkj.pk).update(detail_ready=(moved > 0))
    invalidate_rekap_cache(project)  # NEW
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

# ---------- View: Project Pricing (Profit/Margin) ----------
@login_required
@require_http_methods(["GET","POST"])
@transaction.atomic
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
        obj = _get_or_create_pricing(project)
        return JsonResponse({
            "ok": True,
            "markup_percent": to_dp_str(getattr(obj, "markup_percent", Decimal("0.00")), 2),
            "ppn_percent": to_dp_str(getattr(obj, "ppn_percent", Decimal("11.00")), 2),
            "rounding_base": int(getattr(obj, "rounding_base", 10000) or 10000),
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
        invalidate_rekap_cache(project)  # perubahan pricing memengaruhi rekap

    return JsonResponse({
        "ok": True,
        "markup_percent": to_dp_str(obj.markup_percent, 2),
        "ppn_percent": to_dp_str(obj.ppn_percent, 2),
        "rounding_base": int(getattr(obj, "rounding_base", 10000) or 10000),
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

    if total_saved > 0:
        invalidate_rekap_cache(project)  # NEW

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
    List all Harga Items used in this project.

    DUAL STORAGE UPDATE:
    - Reads from DetailAHSPExpanded (expanded components) instead of DetailAHSPProject (raw input)
    - Shows only base components (TK/BHN/ALT) from bundle expansion
    - Bundle items (LAIN) are NOT shown (they're expanded to components)

    P0 FIX (2025-11-11):
    - Added project_updated_at for optimistic locking
    """
    project = _owner_or_404(project_id, request.user)
    qs = (HargaItemProject.objects
          .filter(project=project, expanded_refs__project=project)  # DUAL STORAGE: expanded_refs instead of detail_refs
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

    # Peta override per pekerjaan
    pids = [r.get("pekerjaan_id") for r in data if r.get("pekerjaan_id")]
    ov_map = {}
    if pids:
        ov_map = dict(
            Pekerjaan.objects
            .filter(project=project, id__in=pids)
            .values_list("id", "markup_override_percent")
        )

    # Suntik markup_eff bila kosong/0; set HSP = D; isi F/G/total hanya jika belum ada
    for r in data:
        curr = r.get("markup_eff")
        if curr in (None, "", 0, 0.0):
            ov = ov_map.get(r.get("pekerjaan_id"))
            proj_mp = pp.markup_percent if pp and pp.markup_percent is not None else default_proj_mp
            eff = ov if ov is not None else proj_mp
            r["markup_eff"] = float(eff)

        # Harga Satuan untuk UI = biaya langsung (A+B+C), yaitu D
        try:
            d_direct = float(r.get("D") or 0.0)
        except Exception:
            d_direct = 0.0
        r["HSP"] = d_direct

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
    from .services import compute_kebutuhan_items

    rows = compute_kebutuhan_items(project)  # list of dicts: {kategori,kode,uraian,satuan,quantity}

    # --- meta (mundur-kompatibel) ---
    counts = {"TK": 0, "BHN": 0, "ALT": 0, "LAIN": 0}
    for r in rows:
        k = r.get("kategori")
        if k in counts:
            counts[k] += 1

    meta = {
        "counts_per_kategori": counts,
        "n_rows": len(rows),
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return JsonResponse({"ok": True, "rows": rows, "meta": meta})

# ============== FUNCTION 1: CSV EXPORT (REFACTORED) ==============
@login_required
@require_GET
def api_export_rekap_kebutuhan_csv(request, project_id: int):
    """Export Rekap Kebutuhan ke CSV (minimal header-first).

    Catatan: Test mengharapkan baris pertama adalah header kolom
    "kategori;kode;uraian;satuan;quantity" tanpa judul/identitas.
    Implementasi di sini sengaja menulis CSV minimal untuk kompatibilitas
    mundur dengan test suite.
    """
    try:
        project = _owner_or_404(project_id, request.user)
        from .services import compute_kebutuhan_items

        rows = compute_kebutuhan_items(project)

        # Build CSV minimal (semicolon-delimited)
        import csv
        from io import StringIO

        buf = StringIO()
        writer = csv.writer(buf, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["kategori", "kode", "uraian", "satuan", "quantity"])

        for r in rows:
            writer.writerow([
                r.get("kategori", "") or "",
                r.get("kode", "") or "",
                r.get("uraian", "") or "",
                r.get("satuan", "") or "",
                str(r.get("quantity", "")) or "",
            ])

        content = buf.getvalue().encode('utf-8')
        resp = HttpResponse(content, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="rekap_kebutuhan.csv"'
        return resp

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export CSV gagal: {str(e)}'
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
        return manager.export_rekap_kebutuhan('pdf')
        
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
        return manager.export_rekap_kebutuhan('word')
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Export Word gagal: {str(e)}'
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
        invalidate_rekap_cache(project)  # NEW  : rekap berubah bila ada override
        return JsonResponse({"ok": True, "cleared": True})

    dec = parse_any(raw)
    if dec is None or dec < 0 or dec > 100:
        return JsonResponse({"ok": False, "errors": [_err("override_markup","Harus angka 0–100")]} , status=400)

    Pekerjaan.objects.filter(pk=pkj.pk).update(markup_override_percent=dec)
    invalidate_rekap_cache(project)  # NEW
    return JsonResponse({"ok": True, "saved": True, "override_markup": to_dp_str(dec, 2)})


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


# ============================================================================
# EXPORT: VOLUME PEKERJAAN (CSV / PDF / WORD)
# ============================================================================

@login_required
@require_GET
def export_volume_pekerjaan_csv(request: HttpRequest, project_id: int):
    """Export Volume Pekerjaan to CSV"""
    try:
        project = _owner_or_404(project_id, request.user)
        # Extract parameters from query string (optional: ?params={"panjang":100,"lebar":50})
        parameters = _extract_parameters_from_request(request)
        from .exports.export_manager import ExportManager
        manager = ExportManager(project, request.user)
        return manager.export_volume_pekerjaan('csv', parameters=parameters)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export CSV gagal: {str(e)}'}, status=500)


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
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export Word gagal: {str(e)}'}, status=500)


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

