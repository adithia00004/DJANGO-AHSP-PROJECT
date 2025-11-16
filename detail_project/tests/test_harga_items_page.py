import pytest
from django.conf import settings
from django.urls import reverse

from decimal import Decimal

from detail_project.models import (
    HargaItemProject,
    Pekerjaan,
    DetailAHSPProject,
    DetailAHSPExpanded,
)


@pytest.mark.django_db
def test_harga_items_page_requires_login(client, project):
    url = reverse("detail_project:harga_items", args=[project.id])
    response = client.get(url)
    assert response.status_code == 302
    assert settings.LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_harga_items_page_context(client_logged, project):
    url = reverse("detail_project:harga_items", args=[project.id])
    response = client_logged.get(url)
    assert response.status_code == 200
    assert response.context["project"] == project
    assert response.context["side_active"] == "harga_items"
    template_names = [tmpl.name for tmpl in response.templates if tmpl.name]
    assert "detail_project/harga_items.html" in template_names


@pytest.mark.django_db
def test_harga_items_api_search_filters_results(client_logged, project, sub_klas):
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-9999",
        snapshot_uraian="Dummy",
        snapshot_satuan="OH",
        ordering_index=1,
    )
    harga = HargaItemProject.objects.create(
        project=project, kode_item="TK-001", uraian="Mandor", kategori="TK"
    )
    detail = DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga,
        kategori="TK",
        kode="TK.001",
        uraian="Mandor",
        satuan="OH",
        koefisien=Decimal("1.000000"),
    )
    DetailAHSPExpanded.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        source_detail=detail,
        harga_item=harga,
        kategori="TK",
        kode="TK.001",
        uraian="Mandor",
        satuan="OH",
        koefisien=Decimal("1.000000"),
        source_bundle_kode=None,
        expansion_depth=0,
    )

    url_list = reverse("detail_project:api_list_harga_items", kwargs={"project_id": project.id})
    resp = client_logged.get(url_list, {"q": "Mandor"})
    assert resp.status_code == 200
    data = resp.json()
    rows = data.get("items") or data.get("rows") or []
    assert any("mandor" in (row.get("uraian") or "").lower() for row in rows)
