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
# Support scientific notation (e.g., 8e-05, 1.23E+10)
_NUM_SCIENTIFIC = re.compile(r"^-?\d+(?:\.\d+)?[eE][+-]?\d+$")

# PHASE 2: Import normalizer for category normalization (single source of truth)
from referensi.services.normalizers import KategoriNormalizer

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
    """
    Parse numeric value from various formats including scientific notation.

    Supports:
    - Standard decimal: 123.456, 0.000008
    - Comma as decimal separator: 123,456
    - Mixed thousand separators: 1.234,56 or 1,234.56
    - Scientific notation: 8e-05, 1.23E+10 (for very small/large Excel values)

    Returns:
        Decimal object or None if invalid
    """
    # Handle numeric types directly
    if isinstance(val, (int, float)):
        if isinstance(val, float):
            if pd is not None and pd.isna(val):
                return None
            if math.isnan(val) or math.isinf(val):
                return None
        try:
            return Decimal(str(val))
        except (InvalidOperation, ValueError):
            return None

    s = norm_text(val).replace(" ", "")
    if s == "":
        return None

    # Normalize comma/dot separators (skip if scientific notation detected)
    if "e" not in s.lower():
        if "." in s and "," in s:
            # Determine which is decimal separator based on position
            if s.rfind(",") > s.rfind("."):
                # European format: 1.234,56 → 1234.56
                s = s.replace(".", "").replace(",", ".")
            else:
                # US format: 1,234.56 → 1234.56
                s = s.replace(",", "")
        elif "," in s and "." not in s:
            # Comma as decimal: 123,456 → 123.456
            s = s.replace(",", ".")

    # Validate format (standard or scientific)
    if not (_NUM_CANON.match(s) or _NUM_SCIENTIFIC.match(s)):
        return None

    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None

def pick_first_col(columns_source, candidates: list[str]) -> str | None:
    if hasattr(columns_source, "columns"):
        raw_columns = list(getattr(columns_source, "columns"))
    else:
        raw_columns = list(columns_source or [])

    lookup: dict[str, str] = {}
    for column in raw_columns:
        if column is None:
            continue
        column_str = str(column).strip()
        if not column_str:
            continue
        lowered = column_str.lower()
        if lowered not in lookup:
            lookup[lowered] = column_str

    for candidate in candidates:
        lowered = candidate.lower()
        if lowered in lookup:
            return lookup[lowered]
    return None


def canonicalize_kategori(value: str) -> str:
    """
    Map berbagai penulisan kategori ke kode standar (TK/BHN/ALT/LAIN).

    PHASE 2: Now delegates to KategoriNormalizer for single source of truth.
    This function kept for backward compatibility.
    """
    return KategoriNormalizer.normalize(value)


__all__ = [
    "canonicalize_kategori",
    "norm_text",
    "normalize_num",
    "pick_first_col",
]
