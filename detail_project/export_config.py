# ============================================================================
# FILE 1 (NEW): detail_project/export_config.py
# ============================================================================
"""
Export Configuration - Single Source of Truth
Centralized styling constants untuk semua export formats

⏱️ Implementation time: 15 minutes (copy-paste this file)
🎯 Goal: Eliminate magic numbers, ensure consistency
📝 Usage: Import and use constants instead of hardcoded values

Author: Export System v2.0
Created: 2025
"""

from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# COLOR CONFIGURATION
# ============================================================================

class ExportColors:
    """
    Color palette untuk export styling
    Semua colors dalam format HEX (tanpa #)
    
    Usage:
        from .export_config import ExportColors
        color = ExportColors.LEVEL1_BG  # Returns: 'e8e8e8'
    """
    
    # ===== Hierarchy Background Colors =====
    LEVEL1_BG = 'e8e8e8'      # Klasifikasi (dark gray)
    LEVEL2_BG = 'f5f5f5'      # Sub-Klasifikasi (light gray)
    LEVEL3_BG = 'ffffff'      # Pekerjaan (white)
    
    # ===== Other Background Colors =====
    HEADER_BG = 'e8e8e8'      # Table header
    FOOTER_BG = 'f8f8f8'      # Footer/total row
    
    # ===== Border Colors =====
    BORDER_DARK = '000000'    # Strong borders (header, footer)
    BORDER_LIGHT = '666666'   # Normal cell borders
    
    # ===== Text Colors =====
    TEXT_PRIMARY = '000000'   # Primary text (black)
    TEXT_SECONDARY = '666666' # Secondary text (gray) - timestamps, notes
    
    @classmethod
    def get_hex(cls, color_name: str) -> str:
        """Get color with # prefix for libraries that need it"""
        color = getattr(cls, color_name.upper(), 'ffffff')
        return f'#{color}'


# ============================================================================
# FONT CONFIGURATION
# ============================================================================

class ExportFonts:
    """
    Font sizes untuk berbagai elemen (in points)
    
    Usage:
        from .export_config import ExportFonts
        size = ExportFonts.TITLE  # Returns: 18
    """
    
    # ===== Header Section =====
    TITLE = 18        # Main title "RENCANA ANGGARAN BIAYA (RAB)"
    SUBTITLE = 16     # Project name
    INFO = 10         # Project info section (kode, lokasi, tahun)
    
    # ===== Table =====
    HEADER = 9        # Table header row
    LEVEL1 = 10       # Klasifikasi rows
    LEVEL2 = 9        # Sub-Klasifikasi rows
    LEVEL3 = 9        # Pekerjaan rows
    
    # ===== Footer Section =====
    FOOTER = 10       # Footer/total row
    SUMMARY = 11      # Summary section title
    SUMMARY_TEXT = 9  # Summary section details
    TIMESTAMP = 8     # Footer timestamp


# ============================================================================
# LAYOUT CONFIGURATION
# ============================================================================

class ExportLayout:
    """
    Layout configuration: margins, spacing, column widths
    
    Usage:
        from .export_config import ExportLayout
        widths = ExportLayout.get_col_widths_mm(277)
    """
    
    # ===== Page Settings =====
    PAGE_SIZE = 'A4'
    ORIENTATION = 'landscape'
    
    # ===== Margins (in mm) =====
    MARGIN_TOP = 20
    MARGIN_BOTTOM = 20
    MARGIN_LEFT = 15
    MARGIN_RIGHT = 15
    
    # ===== Column Width Percentages =====
    # Must sum to 1.0 (100%)
    COL_URAIAN = 0.35     # 35% - Uraian Pekerjaan
    COL_KODE = 0.12       # 12% - Kode Pekerjaan
    COL_SATUAN = 0.08     # 8%  - Satuan
    COL_VOLUME = 0.10     # 10% - Volume
    COL_HARGA = 0.15      # 15% - Harga Satuan
    COL_TOTAL = 0.20      # 20% - Total Harga
    
    # ===== Spacing (in mm) =====
    SPACING_AFTER_HEADER = 8
    SPACING_AFTER_TABLE = 8
    SPACING_AFTER_SUMMARY = 5
    
    @classmethod
    def get_col_widths_mm(cls, total_width_mm: float) -> dict:
        """
        Convert column percentages to millimeters
        
        Args:
            total_width_mm: Total available width in mm
                           For A4 landscape: 297 - margins = ~267mm
        
        Returns:
            Dict with column names as keys, widths in mm as values
        """
        return {
            'uraian': total_width_mm * cls.COL_URAIAN,
            'kode': total_width_mm * cls.COL_KODE,
            'satuan': total_width_mm * cls.COL_SATUAN,
            'volume': total_width_mm * cls.COL_VOLUME,
            'harga': total_width_mm * cls.COL_HARGA,
            'total': total_width_mm * cls.COL_TOTAL,
        }
    
    @classmethod
    def get_col_widths_inches(cls, total_width_inches: float) -> dict:
        """
        Convert column percentages to inches
        
        Args:
            total_width_inches: Total available width in inches
        
        Returns:
            Dict with column names as keys, widths in inches as values
        """
        return {
            'uraian': total_width_inches * cls.COL_URAIAN,
            'kode': total_width_inches * cls.COL_KODE,
            'satuan': total_width_inches * cls.COL_SATUAN,
            'volume': total_width_inches * cls.COL_VOLUME,
            'harga': total_width_inches * cls.COL_HARGA,
            'total': total_width_inches * cls.COL_TOTAL,
        }


