
# =====================================================================
# FILE: detail_project/exports/pdf_exporter.py
# Copy this entire file
# =====================================================================

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Flowable,
    Spacer, PageBreak, KeepTogether, Image, NextPageTemplate
)
from reportlab.graphics.shapes import Drawing, String, Line, Rect, Circle
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker
from io import BytesIO
from typing import Dict, Any, List
from .base import ConfigExporterBase
from ..export_config import get_page_size_mm
from .table_styles import (
    UnifiedTableStyles as UTS,
    TableLayoutCalculator as TLC,
    WeekHeaderFormatter as WHF,
    HierarchyStyler as HS,
    DataRowParser as DRP,
    SectionHeaderFormatter as SHF
)
from .pdf_table_builder import PDFTableBuilder, TableType
from django.http import HttpResponse
import logging

# Module-level logger for PDF export operations
logger = logging.getLogger(__name__)

PAGE_SIZE_MAP = {
    'A4': A4,
    'A3': A3,
}


# =====================================================================
# NUMBERED CANVAS - Running Page Header/Footer
# =====================================================================

from reportlab.pdfgen import canvas as pdf_canvas
from datetime import datetime


class NumberedCanvas(pdf_canvas.Canvas):
    """
    Custom canvas with running page headers and footers.
    
    Simplified implementation that draws header/footer on each page
    and adds page numbers at the end.
    
    Features:
    - Header: Project name (left) | Segment title with page (1/X) (right)
    - Footer: Watermark (right)
    - Segment-aware page numbering that resets per segment
    """
    
    def __init__(self, *args, project_name='', section_title='', **kwargs):
        self._project_name = project_name
        self._section_title = section_title
        self._page_count = 0
        
        # Segment tracking for (1/X) format
        self._current_segment = ''           # Current segment name e.g. "Rincian Progress Bulan ke-3"
        self._segment_pages = {}             # {segment_name: [page_numbers]}
        self._page_segments = {}             # {absolute_page: segment_name}
        self._segment_page_within = {}       # {absolute_page: page_within_segment}
        
        super().__init__(*args, **kwargs)
    
    def set_segment(self, segment_name):
        """Set current segment name. Call this when entering a new segment."""
        self._current_segment = segment_name
        if segment_name and segment_name not in self._segment_pages:
            self._segment_pages[segment_name] = []
    
    def showPage(self):
        """Called when a page finishes - track segment and draw decorations."""
        self._page_count += 1
        
        # Track which segment this page belongs to
        if self._current_segment:
            self._page_segments[self._page_count] = self._current_segment
            if self._current_segment not in self._segment_pages:
                self._segment_pages[self._current_segment] = []
            self._segment_pages[self._current_segment].append(self._page_count)
            # Calculate page within segment
            self._segment_page_within[self._page_count] = len(self._segment_pages[self._current_segment])
        
        # Draw header/footer on THIS page BEFORE finishing
        self._draw_header_footer()
        
        # Standard behavior
        super().showPage()
    
    def save(self):
        """Save with page decorations already drawn."""
        # Second pass: Update segment page totals (X in 1/X)
        # Note: This happens after all pages are built, so we know totals
        super().save()
    
    def _draw_header_footer(self):
        """Draw header and footer on current page.
        
        Skip page 1 (cover page) - no header/footer on cover.
        """
        # SKIP COVER PAGE (page 1)
        if self._page_count == 1:
            return
        
        width, height = self._pagesize
        side_margin = 12 * mm  # Left/right margin
        
        # Colors
        header_color = colors.HexColor(UTS.TEXT_SECONDARY)
        footer_color = colors.HexColor(UTS.TEXT_MUTED)
        line_color = colors.HexColor(UTS.LIGHT_BORDER)
        
        # ===== HEADER (closer to top edge) =====
        header_offset = 8 * mm  # Distance from top edge
        header_y = height - header_offset
        
        # Header line
        self.setStrokeColor(line_color)
        self.setLineWidth(0.5)
        self.line(side_margin, header_y - 3*mm, width - side_margin, header_y - 3*mm)
        
        # Project name (left)
        self.setFont('Helvetica', 8)
        self.setFillColor(header_color)
        project_name = (self._project_name or '')[:50]
        self.drawString(side_margin, header_y, project_name)
        
        # Segment title with page number (right)
        segment_name = self._page_segments.get(self._page_count, self._section_title or '')
        page_within = self._segment_page_within.get(self._page_count, 0)
        
        if segment_name and page_within > 0:
            # Format: "Segment Name - Halaman 1"
            # Note: Total unknown during single-pass, would need two-pass for (1/X) format
            right_text = f"{segment_name} - Halaman {page_within}"
        else:
            right_text = (self._section_title or '')[:30]
        
        self.drawRightString(width - side_margin, header_y, right_text[:60])
        
        # ===== FOOTER (closer to bottom edge) =====
        footer_offset = 6 * mm  # Distance from bottom edge
        footer_y = footer_offset
        
        # Footer line
        self.setStrokeColor(line_color)
        self.line(side_margin, footer_y + 6*mm, width - side_margin, footer_y + 6*mm)
        
        # Watermark (right)
        self.drawRightString(width - side_margin, footer_y, 'Dashboard-RAB.com')



# Helper function to create canvas maker
def make_numbered_canvas(project_name='', section_title=''):
    """
    Create a canvas maker function for doc.build().
    
    Usage:
        doc.build(story, canvasmaker=make_numbered_canvas('Project X', 'Laporan'))
    """
    def canvas_maker(*args, **kwargs):
        return NumberedCanvas(*args, project_name=project_name, 
                            section_title=section_title, **kwargs)
    return canvas_maker


class SegmentMarker(Flowable):
    """
    Invisible flowable that signals a segment change to NumberedCanvas.
    
    When this flowable is drawn, it tells the canvas to start a new segment
    for page numbering purposes.
    
    Usage:
        story.append(SegmentMarker("Rincian Progress Bulan ke-3"))
        story.append(rincian_table)
        story.append(SegmentMarker(""))  # End segment
    """
    
    def __init__(self, segment_name):
        Flowable.__init__(self)
        self.segment_name = segment_name
        self.width = 0
        self.height = 0
    
    def draw(self):
        """Signal segment change to canvas."""
        canvas = self.canv
        if hasattr(canvas, 'set_segment'):
            canvas.set_segment(self.segment_name)
    
    def wrap(self, availWidth, availHeight):
        """This flowable takes no space."""
        return (0, 0)


