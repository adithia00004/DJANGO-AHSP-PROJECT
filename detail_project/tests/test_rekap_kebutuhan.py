# detail_project/tests/test_rekap_kebutuhan.py
import pytest
from decimal import Decimal
from django.urls import reverse


@pytest.mark.django_db
def test_rekap_kebutuhan_page_and_api_smoke(client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5):
    # Halaman web
    page = client_logged.get(reverse("detail_project:rekap_kebutuhan", args=[project.id]))
    assert page.status_code == 200
    assert b'id="rk-app"' in page.content

    # API
    api = client_logged.get(reverse("detail_project:api_get_rekap_kebutuhan", args=[project.id]))
    assert api.status_code == 200
    js = api.json()
    assert isinstance(js.get("rows", []), list)


@pytest.mark.django_db
def test_rekap_kebutuhan_totals(client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5):
    api = client_logged.get(reverse("detail_project:api_get_rekap_kebutuhan", args=[project.id]))
    assert api.status_code == 200
    rows = api.json().get("rows", [])

    def q(kode: str):
        r = next((r for r in rows if r["kode"] == kode), None)
        return Decimal(r["quantity"]) if r else None

    # TK.SMOKE = 0.125 * 5.000 = 0.625000
    assert q("TK.SMOKE") == Decimal("0.625000")
