# =====================================================================
# FILE: detail_project/exports/harga_items_adapter.py
# =====================================================================

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List


class HargaItemsAdapter:
    """Data adapter for Harga Items export"""

    def __init__(self, project):
        self.project = project

    def get_export_data(self) -> Dict[str, Any]:
        """
        Transform Harga Items data for export.
        
        Returns 2 pages:
        1. Satuan Dasar - all items priced at the SSOT ``harga_satuan`` (the exact
           value Rincian AHSP / Rekap RAB use).
        2. Satuan Konversi - items with conversion profiles, shown as a RECONCILIATION
           (market price ÷ factor) against ``harga_satuan``, flagged on mismatch.

        WP-P1d (HI-03): the base-unit price is ALWAYS ``harga_satuan`` so this document
        can never disagree with the RAB. The conversion profile is provenance only —
        never a competing price source (Model A: harga_satuan = single SSOT).
        """
        from detail_project.services import used_harga_items_queryset

        # Column configuration for Satuan Dasar
        headers_dasar = ['No', 'Kode', 'Uraian', 'Satuan', 'Harga Satuan (Rp)']
        col_widths_dasar = [12, 25, 80, 25, 40]  # in mm

        # Column configuration for Satuan Konversi (with narrative column)
        headers_konversi = ['No', 'Kode', 'Uraian', 'Keterangan Konversi', 'Harga/Satuan']
        col_widths_konversi = [10, 20, 45, 75, 30]  # in mm - wider for narrative column

        # Fetch harga items
        items_qs = (
            used_harga_items_queryset(self.project)
            .select_related('conversion_profile')
            .order_by('kategori', 'kode_item')
        )

        # Kategori labels
        kategori_labels = {
            'TK': 'TENAGA KERJA',
            'BHN': 'BAHAN',
            'ALT': 'ALAT',
            'LAIN': 'LAINNYA'
        }

        # Group by kategori
        items_by_kategori = {}
        for item in items_qs:
            kategori = item.kategori or 'LAIN'
            if kategori not in items_by_kategori:
                items_by_kategori[kategori] = []
            items_by_kategori[kategori].append(item)

        # Predefined kategori order
        kategori_order = ['TK', 'BHN', 'ALT', 'LAIN']

        # Build rows for satuan dasar table
        satuan_dasar_rows = []
        row_types_dasar = []
        total_items = 0
        row_num = 0
        
        # Also collect items with conversion profiles
        items_with_conversion = []
        
        for kategori in kategori_order:
            if kategori not in items_by_kategori:
                continue

            items = items_by_kategori[kategori]
            
            # Add category header row
            kategori_label = kategori_labels.get(kategori, kategori)
            satuan_dasar_rows.append([kategori_label, '', '', '', ''])
            row_types_dasar.append('category')

            for item in items:
                row_num += 1
                
                # WP-P1d (HI-03): the base-unit price shown here is ALWAYS the SSOT
                # harga_satuan — the same value Rincian AHSP and Rekap RAB use — so
                # the Harga document can never disagree with the RAB. A conversion
                # profile is provenance only; its derived value is shown separately
                # in the konversi table and flagged if it diverges from harga_satuan.
                base_price = item.harga_satuan

                try:
                    if hasattr(item, 'conversion_profile') and item.conversion_profile:
                        conv = item.conversion_profile
                        derived = None
                        if conv.factor_to_base and conv.factor_to_base > 0:
                            derived = (conv.market_price / conv.factor_to_base).quantize(
                                Decimal('0.01'), rounding=ROUND_HALF_UP)
                        mismatch = (
                            derived is not None and base_price is not None
                            and derived != base_price
                        )
                        items_with_conversion.append((item, conv, base_price, derived, mismatch))
                except Exception:
                    pass

                satuan_dasar_rows.append([
                    str(row_num),
                    item.kode_item or '',
                    item.uraian or '',
                    item.satuan or '',
                    self._format_number(base_price, 0),
                ])
                row_types_dasar.append('item')
                total_items += 1

        # Build rows for satuan konversi table
        satuan_konversi_rows = []
        row_types_konversi = []
        
        if items_with_conversion:
            konv_num = 0
            current_kategori = None
            
            for item, conv, base_price, derived, mismatch in items_with_conversion:
                # Add category header if changed
                if item.kategori != current_kategori:
                    current_kategori = item.kategori
                    kategori_label = kategori_labels.get(current_kategori, current_kategori or 'LAIN')
                    satuan_konversi_rows.append([kategori_label, '', '', '', ''])
                    row_types_konversi.append('category')

                konv_num += 1

                # Build narrative text for Keterangan Konversi column
                harga_beli_str = self._format_number(conv.market_price, 0)
                factor_str = self._format_number(conv.factor_to_base, 2)
                derived_str = self._format_number(derived, 0) if derived is not None else '-'
                base_str = self._format_number(base_price, 0) if base_price is not None else '-'
                market_unit = conv.market_unit or 'satuan'
                base_unit = item.satuan or 'satuan'

                # WP-P1d (HI-03): narrative is a RECONCILIATION against the SSOT
                # harga_satuan — never a competing price. Flag when the profile-derived
                # value no longer matches the stored base price (e.g. price negotiated
                # manually after the profile was set).
                keterangan_lines = [
                    f"Harga Beli: Rp {harga_beli_str}/{market_unit}",
                    f"Konversi: 1 {market_unit} = {factor_str} {base_unit}",
                    f"Perhitungan: Rp {harga_beli_str} ÷ {factor_str} = Rp {derived_str}/{base_unit}",
                ]
                if mismatch:
                    keterangan_lines.append(
                        f"⚠ Harga dasar dipakai = Rp {base_str}/{base_unit} (override manual; berbeda dari hasil konversi)"
                    )
                keterangan_konversi = "\n".join(keterangan_lines)

                satuan_konversi_rows.append([
                    str(konv_num),
                    item.kode_item or '',
                    item.uraian or '',
                    keterangan_konversi,
                    f"Rp {base_str}/{base_unit}",
                ])
                row_types_konversi.append('item')

        # Get Profit/Margin info
        try:
            from detail_project.models import ProjectPricing
            pricing = ProjectPricing.objects.filter(project=self.project).first()
            markup_percent = pricing.markup_percent if pricing else Decimal('10.00')
        except Exception:
            markup_percent = Decimal('10.00')

        # Footer rows
        footer_rows = [
            ['Total Items', str(total_items)],
            ['Profit/Margin', f"{self._format_number(markup_percent, 2)}%"],
        ]

        # Build pages
        pages = [
            {
                'title': 'DAFTAR HARGA SATUAN DASAR',
                'table_data': {
                    'headers': headers_dasar,
                    'rows': satuan_dasar_rows,
                },
                'row_types': row_types_dasar,
                'col_widths': col_widths_dasar,
                'footer_rows': footer_rows,
            },
        ]
        
        # Add conversion table only if there are items with conversion profiles
        if satuan_konversi_rows:
            pages.append({
                'title': 'DAFTAR SATUAN KONVERSI',
                'table_data': {
                    'headers': headers_konversi,
                    'rows': satuan_konversi_rows,
                },
                'row_types': row_types_konversi,
                'col_widths': col_widths_konversi,
                'footer_rows': [['Total Items dengan Konversi', str(len(items_with_conversion))]],
            })

        return {
            'pages': pages,
            # Legacy single-table format (for backward compatibility)
            'table_data': {
                'headers': headers_dasar,
                'rows': satuan_dasar_rows,
            },
            'col_widths': col_widths_dasar,
            'footer_rows': footer_rows,
            'row_types': row_types_dasar,
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