class PDFExporter(ConfigExporterBase):
    """PDF Export handler with ReportLab"""
    
    def __init__(self, config):
        super().__init__(config)
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create paragraph styles"""
        styles = getSampleStyleSheet()
        
        return {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=self.config.font_size_title,
                textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                spaceAfter=1*mm,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold'
            ),
            'subtitle': ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=self.config.font_size_header,
                spaceAfter=1*mm,
                alignment=TA_LEFT
            ),
            'subtitle_left': ParagraphStyle(
                'CustomSubtitleLeft',
                parent=styles['Heading2'],
                fontSize=self.config.font_size_header,
                spaceAfter=1*mm,
                alignment=TA_LEFT
            ),
            'normal': ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=self.config.font_size_normal
            )
        }
    
    # =========================================================================
    # SHARED HELPER METHODS FOR MONTHLY REPORT SEGMENTS
    # Used by: Rincian Progress, Kurva S Lengkap, Kurva S Bulanan
    # =========================================================================
    
    def _get_row_styling(self, row_type: str, row_idx: int = 0) -> tuple:
        """
        Get background color and font weight based on row type.
        
        Args:
            row_type: 'klasifikasi', 'sub_klasifikasi', or 'pekerjaan'
            row_idx: Row index for zebra striping (only used for pekerjaan)
            
        Returns:
            Tuple of (bg_color, font_weight)
        """
        if row_type == 'klasifikasi':
            bg_color = colors.HexColor(UTS.KLASIFIKASI_BG)
            font_weight = 'Helvetica-Bold'
        elif row_type == 'sub_klasifikasi':
            bg_color = colors.HexColor(UTS.SUB_KLASIFIKASI_BG)
            font_weight = 'Helvetica-Bold'
        else:
            bg_color = colors.white if row_idx % 2 == 0 else colors.HexColor('#f8f9fa')
            font_weight = 'Helvetica'
        return bg_color, font_weight
    
    def _render_uraian_text(
        self, 
        drawing, 
        raw_name: str, 
        level: int, 
        uraian_width: float, 
        x: float, 
        row_y: float, 
        row_height: float, 
        font_weight: str = 'Helvetica',
        font_size: int = 7,
        char_width: float = 3.3,
        padding_left: float = 4,
        padding_right: float = 6
    ):
        """
        Render uraian pekerjaan text with 2-line support and proper indentation.
        
        Args:
            drawing: ReportLab Drawing object
            raw_name: Text to render (without indent)
            level: Hierarchy level for indentation (2 spaces per level)
            uraian_width: Total column width in points
            x: X position (left edge of column)
            row_y: Y position (bottom of row)
            row_height: Row height in points
            font_weight: 'Helvetica' or 'Helvetica-Bold'
            font_size: Font size in points (default 7)
            char_width: Average character width in points (default 3.3)
            padding_left: Left padding in points (default 4)
            padding_right: Right padding in points (default 6)
        """
        # Calculate indent
        indent_chars = ' ' * (level * 2) if level > 0 else ''
        
        # Calculate usable width and chars per line
        usable_width = uraian_width - padding_left - padding_right
        chars_per_line = int(usable_width / char_width)
        
        # Account for indent in available space
        text_chars = chars_per_line - len(indent_chars)
        
        if len(raw_name) > text_chars:
            # 2-line rendering - both lines get same indent
            line1 = indent_chars + raw_name[:text_chars]
            remaining = raw_name[text_chars:]
            if len(remaining) > text_chars - 2:
                line2 = indent_chars + remaining[:text_chars-2] + '..'
            else:
                line2 = indent_chars + remaining
            
            drawing.add(String(x + padding_left, row_y + row_height * 0.65, line1, 
                              fontSize=font_size, fontName=font_weight))
            drawing.add(String(x + padding_left, row_y + row_height * 0.25, line2, 
                              fontSize=font_size, fontName=font_weight))
        else:
            # Single line - vertically centered
            full_name = indent_chars + raw_name
            drawing.add(String(x + padding_left, row_y + row_height * 0.35, full_name, 
                              fontSize=font_size, fontName=font_weight))
    
    def _calculate_pagination(
        self,
        total_rows: int,
        row_height: float,
        max_height: float,
        header_height: float = 20,
        chart_height: float = 40,
        legend_height: float = 25,
        signature_height: float = 140,
        extra_padding: float = 20
    ) -> dict:
        """
        Calculate pagination for multi-page tables.
        
        Args:
            total_rows: Total number of data rows
            row_height: Height per row in points
            max_height: Maximum usable height per page
            header_height: Height of table header
            chart_height: Height reserved for chart overlay
            legend_height: Height for legend (first page only)
            signature_height: Height for signature section (last page only)
            extra_padding: Additional padding per page
            
        Returns:
            Dict with pagination info: rows_per_first, rows_per_middle, rows_per_last, num_pages
        """
        # Calculate available space for each page type
        first_page_space = max_height - header_height - chart_height - legend_height - extra_padding
        middle_page_space = max_height - header_height - chart_height - extra_padding
        last_page_space = max_height - header_height - chart_height - signature_height - extra_padding
        single_page_space = max_height - header_height - chart_height - legend_height - signature_height - extra_padding
        
        rows_per_first = int(first_page_space / row_height)
        rows_per_middle = int(middle_page_space / row_height)
        rows_per_last = int(last_page_space / row_height)
        rows_per_single = int(single_page_space / row_height)
        
        # Calculate number of pages needed
        if total_rows <= rows_per_single:
            num_pages = 1
        elif total_rows <= rows_per_first:
            # Fits on first page alone, but need to check with signature
            if total_rows <= rows_per_single:
                num_pages = 1
            else:
                num_pages = 2
        else:
            remaining = total_rows - rows_per_first
            if remaining <= rows_per_last:
                num_pages = 2
            else:
                remaining -= rows_per_last
                middle_pages = max(0, (remaining + rows_per_middle - 1) // rows_per_middle)
                num_pages = 1 + middle_pages + 1
        
        return {
            'rows_per_first': rows_per_first,
            'rows_per_middle': rows_per_middle,
            'rows_per_last': rows_per_last,
            'rows_per_single': rows_per_single,
            'num_pages': num_pages,
            'total_rows': total_rows
        }
    
    def _draw_week_cell(
        self,
        drawing,
        x: float,
        row_y: float,
        week_width: float,
        row_height: float,
        planned_val: str = None,
        actual_val: str = None,
        border_color=None,
        font_size: int = 5
    ):
        """
        Draw a single week column cell with optional planned/actual values.
        
        Args:
            drawing: ReportLab Drawing object
            x: X position of cell
            row_y: Y position (bottom of row)
            week_width: Width of week column
            row_height: Height of row
            planned_val: Planned progress value (optional)
            actual_val: Actual progress value (optional)
            border_color: Border color (defaults to light gray)
            font_size: Font size for values
        """
        if border_color is None:
            border_color = colors.HexColor('#cccccc')
        
        # Draw cell rectangle
        drawing.add(Rect(x, row_y, week_width, row_height,
                        fillColor=colors.white, strokeColor=border_color, strokeWidth=0.2))
        
        cell_center_x = x + week_width / 2
        
        # Draw planned value (top half)
        if planned_val:
            drawing.add(String(cell_center_x, row_y + row_height * 0.6, str(planned_val)[:4],
                              fontSize=font_size, fontName='Helvetica',
                              fillColor=colors.HexColor(UTS.PLANNED_COLOR),
                              textAnchor='middle'))
        
        # Draw actual value (bottom half)
        if actual_val:
            drawing.add(String(cell_center_x, row_y + row_height * 0.15, str(actual_val)[:4],
                              fontSize=font_size, fontName='Helvetica',
                              fillColor=colors.HexColor(UTS.ACTUAL_COLOR),
                              textAnchor='middle'))
    
    # =========================================================================
    # PHASE 3: NUMBER FORMATTING AND TABLE STYLE HELPERS
    # =========================================================================
    
    @staticmethod
    def _format_rupiah(value: float, with_prefix: bool = True) -> str:
        """
        Format number as Indonesian Rupiah.
        
        Args:
            value: Number to format
            with_prefix: Include 'Rp ' prefix (default True)
            
        Returns:
            Formatted string like 'Rp 1.234.567' or '1.234.567'
        """
        if value is None or value == 0:
            return '-'
        try:
            formatted = f"{int(value):,}".replace(',', '.')
            return f"Rp {formatted}" if with_prefix else formatted
        except (ValueError, TypeError):
            return '-'
    
    @staticmethod
    def _format_percent(value: float, decimals: int = 2, show_zero: bool = True) -> str:
        """
        Format number as percentage.
        
        Args:
            value: Number to format (already in percentage, e.g. 75.5 for 75.5%)
            decimals: Decimal places (default 2)
            show_zero: Show '0.00%' for zero values, else show '-'
            
        Returns:
            Formatted string like '75.50%' or '-'
        """
        if value is None:
            return '-'
        if value == 0 and not show_zero:
            return '-'
        try:
            return f"{float(value):.{decimals}f}%"
        except (ValueError, TypeError):
            return '-'
    
    def _get_base_table_style(
        self, 
        with_header: bool = True,
        header_bg: str = None,
        grid_color: str = None
    ) -> list:
        """
        Get base table style commands used across all segments.
        
        Args:
            with_header: Include header styling (default True)
            header_bg: Header background color (defaults to UTS.PRIMARY_LIGHT)
            grid_color: Grid line color (defaults to UTS.LIGHT_BORDER)
            
        Returns:
            List of style tuples for TableStyle
        """
        if header_bg is None:
            header_bg = UTS.PRIMARY_LIGHT
        if grid_color is None:
            grid_color = UTS.LIGHT_BORDER
        
        style_cmds = [
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(grid_color)),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 1*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1*mm),
        ]
        
        if with_header:
            style_cmds.extend([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_bg)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ])
        
        return style_cmds
    
    def _apply_row_backgrounds(self, style_cmds: list, rows_data: list, offset: int = 1):
        """
        Apply row-specific background colors based on row type.
        
        Args:
            style_cmds: Existing style commands list (modified in place)
            rows_data: List of (row_content, row_type) tuples
            offset: Row offset for header (default 1)
        """
        for i, (_, item_type) in enumerate(rows_data):
            row_idx = i + offset
            if item_type == 'klasifikasi':
                style_cmds.append(('BACKGROUND', (0, row_idx), (-1, row_idx), 
                                  colors.HexColor(UTS.KLASIFIKASI_BG)))
            elif item_type == 'sub_klasifikasi':
                style_cmds.append(('BACKGROUND', (0, row_idx), (-1, row_idx), 
                                  colors.HexColor(UTS.SUB_KLASIFIKASI_BG)))
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """Export to PDF (supports single or multi-page payload)"""
        buffer = BytesIO()

        # Determine page size based on orientation
        orientation = getattr(self.config, 'page_orientation', 'landscape')
        size_name = getattr(self.config, 'page_size', 'A4') or 'A4'
        base_size = PAGE_SIZE_MAP.get(size_name.upper(), A4)
        if orientation == 'portrait':
            pagesize = base_size
        else:
            pagesize = landscape(base_size)

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            topMargin=self.config.margin_top * mm,
            bottomMargin=self.config.margin_bottom * mm,
            leftMargin=self.config.margin_left * mm,
            rightMargin=self.config.margin_right * mm,
            title=self.config.title
        )
        
        story = []

        def build_page(section: Dict[str, Any], is_pengesahan: bool = False):
            # Header with page-specific title
            story.extend(self._build_header(section.get('title') or self.config.title))
            story.append(Spacer(1, 5*mm))

            # Check if this page has sections (appendix with multiple tables OR pekerjaan sections)
            if 'sections' in section:
                # Check if sections are pekerjaan sections (Rincian AHSP style)
                if section['sections'] and isinstance(section['sections'][0], dict) and 'pekerjaan' in section['sections'][0]:
                    # Rincian AHSP sections (each pekerjaan with its detail table)
                    for pek_section in section['sections']:
                        self._build_pekerjaan_section(pek_section, story)
                        story.append(Spacer(1, 8*mm))
                else:
                    # Multi-section page (e.g., Parameter + Formula appendix)
                    for subsection in section['sections']:
                        # Section title
                        section_title = subsection.get('section_title')
                        if section_title:
                            section_para = Paragraph(
                                f"<b>{section_title}</b>",
                                self.styles['subtitle']
                            )
                            story.append(section_para)
                            story.append(Spacer(1, 3*mm))

                        # Section table
                        table = self._build_table(subsection)
                        story.append(table)
                        story.append(Spacer(1, 5*mm))

            else:
                # Single table page
                table = self._build_table(section)

                # On pengesahan, try to keep table + footer together when possible
                if is_pengesahan and 'footer_rows' in section:
                    bundle = []
                    bundle.append(table)
                    bundle.append(Spacer(1, 3*mm))
                    bundle.append(self._build_footer_table(section['footer_rows']))
                    story.append(KeepTogether(bundle))
                else:
                    story.append(table)
                    if 'footer_rows' in section:
                        story.append(Spacer(1, 3*mm))
                        story.append(self._build_footer_table(section['footer_rows']))

            story.append(Spacer(1, 8*mm))

        # Multi-page support
        pages = data.get('pages')
        if pages:
            for idx, section in enumerate(pages):
                is_pengesahan = (idx == 1)
                build_page(section, is_pengesahan=is_pengesahan)

                # Add signatures after first page (Volume Pekerjaan)
                if idx == 0 and self.config.signature_config.enabled:
                    bundle = self._build_signatures()
                    story.extend(bundle)

                # Page break between pages
                if idx < len(pages) - 1:
                    story.append(PageBreak())
        # Sections at root level (Rincian AHSP style)
        elif 'sections' in data and data['sections'] and isinstance(data['sections'][0], dict) and 'pekerjaan' in data['sections'][0]:
            # Rincian AHSP: sections with pekerjaan data
            build_page(data)

            # Add summary at the end
            if 'summary' in data:
                story.append(Spacer(1, 10*mm))
                summary = data['summary']
                summary_lines = [
                    f"<b>Total Pekerjaan:</b> {summary.get('total_pekerjaan', 0)}",
                    f"<b>Total Items:</b> {summary.get('total_items', 0)}",
                    f"<b>Grand Total:</b> Rp {summary.get('grand_total', '0')}",
                ]
                for line in summary_lines:
                    para = Paragraph(line, self.styles['normal'])
                    story.append(para)
                    story.append(Spacer(1, 2*mm))

            # Add signatures if enabled
            if self.config.signature_config.enabled:
                bundle = self._build_signatures()
                story.extend(bundle)
        else:
            build_page(data)
            if self.config.signature_config.enabled:
                bundle = []
                if 'footer_rows' in data:
                    bundle.append(self._build_footer_table(data['footer_rows']))
                bundle.extend(self._build_signatures())
                story.append(KeepTogether(bundle))
        
        # Append appendix recap if provided
        recap = data.get('recap')
        if recap and isinstance(recap, dict):
            # Page break before appendix when there is prior content
            if story:
                story.append(PageBreak())
            story.append(Paragraph("<b>Lampiran Rekap AHSP</b>", self.styles['subtitle']))
            story.append(Spacer(1, 3*mm))

            # Determine sensible column widths based on orientation
            page_w_mm = self._get_page_width_mm()
            usable_w = page_w_mm - (self.config.margin_left + self.config.margin_right)
            # Allocate widths: Kode (20%), Uraian (60%), Total (20%)
            col_widths = [0.20*usable_w, 0.60*usable_w, 0.20*usable_w]

            appendix_section = {
                'table_data': {
                    'headers': recap.get('headers', ['Kode AHSP', 'Uraian', 'Total HSP (Rp)']),
                    'rows': recap.get('rows', []),
                },
                'col_widths': col_widths,
            }
            story.append(self._build_table(appendix_section))

        # Attach image pages (e.g., Gantt / Kurva-S screenshots)
        attachments = data.get('attachments') or []
        for att in attachments:
            img_bytes = att.get('bytes')
            if not img_bytes:
                continue
            att_title = att.get('title') or 'Lampiran'
            story.append(PageBreak())
            story.append(Paragraph(f"<b>{att_title}</b>", self.styles['title']))
            try:
                img = Image(BytesIO(img_bytes))
                max_w = doc.width
                max_h = doc.height
                iw, ih = img.wrap(0, 0)
                scale = min(max_w / max(iw, 1), max_h / max(ih, 1), 1.0)
                img.drawWidth = iw * scale
                img.drawHeight = ih * scale
                story.append(Spacer(1, 4*mm))
                story.append(img)
            except Exception:
                continue

        # Build PDF
        # Note: NumberedCanvas temporarily disabled due to ReportLab compatibility
        # TODO: Re-enable with proper implementation
        doc.build(story)
        
        # Create response
        pdf_content = buffer.getvalue()
        buffer.close()
        
        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.pdf"
        return self._create_response(pdf_content, filename, 'application/pdf')

    def export_professional(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export professional formatted PDF report (Laporan Tertulis).
        
        This method handles:
        - Cover page
        - Table of contents (for rekap)
        - Executive summary (for monthly/weekly)
        - Comparison tables (for monthly/weekly)
        - Grid sections (separated Planned/Actual)
        - Chart attachments
        - Signature section
        """
        buffer = BytesIO()
        
        # Determine page sizes
        size_name = getattr(self.config, 'page_size', 'A4') or 'A4'
        base_size = PAGE_SIZE_MAP.get(size_name.upper(), A4)
        orientation = getattr(self.config, 'page_orientation', 'landscape')
        
        report_type_check = data.get('report_type', 'rekap')
        
        # Margins
        margin_top = self.config.margin_top * mm
        margin_bottom = self.config.margin_bottom * mm
        margin_left = self.config.margin_left * mm
        margin_right = self.config.margin_right * mm
        
        if report_type_check == 'monthly':
            # Monthly reports: Use BaseDocTemplate for mixed orientation
            # Portrait A4: for signature page, progress page
            # Portrait A3: for Kurva S portrait segment table (needs 750pt width)
            # Landscape A3: for Kurva S landscape table (needs 1100pt width)
            portrait_size = A4  # A4 Portrait (210 x 297 mm)
            portrait_a3_size = A3  # A3 Portrait (297 x 420 mm = 842 x 1190 pt)
            landscape_size = landscape(A3)  # A3 Landscape (420 x 297 mm = 1190 x 842 pt)
            
            # Calculate frame dimensions for Portrait A4
            pw, ph = portrait_size
            portrait_frame = Frame(
                margin_left, margin_bottom,
                pw - margin_left - margin_right,
                ph - margin_top - margin_bottom,
                id='portrait_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            
            # Calculate frame dimensions for Portrait A3
            pa3w, pa3h = portrait_a3_size
            portrait_a3_frame = Frame(
                margin_left, margin_bottom,
                pa3w - margin_left - margin_right,
                pa3h - margin_top - margin_bottom,
                id='portrait_a3_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            
            # Calculate frame dimensions for Landscape A3
            lw, lh = landscape_size
            landscape_frame = Frame(
                margin_left, margin_bottom,
                lw - margin_left - margin_right,
                lh - margin_top - margin_bottom,
                id='landscape_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            
            # Create page templates
            portrait_template = PageTemplate(
                id='portrait',
                frames=[portrait_frame],
                pagesize=portrait_size
            )
            portrait_a3_template = PageTemplate(
                id='portrait_a3',
                frames=[portrait_a3_frame],
                pagesize=portrait_a3_size
            )
            landscape_template = PageTemplate(
                id='landscape',
                frames=[landscape_frame],
                pagesize=landscape_size
            )
            
            doc = BaseDocTemplate(
                buffer,
                pageTemplates=[portrait_template, portrait_a3_template, landscape_template],
                title=self.config.title
            )
        elif report_type_check == 'weekly':
            # Weekly reports: Use BaseDocTemplate with portrait A4 (same setup as monthly)
            # This ensures consistent margins, padding, and layout
            portrait_size = A4  # A4 Portrait (210 x 297 mm)
            
            # Calculate frame dimensions for Portrait A4 (same as monthly)
            pw, ph = portrait_size
            portrait_frame = Frame(
                margin_left, margin_bottom,
                pw - margin_left - margin_right,
                ph - margin_top - margin_bottom,
                id='portrait_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            
            portrait_template = PageTemplate(
                id='portrait',
                frames=[portrait_frame],
                pagesize=portrait_size
            )
            
            doc = BaseDocTemplate(
                buffer,
                pageTemplates=[portrait_template],
                title=self.config.title
            )
        else:
            # Rekap: Use SimpleDocTemplate
            if orientation == 'portrait':
                pagesize = base_size
            else:
                pagesize = landscape(base_size)
            
            doc = SimpleDocTemplate(
                buffer,
                pagesize=pagesize,
                topMargin=margin_top,
                bottomMargin=margin_bottom,
                leftMargin=margin_left,
                rightMargin=margin_right,
                title=self.config.title
            )
        
        story = []
        report_type = data.get('report_type', 'rekap')
        project_info = data.get('project_info', {})
        
        # =====================================================================
        # MULTI-MONTH EXPORT SUPPORT
        # =====================================================================
        months_data = data.get('months_data', [])
        
        if report_type == 'monthly' and months_data:
            # Multi-month mode: loop over each month's data
            for month_idx, month_entry in enumerate(months_data):
                month = month_entry.get('month', 1)
                month_data = month_entry.get('data', {})
                
                # 1. Cover Page for this month
                period_info = month_data.get('period', {})
                period_info['month'] = month
                cover_elements = self._build_cover_page('monthly', project_info, period_info)
                story.extend(cover_elements)
                story.append(PageBreak())
                
                # 2. Progress Pelaksanaan for this month
                exec_summary = month_data.get('executive_summary', {})
                hierarchy_data = month_data.get('hierarchy_progress', [])
                
                progress_elements = self._build_progress_pelaksanaan_page(
                    month=month,
                    project_info=project_info,
                    summary=exec_summary,
                    hierarchy_data=hierarchy_data,
                    period_info=period_info
                )
                story.extend(progress_elements)
                story.append(PageBreak())
                
                # 3. Kurva S sections for this month
                cumulative_end_week = month_data.get('cumulative_end_week', month * 4)
                total_project_weeks = month_data.get('total_project_weeks', cumulative_end_week)
                kurva_s_data = month_data.get('kurva_s_data', [])
                all_weekly_columns = month_data.get('all_weekly_columns', [])
                base_rows = month_data.get('base_rows', [])
                hierarchy = month_data.get('hierarchy', {})
                planned_map_str = month_data.get('planned_map', {})
                actual_map_str = month_data.get('actual_map', {})
                
                if kurva_s_data or all_weekly_columns:
                    # Switch to LANDSCAPE for Kurva S pages
                    story.append(NextPageTemplate('landscape'))
                    story.append(PageBreak())
                    
                    # Segment marker for Kurva S Landscape
                    story.append(SegmentMarker(f"Kurva S Lengkap Bulan ke-{month}"))
                    
                    section_title = ParagraphStyle(
                        'SectionHeader',
                        fontSize=14,
                        textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                        fontName='Helvetica-Bold',
                        spaceAfter=5*mm,
                    )
                    story.append(Paragraph(
                        f"<b>RINGKASAN PROGRESS KURVA S (Grafik: Minggu 1 - Minggu {cumulative_end_week})</b>", 
                        section_title
                    ))
                    story.append(Spacer(1, 5*mm))
                    
                    # Build hierarchy rows
                    hierarchy_rows = []
                    for idx, row in enumerate(base_rows):
                        row_type = row.get('type', 'pekerjaan')
                        pek_id = row.get('pekerjaan_id')
                        level = hierarchy.get(idx, 2)
                        
                        if row_type == 'klasifikasi':
                            level = 1
                        elif row_type == 'sub_klasifikasi':
                            level = 2
                        else:
                            level = level if level > 0 else 3
                        
                        week_planned = []
                        week_actual = []
                        if row_type == 'pekerjaan' and pek_id:
                            for wk in range(1, total_project_weeks + 1):
                                key = f"{pek_id}-{wk}"
                                planned_val = planned_map_str.get(key, 0)
                                actual_val = actual_map_str.get(key, 0)
                                week_planned.append(str(planned_val) if planned_val else '')
                                week_actual.append(str(actual_val) if actual_val else '')
                        
                        hierarchy_rows.append({
                            'type': row_type,
                            'name': row.get('uraian', ''),
                            'volume': row.get('volume_display', '') if row_type == 'pekerjaan' else '',
                            'satuan': row.get('unit', '') if row_type == 'pekerjaan' else '',
                            'level': level,
                            'week_planned': week_planned,
                            'week_actual': week_actual
                        })
                    
                    if hierarchy_rows:
                        monthly_kurva_pages = self._build_monthly_kurva_s_table(
                            hierarchy_rows,
                            kurva_s_data,
                            all_weekly_columns,
                            total_project_weeks=total_project_weeks,
                            cumulative_end_week=cumulative_end_week,
                            row_height=22,
                            project_info=project_info
                        )
                        for page_idx, kurva_drawing in enumerate(monthly_kurva_pages):
                            if kurva_drawing:
                                story.append(kurva_drawing)
                                if page_idx < len(monthly_kurva_pages) - 1:
                                    story.append(PageBreak())
                        story.append(Spacer(1, 10*mm))
                    
                    # Portrait Kurva S Page
                    story.append(NextPageTemplate('portrait_a3'))
                    story.append(PageBreak())
                    
                    # Start Kurva S Portrait segment
                    story.append(SegmentMarker(f"Kurva S Bulanan Bulan ke-{month}"))
                    
                    portrait_title = ParagraphStyle(
                        'PortraitSectionHeader',
                        fontSize=14,
                        textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                        fontName='Helvetica-Bold',
                        spaceAfter=5*mm,
                    )
                    story.append(Paragraph(
                        f"<b>GRAFIK KURVA S (Tampilan Bulanan)</b>", 
                        portrait_title
                    ))
                    story.append(Spacer(1, 5*mm))
                    
                    planned_progress = month_data.get('planned_map', {})
                    actual_progress = month_data.get('actual_map', {})
                    
                    portrait_charts = self._build_portrait_kurva_s_chart(
                        kurva_s_data,
                        cumulative_end_week=cumulative_end_week,
                        hierarchy_rows=hierarchy_data,
                        summary=exec_summary,
                        month=month,
                        project_info=project_info,
                        planned_progress=planned_progress,
                        actual_progress=actual_progress
                    )
                    if portrait_charts:
                        for p_idx, p_chart in enumerate(portrait_charts):
                            if p_chart:
                                story.append(p_chart)
                                if p_idx < len(portrait_charts) - 1:
                                    story.append(PageBreak())
                        story.append(Spacer(1, 10*mm))
                
                # Return to portrait for next month's cover (except last month)
                if month_idx < len(months_data) - 1:
                    # Clear segment before cover page
                    story.append(SegmentMarker(""))
                    story.append(NextPageTemplate('portrait'))
                    story.append(PageBreak())
        
        # =====================================================================
        # MULTI-WEEK EXPORT SUPPORT (same pattern as multi-month)
        # =====================================================================
        weeks_data = data.get('weeks_data', [])
        
        if report_type == 'weekly' and weeks_data:
            # Multi-week mode: loop over each week's data
            for week_idx, week_entry in enumerate(weeks_data):
                week = week_entry.get('week', 1)
                week_data = week_entry.get('data', {})
                
                # 1. Cover Page for this week
                period_info = week_data.get('period', {})
                period_info['week'] = week
                cover_elements = self._build_cover_page('weekly', project_info, period_info)
                story.extend(cover_elements)
                story.append(PageBreak())
                
                # 2. Progress Pelaksanaan for this week (using weekly-specific method)
                exec_summary = week_data.get('executive_summary', {})
                hierarchy_data = week_data.get('hierarchy_progress', [])
                
                progress_elements = self._build_weekly_progress_page(
                    week=week,
                    project_info=project_info,
                    summary=exec_summary,
                    hierarchy_data=hierarchy_data,
                    period_info=period_info
                )
                story.extend(progress_elements)
                
                # Add page break for next week (except last week)
                if week_idx < len(weeks_data) - 1:
                    story.append(PageBreak())
        
        elif not months_data and not weeks_data:
            # =====================================================================
            # SINGLE MONTH / REKAP / WEEKLY (existing logic)
            # =====================================================================

            
            # 1. Cover Page
            if report_type == 'rekap':
                cover_elements = self._build_cover_page(report_type, project_info)
            else:
                period_info = data.get('period', {})
                if report_type == 'monthly':
                    period_info['month'] = data.get('month', 1)
                else:
                    period_info['week'] = data.get('week', 1)
                cover_elements = self._build_cover_page(report_type, project_info, period_info)
            
            story.extend(cover_elements)
            story.append(PageBreak())
            
            # 2. Table of Contents (for rekap only)
            if report_type == 'rekap':
                sections = data.get('sections', [])
                if sections:
                    toc_elements = self._build_table_of_contents(sections)
                    story.extend(toc_elements)
                    story.append(PageBreak())
            
            # 3. Progress Pelaksanaan Page (for monthly/weekly)
            # Combines: Identitas, Ringkasan Progress, Rincian Progress
            if report_type == 'monthly':
                exec_summary = data.get('executive_summary', {})
                hierarchy_data = data.get('hierarchy_progress', [])
                month = data.get('month', 1)
                
                progress_elements = self._build_progress_pelaksanaan_page(
                    month=month,
                    project_info=project_info,
                    summary=exec_summary,
                    hierarchy_data=hierarchy_data,
                    period_info=data.get('period', {})
                )
                story.extend(progress_elements)
                story.append(PageBreak())
            
            elif report_type == 'weekly':
                exec_summary = data.get('executive_summary', {})
                hierarchy_data = data.get('hierarchy_progress', [])
                week = data.get('week', 1)
                
                progress_elements = self._build_weekly_progress_page(
                    week=week,
                    project_info=project_info,
                    summary=exec_summary,
                    hierarchy_data=hierarchy_data,
                    period_info=data.get('period', {})
                )
                story.extend(progress_elements)
                story.append(PageBreak())
                
            # 5. Kurva S Kumulatif (for monthly - uses same approach as rekap)
            if report_type == 'monthly':
                month = data.get('month', 1)
                cumulative_end_week = data.get('cumulative_end_week', month * 4)
                total_project_weeks = data.get('total_project_weeks', cumulative_end_week)
                kurva_s_data = data.get('kurva_s_data', [])  # Chart data (cumulative only)
                all_weekly_columns = data.get('all_weekly_columns', [])  # ALL weeks for table
                base_rows = data.get('base_rows', [])
                hierarchy = data.get('hierarchy', {})
                planned_map_str = data.get('planned_map', {})
                actual_map_str = data.get('actual_map', {})
                
                if kurva_s_data or all_weekly_columns:
                    # Switch to LANDSCAPE for Kurva S pages
                    story.append(NextPageTemplate('landscape'))
                    story.append(PageBreak())
                    
                    # Segment marker for Kurva S Landscape
                    story.append(SegmentMarker(f"Kurva S Lengkap Bulan ke-{month}"))
                    
                    # Title appears after the header line (which is drawn by NumberedCanvas)
                    section_title = ParagraphStyle(
                        'SectionHeader',
                        fontSize=14,
                        textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                        fontName='Helvetica-Bold',
                        spaceAfter=5*mm,
                    )
                    story.append(Paragraph(
                        f"<b>RINGKASAN PROGRESS KURVA S (Grafik: Minggu 1 - Minggu {cumulative_end_week})</b>", 
                        section_title
                    ))
                    story.append(Spacer(1, 5*mm))
                    
                    # Build all rows from base_rows (include klasifikasi, sub_klasifikasi, pekerjaan)
                    # Include ALL weeks for table columns
                    hierarchy_rows = []
                    for idx, row in enumerate(base_rows):
                        row_type = row.get('type', 'pekerjaan')
                        pek_id = row.get('pekerjaan_id')
                        level = hierarchy.get(idx, 2)
                        
                        # Determine level based on type if not in hierarchy
                        if row_type == 'klasifikasi':
                            level = 1
                        elif row_type == 'sub_klasifikasi':
                            level = 2
                        else:
                            level = level if level > 0 else 3
                        
                        # Extract weekly planned/actual values for ALL weeks (only for pekerjaan)
                        week_planned = []
                        week_actual = []
                        if row_type == 'pekerjaan' and pek_id:
                            for wk in range(1, total_project_weeks + 1):
                                key = f"{pek_id}-{wk}"
                                planned_val = planned_map_str.get(key, 0)
                                actual_val = actual_map_str.get(key, 0)
                                week_planned.append(str(planned_val) if planned_val else '')
                                week_actual.append(str(actual_val) if actual_val else '')
                        
                        # Use correct field names from base_rows
                        hierarchy_rows.append({
                            'type': row_type,
                            'name': row.get('uraian', ''),
                            'volume': row.get('volume_display', '') if row_type == 'pekerjaan' else '',
                            'satuan': row.get('unit', '') if row_type == 'pekerjaan' else '',
                            'level': level,
                            'week_planned': week_planned,
                            'week_actual': week_actual
                        })
                    
                    # Use monthly-specific Kurva S table (returns List[Drawing] for pagination)
                    # Table: ALL weeks, Chart: only cumulative on first page
                    if hierarchy_rows:
                        monthly_kurva_pages = self._build_monthly_kurva_s_table(
                            hierarchy_rows,
                            kurva_s_data,
                            all_weekly_columns,
                            total_project_weeks=total_project_weeks,
                            cumulative_end_week=cumulative_end_week,
                            row_height=22,  # Increased for 2-line text support
                            project_info=project_info  # For signature section on last page
                        )
                        # Add each page with page breaks between them
                        for page_idx, kurva_drawing in enumerate(monthly_kurva_pages):
                            if kurva_drawing:
                                story.append(kurva_drawing)
                                if page_idx < len(monthly_kurva_pages) - 1:
                                    story.append(PageBreak())  # Page break between pages
                        story.append(Spacer(1, 10*mm))
                    
                    # === Portrait Kurva S Page (monthly segment table + chart) ===
                    # Switch to PORTRAIT A3 for table-focused view (750pt width)
                    story.append(NextPageTemplate('portrait_a3'))
                    story.append(PageBreak())
                    
                    # Start Kurva S Portrait segment
                    story.append(SegmentMarker(f"Kurva S Bulanan Bulan ke-{month}"))
                    
                    # Title for portrait page
                    portrait_title = ParagraphStyle(
                        'PortraitSectionHeader',
                        fontSize=14,
                        textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                        fontName='Helvetica-Bold',
                        spaceAfter=5*mm,
                    )
                    story.append(Paragraph(
                        f"<b>GRAFIK KURVA S (Tampilan Bulanan)</b>", 
                        portrait_title
                    ))
                    story.append(Spacer(1, 5*mm))
                    
                    # Build portrait chart as monthly segment table + chart overlay
                    # Use hierarchy_data from 'hierarchy_progress' (same as Rincian Progress)
                    # Returns List[Drawing] with pagination
                    hierarchy_data = data.get('hierarchy_progress', [])
                    
                    # Get weekly progress data - prefer adapter format (flat key: pek_id-week)
                    # Fallback to gantt_data format (nested: {pek_id: {week: val}})
                    planned_progress = data.get('planned_map', {})
                    actual_progress = data.get('actual_map', {})
                    
                    # Fallback to gantt_data if adapter maps are empty
                    if not planned_progress:
                        gantt_data = data.get('gantt_data', {})
                        planned_progress = gantt_data.get('planned', {})
                        actual_progress = gantt_data.get('actual', {})
                    
                    portrait_charts = self._build_portrait_kurva_s_chart(
                        kurva_s_data,
                        cumulative_end_week=cumulative_end_week,
                        hierarchy_rows=hierarchy_data,  # Use same data as Rincian Progress
                        summary=data.get('executive_summary', {}),
                        month=month,
                        project_info=project_info,
                        planned_progress=planned_progress,
                        actual_progress=actual_progress
                    )
                    if portrait_charts:
                        for p_idx, p_chart in enumerate(portrait_charts):
                            if p_chart:
                                story.append(p_chart)
                                if p_idx < len(portrait_charts) - 1:
                                    story.append(PageBreak())
                        story.append(Spacer(1, 10*mm))
                    
                    # Signature is now embedded in portrait chart, no separate page needed
                
                story.append(PageBreak())

        
        # 6. Grid Pages (for rekap - Planned section - NO chart here, chart in RINGKASAN)
        if report_type == 'rekap':
            planned_pages = data.get('planned_pages', [])
            
            for idx, page in enumerate(planned_pages):
                # Section header for first page
                if idx == 0:
                    section_title = ParagraphStyle(
                        'SectionHeader',
                        fontSize=16,
                        textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                        fontName='Helvetica-Bold',
                        spaceAfter=5*mm,
                    )
                    story.append(Paragraph("<b>BAGIAN 1: GRID VIEW - RENCANA (PLANNED)</b>", section_title))
                    story.append(Spacer(1, 5*mm))
                
                # Page title (simple, no project identity - that's on cover page)
                page_title_style = ParagraphStyle(
                    'GridPageTitle',
                    fontSize=SHF.FONT_SIZE,
                    fontName=SHF.FONT_NAME,
                    textColor=colors.HexColor(SHF.FONT_COLOR),
                    spaceAfter=3*mm,
                )
                story.append(Paragraph(page.get('title', 'Input Progress Planned'), page_title_style))
                story.append(Spacer(1, 3*mm))
                
                # Build table
                table = self._build_table(page)
                story.append(table)
                story.append(PageBreak())
            
            # Actual section
            actual_pages = data.get('actual_pages', [])
            for idx, page in enumerate(actual_pages):
                if idx == 0:
                    section_title = ParagraphStyle(
                        'SectionHeader',
                        fontSize=16,
                        textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                        fontName='Helvetica-Bold',
                        spaceAfter=5*mm,
                    )
                    story.append(Paragraph("<b>BAGIAN 2: GRID VIEW - REALISASI (ACTUAL)</b>", section_title))
                    story.append(Spacer(1, 5*mm))
                
                # Page title (simple, no project identity)
                page_title_style = ParagraphStyle(
                    'GridPageTitle',
                    fontSize=SHF.FONT_SIZE,
                    fontName=SHF.FONT_NAME,
                    textColor=colors.HexColor(SHF.FONT_COLOR),
                    spaceAfter=3*mm,
                )
                story.append(Paragraph(page.get('title', 'Input Progress Actual'), page_title_style))
                story.append(Spacer(1, 3*mm))
                
                table = self._build_table(page)
                story.append(table)
                story.append(PageBreak())
            
            # RINGKASAN PROGRESS KURVA S - with paginated Kurva S overlay
            kurva_s_data = data.get('kurva_s_data', [])
            summary = data.get('summary', {})
            planned_pages = data.get('planned_pages', [])
            
            if kurva_s_data:
                section_title = ParagraphStyle(
                    'SectionHeader',
                    fontSize=14,
                    textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                    fontName='Helvetica-Bold',
                    spaceAfter=5*mm,
                )
                story.append(Paragraph("<b>GRAFIK KURVA S</b>", section_title))
                story.append(Spacer(1, 5*mm))
                
                # Extract pekerjaan rows from planned_pages and actual_pages data
                # Row format from adapter: [kode, uraian, volume, satuan, week1_progress, week2_progress, ...]
                pekerjaan_rows = []
                hierarchy_levels = {}
                
                # Get rows from both planned and actual pages
                planned_rows = []
                actual_rows = []
                
                if planned_pages:
                    first_page = planned_pages[0]
                    table_data = first_page.get('table_data', {})
                    planned_rows = table_data.get('rows', [])
                    hierarchy_levels = first_page.get('hierarchy_levels', {})
                
                if actual_pages:
                    first_actual = actual_pages[0]
                    actual_table = first_actual.get('table_data', {})
                    actual_rows = actual_table.get('rows', [])
                
                for idx, row in enumerate(planned_rows):
                    # Extract data from correct column indices
                    # UNIFIED STRUCTURE (no Kode):
                    # Col 0 = Uraian Pekerjaan
                    # Col 1 = Volume
                    # Col 2 = Satuan
                    # Col 3+ = Week progress values
                    uraian = str(row[0]) if len(row) > 0 else ''
                    volume = str(row[1]) if len(row) > 1 else ''
                    satuan = str(row[2]) if len(row) > 2 else ''
                    level = hierarchy_levels.get(idx, 2)
                    
                    # Extract week progress values (from col 3 onwards)
                    week_planned = [str(row[i]) if i < len(row) else '' for i in range(3, len(row))]
                    
                    # Get actual values from actual_rows if available
                    actual_row = actual_rows[idx] if idx < len(actual_rows) else []
                    week_actual = [str(actual_row[i]) if i < len(actual_row) else '' for i in range(3, len(actual_row))]
                    
                    pekerjaan_rows.append({
                        'name': uraian,
                        'volume': volume,
                        'satuan': satuan,
                        'level': level if level > 0 else 2,
                        'week_planned': week_planned,
                        'week_actual': week_actual
                    })
                
                # Use paginated Kurva S if we have data
                if pekerjaan_rows:
                    kurva_pages = self._build_kurva_s_paginated(
                        pekerjaan_rows,
                        kurva_s_data,
                        total_weeks=len(kurva_s_data),
                        max_rows_per_page=25
                    )
                    
                    for idx, page_drawing in enumerate(kurva_pages):
                        story.append(page_drawing)
                        # Add page break after each table (1 table per page)
                        if idx < len(kurva_pages) - 1:
                            story.append(PageBreak())
                        else:
                            story.append(Spacer(1, 10*mm))
                else:
                    # Fallback to basic grid if no pekerjaan data
                    integrated_overlay = self._build_integrated_kurva_s_grid(
                        kurva_s_data, 
                        width=doc.width, 
                        max_weeks=20
                    )
                    if integrated_overlay:
                        story.append(integrated_overlay)
                        story.append(Spacer(1, 10*mm))
                
                # Summary stats table
                if summary:
                    summary_rows_data = [
                        ['Keterangan', 'Nilai'],
                        ['Total Progress Rencana', f"{summary.get('total_planned', 0):.2f}%"],
                        ['Total Progress Realisasi', f"{summary.get('total_actual', 0):.2f}%"],
                        ['Deviasi', f"{summary.get('deviation', 0):+.2f}%"],
                    ]
                    summary_table = Table(summary_rows_data, colWidths=[150, 100])
                    summary_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(UTS.SECTION_HEADER_BG)),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    story.append(summary_table)
                story.append(PageBreak())
        
        # 7. Gantt Chart (BAGIAN 3)
        if report_type == 'rekap':
            # Get data needed for Gantt
            pekerjaan_rows = []
            time_columns = []
            planned_progress = {}
            actual_progress = {}
            
            # Try to get structured data from payload
            # This data should be sent from frontend via API
            gantt_data = data.get('gantt_data', {})
            if gantt_data:
                pekerjaan_rows = gantt_data.get('rows', [])
                time_columns = gantt_data.get('time_columns', [])
                planned_progress = gantt_data.get('planned', {})
                actual_progress = gantt_data.get('actual', {})
            
            # FALLBACK: If pekerjaan_rows is empty or lacks volume/unit data,
            # extract from planned_pages which comes from adapter with proper data
            if not pekerjaan_rows or (pekerjaan_rows and not pekerjaan_rows[0].get('volume_display')):
                planned_pages = data.get('planned_pages', [])
                if planned_pages:
                    # Get unique rows from first planned page's table_data rows
                    first_page = planned_pages[0]
                    # Build pekerjaan_rows from base row info (before materialized)
                    # Use hierarchy from page
                    hierarchy = first_page.get('hierarchy_levels', {})
                    
                    # Try to get base_rows from data or build volume/satuan lookup
                    volume_satuan_map = {}
                    for page in planned_pages:
                        table_rows = page.get('table_data', {}).get('rows', [])
                        hier = page.get('hierarchy_levels', {})
                        
                        for idx, row in enumerate(table_rows):
                            if isinstance(row, (list, tuple)) and len(row) >= 3:
                                # Row format: [uraian, volume, satuan, week1, week2, ...]
                                row_key = str(row[0])[:50]  # Use truncated uraian as key
                                level = hier.get(idx, 3)
                                volume_satuan_map[row_key] = {
                                    'volume_display': row[1] if len(row) > 1 else '',
                                    'unit': row[2] if len(row) > 2 else '',
                                    'level': level,
                                    'type': 'pekerjaan' if level >= 3 else ('klasifikasi' if level == 1 else 'sub_klasifikasi'),
                                }
                    
                    # Merge volume/satuan into gantt_data rows if they exist
                    if pekerjaan_rows and volume_satuan_map:
                        for row in pekerjaan_rows:
                            name = row.get('name', row.get('uraian', ''))[:50]
                            if name in volume_satuan_map:
                                row['volume_display'] = volume_satuan_map[name]['volume_display']
                                row['unit'] = volume_satuan_map[name]['unit']
            
            # Ensure time_columns have proper keys for WHF.format_html
            # time_columns from frontend may use different keys - normalize them
            if time_columns:
                for idx, tc in enumerate(time_columns):
                    # Ensure week_number key exists (adapter uses 'week_number', frontend might use 'week')
                    if 'week_number' not in tc and 'week' in tc:
                        tc['week_number'] = tc['week']
                    if 'week_number' not in tc:
                        tc['week_number'] = idx + 1
                    
                    # Ensure we have a 'range' key for date display
                    if 'range' not in tc and 'start_date' in tc and 'end_date' in tc:
                        start = tc.get('start_date')
                        end = tc.get('end_date')
                        if start and end and hasattr(start, 'strftime'):
                            tc['range'] = f"{start.strftime('%d/%m')}-{end.strftime('%d/%m')}"
            
            # FALLBACK: Use weekly_columns from adapter if time_columns lacks date info
            weekly_columns_from_adapter = data.get('weekly_columns', [])
            if weekly_columns_from_adapter and (not time_columns or not time_columns[0].get('range')):
                # Use adapter's weekly_columns which have proper date info
                time_columns = weekly_columns_from_adapter
            
            # If no time_columns at all, build basic ones from meta
            if not time_columns:
                meta = data.get('meta', {})
                total_weeks = meta.get('total_weeks', 0)
                if total_weeks > 0:
                    time_columns = [{'week_number': i+1, 'week': i+1, 'label': f'W{i+1}', 'range': ''} for i in range(total_weeks)]
            
            # Build backend Gantt if we have data
            if pekerjaan_rows and time_columns:
                section_title = ParagraphStyle(
                    'SectionHeader',
                    fontSize=16,
                    textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                    fontName='Helvetica-Bold',
                    spaceAfter=5*mm,
                )
                story.append(Paragraph("<b>BAGIAN 4: GANTT CHART</b>", section_title))
                story.append(Spacer(1, 5*mm))
                
                gantt_elements = self._build_gantt_chart(
                    pekerjaan_rows, time_columns, 
                    planned_progress, actual_progress,
                    width=doc.width
                )
                story.extend(gantt_elements)
                story.append(PageBreak())
        
        # 8. Fallback: Attachments (Frontend rendered images) - only if backend Gantt not available
        attachments = data.get('attachments') or []
        gantt_section_added = 'gantt_data' in data and data.get('gantt_data', {}).get('rows')
        
        for att in attachments:
            img_bytes = att.get('bytes')
            if not img_bytes:
                continue
            att_title = att.get('title') or 'Lampiran'
            
            # Skip Gantt attachments if we already added backend Gantt
            if gantt_section_added and 'gantt' in att_title.lower():
                continue
            
            # Skip Kurva S attachments since we use backend chart now
            if 'kurva' in att_title.lower():
                continue
            
            if report_type == 'rekap' and 'gantt' in att_title.lower() and not gantt_section_added:
                section_title = ParagraphStyle(
                    'SectionHeader',
                    fontSize=16,
                    textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
                    fontName='Helvetica-Bold',
                    spaceAfter=5*mm,
                )
                story.append(Paragraph("<b>BAGIAN 4: GANTT CHART</b>", section_title))
                story.append(Spacer(1, 5*mm))
                gantt_section_added = True
            
            story.append(Paragraph(f"<b>{att_title}</b>", self.styles['title']))
            try:
                img = Image(BytesIO(img_bytes))
                max_w = doc.width
                max_h = doc.height * 0.7
                iw, ih = img.wrap(0, 0)
                scale = min(max_w / max(iw, 1), max_h / max(ih, 1), 1.0)
                img.drawWidth = iw * scale
                img.drawHeight = ih * scale
                story.append(Spacer(1, 4*mm))
                story.append(img)
            except Exception:
                continue
            story.append(PageBreak())
        
        # 8. Signature Section - REMOVED for monthly reports per user request
        # This used config-based labels instead of the correct 3-column layout
        # The correct signature is in _build_progress_signature_section() (Pelaksana, Pengawas, Pemilik)
        # if self.config.signature_config.enabled:
        #     sig_elements = self._build_signatures()
        #     story.extend(sig_elements)
        
        # Build PDF with NumberedCanvas for headers/footers
        project_name = project_info.get('nama', self.config.project_name) or ''
        section_title = 'Jadwal Pekerjaan'
        doc.build(story, canvasmaker=make_numbered_canvas(project_name, section_title))
        
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Generate filename based on report type and months
        project_name_safe = project_name.replace(' ', '_') if project_name else 'Project'
        date_suffix = self.config.export_date.strftime('%Y%m%d')
        
        if report_type == 'monthly':
            months = data.get('months', [])
            if months and len(months) > 1:
                # Multi-month: Laporan Bulan {min}-{max} NamaProject.pdf
                min_m, max_m = min(months), max(months)
                filename = f"Laporan_Bulan_{min_m}-{max_m}_{project_name_safe}_{date_suffix}.pdf"
            else:
                # Single month
                month = data.get('month', 1)
                if months:
                    month = months[0]
                filename = f"Laporan_Bulan_{month}_{project_name_safe}_{date_suffix}.pdf"
        elif report_type == 'weekly':
            week = data.get('week', 1)
            filename = f"Laporan_Minggu_{week}_{project_name_safe}_{date_suffix}.pdf"
        else:
            filename = f"Laporan_Rekap_{project_name_safe}_{date_suffix}.pdf"
        
        return self._create_response(pdf_content, filename, 'application/pdf')
    
    
    def _build_header(self, title_override: str = None) -> List:
        """Build document header"""
        elements = []
        
        # Title
        the_title = title_override or self.config.title
        title = Paragraph(f"<b>{the_title}</b>", self.styles['title'])
        elements.append(title)
        
        # Project info (aligned with page identity) built from single helper
        from ..export_config import build_identity_rows
        info_data = build_identity_rows(self.config)
        
        info_table = Table(info_data, colWidths=[40*mm, 5*mm, 120*mm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), self.config.font_size_normal),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            # Tighter spacing between identity rows
            ('TOPPADDING', (0, 0), (-1, -1), 0.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5*mm),
        ]))
        
        elements.append(info_table)
        
        return elements
    
    def _build_table(self, data: Dict[str, Any]) -> Table:
        """Build main data table with hierarchy styling"""
        table_data = data.get('table_data', {})
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        col_widths = [w * mm for w in data.get('col_widths', [])]
        hierarchy = data.get('hierarchy_levels', {})

        # Convert text to Paragraphs for wrapping
        def P(text, bold=False, align='LEFT'):
            styles = getSampleStyleSheet()
            st = ParagraphStyle(
                'Cell', parent=styles['Normal'],
                fontSize=self.config.font_size_normal,
                alignment={'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}.get(align, 0)
            )
            if bold:
                st.fontName = 'Helvetica-Bold'
            return Paragraph(str(text or ''), st)

        # Helper to check if value is effectively 0% (handles comma decimal)
        def is_zero_percent(val):
            if not val:
                return False
            val_str = str(val).strip()
            if '%' not in val_str:
                return False
            val_clean = val_str.replace('%', '').replace(',', '.').strip()
            try:
                return float(val_clean) == 0
            except:
                return False

        wrapped_rows = []
        for r in rows:
            if not isinstance(r, (list, tuple)):
                r = [r]
            wrapped = []
            for idx, cell in enumerate(r):
                # Replace 0% with "-" for cleaner display
                cell_value = str(cell) if cell else ''
                if is_zero_percent(cell_value):
                    cell_value = '-'
                
                if idx == 0:
                    wrapped.append(P(cell_value, bold=False, align='LEFT'))
                else:
                    wrapped.append(P(cell_value, bold=False, align='RIGHT' if idx >= len(r) - 3 else 'LEFT'))
            wrapped_rows.append(wrapped)
        # Process headers - create 2-line format for week headers
        import re
        def create_header_cell(header_text, is_week=False):
            """Create header cell, with 2-line format for week columns"""
            styles = getSampleStyleSheet()
            
            if is_week:
                # Parse week header like "Week 1 (01/01 - 07/01)" or "W1 (01/01-07/01)"
                # Match both "Week X" and "WX" formats
                match = re.match(r'(Week\s*\d+|W\d+)\s*\(?([^)]*)\)?', str(header_text), re.IGNORECASE)
                if match:
                    week_full = match.group(1)  # "Week 1" or "W1"
                    date_range = match.group(2).strip() if match.group(2) else ''
                    
                    # Convert "Week 1" to "W1" for compact display
                    week_num = re.search(r'\d+', week_full)
                    week_label = f"W{week_num.group()}" if week_num else week_full
                    
                    # Create 2-line header: WX on top, date range below
                    if date_range:
                        # Use non-breaking space to prevent word wrap
                        # Keep regular hyphen (&#8209; not supported by Helvetica)
                        date_range_nowrap = date_range.replace(' ', '&nbsp;')
                        header_text = f'{week_label}<br/><font size="4">{date_range_nowrap}</font>'
                    else:
                        header_text = week_label
                
                st = ParagraphStyle(
                    'WeekHeader', parent=styles['Normal'],
                    fontSize=5,
                    fontName='Helvetica-Bold',
                    alignment=1,  # CENTER
                    textColor=colors.white,
                    leading=7,  # Line spacing for 2-line
                    wordWrap='CJK',  # Prevent word wrapping
                    splitLongWords=0,  # Don't split words
                )
            else:
                st = ParagraphStyle(
                    'Header', parent=styles['Normal'],
                    fontSize=7,
                    fontName='Helvetica-Bold',
                    alignment=1,  # CENTER
                    textColor=colors.white,
                )
            return Paragraph(str(header_text or ''), st)
        
        # Identify which headers are week columns (start after static columns)
        # UNIFIED: 3 static columns (Uraian, Volume, Satuan) - NO Kode
        static_cols = 3  # Uraian, Volume, Satuan
        header_cells = []
        for idx, h in enumerate(headers):
            is_week = idx >= static_cols
            header_cells.append(create_header_cell(h, is_week))
        
        # =============================================
        # FIXED TABLE WIDTH CALCULATION
        # All column widths are FIXED pt values
        # Table width = 100% of usable page width
        # =============================================
        
        # Get page dimensions from config
        # =============================================
        # UNIFIED LAYOUT using TableLayoutCalculator
        # =============================================
        layout_calc = TLC(self.config)
        actual_weeks = len(headers) - static_cols if len(headers) > static_cols else 0
        layout = layout_calc.calculate(actual_weeks)
        
        # Extract layout values
        TABLE_WIDTH_PT = layout['table_width']
        fixed_col_widths = layout['column_widths']
        weeks_to_render = layout['weeks_to_render']
        blank_cols = layout['blank_cols']
        MAX_WEEKS_PER_PAGE = layout['max_weeks_per_page']
        
        # ==================================================
        # TRUNCATE DATA TO MATCH weeks_to_render
        # ==================================================
        total_cols_to_keep = static_cols + weeks_to_render
        header_cells = header_cells[:total_cols_to_keep]
        wrapped_rows = [row[:total_cols_to_keep] for row in wrapped_rows]
        
        # ==================================================
        # ADD BLANK CELLS TO FILL TO MAX_WEEKS_PER_PAGE
        # ==================================================
        blank_cell_style = ParagraphStyle(
            'BlankCell', parent=getSampleStyleSheet()['Normal'],
            fontSize=5,
            alignment=1,
        )
        for _ in range(blank_cols):
            header_cells.append(Paragraph('', blank_cell_style))
        for row in wrapped_rows:
            for _ in range(blank_cols):
                row.append(Paragraph('', blank_cell_style))
        
        # Rebuild full_data
        full_data = [header_cells] + wrapped_rows
        
        # Create table with FIXED column widths
        table = Table(full_data, colWidths=fixed_col_widths, repeatRows=1)
        
        # Professional color palette (matching Kurva S)
        header_bg = colors.HexColor('#1a365d')  # Deep professional blue
        header_text = UTS.get_header_text_color()
        klasifikasi_bg = UTS.get_klasifikasi_bg_color()
        sub_klasifikasi_bg = UTS.get_sub_klasifikasi_bg_color()
        border_color = UTS.get_inner_border_color()
        outer_border = UTS.get_outer_border_color()
        
        # Font sizes from UTS
        font_header = UTS.HEADER_FONT_SIZE
        font_data = UTS.DATA_FONT_SIZE
        
        # Padding from UTS
        pad_top, pad_bottom, pad_left, pad_right = UTS.get_padding_tuple_mm()
        
        # Build style commands
        style_commands = [
            # Header row - professional deep blue
            ('BACKGROUND', (0, 0), (-1, 0), header_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), header_text),
            ('FONTSIZE', (0, 0), (-1, 0), font_header),
            ('FONTNAME', (0, 0), (-1, 0), UTS.HEADER_FONT_NAME),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Default data rows
            ('FONTSIZE', (0, 1), (-1, -1), font_data),
            ('FONTNAME', (0, 1), (-1, -1), UTS.DATA_FONT_NAME),
            
            # Borders from UTS
            ('GRID', (0, 0), (-1, -1), UTS.INNER_BORDER_WIDTH, border_color),
            ('BOX', (0, 0), (-1, -1), UTS.OUTER_BORDER_WIDTH, outer_border),
            
            # Padding from UTS
            ('TOPPADDING', (0, 0), (-1, -1), pad_top),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad_bottom),
            ('LEFTPADDING', (0, 0), (-1, -1), pad_left),
            ('RIGHTPADDING', (0, 0), (-1, -1), pad_right),
        ]
        
        # Apply hierarchy styling using HierarchyStyler
        hierarchy_commands = HS.get_style_commands(hierarchy, header_offset=1)
        style_commands.extend(hierarchy_commands)
        
        table.setStyle(TableStyle(style_commands))
        
        return table
    
    def _build_footer_table(self, footer_rows: List) -> Table:
        """Build footer table for totals"""
        # Right-align footer table
        table = Table(footer_rows, colWidths=[120*mm, 60*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), self.config.font_size_normal),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor(UTS.PRIMARY_LIGHT)),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor(UTS.PRIMARY_LIGHT)),
        ]))

        return table

    def _get_page_width_mm(self) -> float:
        width_mm, height_mm = get_page_size_mm(getattr(self.config, 'page_size', 'A4'))
        return width_mm if getattr(self.config, 'page_orientation', 'landscape') == 'portrait' else height_mm

    def _build_truncation_notice(self, shown: int, total: int, unit: str = 'minggu') -> Paragraph:
        """
        Build a styled truncation notice when data exceeds display limit.
        
        Args:
            shown: Number of items actually displayed
            total: Total number of items available
            unit: Unit name (e.g., 'minggu', 'kolom', 'baris')
            
        Returns:
            Styled Paragraph with warning notice
        """
        if shown >= total:
            return None
            
        notice_style = ParagraphStyle(
            'TruncationNotice',
            fontSize=8,
            textColor=colors.HexColor(UTS.STATUS_BEHIND),
            fontName='Helvetica-Oblique',
            spaceAfter=3*mm,
            spaceBefore=2*mm,
        )
        
        hidden = total - shown
        notice_text = f"⚠ Menampilkan {shown} dari {total} {unit}. {hidden} {unit} berikutnya ditampilkan di halaman lanjutan."
        
        logger.info(f"Truncation notice: displaying {shown}/{total} {unit}")
        return Paragraph(notice_text, notice_style)

    def _build_pekerjaan_section(self, section: Dict[str, Any], story: List) -> None:
        """
        Build a pekerjaan section for Rincian AHSP export.
        Structure mimics the .rk-right .ra-editor on the web page:
        - Pekerjaan header (metadata + title)
        - Detail items table
        """
        pekerjaan = section.get('pekerjaan', {})
        detail_table = section.get('detail_table', {})

        # Helper for paragraphs
        def P(text, style_name='Normal', bold=False):
            styles = getSampleStyleSheet()
            st = ParagraphStyle(
                'Custom', parent=styles[style_name],
                fontSize=self.config.font_size_normal
            )
            if bold:
                st.fontName = 'Helvetica-Bold'
            return Paragraph(str(text or ''), st)

        # Pekerjaan Header Section (similar to .rk-right-header)
        # Metadata line: Kode • Satuan
        meta_text = f"<font color='#666'>{pekerjaan.get('kode', '-')} · {pekerjaan.get('satuan', '-')}</font>"
        meta_para = Paragraph(meta_text, self.styles['normal'])
        story.append(meta_para)
        story.append(Spacer(1, 1*mm))

        # Uraian (main title)
        uraian_text = f"<b>{pekerjaan.get('uraian', 'Pekerjaan')}</b>"
        uraian_para = Paragraph(uraian_text, self.styles['subtitle'])
        story.append(uraian_para)
        story.append(Spacer(1, 1*mm))

        # Replace two-line header (kode+satuan, then uraian) with single-line: "<kode> <uraian>"
        try:
            # Remove: spacer, uraian_para, spacer, meta_para (in reverse order)
            story.pop(); story.pop(); story.pop(); story.pop()
        except Exception:
            pass
        combined_header = Paragraph(
            f"<b>{pekerjaan.get('kode', '-')} {pekerjaan.get('uraian', 'Pekerjaan')}</b>",
            self.styles['subtitle']
        )
        story.append(combined_header)
        story.append(Spacer(1, 1*mm))
        # Optional secondary line for satuan
        story.append(Paragraph(
            f"<font color='#666'>Satuan: {pekerjaan.get('satuan', '-')}</font>",
            self.styles['normal']
        ))
        story.append(Spacer(1, 1*mm))

        # Total
        total_text = f"<font color='{UTS.PRIMARY_LIGHT}'><b>Total: Rp {pekerjaan.get('total', '0')}</b></font>"
        total_para = Paragraph(total_text, self.styles['normal'])
        story.append(total_para)
        story.append(Spacer(1, 3*mm))

        # Detail Table
        if section.get('has_details'):
            headers = detail_table.get('headers', [])
            widths_mm = list(detail_table.get('col_widths', []) or [])
            # Scale column widths to fit page orientation/margins
            try:
                page_w_mm = self._get_page_width_mm()
                usable_w = page_w_mm - (self.config.margin_left + self.config.margin_right)
                current = sum(widths_mm) if widths_mm else 0
                if current and abs(current - usable_w) > 0.5:
                    factor = usable_w / current
                    widths_mm = [w * factor for w in widths_mm]
            except Exception:
                pass
            col_widths = [w * mm for w in widths_mm] if widths_mm else None
            ncols = len(headers)

            # Wrap cells in Paragraphs
            def wrap_cell(text, align='LEFT', bold=False):
                styles = getSampleStyleSheet()
                st = ParagraphStyle(
                    'Cell', parent=styles['Normal'],
                    fontSize=self.config.font_size_normal,
                    alignment={'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}.get(align, 0)
                )
                if bold:
                    st.fontName = 'Helvetica-Bold'
                return Paragraph(str(text or ''), st)

            # Header row
            header_cells = [wrap_cell(h, align='CENTER', bold=True) for h in headers]

            full_data = [header_cells]
            style_commands = [
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(UTS.PRIMARY_LIGHT)),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), self.config.font_size_header),
                ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor(UTS.PRIMARY_LIGHT)),

                # Body defaults
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), self.config.font_size_normal),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
                ('BOX', (0, 0), (-1, -1), 1.5, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                ('LEFTPADDING', (0, 0), (-1, -1), 1.5*mm),
                ('RIGHTPADDING', (0, 0), (-1, -1), 1.5*mm),
            ]

            groups = section.get('groups') or []
            totals = section.get('totals') or {}

            current_row = 1  # account for header

            def add_group(title: str, rows: list, subtotal_text: str):
                nonlocal current_row
                # Group header (spanned)
                full_data.append([wrap_cell(title, bold=True)] + [''] * (ncols - 1))
                style_commands.extend([
                    ('SPAN', (0, current_row), (-1, current_row)),
                    ('BACKGROUND', (0, current_row), (-1, current_row), colors.HexColor('#f5f5f5')),
                    ('FONTNAME', (0, current_row), (-1, current_row), 'Helvetica-Bold'),
                    ('LINEABOVE', (0, current_row), (-1, current_row), 0.8, colors.HexColor(UTS.PRIMARY_LIGHT)),
                    ('LINEBELOW', (0, current_row), (-1, current_row), 0.8, colors.HexColor(UTS.PRIMARY_LIGHT)),
                ])
                current_row += 1

                # Group rows
                for row in rows:
                    wrapped = []
                    for idx, cell in enumerate(row):
                        if idx == 0:
                            wrapped.append(wrap_cell(cell, align='CENTER'))
                        elif idx in [4, 5, 6]:
                            wrapped.append(wrap_cell(cell, align='RIGHT'))
                        elif idx == 3:
                            wrapped.append(wrap_cell(cell, align='CENTER'))
                        else:
                            wrapped.append(wrap_cell(cell, align='LEFT'))
                    full_data.append(wrapped)
                    current_row += 1

                # Subtotal row (label spans ncols-1)
                full_data.append([wrap_cell(f"Subtotal {title.split('—')[1].strip() if '—' in title else title}", bold=True)] + [''] * (ncols - 2) + [wrap_cell(subtotal_text, align='RIGHT', bold=True)])
                style_commands.extend([
                    ('SPAN', (0, current_row), (ncols - 2, current_row)),
                    ('FONTNAME', (0, current_row), (-1, current_row), 'Helvetica-Bold'),
                ])
                current_row += 1

            for g in groups:
                add_group(g.get('title') or '', g.get('rows') or [], g.get('subtotal') or '0')

            # Totals E, F, G
            if totals:
                labels = [
                    (f"E — Jumlah (A+B+C+D)", totals.get('E', '0')),
                    (f"F — Profit/Margin × Jumlah (E) ({totals.get('markup_eff', '0')}%)", totals.get('F', '0')),
                    (f"G — HSP = E + F", totals.get('G', '0')),
                ]
                for idx, (label, value) in enumerate(labels):
                    full_data.append([wrap_cell(label, bold=True)] + [''] * (ncols - 2) + [wrap_cell(value, align='RIGHT', bold=True)])
                    style_commands.extend([
                        ('SPAN', (0, current_row), (ncols - 2, current_row)),
                        ('FONTNAME', (0, current_row), (-1, current_row), 'Helvetica-Bold'),
                    ])
                    # Add thicker line hierarchy: E/G thicker, F medium
                    thickness = 1.2 if idx in (0, 2) else 0.8
                    style_commands.append(('LINEABOVE', (0, current_row), (-1, current_row), thickness, colors.HexColor(UTS.PRIMARY_LIGHT)))
                    current_row += 1

            # Create table
            table = Table(full_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle(style_commands))
            story.append(table)
        else:
            # No details message
            no_detail_para = Paragraph("<i>Tidak ada detail item untuk pekerjaan ini</i>", self.styles['normal'])
            story.append(no_detail_para)

    def _build_signatures(self) -> List:
        """Build signature section"""
        elements = []
        
        # Title
        sig_title = Paragraph(
            "<b>LEMBAR PENGESAHAN</b>",
            self.styles['subtitle']
        )
        elements.append(sig_title)
        elements.append(Spacer(1, 3*mm))
        
        # Get signatures from config
        sigs = self.config.signature_config.signatures
        if self.config.signature_config.custom_signatures:
            sigs = self.config.signature_config.custom_signatures
        
        # Build signature cells
        sig_headers = [sig['label'] for sig in sigs]
        empty_rows = [[''] * len(sigs) for _ in range(3)]  # Space for signature
        name_rows = [['_' * 20] * len(sigs)]
        position_rows = [[sig.get('position', '') for sig in sigs]]
        
        sig_data = [sig_headers] + empty_rows + name_rows + position_rows
        
        # Calculate column width
        col_width = 250 * mm / len(sigs)
        
        sig_table = Table(sig_data, colWidths=[col_width] * len(sigs))
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, 3), 10*mm),  # Space for hand signature
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(sig_table)
        
        # Wrap in KeepTogether so signature section stays together
        return [KeepTogether(elements)]

    def _build_monthly_signature_page(self) -> List:
        """
        Build Lembar Pengesahan for Laporan Bulanan.
        
        Three columns:
        - Pelaksana
        - Pengawas
        - Pemilik Pekerjaan
        """
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'SigTitle',
            fontSize=16,
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=10*mm,
        )
        elements.append(Spacer(1, 20*mm))
        elements.append(Paragraph("<b>LEMBAR PENGESAHAN</b>", title_style))
        elements.append(Spacer(1, 15*mm))
        
        # Signature roles
        roles = [
            {'label': 'PELAKSANA', 'position': 'Pelaksana Pekerjaan'},
            {'label': 'PENGAWAS', 'position': 'Pengawas Lapangan'},
            {'label': 'PEMILIK PEKERJAAN', 'position': 'Pemilik/Owner'},
        ]
        
        # Build signature table data
        # Row 1: Labels
        labels_row = [role['label'] for role in roles]
        
        # Row 2-4: Empty space for signature
        empty_rows = [[''] * 3 for _ in range(3)]
        
        # Row 5: Signature line
        line_row = ['_' * 25] * 3
        
        # Row 6: "Nama:" label
        name_label_row = ['Nama:'] * 3
        
        # Row 7: Name placeholder
        name_row = ['_' * 25] * 3
        
        # Row 8: "Tanggal:" label
        date_label_row = ['Tanggal:'] * 3
        
        # Row 9: Date placeholder
        date_row = ['_' * 15] * 3
        
        sig_data = [labels_row] + empty_rows + [line_row, name_label_row, name_row, date_label_row, date_row]
        
        col_width = 80 * mm
        sig_table = Table(sig_data, colWidths=[col_width] * 3)
        sig_table.setStyle(TableStyle([
            # Header row styling
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(UTS.PRIMARY_LIGHT)),
            
            # Other rows
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor(UTS.TEXT_SECONDARY)),
            
            # Spacing for signature area
            ('TOPPADDING', (0, 1), (-1, 3), 8*mm),
            ('BOTTOMPADDING', (0, 3), (-1, 3), 5*mm),
            
            # Normal padding for other rows
            ('TOPPADDING', (0, 4), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 4), (-1, -1), 2*mm),
            
            # Vertical alignment
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Border only for signature boxes
            ('BOX', (0, 0), (0, 4), 0.5, colors.HexColor(UTS.INNER_BORDER)),
            ('BOX', (1, 0), (1, 4), 0.5, colors.HexColor(UTS.INNER_BORDER)),
            ('BOX', (2, 0), (2, 4), 0.5, colors.HexColor(UTS.INNER_BORDER)),
        ]))
        
        elements.append(sig_table)
        
        # Wrap in KeepTogether to ensure signature section stays on same page
        return [KeepTogether(elements)]

    # ------------------------------------------------------------------
    # Professional Report Methods (Laporan Tertulis)
    # ------------------------------------------------------------------

    def _build_cover_page(self, report_type: str, project_info: Dict[str, Any], period_info: Dict[str, Any] = None) -> List:
        """
        Build professional cover page for report.
        
        Design principles:
        - Border spans entire page margins (edge to edge)
        - Title: "LAPORAN BULAN ke-X" (no JADWAL PEKERJAAN)
        - Logo box with 40% opacity
        - No header/footer on cover
        
        Args:
            report_type: 'rekap', 'monthly', or 'weekly'
            project_info: Project information dict
            period_info: Period information for monthly/weekly reports
        """
        elements = []
        
        # Frame content (will be wrapped in border)
        frame_content = []
        
        # ==============================================
        # LOGO PLACEHOLDER (40% opacity / muted)
        # Empty box - no text, just placeholder for logo image
        # ==============================================
        logo_border_color = colors.Color(0.3, 0.4, 0.6, alpha=0.4)  # 40% opacity
        logo_bg_color = colors.Color(0.95, 0.96, 0.98, alpha=0.4)   # 40% opacity
        
        # Empty string instead of "LOGO" text
        logo_table = Table([['']], colWidths=[40*mm], rowHeights=[25*mm])
        logo_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, logo_border_color),
            ('BACKGROUND', (0, 0), (-1, -1), logo_bg_color),
        ]))
        frame_content.append(Spacer(1, 25*mm))
        frame_content.append(logo_table)
        frame_content.append(Spacer(1, 25*mm))
        
        # ==============================================
        # MAIN TITLE - Dynamic based on report type
        # "LAPORAN BULAN ke-X" or "LAPORAN MINGGU ke-X" or "LAPORAN REKAPITULASI"
        # ==============================================
        title_text = "LAPORAN"
        if report_type == 'monthly':
            month_num = period_info.get('month', 1) if period_info else 1
            title_text = f"LAPORAN BULAN ke-{month_num}"
        elif report_type == 'weekly':
            week_num = period_info.get('week', 1) if period_info else 1
            title_text = f"LAPORAN MINGGU ke-{week_num}"
        elif report_type == 'rekap':
            title_text = "LAPORAN REKAPITULASI"
        
        title_style = ParagraphStyle(
            'CoverTitle',
            fontSize=22,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            alignment=TA_CENTER,
            leading=28,
        )
        frame_content.append(Paragraph(f"<b>{title_text}</b>", title_style))
        frame_content.append(Spacer(1, 10*mm))
        
        # ==============================================
        # DECORATIVE LINE
        # ==============================================
        line_table = Table([['─' * 35]], colWidths=[100*mm])
        line_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(UTS.PRIMARY_LIGHT)),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        frame_content.append(line_table)
        frame_content.append(Spacer(1, 10*mm))
        
        # ==============================================
        # PROJECT NAME
        # ==============================================
        project_name_style = ParagraphStyle(
            'ProjectName',
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a365d'),
            alignment=TA_CENTER,
            leading=20,
        )
        project_name = project_info.get('nama', 'Nama Proyek')
        frame_content.append(Paragraph(f"<b>{project_name}</b>", project_name_style))
        frame_content.append(Spacer(1, 12*mm))
        
        # ==============================================
        # PERIOD INFO (for monthly/weekly) - dates only
        # ==============================================
        if period_info and (period_info.get('start_date') or period_info.get('end_date')):
            period_style = ParagraphStyle(
                'Period',
                fontSize=12,
                fontName='Helvetica',
                textColor=colors.HexColor(UTS.TEXT_SECONDARY),
                alignment=TA_CENTER,
            )
            start = period_info.get('start_date', '')
            end = period_info.get('end_date', '')
            if hasattr(start, 'strftime'):
                start = start.strftime('%d/%m/%Y')  # DD/MM/YYYY format
            if hasattr(end, 'strftime'):
                end = end.strftime('%d/%m/%Y')  # DD/MM/YYYY format
            
            if start and end:
                period_text = f"Periode: {start} - {end}"  # Use dash, not s.d.
            elif start:
                period_text = f"Mulai: {start}"
            else:
                period_text = ""
            
            if period_text:
                frame_content.append(Paragraph(period_text, period_style))
                frame_content.append(Spacer(1, 12*mm))
        
        # ==============================================
        # PROJECT DETAILS TABLE
        # ==============================================
        details = []
        
        if project_info.get('lokasi'):
            details.append(['Lokasi', ':', project_info.get('lokasi')])
        if project_info.get('nama_client'):
            details.append(['Pemilik', ':', project_info.get('nama_client')])
        if project_info.get('sumber_dana'):
            details.append(['Sumber Dana', ':', project_info.get('sumber_dana')])
        
        # Format anggaran with thousand separator
        anggaran = project_info.get('anggaran', 0)
        if anggaran:
            try:
                anggaran_num = float(str(anggaran).replace(',', '').replace('.', ''))
                anggaran_fmt = f"Rp {anggaran_num:,.0f}".replace(',', '.')
            except:
                anggaran_fmt = f"Rp {anggaran}"
            details.append(['Anggaran', ':', anggaran_fmt])
        
        if details:
            details_table = Table(details, colWidths=[40*mm, 5*mm, 100*mm])
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.TEXT_SECONDARY)),
                ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2d3748')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ]))
            frame_content.append(details_table)
        
        # ==============================================
        # FULL-PAGE BORDER FRAME
        # Border at page margin edges (top, bottom, left, right)
        # 
        # CALCULATION:
        # A4 Portrait = 210mm × 297mm
        # Margins: Left=15mm, Right=15mm, Top=20mm, Bottom=20mm
        # Usable width  = 210 - 15 - 15 = 180mm
        # Usable height = 297 - 20 - 20 = 257mm
        # ==============================================
        
        # Inner table for content (with some padding from border)
        inner_table = Table([[elem] for elem in frame_content], colWidths=[160*mm])
        inner_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        # Full-page border - fills entire usable area
        frame_table = Table(
            [[inner_table]], 
            colWidths=[180*mm],    # 210 - 15 - 15 = 180mm
            rowHeights=[257*mm]    # 297 - 20 - 20 = 257mm
        )
        frame_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor(UTS.PRIMARY_LIGHT)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10*mm),
            ('TOPPADDING', (0, 0), (-1, -1), 5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5*mm),
        ]))
        
        elements.append(frame_table)
        
        # NO HEADER/FOOTER ON COVER - This is handled by NumberedCanvas
        # which should skip page 1 for headers/footers
        
        return elements

    def _build_progress_pelaksanaan_page(
        self,
        month: int,
        project_info: Dict[str, Any],
        summary: Dict[str, Any],
        hierarchy_data: List[Dict[str, Any]],
        period_info: Dict[str, Any] = None
    ) -> List:
        """
        Build combined Progress Pelaksanaan Pekerjaan page.
        
        Combines:
        1. Identitas Project Singkat
        2. Ringkasan Progress
        3. Tabel Rincian Progress
        
        Args:
            month: Month number (1-based)
            project_info: Project information dict
            summary: Executive summary data
            hierarchy_data: Hierarchical pekerjaan with harga and progress
            period_info: Period date information
        """
        elements = []
        
        # ==============================================
        # PAGE TITLE (with top margin to avoid header collision)
        # ==============================================
        elements.append(Spacer(1, 10*mm))  # Top clearance from header
        title_style = ParagraphStyle(
            'PageTitle',
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            alignment=TA_CENTER,
            spaceAfter=8*mm,
        )
        elements.append(Paragraph(
            f"<b>PROGRESS PELAKSANAAN PEKERJAAN BULAN KE-{month}</b>",
            title_style
        ))
        elements.append(Spacer(1, 5*mm))
        
        # ==============================================
        # SEGMENTS 1 & 2: SIDE-BY-SIDE LAYOUT
        # Left: IDENTITAS PROJECT | Right: RINGKASAN PROGRESS
        # ==============================================
        section_title_style = ParagraphStyle(
            'SectionTitle',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(UTS.PRIMARY_DARK),
            spaceAfter=2*mm,
        )
        
        # --- LEFT COLUMN: IDENTITAS PROJECT ---
        identity_header = Paragraph("IDENTITAS PROJECT", section_title_style)
        identity_data = [
            ['Nama Project', ':', project_info.get('nama', '-')],
            ['Ket. Project 1', ':', project_info.get('keterangan_1', project_info.get('sumber_dana', '-'))],
            ['Ket. Project 2', ':', project_info.get('keterangan_2', project_info.get('nama_client', '-'))],
            ['Lokasi', ':', project_info.get('lokasi', '-')],
        ]
        identity_table = Table(identity_data, colWidths=[32*mm, 3*mm, 58*mm])
        identity_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.TEXT_SECONDARY)),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor(UTS.TEXT_PRIMARY)),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(UTS.LIGHT_BORDER)),
        ]))
        left_content = [[identity_header], [identity_table]]
        left_cell = Table(left_content, colWidths=[90*mm])
        left_cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        # --- RIGHT COLUMN: RINGKASAN PROGRESS ---
        ringkasan_header = Paragraph("RINGKASAN PROGRESS", section_title_style)
        
        # Deviation color: Green positive, Red negative, Yellow/Amber zero
        deviation = summary.get('deviation_cumulative', 0)
        if deviation > 0:
            deviation_color = '#22c55e'  # Green
        elif deviation < 0:
            deviation_color = '#ef4444'  # Red
        else:
            deviation_color = '#eab308'  # Yellow/Amber
        
        # Format deviation with color
        deviation_para = Paragraph(
            f'<font color="{deviation_color}"><b>{deviation:+.2f}%</b></font>',
            ParagraphStyle('Deviation', fontSize=8, fontName='Helvetica')
        )
        
        ringkasan_data = [
            ['Rencana Bulan Ini', ':', f"{summary.get('target_period', 0):.2f}%"],
            ['Actual Bulan Ini', ':', f"{summary.get('actual_period', 0):.2f}%"],
            ['Akumulasi Rencana', ':', f"{summary.get('cumulative_target', 0):.2f}%"],
            ['Akumulasi Actual', ':', f"{summary.get('cumulative_actual', 0):.2f}%"],
            ['Deviasi', ':', deviation_para],  # Colored deviation
        ]
        
        ringkasan_cells = []
        for row in ringkasan_data:
            ringkasan_cells.append(row)
        # Status row removed - deviation color now indicates status
        
        ringkasan_table = Table(ringkasan_cells, colWidths=[40*mm, 3*mm, 47*mm])
        ringkasan_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.TEXT_SECONDARY)),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 0.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5*mm),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(UTS.LIGHT_BORDER)),
            ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        right_content = [[ringkasan_header], [ringkasan_table]]
        right_cell = Table(right_content, colWidths=[90*mm])
        right_cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        # --- COMBINE INTO 2-COLUMN LAYOUT with center gap ---
        # 90mm + 6mm gap + 90mm = 186mm
        two_column = Table([[left_cell, Spacer(1, 1), right_cell]], colWidths=[90*mm, 6*mm, 90*mm])
        two_column.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(two_column)
        elements.append(Spacer(1, 6*mm))
        
        # ==============================================
        # SEGMENT 3: TABEL RINCIAN PROGRESS
        # ==============================================
        # Start segment tracking for page numbering (X/Y format)
        segment_name = f"Rincian Progress Bulan ke-{month}"
        elements.append(SegmentMarker(segment_name))
        
        elements.append(Paragraph("RINCIAN PROGRESS", section_title_style))
        elements.append(Spacer(1, 2*mm))
        
        # Table headers - 8 columns now
        # URAIAN | VOLUME | HARGA SATUAN | TOTAL HARGA | BOBOT | KUM. LALU | PROGRESS INI | KUM. INI
        headers = [
            'URAIAN PEKERJAAN', 
            'VOLUME', 
            'HARGA\nSATUAN', 
            'TOTAL\nHARGA', 
            'BOBOT\n(%)', 
            'KUMULATIF\nBULAN LALU',
            'PROGRESS\nBULAN INI', 
            'KUMULATIF\nBULAN INI'
        ]
        
        # Smart truncation calculation
        # Column width: 55mm = 155.9pt, Avg char width for Helvetica 7pt ≈ 2.5pt
        # With padding (2mm each side = ~5.7pt each), effective width = 155.9 - 11.4 = 144.5pt
        URAIAN_COL_WIDTH_PT = 144.5  # Effective width after padding
        
        def smart_truncate(text, font_size=7, max_lines=2, indent_level=0):
            """
            Smart truncation based on actual column width and font size.
            
            Args:
                text: Text to truncate
                font_size: Font size in points
                max_lines: Maximum lines allowed (default 2)
                indent_level: Hierarchy level for indent (2 spaces per level)
            """
            if not text:
                return ''
            text = str(text)
            
            # Average char width estimation for Helvetica
            # 7pt ≈ 2.5pt per char, 7.5pt ≈ 2.7pt, 8pt ≈ 2.9pt
            avg_char_width = font_size * 0.38  # Empirical factor for Helvetica
            
            # Calculate chars per line
            chars_per_line = int(URAIAN_COL_WIDTH_PT / avg_char_width)
            
            # Subtract indent (2 chars per level)
            indent_chars = indent_level * 2
            effective_chars_per_line = chars_per_line - indent_chars
            
            # Max chars = chars_per_line * max_lines
            max_chars = effective_chars_per_line * max_lines
            
            if len(text) <= max_chars:
                return text
            
            return text[:max_chars-3].rstrip() + '...'
        
        def P(text, bold=False, align='LEFT', size=7, color=None, max_chars=None, max_lines=None, indent_level=0):
            """Helper to create Paragraph with style."""
            # Smart truncate if max_lines specified
            if max_lines and text:
                text = smart_truncate(str(text), font_size=size, max_lines=max_lines, indent_level=indent_level)
            # Legacy: truncate if max_chars specified
            elif max_chars and text:
                text = str(text)
                if len(text) > max_chars:
                    text = text[:max_chars-3].rstrip() + '...'
            
            al = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}.get(align, TA_LEFT)
            st = ParagraphStyle(
                'Cell', 
                fontSize=size, 
                alignment=al,
                fontName='Helvetica-Bold' if bold else 'Helvetica',
                textColor=colors.HexColor(color) if color else colors.black,
                leading=size + 2,
            )
            return Paragraph(str(text or ''), st)
        
        def PHeader(text):
            """Header paragraph with white color."""
            st = ParagraphStyle(
                'Header', 
                fontSize=7, 
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.white,
                leading=9,
            )
            return Paragraph(str(text or ''), st)
        
        # Build header row with white font
        header_row = [PHeader(h) for h in headers]
        
        # Build data rows from hierarchy
        data_rows = []
        total_harga = 0
        total_bobot = 0
        total_kumulatif_lalu = 0
        total_progress_ini = 0
        total_progress_kumulatif = 0
        
        for item in hierarchy_data:
            level = item.get('level', 0)
            item_type = item.get('type', 'pekerjaan')
            name = item.get('name', item.get('uraian', ''))
            volume = item.get('volume', 0) or 0
            harga_satuan = item.get('harga_satuan', 0) or 0
            harga = item.get('harga', 0) or 0
            bobot = item.get('bobot', 0) or 0
            progress_ini = item.get('progress_bulan_ini', 0) or 0
            progress_lalu = item.get('progress_bulan_lalu', 0) or 0
            # Kumulatif bulan lalu = same as progress_lalu (cumulative up to prev month)
            kumulatif_lalu = progress_lalu
            # Calculate cumulative progress = previous + current month
            progress_kumulatif = progress_lalu + progress_ini
            
            # Indentation for hierarchy
            indent = "  " * level
            display_name = f"{indent}{name}"
            
            # Determine styling based on type
            is_klasifikasi = item_type == 'klasifikasi'
            is_sub_klasifikasi = item_type == 'sub_klasifikasi'
            is_parent = is_klasifikasi or is_sub_klasifikasi
            
            # Font size: Klasifikasi=8, Sub=7.5, Pekerjaan=7
            if is_klasifikasi:
                font_size = 8
                row_bold = True
            elif is_sub_klasifikasi:
                font_size = 7.5
                row_bold = True
            else:
                font_size = 7
                row_bold = False
            
            # Format values - only show for pekerjaan
            if is_parent:
                # Parent rows: only show name, no values
                volume_fmt = ""
                harga_satuan_fmt = ""
                harga_fmt = ""
                bobot_fmt = ""
                progress_ini_fmt = ""
                kumulatif_lalu_fmt = ""
                progress_kumulatif_fmt = ""
            else:
                # Pekerjaan: show all values using helpers
                volume_fmt = f"{volume:,.2f}".replace(',', '.') if volume > 0 else "-"
                harga_satuan_fmt = self._format_rupiah(harga_satuan) if harga_satuan > 0 else "-"
                harga_fmt = self._format_rupiah(harga) if harga > 0 else "-"
                bobot_fmt = self._format_percent(bobot, show_zero=False)
                progress_ini_fmt = self._format_percent(progress_ini)
                kumulatif_lalu_fmt = self._format_percent(kumulatif_lalu)
                progress_kumulatif_fmt = self._format_percent(progress_kumulatif)
            
            row = [
                P(display_name, bold=row_bold, align='LEFT', size=font_size, max_lines=2, indent_level=level),  # Smart truncation
                P(volume_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(harga_satuan_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(harga_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(bobot_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(kumulatif_lalu_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(progress_ini_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(progress_kumulatif_fmt, bold=row_bold, align='CENTER', size=font_size),
            ]
            data_rows.append((row, item_type))
            
            # Accumulate totals (only pekerjaan level)
            if item_type == 'pekerjaan':
                total_harga += harga
                total_bobot += bobot
                total_kumulatif_lalu += kumulatif_lalu
                total_progress_ini += progress_ini
                total_progress_kumulatif += progress_kumulatif
        
        # Fix bobot rounding - if close to 100%, round to exactly 100%
        if 99.9 <= total_bobot <= 100.1:
            total_bobot = 100.0
        
        # Total row - using helpers
        total_row = [
            P("TOTAL", bold=True, align='LEFT', size=7),
            P("", bold=True, align='CENTER', size=7),
            P("", bold=True, align='CENTER', size=7),
            P(self._format_rupiah(total_harga), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_bobot), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_kumulatif_lalu), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_progress_ini), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_progress_kumulatif), bold=True, align='CENTER', size=7),
        ]
        
        # Build full table data
        table_data = [header_row]
        for row, _ in data_rows:
            table_data.append(row)
        table_data.append(total_row)
        
        # Column widths - A4 Portrait usable ~180mm
        # URAIAN(55) | VOL(12) | H.SAT(22) | TOTAL(22) | BOBOT(12) | KUM.LALU(18) | PROG.INI(18) | KUM.INI(18) = 177mm
        col_widths = [55*mm, 12*mm, 22*mm, 22*mm, 12*mm, 18*mm, 18*mm, 18*mm]
        
        # ==========================================
        # TABLE SPLITTING FOR KEEPTOGETHER WITH SIGNATURE
        # ==========================================
        MIN_ROWS_WITH_SIGNATURE = 5
        
        # Common table styling function - using helpers
        def apply_table_style(table, rows_data):
            # Start with base style from helper
            style_cmds = self._get_base_table_style(with_header=True)
            
            # Add table-specific styles
            style_cmds.extend([
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),  # Total row
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEBEFORE', (5, 0), (5, -1), 1.0, colors.HexColor('#888888')),  # Progress section divider
                ('LINEAFTER', (7, 0), (7, -1), 1.0, colors.HexColor('#888888')),
            ])
            
            # Apply row backgrounds using helper
            self._apply_row_backgrounds(style_cmds, rows_data, offset=1)
            table.setStyle(TableStyle(style_cmds))
        
        # Build signature section
        sig_section = self._build_progress_signature_section(project_info)
        sig_inner = sig_section[0]._content if hasattr(sig_section[0], '_content') else sig_section
        
        if len(data_rows) > MIN_ROWS_WITH_SIGNATURE:
            # SPLIT TABLE: Main table + Closing table
            split_point = len(data_rows) - MIN_ROWS_WITH_SIGNATURE
            
            # Main table
            main_rows = data_rows[:split_point]
            main_table_data = [header_row] + [row for row, _ in main_rows]
            main_table = Table(main_table_data, colWidths=col_widths, repeatRows=1)
            apply_table_style(main_table, main_rows)
            elements.append(main_table)
            
            # Closing table (5 rows + TOTAL) with signature - NO HEADER (continuation of main table)
            closing_rows = data_rows[split_point:]
            closing_table_data = [row for row, _ in closing_rows] + [total_row]  # No header row
            closing_table = Table(closing_table_data, colWidths=col_widths)
            # Apply style using helper - no header for continuation table
            style_cmds = self._get_base_table_style(with_header=False)
            
            # Add table-specific styles (same as main table)
            style_cmds.extend([
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),  # Total row
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEBEFORE', (5, 0), (5, -1), 1.0, colors.HexColor('#888888')),  # Progress section divider
                ('LINEAFTER', (7, 0), (7, -1), 1.0, colors.HexColor('#888888')),
            ])
            
            # Apply row backgrounds using helper - offset=0 since no header row
            self._apply_row_backgrounds(style_cmds, closing_rows, offset=0)
            closing_table.setStyle(TableStyle(style_cmds))
            
            keep_block = [closing_table, Spacer(1, 8*mm)]
            if isinstance(sig_inner, list):
                keep_block.extend(sig_inner)
            else:
                keep_block.append(sig_inner)
            elements.append(KeepTogether(keep_block))
        else:
            # NO SPLIT: Small table
            table_data = [header_row] + [row for row, _ in data_rows] + [total_row]
            rincian_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            apply_table_style(rincian_table, data_rows)
            
            keep_block = [rincian_table, Spacer(1, 8*mm)]
            if isinstance(sig_inner, list):
                keep_block.extend(sig_inner)
            else:
                keep_block.append(sig_inner)
            elements.append(KeepTogether(keep_block))
        
        return elements
    
    def _build_weekly_progress_page(
        self,
        week: int,
        project_info: Dict[str, Any],
        summary: Dict[str, Any],
        hierarchy_data: List[Dict[str, Any]],
        period_info: Dict[str, Any] = None
    ) -> List:
        """
        Build Weekly Progress page (same structure as monthly, but with "Minggu" labels).
        
        Combines:
        1. Identitas Project Singkat
        2. Ringkasan Progress
        3. Tabel Rincian Progress
        
        Args:
            week: Week number (1-based)
            project_info: Project information dict
            summary: Executive summary data
            hierarchy_data: Hierarchical pekerjaan with harga and progress
            period_info: Period date information
        """
        elements = []
        
        # ==============================================
        # PAGE TITLE (with top margin to avoid header collision)
        # ==============================================
        elements.append(Spacer(1, 10*mm))
        title_style = ParagraphStyle(
            'PageTitle',
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            alignment=TA_CENTER,
            spaceAfter=8*mm,
        )
        elements.append(Paragraph(
            f"<b>PROGRESS PELAKSANAAN PEKERJAAN MINGGU KE-{week}</b>",
            title_style
        ))
        elements.append(Spacer(1, 5*mm))
        
        # ==============================================
        # SEGMENTS 1 & 2: SIDE-BY-SIDE LAYOUT
        # Left: IDENTITAS PROJECT | Right: RINGKASAN PROGRESS
        # ==============================================
        section_title_style = ParagraphStyle(
            'SectionTitle',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(UTS.PRIMARY_DARK),
            spaceAfter=2*mm,
        )
        
        # --- LEFT COLUMN: IDENTITAS PROJECT ---
        identity_header = Paragraph("IDENTITAS PROJECT", section_title_style)
        identity_data = [
            ['Nama Project', ':', project_info.get('nama', '-')],
            ['Ket. Project 1', ':', project_info.get('keterangan_1', project_info.get('sumber_dana', '-'))],
            ['Ket. Project 2', ':', project_info.get('keterangan_2', project_info.get('nama_client', '-'))],
            ['Lokasi', ':', project_info.get('lokasi', '-')],
        ]
        identity_table = Table(identity_data, colWidths=[32*mm, 3*mm, 58*mm])
        identity_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.TEXT_SECONDARY)),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor(UTS.TEXT_PRIMARY)),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(UTS.LIGHT_BORDER)),
        ]))
        left_content = [[identity_header], [identity_table]]
        left_cell = Table(left_content, colWidths=[90*mm])
        left_cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        # --- RIGHT COLUMN: RINGKASAN PROGRESS ---
        ringkasan_header = Paragraph("RINGKASAN PROGRESS", section_title_style)
        
        # Deviation color: Green positive, Red negative, Yellow/Amber zero
        deviation = summary.get('deviation_cumulative', 0)
        if deviation > 0:
            deviation_color = '#22c55e'  # Green
        elif deviation < 0:
            deviation_color = '#ef4444'  # Red
        else:
            deviation_color = '#eab308'  # Yellow/Amber
        
        # Format deviation with color
        deviation_para = Paragraph(
            f'<font color="{deviation_color}"><b>{deviation:+.2f}%</b></font>',
            ParagraphStyle('Deviation', fontSize=8, fontName='Helvetica')
        )
        
        # Weekly labels: "Minggu Ini" instead of "Bulan Ini"
        ringkasan_data = [
            ['Rencana Minggu Ini', ':', f"{summary.get('target_period', 0):.2f}%"],
            ['Actual Minggu Ini', ':', f"{summary.get('actual_period', 0):.2f}%"],
            ['Akumulasi Rencana', ':', f"{summary.get('cumulative_target', 0):.2f}%"],
            ['Akumulasi Actual', ':', f"{summary.get('cumulative_actual', 0):.2f}%"],
            ['Deviasi', ':', deviation_para],  # Colored deviation
        ]
        
        ringkasan_cells = []
        for row in ringkasan_data:
            ringkasan_cells.append(row)
        
        ringkasan_table = Table(ringkasan_cells, colWidths=[40*mm, 3*mm, 47*mm])
        ringkasan_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.TEXT_SECONDARY)),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 0.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5*mm),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(UTS.LIGHT_BORDER)),
            ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        right_content = [[ringkasan_header], [ringkasan_table]]
        right_cell = Table(right_content, colWidths=[90*mm])
        right_cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        # --- COMBINE INTO 2-COLUMN LAYOUT with center gap ---
        two_column = Table([[left_cell, Spacer(1, 1), right_cell]], colWidths=[90*mm, 6*mm, 90*mm])
        two_column.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(two_column)
        elements.append(Spacer(1, 6*mm))
        
        # ==============================================
        # SEGMENT 3: TABEL RINCIAN PROGRESS (Weekly labels)
        # ==============================================
        segment_name = f"Rincian Progress Minggu ke-{week}"
        elements.append(SegmentMarker(segment_name))
        
        elements.append(Paragraph("RINCIAN PROGRESS", section_title_style))
        elements.append(Spacer(1, 2*mm))
        
        # Table headers - 8 columns with MINGGU labels
        headers = [
            'URAIAN PEKERJAAN', 
            'VOLUME', 
            'HARGA\nSATUAN', 
            'TOTAL\nHARGA', 
            'BOBOT\n(%)', 
            'KUMULATIF\nMINGGU LALU',
            'PROGRESS\nMINGGU INI', 
            'KUMULATIF\nMINGGU INI'
        ]
        
        # Smart truncation calculation
        URAIAN_COL_WIDTH_PT = 144.5
        
        def smart_truncate(text, font_size=7, max_lines=2, indent_level=0):
            if not text:
                return ''
            text = str(text)
            avg_char_width = font_size * 0.38
            chars_per_line = int(URAIAN_COL_WIDTH_PT / avg_char_width)
            indent_chars = indent_level * 2
            effective_chars_per_line = chars_per_line - indent_chars
            max_chars = effective_chars_per_line * max_lines
            if len(text) <= max_chars:
                return text
            return text[:max_chars-3].rstrip() + '...'
        
        def P(text, bold=False, align='LEFT', size=7, color=None, max_chars=None, max_lines=None, indent_level=0):
            if max_lines and text:
                text = smart_truncate(str(text), font_size=size, max_lines=max_lines, indent_level=indent_level)
            elif max_chars and text:
                text = str(text)
                if len(text) > max_chars:
                    text = text[:max_chars-3].rstrip() + '...'
            
            al = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}.get(align, TA_LEFT)
            st = ParagraphStyle(
                'Cell', 
                fontSize=size, 
                alignment=al,
                fontName='Helvetica-Bold' if bold else 'Helvetica',
                textColor=colors.HexColor(color) if color else colors.black,
                leading=size + 2,
            )
            return Paragraph(str(text or ''), st)
        
        def PHeader(text):
            st = ParagraphStyle(
                'Header', 
                fontSize=7, 
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.white,
                leading=9,
            )
            return Paragraph(str(text or ''), st)
        
        header_row = [PHeader(h) for h in headers]
        
        # Build data rows from hierarchy
        data_rows = []
        total_harga = 0
        total_bobot = 0
        total_kumulatif_lalu = 0
        total_progress_ini = 0
        total_progress_kumulatif = 0
        
        for item in hierarchy_data:
            level = item.get('level', 0)
            item_type = item.get('type', 'pekerjaan')
            name = item.get('name', item.get('uraian', ''))
            volume = item.get('volume', 0) or 0
            harga_satuan = item.get('harga_satuan', 0) or 0
            harga = item.get('harga', 0) or 0
            bobot = item.get('bobot', 0) or 0
            # Use weekly progress fields
            progress_ini = item.get('progress_minggu_ini', item.get('progress_bulan_ini', 0)) or 0
            progress_lalu = item.get('progress_minggu_lalu', item.get('progress_bulan_lalu', 0)) or 0
            kumulatif_lalu = progress_lalu
            progress_kumulatif = progress_lalu + progress_ini
            
            indent = "  " * level
            display_name = f"{indent}{name}"
            
            is_klasifikasi = item_type == 'klasifikasi'
            is_sub_klasifikasi = item_type == 'sub_klasifikasi'
            is_parent = is_klasifikasi or is_sub_klasifikasi
            
            if is_klasifikasi:
                font_size = 8
                row_bold = True
            elif is_sub_klasifikasi:
                font_size = 7.5
                row_bold = True
            else:
                font_size = 7
                row_bold = False
            
            if is_parent:
                volume_fmt = ""
                harga_satuan_fmt = ""
                harga_fmt = ""
                bobot_fmt = ""
                progress_ini_fmt = ""
                kumulatif_lalu_fmt = ""
                progress_kumulatif_fmt = ""
            else:
                volume_fmt = f"{volume:,.2f}".replace(',', '.') if volume > 0 else "-"
                harga_satuan_fmt = self._format_rupiah(harga_satuan) if harga_satuan > 0 else "-"
                harga_fmt = self._format_rupiah(harga) if harga > 0 else "-"
                bobot_fmt = self._format_percent(bobot, show_zero=False)
                progress_ini_fmt = self._format_percent(progress_ini)
                kumulatif_lalu_fmt = self._format_percent(kumulatif_lalu)
                progress_kumulatif_fmt = self._format_percent(progress_kumulatif)
            
            row = [
                P(display_name, bold=row_bold, align='LEFT', size=font_size, max_lines=2, indent_level=level),
                P(volume_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(harga_satuan_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(harga_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(bobot_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(kumulatif_lalu_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(progress_ini_fmt, bold=row_bold, align='CENTER', size=font_size),
                P(progress_kumulatif_fmt, bold=row_bold, align='CENTER', size=font_size),
            ]
            data_rows.append((row, item_type))
            
            if item_type == 'pekerjaan':
                total_harga += harga
                total_bobot += bobot
                total_kumulatif_lalu += kumulatif_lalu
                total_progress_ini += progress_ini
                total_progress_kumulatif += progress_kumulatif
        
        if 99.9 <= total_bobot <= 100.1:
            total_bobot = 100.0
        
        total_row = [
            P("TOTAL", bold=True, align='LEFT', size=7),
            P("", bold=True, align='CENTER', size=7),
            P("", bold=True, align='CENTER', size=7),
            P(self._format_rupiah(total_harga), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_bobot), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_kumulatif_lalu), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_progress_ini), bold=True, align='CENTER', size=7),
            P(self._format_percent(total_progress_kumulatif), bold=True, align='CENTER', size=7),
        ]
        
        table_data = [header_row]
        for row, _ in data_rows:
            table_data.append(row)
        table_data.append(total_row)
        
        col_widths = [55*mm, 12*mm, 22*mm, 22*mm, 12*mm, 18*mm, 18*mm, 18*mm]
        
        MIN_ROWS_WITH_SIGNATURE = 5
        
        def apply_table_style(table, rows_data):
            style_cmds = self._get_base_table_style(with_header=True)
            style_cmds.extend([
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEBEFORE', (5, 0), (5, -1), 1.0, colors.HexColor('#888888')),
                ('LINEAFTER', (7, 0), (7, -1), 1.0, colors.HexColor('#888888')),
            ])
            self._apply_row_backgrounds(style_cmds, rows_data, offset=1)
            table.setStyle(TableStyle(style_cmds))
        
        sig_section = self._build_progress_signature_section(project_info)
        sig_inner = sig_section[0]._content if hasattr(sig_section[0], '_content') else sig_section
        
        if len(data_rows) > MIN_ROWS_WITH_SIGNATURE:
            split_point = len(data_rows) - MIN_ROWS_WITH_SIGNATURE
            
            main_rows = data_rows[:split_point]
            main_table_data = [header_row] + [row for row, _ in main_rows]
            main_table = Table(main_table_data, colWidths=col_widths, repeatRows=1)
            apply_table_style(main_table, main_rows)
            elements.append(main_table)
            
            closing_rows = data_rows[split_point:]
            closing_table_data = [row for row, _ in closing_rows] + [total_row]
            closing_table = Table(closing_table_data, colWidths=col_widths)
            style_cmds = self._get_base_table_style(with_header=False)
            style_cmds.extend([
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEBEFORE', (5, 0), (5, -1), 1.0, colors.HexColor('#888888')),
                ('LINEAFTER', (7, 0), (7, -1), 1.0, colors.HexColor('#888888')),
            ])
            self._apply_row_backgrounds(style_cmds, closing_rows, offset=0)
            closing_table.setStyle(TableStyle(style_cmds))
            
            keep_block = [closing_table, Spacer(1, 8*mm)]
            if isinstance(sig_inner, list):
                keep_block.extend(sig_inner)
            else:
                keep_block.append(sig_inner)
            elements.append(KeepTogether(keep_block))
        else:
            table_data = [header_row] + [row for row, _ in data_rows] + [total_row]
            rincian_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            apply_table_style(rincian_table, data_rows)
            
            keep_block = [rincian_table, Spacer(1, 8*mm)]
            if isinstance(sig_inner, list):
                keep_block.extend(sig_inner)
            else:
                keep_block.append(sig_inner)
            elements.append(KeepTogether(keep_block))
        
        return elements
    
    def _build_progress_signature_section(self, project_info: Dict[str, Any]) -> List:

        """
        Build reusable Lembar Pengesahan (signature section).
        
        Can be used in:
        - Laporan Bulanan (monthly)
        - Laporan Mingguan (weekly) 
        - Rekap Laporan (rekap)
        
        Structure:
        - Title: "LEMBAR PENGESAHAN" (10pt, centered)
        - 3 columns: PELAKSANA | PENGAWAS | PEMILIK PEKERJAAN
        - 2 empty rows for hand signature
        - Names row with signature line (70mm underscores)
        - Jabatan row: Direktur | Direktur | jabatan_client
        - Instansi row: instansi_kontraktor | instansi_konsultan | instansi_client
        
        Args:
            project_info: Dict containing:
                - nama_kontraktor, nama_konsultan_pengawas, nama_client
                - jabatan_client, instansi_client
                - instansi_kontraktor, instansi_konsultan_pengawas
        
        Returns:
            List of flowable elements for the signature section
        """
        sig_elements = []
        sig_elements.append(Spacer(1, 10*mm))
        
        # Title style: 10pt bold, centered
        sig_title_style = ParagraphStyle(
            'SigTitle',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(UTS.TEXT_SECONDARY),
            alignment=TA_CENTER,
            spaceAfter=5*mm,
        )
        sig_elements.append(Paragraph("LEMBAR PENGESAHAN", sig_title_style))
        
        # Label style: 8pt normal, centered (for column headers)
        sig_label_style = ParagraphStyle(
            'SigLabel',
            fontSize=8,
            fontName='Helvetica',
            alignment=TA_CENTER,
        )
        
        # Name style: 7pt normal, centered (for names, jabatan, instansi)
        sig_name_style = ParagraphStyle(
            'SigName',
            fontSize=7,
            fontName='Helvetica',
            alignment=TA_CENTER,
        )
        
        # Get project info values
        instansi_kontraktor = project_info.get('instansi_kontraktor', '-')
        instansi_konsultan = project_info.get('instansi_konsultan_pengawas', '-')
        jabatan_client = project_info.get('jabatan_client', '-')
        instansi_client = project_info.get('instansi_client', '-')
        
        # Build table data
        sig_data = [
            # Row 0: Headers (role titles)
            [
                Paragraph("PELAKSANA", sig_label_style),
                Paragraph("PENGAWAS", sig_label_style), 
                Paragraph("PEMILIK PEKERJAAN", sig_label_style)
            ],
            # Row 1-2: Space for hand signature
            ['', '', ''],
            ['', '', ''],
            # Row 3: Signature names
            [
                Paragraph(project_info.get('nama_kontraktor', '-') or '-', sig_name_style),
                Paragraph(project_info.get('nama_konsultan_pengawas', '-') or '-', sig_name_style),
                Paragraph(project_info.get('nama_client', '-') or '-', sig_name_style)
            ],
            # Row 4: Signature line (70mm / 7cm centered)
            [
                Paragraph('_' * 35, sig_name_style),
                Paragraph('_' * 35, sig_name_style),
                Paragraph('_' * 35, sig_name_style)
            ],
            # Row 5: Jabatan
            [
                Paragraph("Direktur", sig_name_style),
                Paragraph("Direktur", sig_name_style),
                Paragraph(jabatan_client or "-", sig_name_style)
            ],
            # Row 6: Instansi
            [
                Paragraph(instansi_kontraktor or "-", sig_name_style),
                Paragraph(instansi_konsultan or "-", sig_name_style),
                Paragraph(instansi_client or "-", sig_name_style)
            ],
        ]
        
        # Table: 3 columns x 60mm each = 180mm total
        sig_table = Table(sig_data, colWidths=[60*mm, 60*mm, 60*mm])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, 2), 6*mm),   # Space for hand signature
            ('TOPPADDING', (0, 3), (-1, 4), 0),      # No space between name/line
            ('BOTTOMPADDING', (0, 3), (-1, 4), 0),
            ('TOPPADDING', (0, 5), (-1, -1), 0),     # Minimum spacing jabatan/instansi
            ('BOTTOMPADDING', (0, 5), (-1, -1), 0),
        ]))
        sig_elements.append(sig_table)
        
        # Wrap in KeepTogether to stay with preceding content
        return [KeepTogether(sig_elements)]

    def _build_executive_summary_section(self, summary: Dict[str, Any], mode: str = 'monthly') -> List:
        """
        Build executive summary section for reports.
        
        Args:
            summary: Executive summary data from adapter
            mode: 'monthly' or 'weekly'
        """
        elements = []
        
        # Section title
        title_style = ParagraphStyle(
            'SectionTitle',
            fontSize=14,
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            fontName='Helvetica-Bold',
            spaceAfter=3*mm,
        )
        elements.append(Paragraph("<b>RINGKASAN EKSEKUTIF</b>", title_style))
        elements.append(Spacer(1, 5*mm))
        
        # Status indicator color - using UTS constants
        status = summary.get('status', 'On Track')
        status_color = {
            'On Track': UTS.STATUS_ON_TRACK,
            'Ahead': UTS.STATUS_AHEAD,
            'Behind': UTS.STATUS_BEHIND,
            'Critical': UTS.STATUS_CRITICAL,
        }.get(status, UTS.TEXT_MUTED)
        
        # Summary metrics
        period_label = summary.get('period_label', 'Periode Ini')
        metrics = [
            [f'Target {period_label}', ':', f"{summary.get('target_period', 0):.2f}%"],
            [f'Realisasi {period_label}', ':', f"{summary.get('actual_period', 0):.2f}%"],
            ['Deviasi', ':', f"{summary.get('deviation', 0):+.2f}%"],
            ['', '', ''],
            ['Kumulatif Target', ':', f"{summary.get('cumulative_target', 0):.2f}%"],
            ['Kumulatif Realisasi', ':', f"{summary.get('cumulative_actual', 0):.2f}%"],
            ['Deviasi Kumulatif', ':', f"{summary.get('deviation_cumulative', 0):+.2f}%"],
        ]
        
        summary_table = Table(metrics, colWidths=[60*mm, 5*mm, 50*mm])
        summary_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.TEXT_MUTED)),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
        ]))
        elements.append(summary_table)
        
        return elements

    def _build_comparison_table(
        self,
        current_data: Dict[str, Any],
        previous_data: Dict[str, Any],
        comparison: Dict[str, Any],
        mode: str = 'monthly'
    ) -> List:
        """
        Build comparison table for this period vs previous period.
        
        Args:
            current_data: Current period data
            previous_data: Previous period data
            comparison: Comparison/delta data
            mode: 'monthly' or 'weekly'
        """
        elements = []
        
        # Section title
        period_name = "Bulan" if mode == "monthly" else "Minggu"
        title_style = ParagraphStyle(
            'SectionTitle',
            fontSize=14,
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            fontName='Helvetica-Bold',
            spaceAfter=3*mm,
        )
        elements.append(Paragraph(
            f"<b>PERBANDINGAN: {period_name.upper()} INI vs {period_name.upper()} SEBELUMNYA</b>",
            title_style
        ))
        elements.append(Spacer(1, 5*mm))
        
        if not comparison.get('has_previous', False):
            no_prev_style = ParagraphStyle(
                'NoPrev',
                fontSize=10,
                textColor=colors.HexColor(UTS.TEXT_MUTED),
                fontStyle='italic',
            )
            elements.append(Paragraph(
                f"<i>Tidak ada data {period_name.lower()} sebelumnya untuk perbandingan.</i>",
                no_prev_style
            ))
            elements.append(Spacer(1, 5*mm))
            return elements
        
        # Format delta values
        def format_delta(val):
            if val >= 0:
                return f'<font color="#27ae60">+{val:.2f}%</font>'
            else:
                return f'<font color="#e74c3c">{val:.2f}%</font>'
        
        # Headers
        headers = ['Metrik', f'{period_name} Lalu', f'{period_name} Ini', 'Delta']
        
        # Data rows
        data_rows = [
            [
                'Target',
                f"{previous_data.get('target_period', 0):.2f}%",
                f"{current_data.get('target_period', 0):.2f}%",
                format_delta(comparison.get('delta_target', 0)),
            ],
            [
                'Realisasi',
                f"{previous_data.get('actual_period', 0):.2f}%",
                f"{current_data.get('actual_period', 0):.2f}%",
                format_delta(comparison.get('delta_actual', 0)),
            ],
            [
                'Kumulatif',
                f"{previous_data.get('cumulative_actual', 0):.2f}%",
                f"{current_data.get('cumulative_actual', 0):.2f}%",
                format_delta(comparison.get('delta_cumulative', 0)),
            ],
        ]
        
        # Create paragraphs for wrapping
        def P(text, bold=False, align='LEFT'):
            styles = getSampleStyleSheet()
            st = ParagraphStyle(
                'Cell', parent=styles['Normal'],
                fontSize=10,
                alignment={'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}.get(align, TA_LEFT)
            )
            if bold:
                st.fontName = 'Helvetica-Bold'
            return Paragraph(str(text or ''), st)
        
        header_cells = [P(h, bold=True, align='CENTER') for h in headers]
        wrapped_rows = []
        for row in data_rows:
            wrapped_rows.append([
                P(row[0], bold=True, align='LEFT'),
                P(row[1], align='CENTER'),
                P(row[2], align='CENTER'),
                P(row[3], align='CENTER'),
            ])
        
        full_data = [header_cells] + wrapped_rows
        
        table = Table(full_data, colWidths=[50*mm, 35*mm, 35*mm, 35*mm])
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(UTS.SECTION_HEADER_BG)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(UTS.PRIMARY_LIGHT)),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        
        elements.append(table)
        
        return elements

    def _build_table_of_contents(self, sections: List[str]) -> List:
        """
        Build enhanced table of contents for rekap report.
        
        Features:
        - Decorative title
        - Dotted leaders between entry and page number
        - Section icons
        - Professional layout
        
        Args:
            sections: List of section titles
        """
        elements = []
        
        # Title with decorative line
        title_style = ParagraphStyle(
            'TOCTitle',
            fontSize=18,
            textColor=colors.HexColor(UTS.PRIMARY_LIGHT),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=5*mm,
        )
        elements.append(Paragraph("<b>DAFTAR ISI</b>", title_style))
        
        # Decorative line under title
        line_drawing = Drawing(200*mm, 4)
        line_drawing.add(Line(0, 2, 200*mm, 2, strokeColor=colors.HexColor(UTS.PRIMARY_LIGHT), strokeWidth=1))
        elements.append(line_drawing)
        elements.append(Spacer(1, 10*mm))
        
        # Section icons
        section_icons = {
            'Grid View': '▣',
            'Kurva S': '📈',
            'Gantt Chart': '📊',
            'Rencana': '📋',
            'Realisasi': '✓',
        }
        
        # TOC entries as table
        toc_data = []
        for idx, section in enumerate(sections, 1):
            # Determine icon based on section name
            icon = ''
            for key, ico in section_icons.items():
                if key.lower() in section.lower():
                    icon = ico
                    break
            
            # Create dotted leader
            dots = '.' * 80  # Will be styled with color
            
            # Build row: [number, icon, section name, dots, page num]
            toc_data.append([
                f"{idx}.",
                icon,
                section,
                dots,
                f"..."  # Placeholder for page number
            ])
        
        if toc_data:
            toc_table = Table(toc_data, colWidths=[10*mm, 8*mm, 120*mm, 70*mm, 15*mm])
            toc_table.setStyle(TableStyle([
                # Font styling
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Numbers bold
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),  # Section names
                ('FONTSIZE', (3, 0), (3, -1), 8),  # Dots smaller
                
                # Colors
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(UTS.PRIMARY_LIGHT)),
                ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor(UTS.LIGHT_BORDER)),
                ('TEXTCOLOR', (4, 0), (4, -1), colors.HexColor(UTS.TEXT_MUTED)),
                
                # Alignment
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Padding
                ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
                
                # Alternating row backgrounds
                *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8f9fa')) 
                  for i in range(0, len(toc_data), 2)],
                
                # Subtle bottom border for each row
                ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor(UTS.LIGHT_BORDER)),
            ]))
            elements.append(toc_table)
        
        return elements

    def _build_detail_progress_table(self, detail_table: Dict[str, Any]) -> Table:
        """
        Build detail progress table for monthly/weekly reports.
        
        Args:
            detail_table: Detail table data from adapter
        """
        headers = detail_table.get('headers', [])
        rows = detail_table.get('rows', [])
        
        # Create paragraphs
        def P(text, bold=False, align='LEFT'):
            styles = getSampleStyleSheet()
            st = ParagraphStyle(
                'Cell', parent=styles['Normal'],
                fontSize=8,
                alignment={'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}.get(align, TA_LEFT)
            )
            if bold:
                st.fontName = 'Helvetica-Bold'
            return Paragraph(str(text or ''), st)
        
        header_cells = [P(h, bold=True, align='CENTER') for h in headers]
        
        wrapped_rows = []
        for row_data in rows:
            row_type = row_data.get('type', 'pekerjaan')
            level = row_data.get('level', 3)
            values = row_data.get('values', [])
            
            wrapped = []
            for idx, val in enumerate(values):
                if idx == 0:  # No column
                    wrapped.append(P(val, align='CENTER'))
                elif idx == 1:  # Uraian
                    # Indent based on level
                    indent = '   ' * (level - 1)
                    display_val = f"{indent}{val}"
                    wrapped.append(P(display_val, bold=(row_type != 'pekerjaan'), align='LEFT'))
                elif idx == 2:  # Total Harga
                    wrapped.append(P(val, align='RIGHT'))
                else:  # Bobot and progress columns
                    wrapped.append(P(val, align='CENTER'))
            
            wrapped_rows.append(wrapped)
        
        full_data = [header_cells] + wrapped_rows
        
        # Column widths (adjust based on content)
        col_widths = [10*mm, 60*mm, 30*mm, 18*mm, 18*mm, 18*mm, 22*mm, 22*mm]
        
        table = Table(full_data, colWidths=col_widths, repeatRows=1)
        
        # Build style
        style_commands = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(UTS.SECTION_HEADER_BG)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdc3c7')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(UTS.PRIMARY_LIGHT)),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 1*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1*mm),
        ]
        
        # Apply hierarchy styling
        for idx, row_data in enumerate(rows):
            row_num = idx + 1
            row_type = row_data.get('type', 'pekerjaan')
            
            if row_type == 'klasifikasi':
                style_commands.extend([
                    ('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor(UTS.SECTION_HEADER_BG)),
                    ('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'),
                ])
            elif row_type == 'sub_klasifikasi':
                style_commands.extend([
                    ('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#f5f5f5')),
                    ('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'),
                ])
        
        table.setStyle(TableStyle(style_commands))
        
        return table
    
    def _build_kurva_s_chart(self, kurva_s_data: List[Dict], width: float = 500, height: float = 300) -> Drawing:
        """
        Build Kurva S line chart using ReportLab graphics.
        
        Args:
            kurva_s_data: List of dicts with 'week', 'planned', 'actual' keys
            width: Chart width in points
            height: Chart height in points
            
        Returns:
            Drawing object containing the chart
        """
        if not kurva_s_data:
            return None
            
        # Create Drawing
        drawing = Drawing(width, height)
        
        # Add background
        drawing.add(Rect(0, 0, width, height, fillColor=colors.white, strokeColor=colors.lightgrey))
        
        # Chart area margins
        left_margin = 60
        right_margin = 30
        top_margin = 40
        bottom_margin = 50
        
        chart_width = width - left_margin - right_margin
        chart_height = height - top_margin - bottom_margin
        
        # Create LinePlot
        lp = LinePlot()
        lp.x = left_margin
        lp.y = bottom_margin
        lp.width = chart_width
        lp.height = chart_height
        
        # Prepare data
        # Format: [(x1, y1), (x2, y2), ...] for each series
        planned_data = []
        actual_data = []
        
        for i, item in enumerate(kurva_s_data):
            week = item.get('week', i + 1)
            planned = item.get('planned', 0) or 0
            actual = item.get('actual', 0) or 0
            planned_data.append((week, planned))
            actual_data.append((week, actual))
        
        lp.data = [planned_data, actual_data]
        
        # Style the lines
        # Planned: Cyan
        lp.lines[0].strokeColor = colors.HexColor(UTS.PLANNED_COLOR)
        lp.lines[0].strokeWidth = 2
        lp.lines[0].symbol = makeMarker('Circle')
        lp.lines[0].symbol.fillColor = colors.HexColor(UTS.PLANNED_COLOR)
        lp.lines[0].symbol.strokeColor = colors.HexColor(UTS.PLANNED_COLOR)
        lp.lines[0].symbol.size = 4
        
        # Actual: Yellow/Gold
        lp.lines[1].strokeColor = colors.HexColor(UTS.ACTUAL_COLOR)
        lp.lines[1].strokeWidth = 2
        lp.lines[1].symbol = makeMarker('Circle')
        lp.lines[1].symbol.fillColor = colors.HexColor(UTS.ACTUAL_COLOR)
        lp.lines[1].symbol.strokeColor = colors.HexColor(UTS.ACTUAL_COLOR)
        lp.lines[1].symbol.size = 4
        
        # X-axis configuration
        lp.xValueAxis.valueMin = 1
        lp.xValueAxis.valueMax = max(len(kurva_s_data), 1)
        lp.xValueAxis.valueStep = max(1, len(kurva_s_data) // 10)  # Show ~10 labels
        lp.xValueAxis.labels.fontName = 'Helvetica'
        lp.xValueAxis.labels.fontSize = 8
        lp.xValueAxis.labels.angle = 0
        
        # Y-axis configuration (percentage 0-100)
        max_val = max(
            max((d.get('planned', 0) or 0) for d in kurva_s_data),
            max((d.get('actual', 0) or 0) for d in kurva_s_data),
            10  # Minimum
        )
        lp.yValueAxis.valueMin = 0
        lp.yValueAxis.valueMax = min(100, max_val * 1.1)  # Add 10% buffer, max 100
        lp.yValueAxis.valueStep = 10
        lp.yValueAxis.labels.fontName = 'Helvetica'
        lp.yValueAxis.labels.fontSize = 8
        lp.yValueAxis.labelTextFormat = '%d%%'
        
        drawing.add(lp)
        
        # Add title
        title = String(width / 2, height - 15, 'Kurva S Progress Kumulatif',
                       fontSize=12, fontName='Helvetica-Bold', textAnchor='middle')
        drawing.add(title)
        
        # Add X-axis label
        x_label = String(left_margin + chart_width / 2, 10, 'Minggu ke-',
                         fontSize=9, fontName='Helvetica', textAnchor='middle')
        drawing.add(x_label)
        
        # Add Y-axis label (horizontal, positioned at top left of Y-axis)
        y_label = String(5, bottom_margin + chart_height + 5, '(%)',
                         fontSize=9, fontName='Helvetica', textAnchor='start')
        drawing.add(y_label)
        
        # Add legend
        legend = Legend()
        legend.x = left_margin + chart_width - 100
        legend.y = height - 30
        legend.columnMaximum = 1
        legend.fontSize = 8
        legend.fontName = 'Helvetica'
        legend.alignment = 'right'
        legend.colorNamePairs = [
            (colors.HexColor(UTS.PLANNED_COLOR), 'Planned'),
            (colors.HexColor(UTS.ACTUAL_COLOR), 'Actual'),
        ]
        drawing.add(legend)
        
        return drawing
    
    def _build_kurva_s_data_table(self, kurva_s_data: List[Dict], max_cols: int = 12) -> Table:
        """
        Build Kurva S data table showing weekly planned/actual values.
        
        Args:
            kurva_s_data: List of dicts with 'week', 'planned', 'actual' keys
            max_cols: Maximum columns to show (will sample if more weeks)
            
        Returns:
            Table object with weekly data
        """
        if not kurva_s_data:
            return None
        
        # Sample data if too many weeks (show first, last, and evenly distributed)
        total_weeks = len(kurva_s_data)
        if total_weeks > max_cols:
            # Take samples: first, middle samples, last
            step = total_weeks // (max_cols - 1)
            indices = list(range(0, total_weeks, step))[:max_cols-1] + [total_weeks - 1]
            sampled_data = [kurva_s_data[i] for i in indices]
        else:
            sampled_data = kurva_s_data
        
        # Build table data
        header_row = [''] + [f"W{d.get('week', i+1)}" for i, d in enumerate(sampled_data)]
        planned_row = ['Planned'] + [f"{d.get('planned', 0):.1f}%" for d in sampled_data]
        actual_row = ['Actual'] + [f"{d.get('actual', 0):.1f}%" for d in sampled_data]
        
        table_data = [header_row, planned_row, actual_row]
        
        # Calculate column widths
        col_width = 45  # Fixed width per week column
        first_col_width = 60
        col_widths = [first_col_width] + [col_width] * len(sampled_data)
        
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(UTS.PRIMARY_LIGHT)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Planned row - cyan tint
            ('BACKGROUND', (0, 1), (0, 1), colors.HexColor(UTS.PLANNED_COLOR)),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
            # Actual row - gold tint
            ('BACKGROUND', (0, 2), (0, 2), colors.HexColor(UTS.ACTUAL_COLOR)),
            ('TEXTCOLOR', (0, 2), (0, 2), colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        return table
    
    def _build_gantt_chart(self, pekerjaan_rows: List[Dict], time_columns: List[Dict], 
                           planned_progress: Dict, actual_progress: Dict,
                           width: float = 700, row_height: float = 24) -> List:
        """
        Build Gantt chart with dual bars (planned/actual) per pekerjaan using ReportLab.
        Uses FIXED column widths matching Grid View rules.
        SUPPORTS PAGINATION: renders all weeks across multiple pages.
        """
        if not pekerjaan_rows or not time_columns:
            return []
        
        all_elements = []
        
        # =============================================
        # FIXED WIDTH RULES (Match Grid View)
        # =============================================
        # UNIFIED LAYOUT using TableLayoutCalculator
        # =============================================
        layout_calc = TLC(self.config)
        total_weeks = len(time_columns)
        
        # Get layout for total weeks
        TABLE_WIDTH_PT = layout_calc.table_width
        MAX_WEEKS_PER_PAGE = layout_calc.max_weeks_per_page
        WEEK_WIDTH_PT = UTS.WEEK_WIDTH
        
        # Calculate number of pages
        num_pages = layout_calc.get_num_pages(total_weeks)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[Gantt] TABLE_WIDTH={TABLE_WIDTH_PT:.0f}pt, MAX_WEEKS={MAX_WEEKS_PER_PAGE}, total_weeks={total_weeks}, pages={num_pages}")
        
        # =============================================
        # PAGINATE: Loop through week chunks
        # =============================================
        for page_idx in range(num_pages):
            start_week_idx = page_idx * MAX_WEEKS_PER_PAGE
            end_week_idx = min(start_week_idx + MAX_WEEKS_PER_PAGE, total_weeks)
            page_time_columns = time_columns[start_week_idx:end_week_idx]
            
            weeks_on_this_page = len(page_time_columns)
            
            # UNIFIED: Use TLC.calculate() for column widths
            page_layout = layout_calc.calculate(weeks_on_this_page)
            col_widths = page_layout['column_widths']
            blank_cols = page_layout['blank_cols']
            
            # Add page indicator if multiple pages
            if num_pages > 1:
                header_text = SHF.gantt(page_idx + 1, num_pages, start_week_idx + 1, end_week_idx)
                page_label = Paragraph(
                    f"<b>{header_text}</b>",
                    ParagraphStyle('PageLabel', fontSize=SHF.FONT_SIZE, fontName=SHF.FONT_NAME, spaceAfter=3*mm)
                )
                all_elements.append(page_label)
            
            # =============================================
            # BUILD HEADER with WHF (WeekHeaderFormatter)
            # 2-line format: Wx (line 1) + dd/mm-dd/mm (line 2)
            # =============================================
            def create_week_header(tc, idx):
                """Create 2-line week header - ALWAYS 2 lines with <br/>"""
                # Note: adapter uses 'week_number' key, not 'week'
                week_num = tc.get('week_number', tc.get('week', idx + 1))
                date_range = tc.get('range', '')
                if not date_range:
                    start = tc.get('start_date', '')
                    end = tc.get('end_date', '')
                    if start and end and hasattr(start, 'strftime'):
                        date_range = f"{start.strftime('%d/%m')}-{end.strftime('%d/%m')}"
                
                # ALWAYS return 2-line format with <br/>
                week_label = f'W{week_num}'
                if date_range:
                    return f'<b>{week_label}</b><br/><font size="4">{date_range}</font>'
                else:
                    # Use dash placeholder to maintain 2-line format
                    return f'<b>{week_label}</b><br/><font size="4">-</font>'
            
            # Create header cells with proper leading for 2-line display
            header_style = ParagraphStyle(
                'GanttHeader', parent=getSampleStyleSheet()['Normal'],
                fontSize=5,
                fontName='Helvetica-Bold',
                alignment=1,
                textColor=colors.white,
                leading=8,  # Increased for 2-line display
            )
            
            # Static column header style (larger font)
            static_header_style = ParagraphStyle(
                'StaticHeader', parent=getSampleStyleSheet()['Normal'],
                fontSize=7,
                fontName='Helvetica-Bold',
                alignment=1,
                textColor=colors.white,
            )
            
            # UNIFIED: 3 static headers (Uraian, Volume, Satuan)
            uraian_header = Paragraph('Uraian Pekerjaan', static_header_style)
            volume_header = Paragraph('Volume', static_header_style)
            satuan_header = Paragraph('Satuan', static_header_style)
            
            header_cells = [uraian_header, volume_header, satuan_header]
            for i, tc in enumerate(page_time_columns):
                header_text = create_week_header(tc, start_week_idx + i)
                header_cells.append(Paragraph(header_text, header_style))
            
            # Add blank header cells
            for _ in range(blank_cols):
                header_cells.append(Paragraph('', header_style))
            
            table_data = [header_cells]
            
            # =============================================
            # BUILD DATA ROWS WITH BAR CHART DRAWINGS
            # =============================================
            
            # Bar colors
            planned_color = colors.HexColor('#0891b2')  # Teal (matching Kurva S)
            actual_color = colors.HexColor('#f59e0b')   # Amber (matching Kurva S)
            
            ROW_HEIGHT = 24  # Height per pekerjaan row
            BAR_HEIGHT = 8   # Height of each bar (planned/actual)
            BAR_GAP = 2      # Gap between bars
            
            from reportlab.graphics.shapes import Drawing, Rect, String, Line
            
            def create_bar_cell(planned_weeks, actual_weeks, weeks_to_render, week_width, is_pekerjaan=True):
                """Create a Drawing with dual horizontal bars and vertical grid lines"""
                total_width = weeks_to_render * week_width
                d = Drawing(total_width, ROW_HEIGHT)
                
                # Draw vertical grid lines for week boundaries
                grid_color = colors.HexColor('#e2e8f0')
                for i in range(1, weeks_to_render):
                    x = i * week_width
                    d.add(Line(x, 0, x, ROW_HEIGHT, strokeColor=grid_color, strokeWidth=0.5))
                
                # Only draw bars for pekerjaan rows
                if is_pekerjaan:
                    # Calculate bar positions
                    bar_y_planned = ROW_HEIGHT - 4 - BAR_HEIGHT  # Top bar
                    bar_y_actual = 4  # Bottom bar
                    
                    # Draw planned bar (teal) - spans from first to last week with progress
                    if planned_weeks:
                        start_week = min(planned_weeks)
                        end_week = max(planned_weeks)
                        bar_x = (start_week - 1) * week_width
                        bar_width = (end_week - start_week + 1) * week_width
                        d.add(Rect(bar_x, bar_y_planned, bar_width, BAR_HEIGHT, 
                                  fillColor=planned_color, strokeColor=None))
                    
                    # Draw actual bar (amber) - spans from first to last week with progress
                    if actual_weeks:
                        start_week = min(actual_weeks)
                        end_week = max(actual_weeks)
                        bar_x = (start_week - 1) * week_width
                        bar_width = (end_week - start_week + 1) * week_width
                        d.add(Rect(bar_x, bar_y_actual, bar_width, BAR_HEIGHT,
                                  fillColor=actual_color, strokeColor=None))
                
                return d
            
            # Include ALL rows with hierarchy (not just pekerjaan)
            # Track row indices for hierarchy styling
            hierarchy_row_styles = []  # List of (row_idx, row_type)
            
            for row in pekerjaan_rows:
                # UNIFIED: Use DRP for consistent data parsing
                parsed = DRP.from_dict(row)
                row_type = parsed['type']
                name = parsed['uraian']
                level = parsed['level']
                volume = parsed['volume']
                satuan = parsed['satuan']
                
                row_id = str(row.get('id', ''))
                
                # Determine if this is a pekerjaan (has bars) or hierarchy header
                is_pekerjaan = DRP.is_pekerjaan(row)
                
                # Indent based on level (no truncation - use text wrapping)
                indent = '  ' * level
                
                # UNIFIED: Use HS for font styling
                font_name, font_size = HS.get_row_font(row_type=row_type)
                
                # Find weeks with planned/actual progress (only for pekerjaan)
                planned_weeks_list = []
                actual_weeks_list = []
                
                if is_pekerjaan:
                    row_progress = planned_progress.get(row_id, {})
                    row_actual = actual_progress.get(row_id, {})
                    
                    # Debug: Log first row's progress data (only on first page)
                    if len(hierarchy_row_styles) < 3 and page_idx == 0:
                        logger.info(f"[Gantt] Row {row_id}: planned_keys={list(row_progress.keys())[:5]}, actual_keys={list(row_actual.keys())[:5]}")
                    
                    for i, tc in enumerate(page_time_columns):
                        # Try multiple key formats
                        week = tc.get('week', start_week_idx + i + 1)
                        week_label = tc.get('label', f'W{week}')
                        week_index = i + 1  # 1-indexed for bar position
                        
                        # Try week number, then index, then string formats
                        planned_val = (
                            row_progress.get(week, 0) or 
                            row_progress.get(str(week), 0) or 
                            row_progress.get(week_index, 0) or
                            row_progress.get(week_label, 0)
                        )
                        actual_val = (
                            row_actual.get(week, 0) or 
                            row_actual.get(str(week), 0) or 
                            row_actual.get(week_index, 0) or
                            row_actual.get(week_label, 0)
                        )
                        
                        if planned_val > 0:
                            planned_weeks_list.append(week_index)
                        if actual_val > 0:
                            actual_weeks_list.append(week_index)
                    
                    # Debug: Log if bars found
                    if planned_weeks_list or actual_weeks_list:
                        logger.info(f"[Gantt] Row {row_id}: planned_weeks={planned_weeks_list}, actual_weeks={actual_weeks_list}")
                
                # Create name cell with hierarchy styling and TEXT WRAPPING
                # Don't truncate name - let Paragraph handle wrapping
                full_display_name = f"{indent}{name}"
                
                name_cell = Paragraph(full_display_name, ParagraphStyle(
                    'NameCell', parent=getSampleStyleSheet()['Normal'],
                    fontSize=font_size,
                    fontName=font_name,
                    alignment=0,
                    wordWrap='CJK',  # Enable word wrap
                    leading=font_size + 2,  # Line height
                ))
                
                # UNIFIED: Create Volume and Satuan cells
                data_cell_style = ParagraphStyle(
                    'DataCell', parent=getSampleStyleSheet()['Normal'],
                    fontSize=font_size,
                    fontName=font_name,
                    alignment=2,  # RIGHT align
                )
                volume_cell = Paragraph(str(volume) if volume else '', data_cell_style)
                satuan_cell = Paragraph(str(satuan) if satuan else '', data_cell_style)
                
                # Create bar chart drawing for timeline area
                bar_drawing = create_bar_cell(
                    planned_weeks_list, 
                    actual_weeks_list, 
                    weeks_on_this_page + blank_cols,
                    WEEK_WIDTH_PT,
                    is_pekerjaan=is_pekerjaan
                )
                
                # UNIFIED: Row contains 3 static cells + bar drawing merged cell
                # [Uraian, Volume, Satuan, bar_drawing, '', '', ...]
                row_cells = [name_cell, volume_cell, satuan_cell, bar_drawing]
                
                # Pad with empty cells for remaining week columns (bar merges these)
                for _ in range(weeks_on_this_page + blank_cols - 1):
                    row_cells.append('')
                
                table_data.append(row_cells)
                hierarchy_row_styles.append((len(table_data) - 1, row_type))
            
            # =============================================
            # CREATE TABLE WITH BAR CHART STYLING
            # =============================================
            
            # Adjust column widths for merged bar area
            # First column = Uraian, Rest = individual week columns for header
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Styling from UTS
            header_bg = UTS.get_header_bg_color()
            border_color = UTS.get_inner_border_color()
            outer_border = UTS.get_outer_border_color()
            klasifikasi_bg = UTS.get_klasifikasi_bg_color()
            sub_klasifikasi_bg = UTS.get_sub_klasifikasi_bg_color()
            
            # Padding from UTS
            pad_top, pad_bottom, pad_left, pad_right = UTS.get_padding_tuple_mm()
            
            style_commands = [
                # Header row styling from UTS
                ('BACKGROUND', (0, 0), (-1, 0), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), UTS.get_header_text_color()),
                ('FONTNAME', (0, 0), (-1, 0), UTS.HEADER_FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, 0), UTS.HEADER_FONT_SIZE),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Data rows - merge week columns for bar display
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                
                # Borders from UTS - FULL GRID for visibility
                ('INNERGRID', (0, 0), (2, -1), 0.5, border_color),  # Grid for static columns
                ('LINEBELOW', (0, 0), (-1, 0), 1, outer_border),  # Header bottom
                ('BOX', (0, 0), (-1, -1), UTS.OUTER_BORDER_WIDTH, outer_border),  # Outer border
                # Horizontal lines for all rows (visible grid)
                ('LINEBELOW', (0, 1), (-1, -2), 0.3, border_color),  # All data rows
                
                # Padding from UTS
                ('TOPPADDING', (0, 0), (-1, -1), pad_top),
                ('BOTTOMPADDING', (0, 0), (-1, -1), pad_bottom),
                ('LEFTPADDING', (0, 0), (-1, -1), pad_left),
                ('RIGHTPADDING', (0, 0), (-1, -1), pad_right),
                
                # Row heights
                ('ROWHEIGHT', (0, 1), (-1, -1), ROW_HEIGHT),
            ]
            
            # Add hierarchy row background colors
            for row_idx, row_type in hierarchy_row_styles:
                if row_type == 'klasifikasi':
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), klasifikasi_bg))
                elif row_type == 'sub_klasifikasi':
                    style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), sub_klasifikasi_bg))
            
            # UNIFIED: Add line separators for static columns (after Uraian, Volume, Satuan)
            style_commands.append(('LINEBEFORE', (1, 0), (1, -1), 0.5, border_color))  # After Uraian
            style_commands.append(('LINEBEFORE', (2, 0), (2, -1), 0.5, border_color))  # After Volume
            style_commands.append(('LINEBEFORE', (3, 0), (3, -1), 0.5, border_color))  # After Satuan
            
            # Merge week columns in data rows for bar display (col 3 to end)
            # Column indices: 0=Uraian, 1=Volume, 2=Satuan, 3+=Weeks
            for row_idx in range(1, len(table_data)):
                if weeks_on_this_page + blank_cols > 1:
                    style_commands.append(
                        ('SPAN', (3, row_idx), (-1, row_idx))  # Merge all week columns (start from col 3)
                    )
            
            table.setStyle(TableStyle(style_commands))
            all_elements.append(table)
            
            # =============================================
            # LEGEND (only on last page)
            # =============================================
            if page_idx == num_pages - 1:
                legend_drawing = Drawing(360, 20)
                legend_drawing.add(Rect(10, 8, 40, 8, fillColor=planned_color, strokeColor=None))
                legend_drawing.add(String(55, 9, 'Planned (Rencana)', fontSize=8, fontName='Helvetica'))
                legend_drawing.add(Rect(180, 8, 40, 8, fillColor=actual_color, strokeColor=None))
                legend_drawing.add(String(225, 9, 'Actual (Realisasi)', fontSize=8, fontName='Helvetica'))
                
                all_elements.append(Spacer(1, 5*mm))
                all_elements.append(legend_drawing)
            
            # Add page break between pages (not after last page)
            if page_idx < num_pages - 1:
                all_elements.append(PageBreak())
        
        # END OF PAGINATION LOOP - return is OUTSIDE the loop
        return all_elements
    
    def _build_integrated_kurva_s_grid(
        self, 
        kurva_s_data: List[Dict], 
        pekerjaan_rows: List[Dict] = None,
        width: float = 700, 
        row_height: float = 18,
        max_weeks: int = 20
    ) -> Drawing:
        """
        Build table with Kurva S line overlay INSIDE the grid.
        
        Layout:
        - Y-axis: 0% at bottom row, 100% at top row (inverted)
        - X-axis: Each week column aligned with table grid
        - Kurva S line drawn OVER the table rows (true overlay)
        """
        if not kurva_s_data:
            return None
        
        # Sample weeks if too many
        total_weeks = len(kurva_s_data)
        if total_weeks > max_weeks:
            step = max(1, total_weeks // max_weeks)
            sampled_data = [kurva_s_data[i] for i in range(0, total_weeks, step)][:max_weeks]
        else:
            sampled_data = kurva_s_data
        
        num_weeks = len(sampled_data)
        
        # Default pekerjaan rows if not provided (progress bands)
        if not pekerjaan_rows:
            pekerjaan_rows = [
                {'name': '100%'}, {'name': '80%'}, {'name': '60%'},
                {'name': '40%'}, {'name': '20%'}, {'name': '0%'},
            ]
        
        num_rows = len(pekerjaan_rows)
        
        # Layout
        label_width = 80
        week_width = (width - label_width) / num_weeks
        table_height = (num_rows + 1) * row_height
        total_height = table_height + 40
        
        drawing = Drawing(width, total_height)
        
        # Table grid
        table_top = total_height - 25
        table_bottom = table_top - table_height
        
        # Header row
        header_y = table_top - row_height
        drawing.add(Rect(0, header_y, width, row_height,
                        fillColor=colors.HexColor(UTS.PRIMARY_LIGHT), strokeColor=colors.grey, strokeWidth=0.5))
        drawing.add(String(5, header_y + 5, 'Progress', fontSize=8, fontName='Helvetica-Bold', fillColor=colors.white))
        
        for i, data in enumerate(sampled_data):
            week_num = data.get('week', i + 1)
            x = label_width + i * week_width + week_width/2
            drawing.add(String(x, header_y + 5, f'W{week_num}', fontSize=6, fontName='Helvetica-Bold', 
                               fillColor=colors.white, textAnchor='middle'))
        
        # Data rows
        for row_idx, row in enumerate(pekerjaan_rows):
            row_y = header_y - (row_idx + 1) * row_height
            bg_color = colors.HexColor('#f8f9fa') if row_idx % 2 == 0 else colors.white
            drawing.add(Rect(0, row_y, label_width, row_height,
                            fillColor=bg_color, strokeColor=colors.lightgrey, strokeWidth=0.5))
            drawing.add(String(5, row_y + 5, row.get('name', ''), fontSize=7, fontName='Helvetica'))
            
            for i in range(num_weeks):
                x_start = label_width + i * week_width
                drawing.add(Rect(x_start, row_y, week_width, row_height,
                                fillColor=colors.white, strokeColor=colors.HexColor('#e8e8e8'), strokeWidth=0.3))
        
        # Kurva S overlay
        chart_top = header_y
        chart_bottom = table_bottom
        chart_height_calc = chart_top - chart_bottom
        
        def progress_to_y(progress):
            return chart_bottom + (progress / 100.0) * chart_height_calc
        
        def week_to_x(week_index):
            return label_width + week_index * week_width + week_width / 2
        
        # Planned curve
        week0_x = label_width
        week0_y = progress_to_y(0)
        planned_points = [(week0_x, week0_y)]
        for i, data in enumerate(sampled_data):
            planned_points.append((week_to_x(i), progress_to_y(data.get('planned', 0) or 0)))
        
        for j in range(len(planned_points) - 1):
            drawing.add(Line(planned_points[j][0], planned_points[j][1], 
                            planned_points[j+1][0], planned_points[j+1][1],
                            strokeColor=colors.HexColor(UTS.PLANNED_COLOR), strokeWidth=2.5))
        
        for x, y in planned_points:
            drawing.add(Rect(x-4, y-4, 8, 8, fillColor=colors.HexColor(UTS.PLANNED_COLOR), strokeColor=colors.white, strokeWidth=1))
        
        # Actual curve
        actual_points = [(week0_x, week0_y)]
        for i, data in enumerate(sampled_data):
            actual_points.append((week_to_x(i), progress_to_y(data.get('actual', 0) or 0)))
        
        for j in range(len(actual_points) - 1):
            drawing.add(Line(actual_points[j][0], actual_points[j][1], 
                            actual_points[j+1][0], actual_points[j+1][1],
                            strokeColor=colors.HexColor(UTS.ACTUAL_COLOR), strokeWidth=2.5))
        
        for x, y in actual_points:
            drawing.add(Rect(x-4, y-4, 8, 8, fillColor=colors.HexColor(UTS.ACTUAL_COLOR), strokeColor=colors.white, strokeWidth=1))
        
        # Title & Legend
        drawing.add(String(width/2, total_height - 10, 'KURVA S - Tabel dengan Overlay',
                          fontSize=10, fontName='Helvetica-Bold', textAnchor='middle'))
        
        legend_y = table_bottom - 20
        drawing.add(Rect(width/2 - 100, legend_y, 10, 8, fillColor=colors.HexColor(UTS.PLANNED_COLOR)))
        drawing.add(String(width/2 - 87, legend_y + 1, 'Planned', fontSize=7, fontName='Helvetica'))
        drawing.add(Rect(width/2, legend_y, 10, 8, fillColor=colors.HexColor(UTS.ACTUAL_COLOR)))
        drawing.add(String(width/2 + 13, legend_y + 1, 'Actual', fontSize=7, fontName='Helvetica'))
        
        return drawing

    def _build_monthly_kurva_s_table(
        self,
        pekerjaan_rows: List[Dict],
        kurva_s_data: List[Dict],
        all_weekly_columns: List[Dict],
        total_project_weeks: int,
        cumulative_end_week: int,
        row_height: float = 16,
        project_info: Dict[str, Any] = None
    ) -> List[Drawing]:
        """
        Build Monthly Kurva S table with ALL weeks, paginated across multiple A3 landscape pages.
        
        Layout requirements:
        - Columns: Uraian Pekerjaan, Volume, Satuan, + ALL weekly columns
        - Table shows ALL 50++ weeks (full project)
        - Chart (Kurva S line) drawn on every page (segmented)
        - Rows paginated across pages when exceeding height
        - Signature section embedded on last page
        
        Args:
            pekerjaan_rows: List of dicts with 'name', 'volume', 'satuan', 'level'
            kurva_s_data: List of dicts with 'week', 'planned', 'actual' (cumulative only)
            all_weekly_columns: All weekly columns for full project
            total_project_weeks: Total weeks in project (for table columns)
            cumulative_end_week: Week number where chart stops
            row_height: Height per row
            project_info: Dict with signature data (nama_kontraktor, nama_konsultan, etc.)
            
        Returns:
            List of Drawing objects (one per page)
        """
        if not pekerjaan_rows:
            return []
        
        # =================================================================
        # A3 LANDSCAPE DIMENSIONS
        # A3 = 420mm × 297mm = 1190pt × 842pt
        # Header zone: 8mm offset + 5mm text = ~37pt reserved at top
        # Footer zone: 6mm offset + 8mm text = ~40pt reserved at bottom
        # Usable height: 842 - 37 - 40 = ~765pt, use 720pt for safety
        # =================================================================
        page_width = 1100  # A3 Landscape usable width
        max_height = 720   # A3 Landscape usable height (was 773, reduced for header/footer)
        
        # Use ALL project weeks for table columns
        num_weeks = total_project_weeks if total_project_weeks > 0 else len(all_weekly_columns)
        total_rows = len(pekerjaan_rows)
        
        if num_weeks == 0:
            return []
        
        # =================================================================
        # COLUMN WIDTH CALCULATION
        # RULE: All weeks MUST fit on 1 sheet (no horizontal pagination)
        # Priority: Fit weeks first, then allocate remaining to static cols
        # =================================================================
        
        # Left margin for print safety (prevents cutoff)
        left_margin = 15  # 15pt margin from left edge
        effective_page_width = page_width - left_margin
        
        # Week column constraints
        min_week_width = 12  # Minimum for readability (~5pt font)
        max_week_width = 45  # Maximum to prevent excessive whitespace
        
        # Static columns: Only Uraian Pekerjaan (Volume/Satuan removed)
        min_uraian_width = 150   # Minimum for 2-line text ~25 chars
        max_uraian_width = 400   # Maximum when few weeks (prevent too wide)
        
        # Calculate ideal week width
        available_for_weeks = effective_page_width - min_uraian_width
        ideal_week_width = available_for_weeks / num_weeks if num_weeks > 0 else max_week_width
        
        # Apply week width constraints
        if ideal_week_width < min_week_width:
            # Not enough space - weeks at minimum, uraian shrinks
            week_width = min_week_width
            uraian_width = effective_page_width - (num_weeks * week_width)
            uraian_width = max(min_uraian_width, uraian_width)  # Floor at minimum
        elif ideal_week_width > max_week_width:
            # Plenty of space - weeks at maximum, uraian expands
            week_width = max_week_width
            uraian_width = effective_page_width - (num_weeks * week_width)
            uraian_width = min(max_uraian_width, uraian_width)  # Cap at maximum
        else:
            # Goldilocks zone - balanced allocation
            week_width = ideal_week_width
            uraian_width = effective_page_width - (num_weeks * week_width)
            uraian_width = max(min_uraian_width, min(max_uraian_width, uraian_width))
        
        static_total = uraian_width
        total_table_width = static_total + (num_weeks * week_width)
        
        # =================================================================
        # PAGINATION CALCULATION (ROWS ONLY)
        # Chart on every page (segmented), Signature on LAST page
        # =================================================================
        header_height = 20  # Row for column headers
        chart_overlay_height = 40  # Space above table for chart lines
        legend_height = 25  # Legend below table (first page only)
        signature_height = 140  # ~50mm for signature section (last page only)
        
        # First page: chart + legend
        first_page_row_space = max_height - header_height - chart_overlay_height - legend_height - 20
        # Middle pages: no legend, no signature
        middle_page_row_space = max_height - header_height - chart_overlay_height - 20
        # Last page: signature section (no legend)
        last_page_row_space = max_height - header_height - chart_overlay_height - signature_height - 20
        
        rows_per_first_page = int(first_page_row_space / row_height)
        rows_per_middle_page = int(middle_page_row_space / row_height)
        rows_per_last_page = int(last_page_row_space / row_height)
        
        # Calculate pages needed (accounting for reserved signature space on last page)
        if total_rows <= rows_per_first_page:
            # All fits on first page (which is also last page)
            # Need to recalculate with signature space
            first_and_last_row_space = max_height - header_height - chart_overlay_height - legend_height - signature_height - 20
            rows_per_single_page = int(first_and_last_row_space / row_height)
            if total_rows <= rows_per_single_page:
                num_pages = 1
            else:
                # Need 2 pages
                num_pages = 2
        else:
            # Calculate how many middle pages needed
            remaining_after_first = total_rows - rows_per_first_page
            
            # How many rows can fit on middle pages + last page?
            if remaining_after_first <= rows_per_last_page:
                num_pages = 2  # First + Last
            else:
                # Need middle pages
                remaining_after_last_reserved = remaining_after_first - rows_per_last_page
                middle_pages = max(0, (remaining_after_last_reserved + rows_per_middle_page - 1) // rows_per_middle_page)
                num_pages = 1 + middle_pages + 1  # First + Middle + Last
        
        # Colors from UTS
        header_bg = colors.HexColor(UTS.PRIMARY_LIGHT)
        header_text = colors.white
        klasifikasi_bg = colors.HexColor(UTS.KLASIFIKASI_BG)
        sub_klas_bg = colors.HexColor(UTS.SUB_KLASIFIKASI_BG)
        border_color = colors.HexColor('#cccccc')
        outer_border = colors.HexColor('#333333')
        
        # =================================================================
        # VIRTUAL FULL TABLE CONCEPT
        # Full table height: header + all rows
        # Chart spans from top (100%) to bottom (0%) of full table
        # Each page shows a "slice" of the full table + chart
        # =================================================================
        full_virtual_height = header_height + (total_rows * row_height)
        
        drawings = []
        
        for page_num in range(num_pages):
            is_first_page = (page_num == 0)
            is_last_page = (page_num == num_pages - 1)
            is_single_page = (num_pages == 1)
            
            # Calculate which rows are on this page
            if is_first_page:
                if is_single_page:
                    # Single page: first + last, use reduced row count
                    first_and_last_row_space = max_height - header_height - chart_overlay_height - legend_height - signature_height - 20
                    max_rows_single = int(first_and_last_row_space / row_height)
                    rows_this_page = min(max_rows_single, total_rows)
                else:
                    rows_this_page = min(rows_per_first_page, total_rows)
                global_row_start = 0
            elif is_last_page:
                # Last page (not first): fewer rows due to signature
                global_row_start = rows_per_first_page
                if num_pages > 2:
                    # Add middle pages rows
                    global_row_start += (num_pages - 2) * rows_per_middle_page
                rows_this_page = total_rows - global_row_start
            else:
                # Middle page
                global_row_start = rows_per_first_page + (page_num - 1) * rows_per_middle_page
                global_row_end = min(global_row_start + rows_per_middle_page, total_rows)
                rows_this_page = global_row_end - global_row_start
            
            if rows_this_page <= 0:
                break
            
            page_rows = pekerjaan_rows[global_row_start:global_row_start + rows_this_page]
            
            # Calculate page height - include signature space on last page
            table_height = header_height + (rows_this_page * row_height)
            legend_space = legend_height if is_first_page else 0
            sig_space = signature_height if is_last_page else 0
            page_total_height = table_height + chart_overlay_height + legend_space + sig_space + 10
            
            drawing = Drawing(total_table_width, page_total_height)
            
            # === Draw Table for this page ===
            table_top = page_total_height - chart_overlay_height - 5
            table_bottom = table_top - table_height
            
            # Outer border - with left margin offset
            drawing.add(Rect(left_margin, table_bottom, total_table_width, table_height,
                            fillColor=None, strokeColor=outer_border, strokeWidth=1.5))
            
            # Header row background
            header_y = table_top - header_height
            drawing.add(Rect(left_margin, header_y, total_table_width, header_height,
                            fillColor=header_bg, strokeColor=outer_border, strokeWidth=0.5))
            
            # Header text (larger fonts for A3) - with left margin offset
            drawing.add(String(left_margin + 5, header_y + 6, 'Uraian Pekerjaan',
                              fontSize=8, fontName='Helvetica-Bold', fillColor=header_text))
            
            # Week headers
            for i in range(num_weeks):
                if i < len(all_weekly_columns):
                    col = all_weekly_columns[i]
                    week_num = col.get('week_number', i + 1)
                else:
                    week_num = i + 1
                
                x = left_margin + static_total + (i * week_width) + week_width/2  # Add left_margin offset
                # Adaptive font size based on week_width
                week_font_size = 6 if week_width >= 15 else 5
                drawing.add(String(x, header_y + 6, f'W{week_num}',
                                  fontSize=week_font_size, fontName='Helvetica-Bold', 
                                  fillColor=header_text, textAnchor='middle'))
            
            # Data rows for this page
            for row_idx, row in enumerate(page_rows):
                row_y = header_y - (row_idx + 1) * row_height
                level = row.get('level', 3)
                row_type = row.get('type', 'pekerjaan')
                
                # Use helper for row styling
                bg_color, font_weight = self._get_row_styling(row_type, row_idx)
                
                # Uraian column - with left margin offset
                drawing.add(Rect(left_margin, row_y, uraian_width, row_height,
                                fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                
                # Use helper for text rendering
                raw_name = row.get('name', '') or row.get('uraian', '')
                self._render_uraian_text(
                    drawing=drawing,
                    raw_name=raw_name,
                    level=level,
                    uraian_width=uraian_width,
                    x=left_margin,
                    row_y=row_y,
                    row_height=row_height,
                    font_weight=font_weight
                )
                
                # Volume and Satuan columns REMOVED to give more space to Uraian
                
                # Week columns with progress values - using helper
                week_planned = row.get('week_planned', [])
                week_actual = row.get('week_actual', [])
                
                for i in range(num_weeks):
                    x = left_margin + static_total + (i * week_width)
                    week_num = i + 1
                    
                    # Get planned/actual values if within cumulative range
                    planned_val = None
                    actual_val = None
                    if row_type == 'pekerjaan' and week_num <= cumulative_end_week:
                        planned_val = week_planned[i] if i < len(week_planned) else None
                        actual_val = week_actual[i] if i < len(week_actual) else None
                    
                    self._draw_week_cell(
                        drawing=drawing,
                        x=x,
                        row_y=row_y,
                        week_width=week_width,
                        row_height=row_height,
                        planned_val=planned_val,
                        actual_val=actual_val,
                        border_color=border_color
                    )
            
            # =================================================================
            # KURVA S CHART - Rendered on EVERY page (segmented)
            # Uses global Y coordinate system, then translated to page coordinates
            # =================================================================
            chart_weeks = min(len(kurva_s_data), cumulative_end_week)
            
            if chart_weeks > 0:
                # Global coordinates (virtual full table)
                # 100% at top of header (global Y = full_virtual_height)
                # 0% at bottom of last row (global Y = 0)
                
                def global_progress_to_y(progress):
                    """Map progress 0-100% to global virtual height"""
                    return (progress / 100.0) * full_virtual_height
                
                def global_y_to_page_y(global_y):
                    """Convert global Y to page Y coordinate, accounting for row offset"""
                    # global_row_start is the first row on this page
                    # Page Y coordinate system: table_top = header, going down
                    
                    # In global coords: row 0 bottom is at 0, row N-1 top is at full_virtual_height - header
                    # This page shows rows [global_row_start : global_row_start + rows_this_page]
                    
                    # Global Y for top of this page's data:
                    page_global_top = full_virtual_height - header_height - (global_row_start * row_height)
                    # Global Y for bottom of this page's data:
                    page_global_bottom = page_global_top - (rows_this_page * row_height)
                    
                    # Map global Y to page Y
                    # page_global_top -> table_top - header_height
                    # page_global_bottom -> table_bottom
                    
                    page_data_top = table_top - header_height
                    page_data_bottom = table_bottom
                    
                    if page_global_top == page_global_bottom:
                        return page_data_bottom
                    
                    # Linear interpolation
                    t = (global_y - page_global_bottom) / (page_global_top - page_global_bottom)
                    return page_data_bottom + t * (page_data_top - page_data_bottom)
                
                def week_to_x(week_idx):
                    return left_margin + static_total + (week_idx * week_width) + week_width / 2  # Add left_margin
                
                def clip_line_to_page(y1, y2, x1, x2, min_y, max_y):
                    """Clip a line segment to visible Y range, returns clipped coordinates or None"""
                    # Both points above or below visible area
                    if (y1 > max_y and y2 > max_y) or (y1 < min_y and y2 < min_y):
                        return None
                    
                    # Clip to visible area
                    clipped_y1, clipped_y2 = y1, y2
                    clipped_x1, clipped_x2 = x1, x2
                    
                    if y1 > max_y:
                        t = (max_y - y2) / (y1 - y2)
                        clipped_y1 = max_y
                        clipped_x1 = x2 + t * (x1 - x2)
                    elif y1 < min_y:
                        t = (min_y - y2) / (y1 - y2)
                        clipped_y1 = min_y
                        clipped_x1 = x2 + t * (x1 - x2)
                    
                    if y2 > max_y:
                        t = (max_y - y1) / (y2 - y1)
                        clipped_y2 = max_y
                        clipped_x2 = x1 + t * (x2 - x1)
                    elif y2 < min_y:
                        t = (min_y - y1) / (y2 - y1)
                        clipped_y2 = min_y
                        clipped_x2 = x1 + t * (x2 - x1)
                    
                    return (clipped_x1, clipped_y1, clipped_x2, clipped_y2)
                
                # Visible Y range for this page (chart should NOT overlap header)
                visible_min_y = table_bottom
                visible_max_y = table_top - header_height  # Stop at bottom of header, not top
                
                # Generate curve points in global coordinates, then convert to page coords
                # Week 0 starting point should be at left edge of W1 column
                week0_x = left_margin + static_total  # Fixed: was missing left_margin
                week0_global_y = global_progress_to_y(0)
                
                # Planned curve
                planned_global_points = [(week0_x, week0_global_y)]
                for i, data in enumerate(kurva_s_data[:chart_weeks]):
                    planned_val = data.get('planned', 0) or 0
                    planned_global_points.append((week_to_x(i), global_progress_to_y(planned_val)))
                
                # Convert to page coords and draw
                planned_page_points = [(x, global_y_to_page_y(y)) for x, y in planned_global_points]
                
                for j in range(len(planned_page_points) - 1):
                    x1, y1 = planned_page_points[j]
                    x2, y2 = planned_page_points[j+1]
                    
                    clipped = clip_line_to_page(y1, y2, x1, x2, visible_min_y, visible_max_y)
                    if clipped:
                        drawing.add(Line(clipped[0], clipped[1], clipped[2], clipped[3],
                                        strokeColor=colors.HexColor(UTS.PLANNED_COLOR), strokeWidth=2.5))
                
                # Draw planned markers (only if visible)
                for px, py in planned_page_points[1:]:
                    if visible_min_y <= py <= visible_max_y:
                        drawing.add(Rect(px-4, py-4, 8, 8, 
                                        fillColor=colors.HexColor(UTS.PLANNED_COLOR), 
                                        strokeColor=colors.white, strokeWidth=1))
                
                # Actual curve
                actual_global_points = [(week0_x, week0_global_y)]
                for i, data in enumerate(kurva_s_data[:chart_weeks]):
                    actual_val = data.get('actual', 0) or 0
                    actual_global_points.append((week_to_x(i), global_progress_to_y(actual_val)))
                
                # Convert to page coords and draw
                actual_page_points = [(x, global_y_to_page_y(y)) for x, y in actual_global_points]
                
                for j in range(len(actual_page_points) - 1):
                    x1, y1 = actual_page_points[j]
                    x2, y2 = actual_page_points[j+1]
                    
                    clipped = clip_line_to_page(y1, y2, x1, x2, visible_min_y, visible_max_y)
                    if clipped:
                        drawing.add(Line(clipped[0], clipped[1], clipped[2], clipped[3],
                                        strokeColor=colors.HexColor(UTS.ACTUAL_COLOR), strokeWidth=2.5))
                
                # Draw actual markers (only if visible)
                for ax, ay in actual_page_points[1:]:
                    if visible_min_y <= ay <= visible_max_y:
                        drawing.add(Rect(ax-4, ay-4, 8, 8, 
                                        fillColor=colors.HexColor(UTS.ACTUAL_COLOR), 
                                        strokeColor=colors.white, strokeWidth=1))
            
            # === Legend (only on first page) - positioned above table, aligned with week columns ===
            if is_first_page:
                # Position legend in chart overlay area, right side (aligned with week columns)
                legend_x = static_total + 10  # Start from week columns area
                legend_y_top = table_top + chart_overlay_height - 5  # Above table in chart area
                
                # Vertical layout (stacked)
                # Rencana line
                drawing.add(Rect(legend_x, legend_y_top - 8, 10, 8, 
                                fillColor=colors.HexColor(UTS.PLANNED_COLOR)))
                drawing.add(String(legend_x + 13, legend_y_top - 7, 'Rencana', 
                                  fontSize=7, fontName='Helvetica'))
                # Realisasi line (below Rencana)
                drawing.add(Rect(legend_x, legend_y_top - 20, 10, 8, 
                                fillColor=colors.HexColor(UTS.ACTUAL_COLOR)))
                drawing.add(String(legend_x + 13, legend_y_top - 19, 'Realisasi', 
                                  fontSize=7, fontName='Helvetica'))
            
            # Page indicator removed per user request
            # if not is_first_page and not is_last_page:
            #     drawing.add(String(total_table_width / 2, table_bottom - 10, 
            #                       f'(Halaman {page_num + 1} dari {num_pages})',
            #                       fontSize=7, fontName='Helvetica-Oblique',
            #                       textAnchor='middle', fillColor=colors.grey))
            
            # =================================================================
            # SIGNATURE SECTION REMOVED per user request
            # =================================================================
            
            drawings.append(drawing)
        
        return drawings

    def _build_portrait_kurva_s_chart(
        self,
        kurva_s_data: List[Dict],
        cumulative_end_week: int,
        hierarchy_rows: List[Dict] = None,
        summary: Dict[str, Any] = None,
        month: int = 1,
        project_info: Dict[str, Any] = None,
        planned_progress: Dict[str, Dict] = None,
        actual_progress: Dict[str, Dict] = None
    ) -> List[Drawing]:
        """
        Build Portrait mode Kurva S table with 4-week segment chart overlay.
        
        NEW Layout (A3 Portrait):
        - Table: Uraian, Volume, Satuan, Total Harga, Bobot, Week1-4
        - Kurva S overlay on week columns (4 weeks only for this month)
        - Pagination for rows, signature on last page
        
        Args:
            kurva_s_data: Cumulative Kurva S data
            cumulative_end_week: Final week for chart (for reference)
            hierarchy_rows: ALL data rows (klasifikasi, sub, pekerjaan)
            summary: Executive summary data
            month: Month number (1=Week 1-4, 2=Week 5-8, etc.)
            project_info: For signature section
            
        Returns:
            List of Drawing objects (one per page)
        """
        if not hierarchy_rows:
            return []
        
        # =================================================================
        # A3 PORTRAIT DIMENSIONS
        # A3 = 297mm × 420mm = 842pt × 1190pt
        # Header zone: 8mm offset + 5mm text = ~37pt reserved at top
        # Footer zone: 6mm offset + 8mm text = ~40pt reserved at bottom
        # Usable height: 1190 - 37 - 40 = ~1113pt, use 1000pt for safety
        # =================================================================
        page_width = 750  # Safe A3 portrait width
        max_height = 1000  # A3 portrait usable height (was 1050, reduced for header/footer)
        
        # Calculate which 4 weeks to show for this month
        week_start = (month - 1) * 4  # 0-indexed
        week_end = week_start + 4
        weeks_this_month = [week_start + 1, week_start + 2, week_start + 3, week_start + 4]
        
        total_rows = len(hierarchy_rows)
        if total_rows == 0:
            return []
        
        # =================================================================
        # COLUMN WIDTHS (fixed for portrait)
        # Total: 750pt for A3 Portrait
        # =================================================================
        uraian_width = 350      # Reduced from 450 to make room for progress columns
        volume_width = 25
        satuan_width = 25
        harga_width = 65
        bobot_width = 30
        progress_lalu_width = 45  # NEW: Progress Bulan Lalu
        progress_ini_width = 45   # NEW: Progress Bulan Ini
        week_width = 25
        num_weeks = 4
        
        static_total = uraian_width + volume_width + satuan_width + harga_width + bobot_width + progress_lalu_width + progress_ini_width
        weeks_total = num_weeks * week_width  # 140pt
        total_table_width = static_total + weeks_total  # 750pt
        
        # =================================================================
        # PAGINATION CALCULATION
        # =================================================================
        row_height = 25  # 2-line text support
        header_height = 20
        chart_overlay_height = 30
        legend_height = 25
        signature_height = 140
        
        # First page: fewer rows due to title area
        first_page_row_space = max_height - header_height - chart_overlay_height - legend_height - 50
        middle_page_row_space = max_height - header_height - chart_overlay_height - 30
        last_page_row_space = max_height - header_height - chart_overlay_height - signature_height - 30
        
        rows_per_first_page = int(first_page_row_space / row_height)
        rows_per_middle_page = int(middle_page_row_space / row_height)
        rows_per_last_page = int(last_page_row_space / row_height)
        
        # Calculate pages needed
        if total_rows <= rows_per_first_page:
            first_and_last_space = max_height - header_height - chart_overlay_height - legend_height - signature_height - 50
            rows_per_single = int(first_and_last_space / row_height)
            num_pages = 1 if total_rows <= rows_per_single else 2
        else:
            remaining = total_rows - rows_per_first_page
            if remaining <= rows_per_last_page:
                num_pages = 2
            else:
                remaining -= rows_per_last_page
                middle_pages = max(0, (remaining + rows_per_middle_page - 1) // rows_per_middle_page)
                num_pages = 1 + middle_pages + 1
        
        # Colors
        header_bg = colors.HexColor(UTS.PRIMARY_LIGHT)
        header_text = colors.white
        klasifikasi_bg = colors.HexColor(UTS.KLASIFIKASI_BG)
        sub_klas_bg = colors.HexColor(UTS.SUB_KLASIFIKASI_BG)
        border_color = colors.HexColor('#cccccc')
        outer_border = colors.HexColor('#333333')
        planned_color = colors.HexColor(UTS.PLANNED_COLOR)
        actual_color = colors.HexColor(UTS.ACTUAL_COLOR)
        
        # Get Kurva S data for the 4 weeks of this month
        month_kurva_data = kurva_s_data[week_start:week_end] if kurva_s_data else []
        
        # Full virtual table for chart Y calculation
        full_virtual_height = header_height + (total_rows * row_height)
        
        drawings = []
        
        for page_num in range(num_pages):
            is_first_page = (page_num == 0)
            is_last_page = (page_num == num_pages - 1)
            is_single_page = (num_pages == 1)
            
            # Calculate rows for this page
            if is_first_page:
                if is_single_page:
                    max_rows_single = int((max_height - header_height - chart_overlay_height - legend_height - signature_height - 50) / row_height)
                    rows_this_page = min(max_rows_single, total_rows)
                else:
                    rows_this_page = min(rows_per_first_page, total_rows)
                global_row_start = 0
            elif is_last_page:
                global_row_start = rows_per_first_page
                if num_pages > 2:
                    global_row_start += (num_pages - 2) * rows_per_middle_page
                rows_this_page = total_rows - global_row_start
            else:
                global_row_start = rows_per_first_page + (page_num - 1) * rows_per_middle_page
                rows_this_page = min(rows_per_middle_page, total_rows - global_row_start)
            
            if rows_this_page <= 0:
                break
            
            page_rows = hierarchy_rows[global_row_start:global_row_start + rows_this_page]
            
            # Calculate page height
            table_height = header_height + (rows_this_page * row_height)
            legend_space = legend_height if is_first_page else 0
            sig_space = signature_height if is_last_page else 0
            title_space = 40 if is_first_page else 10
            page_total_height = table_height + chart_overlay_height + legend_space + sig_space + title_space + 10
            
            drawing = Drawing(total_table_width, page_total_height)
            
            # === Title (first page only) ===
            if is_first_page:
                drawing.add(String(total_table_width / 2, page_total_height - 15,
                                  f'KURVA S - BULAN {month} (Minggu {weeks_this_month[0]} - {weeks_this_month[3]})',
                                  fontSize=12, fontName='Helvetica-Bold',
                                  textAnchor='middle', fillColor=colors.HexColor(UTS.PRIMARY_LIGHT)))
            
            # === Draw Table ===
            table_top = page_total_height - title_space - chart_overlay_height
            table_bottom = table_top - table_height
            
            # Outer border
            drawing.add(Rect(0, table_bottom, total_table_width, table_height,
                            fillColor=None, strokeColor=outer_border, strokeWidth=1.5))
            
            # Header row
            header_y = table_top - header_height
            drawing.add(Rect(0, header_y, total_table_width, header_height,
                            fillColor=header_bg, strokeColor=outer_border, strokeWidth=0.5))
            
            # Header text
            x_pos = 3
            drawing.add(String(x_pos, header_y + 6, 'Uraian Pekerjaan', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text))
            # Center-aligned headers
            x_pos = uraian_width + volume_width/2
            drawing.add(String(x_pos, header_y + 6, 'Vol', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            x_pos = uraian_width + volume_width + satuan_width/2
            drawing.add(String(x_pos, header_y + 6, 'Sat', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            x_pos = uraian_width + volume_width + satuan_width + harga_width/2
            drawing.add(String(x_pos, header_y + 6, 'Total Harga', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            x_pos = uraian_width + volume_width + satuan_width + harga_width + bobot_width/2
            drawing.add(String(x_pos, header_y + 6, 'Bobot', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            # NEW: Progress columns
            x_pos = uraian_width + volume_width + satuan_width + harga_width + bobot_width + progress_lalu_width/2
            drawing.add(String(x_pos, header_y + 6, 'Prog. Lalu', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            x_pos = uraian_width + volume_width + satuan_width + harga_width + bobot_width + progress_lalu_width + progress_ini_width/2
            drawing.add(String(x_pos, header_y + 6, 'Prog. Ini', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            
            # Week headers
            for i, wk in enumerate(weeks_this_month):
                x = static_total + (i * week_width) + week_width/2
                drawing.add(String(x, header_y + 6, f'W{wk}', fontSize=7, fontName='Helvetica-Bold', fillColor=header_text, textAnchor='middle'))
            
            # Data rows
            for row_idx, row in enumerate(page_rows):
                row_y = header_y - (row_idx + 1) * row_height
                level = row.get('level', 3)
                row_type = row.get('type', 'pekerjaan')
                
                # Use helper for row styling
                bg_color, font_weight = self._get_row_styling(row_type, row_idx)
                
                # Uraian column - use 'name' or 'uraian' (same as Rincian Progress)
                drawing.add(Rect(0, row_y, uraian_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                
                # Use helper for text rendering (with smaller padding for Portrait A3)
                raw_name = row.get('name', '') or row.get('uraian', '')
                self._render_uraian_text(
                    drawing=drawing,
                    raw_name=raw_name,
                    level=level,
                    uraian_width=uraian_width,
                    x=0,  # No left margin offset in this table
                    row_y=row_y,
                    row_height=row_height,
                    font_weight=font_weight,
                    padding_left=2,  # Smaller padding for this table
                    padding_right=2
                )
                
                # Volume - center aligned
                drawing.add(Rect(uraian_width, row_y, volume_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                if row_type == 'pekerjaan':
                    vol = row.get('volume', 0) or 0
                    try:
                        vol_str = f"{float(vol):.1f}" if vol else ''
                    except (ValueError, TypeError):
                        vol_str = str(vol)[:5]
                    drawing.add(String(uraian_width + volume_width/2, row_y + row_height * 0.35, vol_str[:5], fontSize=7, fontName='Helvetica', textAnchor='middle'))
                
                # Satuan - center aligned
                drawing.add(Rect(uraian_width + volume_width, row_y, satuan_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                if row_type == 'pekerjaan':
                    sat = row.get('satuan', '') or ''
                    drawing.add(String(uraian_width + volume_width + satuan_width/2, row_y + row_height * 0.35, str(sat)[:4], fontSize=7, fontName='Helvetica', textAnchor='middle'))
                
                # Total Harga - hierarchy_progress uses 'harga' directly
                drawing.add(Rect(uraian_width + volume_width + satuan_width, row_y, harga_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                if row_type == 'pekerjaan':
                    try:
                        harga = float(row.get('harga', 0) or 0)
                    except (ValueError, TypeError):
                        harga = 0
                    if harga > 0:
                        harga_fmt = f"Rp{int(harga):,}".replace(',', '.')
                        drawing.add(String(uraian_width + volume_width + satuan_width + harga_width/2, row_y + row_height * 0.35, harga_fmt[:14], fontSize=7, fontName='Helvetica', textAnchor='middle'))
                
                # Bobot - hierarchy_progress uses 'bobot' directly
                drawing.add(Rect(uraian_width + volume_width + satuan_width + harga_width, row_y, bobot_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                if row_type == 'pekerjaan':
                    try:
                        bobot = float(row.get('bobot', 0) or 0)
                    except (ValueError, TypeError):
                        bobot = 0
                    if bobot > 0:
                        drawing.add(String(uraian_width + volume_width + satuan_width + harga_width + bobot_width/2, row_y + row_height * 0.35, f"{bobot:.1f}%", fontSize=7, fontName='Helvetica', textAnchor='middle'))
                
                # Progress Bulan Lalu
                progress_lalu_x = uraian_width + volume_width + satuan_width + harga_width + bobot_width
                drawing.add(Rect(progress_lalu_x, row_y, progress_lalu_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                if row_type == 'pekerjaan':
                    try:
                        prog_lalu = float(row.get('progress_bulan_lalu', 0) or 0)
                    except (ValueError, TypeError):
                        prog_lalu = 0
                    if prog_lalu > 0:
                        drawing.add(String(progress_lalu_x + progress_lalu_width/2, row_y + row_height * 0.35, f"{prog_lalu:.1f}%", fontSize=7, fontName='Helvetica', textAnchor='middle'))
                
                # Progress Bulan Ini
                progress_ini_x = progress_lalu_x + progress_lalu_width
                drawing.add(Rect(progress_ini_x, row_y, progress_ini_width, row_height, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.3))
                if row_type == 'pekerjaan':
                    try:
                        prog_ini = float(row.get('progress_bulan_ini', 0) or 0)
                    except (ValueError, TypeError):
                        prog_ini = 0
                    if prog_ini > 0:
                        drawing.add(String(progress_ini_x + progress_ini_width/2, row_y + row_height * 0.35, f"{prog_ini:.1f}%", fontSize=7, fontName='Helvetica', textAnchor='middle'))
                
                # Week columns with progress values - with enhanced borders
                # Get row identifier for progress lookup
                row_id = str(row.get('id', row.get('pekerjaan_id', '')))
                
                def safe_float(val):
                    """Safely convert value to float, handling empty strings."""
                    if val is None or val == '':
                        return 0.0
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0
                
                # Week cell color - slightly different to distinguish
                week_bg = bg_color
                week_border = colors.HexColor('#666666')  # Darker border for week columns
                
                for i in range(num_weeks):
                    week_x = static_total + (i * week_width)
                    # Thicker inner vertical grid (0.8pt)
                    drawing.add(Rect(week_x, row_y, week_width, row_height, fillColor=week_bg, strokeColor=week_border, strokeWidth=0.8))
                    
                    if row_type == 'pekerjaan':
                        week_num = week_start + i + 1  # weeks are 1-indexed
                        
                        # Look up progress from dicts 
                        # Adapter format: "{pekerjaan_id}-{week_number}" -> value (flat key)
                        # Or gantt_data format: {pekerjaan_id: {week_num: value}} (nested)
                        planned_val = 0.0
                        actual_val = 0.0
                        
                        if planned_progress and row_id:
                            # Try flat key format first (adapter planned_map)
                            flat_key = f"{row_id}-{week_num}"
                            if flat_key in planned_progress:
                                planned_val = safe_float(planned_progress.get(flat_key, 0))
                            else:
                                # Fallback to nested dict format (gantt_data)
                                row_planned = planned_progress.get(row_id, {})
                                if isinstance(row_planned, dict):
                                    planned_val = safe_float(row_planned.get(week_num, 0))
                        
                        if actual_progress and row_id:
                            # Try flat key format first (adapter actual_map)
                            flat_key = f"{row_id}-{week_num}"
                            if flat_key in actual_progress:
                                actual_val = safe_float(actual_progress.get(flat_key, 0))
                            else:
                                # Fallback to nested dict format (gantt_data)
                                row_actual = actual_progress.get(row_id, {})
                                if isinstance(row_actual, dict):
                                    actual_val = safe_float(row_actual.get(week_num, 0))
                        
                        if planned_val or actual_val:
                            cell_center = week_x + week_width / 2
                            if planned_val:
                                drawing.add(String(cell_center, row_y + row_height * 0.65, f"{planned_val:.1f}%", fontSize=5, fontName='Helvetica', textAnchor='middle', fillColor=planned_color))
                            if actual_val:
                                drawing.add(String(cell_center, row_y + row_height * 0.25, f"{actual_val:.1f}%", fontSize=5, fontName='Helvetica', textAnchor='middle', fillColor=actual_color))
            
            # === Draw thick outer border around entire week columns area ===
            week_area_x = static_total
            week_area_width = num_weeks * week_width
            week_area_top = table_top
            week_area_bottom = table_bottom
            thick_border = colors.HexColor('#333333')  # Dark border
            # Draw outer rectangle (no fill, just stroke)
            drawing.add(Rect(week_area_x, week_area_bottom, week_area_width, week_area_top - week_area_bottom,
                           fillColor=None, strokeColor=thick_border, strokeWidth=1.5))
            
            # === Kurva S Chart Overlay (on week columns only) ===
            if len(month_kurva_data) > 0:
                # Chart coordinate conversion for this month's segment
                def global_progress_to_y(progress):
                    return (progress / 100.0) * full_virtual_height
                
                def global_y_to_page_y(global_y):
                    page_global_top = full_virtual_height - header_height - (global_row_start * row_height)
                    page_global_bottom = page_global_top - (rows_this_page * row_height)
                    page_data_top = table_top - header_height
                    page_data_bottom = table_bottom
                    if page_global_top == page_global_bottom:
                        return page_data_bottom
                    t = (global_y - page_global_bottom) / (page_global_top - page_global_bottom)
                    return page_data_bottom + t * (page_data_top - page_data_bottom)
                
                def week_to_x(week_idx_in_month):
                    return static_total + (week_idx_in_month * week_width) + week_width / 2
                
                visible_min_y = table_bottom
                visible_max_y = table_top - header_height
                
                def clip_line_to_page(y1, y2, x1, x2, min_y, max_y):
                    if (y1 > max_y and y2 > max_y) or (y1 < min_y and y2 < min_y):
                        return None
                    clipped_y1, clipped_y2, clipped_x1, clipped_x2 = y1, y2, x1, x2
                    if y1 > max_y:
                        t = (max_y - y2) / (y1 - y2)
                        clipped_y1, clipped_x1 = max_y, x2 + t * (x1 - x2)
                    elif y1 < min_y:
                        t = (min_y - y2) / (y1 - y2)
                        clipped_y1, clipped_x1 = min_y, x2 + t * (x1 - x2)
                    if y2 > max_y:
                        t = (max_y - y1) / (y2 - y1)
                        clipped_y2, clipped_x2 = max_y, x1 + t * (x2 - x1)
                    elif y2 < min_y:
                        t = (min_y - y1) / (y2 - y1)
                        clipped_y2, clipped_x2 = min_y, x1 + t * (x2 - x1)
                    return (clipped_x1, clipped_y1, clipped_x2, clipped_y2)
                
                # Start from previous month's end value (or 0 if month 1)
                if week_start > 0 and week_start <= len(kurva_s_data):
                    prev_planned = kurva_s_data[week_start - 1].get('planned', 0) or 0
                    prev_actual = kurva_s_data[week_start - 1].get('actual', 0) or 0
                else:
                    prev_planned, prev_actual = 0, 0
                
                start_x = static_total
                start_y_planned = global_y_to_page_y(global_progress_to_y(prev_planned))
                start_y_actual = global_y_to_page_y(global_progress_to_y(prev_actual))
                
                # Planned curve
                planned_points = [(start_x, start_y_planned)]
                for i, data in enumerate(month_kurva_data):
                    planned_val = data.get('planned', 0) or 0
                    planned_points.append((week_to_x(i), global_y_to_page_y(global_progress_to_y(planned_val))))
                
                for j in range(len(planned_points) - 1):
                    x1, y1 = planned_points[j]
                    x2, y2 = planned_points[j + 1]
                    clipped = clip_line_to_page(y1, y2, x1, x2, visible_min_y, visible_max_y)
                    if clipped:
                        drawing.add(Line(clipped[0], clipped[1], clipped[2], clipped[3], strokeColor=planned_color, strokeWidth=2))
                
                for px, py in planned_points[1:]:
                    if visible_min_y <= py <= visible_max_y:
                        drawing.add(Rect(px-3, py-3, 6, 6, fillColor=planned_color, strokeColor=colors.white, strokeWidth=1))
                
                # Actual curve
                actual_points = [(start_x, start_y_actual)]
                for i, data in enumerate(month_kurva_data):
                    actual_val = data.get('actual', 0) or 0
                    actual_points.append((week_to_x(i), global_y_to_page_y(global_progress_to_y(actual_val))))
                
                for j in range(len(actual_points) - 1):
                    x1, y1 = actual_points[j]
                    x2, y2 = actual_points[j + 1]
                    clipped = clip_line_to_page(y1, y2, x1, x2, visible_min_y, visible_max_y)
                    if clipped:
                        drawing.add(Line(clipped[0], clipped[1], clipped[2], clipped[3], strokeColor=actual_color, strokeWidth=2))
                
                for ax, ay in actual_points[1:]:
                    if visible_min_y <= ay <= visible_max_y:
                        drawing.add(Rect(ax-3, ay-3, 6, 6, fillColor=actual_color, strokeColor=colors.white, strokeWidth=1))
            
            # === Legend (first page only) - positioned above table, aligned with week columns ===
            if is_first_page:
                # Position legend in chart overlay area, right side (aligned with week columns)
                legend_x = static_total + 10  # Start from week columns area
                legend_y_top = table_top + chart_overlay_height - 5  # Above table in chart area
                
                # Vertical layout (stacked)
                # Rencana line
                drawing.add(Rect(legend_x, legend_y_top - 8, 10, 8, fillColor=planned_color))
                drawing.add(String(legend_x + 13, legend_y_top - 7, 'Rencana', fontSize=7, fontName='Helvetica'))
                # Realisasi line (below Rencana)
                drawing.add(Rect(legend_x, legend_y_top - 20, 10, 8, fillColor=actual_color))
                drawing.add(String(legend_x + 13, legend_y_top - 19, 'Realisasi', fontSize=7, fontName='Helvetica'))
            
            # === Signature section REMOVED per user request ===
            
            drawings.append(drawing)
        
        return drawings
    
    def _build_pekerjaan_table_with_kurva_overlay(
        self, 
        page_data: Dict[str, Any],
        kurva_s_data: List[Dict],
        width: float = 700, 
        row_height: float = 16,
        max_weeks: int = 20
    ) -> Drawing:
        """
        Build pekerjaan table (from planned_pages) with Kurva S line overlay.
        
        This replicates browser behavior: Kurva S line drawn OVER the actual
        pekerjaan data table, not a separate visualization.
        
        Y-axis: 0% = bottom row, 100% = top row (inverted)
        X-axis: Each week column center
        """
        if not page_data or not kurva_s_data:
            return None
        
        table_data = page_data.get('table_data', {})
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        if not headers or not rows:
            return None
        
        # Parse headers: first column is Uraian, rest are weeks
        uraian_header = headers[0] if headers else 'Uraian'
        week_headers = headers[1:] if len(headers) > 1 else []
        
        # Limit weeks if too many
        if len(week_headers) > max_weeks:
            week_headers = week_headers[:max_weeks]
        
        num_weeks = len(week_headers)
        num_rows = len(rows)
        
        if num_weeks == 0 or num_rows == 0:
            return None
        
        # Layout calculations
        label_width = 120
        week_width = (width - label_width) / num_weeks
        table_height = (num_rows + 1) * row_height  # +1 for header
        total_height = table_height + 50  # margin for title and legend
        
        drawing = Drawing(width, total_height)
        
        # ============================================
        # PART 1: Draw Table Grid with Pekerjaan Data
        # ============================================
        
        table_top = total_height - 25
        table_bottom = table_top - table_height
        
        # Header row
        header_y = table_top - row_height
        drawing.add(Rect(0, header_y, width, row_height,
                        fillColor=colors.HexColor(UTS.PRIMARY_LIGHT), strokeColor=colors.grey, strokeWidth=0.5))
        
        # Header: Uraian column
        drawing.add(String(5, header_y + 4, uraian_header[:15], fontSize=7, fontName='Helvetica-Bold', fillColor=colors.white))
        
        # Header: Week columns
        for i, week_header in enumerate(week_headers):
            x = label_width + i * week_width + week_width/2
            # Truncate header if too long
            header_text = str(week_header)[:4] if len(str(week_header)) > 4 else str(week_header)
            drawing.add(String(x, header_y + 4, header_text, fontSize=5, fontName='Helvetica-Bold', 
                               fillColor=colors.white, textAnchor='middle'))
        
        # Data rows (pekerjaan)
        for row_idx, row in enumerate(rows):
            row_y = header_y - (row_idx + 1) * row_height
            
            # Alternate row colors
            bg_color = colors.HexColor('#f8f9fa') if row_idx % 2 == 0 else colors.white
            
            # Label cell (first column - pekerjaan name)
            drawing.add(Rect(0, row_y, label_width, row_height,
                            fillColor=bg_color, strokeColor=colors.lightgrey, strokeWidth=0.5))
            label_text = str(row[0])[:20] if row else ''
            drawing.add(String(3, row_y + 4, label_text, fontSize=5, fontName='Helvetica'))
            
            # Week cells (remaining columns - progress values)
            for i in range(num_weeks):
                x_start = label_width + i * week_width
                drawing.add(Rect(x_start, row_y, week_width, row_height,
                                fillColor=colors.white, strokeColor=colors.HexColor('#e8e8e8'), strokeWidth=0.3))
                
                # Cell value if available
                if len(row) > i + 1:
                    cell_val = str(row[i + 1])[:5] if row[i + 1] else ''
                    drawing.add(String(x_start + week_width/2, row_y + 4, cell_val, 
                                      fontSize=4, fontName='Helvetica', textAnchor='middle'))
        
        # ============================================
        # PART 2: Draw Kurva S Lines (OVERLAY)
        # ============================================
        
        # Y-coordinate mapping: 0% = bottom of last data row, 100% = top of first data row
        chart_top = header_y  # Top of first data row (100%)
        chart_bottom = table_bottom  # Bottom of last data row (0%)
        chart_height_calc = chart_top - chart_bottom
        
        def progress_to_y(progress):
            """Map progress % to Y coordinate (inverted: 0% at bottom)"""
            return chart_bottom + (progress / 100.0) * chart_height_calc
        
        def week_to_x(week_index):
            """Map week index to X coordinate (center of column)"""
            return label_width + week_index * week_width + week_width / 2
        
        # Sample kurva_s_data if too many weeks
        sampled_data = kurva_s_data[:num_weeks] if len(kurva_s_data) > num_weeks else kurva_s_data
        
        # Week 0 starting point (left edge, 0%)
        week0_x = label_width
        week0_y = progress_to_y(0)
        
        # Draw Planned curve
        planned_points = [(week0_x, week0_y)]
        for i, data in enumerate(sampled_data):
            x = week_to_x(i)
            y = progress_to_y(data.get('planned', 0) or 0)
            planned_points.append((x, y))
        
        # Draw planned line segments
        for j in range(len(planned_points) - 1):
            drawing.add(Line(planned_points[j][0], planned_points[j][1], 
                            planned_points[j+1][0], planned_points[j+1][1],
                            strokeColor=colors.HexColor(UTS.PLANNED_COLOR), strokeWidth=2))
        
        # Draw planned markers
        for x, y in planned_points:
            drawing.add(Rect(x-3, y-3, 6, 6, fillColor=colors.HexColor(UTS.PLANNED_COLOR), 
                            strokeColor=colors.white, strokeWidth=1))
        
        # Draw Actual curve
        actual_points = [(week0_x, week0_y)]
        for i, data in enumerate(sampled_data):
            x = week_to_x(i)
            y = progress_to_y(data.get('actual', 0) or 0)
            actual_points.append((x, y))
        
        # Draw actual line segments
        for j in range(len(actual_points) - 1):
            drawing.add(Line(actual_points[j][0], actual_points[j][1], 
                            actual_points[j+1][0], actual_points[j+1][1],
                            strokeColor=colors.HexColor(UTS.ACTUAL_COLOR), strokeWidth=2))
        
        # Draw actual markers
        for x, y in actual_points:
            drawing.add(Rect(x-3, y-3, 6, 6, fillColor=colors.HexColor(UTS.ACTUAL_COLOR), 
                            strokeColor=colors.white, strokeWidth=1))
        
        # ============================================
        # PART 3: Title and Legend
        # ============================================
        
        # Title
        drawing.add(String(width/2, total_height - 10, 'KURVA S - Overlay pada Tabel Pekerjaan',
                          fontSize=10, fontName='Helvetica-Bold', textAnchor='middle'))
        
        # Legend (at bottom)
        legend_y = table_bottom - 18
        drawing.add(Rect(width/2 - 100, legend_y, 10, 8, fillColor=colors.HexColor(UTS.PLANNED_COLOR)))
        drawing.add(String(width/2 - 87, legend_y + 1, 'Planned', fontSize=7, fontName='Helvetica'))
        drawing.add(Rect(width/2, legend_y, 10, 8, fillColor=colors.HexColor(UTS.ACTUAL_COLOR)))
        drawing.add(String(width/2 + 13, legend_y + 1, 'Actual', fontSize=7, fontName='Helvetica'))
        
        return drawing
    
    def _build_kurva_s_paginated(
        self,
        pekerjaan_rows: List[Dict],
        kurva_s_data: List[Dict],
        total_weeks: int,
        row_height: float = 14,
        max_rows_per_page: int = 30
    ) -> List[Drawing]:
        """
        Build paginated Kurva S visualization with freeze columns.
        
        Features:
        - Freeze columns: Uraian (inc. hierarchy), Volume, Satuan
        - Grid line positioning: W0 at freeze/week boundary
        - Pagination: Splits weeks and rows across multiple pages
        
        Args:
            pekerjaan_rows: List of dicts with 'name', 'volume', 'satuan', 'level'
            kurva_s_data: List of dicts with 'week', 'planned', 'actual'
            total_weeks: Total number of weeks
            width: Page width in points
            row_height: Height per row
            max_weeks_per_page: Max week columns per page
            max_rows_per_page: Max data rows per page
            
        Returns:
            List of Drawing objects (one per page)
        """
        if not pekerjaan_rows or not kurva_s_data:
            return []
        
        # =============================================
        # UNIFIED LAYOUT using TableLayoutCalculator
        # =============================================
        layout_calc = TLC(self.config)
        actual_total_weeks = min(total_weeks, len(kurva_s_data))
        
        # Get layout values
        width = layout_calc.table_width
        max_weeks_per_page = layout_calc.max_weeks_per_page
        freeze_width = UTS.STATIC_TOTAL
        uraian_width = UTS.URAIAN_WIDTH
        volume_width = UTS.VOLUME_WIDTH
        satuan_width = UTS.SATUAN_WIDTH
        uraian_padding = 2
        week_column_width = UTS.WEEK_WIDTH
        
        # Determine weeks on first page
        weeks_on_page = min(actual_total_weeks, max_weeks_per_page)
        
        # =============================================
        # STYLING from UnifiedTableStyles
        # =============================================
        
        # Font sizes from UTS
        font_size_header = UTS.HEADER_FONT_SIZE
        font_size_data = UTS.DATA_FONT_SIZE
        font_size_week = UTS.WEEK_HEADER_FONT_SIZE
        
        # Colors from UTS
        header_bg_color = UTS.get_header_bg_color()
        header_text_color = UTS.get_header_text_color()
        row_even_color = UTS.get_sub_klasifikasi_bg_color()
        row_odd_color = colors.white
        klasifikasi_color = UTS.get_klasifikasi_bg_color()
        border_color = UTS.get_inner_border_color()
        outer_border_color = UTS.get_outer_border_color()
        
        # Border widths from UTS
        outer_border_width = UTS.OUTER_BORDER_WIDTH
        inner_border_width = UTS.INNER_BORDER_WIDTH
        
        # Kurva S line styling from UTS
        planned_color = UTS.get_planned_color()
        actual_color = UTS.get_actual_color()
        line_width = 2.5
        marker_radius = 4
        
        # Dynamic row height calculation for text wrapping
        base_row_height = 16
        line_height = 9  # Height per line of text
        
        # Max chars per line based on column width
        max_chars_per_line = 45
        
        def calculate_row_height(text):
            """Calculate row height based on text length for multi-line wrapping"""
            if not text:
                return base_row_height
            # Calculate how many lines the text will need
            lines = (len(text) // max_chars_per_line) + 1
            return max(base_row_height, 8 + (lines * line_height))  # 8pt padding + lines
        
        # Pagination calculations
        num_weeks = min(total_weeks, len(kurva_s_data))
        num_rows = len(pekerjaan_rows)
        
        week_chunks = []
        for start in range(0, num_weeks, max_weeks_per_page):
            end = min(start + max_weeks_per_page, num_weeks)
            week_chunks.append((start, end))
        
        row_chunks = []
        for start in range(0, num_rows, max_rows_per_page):
            end = min(start + max_rows_per_page, num_rows)
            row_chunks.append((start, end))
        
        pages = []
        total_pages = len(week_chunks) * len(row_chunks)
        page_num = 0
        
        for week_start, week_end in week_chunks:
            for row_start, row_end in row_chunks:
                page_num += 1
                
                # Current page data
                weeks_in_page = week_end - week_start
                page_kurva_data = kurva_s_data[week_start:week_end]
                page_rows = pekerjaan_rows[row_start:row_end]
                
                # Use fixed week width
                week_width = week_column_width
                
                # =============================================
                # UNIFIED: Add blank column padding (like Grid View/Gantt)
                # =============================================
                blank_cols = max_weeks_per_page - weeks_in_page
                total_weeks_rendered = weeks_in_page + blank_cols  # Always = max_weeks_per_page
                
                # Calculate FIXED table width (same as Grid View and Gantt)
                # total_table_width = freeze_width + (max_weeks_per_page * week_width)
                total_table_width = freeze_width + (total_weeks_rendered * week_width)
                
                # Apply remainder handling (like Grid View and Gantt)
                remainder = width - total_table_width
                if abs(remainder) <= 10:
                    total_table_width = width  # Expand to exact page width
                
                # Calculate dynamic table height based on text wrapping
                row_heights = [calculate_row_height(row.get('name', '')) for row in page_rows]
                header_row_height = 24  # Increased for 2-line week headers (WX + date range)
                table_height = header_row_height + sum(row_heights)
                total_height = table_height + 70  # Header + legend
                
                # Use FIXED table width (matches Grid View and Gantt)
                drawing = Drawing(total_table_width, total_height)
                
                # ============================================
                # PAGE HEADER (left-aligned like Input Progress and Gantt)
                # ============================================
                header_text = SHF.kurva_s(page_num, total_pages, week_start+1, week_end)
                drawing.add(String(0, total_height - 12, header_text,
                                  fontSize=SHF.FONT_SIZE, fontName=SHF.FONT_NAME, 
                                  textAnchor='start', fillColor=colors.black))
                
                # ============================================
                # DRAW TABLE WITH PROFESSIONAL STYLING
                # ============================================
                table_top = total_height - 30
                table_bottom = table_top - table_height
                
                # Outer border (professional thick border)
                drawing.add(Rect(0, table_bottom, total_table_width, table_height,
                                fillColor=None, strokeColor=outer_border_color, strokeWidth=outer_border_width))
                
                # Header row with professional color
                header_y = table_top - header_row_height
                drawing.add(Rect(0, header_y, total_table_width, header_row_height,
                                fillColor=header_bg_color, strokeColor=outer_border_color, strokeWidth=inner_border_width))
                
                # Freeze column headers with larger font
                drawing.add(String(uraian_padding + 2, header_y + 5, 'Uraian Pekerjaan', fontSize=font_size_header, 
                                  fontName='Helvetica-Bold', fillColor=header_text_color))
                drawing.add(String(uraian_width + 3, header_y + 10, 'Volume', fontSize=font_size_header,
                                  fontName='Helvetica-Bold', fillColor=header_text_color))
                drawing.add(String(uraian_width + volume_width + 3, header_y + 10, 'Satuan', fontSize=font_size_header,
                                  fontName='Helvetica-Bold', fillColor=header_text_color))
                
                # Week headers using WHF (WeekHeaderFormatter)
                for i in range(weeks_in_page):
                    week_num = week_start + i + 1
                    x = freeze_width + i * week_width + week_width/2
                    
                    # Get date range from data
                    week_data = page_kurva_data[i] if i < len(page_kurva_data) else {}
                    date_range = week_data.get('range', '')
                    
                    # Use WHF for consistent week header drawing
                    WHF.draw_on_canvas(drawing, x, header_y + 4, week_num, date_range, header_text_color)
                
                # Data rows with dynamic heights
                current_y = header_y
                row_y_positions = []  # Store Y positions for Kurva S overlay
                
                for row_idx, row in enumerate(page_rows):
                    row_h = row_heights[row_idx]
                    row_y = current_y - row_h
                    row_y_positions.append((row_y, row_h))
                    
                    level = row.get('level', 2)
                    
                    # Determine row color based on level (hierarchy styling)
                    if level == 1:  # Klasifikasi
                        bg_color = klasifikasi_color
                        font_style = 'Helvetica-Bold'
                    elif level == 2:  # Sub-klasifikasi
                        bg_color = row_even_color if row_idx % 2 == 0 else row_odd_color
                        font_style = 'Helvetica-Oblique'
                    else:  # Pekerjaan
                        bg_color = row_even_color if row_idx % 2 == 0 else row_odd_color
                        font_style = 'Helvetica'
                    
                    # Uraian column with indent and multi-line text wrap
                    drawing.add(Rect(0, row_y, uraian_width, row_h,
                                    fillColor=bg_color, strokeColor=border_color, strokeWidth=inner_border_width))
                    indent = (level - 1) * 10
                    name = str(row.get('name', ''))
                    
                    # Split text into multiple lines for wrapping
                    # Use max_chars based on column width, reduced by indent
                    text_max_chars = max_chars_per_line - (level * 3)  # Reduce chars based on indent
                    lines = []
                    temp_name = name
                    while temp_name:
                        if len(temp_name) <= text_max_chars:
                            lines.append(temp_name)
                            break
                        # Find last space within limit
                        split_idx = temp_name[:text_max_chars].rfind(' ')
                        if split_idx == -1:
                            split_idx = text_max_chars
                        lines.append(temp_name[:split_idx])
                        temp_name = temp_name[split_idx:].strip()
                        if len(lines) >= 3:  # Max 3 lines
                            if temp_name:
                                lines[-1] = lines[-1][:text_max_chars-3] + '...'
                            break
                    
                    # Draw each line with padding from border and proper font
                    for line_idx, line_text in enumerate(lines):
                        line_y = row_y + row_h - 7 - (line_idx * line_height)
                        drawing.add(String(uraian_padding + indent, line_y, line_text, 
                                          fontSize=font_size_data, fontName=font_style))
                    
                    # Volume column
                    drawing.add(Rect(uraian_width, row_y, volume_width, row_h,
                                    fillColor=bg_color, strokeColor=border_color, strokeWidth=inner_border_width))
                    vol = str(row.get('volume', ''))[:10]
                    drawing.add(String(uraian_width + 3, row_y + row_h/2 - 2, vol, 
                                      fontSize=font_size_data, fontName='Helvetica'))
                    
                    # Satuan column
                    drawing.add(Rect(uraian_width + volume_width, row_y, satuan_width, row_h,
                                    fillColor=bg_color, strokeColor=border_color, strokeWidth=inner_border_width))
                    sat = str(row.get('satuan', ''))[:8]
                    drawing.add(String(uraian_width + volume_width + 3, row_y + row_h/2 - 2, sat, 
                                      fontSize=font_size_data, fontName='Helvetica'))
                    
                    # Week columns with progress values (Planned & Actual)
                    week_planned_list = row.get('week_planned', [])
                    week_actual_list = row.get('week_actual', [])
                    
                    for i in range(weeks_in_page):
                        x_start = freeze_width + i * week_width
                        drawing.add(Rect(x_start, row_y, week_width, row_h,
                                        fillColor=row_odd_color, strokeColor=border_color, strokeWidth=inner_border_width))
                        
                        # Get progress values for this week (offset by week_start for pagination)
                        week_index = week_start + i
                        planned_val = week_planned_list[week_index] if week_index < len(week_planned_list) else ''
                        actual_val = week_actual_list[week_index] if week_index < len(week_actual_list) else ''
                        
                        # Only show for pekerjaan rows (level 3)
                        if level == 3:
                            x_center = x_start + week_width / 2
                            
                            # Helper to check if value is effectively 0%
                            def is_zero_percent(val):
                                if not val:
                                    return True
                                # Remove % and strip, also handle comma decimal (Indonesian locale)
                                val_clean = val.replace('%', '').replace(',', '.').strip()
                                try:
                                    return float(val_clean) == 0
                                except:
                                    return False
                            
                            # Display planned (teal color) on top - show "-" for 0%
                            if planned_val:
                                display_planned = '-' if is_zero_percent(planned_val) else planned_val
                                drawing.add(String(x_center, row_y + row_h - 6, display_planned, 
                                                  fontSize=4, fontName='Helvetica-Bold', 
                                                  fillColor=planned_color, textAnchor='middle'))
                            
                            # Display actual (amber color) on bottom - show "-" for 0%
                            if actual_val:
                                display_actual = '-' if is_zero_percent(actual_val) else actual_val
                                drawing.add(String(x_center, row_y + 2, display_actual, 
                                                  fontSize=4, fontName='Helvetica-Bold', 
                                                  fillColor=actual_color, textAnchor='middle'))
                    
                    current_y = row_y
                
                
                # ============================================
                # KURVA S OVERLAY
                # ============================================
                
                # Y-axis mapping: 0% at bottom, 100% at top
                chart_top = header_y
                chart_bottom = table_bottom
                chart_height = chart_top - chart_bottom
                
                def progress_to_y(progress):
                    return chart_bottom + (progress / 100.0) * chart_height
                
                # X-axis mapping: Week node on RIGHT edge of week column (grid line)
                # W0 = left edge of week area (grid line between freeze and W1)
                def week_to_x(week_idx):
                    """Week index 0 = right edge of week 1 column, etc."""
                    return freeze_width + (week_idx + 1) * week_width  # Right edge of column
                
                # Draw Planned curve (only weeks in this page)
                planned_points = []
                
                # On page 1: Start from 0% at left edge
                # On page 2+: Start from previous page's last value at left edge
                if week_start == 0:
                    # First page: start at 0%
                    planned_points.append((freeze_width, progress_to_y(0)))
                else:
                    # Subsequent pages: start at the value from the week BEFORE this page's range
                    # This is the last week of the previous page (week_start - 1)
                    prev_week_idx = week_start - 1
                    if prev_week_idx >= 0 and prev_week_idx < len(kurva_s_data):
                        prev_planned = kurva_s_data[prev_week_idx].get('planned', 0) or 0
                        planned_points.append((freeze_width, progress_to_y(prev_planned)))
                
                for i, data in enumerate(page_kurva_data):
                    x = week_to_x(i)  # Position at right edge of each week column
                    y = progress_to_y(data.get('planned', 0) or 0)
                    planned_points.append((x, y))
                
                # Draw planned lines with professional styling
                for j in range(len(planned_points) - 1):
                    drawing.add(Line(planned_points[j][0], planned_points[j][1],
                                    planned_points[j+1][0], planned_points[j+1][1],
                                    strokeColor=planned_color, strokeWidth=line_width))
                
                # Draw planned markers (circles)
                for x, y in planned_points:
                    drawing.add(Circle(x, y, marker_radius, fillColor=planned_color,
                                      strokeColor=colors.white, strokeWidth=1))
                
                # Draw Actual curve
                actual_points = []
                
                # Same logic for actual curve
                if week_start == 0:
                    actual_points.append((freeze_width, progress_to_y(0)))
                else:
                    prev_week_idx = week_start - 1
                    if prev_week_idx >= 0 and prev_week_idx < len(kurva_s_data):
                        prev_actual = kurva_s_data[prev_week_idx].get('actual', 0) or 0
                        actual_points.append((freeze_width, progress_to_y(prev_actual)))
                
                for i, data in enumerate(page_kurva_data):
                    x = week_to_x(i)
                    y = progress_to_y(data.get('actual', 0) or 0)
                    actual_points.append((x, y))
                
                # Draw actual lines with professional styling
                for j in range(len(actual_points) - 1):
                    drawing.add(Line(actual_points[j][0], actual_points[j][1],
                                    actual_points[j+1][0], actual_points[j+1][1],
                                    strokeColor=actual_color, strokeWidth=line_width))
                
                # Draw actual markers (circles)
                for x, y in actual_points:
                    drawing.add(Circle(x, y, marker_radius, fillColor=actual_color,
                                      strokeColor=colors.white, strokeWidth=1))
                
                # ============================================
                # LEGEND (at bottom) with professional styling
                # ============================================
                legend_y = table_bottom - 18
                # Planned legend
                drawing.add(Circle(width/2 - 75, legend_y + 4, 4, fillColor=planned_color, strokeColor=colors.white, strokeWidth=0.5))
                drawing.add(String(width/2 - 68, legend_y + 1, 'Planned', fontSize=7, fontName='Helvetica-Bold'))
                # Actual legend
                drawing.add(Circle(width/2 + 15, legend_y + 4, 4, fillColor=actual_color, strokeColor=colors.white, strokeWidth=0.5))
                drawing.add(String(width/2 + 22, legend_y + 1, 'Actual', fontSize=7, fontName='Helvetica-Bold'))
                
                pages.append(drawing)
        
        return pages

