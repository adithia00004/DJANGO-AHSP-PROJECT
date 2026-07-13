"""Registry token desain semantik export PDF/Word (Doc 32 Fase 1.1).

Nilai token = desain target Fase 2 (doc 32 §5: skala tipografi 6 peran, satu
warna header, perataan berbasis tipe). Di Fase 1 modul ini BELUM dikonsumsi
jalur output mana pun — aktivasi per-report terjadi di Fase 2 dengan review
owner per-report (gate image-diff). Konstanta legacy (`export_config.ExportColors/
ExportFonts` dan `table_styles.UTS/ED`) TIDAK diubah oleh modul ini.

Baca docs/DESIGN_REGISTRY_EXPORT.md sebelum mengubah nilai apa pun di sini.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class Palette:
    """Satu palet untuk semua dokumen (menggantikan 3 biru drift T-1 saat aktivasi)."""
    HEADER_BG = '#1e3a5f'      # navy — selaras UTS.HEADER_BG yang sudah dipakai grid
    HEADER_TEXT = '#ffffff'
    TITLE = '#1e3a5f'
    BODY_TEXT = '#1a1a1a'
    CAPTION_TEXT = '#4a5568'
    TOTAL_BG = '#e8edf3'        # tint navy untuk baris total (pengganti hijau lokal)
    TOTAL_BG_STRONG = '#d7e0ec'  # tint navy lebih kuat untuk grand total (G)
    GRID = '#808080'


class TypeScale:
    """Skala 6 peran (pt) — doc 32 item 2.2. Grid Jadwal (R-2/R-3, jalur B)
    TIDAK memakai skala ini kecuali O-1 disetujui."""
    DOC_TITLE = 16
    SECTION_HEADING = 11
    TABLE_HEADER = 8
    BODY = 8
    TOTAL = 8
    CAPTION = 7


class FontFamily:
    """Pasangan metric-compatible Helvetica (PDF) ↔ Arial (Word) — tanpa embed."""
    PDF_REGULAR = 'Helvetica'
    PDF_BOLD = 'Helvetica-Bold'
    PDF_ITALIC = 'Helvetica-Oblique'
    PDF_BOLD_ITALIC = 'Helvetica-BoldOblique'
    WORD = 'Arial'


class Spacing:
    """Skala spasi tetap (mm) — doc 32 item 2.6: judul→tabel SM, antar tabel MD,
    sebelum blok pengesahan LG."""
    XS = 2
    SM = 4
    MD = 8
    LG = 12


@dataclass(frozen=True)
class StyleToken:
    size: int
    bold: bool = False
    italic: bool = False
    color: str = Palette.BODY_TEXT
    bg: Optional[str] = None
    align: str = 'LEFT'  # LEFT | RIGHT | CENTER


REGISTRY = {
    'doc_title': StyleToken(TypeScale.DOC_TITLE, bold=True, color=Palette.TITLE),
    'section_heading': StyleToken(TypeScale.SECTION_HEADING, bold=True),
    'table_header': StyleToken(
        TypeScale.TABLE_HEADER, bold=True, color=Palette.HEADER_TEXT,
        bg=Palette.HEADER_BG, align='CENTER'),
    'text_cell': StyleToken(TypeScale.BODY),
    'money_cell': StyleToken(TypeScale.BODY, align='RIGHT'),
    'code_cell': StyleToken(TypeScale.BODY, align='CENTER'),
    'group_title': StyleToken(TypeScale.BODY, bold=True, italic=True),
    'total_row': StyleToken(TypeScale.TOTAL, bold=True, bg=Palette.TOTAL_BG,
                            align='RIGHT'),
    'caption': StyleToken(TypeScale.CAPTION, color=Palette.CAPTION_TEXT),
    'identity_label': StyleToken(TypeScale.CAPTION, bold=True),
    'identity_value': StyleToken(TypeScale.CAPTION),
}


def leading_for(size: int) -> int:
    """Leading 1.25× untuk teks yang bisa wrap (dibulatkan ke atas)."""
    return -(-size * 5 // 4)  # ceil(size * 1.25)


# ---------------------------------------------------------------------------
# Adapter PDF (ReportLab) — ParagraphStyle di-cache per token (hindari pola
# T-10: stylesheet baru per sel).
# ---------------------------------------------------------------------------

_PDF_CACHE: dict = {}


def pdf_paragraph_style(token_name: str):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle

    if token_name not in _PDF_CACHE:
        tok = REGISTRY[token_name]
        if tok.bold and tok.italic:
            font = FontFamily.PDF_BOLD_ITALIC
        elif tok.bold:
            font = FontFamily.PDF_BOLD
        elif tok.italic:
            font = FontFamily.PDF_ITALIC
        else:
            font = FontFamily.PDF_REGULAR
        alignment = {'LEFT': TA_LEFT, 'RIGHT': TA_RIGHT, 'CENTER': TA_CENTER}[tok.align]
        _PDF_CACHE[token_name] = ParagraphStyle(
            name=f"tok_{token_name}",
            fontName=font,
            fontSize=tok.size,
            leading=leading_for(tok.size),
            textColor=HexColor(tok.color),
            alignment=alignment,
        )
    return _PDF_CACHE[token_name]


# ---------------------------------------------------------------------------
# Adapter Word (python-docx) — named styles didaftarkan sekali per dokumen
# sehingga Navigation Pane hidup dan edit user tidak merusak format (T-8).
# ---------------------------------------------------------------------------

WORD_STYLE_PREFIX = 'AHSP '

# Token yang dipetakan ke named style paragraf Word (sel tabel memakai
# formatting kolom, bukan named style per sel).
_WORD_PARAGRAPH_TOKENS = (
    'doc_title', 'section_heading', 'caption', 'identity_label', 'identity_value',
)


def word_style_name(token_name: str) -> str:
    return WORD_STYLE_PREFIX + token_name


def ensure_word_styles(document) -> dict:
    """Daftarkan named styles ke ``document`` (idempoten). Return mapping
    token → nama style Word."""
    from docx.enum.style import WD_STYLE_TYPE
    from docx.shared import Pt, RGBColor

    mapping = {}
    for token_name in _WORD_PARAGRAPH_TOKENS:
        tok = REGISTRY[token_name]
        name = word_style_name(token_name)
        try:
            style = document.styles[name]
        except KeyError:
            style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            style.base_style = document.styles['Normal']
        style.font.name = FontFamily.WORD
        style.font.size = Pt(tok.size)
        style.font.bold = tok.bold
        style.font.italic = tok.italic
        style.font.color.rgb = RGBColor.from_string(tok.color.lstrip('#').upper())
        mapping[token_name] = name
    return mapping
