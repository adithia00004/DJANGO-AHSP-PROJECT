# =====================================================================
# FILE: detail_project/exports/harga_items_adapter.py
# =====================================================================

from decimal import Decimal
from typing import Dict, Any, List


class HargaItemsAdapter:
    """Data adapter for Harga Items export"""

    def __init__(self, project):
        self.project = project

    def get_export_data(self) -> Dict[str, Any]:
        """Transform Harga Items data for export"""
        from detail_project.models import HargaItemProject

        rows = []

        # Column configuration
        headers = [
            'Kode Item',
            'Kategori',
            'Uraian',
            'Satuan',
            'Harga Satuan (Rp)'
        ]

        # Column widths for A4 Portrait (210mm width - 20mm margins = 190mm usable)
        col_widths = [25, 25, 85, 25, 30]  # in mm (total: 190mm)

        # Fetch harga items yang digunakan di project
        items_qs = (
            HargaItemProject.objects
            .filter(project=self.project, detail_refs__project=self.project)
            .distinct()
            .order_by('kategori', 'kode_item')
        )

        # Group by kategori for better organization
        items_by_kategori = {}
        for item in items_qs:
            kategori = item.kategori or 'LAIN'
            if kategori not in items_by_kategori:
                items_by_kategori[kategori] = []
            items_by_kategori[kategori].append(item)

        # Predefined kategori order
        kategori_order = ['TK', 'BHN', 'ALT', 'LAIN']

        # Add items grouped by kategori
        total_items = 0
        for kategori in kategori_order:
            if kategori not in items_by_kategori:
                continue

            items = items_by_kategori[kategori]

            for item in items:
                rows.append([
                    item.kode_item or '',
                    item.kategori or '',
                    item.uraian or '',
                    item.satuan or '',
                    self._format_number(item.harga_satuan, 0),
                ])
                total_items += 1

        # Add any remaining categories not in predefined order
        for kategori, items in items_by_kategori.items():
            if kategori in kategori_order:
                continue
            for item in items:
                rows.append([
                    item.kode_item or '',
                    item.kategori or '',
                    item.uraian or '',
                    item.satuan or '',
                    self._format_number(item.harga_satuan, 0),
                ])
                total_items += 1

        # Get Profit/Margin info
        try:
            from detail_project.models import ProjectPricing
            pricing = ProjectPricing.objects.filter(project=self.project).first()
            markup_percent = pricing.markup_percent if pricing else Decimal('10.00')
        except Exception:
            markup_percent = Decimal('10.00')

        # Footer rows - summary info
        footer_rows = [
            ['Total Items', str(total_items)],
            ['Profit/Margin', f"{self._format_number(markup_percent, 2)}%"],
        ]

        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'footer_rows': footer_rows,
        }

    def _format_number(self, value: Any, decimals: int = 2) -> str:
        """Format number Indonesian style"""
        try:
            if value is None or value == '':
                return '-'
            num = Decimal(str(value))
            if decimals == 0:
                formatted = f"{int(round(num)):,}"
            else:
                formatted = f"{float(num):,.{decimals}f}"
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return '-'

    def _to_decimal(self, val: Any) -> Decimal:
        """Robust conversion to Decimal"""
        try:
            if isinstance(val, Decimal):
                return val
            if val is None:
                return Decimal('0')
            return Decimal(str(val))
        except Exception:
            try:
                s = str(val).strip()
                if not s:
                    return Decimal('0')
                # Normalize Indonesian format
                if ',' in s and '.' in s:
                    s = s.replace('.', '')
                    s = s.replace(',', '.')
                elif ',' in s and '.' not in s:
                    s = s.replace(',', '.')
                import re
                m = re.search(r"-?[0-9]+(\.[0-9]+)?", s)
                if m:
                    s = m.group(0)
                return Decimal(s)
            except Exception:
                return Decimal('0')
