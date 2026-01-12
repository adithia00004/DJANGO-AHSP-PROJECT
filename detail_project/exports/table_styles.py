"""
Unified Table Styles for PDF Export
====================================

Central module containing all shared styling constants for:
- Grid View (Planned/Actual)
- Kurva S
- Gantt Chart
- Export Defaults (fonts, margins, page settings)

Usage:
    from .table_styles import UnifiedTableStyles as UTS
    from .table_styles import ExportDefaults as ED
    
    header_bg = colors.HexColor(UTS.HEADER_BG)
    font_size = UTS.HEADER_FONT_SIZE
    margin = ED.MARGIN_TOP
"""

from reportlab.lib import colors
from reportlab.lib.units import mm


# =============================================================================
# EXPORT DEFAULTS (SSOT)
# =============================================================================

class ExportDefaults:
    """
    SSOT: Base defaults for all export formats (PDF, Word, Excel).
    
    This class centralizes common settings used across all exports:
    - Font sizes for title, header, and normal text
    - Page margins
    - Default page size and orientation
    
    Usage:
        from .table_styles import ExportDefaults as ED
        
        config.font_size_title = ED.FONT_SIZE_TITLE
        config.margin_top = ED.MARGIN_TOP
    """
    
    # =========================================
    # FONT SIZES (pt)
    # =========================================
    
    FONT_SIZE_TITLE = 16        # Document title (e.g., "REKAP RAB")
    FONT_SIZE_SUBTITLE = 12     # Subtitle/section headers
    FONT_SIZE_HEADER = 8        # Table headers
    FONT_SIZE_NORMAL = 8        # Normal text/table data
    FONT_SIZE_SMALL = 7         # Small text/footnotes
    FONT_SIZE_TINY = 6          # Very small (dense tables)
    
    # =========================================
    # MARGINS (mm)
    # =========================================
    
    MARGIN_TOP = 10
    MARGIN_BOTTOM = 10
    MARGIN_LEFT = 10
    MARGIN_RIGHT = 10
    
    # =========================================
    # PAGE DEFAULTS
    # =========================================
    
    DEFAULT_PAGE_SIZE = 'A4'
    DEFAULT_ORIENTATION = 'portrait'
    
    # =========================================
    # HELPER METHODS
    # =========================================
    
    @classmethod
    def get_margins_mm(cls) -> tuple:
        """Get all margins as tuple (top, right, bottom, left)."""
        return (cls.MARGIN_TOP, cls.MARGIN_RIGHT, cls.MARGIN_BOTTOM, cls.MARGIN_LEFT)
    
    @classmethod
    def get_margins_pt(cls) -> tuple:
        """Get all margins in points (for ReportLab)."""
        return (
            cls.MARGIN_TOP * mm,
            cls.MARGIN_RIGHT * mm,
            cls.MARGIN_BOTTOM * mm,
            cls.MARGIN_LEFT * mm
        )


# Shorthand alias
ED = ExportDefaults


