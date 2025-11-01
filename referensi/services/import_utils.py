# referensi/services/import_utils.py
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import math
import re
try:  # pragma: no cover - optional dependency
    import pandas as pd  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback tanpa pandas
    pd = None

_NUM_CANON = re.compile(r"^-?\d+(?:\.\d+)?$")

_KATEGORI_PATTERNS = (
    ("TK", ("tk", "tenaga", "tenaga kerja", "upah", "labor", "pekerja")),
    ("BHN", ("bhn", "bahan", "material", "mat")),
    ("ALT", ("alt", "alat", "peralatan", "equipment", "mesin", "tools")),
)

def norm_text(val) -> str:
    if val is None:
        return ""
    if isinstance(val, float):
        if pd is not None and pd.isna(val):
            return ""
        if math.isnan(val):
            return ""
        return str(val).strip()
    s = str(val).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s

def normalize_num(val) -> Decimal | None:
    s = norm_text(val).replace(" ", "")
    if s == "":
        return None
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    if not _NUM_CANON.match(s):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def pick_first_col(df, candidates: list[str]) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols:
            return cols[c.lower()]
    return None


def canonicalize_kategori(value: str) -> str:
    """Map berbagai penulisan kategori ke kode standar (TK/BHN/ALT/LAIN)."""

    s = norm_text(value)
    if not s:
        return "LAIN"

    lowered = s.lower()
    for code, patterns in _KATEGORI_PATTERNS:
        if lowered == code.lower():
            return code
        if any(lowered == p or lowered.startswith(p) or p in lowered for p in patterns):
            return code

    return "LAIN"


__all__ = [
    "canonicalize_kategori",
    "norm_text",
    "normalize_num",
    "pick_first_col",
]
