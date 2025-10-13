# =====================================================================
# FILE: detail_project/exports/rekap_rab_adapter.py
# Copy this entire file
# =====================================================================

from decimal import Decimal
from typing import Dict, Any, List


class RekapRABAdapter:
    """Data adapter for Rekap RAB export"""
    
    def __init__(self, project):
        self.project = project
    
    def get_export_data(self) -> Dict[str, Any]:
        """Transform Rekap RAB data for export"""
        from detail_project.models import Klasifikasi
        
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
        
        # Fetch data
        klasifikasi_list = Klasifikasi.objects.filter(
            project=self.project
        ).prefetch_related(
            'subklasifikasi_set__pekerjaan_set'
        ).order_by('urutan')
        
        grand_total = Decimal('0')
        
        for klas in klasifikasi_list:
            # Klasifikasi header
            rows.append([
                klas.nama,
                '',
                '',
                '',
                '',
                '',
            ])
            hierarchy_levels[row_idx] = 1
            row_idx += 1
            
            klas_total = Decimal('0')
            
            for sub in klas.subklasifikasi_set.all().order_by('urutan'):
                # Sub header
                rows.append([
                    sub.nama,
                    '',
                    '',
                    '',
                    '',
                    '',
                ])
                hierarchy_levels[row_idx] = 2
                row_idx += 1
                
                sub_total = Decimal('0')
                
                # Pekerjaan items
                for pek in sub.pekerjaan_set.all().order_by('urutan'):
                    # Get harga satuan from pekerjaan method
                    harga_satuan = pek.get_harga_satuan() if hasattr(pek, 'get_harga_satuan') else Decimal('0')
                    volume = Decimal(str(pek.volume or 0))
                    jumlah = harga_satuan * volume
                    
                    rows.append([
                        pek.nama,
                        pek.kode_ahsp or '',
                        pek.satuan or '',
                        self._format_number(volume, 3),
                        self._format_number(harga_satuan, 0),
                        self._format_number(jumlah, 0),
                    ])
                    hierarchy_levels[row_idx] = 3
                    row_idx += 1
                    
                    sub_total += jumlah
                
                # Sub subtotal
                if sub_total > 0:
                    rows.append([
                        f'Jumlah {sub.nama}',
                        '',
                        '',
                        '',
                        '',
                        self._format_number(sub_total, 0),
                    ])
                    hierarchy_levels[row_idx] = 2
                    row_idx += 1
                
                klas_total += sub_total
            
            # Klas subtotal
            if klas_total > 0:
                rows.append([
                    f'Jumlah {klas.nama}',
                    '',
                    '',
                    '',
                    '',
                    self._format_number(klas_total, 0),
                ])
                hierarchy_levels[row_idx] = 1
                row_idx += 1
            
            grand_total += klas_total
        
        # Footer rows (totals)
        ppn_pct = getattr(self.project, 'ppn_percentage', None) or Decimal('11')
        ppn_value = grand_total * ppn_pct / Decimal('100')
        grand_with_ppn = grand_total + ppn_value
        
        footer_rows = [
            ['JUMLAH', self._format_number(grand_total, 0)],
            [f'PPN {ppn_pct}%', self._format_number(ppn_value, 0)],
            ['TOTAL + PPN', self._format_number(grand_with_ppn, 0)],
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
                'subtotal': grand_total,
                'ppn': ppn_value,
                'grand_total': grand_with_ppn,
            }
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
