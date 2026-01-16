import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse

from detail_project.models import PekerjaanProgressWeekly


@pytest.mark.django_db
def test_kurva_s_harga_returns_evm_data(client_logged, project_with_dates, pekerjaan_with_volume):
    project_with_dates.tanggal_mulai = date(2025, 1, 1)
    project_with_dates.save(update_fields=["tanggal_mulai"])

    pekerjaan_with_volume.budgeted_cost = Decimal("1000000.00")
    pekerjaan_with_volume.save(update_fields=["budgeted_cost"])

    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan_with_volume,
        project=project_with_dates,
        week_number=1,
        week_start_date=date(2025, 1, 1),
        week_end_date=date(2025, 1, 7),
        planned_proportion=Decimal("50.00"),
        actual_proportion=Decimal("40.00"),
        actual_cost=Decimal("300000.00"),
    )
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan_with_volume,
        project=project_with_dates,
        week_number=2,
        week_start_date=date(2025, 1, 8),
        week_end_date=date(2025, 1, 14),
        planned_proportion=Decimal("50.00"),
        actual_proportion=Decimal("60.00"),
        actual_cost=Decimal("450000.00"),
    )

    url = reverse('detail_project:api_kurva_s_harga_data', args=[project_with_dates.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_project_cost"] == pytest.approx(1000000.0)
    assert "evm" in data and data["evm"]["labels"]
    assert data["evm"]["summary"]["bac"] == pytest.approx(1000000.0)
    assert data["evm"]["summary"]["actual_cost"] > 0


@pytest.mark.django_db
def test_kurva_s_harga_handles_zero_budget(monkeypatch, client_logged, project_with_dates, pekerjaan_with_volume):
    """
    Ketika total biaya proyek 0 (tidak ada rekap & budgeted_cost), API harus memberi fallback agar kurva tidak flat.
    """
    project_with_dates.tanggal_mulai = date(2025, 2, 1)
    project_with_dates.save(update_fields=["tanggal_mulai"])

    # Pastikan budgeted_cost 0 sehingga total_project_cost normalnya ikut 0.
    pekerjaan_with_volume.budgeted_cost = Decimal("0")
    pekerjaan_with_volume.save(update_fields=["budgeted_cost"])

    # Monkeypatch compute_rekap_for_project agar mengembalikan list kosong (simulasi belum ada rekap RAB).
    monkeypatch.setattr(
        "detail_project.views_api.compute_rekap_for_project",
        lambda project: [],
    )

    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan_with_volume,
        project=project_with_dates,
        week_number=1,
        week_start_date=date(2025, 2, 1),
        week_end_date=date(2025, 2, 7),
        planned_proportion=Decimal("25.00"),
        actual_proportion=Decimal("20.00"),
    )
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan_with_volume,
        project=project_with_dates,
        week_number=2,
        week_start_date=date(2025, 2, 8),
        week_end_date=date(2025, 2, 14),
        planned_proportion=Decimal("40.00"),
        actual_proportion=Decimal("35.00"),
    )

    url = reverse("detail_project:api_kurva_s_harga_data", args=[project_with_dates.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    data = response.json()

    # Dengan fallback, total_project_cost tidak lagi 0 dan cumulative_cost > 0.
    assert data["summary"]["total_project_cost"] > 0
    assert data["summary"]["planned_cost"] > 0
    assert data["weeklyData"]["planned"][0]["cumulative_cost"] > 0
    assert data["evm"]["summary"]["planned_cost"] > 0
