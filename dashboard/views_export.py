from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Value, DecimalField, Q
from django.db.models.functions import Coalesce
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from datetime import date

from .models import Project
from .forms import ProjectFilterForm
from detail_project.services import compute_rekap_for_project
from detail_project.models import PekerjaanProgressWeekly

@login_required
def export_dashboard_xlsx(request):
    """
    Export list of projects to Excel, respecting current filters.
    Includes full columns and weighted progress calculation.
    """
    # 1. Base QuerySet
    queryset = Project.objects.filter(owner=request.user)

    # 2. Apply Filters (Replicating dashboard_view logic)
    filter_form = ProjectFilterForm(request.GET or None)

    if request.GET and filter_form.is_valid():
        search_query = filter_form.cleaned_data.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(nama__icontains=search_query) |
                Q(lokasi_project__icontains=search_query) |
                Q(tahun_project__icontains=search_query) |
                Q(nama_client__icontains=search_query)
            )

        tahun = filter_form.cleaned_data.get('tahun')
        if tahun:
            queryset = queryset.filter(tahun_project=tahun)

        # Date range filters
        tanggal_from = filter_form.cleaned_data.get('tanggal_from')
        tanggal_to = filter_form.cleaned_data.get('tanggal_to')
        
        if tanggal_from or tanggal_to:
            if tanggal_from and tanggal_to:
                queryset = queryset.filter(
                    tanggal_mulai__lte=tanggal_to,
                    tanggal_selesai__gte=tanggal_from
                )
            elif tanggal_from:
                queryset = queryset.filter(tanggal_selesai__gte=tanggal_from)
            elif tanggal_to:
                queryset = queryset.filter(tanggal_mulai__lte=tanggal_to)

        is_active_filter = filter_form.cleaned_data.get('is_active')
        if is_active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'false':
            queryset = queryset.filter(is_active=False)
        elif 'is_active' not in request.GET:
            queryset = queryset.filter(is_active=True)

        sort_by = filter_form.cleaned_data.get('sort_by') or '-updated_at'
        queryset = queryset.order_by(sort_by)
    else:
        # Default view logic
        if 'is_active' not in request.GET:
             queryset = queryset.filter(is_active=True)
        queryset = queryset.order_by('-updated_at')

    # 3. Calculate Progress for all filtered projects (Batch optimization)
    # We do this logic manually to match dashboard_view's new weighted logic
    
    # Pre-fetch actual sums
    project_ids = list(queryset.values_list('id', flat=True))
    pekerjaan_actual_aggregates = {}
    
    weekly_aggregates = PekerjaanProgressWeekly.objects.filter(
        project_id__in=project_ids
    ).values('pekerjaan_id').annotate(
        total_actual=Coalesce(
            Sum('actual_proportion'),
            Value(Decimal('0')),
            output_field=DecimalField()
        )
    )
    
    for agg in weekly_aggregates:
        pekerjaan_actual_aggregates[agg['pekerjaan_id']] = float(agg['total_actual'])

    # 4. Prepare Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Daftar Project"

    # Headers
    headers = [
        "Index", "Nama Project", "Tahun", "Sumber Dana", "Lokasi", 
        "Nilai Anggaran (Rp)", "Progress (%)", "Status",
        # Client Info
        "Nama Client", "Jabatan Client", "Instansi Client",
        # Kontraktor Info
        "Nama Kontraktor", "Instansi Kontraktor",
        # Konsultan Info
        "Konsultan Perencana", "Instansi Perencana",
        "Konsultan Pengawas", "Instansi Pengawas",
        # Dates
        "Tanggal Mulai", "Tanggal Selesai", "Durasi (Hari)",
        "Ket 1", "Ket 2", "Kategori"
    ]
    
    # Styling headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = openpyxl.styles.PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Rows
    for row_num, project in enumerate(queryset, 2):
        # Calculate Weighted Progress per project
        weighted_progress = 0.0
        try:
            from detail_project.models import Pekerjaan as PekerjaanModel
            
            rekap_rows = compute_rekap_for_project(project)
            rekap_lookup = {row['pekerjaan_id']: row for row in rekap_rows}
            
            # Get all Pekerjaan for this project to access budgeted_cost
            pekerjaan_qs = PekerjaanModel.objects.filter(project=project)
            
            total_project_cost = Decimal('0.00')
            total_realization_cost = Decimal('0.00')
            
            for pkj in pekerjaan_qs:
                pekerjaan_id = pkj.id
                
                # Get rekap fallback
                fallback_row = rekap_lookup.get(pekerjaan_id)
                fallback_total = Decimal(str(fallback_row.get('total', 0))) if fallback_row else Decimal('0')
                
                # Prioritize budgeted_cost (like S-Curve logic), fallback to rekap total
                if pkj.budgeted_cost and pkj.budgeted_cost > 0:
                    item_cost = pkj.budgeted_cost
                else:
                    item_cost = fallback_total
                
                if item_cost > 0:
                    total_project_cost += item_cost
                    actual_percent = pekerjaan_actual_aggregates.get(pekerjaan_id, 0.0)
                    actual_percent = min(actual_percent, 100.0)
                    realization = item_cost * Decimal(str(actual_percent / 100.0))
                    total_realization_cost += realization
            
            if total_project_cost > 0:
                weighted_progress = float((total_realization_cost / total_project_cost) * 100)
            else:
                # Fallback unweighted
                pekerjaan_ids = list(pekerjaan_qs.values_list('id', flat=True))
                if pekerjaan_ids:
                    sum_progress = sum(pekerjaan_actual_aggregates.get(pid, 0.0) for pid in pekerjaan_ids)
                    weighted_progress = sum_progress / len(pekerjaan_ids)
                else:
                    weighted_progress = 0.0
        except Exception:
            weighted_progress = 0.0

        # Status text
        status_text = "Aktif" if project.is_active else "Non-Aktif"

        # Populate row
        row_data = [
            project.index_project,
            project.nama,
            project.tahun_project,
            project.sumber_dana,
            project.lokasi_project,
            float(project.anggaran_owner), # Nilai Anggaran
            weighted_progress,             # Progress
            status_text,
            # Client
            project.nama_client,
            project.jabatan_client,
            project.instansi_client,
            # Kontraktor
            project.nama_kontraktor,
            project.instansi_kontraktor,
            # Konsultan
            project.nama_konsultan_perencana,
            project.instansi_konsultan_perencana,
            project.nama_konsultan_pengawas,
            project.instansi_konsultan_pengawas,
            # Dates
            project.tanggal_mulai,
            project.tanggal_selesai,
            project.durasi_hari,
            project.ket_project1,
            project.ket_project2,
            project.kategori
        ]
        
        for col_num, cell_value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num, value=cell_value)
            
            # Formatting
            if col_num == 6: # Anggaran
                cell.number_format = '#,##0.00'
            elif col_num == 7: # Progress
                cell.number_format = '0.00'
            elif isinstance(cell_value, date):
                cell.number_format = 'DD/MM/YYYY'

    # Auto-adjust column width (simple adj)
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter # Get the column name
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = min(adjusted_width, 50) # Cap at 50

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename=Project_Export_{date.today().isoformat()}.xlsx'
    
    wb.save(response)
    return response

# === Aliases & Stubs for Compatibility with dashboard/urls.py ===

# 1. Excel Export (Upgraded to new logic)
export_excel = export_dashboard_xlsx

# 2. CSV Export (Stub - Deprecated in favor of Excel)
def export_csv(request):
    return HttpResponse("Fitur Export CSV telah digantikan oleh Export Excel (Full Columns). Silakan gunakan tombol Export Excel.", content_type="text/plain")

# 3. Project PDF Export (Stub - Placeholder)
def export_project_pdf(request, pk):
    return HttpResponse("Fitur Export PDF Project sedang dalam maintenance. Silakan gunakan Export PDF di halaman Detail Project.", content_type="text/plain")
