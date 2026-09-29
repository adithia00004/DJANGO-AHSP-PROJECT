import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse

from .forms import ProjectForm
from .models import Project
from .views import UPLOAD_ALL_HEADERS
from detail_project.timeline_utils import (
    TimelineChangeError,
    analyze_project_timeline_change,
    apply_project_timeline_change,
)


logger = logging.getLogger(__name__)


def _decision_message(impact):
    """Alasan singkat, dalam bahasa user, kenapa project ini butuh keputusan."""
    if impact.get("blocking_reason") == "actual_present_start_shift":
        return (
            "Tanggal mulai bergeser sedangkan project sudah memiliki realisasi. "
            "Realisasi tidak dipindahkan otomatis."
        )
    if impact.get("blocking_reason") == "actual_out_of_window":
        return (
            "Tanggal baru melewati minggu yang sudah memiliki realisasi atau "
            "biaya aktual."
        )
    if impact.get("planned_extension_records"):
        return (
            "Perubahan akhir waktu kerja membuat rencana berada di masa tambahan. "
            "Ubah project satu per satu untuk memilih pemindahan rencana atau membatalkan."
        )
    if impact.get("start_requires_policy"):
        return (
            "Tanggal mulai bergeser sedangkan project sudah memiliki rencana "
            "progress. Pilih cara penataan minggunya."
        )
    return (
        "Tanggal baru melewati minggu yang sudah memiliki rencana progress. "
        "Pilih cara penataan minggunya."
    )


def _decision_entry(project, impact, message):
    return {
        "id": project.pk,
        "nama": project.nama,
        "reason": message,
        "blocking_reason": (impact or {}).get("blocking_reason"),
        "allowed_resolutions": (impact or {}).get("allowed_resolutions", []),
        "recommended_resolution": (impact or {}).get("recommended_resolution"),
        "planned_records": (impact or {}).get("planned_records", 0),
        "planned_extension_records": (impact or {}).get("planned_extension_records", 0),
        "actual_records": (impact or {}).get("actual_records", 0),
    }