class UnifiedTableStyles:
    """Centralized styling constants for all PDF export tables."""
    
    # =========================================
    # UNIFIED COLOR PALETTE
    # =========================================
    # Primary colors (Headers, Titles)
    PRIMARY = '#1e3a5f'             # Deep navy blue (main brand)
    PRIMARY_LIGHT = '#2c5282'       # Lighter navy (hover/accent)
    PRIMARY_DARK = '#1a365d'        # Darker navy (legacy compat)
    
    # Header colors (unified for all tables)
    HEADER_BG = '#1e3a5f'           # Unified header background
    HEADER_TEXT = '#FFFFFF'         # White text
    
    # Section/Detail header colors
    SECTION_HEADER_BG = '#e2e8f0'   # Section headers (light slate)
    DETAIL_HEADER_BG = '#f1f5f9'    # Detail table headers (lighter)
    
    # Hierarchy backgrounds
    KLASIFIKASI_BG = '#e2e8f0'      # Light blue-gray
    SUB_KLASIFIKASI_BG = '#f7fafc'  # Very light gray
    PEKERJAAN_BG = '#ffffff'        # White for data rows
    
    # Border colors
    INNER_BORDER = '#cbd5e0'        # Subtle inner border
    OUTER_BORDER = '#2d3748'        # Dark outer border
    LIGHT_BORDER = '#e2e8f0'        # Very light border for grids
    
    # Chart/Data visualization colors
    PLANNED_COLOR = '#0891b2'       # Teal (planned progress)
    ACTUAL_COLOR = '#f59e0b'        # Amber (actual progress)
    
    # Text colors
    TEXT_PRIMARY = '#1a202c'        # Near black
    TEXT_SECONDARY = '#4a5568'      # Gray
    TEXT_MUTED = '#718096'          # Light gray
    TEXT_LINK = '#2b6cb0'           # Link blue
    
    # Status colors
    STATUS_ON_TRACK = '#38a169'     # Green
    STATUS_AHEAD = '#3182ce'        # Blue
    STATUS_BEHIND = '#d69e2e'       # Yellow/orange
    STATUS_CRITICAL = '#e53e3e'     # Red
    
    # =========================================
    # TABLE TYPE-SPECIFIC FONTS
    # =========================================
    # Grid Tables (main data tables - compact)
    GRID_HEADER_FONT_SIZE = 7
    GRID_DATA_FONT_SIZE = 6
    
    # Detail Tables (monthly/weekly reports - larger)
    DETAIL_HEADER_FONT_SIZE = 9
    DETAIL_DATA_FONT_SIZE = 8
    
    # Summary Tables (executive summary - emphasis)
    SUMMARY_HEADER_FONT_SIZE = 10
    SUMMARY_DATA_FONT_SIZE = 9
    
    # Cover/Title fonts
    COVER_TITLE_FONT_SIZE = 24
    COVER_SUBTITLE_FONT_SIZE = 18
    SECTION_TITLE_FONT_SIZE = 14
    
    # Legacy compatibility aliases
    HEADER_FONT_NAME = 'Helvetica-Bold'
    HEADER_FONT_SIZE = 7
    
    WEEK_HEADER_FONT_NAME = 'Helvetica-Bold'
    WEEK_HEADER_FONT_SIZE = 5
    WEEK_DATE_FONT_SIZE = 4
    
    DATA_FONT_NAME = 'Helvetica'
    DATA_FONT_SIZE = 6
    
    KLASIFIKASI_FONT_NAME = 'Helvetica-Bold'
    KLASIFIKASI_FONT_SIZE = 7
    
    SUB_KLASIFIKASI_FONT_NAME = 'Helvetica-Bold'
    SUB_KLASIFIKASI_FONT_SIZE = 6
    
    # =========================================
    # COLUMN WIDTHS (pt) - Unified across all tables
    # =========================================
    URAIAN_WIDTH = 150      # ~53mm
    VOLUME_WIDTH = 50       # ~18mm
    SATUAN_WIDTH = 45       # ~16mm
    WEEK_WIDTH = 45         # ~16mm per week
    
    # Total static columns (Uraian + Volume + Satuan)
    STATIC_TOTAL = URAIAN_WIDTH + VOLUME_WIDTH + SATUAN_WIDTH  # 245pt
    
    # Static column count
    STATIC_COLS = 3  # Uraian, Volume, Satuan
    
    # =========================================
    # BORDERS (pt) - Unified
    # =========================================
    OUTER_BORDER_WIDTH = 1.5
    INNER_BORDER_WIDTH = 0.5
    LIGHT_BORDER_WIDTH = 0.3
    HEADER_BOTTOM_WIDTH = 1.0
    
    # =========================================
    # PADDING (mm) - Unified
    # =========================================
    PADDING_TOP = 2
    PADDING_BOTTOM = 2
    PADDING_LEFT = 1.5
    PADDING_RIGHT = 1.5
    
    # Compact padding for dense tables
    PADDING_COMPACT = 1.0
    
    # Spacious padding for summary tables
    PADDING_SPACIOUS = 3.0
    
    # =========================================
    # PAGINATION
    # =========================================
    MAX_WEEKS_PER_PAGE = 18
    MAX_ROWS_PER_PAGE = 50
    
    # =========================================
    # ROW HEIGHTS (pt)
    # =========================================
    GANTT_ROW_HEIGHT = 24
    GANTT_BAR_HEIGHT = 8
    KURVA_S_ROW_HEIGHT = 16
    DEFAULT_ROW_HEIGHT = 18
    
    # =========================================
    # SPACING (mm) - Unified section spacing
    # =========================================
    SPACING_SECTION = 10        # Between major sections
    SPACING_SUBSECTION = 5      # Between subsections
    SPACING_PARAGRAPH = 3       # Between paragraphs
    SPACING_TABLE_AFTER = 8     # After tables
    
    # =========================================
    # HELPER METHODS
    # =========================================
    
    @classmethod
    def get_header_bg_color(cls):
        """Get header background as ReportLab color."""
        return colors.HexColor(cls.HEADER_BG)
    
    @classmethod
    def get_header_text_color(cls):
        """Get header text as ReportLab color."""
        return colors.white
    
    @classmethod
    def get_klasifikasi_bg_color(cls):
        """Get klasifikasi background as ReportLab color."""
        return colors.HexColor(cls.KLASIFIKASI_BG)
    
    @classmethod
    def get_sub_klasifikasi_bg_color(cls):
        """Get sub_klasifikasi background as ReportLab color."""
        return colors.HexColor(cls.SUB_KLASIFIKASI_BG)
    
    @classmethod
    def get_inner_border_color(cls):
        """Get inner border as ReportLab color."""
        return colors.HexColor(cls.INNER_BORDER)
    
    @classmethod
    def get_outer_border_color(cls):
        """Get outer border as ReportLab color."""
        return colors.HexColor(cls.OUTER_BORDER)
    
    @classmethod
    def get_planned_color(cls):
        """Get planned (teal) as ReportLab color."""
        return colors.HexColor(cls.PLANNED_COLOR)
    
    @classmethod
    def get_actual_color(cls):
        """Get actual (amber) as ReportLab color."""
        return colors.HexColor(cls.ACTUAL_COLOR)
    
    @classmethod
    def get_static_col_widths(cls):
        """Get list of static column widths [Uraian, Volume, Satuan]."""
        return [cls.URAIAN_WIDTH, cls.VOLUME_WIDTH, cls.SATUAN_WIDTH]
    
    @classmethod
    def get_padding_tuple_mm(cls):
        """Get padding as (top, bottom, left, right) in mm."""
        return (
            cls.PADDING_TOP * mm,
            cls.PADDING_BOTTOM * mm,
            cls.PADDING_LEFT * mm,
            cls.PADDING_RIGHT * mm
        )
    
    @classmethod
    def calculate_max_weeks(cls, table_width_pt):
        """Calculate max weeks that fit in given table width."""
        week_area = table_width_pt - cls.STATIC_TOTAL
        calculated = int(week_area / cls.WEEK_WIDTH)
        return min(calculated, cls.MAX_WEEKS_PER_PAGE)


