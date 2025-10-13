# =====================================================================
# FILE: detail_project/exports/csv_exporter.py
# Copy this entire file
# =====================================================================

import csv
from io import StringIO
from typing import Dict, Any
from .base import BaseExporter


class CSVExporter(BaseExporter):
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
        
        # Write project info as header
        writer.writerow([self.config.title])
        writer.writerow(['Nama Proyek', self.config.project_name])
        writer.writerow(['Kode Proyek', self.config.project_code])
        writer.writerow(['Lokasi', self.config.location])
        writer.writerow(['Tahun', self.config.year])
        writer.writerow([])  # Empty row
        
        # Write table
        table_data = data.get('table_data', {})
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        hierarchy = data.get('hierarchy_levels', {})
        
        # Write headers
        if headers:
            writer.writerow(headers)
        
        # Write data rows with indentation for hierarchy
        for idx, row in enumerate(rows):
            level = hierarchy.get(idx, 3)
            
            # Add indentation for hierarchy in first column
            if level > 1 and len(row) > 0:
                indent = '  ' * (level - 1)
                row_with_indent = [indent + str(row[0])] + list(row[1:])
            else:
                row_with_indent = row
            
            writer.writerow(row_with_indent)
        
        # Add footer if present
        if 'footer_rows' in data:
            writer.writerow([])  # Empty row
            for footer_row in data['footer_rows']:
                writer.writerow(footer_row)
        
        # Create response
        content = output.getvalue().encode('utf-8-sig')  # BOM for Excel
        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.csv"
        
        return self._create_response(
            content, 
            filename, 
            'text/csv; charset=utf-8-sig'
        )
