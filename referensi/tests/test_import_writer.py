from decimal import Decimal

import pytest

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.import_writer import write_parse_result_to_db


@pytest.mark.django_db
def test_write_parse_result_creates_jobs_and_details():
    parse_result = ParseResult(
        jobs=[
            AHSPPreview(
                sumber="Sumber",
                kode_ahsp="K-001",
                nama_ahsp="Pekerjaan A",
                klasifikasi="Sipil",
                sub_klasifikasi="Tanah",
                satuan="m3",
                row_number=2,
                rincian=[
                    RincianPreview(
                        kategori="TK",
                        kategori_source="Tenaga Kerja",
                        kode_item="TK-01",
                        uraian_item="Pekerja",
                        satuan_item="OH",
                        koefisien=Decimal("1.25"),
                        row_number=3,
                    ),
                    RincianPreview(
                        kategori="LAIN",
                        kategori_source="",
                        kode_item="",
                        uraian_item="Biaya Lain",
                        satuan_item="ls",
                        koefisien=Decimal("0"),
                        row_number=4,
                    ),
                ],
            )
        ]
    )

    summary = write_parse_result_to_db(parse_result, "contoh.xlsx")

    assert summary.jobs_created == 1
    assert summary.jobs_updated == 0
    assert summary.rincian_written == 2
    assert summary.detail_errors == []

    job = AHSPReferensi.objects.get()
    assert job.nama_ahsp == "Pekerjaan A"
    assert job.klasifikasi == "Sipil"
    assert job.sub_klasifikasi == "Tanah"
    assert job.satuan == "m3"
    assert job.source_file == "contoh.xlsx"

    details = list(RincianReferensi.objects.filter(ahsp=job).order_by("id"))
    assert len(details) == 2
    categories = {d.kategori for d in details}
    assert categories == {"TK", "LAIN"}


@pytest.mark.django_db
def test_write_parse_result_replaces_existing_details():
    job = AHSPReferensi.objects.create(
        kode_ahsp="K-001",
        nama_ahsp="Lama",
        sumber="Sumber",
        klasifikasi="",
        sub_klasifikasi="",
        satuan="",
    )
    RincianReferensi.objects.create(
        ahsp=job,
        kategori="TK",
        kode_item="OLD",
        uraian_item="Old",
        satuan_item="OH",
        koefisien=Decimal("1"),
    )

    parse_result = ParseResult(
        jobs=[
            AHSPPreview(
                sumber="Sumber",
                kode_ahsp="K-001",
                nama_ahsp="Baru",
                klasifikasi="Sipil",
                sub_klasifikasi="Pondasi",
                satuan="m2",
                row_number=2,
                rincian=[
                    RincianPreview(
                        kategori="BHN",
                        kategori_source="Bahan",
                        kode_item="MAT-01",
                        uraian_item="Material",
                        satuan_item="kg",
                        koefisien=Decimal("2"),
                        row_number=3,
                    )
                ],
            )
        ]
    )

    summary = write_parse_result_to_db(parse_result, "update.xlsx")

    assert summary.jobs_created == 0
    assert summary.jobs_updated == 1
    assert summary.rincian_written == 1

    job.refresh_from_db()
    assert job.nama_ahsp == "Baru"
    assert job.klasifikasi == "Sipil"
    assert job.sub_klasifikasi == "Pondasi"
    assert job.satuan == "m2"
    assert job.source_file == "update.xlsx"

    details = list(RincianReferensi.objects.filter(ahsp=job))
    assert len(details) == 1
    assert details[0].kategori == "BHN"
    assert details[0].uraian_item == "Material"