# Shorthand alias for convenience
UTS = UnifiedTableStyles


class TableLayoutCalculator:
    """
    Unified table layout calculator for Grid View, Kurva S, and Gantt.
    
    Usage:
        from .table_styles import TableLayoutCalculator
        
        # In any table builder:
        calc = TableLayoutCalculator(config)
        layout = calc.calculate(actual_weeks=25)
        
        # Access results:
        table_width = layout['table_width']
        col_widths = layout['column_widths']
        max_weeks = layout['max_weeks_per_page']
    """
    
    def __init__(self, config):
        """
        Initialize calculator with export config.
        
        Args:
            config: Export config object with page_size, page_orientation, 
                   margin_left, margin_right attributes
        """
        self.config = config
        
        # Import here to avoid circular import
        from ..export_config import get_page_size_mm
        
        # Get page dimensions from config
        page_size = getattr(config, 'page_size', 'A4') or 'A4'
        orientation = getattr(config, 'page_orientation', 'landscape')
        margin_left = getattr(config, 'margin_left', 10)
        margin_right = getattr(config, 'margin_right', 10)
        
        # Calculate page width
        base_width_mm, base_height_mm = get_page_size_mm(page_size)
        if orientation == 'landscape':
            page_width_mm = base_height_mm
        else:
            page_width_mm = base_width_mm
        
        # FIXED: Usable width (same for all tables)
        usable_width_mm = page_width_mm - margin_left - margin_right
        self.table_width = usable_width_mm * mm  # In pt
        
        # Week area
        self.week_area = self.table_width - UTS.STATIC_TOTAL
        
        # Max weeks per page (capped by UTS constant)
        self.max_weeks_per_page = min(
            int(self.week_area / UTS.WEEK_WIDTH),
            UTS.MAX_WEEKS_PER_PAGE
        )
    
    def calculate(self, actual_weeks: int) -> dict:
        """
        Calculate unified layout for given number of weeks.
        
        Args:
            actual_weeks: Actual number of week columns in data
            
        Returns:
            dict with:
                - table_width: Total table width (pt)
                - weeks_to_render: Number of weeks to show (may be truncated)
                - blank_cols: Number of blank columns to add
                - column_widths: List of column widths [Uraian, Vol, Sat, Week1, Week2, ...]
                - max_weeks_per_page: Maximum weeks that fit
                - static_total: Total width of static columns
        """
        # Truncate weeks to max per page
        weeks_to_render = min(actual_weeks, self.max_weeks_per_page)
        
        # Calculate blank columns (to fill to max weeks)
        blank_cols = self.max_weeks_per_page - weeks_to_render
        
        # Build column widths
        column_widths = UTS.get_static_col_widths()  # [Uraian, Volume, Satuan]
        column_widths += [UTS.WEEK_WIDTH] * weeks_to_render
        column_widths += [UTS.WEEK_WIDTH] * blank_cols
        
        # Apply remainder handling
        current_total = sum(column_widths)
        remainder = self.table_width - current_total
        if abs(remainder) <= 10:
            column_widths[-1] += remainder
        
        return {
            'table_width': self.table_width,
            'weeks_to_render': weeks_to_render,
            'blank_cols': blank_cols,
            'column_widths': column_widths,
            'max_weeks_per_page': self.max_weeks_per_page,
            'static_total': UTS.STATIC_TOTAL,
            'week_width': UTS.WEEK_WIDTH,
        }
    
    def get_num_pages(self, total_weeks: int) -> int:
        """Calculate number of pages needed for given weeks."""
        if total_weeks <= 0:
            return 1
        return (total_weeks + self.max_weeks_per_page - 1) // self.max_weeks_per_page


