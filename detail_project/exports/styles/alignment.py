"""Helper perataan kolom tunggal dari ``column_formats`` (Doc 32 Fase 1.4).

Aturan doc 32 item 2.3 — perataan berbasis TIPE data, bukan posisi kolom:
- format numerik (mis. ``#,##0.00``) → RIGHT (angka/mata uang/%)
- format teks ``'@'`` → LEFT, kecuali header No/Kode/Satuan → CENTER
- tabel tanpa ``column_formats`` → ``None`` (caller fallback ke perilaku lama)

Dibangun + diuji di Fase 1; DIAKTIFKAN per-report di Fase 2 (belum ada
pemanggil di jalur output — behavior-preserving).
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from ..cell_format import _is_numeric_format

# Header yang dirata-tengah walau bertipe teks (identitas pendek, bukan uraian)
_CENTERED_TEXT_HEADERS = {'no', 'kode', 'satuan', 'sat', 'unit'}


def alignment_for_columns(
    headers: Optional[Sequence],
    column_formats: Optional[Sequence],
) -> Optional[List[str]]:
    """Return perataan ``'LEFT'|'RIGHT'|'CENTER'`` per kolom, atau ``None``
    bila tabel belum ber-``column_formats`` (belum migrasi — jangan sentuh)."""
    if not column_formats:
        return None

    n = max(len(headers or []), len(column_formats))
    aligns: List[str] = []
    for i in range(n):
        fmt = column_formats[i] if i < len(column_formats) else None
        header = headers[i] if headers and i < len(headers) else ''
        if _is_numeric_format(fmt):
            aligns.append('RIGHT')
        elif str(header or '').strip().rstrip('.').lower() in _CENTERED_TEXT_HEADERS:
            aligns.append('CENTER')
        else:
            aligns.append('LEFT')
    return aligns
