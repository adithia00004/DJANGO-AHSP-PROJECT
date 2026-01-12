# =====================================================================
# FILE: detail_project/exports/pdf_table_builder.py
# Unified Table Builder for PDF Export
# =====================================================================
"""
PDFTableBuilder - Single source of truth for table creation.

This module provides unified table building utilities that ensure
consistent styling across all PDF export tables (Grid, Kurva S, Gantt,
Detail Progress, Summary, etc.)

Usage:
    from .pdf_table_builder import PDFTableBuilder
    
    builder = PDFTableBuilder(config)
    table = builder.create_table(data, col_widths, table_type='grid')
"""

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Table, TableStyle, Paragraph

from .table_styles import UnifiedTableStyles as UTS, HierarchyStyler as HS


# =====================================================================
# TABLE TYPES ENUM
# =====================================================================

class TableType:
    """Table type constants for styling selection."""
    GRID = 'grid'           # Main data grid (compact)
    DETAIL = 'detail'       # Detail progress table
    SUMMARY = 'summary'     # Executive summary table
    KURVA_S = 'kurva_s'     # Kurva S data table
    GANTT = 'gantt'         # Gantt chart table
    COVER = 'cover'         # Cover page info table
    FOOTER = 'footer'       # Footer/totals table


# =====================================================================
# PDF TABLE BUILDER CLASS
# =====================================================================

