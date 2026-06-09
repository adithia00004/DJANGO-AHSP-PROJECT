"""Manajemen kode item referensi (generate & sinkronisasi)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from django.db import IntegrityError, transaction

from referensi.models import KodeItemReferensi, RincianReferensi
from .import_utils import canonicalize_kategori

PREFIX_MAP = {
    RincianReferensi.Kategori.TK: "TK",
    RincianReferensi.Kategori.BHN: "B",
    RincianReferensi.Kategori.ALT: "PR",
    RincianReferensi.Kategori.LAIN: "LN",
}


@dataclass
class CodeAssignmentStats:
    manual: int = 0
    reused: int = 0
    generated: int = 0

    @property
    def total(self) -> int:
        return self.manual + self.reused + self.generated


def _prefix_for_category(kategori: str) -> str:
    return PREFIX_MAP.get(kategori, PREFIX_MAP[RincianReferensi.Kategori.LAIN])


def _extract_sequence(kode_item: str, prefix: str) -> int | None:
    if not kode_item:
        return None
    marker = f"{prefix}-"
    if not kode_item.startswith(marker):
        return None
    suffix = kode_item[len(marker) :]
    if not suffix.isdigit():
        return None
    try:
        return int(suffix)
    except ValueError:
        return None


def resolve_item_code(
    kategori: str,
    uraian: str,
    satuan: str | None,
) -> str:
    """
    Resolve a canonical item code from semantic identity.

    Source-file item codes are intentionally not accepted here. The registry is
    the SSOT for project item identity; a new code is allocated only when the
    category/description/unit combination has never been seen before.
    """
    kategori = canonicalize_kategori(kategori)
    uraian = (uraian or "").strip()
    satuan = (satuan or "").strip()
    if not uraian:
        raise ValueError("Uraian item wajib diisi untuk menghasilkan kode otomatis.")

    existing = KodeItemReferensi.objects.filter(
        kategori=kategori,
        uraian_item=uraian,
        satuan_item=satuan,
    ).only("kode_item").first()
    if existing:
        return existing.kode_item

    prefix = _prefix_for_category(kategori)
    # The category rows act as the allocation lock. The unique constraints on
    # semantic identity and category+code provide the final concurrency guard.
    for _attempt in range(3):
        try:
            with transaction.atomic():
                rows = list(
                    KodeItemReferensi.objects.select_for_update()
                    .filter(kategori=kategori)
                    .only("kode_item")
                )
                existing = KodeItemReferensi.objects.filter(
                    kategori=kategori,
                    uraian_item=uraian,
                    satuan_item=satuan,
                ).only("kode_item").first()
                if existing:
                    return existing.kode_item

                max_sequence = max(
                    (
                        sequence
                        for row in rows
                        if (sequence := _extract_sequence(row.kode_item, prefix))
                        is not None
                    ),
                    default=0,
                )
                code = f"{prefix}-{max_sequence + 1:04d}"
                KodeItemReferensi.objects.create(
                    kategori=kategori,
                    uraian_item=uraian,
                    satuan_item=satuan,
                    kode_item=code,
                )
                return code
        except IntegrityError:
            existing = KodeItemReferensi.objects.filter(
                kategori=kategori,
                uraian_item=uraian,
                satuan_item=satuan,
            ).only("kode_item").first()
            if existing:
                return existing.kode_item

    raise RuntimeError("Gagal mengalokasikan kode item otomatis setelah beberapa percobaan.")


def assign_item_codes(parse_result) -> CodeAssignmentStats:
    """Lengkapi kode item pada ParseResult tanpa menyentuh database."""

    stats = CodeAssignmentStats()
    if not parse_result or not getattr(parse_result, "jobs", None):
        return stats

    combos: set[Tuple[str, str, str]] = set()
    categories: set[str] = set()
    details: list[Tuple[object, Tuple[str, str, str]]] = []

    for job in parse_result.jobs:
        for detail in getattr(job, "rincian", []):
            kategori = canonicalize_kategori(detail.kategori or detail.kategori_source)
            detail.kategori = kategori
            uraian = detail.uraian_item or ""
            satuan = detail.satuan_item or ""
            key = (kategori, uraian, satuan)
            combos.add(key)
            categories.add(kategori)
            details.append((detail, key))

    if not details:
        return stats

    existing_map: Dict[Tuple[str, str, str], str] = {}
    max_seq: Dict[str, int] = defaultdict(int)

    if categories:
        qs = (
            KodeItemReferensi.objects.filter(kategori__in=categories)
            .values_list("kategori", "uraian_item", "satuan_item", "kode_item")
            .iterator(chunk_size=1000)
        )
        for kategori, uraian, satuan, kode in qs:
            prefix = _prefix_for_category(kategori)
            seq = _extract_sequence(kode, prefix)
            if seq is not None and seq > max_seq[kategori]:
                max_seq[kategori] = seq
            key = (kategori, uraian, satuan)
            if key in combos and key not in existing_map:
                existing_map[key] = kode

    generated_cache: Dict[Tuple[str, str, str], str] = {}

    for detail, key in details:
        if key in generated_cache:
            detail.kode_item = generated_cache[key]
            detail.kode_item_source = "generated"
            stats.generated += 1
            continue

        if key in existing_map:
            detail.kode_item = existing_map[key]
            detail.kode_item_source = "existing"
            stats.reused += 1
            continue

        prefix = _prefix_for_category(detail.kategori)
        next_seq = max_seq[detail.kategori] + 1
        max_seq[detail.kategori] = next_seq
        kode_baru = f"{prefix}-{next_seq:04d}"
        detail.kode_item = kode_baru
        detail.kode_item_source = "generated"
        generated_cache[key] = kode_baru
        stats.generated += 1

    return stats


def persist_item_codes(parse_result) -> int:
    """Simpan mapping kategori+uraian+satuan -> kode ke database."""

    if not parse_result or not getattr(parse_result, "jobs", None):
        return 0

    pending: Dict[Tuple[str, str, str], str] = {}
    for job in parse_result.jobs:
        for detail in getattr(job, "rincian", []):
            kategori = canonicalize_kategori(detail.kategori or detail.kategori_source)
            detail.kategori = kategori
            key = (kategori, detail.uraian_item or "", detail.satuan_item or "")
            kode = (detail.kode_item or "").strip()
            if not kode:
                raise ValueError(
                    "Kode item kosong tidak dapat disimpan. Lengkapi kode item sebelum impor."
                )
            existing = pending.get(key)
            if existing and existing != kode:
                raise ValueError(
                    "Kode item berbeda ditemukan untuk kombinasi kategori/uraian/satuan yang sama."
                )
            pending[key] = kode

    if not pending:
        return 0

    categories = {kategori for kategori, _, _ in pending}
    uraian_values = {uraian for _, uraian, _ in pending}
    satuan_values = {satuan for _, _, satuan in pending}

    existing_map: Dict[Tuple[str, str, str], KodeItemReferensi] = {}
    existing_qs = KodeItemReferensi.objects.filter(
        kategori__in=categories,
        uraian_item__in=uraian_values,
        satuan_item__in=satuan_values,
    ).iterator(chunk_size=500)
    for obj in existing_qs:
        key = (obj.kategori, obj.uraian_item, obj.satuan_item)
        existing_map[key] = obj

    to_create: list[KodeItemReferensi] = []
    to_update: list[KodeItemReferensi] = []

    for (kategori, uraian, satuan), kode in pending.items():
        existing = existing_map.get((kategori, uraian, satuan))
        if existing:
            if existing.kode_item != kode:
                existing.kode_item = kode
                to_update.append(existing)
        else:
            to_create.append(
                KodeItemReferensi(
                    kategori=kategori,
                    uraian_item=uraian,
                    satuan_item=satuan,
                    kode_item=kode,
                )
            )

    saved = 0
    with transaction.atomic():
        if to_create:
            KodeItemReferensi.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
            saved += len(to_create)
        if to_update:
            KodeItemReferensi.objects.bulk_update(to_update, ["kode_item"], batch_size=500)
            saved += len(to_update)
    return saved


__all__ = [
    "CodeAssignmentStats",
    "assign_item_codes",
    "persist_item_codes",
    "resolve_item_code",
]
