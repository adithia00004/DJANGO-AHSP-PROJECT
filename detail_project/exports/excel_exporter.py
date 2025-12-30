"""
Excel Exporter built on top of ConfigExporterBase.

Supports the same payload structure used by CSV/PDF/Word exporters:
- data['pages'] -> list of sections (page-wise)
- section['table_data'] with headers/rows/hierarchy_levels
- section['sections'] for nested tables or pekerjaan detail (rincian AHSP)

Requirements: openpyxl
"""

from io import BytesIO
from typing import Any, Dict, List

from .base import ConfigExporterBase
from ..export_config import build_identity_rows

try:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    OPENPYXL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OPENPYXL_AVAILABLE = False


class ExcelExporter(ConfigExporterBase):
    """Excel (XLSX) exporter."""

    def export(self, data: Dict[str, Any]):
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError('openpyxl belum terpasang. Install via "pip install openpyxl".')

        wb = Workbook()
        self._sheet_index = 0

        def write_section_to_sheet(section: Dict[str, Any], is_first: bool = False):
            title = section.get('title') or self.config.title
            ws = self._create_sheet(wb, title, is_first=is_first)
            current_row = 1

            # Title
            ws.cell(row=current_row, column=1, value=title)
            ws.cell(row=current_row, column=1).font = Font(size=16, bold=True)
            current_row += 2

            # Identity rows (project info)
            for label, _, value in build_identity_rows(self.config):
                ws.cell(row=current_row, column=1, value=label)
                ws.cell(row=current_row, column=2, value=value)
                current_row += 1

            current_row += 1

            if 'sections' in section:
                subsections = section.get('sections') or []
                is_pekerjaan = bool(subsections and isinstance(subsections[0], dict) and 'pekerjaan' in subsections[0])
                for subsection in subsections:
                    if is_pekerjaan:
                        current_row = self._write_pekerjaan_section(ws, current_row, subsection)
                    else:
                        subtitle = subsection.get('section_title')
                        if subtitle:
                            ws.cell(row=current_row, column=1, value=subtitle)
                            ws.cell(row=current_row, column=1).font = Font(bold=True)
                            current_row += 1
                        current_row = self._write_table(ws, current_row, subsection)
                    current_row += 2
            else:
                current_row = self._write_table(ws, current_row, section)

            footer_rows = section.get('footer_rows') or []
            if footer_rows:
                current_row += 1
                for footer in footer_rows:
                    ws.cell(row=current_row, column=1, value=footer[0] if footer else '')
                    if len(footer) > 1:
                        ws.cell(row=current_row, column=2, value=footer[1])
                    current_row += 1

            self._apply_column_widths(ws, section.get('col_widths'))

        pages = data.get('pages')
        if pages:
            for idx, page in enumerate(pages):
                write_section_to_sheet(page, is_first=(idx == 0))
        else:
            write_section_to_sheet(data, is_first=True)

        # Attach image sheets (e.g., Gantt / Kurva-S screenshots)
        attachments = data.get('attachments') or []
        for att in attachments:
            img_bytes = att.get('bytes')
            if not img_bytes:
                continue
            ws_img = self._create_sheet(wb, att.get('title') or 'Lampiran', is_first=False)
            try:
                xl_img = XLImage(BytesIO(img_bytes))
                ws_img.add_image(xl_img, "A1")
            except Exception:
                ws_img.cell(row=1, column=1, value="Lampiran tidak dapat ditampilkan")

        output = BytesIO()
        wb.save(output)
        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.xlsx"
        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # ------------------------------------------------------------------
    def _create_sheet(self, wb: Workbook, title: str, is_first: bool = False):
        safe_title = self._sanitize_title(title)
        if is_first:
            ws = wb.active
            ws.title = safe_title
        else:
            ws = wb.create_sheet(title=safe_title)
        self._sheet_index += 1
        return ws

    def _sanitize_title(self, title: str) -> str:
        sanitized = ''.join(ch for ch in (title or '') if ch not in '[]:*?/\\').strip()
        if not sanitized:
            sanitized = f'Section {self._sheet_index + 1}'
        return sanitized[:31]

    def _write_table(self, ws, start_row: int, section: Dict[str, Any]) -> int:
        table = section.get('table_data', {})
        headers: List[Any] = table.get('headers', []) or []
        rows: List[List[Any]] = table.get('rows', []) or []
        hierarchy = section.get('hierarchy_levels', {}) or {}

        row_idx = start_row
        header_fill = PatternFill('solid', fgColor='e8e8e8')
        border = Border(
            left=Side(style='thin', color='999999'),
            right=Side(style='thin', color='999999'),
            top=Side(style='thin', color='999999'),
            bottom=Side(style='thin', color='999999'),
        )

        if headers:
            for col, text in enumerate(headers, start=1):
                cell = ws.cell(row=row_idx, column=col, value=text)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
                cell.fill = header_fill
                cell.border = border
            row_idx += 1

        for idx, row in enumerate(rows):
            level = hierarchy.get(idx, 3)
            display_row = list(row)
            if display_row:
                indent = '  ' * max(level - 1, 0)
                display_row[0] = f"{indent}{display_row[0]}"
            for col, value in enumerate(display_row, start=1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.border = border
                if isinstance(value, (int, float)):
                    cell.number_format = '#,##0.00'
            row_idx += 1

        return row_idx

    def _write_pekerjaan_section(self, ws, start_row: int, section: Dict[str, Any]) -> int:
        row_idx = start_row
        pekerjaan = section.get('pekerjaan', {})
        detail_table = section.get('detail_table', {})
        headers = detail_table.get('headers', [])
        rows = detail_table.get('rows', [])

        ws.cell(row=row_idx, column=1, value='PEKERJAAN')
        ws.cell(row=row_idx, column=1).font = Font(bold=True)
        row_idx += 1

        meta_fields = [
            ('Kode', pekerjaan.get('kode', '-')),
            ('Uraian', pekerjaan.get('uraian', '-')),
            ('Satuan', pekerjaan.get('satuan', '-')),
            ('Total', pekerjaan.get('total', '-')),
        ]
        for label, value in meta_fields:
            ws.cell(row=row_idx, column=1, value=label)
            ws.cell(row=row_idx, column=2, value=value)
            row_idx += 1

        row_idx += 1

        if not section.get('has_details'):
            ws.cell(row=row_idx, column=1, value='Tidak ada detail item untuk pekerjaan ini')
            return row_idx + 2

        border = Border(
            left=Side(style='thin', color='999999'),
            right=Side(style='thin', color='999999'),
            top=Side(style='thin', color='999999'),
            bottom=Side(style='thin', color='999999'),
        )
        header_fill = PatternFill('solid', fgColor='e8e8e8')

        if headers:
            for col, text in enumerate(headers, start=1):
                cell = ws.cell(row=row_idx, column=col, value=text)
                cell.font = Font(bold=True)
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
                cell.border = border
            row_idx += 1

        for row in rows:
            for col, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.border = border
                if isinstance(value, (int, float)):
                    cell.number_format = '#,##0.00'
            row_idx += 1

        return row_idx

    def _apply_column_widths(self, ws, widths: List[float] | None):
        if not widths:
            return
        for idx, width in enumerate(widths, start=1):
            excel_width = self._mm_to_excel_width(width)
            if excel_width:
                ws.column_dimensions[get_column_letter(idx)].width = excel_width

    def _mm_to_excel_width(self, mm_value: float | None):
        if not mm_value:
            return None
        try:
            inches = float(mm_value) / 25.4
            # Approximate: 1 Excel width unit ≈ character ≈ 1/7 inch
            return round(inches * 7, 2)
        except Exception:
            return None

    # ==================================================================
    # Professional Export for Rekap Report
    # ==================================================================
    
    def export_professional(self, data: Dict[str, Any]):
        """
        Export professionally styled Excel for Rekap/Monthly/Weekly reports.
        
        Creates multiple sheets:
        - Sheet 1: Ringkasan (Project Info)
        - Sheet 2: Grid Planned 
        - Sheet 3: Grid Actual
        - Sheet 4: Kurva S (Data + Native Chart)
        """
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError('openpyxl belum terpasang. Install via "pip install openpyxl".')
        
        import time
        start_time = time.time()
        print(f"[ExcelExporter] Starting professional export...")
        
        from openpyxl.chart import LineChart, Reference
        from openpyxl.chart.label import DataLabelList
        
        wb = Workbook()
        report_type = data.get('report_type', 'rekap')
        
        # Get data
        planned_pages = data.get('planned_pages', [])
        actual_pages = data.get('actual_pages', [])
        kurva_s_data = data.get('kurva_s_data', [])
        summary = data.get('summary', {})
        project_info = data.get('project_info', {})
        
        # Sheet 1: Ringkasan
        ws_ringkasan = wb.active
        ws_ringkasan.title = "Ringkasan"
        self._build_ringkasan_sheet(ws_ringkasan, project_info, summary, data)
        
        # Sheet 2: Grid Planned
        ws_planned = wb.create_sheet("Grid Planned")
        self._build_grid_sheet(ws_planned, planned_pages, "RENCANA (PLANNED)")
        
        # Sheet 3: Grid Actual 
        ws_actual = wb.create_sheet("Grid Actual")
        self._build_grid_sheet(ws_actual, actual_pages, "REALISASI (ACTUAL)")
        
        # Sheet 4: Kurva S with Native Chart
        ws_kurva = wb.create_sheet("Kurva S")
        self._build_kurva_s_sheet(ws_kurva, kurva_s_data)
        
        print(f"[ExcelExporter] [TIME] Workbook built in {time.time() - start_time:.2f}s")
        
        # Save to response
        output = BytesIO()
        wb.save(output)
        
        from datetime import date
        filename = f"Laporan_{report_type}_{date.today()}.xlsx"
        
        print(f"[ExcelExporter] [OK] Total export time: {time.time() - start_time:.2f}s")
        
        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def _build_ringkasan_sheet(self, ws, project_info: Dict, summary: Dict, data: Dict):
        """Build summary sheet with project info."""
        # Styles
        title_font = Font(size=16, bold=True)
        header_font = Font(size=11, bold=True)
        border = self._get_thin_border()
        header_fill = PatternFill('solid', fgColor='E8F0FE')
        
        row = 1
        
        # Title
        ws.cell(row=row, column=1, value="LAPORAN REKAPITULASI JADWAL PEKERJAAN")
        ws.cell(row=row, column=1).font = title_font
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 2
        
        # Project Info
        info_items = [
            ("Nama Proyek", project_info.get('nama_proyek', self.config.project_name if self.config else '-')),
            ("Lokasi", project_info.get('lokasi', '-')),
            ("Tanggal Export", data.get('export_date', '')),
            ("Total Minggu", str(len(data.get('kurva_s_data', [])))),
        ]
        
        for label, value in info_items:
            ws.cell(row=row, column=1, value=label)
            ws.cell(row=row, column=1).font = header_font
            ws.cell(row=row, column=2, value=value)
            row += 1
        
        row += 1
        
        # Summary section
        ws.cell(row=row, column=1, value="RINGKASAN PROGRESS")
        ws.cell(row=row, column=1).font = title_font
        row += 1
        
        summary_items = [
            ("Progress Rencana", f"{summary.get('planned_progress', 0):.2f}%"),
            ("Progress Realisasi", f"{summary.get('actual_progress', 0):.2f}%"),
            ("Deviasi", f"{summary.get('deviation', 0):.2f}%"),
        ]
        
        for label, value in summary_items:
            ws.cell(row=row, column=1, value=label)
            ws.cell(row=row, column=1).font = header_font
            ws.cell(row=row, column=1).border = border
            ws.cell(row=row, column=2, value=value)
            ws.cell(row=row, column=2).border = border
            row += 1
        
        # Column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 40
    
    def _build_grid_sheet(self, ws, pages: List[Dict], title: str):
        """Build Grid sheet with hierarchy, borders, merge, and indentation."""
        if not pages:
            ws.cell(row=1, column=1, value="Tidak ada data")
            return
        
        # Styles
        title_font = Font(size=14, bold=True)
        header_font = Font(size=9, bold=True)
        data_font = Font(size=8, name='Arial')
        border = self._get_thin_border()
        header_fill = PatternFill('solid', fgColor='E8F0FE')
        klasifikasi_fill = PatternFill('solid', fgColor='D9E8FB')
        sub_klasifikasi_fill = PatternFill('solid', fgColor='F0F4F8')
        
        row = 1
        
        # Title
        ws.cell(row=row, column=1, value=f"GRID VIEW - {title}")
        ws.cell(row=row, column=1).font = title_font
        row += 2
        
        # Process each page
        for page_idx, page in enumerate(pages):
            table_data = page.get('table_data', {})
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            hierarchy = page.get('hierarchy_levels', {})
            
            if page_idx > 0:
                row += 2  # Space between pages
            
            # Headers
            if headers:
                # Column A: No (narrow)
                # Column B-C: Uraian (merged)
                # Column D: Volume
                # Column E onwards: Week columns
                
                col = 1
                for h_idx, header in enumerate(headers):
                    cell = ws.cell(row=row, column=col, value=header)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    col += 1
                row += 1
            
            # Data rows
            for r_idx, row_data in enumerate(rows):
                level = hierarchy.get(r_idx, 3)
                
                col = 1
                for c_idx, cell_value in enumerate(row_data):
                    cell = ws.cell(row=row, column=col, value=cell_value if cell_value else '')
                    cell.font = data_font
                    cell.border = border
                    
                    # Apply hierarchy styling
                    if level == 1:  # Klasifikasi
                        cell.fill = klasifikasi_fill
                        cell.font = Font(size=9, bold=True, name='Arial')
                    elif level == 2:  # Sub Klasifikasi
                        cell.fill = sub_klasifikasi_fill
                        cell.font = Font(size=8, bold=True, name='Arial')
                    
                    # Indentation for Uraian column (column 1, index 0)
                    if c_idx == 0:
                        indent = max(0, level - 1) * 2
                        cell.alignment = Alignment(indent=indent, wrap_text=True)
                    else:
                        cell.alignment = Alignment(horizontal='center')
                    
                    col += 1
                row += 1
        
        # Freeze header row
        ws.freeze_panes = 'A4'
        
        # Column widths
        ws.column_dimensions['A'].width = 40  # Uraian
        ws.column_dimensions['B'].width = 10  # Volume
        ws.column_dimensions['C'].width = 8   # Satuan
        # Week columns
        for col_idx in range(4, 60):
            ws.column_dimensions[get_column_letter(col_idx)].width = 7
    
    def _build_kurva_s_sheet(self, ws, kurva_s_data: List[Dict]):
        """Build Kurva S sheet with data table and native LineChart."""
        from openpyxl.chart import LineChart, Reference
        from openpyxl.chart.label import DataLabelList
        from openpyxl.chart.series import SeriesLabel
        
        if not kurva_s_data:
            ws.cell(row=1, column=1, value="Tidak ada data Kurva S")
            return
        
        # Styles
        title_font = Font(size=14, bold=True)
        header_font = Font(size=10, bold=True)
        border = self._get_thin_border()
        header_fill = PatternFill('solid', fgColor='E8F0FE')
        
        row = 1
        
        # Title
        ws.cell(row=row, column=1, value="KURVA S - PROGRESS KUMULATIF")
        ws.cell(row=row, column=1).font = title_font
        row += 2
        
        # Headers
        headers = ['Minggu', 'Rencana (%)', 'Realisasi (%)']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
        row += 1
        
        data_start_row = row
        
        # Data rows
        for item in kurva_s_data:
            week_label = item.get('label', item.get('week', ''))
            planned = item.get('planned_cumulative', item.get('planned', 0))
            actual = item.get('actual_cumulative', item.get('actual', 0))
            
            ws.cell(row=row, column=1, value=week_label).border = border
            ws.cell(row=row, column=2, value=planned).border = border
            ws.cell(row=row, column=2).number_format = '0.00'
            ws.cell(row=row, column=3, value=actual).border = border
            ws.cell(row=row, column=3).number_format = '0.00'
            row += 1
        
        data_end_row = row - 1
        
        # Column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15
        
        # Create Native LineChart
        chart = LineChart()
        chart.title = "Kurva S Progress"
        chart.style = 10
        chart.y_axis.title = "% Kumulatif"
        chart.x_axis.title = "Minggu"
        chart.width = 18
        chart.height = 10
        
        # Data references
        planned_data = Reference(ws, min_col=2, min_row=data_start_row - 1, 
                                  max_row=data_end_row)
        actual_data = Reference(ws, min_col=3, min_row=data_start_row - 1, 
                                 max_row=data_end_row)
        categories = Reference(ws, min_col=1, min_row=data_start_row, 
                               max_row=data_end_row)
        
        chart.add_data(planned_data, titles_from_data=True)
        chart.add_data(actual_data, titles_from_data=True)
        chart.set_categories(categories)
        
        # Style series
        if chart.series:
            chart.series[0].graphicalProperties.line.solidFill = "4285F4"  # Blue - Planned
            chart.series[0].graphicalProperties.line.width = 25000  # 2.5pt
            if len(chart.series) > 1:
                chart.series[1].graphicalProperties.line.solidFill = "34A853"  # Green - Actual
                chart.series[1].graphicalProperties.line.width = 25000
        
        # Position chart below data (aligned with column E)
        chart_position = f"E{data_start_row - 1}"
        ws.add_chart(chart, chart_position)
    
    def _get_thin_border(self):
        """Get standard thin border."""
        thin = Side(style='thin', color='999999')
        return Border(left=thin, right=thin, top=thin, bottom=thin)

