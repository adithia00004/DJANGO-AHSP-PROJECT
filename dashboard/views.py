from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import date, timedelta
import json
import decimal

from .forms import ProjectForm, ProjectFilterForm, UploadProjectForm
from .models import Project

import openpyxl


# Custom JSON Encoder for Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def _get_safe_next(request, default_name='dashboard:dashboard'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    # fallback ke dashboard
    from django.urls import reverse
    return reverse(default_name)

@login_required
def dashboard_view(request):
    # Start with all projects owned by user
    queryset = Project.objects.filter(owner=request.user)

    # Initialize filter form with user for dynamic choices
    filter_form = ProjectFilterForm(request.GET, user=request.user)

    # Info ramah saat navigasi tanpa project terpilih
    if request.GET.get("need_project") == "1":
        messages.info(request, "Silakan pilih project dari tabel, lalu buka halaman Detail Project.")

    # === FASE 2.2: Advanced Filtering ===
    if filter_form.is_valid():
        # Basic search
        search = filter_form.cleaned_data.get('search')
        if search:
            queryset = queryset.filter(
                Q(nama__icontains=search) |
                Q(deskripsi__icontains=search) |
                Q(sumber_dana__icontains=search) |
                Q(lokasi_project__icontains=search) |
                Q(nama_client__icontains=search) |
                Q(kategori__icontains=search)
            )

        # Filter by year
        tahun = filter_form.cleaned_data.get('tahun_project')
        if tahun:
            queryset = queryset.filter(tahun_project=tahun)

        # Filter by sumber dana
        sumber = filter_form.cleaned_data.get('sumber_dana')
        if sumber:
            queryset = queryset.filter(sumber_dana=sumber)

        # Filter by timeline status
        status = filter_form.cleaned_data.get('status_timeline')
        if status:
            today = date.today()
            if status == 'belum_mulai':
                queryset = queryset.filter(tanggal_mulai__gt=today)
            elif status == 'berjalan':
                queryset = queryset.filter(
                    tanggal_mulai__lte=today,
                    tanggal_selesai__gte=today
                )
            elif status == 'terlambat':
                queryset = queryset.filter(tanggal_selesai__lt=today)
            elif status == 'selesai':
                # Projects that finished on time (ended in the past, but not marked overdue)
                queryset = queryset.filter(
                    tanggal_selesai__lt=today,
                    tanggal_mulai__lte=today
                )

        # Filter by budget range
        anggaran_min = filter_form.cleaned_data.get('anggaran_min')
        anggaran_max = filter_form.cleaned_data.get('anggaran_max')
        if anggaran_min is not None:
            queryset = queryset.filter(anggaran_owner__gte=anggaran_min)
        if anggaran_max is not None:
            queryset = queryset.filter(anggaran_owner__lte=anggaran_max)

        # Filter by date range
        tanggal_from = filter_form.cleaned_data.get('tanggal_mulai_from')
        tanggal_to = filter_form.cleaned_data.get('tanggal_mulai_to')
        if tanggal_from:
            queryset = queryset.filter(tanggal_mulai__gte=tanggal_from)
        if tanggal_to:
            queryset = queryset.filter(tanggal_mulai__lte=tanggal_to)

        # Filter by active status
        is_active_filter = filter_form.cleaned_data.get('is_active')
        if is_active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'false':
            queryset = queryset.filter(is_active=False)
        elif 'is_active' not in request.GET:
            # Default: show only active projects when no filter is explicitly set
            queryset = queryset.filter(is_active=True)
        # else: if is_active='' (user selected "Semua"), show all (don't filter)

        # Sorting
        sort_by = filter_form.cleaned_data.get('sort_by') or '-updated_at'
        queryset = queryset.order_by(sort_by)
    else:
        # Default: only show active projects if no filter applied
        queryset = queryset.filter(is_active=True).order_by('-updated_at')

    ProjectFormSet = modelformset_factory(
        Project,
        form=ProjectForm,
        extra=1,
        can_delete=False
    )

    # Longgarkan: proses POST tanpa bergantung pada name tombol
    if request.method == 'POST':
        formset = ProjectFormSet(
            request.POST,
            queryset=Project.objects.none(),
            prefix='form',  # konsisten dengan HTML/JS
        )

        if formset.is_valid():
            saved_count = 0
            with transaction.atomic():
                for form in formset:
                    if not form.has_changed():
                        continue
                    obj = form.save(commit=False)
                    obj.owner = request.user
                    obj.is_active = True
                    obj.save()
                    saved_count += 1

            if saved_count:
                messages.success(request, f"{saved_count} proyek berhasil disimpan.")
            else:
                messages.info(request, "Tidak ada baris yang disimpan (semua kosong).")

            return redirect('dashboard:dashboard')

        else:
            nfe = formset.non_form_errors()
            if nfe:
                messages.error(request, "Form gagal diproses: " + "; ".join([str(e) for e in nfe]))
            for idx, form in enumerate(formset.forms):
                if form.errors:
                    for field, errs in form.errors.items():
                        for err in errs:
                            messages.error(request, f"Baris {idx+1} – {field}: {err}")

    else:
        formset = ProjectFormSet(
            queryset=Project.objects.none(),
            prefix='form',
        )

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    paginated_projects = paginator.get_page(page_number)

    # === FASE 2.1: Analytics & Statistics ===
    all_active_projects = Project.objects.filter(owner=request.user, is_active=True)
    current_year = timezone.now().year
    today = date.today()

    # Summary Statistics
    total_projects = all_active_projects.count()
    total_anggaran = all_active_projects.aggregate(total=Sum('anggaran_owner'))['total'] or 0
    projects_this_year = all_active_projects.filter(tahun_project=current_year).count()

    # Active projects (with deadline in next 30 days or currently running)
    deadline_threshold = today + timedelta(days=30)
    active_projects_count = all_active_projects.filter(
        tanggal_mulai__lte=today,
        tanggal_selesai__gte=today
    ).count()

    # Projects by Year (for chart)
    projects_by_year = all_active_projects.values('tahun_project').annotate(
        count=Count('id')
    ).order_by('tahun_project')

    # Projects by Sumber Dana (for chart)
    projects_by_sumber = all_active_projects.values('sumber_dana').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10

    # Budget by Year (for chart)
    budget_by_year = all_active_projects.values('tahun_project').annotate(
        total_budget=Sum('anggaran_owner')
    ).order_by('tahun_project')

    # Recent Activity
    recent_created = all_active_projects.order_by('-created_at')[:5]
    recent_updated = all_active_projects.order_by('-updated_at')[:5]

    # Projects with upcoming deadlines (next 7 days)
    upcoming_deadline_threshold = today + timedelta(days=7)
    upcoming_deadlines = all_active_projects.filter(
        tanggal_selesai__gte=today,
        tanggal_selesai__lte=upcoming_deadline_threshold
    ).order_by('tanggal_selesai')[:5]

    # Overdue projects
    overdue_projects = all_active_projects.filter(
        tanggal_selesai__lt=today
    ).order_by('tanggal_selesai')[:5]

    context = {
        'projects': paginated_projects,
        'filter_form': filter_form,
        'formset': formset,
        'total_projects': queryset.count(),
        # Analytics data
        'analytics': {
            'total_projects': total_projects,
            'total_anggaran': total_anggaran,
            'projects_this_year': projects_this_year,
            'active_projects_count': active_projects_count,
            'upcoming_deadlines': upcoming_deadlines,
            'overdue_projects': overdue_projects,
        },
        # Chart data (JSON serialized for JavaScript)
        'chart_data': {
            'projects_by_year': mark_safe(json.dumps(list(projects_by_year), cls=DecimalEncoder)),
            'projects_by_sumber': mark_safe(json.dumps(list(projects_by_sumber), cls=DecimalEncoder)),
            'budget_by_year': mark_safe(json.dumps(list(budget_by_year), cls=DecimalEncoder)),
        },
        # Recent activity
        'recent_created': recent_created,
        'recent_updated': recent_updated,
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user, is_active=True)
    return render(request, 'dashboard/project_detail.html', {'project': project})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user, is_active=True)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project berhasil diperbarui.')
            return redirect(_get_safe_next(request))
    else:
        form = ProjectForm(instance=project)
    return render(request, 'dashboard/project_form.html', {
        'form': form,
        'title': 'Edit Project',
        'project': project,
    })


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user, is_active=True)
    if request.method == 'POST':
        project.is_active = False  # Soft delete
        project.save()
        messages.success(request, 'Project berhasil dihapus.')
        return redirect(_get_safe_next(request))
    return render(request, 'dashboard/project_confirm_delete.html', {'project': project})


