# =====================================================================
# FILE: detail_project/exports/base.py
# Copy this entire file
# =====================================================================

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from django.http import HttpResponse
from decimal import Decimal


@dataclass
class SignatureConfig:
    """Configuration for signature section"""
    enabled: bool = True
    signatures: list = field(default_factory=lambda: [
        {'label': 'Pemilik Proyek', 'name': '', 'position': ''},
        {'label': 'Konsultan Perencana', 'name': '', 'position': ''},
    ])
    custom_signatures: list = field(default_factory=list)


@dataclass
class WatermarkConfig:
    """Configuration for watermark (future feature)"""
    enabled: bool = False
    text: str = "DRAFT"
    opacity: float = 0.1
    angle: int = 45
    color: tuple = (200, 200, 200)


@dataclass
class ExportConfig:
    """Unified export configuration"""
    # Document metadata
    title: str
    project_name: str
    project_code: str
    location: str
    year: str
    owner: Optional[str] = None
    consultant: Optional[str] = None
    
    # Page settings (in mm)
    page_width: float = 297.0      # A4 Landscape
    page_height: float = 210.0
    margin_top: float = 20.0
    margin_bottom: float = 20.0
    margin_left: float = 15.0
    margin_right: float = 15.0
    
    # Typography
    font_family: str = "Helvetica"
    font_size_normal: int = 9
    font_size_header: int = 10
    font_size_title: int = 14
    
    # Colors (RGB tuples)
    color_primary: tuple = (44, 62, 80)
    color_accent: tuple = (52, 152, 219)
    color_border: tuple = (189, 195, 199)
    
    # Features
    signature_config: SignatureConfig = field(default_factory=SignatureConfig)
    watermark_config: WatermarkConfig = field(default_factory=WatermarkConfig)
    
    # Export metadata
    export_date: datetime = field(default_factory=datetime.now)
    export_by: str = ""
    
    # Future: Digital signature support
    digital_signature_enabled: bool = False


class BaseExporter(ABC):
    """Base class untuk semua exporter"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
        
    @abstractmethod
    def export(self, data: Any) -> HttpResponse:
        """Main export method - must be implemented by subclasses"""
        pass
    
    def _create_response(self, content: bytes, filename: str, 
                        content_type: str) -> HttpResponse:
        """Create HTTP response with proper headers"""
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    
    def _format_number(self, value: Any, decimals: int = 2) -> str:
        """Format number dengan locale Indonesia"""
        try:
            if value is None or value == '':
                return '-'
            num = Decimal(str(value))
            if decimals == 0:
                formatted = f"{int(round(num)):,}"
            else:
                formatted = f"{float(num):,.{decimals}f}"
            # Convert to Indonesian format
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return '-'
    
    def _format_date(self, date: datetime, format_type: str = 'long') -> str:
        """Format tanggal Indonesia"""
        months = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        if format_type == 'long':
            return f"{date.day} {months[date.month-1]} {date.year}"
        else:  # short
            return date.strftime('%d-%m-%Y')
