# =====================================================================
# FILE: detail_project/exports/word_exporter.py
# Copy this entire file
# =====================================================================

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
from typing import Dict, Any, List
from .base import BaseExporter


class WordExporter(BaseExporter):
    """Word Export handler with python-docx"""
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """Export to Word document"""
        doc = Document()
        
        # Set landscape orientation
        section = doc.sections[0]
        section.page_width = Cm(29.7)
        section.page_height = Cm(21.0)
        section.top_margin = Cm(self.config.margin_top / 10)
        section.bottom_margin = Cm(self.config.margin_bottom / 10)
        section.left_margin = Cm(self.config.margin_left / 10)
        section.right_margin = Cm(self.config.margin_right / 10)
        
        # Add header
        self._add_header(doc)
        
        # Add table
        self._add_table(doc, data)
        
        # Add footer totals if present
        if 'footer_rows' in data:
            self._add_footer_totals(doc, data['footer_rows'])
        
        # Add signatures
        if self.config.signature_config.enabled:
            self._add_signatures(doc)
        
        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        filename = f"{self.config.title.replace(' ', '_')}_{self.config.export_date.strftime('%Y%m%d')}.docx"
        return self._create_response(
            buffer.getvalue(), 
            filename, 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    
    def _add_header(self, doc: Document):
        """Add document header"""
        # Title
        title = doc.add_heading(self.config.title, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Project info table
        info_table = doc.add_table(rows=4, cols=3)
        info_table.style = 'Light Grid'
        
        info_data = [
            ('Nama Proyek', ':', self.config.project_name),
            ('Kode Proyek', ':', self.config.project_code),
            ('Lokasi', ':', self.config.location),
            ('Tahun Anggaran', ':', self.config.year),
        ]
        
        for i, (label, sep, value) in enumerate(info_data):
            row = info_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = sep
            row.cells[2].text = value
            
            # Set column widths
            row.cells[0].width = Cm(4)
            row.cells[1].width = Cm(0.5)
            row.cells[2].width = Cm(12)
            
            # Formatting
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
                        run.font.name = 'Arial'
        
        doc.add_paragraph()  # Spacer
    
    def _add_table(self, doc: Document, data: Dict[str, Any]):
        """Add main data table"""
        table_data = data.get('table_data', {})
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        col_widths = data.get('col_widths', [])
        hierarchy = data.get('hierarchy_levels', {})
        
        # Create table
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = 'Light Grid Accent 1'
        
        # Set column widths
        if col_widths:
            for i, width in enumerate(col_widths):
                for row in table.rows:
                    row.cells[i].width = Cm(width / 10)  # mm to cm
        
        # Header row
        header_row = table.rows[0]
        for i, header_text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = header_text
            
            # Style header
            self._style_cell(cell, bold=True, size=10, 
                           align=WD_ALIGN_PARAGRAPH.CENTER,
                           bg_color=self.config.color_primary,
                           text_color=(255, 255, 255))
        
        # Data rows
        for idx, row_data in enumerate(rows):
            row = table.rows[idx + 1]
            level = hierarchy.get(idx, 3)
            
            for i, cell_value in enumerate(row_data):
                cell = row.cells[i]
                cell.text = str(cell_value)
                
                # Style based on hierarchy
                if level == 1:  # Klasifikasi
                    self._style_cell(cell, bold=True, size=10,
                                   bg_color=self.config.color_primary,
                                   text_color=(255, 255, 255))
                elif level == 2:  # Sub-Klasifikasi
                    self._style_cell(cell, bold=True, size=9,
                                   bg_color=(233, 236, 239))
                else:  # Item
                    self._style_cell(cell, size=9)
    
    def _add_footer_totals(self, doc: Document, footer_rows: List):
        """Add footer totals table"""
        doc.add_paragraph()  # Spacer
        
        table = doc.add_table(rows=len(footer_rows), cols=2)
        
        for idx, (label, value) in enumerate(footer_rows):
            row = table.rows[idx]
            row.cells[0].text = label
            row.cells[1].text = value
            
            # Set widths
            row.cells[0].width = Cm(12)
            row.cells[1].width = Cm(6)
            
            # Style
            self._style_cell(row.cells[0], bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
            self._style_cell(row.cells[1], bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    
    def _add_signatures(self, doc: Document):
        """Add signature section"""
        doc.add_page_break()  # New page for signatures
        
        heading = doc.add_heading('LEMBAR PENGESAHAN', 2)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Get signatures
        sigs = self.config.signature_config.signatures
        if self.config.signature_config.custom_signatures:
            sigs = self.config.signature_config.custom_signatures
        
        # Signature table
        sig_table = doc.add_table(rows=5, cols=len(sigs))
        
        # Row 0: Labels
        for i, sig in enumerate(sigs):
            cell = sig_table.rows[0].cells[i]
            cell.text = sig['label']
            self._style_cell(cell, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        
        # Rows 1-3: Space for signature (empty)
        for row_idx in range(1, 4):
            for cell in sig_table.rows[row_idx].cells:
                cell.text = ''
        
        # Row 4: Name line
        for cell in sig_table.rows[4].cells:
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run('_' * 20)
    
    def _style_cell(self, cell, bold=False, size=9, 
                    align=WD_ALIGN_PARAGRAPH.LEFT,
                    bg_color=None, text_color=None):
        """Apply styling to cell"""
        paragraph = cell.paragraphs[0]
        paragraph.alignment = align
        
        if paragraph.runs:
            run = paragraph.runs[0]
            run.font.bold = bold
            run.font.size = Pt(size)
            run.font.name = 'Arial'
            
            if text_color:
                run.font.color.rgb = RGBColor(*text_color)
        
        if bg_color:
            shading_elm = OxmlElement('w:shd')
            if isinstance(bg_color, tuple):
                color_hex = '{:02x}{:02x}{:02x}'.format(*bg_color)
            else:
                color_hex = bg_color
            shading_elm.set(qn('w:fill'), color_hex)
            cell._element.get_or_add_tcPr().append(shading_elm)
