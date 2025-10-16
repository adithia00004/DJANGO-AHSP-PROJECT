# =====================================================================
# FILE: detail_project/exports/rekap_rab_adapter.py
# Copy this entire file
# =====================================================================

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List


class RekapRABAdapter:
    """Data adapter for Rekap RAB export"""
    
    def __init__(self, project):
        self.project = project
    
    def get_export_data(self) -> Dict[str, Any]:
        """Transform Rekap RAB data for export"""
        from detail_project.models import Klasifikasi
        try:
            from detail_project.models import ProjectPricing  # type: ignore
        except Exception:  # fallback if not available
            ProjectPricing = None  # type: ignore
        
        # Use the same computation as the page to ensure parity
        try:
            from detail_project.services import compute_rekap_for_project  # type: ignore
        except Exception:
            compute_rekap_for_project = None  # type: ignore
        
        rows = []
        hierarchy_levels = {}
        row_idx = 0
        
        # Column configuration
        headers = [
            'Uraian Pekerjaan',
            'Kode AHSP',
            'Satuan',
            'Volume',
            'Harga Satuan (Rp)',
            'Jumlah Harga (Rp)'
        ]
        
        col_widths = [90, 35, 25, 25, 40, 45]  # in mm
        
        # Fetch hierarchical containers
        klasifikasi_list = (
            Klasifikasi.objects
            .filter(project=self.project)
            .prefetch_related('sub_list__pekerjaan_list')
            .order_by('ordering_index', 'id')
        )
        
        # Compute pekerjaan values via service for parity with UI
        pkj_map: Dict[int, Dict[str, Any]] = {}
        if compute_rekap_for_project:
            try:
                rows_calc = compute_rekap_for_project(self.project)
                for r in rows_calc:
                    pid = int(r.get('pekerjaan_id'))
                    pkj_map[pid] = r
            except Exception:
                pkj_map = {}
        
        grand_total = Decimal('0')  # total biaya langsung
        summary_by_klas = []
        
        for klas in klasifikasi_list:
            # Klasifikasi header
            rows.append([
                getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi')),
                '',
                '',
                '',
                '',
                '',
            ])
            hierarchy_levels[row_idx] = 1
            klas_header_idx = row_idx
            row_idx += 1
            
            klas_total = Decimal('0')
            
            for sub in klas.sub_list.all().order_by('ordering_index', 'id'):
                # Sub header
                rows.append([
                    getattr(sub, 'name', getattr(sub, 'nama', 'Sub')),
                    '',
                    '',
                    '',
                    '',
                    '',
                ])
                hierarchy_levels[row_idx] = 2
                sub_header_idx = row_idx
                row_idx += 1
                
                sub_total = Decimal('0')
                
                # Pekerjaan items
                for pek in sub.pekerjaan_list.all().order_by('ordering_index', 'id'):
                    # Prefer computed row for exact parity with UI
                    calc = pkj_map.get(int(getattr(pek, 'id', 0)))
                    if calc:
                        uraian = calc.get('uraian') or getattr(pek, 'snapshot_uraian', '')
                        kode = calc.get('kode') or getattr(pek, 'snapshot_kode', '')
                        satuan = calc.get('satuan') or getattr(pek, 'snapshot_satuan', '')
                        volume = self._to_decimal(calc.get('volume', 0))
                        harga_satuan = self._to_decimal(calc.get('G', calc.get('unit_price', 0)))
                        jumlah = self._to_decimal(calc.get('total', 0))
                    else:
                        # Fallback to model values if computation not available
                        if hasattr(pek, 'get_harga_satuan'):
                            harga_satuan = self._to_decimal(pek.get_harga_satuan())
                        else:
                            harga_satuan = self._to_decimal(getattr(pek, 'harga_satuan', 0))
                        volume = self._to_decimal(getattr(pek, 'volume', 0))
                        uraian = getattr(pek, 'snapshot_uraian', getattr(pek, 'nama', getattr(pek, 'name', '')))
                        kode = getattr(pek, 'snapshot_kode', getattr(pek, 'kode_ahsp', ''))
                        satuan = getattr(pek, 'snapshot_satuan', getattr(pek, 'satuan', ''))
                        jumlah = harga_satuan * volume
                    
                    rows.append([
                        uraian,
                        kode or '',
                        satuan or '',
                        self._format_number(volume, 3),
                        self._format_number(harga_satuan, 0),
                        self._format_number(jumlah, 0),
                    ])
                    hierarchy_levels[row_idx] = 3
                    row_idx += 1
                    
                    sub_total += jumlah
                
                # Sub total: place in the same sub header row (Total column)
                if sub_total > 0:
                    rows[sub_header_idx][-1] = self._format_number(sub_total, 0)
                
                klas_total += sub_total
            
            # Klas total: place in the same klas header row (Total column)
            if klas_total > 0:
                rows[klas_header_idx][-1] = self._format_number(klas_total, 0)

            # Append summary per klasifikasi (for pengesahan page)
            summary_by_klas.append([
                getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi')),
                self._format_number(klas_total, 0)
            ])
            
            grand_total += klas_total
        
        # Footer rows (totals)
        # Determine ppn_percent and rounding_base from ProjectPricing if exists
        ppn_pct = None
        rounding_base = None
        if ProjectPricing:
            try:
                pricing = ProjectPricing.objects.filter(project=self.project).first()
                if pricing and hasattr(pricing, 'ppn_percent'):
                    ppn_pct = Decimal(str(pricing.ppn_percent))
                if pricing and hasattr(pricing, 'rounding_base') and pricing.rounding_base:
                    rounding_base = int(pricing.rounding_base)
            except Exception:
                pass

        if ppn_pct is None:
            ppn_pct = Decimal('11')
        if not rounding_base:
            rounding_base = 10000

        ppn_value = (grand_total * ppn_pct / Decimal('100')).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        grand_with_ppn = (grand_total + ppn_value).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        rounded = int((Decimal(grand_with_ppn) / Decimal(rounding_base)).to_integral_value(rounding=ROUND_HALF_UP)) * rounding_base

        footer_rows = [
            ['TOTAL BIAYA LANGSUNG', self._format_number(grand_total, 0)],
            [f'PPN {ppn_pct}%', self._format_number(ppn_value, 0)],
            ['GRAND TOTAL', self._format_number(grand_with_ppn, 0)],
            ['PEMBULATAN', self._format_number(rounded, 0)],
        ]
        
        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'hierarchy_levels': hierarchy_levels,
            'footer_rows': footer_rows,
            'totals': {
                'total_biaya_langsung': grand_total,
                'ppn_percent': ppn_pct,
                'ppn': ppn_value,
                'grand_total': grand_with_ppn,
                'rounding_base': rounding_base,
                'rounded': Decimal(rounded),
            },
            'summary_by_klasifikasi': summary_by_klas,
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
        """Robust conversion to Decimal handling localized strings and None"""
        try:
            if isinstance(val, Decimal):
                return val
            if val is None:
                return Decimal('0')
            # direct try
            return Decimal(str(val))
        except Exception:
            try:
                s = str(val).strip()
                if not s:
                    return Decimal('0')
                # Normalize Indonesian format: remove thousand sep and fix decimal sep
                # If contains both '.' and ',', assume '.' thousands and ',' decimal
                if ',' in s and '.' in s:
                    s = s.replace('.', '')
                    s = s.replace(',', '.')
                elif ',' in s and '.' not in s:
                    # Only comma present: treat as decimal separator
                    s = s.replace(',', '.')
                # Remove any non-numeric trailing/leading characters
                import re
                m = re.search(r"-?[0-9]+(\.[0-9]+)?", s)
                if m:
                    s = m.group(0)
                return Decimal(s)
            except Exception:
                return Decimal('0')
