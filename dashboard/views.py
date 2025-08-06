from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProjectForm, ProjectFilterForm, UploadProjectForm
from .models import Project
import openpyxl


@login_required
def dashboard_view(request):
    queryset = Project.objects.filter(owner=request.user, is_active=True)
    filter_form = ProjectFilterForm(request.GET)

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

    if request.method == 'POST':
        formset = ProjectFormSet(request.POST)
        saved_count = 0
        has_error = False

        for i, form in enumerate(formset.forms):
            if form.is_valid():
                instance = form.save(commit=False)
                instance.owner = request.user
                instance.save()
                saved_count += 1
            else:
                has_error = True
                print(f"\n🔴 Baris ke-{i+1} GAGAL disimpan:")
                for field, errors in form.errors.items():
                    raw_value = form.data.get(form.add_prefix(field), '[KOSONG]')
                    print(f"   • Field '{field}' → '{raw_value}'")
                    for err in errors:
                        print(f"     ❌ Error: {err}")

        if saved_count > 0:
            messages.success(request, f"{saved_count} proyek berhasil disimpan.")
        if has_error:
            messages.warning(request, "Beberapa baris tidak disimpan karena error. Silakan periksa kembali.")
        if not saved_count and not has_error:
            messages.info(request, "Tidak ada perubahan yang disimpan.")
    else:
        formset = ProjectFormSet(queryset=Project.objects.none())

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

# === Detail, Edit, Delete ===

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
            return redirect('dashboard')
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
        return redirect('dashboard')
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
            return redirect('dashboard')
        else:
            messages.error(request, 'Gagal menyimpan duplikat. Silakan periksa kembali.')
    else:
        # Pre-fill dengan data original, tambahkan "(Copy)" pada nama
        initial_data = original.__dict__.copy()
        initial_data.pop('id', None)
        initial_data['nama'] = f"{original.nama} (Copy)"
        form = ProjectForm(initial=initial_data)

    return render(request, 'dashboard/project_confirm_duplicate.html', {
        'form': form,
        'original_project': original
    })

@login_required
def project_upload_view(request):
    context = {'upload_form': UploadProjectForm()}
    preview_data = []
    error_rows = []

    if request.method == 'POST':
        form = UploadProjectForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            wb = openpyxl.load_workbook(file)
            ws = wb.active

            headers = [cell.value for cell in ws[1]]

            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                row_data = dict(zip(headers, row))
                form_data = ProjectForm(data=row_data)
                if form_data.is_valid():
                    project = form_data.save(commit=False)
                    project.owner = request.user
                    preview_data.append(project)
                else:
                    error_rows.append((i, form_data.errors, row_data))

            if preview_data:
                for project in preview_data:
                    project.save()  # Gunakan save() untuk trigger auto indexing
                messages.success(request, f"{len(preview_data)} proyek berhasil diupload.")
                return redirect('dashboard')
            else:
                messages.error(request, "Tidak ada proyek yang valid untuk diupload.")

        context['upload_form'] = form

    context['error_rows'] = error_rows
    return render(request, 'dashboard/project_upload.html', context)


