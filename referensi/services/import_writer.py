"""Utility untuk menulis hasil parse AHSP ke database."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from django.db import transaction

from referensi.models import AHSPReferensi, RincianReferensi
from .import_utils import canonicalize_kategori
from .item_code_registry import assign_item_codes, persist_item_codes


@dataclass
class ImportSummary:
    """Ringkasan hasil impor AHSP."""

    jobs_created: int = 0
    jobs_updated: int = 0
    rincian_written: int = 0
    detail_errors: list[str] = field(default_factory=list)


def _log(stdout, message: str) -> None:
    if stdout is None:
        return
    stdout.write(message)


def write_parse_result_to_db(parse_result, source_file: str | None = None, *, stdout=None) -> ImportSummary:
    """Persisten ParseResult ke database.

    Parameters
    ----------
    parse_result: referensi.services.ahsp_parser.ParseResult
        Hasil parsing Excel AHSP.
    source_file: str | None
        Nama file sumber untuk disimpan ke model (opsional).
    stdout:
        Handler stdout (misal dari BaseCommand) untuk logging progres.
    """

    from referensi.services.ahsp_parser import ParseResult  # menghindari import siklik

    if not isinstance(parse_result, ParseResult):
        raise TypeError("parse_result harus instance ParseResult")

    summary = ImportSummary()

    if parse_result.errors:
        raise ValueError("ParseResult mengandung error, tidak bisa diimpor.")

    if source_file:
        source_file = os.path.basename(source_file)

    assign_item_codes(parse_result)

    with transaction.atomic():
        persist_item_codes(parse_result)
        for job in parse_result.jobs:
            defaults = {
                "nama_ahsp": job.nama_ahsp,
                "satuan": job.satuan or "",
                "klasifikasi": job.klasifikasi or "",
                "sub_klasifikasi": job.sub_klasifikasi or "",
                "source_file": source_file,
            }
            ahsp_obj, created = AHSPReferensi.objects.get_or_create(
                sumber=job.sumber,
                kode_ahsp=job.kode_ahsp,
                defaults=defaults,
            )

            if created:
                summary.jobs_created += 1
            else:
                updated_fields: list[str] = []
                if ahsp_obj.nama_ahsp != job.nama_ahsp:
                    ahsp_obj.nama_ahsp = job.nama_ahsp
                    updated_fields.append("nama_ahsp")
                if job.klasifikasi is not None and ahsp_obj.klasifikasi != job.klasifikasi:
                    ahsp_obj.klasifikasi = job.klasifikasi or ""
                    updated_fields.append("klasifikasi")
                if (
                    job.sub_klasifikasi is not None
                    and ahsp_obj.sub_klasifikasi != job.sub_klasifikasi
                ):
                    ahsp_obj.sub_klasifikasi = job.sub_klasifikasi or ""
                    updated_fields.append("sub_klasifikasi")
                if job.satuan is not None and ahsp_obj.satuan != job.satuan:
                    ahsp_obj.satuan = job.satuan or ""
                    updated_fields.append("satuan")
                if source_file and ahsp_obj.source_file != source_file:
                    ahsp_obj.source_file = source_file
                    updated_fields.append("source_file")
                if updated_fields:
                    ahsp_obj.save(update_fields=updated_fields)
                summary.jobs_updated += 1

            _log(stdout, f"➡️  [{job.sumber}] {job.kode_ahsp} - {job.nama_ahsp}")

            # Kosongkan rincian lama sebelum tulis ulang
            RincianReferensi.objects.filter(ahsp=ahsp_obj).delete()

            for detail in job.rincian:
                try:
                    fields = dict(
                        ahsp=ahsp_obj,
                        kategori=canonicalize_kategori(detail.kategori or detail.kategori_source),
                        kode_item=detail.kode_item,
                        uraian_item=detail.uraian_item,
                        satuan_item=detail.satuan_item,
                        koefisien=detail.koefisien,
                    )
                    if hasattr(RincianReferensi, "uraian_item"):
                        RincianReferensi.objects.create(**fields)
                    else:  # pragma: no cover - fallback untuk skema lama
                        legacy_fields = dict(
                            ahsp=ahsp_obj,
                            kategori=canonicalize_kategori(detail.kategori or detail.kategori_source),
                            kode_item_lookup=detail.kode_item,
                            item=detail.uraian_item,
                            satuan=detail.satuan_item,
                            koefisien=detail.koefisien,
                        )
                        RincianReferensi.objects.create(**legacy_fields)
                    summary.rincian_written += 1
                except Exception as exc:  # pragma: no cover - dependensi DB
                    message = f"⚠️  Gagal import rincian baris {detail.row_number}: {exc}"
                    _log(stdout, message)
                    summary.detail_errors.append(message)

    return summary


__all__ = [
    "ImportSummary",
    "write_parse_result_to_db",
]
