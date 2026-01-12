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
        Structure: Each pekerjaan becomes a separate section with header and detail table.
        Similar to the web page .rk-right .ra-editor structure.
        """
        from detail_project.models import (
            Klasifikasi,
            DetailAHSPProject,
            DetailAHSPExpanded,
        )

        sections = []  # List of pekerjaan sections
        recap_rows = []  # Lampiran Rekap AHSP rows

        # Detail table configuration (7 columns)
        detail_headers = [
            'No',
            'Uraian',
            'Kode',
            'Satuan',
            'Koefisien',
            'Harga Satuan (Rp)',
            'Jumlah Harga (Rp)'
        ]

        # Column widths for A4 Landscape (297mm width - 20mm margins = 277mm usable)
        detail_col_widths = [15, 80, 35, 25, 30, 46, 46]  # in mm (total: 277mm)

        # Fetch hierarchical containers with detail AHSP
        klasifikasi_list = (
            Klasifikasi.objects
            .filter(project=self.project)
            .prefetch_related('sub_list__pekerjaan_list')
            .order_by('ordering_index', 'id')
        )

        # Fetch all details at once for efficiency
        all_details = (
            DetailAHSPProject.objects
            .filter(project=self.project)
            .select_related('harga_item')
            .order_by('pekerjaan_id', 'kategori', 'id')
        )

        detail_ids = [d.id for d in all_details if d.id]
        bundle_totals: dict[int, Decimal] = {}
        if detail_ids:
            expanded_qs = (
                DetailAHSPExpanded.objects
                .filter(project=self.project, source_detail_id__in=detail_ids)
                .select_related('harga_item')
            )
            for expanded in expanded_qs:
                if not expanded.source_detail_id:
                    continue
                price = self._to_decimal(
                    expanded.harga_item.harga_satuan if expanded.harga_item else 0
                )
                koef = self._to_decimal(expanded.koefisien)
                bundle_totals[expanded.source_detail_id] = (
                    bundle_totals.get(expanded.source_detail_id, Decimal('0'))
                    + (price * koef)
                )

        # Group details by pekerjaan_id
        details_by_pekerjaan = {}
        for detail in all_details:
            pkj_id = detail.pekerjaan_id
            if pkj_id not in details_by_pekerjaan:
                details_by_pekerjaan[pkj_id] = []
            details_by_pekerjaan[pkj_id].append(detail)

        total_pekerjaan = 0
        total_items = 0
        grand_total = Decimal('0')

        # Build sections - each pekerjaan becomes a section
        # Determine default project markup (Profit/Margin)
        try:
            default_markup = Decimal(str(getattr(self.project.pricing, 'markup_percent', '10.00')))
        except Exception:
            # If pricing not created yet, use 10.00%
            default_markup = Decimal('10.00')

        for klas in klasifikasi_list:
            klas_name = getattr(klas, 'name', getattr(klas, 'nama', 'Klasifikasi'))

            for sub in klas.sub_list.all().order_by('ordering_index', 'id'):
                sub_name = getattr(sub, 'name', getattr(sub, 'nama', 'Sub'))

                # Pekerjaan items
                for pek in sub.pekerjaan_list.all().order_by('ordering_index', 'id'):
                    uraian = getattr(pek, 'snapshot_uraian', getattr(pek, 'nama', getattr(pek, 'name', '')))
                    kode_pek = getattr(pek, 'snapshot_kode', getattr(pek, 'kode_ahsp', ''))
                    satuan_pek = getattr(pek, 'satuan', '-')

                    # Get details for this pekerjaan
                    details = details_by_pekerjaan.get(pek.id, [])

                    # Group detail rows by kategori to mirror page structure
                    groups_spec = [
                        ('TK', 'A — Tenaga Kerja', 'Tenaga Kerja'),
                        ('BHN', 'B — Bahan', 'Bahan'),
                        ('ALT', 'C — Peralatan', 'Peralatan'),
                        ('LAIN', 'D — Lainnya', 'Lainnya'),
                    ]

                    groups: List[dict] = []
                    detail_no = 1
                    pekerjaan_total = Decimal('0')

                    for key, title, short_title in groups_spec:
                        rows_in_group = []
                        subtotal = Decimal('0')
                        for detail in (d for d in details if (d.kategori or '').upper() == key):
                            koefisien = self._to_decimal(detail.koefisien)
                            is_bundle = (
                                key == 'LAIN'
                                and (getattr(detail, 'ref_pekerjaan_id', None) or getattr(detail, 'ref_ahsp_id', None))
                            )
                            if is_bundle:
                                # Koefisien komponen disimpan per-unit bundle;
                                # bundle_total sudah merupakan harga per unit.
                                bundle_total = bundle_totals.get(detail.id, Decimal('0'))
                                harga_satuan = bundle_total
                            else:
                                harga_satuan = self._to_decimal(
                                    detail.harga_item.harga_satuan if detail.harga_item else 0
                                )
                            jumlah = koefisien * harga_satuan
                            subtotal += jumlah
                            pekerjaan_total += jumlah

                            rows_in_group.append([
                                str(detail_no),
                                detail.uraian or '',
                                detail.kode or '',
                                detail.satuan or '',
                                self._format_number(koefisien, 6),
                                self._format_number(harga_satuan, 0),
                                self._format_number(jumlah, 0),
                            ])
                            detail_no += 1
                            total_items += 1

                        groups.append({
                            'key': key,
                            'title': title,
                            'short_title': short_title,
                            'rows': rows_in_group,
                            'subtotal': self._format_number(subtotal, 0),
                        })

                    # Effective Profit/Margin (override per pekerjaan if available)
                    ov = getattr(pek, 'markup_override_percent', None)
                    eff_markup = Decimal(str(ov)) if ov is not None else default_markup
                    E_total = pekerjaan_total
                    F_margin = (E_total * eff_markup) / Decimal('100')
                    G_hsp = E_total + F_margin

                    # Add to recap rows (Lampiran)
                    recap_rows.append([
                        kode_pek or '-',
                        uraian,
                        self._format_number(G_hsp, 0),
                    ])

                    # Create section for this pekerjaan
                    section = {
                        'klasifikasi': klas_name,
                        'sub_klasifikasi': sub_name,
                        'pekerjaan': {
                            'kode': kode_pek or '-',
                            'uraian': uraian,
                            'satuan': satuan_pek,
                            'total': self._format_number(G_hsp, 0),
                        },
                        'detail_table': {
                            'headers': detail_headers,
                            'col_widths': detail_col_widths,
                        },
                        # New: grouped rows to mirror page structure
                        'groups': groups,
                        'totals': {
                            'E': self._format_number(E_total, 0),
                            'F': self._format_number(F_margin, 0),
                            'G': self._format_number(G_hsp, 0),
                            'markup_eff': f"{eff_markup:.2f}",
                        },
                        'has_details': any(len(g['rows']) > 0 for g in groups),
                    }

                    sections.append(section)
                    total_pekerjaan += 1
                    grand_total += G_hsp

        return {
            'sections': sections,
            'recap': {
                'headers': ['Kode AHSP', 'Uraian', 'Total HSP (Rp)'],
                'rows': recap_rows,
            },
            'summary': {
                'total_pekerjaan': total_pekerjaan,
                'total_items': total_items,
                'grand_total': self._format_number(grand_total, 0),
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