# Shorthand alias
TLC = TableLayoutCalculator


class WeekHeaderFormatter:
    """
    Unified week header formatter for consistent 2-line week headers.
    
    Usage:
        from .table_styles import WeekHeaderFormatter as WHF
        
        header = WHF.format(week_num=5, date_range='01/01-07/01')
        # Returns: {'line1': 'W5', 'line2': '01/01-07/01'}
        
        # For Paragraph (Grid View, Gantt):
        para = WHF.create_paragraph(week_num=5, date_range='01/01-07/01', style)
        
        # For Drawing String (Kurva S):
        WHF.draw_on_canvas(drawing, x, y, week_num, date_range)
    """
    
    @classmethod
    def format(cls, week_num: int, date_range: str = None) -> dict:
        """
        Format week header data.
        
        Args:
            week_num: Week number (1, 2, 3, ...)
            date_range: Optional date range string (e.g., '01/01-07/01')
            
        Returns:
            dict with 'line1' (week label) and 'line2' (date range)
        """
        return {
            'line1': f'W{week_num}',
            'line2': date_range or ''
        }
    
    @classmethod
    def format_html(cls, week_num: int, date_range: str = None) -> str:
        """
        Format as HTML for Paragraph (Grid View, Gantt).
        
        Returns:
            HTML string with 2 lines: '<b>W5</b><br/><font size="4">01/01-07/01</font>'
        """
        week_label = f'W{week_num}'
        if date_range:
            return f'<b>{week_label}</b><br/><font size="{UTS.WEEK_DATE_FONT_SIZE}">{date_range}</font>'
        return f'<b>{week_label}</b>'
    
    @classmethod
    def create_paragraph(cls, week_num: int, date_range: str, style):
        """
        Create Paragraph object for Table cell.
        
        Args:
            week_num: Week number
            date_range: Date range string
            style: ParagraphStyle to apply
            
        Returns:
            Paragraph object
        """
        from reportlab.platypus import Paragraph
        html = cls.format_html(week_num, date_range)
        return Paragraph(html, style)
    
    @classmethod
    def draw_on_canvas(cls, drawing, x: float, y: float, week_num: int, 
                       date_range: str = None, text_color=None):
        """
        Draw week header directly on Drawing canvas (for Kurva S).
        
        Args:
            drawing: ReportLab Drawing object
            x: X position (center)
            y: Y position of bottom line
            week_num: Week number
            date_range: Optional date range
            text_color: Text color (default: white)
        """
        from reportlab.graphics.shapes import String
        
        if text_color is None:
            text_color = colors.white
        
        # Line 1: Week number (WX) - positioned higher
        drawing.add(String(x, y + 8, f'W{week_num}', 
                          fontSize=UTS.WEEK_HEADER_FONT_SIZE,
                          fontName=UTS.WEEK_HEADER_FONT_NAME, 
                          fillColor=text_color, 
                          textAnchor='middle'))
        
        # Line 2: Date range - positioned lower
        if date_range:
            drawing.add(String(x, y, date_range, 
                              fontSize=UTS.WEEK_DATE_FONT_SIZE,
                              fontName=UTS.DATA_FONT_NAME, 
                              fillColor=text_color, 
                              textAnchor='middle'))