class JadwalExportLayout:
    """
    Layout defaults for Jadwal (Grid / Gantt / Kurva S) exports.
    Tuned for A3 landscape with compact columns and predictable pagination.
    """

    PAGE_SIZE = 'A3'
    ORIENTATION = 'landscape'

    # Margins (mm) — slightly larger than default for header/footer room
    MARGIN_TOP = 12
    MARGIN_BOTTOM = 12
    MARGIN_LEFT = 12
    MARGIN_RIGHT = 12

    # Static column widths (mm) for grid section
    # UNIFIED: 3 columns only (no Kode) - matches Grid View, Kurva S, Gantt
    # COL_KODE = 18  # REMOVED - unified structure
    COL_URAIAN = 75
    COL_VOLUME = 20
    COL_SATUAN = 18

    # Timeline columns (mm)
    WEEKLY_MIN_COL = 12          # fits ~22 cols on A3 after static columns
    WEEKLY_HARD_LIMIT = 18       # FIXED: max 18 weeks per page (45pt width each)
    AUTO_MONTHLY_THRESHOLD = 18  # switch to monthly when weeks exceed this
    MONTHLY_MIN_COL = 22         # month labels are wider
    MONTHLY_HARD_LIMIT = 12

    # Row handling
    ROWS_PER_PAGE = 55           # paginate tables with many rows (PDF/Excel)
    WRAP_MAX_LINES = 3           # cap name/description wrapping

    @classmethod
    def static_widths_mm(cls) -> list:
        # UNIFIED: 3 columns (Uraian, Volume, Satuan) - no Kode
        return [cls.COL_URAIAN, cls.COL_VOLUME, cls.COL_SATUAN]


# ============================================================================
# CONTENT CONFIGURATION
# ============================================================================

class ExportContent:
    """
    Content and text configuration
    """
    
    # ===== Text Content =====
    TITLE_TEXT = 'RENCANA ANGGARAN BIAYA (RAB)'
    SUMMARY_TITLE = 'RINGKASAN'
    TOTAL_LABEL = 'TOTAL KESELURUHAN:'
    
    # ===== Table Headers =====
    TABLE_HEADERS = [
        'Uraian Pekerjaan',
        'Kode',
        'Satuan',
        'Volume',
        'Harga Satuan',
        'Total Harga'
    ]
    
    # ===== Settings =====
    SHOW_HEADER = True
    SHOW_PROJECT_INFO = True
    SHOW_SUMMARY = True
    SHOW_FOOTER = True
    
    DEFAULT_MARKUP_PERCENT = Decimal('10.00')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_level_style(level: int) -> dict:
    """
    Get styling configuration for hierarchy level
    
    Centralized function untuk mendapatkan style berdasarkan level.
    Digunakan oleh semua exporters untuk consistency.
    
    Args:
        level: Hierarchy level
               1 = Klasifikasi
               2 = Sub-Klasifikasi
               3 = Pekerjaan
    
    Returns:
        Dict with:
            - bg_color: Background color (hex tanpa #)
            - font_size: Font size (points)
            - font_weight: 'bold' or 'normal'
            - indent_text: Indentation string
            - indent_spaces: Number of spaces for indent
    
    Usage:
        from .export_config import get_level_style
        
        style = get_level_style(1)
        print(style['bg_color'])    # 'e8e8e8'
        print(style['font_size'])   # 10
        print(style['font_weight']) # 'bold'
    """
    if level == 1:
        # KLASIFIKASI
        return {
            'bg_color': ExportColors.LEVEL1_BG,
            'font_size': ExportFonts.LEVEL1,
            'font_weight': 'bold',
            'indent_text': '',
            'indent_spaces': 0,
        }
    elif level == 2:
        # SUB-KLASIFIKASI
        return {
            'bg_color': ExportColors.LEVEL2_BG,
            'font_size': ExportFonts.LEVEL2,
            'font_weight': 'bold',
            'indent_text': '  ',  # 2 spaces
            'indent_spaces': 2,
        }
    else:  # level 3
        # PEKERJAAN
        return {
            'bg_color': ExportColors.LEVEL3_BG,
            'font_size': ExportFonts.LEVEL3,
            'font_weight': 'normal',
            'indent_text': '    ',  # 4 spaces
            'indent_spaces': 4,
        }


