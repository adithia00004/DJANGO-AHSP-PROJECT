import csv
import io
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_rekap_kebutuhan_api_has_meta(client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5):
    resp = client_logged.get(reverse("detail_project:api_get_rekap_kebutuhan", args=[project.id]))
    assert resp.status_code == 200
    js = resp.json()
    assert "rows" in js
    assert "meta" in js
    m = js["meta"]
    assert "counts_per_kategori" in m
    assert "n_rows" in m
    assert isinstance(m["counts_per_kategori"], dict)

@pytest.mark.django_db
def test_export_csv_basic(client_logged, project, pekerjaan_custom, detail_tk_smoke, volume5):
    resp = client_logged.get(reverse("detail_project:api_export_rekap_kebutuhan_csv", args=[project.id]))
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    body = resp.content.decode("utf-8")
    # Skip comment lines (metadata headers) and find data header
    lines = [ln for ln in body.splitlines() if ln.strip()]
    # Find first non-comment line (data header)
    data_lines = [ln for ln in lines if not ln.startswith("#")]
    assert data_lines, "CSV should have data lines after comments"
    assert data_lines[0].startswith("kategori;kode;uraian;satuan;quantity")

