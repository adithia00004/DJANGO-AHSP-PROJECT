# ================================
# detail_project/views.py (web views)
# ================================
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect

from .models import Pekerjaan, ProjectChangeStatus, VolumePekerjaan


def staff_only_page(view_func):
    """
    U14: utility/maintenance pages (Orphan Cleanup, Audit Trail) are intended
    for the admin role only. Non-staff owners are redirected to the project's
    List Pekerjaan with a notice. Mirrors the in-body guard pattern used by
    referensi (has_referensi_portal_access).
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not (user.is_staff or user.is_superuser):
            messages.warning(request, "Halaman ini hanya tersedia untuk admin.")
            project_id = kwargs.get('project_id') or kwargs.get('pid')
            if project_id:
                return redirect('detail_project:list_pekerjaan', project_id=project_id)
            return redirect('dashboard:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _ensure_change_status(project):
    change_status, _ = ProjectChangeStatus.objects.get_or_create(project=project)
    return change_status


def _get_sync_initial_timestamps(project):
    """
    Compute actual DB timestamps for sync LED initial values.
    Prevents false-positive change detection caused by using page-render time.
    """
    from django.db.models import Max
    from .models import PekerjaanProgressWeekly, PekerjaanTahapan, TahapPelaksanaan

    pekerjaan_latest = (
        Pekerjaan.objects
        .filter(project=project)
        .order_by('-updated_at')
        .values_list('updated_at', flat=True)
        .first()
    )
    volume_latest = (
        VolumePekerjaan.objects
        .filter(pekerjaan__project=project)
        .order_by('-updated_at')
        .values_list('updated_at', flat=True)
        .first()
    )
    jadwal_latest = max(
        filter(
            None,
            [
                TahapPelaksanaan.objects.filter(project=project).aggregate(last=Max("updated_at"))["last"],
                PekerjaanTahapan.objects.filter(tahapan__project=project).aggregate(last=Max("updated_at"))["last"],
                PekerjaanProgressWeekly.objects.filter(project=project).aggregate(last=Max("updated_at"))["last"],
            ],
        ),
        default=None,
    )
    return {
        "initial_pekerjaan_ts": pekerjaan_latest,
        "initial_volume_ts": volume_latest,
        "initial_jadwal_ts": jadwal_latest,
    }


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
    # PERF: bootstrap volume + formula state ke HTML supaya prefill() tidak perlu
    # round-trip AJAX (kolom volume/formula kosong → terisi) saat halaman dibuka.
    from .views_api import build_volume_list_payload, build_volume_formula_state_payload
    bootstrap_volume = {
        "volume_list": build_volume_list_payload(project),
        "formula_state": build_volume_formula_state_payload(project),
    }

    context = {
        "project": project,
        "pekerjaan": pekerjaan,
        "bootstrap_volume": bootstrap_volume,
        "side_active": "volume_pekerjaan",
        "opaque_id_enabled": getattr(settings, "OPAQUE_ID_ENABLED", True),
        "formula_label_only_ui_enabled": getattr(settings, "FORMULA_LABEL_ONLY_UI_ENABLED", False),
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
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

    # PERF: bootstrap detail pekerjaan pertama langsung ke HTML supaya halaman
    # Template tidak perlu round-trip AJAX (dan flash "Memuat data...") saat dibuka.
    # JS akan men-seed cache dari sini; pekerjaan lain tetap lazy-fetch saat diklik.
    first_pkj = pekerjaan[0] if pekerjaan else None
    bootstrap_detail = None
    if first_pkj is not None:
        from .views_api import build_detail_ahsp_payload
        bootstrap_detail = build_detail_ahsp_payload(project, first_pkj)

    ctx = {
        "project": project,
        "pekerjaan": pekerjaan,  # ← sidebar akan melisting semuanya
        "bootstrap_detail": bootstrap_detail,
        # kalau template Anda butuh stats (opsional):
        "count_ref": sum(1 for p in pekerjaan if p.source_type == Pekerjaan.SOURCE_REF),
        "count_mod": sum(1 for p in pekerjaan if p.source_type == Pekerjaan.SOURCE_REF_MOD),
        "count_custom": sum(1 for p in pekerjaan if p.source_type == Pekerjaan.SOURCE_CUSTOM),
        "side_active": "template_ahsp",
        "opaque_id_enabled": getattr(settings, "OPAQUE_ID_ENABLED", True),
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
    }
    return render(request, "detail_project/template_ahsp.html", ctx)


@login_required
@coerce_project_id
def harga_items_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    # PERF: bootstrap daftar harga ke HTML supaya fetchList() tidak round-trip
    # ("Memuat data…") saat halaman dibuka. canon=True menyamai EP_LIST?canon=1.
    from .views_api import build_harga_items_payload
    context = {
        "project": project,
        "bootstrap_harga": build_harga_items_payload(project, canon=True),
        "side_active": "harga_items",
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
    }
    return render(request, "detail_project/harga_items.html", context)


@login_required
@coerce_project_id
@staff_only_page
def orphan_cleanup_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    context = {
        "project": project,
        "side_active": "orphan_cleanup",
    }
    return render(request, "detail_project/orphan_cleanup.html", context)


@login_required
@coerce_project_id
@staff_only_page
def audit_trail_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    pekerjaan_options = (
        Pekerjaan.objects
        .filter(project=project)
        .order_by("ordering_index", "id")
        .values("id", "snapshot_kode", "snapshot_uraian")
    )
    context = {
        "project": project,
        "pekerjaan_options": pekerjaan_options,
        "side_active": "audit_trail",
    }
    return render(request, "detail_project/audit_trail.html", context)


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
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
    }
    return render(request, "detail_project/rincian_ahsp.html", context)

@login_required
@coerce_project_id
def rekap_rab_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    context = {
        "project": project,
        "side_active": "rekap_rab",
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
    }
    return render(request, "detail_project/rekap_rab.html", context)


@login_required
@coerce_project_id
def rekap_kebutuhan_view(request, project_id: int):
    project = _project_or_404(project_id, request.user)
    ctx = {
        "project": project,
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
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
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
    }
    return render(request, "detail_project/rincian_rab.html", ctx)


@login_required
@coerce_project_id
def export_test_view(request, project_id: int):
    """
    Export System Test Page - Phase 4
    Interactive test page for verifying export functionality
    """
    project = _project_or_404(project_id, request.user)

    context = {
        "project": project,
        "side_active": "export_test",
        "DEBUG": settings.DEBUG,
    }

    return render(request, "detail_project/export_test.html", context)


@login_required
@coerce_project_id
def jadwal_pekerjaan_view(request, project_id: int):
    """
    Jadwal Pekerjaan - Excel-like Grid View untuk penjadwalan dengan Gantt & Kurva S.
    Professional project scheduling interface dengan time-based grid.
    Data di-load via JavaScript dari API.
    """
    project = _project_or_404(project_id, request.user)
    
    # Calculate total weeks from PekerjaanProgressWeekly (has week_number field)
    from .models import PekerjaanProgressWeekly
    from django.db.models import Max
    
    progress_max_week = PekerjaanProgressWeekly.objects.filter(project=project).aggregate(
        max_week=Max('week_number')
    )['max_week'] or 0
    
    # Alternative: Calculate from project dates if no progress data exists
    if progress_max_week == 0:
        # Fallback: calculate from project start/end dates if available
        start_date = getattr(project, 'tanggal_mulai', None)
        end_date = getattr(project, 'tanggal_selesai', None)
        if start_date and end_date:
            days_diff = (end_date - start_date).days
            progress_max_week = max(1, (days_diff + 6) // 7)  # Round up to weeks
    
    total_weeks = max(progress_max_week, 12)  # At least 12 weeks
    total_months = max((total_weeks + 3) // 4, 3)  # At least 3 months

    context = {
        "project": project,
        "side_active": "jadwal_pekerjaan",  # untuk sidebar highlighting
        "DEBUG": getattr(settings, "DEBUG", False),
        "use_vite_dev_server": getattr(settings, "USE_VITE_DEV_SERVER", False),
        # Export modal period selection
        "total_weeks": total_weeks,
        "total_months": total_months,
        "change_status": _ensure_change_status(project),
        **_get_sync_initial_timestamps(project),
    }

    # MODERN TEMPLATE (2025-11-19): Clean, no conditional legacy code
    # Rollback: change to kelola_tahapan_grid_LEGACY.html if needed
    return render(request, "detail_project/kelola_tahapan_grid_modern.html", context)
