from django.core.cache import cache
from django.test.utils import override_settings
import pytest

from referensi.models import AHSPReferensi
from referensi.services.cache_helpers import ReferensiCache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "referensi-tests",
        }
    }
)
def test_available_sources_cache_roundtrip(django_assert_num_queries):
    AHSPReferensi.objects.create(
        kode_ahsp="01.01",
        nama_ahsp="Pekerjaan Tanah",
        sumber="SNI 2025",
    )

    with django_assert_num_queries(1):
        first = ReferensiCache.get_available_sources()
        assert first == ["SNI 2025"]

    with django_assert_num_queries(0):
        cached = ReferensiCache.get_available_sources()
        assert cached == first

    # Data mutation triggers signal-based invalidation
    AHSPReferensi.objects.create(
        kode_ahsp="02.01",
        nama_ahsp="Pekerjaan Beton",
        sumber="Custom 2024",
    )
    with django_assert_num_queries(1):
        refreshed = ReferensiCache.get_available_sources()
    assert refreshed == ["Custom 2024", "SNI 2025"]


@pytest.mark.django_db
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "referensi-tests",
        }
    }
)
def test_job_choices_cached_per_limit(django_assert_num_queries):
    objs = [
        AHSPReferensi.objects.create(
            kode_ahsp=f"0{i}.01",
            nama_ahsp=f"Pekerjaan {i}",
            sumber="SNI 2025",
        )
        for i in range(1, 4)
    ]

    with django_assert_num_queries(1):
        first = ReferensiCache.get_job_choices(limit=5000)
    assert len(first) == 3

    # Different limit should hit database and cache separately
    with django_assert_num_queries(1):
        limit_two = ReferensiCache.get_job_choices(limit=2)
    assert len(limit_two) == 2

    # Creating new job invalidates cache via signal
    AHSPReferensi.objects.create(
        kode_ahsp="04.01",
        nama_ahsp="Pekerjaan Baru",
        sumber="SNI 2025",
    )
    with django_assert_num_queries(1):
        cached = ReferensiCache.get_job_choices(limit=5000)
    assert len(cached) == 4
    assert cached[-1][1] == "04.01"

    ReferensiCache.invalidate_job_choices()
    with django_assert_num_queries(1):
        refreshed = ReferensiCache.get_job_choices(limit=5000)
    assert refreshed == cached


@pytest.mark.django_db
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "referensi-tests",
        }
    }
)
def test_invalidate_all_clears_stats():
    AHSPReferensi.objects.create(
        kode_ahsp="01.01",
        nama_ahsp="Pekerjaan Tanah",
        sumber="SNI 2025",
    )
    ReferensiCache.warm_cache()
    stats = ReferensiCache.get_cache_stats()
    assert stats["sources_cached"] is True
    assert stats["klasifikasi_cached"] is True
    assert stats["job_choices_cached"] is True

    ReferensiCache.invalidate_all()
    stats = ReferensiCache.get_cache_stats()
    assert stats["sources_cached"] is False
    assert stats["job_choices_cached"] is False
