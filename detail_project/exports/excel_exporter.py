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
