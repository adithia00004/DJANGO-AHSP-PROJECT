# ============================================================================
# FILE: detail_project/exports/__init__.py
# ============================================================================
"""
Export System - Phase 2: Unified Styling

Menyediakan base exporter, table builders, dan exports.
Implementasi Opsi 3 Pragmatic Architecture dengan Unified Table Styles.

Usage:
    from .exports import BaseExporter, PDFTableBuilder, WordExporter
    from .exports.table_styles import UnifiedTableStyles as UTS

Author: Export Refactoring Phase 2
Created: 2025
"""

from .base import BaseExporter

# Table utilities
from .pdf_table_builder import PDFTableBuilder, TableType

# Export implementations
from .rekap_rab import RekapRABExporter
# from .rincian_rab import RincianRABExporter
from .rekap_kebutuhan import RekapKebutuhanExporter

# Word Export
from .word_exporter import WordExporter

__all__ = [
    'BaseExporter',
    'PDFTableBuilder',
    'TableType',
    'RekapRABExporter',
    'RekapKebutuhanExporter',
    'WordExporter',
]

__version__ = '2.1.0'
__phase__ = 'Phase 2: Unified Styling + Word Export'
