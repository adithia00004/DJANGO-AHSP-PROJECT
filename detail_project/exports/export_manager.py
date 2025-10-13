# =====================================================================
# FILE: detail_project/exports/export_manager.py
# Copy this entire file
# =====================================================================

from typing import Dict, Any
from django.http import HttpResponse
from .base import ExportConfig, SignatureConfig
from .csv_exporter import CSVExporter
from .pdf_exporter import PDFExporter
from .word_exporter import WordExporter
from .rekap_rab_adapter import RekapRABAdapter


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
        data = adapter.get_export_data()
        
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
        
        return ExportConfig(
            title='REKAPITULASI RENCANA ANGGARAN BIAYA',
            project_name=self.project.nama,
            project_code=getattr(self.project, 'kode', '') or '-',
            location=getattr(self.project, 'lokasi', '') or '-',
            year=str(getattr(self.project, 'tahun_anggaran', '') or '-'),
            owner=getattr(self.project, 'nama_client', '') or '-',
            signature_config=sig_config,
            export_by=self.user.get_full_name() if self.user else '',
        )
