"""Shared column schema metadata for referensi imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


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
        aliases=("satuan_pekerjaan", "satuan_ahsp", "satuan_pekerjaan_ahsp", "satuan"),
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
        required=False,
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
        data_type="Angka desimal >= 0",
        description="Koefisien pemakaian item",
    ),
)


COLUMN_SCHEMA: Dict[str, Tuple[ColumnSpec, ...]] = {
    "jobs": JOB_COLUMN_SPECS,
    "details": DETAIL_COLUMN_SPECS,
}


COLUMN_SPEC_LOOKUP: Dict[str, ColumnSpec] = {
    spec.canonical: spec
    for specs in COLUMN_SCHEMA.values()
    for spec in specs
}


__all__ = [
    "ColumnSpec",
    "COLUMN_SCHEMA",
    "COLUMN_SPEC_LOOKUP",
    "DETAIL_COLUMN_SPECS",
    "JOB_COLUMN_SPECS",
]
