# =====================================================================
# FILE: detail_project/exports/rekap_kebutuhan_adapter.py
# =====================================================================

from typing import Dict, Any, List
from collections import Counter


class RekapKebutuhanAdapter:
    """Data adapter for Rekap Kebutuhan export"""

    def __init__(self, project):
        self.project = project

    def get_export_data(self) -> Dict[str, Any]:
        """Transform Rekap Kebutuhan data (flat) for export"""
        from detail_project.services import compute_kebutuhan_items

        headers = ['Kategori', 'Kode', 'Uraian', 'Satuan', 'Quantity']

        rows_src: List[Dict[str, Any]] = compute_kebutuhan_items(self.project)
        rows: List[List[str]] = []

        counts = Counter()
        for r in rows_src:
            kat = (r.get('kategori') or '').upper()
            rows.append([
                kat,
                r.get('kode', '') or '-',
                r.get('uraian', '') or '-',
                r.get('satuan', '') or '-',
                str(r.get('quantity', '0')),
            ])
            counts[kat] += 1

        footer_rows = [
            ['Total Items', str(len(rows_src))],
            ['Tenaga Kerja (TK)', str(counts.get('TK', 0))],
            ['Bahan (BHN)', str(counts.get('BHN', 0))],
            ['Alat (ALT)', str(counts.get('ALT', 0))],
        ]

        # Column widths for 5 columns (approximate proportions)
        total_width = 277  # A4 landscape content width in mm minus margins
        col_widths = [
            0.12 * total_width,  # Kategori
            0.15 * total_width,  # Kode
            0.45 * total_width,  # Uraian
            0.13 * total_width,  # Satuan
            0.15 * total_width,  # Quantity
        ]

        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'footer_rows': footer_rows,
        }

