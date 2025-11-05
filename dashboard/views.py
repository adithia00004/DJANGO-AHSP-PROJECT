from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ProjectForm, ProjectFilterForm, UploadProjectForm
from .models import Project

import openpyxl


def _get_safe_next(request, default_name='dashboard:dashboard'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    # fallback ke dashboard
    from django.urls import reverse
    return reverse(default_name)

@login_required
def dashboard_view(request):
    queryset = Project.objects.filter(owner=request.user, is_active=True)
    filter_form = ProjectFilterForm(request.GET)

    # Info ramah saat navigasi tanpa project terpilih
    if request.GET.get("need_project") == "1":
        messages.info(request, "Silakan pilih project dari tabel, lalu buka halaman Detail Project.")


    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        sort_by = filter_form.cleaned_data.get('sort_by') or '-updated_at'
        if search:
            queryset = queryset.filter(
                Q(nama__icontains=search) |
                Q(deskripsi__icontains=search) |
                Q(sumber_dana__icontains=search) |
                Q(lokasi_project__icontains=search) |
                Q(nama_client__icontains=search) |
                Q(kategori__icontains=search)
            )
        queryset = queryset.order_by(sort_by)

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

    context = {
        'projects': paginated_projects,
        'filter_form': filter_form,
        'formset': formset,
        'total_projects': queryset.count(),
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
