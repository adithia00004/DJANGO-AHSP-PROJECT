# ================================
# detail_project/views_api.py
# ================================
import json
from typing import Any
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP  # <-- NEW: Decimal handling
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.db.models import Max

from referensi.models import AHSPReferensi

from .models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    DetailAHSPProject, HargaItemProject,VolumeFormulaState,  # NEW
)
from .services import (
    clone_ref_pekerjaan, _upsert_harga_item, compute_rekap_for_project,
    generate_custom_code,
)

# Util
def _err(path: str, message: str):
    return {"path": path, "message": message}

def _owner_or_404(project_id, user):
    from dashboard.models import Project
    return get_object_or_404(Project, id=project_id, owner=user, is_active=True)

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
            k_name = (k.get('name') or f"Klasifikasi {k_counter}").strip()
            k_order = int(k.get('ordering_index') or k_counter)

            # Klasifikasi
            try:
                k_obj = Klasifikasi.objects.create(project=project, name=k_name, ordering_index=k_order)
            except IntegrityError as e:
                errors.append(_err(f"klasifikasi[{ki}]", f"Gagal membuat klasifikasi: {e}"))
                continue
            id_map['klasifikasi'][k.get('temp_id') or f"k{ki}"] = k_obj.id

            # Sub
            sub_list = k.get('sub') or []
            if not isinstance(sub_list, list):
                errors.append(_err(f"klasifikasi[{ki}].sub", "Harus berupa list"))
                continue

            for si, s in enumerate(sub_list):
                s_name = (s.get('name') or f"{ki+1}.{si+1}").strip()
                s_order = int(s.get('ordering_index') or (si+1))
                try:
                    s_obj = SubKlasifikasi.objects.create(project=project, klasifikasi=k_obj, name=s_name, ordering_index=s_order)
                except IntegrityError as e:
                    errors.append(_err(f"klasifikasi[{ki}].sub[{si}]", f"Gagal membuat sub: {e}"))
                    continue
                id_map['sub'][s.get('temp_id') or f"s{ki}_{si}"] = s_obj.id

                # Pekerjaan
                pekerjaan_list = s.get('pekerjaan') or []
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
    return JsonResponse({"ok": True, "id_map": id_map, "summary": summary})