# Shorthand alias
WHF = WeekHeaderFormatter


class HierarchyStyler:
    """
    Unified hierarchy styling for klasifikasi/sub_klasifikasi rows.
    
    Usage:
        from .table_styles import HierarchyStyler as HS
        
        # Get style commands for TableStyle
        commands = HS.get_style_commands(hierarchy_map)
        table.setStyle(TableStyle(base_commands + commands))
        
        # Get background color for Drawing
        bg_color = HS.get_row_background(level=1)  # klasifikasi
    """
    
    # Row type constants
    TYPE_KLASIFIKASI = 'klasifikasi'
    TYPE_SUB_KLASIFIKASI = 'sub_klasifikasi'
    TYPE_PEKERJAAN = 'pekerjaan'
    
    # Level mapping
    LEVEL_KLASIFIKASI = 1
    LEVEL_SUB_KLASIFIKASI = 2
    LEVEL_PEKERJAAN = 3
    
    @classmethod
    def get_row_background(cls, level: int = None, row_type: str = None):
        """
        Get background color for given hierarchy level or type.
        
        Args:
            level: Hierarchy level (1=klasifikasi, 2=sub, 3+=pekerjaan)
            row_type: Row type string ('klasifikasi', 'sub_klasifikasi', 'pekerjaan')
            
        Returns:
            ReportLab color object or None for default
        """
        if row_type == cls.TYPE_KLASIFIKASI or level == cls.LEVEL_KLASIFIKASI:
            return UTS.get_klasifikasi_bg_color()
        elif row_type == cls.TYPE_SUB_KLASIFIKASI or level == cls.LEVEL_SUB_KLASIFIKASI:
            return UTS.get_sub_klasifikasi_bg_color()
        return None  # Default/pekerjaan - no special background
    
    @classmethod
    def get_row_font(cls, level: int = None, row_type: str = None) -> tuple:
        """
        Get font (name, size) for given hierarchy level.
        
        Returns:
            tuple of (font_name, font_size)
        """
        if row_type == cls.TYPE_KLASIFIKASI or level == cls.LEVEL_KLASIFIKASI:
            return (UTS.KLASIFIKASI_FONT_NAME, UTS.KLASIFIKASI_FONT_SIZE)
        elif row_type == cls.TYPE_SUB_KLASIFIKASI or level == cls.LEVEL_SUB_KLASIFIKASI:
            return (UTS.SUB_KLASIFIKASI_FONT_NAME, UTS.SUB_KLASIFIKASI_FONT_SIZE)
        return (UTS.DATA_FONT_NAME, UTS.DATA_FONT_SIZE)
    
    @classmethod
    def get_style_commands(cls, hierarchy: dict, header_offset: int = 1) -> list:
        """
        Generate TableStyle commands for hierarchy rows.
        
        Args:
            hierarchy: Dict mapping row_index -> level (e.g., {0: 1, 3: 2, 5: 3})
            header_offset: Number of header rows (default 1)
            
        Returns:
            List of TableStyle command tuples
        """
        commands = []
        
        for row_idx, level in hierarchy.items():
            actual_row = row_idx + header_offset
            bg_color = cls.get_row_background(level=level)
            font_name, font_size = cls.get_row_font(level=level)
            
            if bg_color:
                commands.append(('BACKGROUND', (0, actual_row), (-1, actual_row), bg_color))
            
            # Bold font for klasifikasi/sub_klasifikasi
            if level in [cls.LEVEL_KLASIFIKASI, cls.LEVEL_SUB_KLASIFIKASI]:
                commands.append(('FONTNAME', (0, actual_row), (-1, actual_row), font_name))
                commands.append(('FONTSIZE', (0, actual_row), (-1, actual_row), font_size))
        
        return commands


