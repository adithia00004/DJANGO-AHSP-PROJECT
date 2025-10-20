# =====================================================================
# FILE: detail_project/exports/export_manager.py
# Copy this entire file
# =====================================================================

from typing import Dict, Any
from django.http import HttpResponse
from ..export_config import ExportConfig, SignatureConfig, format_currency
from .csv_exporter import CSVExporter
from .pdf_exporter import PDFExporter
from .word_exporter import WordExporter
from .rekap_rab_adapter import RekapRABAdapter
from .rekap_kebutuhan_adapter import RekapKebutuhanAdapter
from .volume_pekerjaan_adapter import VolumePekerjaanAdapter
from .harga_items_adapter import HargaItemsAdapter
from .rincian_ahsp_adapter import RincianAHSPAdapter


class ExportManager:
    """Centralized export coordinator"""
    
    EXPORTER_MAP = {
        'csv': CSVExporter,
        'pdf': PDFExporter,
        'word': WordExporter,
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

    def export_rekap_kebutuhan(self, format_type: str) -> HttpResponse:
        """Export Rekap Kebutuhan (flat table)"""
        config = self._create_config()

        adapter = RekapKebutuhanAdapter(self.project)
        data = adapter.get_export_data()

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

    def export_rincian_ahsp(self, format_type: str) -> HttpResponse:
        """
        Export Rincian AHSP (Detail AHSP for all pekerjaan)

        Args:
            format_type: 'csv', 'pdf', or 'word'

        Returns:
            HttpResponse with exported file
        """
        # Create export config with landscape orientation (many columns) and signatures
        config = self._create_config_simple('RINCIAN ANALISA HARGA SATUAN PEKERJAAN', page_orientation='landscape')

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

    def _create_config_simple(self, title: str, page_orientation: str = 'portrait') -> ExportConfig:
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
