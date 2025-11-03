from decimal import Decimal

import pytest

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.repositories.item_repository import ItemRepository


@pytest.mark.django_db
def test_filter_by_search_and_category():
    ahsp = AHSPReferensi.objects.create(
        kode_ahsp="20.01",
        nama_ahsp="Pekerjaan Struktur",
    )
    tk = RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori=RincianReferensi.Kategori.TK,
        kode_item="TK-001",
        uraian_item="Mandor",
        satuan_item="OH",
        koefisien=Decimal("1"),
    )
    bahan = RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori=RincianReferensi.Kategori.BHN,
        kode_item="BHN-001",
        uraian_item="Semen Portland",
        satuan_item="Zak",
        koefisien=Decimal("15"),
    )

    qs = ItemRepository.base_queryset()
    search_results = ItemRepository.filter_by_search(qs, "semen")
    assert list(search_results.values_list("id", flat=True)) == [bahan.id]

    kategori_results = ItemRepository.filter_by_category(qs, "TK")
    assert list(kategori_results.values_list("id", flat=True)) == [tk.id]


@pytest.mark.django_db
def test_filter_by_job():
    ahsp1 = AHSPReferensi.objects.create(kode_ahsp="30.01", nama_ahsp="Pekerjaan A")
    ahsp2 = AHSPReferensi.objects.create(kode_ahsp="30.02", nama_ahsp="Pekerjaan B")
    item1 = RincianReferensi.objects.create(
        ahsp=ahsp1,
        kategori=RincianReferensi.Kategori.TK,
        kode_item="TK-A",
        uraian_item="Mandor A",
        satuan_item="OH",
        koefisien=Decimal("1"),
    )
    RincianReferensi.objects.create(
        ahsp=ahsp2,
        kategori=RincianReferensi.Kategori.TK,
        kode_item="TK-B",
        uraian_item="Mandor B",
        satuan_item="OH",
        koefisien=Decimal("1"),
    )

    qs = ItemRepository.base_queryset()
    filtered = ItemRepository.filter_by_job(qs, ahsp1.id)
    assert list(filtered.values_list("id", flat=True)) == [item1.id]
