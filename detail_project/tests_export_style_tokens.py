"""Doc 32 Fase 1.1/1.4 — style registry semantik + helper alignment.

Termasuk test penjaga (guard) bahwa nilai konstanta legacy TIDAK berubah:
kontrak behavior-preserving Fase 1 (koreksi review Codex atas rencana alias
v1.0 — konsumen legacy harus tetap menerima nilai lama).
"""
from django.test import SimpleTestCase

from detail_project.exports.styles.alignment import alignment_for_columns
from detail_project.exports.styles.tokens import (
    REGISTRY,
    FontFamily,
    Palette,
    TypeScale,
    ensure_word_styles,
    leading_for,
    pdf_paragraph_style,
    word_style_name,
)


class AlignmentHelperTests(SimpleTestCase):
    def test_numeric_formats_align_right(self):
        aligns = alignment_for_columns(
            ['No', 'Uraian', 'Volume', 'Harga Satuan', 'Jumlah'],
            ['@', '@', '#,##0.000', '#,##0.00', '#,##0.00'],
        )
        self.assertEqual(aligns, ['CENTER', 'LEFT', 'RIGHT', 'RIGHT', 'RIGHT'])

    def test_text_headers_no_kode_satuan_center(self):
        aligns = alignment_for_columns(
            ['Kode', 'Uraian', 'Satuan'],
            ['@', '@', '@'],
        )
        self.assertEqual(aligns, ['CENTER', 'LEFT', 'CENTER'])

    def test_header_with_trailing_dot_and_case(self):
        aligns = alignment_for_columns(['NO.', 'URAIAN'], ['@', '@'])
        self.assertEqual(aligns, ['CENTER', 'LEFT'])

    def test_table_without_column_formats_returns_none(self):
        self.assertIsNone(alignment_for_columns(['A', 'B'], None))
        self.assertIsNone(alignment_for_columns(['A', 'B'], []))

    def test_formats_shorter_than_headers_fall_back_to_text(self):
        aligns = alignment_for_columns(
            ['Uraian', 'Jumlah', 'Keterangan'],
            ['@', '#,##0.00'],
        )
        self.assertEqual(aligns, ['LEFT', 'RIGHT', 'LEFT'])

    def test_formats_longer_than_headers_still_covered(self):
        aligns = alignment_for_columns(['Uraian'], ['@', '#,##0.00'])
        self.assertEqual(aligns, ['LEFT', 'RIGHT'])


class TokenRegistryTests(SimpleTestCase):
    def test_registry_has_all_semantic_roles(self):
        for key in ('doc_title', 'section_heading', 'table_header', 'text_cell',
                    'money_cell', 'code_cell', 'total_row', 'caption'):
            self.assertIn(key, REGISTRY)

    def test_type_scale_matches_doc32(self):
        self.assertEqual(TypeScale.DOC_TITLE, 16)
        self.assertEqual(TypeScale.SECTION_HEADING, 11)
        self.assertEqual(TypeScale.BODY, 8)
        self.assertEqual(TypeScale.CAPTION, 7)

    def test_money_cell_is_right_aligned_body_size(self):
        tok = REGISTRY['money_cell']
        self.assertEqual(tok.align, 'RIGHT')
        self.assertEqual(tok.size, TypeScale.BODY)
        self.assertFalse(tok.bold)

    def test_leading_is_ceil_1_25x(self):
        self.assertEqual(leading_for(8), 10)
        self.assertEqual(leading_for(7), 9)   # ceil(8.75)
        self.assertEqual(leading_for(16), 20)


class PdfAdapterTests(SimpleTestCase):
    def test_style_is_cached_same_instance(self):
        self.assertIs(pdf_paragraph_style('money_cell'),
                      pdf_paragraph_style('money_cell'))

    def test_style_values_follow_token(self):
        from reportlab.lib.enums import TA_RIGHT
        style = pdf_paragraph_style('money_cell')
        self.assertEqual(style.fontName, FontFamily.PDF_REGULAR)
        self.assertEqual(style.fontSize, TypeScale.BODY)
        self.assertEqual(style.alignment, TA_RIGHT)

    def test_bold_token_uses_bold_font(self):
        style = pdf_paragraph_style('doc_title')
        self.assertEqual(style.fontName, FontFamily.PDF_BOLD)


class WordAdapterTests(SimpleTestCase):
    def test_styles_registered_and_idempotent(self):
        from docx import Document
        doc = Document()
        mapping1 = ensure_word_styles(doc)
        n_styles = len(doc.styles)
        mapping2 = ensure_word_styles(doc)  # panggilan kedua tidak menduplikasi
        self.assertEqual(mapping1, mapping2)
        self.assertEqual(len(doc.styles), n_styles)

        style = doc.styles[word_style_name('doc_title')]
        self.assertEqual(style.font.name, FontFamily.WORD)
        self.assertTrue(style.font.bold)


class LegacyValuesUntouchedGuardTests(SimpleTestCase):
    """Fase 1 TIDAK boleh mengubah nilai yang diterima konsumen legacy.

    Bila salah satu assert ini gagal, ada perubahan nilai visual di luar
    aktivasi per-report Fase 2 — itu bug fase, bukan pembaruan test.
    """

    def test_export_config_legacy_values(self):
        from detail_project.export_config import ExportColors, ExportFonts
        self.assertEqual(ExportColors.HEADER_BG, 'e8e8e8')
        self.assertEqual(ExportFonts.TITLE, 18)

    def test_table_styles_legacy_values(self):
        from detail_project.exports.table_styles import (
            UnifiedTableStyles as UTS,
            ExportDefaults as ED,
        )
        self.assertEqual(UTS.HEADER_BG, '#1e3a5f')
        self.assertEqual(ED.FONT_SIZE_TITLE, 16)
        self.assertEqual(ED.FONT_SIZE_NORMAL, 8)
