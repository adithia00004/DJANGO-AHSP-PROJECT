import json
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse

from detail_project.models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
)
from detail_project.services import (
    detect_orphaned_items,
    cleanup_orphaned_items,
)


def _create_harga_item(project, kode, kategori="TK", harga="150000"):
    return HargaItemProject.objects.create(
        project=project,
        kode_item=kode,
        uraian=f"Item {kode}",
        kategori=kategori,
        satuan="OH",
        harga_satuan=Decimal(harga),
    )


def _attach_detail(project, pekerjaan, harga_item):
    detail = DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_item,
        kategori="TK",
        kode=f"{harga_item.kode_item}",
        uraian="Detail Used",
        satuan="OH",
        koefisien=Decimal("1.0"),
    )
    DetailAHSPExpanded.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        source_detail=detail,
        harga_item=harga_item,
        kategori="TK",
        kode=detail.kode,
        uraian=detail.uraian,
        satuan=detail.satuan,
        koefisien=Decimal("1.0"),
        source_bundle_kode=None,
        expansion_depth=0,
    )


@pytest.mark.django_db
def test_detect_orphaned_items_returns_only_unused(project, pekerjaan_custom):
    orphan = _create_harga_item(project, "ORP.001")
    used = _create_harga_item(project, "USE.001")
    _attach_detail(project, pekerjaan_custom, used)

    items, total_value = detect_orphaned_items(project)

    assert len(items) == 1
    assert items[0]["id"] == orphan.id
    assert total_value == orphan.harga_satuan


@pytest.mark.django_db
def test_api_list_orphaned_items_returns_payload(client_logged, project):
    item = _create_harga_item(project, "ORP.002", harga="250000")
    url = reverse("detail_project:api_list_orphaned_items", args=[project.id])

    response = client_logged.get(url)
    data = response.json()

    assert response.status_code == 200
    assert data["ok"] is True
    assert data["orphaned_count"] == 1
    assert data["orphaned_items"][0]["kode"] == item.kode_item
    assert "total_value" in data


@pytest.mark.django_db
def test_api_cleanup_orphaned_items_deletes_only_orphans(
    client_logged, project, pekerjaan_custom
):
    orphan = _create_harga_item(project, "ORP.003")
    used = _create_harga_item(project, "USE.002")
    _attach_detail(project, pekerjaan_custom, used)

    url = reverse("detail_project:api_cleanup_orphaned_items", args=[project.id])
    payload = {"item_ids": [orphan.id, used.id], "confirm": True}

    response = client_logged.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )
    data = response.json()

    assert response.status_code == 200
    assert data["deleted_count"] == 1
    assert orphan.id not in HargaItemProject.objects.filter(project=project).values_list(
        "id", flat=True
    )
    assert used.id in HargaItemProject.objects.filter(project=project).values_list(
        "id", flat=True
    )
    assert used.id in data["skipped_ids"]


@pytest.mark.django_db
def test_api_cleanup_requires_confirmation(client_logged, project):
    _create_harga_item(project, "ORP.004")
    url = reverse("detail_project:api_cleanup_orphaned_items", args=[project.id])
    response = client_logged.post(
        url,
        data=json.dumps({"item_ids": [999], "confirm": False}),
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_cleanup_helper_dry_run(project, pekerjaan_custom):
    orphan = _create_harga_item(project, "ORP.005")
    _create_harga_item(project, "USE.005")
    result = cleanup_orphaned_items(project, dry_run=True)
    assert result["candidate_count"] >= 1
    assert orphan.id in result["target_ids"]
    assert HargaItemProject.objects.filter(id=orphan.id).exists()


@pytest.mark.django_db
def test_cleanup_command_removes_orphan(project, pekerjaan_custom):
    orphan = _create_harga_item(project, "ORP.006")
    out = StringIO()
    call_command("cleanup_orphans", project_id=project.id, stdout=out)
    assert not HargaItemProject.objects.filter(id=orphan.id).exists()
