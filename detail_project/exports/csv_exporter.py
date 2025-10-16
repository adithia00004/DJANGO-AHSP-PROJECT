# =====================================================================
# FILE: detail_project/exports/csv_exporter.py
# Copy this entire file
# =====================================================================

import csv
from io import StringIO
from typing import Dict, Any
from .base import ConfigExporterBase
from django.http import HttpResponse


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
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        def write_section(section: Dict[str, Any]):
            # Header per section
            title = section.get('title') or self.config.title
            writer.writerow([title])
            # Identity block aligned with page
            from ..export_config import build_identity_rows
            for label, _colon, value in build_identity_rows(self.config):
                writer.writerow([label, value])
            writer.writerow([])

            table_data = section.get('table_data', {})
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            hierarchy = section.get('hierarchy_levels', {})

            if headers:
                writer.writerow(headers)

            for idx, row in enumerate(rows):
                level = hierarchy.get(idx, 3)
                if level > 1 and len(row) > 0:
                    indent = '  ' * (level - 1)
                    row_with_indent = [indent + str(row[0])] + list(row[1:])
                else:
                    row_with_indent = row
                writer.writerow(row_with_indent)

            if 'footer_rows' in section:
                writer.writerow([])
                for footer_row in section['footer_rows']:
                    writer.writerow(footer_row)

        # Multi-page support
        if 'pages' in data:
            pages = data['pages']
            for i, section in enumerate(pages):
                write_section(section)
                if i < len(pages) - 1:
                    writer.writerow([])
        else:
            write_section(data)
        
        # Create response
        content = output.getvalue().encode('utf-8-sig')  # BOM for Excel
        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.csv"
        
        return self._create_response(
            content, 
            filename, 
            'text/csv; charset=utf-8-sig'
        )
