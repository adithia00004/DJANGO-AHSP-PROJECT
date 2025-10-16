
# =====================================================================
# FILE: detail_project/exports/pdf_exporter.py
# Copy this entire file
# =====================================================================

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, KeepTogether
)
from io import BytesIO
from typing import Dict, Any, List
from .base import ConfigExporterBase
from django.http import HttpResponse


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
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=6*mm,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ),
            'subtitle': ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=self.config.font_size_header,
                spaceAfter=3*mm,
                alignment=TA_CENTER
            ),
            'normal': ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=self.config.font_size_normal
            )
        }
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """Export to PDF (supports single or multi-page payload)"""
        buffer = BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
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

            # Main table
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
                if idx < len(pages) - 1:
                    story.append(PageBreak())
            # Keep footer + signatures together on last page
            if self.config.signature_config.enabled and pages:
                last = pages[-1]
                bundle = []
                if 'footer_rows' in last:
                    bundle.append(self._build_footer_table(last['footer_rows']))
                bundle.extend(self._build_signatures())
                story.append(KeepTogether(bundle))
        else:
            build_page(data)
            if self.config.signature_config.enabled:
                bundle = []
                if 'footer_rows' in data:
                    bundle.append(self._build_footer_table(data['footer_rows']))
                bundle.extend(self._build_signatures())
                story.append(KeepTogether(bundle))
        
        # Build PDF
        doc.build(story)
        
        # Create response
        pdf_content = buffer.getvalue()
        buffer.close()
        
        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.pdf"
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

        wrapped_rows = []
        for r in rows:
            if not isinstance(r, (list, tuple)):
                r = [r]
            wrapped = []
            for idx, cell in enumerate(r):
                if idx == 0:
                    wrapped.append(P(cell, bold=False, align='LEFT'))
                else:
                    wrapped.append(P(cell, bold=False, align='RIGHT' if idx >= len(r) - 3 else 'LEFT'))
            wrapped_rows.append(wrapped)

        header_cells = [P(h, bold=True, align='CENTER') for h in headers]
        full_data = [header_cells] + wrapped_rows
        
        # Create table
        table = Table(full_data, colWidths=col_widths or None, repeatRows=1)
        
        # Build style commands
        style_commands = [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTSIZE', (0, 0), (-1, 0), self.config.font_size_header),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Default data rows
            ('FONTSIZE', (0, 1), (-1, -1), self.config.font_size_normal),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 1.5*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1.5*mm),
        ]
        
        # Apply hierarchy styling (only when provided)
        for idx, level in hierarchy.items():
            row_num = idx + 1  # +1 because of header row
            
            if level == 1:  # Klasifikasi
                style_commands.extend([
                    ('BACKGROUND', (0, row_num), (-1, row_num), 
                     colors.HexColor('#e8e8e8')),
                    ('TEXTCOLOR', (0, row_num), (-1, row_num), colors.black),
                    ('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, row_num), (-1, row_num), self.config.font_size_normal),
                ])
            elif level == 2:  # Sub-Klasifikasi
                style_commands.extend([
                    ('BACKGROUND', (0, row_num), (-1, row_num), 
                     colors.HexColor('#f5f5f5')),
                    ('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'),
                ])
        
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
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#2c3e50')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2c3e50')),
        ]))
        
        return table
    
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
        
        return elements
