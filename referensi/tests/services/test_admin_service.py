from decimal import Decimal
from types import SimpleNamespace

import pytest

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.admin_service import AdminPortalService


class _DummyForm:
    def __init__(self, instance):
        self.instance = instance


@pytest.fixture
def service():
    return AdminPortalService(job_limit=100, item_limit=100)


@pytest.fixture
@pytest.mark.django_db
def sample_jobs():
    """Create sample AHSP data with and without anomalies."""
    healthy = AHSPReferensi.objects.create(
        kode_ahsp="01.01",
        nama_ahsp="Pekerjaan Tanah",
        klasifikasi="Sipil",
        sub_klasifikasi="Galian",
        satuan="LS",
        sumber="SNI 2025",
    )
    RincianReferensi.objects.create(
        ahsp=healthy,
        kategori=RincianReferensi.Kategori.TK,
        kode_item="TK-001",
        uraian_item="Mandor",
        satuan_item="OH",
        koefisien=Decimal("1"),
    )

    anomaly = AHSPReferensi.objects.create(
        kode_ahsp="02.01",
        nama_ahsp="Pekerjaan Beton",
        klasifikasi="Sipil",
        sub_klasifikasi="Struktur",
        satuan="LS",
        sumber="SNI 2025",
    )
    RincianReferensi.objects.create(
        ahsp=anomaly,
        kategori=RincianReferensi.Kategori.BHN,
        kode_item="BHN-001",
        uraian_item="Semen",
        satuan_item="",
        koefisien=Decimal("0"),
    )
    return {"healthy": healthy, "anomaly": anomaly}


def test_parse_job_filters_normalizes_values(service):
    filters = service.parse_job_filters(
        {
            "job_q": " beton ",
            "job_sumber": " SNI 2025 ",
            "job_klasifikasi": " Sipil ",
            "job_kategori": " TK ",
            "job_anomali": "1",
        }
    )
    assert filters["search"] == "beton"
    assert filters["sumber"] == "SNI 2025"
    assert filters["klasifikasi"] == "Sipil"
    assert filters["kategori"] == "TK"
    assert filters["anomali"] == "any"


def test_job_filter_query_params_roundtrip(service):
    params = service.job_filter_query_params(
        {
            "search": "galian",
            "sumber": "SNI 2025",
            "klasifikasi": "Sipil",
            "kategori": "TK",
            "anomali": "any",
        }
    )
    assert params == {
        "job_q": "galian",
        "job_sumber": "SNI 2025",
        "job_klasifikasi": "Sipil",
        "job_kategori": "TK",
        "job_anomali": "1",
    }


@pytest.mark.django_db
def test_apply_job_filters_handles_anomalies(service, sample_jobs):
    base_queryset = service.base_ahsp_queryset()
    filtered = service.apply_job_filters(
        base_queryset,
        {
            "search": "",
            "sumber": "",
            "klasifikasi": "",
            "kategori": "",
            "anomali": "any",
        },
    )
    results = list(filtered.values_list("kode_ahsp", flat=True))
    assert results == [sample_jobs["anomaly"].kode_ahsp]


def test_parse_item_filters_extracts_job_id(service):
    filters = service.parse_item_filters(
        {"item_q": " semen ", "item_kategori": " BHN ", "item_job": " 42 "}
    )
    assert filters["search"] == "semen"
    assert filters["kategori"] == "BHN"
    assert filters["job_id"] == 42
    assert filters["job_value"] == "42"

    fallback = service.parse_item_filters({})
    assert fallback["job_id"] is None
    assert fallback["job_value"] == ""


@pytest.mark.django_db
def test_build_job_rows_flags_anomalies(service, sample_jobs):
    queryset = service.base_ahsp_queryset().filter(pk=sample_jobs["anomaly"].pk)
    job = queryset.first()
    formset = SimpleNamespace(forms=[_DummyForm(job)])

    rows, anomaly_count = service.build_job_rows(formset)
    assert anomaly_count == 1
    assert rows[0]["anomaly_reasons"]
    assert rows[0]["category_counts"]["BHN"] == 1


@pytest.mark.django_db
def test_build_item_rows_returns_anomaly_reasons(service, sample_jobs):
    item = sample_jobs["anomaly"].rincian.first()
    formset = SimpleNamespace(forms=[_DummyForm(item)])

    rows, anomaly_count = service.build_item_rows(formset)
    assert anomaly_count == 1
    assert rows[0]["anomaly_reasons"] == [
        "Koefisien bernilai 0",
        "Satuan item kosong",
    ]
