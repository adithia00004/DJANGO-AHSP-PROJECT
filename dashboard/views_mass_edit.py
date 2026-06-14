import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse

from .forms import ProjectForm
from .models import Project
from .views import UPLOAD_ALL_HEADERS


logger = logging.getLogger(__name__)


@login_required
def mass_edit_bulk_update(request):
    """Validate and update selected projects as one atomic operation."""
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

                form = ProjectForm(merged_data, instance=project)
                if form.is_valid():
                    valid_forms.append(form)
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

            for form in valid_forms:
                form.save()

        updated_count = len(valid_forms)
        return JsonResponse(
            {
                "success": True,
                "updated_count": updated_count,
                "message": f"{updated_count} project berhasil diperbarui.",
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