def format_currency(value) -> str:
    """
    Format number as Indonesian currency
    
    Args:
        value: Number to format (int, float, Decimal, or str)
    
    Returns:
        Formatted string (e.g., "1.234.567,89")
    
    Usage:
        from .export_config import format_currency
        
        formatted = format_currency(1234567.89)
        print(formatted)  # "1.234.567,89"
    """
    try:
        val = Decimal(str(value))
        formatted = f"{val:,.2f}"
        # Convert to Indonesian format: , -> X, . -> ,, X -> .
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except:
        return '0,00'


def format_volume(value) -> str:
    """
    Format volume number (typically shown without thousand separators)
    
    Args:
        value: Volume value
    
    Returns:
        Formatted string
    
    Usage:
        from .export_config import format_volume
        
        formatted = format_volume(123.456)
        print(formatted)  # "123,46" or "123" (removes ,00)
    """
    try:
        val = Decimal(str(value))
        formatted = f"{val:.2f}".replace('.', ',')
        # Remove trailing ,00
        if formatted.endswith(',00'):
            formatted = formatted[:-3]
        return formatted
    except:
        return '0'


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """
    Validate configuration values
    Returns True if valid, raises ValueError if not
    """
    # Validate column widths sum to 1.0
    total = (ExportLayout.COL_URAIAN + ExportLayout.COL_KODE + 
             ExportLayout.COL_SATUAN + ExportLayout.COL_VOLUME + 
             ExportLayout.COL_HARGA + ExportLayout.COL_TOTAL)
    
    if not (0.99 <= total <= 1.01):
        raise ValueError(f"Column widths must sum to 1.0, got {total}")
    
    # Validate font sizes are reasonable
    for attr in dir(ExportFonts):
        if attr.isupper():
            size = getattr(ExportFonts, attr)
            if not (6 <= size <= 72):
                raise ValueError(f"Font size {attr} ({size}) out of range (6-72)")
    
    return True


# Run validation on import
try:
    validate_config()
except ValueError as e:
    import warnings
    warnings.warn(f"Export config validation failed: {e}")


# ============================================================================
# CONFIG OBJECTS (Phase 1)
# ============================================================================

@dataclass
class SignatureConfig:
    """Signature section configuration"""
    enabled: bool = False
    signatures: list = field(default_factory=list)
    # Optional runtime override (if provided, replace signatures when rendering)
    custom_signatures: list | None = None


@dataclass
class ExportConfig:
    """Export configuration (single source of truth per export run)"""
    # Titles and meta
    title: str
    project_name: str
    project_code: str
    location: str
    year: str
    owner: str = ''
    export_by: str = ''
    export_date: datetime = field(default_factory=datetime.now)

    # Section visibility / signatures
    signature_config: SignatureConfig = field(default_factory=SignatureConfig)

    # Extra identity fields (label/value pairs or known keys)
    # Suggested keys: tahap, prioritas, sumber_dana, project_anggaran
    extra_identity: dict = field(default_factory=dict)

    # Styling shortcuts (optional quick access)
    color_primary: str = ExportColors.HEADER_BG
    font_size_title: int = ExportFonts.TITLE
    font_size_header: int = ExportFonts.HEADER
    font_size_normal: int = ExportFonts.LEVEL3

    # Layout (mm)
    margin_top: int = ExportLayout.MARGIN_TOP
    margin_bottom: int = ExportLayout.MARGIN_BOTTOM
    margin_left: int = ExportLayout.MARGIN_LEFT
    margin_right: int = ExportLayout.MARGIN_RIGHT

    # Page orientation
    page_orientation: str = 'landscape'  # 'portrait' or 'landscape'
    page_size: str = ExportLayout.PAGE_SIZE  # 'A4', 'A3', etc.


# ============================================================================
# IDENTITY RENDER HELPERS (single source of truth)
# ============================================================================

PAGE_DIMENSIONS_MM = {
    'A4': (210.0, 297.0),
    'A3': (297.0, 420.0),
}


