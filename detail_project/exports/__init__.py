# ============================================================================
# FILE: detail_project/exports/__init__.py
# ============================================================================
"""
Export System - Phase 1: Foundation

Menyediakan base exporter dan shared utilities untuk export ke berbagai format.
Implementasi Opsi 3 Pragmatic Architecture.

Usage:
    from .exports import BaseExporter, RekapRABExporter
    
    exporter = RekapRABExporter(project, data, pricing)
    response = exporter.to_csv()

Author: Export Refactoring Phase 1
Created: 2025
"""

from .base import BaseExporter

# Placeholder untuk future exports (Phase 2+)
from .rekap_rab import RekapRABExporter
# from .rincian_rab import RincianRABExporter
from .rekap_kebutuhan import RekapKebutuhanExporter

__all__ = [
    'BaseExporter',
    # Future exports akan ditambahkan di sini
    'RekapRABExporter',
    # 'RincianRABExporter', 
    'RekapKebutuhanExporter',
]

__version__ = '1.0.0'
__phase__ = 'Phase 1: Foundation'