class PDFTableBuilder:
    """
    Unified table builder for all PDF tables.
    
    Provides consistent styling across all table types with centralized
    paragraph creation and style application.
    
    Usage:
        builder = PDFTableBuilder(config)
        
        # Create paragraph for cell
        cell = builder.create_cell_paragraph('Text', align='CENTER', bold=True)
        
        # Build complete table
        table = builder.create_table(data, col_widths, table_type='grid')
        
        # Apply hierarchy styling
        builder.apply_hierarchy_style(table, hierarchy_map)
    """
    
    def __init__(self, config=None):
        """
        Initialize builder with optional export config.
        
        Args:
            config: ExportConfig object (optional, uses UTS defaults if None)
        """
        self.config = config
        self._styles_cache = {}
        self._base_styles = getSampleStyleSheet()
    
    # =========================================
    # PARAGRAPH CREATION (replaces all P() functions)
    # =========================================
    
    def create_cell_paragraph(
        self, 
        text, 
        align='LEFT', 
        bold=False, 
        font_size=None, 
        text_color=None,
        table_type=TableType.GRID
    ):
        """
        Create a Paragraph for table cell with proper styling.
        
        This is the single source for all cell paragraph creation,
        replacing all nested P() functions throughout the codebase.
        
        Args:
            text: Cell text content
            align: Text alignment ('LEFT', 'CENTER', 'RIGHT')
            bold: Whether text should be bold
            font_size: Font size (uses table_type default if None)
            text_color: Text color (uses UTS.TEXT_PRIMARY if None)
            table_type: Table type for default styling
            
        Returns:
            Paragraph object
        """
        # Resolve alignment
        alignment_map = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}
        alignment = alignment_map.get(align.upper(), TA_LEFT)
        
        # Resolve font size based on table type
        if font_size is None:
            font_size = self._get_default_font_size(table_type)
        
        # Resolve font name
        font_name = 'Helvetica-Bold' if bold else 'Helvetica'
        
        # Resolve text color
        if text_color is None:
            fill_color = colors.HexColor(UTS.TEXT_PRIMARY)
        elif isinstance(text_color, str):
            fill_color = colors.HexColor(text_color)
        else:
            fill_color = text_color
        
        # Create style with cache key for performance
        cache_key = f"{table_type}_{align}_{bold}_{font_size}"
        
        if cache_key not in self._styles_cache:
            self._styles_cache[cache_key] = ParagraphStyle(
                f'Cell_{cache_key}',
                parent=self._base_styles['Normal'],
                fontSize=font_size,
                fontName=font_name,
                alignment=alignment,
                textColor=fill_color,
                leading=font_size * 1.2,
            )
        
        return Paragraph(str(text or ''), self._styles_cache[cache_key])
    
    def create_header_paragraph(
        self,
        text,
        table_type=TableType.GRID,
        is_week_header=False,
        date_range=None
    ):
        """
        Create header cell paragraph with appropriate styling.
        
        Args:
            text: Header text
            table_type: Table type
            is_week_header: Whether this is a week column header
            date_range: Optional date range for week headers
            
        Returns:
            Paragraph object
        """
        if is_week_header:
            # 2-line format for week headers: WX on top, date range below
            font_size = UTS.WEEK_HEADER_FONT_SIZE
            if date_range:
                date_range_nowrap = date_range.replace(' ', '&nbsp;')
                text = f'<b>{text}</b><br/><font size="{UTS.WEEK_DATE_FONT_SIZE}">{date_range_nowrap}</font>'
            else:
                text = f'<b>{text}</b>'
        else:
            font_size = self._get_header_font_size(table_type)
            text = f'<b>{text}</b>' if text else ''
        
        style = ParagraphStyle(
            f'Header_{table_type}_{is_week_header}',
            parent=self._base_styles['Normal'],
            fontSize=font_size,
            fontName=UTS.HEADER_FONT_NAME,
            alignment=TA_CENTER,
            textColor=colors.white,
            leading=font_size * 1.4 if is_week_header else font_size * 1.2,
        )
        
        return Paragraph(text, style)
    
    # =========================================
    # TABLE CREATION
    # =========================================
    
    def create_table(
        self,
        data,
        col_widths,
        table_type=TableType.GRID,
        repeat_rows=1,
        hierarchy=None
    ):
        """
        Create table with unified styling.
        
        Args:
            data: List of rows (each row is a list of cells)
            col_widths: List of column widths in points
            table_type: Table type for styling
            repeat_rows: Number of header rows to repeat
            hierarchy: Optional dict mapping row_index -> level
            
        Returns:
            Styled Table object
        """
        table = Table(data, colWidths=col_widths, repeatRows=repeat_rows)
        
        # Apply base style
        style_commands = self._get_base_style_commands(table_type)
        
        # Apply hierarchy styling if provided
        if hierarchy:
            hierarchy_commands = HS.get_style_commands(hierarchy, header_offset=repeat_rows)
            style_commands.extend(hierarchy_commands)
        
        table.setStyle(TableStyle(style_commands))
        return table
    
    def _get_base_style_commands(self, table_type):
        """Get base TableStyle commands for given table type."""
        # Common colors from UTS
        header_bg = colors.HexColor(UTS.HEADER_BG)
        header_text = colors.white
        inner_border = colors.HexColor(UTS.INNER_BORDER)
        outer_border = colors.HexColor(UTS.OUTER_BORDER)
        
        # Padding
        pad_top, pad_bottom, pad_left, pad_right = UTS.get_padding_tuple_mm()
        
        # Get table-specific settings
        header_font_size = self._get_header_font_size(table_type)
        data_font_size = self._get_default_font_size(table_type)
        
        # Adjust header background for different table types
        if table_type == TableType.DETAIL:
            header_bg = colors.HexColor(UTS.SECTION_HEADER_BG)
            header_text = colors.HexColor(UTS.TEXT_PRIMARY)
        elif table_type == TableType.COVER:
            # No header background for cover tables
            header_bg = None
        
        commands = [
            # Alignment
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Fonts
            ('FONTNAME', (0, 0), (-1, 0), UTS.HEADER_FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, 0), header_font_size),
            ('FONTNAME', (0, 1), (-1, -1), UTS.DATA_FONT_NAME),
            ('FONTSIZE', (0, 1), (-1, -1), data_font_size),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), UTS.INNER_BORDER_WIDTH, inner_border),
            ('BOX', (0, 0), (-1, -1), UTS.OUTER_BORDER_WIDTH, outer_border),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), pad_top),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad_bottom),
            ('LEFTPADDING', (0, 0), (-1, -1), pad_left),
            ('RIGHTPADDING', (0, 0), (-1, -1), pad_right),
        ]
        
        # Add header background if applicable
        if header_bg:
            commands.insert(0, ('BACKGROUND', (0, 0), (-1, 0), header_bg))
            commands.insert(1, ('TEXTCOLOR', (0, 0), (-1, 0), header_text))
        
        return commands
    
    # =========================================
    # HELPER METHODS
    # =========================================
    
    def _get_default_font_size(self, table_type):
        """Get default data font size for table type."""
        size_map = {
            TableType.GRID: UTS.GRID_DATA_FONT_SIZE,
            TableType.DETAIL: UTS.DETAIL_DATA_FONT_SIZE,
            TableType.SUMMARY: UTS.SUMMARY_DATA_FONT_SIZE,
            TableType.KURVA_S: UTS.GRID_DATA_FONT_SIZE,
            TableType.GANTT: UTS.GRID_DATA_FONT_SIZE,
            TableType.COVER: UTS.SUMMARY_DATA_FONT_SIZE,
            TableType.FOOTER: UTS.DETAIL_DATA_FONT_SIZE,
        }
        return size_map.get(table_type, UTS.GRID_DATA_FONT_SIZE)
    
    def _get_header_font_size(self, table_type):
        """Get header font size for table type."""
        size_map = {
            TableType.GRID: UTS.GRID_HEADER_FONT_SIZE,
            TableType.DETAIL: UTS.DETAIL_HEADER_FONT_SIZE,
            TableType.SUMMARY: UTS.SUMMARY_HEADER_FONT_SIZE,
            TableType.KURVA_S: UTS.GRID_HEADER_FONT_SIZE,
            TableType.GANTT: UTS.GRID_HEADER_FONT_SIZE,
            TableType.COVER: UTS.SUMMARY_HEADER_FONT_SIZE,
            TableType.FOOTER: UTS.DETAIL_HEADER_FONT_SIZE,
        }
        return size_map.get(table_type, UTS.GRID_HEADER_FONT_SIZE)
    
    # =========================================
    # STATUS BADGE CREATION
    # =========================================
    
    def create_status_badge(self, status):
        """
        Create status indicator with appropriate color.
        
        Args:
            status: Status string ('On Track', 'Ahead', 'Behind', 'Critical')
            
        Returns:
            Paragraph with colored status badge
        """
        color_map = {
            'On Track': UTS.STATUS_ON_TRACK,
            'Ahead': UTS.STATUS_AHEAD,
            'Behind': UTS.STATUS_BEHIND,
            'Critical': UTS.STATUS_CRITICAL,
        }
        status_color = color_map.get(status, UTS.TEXT_MUTED)
        
        badge_style = ParagraphStyle(
            'StatusBadge',
            parent=self._base_styles['Normal'],
            fontSize=UTS.DETAIL_DATA_FONT_SIZE,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(status_color),
            alignment=TA_CENTER,
        )
        
        return Paragraph(f'<b>{status}</b>', badge_style)


# =====================================================================
# SHORTHAND ALIAS
# =====================================================================
PTB = PDFTableBuilder
