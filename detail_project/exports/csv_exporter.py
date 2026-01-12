# =====================================================================
# FILE: detail_project/exports/csv_exporter.py
# Copy this entire file
# =====================================================================

import csv
from typing import Dict, Any, Iterable
from .base import ConfigExporterBase
from django.http import HttpResponse, StreamingHttpResponse


class CSVExporter(ConfigExporterBase):
    """CSV Export handler - Excel friendly"""
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export to CSV with semicolon delimiter (Excel-friendly)
        
        Expected data structure:
        {
            'table_data': {
                'headers': ['Col1', 'Col2', ...],
                'rows': [['val1', 'val2', ...], ...]
            },
            'hierarchy_levels': {0: 1, 5: 2, ...} (optional),
            'footer_rows': [['label', 'value'], ...] (optional)
        }
        """
        class _Echo:
            def write(self, value):
                return value

        writer = csv.writer(_Echo(), delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        def iter_section(section: Dict[str, Any]) -> Iterable[str]:
            # Header per section
            title = section.get('title') or self.config.title
            yield writer.writerow([title])
            # Identity block aligned with page
            from ..export_config import build_identity_rows
            for label, _colon, value in build_identity_rows(self.config):
                yield writer.writerow([label, value])
            yield writer.writerow([])

            # Check if this section has subsections (appendix with multiple tables OR pekerjaan sections)
            if 'sections' in section:
                # Check if sections are pekerjaan sections (Rincian AHSP style)
                if section['sections'] and isinstance(section['sections'][0], dict) and 'pekerjaan' in section['sections'][0]:
                    # Rincian AHSP sections (each pekerjaan with its detail table)
                    for pek_section in section['sections']:
                        yield from iter_pekerjaan_section(pek_section)
                        yield writer.writerow([])  # Separator between pekerjaan
                else:
                    # Multi-section page (e.g., Parameter + Formula appendix)
                    for subsection in section['sections']:
                        # Subsection title
                        subsection_title = subsection.get('section_title')
                        if subsection_title:
                            yield writer.writerow([subsection_title])
                            yield writer.writerow([])

                        # Subsection table
                        yield from iter_table(subsection)
                        yield writer.writerow([])  # Separator between sections
            else:
                # Single table section
                yield from iter_table(section)

            if 'footer_rows' in section:
                yield writer.writerow([])
                for footer_row in section['footer_rows']:
                    yield writer.writerow(footer_row)

        def iter_table(section: Dict[str, Any]) -> Iterable[str]:
            """Write a single table"""
            table_data = section.get('table_data', {})
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            hierarchy = section.get('hierarchy_levels', {})

            if headers:
                yield writer.writerow(headers)

            for idx, row in enumerate(rows):
                level = hierarchy.get(idx, 3)
                if level > 1 and len(row) > 0:
                    indent = '  ' * (level - 1)
                    row_with_indent = [indent + str(row[0])] + list(row[1:])
                else:
                    row_with_indent = row
                yield writer.writerow(row_with_indent)

        def iter_pekerjaan_section(pek_section: Dict[str, Any]) -> Iterable[str]:
            """Write a pekerjaan section (Rincian AHSP style)"""
            pekerjaan = pek_section.get('pekerjaan', {})
            detail_table = pek_section.get('detail_table', {})

            # Pekerjaan header section
            yield writer.writerow(['=== PEKERJAAN ==='])
            yield writer.writerow(['Kode', pekerjaan.get('kode', '-')])
            yield writer.writerow(['Uraian', pekerjaan.get('uraian', '-')])
            yield writer.writerow(['Satuan', pekerjaan.get('satuan', '-')])
            yield writer.writerow(['Total', f"Rp {pekerjaan.get('total', '0')}"])
            yield writer.writerow([])

            # Detail items table
            if pek_section.get('has_details'):
                headers = detail_table.get('headers', [])
                rows = detail_table.get('rows', [])

                # Write headers
                if headers:
                    yield writer.writerow(headers)

                # Write data rows
                for row in rows:
                    yield writer.writerow(row)
            else:
                yield writer.writerow(['Tidak ada detail item untuk pekerjaan ini'])

        def row_generator() -> Iterable[str]:
            # BOM for Excel
            yield '\ufeff'

            if 'pages' in data:
                pages = data['pages']
                for i, section in enumerate(pages):
                    yield from iter_section(section)
                    if i < len(pages) - 1:
                        yield writer.writerow([])
            elif 'sections' in data and data['sections'] and isinstance(data['sections'][0], dict) and 'pekerjaan' in data['sections'][0]:
                yield from iter_section(data)
                if 'summary' in data:
                    yield writer.writerow([])
                    yield writer.writerow(['=== RINGKASAN ==='])
                    summary = data['summary']
                    yield writer.writerow(['Total Pekerjaan', summary.get('total_pekerjaan', 0)])
                    yield writer.writerow(['Total Items', summary.get('total_items', 0)])
                    yield writer.writerow(['Grand Total', f"Rp {summary.get('grand_total', '0')}"])
            else:
                yield from iter_section(data)

        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.csv"
        response = StreamingHttpResponse(row_generator(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response
