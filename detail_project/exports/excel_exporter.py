"""
Excel Exporter built on top of ConfigExporterBase.

Supports:
- Standard export via export() for RAB, Kebutuhan, etc.
- Professional export via export_professional() for Jadwal Pekerjaan Rekap
  with 3 sheets: Cover, Kurva S (with LineChart), Input Progress-Gantt

Requirements: openpyxl
"""

from io import BytesIO
import logging
from typing import Any, Dict, List
from decimal import Decimal

from .base import ConfigExporterBase
from ..export_config import build_identity_rows

try:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.chart import LineChart, Reference
    from openpyxl.chart.series import SeriesLabel
    OPENPYXL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OPENPYXL_AVAILABLE = False


logger = logging.getLogger(__name__)


def parse_number(value, default=0.0):
    """
    Unified number parser for Excel exports.
    
    Handles:
    - Indonesian format: dot as thousands (150.000 = 150000), comma as decimal (150.000,50)
    - US/Standard format: comma as thousands (150,000), dot as decimal (150,000.50)
    - European format: 1.234,56 = 1234.56
    - Percentage: '50%' -> 0.5, '50,00%' -> 0.5
    - Decimal types
    
    Args:
        value: Input value (string, int, float, Decimal)
        default: Default value if parsing fails
        
    Returns:
        float: Parsed number
    """
    if value is None or value == '' or value == '-':
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if not isinstance(value, str):
        return default
        
    s = value.strip()
    if not s:
        return default
    
    # Check for percentage
    is_percent = '%' in s
    s = s.replace('%', '').strip()
    
    try:
        # Case 1: Both comma and dot present
        if ',' in s and '.' in s:
            # Determine which is decimal separator by position
            comma_pos = s.rfind(',')
            dot_pos = s.rfind('.')
            
            if comma_pos > dot_pos:
                # Indonesian/European: 1.234.567,89 -> comma is decimal
                s = s.replace('.', '').replace(',', '.')
            else:
                # US: 1,234,567.89 -> dot is decimal
                s = s.replace(',', '')
        
        # Case 2: Only comma
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2:
                after_comma = parts[1]
                # Indonesian thousands: "150,000" (3 digits after) -> 150000
                # Decimal: "150,5" or "150,50" (1-2 digits after) -> 150.5
                if len(after_comma) == 3 and after_comma.isdigit():
                    # Likely thousands separator
                    s = s.replace(',', '')
                elif len(after_comma) <= 2:
                    # Likely decimal separator
                    s = s.replace(',', '.')
                else:
                    # Koefisien with many decimals: "0,001234" -> 0.001234
                    s = s.replace(',', '.')
            else:
                # Multiple commas = thousands: "1,234,567"
                s = s.replace(',', '')
        
        # Case 3: Only dot
        elif '.' in s:
            parts = s.split('.')
            if len(parts) > 2:
                # Multiple dots = thousands: "1.234.567" -> 1234567
                s = s.replace('.', '')
            elif len(parts) == 2:
                after_dot = parts[1]
                before_dot = parts[0]
                # Indonesian thousands: "150.000" (3 digits, short before) -> 150000
                # Also: "1.500.000" but already handled by len(parts) > 2
                if len(after_dot) == 3 and len(before_dot) <= 3 and after_dot.isdigit():
                    s = s.replace('.', '')
                # else: keep as decimal (e.g., "3.14", "0.5")
        
        result = float(s)
        
        if is_percent:
            result /= 100.0
            
        return result
        
    except (ValueError, TypeError):
        return default


# Alias for backward compatibility
safe_float = parse_number


# Style constants matching ExcelJS
COLORS = {
    'PLANNED_BG': '00CED1',     # Cyan for Planned
    'ACTUAL_BG': '34A853',      # Green for Actual
    'HEADER_BG': '2D5A8E',      # Dark blue for headers
    'HEADER_TEXT': 'FFFFFF',    # White
    'SUBHEADER_BG': 'E8F0FE',   # Light blue
    'KLASIFIKASI_BG': 'D9E8FB',
    'SUB_KLASIFIKASI_BG': 'F0F4F8',
    'TOTAL_BG': 'FCE7F3',       # Light pink
    'BORDER': '999999',
    'PRIMARY': '2D5A8E',
}

# Standard dimensions for consistent sizing
# Excel column width: approximate characters (1 char ≈ 7 pixels ≈ 0.185 cm)
# Excel row height: points (1 point = 1/72 inch = 0.0352778 cm)
DIMENSIONS = {
    # Week column: fits "Week XX" (about 9 characters)
    'WEEK_COL_WIDTH': 9,            # characters
    'WEEK_COL_WIDTH_CM': 1.7,       # ≈ 9 chars × 0.185 cm
    
    # Pekerjaan row: fits 2 lines of text (standard line ≈ 15 points)
    'PEKERJAAN_ROW_HEIGHT': 30,     # points (2 lines × 15 pts)
    'PEKERJAAN_ROW_HEIGHT_CM': 1.06,  # ≈ 30 pts × 0.0352778 cm
    
    # Header row
    'HEADER_ROW_HEIGHT': 30,        # points
    
    # Each pekerjaan = 2 rows (planned + actual)
    'ROWS_PER_PEKERJAAN': 2,
}