@login_required
def project_duplicate(request, pk):
    original = get_object_or_404(Project, pk=pk, owner=request.user, is_active=True)

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            duplicated = form.save(commit=False)
            duplicated.pk = None
            duplicated.owner = request.user
            duplicated.save()
            messages.success(request, 'Proyek berhasil diduplikasi dan disimpan.')
            return redirect(_get_safe_next(request))
        else:
            messages.error(request, 'Gagal menyimpan duplikat. Silakan periksa kembali.')
    else:
        initial_data = {
            field.name: getattr(original, field.name)
            for field in original._meta.fields
            if field.name != 'id'
        }
        initial_data['nama'] = f"{original.nama} (Copy)"
        form = ProjectForm(initial=initial_data)

    return render(request, 'dashboard/project_confirm_duplicate.html', {
        'form': form,
        'original_project': original
    })


@login_required
def project_upload_view(request):
    context = {'upload_form': UploadProjectForm()}
    error_rows = []
    to_create = []

    if request.method == 'POST':
        form = UploadProjectForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file']
                wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
                ws = wb.active
                # Batasi ukuran untuk mencegah beban berlebih
                MAX_ROWS = 2000  # data saja (tanpa header)
                if (ws.max_row - 1) > MAX_ROWS:
                    messages.error(request, f"Baris data melebihi batas {MAX_ROWS}.")
                    context["upload_form"] = form
                    return render(request, "dashboard/project_upload.html", context)

                raw_headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
                lower_headers = [h.lower() for h in raw_headers]

                expected = [
                    "nama","tahun_project","sumber_dana","lokasi_project","nama_client","anggaran_owner",
                    "tanggal_mulai","tanggal_selesai","durasi_hari",
                    "ket_project1","ket_project2","jabatan_client","instansi_client",
                    "nama_kontraktor","instansi_kontraktor",
                    "nama_konsultan_perencana","instansi_konsultan_perencana",
                    "nama_konsultan_pengawas","instansi_konsultan_pengawas",
                    "deskripsi","kategori",
                ]

                missing = [h for h in expected if h not in lower_headers]
                if missing:
                    messages.error(request, "Header Excel tidak sesuai. Kolom belum ada: " + ", ".join(missing))
                    context["upload_form"] = form
                    return render(request, "dashboard/project_upload.html", context)

                idx = {h.lower(): i for i, h in enumerate(raw_headers)}

                for rownum, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                  data = {h: (row[idx[h]] if idx.get(h) is not None and idx[h] < len(row) else None) for h in expected}
                  if not any([data.get("nama"), data.get("lokasi_project"), data.get("sumber_dana")]):
                      continue

                  f = ProjectForm(data=data)
                  if f.is_valid():
                      obj = f.save(commit=False)
                      obj.owner = request.user
                      to_create.append(obj)
                  else:
                      error_rows.append((rownum, dict(f.errors)))
                
                if to_create:
                    with transaction.atomic():
                        for obj in to_create:
                            obj.save()
                    messages.success(request, f"{len(to_create)} proyek berhasil diupload.")
                    return redirect('dashboard:dashboard')
                else:
                    if error_rows:
                        messages.warning(request, "Tidak ada baris valid yang bisa diimport. Silakan perbaiki error di bawah.")
                    else:
                        messages.info(request, "File tidak berisi data yang dapat diimport.")

            except Exception as e:
                messages.error(request, f"Gagal membaca file: {e}")

        context['upload_form'] = form

    context['error_rows'] = error_rows
    return render(request, 'dashboard/project_upload.html', context)
