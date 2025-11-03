from decimal import Decimal

import pytest
from django.db import connection

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.repositories.ahsp_repository import AHSPRepository


@pytest.mark.django_db
def test_filter_by_metadata_and_anomaly():
    healthy = AHSPReferensi.objects.create(
        kode_ahsp="01.01",
        nama_ahsp="Pekerjaan Tanah",
        klasifikasi="Sipil",
        sumber="SNI 2025",
    )
    anomaly = AHSPReferensi.objects.create(
        kode_ahsp="02.01",
        nama_ahsp="Pekerjaan Beton",
        klasifikasi="Sipil",
        sumber="Custom 2024",
    )
    # Healthy rincian
    RincianReferensi.objects.create(
        ahsp=healthy,
        kategori=RincianReferensi.Kategori.TK,
        kode_item="TK-001",
        uraian_item="Mandor",
        satuan_item="OH",
        koefisien=Decimal("1"),
    )
    # Anomaly rincian (missing unit, zero coefficient)
    RincianReferensi.objects.create(
        ahsp=anomaly,
        kategori=RincianReferensi.Kategori.BHN,
        kode_item="BHN-001",
        uraian_item="Semen",
        satuan_item="",
        koefisien=Decimal("0"),
    )

    qs = AHSPRepository.get_with_category_counts()
    filtered = AHSPRepository.filter_by_metadata(qs, sumber="SNI 2025")
    assert list(filtered.values_list("kode_ahsp", flat=True)) == ["01.01"]

    anomalies = AHSPRepository.filter_by_anomaly(qs, "any")
    assert list(anomalies.values_list("kode_ahsp", flat=True)) == ["02.01"]


@pytest.mark.django_db
def test_filter_by_kategori():
    ahsp = AHSPReferensi.objects.create(
        kode_ahsp="03.01",
        nama_ahsp="Pekerjaan Jalan",
    )
    RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori=RincianReferensi.Kategori.ALT,
        kode_item="ALT-001",
        uraian_item="Excavator",
        satuan_item="Unit",
        koefisien=Decimal("1"),
    )
    qs = AHSPRepository.get_with_category_counts()
    filtered = AHSPRepository.filter_by_kategori(qs, "ALT")
    assert filtered.count() == 1
    assert filtered.first().kode_ahsp == "03.01"


@pytest.mark.django_db
@pytest.mark.skipif(connection.vendor != "postgresql", reason="Full-text search requires PostgreSQL.")
def test_filter_by_search_full_text_postgres():
    AHSPReferensi.objects.bulk_create(
        [
            AHSPReferensi(kode_ahsp="10.01", nama_ahsp="Pekerjaan Aspal", sumber="SNI"),
            AHSPReferensi(kode_ahsp="10.02", nama_ahsp="Pekerjaan Beton", sumber="SNI"),
        ]
    )
    qs = AHSPRepository.base_queryset()
    results = AHSPRepository.filter_by_search(qs, "beton")
    assert list(results.values_list("kode_ahsp", flat=True)) == ["10.02"]
