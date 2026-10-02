# =====================================================================
# FILE: detail_project/exports/rekap_kebutuhan_adapter.py
# =====================================================================

from typing import Dict, Any, List
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar


class RekapKebutuhanAdapter:
    """Data adapter for Rekap Kebutuhan export"""

    def __init__(self, project, rows=None, summary=None):
        self.project = project
        self.rows_override = rows
        self.summary = summary or {}

    @staticmethod
    def _to_dec(val) -> Decimal:
        """Canonical Decimal at the adapter->exporter boundary (never a locale string)."""
        try:
            if val is None or val == '':
                return Decimal('0')
            if isinstance(val, Decimal):
                return val
            return Decimal(str(val))
        except Exception:
            return Decimal('0')

    @staticmethod
    def _parse_week_value(value: str):
        if not value or "-W" not in value:
            return None
        try:
            year_str, week_str = value.split("-W", 1)
            year = int(year_str)
            week = int(week_str)
            start = date.fromisocalendar(year, week, 1)
            end = start + timedelta(days=6)
            return start, end
        except Exception:
            return None

    @staticmethod
    def _parse_month_value(value: str):
        if not value or "-" not in value:
            return None
        try:
            year_str, month_str = value.split("-", 1)
            year = int(year_str)
            month = int(month_str)
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            return start, end
        except Exception:
            return None

    @classmethod
    def _describe_time_scope(cls, scope: Dict[str, Any]) -> str:
        if not scope:
            return ''
        mode = (scope.get('mode') or '').lower()
        start_raw = scope.get('start') or scope.get('start_value')
        end_raw = scope.get('end') or scope.get('end_value') or start_raw
        if not start_raw:
            return ''

        if mode == 'week':
            rng = cls._parse_week_value(start_raw)
            if rng:
                return f"Minggu {start_raw} ({rng[0].strftime('%d %b')} - {rng[1].strftime('%d %b %Y')})"
            return f"Minggu {start_raw}"
        if mode == 'week_range':
            start_rng = cls._parse_week_value(start_raw)
            end_rng = cls._parse_week_value(end_raw) or start_rng
            if start_rng and end_rng:
                return (
                    f"Minggu {start_raw} - {end_raw} "
                    f"({start_rng[0].strftime('%d %b')} - {end_rng[1].strftime('%d %b %Y')})"
                )
            return f"Minggu {start_raw} - {end_raw}"
        if mode == 'month':
            rng = cls._parse_month_value(start_raw)
            if rng:
                return f"Bulan {start_raw} ({rng[0].strftime('%b %Y')})"
            return f"Bulan {start_raw}"
        if mode == 'month_range':
            start_rng = cls._parse_month_value(start_raw)
            end_rng = cls._parse_month_value(end_raw) or start_rng
            if start_rng and end_rng:
                return (
                    f"Bulan {start_raw} - {end_raw} "
                    f"({start_rng[0].strftime('%b %Y')} - {end_rng[0].strftime('%b %Y')})"
                )
            return f"Bulan {start_raw} - {end_raw}"
        return ''

    def get_export_data(self, unit_mode: str = 'base') -> Dict[str, Any]:
        """
        Transform Rekap Kebutuhan data (flat) for export.
        
        Args:
            unit_mode: 'base' for Satuan Dasar, 'market' for Satuan Beli
                - base: Shows base unit (kg), base quantity, calculated base price
                - market: Shows market unit (batang), converted quantity, market price
        """
        from decimal import Decimal, ROUND_HALF_UP
        from detail_project.models import HargaItemProject, ItemConversionProfile
        
        headers = ['No', 'Kode', 'Uraian', 'Satuan', 'Qty', 'Harga Satuan', 'Total Harga']
        if self.rows_override is not None:
            rows_src = self.rows_override
        else:
            from detail_project.services import compute_kebutuhan_items
            rows_src = compute_kebutuhan_items(self.project)
        
        # If market mode, build conversion profile lookup
        conversion_map = {}
        if unit_mode == 'market':
            # Get all HargaItemProject kode -> conversion profile mapping
            harga_items = HargaItemProject.objects.filter(
                project=self.project
            ).select_related('conversion_profile')
            
            for hi in harga_items:
                try:
                    if hasattr(hi, 'conversion_profile') and hi.conversion_profile:
                        conv = hi.conversion_profile
                        if conv.factor_to_base and conv.factor_to_base > 0:
                            conversion_map[hi.kode_item] = {
                                'market_unit': conv.market_unit or hi.satuan,
                                'market_price': conv.market_price,
                                'factor_to_base': conv.factor_to_base,
                            }
                except Exception:
                    pass
        
        rows: List[List[str]] = []
        row_kategori: List[str] = []  # kategori per baris (pengelompokan template standar)
        counts = Counter()
        
        for r in rows_src:
            kat = (r.get('kategori') or '').upper()
            kode = r.get('kode', '') or '-'
            uraian = r.get('uraian', '') or '-'
            satuan = r.get('satuan', '') or '-'
            quantity = r.get('quantity', 0)
            harga_satuan = r.get('harga_satuan', 0)
            harga_total = r.get('harga_total', 0)
            
            # Apply unit mode conversion if market mode and has conversion profile
            if unit_mode == 'market' and kode in conversion_map:
                conv = conversion_map[kode]
                try:
                    # Convert quantity: base_qty / factor_to_base = market_qty
                    base_qty = Decimal(str(quantity)) if quantity else Decimal('0')
                    factor = Decimal(str(conv['factor_to_base']))
                    market_qty = (base_qty / factor).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                    
                    # Replace with market values (keep Decimal — owner contract:
                    # Decimal on the adapter->exporter path, never float).
                    satuan = conv['market_unit']
                    quantity = market_qty
                    harga_satuan = Decimal(str(conv['market_price']))
                    # Total stays the same (market_qty * market_price = base_qty * base_price)
                except Exception:
                    pass  # Keep original values on error

            # WP Export (all Option A): emit canonical Decimal; the exporter writes
            # real Excel numbers at its boundary (Qty 3 dp, money 2 dp). Values are
            # unchanged — only their representation — so the scheduled/unscheduled
            # split and the totals stay identical.
            rows.append([
                str(len(rows) + 1),  # No (1-indexed)
                kode,
                uraian,
                satuan,
                self._to_dec(quantity),
                self._to_dec(harga_satuan),
                self._to_dec(harga_total),
            ])
            counts[kat] += 1
            row_kategori.append(kat)

        footer_rows = [
            ['Total Items', str(len(rows_src))],
            ['Tenaga Kerja (TK)', str(counts.get('TK', 0))],
            ['Bahan (BHN)', str(counts.get('BHN', 0))],
            ['Alat (ALT)', str(counts.get('ALT', 0))],
        ]
        
        # Add unit mode indicator to footer
        mode_label = 'Satuan Dasar' if unit_mode == 'base' else 'Satuan Beli'
        footer_rows.append(['Mode Satuan', mode_label])
        
        summary = getattr(self, 'summary', {}) or {}
        if summary.get('grand_total_cost'):
            footer_rows.append(['Grand Total Harga', self._to_dec(summary['grand_total_cost'])])

        # Baris "Total Quantity per kategori" DIHAPUS — keputusan owner
        # 2026-07-13 (registri R-18): agregat kuantitas lintas satuan tidak
        # relevan di footer. Jangan ditambahkan kembali tanpa keputusan baru.

        filters_meta = self.summary.get('filters') if self.summary else None
        if self.summary.get('filters_applied') and filters_meta:
            parts = []
            if self.summary.get('mode') == 'tahapan' and self.summary.get('tahapan_id'):
                parts.append(f"Tahapan #{self.summary['tahapan_id']}")
            if filters_meta.get('klasifikasi_ids'):
                parts.append(f"Klasifikasi: {', '.join(map(str, filters_meta['klasifikasi_ids']))}")
            if filters_meta.get('sub_klasifikasi_ids'):
                parts.append(f"Sub: {', '.join(map(str, filters_meta['sub_klasifikasi_ids']))}")
            if filters_meta.get('kategori_items'):
                parts.append(f"Kategori: {', '.join(filters_meta['kategori_items'])}")
            if filters_meta.get('pekerjaan_ids'):
                parts.append(f"Pekerjaan: {len(filters_meta['pekerjaan_ids'])} dipilih")
            if self.summary.get('search'):
                parts.append(f"Cari: \"{self.summary['search']}\"")
            if self.summary.get('time_scope_active') and self.summary.get('time_scope'):
                label = self._describe_time_scope(self.summary.get('time_scope'))
                if label:
                    parts.append(f"Waktu: {label}")
            footer_rows.append([
                'Filters',
                ' | '.join(parts) if parts else 'Aktif'
            ])

        # Column widths for A4 Portrait (raw values in mm)
        # A4 portrait: 210mm, margins: 10+10=20mm, usable: ~190mm
        col_widths = [
            8,     # No
            18,    # Kode
            64,    # Uraian (widest)
            14,    # Satuan
            20,    # Qty
            30,    # Harga Satuan
            36,    # Total Harga
        ]  # Total: 190mm

        # Determine if charts should be included
        # Charts are ONLY included when exporting full project data (no time filter)
        time_scope_active = self.summary.get('time_scope_active', False)
        include_charts = not time_scope_active

        # Build chart data for distribution chart (only if including charts)
        chart_data = None
        if include_charts:
            # Calculate category totals for pie chart
            category_totals = {}
            for r in rows_src:
                kat = (r.get('kategori') or 'LAIN').upper()
                total = float(r.get('harga_total', 0) or 0)
                category_totals[kat] = category_totals.get(kat, 0) + total

            chart_data = {
                'distribution': {
                    'labels': list(category_totals.keys()),
                    'values': list(category_totals.values()),
                },
                'counts': dict(counts),
            }

        return {
            'row_kategori': row_kategori,
            'table_data': {
                'headers': headers,
                'rows': rows,
                # No/Kode/Uraian/Satuan text; Qty 3 dp; Harga & Total 2 dp.
                'column_formats': ['@', '@', '@', '@', '#,##0.000', '#,##0.00', '#,##0.00'],
            },
            'col_widths': col_widths,
            'footer_rows': footer_rows,
            'footer_value_format': '#,##0.00',
            'include_charts': include_charts,
            'chart_data': chart_data,
            'unit_mode': unit_mode,
        }