# helper untuk normalisasi source_type
def _src_to_str(val):
  m = {
      Pekerjaan.SOURCE_REF: 'ref',
      Pekerjaan.SOURCE_CUSTOM: 'custom',
      Pekerjaan.SOURCE_REF_MOD: 'ref_modified',
  }
  return m.get(val, val)

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
      * Khusus REF/REF_MOD ketika reuse: clone ke TEMP dgn temp_order aman, adopsi ke record reuse,
        pindahkan seluruh Detail dari TEMP ke record reuse, lalu hapus TEMP (hindari UniqueViolation).
    - Entitas yang tidak ada di payload akan dihapus (idempotent).
    """
    def _safe_int(x, default):
        try:
            return int(x)
        except Exception:
            return default

    project = _owner_or_404(project_id, request.user)

    # Parse payload
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    klas_list = payload.get('klasifikasi') or []
    if not isinstance(klas_list, list):
        return JsonResponse({"ok": False, "errors": [_err("klasifikasi", "Harus list")]}, status=400)

    # ============================
    # PRE-FLIGHT VALIDATION (BARU)
    # ============================
    # Cek error fatal yang harus menggagalkan request SEBELUM ada tulis DB
    pre_errors = []
    for ki, k in enumerate(klas_list):
        sub_list = k.get('sub') or []
        if not isinstance(sub_list, list):
            pre_errors.append(_err(f"klasifikasi[{ki}].sub", "Harus list"))
            continue
        for si, s in enumerate(sub_list):
            pekerjaan_list = s.get('pekerjaan') or []
            if not isinstance(pekerjaan_list, list):
                pre_errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan", "Harus list"))
                continue
            for pi, p in enumerate(pekerjaan_list):
                src = _str_to_src(p.get('source_type'))
                # ref/ref_modified WAJIB ref_id
                if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                    if not p.get('ref_id'):
                        pre_errors.append(_err(
                            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                            "Wajib untuk source=ref/ref_modified"
                        ))
                # custom WAJIB snapshot_uraian (boleh kosongkan satuan)
                elif src == Pekerjaan.SOURCE_CUSTOM:
                    if not (p.get('snapshot_uraian') or '').strip():
                        pre_errors.append(_err(
                            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian",
                            "Wajib untuk custom"
                        ))
                else:
                    pre_errors.append(_err(
                        f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].source_type",
                        "Nilai tidak valid"
                    ))

    if pre_errors:
        # Gagalkan seluruh request → tidak ada create/update terjadi
        return JsonResponse({"ok": False, "errors": pre_errors}, status=400)

    # ============================
    # LANJUT PROSES UPSERT (lama)
    # ============================
    errors = []
    keep_k = set()

    existing_k = {k.id: k for k in Klasifikasi.objects.filter(project=project)}
    existing_s = {s.id: s for s in SubKlasifikasi.objects.filter(project=project)}
    existing_p = {p.id: p for p in Pekerjaan.objects.filter(project=project)}

    def _get_or_reuse_pekerjaan_for_order(order: int):
        """Cari Pekerjaan berdasarkan natural key (project, ordering_index)."""
        return Pekerjaan.objects.filter(project=project, ordering_index=order).first()

    def _get_safe_temp_order():
        """Dapatkan ordering sementara yang aman agar tidak tabrakan uniq (project, ordering_index)."""
        max_order = Pekerjaan.objects.filter(project=project).aggregate(Max('ordering_index'))['ordering_index__max'] or 0
        return max_order + 1_000_000  # lompat jauh

    def _adopt_tmp_into(pobj, tmp, s_obj, order: int):
        """
        Salin snapshot tmp → pobj, pindahkan seluruh detail tmp → pobj, lalu hapus tmp.
        """
        from .models import DetailAHSPProject  # import lokal untuk hindari import cycle
        pobj.sub_klasifikasi = s_obj
        pobj.source_type = tmp.source_type
        pobj.snapshot_kode = tmp.snapshot_kode
        pobj.snapshot_uraian = tmp.snapshot_uraian
        pobj.snapshot_satuan = tmp.snapshot_satuan
        pobj.ordering_index = order
        pobj.save(update_fields=[
            'sub_klasifikasi', 'source_type',
            'snapshot_kode', 'snapshot_uraian',
            'snapshot_satuan', 'ordering_index'
        ])
        DetailAHSPProject.objects.filter(project=project, pekerjaan=tmp).update(pekerjaan=pobj)
        tmp.delete()

    # === Loop utama ===
    for ki, k in enumerate(klas_list):
        k_id = k.get('id')
        k_name = (k.get('name') or f"Klasifikasi {ki+1}").strip()
        k_order = _safe_int(k.get('ordering_index'), ki+1)

        # Upsert Klasifikasi by natural key
        if k_id and k_id in existing_k:
            k_obj = existing_k[k_id]
            k_obj.name = k_name
            k_obj.ordering_index = k_order
            k_obj.save(update_fields=['name', 'ordering_index'])
        else:
            k_obj = Klasifikasi.objects.filter(project=project, ordering_index=k_order).first()
            if k_obj:
                if k_obj.name != k_name:
                    k_obj.name = k_name
                    k_obj.save(update_fields=['name'])
            else:
                k_obj = Klasifikasi.objects.create(project=project, name=k_name, ordering_index=k_order)
        keep_k.add(k_obj.id)

        keep_s = set()
        sub_list = k.get('sub') or []
        if not isinstance(sub_list, list):
            errors.append(_err(f"klasifikasi[{ki}].sub", "Harus list"))
            continue

        for si, s in enumerate(sub_list):
            s_id = s.get('id')
            s_name = (s.get('name') or f"{ki+1}.{si+1}").strip()
            s_order = _safe_int(s.get('ordering_index'), si+1)

            # Upsert SubKlasifikasi by natural key
            if s_id and s_id in existing_s and existing_s[s_id].klasifikasi_id == k_obj.id:
                s_obj = existing_s[s_id]
                s_obj.name = s_name
                s_obj.ordering_index = s_order
                s_obj.klasifikasi = k_obj
                s_obj.save(update_fields=['name', 'ordering_index', 'klasifikasi'])
            else:
                s_obj = SubKlasifikasi.objects.filter(project=project, klasifikasi=k_obj, ordering_index=s_order).first()
                if s_obj:
                    if s_obj.name != s_name:
                        s_obj.name = s_name
                        s_obj.save(update_fields=['name'])
                else:
                    s_obj = SubKlasifikasi.objects.create(
                        project=project, klasifikasi=k_obj, name=s_name, ordering_index=s_order
                    )
            keep_s.add(s_obj.id)

            keep_p = set()
            pekerjaan_list = s.get('pekerjaan') or []
            if not isinstance(pekerjaan_list, list):
                errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan", "Harus list"))
                continue

            for pi, p in enumerate(pekerjaan_list):
                src_in = p.get('source_type')
                src = _str_to_src(src_in)
                if src not in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_CUSTOM, Pekerjaan.SOURCE_REF_MOD]:
                    errors.append(_err(f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].source_type", "Nilai tidak valid"))
                    continue

                order = _safe_int(p.get('ordering_index'), pi + 1)
                p_id = p.get('id')

                # optional override utk ref_modified (jika dikirim dari UI)
                ov_ura = (p.get('snapshot_uraian') or '').strip() or None
                ov_sat = (p.get('snapshot_satuan') or '').strip() or None

                if p_id and p_id in existing_p and existing_p[p_id].project_id == project.id:
                    # UPDATE in-place (dengan kemungkinan REPLACE)
                    pobj = existing_p[p_id]
                    replace = False
                    new_ref_id = p.get('ref_id')
                    if pobj.source_type != src:
                        replace = True
                    elif src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and new_ref_id:
                        replace = True

                    if replace:
                        pobj.delete()
                        try:
                            if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                                if not new_ref_id:
                                    errors.append(_err(
                                        f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                                        "Wajib saat mengganti REF/REF_MOD"
                                    ))
                                    continue
                                ref_obj = AHSPReferensi.objects.get(id=new_ref_id)

                                # REUSE by (project, ordering_index) dgn temp clone aman
                                pobj_reuse = _get_or_reuse_pekerjaan_for_order(order)
                                if pobj_reuse:
                                    temp_order = _get_safe_temp_order()
                                    tmp = clone_ref_pekerjaan(
                                        project, s_obj, ref_obj, src,
                                        ordering_index=temp_order, auto_load_rincian=True,
                                        override_uraian=ov_ura if src == Pekerjaan.SOURCE_REF_MOD else None,
                                        override_satuan=ov_sat if src == Pekerjaan.SOURCE_REF_MOD else None,
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
                            else:
                                # custom baru (replace)
                                uraian = (p.get('snapshot_uraian') or '').strip()
                                if not uraian:
                                    errors.append(_err(
                                        f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian",
                                        "Wajib untuk custom baru"
                                    ))
                                    continue
                                satuan = (p.get('snapshot_satuan') or None)
                                pobj = _get_or_reuse_pekerjaan_for_order(order)
                                if pobj:
                                    pobj.sub_klasifikasi = s_obj
                                    pobj.source_type = src
                                    if not pobj.snapshot_kode:
                                        pobj.snapshot_kode = generate_custom_code(project)
                                    pobj.snapshot_uraian = uraian
                                    pobj.snapshot_satuan = satuan
                                    pobj.ordering_index = order
                                    pobj.save(update_fields=[
                                        'sub_klasifikasi', 'source_type',
                                        'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan', 'ordering_index'
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
                                f"Referensi #{new_ref_id} tidak ditemukan"
                            ))
                            continue
                    else:
                        # Update biasa
                        pobj.ordering_index = order
                        pobj.sub_klasifikasi = s_obj
                        if src == Pekerjaan.SOURCE_CUSTOM:
                            pobj.snapshot_uraian = (p.get('snapshot_uraian') or pobj.snapshot_uraian or '').strip()
                            val_sat = p.get('snapshot_satuan')
                            pobj.snapshot_satuan = (val_sat or pobj.snapshot_satuan)
                            if not pobj.snapshot_kode:
                                pobj.snapshot_kode = generate_custom_code(project)
                        elif src == Pekerjaan.SOURCE_REF_MOD:
                            # izinkan minor override jika dikirim
                            if ov_ura: pobj.snapshot_uraian = ov_ura
                            if ov_sat: pobj.snapshot_satuan = ov_sat
                        pobj.save(update_fields=[
                            'ordering_index', 'sub_klasifikasi', 'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan'
                        ])

                else:
                    # CREATE BARU (atau REUSE by natural key)
                    try:
                        if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD]:
                            ref_id = p.get('ref_id')
                            if not ref_id:
                                errors.append(_err(
                                    f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
                                    "Wajib untuk source=ref/ref_modified"
                                ))
                                continue
                            ref_obj = AHSPReferensi.objects.get(id=ref_id)

                            pobj_reuse = _get_or_reuse_pekerjaan_for_order(order)
                            if pobj_reuse:
                                temp_order = _get_safe_temp_order()
                                tmp = clone_ref_pekerjaan(
                                    project, s_obj, ref_obj, src,
                                    ordering_index=temp_order, auto_load_rincian=True,
                                    override_uraian=ov_ura if src == Pekerjaan.SOURCE_REF_MOD else None,
                                    override_satuan=ov_sat if src == Pekerjaan.SOURCE_REF_MOD else None,
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
                        else:
                            uraian = (p.get('snapshot_uraian') or '').strip()
                            if not uraian:
                                errors.append(_err(
                                    f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].snapshot_uraian",
                                    "Wajib untuk custom"
                                ))
                                continue
                            satuan = (p.get('snapshot_satuan') or None)
                            pobj = _get_or_reuse_pekerjaan_for_order(order)
                            if pobj:
                                pobj.sub_klasifikasi = s_obj
                                pobj.source_type = src
                                if not pobj.snapshot_kode:
                                    pobj.snapshot_kode = generate_custom_code(project)
                                pobj.snapshot_uraian = uraian
                                pobj.snapshot_satuan = satuan
                                pobj.ordering_index = order
                                pobj.save(update_fields=[
                                    'sub_klasifikasi', 'source_type',
                                    'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan', 'ordering_index'
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

                keep_p.add(pobj.id)

            # Hapus pekerjaan yang tidak ada di payload sub ini
            Pekerjaan.objects.filter(project=project, sub_klasifikasi=s_obj).exclude(id__in=keep_p).delete()

        # Hapus sub yang tidak ada lagi
        SubKlasifikasi.objects.filter(project=project, klasifikasi=k_obj).exclude(id__in=keep_s).delete()

    # Hapus klasifikasi yang tidak ada lagi
    Klasifikasi.objects.filter(project=project).exclude(id__in=keep_k).delete()

    status = 200 if not errors else 207
    summary = {
        "klasifikasi": Klasifikasi.objects.filter(project=project).count(),
        "sub": SubKlasifikasi.objects.filter(project=project).count(),
        "pekerjaan": Pekerjaan.objects.filter(project=project).count(),
    }
    return JsonResponse({"ok": status == 200, "errors": errors, "summary": summary}, status=status)



# ---------- View 2: Volume ----------
@login_required
@require_POST
@transaction.atomic
def api_save_volume_pekerjaan(request: HttpRequest, project_id: int):
    """
    Simpan volume pekerjaan.
    - Backward-compatible: payload tetap { items: [{pekerjaan_id, quantity}] }.
    - Penerimaan angka lebih robust: terima koma (,) dan underscore (_).
    - Simpan sebagai Decimal dengan pembulatan HALF_UP ke decimal_places field model (saat ini 3).
    """
    project = _owner_or_404(project_id, request.user)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    items = payload.get('items') or []
    if not isinstance(items, list):
        return JsonResponse({"ok": False, "errors": [_err("items", "Harus berupa list")]}, status=400)

    # Ambil jumlah desimal dari model agar dinamis bila berubah di masa depan
    dp = getattr(VolumePekerjaan._meta.get_field('quantity'), 'decimal_places', 3)
    quantum = Decimal('1').scaleb(-dp)  # 10^-dp, mis. 0.001

    errors = []
    saved = 0

    for i, it in enumerate(items):
        pkj_id = it.get('pekerjaan_id')
        qty = it.get('quantity')

        if pkj_id is None:
            errors.append(_err(f"items[{i}].pekerjaan_id", "Wajib")); continue

        try:
            pkj = Pekerjaan.objects.get(id=pkj_id, project=project)
        except Pekerjaan.DoesNotExist:
            errors.append(_err(f"items[{i}].pekerjaan_id", "Tidak ditemukan di project ini")); continue

        # Normalisasi & validasi angka → Decimal
        try:
            if isinstance(qty, str):
                s = qty.strip().replace('_', '').replace(',', '.')
            else:
                s = str(qty)
            dec = Decimal(s)
            if dec < 0:
                raise InvalidOperation
        except Exception:
            errors.append(_err(f"items[{i}].quantity", "Harus ≥ 0 dan berupa angka yang valid")); continue

        # Quantize HALF_UP ke dp
        dec_q = dec.quantize(quantum, rounding=ROUND_HALF_UP)

        VolumePekerjaan.objects.update_or_create(
            project=project, pekerjaan=pkj,
            defaults=dict(quantity=dec_q)
        )
        saved += 1

    status_code = 400 if errors and not saved else 200
    # Tambahkan info decimal_places (opsional, backward-compatible)
    return JsonResponse(
        {"ok": status_code == 200, "saved": saved, "errors": errors, "decimal_places": dp},
        status=status_code
    )

# ---------- View 3: Detail AHSP per Pekerjaan ----------
@login_required
@require_POST
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan(request: HttpRequest, project_id: int, pekerjaan_id: int):
    project = _owner_or_404(project_id, request.user)
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)

    if pkj.source_type == Pekerjaan.SOURCE_REF:
        return JsonResponse({"ok": False, "errors": [_err("source_type", "Pekerjaan referensi tidak bisa diubah di tahap ini (gunakan tahap Gabungan).") ]}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"ok": False, "errors": [_err("$", "Payload JSON tidak valid")]}, status=400)

    rows = payload.get('rows') or []
    if not isinstance(rows, list):
        return JsonResponse({"ok": False, "errors": [_err("rows", "Harus list")]}, status=400)

    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()

    valid_count = 0
    errors = []
    created_details = []

    for i, r in enumerate(rows):
        kat = r.get('kategori')
        if kat not in dict(HargaItemProject.KATEGORI_CHOICES):
            errors.append(_err(f"rows[{i}].kategori", "Kategori tidak valid")); continue
        kode = (r.get('kode') or '').strip()
        uraian = (r.get('uraian') or '').strip()
        satuan = (r.get('satuan') or '').strip() or None
        try:
            koef = float(r.get('koefisien'))
            if koef < 0:
                raise ValueError
        except Exception:
            errors.append(_err(f"rows[{i}].koefisien", "Harus ≥ 0")); continue

        if not uraian:
            errors.append(_err(f"rows[{i}].uraian", "Wajib")); continue
        if not kode:
            errors.append(_err(f"rows[{i}].kode", "Wajib")); continue

        hip = _upsert_harga_item(project, kat, kode, uraian, satuan)

        created_details.append(DetailAHSPProject(
            project=project,
            pekerjaan=pkj,
            harga_item=hip,
            kategori=kat,
            kode=kode,
            uraian=uraian,
            satuan=satuan,
            koefisien=Decimal(str(koef)),
        ))
        valid_count += 1

    if created_details:
        DetailAHSPProject.objects.bulk_create(created_details, ignore_conflicts=True)

    if pkj.source_type == Pekerjaan.SOURCE_CUSTOM:
        pkj.detail_ready = valid_count > 0
        pkj.save(update_fields=["detail_ready", "updated_at"])

    status_code = 200 if errors == [] else (400 if valid_count == 0 else 207)
    return JsonResponse({"ok": status_code == 200, "saved_rows": valid_count, "errors": errors}, status=status_code)

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

    for i, it in enumerate(items):
        item_id = it.get('id')
        harga = it.get('harga_satuan')
        if item_id is None:
            errors.append(_err(f"items[{i}].id", "Wajib")); continue
        if item_id not in allowed_ids:
            errors.append(_err(f"items[{i}].id", "Item ini tidak digunakan di Detail AHSP proyek")); continue
        try:
            val = float(harga)
            if val < 0:
                raise ValueError
        except Exception:
            errors.append(_err(f"items[{i}].harga_satuan", "Harus ≥ 0")); continue

        HargaItemProject.objects.filter(project=project, id=item_id).update(harga_satuan=Decimal(str(val)))
        updated += 1

    status_code = 400 if errors and not updated else 200
    return JsonResponse({"ok": status_code == 200, "updated": updated, "errors": errors}, status=status_code)

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
            try:
                koef = float(r.get('koefisien'))
                if koef < 0:
                    raise ValueError
            except Exception:
                all_errors.append(_err(f"items[{i}].rows[{j}].koefisien", "Harus ≥ 0")); continue
            if not uraian or not kode:
                all_errors.append(_err(f"items[{i}].rows[{j}]", "kode & uraian wajib")); continue
            hip = _upsert_harga_item(project, kat, kode, uraian, satuan)
            to_create.append(DetailAHSPProject(
                project=project, pekerjaan=pkj, harga_item=hip,
                kategori=kat, kode=kode, uraian=uraian, satuan=satuan, koefisien=Decimal(str(koef))
            ))
            saved_here += 1
        if to_create:
            DetailAHSPProject.objects.bulk_create(to_create, ignore_conflicts=True)
        total_saved += saved_here

    status_code = 200 if not all_errors else (207 if total_saved > 0 else 400)
    return JsonResponse({"ok": status_code == 200, "saved_rows": total_saved, "errors": all_errors}, status=status_code)

# ---------- View 6: Rekap ----------
@login_required
def api_list_harga_items(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)
    qs = (HargaItemProject.objects
          .filter(project=project, detail_refs__project=project)
          .distinct()
          .order_by('kode_item'))
    items = list(qs.values('id','kode_item','kategori','uraian','satuan','harga_satuan'))
    return JsonResponse({"ok": True, "items": items})

@login_required
def api_get_rekap_rab(request: HttpRequest, project_id: int):
    project = _owner_or_404(project_id, request.user)
    data = compute_rekap_for_project(project)
    return JsonResponse({"ok": True, "rows": data})


# ---------- View7 Volume Formula State (GET/POST di endpoint yang sama) ----------
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