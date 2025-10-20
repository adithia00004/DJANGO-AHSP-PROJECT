# =====================================================================
# FILE: detail_project/exports/volume_pekerjaan_adapter.py
# =====================================================================

from decimal import Decimal
from typing import Dict, Any, List
import re
import json


class VolumePekerjaanAdapter:
    """Data adapter for Volume Pekerjaan export"""

    def __init__(self, project, include_appendix: bool = True, parameters: dict = None):
        self.project = project
        self.include_appendix = include_appendix
        self.parameters = parameters or {}  # { 'panjang': 100.0, 'lebar': 50.0, ... }

    def get_export_data(self) -> Dict[str, Any]:
        """Transform Volume Pekerjaan data for export"""
        from detail_project.models import Klasifikasi, VolumePekerjaan

        rows = []
        hierarchy_levels = {}
        row_idx = 0

        # Column configuration
        headers = [
            'Uraian Pekerjaan',
            'Kode AHSP',
            'Satuan',
            'Volume'
        ]

        # Column widths for A4 Portrait (210mm width - 20mm margins = 190mm usable)
        col_widths = [95, 45, 25, 25]  # in mm (total: 190mm)

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

        total_items = 0

        for klas in klasifikasi_list:
            # Klasifikasi header
            rows.append([
                getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi')),
                '',
                '',
                '',
            ])
            hierarchy_levels[row_idx] = 1
            row_idx += 1

            for sub in klas.sub_list.all().order_by('ordering_index', 'id'):
                # Sub header
                rows.append([
                    getattr(sub, 'name', getattr(sub, 'nama', 'Sub')),
                    '',
                    '',
                    '',
                ])
                hierarchy_levels[row_idx] = 2
                row_idx += 1

                # Pekerjaan items
                for pek in sub.pekerjaan_list.all().order_by('ordering_index', 'id'):
                    uraian = getattr(pek, 'snapshot_uraian', getattr(pek, 'nama', getattr(pek, 'name', '')))
                    kode = getattr(pek, 'snapshot_kode', getattr(pek, 'kode_ahsp', ''))
                    satuan = getattr(pek, 'snapshot_satuan', getattr(pek, 'satuan', ''))
                    volume = vol_map.get(pek.id, Decimal('0'))

                    rows.append([
                        uraian,
                        kode or '',
                        satuan or '',
                        self._format_number(volume, 3),
                    ])
                    hierarchy_levels[row_idx] = 3
                    row_idx += 1
                    total_items += 1

        # Footer rows - summary info
        footer_rows = [
            ['Total Pekerjaan', str(total_items)],
        ]

        # Page 1: Main volume table
        page1 = {
            'title': 'VOLUME PEKERJAAN',
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'hierarchy_levels': hierarchy_levels,
            'footer_rows': footer_rows,
        }

        # If appendix not requested, return single page
        if not self.include_appendix:
            return page1

        # Page 2: Appendix with parameters and formulas
        page2_sections = []

        # Build parameter table
        param_table = self._build_parameter_table()
        if param_table:
            page2_sections.append({
                'section_title': 'LAMPIRAN A: PARAMETER PERHITUNGAN',
                'table_data': param_table['table_data'],
                'col_widths': param_table['col_widths'],
            })

        # Build formula table
        formula_table = self._build_formula_table(klasifikasi_list, vol_map)
        if formula_table:
            page2_sections.append({
                'section_title': 'LAMPIRAN B: FORMULA PERHITUNGAN',
                'table_data': formula_table['table_data'],
                'col_widths': formula_table['col_widths'],
                'hierarchy_levels': formula_table.get('hierarchy_levels', {}),
            })

        # If no appendix data, return single page
        if not page2_sections:
            return page1

        # Return multi-page structure
        return {
            'pages': [
                page1,
                {
                    'title': 'LAMPIRAN: PARAMETER DAN FORMULA',
                    'sections': page2_sections,
                }
            ]
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

    def _build_parameter_table(self) -> Dict[str, Any]:
        """
        Build parameter table with values
        Parameters can be passed via constructor or extracted from formulas
        """
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
            # Pattern: word characters that are not numbers
            variables = re.findall(r'\b([a-z_][a-z0-9_]*)\b', formula.lower())
            for var in variables:
                # Filter out common keywords and functions
                if var not in ['sum', 'min', 'max', 'round', 'abs', 'floor', 'ceil', 'sqrt']:
                    params_from_formulas.add(var)

        # Merge with provided parameters
        all_params = params_from_formulas | set(self.parameters.keys())

        if not all_params:
            return None

        # Build table with values
        headers = ['Nama Parameter', 'Kode', 'Nilai']
        rows = []

        for param in sorted(all_params):
            # Convert code to label (capitalize first letter, replace underscore with space)
            label = param.replace('_', ' ').title()

            # Get value if available
            value = self.parameters.get(param, '-')
            if isinstance(value, (int, float, Decimal)):
                value_str = self._format_number(value, 2)
            else:
                value_str = str(value) if value else '-'

            rows.append([
                label,
                param,
                value_str
            ])

        # Column widths for A4 Portrait (190mm usable)
        col_widths = [70, 60, 60]  # in mm

        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
        }

    def _build_formula_table(self, klasifikasi_list, vol_map) -> Dict[str, Any]:
        """Build formula table showing which pekerjaan use formulas"""
        from detail_project.models import VolumeFormulaState

        # Get all formula states
        formula_states = {
            fs.pekerjaan_id: fs
            for fs in VolumeFormulaState.objects.filter(
                project=self.project,
                is_fx=True
            ).select_related('pekerjaan')
        }

        if not formula_states:
            return None

        headers = ['No', 'Uraian Pekerjaan', 'Formula', 'Volume']
        rows = []
        hierarchy_levels = {}
        row_idx = 0
        counter = 1

        for klas in klasifikasi_list:
            # Klasifikasi header
            rows.append([
                '',
                getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi')),
                '',
                '',
            ])
            hierarchy_levels[row_idx] = 1
            row_idx += 1

            for sub in klas.sub_list.all().order_by('ordering_index', 'id'):
                # Sub header
                rows.append([
                    '',
                    getattr(sub, 'name', getattr(sub, 'nama', 'Sub')),
                    '',
                    '',
                ])
                hierarchy_levels[row_idx] = 2
                row_idx += 1

                # Pekerjaan items (only those with formulas)
                for pek in sub.pekerjaan_list.all().order_by('ordering_index', 'id'):
                    if pek.id not in formula_states:
                        continue  # Skip pekerjaan without formula

                    uraian = getattr(pek, 'snapshot_uraian', getattr(pek, 'nama', getattr(pek, 'name', '')))
                    volume = vol_map.get(pek.id, Decimal('0'))
                    formula_raw = formula_states[pek.id].raw

                    rows.append([
                        str(counter),
                        uraian,
                        formula_raw or '-',
                        self._format_number(volume, 3),
                    ])
                    hierarchy_levels[row_idx] = 3
                    row_idx += 1
                    counter += 1

        if counter == 1:  # No formulas found
            return None

        # Column widths for A4 Portrait (190mm usable)
        col_widths = [15, 75, 60, 40]  # in mm

        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'hierarchy_levels': hierarchy_levels,
        }
