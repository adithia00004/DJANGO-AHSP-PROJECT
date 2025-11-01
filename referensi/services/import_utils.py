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
