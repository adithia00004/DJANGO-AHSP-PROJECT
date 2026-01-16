import pytest
from django.urls import reverse

from referensi.models import AHSPReferensi


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="tester",
        email="tester@example.com",
        password="pass",
    )


@pytest.mark.django_db
def test_api_search_requires_login(client):
    response = client.get(reverse("referensi:api_search_ahsp"))
    assert response.status_code == 302  # redirected to login


@pytest.mark.django_db
def test_api_search_returns_matching_results(client, user):
    client.force_login(user)
    obj = AHSPReferensi.objects.create(
        kode_ahsp="01.01",
        nama_ahsp="Pekerjaan Tanah",
        sumber="SNI 2025",
    )
    AHSPReferensi.objects.create(
        kode_ahsp="02.01",
        nama_ahsp="Pekerjaan Beton",
        sumber="SNI 2025",
    )

    response = client.get(reverse("referensi:api_search_ahsp"), {"q": "Tanah"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == [
        {"id": obj.id, "text": "01.01 - Pekerjaan Tanah"}
    ]
