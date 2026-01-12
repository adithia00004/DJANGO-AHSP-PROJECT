# =====================================================================
# FILE: detail_project/exports/volume_pekerjaan_adapter.py
# Enhanced export adapter for Volume Pekerjaan
# - 2 Segments: Parameters + Volume/Formula
# - Excel formula references support
# - Signature page aligned with Harga Items
# =====================================================================

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
import re


class VolumePekerjaanAdapter:
    """Data adapter for Volume Pekerjaan export"""

    def __init__(self, project, include_signatures: bool = True, parameters: dict = None):
        self.project = project
        self.include_signatures = include_signatures
        self.parameters = parameters or {}  # { 'panjang': 100.0, 'lebar': 50.0, ... }
        self._parameter_cells = {}  # For Excel formula references: {'panjang': 'B2', ...}

    def get_export_data(self) -> Dict[str, Any]:
        """
        Transform Volume Pekerjaan data for export.
        
        Returns structured data with 2 segments:
        1. Parameter Perhitungan - table of parameters with codes and values
        2. Volume & Formula - work items with formulas and calculated volumes
        """
        from detail_project.models import Klasifikasi, VolumePekerjaan, VolumeFormulaState

        # Fetch hierarchical containers with volume data
        klasifikasi_list = (
            Klasifikasi.objects
            .filter(project=self.project)
            .prefetch_related('sub_list__pekerjaan_list')
            .order_by('ordering_index', 'id')
        )

        # Fetch all volumes at once for efficiency
        vol_map = {}
        all_volume_qs = VolumePekerjaan.objects.filter(project=self.project).values('pekerjaan_id', 'quantity')
        for v in all_volume_qs:
            vol_map[v['pekerjaan_id']] = self._to_decimal(v['quantity'])

        # Fetch all formula states
        formula_map = {}
        formula_qs = VolumeFormulaState.objects.filter(project=self.project)
        for fs in formula_qs:
            formula_map[fs.pekerjaan_id] = {
                'raw': fs.raw or '',
                'is_fx': fs.is_fx,
            }

        # ===== SEGMENT 1: PARAMETER PERHITUNGAN =====
        param_page = self._build_parameter_segment()

        # ===== SEGMENT 2: VOLUME & FORMULA =====
        volume_page = self._build_volume_segment(klasifikasi_list, vol_map, formula_map)

        # Build signature data (same as Harga Items)
        signature_data = None
        if self.include_signatures:
            signature_data = {
                'left_title': 'Disetujui Oleh,',
                'left_name': '...........................',
                'left_position': 'Pejabat Pembuat Komitmen',
                'right_title': 'Dibuat Oleh,',
                'right_name': '...........................',
                'right_position': 'Konsultan Perencana',
            }

        return {
            'pages': [volume_page, param_page],  # Volume first, then Parameters as appendix
            'include_signatures': self.include_signatures,
            'signature_data': signature_data,
            'parameter_cells': self._parameter_cells,  # For Excel formula references
        }

    def _build_parameter_segment(self) -> Dict[str, Any]:
        """Build Segment 1: Parameter Perhitungan"""
        from detail_project.models import VolumeFormulaState

        # Get all formulas for this project
        formulas = VolumeFormulaState.objects.filter(
            project=self.project,
            is_fx=True
        ).values_list('raw', flat=True)

        # Extract all variable names from formulas
        params_from_formulas = set()
        for formula in formulas:
            if not formula or not formula.strip():
                continue
            # Extract variable names (lowercase alphanumeric + underscore)
            variables = re.findall(r'\b([a-z_][a-z0-9_]*)\b', formula.lower())
            for var in variables:
                # Filter out common keywords and functions
                if var not in ['sum', 'min', 'max', 'round', 'abs', 'floor', 'ceil', 'sqrt', 'pow']:
                    params_from_formulas.add(var)

        # Merge with provided parameters
        all_params = params_from_formulas | set(self.parameters.keys())

        # Column configuration
        headers = ['No', 'Kode Parameter', 'Nama Parameter', 'Nilai']
        col_widths = [12, 40, 80, 50]  # in mm (total: 182mm for A4)

        rows = []
        row_num = 0

        for param in sorted(all_params):
            row_num += 1
            # Convert code to label
            label = param.replace('_', ' ').title()

            # Get value if available
            value = self.parameters.get(param, 0)
            if isinstance(value, (int, float, Decimal)):
                value_str = self._format_number(value, 2)
            else:
                value_str = str(value) if value else '-'

            rows.append([str(row_num), param, label, value_str])

            # Store cell reference for Excel (row_num + 1 because of header row)
            self._parameter_cells[param] = f'D{row_num + 1}'

        # Empty state
        if not rows:
            rows.append(['', '-', 'Tidak ada parameter', '-'])

        return {
            'title': 'DAFTAR PARAMETER PERHITUNGAN',
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'row_types': ['item'] * len(rows),
        }

    def _build_volume_segment(self, klasifikasi_list, vol_map, formula_map) -> Dict[str, Any]:
        """Build Segment 2: Volume & Formula"""
        
        # Column configuration (no empty columns)
        headers = ['No', 'Uraian Pekerjaan', 'Formula', 'Satuan', 'Volume']
        col_widths = [10, 70, 55, 20, 27]  # in mm (total: 182mm for A4)

        rows = []
        row_types = []
        hierarchy_levels = {}
        row_idx = 0
        item_num = 0

        for klas in klasifikasi_list:
            # Klasifikasi header
            klas_name = getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi'))
            rows.append([klas_name, '', '', '', ''])
            row_types.append('category')
            hierarchy_levels[row_idx] = 1
            row_idx += 1

            for sub in klas.sub_list.all().order_by('ordering_index', 'id'):
                # Sub header
                sub_name = getattr(sub, 'name', getattr(sub, 'nama', 'Sub'))
                rows.append([sub_name, '', '', '', ''])
                row_types.append('category')
                hierarchy_levels[row_idx] = 2
                row_idx += 1

                # Pekerjaan items
                for pek in sub.pekerjaan_list.all().order_by('ordering_index', 'id'):
                    item_num += 1
                    uraian = getattr(pek, 'snapshot_uraian', getattr(pek, 'nama', getattr(pek, 'name', '')))
                    satuan = getattr(pek, 'snapshot_satuan', getattr(pek, 'satuan', ''))
                    volume = vol_map.get(pek.id, Decimal('0'))

                    # Get formula if exists
                    formula_info = formula_map.get(pek.id, {})
                    formula_raw = formula_info.get('raw', '')
                    is_fx = formula_info.get('is_fx', False)

                    # Display formula or "-"
                    formula_display = formula_raw if is_fx and formula_raw else '-'

                    rows.append([
                        str(item_num),
                        uraian,
                        formula_display,
                        satuan or '-',
                        self._format_number(volume, 3),
                    ])
                    row_types.append('item')
                    hierarchy_levels[row_idx] = 3
                    row_idx += 1

        # Summary footer
        footer_rows = [
            ['Total Pekerjaan', str(item_num)],
        ]

        return {
            'title': 'VOLUME PEKERJAAN',
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'row_types': row_types,
            'hierarchy_levels': hierarchy_levels,
            'footer_rows': footer_rows,
        }

    def _format_number(self, value: Any, decimals: int = 2) -> str:
        """Format number Indonesian style"""
        try:
            if value is None or value == '':
                return '-'
            num = Decimal(str(value))
            if num == 0:
                return '0'
            if decimals == 0:
                formatted = f"{int(round(num)):,}"
            else:
                # Remove trailing zeros
                formatted = f"{float(num):,.{decimals}f}".rstrip('0').rstrip('.')
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
                m = re.search(r"-?[0-9]+(\.[0-9]+)?", s)
                if m:
                    s = m.group(0)
                return Decimal(s)
            except Exception:
                return Decimal('0')

    def convert_formula_to_excel(self, formula_str: str, sheet_name: str = 'Parameters') -> str:
        """
        Convert volume formula to Excel formula with cell references.
        
        Example:
            Input: "= panjang * lebar * tinggi"
            Output: "=Parameters!$D$2*Parameters!$D$3*Parameters!$D$4"
        """
        if not formula_str or not formula_str.strip().startswith('='):
            return formula_str

        excel_formula = formula_str.strip()

        # Replace each parameter with its cell reference
        for param, cell_ref in self._parameter_cells.items():
            # Use word boundary to avoid partial replacements
            pattern = r'\b' + re.escape(param) + r'\b'
            replacement = f"'{sheet_name}'!${cell_ref.replace(str(int(cell_ref[1:])), '$' + cell_ref[1:])}"
            excel_formula = re.sub(pattern, replacement, excel_formula, flags=re.IGNORECASE)

        return excel_formula