class ExcelExporter(ConfigExporterBase):
    """Excel (XLSX) exporter."""

    # Diisi export_package() selama merakit paket; lihat catatan di export().
    _package_wb = None
    _package_first_used = False

    def _get_thin_border(self):
        """Get standard thin border."""
        side = Side(style='thin', color=COLORS['BORDER'])
        return Border(top=side, bottom=side, left=side, right=side)

    def export(self, data: Dict[str, Any]):
        """Standard export method for non-Jadwal exports."""
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError('openpyxl belum terpasang. Install via "pip install openpyxl".')

        # Check if this is Rincian AHSP data (has 'sections' with 'pekerjaan' and 'groups')
        sections = data.get('sections', [])
        is_rincian_ahsp = bool(
            sections and 
            isinstance(sections[0], dict) and 
            'pekerjaan' in sections[0] and 
            'groups' in sections[0]
        )

        if is_rincian_ahsp:
            return self._export_rincian_ahsp_2sheet(data)

        # Mode paket: workbook sudah disiapkan export_package() dan responsnya
        # dibuat sekali di akhir, sehingga keempat dokumen menulis sheet ke
        # workbook yang SAMA alih-alih membuat berkas masing-masing.
        wb = self._package_wb if self._package_wb is not None else Workbook()
        if self._package_wb is None:
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
                footer_fmt = section.get('footer_value_format')
                for footer in footer_rows:
                    ws.cell(row=current_row, column=1, value=footer[0] if footer else '')
                    if len(footer) > 1:
                        self._write_value_cell(ws, current_row, 2, footer[1], footer_fmt)
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

        if self._package_wb is not None:
            return None

        output = BytesIO()
        wb.save(output)
        from .naming import build_export_filename  # WP-B5 inc-B5c
        filename = build_export_filename(self.config.project_name, self.config.title, 'xlsx', self.config.export_date)
        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def export_package(self, documents, filename_title: str = 'Paket Perencanaan'):
        """Gabungkan beberapa dokumen menjadi SATU workbook.

        Excel tidak mengenal "dokumen berurutan", jadi paket di format ini
        berarti satu berkas berisi sheet dari tiap dokumen. Nama sheet diambil
        dari judul bagian; openpyxl menjamin keunikannya.
        """
        self._package_wb = Workbook()
        self._package_first_used = False
        self._sheet_index = 0
        original_title = self.config.title
        try:
            for entry in documents:
                self.config.title = entry['title']
                # Dokumen dapat menunjuk metode exporter khusus untuk format ini
                # (mis. Volume, yang kolom Formula-nya harus ditulis sebagai teks).
                spec = entry.get('xlsx')
                if spec:
                    method_name, adapter = spec
                    getattr(self, method_name)(entry['data'], adapter)
                else:
                    self.export(entry['data'])
            wb = self._package_wb
        finally:
            self._package_wb = None
            self.config.title = original_title

        output = BytesIO()
        wb.save(output)
        from .naming import build_export_filename
        filename = build_export_filename(
            self.config.project_name, filename_title, 'xlsx', self.config.export_date
        )
        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def export_volume_pekerjaan(self, data: Dict[str, Any], adapter=None):
        """
        Export Volume Pekerjaan with 2 sheets:
        1. Parameters - Parameter table with values (SSOT for formula references)
        2. Volume Pekerjaan - Main table with Excel formula references
        
        Args:
            data: Export data from VolumePekerjaanAdapter
            adapter: Adapter instance for formula conversion
        """
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError('openpyxl belum terpasang. Install via "pip install openpyxl".')

        # Ikut mode paket bila sedang merakit; lihat catatan di export().
        wb = self._package_wb if self._package_wb is not None else Workbook()
        border = self._get_thin_border()
        
        pages = data.get('pages', [])
        if len(pages) < 2:
            # Fallback to standard export
            return self.export(data)
        
        volume_page = pages[0]  # Volume & Formula (main content)
        param_page = pages[1]   # Parameters (appendix)
        parameter_cells = data.get('parameter_cells', {})
        
        # ========== SHEET 1: PARAMETERS ==========
        ws_params = self._create_sheet(wb, "Parameter", is_first=True)
        ws_params.title = "Parameters"
        
        current_row = 1
        
        # Title
        ws_params.cell(row=current_row, column=1, value=param_page.get('title', 'DAFTAR PARAMETER'))
        ws_params.cell(row=current_row, column=1).font = Font(size=14, bold=True, color='4472C4')
        current_row += 2
        
        # Identity rows (project info)
        for label, _, value in build_identity_rows(self.config):
            ws_params.cell(row=current_row, column=1, value=label)
            ws_params.cell(row=current_row, column=1).font = Font(bold=True)
            ws_params.cell(row=current_row, column=2, value=value)
            current_row += 1
        current_row += 1
        
        # Parameter table
        param_table = param_page.get('table_data', {})
        param_headers = param_table.get('headers', [])
        param_rows = param_table.get('rows', [])
        param_codes = param_table.get('param_codes', [])
        param_formulas = param_table.get('param_formulas', [])
        
        # Track actual cell locations for formula references
        param_value_cells = {}  # {param_code: 'C5', ...}
        param_header_row = current_row
        first_param_row = param_header_row + 1
        for row_idx, param_code_raw in enumerate(param_codes):
            param_code = str(param_code_raw or '').strip().lower()
            if param_code:
                param_value_cells[param_code] = f'C{first_param_row + row_idx}'
        
        # Headers
        for col_idx, header in enumerate(param_headers, 1):
            cell = ws_params.cell(row=current_row, column=col_idx, value=header)
            cell.font = Font(bold=True, color='FFFFFF', size=9)
            cell.fill = PatternFill('solid', fgColor='4472C4')
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        current_row += 1
        
        # Parameter rows. WP Export: Nilai (base param) is written as a real number
        # via the boundary helper; computed params carry '-' (text) for Nilai and the
        # expression text in the Expression column — no live Excel formula.
        param_column_formats = param_table.get('column_formats', [])
        for row_idx, row in enumerate(param_rows):
            for col_idx, val in enumerate(row, 1):
                fmt = param_column_formats[col_idx - 1] if col_idx - 1 < len(param_column_formats) else None
                cell = self._write_value_cell(ws_params, current_row, col_idx, val, fmt)
                cell.font = Font(size=9)
                cell.border = border
                if col_idx == 4:  # Nilai column - right align numbers
                    cell.alignment = Alignment(horizontal='right')
            current_row += 1
        
        # Apply column widths
        param_widths = param_page.get('col_widths', [12, 40, 80, 50])
        for idx, w in enumerate(param_widths):
            ws_params.column_dimensions[get_column_letter(idx + 1)].width = self._mm_to_excel_width(w)
        
        # ========== SHEET 2: VOLUME PEKERJAAN ==========
        ws_volume = wb.create_sheet("Volume Pekerjaan")
        
        current_row = 1
        
        # Title
        ws_volume.cell(row=current_row, column=1, value=volume_page.get('title', 'VOLUME PEKERJAAN'))
        ws_volume.cell(row=current_row, column=1).font = Font(size=14, bold=True, color='4472C4')
        current_row += 2
        
        # Identity rows
        for label, _, value in build_identity_rows(self.config):
            ws_volume.cell(row=current_row, column=1, value=label)
            ws_volume.cell(row=current_row, column=1).font = Font(bold=True)
            ws_volume.cell(row=current_row, column=2, value=value)
            current_row += 1
        current_row += 1
        
        # Volume table
        volume_table = volume_page.get('table_data', {})
        volume_headers = volume_table.get('headers', [])
        volume_rows = volume_table.get('rows', [])
        hierarchy_levels = volume_page.get('hierarchy_levels', {})
        row_types = volume_page.get('row_types', [])
        row_formulas = volume_page.get('row_formulas', [])
        formula_display_mode = volume_page.get('formula_display_mode', 'raw')
        num_cols = len(volume_headers)
        
        # Headers
        for col_idx, header in enumerate(volume_headers, 1):
            cell = ws_volume.cell(row=current_row, column=col_idx, value=header)
            cell.font = Font(bold=True, color='FFFFFF', size=9)
            cell.fill = PatternFill('solid', fgColor='4472C4')
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        current_row += 1
        
        # Volume rows
        for row_idx, row in enumerate(volume_rows):
            row_type = row_types[row_idx] if row_idx < len(row_types) else 'item'
            
            if row_type == 'category':
                # Category row - merge and style
                cell = ws_volume.cell(row=current_row, column=1, value=row[0] if row else '')
                cell.font = Font(bold=True, size=9)
                cell.fill = PatternFill('solid', fgColor='E8E8E8')
                cell.border = border
                
                if num_cols > 1:
                    ws_volume.merge_cells(start_row=current_row, start_column=1, 
                                         end_row=current_row, end_column=num_cols)
                for col_idx in range(2, num_cols + 1):
                    ws_volume.cell(row=current_row, column=col_idx).border = border
            else:
                # Normal row. WP Export: the Volume column is the canonical backend
                # number; the Formula column keeps the input formula as TEXT (audit).
                # No _convert_volume_formula / live Excel formula on the official report.
                volume_column_formats = volume_table.get('column_formats', [])
                for col_idx, val in enumerate(row, 1):
                    fmt = volume_column_formats[col_idx - 1] if col_idx - 1 < len(volume_column_formats) else None
                    if col_idx == 3 and isinstance(val, str) and val.startswith('='):
                        # Force text so Excel never evaluates the formula provenance.
                        cell = ws_volume.cell(row=current_row, column=col_idx, value=f"'{val}")
                    else:
                        cell = self._write_value_cell(ws_volume, current_row, col_idx, val, fmt)
                    cell.font = Font(size=9)
                    cell.border = border

                    # Text wrapping for Uraian column (column 2)
                    if col_idx == 2:
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                    # Right-align numeric columns (Volume = last column)
                    elif col_idx == num_cols:
                        cell.alignment = Alignment(horizontal='right', vertical='top')
                
                # Apply indent for hierarchy
                level = hierarchy_levels.get(row_idx, 0)
                if level > 0:
                    ws_volume.cell(row=current_row, column=1).alignment = Alignment(indent=level)
            
            current_row += 1
        
        # Footer
        footer_rows = volume_page.get('footer_rows', [])
        if footer_rows:
            current_row += 1
            for footer in footer_rows:
                ws_volume.cell(row=current_row, column=1, value=footer[0] if footer else '')
                ws_volume.cell(row=current_row, column=1).font = Font(bold=True)
                if len(footer) > 1:
                    ws_volume.cell(row=current_row, column=2, value=footer[1])
                current_row += 1
        
        # Apply column widths
        volume_widths = volume_page.get('col_widths', [10, 70, 55, 20, 27])
        for idx, w in enumerate(volume_widths):
            ws_volume.column_dimensions[get_column_letter(idx + 1)].width = self._mm_to_excel_width(w)
        
        # ========== SHEET 3: PENGESAHAN (Signatures) ==========
        signature_data = data.get('signature_data')
        if data.get('include_signatures') and signature_data:
            ws_sign = wb.create_sheet("Pengesahan")
            self._write_signature_sheet(ws_sign, signature_data)
        
        # Save workbook
        output = BytesIO()
        if self._package_wb is not None:
            return None

        wb.save(output)
        from .naming import build_export_filename
        filename = build_export_filename(
            self.config.project_name, "Volume Pekerjaan", "xlsx",
            self.config.export_date,
        )
        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def _convert_volume_formula(self, formula_str: str, param_cells: Dict[str, str]) -> str:
        """
        Convert volume formula to Excel formula with cell references.

        Example:
            Input: "= panjang * lebar"
            param_cells: {'panjang': 'D5', 'lebar': 'D6'}
            Output: "=Parameters!$D$5*Parameters!$D$6"

        WP Export (2026-06-20): RETIRED from the official Volume report — the report
        now writes canonical backend values, never a live formula Excel could
        recompute. Kept (no callers) and reserved for a future, separate
        "Template Kalkulasi" export type that is explicitly an editable/recomputable
        workbook, not the official report.
        """
        import re
        
        if not formula_str or not formula_str.strip().startswith('='):
            return formula_str
        
        excel_formula = formula_str.strip()
        
        # Replace each parameter with its cell reference
        for param, cell_ref in param_cells.items():
            # Extract column letter and row number
            col = ''.join(c for c in cell_ref if c.isalpha())
            row = ''.join(c for c in cell_ref if c.isdigit())
            
            # Use word boundary to avoid partial replacements
            pattern = r'\b' + re.escape(param) + r'\b'
            replacement = f"Parameters!${col}${row}"
            excel_formula = re.sub(pattern, replacement, excel_formula, flags=re.IGNORECASE)
        
        return excel_formula

    def _write_signature_sheet(self, ws, signature_data: Dict[str, Any]):
        """Write signature/pengesahan sheet matching Harga Items format."""
        border = self._get_thin_border()
        
        # Title
        ws.cell(row=1, column=1, value="LEMBAR PENGESAHAN")
        ws.cell(row=1, column=1).font = Font(size=14, bold=True)
        ws.merge_cells('A1:F1')
        ws.cell(row=1, column=1).alignment = Alignment(horizontal='center')
        
        # Signature table starts at row 5
        start_row = 5
        
        # Left signature
        ws.cell(row=start_row, column=2, value=signature_data.get('left_title', 'Disetujui Oleh,'))
        ws.cell(row=start_row, column=2).font = Font(bold=True)
        ws.cell(row=start_row, column=2).alignment = Alignment(horizontal='center')
        
        # Right signature
        ws.cell(row=start_row, column=5, value=signature_data.get('right_title', 'Dibuat Oleh,'))
        ws.cell(row=start_row, column=5).font = Font(bold=True)
        ws.cell(row=start_row, column=5).alignment = Alignment(horizontal='center')
        
        # Space for signature
        space_row = start_row + 5
        
        # Names
        ws.cell(row=space_row, column=2, value=signature_data.get('left_name', '...........................'))
        ws.cell(row=space_row, column=2).alignment = Alignment(horizontal='center')
        
        ws.cell(row=space_row, column=5, value=signature_data.get('right_name', '...........................'))
        ws.cell(row=space_row, column=5).alignment = Alignment(horizontal='center')
        
        # Positions
        ws.cell(row=space_row + 1, column=2, value=signature_data.get('left_position', 'Pejabat Pembuat Komitmen'))
        ws.cell(row=space_row + 1, column=2).alignment = Alignment(horizontal='center')
        
        ws.cell(row=space_row + 1, column=5, value=signature_data.get('right_position', 'Konsultan Perencana'))
        ws.cell(row=space_row + 1, column=5).alignment = Alignment(horizontal='center')
        
        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 30
        ws.column_dimensions['F'].width = 5

    def _export_rincian_ahsp_2sheet(self, data: Dict[str, Any]):
        """
        Export Rincian AHSP with 2 sheets:
        1. Rekap - Summary with references to Rincian sheet
        2. Rincian - Full detail per pekerjaan
        """
        # Ikut mode paket: menulis ke workbook bersama bila sedang merakit paket.
        wb = self._package_wb if self._package_wb is not None else Workbook()
        border = self._get_thin_border()
        sections = data.get('sections', [])

        # ========== SHEET 1: RINCIAN (Detail) ==========
        # Lewat _create_sheet agar penjagaan mode paket berlaku: wb.active hanya
        # boleh dipakai dokumen pertama. Sebelumnya jalur ini memakainya langsung
        # dan menimpa sheet dokumen sebelumnya saat merakit paket.
        ws_rincian = self._create_sheet(wb, "Rincian", is_first=True)
        
        current_row = 1
        
        # Title
        ws_rincian.cell(row=current_row, column=1, value="RINCIAN ANALISA HARGA SATUAN PEKERJAAN")
        ws_rincian.cell(row=current_row, column=1).font = Font(size=16, bold=True)
        current_row += 2

        # Identity rows
        for label, _, value in build_identity_rows(self.config):
            ws_rincian.cell(row=current_row, column=1, value=label)
            ws_rincian.cell(row=current_row, column=2, value=value)
            current_row += 1
        current_row += 1

        # Track G cell references for each pekerjaan (for Rekap cross-reference)
        pekerjaan_refs = []  # List of {kode, uraian, e_cell, f_cell, g_cell}

        # Write each pekerjaan section
        for section in sections:
            pekerjaan = section.get('pekerjaan', {})
            groups = section.get('groups', [])
            totals = section.get('totals', {})
            
            pek_kode = pekerjaan.get('kode', '')
            pek_uraian = pekerjaan.get('uraian', '')
            
            # Write pekerjaan section and track row numbers
            section_start_row = current_row
            current_row = self._write_pekerjaan_section_with_tracking(
                ws_rincian, current_row, section, pekerjaan_refs
            )
            current_row += 2

        # Apply column widths for Rincian
        ws_rincian.column_dimensions['A'].width = 5
        ws_rincian.column_dimensions['B'].width = 40
        ws_rincian.column_dimensions['C'].width = 15
        ws_rincian.column_dimensions['D'].width = 10
        ws_rincian.column_dimensions['E'].width = 12
        ws_rincian.column_dimensions['F'].width = 15
        ws_rincian.column_dimensions['G'].width = 18

        # ========== SHEET 2: REKAP (Summary with References) ==========
        # Dalam paket, jangan sisipkan di posisi 0 -- itu akan mendahului
        # sheet dokumen sebelumnya dan mengacak urutan paket.
        ws_rekap = (wb.create_sheet("Rekap") if self._package_wb is not None
                    else wb.create_sheet("Rekap", 0))
        
        current_row = 1
        
        # Title
        ws_rekap.cell(row=current_row, column=1, value="REKAP ANALISA HARGA SATUAN PEKERJAAN")
        ws_rekap.cell(row=current_row, column=1).font = Font(size=16, bold=True)
        current_row += 2

        # Identity rows
        for label, _, value in build_identity_rows(self.config):
            ws_rekap.cell(row=current_row, column=1, value=label)
            ws_rekap.cell(row=current_row, column=2, value=value)
            current_row += 1
        current_row += 2

        # Headers
        headers = ['No', 'Kode', 'Uraian Pekerjaan', 'E — Jumlah (A+B+C+LAIN)', 'F — Profit/Margin', 'G — Harga Satuan']
        for col_idx, header in enumerate(headers, 1):
            cell = ws_rekap.cell(row=current_row, column=col_idx, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws_rekap.row_dimensions[current_row].height = 30
        current_row += 1

        # Data rows — canonical backend values (no cross-sheet formula references).
        for idx, ref in enumerate(pekerjaan_refs, 1):
            ws_rekap.cell(row=current_row, column=1, value=idx).border = border
            ws_rekap.cell(row=current_row, column=2, value=ref['kode']).border = border
            ws_rekap.cell(row=current_row, column=3, value=ref['uraian']).border = border

            e_cell = self._write_value_cell(ws_rekap, current_row, 4, ref.get('e_val'), '#,##0.00')
            e_cell.border = border

            f_cell = self._write_value_cell(ws_rekap, current_row, 5, ref.get('f_val'), '#,##0.00')
            f_cell.border = border

            g_cell = self._write_value_cell(ws_rekap, current_row, 6, ref.get('g_val'), '#,##0.00')
            g_cell.font = Font(bold=True)
            g_cell.border = border

            current_row += 1

        # Column widths for Rekap
        ws_rekap.column_dimensions['A'].width = 5
        ws_rekap.column_dimensions['B'].width = 15
        ws_rekap.column_dimensions['C'].width = 45
        ws_rekap.column_dimensions['D'].width = 20
        ws_rekap.column_dimensions['E'].width = 18
        ws_rekap.column_dimensions['F'].width = 18

        # ========== SHEET 3: KONTROL KALKULASI (audit-only) ==========
        # WP Export control layer: the official sheets above hold backend-canonical
        # NUMBERS. This sheet re-derives each pekerjaan's G = E + F with a LIVE Excel
        # formula referencing the Rincian sheet, then shows the difference vs the
        # official value. Audit only — its formula results are never used for import
        # or app calculation.
        ws_kontrol = wb.create_sheet("Kontrol Kalkulasi")
        kc_row = 1
        ws_kontrol.cell(row=kc_row, column=1, value="KONTROL KALKULASI (AUDIT)")
        ws_kontrol.cell(row=kc_row, column=1).font = Font(size=14, bold=True, color='B45309')
        kc_row += 1
        ws_kontrol.cell(
            row=kc_row, column=1,
            value=("Nilai Kontrol dihitung ulang oleh Excel dari sheet Rincian (G = E + F). "
                   "Sheet ini hanya untuk audit; hasilnya tidak dipakai untuk perhitungan/import. "
                   "Status PERIKSA = selisih melebihi 0,01."),
        )
        ws_kontrol.cell(row=kc_row, column=1).font = Font(size=9, italic=True, color='6B7280')
        kc_row += 2

        kontrol_headers = ['No', 'Kode', 'Uraian', 'Nilai Resmi', 'Nilai Kontrol', 'Selisih', 'Status']
        for col_idx, header in enumerate(kontrol_headers, 1):
            cell = ws_kontrol.cell(row=kc_row, column=col_idx, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='B45309')
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        kc_row += 1

        for idx, ref in enumerate(pekerjaan_refs, 1):
            ws_kontrol.cell(row=kc_row, column=1, value=idx).border = border
            ws_kontrol.cell(row=kc_row, column=2, value=ref.get('kode')).border = border
            ws_kontrol.cell(row=kc_row, column=3, value=ref.get('uraian')).border = border

            resmi = self._write_value_cell(ws_kontrol, kc_row, 4, ref.get('g_val'), '#,##0.00')
            resmi.border = border

            # Nilai Kontrol: live formula re-deriving G = E + F from the Rincian sheet.
            kontrol = ws_kontrol.cell(
                row=kc_row, column=5,
                value=f"=Rincian!{ref['e_cell']}+Rincian!{ref['f_cell']}",
            )
            kontrol.number_format = '#,##0.00'
            kontrol.border = border

            selisih = ws_kontrol.cell(row=kc_row, column=6, value=f"=D{kc_row}-E{kc_row}")
            selisih.number_format = '#,##0.00'
            selisih.border = border

            status = ws_kontrol.cell(
                row=kc_row, column=7, value=f'=IF(ABS(F{kc_row})<0.01,"OK","PERIKSA")'
            )
            status.border = border
            status.alignment = Alignment(horizontal='center')
            kc_row += 1

        for col, width in zip('ABCDEFG', (5, 15, 40, 18, 18, 14, 12)):
            ws_kontrol.column_dimensions[col].width = width

        # Save
        output = BytesIO()
        wb.save(output)
        from .naming import build_export_filename
        filename = build_export_filename(
            self.config.project_name, "Rincian AHSP", "xlsx",
            self.config.export_date,
        )
        if self._package_wb is not None:
            return None
        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def _write_pekerjaan_section_with_tracking(self, ws, start_row: int, section: Dict[str, Any], pekerjaan_refs: List[Dict]) -> int:
        """Write pekerjaan section and track E, F, G cell references."""
        pekerjaan = section.get('pekerjaan', {})
        groups = section.get('groups', [])
        totals = section.get('totals', {})
        border = self._get_thin_border()

        pek_name = pekerjaan.get('uraian') or pekerjaan.get('name', '')
        pek_kode = pekerjaan.get('kode', '')
        pek_header = f"{pek_kode} - {pek_name}" if pek_kode else pek_name
        
        # Pekerjaan header
        ws.cell(row=start_row, column=1, value=pek_header)
        ws.cell(row=start_row, column=1).font = Font(bold=True, size=11)
        ws.cell(row=start_row, column=1).fill = PatternFill('solid', fgColor='E0E7FF')
        start_row += 1

        # Sub-headers
        sub_headers = ['No', 'Uraian', 'Kode', 'Satuan', 'Koefisien', 'Harga Satuan', 'Jumlah Harga']
        for col_idx, header in enumerate(sub_headers, 1):
            cell = ws.cell(row=start_row, column=col_idx, value=header)
            cell.font = Font(bold=True, size=9)
            cell.fill = PatternFill('solid', fgColor='F3F4F6')
            cell.border = border
        start_row += 1

        subtotal_cells = []
        
        for group in groups:
            group_title = group.get('title', '')
            group_rows = group.get('rows', [])
            
            if not group_rows:
                continue
            
            # Group title
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=7)
            cell = ws.cell(row=start_row, column=1, value=group_title)
            cell.font = Font(bold=True, size=9, italic=True)
            cell.fill = PatternFill('solid', fgColor='FFF3CD')
            cell.border = border
            start_row += 1
            
            group_first_row = start_row
            
            for row_data in group_rows:
                for col_idx, val in enumerate(row_data, 1):
                    # WP Export K2/K3: write the canonical Decimal jumlah/koef/harga
                    # as real numbers — no =E*F formula, no locale re-parse.
                    if col_idx == 5:
                        cell = self._write_value_cell(ws, start_row, col_idx, val, '0.000000')
                    elif col_idx in (6, 7):
                        cell = self._write_value_cell(ws, start_row, col_idx, val, '#,##0.00')
                    else:
                        cell = ws.cell(row=start_row, column=col_idx, value=val)
                    cell.border = border
                start_row += 1

            group_last_row = start_row - 1

            # Subtotal (canonical backend value — not =SUM)
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
            cell = ws.cell(row=start_row, column=1, value=f"Subtotal {group.get('short_title', '')}")
            cell.font = Font(bold=True, size=9)
            cell.alignment = Alignment(horizontal='right')
            cell.border = border

            subtotal_cell = self._write_value_cell(ws, start_row, 7, group.get('subtotal'), '#,##0.00')
            subtotal_cell.font = Font(bold=True)
            subtotal_cell.border = border
            start_row += 1

        # Totals E, F, G — canonical backend values (no live formula).
        markup_pct = float(totals.get('markup_eff') or 0) if totals else 0.0
        e_val = totals.get('E') if totals else None
        f_val = totals.get('F') if totals else None
        g_val = totals.get('G') if totals else None

        # E row
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
        cell = ws.cell(row=start_row, column=1, value="Jumlah (E)")
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='right')
        cell.fill = PatternFill('solid', fgColor='E8F5E9')
        cell.border = border

        e_row = start_row
        cell = self._write_value_cell(ws, start_row, 7, e_val, '#,##0.00')
        cell.font = Font(bold=True)
        cell.fill = PatternFill('solid', fgColor='E8F5E9')
        cell.border = border
        start_row += 1

        # F row
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
        cell = ws.cell(row=start_row, column=1, value=f"Profit/Margin {markup_pct:.2f}% (F)")
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='right')
        cell.fill = PatternFill('solid', fgColor='FFF8E1')
        cell.border = border

        f_row = start_row
        cell = self._write_value_cell(ws, start_row, 7, f_val, '#,##0.00')
        cell.font = Font(bold=True)
        cell.fill = PatternFill('solid', fgColor='FFF8E1')
        cell.border = border
        start_row += 1

        # G row
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
        cell = ws.cell(row=start_row, column=1, value="Harga Satuan Pekerjaan (G = E + F)")
        cell.font = Font(bold=True, size=10)
        cell.alignment = Alignment(horizontal='right')
        cell.fill = PatternFill('solid', fgColor='BBDEFB')
        cell.border = border

        g_row = start_row
        cell = self._write_value_cell(ws, start_row, 7, g_val, '#,##0.00')
        cell.font = Font(bold=True, size=10)
        cell.fill = PatternFill('solid', fgColor='BBDEFB')
        cell.border = border
        start_row += 1

        # Track canonical values (for the Rekap sheet) AND the Rincian cell addresses
        # (for the Kontrol Kalkulasi audit sheet, which recomputes G = E + F by live
        # formula and compares it to the official backend value).
        pekerjaan_refs.append({
            'kode': pek_kode,
            'uraian': pek_name,
            'e_val': e_val,
            'f_val': f_val,
            'g_val': g_val,
            'e_cell': f"G{e_row}",
            'f_cell': f"G{f_row}",
            'g_cell': f"G{g_row}",
        })

        return start_row

    def _create_sheet(self, wb: Workbook, title: str, is_first: bool = False):
        sanitized = self._sanitize_title(title)
        # Dalam paket, wb.active hanya boleh dipakai oleh sheet pertama dari
        # dokumen PERTAMA. Tanpa penjagaan ini dokumen kedua menulis ulang ke
        # sheet yang sudah berisi merged cell -> "MergedCell is read-only".
        use_active = is_first and (self._package_wb is None or not self._package_first_used)
        if use_active:
            ws = wb.active
            ws.title = sanitized
            if self._package_wb is not None:
                self._package_first_used = True
        else:
            ws = wb.create_sheet(sanitized)
        return ws

    def _sanitize_title(self, title: str) -> str:
        invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
        for ch in invalid_chars:
            title = title.replace(ch, '_')
        return title[:31]

    @staticmethod
    def _is_numeric_format(fmt) -> bool:
        """A column number_format is numeric unless it is a text marker."""
        return bool(fmt) and str(fmt).strip() not in ('@', 'text', '')

    def _write_value_cell(self, ws, row: int, col: int, val, fmt=None):
        """Write a cell at the adapter→Excel boundary (WP Export K2/K3 contract).

        When the column carries a numeric number_format and the adapter passed a
        canonical Decimal/number, write a real Excel number (float) and stamp the
        format — never a locale string and never a live formula. Text columns and
        empty placeholders pass through unchanged.
        """
        if (
            self._is_numeric_format(fmt)
            and isinstance(val, (Decimal, int, float))
            and not isinstance(val, bool)
        ):
            cell = ws.cell(row=row, column=col, value=float(val))
            cell.number_format = str(fmt)
        else:
            cell = ws.cell(row=row, column=col, value=val)
        return cell

    def _write_table(self, ws, start_row: int, section: Dict[str, Any]) -> int:
        table_data = section.get('table_data') or {}
        headers = table_data.get('headers') or []
        rows = table_data.get('rows') or []
        column_formats = table_data.get('column_formats') or []
        hierarchy = section.get('hierarchy_levels') or {}
        row_types = section.get('row_types') or []
        border = self._get_thin_border()

        num_cols = len(headers)

        if headers:
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=start_row, column=col_idx, value=header)
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill('solid', fgColor='4472C4')
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')
            start_row += 1

        for row_idx, row in enumerate(rows):
            row_type = row_types[row_idx] if row_idx < len(row_types) else 'item'
            
            if row_type == 'category':
                # Category row - merge cells and apply styling
                cell = ws.cell(row=start_row, column=1, value=row[0] if row else '')
                cell.font = Font(bold=True)
                cell.fill = PatternFill('solid', fgColor='E8E8E8')
                cell.border = border
                
                # Merge cells from column 1 to last column
                if num_cols > 1:
                    ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=num_cols)
                
                # Apply border to merged area
                for col_idx in range(2, num_cols + 1):
                    ws.cell(row=start_row, column=col_idx).border = border
            else:
                # Normal row
                for col_idx, val in enumerate(row, 1):
                    fmt = column_formats[col_idx - 1] if col_idx - 1 < len(column_formats) else None
                    cell = self._write_value_cell(ws, start_row, col_idx, val, fmt)
                    cell.border = border
                    # Check if cell has multi-line content
                    has_newline = isinstance(val, str) and '\n' in val
                    # Right-align price column (last column)
                    if col_idx == num_cols:
                        cell.alignment = Alignment(horizontal='right', vertical='top', wrap_text=has_newline)
                    elif has_newline:
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                        
            level = hierarchy.get(row_idx, 0)
            if level > 0:
                ws.cell(row=start_row, column=1).alignment = Alignment(indent=level * 2)
            start_row += 1

        return start_row

    def _write_pekerjaan_section(self, ws, start_row: int, section: Dict[str, Any]) -> int:
        pekerjaan = section.get('pekerjaan', {})
        items = section.get('items', [])
        groups = section.get('groups', [])  # RincianAHSP uses groups
        border = self._get_thin_border()

        # Pekerjaan header - use 'uraian' or 'name'
        pek_name = pekerjaan.get('uraian') or pekerjaan.get('name', '')
        pek_kode = pekerjaan.get('kode', '')
        pek_header = f"{pek_kode} - {pek_name}" if pek_kode else pek_name
        
        ws.cell(row=start_row, column=1, value=pek_header)
        ws.cell(row=start_row, column=1).font = Font(bold=True, size=11)
        ws.cell(row=start_row, column=1).fill = PatternFill('solid', fgColor='E0E7FF')
        start_row += 1

        # Sub-headers
        sub_headers = ['No', 'Uraian', 'Kode', 'Satuan', 'Koefisien', 'Harga Satuan', 'Jumlah Harga']
        for col_idx, header in enumerate(sub_headers, 1):
            cell = ws.cell(row=start_row, column=col_idx, value=header)
            cell.font = Font(bold=True, size=9)
            cell.fill = PatternFill('solid', fgColor='F3F4F6')
            cell.border = border
        start_row += 1

        # Handle groups structure (from RincianAHSPAdapter)
        if groups:
            subtotal_cells = []  # Track subtotal row references for E formula
            
            for group in groups:
                group_title = group.get('title', '')
                group_rows = group.get('rows', [])
                
                if not group_rows:
                    continue
                
                # Group title row
                ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=7)
                cell = ws.cell(row=start_row, column=1, value=group_title)
                cell.font = Font(bold=True, size=9, italic=True)
                cell.fill = PatternFill('solid', fgColor='FFF3CD')  # Yellow-ish for section
                cell.border = border
                start_row += 1
                
                # Track row numbers for this group's detail rows (for subtotal SUM formula)
                group_first_row = start_row
                
                # Group detail rows (list of lists: [No, Uraian, Kode, Satuan, Koefisien, HargaSatuan, JumlahHarga])
                # Columns: E=Koefisien, F=Harga Satuan, G=Jumlah Harga (formula: E*F)
                for row_data in group_rows:
                    for col_idx, val in enumerate(row_data, 1):
                        cell = ws.cell(row=start_row, column=col_idx)
                        cell.border = border
                        
                        if col_idx == 7:
                            # Jumlah Harga = Koefisien (col 5) × Harga Satuan (col 6)
                            # Use formula instead of static value
                            cell.value = f"=E{start_row}*F{start_row}"
                            cell.number_format = '#,##0'
                        elif col_idx == 5:
                            # Koefisien - parse to number
                            cell.value = self._parse_number(val)
                            cell.number_format = '0.000000'
                        elif col_idx == 6:
                            # Harga Satuan - parse to number
                            cell.value = self._parse_number(val)
                            cell.number_format = '#,##0'
                        else:
                            cell.value = val
                    start_row += 1
                
                group_last_row = start_row - 1
                
                # Subtotal row with SUM formula
                ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
                cell = ws.cell(row=start_row, column=1, value=f"Subtotal {group.get('short_title', '')}")
                cell.font = Font(bold=True, size=9)
                cell.alignment = Alignment(horizontal='right')
                cell.border = border
                
                # Subtotal formula: SUM of Jumlah Harga column (G) for this group
                subtotal_cell = ws.cell(row=start_row, column=7)
                subtotal_cell.value = f"=SUM(G{group_first_row}:G{group_last_row})"
                subtotal_cell.font = Font(bold=True)
                subtotal_cell.border = border
                subtotal_cell.number_format = '#,##0'
                
                subtotal_cells.append(f"G{start_row}")
                start_row += 1

            # Total section (E, F, G) with formulas
            totals = section.get('totals', {})
            markup_pct = float(totals.get('markup_eff', '10.00').replace(',', '.')) if totals else 10.0
            
            # Jumlah E = SUM of all subtotals
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
            cell = ws.cell(row=start_row, column=1, value="Jumlah (E)")
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='right')
            cell.fill = PatternFill('solid', fgColor='E8F5E9')
            cell.border = border
            
            e_row = start_row
            e_formula = "=" + "+".join(subtotal_cells) if subtotal_cells else "=0"
            cell = ws.cell(row=start_row, column=7, value=e_formula)
            cell.font = Font(bold=True)
            cell.fill = PatternFill('solid', fgColor='E8F5E9')
            cell.border = border
            cell.number_format = '#,##0'
            start_row += 1
            
            # Profit/Margin F = E × markup%
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
            cell = ws.cell(row=start_row, column=1, value=f"Profit/Margin {markup_pct:.2f}% (F)")
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='right')
            cell.fill = PatternFill('solid', fgColor='FFF8E1')
            cell.border = border
            
            f_row = start_row
            f_formula = f"=G{e_row}*{markup_pct/100}"
            cell = ws.cell(row=start_row, column=7, value=f_formula)
            cell.font = Font(bold=True)
            cell.fill = PatternFill('solid', fgColor='FFF8E1')
            cell.border = border
            cell.number_format = '#,##0'
            start_row += 1
            
            # HSP G = E + F
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=6)
            cell = ws.cell(row=start_row, column=1, value="Harga Satuan Pekerjaan (G = E + F)")
            cell.font = Font(bold=True, size=10)
            cell.alignment = Alignment(horizontal='right')
            cell.fill = PatternFill('solid', fgColor='BBDEFB')
            cell.border = border
            
            g_formula = f"=G{e_row}+G{f_row}"
            cell = ws.cell(row=start_row, column=7, value=g_formula)
            cell.font = Font(bold=True, size=10)
            cell.fill = PatternFill('solid', fgColor='BBDEFB')
            cell.border = border
            cell.number_format = '#,##0'
            start_row += 1
        else:
            # Fallback: old items structure
            for idx, item in enumerate(items, 1):
                ws.cell(row=start_row, column=1, value=idx).border = border
                ws.cell(row=start_row, column=2, value=item.get('uraian', '')).border = border
                ws.cell(row=start_row, column=3, value=item.get('kode', '')).border = border
                ws.cell(row=start_row, column=4, value=item.get('satuan', '')).border = border
                ws.cell(row=start_row, column=5, value=item.get('koefisien', '')).border = border
                ws.cell(row=start_row, column=6, value=item.get('harga_satuan', '')).border = border
                ws.cell(row=start_row, column=7, value=item.get('jumlah_harga', '')).border = border
                start_row += 1

        return start_row
    
    def _parse_number(self, val):
        """Wrapper for global parse_number function - for consistency across all Excel exports."""
        return parse_number(val, default=0)

    def _apply_column_widths(self, ws, widths: List[float] | None):
        if not widths:
            return
        for idx, w in enumerate(widths, 1):
            col_letter = get_column_letter(idx)
            ws.column_dimensions[col_letter].width = self._mm_to_excel_width(w)

    def _mm_to_excel_width(self, mm_value: float | None) -> float:
        if mm_value is None:
            return 10
        chars = mm_value / 2.5
        return max(8, min(chars, 100))

    # =========================================================================
    # PROFESSIONAL EXPORT FOR JADWAL PEKERJAAN REKAP
    # =========================================================================

    def export_professional(self, data: Dict[str, Any]):
        """
        Export professionally styled Excel for Rekap reports.
        
        Creates 3 sheets:
        - Sheet 1: Cover (Project Info + Progress Summary)
        - Sheet 2: Kurva S (Full data table + Native LineChart)
        - Sheet 3: Input Progress-Gantt (SSOT for input values)
        """
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError('openpyxl belum terpasang. Install via "pip install openpyxl".')

        import time
        start_time = time.time()
        logger.debug("[ExcelExporter] Starting professional export...")

        wb = Workbook()
        report_type = data.get('report_type', 'rekap')

        # Extract data
        project_info = data.get('project_info', {})
        summary = data.get('summary', {})
        kurva_s_data = data.get('kurva_s_data', [])
        planned_pages = data.get('planned_pages', [])
        actual_pages = data.get('actual_pages', [])
        weekly_columns = data.get('weekly_columns', [])
        if data.get('canonical_base_rows'):
            # Canonical payload supersedes page-shaped presentation data. The
            # parser below remains only for backward-compatible callers.
            planned_pages = []
            actual_pages = []
        
        # Build hierarchy rows from planned_pages
        # Note: Adapter returns [uraian, volume, satuan, week1, week2, ...]
        # Only 3 static columns, no code/harga/total/bobot
        base_rows = []
        seen_uraian = set()
        planned_map = {}
        actual_map = {}
        
        # Extract rows from planned_pages (table_data.rows contains materialized rows)
        logger.debug("[ExcelExporter] planned_pages count: %s", len(planned_pages))
        for page_idx, page in enumerate(planned_pages):
            table_data = page.get('table_data', {})
            page_rows = table_data.get('rows', [])
            headers = table_data.get('headers', [])
            logger.debug("[ExcelExporter] Page %s: %s rows, headers: %s...", page_idx, len(page_rows), headers[:5])
            
            for row_idx, row in enumerate(page_rows):
                # Row is a list [uraian, volume, satuan, week1, week2, ...]
                if isinstance(row, list) and len(row) >= 3:
                    uraian = row[0] if len(row) > 0 else ''
                    volume_str = row[1] if len(row) > 1 else ''
                    satuan = row[2] if len(row) > 2 else ''
                    
                    # Skip if empty uraian or already seen
                    if not uraian or uraian in seen_uraian:
                        continue
                    seen_uraian.add(uraian)
                    
                    # Generate a unique ID for this row
                    pek_id = len(base_rows) + 1  # 1-based ID
                    
                    # Build row dict with proper field names
                    row_dict = {
                        'id': pek_id,  # CRITICAL: needed for progress lookup
                        'type': 'pekerjaan',
                        'name': uraian,
                        'volume': volume_str,  # Keep original string for display
                        'volume_num': safe_float(volume_str, 0),  # Numeric for calculations
                        'satuan': satuan,
                        # These will be calculated if needed
                        'harga_satuan': 0,
                        'total_harga': 0,
                        'bobot': 0,
                    }
                    base_rows.append(row_dict)
                    
                    # Debug first few rows
                    if pek_id <= 3:
                        logger.debug("[ExcelExporter] Row %s: uraian='%s...', volume_str='%s', satuan='%s'", pek_id, uraian[:30], volume_str, satuan)
                    
                    # Extract week progress (columns after satuan are weeks)
                    week_values = row[3:] if len(row) > 3 else []  # Weeks start at column 4 (index 3)
                    if week_values:
                        # Build week map: {week_num: value}
                        # Progress values in adapter are formatted as '0,00%' or '50,00%'
                        week_dict = {}
                        for i, v in enumerate(week_values):
                            week_num = i + 1
                            parsed_val = safe_float(v, 0)
                            # safe_float already handles % conversion (divides by 100)
                            # But progress values from adapter are already percentages (0-100)
                            # Need to store as 0-100 for later /100 conversion
                            if parsed_val <= 1 and '%' in str(v):
                                # Already converted to 0-1 by safe_float, convert back to 0-100
                                week_dict[week_num] = parsed_val * 100
                            else:
                                week_dict[week_num] = parsed_val
                        planned_map[pek_id] = week_dict
                        logger.debug("[ExcelExporter] Row %s planned: %s...", pek_id, list(week_dict.items())[:3])
        
        # Extract from actual_pages similarly (using same uraian matching)
        seen_actual_uraian = set()
        for page_idx, page in enumerate(actual_pages):
            table_data = page.get('table_data', {})
            page_rows = table_data.get('rows', [])
            for row_idx, row in enumerate(page_rows):
                if isinstance(row, list) and len(row) > 3:
                    uraian = row[0] if row else ''
                    if not uraian or uraian in seen_actual_uraian:
                        continue
                    seen_actual_uraian.add(uraian)
                    
                    # Find matching pek_id from base_rows
                    pek_id = None
                    for br in base_rows:
                        if br.get('name') == uraian:
                            pek_id = br.get('id')
                            break
                    
                    if pek_id:
                        week_values = row[3:]
                        if week_values:
                            week_dict = {}
                            for i, v in enumerate(week_values):
                                week_num = i + 1
                                parsed_val = safe_float(v, 0)
                                if parsed_val <= 1 and '%' in str(v):
                                    week_dict[week_num] = parsed_val * 100
                                else:
                                    week_dict[week_num] = parsed_val
                            actual_map[pek_id] = week_dict

        # The active professional path carries stable pekerjaan identity and all
        # week chunks directly from the adapter. Keep the page parser above only
        # as a backward-compatible fallback for older callers.
        canonical_rows = data.get('canonical_base_rows')
        if canonical_rows:
            base_rows = []
            for raw in canonical_rows:
                row_type = raw.get('type', '')
                if row_type == 'pekerjaan':
                    pekerjaan_id = raw.get('pekerjaan_id')
                    volume_display = raw.get('volume_display', 0)
                    base_rows.append({
                        'id': pekerjaan_id,
                        'pekerjaan_id': pekerjaan_id,
                        'type': 'pekerjaan',
                        'kode': raw.get('kode', ''),
                        'name': raw.get('uraian', ''),
                        'volume': volume_display,
                        'volume_num': safe_float(volume_display, 0),
                        'satuan': raw.get('unit', ''),
                        'harga_satuan': 0,
                        'total_harga': 0,
                        'bobot': 0,
                    })
                else:
                    base_rows.append({
                        'type': row_type,
                        'kode': raw.get('kode', ''),
                        'name': raw.get('uraian', ''),
                    })

            def _nest_progress_map(flat_map):
                nested = {}
                for key, value in (flat_map or {}).items():
                    if not isinstance(key, tuple) or len(key) != 2:
                        continue
                    pekerjaan_id, week_number = key
                    nested.setdefault(pekerjaan_id, {})[week_number] = value
                return nested

            planned_map = _nest_progress_map(data.get('canonical_planned_map'))
            actual_map = _nest_progress_map(data.get('canonical_actual_map'))

        logger.debug("[ExcelExporter] Data: %s rows, %s weeks, planned_map: %s, actual_map: %s", len(base_rows), len(weekly_columns), len(planned_map), len(actual_map))

        # Merge harga data from base_rows_with_harga (from ExportManager)
        base_rows_with_harga = data.get('base_rows_with_harga', [])
        if base_rows_with_harga:
            logger.debug("[ExcelExporter] Merging %s rows with harga data...", len(base_rows_with_harga))
            # Prefer stable pekerjaan_id; uraian remains a legacy fallback.
            harga_lookup = {}
            harga_lookup_by_id = {}
            for hrow in base_rows_with_harga:
                pekerjaan_id = hrow.get('pekerjaan_id')
                if pekerjaan_id:
                    harga_lookup_by_id[pekerjaan_id] = hrow
                uraian = hrow.get('uraian', '')
                if uraian:
                    harga_lookup[uraian] = hrow
            
            # Update base_rows with harga data
            for brow in base_rows:
                uraian = brow.get('name', '')
                hdata = harga_lookup_by_id.get(brow.get('pekerjaan_id')) or harga_lookup.get(uraian)
                if hdata:
                    brow['satuan'] = hdata.get('satuan', brow.get('satuan', ''))
                    brow['harga_satuan'] = hdata.get('harga_satuan', 0)
                    brow['total_harga'] = hdata.get('total_harga', 0)
                    brow['volume_num'] = hdata.get('volume', brow.get('volume_num', 0))
                    logger.debug("[ExcelExporter] Merged harga for: %s... satuan=%s, harga=%.0f", uraian[:30], brow['satuan'], brow['harga_satuan'])

        # Build sheets in order
        # 1. Input Progress-Gantt FIRST (SSOT)
        ws_gantt = wb.active
        ws_gantt.title = "Input Progress-Gantt"
        gantt_ranges = self._build_input_progress_sheet(
            ws_gantt, base_rows, weekly_columns, planned_map, actual_map
        )

        # 2. Kurva S (references Input Progress-Gantt)
        ws_kurva = wb.create_sheet("Kurva S")
        kurva_ranges = self._build_kurva_s_sheet(
            ws_kurva, base_rows, weekly_columns, planned_map, actual_map,
            kurva_s_data, gantt_ranges
        )

        # 3. Cover sheet
        ws_cover = wb.create_sheet("Cover", 0)  # Insert at beginning
        self._build_cover_sheet(ws_cover, project_info, summary, kurva_ranges)

        logger.debug("[ExcelExporter] Workbook built in %.2fs", time.time() - start_time)

        # Save to response
        output = BytesIO()
        wb.save(output)

        from .naming import build_export_filename
        filename = build_export_filename(
            self.config.project_name, report_type, "xlsx",
            self.config.export_date,
        )

        logger.info("[ExcelExporter] Total export time: %.2fs", time.time() - start_time)

        return self._create_response(
            output.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def _build_cover_sheet(self, ws, project_info: Dict, summary: Dict, kurva_ranges: Dict):
        """Build Cover sheet with project info and cross-sheet formulas."""
        border = self._get_thin_border()
        
        # Column widths
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 5
        ws.column_dimensions['D'].width = 45
        ws.column_dimensions['E'].width = 8

        # Title
        title_row = 6
        ws.merge_cells(f'B{title_row}:D{title_row}')
        ws[f'B{title_row}'] = 'LAPORAN REKAPITULASI'
        ws[f'B{title_row}'].font = Font(size=18, bold=True, color=COLORS['PRIMARY'])
        ws[f'B{title_row}'].alignment = Alignment(horizontal='center')

        ws.merge_cells(f'B{title_row+1}:D{title_row+1}')
        ws[f'B{title_row+1}'] = 'JADWAL PEKERJAAN'
        ws[f'B{title_row+1}'].font = Font(size=14, bold=True, color=COLORS['PRIMARY'])
        ws[f'B{title_row+1}'].alignment = Alignment(horizontal='center')

        # Decorative line
        ws.merge_cells(f'B{title_row+3}:D{title_row+3}')
        ws[f'B{title_row+3}'] = '────────────────────────────────────'
        ws[f'B{title_row+3}'].font = Font(size=8, color=COLORS['PRIMARY'])
        ws[f'B{title_row+3}'].alignment = Alignment(horizontal='center')

        # Project Name
        project_name = project_info.get('name', project_info.get('nama', '-'))
        ws.merge_cells(f'B{title_row+5}:D{title_row+5}')
        ws[f'B{title_row+5}'] = project_name
        ws[f'B{title_row+5}'].font = Font(size=16, bold=True)
        ws[f'B{title_row+5}'].alignment = Alignment(horizontal='center')

        # Project details
        details_start = title_row + 8
        lokasi = project_info.get('lokasi', '-')
        pemilik = project_info.get('nama_client', project_info.get('owner', '-'))
        sumber_dana = project_info.get('sumber_dana', '-')
        anggaran = kurva_ranges.get('total_harga', 0)
        
        from datetime import date
        
        details = [
            ('Lokasi', lokasi),
            ('Pemilik', pemilik),
            ('Sumber Dana', sumber_dana),
            ('Anggaran', f"Rp {anggaran:,.0f}" if anggaran else 'Rp 0'),
            ('Tanggal Export', date.today().strftime('%d/%m/%Y')),
            ('Jumlah Pekerjaan', f"{kurva_ranges.get('pekerjaan_count', 0)} item"),
        ]

        for idx, (label, value) in enumerate(details):
            row = details_start + idx
            ws[f'B{row}'] = label
            ws[f'B{row}'].font = Font(bold=True)
            ws[f'B{row}'].alignment = Alignment(horizontal='right')
            ws[f'C{row}'] = ':'
            ws[f'C{row}'].alignment = Alignment(horizontal='center')
            ws[f'D{row}'] = value

        # Progress Summary section
        summary_start = details_start + 8
        ws.merge_cells(f'B{summary_start}:D{summary_start}')
        ws[f'B{summary_start}'] = 'RINGKASAN PROGRESS'
        ws[f'B{summary_start}'].font = Font(size=14, bold=True, color=COLORS['PRIMARY'])
        ws[f'B{summary_start}'].alignment = Alignment(horizontal='center')
        ws[f'B{summary_start}'].fill = PatternFill('solid', fgColor=COLORS['SUBHEADER_BG'])

        # Progress formulas (cross-sheet reference)
        summary_data = [
            ('Progress Rencana', kurva_ranges.get('final_planned_ref', '0')),
            ('Progress Realisasi', kurva_ranges.get('final_actual_ref', '0')),
            ('Deviasi', kurva_ranges.get('deviation_ref', '0')),
        ]

        for idx, (label, formula_ref) in enumerate(summary_data):
            row = summary_start + 2 + idx
            ws[f'B{row}'] = label
            ws[f'B{row}'].font = Font(bold=True)
            ws[f'B{row}'].alignment = Alignment(horizontal='right')
            ws[f'B{row}'].border = border
            ws[f'C{row}'] = ':'
            ws[f'C{row}'].alignment = Alignment(horizontal='center')
            ws[f'C{row}'].border = border
            ws[f'D{row}'] = formula_ref
            ws[f'D{row}'].number_format = '0.00%'
            ws[f'D{row}'].border = border

        logger.debug("[ExcelExporter] Cover sheet created")

    def _build_input_progress_sheet(self, ws, rows: List[Dict], weekly_columns: List[Dict],
                                     planned_map: Dict, actual_map: Dict) -> Dict:
        """Build Input Progress-Gantt sheet as SSOT for input values."""
        border = self._get_thin_border()
        
        gantt_ranges = {
            'pekerjaan_rows': [],
            'week_start_col': 4,
            'header_row': 1
        }

        if not rows or not weekly_columns:
            ws['A1'] = 'Tidak ada data pekerjaan'
            return gantt_ranges

        fixed_cols = 3
        week_start_col = fixed_cols + 1
        week_count = len(weekly_columns)
        total_col = week_start_col + week_count

        gantt_ranges['week_start_col'] = week_start_col

        # Column widths
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 10
        for i in range(week_start_col, total_col + 1):
            ws.column_dimensions[get_column_letter(i)].width = 8

        # Header row
        header_row = 1
        gantt_ranges['header_row'] = header_row

        headers = ['No', 'Uraian Pekerjaan', 'Bobot']
        for col in weekly_columns:
            headers.append(col.get('label', f"W{col.get('week', '')}"))
        headers.append('Total')

        for idx, header in enumerate(headers):
            col_num = idx + 1
            cell = ws.cell(row=header_row, column=col_num, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # Freeze panes
        ws.freeze_panes = f'{get_column_letter(fixed_cols + 1)}2'

        # Calculate total harga for bobot
        total_harga_project = sum(
            safe_float(r.get('total_harga', 0) or 0)
            for r in rows if r.get('type') == 'pekerjaan'
        )

        # Process rows
        current_row = 2
        pekerjaan_counter = 0

        for item in rows:
            item_type = item.get('type', '')
            item_id = item.get('id')

            if item_type == 'pekerjaan':
                pekerjaan_counter += 1
                planned_row = current_row
                actual_row = current_row + 1

                gantt_ranges['pekerjaan_rows'].append({
                    'id': item_id,
                    'planned_row': planned_row,
                    'actual_row': actual_row
                })

                # Merge fixed columns
                for c in range(1, fixed_cols + 1):
                    ws.merge_cells(
                        start_row=planned_row, start_column=c,
                        end_row=actual_row, end_column=c
                    )

                # No
                cell = ws.cell(row=planned_row, column=1, value=pekerjaan_counter)
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border

                # Uraian
                cell = ws.cell(row=planned_row, column=2, value=item.get('name', item.get('uraian', '')))
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                cell.border = border

                # Bobot (calculated value)
                total_harga = safe_float(item.get('total_harga', 0) or 0)
                bobot = total_harga / total_harga_project if total_harga_project > 0 else 0
                cell = ws.cell(row=planned_row, column=3, value=bobot)
                cell.number_format = '0.00%'
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border

                # Week columns - Planned row (direct input values)
                for week_idx, week_col in enumerate(weekly_columns):
                    col_num = week_start_col + week_idx
                    week_key = week_col.get('week', week_idx + 1)
                    planned_value = 0
                    
                    if item_id and item_id in planned_map:
                        week_progress = planned_map[item_id]
                        if isinstance(week_progress, dict):
                            planned_value = safe_float(week_progress.get(week_key, 0) or 0)

                    cell = ws.cell(row=planned_row, column=col_num, value=planned_value / 100 if planned_value else 0)
                    cell.number_format = '0.0%'
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')
                    if planned_value > 0:
                        cell.fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])

                # Week columns - Actual row (direct input values)
                for week_idx, week_col in enumerate(weekly_columns):
                    col_num = week_start_col + week_idx
                    week_key = week_col.get('week', week_idx + 1)
                    actual_value = 0
                    
                    if item_id and item_id in actual_map:
                        week_progress = actual_map[item_id]
                        if isinstance(week_progress, dict):
                            actual_value = safe_float(week_progress.get(week_key, 0) or 0)

                    cell = ws.cell(row=actual_row, column=col_num, value=actual_value / 100 if actual_value else 0)
                    cell.number_format = '0.0%'
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')
                    if actual_value > 0:
                        cell.fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])

                # Total column (merged)
                ws.merge_cells(
                    start_row=planned_row, start_column=total_col,
                    end_row=actual_row, end_column=total_col
                )
                planned_total = sum(
                    Decimal(str((planned_map.get(item_id) or {}).get(
                        week_col.get('week', week_idx + 1), 0
                    ) or 0))
                    for week_idx, week_col in enumerate(weekly_columns)
                ) / Decimal('100')
                actual_total = sum(
                    Decimal(str((actual_map.get(item_id) or {}).get(
                        week_col.get('week', week_idx + 1), 0
                    ) or 0))
                    for week_idx, week_col in enumerate(weekly_columns)
                ) / Decimal('100')
                cell = ws.cell(
                    row=planned_row,
                    column=total_col,
                    value=float(planned_total + actual_total),
                )
                cell.number_format = '0.0%'
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border

                # Apply borders to actual row cells
                for c in range(1, fixed_cols + 1):
                    ws.cell(row=actual_row, column=c).border = border
                ws.cell(row=actual_row, column=total_col).border = border

                current_row += 2

            else:
                # Klasifikasi / Sub-klasifikasi
                ws.merge_cells(
                    start_row=current_row, start_column=2,
                    end_row=current_row, end_column=total_col
                )
                cell = ws.cell(row=current_row, column=2, value=item.get('name', item.get('uraian', '')))
                cell.font = Font(bold=True)
                cell.border = border

                if item_type == 'klasifikasi':
                    cell.fill = PatternFill('solid', fgColor=COLORS['KLASIFIKASI_BG'])
                elif item_type in ('sub-klasifikasi', 'sub_klasifikasi'):
                    cell.fill = PatternFill('solid', fgColor=COLORS['SUB_KLASIFIKASI_BG'])
                    cell.alignment = Alignment(indent=2)

                ws.cell(row=current_row, column=1).border = border
                current_row += 1

        logger.debug("[ExcelExporter] Input Progress-Gantt sheet created with %s pekerjaan", len(gantt_ranges['pekerjaan_rows']))
        return gantt_ranges

    def _build_kurva_s_sheet(self, ws, rows: List[Dict], weekly_columns: List[Dict],
                              planned_map: Dict, actual_map: Dict,
                              kurva_s_data: List[Dict], gantt_ranges: Dict,
                              title_text: str = 'KURVA S - RINCIAN PROGRESS',
                              max_week_num: int = None) -> Dict:
        """
        Build Kurva S sheet with canonical backend values and a native LineChart.
        
        Args:
            ws: Worksheet to build on
            rows: List of row data (pekerjaan, etc)
            weekly_columns: List of weekly column definitions
            planned_map: Dict mapping (pek_id, week) -> progress
            actual_map: Dict mapping (pek_id, week) -> progress
            kurva_s_data: List of kurva s data points for chart
            gantt_ranges: Dict with gantt sheet references
            title_text: Title to show at top of sheet (default: 'KURVA S - RINCIAN PROGRESS')
            max_week_num: If set, only show weeks up to this number (for monthly)
        """
        border = self._get_thin_border()

        kurva_ranges = {
            'final_planned_ref': '0',
            'final_actual_ref': '0',
            'deviation_ref': '0',
            'total_harga': 0,
            'pekerjaan_count': 0
        }

        if not rows or not weekly_columns:
            ws['A1'] = 'Tidak ada data'
            return kurva_ranges

        # Filter weekly_columns by max_week_num if specified
        if max_week_num is not None:
            weekly_columns = [col for col in weekly_columns 
                              if col.get('week', col.get('week_number', 0)) <= max_week_num]
            if not weekly_columns:
                ws['A1'] = 'Tidak ada data minggu'
                return kurva_ranges

        # Columns: No, Uraian, Volume, Satuan, Harga Satuan, Total Harga, Bobot, W1...Wn, Total
        fixed_col_count = 7
        week_start_col = fixed_col_count + 1
        week_count = len(weekly_columns)
        total_col = week_start_col + week_count

        # Column widths - use standardized dimensions
        ws.column_dimensions['A'].width = 6   # No
        ws.column_dimensions['B'].width = 40  # Uraian Pekerjaan (wider for text)
        ws.column_dimensions['C'].width = 10  # Volume
        ws.column_dimensions['D'].width = 8   # Satuan
        ws.column_dimensions['E'].width = 14  # Harga Satuan
        ws.column_dimensions['F'].width = 14  # Total Harga
        ws.column_dimensions['G'].width = DIMENSIONS['WEEK_COL_WIDTH']  # W0 column (same as weeks)
        # Week columns: standardized width to fit "Week XX"
        for i in range(week_start_col, total_col + 1):
            ws.column_dimensions[get_column_letter(i)].width = DIMENSIONS['WEEK_COL_WIDTH']

        # Title - use title_text parameter
        ws.merge_cells(f'A1:{get_column_letter(total_col)}1')
        ws['A1'] = title_text
        ws['A1'].font = Font(size=14, bold=True, color=COLORS['PRIMARY'])
        ws['A1'].alignment = Alignment(horizontal='center')

        # Header row
        header_row = 3
        headers = ['No', 'Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan', 'Total Harga', 'Bobot']
        for col in weekly_columns:
            headers.append(col.get('label', f"W{col.get('week', '')}"))
        headers.append('Total')

        for idx, header in enumerate(headers):
            col_num = idx + 1
            cell = ws.cell(row=header_row, column=col_num, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[header_row].height = DIMENSIONS['HEADER_ROW_HEIGHT']

        # Freeze panes
        ws.freeze_panes = 'C4'

        pekerjaan_items = [item for item in rows if item.get('type') == 'pekerjaan']
        total_harga_project = sum(
            (Decimal(str(item.get('total_harga', 0) or 0)) for item in pekerjaan_items),
            Decimal('0'),
        )
        kurva_by_week = {
            point.get('week'): point
            for point in kurva_s_data
            if point.get('week') is not None
        }

        # Process rows
        current_row = header_row + 1
        pekerjaan_counter = 0
        pekerjaan_row_data = []
        first_pekerjaan_row = None
        last_pekerjaan_row = None

        for item in rows:
            item_type = item.get('type', '')
            # Consistent with SSOT: try 'id' first, then 'pekerjaan_id', then 'pk'
            item_id = item.get('id') or item.get('pekerjaan_id') or item.get('pk')

            if item_type == 'pekerjaan':
                pekerjaan_counter += 1
                planned_row = current_row
                actual_row = current_row + 1

                if first_pekerjaan_row is None:
                    first_pekerjaan_row = planned_row
                last_pekerjaan_row = actual_row

                total_harga = Decimal(str(item.get('total_harga', 0) or 0))
                bobot = (
                    total_harga / total_harga_project
                    if total_harga_project > 0 else Decimal('0')
                )
                pekerjaan_row_data.append({
                    'planned': planned_row,
                    'actual': actual_row,
                    'id': item_id,
                    'total_harga': total_harga,
                    'bobot': bobot,
                })

                # Merge fixed columns
                for c in range(1, fixed_col_count + 1):
                    ws.merge_cells(
                        start_row=planned_row, start_column=c,
                        end_row=actual_row, end_column=c
                    )

                # No
                cell = ws.cell(row=planned_row, column=1, value=item.get('kode', pekerjaan_counter))
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Uraian
                cell = ws.cell(row=planned_row, column=2, value=item.get('name', item.get('uraian', '')))
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                cell.border = border
                cell.font = Font(size=8)

                # Volume - use volume_num which is already parsed numeric
                volume = item.get('volume_num', 0)
                if volume == 0:
                    # Fallback: try parsing volume string
                    volume = safe_float(item.get('volume', 0) or 0)
                cell = ws.cell(row=planned_row, column=3, value=volume)
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Satuan
                cell = ws.cell(row=planned_row, column=4, value=item.get('satuan', '-'))
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Harga Satuan
                harga_satuan = safe_float(item.get('harga_satuan', 0) or 0)
                cell = ws.cell(row=planned_row, column=5, value=harga_satuan)
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Canonical backend total, not a spreadsheet recomputation.
                cell = ws.cell(row=planned_row, column=6, value=float(total_harga))
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                cell = ws.cell(row=planned_row, column=7, value=float(bobot))
                cell.number_format = '0.00%'
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Preserve planned/actual as separate weighted series.
                planned_week_values = []
                actual_week_values = []

                # Week columns - planned weighted values from canonical input.
                for week_idx in range(week_count):
                    col_num = week_start_col + week_idx
                    week_key = weekly_columns[week_idx].get(
                        'week', weekly_columns[week_idx].get('week_number', week_idx + 1)
                    )
                    planned_fraction = Decimal(str(
                        (planned_map.get(item_id) or {}).get(week_key, 0) or 0
                    )) / Decimal('100')
                    weighted_value = bobot * planned_fraction
                    planned_week_values.append(weighted_value)
                    cell = ws.cell(row=planned_row, column=col_num, value=float(weighted_value))
                    cell.number_format = '0.00%;-0.00%;"-"'
                    if planned_fraction > 0:
                        cell.fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')
                    cell.font = Font(size=8)

                # Week columns - actual weighted values from canonical input.
                for week_idx in range(week_count):
                    col_num = week_start_col + week_idx
                    week_key = weekly_columns[week_idx].get(
                        'week', weekly_columns[week_idx].get('week_number', week_idx + 1)
                    )
                    actual_fraction = Decimal(str(
                        (actual_map.get(item_id) or {}).get(week_key, 0) or 0
                    )) / Decimal('100')
                    weighted_value = bobot * actual_fraction
                    actual_week_values.append(weighted_value)
                    cell = ws.cell(row=actual_row, column=col_num, value=float(weighted_value))
                    cell.number_format = '0.00%;-0.00%;"-"'
                    if actual_fraction > 0:
                        cell.fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')
                    cell.font = Font(size=8)

                # Total column - SEPARATE cells for planned and actual rows (not merged)
                # Total for Planned row
                cell_planned = ws.cell(
                    row=planned_row,
                    column=total_col,
                    value=float(sum(planned_week_values, Decimal('0'))),
                )
                cell_planned.number_format = '0.00%;-0.00%;"-"'
                cell_planned.alignment = Alignment(horizontal='center', vertical='center')
                cell_planned.border = border
                cell_planned.font = Font(size=8)
                cell_planned.fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])
                
                # Total for Actual row
                cell_actual = ws.cell(
                    row=actual_row,
                    column=total_col,
                    value=float(sum(actual_week_values, Decimal('0'))),
                )
                cell_actual.number_format = '0.00%;-0.00%;"-"'
                cell_actual.alignment = Alignment(horizontal='center', vertical='center')
                cell_actual.border = border
                cell_actual.font = Font(size=8)
                cell_actual.fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])

                # Apply borders to actual row
                for c in range(1, fixed_col_count + 1):
                    ws.cell(row=actual_row, column=c).border = border

                # Set reduced row heights for pekerjaan (40% smaller than default)
                kurva_row_height = DIMENSIONS['PEKERJAAN_ROW_HEIGHT'] * 0.6  # 60% of original
                ws.row_dimensions[planned_row].height = kurva_row_height
                ws.row_dimensions[actual_row].height = kurva_row_height

                current_row += 2

            else:
                # Klasifikasi / Sub-klasifikasi
                ws.merge_cells(
                    start_row=current_row, start_column=2,
                    end_row=current_row, end_column=total_col
                )
                cell = ws.cell(row=current_row, column=2, value=item.get('name', item.get('uraian', '')))
                cell.font = Font(bold=True)
                cell.border = border

                if item_type == 'klasifikasi':
                    cell.fill = PatternFill('solid', fgColor=COLORS['KLASIFIKASI_BG'])
                elif item_type in ('sub-klasifikasi', 'sub_klasifikasi'):
                    cell.fill = PatternFill('solid', fgColor=COLORS['SUB_KLASIFIKASI_BG'])
                    cell.alignment = Alignment(indent=2)

                ws.cell(row=current_row, column=1).border = border
                current_row += 1

        # TOTAL ROW
        total_row = current_row + 1
        
        ws.cell(row=total_row, column=2, value='TOTAL')
        ws.cell(row=total_row, column=2).font = Font(bold=True)
        ws.cell(row=total_row, column=2).fill = PatternFill('solid', fgColor=COLORS['TOTAL_BG'])
        ws.cell(row=total_row, column=2).border = border

        cell = ws.cell(row=total_row, column=6, value=float(total_harga_project))
        cell.number_format = '#,##0.00'
        cell.font = Font(bold=True)
        cell.border = border

        total_bobot = sum((p['bobot'] for p in pekerjaan_row_data), Decimal('0'))
        cell = ws.cell(row=total_row, column=7, value=float(total_bobot))
        cell.number_format = '0.00%'
        cell.font = Font(bold=True)
        cell.border = border

        # Apply borders to total row
        for c in range(1, total_col + 1):
            ws.cell(row=total_row, column=c).border = border
            if week_start_col <= c < total_col:
                ws.cell(row=total_row, column=c).fill = PatternFill('solid', fgColor=COLORS['TOTAL_BG'])

        # Calculate total harga for cover
        kurva_ranges['total_harga'] = float(total_harga_project)
        kurva_ranges['pekerjaan_count'] = len(pekerjaan_row_data)

        # SUMMARY ROWS
        summary_start = total_row + 2

        # Note
        ws.merge_cells(f'A{summary_start}:{get_column_letter(fixed_col_count)}{summary_start}')
        ws[f'A{summary_start}'] = 'DATA UNTUK GRAFIK KURVA S:'
        ws[f'A{summary_start}'].font = Font(bold=True, italic=True)

        data_start_row = summary_start + 1

        # ==== ADD WEEK 0 COLUMN ====
        # Week 0 is in the column just before week_start_col (column 7 = fixed_col_count)
        # We'll use column 7 (G) for Week 0
        week0_col = fixed_col_count  # Column G
        
        # Week 0 header
        ws.cell(row=header_row, column=week0_col, value='W0')
        ws.cell(row=header_row, column=week0_col).font = Font(bold=True, color='FFFFFF', size=8)
        ws.cell(row=header_row, column=week0_col).fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
        ws.cell(row=header_row, column=week0_col).alignment = Alignment(horizontal='center')
        ws.cell(row=header_row, column=week0_col).border = border

        # Progress Mingguan Rencana
        ws.cell(row=data_start_row, column=2, value='Progress Mingguan Rencana')
        ws.cell(row=data_start_row, column=2).font = Font(bold=True)
        ws.cell(row=data_start_row, column=2).fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])
        ws.cell(row=data_start_row, column=2).border = border
        # Week 0 value = 0
        ws.cell(row=data_start_row, column=week0_col, value=0)
        ws.cell(row=data_start_row, column=week0_col).number_format = '0.00%'
        ws.cell(row=data_start_row, column=week0_col).border = border

        cumulative_planned_values = []
        cumulative_actual_values = []
        previous_planned = Decimal('0')
        for week_idx in range(week_count):
            col_num = week_start_col + week_idx
            week_key = weekly_columns[week_idx].get(
                'week', weekly_columns[week_idx].get('week_number', week_idx + 1)
            )
            point = kurva_by_week.get(week_key, {})
            cumulative_planned = Decimal(str(point.get('planned', 0) or 0)) / Decimal('100')
            cumulative_actual = Decimal(str(point.get('actual', 0) or 0)) / Decimal('100')
            cumulative_planned_values.append(cumulative_planned)
            cumulative_actual_values.append(cumulative_actual)
            weekly_planned = cumulative_planned - previous_planned
            previous_planned = cumulative_planned
            cell = ws.cell(row=data_start_row, column=col_num, value=float(weekly_planned))
            cell.number_format = '0.00%'
            cell.border = border
            cell.font = Font(size=8)

        # Progress Mingguan Realisasi
        ws.cell(row=data_start_row + 1, column=2, value='Progress Mingguan Realisasi')
        ws.cell(row=data_start_row + 1, column=2).font = Font(bold=True)
        ws.cell(row=data_start_row + 1, column=2).fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])
        ws.cell(row=data_start_row + 1, column=2).border = border
        # Week 0 value = 0
        ws.cell(row=data_start_row + 1, column=week0_col, value=0)
        ws.cell(row=data_start_row + 1, column=week0_col).number_format = '0.00%'
        ws.cell(row=data_start_row + 1, column=week0_col).border = border

        previous_actual = Decimal('0')
        for week_idx in range(week_count):
            col_num = week_start_col + week_idx
            cumulative_actual = cumulative_actual_values[week_idx]
            weekly_actual = cumulative_actual - previous_actual
            previous_actual = cumulative_actual
            cell = ws.cell(row=data_start_row + 1, column=col_num, value=float(weekly_actual))
            cell.number_format = '0.00%'
            cell.border = border
            cell.font = Font(size=8)

        # Kumulatif Rencana
        ws.cell(row=data_start_row + 2, column=2, value='Kumulatif Rencana')
        ws.cell(row=data_start_row + 2, column=2).font = Font(bold=True)
        ws.cell(row=data_start_row + 2, column=2).fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])
        ws.cell(row=data_start_row + 2, column=2).border = border
        # Week 0 kumulatif = 0
        ws.cell(row=data_start_row + 2, column=week0_col, value=0)
        ws.cell(row=data_start_row + 2, column=week0_col).number_format = '0.00%'
        ws.cell(row=data_start_row + 2, column=week0_col).border = border

        for week_idx in range(week_count):
            col_num = week_start_col + week_idx
            cell = ws.cell(
                row=data_start_row + 2,
                column=col_num,
                value=float(cumulative_planned_values[week_idx]),
            )
            cell.number_format = '0.00%'
            cell.border = border
            cell.font = Font(size=8)

        # Kumulatif Realisasi
        ws.cell(row=data_start_row + 3, column=2, value='Kumulatif Realisasi')
        ws.cell(row=data_start_row + 3, column=2).font = Font(bold=True)
        ws.cell(row=data_start_row + 3, column=2).fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])
        ws.cell(row=data_start_row + 3, column=2).border = border
        # Week 0 kumulatif = 0
        ws.cell(row=data_start_row + 3, column=week0_col, value=0)
        ws.cell(row=data_start_row + 3, column=week0_col).number_format = '0.00%'
        ws.cell(row=data_start_row + 3, column=week0_col).border = border

        for week_idx in range(week_count):
            col_num = week_start_col + week_idx
            cell = ws.cell(
                row=data_start_row + 3,
                column=col_num,
                value=float(cumulative_actual_values[week_idx]),
            )
            cell.number_format = '0.00%'
            cell.border = border
            cell.font = Font(size=8)

        # Calculate final references for Cover sheet
        last_week_col = get_column_letter(week_start_col + week_count - 1)
        quoted_title = ws.title.replace("'", "''")
        kurva_ranges['final_planned_ref'] = f"='{quoted_title}'!{last_week_col}{data_start_row + 2}"
        kurva_ranges['final_actual_ref'] = f"='{quoted_title}'!{last_week_col}{data_start_row + 3}"
        final_planned = cumulative_planned_values[-1] if cumulative_planned_values else Decimal('0')
        final_actual = cumulative_actual_values[-1] if cumulative_actual_values else Decimal('0')
        kurva_ranges['deviation_ref'] = float(final_actual - final_planned)

        # =====================================================================
        # NATIVE LINECHART - Kurva S (Rencana vs Realisasi)
        # 
        # Features:
        # - X-axis: Week 0, Week 1, Week 2, ... Week N
        # - Y-axis: Cumulative percentage (0-100%)
        # - 2 Series: Kumulatif Rencana (blue) & Kumulatif Realisasi (green)
        # - Markers (nodes) on data points
        # - No titles (chart title, axis titles)
        # - Transparent background
        # - Size matches week columns width and pekerjaan rows height
        # =====================================================================
        if week_count > 0 and pekerjaan_row_data:
            from openpyxl.chart.marker import Marker
            from openpyxl.chart.shapes import GraphicalProperties
            
            chart = LineChart()
            chart.style = 10
            
            # NO TITLES
            chart.title = None
            chart.y_axis.title = None
            chart.x_axis.title = None
            
            # Y-axis settings
            chart.y_axis.scaling.min = 0
            chart.y_axis.scaling.max = 1  # 100%
            chart.y_axis.numFmt = '0%'
            
            # Make chart background TRANSPARENT
            # Set plot_area fill to NoFill (transparent)
            chart.plot_area.graphicalProperties = GraphicalProperties()
            chart.plot_area.graphicalProperties.noFill = True
            
            # Also make the chart frame/border transparent
            chart.graphical_properties = GraphicalProperties()
            chart.graphical_properties.noFill = True
            
            kumulatif_rencana_row = data_start_row + 2
            kumulatif_realisasi_row = data_start_row + 3
            
            # Data includes Week 0 (column week0_col) + all week columns
            # Data reference: from Week 0 column to last week column
            data_ref = Reference(ws, 
                                 min_col=week0_col,  # Start from Week 0
                                 max_col=week_start_col + week_count - 1,
                                 min_row=kumulatif_rencana_row,
                                 max_row=kumulatif_realisasi_row)
            
            # Categories: Week labels from header row (W0, W1, W2, ...)
            categories = Reference(ws, 
                                   min_col=week0_col,
                                   max_col=week_start_col + week_count - 1,
                                   min_row=header_row)

            # Add data with from_rows=True - each ROW becomes a series
            chart.add_data(data_ref, from_rows=True, titles_from_data=False)
            chart.set_categories(categories)

            # Style series with markers (nodes)
            if chart.series:
                # Series 0: Kumulatif Rencana (Blue)
                s1 = chart.series[0]
                s1.graphicalProperties.line.solidFill = "4285F4"
                s1.graphicalProperties.line.width = 20000  # 2pt
                s1.marker = Marker(symbol='circle', size=5)
                s1.marker.graphicalProperties.solidFill = "4285F4"
                s1.marker.graphicalProperties.line.solidFill = "4285F4"
                
                if len(chart.series) > 1:
                    # Series 1: Kumulatif Realisasi (Green)
                    s2 = chart.series[1]
                    s2.graphicalProperties.line.solidFill = "34A853"
                    s2.graphicalProperties.line.width = 20000
                    s2.marker = Marker(symbol='circle', size=5)
                    s2.marker.graphicalProperties.solidFill = "34A853"
                    s2.marker.graphicalProperties.line.solidFill = "34A853"

            # Chart size: CALCULATED from standardized dimensions
            # Width = (weeks + 1 for W0) × WEEK_COL_WIDTH_CM
            # Height = num_pekerjaan × 2 rows × reduced_row_height (0.6x of default)
            num_pekerjaan = len(pekerjaan_row_data)
            total_week_cols = week_count + 1  # Including W0
            
            # Kurva S rows are 60% of default height (reduced by 40%)
            kurva_row_height_cm = DIMENSIONS['PEKERJAAN_ROW_HEIGHT_CM'] * 0.6
            
            chart.width = total_week_cols * DIMENSIONS['WEEK_COL_WIDTH_CM']
            chart.height = num_pekerjaan * DIMENSIONS['ROWS_PER_PEKERJAAN'] * kurva_row_height_cm
            
            # Log calculated size
            logger.debug("[ExcelExporter] Chart calculated: %s week cols x %scm = %.1fcm width", total_week_cols, DIMENSIONS['WEEK_COL_WIDTH_CM'], chart.width)
            logger.debug("[ExcelExporter] Chart calculated: %s pek x 2 rows x %.2fcm = %.1fcm height", num_pekerjaan, kurva_row_height_cm, chart.height)
            
            # Position: starts at Week 0 column (G), at the first pekerjaan row
            chart_anchor = f'{get_column_letter(week0_col)}{first_pekerjaan_row}' if first_pekerjaan_row else 'G4'
            ws.add_chart(chart, chart_anchor)
            
            logger.debug("[ExcelExporter] Chart: %s weeks, %s pek, anchor=%s, size=%.1fx%.1fcm", total_week_cols, num_pekerjaan, chart_anchor, chart.width, chart.height)

        logger.debug("[ExcelExporter] Kurva S sheet created with %s pekerjaan", len(pekerjaan_row_data))
        return kurva_ranges

    # =========================================================================
    # PROFESSIONAL EXPORT FOR LAPORAN BULANAN (MONTHLY REPORT)
    # =========================================================================

    def export_monthly_professional(self, data: Dict[str, Any]):
        """
        Export professionally styled Excel for Monthly reports.
        
        Creates 2 sheets:
        - Sheet 1: Detail Progress (Ringkasan + Rincian per Pekerjaan)
        - Sheet 2: Kurva S (with chart overlay, weeks up to current month)
        
        Args:
            data: Dict with keys:
                - month: Month number (1-based)
                - project_info: Project information
                - executive_summary: Summary data
                - hierarchy_progress: List of progress per klasifikasi/pekerjaan
                - kurva_s_data: Data for chart
                - base_rows: Pekerjaan rows
                - all_weekly_columns: All weekly columns
                - cumulative_end_week: Max week to show
                - planned_map, actual_map: Progress maps
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel export")

        logger.debug("[ExcelExporter] Starting Monthly Professional export...")

        month = data.get('month', 1)
        project_info = data.get('project_info', {})
        exec_summary = data.get('executive_summary', {})
        hierarchy_progress = data.get('hierarchy_progress', [])
        base_rows = data.get('base_rows', [])
        all_weekly_columns = data.get('all_weekly_columns', [])
        kurva_s_data = data.get('kurva_s_data', [])
        cumulative_end_week = data.get('cumulative_end_week', month * 4)
        
        # Parse planned_map and actual_map
        planned_map_str = data.get('planned_map', {})
        actual_map_str = data.get('actual_map', {})
        
        planned_map = {}
        for key, val in planned_map_str.items():
            parts = key.split('-')
            if len(parts) == 2:
                pek_id = int(parts[0])
                week_num = int(parts[1])
                if pek_id not in planned_map:
                    planned_map[pek_id] = {}
                planned_map[pek_id][week_num] = float(val)
        
        actual_map = {}
        for key, val in actual_map_str.items():
            parts = key.split('-')
            if len(parts) == 2:
                pek_id = int(parts[0])
                week_num = int(parts[1])
                if pek_id not in actual_map:
                    actual_map[pek_id] = {}
                actual_map[pek_id][week_num] = float(val)

        logger.debug("[ExcelExporter] Monthly Month %s: %s rows, %s total weeks, max week %s", month, len(base_rows), len(all_weekly_columns), cumulative_end_week)
        logger.debug("[ExcelExporter] planned_map_str type: %s, len: %s", type(planned_map_str), len(planned_map_str))
        logger.debug("[ExcelExporter] planned_map_str keys sample: %s", list(planned_map_str.keys())[:10] if planned_map_str else 'EMPTY')
        if planned_map_str:
            sample_key = list(planned_map_str.keys())[0] if planned_map_str else None
            logger.debug("[ExcelExporter] Sample: key=%s, value=%s", sample_key, planned_map_str.get(sample_key) if sample_key else None)
        logger.debug("[ExcelExporter] planned_map parsed: %s pekerjaan, total entries: %s", len(planned_map), sum(len(v) for v in planned_map.values()))
        logger.debug("[ExcelExporter] actual_map parsed: %s pekerjaan, total entries: %s", len(actual_map), sum(len(v) for v in actual_map.values()))
        logger.debug("[ExcelExporter] base_rows sample: %s", base_rows[0] if base_rows else 'EMPTY')

        # Merge harga data from base_rows_with_harga (same as rekap)
        base_rows_with_harga = data.get('base_rows_with_harga', [])
        if base_rows_with_harga:
            logger.debug("[ExcelExporter] Monthly: Merging %s rows with harga data...", len(base_rows_with_harga))
            harga_lookup = {}
            harga_lookup_by_id = {}
            for hrow in base_rows_with_harga:
                pekerjaan_id = hrow.get('pekerjaan_id')
                if pekerjaan_id:
                    harga_lookup_by_id[pekerjaan_id] = hrow
                uraian = hrow.get('uraian', '')
                if uraian:
                    harga_lookup[uraian] = hrow
            
            # Update base_rows with harga data
            for brow in base_rows:
                uraian = brow.get('name', brow.get('uraian', ''))
                pekerjaan_id = brow.get('pekerjaan_id') or brow.get('id')
                hdata = harga_lookup_by_id.get(pekerjaan_id) or harga_lookup.get(uraian)
                if hdata:
                    brow['satuan'] = hdata.get('satuan', brow.get('satuan', '-'))
                    brow['harga_satuan'] = hdata.get('harga_satuan', 0)
                    brow['total_harga'] = hdata.get('total_harga', 0)
                    brow['volume'] = hdata.get('volume', brow.get('volume', 0))
                    logger.debug("[ExcelExporter] Monthly: Merged harga for: %s... vol=%s, harga=%s", uraian[:30], brow['volume'], brow['harga_satuan'])
        else:
            logger.debug("[ExcelExporter] Monthly: No base_rows_with_harga found - using existing data")

        # Create workbook
        wb = Workbook()
        
        # ================================================================
        # Sheet 1: Data Master (SSOT) - contains all project data
        # ================================================================
        ws_ssot = wb.active
        ws_ssot.title = 'Data Master'
        ssot_ranges = self._build_ssot_sheet(
            ws_ssot, project_info, base_rows, all_weekly_columns, planned_map, actual_map
        )
        
        # Build gantt_ranges compatible format from ssot_ranges
        gantt_ranges = {
            'week_start_col': ssot_ranges['table']['week_start_col'],
            'pekerjaan_rows': ssot_ranges['pekerjaan_rows']
        }
        
        # ================================================================
        # Handle multi-month export
        # ================================================================
        months_list = data.get('months', [month])  # Default to single month
        if not months_list:
            months_list = [month]
        
        logger.debug("[ExcelExporter] Multi-month export: %s months: %s", len(months_list), months_list)
        
        for m in sorted(months_list):
            m_cumulative_end_week = m * 4  # Each month covers 4 weeks
            
            # ================================================================
            # Sheet: Rincian Progress M{m} (formula references to SSOT)
            # ================================================================
            ws_rincian = wb.create_sheet(f'Rincian Progress M{m}')
            self._build_monthly_rincian_sheet(
                ws_rincian, 
                month=m,
                ssot_ranges=ssot_ranges,
                executive_summary=exec_summary
            )
    
            # ================================================================
            # Sheet: Kurva S M{m} (references Data Master)
            # ================================================================
            ws_kurva = wb.create_sheet(f'Kurva S M{m}')
            
            kurva_title = f'KURVA S - LAPORAN BULAN KE-{m}'
            self._build_kurva_s_sheet(
                ws_kurva,
                rows=base_rows,
                weekly_columns=all_weekly_columns,
                planned_map=planned_map,
                actual_map=actual_map,
                kurva_s_data=kurva_s_data,
                gantt_ranges=gantt_ranges,
                title_text=kurva_title,
                max_week_num=m_cumulative_end_week
            )
            
            logger.debug("[ExcelExporter] Created sheets for Month %s: Rincian Progress M%s, Kurva S M%s", m, m, m)

        # Save to buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        from .naming import build_export_filename
        filename = build_export_filename(
            project_info.get('nama') or self.config.project_name,
            "Laporan Bulanan",
            "xlsx",
            self.config.export_date,
        )

        logger.info("[ExcelExporter] Monthly export complete: %s", filename)
        return self._create_response(buffer.getvalue(), filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def _build_monthly_detail_sheet(self, ws, month: int, project_info: Dict, 
                                     executive_summary: Dict, hierarchy_progress: List[Dict],
                                     gantt_ranges: Dict = None, cumulative_end_week: int = 0):
        """
        Build Detail Progress sheet for monthly report.
        
        Structure:
        1. Title: "LAPORAN BULAN KE-{N}"
        2. Side-by-side: IDENTITAS PROJECT | RINGKASAN PROGRESS
        3. Tabel Rincian Progress per Pekerjaan with formulas referencing Input Progress sheet
        
        Args:
            gantt_ranges: Dict with pekerjaan_rows from Input Progress sheet for cross-ref
            cumulative_end_week: Max week number for this month's report
        """
        border = self._get_thin_border()
        current_row = 1

        # ==============================================
        # TITLE
        # ==============================================
        ws.merge_cells(f'A{current_row}:K{current_row}')
        title_cell = ws[f'A{current_row}']
        title_cell.value = f'LAPORAN BULAN KE-{month}'
        title_cell.font = Font(size=16, bold=True, color=COLORS['PRIMARY'])
        title_cell.alignment = Alignment(horizontal='center')
        ws.row_dimensions[current_row].height = 30
        current_row += 2

        # ==============================================
        # SEGMENT 1 & 2: IDENTITAS PROJECT | RINGKASAN PROGRESS (side-by-side)
        # ==============================================
        # IDENTITAS PROJECT (columns A-D)
        ws[f'A{current_row}'] = 'IDENTITAS PROJECT'
        ws[f'A{current_row}'].font = Font(bold=True, size=11, color=COLORS['PRIMARY'])
        # RINGKASAN PROGRESS (columns F-H)
        ws[f'F{current_row}'] = 'RINGKASAN PROGRESS'
        ws[f'F{current_row}'].font = Font(bold=True, size=11, color=COLORS['PRIMARY'])
        current_row += 1

        # Identitas data (left side)
        identitas_data = [
            ('Nama Project', project_info.get('nama', '-')),
            ('Lokasi', project_info.get('lokasi', '-')),
            ('Pemilik', project_info.get('nama_client', project_info.get('pemilik', '-'))),
            ('Sumber Dana', project_info.get('sumber_dana', '-')),
        ]
        
        # Ringkasan data (right side)
        ringkasan_data = [
            ('Rencana Bulan Ini', f"{executive_summary.get('target_period', 0):.2f}%"),
            ('Actual Bulan Ini', f"{executive_summary.get('actual_period', 0):.2f}%"),
            ('Kumulatif Bulan Lalu', f"{executive_summary.get('cumulative_prev', 0):.2f}%"),
            ('Kumulatif s.d Ini', f"{executive_summary.get('cumulative_current', 0):.2f}%"),
            ('Deviasi', f"{executive_summary.get('deviation_cumulative', 0):+.2f}%"),
        ]

        # Write side-by-side
        max_rows = max(len(identitas_data), len(ringkasan_data))
        for i in range(max_rows):
            # Left: Identitas
            if i < len(identitas_data):
                label, value = identitas_data[i]
                ws.cell(row=current_row, column=1, value=label).font = Font(bold=True)
                ws.cell(row=current_row, column=2, value=':')
                ws.cell(row=current_row, column=3, value=value)
            
            # Right: Ringkasan (column F onwards)
            if i < len(ringkasan_data):
                label, value = ringkasan_data[i]
                ws.cell(row=current_row, column=6, value=label).font = Font(bold=True)
                ws.cell(row=current_row, column=7, value=':')
                value_cell = ws.cell(row=current_row, column=8, value=value)
                # Color for deviation
                if 'Deviasi' in label:
                    dev_val = executive_summary.get('deviation_cumulative', 0)
                    if dev_val > 0:
                        value_cell.font = Font(bold=True, color='22c55e')
                    elif dev_val < 0:
                        value_cell.font = Font(bold=True, color='ef4444')
            
            current_row += 1

        current_row += 2

        # ==============================================
        # SEGMENT 3: TABEL RINCIAN PROGRESS
        # ==============================================
        ws[f'A{current_row}'] = 'RINCIAN PROGRESS PER PEKERJAAN'
        ws[f'A{current_row}'].font = Font(bold=True, size=12)
        current_row += 1

        header_row = current_row
        # Updated headers per user request
        headers = ['No', 'Uraian Pekerjaan', 'Volume', 'Harga Satuan', 'Total Harga', 
                   'Bobot (%)', 'Kum. Lalu', 'Progress Ini', 'Kum. Ini']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[current_row].height = 30
        current_row += 1

        data_start_row = current_row

        # Data rows
        no_counter = 0
        # WP Export: track each row's canonical total so the SUM and bobot are written
        # as backend NUMBERS, not live Excel formulas.
        row_total_values = []  # list of (row, total_harga)
        for item in hierarchy_progress:
            item_type = item.get('type', 'pekerjaan')
            level = item.get('level', 3)
            
            # Row styling based on type
            if item_type == 'klasifikasi':
                bg_color = COLORS['KLASIFIKASI_BG']
                is_bold = True
                no_counter = 0
            elif item_type == 'sub_klasifikasi':
                bg_color = COLORS['SUB_KLASIFIKASI_BG']
                is_bold = True
            else:
                bg_color = None
                is_bold = False
                no_counter += 1

            # Col A: No
            no_text = str(no_counter) if item_type == 'pekerjaan' else ''
            ws.cell(row=current_row, column=1, value=no_text).border = border

            # Col B: Uraian with indent
            indent = '  ' * (level - 1)
            uraian_cell = ws.cell(row=current_row, column=2, value=f"{indent}{item.get('name', '')}")
            uraian_cell.border = border
            uraian_cell.font = Font(bold=is_bold)
            uraian_cell.alignment = Alignment(wrap_text=True, vertical='center')

            # Col C: Volume
            volume = item.get('volume', 0) or 0
            volume_cell = ws.cell(row=current_row, column=3, value=volume)
            volume_cell.number_format = '#,##0.00'
            volume_cell.border = border

            # Col D: Harga Satuan
            harga_satuan = item.get('harga_satuan', 0) or 0
            harga_satuan_cell = ws.cell(row=current_row, column=4, value=harga_satuan)
            harga_satuan_cell.number_format = '#,##0'
            harga_satuan_cell.border = border

            # Col E: Total Harga (canonical backend value Volume × Harga Satuan —
            # written as a number, never a live =C*D formula).
            total_value = item.get('total_harga')
            if total_value in (None, ''):
                total_value = (volume or 0) * (harga_satuan or 0)
            total_value = float(total_value or 0)
            total_harga_cell = ws.cell(row=current_row, column=5, value=total_value)
            total_harga_cell.number_format = '#,##0'
            total_harga_cell.border = border
            # Match the original =SUM(E..)/bobot semantics: every data row participates.
            row_total_values.append((current_row, total_value))

            # Col F: Bobot (FORMULA will be set after all data with SUM reference)
            bobot_cell = ws.cell(row=current_row, column=6)
            bobot_cell.border = border
            bobot_cell.number_format = '0.00%'

            # Col G: Kumulatif Bulan Lalu
            kum_lalu = item.get('kumulatif_lalu', item.get('cumulative_prev', 0)) or 0
            kum_lalu_cell = ws.cell(row=current_row, column=7, value=kum_lalu / 100)
            kum_lalu_cell.number_format = '0.00%'
            kum_lalu_cell.border = border

            # Col H: Progress Bulan Ini
            progress_ini = item.get('progress_ini', item.get('progress_period', 0)) or 0
            progress_cell = ws.cell(row=current_row, column=8, value=progress_ini / 100)
            progress_cell.number_format = '0.00%'
            progress_cell.border = border

            # Col I: Kumulatif Bulan Ini
            kum_ini = item.get('kumulatif_ini', item.get('cumulative_current', 0)) or 0
            kum_ini_cell = ws.cell(row=current_row, column=9, value=kum_ini / 100)
            kum_ini_cell.number_format = '0.00%'
            kum_ini_cell.border = border

            # Apply background color
            if bg_color:
                for col in range(1, 10):
                    ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=bg_color)

            current_row += 1

        data_end_row = current_row - 1

        # Add TOTAL row
        ws.cell(row=current_row, column=1, value='').border = border
        total_label = ws.cell(row=current_row, column=2, value='TOTAL')
        total_label.font = Font(bold=True)
        total_label.border = border
        ws.cell(row=current_row, column=3, value='').border = border
        ws.cell(row=current_row, column=4, value='').border = border
        
        # Total Harga SUM — canonical backend sum (not =SUM)
        grand_total_value = sum(v for _, v in row_total_values)
        total_harga_sum = ws.cell(row=current_row, column=5, value=grand_total_value)
        total_harga_sum.number_format = '#,##0'
        total_harga_sum.font = Font(bold=True)
        total_harga_sum.border = border
        
        # Bobot 100%
        ws.cell(row=current_row, column=6, value=1).number_format = '0.00%'
        ws.cell(row=current_row, column=6).font = Font(bold=True)
        ws.cell(row=current_row, column=6).border = border
        
        for col in range(7, 10):
            ws.cell(row=current_row, column=col, value='').border = border
        
        # Fill total row background
        for col in range(1, 10):
            ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            if col >= 2:
                ws.cell(row=current_row, column=col).font = Font(bold=True, color='FFFFFF')
        
        current_row += 1

        # Now set Bobot as canonical share (row total / grand total) — not a formula.
        for row, value in row_total_values:
            bobot_cell = ws.cell(row=row, column=6)
            bobot_cell.value = (value / grand_total_value) if grand_total_value else 0
            bobot_cell.number_format = '0.00%'

        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 45
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 14
        ws.column_dimensions['E'].width = 14
        ws.column_dimensions['F'].width = 10
        ws.column_dimensions['G'].width = 11
        ws.column_dimensions['H'].width = 11
        ws.column_dimensions['I'].width = 11

        # ==============================================
        # SEGMENT 4: PENGESAHAN (at bottom of same sheet)
        # ==============================================
        current_row += 3  # Space before pengesahan

        # Date/Location row
        ws.merge_cells(f'F{current_row}:I{current_row}')
        date_cell = ws[f'F{current_row}']
        lokasi = project_info.get('lokasi', '..................')
        date_str = self.config.export_date.strftime('%d %B %Y')
        date_cell.value = f"{lokasi}, {date_str}"
        date_cell.alignment = Alignment(horizontal='center')
        current_row += 2

        # Two signature blocks
        # Left: Mengetahui (column B-C)
        ws.merge_cells(f'B{current_row}:C{current_row}')
        ws[f'B{current_row}'] = 'Mengetahui,'
        ws[f'B{current_row}'].font = Font(bold=True)
        ws[f'B{current_row}'].alignment = Alignment(horizontal='center')
        
        # Right: Dibuat Oleh (column G-H)
        ws.merge_cells(f'G{current_row}:H{current_row}')
        ws[f'G{current_row}'] = 'Dibuat Oleh,'
        ws[f'G{current_row}'].font = Font(bold=True)
        ws[f'G{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1

        # Role/Title
        ws.merge_cells(f'B{current_row}:C{current_row}')
        ws[f'B{current_row}'] = 'Manajer Proyek'
        ws[f'B{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'G{current_row}:H{current_row}')
        ws[f'G{current_row}'] = 'Pelaksana'
        ws[f'G{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 5  # Signature space

        # Signature line
        ws.merge_cells(f'B{current_row}:C{current_row}')
        ws[f'B{current_row}'] = '.................................'
        ws[f'B{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'G{current_row}:H{current_row}')
        ws[f'G{current_row}'] = '.................................'
        ws[f'G{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1

        # Name placeholder
        ws.merge_cells(f'B{current_row}:C{current_row}')
        ws[f'B{current_row}'] = '(Nama Manajer)'
        ws[f'B{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'G{current_row}:H{current_row}')
        ws[f'G{current_row}'] = '(Nama Pelaksana)'
        ws[f'G{current_row}'].alignment = Alignment(horizontal='center')

        logger.debug("[ExcelExporter] Monthly Detail sheet created: %s rows + pengesahan", len(hierarchy_progress))

    def _build_pengesahan_sheet(self, ws, month: int, project_info: Dict):
        """
        Build Pengesahan (signature/approval) sheet for monthly report.
        
        Contains signature blocks for:
        - Mengetahui (Manager)
        - Dibuat Oleh (Created By)
        """
        border = self._get_thin_border()
        
        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 5
        ws.column_dimensions['D'].width = 5
        ws.column_dimensions['E'].width = 25
        ws.column_dimensions['F'].width = 5

        current_row = 3

        # Title
        ws.merge_cells(f'A{current_row}:F{current_row}')
        title = ws[f'A{current_row}']
        title.value = 'LEMBAR PENGESAHAN'
        title.font = Font(size=16, bold=True, color=COLORS['PRIMARY'])
        title.alignment = Alignment(horizontal='center')
        ws.row_dimensions[current_row].height = 30
        current_row += 2

        # Subtitle
        ws.merge_cells(f'A{current_row}:F{current_row}')
        subtitle = ws[f'A{current_row}']
        subtitle.value = f'Laporan Bulan ke-{month}'
        subtitle.font = Font(size=12)
        subtitle.alignment = Alignment(horizontal='center')
        current_row += 3

        # Date/Location
        ws.merge_cells(f'A{current_row}:F{current_row}')
        date_cell = ws[f'A{current_row}']
        lokasi = project_info.get('lokasi', '..................')
        date_str = self.config.export_date.strftime('%d %B %Y')
        date_cell.value = f"{lokasi}, {date_str}"
        date_cell.alignment = Alignment(horizontal='center')
        current_row += 3

        # Two signature blocks side by side
        # Left: Mengetahui
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = 'Mengetahui,'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        # Right: Dibuat Oleh
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = 'Dibuat Oleh,'
        ws[f'E{current_row}'].font = Font(bold=True)
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1

        # Role/Title
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = 'Manajer Proyek'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = 'Pelaksana'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1

        # Signature space
        for _ in range(5):
            current_row += 1

        # Bottom line for signature
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = '.................................'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = '.................................'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1

        # Name placeholder
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = '(Nama Manajer)'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = '(Nama Pelaksana)'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')

        logger.debug("[ExcelExporter] Pengesahan sheet created")

    def _build_ssot_sheet(self, ws, project_info: Dict, base_rows: List[Dict], 
                          weekly_columns: List[Dict], planned_map: Dict, actual_map: Dict) -> Dict:
        """
        Build SSOT (Single Source of Truth) "Data Master" sheet.
        
        Structure:
        - Rows 1-4: Identitas Project
        - Rows 5-9: Pengesahan Template
        - Row 10: Empty
        - Row 11: Table Header
        - Rows 12+: Data rows with all weeks
        
        Returns dict with cell references (ssot_ranges) for other sheets to use.
        """
        border = self._get_thin_border()
        
        # ================================================================
        # SECTION 1: IDENTITAS PROJECT (Rows 2-4)
        # ================================================================
        ws['A2'] = 'IDENTITAS PROJECT'
        ws['A2'].font = Font(bold=True, size=12, color=COLORS['PRIMARY'])
        
        # Row 3: Nama Project | Lokasi
        ws['A3'] = 'Nama Project'
        ws['A3'].font = Font(bold=True)
        ws['B3'] = ':'
        ws['C3'] = project_info.get('nama', '-')
        
        ws['E3'] = 'Lokasi'
        ws['E3'].font = Font(bold=True)
        ws['F3'] = ':'
        ws['G3'] = project_info.get('lokasi', '-')
        
        # Row 4: Pemilik | Sumber Dana
        ws['A4'] = 'Pemilik'
        ws['A4'].font = Font(bold=True)
        ws['B4'] = ':'
        ws['C4'] = project_info.get('nama_client', project_info.get('pemilik', '-'))
        
        ws['E4'] = 'Sumber Dana'
        ws['E4'].font = Font(bold=True)
        ws['F4'] = ':'
        ws['G4'] = project_info.get('sumber_dana', '-')
        
        # ================================================================
        # SECTION 2: PENGESAHAN TEMPLATE (Rows 6-9)
        # ================================================================
        ws['A6'] = 'TEMPLATE PENGESAHAN'
        ws['A6'].font = Font(bold=True, size=11, color=COLORS['PRIMARY'])
        
        # Row 7: Lokasi & Tanggal
        ws['A7'] = 'Lokasi Pengesahan'
        ws['B7'] = ':'
        ws['C7'] = project_info.get('lokasi', '..................')
        
        ws['E7'] = 'Tanggal Export'
        ws['F7'] = ':'
        ws['G7'] = self.config.export_date.strftime('%d %B %Y')
        
        # Row 8: Label signature
        ws['A8'] = 'Label Mengetahui'
        ws['B8'] = ':'
        ws['C8'] = 'Mengetahui,'
        
        ws['E8'] = 'Label Dibuat'
        ws['F8'] = ':'
        ws['G8'] = 'Dibuat Oleh,'
        
        # Row 9: Jabatan
        ws['A9'] = 'Jabatan 1'
        ws['B9'] = ':'
        ws['C9'] = 'Manajer Proyek'
        
        ws['E9'] = 'Jabatan 2'
        ws['F9'] = ':'
        ws['G9'] = 'Pelaksana'
        
        # ================================================================
        # SECTION 3: DATA TABLE (Row 11+)
        # ================================================================
        header_row = 11
        data_start_row = 12
        
        # Fixed columns: No, Uraian, Volume, Satuan, Harga Satuan, Total Harga, Bobot
        fixed_headers = ['No', 'Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan', 'Total Harga', 'Bobot (%)']
        num_fixed_cols = len(fixed_headers)  # 7 columns
        
        # Weekly columns
        week_headers = []
        week_col_map = {}  # week_num -> column letter
        for i, week in enumerate(weekly_columns):
            week_num = week.get('week', week.get('week_number', i+1))
            week_headers.append(f"W{week_num}")
            week_col_map[week_num] = get_column_letter(num_fixed_cols + 1 + i)
        
        all_headers = fixed_headers + week_headers
        total_cols = len(all_headers)
        
        # Write headers
        for col, header in enumerate(all_headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        ws.row_dimensions[header_row].height = 25
        
        # Track pekerjaan rows for reference
        pekerjaan_rows = []  # List of {id, planned_row, actual_row, type, name}
        weekly_total_by_row = {}  # row -> canonical Decimal total (backend value, no formula)
        # WP Export 2A/2B: capture the canonical weekly fractions per pekerjaan so the
        # monthly/weekly rincian sheets can aggregate in Python (Decimal) instead of
        # re-summing Data Master cells with Excel formulas.
        weekly_values_by_row = {}  # planned_row -> {'planned': {wk: Decimal}, 'actual': {wk: Decimal}}
        current_row = data_start_row
        pekerjaan_counter = 0
        
        # Write data rows
        for item in base_rows:
            item_type = item.get('type', 'pekerjaan')
            # Try multiple field names for pekerjaan ID
            item_id = item.get('id') or item.get('pekerjaan_id') or item.get('pk') or 0
            name = item.get('uraian', item.get('name', ''))
            level = item.get('level', 1)
            
            if item_type == 'pekerjaan':
                # Debug: Show first pekerjaan item structure
                if pekerjaan_counter == 0:
                    logger.debug("[SSOT Debug] First pekerjaan item keys: %s", list(item.keys()))
                    logger.debug("[SSOT Debug] First pekerjaan item: %s", item)
                
                # ==========================================
                # PEKERJAAN: 2-row structure (planned/actual)
                pekerjaan_counter += 1
                planned_row = current_row
                actual_row = current_row + 1
                
                # Merge fixed columns (A-G) across 2 rows
                for c in range(1, num_fixed_cols + 1):
                    ws.merge_cells(
                        start_row=planned_row, start_column=c,
                        end_row=actual_row, end_column=c
                    )
                
                # Col A: No
                cell = ws.cell(row=planned_row, column=1, value=pekerjaan_counter)
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                
                # Col B: Uraian
                indent = '  ' * (level - 1)
                uraian_cell = ws.cell(row=planned_row, column=2, value=f"{indent}{name}")
                uraian_cell.alignment = Alignment(wrap_text=True, vertical='center')
                uraian_cell.border = border
                
                # Col C: Volume
                volume = item.get('volume', item.get('volume_num', 0)) or 0
                cell = ws.cell(row=planned_row, column=3, value=volume if volume else '-')
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                if volume:
                    cell.number_format = '#,##0.00'
                
                # Col D: Satuan
                satuan = item.get('satuan', '-')
                cell = ws.cell(row=planned_row, column=4, value=satuan)
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                
                # Col E: Harga Satuan
                harga_satuan = item.get('harga_satuan', 0) or 0
                cell = ws.cell(row=planned_row, column=5, value=harga_satuan if harga_satuan else '-')
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                if harga_satuan:
                    cell.number_format = '#,##0'
                
                # Col F: Total Harga (canonical backend value — no live =C*E formula)
                total_value = item.get('total_harga')
                if total_value in (None, ''):
                    total_value = Decimal(str(volume or 0)) * Decimal(str(harga_satuan or 0))
                else:
                    total_value = Decimal(str(total_value or 0))
                total_cell = ws.cell(row=planned_row, column=6, value=float(total_value))
                total_cell.number_format = '#,##0'
                total_cell.alignment = Alignment(horizontal='center', vertical='center')
                total_cell.border = border
                weekly_total_by_row[planned_row] = total_value
                
                # Col G: Bobot (will be set later)
                bobot_cell = ws.cell(row=planned_row, column=7)
                bobot_cell.border = border
                bobot_cell.number_format = '0.00%'
                bobot_cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Weekly columns - PLANNED row
                pek_planned = planned_map.get(item_id, {})
                planned_weeks = {}  # week_num -> Decimal fraction (canonical)
                actual_weeks = {}

                # Debug: First 3 pekerjaan only
                if pekerjaan_counter <= 3:
                    logger.debug("[SSOT Debug] pek #%s: item_id=%s (type=%s)", pekerjaan_counter, item_id, type(item_id).__name__)
                    logger.debug("[SSOT Debug] planned_map keys: %s", list(planned_map.keys())[:5])
                    logger.debug("[SSOT Debug] pek_planned found: %s, entries: %s", bool(pek_planned), len(pek_planned))
                    logger.debug("[SSOT Debug] week_col_map keys sample: %s", list(week_col_map.keys())[:5])
                
                for week_num, col_letter in week_col_map.items():
                    col_idx = num_fixed_cols + 1 + list(week_col_map.keys()).index(week_num)
                    val = pek_planned.get(week_num, 0) or 0
                    frac = Decimal(str(val)) / Decimal('100')
                    planned_weeks[week_num] = frac
                    if val > 0:
                        week_cell = ws.cell(row=planned_row, column=col_idx, value=val / 100)
                        week_cell.number_format = '0.0%'
                        week_cell.fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])
                    else:
                        # Use 0 with custom format that displays as "-" for 0 values
                        week_cell = ws.cell(row=planned_row, column=col_idx, value=0)
                        week_cell.number_format = '0.0%;-0.0%;"-"'
                    week_cell.border = border
                    week_cell.alignment = Alignment(horizontal='center')

                # Weekly columns - ACTUAL row
                pek_actual = actual_map.get(item_id, {})
                for week_num, col_letter in week_col_map.items():
                    col_idx = num_fixed_cols + 1 + list(week_col_map.keys()).index(week_num)
                    val = pek_actual.get(week_num, 0) or 0
                    actual_weeks[week_num] = Decimal(str(val)) / Decimal('100')
                    if val > 0:
                        week_cell = ws.cell(row=actual_row, column=col_idx, value=val / 100)
                        week_cell.number_format = '0.0%'
                        week_cell.fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])
                    else:
                        # Use 0 with custom format that displays as "-" for 0 values
                        week_cell = ws.cell(row=actual_row, column=col_idx, value=0)
                        week_cell.number_format = '0.0%;-0.0%;"-"'
                    week_cell.border = border
                    week_cell.alignment = Alignment(horizontal='center')

                weekly_values_by_row[planned_row] = {'planned': planned_weeks, 'actual': actual_weeks}

                # Track pekerjaan rows
                pekerjaan_rows.append({
                    'id': item_id,
                    'planned_row': planned_row,
                    'actual_row': actual_row,
                    'type': item_type,
                    'name': name[:50]
                })
                
                current_row += 2  # Move 2 rows for pekerjaan
                
            else:
                # ==========================================
                # KLASIFIKASI/SUB-KLASIFIKASI: 1 row, no week values
                # ==========================================
                if item_type == 'klasifikasi':
                    bg_color = COLORS['KLASIFIKASI_BG']
                    pekerjaan_counter = 0
                else:
                    bg_color = COLORS['SUB_KLASIFIKASI_BG']
                
                # Col A: Empty
                ws.cell(row=current_row, column=1, value='').border = border
                
                # Col B: Uraian
                indent = '  ' * (level - 1)
                uraian_cell = ws.cell(row=current_row, column=2, value=f"{indent}{name}")
                uraian_cell.border = border
                uraian_cell.font = Font(bold=True)
                uraian_cell.alignment = Alignment(wrap_text=True, vertical='center')
                
                # Columns C-G: Empty for klasifikasi
                for c in range(3, num_fixed_cols + 1):
                    ws.cell(row=current_row, column=c, value='').border = border
                
                # Weekly columns: Empty for klasifikasi
                for week_num in week_col_map.keys():
                    col_idx = num_fixed_cols + 1 + list(week_col_map.keys()).index(week_num)
                    ws.cell(row=current_row, column=col_idx, value='').border = border
                
                # Apply background
                for col in range(1, total_cols + 1):
                    ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=bg_color)
                
                # Track klasifikasi rows
                pekerjaan_rows.append({
                    'id': item_id,
                    'planned_row': current_row,
                    'actual_row': current_row,
                    'type': item_type,
                    'name': name[:50]
                })
                
                current_row += 1  # Move 1 row for klasifikasi
        
        data_end_row = current_row - 1
        
        # Add TOTAL row
        ws.cell(row=current_row, column=1, value='').border = border
        total_label = ws.cell(row=current_row, column=2, value='TOTAL')
        total_label.font = Font(bold=True)
        total_label.border = border
        
        for col in range(3, 6):
            ws.cell(row=current_row, column=col, value='').border = border
        
        # Total Harga SUM — canonical backend sum (not =SUM)
        grand_total_value = sum(weekly_total_by_row.values(), Decimal('0'))
        total_harga_sum = ws.cell(row=current_row, column=6, value=float(grand_total_value))
        total_harga_sum.number_format = '#,##0'
        total_harga_sum.font = Font(bold=True)
        total_harga_sum.border = border

        # Bobot 100%
        ws.cell(row=current_row, column=7, value=1).number_format = '0.00%'
        ws.cell(row=current_row, column=7).font = Font(bold=True)
        ws.cell(row=current_row, column=7).border = border
        
        # Fill TOTAL row background
        for col in range(1, total_cols + 1):
            ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            if col >= 2:
                ws.cell(row=current_row, column=col).font = Font(bold=True, color='FFFFFF')
        
        total_row = current_row
        
        # Set Bobot as canonical share (pekerjaan total / grand total) — not a formula.
        grand_dec = grand_total_value
        bobot_by_row = {}
        for pek in pekerjaan_rows:
            if pek['type'] == 'pekerjaan':
                planned_row = pek['planned_row']
                pek_total = weekly_total_by_row.get(planned_row, Decimal('0'))
                bobot = (pek_total / grand_dec) if grand_dec else Decimal('0')
                bobot_by_row[planned_row] = bobot
                bobot_cell = ws.cell(row=planned_row, column=7)
                bobot_cell.value = float(bobot)
                bobot_cell.number_format = '0.00%'

        # WP Export 2A/2B: canonical project-level weekly aggregates (Σ bobot×proporsi)
        # computed in Python (Decimal) so the SSOT summary rows + rincian sheets carry
        # backend VALUES, not =SUM(G*col) recompute formulas. Cumulative is a running
        # sum of the weekly aggregate (matches the old =prev+col formula).
        week_order = list(week_col_map.keys())
        project_planned, project_actual = {}, {}
        project_cumul_planned, project_cumul_actual = {}, {}
        run_p, run_a = Decimal('0'), Decimal('0')
        for wk in week_order:
            p_sum = sum(
                (bobot_by_row.get(pr, Decimal('0')) * wv['planned'].get(wk, Decimal('0'))
                 for pr, wv in weekly_values_by_row.items()),
                Decimal('0'),
            )
            a_sum = sum(
                (bobot_by_row.get(pr, Decimal('0')) * wv['actual'].get(wk, Decimal('0'))
                 for pr, wv in weekly_values_by_row.items()),
                Decimal('0'),
            )
            project_planned[wk] = p_sum
            project_actual[wk] = a_sum
            run_p += p_sum
            run_a += a_sum
            project_cumul_planned[wk] = run_p
            project_cumul_actual[wk] = run_a

        # ================================================================
        # SUMMARY ROWS: Weekly and Cumulative Progress
        # ================================================================
        current_row = total_row + 2  # Skip 1 empty row
        
        # Colors for summary rows
        PROGRESS_WEEKLY_COLOR = '14b8a6'  # Teal for weekly
        PROGRESS_CUMUL_COLOR = '22c55e'   # Green for cumulative
        
        # ROW 1: Progress Mingguan Rencana
        row1 = current_row
        ws.merge_cells(f'A{row1}:G{row1}')
        ws[f'A{row1}'] = 'Progress Mingguan Rencana'
        ws[f'A{row1}'].font = Font(bold=True, color='FFFFFF')
        ws[f'A{row1}'].alignment = Alignment(horizontal='left', vertical='center')
        for col in range(1, num_fixed_cols + 1):
            ws.cell(row=row1, column=col).fill = PatternFill('solid', fgColor=PROGRESS_WEEKLY_COLOR)
            ws.cell(row=row1, column=col).border = border
        
        # Weekly values for planned — canonical Python aggregate (Σ bobot×proporsi)
        for wk_num, col_letter in week_col_map.items():
            col_idx = num_fixed_cols + 1 + list(week_col_map.keys()).index(wk_num)
            cell = ws.cell(row=row1, column=col_idx, value=float(project_planned.get(wk_num, Decimal('0'))))
            cell.number_format = '0.0%'
            cell.fill = PatternFill('solid', fgColor=PROGRESS_WEEKLY_COLOR)
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
        
        current_row += 1
        
        # ROW 2: Progress Mingguan Realisasi
        row2 = current_row
        ws.merge_cells(f'A{row2}:G{row2}')
        ws[f'A{row2}'] = 'Progress Mingguan Realisasi'
        ws[f'A{row2}'].font = Font(bold=True, color='FFFFFF')
        ws[f'A{row2}'].alignment = Alignment(horizontal='left', vertical='center')
        for col in range(1, num_fixed_cols + 1):
            ws.cell(row=row2, column=col).fill = PatternFill('solid', fgColor=PROGRESS_WEEKLY_COLOR)
            ws.cell(row=row2, column=col).border = border
        
        # Weekly values for actual — canonical Python aggregate (Σ bobot×proporsi)
        for wk_num, col_letter in week_col_map.items():
            col_idx = num_fixed_cols + 1 + list(week_col_map.keys()).index(wk_num)
            cell = ws.cell(row=row2, column=col_idx, value=float(project_actual.get(wk_num, Decimal('0'))))
            cell.number_format = '0.0%'
            cell.fill = PatternFill('solid', fgColor=PROGRESS_WEEKLY_COLOR)
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
        
        current_row += 1
        
        # ROW 3: Kumulatif Rencana
        row3 = current_row
        ws.merge_cells(f'A{row3}:G{row3}')
        ws[f'A{row3}'] = 'Kumulatif Rencana'
        ws[f'A{row3}'].font = Font(bold=True, color='FFFFFF')
        ws[f'A{row3}'].alignment = Alignment(horizontal='left', vertical='center')
        for col in range(1, num_fixed_cols + 1):
            ws.cell(row=row3, column=col).fill = PatternFill('solid', fgColor=PROGRESS_CUMUL_COLOR)
            ws.cell(row=row3, column=col).border = border
        
        # Cumulative planned — canonical running sum (Python value, not =prev+col)
        week_list = list(week_col_map.keys())
        for i, wk_num in enumerate(week_list):
            col_idx = num_fixed_cols + 1 + i
            cell = ws.cell(row=row3, column=col_idx, value=float(project_cumul_planned.get(wk_num, Decimal('0'))))
            cell.number_format = '0.0%'
            cell.fill = PatternFill('solid', fgColor=PROGRESS_CUMUL_COLOR)
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
        
        current_row += 1
        
        # ROW 4: Kumulatif Realisasi
        row4 = current_row
        ws.merge_cells(f'A{row4}:G{row4}')
        ws[f'A{row4}'] = 'Kumulatif Realisasi'
        ws[f'A{row4}'].font = Font(bold=True, color='FFFFFF')
        ws[f'A{row4}'].alignment = Alignment(horizontal='left', vertical='center')
        for col in range(1, num_fixed_cols + 1):
            ws.cell(row=row4, column=col).fill = PatternFill('solid', fgColor=PROGRESS_CUMUL_COLOR)
            ws.cell(row=row4, column=col).border = border
        
        # Cumulative actual — canonical running sum (Python value, not =prev+col)
        for i, wk_num in enumerate(week_list):
            col_idx = num_fixed_cols + 1 + i
            cell = ws.cell(row=row4, column=col_idx, value=float(project_cumul_actual.get(wk_num, Decimal('0'))))
            cell.number_format = '0.0%'
            cell.fill = PatternFill('solid', fgColor=PROGRESS_CUMUL_COLOR)
            cell.border = border
            cell.alignment = Alignment(horizontal='center')
        
        # Store summary row references
        summary_rows = {
            'weekly_planned_row': row1,
            'weekly_actual_row': row2,
            'cumul_planned_row': row3,
            'cumul_actual_row': row4
        }
        
        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 45
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 8
        ws.column_dimensions['E'].width = 14
        ws.column_dimensions['F'].width = 14
        ws.column_dimensions['G'].width = 10
        
        for col_letter in week_col_map.values():
            ws.column_dimensions[col_letter].width = 8
        
        # Return ranges for other sheets to reference
        ssot_ranges = {
            'sheet_name': 'Data Master',
            'identitas': {
                'nama_project': 'C3',
                'lokasi': 'G3',
                'pemilik': 'C4',
                'sumber_dana': 'G4'
            },
            'pengesahan': {
                'lokasi': 'C7',
                'tanggal': 'G7',
                'label_mengetahui': 'C8',
                'label_dibuat': 'G8',
                'jabatan_1': 'C9',
                'jabatan_2': 'G9'
            },
            'table': {
                'header_row': header_row,
                'data_start_row': data_start_row,
                'data_end_row': data_end_row,
                'total_row': total_row,
                'week_start_col': num_fixed_cols + 1,
                'week_col_map': week_col_map
            },
            'pekerjaan_rows': pekerjaan_rows,
            'summary_rows': summary_rows,
            'weekly_values': weekly_values_by_row,  # planned_row -> {'planned'/'actual': {wk: Decimal}}
            'bobot_by_row': bobot_by_row,           # planned_row -> Decimal share
            'total_by_row': {r: Decimal(str(v or 0)) for r, v in weekly_total_by_row.items()},
            'grand_total': Decimal(str(grand_total_value or 0)),
            'week_order': week_order,               # canonical week ordering (incl. partial weeks)
            'project_weekly': {                     # project-level Σ bobot×proporsi (Decimal)
                'planned': project_planned,
                'actual': project_actual,
                'cumul_planned': project_cumul_planned,
                'cumul_actual': project_cumul_actual,
            },
            'pengesahan_values': {                  # resolved strings (so views write a value, not a &-concat)
                'lokasi': project_info.get('lokasi', '..................'),
                'tanggal': self.config.export_date.strftime('%d %B %Y'),
            },
        }

        logger.debug("[ExcelExporter] SSOT Data Master sheet created: %s rows, %s weeks", len(pekerjaan_rows), len(week_col_map))
        return ssot_ranges

    def _build_monthly_rincian_sheet(self, ws, month: int, ssot_ranges: Dict, 
                                      executive_summary: Dict) -> None:
        """
        Build "Rincian Progress MX" sheet with formula references to SSOT.
        
        All data references 'Data Master' sheet via formulas.
        
        Args:
            month: Month number (1-based)
            ssot_ranges: Dict with cell references from _build_ssot_sheet
            executive_summary: Summary data for header section
        """
        border = self._get_thin_border()
        ssot_name = ssot_ranges['sheet_name']  # 'Data Master'
        
        current_row = 1
        
        # ================================================================
        # TITLE
        # ================================================================
        ws.merge_cells(f'A{current_row}:I{current_row}')
        title_cell = ws[f'A{current_row}']
        title_cell.value = f'LAPORAN BULAN KE-{month}'
        title_cell.font = Font(size=16, bold=True, color=COLORS['PRIMARY'])
        title_cell.alignment = Alignment(horizontal='center')
        ws.row_dimensions[current_row].height = 30
        current_row += 2
        
        # ================================================================
        # IDENTITAS PROJECT (Formula references to SSOT)
        # ================================================================
        ws[f'A{current_row}'] = 'IDENTITAS PROJECT'
        ws[f'A{current_row}'].font = Font(bold=True, size=11, color=COLORS['PRIMARY'])
        ws[f'F{current_row}'] = 'RINGKASAN PROGRESS'
        ws[f'F{current_row}'].font = Font(bold=True, size=11, color=COLORS['PRIMARY'])
        current_row += 1
        
        # Left: Identitas (formulas)
        identitas = ssot_ranges['identitas']
        ws[f'A{current_row}'] = 'Nama Project'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'B{current_row}'] = ':'
        ws[f'C{current_row}'] = f"='{ssot_name}'!{identitas['nama_project']}"
        
        ws[f'F{current_row}'] = 'Rencana Bulan Ini'
        ws[f'F{current_row}'].font = Font(bold=True)
        ws[f'G{current_row}'] = ':'
        # Reference: sum of month's weeks in Kumulatif Rencana row
        summary_rows = ssot_ranges.get('summary_rows', {})
        week_col_map = ssot_ranges['table']['week_col_map']
        # WP Export 2A: canonical aggregates captured on the SSOT sheet (Decimal) so
        # this sheet writes backend VALUES; only pure 1:1 ='Data Master'!cell mirrors stay.
        weekly_values = ssot_ranges.get('weekly_values', {})
        bobot_by_row = ssot_ranges.get('bobot_by_row', {})
        project_weekly = ssot_ranges.get('project_weekly', {})
        weeks_per_month = 4
        month_start_week = (month - 1) * weeks_per_month + 1
        month_end_week = month * weeks_per_month
        available_weeks = sorted(wk for wk in week_col_map if isinstance(wk, int))
        month_weeks = [wk for wk in available_weeks if month_start_week <= wk <= month_end_week]
        previous_weeks = [wk for wk in available_weeks if wk < month_start_week]
        effective_month_end_week = max(month_weeks) if month_weeks else None
        effective_prev_week = max(previous_weeks) if previous_weeks else None
        
        # Rencana Bulan Ini = Σ project planned weekly for this month (Python value)
        ws[f'H{current_row}'] = float(sum(
            (project_weekly.get('planned', {}).get(wk, Decimal('0')) for wk in month_weeks),
            Decimal('0'),
        ))
        ws[f'H{current_row}'].number_format = '0.00%;-0.00%;"-"'
        current_row += 1
        
        ws[f'A{current_row}'] = 'Lokasi'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'B{current_row}'] = ':'
        ws[f'C{current_row}'] = f"='{ssot_name}'!{identitas['lokasi']}"
        
        ws[f'F{current_row}'] = 'Actual Bulan Ini'
        ws[f'F{current_row}'].font = Font(bold=True)
        ws[f'G{current_row}'] = ':'
        # Actual Bulan Ini = Σ project actual weekly for this month (Python value)
        ws[f'H{current_row}'] = float(sum(
            (project_weekly.get('actual', {}).get(wk, Decimal('0')) for wk in month_weeks),
            Decimal('0'),
        ))
        ws[f'H{current_row}'].number_format = '0.00%;-0.00%;"-"'
        current_row += 1
        
        ws[f'A{current_row}'] = 'Pemilik'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'B{current_row}'] = ':'
        ws[f'C{current_row}'] = f"='{ssot_name}'!{identitas['pemilik']}"
        
        ws[f'F{current_row}'] = 'Kumulatif Bulan Lalu'
        ws[f'F{current_row}'].font = Font(bold=True)
        ws[f'G{current_row}'] = ':'
        # Kumulatif Bulan Lalu = cumulative planned at the last canonical week
        # before this period. This also handles non-full/partial periods.
        if effective_prev_week is not None and summary_rows.get('cumul_planned_row'):
            prev_col = week_col_map[effective_prev_week]
            cumul_plan_row = summary_rows['cumul_planned_row']
            ws[f'H{current_row}'] = f"='{ssot_name}'!{prev_col}{cumul_plan_row}"
        else:
            ws[f'H{current_row}'] = 0
        ws[f'H{current_row}'].number_format = '0.00%;-0.00%;"-"'
        current_row += 1
        
        ws[f'A{current_row}'] = 'Sumber Dana'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'B{current_row}'] = ':'
        ws[f'C{current_row}'] = f"='{ssot_name}'!{identitas['sumber_dana']}"
        
        ws[f'F{current_row}'] = 'Kumulatif s.d Ini'
        ws[f'F{current_row}'].font = Font(bold=True)
        ws[f'G{current_row}'] = ':'
        # Kumulatif s.d Ini = cumulative planned at the final canonical week that
        # actually exists in this period (the last period may contain only 1-3 weeks).
        if effective_month_end_week is not None and summary_rows.get('cumul_planned_row'):
            curr_col = week_col_map[effective_month_end_week]
            cumul_plan_row = summary_rows['cumul_planned_row']
            ws[f'H{current_row}'] = f"='{ssot_name}'!{curr_col}{cumul_plan_row}"
        else:
            ws[f'H{current_row}'] = 0
        ws[f'H{current_row}'].number_format = '0.00%;-0.00%;"-"'
        current_row += 1
        
        ws[f'F{current_row}'] = 'Deviasi'
        ws[f'F{current_row}'].font = Font(bold=True)
        ws[f'G{current_row}'] = ':'
        # Deviasi = cumulative Actual - Rencana s.d akhir bulan (Python value, not =ref-ref)
        dev_value = Decimal('0')
        if effective_month_end_week is not None:
            dev_value = (
                project_weekly.get('cumul_actual', {}).get(effective_month_end_week, Decimal('0'))
                - project_weekly.get('cumul_planned', {}).get(effective_month_end_week, Decimal('0'))
            )
        ws[f'H{current_row}'] = float(dev_value)
        ws[f'H{current_row}'].number_format = '+0.00%;-0.00%;"-"'
        current_row += 2
        
        # ================================================================
        # TABEL RINCIAN PROGRESS (Formula references to SSOT)
        # ================================================================
        ws[f'A{current_row}'] = 'RINCIAN PROGRESS PER PEKERJAAN'
        ws[f'A{current_row}'].font = Font(bold=True, size=12)
        current_row += 1
        
        # Table headers
        headers = ['No', 'Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan', 
                   'Total Harga', 'Bobot (%)', 'Kum. Lalu', 'Progress Ini', 'Kum. Ini']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        ws.row_dimensions[current_row].height = 30
        header_row = current_row
        current_row += 1
        data_start_row = current_row
        
        # Data rows - all formulas referencing SSOT
        table_info = ssot_ranges['table']
        pekerjaan_rows = ssot_ranges['pekerjaan_rows']
        week_col_map = table_info['week_col_map']
        
        # Calculate week ranges for this month
        weeks_per_month = 4
        month_end_week = month * weeks_per_month
        month_start_week = (month - 1) * weeks_per_month + 1
        # Reuse the canonical period membership resolved above. Do not assume the
        # final four-week period always contains its nominal ending week.

        row_hij = []  # (bobot, kum_lalu, prog_ini, kum_ini) per row for the bobot-weighted TOTAL
        for pek in pekerjaan_rows:
            ssot_row = pek['planned_row']  # Use planned_row for merged cell reference
            item_type = pek['type']
            
            # Row styling
            if item_type == 'klasifikasi':
                bg_color = COLORS['KLASIFIKASI_BG']
                is_bold = True
            elif item_type in ('sub-klasifikasi', 'sub_klasifikasi'):
                bg_color = COLORS['SUB_KLASIFIKASI_BG']
                is_bold = True
            else:
                bg_color = None
                is_bold = False
            
            # Col A: No (reference)
            ws.cell(row=current_row, column=1, value=f"='{ssot_name}'!A{ssot_row}").border = border
            
            # Col B: Uraian (reference)
            uraian_cell = ws.cell(row=current_row, column=2, value=f"='{ssot_name}'!B{ssot_row}")
            uraian_cell.border = border
            uraian_cell.font = Font(bold=is_bold)
            uraian_cell.alignment = Alignment(wrap_text=True, vertical='center')
            
            # Col C: Volume (reference)
            ws.cell(row=current_row, column=3, value=f"='{ssot_name}'!C{ssot_row}").border = border
            ws.cell(row=current_row, column=3).number_format = '#,##0.00'
            
            # Col D: Satuan (reference)
            ws.cell(row=current_row, column=4, value=f"='{ssot_name}'!D{ssot_row}").border = border
            
            # Col E: Harga Satuan (reference)
            ws.cell(row=current_row, column=5, value=f"='{ssot_name}'!E{ssot_row}").border = border
            ws.cell(row=current_row, column=5).number_format = '#,##0'
            
            # Col F: Total Harga (reference)
            ws.cell(row=current_row, column=6, value=f"='{ssot_name}'!F{ssot_row}").border = border
            ws.cell(row=current_row, column=6).number_format = '#,##0'
            
            # Col G: Bobot (reference)
            ws.cell(row=current_row, column=7, value=f"='{ssot_name}'!G{ssot_row}").border = border
            ws.cell(row=current_row, column=7).number_format = '0.00%'
            
            # Col H/I/J: canonical Python aggregates of this pekerjaan's PLANNED weekly
            # fractions over the period (not =SUM of Data Master cells). The month/4-week
            # filter is applied before aggregation; week order follows the canonical map.
            pek_planned_wk = weekly_values.get(ssot_row, {}).get('planned', {})
            kum_lalu = sum(
                (pek_planned_wk.get(wk, Decimal('0')) for wk in previous_weeks),
                Decimal('0'),
            )
            prog_ini = sum(
                (pek_planned_wk.get(wk, Decimal('0')) for wk in month_weeks),
                Decimal('0'),
            )
            kum_ini = kum_lalu + prog_ini
            row_hij.append((bobot_by_row.get(ssot_row, Decimal('0')), kum_lalu, prog_ini, kum_ini))

            c = ws.cell(row=current_row, column=8, value=float(kum_lalu)); c.border = border
            c.number_format = '0.00%;-0.00%;"-"'
            c = ws.cell(row=current_row, column=9, value=float(prog_ini)); c.border = border
            c.number_format = '0.00%;-0.00%;"-"'
            c = ws.cell(row=current_row, column=10, value=float(kum_ini)); c.border = border
            c.number_format = '0.00%;-0.00%;"-"'
            
            # Apply background
            if bg_color:
                for col in range(1, 11):
                    ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=bg_color)
            
            current_row += 1
        
        data_end_row = current_row - 1
        
        # TOTAL row
        ws.cell(row=current_row, column=1, value='').border = border
        ws.cell(row=current_row, column=2, value='TOTAL').border = border
        ws.cell(row=current_row, column=2).font = Font(bold=True)
        for col in range(3, 7):
            ws.cell(row=current_row, column=col, value='').border = border
        ws.cell(row=current_row, column=7, value=1).border = border
        ws.cell(row=current_row, column=7).number_format = '0.00%'
        
        # TOTAL progress columns = bobot-weighted sum of the per-row values, computed in
        # Python (canonical), not =SUMPRODUCT. Column 8=Kum.Lalu, 9=Progress, 10=Kum.Ini.
        total_by_col = {
            8: sum((b * h for b, h, _i, _j in row_hij), Decimal('0')),
            9: sum((b * i for b, _h, i, _j in row_hij), Decimal('0')),
            10: sum((b * j for b, _h, _i, j in row_hij), Decimal('0')),
        }
        for col in range(8, 11):
            ws.cell(row=current_row, column=col, value=float(total_by_col[col])).border = border
            ws.cell(row=current_row, column=col).number_format = '0.00%'
            ws.cell(row=current_row, column=col).font = Font(bold=True)
        
        # Fill TOTAL row
        for col in range(1, 11):
            ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            if col >= 2:
                ws.cell(row=current_row, column=col).font = Font(bold=True, color='FFFFFF')
        
        current_row += 3
        
        # ================================================================
        # PENGESAHAN (3 signatures: Pemilik, Pelaksana, Pengawas)
        # ================================================================
        pengesahan = ssot_ranges['pengesahan']
        pv = ssot_ranges.get('pengesahan_values', {})

        # Date/Location — write the resolved string as a VALUE (not an &-concat of two
        # Data Master cells, which would be a multi-reference formula).
        ws.merge_cells(f'E{current_row}:G{current_row}')
        ws[f'E{current_row}'] = f"{pv.get('lokasi', '')}, {pv.get('tanggal', '')}"
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 2
        
        # Signature labels (3 columns)
        # Mengetahui - Pemilik
        ws.merge_cells(f'A{current_row}:C{current_row}')
        ws[f'A{current_row}'] = 'Mengetahui,'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        # Pengawas
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = 'Pengawas,'
        ws[f'E{current_row}'].font = Font(bold=True)
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        
        # Pelaksana
        ws.merge_cells(f'H{current_row}:J{current_row}')
        ws[f'H{current_row}'] = 'Dibuat Oleh,'
        ws[f'H{current_row}'].font = Font(bold=True)
        ws[f'H{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        # Jabatan row
        ws.merge_cells(f'A{current_row}:C{current_row}')
        ws[f'A{current_row}'] = 'Pemilik Proyek'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = 'Konsultan Pengawas'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'H{current_row}:J{current_row}')
        ws[f'H{current_row}'] = 'Kontraktor Pelaksana'
        ws[f'H{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 5  # Space for signatures
        
        # Signature lines
        ws.merge_cells(f'A{current_row}:C{current_row}')
        ws[f'A{current_row}'] = '.................................'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = '.................................'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'H{current_row}:J{current_row}')
        ws[f'H{current_row}'] = '.................................'
        ws[f'H{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        # Name placeholders
        ws.merge_cells(f'A{current_row}:C{current_row}')
        ws[f'A{current_row}'] = '(Nama Pemilik)'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = '(Nama Pengawas)'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'H{current_row}:J{current_row}')
        ws[f'H{current_row}'] = '(Nama Pelaksana)'
        ws[f'H{current_row}'].alignment = Alignment(horizontal='center')
        
        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 8
        ws.column_dimensions['E'].width = 14
        ws.column_dimensions['F'].width = 14
        ws.column_dimensions['G'].width = 10
        ws.column_dimensions['H'].width = 11
        ws.column_dimensions['I'].width = 11
        ws.column_dimensions['J'].width = 11
        
        logger.debug("[ExcelExporter] Rincian Progress M%s sheet created: %s rows", month, len(pekerjaan_rows))

    # =========================================================================
    # PROFESSIONAL EXPORT FOR LAPORAN MINGGUAN (WEEKLY REPORT)
    # =========================================================================

    def export_daily_professional(self, data: Dict[str, Any]):
        """
        Export print-ready A4 XLSX for daily field reports.

        This report intentionally stays lightweight: identity, previous-week
        progress, scheduled work list, manual photo placeholders, notes, and
        signatures. It does not expose volume, bobot, pricing, or daily progress.
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel export")

        logger.debug("[ExcelExporter] Starting Daily Professional export...")

        project_info = data.get('project_info', {})
        sheets = data.get('sheets') or []
        if not sheets:
            raise ValueError("Tidak ada periode laporan harian untuk diexport.")

        wb = Workbook()
        wb.remove(wb.active)

        for sheet_data in sheets:
            ws_daily = wb.create_sheet(sheet_data.get('sheet_name') or 'Laporan Harian')
            self._build_daily_rincian_sheet(ws_daily, sheet_data, project_info)
            logger.debug("[ExcelExporter] Created sheet: %s", ws_daily.title)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        from .naming import build_export_filename
        filename = build_export_filename(
            project_info.get('nama') or self.config.project_name,
            "Laporan Harian",
            "xlsx",
            self.config.export_date,
        )

        logger.info("[ExcelExporter] Daily export complete: %s", filename)
        return self._create_response(
            buffer.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def _parse_weekly_progress_map(self, raw_map: Dict[str, Any]) -> Dict[int, Dict[int, float]]:
        parsed: Dict[int, Dict[int, float]] = {}
        for key, val in (raw_map or {}).items():
            parts = str(key).split('-')
            if len(parts) != 2:
                continue
            try:
                pek_id = int(parts[0])
                week_num = int(parts[1])
                parsed.setdefault(pek_id, {})[week_num] = float(val or 0)
            except (TypeError, ValueError):
                continue
        return parsed

    def _merge_harga_to_base_rows(self, base_rows: List[Dict[str, Any]], harga_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not harga_rows:
            return base_rows

        by_id = {row.get('pekerjaan_id'): row for row in harga_rows if row.get('pekerjaan_id')}
        by_name = {row.get('uraian'): row for row in harga_rows if row.get('uraian')}

        for row in base_rows:
            if row.get('type') != 'pekerjaan':
                continue
            hdata = by_id.get(row.get('pekerjaan_id') or row.get('id')) or by_name.get(row.get('uraian') or row.get('name'))
            if not hdata:
                continue
            row['satuan'] = hdata.get('satuan', row.get('satuan', '-'))
            row['harga_satuan'] = hdata.get('harga_satuan', 0)
            row['total_harga'] = hdata.get('total_harga', 0)
            row['volume'] = hdata.get('volume', row.get('volume', 0))
        return base_rows

    def _build_daily_rincian_sheet(self, ws, sheet_data: Dict[str, Any], project_info: Dict[str, Any]):
        from openpyxl.worksheet.page import PageMargins

        thin = Side(style='thin', color='9CA3AF')
        medium = Side(style='medium', color='374151')
        border = Border(top=thin, left=thin, right=thin, bottom=thin)
        outer = Border(top=medium, left=medium, right=medium, bottom=medium)
        blue = '1F4E78'
        sub_blue = '4472C4'
        light_blue = 'D9EAF7'
        light_gray = 'F3F4F6'
        photo_fill = 'F9FAFB'

        report_date = sheet_data.get('date')
        week_number = sheet_data.get('week_number') or 1
        day_number = sheet_data.get('day_number') or 1
        work_items = sheet_data.get('work_items') or []
        previous = sheet_data.get('previous_progress') or {}

        ws.sheet_view.showGridLines = False
        ws.freeze_panes = 'A17'
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.print_options.horizontalCentered = True
        ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.35, bottom=0.35)
        ws.print_area = 'A1:L67'

        widths = [5, 13, 13, 14, 14, 14, 14, 16, 15, 15, 15, 15]
        for idx, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(idx)].width = width
        for row in range(1, 68):
            ws.row_dimensions[row].height = 20

        def set_border(cell_range, style_border=border):
            for row in ws[cell_range]:
                for cell in row:
                    cell.border = style_border

        def merge(cell_range, value='', font=None, fill=None, alignment=None, style_border=border):
            start_cell = cell_range.split(':')[0]
            end_cell = cell_range.split(':')[-1]
            if start_cell != end_cell:
                ws.merge_cells(cell_range)
            cell = ws[cell_range.split(':')[0]]
            cell.value = value
            if font:
                cell.font = font
            if fill:
                cell.fill = fill
            if alignment:
                cell.alignment = alignment
            if style_border:
                set_border(cell_range, style_border)
            return cell

        def label_value(row, label, value, left='A', label_end='C', value_start='D', value_end='H'):
            merge(f'{left}{row}:{label_end}{row}', label, Font(bold=True, size=9),
                  PatternFill('solid', fgColor=light_gray), Alignment(vertical='center'), border)
            merge(f'{value_start}{row}:{value_end}{row}', value or '-', Font(size=9),
                  None, Alignment(vertical='center', wrap_text=True), border)

        def fmt_date(value):
            if not value:
                return '-'
            month_labels = {
                1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MEI', 6: 'JUN',
                7: 'JUL', 8: 'AGU', 9: 'SEP', 10: 'OKT', 11: 'NOV', 12: 'DES',
            }
            return f"{value.day:02d} {month_labels.get(value.month, value.strftime('%b').upper())} {value.year}"

        def progress_value(value):
            if value is None:
                return '-'
            return float(value)

        merge('A1:L1', 'LAPORAN HARIAN PROYEK',
              Font(bold=True, size=16, color='FFFFFF'), PatternFill('solid', fgColor=blue),
              Alignment(horizontal='center', vertical='center'), outer)
        ws.row_dimensions[1].height = 28
        merge('A2:L2', f"Tanggal Laporan: {fmt_date(report_date)}    |    Minggu {week_number}    |    Hari ke-{day_number}",
              Font(bold=True, size=10), PatternFill('solid', fgColor=light_blue),
              Alignment(horizontal='center', vertical='center'), border)

        merge('A4:L4', 'IDENTITAS PROYEK', Font(bold=True, size=11, color='FFFFFF'),
              PatternFill('solid', fgColor=blue), Alignment(horizontal='left'), border)
        label_value(5, 'Nama Proyek', project_info.get('nama') or self.config.project_name)
        label_value(6, 'Lokasi Proyek', project_info.get('lokasi') or self.config.location)
        label_value(7, 'Nomor Kontrak / Kode', self.config.project_code)
        label_value(8, 'Nama Kontraktor', project_info.get('nama_kontraktor') or project_info.get('kontraktor'))
        label_value(9, 'Konsultan Pengawas', project_info.get('nama_konsultan_pengawas') or project_info.get('konsultan_pengawas'))
        label_value(10, 'Owner / Instansi', project_info.get('nama_client') or project_info.get('pemilik') or project_info.get('owner'))

        merge('I5:J5', 'Cuaca Pagi', Font(bold=True, size=9), PatternFill('solid', fgColor=light_gray), None, border)
        merge('K5:L5', '', Font(size=9), None, None, border)
        merge('I6:J6', 'Cuaca Siang', Font(bold=True, size=9), PatternFill('solid', fgColor=light_gray), None, border)
        merge('K6:L6', '', Font(size=9), None, None, border)
        merge('I7:J7', 'Cuaca Sore', Font(bold=True, size=9), PatternFill('solid', fgColor=light_gray), None, border)
        merge('K7:L7', '', Font(size=9), None, None, border)
        merge('I8:L10', 'Diisi manual oleh user.', Font(italic=True, size=9, color='6B7280'),
              None, Alignment(wrap_text=True, vertical='top'), border)

        merge('A12:L12', 'PROGRESS MINGGU SEBELUMNYA', Font(bold=True, size=11, color='FFFFFF'),
              PatternFill('solid', fgColor=blue), Alignment(horizontal='left'), border)
        for rng, text in (('A13:D13', 'Rencana'), ('E13:H13', 'Realisasi'), ('I13:L13', 'Deviasi')):
            merge(rng, text, Font(bold=True, size=9, color='FFFFFF'), PatternFill('solid', fgColor=sub_blue),
                  Alignment(horizontal='center'), border)
        for rng, value in (
            ('A14:D14', progress_value(previous.get('planned'))),
            ('E14:H14', progress_value(previous.get('actual'))),
            ('I14:L14', progress_value(previous.get('deviation'))),
        ):
            cell = merge(rng, value, Font(bold=True, size=10), None, Alignment(horizontal='center'), border)
            if isinstance(value, float):
                cell.number_format = '0.00%'

        merge('A16:L16', 'PEKERJAAN YANG DILAKSANAKAN HARI INI', Font(bold=True, size=11, color='FFFFFF'),
              PatternFill('solid', fgColor=blue), Alignment(horizontal='left'), border)
        for rng, text in (('A17:A17', 'No'), ('B17:G17', 'Uraian Pekerjaan'), ('H17:J17', 'Lokasi / Area'), ('K17:L17', 'Keterangan')):
            merge(rng, text, Font(bold=True, size=9, color='FFFFFF'), PatternFill('solid', fgColor=sub_blue),
                  Alignment(horizontal='center', vertical='center', wrap_text=True), border)

        row_idx = 18
        visible_items = work_items[:8]
        if not visible_items:
            visible_items = [{'uraian': 'Tidak ada pekerjaan terjadwal pada periode ini.', 'lokasi': '', 'keterangan': ''}]
        for idx, item in enumerate(visible_items, 1):
            ws[f'A{row_idx}'] = idx
            ws[f'A{row_idx}'].alignment = Alignment(horizontal='center', vertical='top')
            ws[f'A{row_idx}'].border = border
            merge(f'B{row_idx}:G{row_idx}', item.get('uraian', ''), Font(size=9), None,
                  Alignment(wrap_text=True, vertical='top'), border)
            merge(f'H{row_idx}:J{row_idx}', item.get('lokasi', ''), Font(size=9), None,
                  Alignment(wrap_text=True, vertical='top'), border)
            merge(f'K{row_idx}:L{row_idx}', item.get('keterangan', ''), Font(size=9), None,
                  Alignment(wrap_text=True, vertical='top'), border)
            ws.row_dimensions[row_idx].height = 28
            row_idx += 1
        while row_idx <= 25:
            ws[f'A{row_idx}'].border = border
            merge(f'B{row_idx}:G{row_idx}', '', style_border=border)
            merge(f'H{row_idx}:J{row_idx}', '', style_border=border)
            merge(f'K{row_idx}:L{row_idx}', '', style_border=border)
            ws.row_dimensions[row_idx].height = 28
            row_idx += 1

        merge('A27:L27', 'DOKUMENTASI PEKERJAAN', Font(bold=True, size=11, color='FFFFFF'),
              PatternFill('solid', fgColor=blue), Alignment(horizontal='left'), border)
        for rng, label in (
            ('A28:F39', 'Foto 1'), ('G28:L39', 'Foto 2'),
            ('A41:F52', 'Foto 3'), ('G41:L52', 'Foto 4'),
        ):
            merge(rng, f'{label}\n\nPLACEHOLDER FOTO\nInsert picture manual di area ini',
                  Font(bold=True, size=11, color='6B7280'), PatternFill('solid', fgColor=photo_fill),
                  Alignment(horizontal='center', vertical='center', wrap_text=True), outer)
        for rng, text in (
            ('A40:F40', 'Keterangan foto 1'), ('G40:L40', 'Keterangan foto 2'),
            ('A53:F53', 'Keterangan foto 3'), ('G53:L53', 'Keterangan foto 4'),
        ):
            merge(rng, text, Font(size=9, italic=True, color='6B7280'), None,
                  Alignment(horizontal='center'), border)

        merge('A55:L55', 'HAMBATAN / KENDALA / KETERANGAN', Font(bold=True, size=11, color='FFFFFF'),
              PatternFill('solid', fgColor=blue), Alignment(horizontal='left'), border)
        merge('A56:L60', '', Font(size=9), None, Alignment(wrap_text=True, vertical='top'), border)

        merge('A62:D62', 'Dibuat oleh,', Font(size=9), None, Alignment(horizontal='center'), border)
        merge('E62:H62', 'Diperiksa oleh,', Font(size=9), None, Alignment(horizontal='center'), border)
        merge('I62:L62', 'Disetujui oleh,', Font(size=9), None, Alignment(horizontal='center'), border)
        merge('A63:D66', '', style_border=border)
        merge('E63:H66', '', style_border=border)
        merge('I63:L66', '', style_border=border)
        merge('A67:D67', '(Site Engineer)', Font(size=9), None, Alignment(horizontal='center'), border)
        merge('E67:H67', '(Konsultan Pengawas)', Font(size=9), None, Alignment(horizontal='center'), border)
        merge('I67:L67', '(Owner / PPK)', Font(size=9), None, Alignment(horizontal='center'), border)

        logger.debug("[ExcelExporter] Daily sheet %s created: %s pekerjaan", ws.title, len(work_items))

    def export_weekly_professional(self, data: Dict[str, Any]):
        """
        Export professionally styled Excel for Weekly reports.
        
        Creates sheets:
        - Sheet 1: Data Master (SSOT) - contains all project data
        - Sheet 2..N: Rincian Progress W{n} for each selected week
        
        NOTE: Weekly report does NOT include Kurva S sheets
        
        Args:
            data: Dict with keys:
                - weeks: Array of week numbers (e.g., [1, 2, 3, 4])
                - week: Single week number (fallback)
                - project_info: Project information
                - base_rows: Pekerjaan rows
                - all_weekly_columns: All weekly columns
                - planned_map, actual_map: Progress maps
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel export")

        logger.debug("[ExcelExporter] Starting Weekly Professional export...")

        week = data.get('week', 1)
        weeks_list = data.get('weeks', [week])
        if not weeks_list:
            weeks_list = [week]
            
        project_info = data.get('project_info', {})
        base_rows = data.get('base_rows', [])
        all_weekly_columns = data.get('all_weekly_columns', [])
        
        # Parse planned_map and actual_map (same as monthly)
        planned_map_str = data.get('planned_map', {})
        actual_map_str = data.get('actual_map', {})
        
        planned_map = {}
        for key, val in planned_map_str.items():
            parts = key.split('-')
            if len(parts) == 2:
                pek_id = int(parts[0])
                week_num = int(parts[1])
                if pek_id not in planned_map:
                    planned_map[pek_id] = {}
                planned_map[pek_id][week_num] = float(val)
        
        actual_map = {}
        for key, val in actual_map_str.items():
            parts = key.split('-')
            if len(parts) == 2:
                pek_id = int(parts[0])
                week_num = int(parts[1])
                if pek_id not in actual_map:
                    actual_map[pek_id] = {}
                actual_map[pek_id][week_num] = float(val)

        logger.debug("[ExcelExporter] Weekly export: %s weeks: %s", len(weeks_list), weeks_list)
        logger.debug("[ExcelExporter] Weekly: %s rows, %s total weeks", len(base_rows), len(all_weekly_columns))

        # Merge harga data from base_rows_with_harga
        base_rows_with_harga = data.get('base_rows_with_harga', [])
        if base_rows_with_harga:
            logger.debug("[ExcelExporter] Weekly: Merging %s rows with harga data...", len(base_rows_with_harga))
            harga_lookup = {}
            harga_lookup_by_id = {}
            for hrow in base_rows_with_harga:
                pekerjaan_id = hrow.get('pekerjaan_id')
                if pekerjaan_id:
                    harga_lookup_by_id[pekerjaan_id] = hrow
                uraian = hrow.get('uraian', '')
                if uraian:
                    harga_lookup[uraian] = hrow
            
            for brow in base_rows:
                uraian = brow.get('name', brow.get('uraian', ''))
                pekerjaan_id = brow.get('pekerjaan_id') or brow.get('id')
                hdata = harga_lookup_by_id.get(pekerjaan_id) or harga_lookup.get(uraian)
                if hdata:
                    brow['satuan'] = hdata.get('satuan', brow.get('satuan', '-'))
                    brow['harga_satuan'] = hdata.get('harga_satuan', 0)
                    brow['total_harga'] = hdata.get('total_harga', 0)
                    brow['volume'] = hdata.get('volume', brow.get('volume', 0))

        # Create workbook
        wb = Workbook()
        
        # ================================================================
        # Sheet 1: Data Master (SSOT) - contains all project data
        # ================================================================
        ws_ssot = wb.active
        ws_ssot.title = 'Data Master'
        ssot_ranges = self._build_ssot_sheet(
            ws_ssot, project_info, base_rows, all_weekly_columns, planned_map, actual_map
        )
        
        logger.debug("[ExcelExporter] Multi-week export: %s weeks: %s", len(weeks_list), weeks_list)
        
        # Get executive summary from data
        executive_summary = data.get('executive_summary', {})
        
        # ================================================================
        # Create Rincian Progress sheet for each week
        # ================================================================
        for w in sorted(weeks_list):
            ws_rincian = wb.create_sheet(f'Rincian Progress W{w}')
            self._build_weekly_rincian_sheet(
                ws_rincian, 
                week=w,
                ssot_ranges=ssot_ranges,
                project_info=project_info,
                executive_summary=executive_summary
            )
            logger.debug("[ExcelExporter] Created sheet: Rincian Progress W%s", w)

        # Save to buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        from .naming import build_export_filename
        filename = build_export_filename(
            project_info.get('nama') or self.config.project_name,
            "Laporan Mingguan",
            "xlsx",
            self.config.export_date,
        )

        logger.info("[ExcelExporter] Weekly export complete: %s", filename)
        return self._create_response(buffer.getvalue(), filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def _build_weekly_rincian_sheet(self, ws, week: int, ssot_ranges: Dict, project_info: Dict,
                                      executive_summary: Dict = None):
        """
        Build Rincian Progress sheet for weekly report.
        
        Structure (same as monthly):
        1. Title: "LAPORAN MINGGU KE-{N}"
        2. Project info section (formulas from Data Master)
        3. Ringkasan Progress section (canonical planned values)
        4. Tabel Rincian Progress with 10 columns
        5. Lembar Pengesahan
        
        Note: Klasifikasi/Sub-klasifikasi rows only show No and Uraian, other columns are blank.
        """
        border = self._get_thin_border()
        ssot_name = 'Data Master'
        current_row = 1

        # ==============================================
        # TITLE
        # ==============================================
        ws.merge_cells(f'A{current_row}:J{current_row}')
        title_cell = ws[f'A{current_row}']
        title_cell.value = f'LAPORAN PROGRESS MINGGU KE-{week}'
        title_cell.font = Font(size=14, bold=True, color=COLORS['PRIMARY'])
        title_cell.alignment = Alignment(horizontal='center')
        current_row += 2

        # ==============================================
        # PROJECT INFO (FORMULAS referencing Data Master)
        # Layout: A-B merged for labels, C for ":", D-J merged for values
        # This makes labels wider and more readable
        # ==============================================
        
        # Nama Proyek
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = 'Nama Proyek'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'C{current_row}'] = ':'
        ws.merge_cells(f'D{current_row}:J{current_row}')
        ws[f'D{current_row}'] = f"='{ssot_name}'!C3"
        current_row += 1
        
        # Lokasi
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = 'Lokasi'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'C{current_row}'] = ':'
        ws.merge_cells(f'D{current_row}:J{current_row}')
        ws[f'D{current_row}'] = f"='{ssot_name}'!G3"
        current_row += 1
        
        # Pemilik
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = 'Pemilik'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'C{current_row}'] = ':'
        ws.merge_cells(f'D{current_row}:J{current_row}')
        ws[f'D{current_row}'] = f"='{ssot_name}'!C4"
        current_row += 1
        
        # Minggu ke
        ws.merge_cells(f'A{current_row}:B{current_row}')
        ws[f'A{current_row}'] = 'Minggu ke'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'C{current_row}'] = ':'
        ws.merge_cells(f'D{current_row}:J{current_row}')
        ws[f'D{current_row}'] = week
        current_row += 2
        
        # ==============================================
        # RINGKASAN PROGRESS (canonical planned values)
        # Layout: A-D merged for labels (long text), E for ":", F-G merged for values
        # ==============================================
        ws.merge_cells(f'A{current_row}:D{current_row}')
        ws[f'A{current_row}'] = 'RINGKASAN PROGRESS'
        ws[f'A{current_row}'].font = Font(bold=True, size=11)
        current_row += 1
        
        # Get table range from ssot_ranges
        # All weekly values needed below are carried directly in ssot_ranges.
        # WP Export 2B: canonical aggregates (Decimal) captured on the SSOT sheet — the
        # official sheet carries backend VALUES; only 1:1 ='Data Master'!cell mirrors stay.
        project_weekly = ssot_ranges.get('project_weekly', {})
        weekly_values = ssot_ranges.get('weekly_values', {})
        bobot_by_row = ssot_ranges.get('bobot_by_row', {})
        proj_cum_p = project_weekly.get('cumul_planned', {})
        proj_p = project_weekly.get('planned', {})

        # Progress Kumulatif s.d. Minggu Lalu = project cumulative planned at prev week
        ws.merge_cells(f'A{current_row}:D{current_row}')
        ws[f'A{current_row}'] = 'Progress Kumulatif s.d. Minggu Lalu'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'E{current_row}'] = ':'
        ws.merge_cells(f'F{current_row}:G{current_row}')
        prev_week = week - 1
        ws[f'F{current_row}'] = float(proj_cum_p.get(prev_week, Decimal('0'))) if prev_week > 0 else 0
        ws[f'F{current_row}'].number_format = '0.00%'
        current_row += 1

        # Progress Minggu Ini = project planned weekly at this week
        ws.merge_cells(f'A{current_row}:D{current_row}')
        ws[f'A{current_row}'] = 'Progress Minggu Ini'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'E{current_row}'] = ':'
        ws.merge_cells(f'F{current_row}:G{current_row}')
        ws[f'F{current_row}'] = float(proj_p.get(week, Decimal('0')))
        ws[f'F{current_row}'].number_format = '0.00%'
        current_row += 1

        # Progress Kumulatif s.d. Minggu Ini = project cumulative planned at this week
        ws.merge_cells(f'A{current_row}:D{current_row}')
        ws[f'A{current_row}'] = 'Progress Kumulatif s.d. Minggu Ini'
        ws[f'A{current_row}'].font = Font(bold=True)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='left')
        ws[f'E{current_row}'] = ':'
        ws.merge_cells(f'F{current_row}:G{current_row}')
        ws[f'F{current_row}'] = float(proj_cum_p.get(week, Decimal('0')))
        ws[f'F{current_row}'].number_format = '0.00%'
        current_row += 2
        
        # ==============================================
        # TABEL RINCIAN PROGRESS (10 columns)
        # ==============================================
        ws[f'A{current_row}'] = 'RINCIAN PROGRESS PER PEKERJAAN'
        ws[f'A{current_row}'].font = Font(bold=True, size=12)
        current_row += 1
        
        # Table headers
        headers = ['No', 'Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan', 
                   'Total Harga', 'Bobot (%)', 'Kum. Minggu Lalu', 'Progress Minggu Ini', 'Kum. Minggu Ini']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=COLORS['HEADER_BG'])
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        ws.row_dimensions[current_row].height = 30
        header_row = current_row
        current_row += 1
        table_data_start = current_row
        
        # Data rows — A–G are 1:1 mirrors; H/I/J are canonical Python values.
        pekerjaan_rows = ssot_ranges['pekerjaan_rows']
        row_hij_w = []  # (h, i, j) per pekerjaan for the TOTAL row (Python sum, not =SUM)

        for pek in pekerjaan_rows:
            ssot_row = pek['planned_row']
            item_type = pek['type']
            
            # Row styling
            if item_type == 'klasifikasi':
                bg_color = COLORS['KLASIFIKASI_BG']
                is_bold = True
                is_header = True
            elif item_type in ('sub-klasifikasi', 'sub_klasifikasi'):
                bg_color = COLORS['SUB_KLASIFIKASI_BG']
                is_bold = True
                is_header = True
            else:
                bg_color = None
                is_bold = False
                is_header = False
            
            if is_header:
                # KLASIFIKASI/SUB-KLASIFIKASI: Only Uraian, No and other columns empty
                # Col A: Empty (no number for klasifikasi)
                ws.cell(row=current_row, column=1, value='').border = border
                
                # Col B: Uraian (reference)
                uraian_cell = ws.cell(row=current_row, column=2, value=f"='{ssot_name}'!B{ssot_row}")
                uraian_cell.border = border
                uraian_cell.font = Font(bold=is_bold)
                uraian_cell.alignment = Alignment(wrap_text=True, vertical='center')
                
                # Cols C-J: Empty
                for col in range(3, 11):
                    cell = ws.cell(row=current_row, column=col, value='')
                    cell.border = border
            else:
                # PEKERJAAN: A-G mirror SSOT; H-J canonical weighted values
                
                # Col A: No (reference)
                ws.cell(row=current_row, column=1, value=f"='{ssot_name}'!A{ssot_row}").border = border
                
                # Col B: Uraian (reference)
                uraian_cell = ws.cell(row=current_row, column=2, value=f"='{ssot_name}'!B{ssot_row}")
                uraian_cell.border = border
                uraian_cell.font = Font(bold=is_bold)
                uraian_cell.alignment = Alignment(wrap_text=True, vertical='center')
                
                # Col C: Volume (reference)
                ws.cell(row=current_row, column=3, value=f"='{ssot_name}'!C{ssot_row}").border = border
                ws.cell(row=current_row, column=3).number_format = '#,##0.00'
                
                # Col D: Satuan (reference)
                ws.cell(row=current_row, column=4, value=f"='{ssot_name}'!D{ssot_row}").border = border
                
                # Col E: Harga Satuan (reference)
                ws.cell(row=current_row, column=5, value=f"='{ssot_name}'!E{ssot_row}").border = border
                ws.cell(row=current_row, column=5).number_format = '#,##0'
                
                # Col F: Total Harga (reference)
                ws.cell(row=current_row, column=6, value=f"='{ssot_name}'!F{ssot_row}").border = border
                ws.cell(row=current_row, column=6).number_format = '#,##0'
                
                # Col G: Bobot (reference)
                ws.cell(row=current_row, column=7, value=f"='{ssot_name}'!G{ssot_row}").border = border
                ws.cell(row=current_row, column=7).number_format = '0.00%'
                
                # Col H/I/J = bobot × Σ planned weekly fractions over the period, computed
                # in Python (Decimal) from canonical data — not =G*SUM('Data Master'!..).
                bobot = bobot_by_row.get(ssot_row, Decimal('0'))
                pek_planned_wk = weekly_values.get(ssot_row, {}).get('planned', {})
                h_val = bobot * sum(
                    (pek_planned_wk.get(wk, Decimal('0')) for wk in range(1, prev_week + 1)), Decimal('0')
                ) if prev_week > 0 else Decimal('0')
                i_val = bobot * pek_planned_wk.get(week, Decimal('0'))
                j_val = bobot * sum(
                    (pek_planned_wk.get(wk, Decimal('0')) for wk in range(1, week + 1)), Decimal('0')
                )
                row_hij_w.append((h_val, i_val, j_val))

                c = ws.cell(row=current_row, column=8, value=float(h_val)); c.border = border
                c.number_format = '0.00%;-0.00%;"-"'
                c = ws.cell(row=current_row, column=9, value=float(i_val)); c.border = border
                c.number_format = '0.00%;-0.00%;"-"'
                c = ws.cell(row=current_row, column=10, value=float(j_val)); c.border = border
                c.number_format = '0.00%;-0.00%;"-"'
            
            # Apply background color
            if bg_color:
                for col in range(1, 11):
                    ws.cell(row=current_row, column=col).fill = PatternFill('solid', fgColor=bg_color)
            
            current_row += 1
        
        # ==============================================
        # TOTAL ROW (Sum of Total Harga and Bobot)
        # ==============================================
        total_row = current_row
        
        # Col A-E: "TOTAL" label merged
        ws.merge_cells(f'A{total_row}:E{total_row}')
        ws[f'A{total_row}'] = 'TOTAL'
        ws[f'A{total_row}'].font = Font(bold=True)
        ws[f'A{total_row}'].alignment = Alignment(horizontal='right')
        ws[f'A{total_row}'].border = border
        for col in range(2, 6):
            ws.cell(row=total_row, column=col).border = border
        
        # Canonical Python totals (not =SUM): F = Σ total harga (grand total),
        # G = Σ bobot (≈100%), H/I/J = Σ of the per-pekerjaan weighted values.
        total_harga_all = ssot_ranges.get('grand_total', Decimal('0'))
        total_bobot_all = sum(bobot_by_row.values(), Decimal('0'))
        sum_h = sum((h for h, _i, _j in row_hij_w), Decimal('0'))
        sum_i = sum((i for _h, i, _j in row_hij_w), Decimal('0'))
        sum_j = sum((j for _h, _i, j in row_hij_w), Decimal('0'))

        # Col F: Total Harga (sum)
        ws.cell(row=total_row, column=6, value=float(total_harga_all)).border = border
        ws.cell(row=total_row, column=6).font = Font(bold=True)
        ws.cell(row=total_row, column=6).number_format = '#,##0.00'

        # Col G: Bobot (≈100%)
        ws.cell(row=total_row, column=7, value=float(total_bobot_all)).border = border
        ws.cell(row=total_row, column=7).font = Font(bold=True)
        ws.cell(row=total_row, column=7).number_format = '0.00%'

        for col, val in ((8, sum_h), (9, sum_i), (10, sum_j)):
            ws.cell(row=total_row, column=col, value=float(val)).border = border
            ws.cell(row=total_row, column=col).font = Font(bold=True)
            ws.cell(row=total_row, column=col).number_format = '0.00%'
        
        current_row = total_row + 3
        
        # ==============================================
        # LEMBAR PENGESAHAN (same as monthly)
        # ==============================================
        ws.merge_cells(f'A{current_row}:J{current_row}')
        ws[f'A{current_row}'] = 'LEMBAR PENGESAHAN'
        ws[f'A{current_row}'].font = Font(bold=True, size=11)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 2
        
        # Three signature columns
        ws.merge_cells(f'A{current_row}:C{current_row}')
        ws[f'A{current_row}'] = 'Dibuat oleh,'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = 'Diperiksa oleh,'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'H{current_row}:J{current_row}')
        ws[f'H{current_row}'] = 'Disetujui oleh,'
        ws[f'H{current_row}'].alignment = Alignment(horizontal='center')
        
        current_row += 4  # Space for signatures
        
        ws.merge_cells(f'A{current_row}:C{current_row}')
        ws[f'A{current_row}'] = '(Nama Pelaksana)'
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'E{current_row}:F{current_row}')
        ws[f'E{current_row}'] = '(Nama Pengawas)'
        ws[f'E{current_row}'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells(f'H{current_row}:J{current_row}')
        ws[f'H{current_row}'] = '(Nama Pemilik)'
        ws[f'H{current_row}'].alignment = Alignment(horizontal='center')
        
        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 8
        ws.column_dimensions['E'].width = 14
        ws.column_dimensions['F'].width = 14
        ws.column_dimensions['G'].width = 10
        ws.column_dimensions['H'].width = 13
        ws.column_dimensions['I'].width = 13
        ws.column_dimensions['J'].width = 13
        
        logger.debug("[ExcelExporter] Rincian Progress W%s sheet created: %s rows", week, len(pekerjaan_rows))