@login_required
def mass_edit_bulk_update(request):
    """Validate and update selected projects.

    Dua kelas kegagalan yang sengaja dibedakan (keputusan G0-3, tracker doc 39 §0):

    * **Validasi & otorisasi** tetap *all-or-nothing*. Satu project tidak valid,
      atau satu project bukan milik user, membatalkan seluruh batch.
    * **Perubahan timeline yang memerlukan keputusan user** tidak membatalkan
      batch. Project seperti itu dilewati utuh — tidak ada satu pun field yang
      tersimpan untuknya — lalu dilaporkan di ``needs_decision`` agar user
      menyelesaikannya lewat form edit tunggal.

    Sebelumnya perubahan ``tanggal_mulai`` memanggil ``reset_project_progress``,
    yang menghapus SELURUH ``PekerjaanProgressWeekly`` milik project termasuk
    realisasi, tanpa peringatan; dan perubahan ``tanggal_selesai`` tidak memicu
    apa pun sehingga jadwal menjadi basi. Keduanya kini lewat
    ``apply_project_timeline_change``.
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Metode request tidak diizinkan."},
            status=405,
        )

    try:
        data = json.loads(request.body)
        changes = data.get("changes", [])
        if not isinstance(changes, list) or not changes:
            return JsonResponse(
                {"success": False, "message": "Tidak ada perubahan yang dikirim."},
                status=400,
            )
        if len(changes) > 100:
            return JsonResponse(
                {"success": False, "message": "Maksimal 100 project per penyimpanan."},
                status=400,
            )

        change_by_id = {}
        request_errors = {}
        for index, change in enumerate(changes):
            if not isinstance(change, dict):
                request_errors[str(index)] = {
                    "__all__": ["Format perubahan tidak valid."]
                }
                continue
            try:
                project_id = int(change.get("id"))
            except (TypeError, ValueError):
                request_errors[str(index)] = {"id": ["ID project tidak valid."]}
                continue
            if project_id in change_by_id:
                request_errors[str(project_id)] = {
                    "id": ["ID project dikirim lebih dari sekali."]
                }
                continue
            change_by_id[project_id] = change

        if request_errors:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Payload perubahan tidak valid.",
                    "errors": request_errors,
                },
                status=400,
            )

        with transaction.atomic():
            projects = {
                project.pk: project
                for project in Project.objects.select_for_update().filter(
                    pk__in=change_by_id,
                    owner=request.user,
                )
            }
            missing_ids = sorted(set(change_by_id) - set(projects))
            if missing_ids:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Sebagian project tidak ditemukan atau bukan milik Anda."
                        ),
                        "errors": {
                            str(project_id): {
                                "id": ["Project tidak dapat diakses."]
                            }
                            for project_id in missing_ids
                        },
                    },
                    status=403,
                )

            valid_forms = []
            validation_errors = {}
            for project_id, change in change_by_id.items():
                project = projects[project_id]
                merged_data = {}
                for field_name in UPLOAD_ALL_HEADERS:
                    if field_name in change:
                        merged_data[field_name] = change[field_name]
                        continue
                    value = getattr(project, field_name)
                    if hasattr(value, "isoformat"):
                        value = value.isoformat()
                    merged_data[field_name] = "" if value is None else str(value)

                if project.allow_bundle_soft_errors:
                    merged_data["allow_bundle_soft_errors"] = "on"

                original_start = project.tanggal_mulai
                original_end = project.tanggal_selesai
                form = ProjectForm(merged_data, instance=project)
                if form.is_valid():
                    valid_forms.append((form, original_start, original_end))
                else:
                    validation_errors[str(project_id)] = {
                        field_name: [
                            item["message"]
                            for item in field_errors
                        ]
                        for field_name, field_errors in (
                            form.errors.get_json_data().items()
                        )
                    }

            if validation_errors:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Perubahan dibatalkan karena ada data yang tidak valid."
                        ),
                        "errors": validation_errors,
                    },
                    status=400,
                )

            # Perubahan timeline TIDAK lagi menghapus progress secara senyap.
            # Project yang perubahannya aman disimpan seperti biasa; project yang
            # memerlukan keputusan user dilewati utuh dan dilaporkan, bukan
            # membatalkan seluruh batch (keputusan G0-3, tracker doc 39 §0).
            updated_count = 0
            needs_decision = []

            for form, original_start, original_end in valid_forms:
                project = form.instance
                new_start = form.cleaned_data.get("tanggal_mulai")
                new_end = form.cleaned_data.get("tanggal_selesai")
                timeline_changed = (
                    (original_start or None) != (new_start or None)
                    or (original_end or None) != (new_end or None)
                )

                if not timeline_changed:
                    form.save()
                    updated_count += 1
                    continue

                try:
                    impact = analyze_project_timeline_change(
                        project, new_start, new_end
                    )
                except TimelineChangeError as exc:
                    needs_decision.append(
                        _decision_entry(project, exc.impact, str(exc))
                    )
                    continue

                if (
                    impact.get("blocking_reason")
                    or impact.get("start_requires_policy")
                    or impact.get("planned_records")
                    or impact.get("planned_extension_records")
                ):
                    needs_decision.append(
                        _decision_entry(project, impact, _decision_message(impact))
                    )
                    continue

                # Aman: satu service, satu kebijakan. Perubahan tanggal selesai
                # ikut lewat sini, sehingga struktur jadwal dibangun ulang (T-02).
                try:
                    apply_project_timeline_change(
                        project,
                        new_start,
                        new_end,
                        resolution="none",
                        user=request.user,
                        expected_revision=project.schedule_revision,
                    )
                except TimelineChangeError as exc:
                    needs_decision.append(
                        _decision_entry(project, exc.impact, str(exc))
                    )
                    continue

                # Service sudah menyimpan tanggal dan membangun ulang jadwal.
                # Refresh hanya revisi internal: refresh penuh akan membuang
                # cleaned_data yang belum sempat tersimpan lewat form.save().
                project.refresh_from_db(fields=["schedule_revision", "tanggal_akhir_tambahan"])
                form.save()
                updated_count += 1

        if needs_decision:
            message = (
                f"{updated_count} project berhasil diperbarui. "
                f"{len(needs_decision)} project memerlukan keputusan Anda dan "
                f"belum tersimpan."
            )
        else:
            message = f"{updated_count} project berhasil diperbarui."

        return JsonResponse(
            {
                "success": True,
                "updated_count": updated_count,
                "needs_decision": needs_decision,
                "message": message,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Format JSON tidak valid."},
            status=400,
        )
    except Exception:
        logger.exception(
            "Mass edit project failed",
            extra={"user_id": request.user.id},
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Terjadi kesalahan saat memperbarui project.",
            },
            status=500,
        )
