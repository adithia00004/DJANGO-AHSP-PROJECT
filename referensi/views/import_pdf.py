"""
Views for PDF Import functionality.
Phase 2 & 3: Upload UI and Verification UI.
"""

import os
import uuid
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from referensi.models_staging import AHSPImportStaging


def is_admin(user):
    """Check if user is admin/staff."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def upload_pdf(request):
    """
    Phase 2: Upload PDF View.
    GET: Shows upload form.
    POST: Saves file and triggers Celery task.
    """
    if request.method == 'POST':
        uploaded_file = request.FILES.get('pdf_file')
        
        if not uploaded_file:
            messages.error(request, "Tidak ada file yang diupload.")
            return redirect('referensi:import_pdf_convert')
        
        # Validate file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            messages.error(request, "File harus berformat PDF.")
            return redirect('referensi:import_pdf_convert')
        
        # Save file to temp location
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Unique filename to avoid collisions
        unique_name = f"{uuid.uuid4().hex}_{uploaded_file.name}"
        file_path = os.path.join(temp_dir, unique_name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Run synchronously for local development (bypass Celery/Redis)
        # For production, use: process_ahsp_pdf_task.delay(...)
        try:
            from referensi.tasks import process_ahsp_pdf_task
            result = process_ahsp_pdf_task(
                file_path=file_path,
                user_id=request.user.id,
                file_name=uploaded_file.name
            )
            
            if result.get('status') == 'success':
                messages.success(
                    request,
                    f"File '{uploaded_file.name}' berhasil diproses! "
                    f"{result.get('count', 0)} item ditemukan. Silakan cek halaman Verifikasi."
                )
            else:
                messages.error(
                    request,
                    f"Gagal memproses file: {result.get('message', 'Unknown error')}"
                )
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        
        return redirect('referensi:import_pdf_verification')
    
    # GET: Show upload form
    return render(request, 'referensi/import_upload.html')


@login_required
@user_passes_test(is_admin)
def verification(request):
    """
    Phase 3: Verification View.
    Shows all staging data for the current user.
    """
    # Get staging data for current user
    staging_data = AHSPImportStaging.objects.filter(user=request.user).order_by('-created_at', 'id')
    
    # Group by file_name for easier review
    files = staging_data.values_list('file_name', flat=True).distinct()
    
    context = {
        'staging_data': staging_data,
        'files': list(files),
        'total_items': staging_data.filter(segment_type__in=['A', 'B', 'C']).count(),
        'total_headings': staging_data.filter(segment_type='HEADING').count(),
    }
    
    return render(request, 'referensi/import_verification.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def clear_staging(request):
    """
    Clears all staging data for current user.
    """
    deleted_count, _ = AHSPImportStaging.objects.filter(user=request.user).delete()
    messages.info(request, f"Semua data staging ({deleted_count} item) telah dihapus.")
    return redirect('referensi:import_pdf_verification')


@login_required
@user_passes_test(is_admin)
@require_POST
def commit_to_database(request):
    """
    Phase 4: Commits validated staging data to main database.
    Moves data from AHSPImportStaging to AHSPReferensi + RincianReferensi.
    """
    from referensi.models import AHSPReferensi, RincianReferensi
    
    staging_items = AHSPImportStaging.objects.filter(
        user=request.user,
        is_valid=True,
        segment_type__in=['A', 'B', 'C']  # Only items, not headings
    )
    
    if not staging_items.exists():
        messages.warning(request, "Tidak ada data valid untuk di-commit.")
        return redirect('referensi:import_pdf_verification')
    
    # Group by parent_ahsp_code
    parent_codes = staging_items.values_list('parent_ahsp_code', flat=True).distinct()
    
    created_ahsp = 0
    created_rincian = 0
    
    for parent_code in parent_codes:
        if not parent_code:
            continue
            
        # Get or create AHSP Referensi
        parent_heading = AHSPImportStaging.objects.filter(
            user=request.user,
            kode_item=parent_code,
            segment_type='HEADING'
        ).first()
        
        ahsp_obj, created = AHSPReferensi.objects.get_or_create(
            kode_ahsp=parent_code,
            sumber="PDF Import",
            defaults={
                'nama_ahsp': parent_heading.uraian_item if parent_heading else parent_code,
            }
        )
        if created:
            created_ahsp += 1
        
        # Get items under this parent
        items = staging_items.filter(parent_ahsp_code=parent_code)
        
        for item in items:
            # Map segment to kategori
            kategori_map = {'A': 'TK', 'B': 'BHN', 'C': 'ALT'}
            kategori = kategori_map.get(item.segment_type, 'LAIN')
            
            RincianReferensi.objects.update_or_create(
                ahsp=ahsp_obj,
                kategori=kategori,
                kode_item=item.kode_item,
                uraian_item=item.uraian_item,
                satuan_item=item.satuan_item or '-',
                defaults={
                    'koefisien': item.koefisien,
                }
            )
            created_rincian += 1
    
    # Clear staging after successful commit
    staging_items.delete()
    AHSPImportStaging.objects.filter(user=request.user, segment_type='HEADING').delete()
    
    messages.success(
        request,
        f"Import berhasil! {created_ahsp} AHSP baru, {created_rincian} rincian item ditambahkan."
    )
    return redirect('referensi:admin_portal')
