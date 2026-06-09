"""
Single source of truth for AHSP code parsing, validation, and classification.

This module centralizes the rules for what constitutes a valid AHSP code so that
PDF conversion, the validation report, clean Excel import, and exports all agree.

Rules (locked):
- A code is dot-separated numeric segments, optionally followed by a single
  alphabetic suffix as the LAST segment (e.g. ``2.2.1.1.5.a``).
- Numeric segments: 2 to 5 of them. Each is 1-3 digits, no leading zeros for
  multi-digit segments, and the first segment may not be ``0``.
- The letter suffix is a single ``a-z`` character and is only allowed when there
  are at least 3 numeric segments (mirrors the PDF conversion regex). Letters may
  never appear in the middle of a code.
- The suffix is NOT counted as a numeric segment. Classification is decided by
  the numeric segment count only:

      2 numeric segments      -> "classification"      (e.g. 1.1)
      3 numeric segments      -> "subclassification"   (e.g. 1.1.1)
      4-5 numeric segments    -> "parent"              (e.g. 1.1.1.1, 2.2.1.1.5.a)

A suffixed code keeps the same tier as its numeric base; ``2.2.1.1.5`` and
``2.2.1.1.5.a`` are both parents but are DISTINCT codes (never merge by prefix).
"""

from __future__ import annotations

import re

# Classification labels (also used as return values of classify_ahsp_code).
CLASSIFICATION = "classification"
SUBCLASSIFICATION = "subclassification"
PARENT = "parent"
INVALID = "invalid"

_MIN_NUMERIC_SEGMENTS = 2
_MAX_NUMERIC_SEGMENTS = 5
_MIN_SEGMENTS_FOR_SUFFIX = 3

# A leading code token may carry a single-letter suffix; the rest of the line is
# the title. We capture the candidate token and validate it structurally below.
_LEADING_TOKEN = re.compile(r"^([^\s]+)")


def _is_valid_numeric_segment(seg: str, *, is_first: bool) -> bool:
    """Validate one numeric segment of an AHSP code."""
    if not seg.isdigit():
        return False
    if not (1 <= len(seg) <= 3):
        return False
    # Reject multi-digit segments with a leading zero (e.g. "01").
    if len(seg) > 1 and seg.startswith("0"):
        return False
    # The first numeric segment may not be zero (rejects float-looking codes).
    if is_first and seg == "0":
        return False
    return True


def parse_ahsp_code(code: str | None) -> tuple[list[str], str | None] | None:
    """Parse a code into ``(numeric_segments, suffix)`` or ``None`` if invalid.

    ``suffix`` is the lower-cased single letter, or ``None`` when absent.
    """
    if not code:
        return None
    code = code.strip()
    if not code:
        return None

    parts = code.split(".")
    suffix: str | None = None

    # A single trailing alphabetic character is treated as the suffix.
    if len(parts[-1]) == 1 and parts[-1].isalpha():
        suffix = parts[-1].lower()
        parts = parts[:-1]

    if not parts:
        return None

    for index, part in enumerate(parts):
        if not _is_valid_numeric_segment(part, is_first=(index == 0)):
            return None

    numeric_count = len(parts)
    if numeric_count < _MIN_NUMERIC_SEGMENTS or numeric_count > _MAX_NUMERIC_SEGMENTS:
        return None
    if suffix is not None and numeric_count < _MIN_SEGMENTS_FOR_SUFFIX:
        return None

    return parts, suffix


def is_ahsp_code(code: str | None) -> bool:
    """Return True if ``code`` is a structurally valid AHSP code."""
    return parse_ahsp_code(code) is not None


def numeric_segment_count(code: str | None) -> int:
    """Number of numeric segments (suffix excluded). 0 for invalid codes."""
    parsed = parse_ahsp_code(code)
    return len(parsed[0]) if parsed else 0


def normalize_ahsp_code(code: str | None) -> str:
    """Return the canonical form of a code (suffix lower-cased), or '' if invalid."""
    parsed = parse_ahsp_code(code)
    if not parsed:
        return ""
    numeric, suffix = parsed
    base = ".".join(numeric)
    return f"{base}.{suffix}" if suffix else base


def classify_ahsp_code(code: str | None) -> str:
    """Classify a code by its numeric segment count.

    Returns one of CLASSIFICATION, SUBCLASSIFICATION, PARENT, or INVALID.
    """
    parsed = parse_ahsp_code(code)
    if not parsed:
        return INVALID
    count = len(parsed[0])
    if count == 2:
        return CLASSIFICATION
    if count == 3:
        return SUBCLASSIFICATION
    return PARENT  # 4 or 5 numeric segments


def extract_ahsp_code(text: str | None) -> str | None:
    """Extract the leading AHSP code from a line of text.

    ``"2.2.1.1.5.a Nama Judul"`` -> ``"2.2.1.1.5.a"``. Returns the normalized code
    or ``None`` if the line does not start with a valid code.
    """
    if not text:
        return None
    match = _LEADING_TOKEN.match(text.strip())
    if not match:
        return None
    normalized = normalize_ahsp_code(match.group(1))
    return normalized or None


def split_ahsp_title(text: str | None) -> tuple[str | None, str]:
    """Split a header line into ``(code, title)``.

    ``"1.1.1.1 Nama Judul"`` -> ``("1.1.1.1", "Nama Judul")``.
    If the line does not start with a valid code, returns ``(None, text)``.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None, ""

    match = _LEADING_TOKEN.match(cleaned)
    token = match.group(1) if match else ""
    code = normalize_ahsp_code(token)
    if not code:
        return None, cleaned

    title = cleaned[len(token):].strip()
    # Drop a leading separator left between code and title (e.g. "-", ".", ":").
    title = title.lstrip(".-:–— ").strip()
    return code, title
