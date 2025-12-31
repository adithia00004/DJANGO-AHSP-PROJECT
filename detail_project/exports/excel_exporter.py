"""
Excel Exporter built on top of ConfigExporterBase.

Supports:
- Standard export via export() for RAB, Kebutuhan, etc.
- Professional export via export_professional() for Jadwal Pekerjaan Rekap
  with 3 sheets: Cover, Kurva S (with LineChart), Input Progress-Gantt

Requirements: openpyxl
"""

from io import BytesIO
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


def safe_float(value, default=0.0):
    """
    Safely convert value to float, handling various formats:
    - European format: '0,00%' or '1.234,56' or '100,000' (3 decimals)
    - Standard format: '0.00%' or '1,234.56'
    - Percentage signs: remove and divide by 100
    """
    if value is None:
        return default
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        # Check for percentage
        is_percent = '%' in s
        s = s.replace('%', '')
        # Handle European format (comma as decimal, dot as thousands)
        # vs US format (dot as decimal, comma as thousands)
        if ',' in s and '.' in s:
            # If comma comes after dot: 1.234,56 = European = 1234.56
            # If dot comes after comma: 1,234.56 = US = 1234.56
            if s.rfind(',') > s.rfind('.'):
                # European: 1.234,56
                s = s.replace('.', '').replace(',', '.')
            else:
                # US: 1,234.56
                s = s.replace(',', '')
        elif ',' in s:
            # Only comma: could be European decimal or US thousands
            # If single comma with 1-3 digits after: treat as decimal
            # (volume uses 3 decimals: "100,000")
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 3:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        try:
            result = float(s)
            if is_percent:
                result /= 100.0
            return result
        except (ValueError, TypeError):
            return default
    return default


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

    def _get_thin_border(self):
        """Get standard thin border."""
        side = Side(style='thin', color=COLORS['BORDER'])
        return Border(top=side, bottom=side, left=side, right=side)

    def export(self, data: Dict[str, Any]):
        """Standard export method for non-Jadwal exports."""
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

    def _create_sheet(self, wb: Workbook, title: str, is_first: bool = False):
        sanitized = self._sanitize_title(title)
        if is_first:
            ws = wb.active
            ws.title = sanitized
        else:
            ws = wb.create_sheet(sanitized)
        return ws

    def _sanitize_title(self, title: str) -> str:
        invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
        for ch in invalid_chars:
            title = title.replace(ch, '_')
        return title[:31]

    def _write_table(self, ws, start_row: int, section: Dict[str, Any]) -> int:
        table_data = section.get('table_data') or {}
        headers = table_data.get('headers') or []
        rows = table_data.get('rows') or []
        hierarchy = section.get('hierarchy_levels') or {}
        border = self._get_thin_border()

        if headers:
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=start_row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill('solid', fgColor='E8E8E8')
                cell.border = border
            start_row += 1

        for row_idx, row in enumerate(rows):
            for col_idx, val in enumerate(row, 1):
                cell = ws.cell(row=start_row, column=col_idx, value=val)
                cell.border = border
            level = hierarchy.get(row_idx, 0)
            if level > 0:
                ws.cell(row=start_row, column=1).alignment = Alignment(indent=level * 2)
            start_row += 1

        return start_row

    def _write_pekerjaan_section(self, ws, start_row: int, section: Dict[str, Any]) -> int:
        pekerjaan = section.get('pekerjaan', {})
        items = section.get('items', [])
        border = self._get_thin_border()

        # Pekerjaan header
        ws.cell(row=start_row, column=1, value=pekerjaan.get('name', ''))
        ws.cell(row=start_row, column=1).font = Font(bold=True, size=11)
        ws.cell(row=start_row, column=1).fill = PatternFill('solid', fgColor='E0E7FF')
        start_row += 1

        # Sub-headers
        sub_headers = ['No', 'Kode', 'Uraian Item', 'Satuan', 'Koefisien', 'Harga Satuan', 'Jumlah Harga']
        for col_idx, header in enumerate(sub_headers, 1):
            cell = ws.cell(row=start_row, column=col_idx, value=header)
            cell.font = Font(bold=True, size=9)
            cell.fill = PatternFill('solid', fgColor='F3F4F6')
            cell.border = border
        start_row += 1

        # Items
        for idx, item in enumerate(items, 1):
            ws.cell(row=start_row, column=1, value=idx).border = border
            ws.cell(row=start_row, column=2, value=item.get('kode', '')).border = border
            ws.cell(row=start_row, column=3, value=item.get('uraian', '')).border = border
            ws.cell(row=start_row, column=4, value=item.get('satuan', '')).border = border
            ws.cell(row=start_row, column=5, value=item.get('koefisien', '')).border = border
            ws.cell(row=start_row, column=6, value=item.get('harga_satuan', '')).border = border
            ws.cell(row=start_row, column=7, value=item.get('jumlah_harga', '')).border = border
            start_row += 1

        return start_row

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
        print(f"[ExcelExporter] Starting professional export...")

        wb = Workbook()
        report_type = data.get('report_type', 'rekap')

        # Extract data
        project_info = data.get('project_info', {})
        summary = data.get('summary', {})
        kurva_s_data = data.get('kurva_s_data', [])
        planned_pages = data.get('planned_pages', [])
        actual_pages = data.get('actual_pages', [])
        weekly_columns = data.get('weekly_columns', [])
        
        # Build hierarchy rows from planned_pages
        # Note: Adapter returns [uraian, volume, satuan, week1, week2, ...]
        # Only 3 static columns, no code/harga/total/bobot
        base_rows = []
        seen_uraian = set()
        planned_map = {}
        actual_map = {}
        
        # Extract rows from planned_pages (table_data.rows contains materialized rows)
        print(f"[ExcelExporter] planned_pages count: {len(planned_pages)}")
        for page_idx, page in enumerate(planned_pages):
            table_data = page.get('table_data', {})
            page_rows = table_data.get('rows', [])
            headers = table_data.get('headers', [])
            print(f"[ExcelExporter] Page {page_idx}: {len(page_rows)} rows, headers: {headers[:5]}...")
            
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
                        print(f"[ExcelExporter] Row {pek_id}: uraian='{uraian[:30]}...', volume_str='{volume_str}', satuan='{satuan}'")
                    
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
                        print(f"[ExcelExporter] Row {pek_id} planned: {list(week_dict.items())[:3]}...")
        
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

        print(f"[ExcelExporter] Data: {len(base_rows)} rows, {len(weekly_columns)} weeks, planned_map: {len(planned_map)}, actual_map: {len(actual_map)}")

        # Merge harga data from base_rows_with_harga (from ExportManager)
        base_rows_with_harga = data.get('base_rows_with_harga', [])
        if base_rows_with_harga:
            print(f"[ExcelExporter] Merging {len(base_rows_with_harga)} rows with harga data...")
            # Build lookup by uraian
            harga_lookup = {}
            for hrow in base_rows_with_harga:
                uraian = hrow.get('uraian', '')
                if uraian:
                    harga_lookup[uraian] = hrow
            
            # Update base_rows with harga data
            for brow in base_rows:
                uraian = brow.get('name', '')
                if uraian in harga_lookup:
                    hdata = harga_lookup[uraian]
                    brow['satuan'] = hdata.get('satuan', brow.get('satuan', ''))
                    brow['harga_satuan'] = hdata.get('harga_satuan', 0)
                    brow['total_harga'] = hdata.get('total_harga', 0)
                    brow['volume_num'] = hdata.get('volume', brow.get('volume_num', 0))
                    print(f"[ExcelExporter] Merged harga for: {uraian[:30]}... satuan={brow['satuan']}, harga={brow['harga_satuan']:.0f}")

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

        print("[ExcelExporter] Cover sheet created")

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
                first_week = get_column_letter(week_start_col)
                last_week = get_column_letter(week_start_col + week_count - 1)
                formula = f'=SUM({first_week}{planned_row}:{last_week}{planned_row})+SUM({first_week}{actual_row}:{last_week}{actual_row})'
                cell = ws.cell(row=planned_row, column=total_col, value=formula)
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

        print(f"[ExcelExporter] Input Progress-Gantt sheet created with {len(gantt_ranges['pekerjaan_rows'])} pekerjaan")
        return gantt_ranges

    def _build_kurva_s_sheet(self, ws, rows: List[Dict], weekly_columns: List[Dict],
                              planned_map: Dict, actual_map: Dict,
                              kurva_s_data: List[Dict], gantt_ranges: Dict) -> Dict:
        """Build Kurva S sheet with data table, formulas, and native LineChart."""
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

        # Title
        ws.merge_cells(f'A1:{get_column_letter(total_col)}1')
        ws['A1'] = 'KURVA S - RINCIAN PROGRESS'
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

        # Build gantt row map for cross-reference
        gantt_row_map = {}
        for r in gantt_ranges.get('pekerjaan_rows', []):
            gantt_row_map[r['id']] = r

        # Process rows
        current_row = header_row + 1
        pekerjaan_counter = 0
        pekerjaan_row_data = []
        first_pekerjaan_row = None
        last_pekerjaan_row = None

        for item in rows:
            item_type = item.get('type', '')
            item_id = item.get('id')

            if item_type == 'pekerjaan':
                pekerjaan_counter += 1
                planned_row = current_row
                actual_row = current_row + 1

                if first_pekerjaan_row is None:
                    first_pekerjaan_row = planned_row
                last_pekerjaan_row = actual_row

                pekerjaan_row_data.append({
                    'planned': planned_row,
                    'actual': actual_row,
                    'id': item_id
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
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Total Harga = Volume * Harga Satuan (FORMULA)
                formula = f'=C{planned_row}*E{planned_row}'
                cell = ws.cell(row=planned_row, column=6, value=formula)
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Bobot (placeholder - will be updated after total row)
                cell = ws.cell(row=planned_row, column=7, value=0)
                cell.number_format = '0.00%'
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Get corresponding gantt row for cross-reference
                gantt_row = gantt_row_map.get(item_id)
                bobot_ref = f'$G${planned_row}'

                # Week columns - Planned row: Bobot × Input Progress (cross-sheet formula)
                for week_idx in range(week_count):
                    col_num = week_start_col + week_idx
                    gantt_week_col = gantt_ranges['week_start_col'] + week_idx
                    gantt_col_letter = get_column_letter(gantt_week_col)

                    cell = ws.cell(row=planned_row, column=col_num)
                    if gantt_row:
                        gantt_ref = f"'Input Progress-Gantt'!{gantt_col_letter}{gantt_row['planned_row']}"
                        cell.value = f'={bobot_ref}*{gantt_ref}'
                        cell.number_format = '0.00%'

                        # Check if has progress for coloring
                        week_key = weekly_columns[week_idx].get('week', week_idx + 1)
                        if item_id and item_id in planned_map:
                            wp = planned_map[item_id]
                            if isinstance(wp, dict) and safe_float(wp.get(week_key, 0) or 0) > 0:
                                cell.fill = PatternFill('solid', fgColor=COLORS['PLANNED_BG'])
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')
                    cell.font = Font(size=8)

                # Week columns - Actual row
                for week_idx in range(week_count):
                    col_num = week_start_col + week_idx
                    gantt_week_col = gantt_ranges['week_start_col'] + week_idx
                    gantt_col_letter = get_column_letter(gantt_week_col)

                    cell = ws.cell(row=actual_row, column=col_num)
                    if gantt_row:
                        gantt_ref = f"'Input Progress-Gantt'!{gantt_col_letter}{gantt_row['actual_row']}"
                        cell.value = f'={bobot_ref}*{gantt_ref}'
                        cell.number_format = '0.00%'

                        week_key = weekly_columns[week_idx].get('week', week_idx + 1)
                        if item_id and item_id in actual_map:
                            wp = actual_map[item_id]
                            if isinstance(wp, dict) and safe_float(wp.get(week_key, 0) or 0) > 0:
                                cell.fill = PatternFill('solid', fgColor=COLORS['ACTUAL_BG'])
                    cell.border = border
                    cell.alignment = Alignment(horizontal='center')
                    cell.font = Font(size=8)

                # Total column (merged)
                ws.merge_cells(
                    start_row=planned_row, start_column=total_col,
                    end_row=actual_row, end_column=total_col
                )
                first_week = get_column_letter(week_start_col)
                last_week = get_column_letter(week_start_col + week_count - 1)
                formula = f'=SUM({first_week}{planned_row}:{last_week}{planned_row})+SUM({first_week}{actual_row}:{last_week}{actual_row})'
                cell = ws.cell(row=planned_row, column=total_col, value=formula)
                cell.number_format = '0.00%'
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                cell.font = Font(size=8)

                # Apply borders to actual row
                for c in range(1, fixed_col_count + 1):
                    ws.cell(row=actual_row, column=c).border = border

                # Set standardized row heights for pekerjaan (fits 2 lines of text)
                ws.row_dimensions[planned_row].height = DIMENSIONS['PEKERJAAN_ROW_HEIGHT']
                ws.row_dimensions[actual_row].height = DIMENSIONS['PEKERJAAN_ROW_HEIGHT']

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

        # Total Harga sum
        total_harga_refs = '+'.join([f'F{p["planned"]}' for p in pekerjaan_row_data])
        cell = ws.cell(row=total_row, column=6, value=f'={total_harga_refs}' if total_harga_refs else 0)
        cell.number_format = '#,##0'
        cell.font = Font(bold=True)
        cell.border = border

        # Bobot sum
        bobot_refs = '+'.join([f'G{p["planned"]}' for p in pekerjaan_row_data])
        cell = ws.cell(row=total_row, column=7, value=f'={bobot_refs}' if bobot_refs else 0)
        cell.number_format = '0.00%'
        cell.font = Font(bold=True)
        cell.border = border

        # Apply borders to total row
        for c in range(1, total_col + 1):
            ws.cell(row=total_row, column=c).border = border
            if week_start_col <= c < total_col:
                ws.cell(row=total_row, column=c).fill = PatternFill('solid', fgColor=COLORS['TOTAL_BG'])

        # Update Bobot formulas with total row reference
        total_harga_ref = f'$F${total_row}'
        for p in pekerjaan_row_data:
            cell = ws.cell(row=p['planned'], column=7)
            cell.value = f'=IF({total_harga_ref}=0,0,F{p["planned"]}/{total_harga_ref})'

        # Calculate total harga for cover
        kurva_ranges['total_harga'] = sum(
            safe_float(r.get('total_harga', 0) or 0) for r in rows if r.get('type') == 'pekerjaan'
        )
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

        for week_idx in range(week_count):
            col_num = week_start_col + week_idx
            col_letter = get_column_letter(col_num)
            refs = '+'.join([f'{col_letter}{p["planned"]}' for p in pekerjaan_row_data])
            cell = ws.cell(row=data_start_row, column=col_num, value=f'={refs}' if refs else 0)
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

        for week_idx in range(week_count):
            col_num = week_start_col + week_idx
            col_letter = get_column_letter(col_num)
            refs = '+'.join([f'{col_letter}{p["actual"]}' for p in pekerjaan_row_data])
            cell = ws.cell(row=data_start_row + 1, column=col_num, value=f'={refs}' if refs else 0)
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
            col_letter = get_column_letter(col_num)
            if week_idx == 0:
                # First week: Week0 + this week's progress
                week0_letter = get_column_letter(week0_col)
                formula = f'={week0_letter}{data_start_row + 2}+{col_letter}{data_start_row}'
            else:
                prev_col = get_column_letter(col_num - 1)
                formula = f'={prev_col}{data_start_row + 2}+{col_letter}{data_start_row}'
            cell = ws.cell(row=data_start_row + 2, column=col_num, value=formula)
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
            col_letter = get_column_letter(col_num)
            if week_idx == 0:
                week0_letter = get_column_letter(week0_col)
                formula = f'={week0_letter}{data_start_row + 3}+{col_letter}{data_start_row + 1}'
            else:
                prev_col = get_column_letter(col_num - 1)
                formula = f'={prev_col}{data_start_row + 3}+{col_letter}{data_start_row + 1}'
            cell = ws.cell(row=data_start_row + 3, column=col_num, value=formula)
            cell.number_format = '0.00%'
            cell.border = border
            cell.font = Font(size=8)

        # Calculate final references for Cover sheet
        last_week_col = get_column_letter(week_start_col + week_count - 1)
        kurva_ranges['final_planned_ref'] = f"='Kurva S'!{last_week_col}{data_start_row + 2}"
        kurva_ranges['final_actual_ref'] = f"='Kurva S'!{last_week_col}{data_start_row + 3}"
        kurva_ranges['deviation_ref'] = f"='Kurva S'!{last_week_col}{data_start_row + 3}-'Kurva S'!{last_week_col}{data_start_row + 2}"

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
            # Height = num_pekerjaan × 2 rows × PEKERJAAN_ROW_HEIGHT_CM
            num_pekerjaan = len(pekerjaan_row_data)
            total_week_cols = week_count + 1  # Including W0
            
            chart.width = total_week_cols * DIMENSIONS['WEEK_COL_WIDTH_CM']
            chart.height = num_pekerjaan * DIMENSIONS['ROWS_PER_PEKERJAAN'] * DIMENSIONS['PEKERJAAN_ROW_HEIGHT_CM']
            
            # Log calculated size
            print(f"[ExcelExporter] Chart calculated: {total_week_cols} week cols × {DIMENSIONS['WEEK_COL_WIDTH_CM']}cm = {chart.width:.1f}cm width")
            print(f"[ExcelExporter] Chart calculated: {num_pekerjaan} pek × 2 rows × {DIMENSIONS['PEKERJAAN_ROW_HEIGHT_CM']}cm = {chart.height:.1f}cm height")
            
            # Position: starts at Week 0 column (G), at the first pekerjaan row
            chart_anchor = f'{get_column_letter(week0_col)}{first_pekerjaan_row}' if first_pekerjaan_row else 'G4'
            ws.add_chart(chart, chart_anchor)
            
            print(f"[ExcelExporter] Chart: {total_week_cols} weeks, {num_pekerjaan} pek, anchor={chart_anchor}, size={chart.width:.1f}x{chart.height:.1f}cm")

        print(f"[ExcelExporter] Kurva S sheet created with {len(pekerjaan_row_data)} pekerjaan")
        return kurva_ranges
