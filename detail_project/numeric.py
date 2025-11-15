# detail_project/numeric.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import re

@dataclass(frozen=True)
class DecimalSpec:
    name: str
    dp: int  # fixed decimal places

# Standar proyek (sumber kebenaran)
DECIMAL_SPEC = {
    "KOEF":  DecimalSpec("KOEF", 6),  # koefisien detail AHSP
    "VOL":   DecimalSpec("VOL", 3),   # volume pekerjaan
    "HARGA": DecimalSpec("HARGA", 2), # harga satuan (Rp)
}

def _dp_value(dp_or_spec):
    """Terima int atau DecimalSpec; kembalikan nilai dp (int)."""
    try:
        # DecimalSpec punya atribut .dp
        v = getattr(dp_or_spec, "dp")
        return int(v)
    except Exception:
        return int(dp_or_spec)
    

def quantize_half_up(x, dp_or_spec):
    """
    Bulatkan x ke dp (HALF_UP). dp_or_spec boleh int atau DecimalSpec.
    """
    if x is None:
        return None
    dp = _dp_value(dp_or_spec)
    d = Decimal(str(x))
    quantum = Decimal('1').scaleb(-dp)  # 10^-dp
    return d.quantize(quantum, rounding=ROUND_HALF_UP)


def to_dp_str(x, dp_or_spec):
    """
    Serialize angka ke string kanonik dengan dp tetap (HALF_UP).
    dp_or_spec boleh int atau DecimalSpec.
    """
    if x is None:
        return None
    dp = _dp_value(dp_or_spec)
    try:
        d = Decimal(str(x))
    except Exception:
        return None
    quantum = Decimal('1').scaleb(-dp)
    return str(d.quantize(quantum, rounding=ROUND_HALF_UP))


def parse_any(val) -> Decimal | None:
    r"""
    Parser robust berbagai format:
      "2,7275"      -> 2.7275
      "1.234,555"   -> 1.234555  (KHUSUS: treat '.' as decimal, ',' as grouping)
      "1,000.25"    -> 1000.25
      "1.234,56"    -> 1.23456   ('.' decimal, ',' grouping)
      "2000"        -> 2000
    - Hilangkan underscore.
    - Jika mengandung '.' dan ',':
        * Jika cocok pola r'^\d+\.\d+,\d+$' → '.' decimal, hapus ','.
        * Jika cocok pola r'^\d+,\d+\.\d+$' → '.' decimal, hapus ','.
        * Selain itu → aturan 'last separator wins' (seperti sebelumnya).
    - Jika hanya satu jenis, gunakan separator yang ada sebagai desimal (kecuali banyak → buang ribuan).
    - Tolak negatif.
    """
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None

    s = s.replace("_", "")
    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma > last_dot:
            # separator terakhir adalah koma
            frac_len = len(s) - last_comma - 1
            if frac_len == 3:
                # anggap koma = ribuan, titik = desimal
                s = s.replace(",", "")
            else:
                # koma = desimal, titik = ribuan
                s = s.replace(".", "").replace(",", ".")
        else:
            # separator terakhir adalah titik
            frac_len = len(s) - last_dot - 1
            if frac_len == 3:
                # anggap titik = ribuan, koma = desimal
                s = s.replace(".", "").replace(",", ".")
            else:
                # titik = desimal, koma = ribuan
                s = s.replace(",", "")
    else:
        if s.count(",") == 1 and not has_dot:
            s = s.replace(",", ".")
        elif s.count(".") == 1 and not has_comma:
            pass
        else:
            s = s.replace(".", "").replace(",", ".")

    try:
        d = Decimal(s)
        if d < 0:
            return None
        return d
    except Exception:
        return None
