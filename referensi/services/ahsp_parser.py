"""Utilities untuk mem-parsing Excel AHSP menjadi struktur terstruktur.

Modul ini mengekstrak data pekerjaan & rincian tanpa menyentuh database,
sehingga bisa dipakai untuk preview sebelum commit (UI) maupun import
sebenarnya (management command).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, List

from .import_utils import (
    canonicalize_kategori,
    normalize_num,
    norm_text,
    pick_first_col,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    import pandas as pd


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

    col_sumber = pick_first_col(df, ["sumber_ahsp"])
    col_kode = pick_first_col(df, ["kode_ahsp", "kode"])
    col_nama = pick_first_col(df, ["nama_ahsp", "nama"])
    col_kategori = pick_first_col(df, ["kategori", "kelompok"])
    col_kode_item = pick_first_col(df, ["kode_item_lookup", "kode_item"])
    col_item = pick_first_col(df, ["item", "uraian_item"])
    col_satuan_job = pick_first_col(
        df,
        [
            "satuan_pekerjaan",
            "satuan_ahsp",
            "satuan_pekerjaan_ahsp",
            "satuan",
        ],
    )
    col_satuan_detail = pick_first_col(df, ["satuan_item", "satuan"])
    col_koef = pick_first_col(df, ["koefisien", "koef", "qty"])
    col_klasifikasi = pick_first_col(df, ["klasifikasi"])
    col_sub_klasifikasi = pick_first_col(
        df,
        ["sub_klasifikasi", "sub klasifikasi", "subklasifikasi"],
    )

    missing = [
        name
        for name, col in (
            ("sumber_ahsp", col_sumber),
            ("kode_ahsp", col_kode),
            ("nama_ahsp", col_nama),
        )
        if col is None
    ]
    if missing:
        result.errors.append(
            "Kolom wajib hilang: {}. Pastikan header Excel minimal: "
            "sumber_ahsp, kode_ahsp, nama_ahsp".format(
                ", ".join(missing)
            )
        )
        return result

    current_src = ""
    current_job: AHSPPreview | None = None

    mapped_categories: dict[tuple[str, str], int] = {}
    missing_categories = 0

    for idx, row in df.iterrows():
        row_number = idx + 2  # header dianggap baris pertama

        sumber_ahsp = norm_text(row.get(col_sumber, ""))
        if sumber_ahsp:
            current_src = sumber_ahsp

        kode = norm_text(row.get(col_kode, ""))
        nama = norm_text(row.get(col_nama, ""))

        if kode and nama:
            klasifikasi = (
                norm_text(row.get(col_klasifikasi, ""))
                if col_klasifikasi
                else ""
            )
            sub_klasifikasi = (
                norm_text(row.get(col_sub_klasifikasi, ""))
                if col_sub_klasifikasi
                else ""
            )
            satuan_job = (
                norm_text(row.get(col_satuan_job, ""))
                if col_satuan_job
                else ""
            )
            if not current_src:
                result.errors.append(
                    f"Baris {row_number}: 'sumber_ahsp' kosong untuk pekerjaan {kode} - {nama}."
                )
                current_job = None
                continue

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
                for col_name in (col_kategori, col_item, col_satuan_detail, col_koef)
                if col_name
            ):
                result.warnings.append(
                    f"Baris {row_number}: rincian diabaikan karena belum ada pekerjaan aktif."
                )
            continue

        kategori_source = (
            norm_text(row.get(col_kategori, "")) if col_kategori else ""
        )
        kategori = canonicalize_kategori(kategori_source)
        kode_item = norm_text(row.get(col_kode_item, "")) if col_kode_item else ""
        uraian_item = norm_text(row.get(col_item, "")) if col_item else ""
        satuan_item = (
            norm_text(row.get(col_satuan_detail, "")) if col_satuan_detail else ""
        )
        koef = normalize_num(row.get(col_koef, "")) if col_koef else None
        if koef is None:
            koef = Decimal("0")

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


__all__ = [
    "AHSPPreview",
    "ParseResult",
    "RincianPreview",
    "load_preview_from_file",
    "parse_excel_dataframe",
]

