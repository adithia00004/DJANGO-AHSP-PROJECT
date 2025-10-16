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
        .select_related('sub_klasifikasi', 'sub_klasifikasi__klasifikasi')
        .order_by('ordering_index', 'id')
    )
    context = {
        "project": project,
        "pekerjaan": pekerjaan,
        "side_active": "volume_pekerjaan",
    }
    return render(request, "detail_project/volume_pekerjaan.html", context)


@login_required
@coerce_project_id

def template_ahsp_view(request, project_id: int):
    """
    (RENAMED) Page 'Template AHSP'.
    Sidebar HARUS menampilkan SEMUA pekerjaan (REF, REF_MODIFIED, CUSTOM).
    Mode edit/read-only diatur oleh API get-detail (meta.read_only), bukan disaring di sini.
    """
    project = _project_or_404(project_id, request.user)

    # ⬇️ PENTING: JANGAN filter source_type. Ambil semua pekerjaan.
    pekerjaan = (
        Pekerjaan.objects
        .filter(project=project)
        .select_related("sub_klasifikasi", "sub_klasifikasi__klasifikasi", "ref")
        .order_by("ordering_index", "id")
    )

    ctx = {
        "project": project,
        "pekerjaan": pekerjaan,  # ← sidebar akan melisting semuanya
        # kalau template Anda butuh stats (opsional):
        "count_ref": sum(1 for p in pekerjaan if p.source_type == Pekerjaan.SOURCE_REF),
        "count_mod": sum(1 for p in pekerjaan if p.source_type == Pekerjaan.SOURCE_REF_MOD),
        "count_custom": sum(1 for p in pekerjaan if p.source_type == Pekerjaan.SOURCE_CUSTOM),
        "side_active": "template_ahsp",
    }
    return render(request, "detail_project/template_ahsp.html", ctx)


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

def rincian_ahsp_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    pekerjaan = (
        Pekerjaan.objects
        .filter(project=project)
        .order_by('ordering_index', 'id')
    )
    context = {
        "project": project,
        "pekerjaan": pekerjaan,
        "side_active": "rincian_ahsp",
    }
    # Use UTF-8 safe template version to avoid decode errors
    return render(request, "detail_project/rincian_ahsp_utf8.html", context)

@login_required
@coerce_project_id
def rekap_rab_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    context = {
        "project": project,
        "side_active": "rekap_rab",
    }
    return render(request, "detail_project/rekap_rab.html", context)


@login_required
@coerce_project_id
def rekap_kebutuhan_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    ctx = {
        "project": project,
        # endpoint API dipanggil dari template via {% url %}, jadi cukup project.
    }
    return render(request, "detail_project/rekap_kebutuhan.html", ctx)

# --- NEW: Page Rincian RAB ---
@login_required
@coerce_project_id
def rincian_rab_view(request, project_id: int):
    """
    Page 'Rincian RAB' (read-only table  export).
    Data diambil via API: /api/project/<project_id>/rincian-rab/.
    """
    project = _project_or_404(project_id, request.user)
    ctx = {
        "project": project,
        "side_active": "rincian_rab",
    }
    return render(request, "detail_project/rincian_rab.html", ctx)
