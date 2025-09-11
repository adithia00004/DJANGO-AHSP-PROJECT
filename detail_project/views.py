# ================================
# detail_project/views.py (web views)
# ================================
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from .models import Pekerjaan


# --- Transisi aman: terima pid ATAU project_id ---
def coerce_project_id(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if 'project_id' not in kwargs and 'pid' in kwargs:
            kwargs['project_id'] = kwargs.pop('pid')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _project_or_404(project_id, user):
    from dashboard.models import Project
    return get_object_or_404(Project, id=project_id, owner=user, is_active=True)


@login_required
@coerce_project_id
def list_pekerjaan_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    context = {
        "project": project,
        "side_active": "list_pekerjaan",
    }
    return render(request, "detail_project/list_pekerjaan.html", context)


@login_required
@coerce_project_id
def volume_pekerjaan_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    pekerjaan = (
        Pekerjaan.objects
        .filter(project=project)
        .order_by('ordering_index', 'id')
        .values('id', 'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan')
    )
    context = {
        "project": project,
        "pekerjaan": pekerjaan,
        "side_active": "volume_pekerjaan",
    }
    return render(request, "detail_project/volume_pekerjaan.html", context)


@login_required
@coerce_project_id
def detail_ahsp_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    # tampilkan hanya custom & ref_modified
    pekerjaan = (
        Pekerjaan.objects
        .filter(project=project, source_type__in=[Pekerjaan.SOURCE_CUSTOM, Pekerjaan.SOURCE_REF_MOD])
        .order_by('ordering_index', 'id')
    )
    context = {
        "project": project,
        "pekerjaan": pekerjaan,
        "side_active": "detail_ahsp",
    }
    return render(request, "detail_project/detail_ahsp.html", context)


@login_required
@coerce_project_id
def harga_items_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    context = {
        "project": project,
        "side_active": "harga_items",
    }
    return render(request, "detail_project/harga_items.html", context)


@login_required
@coerce_project_id
def detail_ahsp_gabungan_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    pekerjaan = (
        Pekerjaan.objects
        .filter(project=project)
        .order_by('ordering_index', 'id')
    )
    context = {
        "project": project,
        "pekerjaan": pekerjaan,
        "side_active": "detail_ahsp_gabungan",
    }
    return render(request, "detail_project/detail_ahsp_gabungan.html", context)


@login_required
@coerce_project_id
def rekap_rab_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    context = {
        "project": project,
        "side_active": "rekap_rab",
    }
    return render(request, "detail_project/rekap_rab.html", context)
