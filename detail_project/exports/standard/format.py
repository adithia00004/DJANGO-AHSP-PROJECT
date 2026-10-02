"""Format angka & utilitas tabel bersama (PDF dan Word)."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Sequence


def dec(value) -> Optional[Decimal]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not re.fullmatch(r'-?\d+(\.\d+)?', text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def num(value, dp: int = 2, empty: str = '-') -> str:
    """Angka format id-ID (R-15/R-49); teks non-angka diteruskan apa adanya."""
    if value is None or (isinstance(value, str) and value.strip() in ('', '-')):
        return empty
    d = dec(value)
    if d is None:
        return str(value)
    text = f"{d:,.{dp}f}"
    return text.replace(',', 'X').replace('.', ',').replace('X', '.')


_PCT_DOT = re.compile(r'(\d+)\.(\d+)%')


def id_label(text: str) -> str:
    """Persen bertitik di label (mis. 'PPN 11.00%') -> koma (R-49)."""
    return _PCT_DOT.sub(lambda m: f"{m.group(1)},{m.group(2)}%", str(text))


def drop_empty_columns(headers, rows, widths, aligns, keep=(0, 1)):
    """S-4: buang kolom yang seluruh isinya kosong/'-' (kecuali indeks di keep)."""
    keep_idx = []
    for i in range(len(headers)):
        values = [r[i] if i < len(r) else '' for r in rows]
        if i in keep or any(str(v).strip() not in ('', '-') for v in values):
            keep_idx.append(i)

    def pick(seq):
        return [seq[i] for i in keep_idx]

    return pick(headers), [pick(list(r) + [''] * len(headers)) for r in rows], pick(widths), pick(aligns)


def kinds_from(row_types: Sequence[str]) -> List[str]:
    return ['klas' if t == 'category' else 'sub' if t == 'subcategory' else 'item' for t in row_types]


def kinds_from_levels(levels: Dict, count: int) -> List[str]:
    out = []
    for i in range(count):
        lvl = levels.get(i, levels.get(str(i), 3))
        out.append('klas' if lvl == 1 else 'sub' if lvl == 2 else 'item')
    return out
