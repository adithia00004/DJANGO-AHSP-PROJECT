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

    row = next((r for r in rows if r["kode"] == "TK.SMOKE"), None)
    assert row is not None
    assert row.get("harga_satuan") == "1"
    assert row.get("harga_total") == "0.625"


@pytest.mark.django_db
def test_rekap_kebutuhan_syncs_with_jadwal_progress(client_logged, project_with_dates, pekerjaan_with_volume):
    """
    Phase 3 Verification: Rekap Kebutuhan should reflect changes after Jadwal modification.
    
    This test verifies that when PekerjaanProgressWeekly data is modified,
    the Rekap Kebutuhan API returns fresh data on reload (not stale cached data).
    """
    from detail_project.models import PekerjaanProgressWeekly
    from datetime import date
    from decimal import Decimal
    
    project = project_with_dates
    pekerjaan = pekerjaan_with_volume
    
    # Use correct enhanced API endpoint
    url = reverse("detail_project:api_get_rekap_kebutuhan_enhanced", args=[project.id])
    
    # Initial API call - should have pekerjaan_without_progress
    resp1 = client_logged.get(url)
    assert resp1.status_code == 200
    data1 = resp1.json()
    
    # Check pekerjaan_without_progress field exists in meta
    meta = data1.get("meta", {})
    initial_without_progress = meta.get("pekerjaan_without_progress", [])
    
    # Verify our pekerjaan is in the list (no progress yet)
    pekerjaan_ids_without = [p["id"] for p in initial_without_progress]
    assert pekerjaan.id in pekerjaan_ids_without, \
        f"Pekerjaan {pekerjaan.id} should be in without_progress list, got {pekerjaan_ids_without}"
    
    # Add progress for this pekerjaan
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan,
        project=project,
        week_number=1,
        week_start_date=date(2025, 1, 1),
        week_end_date=date(2025, 1, 7),
        planned_proportion=Decimal('50.00'),
        actual_proportion=Decimal('0.00')
    )
    
    # Reload API - should reflect the change
    resp2 = client_logged.get(url)
    assert resp2.status_code == 200
    data2 = resp2.json()
    
    # Verify pekerjaan is now NOT in without_progress list
    meta2 = data2.get("meta", {})
    updated_without_progress = meta2.get("pekerjaan_without_progress", [])
    pekerjaan_ids_without2 = [p["id"] for p in updated_without_progress]
    
    assert pekerjaan.id not in pekerjaan_ids_without2, \
        "Pekerjaan should be removed from without_progress after adding progress"


