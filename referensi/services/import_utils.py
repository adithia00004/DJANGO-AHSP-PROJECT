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