def get_page_size_mm(page_size: str) -> tuple[float, float]:
    """
    Resolve page width/height in millimeters for the requested paper size (portrait orientation).
    """
    if not page_size:
        return PAGE_DIMENSIONS_MM['A4']
    return PAGE_DIMENSIONS_MM.get(page_size.upper(), PAGE_DIMENSIONS_MM['A4'])

def build_identity_rows(config: ExportConfig) -> list:
    """
    Build identity rows to mirror templates/detail_project/_project_identity.html
    Returns list of [label, ':', value] rows for PDF/Word. CSV can drop ':' column.
    """
    ei = getattr(config, 'extra_identity', {}) or {}
    rows = []

    # Proyek + ket1/ket2 style
    rows.append(['Proyek', ':', config.project_name or '-'])
    ket1 = ei.get('ket_project1') or ei.get('tahap') or None
    ket2 = ei.get('ket_project2') or ei.get('prioritas') or None
    if ket1:
        rows.append(['', ':', str(ket1)])
    if ket2:
        rows.append(['', ':', str(ket2)])

    # Pemilik Project: owner (+ instansi)
    owner = config.owner or ''
    instansi = ei.get('instansi_client')
    if instansi:
        owner_val = f"{owner} ({instansi})" if owner else f"({instansi})"
    else:
        owner_val = owner or '-'
    rows.append(['Pemilik Project', ':', owner_val])

    # Tahun (prefer tahun_project)
    tahun = str(ei.get('tahun_project') or config.year or '-')
    rows.append(['Tahun', ':', tahun])

    # Sumber Dana
    sumber = ei.get('sumber_dana') or '-'
    rows.append(['Sumber Dana', ':', str(sumber)])

    # Lokasi (prefer lokasi_project)
    lokasi = ei.get('lokasi_project') or config.location or '-'
    rows.append(['Lokasi', ':', str(lokasi)])

    # Project Anggaran
    ang = ei.get('project_anggaran') or '-'
    rows.append(['Project Anggaran', ':', str(ang)])

    return rows


# ============================================================================
# USAGE EXAMPLES (for documentation)
# ============================================================================

if __name__ == '__main__':
    """
    Example usage - for testing and documentation
    Run: python export_config.py
    """
    
    print("=" * 60)
    print("EXPORT CONFIGURATION")
    print("=" * 60)
    
    print("\n1. Colors:")
    print(f"   Level 1 BG: #{ExportColors.LEVEL1_BG}")
    print(f"   Level 2 BG: #{ExportColors.LEVEL2_BG}")
    print(f"   Level 3 BG: #{ExportColors.LEVEL3_BG}")
    
    print("\n2. Fonts:")
    print(f"   Title: {ExportFonts.TITLE}pt")
    print(f"   Header: {ExportFonts.HEADER}pt")
    print(f"   Level 1: {ExportFonts.LEVEL1}pt")
    
    print("\n3. Column Widths (for 267mm total):")
    widths = ExportLayout.get_col_widths_mm(267)
    for col, width in widths.items():
        print(f"   {col:10s}: {width:6.2f}mm")
    
    print("\n4. Level Styles:")
    for level in [1, 2, 3]:
        style = get_level_style(level)
        print(f"   Level {level}: bg={style['bg_color']}, "
              f"size={style['font_size']}pt, "
              f"weight={style['font_weight']}")
    
    print("\n5. Formatters:")
    print(f"   Currency: {format_currency(1234567.89)}")
    print(f"   Volume: {format_volume(123.456)}")
    
    print("\n" + "=" * 60)
    print("Configuration valid! ✓")
    print("=" * 60)


# ============================================================================
# MIGRATION NOTES FOR DEVELOPERS
# ============================================================================
"""
HOW TO USE THIS CONFIG IN views_api.py:

STEP 1: Add import
--------------------
from .export_config import (
    ExportColors, 
    ExportFonts, 
    ExportLayout,
    get_level_style,
    format_currency,
    format_volume
)

STEP 2: Replace hardcoded values
---------------------------------
BEFORE:
    fontSize=18
    colors.HexColor('#e8e8e8')
    
AFTER:
    fontSize=ExportFonts.TITLE
    colors.HexColor(ExportColors.LEVEL1_BG)

STEP 3: Use helper functions
-----------------------------
BEFORE:
    if level == 1:
        bg_color = '#e8e8e8'
        font_size = 10
        # ...
        
AFTER:
    style = get_level_style(level)
    bg_color = style['bg_color']
    font_size = style['font_size']

That's it! See the views_api.py modification guide for specific changes.
"""
