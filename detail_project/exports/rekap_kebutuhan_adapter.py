# =====================================================================
# FILE: detail_project/exports/rekap_kebutuhan_adapter.py
# =====================================================================

from typing import Dict, Any, List
from collections import Counter
from datetime import date, timedelta
import calendar


class RekapKebutuhanAdapter:
    """Data adapter for Rekap Kebutuhan export"""

    def __init__(self, project, rows=None, summary=None):
        self.project = project
        self.rows_override = rows
        self.summary = summary or {}

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

    def get_export_data(self) -> Dict[str, Any]:
        """Transform Rekap Kebutuhan data (flat) for export"""
        headers = ['Kategori', 'Kode', 'Uraian', 'Satuan', 'Quantity', 'Harga Satuan', 'Total Harga']
        if self.rows_override is not None:
            rows_src = self.rows_override
        else:
            from detail_project.services import compute_kebutuhan_items
            rows_src = compute_kebutuhan_items(self.project)
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
                str(r.get('harga_satuan', '0')),
                str(r.get('harga_total', '0')),
            ])
            counts[kat] += 1

        footer_rows = [
            ['Total Items', str(len(rows_src))],
            ['Tenaga Kerja (TK)', str(counts.get('TK', 0))],
            ['Bahan (BHN)', str(counts.get('BHN', 0))],
            ['Alat (ALT)', str(counts.get('ALT', 0))],
        ]
        summary = getattr(self, 'summary', {}) or {}
        if summary.get('grand_total_cost'):
            footer_rows.append(['Grand Total Harga', str(summary['grand_total_cost'])])

        qty_totals = (self.summary or {}).get('quantity_totals')
        if qty_totals:
            footer_rows.append([
                'Total Quantity',
                f"TK {qty_totals.get('TK', '0')} | "
                f"BHN {qty_totals.get('BHN', '0')} | "
                f"ALT {qty_totals.get('ALT', '0')} | "
                f"LAIN {qty_totals.get('LAIN', '0')}"
            ])

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

        # Column widths for 5 columns (approximate proportions)
        total_width = 277  # A4 landscape content width in mm minus margins
        col_widths = [
            0.10 * total_width,  # Kategori
            0.14 * total_width,  # Kode
            0.36 * total_width,  # Uraian
            0.10 * total_width,  # Satuan
            0.10 * total_width,  # Quantity
            0.10 * total_width,  # Harga Satuan
            0.10 * total_width,  # Total Harga
        ]

        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'footer_rows': footer_rows,
        }
