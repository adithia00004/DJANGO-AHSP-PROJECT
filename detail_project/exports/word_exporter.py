# ============================================================================
# FILE: detail_project/exports/word_exporter.py
# ============================================================================
"""
Word Document Export Handler

Exports Jadwal Pekerjaan data to Microsoft Word (.docx) format.
Supports 3 report types:
- Rekap: Full summary with Grid Planned/Actual + Kurva S
- Bulanan (Monthly): Progress report with Kurva S
- Mingguan (Weekly): Compact weekly progress

Uses python-docx for native Word element manipulation.

Author: Word Export Phase 1
Created: 2025
"""

from io import BytesIO
import logging
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List
from django.conf import settings
from django.http import HttpResponse

from docx import Document
from docx.shared import Inches, Mm, Pt, Cm, RGBColor
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from ..export_config import (
    ExportConfig,
    ExportColors,
    ExportFonts,
    JadwalExportLayout,
    get_level_style,
    build_identity_rows,
)
from .table_styles import UnifiedTableStyles as UTS, ExportDefaults as ED
from .signature_config import SignatureLayoutRules as SLR, SIGNATURE_SPACE_MM


logger = logging.getLogger(__name__)


class WordExporter:
    """
    Word Document Exporter for Jadwal Pekerjaan reports.
    
    Usage:
        config = ExportConfig(...)
        exporter = WordExporter(config)
        response = exporter.export_rekap(data)
    """
    
    def __init__(self, config: ExportConfig):
        """
        Initialize Word exporter with configuration.
        
        Args:
            config: ExportConfig with project info and styling settings
        """
        self.config = config
        self.doc = None
        # Dinyalakan export_package(); lihat catatan di export().
        self._package_mode = False
        # Tabel yang dikecualikan dari tinggi baris minimum (mis. blok tanda
        # tangan yang sengaja dirapatkan). Berisi id(table._tbl).
        self._min_height_exempt = set()
        # Rincian AHSP memakai ambang minimum lebih rendah; lihat table_styles.
        self._is_rincian_doc = False
    
    # =========================================================================
    # PUBLIC EXPORT METHODS
    # =========================================================================
    
    def export_professional(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export professional formatted Word document.
        
        This is the main entry point called by ExportManager.
        Dispatches to appropriate export method based on report_type.
        
        Args:
            data: Export data containing report_type and content
            
        Returns:
            HttpResponse with .docx file
        """
        report_type = data.get('report_type', 'rekap')
        
        if report_type == 'monthly':
            return self.export_monthly(data)
        elif report_type == 'weekly':
            return self.export_weekly(data)
        elif report_type == 'daily':
            return self.export_daily_professional(data)
        else:
            return self.export_rekap(data)

    def export_daily_professional(self, data: Dict[str, Any]) -> HttpResponse:
        """Export laporan harian as DOCX.

        The generated document starts from the DOCX template package so Word
        diagram/SmartArt parts on the documentation page stay available. Work
        pages are generated dynamically and paginated; documentation pages are
        copied from the template block.
        """
        template_path = Path(settings.BASE_DIR) / 'detail_project' / 'export_templates' / 'laporan_harian_template.docx'
        if template_path.exists():
            self.doc = Document(str(template_path))
            documentation_block = self._extract_daily_doc_block(
                self.doc,
                start_heading='01 JAN - Dokumentasi',
            )
            self._clear_doc_body_preserve_section(self.doc)
        else:
            self.doc = Document()
            documentation_block = []

        self._setup_page_layout('A4', 'portrait')
        self._setup_daily_doc_styles()

        project_info = data.get('project_info', {}) or {}
        reports = data.get('sheets', []) or []
        if not reports:
            reports = [{
                'sheet_name': 'LAPORAN',
                'date': None,
                'week_number': None,
                'previous_week': None,
                'previous_progress': {},
                'work_items': [],
            }]

        first_page = True
        for report in reports:
            work_items = report.get('work_items') or []
            if not work_items:
                work_items = [{'uraian': 'Tidak ada pekerjaan terjadwal pada periode ini.', 'keterangan': ''}]

            chunks = [
                work_items[i:i + self._daily_work_rows_per_page()]
                for i in range(0, len(work_items), self._daily_work_rows_per_page())
            ] or [[]]

            for page_index, chunk in enumerate(chunks, start=1):
                if not first_page:
                    self.doc.add_page_break()
                first_page = False

                page_count = len(chunks)
                sheet_name = report.get('sheet_name') or self._daily_sheet_label(report)
                heading = (
                    f"{sheet_name} - Pekerjaan {page_index}"
                    if page_count > 1 else
                    f"{sheet_name} - Laporan Harian"
                )
                self._daily_add_heading(heading, level=1)
                self._daily_add_title(
                    'LAPORAN HARIAN PROYEK',
                    self._daily_subtitle(report),
                )
                self._daily_add_identity(project_info, report)
                self._daily_add_work_table(chunk, page_index, page_count)
                if page_index == page_count:
                    self._daily_add_signatures()

            self.doc.add_page_break()
            if documentation_block:
                self._append_daily_documentation_block(documentation_block, report)
            else:
                sheet_name = report.get('sheet_name') or self._daily_sheet_label(report)
                self._daily_add_heading(f"{sheet_name} - Dokumentasi", level=1)
                self._daily_add_title('DOKUMENTASI LAPORAN HARIAN', self._daily_subtitle(report))
                self._daily_add_photo_fallback()

        self._daily_normalize_drawing_ids()
        return self._create_daily_response(reports)
    
    def export(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Generic export method for backward compatibility.
        
        Called by ExportManager for non-professional exports like rekap_rab.
        Creates a simple document with pages of tables.
        
        Args:
            data: Export data with 'pages' list
            
        Returns:
            HttpResponse with .docx file
        """
        # WP Export: format canonical Decimal cells to display strings at this
        # text-exporter boundary (only column_formats-tagged tables are touched).
        from .cell_format import materialize_display_rows
        data = materialize_display_rows(data)

        # Check if this is Rincian AHSP data
        sections = data.get('sections', [])
        is_rincian_ahsp = bool(
            sections and 
            isinstance(sections[0], dict) and 
            'pekerjaan' in sections[0] and 
            'groups' in sections[0]
        )

        if is_rincian_ahsp:
            return self._export_rincian_ahsp(data)

        # Mode paket: dokumen dan tata halaman sudah disiapkan export_package(),
        # dan responsnya dibuat sekali di akhir. Tanpa penjagaan ini tiap dokumen
        # akan membuat Document() baru dan menimpa isi sebelumnya.
        if not self._package_mode:
            self.doc = Document()
        # N-2 (doc 32 §13.1): ukuran & orientasi mengikuti config report —
        # sebelumnya hardcoded A4 portrait, sehingga jadwal_full (config A3
        # landscape, 15+ kolom) terjepit; kini paritas dengan PDF.
        self._setup_page_layout(
            getattr(self.config, 'page_size', 'A4') or 'A4',
            getattr(self.config, 'page_orientation', 'portrait') or 'portrait',
        )

        # Doc 32 Fase 3 — aktivasi style registry per-report (flag yang sama
        # dengan PDF Fase 2); report tanpa flag tetap jalur legacy.
        self._registry_active = bool(data.get('style_registry'))
        if self._registry_active:
            self._apply_registry_base_styles()
        
        # Handle single-table data (e.g., Harga Items) vs multi-page data
        pages = data.get('pages', [])
        if not pages and 'table_data' in data:
            # Single table data - wrap it as a single page
            pages = [data]
        
        for idx, page in enumerate(pages):
            # Page title
            title = page.get('title') or self.config.title or f'Page {idx + 1}'
            self._build_section_header(title)
            
            # Project identity
            if getattr(self, '_registry_active', False):
                # Fase 3.4: identitas = tabel 3 kolom, paritas dengan PDF
                self._build_identity_table()
            else:
                from ..export_config import build_identity_rows
                for label, _, value in build_identity_rows(self.config):
                    para = self.doc.add_paragraph()
                    para.add_run(f"{label}: ").bold = True
                    para.add_run(str(value))

            self.doc.add_paragraph()  # Spacing (pemisah wajib antar tabel)
            
            # Build table from page data
            table_data = page.get('table_data', {})
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            row_types = page.get('row_types', [])
            # Lihat catatan di pdf_exporter: tata letak pengesahan dipilih
            # eksplisit, terpisah dari keputusan menambahkan tanda tangan.
            is_pengesahan_page = page.get('pengesahan_layout', False)

            # Fase 3.5: perataan per-tipe kolom dari column_formats (helper 1.4)
            col_aligns = None
            if getattr(self, '_registry_active', False):
                from .styles.alignment import alignment_for_columns
                col_aligns = alignment_for_columns(
                    headers, table_data.get('column_formats'))
            wd_align_map = {
                'LEFT': WD_ALIGN_PARAGRAPH.LEFT,
                'RIGHT': WD_ALIGN_PARAGRAPH.RIGHT,
                'CENTER': WD_ALIGN_PARAGRAPH.CENTER,
            }

            if headers and rows:
                if is_pengesahan_page:
                    # Pengesahan page - use dedicated 3-column table
                    self._build_pengesahan_word_table(table_data, page.get('col_widths', []))
                else:
                    # Regular table - use existing logic
                    num_cols = len(headers)
                    num_rows = len(rows) + 1
                    
                    table = self.doc.add_table(rows=num_rows, cols=num_cols)
                    table.style = 'Table Grid'
                
                    # Header row
                    for col_idx, header_text in enumerate(headers):
                        cell = table.rows[0].cells[col_idx]
                        cell.text = str(header_text)
                        self._style_header_cell(cell)
                    
                    # Data rows
                    for row_idx, row_data in enumerate(rows):
                        row_type = row_types[row_idx] if row_idx < len(row_types) else 'item'
                        table_row = table.rows[row_idx + 1]
                        
                        if row_type in ('category', 'subcategory'):
                            # Baris hierarki: merge semua sel + bold.
                            # Temuan owner #3: Klasifikasi (category) tint lebih
                            # kuat daripada Sub-Klasifikasi (subcategory)
                            for col_idx in range(1, num_cols):
                                table_row.cells[0].merge(table_row.cells[col_idx])
                            table_row.cells[0].text = str(row_data[0]) if row_data else ''
                            for para in table_row.cells[0].paragraphs:
                                for run in para.runs:
                                    run.bold = True
                                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            from docx.oxml.ns import qn
                            from docx.oxml import OxmlElement
                            shading = OxmlElement('w:shd')
                            if getattr(self, '_registry_active', False):
                                cat_fill = 'D7E0EC' if row_type == 'category' else 'E8EDF3'
                            else:
                                cat_fill = 'E8E8E8' if row_type == 'category' else 'F0F0F0'
                            shading.set(qn('w:fill'), cat_fill)
                            table_row.cells[0]._tc.get_or_add_tcPr().append(shading)
                        else:
                            # Normal item row
                            for col_idx, cell_value in enumerate(row_data):
                                if col_idx < num_cols:
                                    cell = table_row.cells[col_idx]
                                    text = str(cell_value) if cell_value else ''
                                    # Handle multi-line text (with \n)
                                    if '\n' in text:
                                        lines = text.split('\n')
                                        cell.text = ''  # Clear default paragraph
                                        for i, line in enumerate(lines):
                                            if i == 0:
                                                cell.paragraphs[0].text = line
                                            else:
                                                cell.add_paragraph(line)
                                    else:
                                        cell.text = text
                                    if col_aligns and col_idx < len(col_aligns):
                                        cell_align = wd_align_map[col_aligns[col_idx]]
                                        for cell_para in cell.paragraphs:
                                            cell_para.alignment = cell_align
                    
                    self._enable_header_repeat(table)
                    
                    # Set column widths if specified
                    col_widths = page.get('col_widths', [])
                    if col_widths:
                        for row in table.rows:
                            for col_idx, cell in enumerate(row.cells):
                                if col_idx < len(col_widths):
                                    cell.width = Mm(col_widths[col_idx])
            
            # Footer rows
            footer_rows = page.get('footer_rows', [])
            if footer_rows:
                self.doc.add_paragraph()  # Spacing
                self._build_footer_table(footer_rows)
            
            # Add signatures if this page has include_signatures=True
            if page.get('include_signatures') and self.config.signature_config.enabled:
                self.doc.add_paragraph()  # Spacing
                self._build_signature_section()
            
            # Page break if not last page
            if idx < len(pages) - 1:
                self.doc.add_page_break()
        
        if self._package_mode:
            return None
        return self._create_response('export')

    def _export_rincian_ahsp(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export Rincian AHSP to Word document.
        
        Structure:
        1. Rekap (summary table)
        2. Rincian (detail per pekerjaan)
        3. Lembar Pengesahan (at bottom of last rincian page)
        """
        # Ambang tinggi baris minimum khusus Rincian AHSP (lihat table_styles).
        self._is_rincian_doc = True
        # Mode paket: dokumen dan tata halaman sudah disiapkan export_package(),
        # dan responsnya dibuat sekali di akhir. Tanpa penjagaan ini tiap dokumen
        # akan membuat Document() baru dan menimpa isi sebelumnya.
        if not self._package_mode:
            self.doc = Document()
        # N-2: ikuti config (Rincian AHSP tetap portrait dari manager — tanpa
        # perubahan visual; konsistensi jalur saja)
        self._setup_page_layout(
            getattr(self.config, 'page_size', 'A4') or 'A4',
            getattr(self.config, 'page_orientation', 'portrait') or 'portrait',
        )

        # Doc 32 Fase 3 — registry per-report (jalur ini keluar sebelum
        # export() generik, jadi flag di-set di sini juga)
        self._registry_active = bool(data.get('style_registry'))
        if self._registry_active:
            self._apply_registry_base_styles()

        sections = data.get('sections', [])

        # ========== SECTION 1: REKAP ==========
        title_para = self.doc.add_paragraph()
        title_run = title_para.add_run('REKAP ANALISA HARGA SATUAN PEKERJAAN')
        title_run.bold = True
        if self._registry_active:
            # 2.7/T-5: judul rata kiri kompak — paritas PDF Rincian (9pt bold)
            title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            title_run.font.size = Pt(9)
        else:
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run.font.size = Pt(16)

        # Identity rows
        if self._registry_active:
            # Fase 3.4: identitas = tabel 3 kolom, paritas PDF
            self._build_identity_table()
        else:
            identity_rows = build_identity_rows(self.config)
            if identity_rows:
                self.doc.add_paragraph()
                id_table = self.doc.add_table(rows=len(identity_rows), cols=3)
                for i, row_data in enumerate(identity_rows):
                    for j, cell_text in enumerate(row_data):
                        id_table.rows[i].cells[j].text = str(cell_text)

        self.doc.add_paragraph()
        
        # Rekap table
        rekap_headers = ['No', 'Kode', 'Uraian Pekerjaan', 'Jumlah', 'Profit/Margin', 'Harga Satuan']
        rekap_table = self.doc.add_table(rows=len(sections) + 1, cols=6)
        rekap_table.style = 'Table Grid'
        
        # Header row
        for col_idx, header_text in enumerate(rekap_headers):
            cell = rekap_table.rows[0].cells[col_idx]
            cell.text = header_text
            self._style_header_cell(cell)
        
        # Data rows
        for idx, section in enumerate(sections):
            pekerjaan = section.get('pekerjaan', {})
            totals = section.get('totals', {})
            row = rekap_table.rows[idx + 1]
            
            row.cells[0].text = str(idx + 1)
            row.cells[1].text = pekerjaan.get('kode', '')
            row.cells[2].text = pekerjaan.get('uraian', '')
            row.cells[3].text = totals.get('E', '0')
            row.cells[4].text = totals.get('F', '0')
            row.cells[5].text = totals.get('G', '0')
            # Bold G column
            for para in row.cells[5].paragraphs:
                for run in para.runs:
                    run.bold = True
            if self._registry_active:
                # 2.3: No/Kode center, uang (E/F/G) kanan
                for c_idx in (0, 1):
                    for para in row.cells[c_idx].paragraphs:
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for c_idx in (3, 4, 5):
                    for para in row.cells[c_idx].paragraphs:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        # Column widths for rekap
        rekap_widths = [Mm(8), Mm(20), Mm(55), Mm(30), Mm(30), Mm(32)]
        for row in rekap_table.rows:
            for col_idx, cell in enumerate(row.cells):
                cell.width = rekap_widths[col_idx]
        
        self.doc.add_page_break()
        
        # ========== SECTION 2: RINCIAN ==========
        rincian_title = self.doc.add_paragraph()
        rincian_run = rincian_title.add_run('RINCIAN ANALISA HARGA SATUAN PEKERJAAN')
        rincian_run.bold = True
        if self._registry_active:
            rincian_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
            rincian_run.font.size = Pt(9)
        else:
            rincian_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rincian_run.font.size = Pt(16)
        
        self.doc.add_paragraph()
        
        # Write each pekerjaan section (no Grand Total)
        for idx, section in enumerate(sections):
            pekerjaan = section.get('pekerjaan', {})
            groups = section.get('groups', [])
            totals = section.get('totals', {})
            
            pek_kode = pekerjaan.get('kode', '')
            pek_uraian = pekerjaan.get('uraian', '')
            
            # Pekerjaan header
            header_para = self.doc.add_paragraph()
            header_run = header_para.add_run(f"{pek_kode} - {pek_uraian}" if pek_kode else pek_uraian)
            header_run.bold = True
            header_run.font.size = Pt(11)
            
            # Detail table headers
            headers = ['No', 'Uraian', 'Kode', 'Satuan', 'Koefisien', 'Harga Satuan', 'Jumlah Harga']
            
            # Count total rows for table
            total_rows = 1  # header
            for group in groups:
                if group.get('rows'):
                    total_rows += 1  # group title
                    total_rows += len(group.get('rows', []))
                    total_rows += 1  # subtotal
            total_rows += 3  # E, F, G
            
            table = self.doc.add_table(rows=total_rows, cols=7)
            table.style = 'Table Grid'
            
            # Header row
            for col_idx, header_text in enumerate(headers):
                cell = table.rows[0].cells[col_idx]
                cell.text = header_text
                self._style_header_cell(cell)
            
            row_idx = 1
            
            # Write groups
            for group in groups:
                group_title = group.get('title', '')
                group_rows = group.get('rows', [])
                group_subtotal = group.get('subtotal', '')
                
                if not group_rows:
                    continue
                
                # Group title
                if row_idx < len(table.rows):
                    # W-3 (temuan owner 2026-08-18): judul grup harus melebar
                    # menutupi kolom 0-5, sama seperti SPAN di PDF. Tanpa merge,
                    # judul terjepit di kolom "No" yang sempit dan terbaca
                    # seperti nilai yang dipaksakan ke satu sel.
                    _gcells = table.rows[row_idx].cells
                    _gcells[0].merge(_gcells[5])
                    table.rows[row_idx].cells[0].text = group_title
                    for para in table.rows[row_idx].cells[0].paragraphs:
                        for run in para.runs:
                            run.bold = True
                            run.italic = True
                            run.font.size = Pt(9)
                    if self._registry_active:
                        # Paritas PDF: latar abu muda utk judul grup
                        self._shade_cells(table.rows[row_idx].cells, 'F0F0F0')
                    row_idx += 1

                # Group detail rows
                for row_data in group_rows:
                    if row_idx < len(table.rows):
                        for col_idx, val in enumerate(row_data):
                            if col_idx < 7:
                                table.rows[row_idx].cells[col_idx].text = str(val) if val else ''
                        if self._registry_active:
                            # 2.3: No/Kode/Satuan center, angka kanan
                            detail_cells = table.rows[row_idx].cells
                            for c_idx in (0, 2, 3):
                                for para in detail_cells[c_idx].paragraphs:
                                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            for c_idx in (4, 5, 6):
                                for para in detail_cells[c_idx].paragraphs:
                                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        row_idx += 1
                
                # Subtotal row
                if row_idx < len(table.rows):
                    # Label subtotal melebar 0-5; kolom 6 tetap terpisah untuk
                    # nilainya, persis seperti PDF.
                    _scells = table.rows[row_idx].cells
                    _scells[0].merge(_scells[5])
                    table.rows[row_idx].cells[0].text = f"Subtotal {group.get('short_title', '')}"
                    for para in table.rows[row_idx].cells[0].paragraphs:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        for run in para.runs:
                            run.bold = True
                    table.rows[row_idx].cells[6].text = str(group_subtotal)
                    for para in table.rows[row_idx].cells[6].paragraphs:
                        if self._registry_active:
                            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        for run in para.runs:
                            run.bold = True
                    row_idx += 1
            
            # Total E
            if row_idx < len(table.rows):
                # Paritas PDF (row_type total_e): label melebar 0-5.
                _ecells = table.rows[row_idx].cells
                _ecells[0].merge(_ecells[5])
                table.rows[row_idx].cells[0].text = "Jumlah (E)"
                for para in table.rows[row_idx].cells[0].paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:
                        run.bold = True
                table.rows[row_idx].cells[6].text = totals.get('E', '0')
                for para in table.rows[row_idx].cells[6].paragraphs:
                    if self._registry_active:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:
                        run.bold = True
                if self._registry_active:
                    self._shade_cells(table.rows[row_idx].cells, 'E8EDF3')
                row_idx += 1
            
            # Total F (Profit/Margin)
            if row_idx < len(table.rows):
                markup = totals.get('markup_eff', '10.00')
                # Paritas PDF (row_type total_f).
                _fcells = table.rows[row_idx].cells
                _fcells[0].merge(_fcells[5])
                table.rows[row_idx].cells[0].text = f"Profit/Margin {markup}% (F)"
                for para in table.rows[row_idx].cells[0].paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:
                        run.bold = True
                table.rows[row_idx].cells[6].text = totals.get('F', '0')
                for para in table.rows[row_idx].cells[6].paragraphs:
                    if self._registry_active:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:
                        run.bold = True
                if self._registry_active:
                    self._shade_cells(table.rows[row_idx].cells, 'E8EDF3')
                row_idx += 1
            
            # Total G (Harga Satuan Pekerjaan)
            if row_idx < len(table.rows):
                # Paritas PDF (row_type total_g).
                _gcells2 = table.rows[row_idx].cells
                _gcells2[0].merge(_gcells2[5])
                table.rows[row_idx].cells[0].text = "Harga Satuan Pekerjaan (G = E + F)"
                for para in table.rows[row_idx].cells[0].paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:
                        run.bold = True
                        run.font.size = Pt(10)
                table.rows[row_idx].cells[6].text = totals.get('G', '0')
                for para in table.rows[row_idx].cells[6].paragraphs:
                    if self._registry_active:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:
                        run.bold = True
                        run.font.size = Pt(10)
                if self._registry_active:
                    self._shade_cells(table.rows[row_idx].cells, 'D7E0EC')
            
            # Column widths
            widths = [Mm(10), Mm(50), Mm(25), Mm(15), Mm(20), Mm(25), Mm(30)]
            for row in table.rows:
                for col_idx, cell in enumerate(row.cells):
                    cell.width = widths[col_idx]
            
            # Spacing between pekerjaan tables (no page break - more compact)
            if idx < len(sections) - 1:
                self.doc.add_paragraph()  # 1 line spacing
                self.doc.add_paragraph()  # 2 lines total
        
        # ========== SECTION 3: LEMBAR PENGESAHAN ==========
        # Memakai blok bersama _build_signature_section(). Sebelumnya di sini ada
        # tabel hardcode berisi label tetap dan "(______)", kembaran dari yang ada
        # di pdf_exporter -- keduanya mengabaikan data proyek, sehingga lembar
        # pengesahan Rincian AHSP terbit kosong di kedua format.
        self.doc.add_paragraph()
        self._build_signature_section()
        
        if self._package_mode:
            return None
        return self._create_response('rincian_ahsp')
    
    def export_package(self, documents, filename_title: str = 'Paket Perencanaan') -> HttpResponse:
        """Rangkai beberapa dokumen menjadi SATU berkas Word.

        ``documents`` adalah urutan ``(judul, data)``. Tiap dokumen dirender
        lewat jalur yang sama persis dengan unduhan tunggal -- termasuk lembar
        pengesahannya masing-masing -- lalu dipisah page break.
        """
        self.doc = Document()
        self._setup_page_layout(
            getattr(self.config, 'page_size', 'A4') or 'A4',
            getattr(self.config, 'page_orientation', 'portrait') or 'portrait',
        )

        self._package_mode = True
        original_title = self.config.title
        try:
            for idx, entry in enumerate(documents):
                if idx:
                    self.doc.add_page_break()
                self.config.title = entry['title']
                self.export(entry['data'])
        finally:
            self._package_mode = False
            self.config.title = original_title

        return self._create_response(filename_title)

    def export_rekap(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export Rekap Laporan to Word document.
        
        Structure:
        1. Cover Page
        2. Table of Contents
        3. Grid Planned Section
        4. Grid Actual Section
        5. Kurva S Section
        
        Args:
            data: Export data containing:
                - project_info: Project metadata
                - planned_pages: Planned progress data
                - actual_pages: Actual progress data
                - kurva_s_data: Kurva S chart data
                - sections: TOC sections
                
        Returns:
            HttpResponse with .docx file
        """
        import time
        start = time.time()
        step_times = {}
        
        self.doc = Document()
        self._setup_page_layout('A3', 'landscape')
        
        project_info = data.get('project_info', {})
        
        # 1. Cover Page
        self._build_cover_page('rekap', project_info)
        self.doc.add_page_break()
        
        # 2. Table of Contents
        sections = data.get('sections', [])
        if sections:
            self._build_toc(sections)
            self.doc.add_page_break()
        
        # 3. Grid Planned Section
        planned_pages = data.get('planned_pages', [])
        if planned_pages:
            grid_planned_start = time.time()
            self._build_section_header('BAGIAN 1: GRID VIEW - RENCANA (PLANNED)')
            for i, page in enumerate(planned_pages):
                page_start = time.time()
                self._build_grid_table(page, mode='planned')
                logger.debug("[WordExporter] Grid Planned page %s/%s: %.2fs", i + 1, len(planned_pages), time.time() - page_start)
            self.doc.add_page_break()
            step_times['grid_planned'] = time.time() - grid_planned_start
            logger.debug("[WordExporter] Grid Planned (%s pages): %.2fs", len(planned_pages), step_times['grid_planned'])
        
        # 4. Grid Actual Section
        actual_pages = data.get('actual_pages', [])
        if actual_pages:
            grid_actual_start = time.time()
            self._build_section_header('BAGIAN 2: GRID VIEW - REALISASI (ACTUAL)')
            for i, page in enumerate(actual_pages):
                page_start = time.time()
                self._build_grid_table(page, mode='actual')
                logger.debug("[WordExporter] Grid Actual page %s/%s: %.2fs", i + 1, len(actual_pages), time.time() - page_start)
            self.doc.add_page_break()
            step_times['grid_actual'] = time.time() - grid_actual_start
            logger.debug("[WordExporter] Grid Actual (%s pages): %.2fs", len(actual_pages), step_times['grid_actual'])
        
        # NOTE: Gantt Chart dan Kurva S dihapus dari Word export
        # karena bukan format native Word (hanya embedded image).
        # User dapat download Gantt/Kurva S sebagai image terpisah dari UI.
        
        # Create response
        step_start = time.time()
        response = self._create_response('rekap_laporan')
        step_times['create_response'] = time.time() - step_start
        logger.debug("[WordExporter] Create response (save doc): %.2fs", step_times['create_response'])
        logger.info("[WordExporter] Total export_rekap: %.2fs", time.time() - start)
        
        return response
    
    def export_monthly(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export Laporan Bulanan to Word document.
        
        Structure:
        1. Cover Page
        2. Progress Pelaksanaan Page
        3. Kurva S Monthly (Landscape)
        4. Kurva S Portrait
        5. Signature Section
        
        Args:
            data: Export data for monthly report
                
        Returns:
            HttpResponse with .docx file
        """
        self.doc = Document()
        self._setup_page_layout('A4', 'portrait')
        
        project_info = data.get('project_info', {})
        month = data.get('month', 1)
        period_info = data.get('period', {})
        
        # 1. Cover Page
        self._build_cover_page('monthly', project_info, period_info)
        self.doc.add_page_break()
        
        # 2. Progress Pelaksanaan
        exec_summary = data.get('executive_summary', {})
        hierarchy_data = data.get('hierarchy_progress', [])
        self._build_progress_page(month, project_info, exec_summary, hierarchy_data, 'monthly')
        self.doc.add_page_break()
        
        # 3. Kurva S Monthly (switch to landscape)
        kurva_s_data = data.get('kurva_s_data', [])
        if kurva_s_data:
            self._add_section_break('landscape')
            self._build_section_header(f'RINGKASAN PROGRESS KURVA S (Bulan ke-{month})')
            self._build_kurva_s_section(kurva_s_data, data)
        
        # 4. Signature Section
        self._add_section_break('portrait')
        self._build_signature_section(project_info)
        
        return self._create_response(f'laporan_bulan_{month}')
    
    def export_weekly(self, data: Dict[str, Any]) -> HttpResponse:
        """
        Export Laporan Mingguan to Word document.
        
        Structure:
        1. Cover Page
        2. Weekly Progress Page
        
        Args:
            data: Export data for weekly report
                
        Returns:
            HttpResponse with .docx file
        """
        self.doc = Document()
        self._setup_page_layout('A4', 'portrait')
        
        project_info = data.get('project_info', {})
        week = data.get('week', 1)
        period_info = data.get('period', {})
        
        # 1. Cover Page
        self._build_cover_page('weekly', project_info, period_info)
        self.doc.add_page_break()
        
        # 2. Weekly Progress Page
        exec_summary = data.get('executive_summary', {})
        hierarchy_data = data.get('hierarchy_progress', [])
        self._build_progress_page(week, project_info, exec_summary, hierarchy_data, 'weekly')
        
        return self._create_response(f'laporan_minggu_{week}')
    
    # =========================================================================
    # PAGE LAYOUT SETUP
    # =========================================================================
    
    def _setup_page_layout(self, size: str = 'A4', orientation: str = 'portrait'):
        """
        Configure page size, orientation, and margins.
        
        Args:
            size: 'A4' or 'A3'
            orientation: 'portrait' or 'landscape'
        """
        section = self.doc.sections[0]
        
        # A4: 210mm x 297mm (Portrait), A3: 297mm x 420mm (Portrait)
        if size.upper() == 'A3':
            base_width = Mm(297)
            base_height = Mm(420)
        else:  # A4
            base_width = Mm(210)
            base_height = Mm(297)
        
        # Apply orientation
        if orientation == 'landscape':
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width = base_height  # Swap for landscape
            section.page_height = base_width
        else:  # portrait
            section.orientation = WD_ORIENT.PORTRAIT
            section.page_width = base_width
            section.page_height = base_height
        
        # Margins from config
        section.top_margin = Mm(self.config.margin_top)
        section.bottom_margin = Mm(self.config.margin_bottom)
        section.left_margin = Mm(self.config.margin_left)
        section.right_margin = Mm(self.config.margin_right)
    
    def _add_section_break(self, orientation: str = 'portrait'):
        """
        Add section break with new orientation.
        
        Args:
            orientation: 'portrait' or 'landscape'
        """
        new_section = self.doc.add_section()
        
        if orientation == 'landscape':
            new_section.orientation = WD_ORIENT.LANDSCAPE
            new_section.page_width = Mm(420 if self.config.page_size == 'A3' else 297)
            new_section.page_height = Mm(297 if self.config.page_size == 'A3' else 210)
        else:
            new_section.orientation = WD_ORIENT.PORTRAIT
            new_section.page_width = Mm(297 if self.config.page_size == 'A3' else 210)
            new_section.page_height = Mm(420 if self.config.page_size == 'A3' else 297)
        
        # Copy margins
        new_section.top_margin = Mm(self.config.margin_top)
        new_section.bottom_margin = Mm(self.config.margin_bottom)
        new_section.left_margin = Mm(self.config.margin_left)
        new_section.right_margin = Mm(self.config.margin_right)
    
    def _build_signature_section(self, project_info: Dict[str, Any] = None):
        """
        Build signature section with signature boxes.
        Uses config.signature_config for signature data.
        
        Args:
            project_info: Optional project info dict (for backward compatibility)
        """
        # Add title
        title_para = self.doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run('LEMBAR PENGESAHAN')
        title_run.bold = True
        title_run.font.size = Pt(14)
        
        self.doc.add_paragraph()  # Spacing
        
        # Get signature data from config
        sig_config = self.config.signature_config
        signatures = sig_config.signatures if sig_config and sig_config.enabled else []
        if not signatures:
            return

        # Susunan disamakan persis dengan PDFExporter._build_signatures (R-37):
        # INSTANSI / ruang TTD / NAMA (digarisbawahi) / keterangan (pemilik:
        # ket_client2 lalu jabatan). Tanpa kata penghubung & sebutan peran.
        # Baris keterangan dipadatkan ke jumlah terbanyak agar kolom sejajar.
        shown = list(signatures)
        num_cols = len(shown)
        details = [sig.get('details') or [] for sig in shown]
        max_details = max((len(d) for d in details), default=0)

        ROW_INSTANSI, ROW_SPACE, ROW_NAME = 0, 1, 2
        table = self.doc.add_table(rows=3 + max_details, cols=num_cols)
        # Tinggi ruang tanda tangan disamakan dengan PDF lewat konstanta bersama.
        table.rows[ROW_SPACE].height = Mm(SIGNATURE_SPACE_MM)
        # Blok ini sengaja dirapatkan (permintaan owner 2026-08-18); tinggi baris
        # minimum tidak boleh membatalkannya.
        self._min_height_exempt.add(id(table._tbl))

        def _put(row_idx, col_idx, text, bold=False, underline=False):
            cell = table.rows[row_idx].cells[col_idx]
            cell.text = text or ''
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                # Spasi dirapatkan (permintaan owner): tanpa ini Word memakai
                # jarak antar-paragraf bawaan dan blok terasa renggang.
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                for run in para.runs:
                    run.bold = bold
                    run.underline = underline

        for col_idx, sig in enumerate(shown):
            _put(ROW_INSTANSI, col_idx, sig.get('instansi') or sig.get('position', ''), bold=True)
            _put(ROW_SPACE, col_idx, '')
            # Nama digarisbawahi sebagai penanda tanda tangan (R-21).
            _put(ROW_NAME, col_idx, sig.get('name', ''), bold=True, underline=True)
            for i in range(max_details):
                value = details[col_idx][i] if i < len(details[col_idx]) else ''
                _put(ROW_NAME + 1 + i, col_idx, value)

        # Instansi terbungkus beda panjang -> ratakan ke bawah agar ruang TTD sejajar.
        for cell in table.rows[ROW_INSTANSI].cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
    
    def _build_pengesahan_word_table(self, table_data: Dict[str, Any], col_widths: List = None):
        """
        Build dedicated 3-column table for REKAPITULASI RENCANA ANGGARAN BIAYA.
        
        This is separate from the generic table building to ensure pengesahan page
        only has 3 columns: No, Uraian Klasifikasi, Jumlah Harga
        
        Args:
            table_data: Dict with 'headers' and 'rows'
            col_widths: List of column widths in mm [15, 105, 70]
        """
        headers = table_data.get('headers', ['No', 'Uraian Pekerjaan', 'Jumlah Harga (Rp)'])
        rows = table_data.get('rows', [])
        
        if not rows:
            para = self.doc.add_paragraph("Tidak ada data")
            return
        
        # Default col widths if not provided
        if not col_widths:
            col_widths = [15, 105, 70]
        
        # Create table with exactly 3 columns
        num_cols = 3
        num_rows = len(rows) + 1  # +1 for header
        
        table = self.doc.add_table(rows=num_rows, cols=num_cols)
        table.style = 'Table Grid'
        
        # Header row
        for col_idx, header_text in enumerate(headers[:num_cols]):
            cell = table.rows[0].cells[col_idx]
            cell.text = str(header_text)
            if getattr(self, '_registry_active', False):
                # Fase 3.5: header navy putih — paritas pengesahan PDF
                self._style_header_cell(cell)
            else:
                # Style header cell (bold)
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.bold = True
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Data rows
        for row_idx, row_data in enumerate(rows):
            table_row = table.rows[row_idx + 1]
            
            # Get exactly 3 values
            if len(row_data) >= 3:
                values = [row_data[0], row_data[1], row_data[2]]
            elif len(row_data) == 2:
                values = ['', row_data[0], row_data[1]]
            else:
                values = [row_data[0] if row_data else '', '', '']
            
            for col_idx, value in enumerate(values):
                cell = table_row.cells[col_idx]
                cell.text = str(value) if value else ''
                
                # Column alignment
                for para in cell.paragraphs:
                    if col_idx == 0:  # No column - center
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    elif col_idx == 1:  # Uraian - left
                        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    else:  # Jumlah - right
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        # Set column widths
        for row in table.rows:
            for col_idx, cell in enumerate(row.cells):
                if col_idx < len(col_widths):
                    cell.width = Mm(col_widths[col_idx])
    
    # =========================================================================
    # COVER PAGE
    # =========================================================================
    
    def _build_cover_page(self, report_type: str, project_info: Dict[str, Any], 
                          period_info: Dict[str, Any] = None):
        """
        Build cover page with title and project identity.
        
        Args:
            report_type: 'rekap', 'monthly', or 'weekly'
            project_info: Project information dict
            period_info: Period info for monthly/weekly reports
        """
        # Title based on report type
        if report_type == 'rekap':
            title = 'REKAP LAPORAN JADWAL PEKERJAAN'
        elif report_type == 'monthly':
            month = period_info.get('month', 1) if period_info else 1
            title = f'LAPORAN BULAN KE-{month}'
        else:  # weekly
            week = period_info.get('week', 1) if period_info else 1
            title = f'LAPORAN MINGGU KE-{week}'
        
        # Add spacing at top
        for _ in range(3):
            self.doc.add_paragraph()
        
        # Main title
        title_para = self.doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(title)
        title_run.bold = True
        title_run.font.size = Pt(24)
        title_run.font.color.rgb = RGBColor.from_string(UTS.PRIMARY_LIGHT[1:])
        
        # Subtitle - Project name
        project_name = project_info.get('nama_project', self.config.project_name)
        if project_name:
            subtitle_para = self.doc.add_paragraph()
            subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle_run = subtitle_para.add_run(project_name)
            subtitle_run.bold = True
            subtitle_run.font.size = Pt(18)
        
        # Spacing
        self.doc.add_paragraph()
        self.doc.add_paragraph()
        
        # Project identity table
        identity_rows = build_identity_rows(self.config)
        if identity_rows:
            table = self.doc.add_table(rows=len(identity_rows), cols=3)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            
            for i, row_data in enumerate(identity_rows):
                row = table.rows[i]
                for j, cell_text in enumerate(row_data):
                    cell = row.cells[j]
                    cell.text = str(cell_text)
                    # Style
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.font.size = Pt(11)
    
    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    
    def _build_toc(self, sections: List[str]):
        """
        Build table of contents.
        
        Args:
            sections: List of section titles
        """
        # TOC Title
        toc_title = self.doc.add_paragraph()
        toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        toc_run = toc_title.add_run('DAFTAR ISI')
        toc_run.bold = True
        toc_run.font.size = Pt(16)
        
        self.doc.add_paragraph()
        
        # Section list
        for idx, section_name in enumerate(sections, 1):
            para = self.doc.add_paragraph()
            para.add_run(f'{idx}. {section_name}')
    
    # =========================================================================
    # SECTION HEADERS
    # =========================================================================
    
    def _apply_registry_base_styles(self):
        """Doc 32 Fase 3.1/3.2: font default dokumen (Arial, skala body) +
        named styles token — dokumen jadi 'native Word' (Navigation Pane
        hidup, edit user tidak merusak format)."""
        from .styles.tokens import FontFamily, TypeScale, ensure_word_styles
        normal = self.doc.styles['Normal']
        normal.font.name = FontFamily.WORD
        normal.font.size = Pt(TypeScale.BODY)
        ensure_word_styles(self.doc)

    def _build_identity_table(self):
        """Doc 32 Fase 3.4: blok identitas = tabel 3 kolom (Label : Nilai),
        struktur & lebar sama dengan PDF; caption 7pt, label bold."""
        from ..export_config import build_identity_rows
        from .styles.tokens import FontFamily, TypeScale

        identity_rows = build_identity_rows(self.config)
        table = self.doc.add_table(rows=len(identity_rows), cols=3)
        widths = (Mm(40), Mm(5), Mm(120))
        for r_idx, (label, sep, value) in enumerate(identity_rows):
            cells = table.rows[r_idx].cells
            for c_idx, text in enumerate((label, sep, str(value))):
                cell = cells[c_idx]
                cell.width = widths[c_idx]
                para = cell.paragraphs[0]
                para.paragraph_format.space_before = Pt(1)
                para.paragraph_format.space_after = Pt(1)
                run = para.add_run(str(text))
                run.font.name = FontFamily.WORD
                run.font.size = Pt(TypeScale.CAPTION)
                run.font.bold = (c_idx == 0)

    def _build_section_header(self, title: str):
        """
        Build section header with styling.

        Args:
            title: Section title text
        """
        if getattr(self, '_registry_active', False):
            # Fase 3.2: judul memakai named style token (16pt bold navy) +
            # spasi native via paragraph_format, bukan paragraf kosong
            from .styles.tokens import word_style_name
            para = self.doc.add_paragraph(title, style=word_style_name('doc_title'))
            para.paragraph_format.space_after = Pt(10)
            return

        para = self.doc.add_paragraph()
        run = para.add_run(title)
        run.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor.from_string(UTS.PRIMARY_LIGHT[1:])

        self.doc.add_paragraph()  # Spacing
    
    # =========================================================================
    # GRID TABLE
    # =========================================================================
    
    def _build_grid_table(self, page_data: Dict[str, Any], mode: str = 'planned'):
        """
        Build grid table with hierarchy styling.
        
        Args:
            page_data: Page data containing table_data, headers
            mode: 'planned' or 'actual'
        """
        table_data = page_data.get('table_data', {})
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        hierarchy_levels = page_data.get('hierarchy_levels', {})
        
        if not headers or not rows:
            return
        
        num_cols = len(headers)
        num_rows = len(rows) + 1  # +1 for header
        
        # Create table
        table = self.doc.add_table(rows=num_rows, cols=num_cols)
        table.style = 'Table Grid'
        
        # Header row
        header_row = table.rows[0]
        for col_idx, header_text in enumerate(headers):
            cell = header_row.cells[col_idx]
            cell.text = str(header_text)
            self._style_header_cell(cell)
        
        # Enable header repeat
        self._enable_header_repeat(table)
        
        # Data rows
        for row_idx, row_data in enumerate(rows):
            table_row = table.rows[row_idx + 1]
            level = hierarchy_levels.get(row_idx, 3)
            row_type = self._get_row_type_from_level(level)
            
            for col_idx, cell_value in enumerate(row_data):
                cell = table_row.cells[col_idx]
                
                # Skip 0% values to reduce clutter and file size
                display_value = ''
                if cell_value:
                    str_val = str(cell_value).strip()
                    # Skip if value is 0, 0%, 0.0, 0.0%, etc.
                    # Include both dot (.) and comma (,) decimal formats for Indonesian locale
                    zero_values = (
                        '0', '0%',
                        '0.0', '0.0%', '0.00', '0.00%', '0.000', '0.000%',
                        '0,0', '0,0%', '0,00', '0,00%', '0,000', '0,000%',
                    )
                    if str_val not in zero_values:
                        display_value = str_val
                cell.text = display_value
                
                # Apply hierarchy styling
                self._apply_hierarchy_style(cell, row_type, col_idx)
        
        # Set column widths
        self._set_grid_column_widths(table, num_cols)
        
        self.doc.add_paragraph()  # Spacing after table
    
    def _set_cell_top_border(self, cell, size_eighths: int, color_hex: str):
        """Garis atas satu sel. python-docx tidak menyediakan API border sel,
        jadi elemennya disusun langsung di XML."""
        tc_pr = cell._tc.get_or_add_tcPr()
        borders = tc_pr.find(qn('w:tcBorders'))
        if borders is None:
            borders = OxmlElement('w:tcBorders')
            tc_pr.append(borders)
        top = borders.find(qn('w:top'))
        if top is None:
            top = OxmlElement('w:top')
            borders.append(top)
        top.set(qn('w:val'), 'single')
        top.set(qn('w:sz'), str(size_eighths))  # satuan 1/8 pt
        top.set(qn('w:color'), color_hex.lstrip('#'))

    def _build_footer_table(self, footer_rows):
        """Blok total sebagai tabel rata kanan, paritas PDF `_build_footer_table`.

        W-2 (temuan owner 2026-08-18): sebelumnya baris total terbit sebagai
        paragraf biasa ("Total Biaya: 123"), sehingga Grand Total dan pembulatan
        terbaca sekadar teks dan tidak terasa sebagai kesimpulan dokumen. PDF
        memakai tabel dua kolom rata kanan dengan garis tipis di atas baris
        pertama dan garis TEBAL di atas baris terakhir; itu yang ditiru di sini.
        """
        rows = [r for r in footer_rows if r]
        if not rows:
            return None

        line_color = '1F3864'
        table = self.doc.add_table(rows=len(rows), cols=2)
        table.autofit = False
        table.alignment = WD_TABLE_ALIGNMENT.RIGHT

        for r_idx, footer in enumerate(rows):
            if isinstance(footer, (list, tuple)) and len(footer) >= 2:
                label, value = str(footer[0]), str(footer[1])
            else:
                label, value = str(footer), ''

            for c_idx, text in ((0, label), (1, value)):
                cell = table.rows[r_idx].cells[c_idx]
                cell.width = Mm(120) if c_idx == 0 else Mm(60)
                cell.text = text
                for para in cell.paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    para.paragraph_format.space_before = Pt(1)
                    para.paragraph_format.space_after = Pt(1)
                    for run in para.runs:
                        run.bold = True

        for cell in table.rows[0].cells:
            self._set_cell_top_border(cell, 8, line_color)   # 1 pt
        for cell in table.rows[-1].cells:
            self._set_cell_top_border(cell, 16, line_color)  # 2 pt, penegas total
        return table

    def _shade_cells(self, cells, fill_hex: str):
        """Beri warna latar (w:shd) pada kumpulan sel — util registry Fase 3."""
        for cell in cells:
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), fill_hex)
            cell._tc.get_or_add_tcPr().append(shading)

    def _style_header_cell(self, cell):
        """Apply header cell styling."""
        # Registry (Fase 3.5): navy tunggal + skala header 8pt; legacy tetap
        if getattr(self, '_registry_active', False):
            from .styles.tokens import Palette, TypeScale
            fill = Palette.HEADER_BG.lstrip('#').upper()
            header_pt = TypeScale.TABLE_HEADER
        else:
            fill = UTS.PRIMARY_LIGHT[1:]
            header_pt = 7

        # Background color
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), fill)
        cell._tc.get_or_add_tcPr().append(shading)

        # Text styling
        for para in cell.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in para.runs:
                run.bold = True
                run.font.size = Pt(header_pt)
                run.font.name = 'Arial'
                run.font.color.rgb = RGBColor(255, 255, 255)
    
    def _apply_hierarchy_style(self, cell, row_type: str, col_idx: int):
        """
        Apply hierarchy-based styling to cell.
        
        Args:
            cell: Table cell
            row_type: 'klasifikasi', 'sub_klasifikasi', or 'pekerjaan'
            col_idx: Column index
        """
        # Get background color and font settings
        # Font: Arial 7pt for data rows (per user request)
        if row_type == 'klasifikasi':
            bg_color = UTS.KLASIFIKASI_BG[1:]
            bold = True
            font_size = 8  # Slightly larger for main category
        elif row_type == 'sub_klasifikasi':
            bg_color = UTS.SUB_KLASIFIKASI_BG[1:]
            bold = True
            font_size = 7
        else:  # pekerjaan
            bg_color = 'FFFFFF'
            bold = False
            font_size = 7  # 7pt for data rows
        
        # Apply background
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), bg_color)
        cell._tc.get_or_add_tcPr().append(shading)
        
        # Text styling
        for para in cell.paragraphs:
            if col_idx == 0:  # Uraian column - left align
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:  # Other columns - center
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            for run in para.runs:
                run.bold = bold
                run.font.size = Pt(font_size)
                run.font.name = 'Arial'  # Base font Arial
    
    def _enable_header_repeat(self, table):
        """Enable table header row repeat on page breaks."""
        tbl = table._tbl
        for row in table.rows[:1]:
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            tblHeader = OxmlElement('w:tblHeader')
            trPr.append(tblHeader)
    
    def _set_grid_column_widths(self, table, num_cols: int):
        """
        Set appropriate column widths for grid table.
        
        Args:
            table: Word table object
            num_cols: Number of columns
        """
        # Static columns: Uraian, Volume, Satuan = 3 cols
        # Rest are week columns
        static_cols = 3
        week_cols = max(0, num_cols - static_cols)
        
        # Calculate widths
        uraian_width = Mm(JadwalExportLayout.COL_URAIAN)
        volume_width = Mm(JadwalExportLayout.COL_VOLUME)
        satuan_width = Mm(JadwalExportLayout.COL_SATUAN)
        
        # Week width - dynamic based on count
        min_week_mm = 4.2  # ~12pt
        max_week_mm = 15.9  # ~45pt
        
        if week_cols > 0:
            # Calculate available width (A3 landscape - margins - static cols)
            available_mm = 396 - JadwalExportLayout.COL_URAIAN - JadwalExportLayout.COL_VOLUME - JadwalExportLayout.COL_SATUAN
            week_width_mm = available_mm / week_cols
            week_width_mm = max(min_week_mm, min(max_week_mm, week_width_mm))
            week_width = Mm(week_width_mm)
        else:
            week_width = Mm(15)
        
        # Apply widths
        for row in table.rows:
            for col_idx, cell in enumerate(row.cells):
                if col_idx == 0:
                    cell.width = uraian_width
                elif col_idx == 1:
                    cell.width = volume_width
                elif col_idx == 2:
                    cell.width = satuan_width
                else:
                    cell.width = week_width
    
    def _get_row_type_from_level(self, level: int) -> str:
        """Convert hierarchy level to row type string."""
        if level == 1:
            return 'klasifikasi'
        elif level == 2:
            return 'sub_klasifikasi'
        else:
            return 'pekerjaan'
    
    # =========================================================================
    # ATTACHMENT IMAGE EMBEDDING
    # =========================================================================
    
    def _embed_attachment_image(self, attachment: Dict[str, Any]):
        """
        Embed attachment image into document.
        
        Used for Gantt charts and Kurva S rendered by frontend.
        
        Args:
            attachment: Dict with 'title', 'bytes' (base64), 'format'
        """
        import base64
        
        title = attachment.get('title', 'Chart')
        img_bytes = attachment.get('bytes', '')
        img_format = attachment.get('format', 'png')
        
        if not img_bytes:
            # Add placeholder text if no image
            para = self.doc.add_paragraph()
            para.add_run(f'[{title} - Image not available]')
            return
        
        try:
            image_data = None
            
            # Case 1: Already raw image bytes (PNG starts with \x89PNG)
            if isinstance(img_bytes, bytes):
                # Check if it's raw PNG (starts with \x89PNG) or JPEG (\xFF\xD8)
                if img_bytes[:4] == b'\x89PNG' or img_bytes[:2] == b'\xff\xd8':
                    # Already raw image bytes, use directly
                    image_data = img_bytes
                else:
                    # Might be base64 encoded as bytes, decode to string first
                    try:
                        img_str = img_bytes.decode('ascii')
                        # Remove data URL prefix if present
                        if img_str.startswith('data:'):
                            if ',' in img_str:
                                img_str = img_str.split(',', 1)[1]
                        image_data = base64.b64decode(img_str)
                    except (UnicodeDecodeError, Exception):
                        # Not valid base64, try using as-is
                        image_data = img_bytes
            
            # Case 2: String (base64 or data URL)
            elif isinstance(img_bytes, str):
                # Remove data URL prefix if present
                if img_bytes.startswith('data:'):
                    if ',' in img_bytes:
                        img_bytes = img_bytes.split(',', 1)[1]
                image_data = base64.b64decode(img_bytes)
            
            if not image_data:
                raise ValueError("Could not process image data")
            
            image_stream = BytesIO(image_data)
            
            # Add title
            title_para = self.doc.add_paragraph()
            title_run = title_para.add_run(title)
            title_run.bold = True
            title_run.font.size = Pt(10)
            title_run.font.name = 'Arial'
            
            # Add image - fit to page width (A3 landscape ~ 39cm usable width)
            # Use 35cm width to leave margins
            self.doc.add_picture(image_stream, width=Cm(35))
            
            # Add spacing after image
            self.doc.add_paragraph()
            
        except Exception as e:
            # WP-B5 inc-B5a: never put exception text in the document. Log under a
            # correlation ID and show a safe placeholder referencing it.
            from .errors import log_export_error
            cid = log_export_error(e, context=f"embed image: {title}")
            para = self.doc.add_paragraph()
            para.add_run(f'[{title} — gambar gagal dimuat. Ref: {cid}]')
    
    # =========================================================================
    # KURVA S SECTION
    # =========================================================================
    
    def _build_kurva_s_section(self, kurva_s_data: List[Dict], data: Dict[str, Any]):
        """
        Build Kurva S section (table-based visualization).
        
        Args:
            kurva_s_data: Chart data points
            data: Full export data
        """
        # For now, create a simple summary table
        # TODO: Add chart image or table-based visualization
        
        if not kurva_s_data:
            return
        
        para = self.doc.add_paragraph()
        para.add_run('Kurva S data visualization will be added here.')
        
        # Create simple data table
        num_weeks = len(kurva_s_data)
        table = self.doc.add_table(rows=3, cols=min(num_weeks + 1, 20))
        table.style = 'Table Grid'
        
        # Headers
        table.rows[0].cells[0].text = 'Minggu'
        table.rows[1].cells[0].text = 'Rencana (%)'
        table.rows[2].cells[0].text = 'Realisasi (%)'
        
        # Data
        for idx, week_data in enumerate(kurva_s_data[:19]):
            col_idx = idx + 1
            if col_idx < len(table.rows[0].cells):
                table.rows[0].cells[col_idx].text = str(week_data.get('week', idx + 1))
                table.rows[1].cells[col_idx].text = f"{week_data.get('planned', 0):.1f}"
                table.rows[2].cells[col_idx].text = f"{week_data.get('actual', 0):.1f}"
    
    # =========================================================================
    # PROGRESS PAGE
    # =========================================================================
    
    def _build_progress_page(self, period: int, project_info: Dict[str, Any],
                             summary: Dict[str, Any], hierarchy_data: List[Dict],
                             mode: str = 'monthly'):
        """
        Build progress page for monthly/weekly reports.
        
        Args:
            period: Month or week number
            project_info: Project information
            summary: Executive summary data
            hierarchy_data: Hierarchy progress data
            mode: 'monthly' or 'weekly'
        """
        period_label = 'Bulan' if mode == 'monthly' else 'Minggu'
        
        # Section title
        self._build_section_header(f'PROGRESS PELAKSANAAN - {period_label} ke-{period}')
        
        # Summary table
        if summary:
            self._build_summary_table(summary)
            self.doc.add_paragraph()
        
        # Hierarchy progress table
        if hierarchy_data:
            self._build_hierarchy_progress_table(hierarchy_data)
    
    def _build_summary_table(self, summary: Dict[str, Any]):
        """Build executive summary table."""
        table = self.doc.add_table(rows=4, cols=2)
        table.style = 'Table Grid'
        
        data = [
            ('Progress Rencana', f"{summary.get('planned_progress', 0):.2f}%"),
            ('Progress Realisasi', f"{summary.get('actual_progress', 0):.2f}%"),
            ('Deviasi', f"{summary.get('deviation', 0):.2f}%"),
            ('Status', summary.get('status', '-')),
        ]
        
        for idx, (label, value) in enumerate(data):
            table.rows[idx].cells[0].text = label
            table.rows[idx].cells[1].text = str(value)
    
    def _build_hierarchy_progress_table(self, hierarchy_data: List[Dict]):
        """Build hierarchy progress detail table."""
        if not hierarchy_data:
            return
        
        # Create table with hierarchy data
        table = self.doc.add_table(rows=len(hierarchy_data) + 1, cols=4)
        table.style = 'Table Grid'
        
        # Headers
        headers = ['Uraian', 'Rencana (%)', 'Realisasi (%)', 'Deviasi (%)']
        for idx, header in enumerate(headers):
            table.rows[0].cells[idx].text = header
            self._style_header_cell(table.rows[0].cells[idx])
        
        # Data rows
        for row_idx, item in enumerate(hierarchy_data):
            row = table.rows[row_idx + 1]
            row.cells[0].text = item.get('name', '')
            row.cells[1].text = f"{item.get('planned', 0):.2f}"
            row.cells[2].text = f"{item.get('actual', 0):.2f}"
            row.cells[3].text = f"{item.get('deviation', 0):.2f}"

    # =========================================================================
    # DAILY DOCX EXPORT HELPERS
    # =========================================================================

    def _daily_work_rows_per_page(self) -> int:
        # 24 baris + identitas + ruang TTD 2.2cm masih muat 1 halaman A4 portrait.
        return 24

    def _setup_daily_doc_styles(self):
        styles = self.doc.styles
        styles['Normal'].font.name = 'Arial'
        styles['Normal'].font.size = Pt(8)
        for style_name in ('Heading 1', 'Heading 2'):
            style = styles[style_name]
            style.font.name = 'Arial'
            style.font.bold = True
            style.font.color.rgb = RGBColor(17, 24, 39)

    def _paragraph_text_from_element(self, element) -> str:
        return ''.join(t.text or '' for t in element.findall('.//' + qn('w:t')))

    def _is_heading_element(self, element) -> bool:
        if element.tag != qn('w:p'):
            return False
        p_style = element.find('.//' + qn('w:pStyle'))
        if p_style is None:
            return False
        style_val = p_style.get(qn('w:val')) or ''
        return style_val.startswith('Heading')

    def _extract_daily_doc_block(self, doc: Document, start_heading: str) -> list:
        children = list(doc._body._element)
        start_index = None
        for idx, child in enumerate(children):
            if child.tag == qn('w:p') and self._paragraph_text_from_element(child).strip() == start_heading:
                start_index = idx
                break
        if start_index is None:
            return []

        end_index = len(children)
        for idx in range(start_index + 1, len(children)):
            if self._is_heading_element(children[idx]):
                end_index = idx
                break
        block = [deepcopy(child) for child in children[start_index:end_index] if child.tag != qn('w:sectPr')]
        while block and self._is_trailing_empty_or_page_break_paragraph(block[-1]):
            block.pop()
        return block

    def _is_trailing_empty_or_page_break_paragraph(self, element) -> bool:
        if element.tag != qn('w:p'):
            return False
        text = self._paragraph_text_from_element(element).strip()
        if text:
            return False
        page_breaks = [
            br for br in element.findall('.//' + qn('w:br'))
            if br.get(qn('w:type')) == 'page'
        ]
        return bool(page_breaks) or not list(element.findall('.//' + qn('w:drawing')))

    def _clear_doc_body_preserve_section(self, doc: Document):
        body = doc._body._element
        sect_pr = body.sectPr
        for child in list(body):
            body.remove(child)
        if sect_pr is not None:
            body.append(sect_pr)

    def _append_daily_documentation_block(self, block: list, report: Dict[str, Any]):
        body = self.doc._body._element
        sect_pr = body.sectPr
        if sect_pr is not None:
            body.remove(sect_pr)

        sheet_name = report.get('sheet_name') or self._daily_sheet_label(report)
        replacements = {
            '01 JAN - Dokumentasi': f'{sheet_name} - Dokumentasi',
            'Kamis, 01 Januari 2026 | Minggu 1': self._daily_subtitle(report),
        }
        for element in [deepcopy(element) for element in block]:
            self._replace_text_in_element(element, replacements)
            body.append(element)
        if sect_pr is not None:
            body.append(sect_pr)

    def _daily_normalize_drawing_ids(self):
        """Make copied drawing identifiers unique for Microsoft Word.

        Word is stricter than python-docx about duplicated DrawingML IDs. The
        documentation template block may be copied many times, so each copied
        SmartArt/drawing needs unique wp:docPr id, wp14:anchorId, and
        wp14:editId values.
        """
        root = self.doc._body._element
        wp_docpr = qn('wp:docPr')
        wp14_ns = 'http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing'
        anchor_attr = f'{{{wp14_ns}}}anchorId'
        edit_attr = f'{{{wp14_ns}}}editId'
        for index, doc_pr in enumerate(root.findall('.//' + wp_docpr), start=1):
            doc_pr.set('id', str(index))
        anchor_index = 1
        edit_index = 1
        for element in root.iter():
            if anchor_attr in element.attrib:
                element.set(anchor_attr, f'{anchor_index:08X}')
                anchor_index += 1
            if edit_attr in element.attrib:
                element.set(edit_attr, f'{(edit_index + 1048576):08X}')
                edit_index += 1

    def _replace_text_in_element(self, element, replacements: Dict[str, str]):
        for text_node in element.findall('.//' + qn('w:t')):
            if not text_node.text:
                continue
            value = text_node.text
            for old, new in replacements.items():
                value = value.replace(old, new)
            text_node.text = value

    def _daily_add_heading(self, text: str, level: int = 1):
        paragraph = self.doc.add_paragraph(style=f'Heading {level}')
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(3)
        run = paragraph.add_run(text)
        run.font.name = 'Arial'
        run.font.size = Pt(11 if level == 1 else 9)
        run.font.bold = True

    def _daily_add_title(self, title: str, subtitle: str):
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(title)
        run.bold = True
        run.font.size = Pt(13)

        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(4)
        run = paragraph.add_run(subtitle)
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(90, 90, 90)

    def _daily_add_identity(self, project_info: Dict[str, Any], report: Dict[str, Any]):
        # Tanggal & minggu sudah di subjudul; kontraktor & konsultan di pengesahan —
        # tabel identitas hanya memuat yang belum tampil di tempat lain.
        table = self.doc.add_table(rows=4, cols=5)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        self._daily_set_col_widths(table, [3.2, 6.4, 2.2, 2.9, 3.3])
        self._daily_set_table_borders(table, '6B7280', '4')

        previous = self._daily_progress_values(report)
        current = self._daily_current_target_values(report)
        previous_week = report.get('previous_week')
        rows = [
            ('Proyek :', self._project_value(project_info, 'nama_proyek', 'name', 'nama', default=self.config.project_name),
             'Progress Kumulatif',
             f"s.d. Minggu {previous_week}" if previous_week else "Awal Proyek",
             f"s.d. Minggu {report.get('week_number') or '-'}"),
            ('Lokasi :', self._project_value(project_info, 'lokasi', 'location', default=self.config.location),
             'Rencana :', previous[0], current[0]),
            ('Cuaca :', '__________',
             'Realisasi :', previous[1], current[1]),
            ('Pemilik/Penanggung Jawab Project :', self._project_value(project_info, 'owner', 'nama_client', 'instansi', default=self.config.owner),
             'Deviasi :', previous[2], current[2]),
        ]
        for row_idx, row_values in enumerate(rows):
            for col_idx, value in enumerate(row_values):
                cell = table.cell(row_idx, col_idx)
                is_label = col_idx in (0, 2)
                is_progress_header = row_idx == 0 and col_idx >= 2
                if col_idx >= 3:
                    align = WD_ALIGN_PARAGRAPH.CENTER if row_idx == 0 else WD_ALIGN_PARAGRAPH.RIGHT
                else:
                    align = None
                self._daily_set_cell_text(cell, value, bold=is_label or is_progress_header, size=7, align=align)
                if is_progress_header:
                    self._daily_set_cell_shading(cell, 'E5E7EB')
                elif is_label:
                    self._daily_set_cell_shading(cell, 'F3F4F6')

    def _daily_add_work_table(self, items: List[Dict[str, Any]], page_index: int, page_count: int):
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(4)
        paragraph.paragraph_format.space_after = Pt(2)
        run = paragraph.add_run(f"Pekerjaan yang Dilaksanakan Hari Ini ({page_index}/{page_count})")
        run.bold = True
        run.font.size = Pt(9)

        table = self.doc.add_table(rows=1 + len(items), cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        self._daily_set_col_widths(table, [1.0, 11.4, 5.6])
        self._daily_set_table_borders(table, '6B7280', '4')
        for idx, header in enumerate(['No', 'Uraian Pekerjaan', 'Keterangan / Hambatan']):
            self._daily_set_cell_text(table.cell(0, idx), header, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color='FFFFFF', size=8)
            self._daily_set_cell_shading(table.cell(0, idx), '374151')

        offset = ((page_index - 1) * self._daily_work_rows_per_page()) + 1
        for idx, item in enumerate(items, start=1):
            row = table.rows[idx]
            row.height = Cm(0.72)
            self._daily_set_cell_text(row.cells[0], offset + idx - 1, align=WD_ALIGN_PARAGRAPH.CENTER, size=8)
            self._daily_set_cell_text(row.cells[1], item.get('uraian') or item.get('name') or '', size=8)
            self._daily_set_cell_text(row.cells[2], item.get('keterangan') or item.get('note') or '', size=8)

    def _daily_add_signatures(self):
        """Pengesahan laporan harian: Kontraktor + Konsultan Pengawas (R-32).

        Susunan sama dengan blok baku (R-37): INSTANSI / ruang TTD / NAMA
        (digarisbawahi) / keterangan. Data dari ``config.signature_config``.
        """
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(12)
        paragraph.paragraph_format.space_after = Pt(0)
        signatures = self._daily_signature_entries()
        details = [sig.get('details') or [] for sig in signatures]
        max_details = max((len(d) for d in details), default=0)

        table = self.doc.add_table(rows=3 + max_details, cols=len(signatures))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        self._daily_set_col_widths(table, [9.0] * len(signatures))
        # Ruang tanda tangan basah + stempel.
        table.rows[1].height = Cm(2.2)
        for idx, signature in enumerate(signatures):
            self._daily_set_cell_text(table.cell(0, idx), signature.get('instansi') or '', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=8)
            table.cell(0, idx).vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
            self._daily_set_cell_text(table.cell(1, idx), '', align=WD_ALIGN_PARAGRAPH.CENTER, size=8)
            name = signature.get('name') or '............................'
            self._daily_set_cell_text(table.cell(2, idx), name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=8)
            for run in table.cell(2, idx).paragraphs[0].runs:
                run.underline = True
            for i in range(max_details):
                value = details[idx][i] if i < len(details[idx]) else ''
                self._daily_set_cell_text(table.cell(3 + i, idx), value, align=WD_ALIGN_PARAGRAPH.CENTER, size=8)
        self._daily_set_table_borders(table, 'FFFFFF', '0')

    def _daily_signature_entries(self) -> List[Dict[str, Any]]:
        sig_config = getattr(self.config, 'signature_config', None)
        signatures = list(sig_config.signatures or []) if sig_config and sig_config.enabled else []
        by_role = {sig.get('role'): sig for sig in signatures}
        return [
            by_role.get('kontraktor') or {'role': 'kontraktor'},
            by_role.get('pengawas') or {'role': 'pengawas'},
        ]

    def _daily_add_photo_fallback(self):
        table = self.doc.add_table(rows=2, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        self._daily_set_col_widths(table, [8.9, 8.9])
        self._daily_set_table_borders(table, '374151', '8')
        labels = ['Foto 1', 'Foto 2', 'Foto 3', 'Foto 4']
        for row in table.rows:
            row.height = Cm(10.0)
        for idx, cell in enumerate([table.cell(0, 0), table.cell(0, 1), table.cell(1, 0), table.cell(1, 1)]):
            self._daily_set_cell_shading(cell, 'F3F4F6')
            self._daily_set_cell_text(
                cell,
                f"{labels[idx]}\nInsert > Pictures > This Device\nLetakkan foto di dalam frame",
                bold=True,
                size=9,
                align=WD_ALIGN_PARAGRAPH.CENTER,
                color='6B7280',
            )

    def _daily_set_cell_text(self, cell, text, bold=False, size=8, align=None, color=None):
        cell.text = ''
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        if align is not None:
            paragraph.alignment = align
        run = paragraph.add_run(str(text))
        run.bold = bold
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = RGBColor.from_string(color)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    def _daily_set_cell_shading(self, cell, fill: str):
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = tc_pr.find(qn('w:shd'))
        if shd is None:
            shd = OxmlElement('w:shd')
            tc_pr.append(shd)
        shd.set(qn('w:fill'), fill)

    def _daily_set_cell_border(self, cell, color='000000', size='6', val='single'):
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_borders = tc_pr.first_child_found_in('w:tcBorders')
        if tc_borders is None:
            tc_borders = OxmlElement('w:tcBorders')
            tc_pr.append(tc_borders)
        for edge in ('top', 'left', 'bottom', 'right'):
            tag = f'w:{edge}'
            element = tc_borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tc_borders.append(element)
            element.set(qn('w:val'), val)
            element.set(qn('w:sz'), size)
            element.set(qn('w:space'), '0')
            element.set(qn('w:color'), color)

    def _daily_set_table_borders(self, table, color='000000', size='4'):
        for row in table.rows:
            for cell in row.cells:
                self._daily_set_cell_border(cell, color=color, size=size)

    def _daily_set_col_widths(self, table, widths_cm: List[float]):
        # tblGrid ikut diset: LibreOffice/Google Docs membaca grid, bukan tcW.
        for grid_col, width in zip(table._tbl.tblGrid.findall(qn('w:gridCol')), widths_cm):
            grid_col.set(qn('w:w'), str(Cm(width).twips))
        for row in table.rows:
            for idx, width in enumerate(widths_cm):
                if idx < len(row.cells):
                    row.cells[idx].width = Cm(width)

    def _project_value(self, project_info: Dict[str, Any], *keys: str, default: Any = ''):
        for key in keys:
            value = project_info.get(key)
            if value not in (None, ''):
                return value
        return default or '-'

    def _daily_sheet_label(self, report: Dict[str, Any]) -> str:
        report_date = report.get('date')
        if report_date:
            month_labels = {
                1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MEI', 6: 'JUN',
                7: 'JUL', 8: 'AGU', 9: 'SEP', 10: 'OKT', 11: 'NOV', 12: 'DES',
            }
            return f"{report_date.day:02d} {month_labels.get(report_date.month, '')}".strip()
        return report.get('sheet_name') or 'LAPORAN'

    def _daily_date_text(self, report: Dict[str, Any]) -> str:
        report_date = report.get('date')
        if not report_date:
            return '-'
        month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember',
        }
        return f"{report_date.day:02d} {month_names.get(report_date.month, '')} {report_date.year}"

    def _daily_day_name(self, report: Dict[str, Any]) -> str:
        report_date = report.get('date')
        if not report_date:
            return '-'
        day_names = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        return day_names[report_date.weekday()]

    def _daily_subtitle(self, report: Dict[str, Any]) -> str:
        week = report.get('week_number')
        week_text = f"Minggu {week}" if week else "Minggu -"
        return f"{self._daily_day_name(report)}, {self._daily_date_text(report)} | {week_text}"

    def _daily_progress_values(self, report: Dict[str, Any]) -> tuple[str, str, str]:
        progress = report.get('previous_progress') or report.get('progress_previous_week') or {}
        return (
            self._daily_percent(progress.get('planned')),
            self._daily_percent(progress.get('actual')),
            self._daily_percent(progress.get('deviation'), signed=True),
        )

    def _daily_current_target_values(self, report: Dict[str, Any]) -> tuple[str, str, str]:
        """Minggu berjalan: hanya target rencana kumulatif (+target minggu ini).

        Realisasi & deviasi minggu ini belum diketahui saat laporan dibuat.
        """
        target = report.get('current_week_target') or {}
        planned = self._daily_percent(target.get('planned'))
        if planned != '-' and target.get('planned_week') is not None:
            planned = f"{planned} ({self._daily_percent(target.get('planned_week'), signed=True)})"
        return planned, '-', '-'

    def _daily_percent(self, value, signed: bool = False) -> str:
        if value is None:
            return '-'
        try:
            numeric = float(value) * 100
        except (TypeError, ValueError):
            return '-'
        if signed and numeric > 0:
            return f"+{numeric:.2f}%"
        return f"{numeric:.2f}%"

    def _create_daily_response(self, reports: List[Dict[str, Any]]) -> HttpResponse:
        self._apply_min_row_heights()

        buffer = BytesIO()
        self.doc.save(buffer)
        content = self._daily_deduplicate_smartart_package(buffer.getvalue())

        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        export_filename = self._daily_export_filename(reports)
        response['Content-Disposition'] = f'attachment; filename="{export_filename}"'
        return response

    def _daily_export_filename(self, reports: List[Dict[str, Any]]) -> str:
        import re

        dates = sorted(
            report.get('date')
            for report in (reports or [])
            if report.get('date')
        )
        if not dates:
            return 'Laporan_Harian.docx'

        start = dates[0]
        end = dates[-1]
        start_text = start.strftime('%d-%m')
        end_text = end.strftime('%d-%m')
        if start == end:
            label = f'Laporan Harian {start_text}'
        else:
            label = f'Laporan Harian {start_text} - {end_text}'
        safe_label = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', '-', label).strip(' .-')
        safe_label = re.sub(r'\\s+', ' ', safe_label)
        return f'{safe_label or "Laporan Harian"}.docx'

    def _daily_deduplicate_smartart_package(self, content: bytes) -> bytes:
        """Duplicate SmartArt diagram parts per instance.

        Copying a documentation page duplicates DrawingML references. Microsoft
        Word rejects the resulting DOCX when several SmartArt instances share
        the same diagram relationship/part. This rewrites every dgm:relIds node
        to unique relationships and copied diagram parts.
        """
        from zipfile import ZipFile, ZIP_DEFLATED
        from lxml import etree
        import re
        import uuid

        rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
        r_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        dgm_ns = 'http://schemas.openxmlformats.org/drawingml/2006/diagram'
        ct_ns = 'http://schemas.openxmlformats.org/package/2006/content-types'

        with ZipFile(BytesIO(content), 'r') as zin:
            files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

        if 'word/document.xml' not in files or 'word/_rels/document.xml.rels' not in files:
            return content

        doc = etree.fromstring(files['word/document.xml'])
        rels = etree.fromstring(files['word/_rels/document.xml.rels'])
        content_types = etree.fromstring(files['[Content_Types].xml']) if '[Content_Types].xml' in files else None
        rel_nodes = rels.findall(f'{{{rel_ns}}}Relationship')
        if not any((rel.get('Type') or '').endswith('diagramData') for rel in rel_nodes):
            return content

        def build_rel_map():
            return {rel.get('Id'): rel for rel in rels.findall(f'{{{rel_ns}}}Relationship')}

        def next_rid():
            numbers = []
            for rel in rels.findall(f'{{{rel_ns}}}Relationship'):
                rid = rel.get('Id', '')
                if rid.startswith('rId') and rid[3:].isdigit():
                    numbers.append(int(rid[3:]))
            candidate = max(numbers or [0]) + 1
            current = build_rel_map()
            while f'rId{candidate}' in current:
                candidate += 1
            return f'rId{candidate}'

        def add_relationship(rid, rel_type, target):
            element = etree.Element(f'{{{rel_ns}}}Relationship')
            element.set('Id', rid)
            element.set('Type', rel_type)
            element.set('Target', target)
            rels.append(element)

        def copy_part(old_target, new_target):
            old_name = 'word/' + old_target
            new_name = 'word/' + new_target
            if old_name not in files:
                return False
            files[new_name] = files[old_name]
            new_content_type_overrides.append('/' + new_name)
            return True

        counters = {'data': 0, 'layout': 0, 'quickStyle': 0, 'colors': 0, 'drawing': 0}
        new_content_type_overrides = []
        rmap = build_rel_map()
        rel_id_nodes = doc.findall(f'.//{{{dgm_ns}}}relIds')
        for node in rel_id_nodes:
            old_data_rid = node.get(f'{{{r_ns}}}dm')
            old_data_rel = rmap.get(old_data_rid)
            if old_data_rel is None:
                continue

            old_data_target = old_data_rel.get('Target')
            old_data_name = 'word/' + old_data_target
            old_data_text = files.get(old_data_name, b'').decode('utf-8', errors='ignore')
            drawing_match = re.search(r'relId="(rId\d+)"', old_data_text)
            old_drawing_rid = drawing_match.group(1) if drawing_match else None
            new_drawing_rid = None
            new_drawing_target = None
            if old_drawing_rid and old_drawing_rid in rmap:
                old_drawing_rel = rmap[old_drawing_rid]
                counters['drawing'] += 1
                new_drawing_target = f'diagrams/drawing_auto{counters["drawing"]}.xml'
                if copy_part(old_drawing_rel.get('Target'), new_drawing_target):
                    new_drawing_rid = next_rid()
                    add_relationship(new_drawing_rid, old_drawing_rel.get('Type'), new_drawing_target)
                    rmap = build_rel_map()

            copied_data_target = None
            copied_drawing_target = new_drawing_target
            for attr_name, kind in (
                (f'{{{r_ns}}}dm', 'data'),
                (f'{{{r_ns}}}lo', 'layout'),
                (f'{{{r_ns}}}qs', 'quickStyle'),
                (f'{{{r_ns}}}cs', 'colors'),
            ):
                old_rid = node.get(attr_name)
                old_rel = rmap.get(old_rid)
                if old_rel is None:
                    continue
                counters[kind] += 1
                new_target = f'diagrams/{kind}_auto{counters[kind]}.xml'
                if not copy_part(old_rel.get('Target'), new_target):
                    continue
                new_rid = next_rid()
                add_relationship(new_rid, old_rel.get('Type'), new_target)
                node.set(attr_name, new_rid)
                if kind == 'data':
                    copied_data_target = new_target
                if kind == 'data' and new_drawing_rid:
                    data_name = 'word/' + new_target
                    data_text = files[data_name].decode('utf-8', errors='ignore')
                    data_text = re.sub(r'relId="rId\d+"', f'relId="{new_drawing_rid}"', data_text, count=1)
                    files[data_name] = data_text.encode('utf-8')
                rmap = build_rel_map()

            if copied_data_target and copied_drawing_target:
                data_name = 'word/' + copied_data_target
                drawing_name = 'word/' + copied_drawing_target
                combined_text = ''
                if data_name in files:
                    combined_text += files[data_name].decode('utf-8', errors='ignore')
                if drawing_name in files:
                    combined_text += files[drawing_name].decode('utf-8', errors='ignore')
                guid_map = {
                    guid: '{' + str(uuid.uuid4()).upper() + '}'
                    for guid in set(re.findall(r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}', combined_text))
                }
                for part_name in (data_name, drawing_name):
                    if part_name not in files:
                        continue
                    part_text = files[part_name].decode('utf-8', errors='ignore')
                    for old_guid, new_guid in guid_map.items():
                        part_text = part_text.replace(old_guid, new_guid)
                    files[part_name] = part_text.encode('utf-8')

        files['word/document.xml'] = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
        files['word/_rels/document.xml.rels'] = etree.tostring(rels, xml_declaration=True, encoding='UTF-8', standalone=True)
        if content_types is not None and new_content_type_overrides:
            content_type_by_prefix = {
                'data': 'application/vnd.openxmlformats-officedocument.drawingml.diagramData+xml',
                'layout': 'application/vnd.openxmlformats-officedocument.drawingml.diagramLayout+xml',
                'quickStyle': 'application/vnd.openxmlformats-officedocument.drawingml.diagramStyle+xml',
                'colors': 'application/vnd.openxmlformats-officedocument.drawingml.diagramColors+xml',
                'drawing': 'application/vnd.ms-office.drawingml.diagramDrawing+xml',
            }
            existing_parts = {
                override.get('PartName')
                for override in content_types.findall(f'{{{ct_ns}}}Override')
            }
            for part_name in new_content_type_overrides:
                filename = part_name.rsplit('/', 1)[-1]
                prefix = filename.split('_auto', 1)[0]
                content_type = content_type_by_prefix.get(prefix)
                if not content_type or part_name in existing_parts:
                    continue
                override = etree.Element(f'{{{ct_ns}}}Override')
                override.set('PartName', part_name)
                override.set('ContentType', content_type)
                content_types.append(override)
                existing_parts.add(part_name)
            files['[Content_Types].xml'] = etree.tostring(content_types, xml_declaration=True, encoding='UTF-8', standalone=True)

        output = BytesIO()
        with ZipFile(output, 'w', ZIP_DEFLATED) as zout:
            for name, data in files.items():
                zout.writestr(name, data)
        return output.getvalue()

    # =========================================================================
    # RESPONSE CREATION
    # =========================================================================
    
    def _apply_min_row_heights(self):
        """Terapkan tinggi baris MINIMUM ke semua tabel (keputusan owner 2026-09-22).

        Word tidak menyimpan tinggi baris kecuali diminta, sehingga kerapatannya
        ditentukan tema dokumen -- bukan oleh kita. `AT_LEAST` menetapkan lantai
        tanpa memotong isi: baris dengan uraian panjang tetap boleh lebih tinggi.

        Dipasang di `_create_response` karena itu satu-satunya titik yang dilalui
        SEMUA jalur export; memasangnya per `add_table` berarti menyentuh belasan
        tempat dan pasti ada yang terlewat.
        """
        from docx.enum.table import WD_ROW_HEIGHT_RULE
        from docx.shared import Cm

        from .table_styles import ROW_MIN_HEIGHT_CM, ROW_MIN_HEIGHT_RINCIAN_CM

        floor = Cm(
            ROW_MIN_HEIGHT_RINCIAN_CM if getattr(self, '_is_rincian_doc', False)
            else ROW_MIN_HEIGHT_CM
        )
        exempt = getattr(self, '_min_height_exempt', set())
        for table in self.doc.tables:
            if id(table._tbl) in exempt:
                continue
            for row in table.rows:
                # Jangan turunkan tinggi yang sudah ditetapkan lebih besar
                # (mis. ruang tanda tangan basah).
                if row.height is not None and row.height >= floor:
                    continue
                row.height = floor
                row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST

    def _create_response(self, filename: str) -> HttpResponse:
        """
        Create HTTP response with Word document.
        
        Args:
            filename: Base filename (without extension)
            
        Returns:
            HttpResponse with .docx attachment
        """
        self._apply_min_row_heights()

        buffer = BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        from .naming import build_export_filename
        export_filename = build_export_filename(
            self.config.project_name,
            filename,
            "docx",
            self.config.export_date,
        )
        response['Content-Disposition'] = f'attachment; filename="{export_filename}"'
        
        return response
