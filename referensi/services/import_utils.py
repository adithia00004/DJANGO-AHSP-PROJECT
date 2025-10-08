# referensi/services/import_utils.py
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re
import pandas as pd

_NUM_CANON = re.compile(r"^-?\d+(?:\.\d+)?$")

def norm_text(val) -> str:
    """Trim string; None/NaN → ''."""
    if val is None:
        return ""
    if isinstance(val, float) and pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s

def normalize_num(val) -> Decimal | None:
    """
    Normalisasi angka dengan dukungan format:
    - '26,406'      → Decimal('26.406')
    - '1.234,56'    → Decimal('1234.56')
    - '1.234'       → Decimal('1.234')   (anggap titik desimal jika tunggal)
    - '1234'        → Decimal('1234')
    Return None untuk kosong/tidak valid.
    """
    s = norm_text(val).replace(" ", "")
    if s == "":
        return None

    # Jika ada titik & koma → tentukan desimal berdasar pemisah TERAKHIR
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            # Pola Eropa: '.' ribuan, ',' desimal
            s = s.replace(".", "").replace(",", ".")
        else:
            # Jarang terjadi, namun kalau '.' desimal terakhir → buang koma ribuan
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        # Hanya koma → koma = desimal
        s = s.replace(",", ".")
    # Hanya titik → biarkan apa adanya

    if not _NUM_CANON.match(s):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def pick_first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Ambil nama kolom pertama yang ada di DataFrame (`candidates` urut prioritas)."""
    cols = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols:
            return cols[c.lower()]
    return None