# Shorthand alias
HS = HierarchyStyler


class DataRowParser:
    """
    Unified data row parser for extracting uraian, volume, satuan, level.
    
    Usage:
        from .table_styles import DataRowParser as DRP
        
        # Parse from adapter row (list format)
        data = DRP.from_list(row, static_cols=3)
        
        # Parse from dict format
        data = DRP.from_dict(row_dict)
        
        # Access data
        uraian = data['uraian']
        volume = data['volume']
    """
    
    @classmethod
    def from_list(cls, row: list, static_cols: int = 3) -> dict:
        """
        Parse row data from list format (adapter output).
        
        Format: [uraian, volume, satuan, week1, week2, ...]
        
        Args:
            row: List of cell values
            static_cols: Number of static columns (default 3: Uraian, Volume, Satuan)
            
        Returns:
            dict with parsed data
        """
        return {
            'uraian': str(row[0]) if len(row) > 0 else '',
            'volume': str(row[1]) if len(row) > 1 else '',
            'satuan': str(row[2]) if len(row) > 2 else '',
            'week_values': [str(row[i]) for i in range(static_cols, len(row))],
        }
    
    @classmethod
    def from_dict(cls, row_dict: dict) -> dict:
        """
        Parse row data from dict format.
        
        Args:
            row_dict: Dict with keys like 'name', 'uraian', 'volume', 'satuan', 'level', etc.
            
        Returns:
            Normalized dict with standard keys
        """
        return {
            'uraian': row_dict.get('name') or row_dict.get('uraian', ''),
            'volume': row_dict.get('volume_display') or row_dict.get('volume', ''),
            'satuan': row_dict.get('unit') or row_dict.get('satuan', ''),
            'level': row_dict.get('level', 3),
            'type': row_dict.get('type', 'pekerjaan'),
            'week_planned': row_dict.get('week_planned', []),
            'week_actual': row_dict.get('week_actual', []),
        }
    
    @classmethod
    def get_row_type(cls, level: int) -> str:
        """
        Get row type string from level.
        
        Args:
            level: Hierarchy level (1, 2, 3+)
            
        Returns:
            'klasifikasi', 'sub_klasifikasi', or 'pekerjaan'
        """
        if level == 1:
            return HierarchyStyler.TYPE_KLASIFIKASI
        elif level == 2:
            return HierarchyStyler.TYPE_SUB_KLASIFIKASI
        return HierarchyStyler.TYPE_PEKERJAAN
    
    @classmethod
    def is_pekerjaan(cls, row_dict: dict) -> bool:
        """Check if row is a pekerjaan (leaf) row."""
        return row_dict.get('type') == 'pekerjaan' or row_dict.get('level', 3) >= 3


# Shorthand alias
DRP = DataRowParser


# ================================================================
# SECTION HEADER FORMATTER - Unified Section Headers
# ================================================================

