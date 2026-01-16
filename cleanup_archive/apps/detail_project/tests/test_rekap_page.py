import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_rekap_rab_page_requires_login(client, project):
    url = reverse("detail_project:rekap_rab", args=[project.id])
    response = client.get(url)

    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_rekap_rab_page_context(client_logged, project):
    url = reverse("detail_project:rekap_rab", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    assert response.context["project"] == project
    assert response.context["side_active"] == "rekap_rab"
    template_names = [tmpl.name for tmpl in response.templates if tmpl.name]
    assert "detail_project/rekap_rab.html" in template_names
