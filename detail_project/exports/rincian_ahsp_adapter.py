# =====================================================================
# FILE: detail_project/exports/rincian_ahsp_adapter.py
# =====================================================================

from decimal import Decimal
from typing import Dict, Any, List


class RincianAHSPAdapter:
    """Data adapter for Rincian AHSP (Detail AHSP) export"""

    def __init__(self, project):
        self.project = project

    def get_export_data(self) -> Dict[str, Any]:
        """
        Transform Rincian AHSP data for export.
        This exports all DetailAHSPProject records grouped by Pekerjaan.
        """
        from detail_project.models import Klasifikasi, DetailAHSPProject

        rows = []
        hierarchy_levels = {}
        row_idx = 0

        # Column configuration
        headers = [
            'Uraian Pekerjaan / Item',
            'Kode',
            'Kategori',
            'Satuan',
            'Koefisien',
            'Harga Satuan (Rp)',
            'Jumlah (Rp)'
        ]

        # Column widths for A4 Landscape (297mm width - 20mm margins = 277mm usable)
        col_widths = [90, 35, 25, 25, 30, 36, 36]  # in mm (total: 277mm)

        # Fetch hierarchical containers with detail AHSP
        klasifikasi_list = (
            Klasifikasi.objects
            .filter(project=self.project)
            .prefetch_related('sub_list__pekerjaan_list')
            .order_by('ordering_index', 'id')
        )

        # Fetch all details at once for efficiency
        all_details = DetailAHSPProject.objects.filter(
            project=self.project
        ).select_related('harga_item').order_by('pekerjaan_id', 'kategori', 'id')

        # Group details by pekerjaan_id
        details_by_pekerjaan = {}
        for detail in all_details:
            pkj_id = detail.pekerjaan_id
            if pkj_id not in details_by_pekerjaan:
                details_by_pekerjaan[pkj_id] = []
            details_by_pekerjaan[pkj_id].append(detail)

        total_pekerjaan = 0
        total_items = 0

        for klas in klasifikasi_list:
            # Klasifikasi header
            rows.append([
                getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi')),
                '',
                '',
                '',
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
                    '',
                    '',
                    '',
                ])
                hierarchy_levels[row_idx] = 2
                row_idx += 1

                # Pekerjaan items
                for pek in sub.pekerjaan_list.all().order_by('ordering_index', 'id'):
                    uraian = getattr(pek, 'snapshot_uraian', getattr(pek, 'nama', getattr(pek, 'name', '')))
                    kode_pek = getattr(pek, 'snapshot_kode', getattr(pek, 'kode_ahsp', ''))

                    # Get details for this pekerjaan
                    details = details_by_pekerjaan.get(pek.id, [])

                    if not details:
                        # Pekerjaan without details - show empty row
                        rows.append([
                            uraian,
                            kode_pek or '',
                            '',
                            '',
                            '',
                            '',
                            '',
                        ])
                        hierarchy_levels[row_idx] = 3
                        row_idx += 1
                        total_pekerjaan += 1
                    else:
                        # Pekerjaan header
                        rows.append([
                            uraian,
                            kode_pek or '',
                            '',
                            '',
                            '',
                            '',
                            '',
                        ])
                        hierarchy_levels[row_idx] = 3
                        pekerjaan_header_idx = row_idx
                        row_idx += 1
                        total_pekerjaan += 1

                        # Detail items (nested under pekerjaan)
                        pekerjaan_total = Decimal('0')
                        for detail in details:
                            koefisien = self._to_decimal(detail.koefisien)
                            harga_satuan = self._to_decimal(
                                detail.harga_item.harga_satuan if detail.harga_item else 0
                            )
                            jumlah = koefisien * harga_satuan

                            rows.append([
                                f"  {detail.uraian}",  # Indent for detail
                                detail.kode or '',
                                detail.kategori or '',
                                detail.satuan or '',
                                self._format_number(koefisien, 6),
                                self._format_number(harga_satuan, 0),
                                self._format_number(jumlah, 0),
                            ])
                            # No hierarchy level for detail rows - they're regular data rows
                            row_idx += 1
                            total_items += 1
                            pekerjaan_total += jumlah

                        # Update pekerjaan header with total in last column
                        if pekerjaan_total > 0:
                            rows[pekerjaan_header_idx][-1] = self._format_number(pekerjaan_total, 0)

        # Footer rows - summary info
        footer_rows = [
            ['Total Pekerjaan', str(total_pekerjaan)],
            ['Total Items', str(total_items)],
        ]

        return {
            'table_data': {
                'headers': headers,
                'rows': rows,
            },
            'col_widths': col_widths,
            'hierarchy_levels': hierarchy_levels,
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
