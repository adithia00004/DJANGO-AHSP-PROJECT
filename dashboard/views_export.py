"""
Export views for dashboard app.

Provides export functionality in multiple formats:
- Excel (.xlsx)
- CSV (.csv)
- PDF (project detail report)
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import csv
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Project
from .forms import ProjectFilterForm


def apply_filters(queryset, request):
    """
    Apply the same filters as dashboard view.
    Reusable function for export views.
    """
    filter_form = ProjectFilterForm(request.GET, user=request.user)

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

        # Sorting
        sort_by = filter_form.cleaned_data.get('sort_by') or '-updated_at'
        queryset = queryset.order_by(sort_by)
    else:
        # Default: only active projects
        queryset = queryset.filter(is_active=True).order_by('-updated_at')

    return queryset


@login_required
def export_excel(request):
    """
    Export filtered projects to Excel (.xlsx) format.
    """
    # Get filtered queryset
    queryset = Project.objects.filter(owner=request.user)
    queryset = apply_filters(queryset, request)

    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Projects"

    # Define headers
    headers = [
        'No',
        'Index Project',
        'Nama Project',
        'Tahun',
        'Sumber Dana',
        'Lokasi',
        'Client',
        'Anggaran (Rp)',
        'Tanggal Mulai',
        'Tanggal Selesai',
        'Durasi (hari)',
        'Status',
        'Kategori',
        'Created',
    ]

    # Style for header
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # Write data
    today = date.today()
    for row_num, project in enumerate(queryset, 2):
        # Determine status
        if not project.is_active:
            status = "Archived"
        elif not project.tanggal_mulai or not project.tanggal_selesai:
            status = "No Timeline"
        elif project.tanggal_selesai < today:
            status = "Terlambat"
        elif project.tanggal_mulai > today:
            status = "Belum Mulai"
        else:
            status = "Berjalan"

        row_data = [
            row_num - 1,  # No
            project.index_project or 'N/A',
            project.nama,
            project.tahun_project,
            project.sumber_dana,
            project.lokasi_project,
            project.nama_client,
            float(project.anggaran_owner) if project.anggaran_owner else 0,
            project.tanggal_mulai.strftime('%Y-%m-%d') if project.tanggal_mulai else '',
            project.tanggal_selesai.strftime('%Y-%m-%d') if project.tanggal_selesai else '',
            project.durasi_hari or '',
            status,
            project.kategori or '',
            project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else '',
        ]

        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = value
            cell.border = border

            # Align numbers to right
            if col_num in [1, 4, 8, 11]:  # No, Tahun, Anggaran, Durasi
                cell.alignment = Alignment(horizontal="right")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto-adjust column widths
    for col_num in range(1, len(headers) + 1):
        column_letter = get_column_letter(col_num)
        max_length = 0
        for cell in ws[column_letter]:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)  # Max 50
        ws.column_dimensions[column_letter].width = adjusted_width

    # Freeze first row
    ws.freeze_panes = "A2"

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="projects_export_{date.today()}.xlsx"'

    # Save workbook to response
    wb.save(response)

    return response


@login_required
def export_csv(request):
    """
    Export filtered projects to CSV format.
    """
    # Get filtered queryset
    queryset = Project.objects.filter(owner=request.user)
    queryset = apply_filters(queryset, request)

    # Create response
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="projects_export_{date.today()}.csv"'

    # Write UTF-8 BOM for Excel compatibility
    response.write('\ufeff')

    writer = csv.writer(response)

    # Write headers
    writer.writerow([
        'No',
        'Index Project',
        'Nama Project',
        'Tahun',
        'Sumber Dana',
        'Lokasi',
        'Client',
        'Anggaran (Rp)',
        'Tanggal Mulai',
        'Tanggal Selesai',
        'Durasi (hari)',
        'Status',
        'Kategori',
        'Created',
    ])

    # Write data
    today = date.today()
    for idx, project in enumerate(queryset, 1):
        # Determine status
        if not project.is_active:
            status = "Archived"
        elif not project.tanggal_mulai or not project.tanggal_selesai:
            status = "No Timeline"
        elif project.tanggal_selesai < today:
            status = "Terlambat"
        elif project.tanggal_mulai > today:
            status = "Belum Mulai"
        else:
            status = "Berjalan"

        writer.writerow([
            idx,
            project.index_project or 'N/A',
            project.nama,
            project.tahun_project,
            project.sumber_dana,
            project.lokasi_project,
            project.nama_client,
            float(project.anggaran_owner) if project.anggaran_owner else 0,
            project.tanggal_mulai.strftime('%Y-%m-%d') if project.tanggal_mulai else '',
            project.tanggal_selesai.strftime('%Y-%m-%d') if project.tanggal_selesai else '',
            project.durasi_hari or '',
            status,
            project.kategori or '',
            project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else '',
        ])

    return response


@login_required
def export_project_pdf(request, pk):
    """
    Export single project detail to PDF format.
    """
    project = get_object_or_404(Project, pk=pk, owner=request.user)

    # Create response
    response = HttpResponse(content_type='application/pdf')
    filename = f"project_{project.index_project or pk}_{date.today()}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Create PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=1  # Center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2c5f9e'),
        spaceAfter=10,
    )

    # Title
    title = Paragraph(f"<b>Project Detail Report</b>", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*cm))

    # Project Index & Name
    index_para = Paragraph(f"<b>{project.index_project or 'N/A'}</b>", styles['Heading2'])
    elements.append(index_para)
    name_para = Paragraph(project.nama, styles['Normal'])
    elements.append(name_para)
    elements.append(Spacer(1, 0.5*cm))

    # Basic Information Table
    basic_data = [
        ['Tahun Project', str(project.tahun_project)],
        ['Sumber Dana', project.sumber_dana],
        ['Lokasi', project.lokasi_project],
        ['Client', project.nama_client],
        ['Anggaran', f"Rp {project.anggaran_owner:,.0f}".replace(',', '.')],
    ]

    basic_table = Table(basic_data, colWidths=[5*cm, 11*cm])
    basic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e7f0f7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(Paragraph("<b>Informasi Dasar</b>", heading_style))
    elements.append(basic_table)
    elements.append(Spacer(1, 0.5*cm))

    # Timeline Information
    if project.tanggal_mulai or project.tanggal_selesai:
        timeline_data = [
            ['Tanggal Mulai', project.tanggal_mulai.strftime('%d %B %Y') if project.tanggal_mulai else '-'],
            ['Tanggal Selesai', project.tanggal_selesai.strftime('%d %B %Y') if project.tanggal_selesai else '-'],
            ['Durasi', f"{project.durasi_hari} hari" if project.durasi_hari else '-'],
        ]

        # Determine status
        today = date.today()
        if not project.is_active:
            status = "Archived"
            status_color = colors.grey
        elif not project.tanggal_mulai or not project.tanggal_selesai:
            status = "No Timeline"
            status_color = colors.grey
        elif project.tanggal_selesai < today:
            status = "Terlambat"
            status_color = colors.red
        elif project.tanggal_mulai > today:
            status = "Belum Mulai"
            status_color = colors.blue
        else:
            status = "Sedang Berjalan"
            status_color = colors.green

        timeline_data.append(['Status', status])

        timeline_table = Table(timeline_data, colWidths=[5*cm, 11*cm])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e7f0f7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (1, 3), (1, 3), status_color),  # Status color
            ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),  # Status bold
        ]))

        elements.append(Paragraph("<b>Timeline Pelaksanaan</b>", heading_style))
        elements.append(timeline_table)
        elements.append(Spacer(1, 0.5*cm))

    # Additional Information
    additional_info = []
    if project.kategori:
        additional_info.append(['Kategori', project.kategori])
    if project.deskripsi:
        additional_info.append(['Deskripsi', project.deskripsi[:200] + '...' if len(project.deskripsi) > 200 else project.deskripsi])

    if additional_info:
        add_table = Table(additional_info, colWidths=[5*cm, 11*cm])
        add_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e7f0f7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(Paragraph("<b>Informasi Tambahan</b>", heading_style))
        elements.append(add_table)
        elements.append(Spacer(1, 0.5*cm))

    # Footer
    elements.append(Spacer(1, 1*cm))
    footer_text = f"Generated on {date.today().strftime('%d %B %Y')}"
    footer = Paragraph(footer_text, styles['Normal'])
    elements.append(footer)

    # Build PDF
    doc.build(elements)

    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response
