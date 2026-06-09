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


FORMULA_BUILTIN_IDENTIFIERS = {
    'sum', 'min', 'max', 'round', 'abs', 'floor', 'ceil',
    'sqrt', 'pow', 'pi', 'e', 'true', 'false',
}


class VolumePekerjaanAdapter:
    """Data adapter for Volume Pekerjaan export"""

    def __init__(self, project, include_signatures: bool = True, parameters: dict = None):
        self.project = project
        self.include_signatures = include_signatures
        self.parameters = self._normalize_parameters_payload(parameters)  # { 'bp_1': 100.0, ... }
        self._parameter_cells = {}  # For Excel formula references: {'panjang': 'B2', ...}
        self._name_to_label: Dict[str, str] = {}
        self._name_to_value: Dict[str, Any] = {}
        self._name_to_unit: Dict[str, str] = {}

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

        self._name_to_label, self._name_to_value, self._name_to_unit = self._load_parameter_metadata()

        # ===== SEGMENT 1: PARAMETER PERHITUNGAN =====
        param_page = self._build_parameter_segment(formula_map)

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

    def _build_parameter_segment(self, formula_map: Optional[Dict[int, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Build Segment 1: Parameter Perhitungan"""
        params_from_formulas = set()
        formula_map = formula_map or {}

        for formula_info in formula_map.values():
            if not formula_info.get('is_fx'):
                continue
            formula = formula_info.get('raw', '')
            if not formula or not formula.strip():
                continue
            params_from_formulas.update(self._extract_identifiers(formula))

        # Merge parameters detected from formulas + provided values + DB metadata.
        all_params = (
            params_from_formulas
            | set(self.parameters.keys())
            | set(self._name_to_label.keys())
            | set(self._name_to_value.keys())
        )

        # User-facing export is label-first. Do not expose opaque code column.
        headers = ['No', 'Nama Parameter', 'Nilai', 'Satuan']
        col_widths = [12, 92, 38, 40]  # in mm (total: 182mm for A4)

        rows = []
        param_codes = []
        row_num = 0

        for param in sorted(all_params, key=self._sort_param_key):
            row_num += 1
            # Prefer DB label. Fallback to compact generated text.
            label = self._name_to_label.get(param) or param.replace('_', ' ').title()

            # Value priority: explicit request payload > DB snapshot > default 0
            value = self.parameters.get(param, self._name_to_value.get(param, 0))
            unit = str(self._name_to_unit.get(param, '') or '-').strip() or '-'
            if isinstance(value, (int, float, Decimal)):
                value_str = self._format_number(value, 2)
            else:
                value_str = str(value) if value else '-'

            rows.append([str(row_num), label, value_str, unit])
            param_codes.append(param)

            # Store value cell reference for Excel (column C after header change).
            self._parameter_cells[param] = f'C{row_num + 1}'

        # Empty state
        if not rows:
            rows.append(['', '-', 'Tidak ada parameter', '-'])
            param_codes.append('')

        return {
            'title': 'DAFTAR PARAMETER PERHITUNGAN',
            'table_data': {
                'headers': headers,
                'rows': rows,
                'param_codes': param_codes,  # aligned with rows, used by XLSX exporter
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
        row_formulas: List[str] = []  # raw formula aligned with rows
        row_pekerjaan_ids: List[Optional[int]] = []  # pekerjaan_id aligned with rows
        row_idx = 0
        item_num = 0

        for klas in klasifikasi_list:
            # Klasifikasi header
            klas_name = getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi'))
            rows.append([klas_name, '', '', '', ''])
            row_types.append('category')
            hierarchy_levels[row_idx] = 1
            row_formulas.append('')
            row_pekerjaan_ids.append(None)
            row_idx += 1

            for sub in klas.sub_list.all().order_by('ordering_index', 'id'):
                # Sub header
                sub_name = getattr(sub, 'name', getattr(sub, 'nama', 'Sub'))
                rows.append([sub_name, '', '', '', ''])
                row_types.append('category')
                hierarchy_levels[row_idx] = 2
                row_formulas.append('')
                row_pekerjaan_ids.append(None)
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

                    # Display formula with human-readable labels or "-"
                    formula_display = self._humanize_formula(formula_raw) if is_fx and formula_raw else '-'

                    rows.append([
                        str(item_num),
                        uraian,
                        formula_display,
                        satuan or '-',
                        self._format_number(volume, 3),
                    ])
                    row_types.append('item')
                    hierarchy_levels[row_idx] = 3
                    row_formulas.append(formula_raw if (is_fx and formula_raw) else '')
                    row_pekerjaan_ids.append(pek.id)
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
            'row_formulas': row_formulas,
            'row_pekerjaan_ids': row_pekerjaan_ids,
            'footer_rows': footer_rows,
            'formula_display_mode': 'label',
        }

    def _load_parameter_metadata(self) -> tuple[Dict[str, str], Dict[str, Any], Dict[str, str]]:
        """Load parameter/computed labels and values for human-readable export."""
        from detail_project.models import ProjectParameter, ProjectComputedParameter

        name_to_label: Dict[str, str] = {}
        name_to_value: Dict[str, Any] = {}
        name_to_unit: Dict[str, str] = {}

        for row in ProjectParameter.objects.filter(project=self.project).values('name', 'label', 'value', 'unit'):
            name = str(row.get('name') or '').strip().lower()
            if not name:
                continue
            label = str(row.get('label') or '').strip()
            name_to_label[name] = label or name
            name_to_value[name] = row.get('value')
            name_to_unit[name] = str(row.get('unit') or '').strip()

        for row in ProjectComputedParameter.objects.filter(project=self.project).values('name', 'label', 'unit'):
            name = str(row.get('name') or '').strip().lower()
            if not name:
                continue
            label = str(row.get('label') or '').strip()
            name_to_label[name] = label or name
            name_to_unit[name] = str(row.get('unit') or '').strip()

        return name_to_label, name_to_value, name_to_unit

    @staticmethod
    def _sort_param_key(param_name: str):
        text = str(param_name or '')
        match = re.match(r'^(bp|cp)_(\d+)$', text)
        if not match:
            return (2, text)
        prefix, num = match.groups()
        group = 0 if prefix == 'bp' else 1
        return (group, int(num), text)

    @staticmethod
    def _extract_identifiers(expr: str) -> set[str]:
        """Extract identifier tokens from a formula expression."""
        from detail_project.formula_tokenizer import tokenize_formula

        output = set()
        for token_type, token_raw, _start, _end in tokenize_formula(expr or ''):
            if token_type != 'id':
                continue
            ident = str(token_raw or '').strip().lower()
            if not ident or ident in FORMULA_BUILTIN_IDENTIFIERS:
                continue
            output.add(ident)
        return output

    def _humanize_formula(self, formula_raw: str) -> str:
        """Translate opaque codes in formula to human labels for export display."""
        from detail_project.formula_tokenizer import remap_expression

        if not formula_raw:
            return formula_raw

        label_map = {
            str(code): str(label)
            for code, label in self._name_to_label.items()
            if code and label and str(code).lower() not in FORMULA_BUILTIN_IDENTIFIERS
        }
        return remap_expression(formula_raw, label_map)

    @staticmethod
    def _normalize_parameters_payload(parameters: Optional[dict]) -> Dict[str, Any]:
        """
        Normalize parameter payload from export endpoint query string.

        Accepts:
        - {'bp_1': 10}
        - {'BP_1': {'value': 10}}
        """
        if not isinstance(parameters, dict):
            return {}

        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in parameters.items():
            key = str(raw_key or '').strip().lower()
            if not key:
                continue

            value = raw_value
            if isinstance(raw_value, dict):
                if 'value' in raw_value:
                    value = raw_value.get('value')
                elif 'nilai' in raw_value:
                    value = raw_value.get('nilai')

            normalized[key] = value
        return normalized

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
