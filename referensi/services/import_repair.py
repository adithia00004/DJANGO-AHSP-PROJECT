"""
Shared import validation and repair helpers for AHSP import flows.

The functions in this module are intentionally request-free so they can be
used by PDF conversion, validation reports, frontend export, and staging guards.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


STANDARD_SEGMENTS = {"A", "B", "C"}
ACCEPTED_SEGMENTS = STANDARD_SEGMENTS | {"LAIN"}
SEGMENT_MAP = {
    "A": "A",
    "TK": "A",
    "TENAGA KERJA": "A",
    "B": "B",
    "BHN": "B",
    "BAHAN": "B",
    "C": "C",
    "PR": "C",
    "PERALATAN": "C",
    "ANOMALI": "ANOMALI",
    "LAIN": "LAIN",
    "LAINNYA": "LAIN",
    "OTHER": "LAIN",
    "UK": "ANOMALI",
    "LL": "ANOMALI",
}


@dataclass(frozen=True)
class RepairCandidate:
    row_id: str
    parent_code: str
    confidence: str
    reason: str
    suggested_action: str
    before: dict[str, str] | None = None
    after: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "parent_code": self.parent_code,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "before": self.before or {},
            "after": self.after or {},
        }


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "-"}:
        return ""
    return text


def normalize_segment(value: Any) -> str:
    return SEGMENT_MAP.get(clean_text(value).upper(), "ANOMALI")


def display_segment(value: Any) -> str:
    segment = normalize_segment(value)
    return {"A": "TK", "B": "BHN", "C": "PR", "LAIN": "LAIN"}.get(segment, segment)


def is_number_like(value: Any) -> bool:
    text = clean_text(value).replace(",", ".")
    if not text:
        return False
    try:
        Decimal(text)
    except (InvalidOperation, ValueError):
        return False
    return True


def coerce_koefisien(value: Any) -> str:
    """A detail item's coefficient must be numeric; any non-numeric value
    (blank, '-', text, garbage from PDF extraction) is assumed to be 0.

    Single source of truth for the rule "koefisien non-numerik = 0" so the
    validation report, frontend export and DB staging all agree.
    """
    text = clean_text(value)
    return text if is_number_like(text) else "0"


def is_summary_row(row: dict[str, Any]) -> bool:
    normalized = row if "parent_code" in row else normalized_row_from_original(row)
    joined = " ".join(
        clean_text(normalized.get(field))
        for field in ("no", "uraian", "kode_ref")
    ).lower()
    return (
        "jumlah harga" in joined
        or joined.startswith("jumlah unit pekerjaan")
        or joined.startswith("jumlah pekerjaan")
    )


def normalized_row_from_original(row: dict[str, Any]) -> dict[str, str]:
    return {
        "parent_code": clean_text(row.get("col_0")),
        "segment": normalize_segment(row.get("col_1")),
        "no": clean_text(row.get("col_2")),
        "uraian": clean_text(row.get("col_3")),
        "kode_ref": clean_text(row.get("col_4")),
        "satuan": clean_text(row.get("col_5")),
        "koefisien": clean_text(row.get("col_6")),
        "row_id": clean_text(row.get("row_id")),
        "issues": row.get("issues", []),
    }


def normalized_row_from_frontend(row: dict[str, Any]) -> dict[str, str]:
    return {
        "parent_code": clean_text(row.get("parent_code")),
        "segment": normalize_segment(row.get("segment")),
        "no": clean_text(row.get("no")),
        "uraian": clean_text(row.get("uraian")),
        "kode_ref": clean_text(row.get("kode_ref")),
        "satuan": clean_text(row.get("satuan")),
        "koefisien": clean_text(row.get("koefisien")),
        "row_id": clean_text(row.get("row_id")),
        "issues": row.get("issues", []),
    }


def detect_wrapped_row(row: dict[str, Any]) -> tuple[bool, RepairCandidate | None]:
    normalized = row if "parent_code" in row else normalized_row_from_original(row)
    segment = normalize_segment(normalized.get("segment"))
    uraian = clean_text(normalized.get("uraian"))
    satuan = clean_text(normalized.get("satuan"))
    koefisien = clean_text(normalized.get("koefisien"))
    kode_ref = clean_text(normalized.get("kode_ref"))

    if segment not in STANDARD_SEGMENTS or uraian:
        return False, None

    if not (satuan or koefisien or kode_ref):
        return False, None

    before = {
        "uraian": uraian,
        "kode_ref": kode_ref,
        "satuan": satuan,
        "koefisien": koefisien,
    }
    after = before.copy()
    if not uraian and kode_ref and not is_number_like(kode_ref):
        after["uraian"] = kode_ref
        after["kode_ref"] = ""

    confidence = "medium"
    if kode_ref and len(kode_ref) >= 8 and not is_number_like(kode_ref) and is_number_like(koefisien):
        confidence = "high"
    elif not is_number_like(koefisien):
        confidence = "low"

    candidate = RepairCandidate(
        row_id=clean_text(normalized.get("row_id")),
        parent_code=clean_text(normalized.get("parent_code")),
        confidence=confidence,
        reason="WARNING: Uraian Kosong (Wrapped Data)",
        suggested_action="Review kolom bergeser; isi Uraian sebelum tabel boleh diekspor.",
        before=before,
        after=after,
    )
    return True, candidate


def detect_shifted_numbered_row(row: dict[str, Any]) -> tuple[bool, RepairCandidate | None]:
    """
    Detect rows where the item number shifted into Uraian and the actual
    description shifted into Kode Referensi.

    Typical bad shape:
      no="", uraian="1", kode_ref="Genteng Palentong", satuan="buah", koef="25"
    Correct shape usually is:
      no="1", uraian="Genteng Palentong", kode_ref="", satuan="buah", koef="25"
    """
    normalized = row if "parent_code" in row else normalized_row_from_original(row)
    segment = normalize_segment(normalized.get("segment"))
    if segment not in STANDARD_SEGMENTS:
        return False, None

    no = clean_text(normalized.get("no"))
    uraian = clean_text(normalized.get("uraian"))
    kode_ref = clean_text(normalized.get("kode_ref"))
    satuan = clean_text(normalized.get("satuan"))
    koefisien = clean_text(normalized.get("koefisien"))

    if no and no != "-":
        return False, None
    if not (uraian and kode_ref and satuan and koefisien):
        return False, None
    if not is_number_like(uraian):
        return False, None
    if is_number_like(kode_ref) or len(kode_ref) < 8:
        return False, None
    if not is_number_like(koefisien):
        return False, None

    before = {
        "no": no,
        "uraian": uraian,
        "kode_ref": kode_ref,
        "satuan": satuan,
        "koefisien": koefisien,
    }
    after = before.copy()
    after["no"] = uraian
    after["uraian"] = kode_ref
    after["kode_ref"] = ""

    candidate = RepairCandidate(
        row_id=clean_text(normalized.get("row_id")),
        parent_code=clean_text(normalized.get("parent_code")),
        confidence="high",
        reason="WARNING: Kolom Bergeser (No/Uraian/Kode)",
        suggested_action="Geser nomor ke kolom No dan teks material ke Uraian sebelum tabel boleh diekspor.",
        before=before,
        after=after,
    )
    return True, candidate


def row_block_reasons(row: dict[str, Any]) -> tuple[list[str], list[RepairCandidate]]:
    normalized = row if "parent_code" in row else normalized_row_from_original(row)
    reasons: list[str] = []
    candidates: list[RepairCandidate] = []
    segment = normalize_segment(normalized.get("segment"))

    if is_summary_row(normalized):
        return reasons, candidates

    if segment == "ANOMALI":
        reasons.append("Segmen tidak dikenal / ANOMALI")
    elif segment in ACCEPTED_SEGMENTS:
        uraian = clean_text(normalized.get("uraian"))
        satuan = clean_text(normalized.get("satuan"))
        # Koefisien non-numerik TIDAK memblokir: diasumsikan 0 (lihat
        # coerce_koefisien). Hanya Uraian/Satuan yang wajib ada.
        if not uraian or not satuan:
            reasons.append("Baris item tidak lengkap: Uraian/Satuan wajib valid")

    for issue in normalized.get("issues", []) or []:
        if "WARNING: Uraian Kosong" in str(issue):
            reasons.append("WARNING: Uraian Kosong (Wrapped Data)")

    is_wrapped, candidate = detect_wrapped_row(normalized)
    if is_wrapped:
        reasons.append("WARNING: Uraian Kosong (Wrapped Data)")
        if candidate:
            candidates.append(candidate)

    is_shifted, shifted_candidate = detect_shifted_numbered_row(normalized)
    if is_shifted:
        reasons.append("WARNING: Kolom Bergeser (No/Uraian/Kode)")
        if shifted_candidate:
            candidates.append(shifted_candidate)

    return reasons, candidates


def compute_block_status(table: dict[str, Any]) -> dict[str, Any]:
    rows = table.get("rows", [])
    reasons: list[str] = []
    warnings: list[str] = []
    candidates: list[RepairCandidate] = []

    if table.get("is_anomaly"):
        reasons.extend(table.get("anomaly_reasons") or ["Tabel ditandai anomali"])
    if table.get("table_status") == "error":
        reasons.append("Status tabel error")

    # Missing standard segments is a PASSIVE warning, NOT a blocker: some AHSP
    # items legitimately have no Bahan/Peralatan (e.g. labor-only work), so the
    # table must still be exportable. Only genuine data problems (wrapped rows,
    # ANOMALI/unknown segments, errors) block the table.
    segments = {normalize_segment(row.get("segment")) for row in rows}
    missing = sorted(STANDARD_SEGMENTS - segments)
    if missing:
        label = {"A": "Tenaga Kerja (TK)", "B": "Bahan (BHN)", "C": "Peralatan (PR)"}
        warnings.append("Struktur tak lengkap: " + ", ".join(label[s] for s in missing))

    # Non-numeric coefficients are assumed 0 (not a blocker). Surface it as a
    # passive warning so the admin can spot a possible extraction error while the
    # table stays exportable.
    coerced_koef = sum(
        1 for row in rows
        if normalize_segment(row.get("segment")) in ACCEPTED_SEGMENTS
        and clean_text(row.get("uraian"))
        and not is_number_like(row.get("koefisien"))
    )
    if coerced_koef:
        warnings.append(f"Koefisien non-numerik pada {coerced_koef} baris diasumsikan 0")

    for row in rows:
        row_reasons, row_candidates = row_block_reasons(row)
        reasons.extend(row_reasons)
        candidates.extend(row_candidates)

    deduped_reasons = list(dict.fromkeys(reasons))
    deduped_warnings = list(dict.fromkeys(warnings))
    if deduped_reasons:
        block_status = "blocked"
    elif deduped_warnings:
        block_status = "warning"
    else:
        block_status = "valid"
    return {
        "is_blocked": bool(deduped_reasons),
        "block_status": block_status,
        "blocked_reasons": deduped_reasons,
        "warnings": deduped_warnings,
        "repair_candidates": [candidate.as_dict() for candidate in candidates],
        "can_export": not deduped_reasons,
    }


def validate_frontend_payload(data_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in data_rows:
        normalized = normalized_row_from_frontend(row)
        if is_summary_row(normalized):
            continue
        if normalized["parent_code"]:
            rows_by_parent[normalized["parent_code"]].append(normalized)

    valid_parent_codes: list[str] = []
    skipped_tables: list[dict[str, Any]] = []
    warning_tables: list[dict[str, Any]] = []
    repair_candidates: list[dict[str, str]] = []
    valid_rows: list[dict[str, str]] = []
    skipped_rows: list[dict[str, str]] = []

    for parent_code in sorted(rows_by_parent):
        rows = rows_by_parent[parent_code]
        status = compute_block_status({"rows": rows})
        if status["is_blocked"]:
            skipped_tables.append({
                "parent_code": parent_code,
                "reasons": status["blocked_reasons"],
                "row_count": len(rows),
            })
            repair_candidates.extend(status["repair_candidates"])
            skipped_rows.extend(rows)
        else:
            # Not blocked: still exported. Passive warnings (e.g. missing
            # Bahan/Peralatan) are surfaced for the user but do not skip it.
            valid_parent_codes.append(parent_code)
            valid_rows.extend(rows)
            if status["warnings"]:
                warning_tables.append({
                    "parent_code": parent_code,
                    "warnings": status["warnings"],
                    "row_count": len(rows),
                })

    return {
        "valid_parent_codes": valid_parent_codes,
        "skipped_tables": skipped_tables,
        "warning_tables": warning_tables,
        "repair_candidates": repair_candidates,
        "valid_rows": valid_rows,
        "skipped_rows": skipped_rows,
        "counts": {
            "valid_tables": len(valid_parent_codes),
            "skipped_tables": len(skipped_tables),
            "warning_tables": len(warning_tables),
            "valid_rows": len(valid_rows),
            "skipped_rows": len(skipped_rows),
        },
    }
