import pytest
from django.conf import settings
from django.urls import reverse


@pytest.mark.django_db
def test_list_pekerjaan_page_requires_login(client, project):
    url = reverse("detail_project:list_pekerjaan", args=[project.id])

    response = client.get(url)

    assert response.status_code == 302
    assert settings.LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_list_pekerjaan_page_context(client_logged, project):
    url = reverse("detail_project:list_pekerjaan", args=[project.id])

    response = client_logged.get(url)

    assert response.status_code == 200
    assert response.context["project"] == project
    assert response.context["side_active"] == "list_pekerjaan"
    template_names = [tmpl.name for tmpl in response.templates if tmpl.name]
    assert "detail_project/list_pekerjaan.html" in template_names