class SectionHeaderFormatter:
    """
    Centralized section header formatting for consistent labels across all exports.
    
    Provides unified:
    - Language: Indonesian (consistent terminology)
    - Font size: Fixed size for all headers
    - Format: Standardized pattern with page/column info
    
    Usage:
        from .table_styles import SectionHeaderFormatter as SHF
        
        title = SHF.grid_view('PLANNED', 1, 3)  # "JADWAL PEKERJAAN - PLANNED (Halaman 1/3)"
        title = SHF.kurva_s(1, 3, 1, 18)        # "KURVA S - Halaman 1/3 (Minggu 1-18)"
        title = SHF.gantt(2, 3, 19, 36)         # "GANTT CHART - Halaman 2/3 (Minggu 19-36)"
    """
    
    # Font constants for section headers (UNIFIED)
    FONT_SIZE = 12
    FONT_NAME = 'Helvetica-Bold'
    FONT_COLOR = '#000000'  # Black for all section headers
    
    # Section type labels (as requested by user)
    LABEL_INPUT_PLANNED = 'Input Progress Planned'
    LABEL_INPUT_ACTUAL = 'Input Progress Actual'
    LABEL_KURVA_S = 'KURVA S'
    LABEL_GANTT = 'Gantt Chart'
    
    @classmethod
    def input_progress(cls, progress_type: str, page: int, total_pages: int,
                       week_start: int = None, week_end: int = None) -> str:
        """
        Format Input Progress section header.
        
        Args:
            progress_type: 'PLANNED' or 'ACTUAL'
            page: Current page number
            total_pages: Total pages
            week_start: Optional start week
            week_end: Optional end week
            
        Returns:
            "Input Progress Planned - Halaman 1/3 (Minggu 1-18)" or
            "Input Progress Actual - Halaman 1/3 (Minggu 1-18)"
        """
        label = cls.LABEL_INPUT_PLANNED if progress_type.upper() == 'PLANNED' else cls.LABEL_INPUT_ACTUAL
        
        # Build: LABEL - Halaman a/X (Minggu n-m)
        if total_pages > 1:
            result = f"{label} - Halaman {page}/{total_pages}"
        else:
            result = label
        
        if week_start is not None and week_end is not None:
            result += f" (Minggu {week_start}-{week_end})"
        
        return result
    
    @classmethod
    def kurva_s(cls, page: int, total_pages: int, week_start: int, week_end: int) -> str:
        """
        Format Kurva S section header.
        
        Args:
            page: Current page number
            total_pages: Total pages
            week_start: Starting week of this page
            week_end: Ending week of this page
            
        Returns:
            Formatted header like "KURVA S - Halaman 1/3 (Minggu 1-18)"
        """
        if total_pages > 1:
            return f"{cls.LABEL_KURVA_S} - Halaman {page}/{total_pages} (Minggu {week_start}-{week_end})"
        return f"{cls.LABEL_KURVA_S} (Minggu {week_start}-{week_end})"
    
    @classmethod
    def gantt(cls, page: int, total_pages: int, week_start: int, week_end: int) -> str:
        """
        Format Gantt Chart section header.
        
        Args:
            page: Current page number
            total_pages: Total pages
            week_start: Starting week of this page
            week_end: Ending week of this page
            
        Returns:
            Formatted header like "GANTT CHART - Halaman 1/3 (Minggu 1-18)"
        """
        if total_pages > 1:
            return f"{cls.LABEL_GANTT} - Halaman {page}/{total_pages} (Minggu {week_start}-{week_end})"
        return f"{cls.LABEL_GANTT} (Minggu {week_start}-{week_end})"
    
    @classmethod
    def custom(cls, label: str, page: int = 1, total_pages: int = 1, suffix: str = '') -> str:
        """
        Generic section header with custom label.
        
        Args:
            label: Custom section label (e.g., 'REKAPITULASI RAB')
            page: Current page
            total_pages: Total pages
            suffix: Optional suffix (e.g., '(Minggu 1-18)')
            
        Returns:
            Formatted header
        """
        base = label
        if total_pages > 1:
            base = f"{label} - Halaman {page}/{total_pages}"
        if suffix:
            return f"{base} {suffix}"
        return base


# Shorthand alias
SHF = SectionHeaderFormatter
