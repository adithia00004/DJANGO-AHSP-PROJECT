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
from .base import ConfigExporterBase
from ..export_config import get_page_size_mm
from django.http import HttpResponse


class WordExporter(ConfigExporterBase):
    """Word Export handler with python-docx"""
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """Export to Word document (supports multi-page payload)"""
        doc = Document()

        # Set page orientation based on config
        orientation = getattr(self.config, 'page_orientation', 'landscape')
        section = doc.sections[0]

        width_mm, height_mm = get_page_size_mm(getattr(self.config, 'page_size', 'A4'))
        if orientation == 'portrait':
            section.page_width = Cm(width_mm / 10)
            section.page_height = Cm(height_mm / 10)
        else:
            section.page_width = Cm(height_mm / 10)
            section.page_height = Cm(width_mm / 10)

        section.top_margin = Cm(self.config.margin_top / 10)
        section.bottom_margin = Cm(self.config.margin_bottom / 10)
        section.left_margin = Cm(self.config.margin_left / 10)
        section.right_margin = Cm(self.config.margin_right / 10)
        
        def build_page(section: Dict[str, Any], add_signatures: bool = False):
            # Header with override title
            self._add_header_with_title(doc, section.get('title') or self.config.title)

            # Check if this page has sections (appendix with multiple tables OR pekerjaan sections)
            if 'sections' in section:
                # Check if sections are pekerjaan sections (Rincian AHSP style)
                if section['sections'] and isinstance(section['sections'][0], dict) and 'pekerjaan' in section['sections'][0]:
                    # Rincian AHSP sections (each pekerjaan with its detail table)
                    for pek_section in section['sections']:
                        self._add_pekerjaan_section(doc, pek_section)
                        doc.add_paragraph()  # Spacer between sections
                else:
                    # Multi-section page (e.g., Parameter + Formula appendix)
                    for subsection in section['sections']:
                        # Section title
                        section_title = subsection.get('section_title')
                        if section_title:
                            heading = doc.add_heading(section_title, level=2)
                            heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

                        # Section table
                        self._add_table(doc, subsection)
                        doc.add_paragraph()  # Spacer

            else:
                # Single table page
                self._add_table(doc, section)
                # Footer
                if 'footer_rows' in section:
                    self._add_footer_totals(doc, section['footer_rows'])

            # Signatures (if requested)
            if add_signatures and self.config.signature_config.enabled:
                self._add_signatures(doc)

        pages = data.get('pages')
        if pages:
            # Page 1 - with signatures at the end
            build_page(pages[0] if len(pages) > 0 else {}, add_signatures=True)

            # Page 2 onwards - no signatures
            for idx in range(1, len(pages)):
                doc.add_page_break()
                build_page(pages[idx], add_signatures=False)
        # Sections at root level (Rincian AHSP style)
        elif 'sections' in data and data['sections'] and isinstance(data['sections'][0], dict) and 'pekerjaan' in data['sections'][0]:
            # Rincian AHSP: sections with pekerjaan data
            build_page(data, add_signatures=False)

            # Add summary at the end
            if 'summary' in data:
                summary = data['summary']
                doc.add_paragraph()
                summary_para = doc.add_paragraph()
                summary_para.add_run('Ringkasan\n').bold = True
                summary_para.add_run(f"Total Pekerjaan: {summary.get('total_pekerjaan', 0)}\n")
                summary_para.add_run(f"Total Items: {summary.get('total_items', 0)}\n")
                summary_para.add_run(f"Grand Total: Rp {summary.get('grand_total', '0')}\n")

            # Lampiran Rekap AHSP (appendix)
            recap = data.get('recap')
            if recap and isinstance(recap, dict):
                doc.add_page_break()
                heading = doc.add_heading('Lampiran Rekap AHSP', level=2)
                heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                table = doc.add_table(rows=1 + len(recap.get('rows', [])), cols=3)
                try:
                    table.autofit = False
                except Exception:
                    pass
                # Header
                headers = recap.get('headers', ['Kode AHSP', 'Uraian', 'Total HSP (Rp)'])
                for i, h in enumerate(headers):
                    cell = table.rows[0].cells[i]
                    cell.text = str(h)
                    self._style_cell(cell, bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
                # Rows
                for ridx, row_data in enumerate(recap.get('rows', [])):
                    row = table.rows[ridx + 1]
                    for cidx in range(3):
                        cell = row.cells[cidx]
                        val = row_data[cidx] if cidx < len(row_data) else ''
                        cell.text = str(val)
                        align = WD_ALIGN_PARAGRAPH.RIGHT if cidx == 2 else WD_ALIGN_PARAGRAPH.LEFT
                        self._style_cell(cell, size=9, align=align)

            # Add signatures if enabled
            if self.config.signature_config.enabled:
                self._add_signatures(doc)
        else:
            build_page(data, add_signatures=True)

        # Attach image pages (e.g., Gantt / Kurva-S screenshots)
        attachments = data.get('attachments') or []
        if attachments:
            # Available width in inches
            width_mm, height_mm = get_page_size_mm(getattr(self.config, 'page_size', 'A4'))
            if getattr(self.config, 'page_orientation', 'landscape') == 'landscape':
                width_mm, height_mm = height_mm, width_mm
            usable_w_in = max(1.0, (width_mm - (self.config.margin_left + self.config.margin_right)) / 25.4)
            for att in attachments:
                img_bytes = att.get('bytes')
                if not img_bytes:
                    continue
                doc.add_page_break()
                title = att.get('title') or 'Lampiran'
                heading = doc.add_heading(title, level=2)
                heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                try:
                    pic = doc.add_picture(BytesIO(img_bytes))
                    pic.width = Inches(usable_w_in)
                except Exception:
                    continue
        
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

    def _get_page_width_mm(self) -> float:
        width_mm, height_mm = get_page_size_mm(getattr(self.config, 'page_size', 'A4'))
        return width_mm if getattr(self.config, 'page_orientation', 'landscape') == 'portrait' else height_mm
    
    def _add_header(self, doc: Document):
        """Add document header (legacy)"""
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
        try:
            table.autofit = False
        except Exception:
            pass
        
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
            
            # Style header (light background, dark text)
            self._style_cell(cell, bold=True, size=10, 
                           align=WD_ALIGN_PARAGRAPH.CENTER,
                           bg_color=self.config.color_primary)
        
        # Data rows
        for idx, row_data in enumerate(rows):
            row = table.rows[idx + 1]
            level = hierarchy.get(idx, 3)

            for i, cell_value in enumerate(row_data):
                cell = row.cells[i]
                cell.text = str(cell_value)

                # Numeric alignment: last 3 columns of 6-col tables (volume,harga,total)
                if len(headers) >= 6 and i >= len(headers) - 3:
                    for para in cell.paragraphs:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                # For 2-col summary tables, align last column right
                if len(headers) == 2 and i == 1:
                    for para in cell.paragraphs:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                # For Rekap Kebutuhan (5 cols), align Quantity column right
                if len(headers) == 5 and headers[-1].strip().lower() in ('quantity',):
                    if i == len(headers) - 1:
                        for para in cell.paragraphs:
                            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

                # Style based on hierarchy
                if level == 1:  # Klasifikasi
                    self._style_cell(cell, bold=True, size=10,
                                     bg_color=self.config.color_primary)
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

    def _add_pekerjaan_section(self, doc: Document, section: Dict[str, Any]):
        """
        Add a pekerjaan section for Rincian AHSP export.
        Structure mimics the .rk-right .ra-editor on the web page:
        - Pekerjaan header (metadata + title)
        - Detail items table
        """
        pekerjaan = section.get('pekerjaan', {})
        detail_table_data = section.get('detail_table', {})

        # Pekerjaan Header Section (similar to .rk-right-header)
        # Header line: Kode — Uraian (left aligned)
        meta_para = doc.add_paragraph()
        meta_run = meta_para.add_run(f"{pekerjaan.get('kode', '-')} {pekerjaan.get('uraian', 'Pekerjaan')}")
        meta_run.font.size = Pt(11)
        meta_run.bold = True
        meta_run.font.color.rgb = RGBColor(0, 0, 0)

        # Satuan (secondary line)
        uraian_para = doc.add_paragraph()
        uraian_run = uraian_para.add_run(f"Satuan: {pekerjaan.get('satuan', '-')}")
        uraian_run.bold = False
        uraian_run.font.size = Pt(9)
        uraian_run.font.color.rgb = RGBColor(102, 102, 102)  # #666

        # Total
        total_para = doc.add_paragraph()
        total_run = total_para.add_run(f"Total: Rp {pekerjaan.get('total', '0')}")
        total_run.bold = True
        total_run.font.size = Pt(10)
        total_run.font.color.rgb = RGBColor(44, 62, 80)  # #2c3e50

        # Detail Table (with grouped sections if provided)
        if section.get('has_details'):
            headers = detail_table_data.get('headers', [])
            groups = section.get('groups') or []
            col_widths = detail_table_data.get('col_widths', [])

            if groups:
                ncols = len(headers)
                table = doc.add_table(rows=1, cols=ncols)
                table.style = 'Light Grid Accent 1'
                try:
                    table.autofit = False
                except Exception:
                    pass

            # Set column widths
            if col_widths:
                # Scale to fit page orientation/margins
                try:
                    page_w_mm = self._get_page_width_mm()
                    usable_w = page_w_mm - (self.config.margin_left + self.config.margin_right)
                    current = sum(col_widths)
                    if current and abs(current - usable_w) > 0.5:
                        factor = usable_w / current
                        col_widths = [w * factor for w in col_widths]
                except Exception:
                    pass
                for i in range(len(col_widths)):
                    try:
                        table.columns[i].width = Cm(col_widths[i] / 10)
                    except Exception:
                        pass

                # Header row
                header_row = table.rows[0]
                for idx, header_text in enumerate(headers):
                    cell = header_row.cells[idx]
                    cell.text = header_text
                    self._style_cell(cell, bold=True, size=9,
                                     align=WD_ALIGN_PARAGRAPH.CENTER,
                                     bg_color=(245, 245, 245))

                # Helper to add aligned row
                def add_row(values: list):
                    row = table.add_row()
                    for i, val in enumerate(values):
                        cell = row.cells[i]
                        cell.text = str(val)
                        if i == 0:
                            align = WD_ALIGN_PARAGRAPH.CENTER
                        elif i in (4, 5, 6):
                            align = WD_ALIGN_PARAGRAPH.RIGHT
                        elif i == 3:
                            align = WD_ALIGN_PARAGRAPH.CENTER
                        else:
                            align = WD_ALIGN_PARAGRAPH.LEFT
                        self._style_cell(cell, size=9, align=align)

                # Track special rows for borders
                group_rows = []
                subtotal_rows = []
                total_rows = []

                # Add groups
                for g in groups:
                    # Group header row merged across columns
                    row = table.add_row()
                    row.cells[0].text = str(g.get('title') or '')
                    for i in range(1, ncols):
                        row.cells[0].merge(row.cells[i])
                    self._style_cell(row.cells[0], bold=True)
                    group_rows.append(len(table.rows) - 1)

                    # Group items
                    for r in (g.get('rows') or []):
                        add_row(r)

                    # Subtotal row: merge first ncols-1 columns
                    row = table.add_row()
                    label_cell = row.cells[0]
                    title_text = str(g.get('title') or '')
                    if '—' in title_text:
                        short = title_text.split('—')[1].strip()
                    else:
                        short = str(g.get('short_title') or '')
                    label_cell.text = f"Subtotal {short}"
                    for i in range(1, ncols-1):
                        label_cell.merge(row.cells[i])
                    self._style_cell(label_cell, bold=True)
                    val_cell = row.cells[-1]
                    val_cell.text = str(g.get('subtotal') or '0')
                    self._style_cell(val_cell, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
                    subtotal_rows.append(len(table.rows) - 1)

                # Totals E, F, G
                totals = section.get('totals') or {}
                if totals:
                    summary_labels = [
                        (f"E — Jumlah (A+B+C+D)", totals.get('E', '0')),
                        (f"F — Profit/Margin × Jumlah (E) ({totals.get('markup_eff', '0')}%)", totals.get('F', '0')),
                        (f"G — HSP = E + F", totals.get('G', '0')),
                    ]
                    for label, val in summary_labels:
                        row = table.add_row()
                        label_cell = row.cells[0]
                        label_cell.text = str(label)
                        for i in range(1, ncols-1):
                            label_cell.merge(row.cells[i])
                        self._style_cell(label_cell, bold=True)
                        val_cell = row.cells[-1]
                        val_cell.text = str(val)
                        self._style_cell(val_cell, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
                        total_rows.append(len(table.rows) - 1)

                # Apply border rules: outer thick, header thicker, segments medium
                self._apply_table_borders(table, group_rows, subtotal_rows, total_rows)
            else:
                # Fallback to flat rows
                rows = detail_table_data.get('rows', [])
                table = doc.add_table(rows=1 + len(rows), cols=len(headers))
                table.style = 'Light Grid Accent 1'
                try:
                    table.autofit = False
                except Exception:
                    pass

                if col_widths:
                    try:
                        page_w_mm = self._get_page_width_mm()
                        usable_w = page_w_mm - (self.config.margin_left + self.config.margin_right)
                        current = sum(col_widths)
                        if current:
                            factor = usable_w / current
                            col_widths = [w * factor for w in col_widths]
                    except Exception:
                        pass
                    for i in range(len(col_widths)):
                        try:
                            table.columns[i].width = Cm(col_widths[i] / 10)
                        except Exception:
                            pass

                header_row = table.rows[0]
                for idx, header_text in enumerate(headers):
                    cell = header_row.cells[idx]
                    cell.text = header_text
                    self._style_cell(cell, bold=True, size=9,
                                     align=WD_ALIGN_PARAGRAPH.CENTER,
                                     bg_color=(245, 245, 245))

                for row_idx, row_data in enumerate(rows):
                    word_row = table.rows[row_idx + 1]
                    for col_idx, cell_value in enumerate(row_data):
                        cell = word_row.cells[col_idx]
                        cell.text = str(cell_value)
                        if col_idx == 0:
                            align = WD_ALIGN_PARAGRAPH.CENTER
                        elif col_idx in (4, 5, 6):
                            align = WD_ALIGN_PARAGRAPH.RIGHT
                        elif col_idx == 3:
                            align = WD_ALIGN_PARAGRAPH.CENTER
                        else:
                            align = WD_ALIGN_PARAGRAPH.LEFT
                        self._style_cell(cell, size=9, align=align)
        else:
            # No details message
            no_detail_para = doc.add_paragraph()
            no_detail_run = no_detail_para.add_run('Tidak ada detail item untuk pekerjaan ini')
            no_detail_run.italic = True
            no_detail_run.font.size = Pt(9)

    def _add_signatures(self, doc: Document):
        """Add signature section (kept on same page as footer)"""
        
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
    
    def _apply_table_borders(self, table, group_rows, subtotal_rows, total_rows):
        """Apply border thickness rules for the table."""
        rows = len(table.rows)
        cols = len(table.columns)
        # Helper to set one edge
        def set_edge(cell, edge, size, color='666666'):
            tc = cell._element
            tcPr = tc.get_or_add_tcPr()
            edge_element = OxmlElement(f'w:{edge}')
            edge_element.set(qn('w:val'), 'single')
            edge_element.set(qn('w:sz'), str(size))
            edge_element.set(qn('w:space'), '0')
            edge_element.set(qn('w:color'), color)
            tcPr.append(edge_element)

        # First: set thin grid everywhere
        for r in range(rows):
            for c in range(cols):
                cell = table.rows[r].cells[c]
                for edge in ('top','bottom','left','right'):
                    set_edge(cell, edge, 4)

        # Outer border thick
        for c in range(cols):
            set_edge(table.rows[0].cells[c], 'top', 16)
            set_edge(table.rows[rows-1].cells[c], 'bottom', 16)
        for r in range(rows):
            set_edge(table.rows[r].cells[0], 'left', 16)
            set_edge(table.rows[r].cells[cols-1], 'right', 16)

        # Header bottom thicker
        for c in range(cols):
            set_edge(table.rows[0].cells[c], 'bottom', 12)

        # Segment rows (group headers): medium lines above and below
        for r in group_rows:
            if 0 <= r < rows:
                for c in range(cols):
                    set_edge(table.rows[r].cells[c], 'top', 8)
                    set_edge(table.rows[r].cells[c], 'bottom', 8)

        # Subtotal rows: medium top line
        for r in subtotal_rows:
            if 0 <= r < rows:
                for c in range(cols):
                    set_edge(table.rows[r].cells[c], 'top', 8)

        # Total rows: E/F medium top, G thicker top
        for i, r in enumerate(total_rows):
            if 0 <= r < rows:
                size = 12 if i == len(total_rows) - 1 else 8
                for c in range(cols):
                    set_edge(table.rows[r].cells[c], 'top', size)
    def _add_header_with_title(self, doc: Document, title_text: str):
        """Add document header with override title"""
        title = doc.add_heading(title_text, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Reuse info table
        from ..export_config import build_identity_rows
        rows = build_identity_rows(self.config)
        info_table = doc.add_table(rows=len(rows), cols=3)
        info_table.style = 'Light Grid'
        for i, (label, sep, value) in enumerate(rows):
            row = info_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = sep
            row.cells[2].text = value
            row.cells[0].width = Cm(4)
            row.cells[1].width = Cm(0.5)
            row.cells[2].width = Cm(12)
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
                        run.font.name = 'Arial'
        doc.add_paragraph()

    def export_professional(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export professional formatted Word document (Laporan Tertulis).
        
        This method handles:
        - Cover page (optional)
        - Executive summary (for monthly/weekly)
        - Comparison tables (for monthly/weekly)
        - Grid sections (separated Planned/Actual for rekap)
        - Chart attachments
        - Signature section
        """
        doc = Document()
        
        # Set page orientation
        orientation = getattr(self.config, 'page_orientation', 'landscape')
        section = doc.sections[0]
        
        width_mm, height_mm = get_page_size_mm(getattr(self.config, 'page_size', 'A4'))
        if orientation == 'portrait':
            section.page_width = Cm(width_mm / 10)
            section.page_height = Cm(height_mm / 10)
        else:
            section.page_width = Cm(height_mm / 10)
            section.page_height = Cm(width_mm / 10)
        
        section.top_margin = Cm(self.config.margin_top / 10)
        section.bottom_margin = Cm(self.config.margin_bottom / 10)
        section.left_margin = Cm(self.config.margin_left / 10)
        section.right_margin = Cm(self.config.margin_right / 10)
        
        report_type = data.get('report_type', 'rekap')
        project_info = data.get('project_info', {})
        
        # 1. Cover page content (simplified - inline)
        self._add_professional_cover(doc, report_type, project_info, data)
        doc.add_page_break()
        
        # 2. Executive Summary (for monthly/weekly)
        if report_type in ('monthly', 'weekly'):
            exec_summary = data.get('executive_summary', {})
            if exec_summary:
                self._add_executive_summary(doc, exec_summary, report_type)
                doc.add_paragraph()
            
            # 3. Comparison Table
            current_data = data.get('current_data', {})
            previous_data = data.get('previous_data', {})
            comparison = data.get('comparison', {})
            
            if current_data:
                self._add_comparison_table(doc, current_data, previous_data, comparison, report_type)
                doc.add_paragraph()
            
            # 4. Detail Progress Table
            detail_table = data.get('detail_table', {})
            if detail_table and detail_table.get('rows'):
                heading = doc.add_heading('DETAIL PROGRESS PER PEKERJAAN', level=2)
                heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                self._add_detail_progress_table(doc, detail_table)
            
            doc.add_page_break()
        
        # 5. Grid Pages (for rekap)
        if report_type == 'rekap':
            # Planned section
            planned_pages = data.get('planned_pages', [])
            for idx, page in enumerate(planned_pages):
                if idx == 0:
                    heading = doc.add_heading('BAGIAN 1: GRID VIEW - RENCANA (PLANNED)', level=1)
                    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    doc.add_paragraph()
                
                self._add_header_with_title(doc, page.get('title', 'JADWAL PEKERJAAN - PLANNED'))
                self._add_table(doc, page)
                doc.add_page_break()
            
            # Actual section
            actual_pages = data.get('actual_pages', [])
            for idx, page in enumerate(actual_pages):
                if idx == 0:
                    heading = doc.add_heading('BAGIAN 2: GRID VIEW - REALISASI (ACTUAL)', level=1)
                    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    doc.add_paragraph()
                
                self._add_header_with_title(doc, page.get('title', 'JADWAL PEKERJAAN - ACTUAL'))
                self._add_table(doc, page)
                doc.add_page_break()
            
            # Summary section
            kurva_s_data = data.get('kurva_s_data', [])
            summary = data.get('summary', {})
            if kurva_s_data or summary:
                heading = doc.add_heading('BAGIAN 3: KURVA S PROGRESS KUMULATIF', level=1)
                heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                doc.add_paragraph()
                
                if summary:
                    summary_para = doc.add_paragraph()
                    summary_para.add_run(f"Total Progress Rencana: {summary.get('total_planned', 0):.2f}%\n")
                    summary_para.add_run(f"Total Progress Realisasi: {summary.get('total_actual', 0):.2f}%\n")
                    deviation = summary.get('deviation', 0)
                    dev_text = f"Deviasi: {deviation:+.2f}%\n"
                    summary_para.add_run(dev_text)
                    summary_para.add_run(f"Total Minggu: {summary.get('total_weeks', 0)}\n")
                    summary_para.add_run(f"Total Pekerjaan: {summary.get('total_pekerjaan', 0)}\n")
                
                doc.add_page_break()
        
        # 6. Chart Attachments
        attachments = data.get('attachments') or []
        if attachments:
            width_mm, height_mm = get_page_size_mm(getattr(self.config, 'page_size', 'A4'))
            if getattr(self.config, 'page_orientation', 'landscape') == 'landscape':
                width_mm, height_mm = height_mm, width_mm
            usable_w_in = max(1.0, (width_mm - (self.config.margin_left + self.config.margin_right)) / 25.4)
            
            gantt_count = 0
            for att in attachments:
                img_bytes = att.get('bytes')
                if not img_bytes:
                    continue
                
                att_title = att.get('title') or 'Lampiran'
                
                # Add section header for first Gantt chart
                if report_type == 'rekap' and 'gantt' in att_title.lower() and gantt_count == 0:
                    heading = doc.add_heading('BAGIAN 4: GANTT CHART', level=1)
                    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    gantt_count += 1
                
                heading = doc.add_heading(att_title, level=2)
                heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                
                try:
                    pic = doc.add_picture(BytesIO(img_bytes))
                    pic.width = Inches(usable_w_in)
                except Exception:
                    error_para = doc.add_paragraph('(Gambar tidak dapat ditampilkan)')
                    error_para.runs[0].italic = True
                
                doc.add_page_break()
        
        # 7. Signature Section
        if self.config.signature_config.enabled:
            self._add_signatures(doc)
        
        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        filename = f"Laporan_{report_type}_{self.config.export_date.strftime('%Y%m%d')}.docx"
        return self._create_response(
            buffer.getvalue(),
            filename,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    def _add_professional_cover(self, doc: Document, report_type: str, project_info: Dict, data: Dict):
        """Add professional cover page content"""
        # Title based on report type
        if report_type == 'rekap':
            title_text = 'LAPORAN REKAPITULASI\nJADWAL PEKERJAAN'
        elif report_type == 'monthly':
            month = data.get('month', 1)
            title_text = f'LAPORAN BULANAN\nJADWAL PEKERJAAN\nBulan ke-{month}'
        else:
            week = data.get('week', 1)
            title_text = f'LAPORAN MINGGUAN\nJADWAL PEKERJAAN\nMinggu ke-{week}'
        
        # Spacer
        for _ in range(3):
            doc.add_paragraph()
        
        # Title
        title = doc.add_heading(title_text, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Spacer
        for _ in range(2):
            doc.add_paragraph()
        
        # Project info table
        info_items = [
            ('Nama Proyek', project_info.get('name', self.config.project_name)),
            ('Lokasi', project_info.get('location', self.config.location)),
            ('Pemilik', project_info.get('owner', '')),
            ('Tahun Anggaran', project_info.get('year', self.config.year)),
            ('Tanggal Cetak', self.config.export_date.strftime('%d-%m-%Y')),
        ]
        
        table = doc.add_table(rows=len(info_items), cols=3)
        for i, (label, value) in enumerate(info_items):
            row = table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = ':'
            row.cells[2].text = str(value) if value else '-'
            row.cells[0].width = Cm(5)
            row.cells[1].width = Cm(0.5)
            row.cells[2].width = Cm(10)
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in para.runs:
                        run.font.size = Pt(12)
                        run.font.name = 'Arial'

    def _add_executive_summary(self, doc: Document, summary: Dict, mode: str):
        """Add executive summary section"""
        heading = doc.add_heading('RINGKASAN EKSEKUTIF', level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        period_label = 'Bulan' if mode == 'monthly' else 'Minggu'
        
        # Summary table
        table = doc.add_table(rows=7, cols=3)
        table.style = 'Light Grid'
        
        rows_data = [
            (f'Target {period_label} Ini', str(summary.get('target_period', '0')) + '%', ''),
            (f'Realisasi {period_label} Ini', str(summary.get('actual_period', '0')) + '%', ''),
            ('Deviasi', str(summary.get('deviation_period', '0')) + '%', 
             self._get_status_text(summary.get('deviation_period', 0))),
            ('', '', ''),
            ('Kumulatif Target', str(summary.get('cumulative_target', '0')) + '%', ''),
            ('Kumulatif Realisasi', str(summary.get('cumulative_actual', '0')) + '%', ''),
            ('Kumulatif Deviasi', str(summary.get('cumulative_deviation', '0')) + '%',
             self._get_status_text(summary.get('cumulative_deviation', 0))),
        ]
        
        for i, (label, value, status) in enumerate(rows_data):
            row = table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = value
            row.cells[2].text = status
            self._style_cell(row.cells[0], size=10)
            self._style_cell(row.cells[1], size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
            self._style_cell(row.cells[2], size=10, bold=bool(status))

    def _add_comparison_table(self, doc: Document, current: Dict, previous: Dict, comparison: Dict, mode: str):
        """Add period comparison table"""
        period_label = 'Bulan' if mode == 'monthly' else 'Minggu'
        current_label = f'{period_label} ke-{current.get("period", "N")}'
        previous_label = f'{period_label} ke-{previous.get("period", "N-1")}'
        
        heading = doc.add_heading(f'PERBANDINGAN: {current_label.upper()} vs {previous_label.upper()}', level=2)
        heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        table = doc.add_table(rows=4, cols=4)
        table.style = 'Light Grid'
        
        # Header row
        headers = ['Metrik', previous_label, current_label, 'Delta']
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
            self._style_cell(table.rows[0].cells[i], bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        
        # Data rows
        rows_data = [
            ('Target', previous.get('target', 0), current.get('target', 0)),
            ('Realisasi', previous.get('actual', 0), current.get('actual', 0)),
            ('Deviasi', previous.get('deviation', 0), current.get('deviation', 0)),
        ]
        
        for i, (label, prev_val, curr_val) in enumerate(rows_data):
            row = table.rows[i + 1]
            delta = curr_val - prev_val if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)) else 0
            delta_str = f'{delta:+.2f}%' if isinstance(delta, float) else f'{delta:+d}%'
            
            row.cells[0].text = label
            row.cells[1].text = f'{prev_val:.2f}%' if isinstance(prev_val, float) else str(prev_val)
            row.cells[2].text = f'{curr_val:.2f}%' if isinstance(curr_val, float) else str(curr_val)
            row.cells[3].text = delta_str
            
            self._style_cell(row.cells[0], size=10)
            self._style_cell(row.cells[1], size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
            self._style_cell(row.cells[2], size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
            self._style_cell(row.cells[3], size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)

    def _add_detail_progress_table(self, doc: Document, detail_data: Dict):
        """Add detail progress per pekerjaan table"""
        headers = detail_data.get('headers', ['No', 'Uraian', 'Bobot', 'Target', 'Aktual', 'Deviasi'])
        rows = detail_data.get('rows', [])
        hierarchy = detail_data.get('hierarchy_levels', {})
        
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = 'Light Grid Accent 1'
        
        # Header row
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
            self._style_cell(table.rows[0].cells[i], bold=True, size=9, 
                           align=WD_ALIGN_PARAGRAPH.CENTER,
                           bg_color=(230, 230, 230))
        
        # Data rows
        for idx, row_data in enumerate(rows):
            row = table.rows[idx + 1]
            level = hierarchy.get(idx, 3)
            
            for col_idx, cell_value in enumerate(row_data):
                cell = row.cells[col_idx]
                cell.text = str(cell_value)
                
                # Alignment
                if col_idx >= 2:  # Numeric columns
                    align = WD_ALIGN_PARAGRAPH.RIGHT
                else:
                    align = WD_ALIGN_PARAGRAPH.LEFT
                
                # Styling based on hierarchy
                if level == 1:
                    self._style_cell(cell, bold=True, size=9, align=align, bg_color=(220, 230, 240))
                elif level == 2:
                    self._style_cell(cell, bold=True, size=9, align=align, bg_color=(240, 240, 245))
                else:
                    self._style_cell(cell, size=9, align=align)

    def _get_status_text(self, deviation: float) -> str:
        """Get status text based on deviation"""
        if deviation is None:
            return ''
        try:
            dev = float(deviation)
            if dev >= 0:
                return '🔵 AHEAD' if dev > 2 else '🟢 ON TRACK'
            elif dev > -2:
                return '🟢 ON TRACK'
            elif dev > -5:
                return '🟡 SLIGHT DELAY'
            else:
                return '🔴 BEHIND'
        except (ValueError, TypeError):
            return ''
