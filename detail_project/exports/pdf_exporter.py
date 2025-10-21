
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
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """Export to PDF (supports single or multi-page payload)"""
        buffer = BytesIO()

        # Determine page size based on orientation
        orientation = getattr(self.config, 'page_orientation', 'landscape')
        if orientation == 'portrait':
            pagesize = A4
        else:
            pagesize = landscape(A4)

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
            page_w_mm = 210 if getattr(self.config, 'page_orientation', 'landscape') == 'portrait' else 297
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
        total_text = f"<font color='#2c3e50'><b>Total: Rp {pekerjaan.get('total', '0')}</b></font>"
        total_para = Paragraph(total_text, self.styles['normal'])
        story.append(total_para)
        story.append(Spacer(1, 3*mm))

        # Detail Table
        if section.get('has_details'):
            headers = detail_table.get('headers', [])
            widths_mm = list(detail_table.get('col_widths', []) or [])
            # Scale column widths to fit page orientation/margins
            try:
                page_w_mm = 210 if getattr(self.config, 'page_orientation', 'landscape') == 'portrait' else 297
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
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), self.config.font_size_header),
                ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor('#2c3e50')),

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
                    ('LINEABOVE', (0, current_row), (-1, current_row), 0.8, colors.HexColor('#2c3e50')),
                    ('LINEBELOW', (0, current_row), (-1, current_row), 0.8, colors.HexColor('#2c3e50')),
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
                    style_commands.append(('LINEABOVE', (0, current_row), (-1, current_row), thickness, colors.HexColor('#2c3e50')))
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
        
        return elements
