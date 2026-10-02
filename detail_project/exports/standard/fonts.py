"""Registrasi huruf PDF standar (S-2: DejaVu Sans, glyph lengkap termasuk ∅).

Berkas huruf disertakan di ``exports/fonts`` (lisensi: LICENSE_DEJAVU.txt).
Bila berkas tidak ada, kembali ke Helvetica agar export tetap jalan.
"""
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parent.parent / 'fonts'
_FILES = {
    'Std': 'DejaVuSans.ttf',
    'Std-Bold': 'DejaVuSans-Bold.ttf',
    'Std-Italic': 'DejaVuSans-Oblique.ttf',
    'Std-BoldItalic': 'DejaVuSans-BoldOblique.ttf',
}
_FALLBACK = {
    'Std': 'Helvetica',
    'Std-Bold': 'Helvetica-Bold',
    'Std-Italic': 'Helvetica-Oblique',
    'Std-BoldItalic': 'Helvetica-BoldOblique',
}
_state = {'ready': None}


def register() -> bool:
    """Daftarkan huruf sekali. Return True bila DejaVu tersedia."""
    if _state['ready'] is not None:
        return _state['ready']
    try:
        for name, file in _FILES.items():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
        pdfmetrics.registerFontFamily(
            'Std', normal='Std', bold='Std-Bold', italic='Std-Italic', boldItalic='Std-BoldItalic')
        _state['ready'] = True
    except Exception:  # noqa: BLE001 - berkas hilang/korup: pakai Helvetica
        _state['ready'] = False
    return _state['ready']


def font(name: str) -> str:
    """Nama huruf siap pakai: 'Std', 'Std-Bold', 'Std-Italic', 'Std-BoldItalic'."""
    return name if register() else _FALLBACK[name]
