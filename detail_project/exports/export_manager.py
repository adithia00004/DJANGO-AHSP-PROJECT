# =====================================================================
# FILE: detail_project/exports/export_manager.py
# Copy this entire file
# =====================================================================

from typing import Dict, Any
from django.http import HttpResponse
from ..export_config import ExportConfig, SignatureConfig, format_currency, JadwalExportLayout
from ..services import compute_kebutuhan_items, summarize_kebutuhan_rows
from .csv_exporter import CSVExporter
from .pdf_exporter import PDFExporter
from .word_exporter import WordExporter
from .excel_exporter import ExcelExporter
from .rekap_rab_adapter import RekapRABAdapter
from .rekap_kebutuhan_adapter import RekapKebutuhanAdapter
from .volume_pekerjaan_adapter import VolumePekerjaanAdapter
from .harga_items_adapter import HargaItemsAdapter
from .rincian_ahsp_adapter import RincianAHSPAdapter
from .jadwal_pekerjaan_adapter import JadwalPekerjaanExportAdapter


class ExportManager:
    """Centralized export coordinator"""
    
    EXPORTER_MAP = {
        'csv': CSVExporter,
        'pdf': PDFExporter,
        'word': WordExporter,
        'xlsx': ExcelExporter,
    }
    
    def __init__(self, project, user=None):
        self.project = project
        self.user = user
    
    def export_rekap_rab(self, format_type: str) -> HttpResponse:
        """
        Export Rekap RAB
        
        Args:
            format_type: 'csv', 'pdf', or 'word'
        
        Returns:
            HttpResponse with exported file
        """
        # Create export config
        config = self._create_config()
        
        # Get data
        adapter = RekapRABAdapter(self.project)
        data_raw = adapter.get_export_data()

        # Build two-page payload per requirements
        # Page 1: Rencana Anggaran Biaya (full table)
        page1 = {
            'title': 'Rencana Anggaran Biaya',
            'table_data': data_raw.get('table_data', {}),
            'hierarchy_levels': data_raw.get('hierarchy_levels', {}),
            'col_widths': data_raw.get('col_widths', []),
            'footer_rows': data_raw.get('footer_rows', []),
        }

        # Page 2: Pengesahan (rekap per klasifikasi + footer + signatures)
        page2_table = {
            'headers': ['Klasifikasi', 'Total Harga (Rp)'],
            'rows': data_raw.get('summary_by_klasifikasi', []),
        }
        # Set column widths to match print (approx 80/20 of 277mm)
        page2_col_widths = [0.80 * 277, 0.20 * 277]

        page2 = {
            'title': 'REKAPITULASI RENCANA ANGGARAN BIAYA',
            'table_data': page2_table,
            'footer_rows': data_raw.get('footer_rows', []),
            'col_widths': page2_col_widths,
        }

        data = {
            'pages': [page1, page2]
        }
        
        # Get exporter
        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")
        
        exporter = exporter_class(config)
        
        # Export!
        return exporter.export(data)
    
    def _create_config(self) -> ExportConfig:
        """Create export configuration"""
        # Signature configuration
        sig_config = SignatureConfig(
            enabled=True,
            signatures=[
                {
                    'label': 'Pemilik Proyek',
                    'name': getattr(self.project, 'nama_client', '') or '',
                    'position': ''
                },
                {
                    'label': 'Konsultan Perencana',
                    'name': '',
                    'position': ''
                },
            ]
        )

        # Project identity fields aligned with page/print data attributes
        name = (
            getattr(self.project, 'nama_project', None)
            or getattr(self.project, 'nama', None)
            or '-'
        )
        code = (
            getattr(self.project, 'kode_project', None)
            or getattr(self.project, 'index_project', None)
            or getattr(self.project, 'kode', None)
            or '-'
        )
        lokasi = getattr(self.project, 'lokasi', '') or '-'
        tahun = str(getattr(self.project, 'tahun_anggaran', '') or '-')

        # Build extra identity fields to mirror page/print identity
        # Values aligned with _project_identity.html
        ket1 = getattr(self.project, 'ket_project1', None)
        ket2 = getattr(self.project, 'ket_project2', None)
        instansi = getattr(self.project, 'instansi_client', None)
        tahun_project = getattr(self.project, 'tahun_project', None)
        sumber_dana = getattr(self.project, 'sumber_dana', None)
        lokasi_project = getattr(self.project, 'lokasi_project', None)
        ang_owner = getattr(self.project, 'anggaran_owner', None)
        anggaran_fmt = f"Rp {format_currency(ang_owner)}" if ang_owner is not None else 'Rp 0'

        extra_identity = {
            'ket_project1': ket1,
            'ket_project2': ket2,
            'instansi_client': instansi,
            'tahun_project': tahun_project,
            'sumber_dana': sumber_dana,
            'lokasi_project': lokasi_project,
            'project_anggaran': anggaran_fmt,
        }

        # Tighter layout + slightly smaller fonts to fit table + signatures on one page
        return ExportConfig(
            title='REKAPITULASI RENCANA ANGGARAN BIAYA',
            project_name=name,
            project_code=code,
            location=lokasi,
            year=tahun,
            owner=getattr(self.project, 'nama_client', '') or '-',
            signature_config=sig_config,
            export_by=self.user.get_full_name() if self.user else '',
            extra_identity=extra_identity,
            # Layout (mm)
            margin_top=10,
            margin_bottom=10,
            margin_left=10,
            margin_right=10,
            # Fonts
            font_size_title=16,
            font_size_header=8,
            font_size_normal=8,
        )

    def export_rekap_kebutuhan(
        self,
        format_type: str,
        *,
        mode: str = 'all',
        tahapan_id: int | None = None,
        filters: dict | None = None,
        search: str | None = None,
        time_scope: dict | None = None,
    ) -> HttpResponse:
        """Export Rekap Kebutuhan (flat table)"""
        config = self._create_config()

        rows_raw = compute_kebutuhan_items(
            self.project,
            mode=mode,
            tahapan_id=tahapan_id,
            filters=filters,
            time_scope=time_scope,
        )
        rows, summary = summarize_kebutuhan_rows(rows_raw, search=search or '')
        filters = filters or {}
        scope_active = bool(time_scope and time_scope.get('mode') not in ('', 'all'))
        filters_applied = bool(
            (filters.get('klasifikasi_ids'))
            or (filters.get('sub_klasifikasi_ids'))
            or (filters.get('kategori_items'))
            or (filters.get('pekerjaan_ids'))
            or (search and search.strip())
            or (mode == 'tahapan' and tahapan_id)
            or scope_active
        )
        summary.update({
            'mode': mode,
            'tahapan_id': tahapan_id,
            'filters': filters,
            'search': search or '',
            'time_scope': time_scope,
            'time_scope_active': scope_active,
            'filters_applied': filters_applied,
        })

        adapter = RekapKebutuhanAdapter(self.project, rows=rows, summary=summary)
        data = adapter.get_export_data()
        if summary:
            data.setdefault('meta', summary)

        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")

        exporter = exporter_class(config)
        return exporter.export(data)

    def export_volume_pekerjaan(self, format_type: str, parameters: dict = None) -> HttpResponse:
        """
        Export Volume Pekerjaan

        Args:
            format_type: 'csv', 'pdf', or 'word'
            parameters: Optional dict of parameter values {'panjang': 100.0, 'lebar': 50.0, ...}

        Returns:
            HttpResponse with exported file
        """
        # Create export config with portrait orientation and signatures
        config = self._create_config_simple('VOLUME PEKERJAAN', page_orientation='portrait')

        # Get data with parameters
        adapter = VolumePekerjaanAdapter(self.project, parameters=parameters)
        data = adapter.get_export_data()

        # Get exporter
        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")

        exporter = exporter_class(config)

        # Export!
        return exporter.export(data)

    def export_harga_items(self, format_type: str) -> HttpResponse:
        """
        Export Harga Items

        Args:
            format_type: 'csv', 'pdf', or 'word'

        Returns:
            HttpResponse with exported file
        """
        # Create export config with portrait orientation and signatures
        config = self._create_config_simple('DAFTAR HARGA ITEMS', page_orientation='portrait')

        # Get data
        adapter = HargaItemsAdapter(self.project)
        data = adapter.get_export_data()

        # Get exporter
        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")

        exporter = exporter_class(config)

        # Export!
        return exporter.export(data)

    def export_rincian_ahsp(self, format_type: str, orientation: str | None = None) -> HttpResponse:
        """
        Export Rincian AHSP (Detail AHSP for all pekerjaan)

        Args:
            format_type: 'csv', 'pdf', or 'word'

        Returns:
            HttpResponse with exported file
        """
        # Create export config; allow override via parameter (default: portrait)
        page_orientation = orientation if orientation in ('portrait', 'landscape') else 'portrait'
        config = self._create_config_simple('RINCIAN ANALISA HARGA SATUAN PEKERJAAN', page_orientation=page_orientation)

        # Get data
        adapter = RincianAHSPAdapter(self.project)
        data = adapter.get_export_data()

        # Get exporter
        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")

        exporter = exporter_class(config)

        # Export!
        return exporter.export(data)

    def export_jadwal_pekerjaan(
        self,
        format_type: str,
        attachments: list | None = None,
        parameters: dict | None = None
    ) -> HttpResponse:
        """
        Export Jadwal Pekerjaan with support for 3 report types.

        Args:
            format_type: 'csv', 'pdf', 'word', or 'xlsx'
            attachments: List of chart attachments [{"title": str, "bytes": bytes}]
            parameters: Export parameters:
                {
                    'report_type': 'full' | 'monthly' | 'weekly',
                    'mode': 'weekly' | 'monthly',
                    'include_dates': bool,
                    'weeks_per_month': int
                }

        Returns:
            HttpResponse with exported file
        """
        # Parse parameters with defaults
        params = parameters or {}
        report_type = params.get('report_type', 'full')
        mode = params.get('mode', 'weekly')
        include_dates = params.get('include_dates', False)
        weeks_per_month = params.get('weeks_per_month', 4)

        # Set title based on report type
        title_map = {
            'full': 'REKAP LAPORAN - JADWAL PELAKSANAAN PEKERJAAN',
            'monthly': 'LAPORAN BULANAN - JADWAL PELAKSANAAN PEKERJAAN',
            'weekly': 'LAPORAN MINGGUAN - JADWAL PELAKSANAAN PEKERJAAN'
        }
        title = title_map.get(report_type, 'JADWAL PELAKSANAAN PEKERJAAN')

        config = self._create_config_simple(
            title,
            page_orientation='landscape',
            page_size=JadwalExportLayout.PAGE_SIZE
        )

        # Apply layout defaults for Jadwal exports
        config.margin_top = JadwalExportLayout.MARGIN_TOP
        config.margin_bottom = JadwalExportLayout.MARGIN_BOTTOM
        config.margin_left = JadwalExportLayout.MARGIN_LEFT
        config.margin_right = JadwalExportLayout.MARGIN_RIGHT

        # Determine if we should use monthly mode for adapter
        use_monthly_mode = (mode == 'monthly')

        adapter = JadwalPekerjaanExportAdapter(
            self.project,
            page_size=config.page_size,
            page_orientation=config.page_orientation,
            margin_left=config.margin_left,
            margin_right=config.margin_right,
            layout_spec=JadwalExportLayout,
            auto_compact_weeks=use_monthly_mode,  # Enable monthly if mode='monthly'
            weekly_threshold=weeks_per_month,     # Use weeks_per_month for aggregation
            max_rows_per_page=JadwalExportLayout.ROWS_PER_PAGE,
        )

        data = adapter.get_export_data()

        # Add metadata
        data['report_type'] = report_type
        data['mode'] = mode
        data['include_dates'] = include_dates
        data['weeks_per_month'] = weeks_per_month

        if attachments:
            # Attachments are list of {"title": str, "bytes": bytes}
            data["attachments"] = attachments

        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")

        exporter = exporter_class(config)
        return exporter.export(data)

    def _create_config_simple(self, title: str, page_orientation: str = 'portrait', page_size: str = 'A4') -> ExportConfig:
        """
        Create export configuration with signature section
        For Volume Pekerjaan, Harga Items, and Rincian AHSP pages

        Args:
            title: Document title
            page_orientation: 'portrait' or 'landscape' (default: portrait)

        Returns:
            ExportConfig object
        """
        # Project identity fields
        name = (
            getattr(self.project, 'nama_project', None)
            or getattr(self.project, 'nama', None)
            or '-'
        )
        code = (
            getattr(self.project, 'kode_project', None)
            or getattr(self.project, 'index_project', None)
            or getattr(self.project, 'kode', None)
            or '-'
        )
        lokasi = getattr(self.project, 'lokasi', '') or '-'
        tahun = str(getattr(self.project, 'tahun_anggaran', '') or '-')

        # Build extra identity fields
        ket1 = getattr(self.project, 'ket_project1', None)
        ket2 = getattr(self.project, 'ket_project2', None)
        instansi = getattr(self.project, 'instansi_client', None)
        tahun_project = getattr(self.project, 'tahun_project', None)
        sumber_dana = getattr(self.project, 'sumber_dana', None)
        lokasi_project = getattr(self.project, 'lokasi_project', None)
        ang_owner = getattr(self.project, 'anggaran_owner', None)
        anggaran_fmt = f"Rp {format_currency(ang_owner)}" if ang_owner is not None else 'Rp 0'

        extra_identity = {
            'ket_project1': ket1,
            'ket_project2': ket2,
            'instansi_client': instansi,
            'tahun_project': tahun_project,
            'sumber_dana': sumber_dana,
            'lokasi_project': lokasi_project,
            'project_anggaran': anggaran_fmt,
        }

        # Enable signatures with Lembar Pengesahan
        sig_config = SignatureConfig(
            enabled=True,
            signatures=[
                {
                    'label': 'Pemilik Proyek',
                    'name': getattr(self.project, 'nama_client', '') or '',
                    'position': ''
                },
                {
                    'label': 'Konsultan Perencana',
                    'name': '',
                    'position': ''
                },
            ]
        )

        return ExportConfig(
            title=title,
            project_name=name,
            project_code=code,
            location=lokasi,
            year=tahun,
            owner=getattr(self.project, 'nama_client', '') or '-',
            signature_config=sig_config,
            export_by=self.user.get_full_name() if self.user else '',
            extra_identity=extra_identity,
            page_orientation=page_orientation,
            page_size=page_size,
            # Consistent margins (same as Rekap RAB)
            margin_top=10,
            margin_bottom=10,
            margin_left=10,
            margin_right=10,
            # Fonts
            font_size_title=16,
            font_size_header=8,
            font_size_normal=8,
        )

    def export_jadwal_professional(
        self,
        format_type: str,
        report_type: str = 'rekap',
        period: int | None = None,
        attachments: list | None = None,
        gantt_data: dict | None = None,
    ) -> HttpResponse:
        """
        Export Jadwal Pekerjaan with professional "Laporan Tertulis" format.
        
        This method generates reports with:
        - Cover page
        - Executive summary (for monthly/weekly)
        - Comparison tables (for monthly/weekly)
        - Separated Planned/Actual sections (for rekap)
        - Kurva S and Gantt charts
        - Signature section
        
        Args:
            format_type: 'pdf' or 'word'
            report_type: 'rekap', 'monthly', or 'weekly'
            period: Month number (1-based) for monthly, Week number for weekly
            attachments: Chart attachments [{"title": str, "bytes": bytes}]
            
        Returns:
            HttpResponse with exported file
        """
        from reportlab.platypus import PageBreak, Spacer
        from reportlab.lib.units import mm
        
        # Title mapping
        title_map = {
            'rekap': 'LAPORAN REKAPITULASI JADWAL PEKERJAAN',
            'monthly': 'LAPORAN PROGRES BULANAN JADWAL PEKERJAAN',
            'weekly': 'LAPORAN PROGRES MINGGUAN JADWAL PEKERJAAN',
        }
        title = title_map.get(report_type, 'LAPORAN JADWAL PEKERJAAN')
        
        config = self._create_config_simple(
            title,
            page_orientation='landscape',
            page_size=JadwalExportLayout.PAGE_SIZE
        )
        config.margin_top = JadwalExportLayout.MARGIN_TOP
        config.margin_bottom = JadwalExportLayout.MARGIN_BOTTOM
        config.margin_left = JadwalExportLayout.MARGIN_LEFT
        config.margin_right = JadwalExportLayout.MARGIN_RIGHT

        adapter = JadwalPekerjaanExportAdapter(
            self.project,
            page_size=config.page_size,
            page_orientation=config.page_orientation,
            margin_left=config.margin_left,
            margin_right=config.margin_right,
            layout_spec=JadwalExportLayout,
            max_rows_per_page=JadwalExportLayout.ROWS_PER_PAGE,
        )

        # Get data based on report type
        if report_type == 'rekap':
            report_data = adapter.get_rekap_report_data()
        elif report_type == 'monthly':
            month = period or 1
            report_data = adapter.get_monthly_comparison_data(month)
        elif report_type == 'weekly':
            week = period or 1
            report_data = adapter.get_weekly_comparison_data(week)
        else:
            report_data = adapter.get_export_data()

        # Build professional export data
        data = {
            'report_type': report_type,
            'professional': True,  # Flag for professional format
            'project_info': report_data.get('project_info', {}),
        }
        
        if report_type == 'rekap':
            data['planned_pages'] = report_data.get('planned_pages', [])
            data['actual_pages'] = report_data.get('actual_pages', [])
            data['kurva_s_data'] = report_data.get('kurva_s_data', [])
            data['summary'] = report_data.get('summary', {})
            data['meta'] = report_data.get('meta', {})
            data['weekly_columns'] = report_data.get('weekly_columns', [])  # For Gantt date headers
            # Include cover page sections
            data['sections'] = [
                'Grid View - Rencana (Planned)',
                'Grid View - Realisasi (Actual)',
                'Kurva S Progress Kumulatif',
                'Gantt Chart'
            ]
        elif report_type in ('monthly', 'weekly'):
            data['period'] = report_data.get('period', {})
            data['current_data'] = report_data.get('current_data', {})
            data['previous_data'] = report_data.get('previous_data', {})
            data['comparison'] = report_data.get('comparison', {})
            data['executive_summary'] = report_data.get('executive_summary', {})
            data['hierarchy_progress'] = report_data.get('hierarchy_progress', [])
            data['detail_table'] = report_data.get('detail_table', {})
            if report_type == 'monthly':
                data['month'] = report_data.get('month', period)
            else:
                data['week'] = report_data.get('week', period)

        if attachments:
            data['attachments'] = attachments
        
        # Include structured Gantt data from frontend for backend rendering
        if gantt_data:
            data['gantt_data'] = gantt_data

        exporter_class = self.EXPORTER_MAP.get(format_type)
        if not exporter_class:
            raise ValueError(f"Unsupported format: {format_type}")

        exporter = exporter_class(config)
        
        # For PDF and Word, use special professional export method
        if format_type in ('pdf', 'word') and hasattr(exporter, 'export_professional'):
            return exporter.export_professional(data)
        
        return exporter.export(data)

