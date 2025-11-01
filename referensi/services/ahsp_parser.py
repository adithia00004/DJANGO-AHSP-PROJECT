"""Utilities untuk mem-parsing Excel AHSP menjadi struktur terstruktur.

Modul ini mengekstrak data pekerjaan & rincian tanpa menyentuh database,
sehingga bisa dipakai untuk preview sebelum commit (UI) maupun import
sebenarnya (management command).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Tuple

from .import_utils import (
    canonicalize_kategori,
    normalize_num,
    norm_text,
    pick_first_col,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    import pandas as pd


@dataclass(frozen=True)
class ColumnSpec:
    canonical: str
    aliases: Tuple[str, ...]
    required: bool
    data_type: str
    description: str
    max_length: int | None = None
    allowed_values: Tuple[str, ...] | None = None


JOB_COLUMN_SPECS: Tuple[ColumnSpec, ...] = (
    ColumnSpec(
        canonical="sumber_ahsp",
        aliases=("sumber_ahsp",),
        required=True,
        data_type="Teks (maks. 100 karakter)",
        description="Nama sumber AHSP, mis. 'AHSP SNI 2025'",
        max_length=100,
    ),
    ColumnSpec(
        canonical="kode_ahsp",
        aliases=("kode_ahsp", "kode"),
        required=True,
        data_type="Teks (maks. 50 karakter)",
        description="Kode pekerjaan unik dalam satu sumber",
        max_length=50,
    ),
    ColumnSpec(
        canonical="nama_ahsp",
        aliases=("nama_ahsp", "nama"),
        required=True,
        data_type="Teks (bebas)",
        description="Nama/uraian pekerjaan AHSP",
    ),
    ColumnSpec(
        canonical="klasifikasi",
        aliases=("klasifikasi",),
        required=False,
        data_type="Teks (maks. 100 karakter)",
        description="Klasifikasi pekerjaan (opsional)",
        max_length=100,
    ),
    ColumnSpec(
        canonical="sub_klasifikasi",
        aliases=("sub_klasifikasi", "sub klasifikasi", "subklasifikasi"),
        required=False,
        data_type="Teks (maks. 100 karakter)",
        description="Sub-klasifikasi pekerjaan (opsional)",
        max_length=100,
    ),
    ColumnSpec(
        canonical="satuan_pekerjaan",
        aliases=("satuan_pekerjaan", "satuan_ahsp", "satuan_pekerjaan_ahsp"),
        required=False,
        data_type="Teks (maks. 50 karakter)",
        description="Satuan kerja untuk pekerjaan AHSP",
        max_length=50,
    ),
)


DETAIL_COLUMN_SPECS: Tuple[ColumnSpec, ...] = (
    ColumnSpec(
        canonical="kategori",
        aliases=("kategori", "kelompok"),
        required=True,
        data_type="Teks (TK/BHN/ALT/LAIN)",
        description="Kategori item; variasi teks akan dipetakan otomatis",
        allowed_values=("TK", "BHN", "ALT", "LAIN"),
    ),
    ColumnSpec(
        canonical="kode_item",
        aliases=("kode_item", "kode_item_lookup"),
        required=True,
        data_type="Teks (maks. 50 karakter)",
        description="Kode item pada rincian",
        max_length=50,
    ),
    ColumnSpec(
        canonical="uraian_item",
        aliases=("uraian_item", "item"),
        required=True,
        data_type="Teks (bebas)",
        description="Uraian item/material",
    ),
    ColumnSpec(
        canonical="satuan_item",
        aliases=("satuan_item", "satuan"),
        required=True,
        data_type="Teks (maks. 20 karakter)",
        description="Satuan untuk item",
        max_length=20,
    ),
    ColumnSpec(
        canonical="koefisien",
        aliases=("koefisien", "koef", "qty"),
        required=True,
        data_type="Angka desimal ≥ 0", 
        description="Koefisien pemakaian item",
    ),
)


COLUMN_SCHEMA: Dict[str, Tuple[ColumnSpec, ...]] = {
    "jobs": JOB_COLUMN_SPECS,
    "details": DETAIL_COLUMN_SPECS,
}


_COLUMN_SPEC_MAP: Dict[str, ColumnSpec] = {
    spec.canonical: spec
    for specs in COLUMN_SCHEMA.values()
    for spec in specs
}


def _resolve_column_mapping(df) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    mapping: Dict[str, Dict[str, str]] = {"jobs": {}, "details": {}}
    errors: List[str] = []

    for group_name, specs in COLUMN_SCHEMA.items():
        for spec in specs:
            column = pick_first_col(df, list(spec.aliases))
            if column is None:
                if spec.required:
                    errors.append(
                        (
                            "Kolom '{canonical}' tidak ditemukan. Gunakan salah satu header: {aliases}."
                        ).format(
                            canonical=spec.canonical,
                            aliases=", ".join(spec.aliases),
                        )
                    )
                continue
            mapping[group_name][spec.canonical] = column

    return mapping, errors


def _read_optional_text(row, column_name: str | None, canonical: str) -> str:
    if not column_name:
        return ""
    value = norm_text(row.get(column_name, ""))
    return value


def _validate_text_length(
    value: str, canonical: str, row_number: int, errors: List[str]
) -> None:
    if not value:
        return
    spec = _COLUMN_SPEC_MAP.get(canonical)
    if not spec or not spec.max_length:
        return
    if len(value) > spec.max_length:
        errors.append(
            (
                "Baris {row}: kolom '{canonical}' melebihi {limit} karakter (panjang {length})."
            ).format(
                row=row_number,
                canonical=canonical,
                limit=spec.max_length,
                length=len(value),
            )
        )


@dataclass
class RincianPreview:
    kategori: str
    kode_item: str
    uraian_item: str
    satuan_item: str
    koefisien: Decimal
    row_number: int
    kategori_source: str = ""

    @property
    def koef_display(self) -> str:
        """Koefisien dalam format string tanpa notasi ilmiah."""

        return format(self.koefisien.normalize(), "f")

    @property
    def kategori_display(self) -> str:
        label_map = {
            "TK": "Tenaga Kerja",
            "BHN": "Bahan",
            "ALT": "Peralatan",
            "LAIN": "Lainnya",
        }
        if not self.kategori:
            return "-"
        label = label_map.get(self.kategori, self.kategori)
        return f"{self.kategori} — {label}"


@dataclass
class AHSPPreview:
    sumber: str
    kode_ahsp: str
    nama_ahsp: str
    row_number: int
    klasifikasi: str = ""
    sub_klasifikasi: str = ""
    satuan: str = ""
    rincian: List[RincianPreview] = field(default_factory=list)

    @property
    def rincian_count(self) -> int:
        return len(self.rincian)


@dataclass
class ParseResult:
    jobs: List[AHSPPreview] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def total_jobs(self) -> int:
        return len(self.jobs)

    @property
    def total_rincian(self) -> int:
        return sum(job.rincian_count for job in self.jobs)


def parse_excel_dataframe(df) -> ParseResult:
    """Parse DataFrame hasil pd.read_excel menjadi struktur preview."""

    result = ParseResult()

    column_map, column_errors = _resolve_column_mapping(df)
    if column_errors:
        result.errors.extend(column_errors)
        return result

    job_cols = column_map["jobs"]
    detail_cols = column_map["details"]

    current_src = ""
    current_job: AHSPPreview | None = None

    mapped_categories: dict[tuple[str, str], int] = {}
    missing_categories = 0

    for idx, row in df.iterrows():
        row_number = idx + 2  # header dianggap baris pertama

        sumber_ahsp = norm_text(row.get(job_cols.get("sumber_ahsp", ""), ""))
        if sumber_ahsp:
            current_src = sumber_ahsp

        kode = norm_text(row.get(job_cols.get("kode_ahsp", ""), ""))
        nama = norm_text(row.get(job_cols.get("nama_ahsp", ""), ""))

        if kode and nama:
            klasifikasi = _read_optional_text(
                row, job_cols.get("klasifikasi"), "klasifikasi"
            )
            sub_klasifikasi = _read_optional_text(
                row, job_cols.get("sub_klasifikasi"), "sub_klasifikasi"
            )
            satuan_job = _read_optional_text(
                row, job_cols.get("satuan_pekerjaan"), "satuan_pekerjaan"
            )
            if not current_src:
                result.errors.append(
                    f"Baris {row_number}: 'sumber_ahsp' kosong untuk pekerjaan {kode} - {nama}."
                )
                current_job = None
                continue

            _validate_text_length(
                current_src,
                "sumber_ahsp",
                row_number,
                result.errors,
            )
            _validate_text_length(kode, "kode_ahsp", row_number, result.errors)
            _validate_text_length(nama, "nama_ahsp", row_number, result.errors)
            _validate_text_length(
                klasifikasi,
                "klasifikasi",
                row_number,
                result.errors,
            )
            _validate_text_length(
                sub_klasifikasi,
                "sub_klasifikasi",
                row_number,
                result.errors,
            )
            _validate_text_length(
                satuan_job,
                "satuan_pekerjaan",
                row_number,
                result.errors,
            )

            current_job = AHSPPreview(
                sumber=current_src,
                kode_ahsp=kode,
                nama_ahsp=nama,
                klasifikasi=klasifikasi,
                sub_klasifikasi=sub_klasifikasi,
                satuan=satuan_job,
                row_number=row_number,
            )
            result.jobs.append(current_job)
            continue

        if current_job is None:
            # Abaikan noise sebelum pekerjaan pertama, tapi catat bila ada data
            if any(
                norm_text(row.get(col_name, ""))
                for col_name in detail_cols.values()
            ):
                result.warnings.append(
                    f"Baris {row_number}: rincian diabaikan karena belum ada pekerjaan aktif."
                )
            continue

        kategori_source = norm_text(
            row.get(detail_cols.get("kategori", ""), "")
        )
        kategori = canonicalize_kategori(kategori_source)
        kode_item = norm_text(row.get(detail_cols.get("kode_item", ""), ""))
        uraian_item = norm_text(row.get(detail_cols.get("uraian_item", ""), ""))
        satuan_item = norm_text(
            row.get(detail_cols.get("satuan_item", ""), "")
        )
        raw_koef = row.get(detail_cols.get("koefisien", ""), "")
        koef = Decimal("0")
        if raw_koef not in ("", None):
            normalized = normalize_num(raw_koef)
            if normalized is None:
                result.errors.append(
                    (
                        "Baris {row}: nilai koefisien '{value}' tidak valid. "
                        "Gunakan angka desimal dengan pemisah koma atau titik."
                    ).format(row=row_number, value=raw_koef)
                )
                continue
            if normalized < 0:
                result.errors.append(
                    f"Baris {row_number}: koefisien tidak boleh bernilai negatif."
                )
                continue
            koef = normalized

        _validate_text_length(kode_item, "kode_item", row_number, result.errors)
        _validate_text_length(uraian_item, "uraian_item", row_number, result.errors)
        _validate_text_length(satuan_item, "satuan_item", row_number, result.errors)

        if uraian_item:
            if kategori_source and kategori_source != kategori:
                mapped_categories[(kategori_source, kategori)] = (
                    mapped_categories.get((kategori_source, kategori), 0) + 1
                )
            elif not kategori_source:
                missing_categories += 1
            current_job.rincian.append(
                RincianPreview(
                    kategori=kategori,
                    kategori_source=kategori_source,
                    kode_item=kode_item,
                    uraian_item=uraian_item,
                    satuan_item=satuan_item,
                    koefisien=koef,
                    row_number=row_number,
                )
            )

    if not result.jobs and not result.errors:
        result.warnings.append("Tidak ada pekerjaan yang terdeteksi dari file Excel.")

    if mapped_categories:
        parts = [
            f"'{src}' → '{dst}' ({count}x)"
            for (src, dst), count in sorted(mapped_categories.items())
        ]
        result.warnings.append(
            "Kategori tertentu dipetakan ke kode standar: " + ", ".join(parts)
        )

    if missing_categories:
        result.warnings.append(
            f"{missing_categories} rincian tanpa kategori diperlakukan sebagai 'LAIN'."
        )

    return result


def load_preview_from_file(excel_file) -> ParseResult:
    """Membaca file Excel (UploadedFile) dan mengembalikan hasil parse."""

    try:
        excel_file.seek(0)
    except (AttributeError, OSError):
        pass

    try:
        import pandas as pd  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        result = ParseResult()
        result.errors.append(
            "Dependensi pandas belum terpasang sehingga file tidak bisa dibaca."
        )
        return result

    try:
        df = pd.read_excel(excel_file, header=0, dtype=str, keep_default_na=False)
    except Exception as exc:  # pragma: no cover - depend on engine errors
        result = ParseResult()
        result.errors.append(f"Gagal membaca Excel: {exc}")
        return result

    return parse_excel_dataframe(df)


def get_column_schema() -> Dict[str, Tuple["ColumnSpec", ...]]:
    """Mengembalikan skema kolom standar untuk keperluan UI/dokumentasi."""

    return COLUMN_SCHEMA


__all__ = [
    "AHSPPreview",
    "ColumnSpec",
    "ParseResult",
    "RincianPreview",
    "get_column_schema",
    "load_preview_from_file",
    "parse_excel_dataframe",
]

