# ================================
# detail_project/views_api.py
# ================================
import json
from typing import Any
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  # <-- NEW: Decimal handling
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
    DetailAHSPProject, HargaItemProject,VolumeFormulaState, ProjectPricing, # NEW
)
from .services import (
    clone_ref_pekerjaan, _upsert_harga_item, compute_rekap_for_project,
    generate_custom_code, invalidate_rekap_cache,
)

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
    """Kembalikan struktur Klasifikasi → Sub → Pekerjaan yang sudah tersimpan."""
    project = _owner_or_404(project_id, request.user)

    k_qs = Klasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')
    s_qs = SubKlasifikasi.objects.filter(project=project).order_by('ordering_index', 'id')
    p_qs = Pekerjaan.objects.filter(project=project).order_by('ordering_index', 'id')

    subs_by_klas = {}
    for s in s_qs:
        subs_by_klas.setdefault(s.klasifikasi_id, []).append(s)

    pkj_by_sub = {}
    for p in p_qs:
        pkj_by_sub.setdefault(p.sub_klasifikasi_id, []).append(p)

    data = []
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
            k_obj["sub"].append(s_obj)
        data.append(k_obj)

    return JsonResponse({"ok": True, "klasifikasi": data})



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

    def _adopt_tmp_into(pobj, tmp, s_obj, order: int):
        """Salin snapshot tmp → pobj, pindahkan seluruh detail tmp → pobj, lalu hapus tmp."""
        from .models import DetailAHSPProject
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
        # --- DEDUP DETAIL ---
        # Hindari UniqueViolation (project, pekerjaan, kode) dengan melewatkan baris TMP
        # yang 'kode'-nya sudah ada pada target.
        existing_kodes = set(
            DetailAHSPProject.objects
            .filter(project=project, pekerjaan=pobj)
            .values_list("kode", flat=True)
        )
        tmp_qs = DetailAHSPProject.objects.filter(project=project, pekerjaan=tmp)
        if existing_kodes:
            tmp_qs = tmp_qs.exclude(kode__in=existing_kodes)
        # Pindahkan hanya baris yang tidak bentrok
        tmp_qs.update(pekerjaan=pobj)
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
                    replace = False
                    new_ref_id = p.get("ref_id")

                    # Ganti tipe sumber → pasti replace
                    if pobj.source_type != src:
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
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    if pkj.source_type == Pekerjaan.SOURCE_REF:
        return JsonResponse({
            "ok": False,
            "errors": [_err("source_type", "Pekerjaan referensi tidak bisa diubah di tahap ini (gunakan tahap Gabungan).")]
        }, status=400)

    # Parse payload
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    rows = payload.get('rows') or []
    if not isinstance(rows, list):
        return JsonResponse({"ok": False, "errors": [_err("rows", "Harus list")]}, status=400)

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

        # --- Bundle referensi (opsional) — hanya untuk CUSTOM.LAIN ---
        ref_ahsp_obj = None
        ref_ahsp_id_raw = r.get('ref_ahsp_id', None)
        if ref_ahsp_id_raw not in (None, ''):
            # harus integer
            try:
                ref_ahsp_id = int(ref_ahsp_id_raw)
            except (TypeError, ValueError):
                errors.append(_err(f"rows[{i}].ref_ahsp_id", "Harus integer")); continue

            # hanya boleh pada pekerjaan custom
            if pkj.source_type != Pekerjaan.SOURCE_CUSTOM:
                errors.append(_err(f"rows[{i}].ref_ahsp_id", "Hanya boleh untuk pekerjaan custom")); continue

            # dan hanya pada kategori LAIN
            if kat != HargaItemProject.KATEGORI_LAIN:
                errors.append(_err(f"rows[{i}].ref_ahsp_id", "Hanya boleh pada kategori 'Lain-lain'")); continue

            # cek eksistensi referensi
            try:
                ref_ahsp_obj = AHSPReferensi.objects.get(id=ref_ahsp_id)
            except AHSPReferensi.DoesNotExist:
                errors.append(_err(f"rows[{i}].ref_ahsp_id", f"Referensi #{ref_ahsp_id} tidak ditemukan")); continue

        # --- Kumpulkan baris tervalidasi ---
        normalized.append((kat, kode, uraian, satuan, koef, ref_ahsp_obj))

    # Bila semua baris error → 400
    if errors and not normalized:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    # Replace-all: hapus lama, masukkan yang baru
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()

    to_create = []
    dp_koef = DECIMAL_SPEC["KOEF"].dp  # default 6
    for kat, kode, uraian, satuan, koef, ref_ahsp_obj in normalized:
        hip = _upsert_harga_item(project, kat, kode, uraian, satuan)
        to_create.append(DetailAHSPProject(
            project=project,
            pekerjaan=pkj,
            harga_item=hip,
            kategori=kat,
            kode=kode,
            uraian=uraian,
            satuan=satuan,
            koefisien=quantize_half_up(koef, dp_koef),  # HALF_UP dp=6
            # Field baru: hanya isi untuk CUSTOM + LAIN (sesuai constraint)
            ref_ahsp=(ref_ahsp_obj if (kat == HargaItemProject.KATEGORI_LAIN and pkj.source_type == Pekerjaan.SOURCE_CUSTOM) else None),
        ))

    if to_create:
        DetailAHSPProject.objects.bulk_create(to_create, ignore_conflicts=True)

    # detail_ready untuk custom & ref_modified
    Pekerjaan.objects.filter(pk=pkj.pk).update(detail_ready=(len(to_create) > 0))
    # NEW: detail berubah → rekap berubah
    invalidate_rekap_cache(project)
    status_code = 207 if errors else 200
    return JsonResponse({"ok": status_code == 200, "saved_rows": len(to_create), "errors": errors}, status=status_code)

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
    temp = clone_ref_pekerjaan(
        project, pkj.sub_klasifikasi, ref_obj, Pekerjaan.SOURCE_REF_MOD,
        ordering_index=pkj.ordering_index, auto_load_rincian=True,
        override_uraian=pkj.snapshot_uraian or None,
        override_satuan=pkj.snapshot_satuan or None,
    )

    moved = 0
    if temp:
        # --- DEDUP saat reset (aman walau sebelumnya sudah delete) ---
        from .models import DetailAHSPProject
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
    project = _owner_or_404(project_id, request.user)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    items = payload.get('items') or []
    errors = []
    updated = 0

    allowed_ids = set(HargaItemProject.objects
                      .filter(project=project, detail_refs__project=project)
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

        HargaItemProject.objects.filter(project=project, id=item_id).update(
            harga_satuan=quantize_half_up(dec, dp)
        )
        updated += 1

    # === NEW: BUK (opsional)
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

    # NEW: rekap berubah jika ada harga/BUK yang berubah
    if updated > 0 or pricing_saved:
        invalidate_rekap_cache(project)

    # kirim balik nilai BUK terbaru untuk sinkronisasi FE
    pricing = _get_or_create_pricing(project)
    return JsonResponse(
        {
            "ok": status_code == 200,
            "updated": updated,
            "pricing_saved": pricing_saved,
            "markup_percent": to_dp_str(pricing.markup_percent, 2),
            "errors": errors,
        },
        status=status_code
    )

# ---------- View: Project Pricing (BUK) ----------
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

    # Ambil BUK proyek
    pricing = _get_or_create_pricing(project)
    mp = pricing.markup_percent or Decimal("10.00")   # Decimal

    D = totals["total_langsung"]                      # biaya langsung
    E = (D * (mp / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # BUK
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

    # Footer ringkas (opsional): total & BUK
    D = totals["total_langsung"]
    E = (D * (mp / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    G = (D + E).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lines += [
        "",
        f"TOTAL LANGSUNG (D);{D}",
        f"BUK %;{mp}",
        f"BUK (E);{E}",
        f"GRAND TOTAL (D+E);{G}",
    ]

    csv = "\n".join(lines)
    resp = HttpResponse(csv, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename=\"rincian_rab_{project.id}.csv\"'
    return resp

# ---------- View 6: Rekap ----------

@login_required
def api_list_harga_items(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)
    qs = (HargaItemProject.objects
          .filter(project=project, detail_refs__project=project)
          .distinct()
          .order_by('kode_item'))
    items = list(qs.values('id','kode_item','kategori','uraian','satuan','harga_satuan'))

    if request.GET.get('canon') == '1':
        dp = getattr(HargaItemProject._meta.get_field('harga_satuan'), 'decimal_places', DECIMAL_SPEC["HARGA"].dp)
        for it in items:
            it['harga_satuan'] = to_dp_str(it.get('harga_satuan'), dp)  # "12345.67" atau None

    # === NEW: expose BUK default 10.00% sebagai string "10.00"
    pricing = _get_or_create_pricing(project)
    meta = { "markup_percent": to_dp_str(pricing.markup_percent, 2) }

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

@login_required
def api_export_rekap_kebutuhan_csv(request, project_id: int):
    project = _owner_or_404(project_id, request.user)
    from .services import compute_kebutuhan_items
    rows = compute_kebutuhan_items(project)

    def q(v):
        return (str(v or "")
                .replace(";", ",")
                .replace("\r", " ")
                .replace("\n", " "))

    lines = ["kategori;kode;uraian;satuan;quantity"]
    use_canon = (request.GET.get("canon") == "1")
    dp_vol   = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', DECIMAL_SPEC["VOL"].dp)
    for r in rows:
        qty = r.get("quantity")
        qty_str = to_dp_str(qty, dp_vol) if use_canon else q(qty)
        lines.append(";".join([
            q(r.get("kategori")),
            q(r.get("kode")),
            q(r.get("uraian")),
            q(r.get("satuan")),
            qty_str,
        ]))
    csv = "\n".join(lines)
    resp = HttpResponse(csv, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="rekap_kebutuhan_{project.id}.csv"'
    return resp

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