import json
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from detail_project.models import (
    DetailAHSPAudit,
    DetailAHSPProject,
    DetailAHSPExpanded,
    HargaItemProject,
    Pekerjaan,
    ProjectChangeStatus,
)
from detail_project.services import (
    _populate_expanded_from_raw,
    cascade_bundle_re_expansion,
)


def _make_detail(project, pekerjaan, kode="TK.001"):
    harga = HargaItemProject.objects.create(
        project=project,
        kode_item=kode,
        kategori="TK",
        uraian="Pekerja",
        satuan="OH",
        harga_satuan=Decimal("150000"),
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga,
        kategori="TK",
        kode=kode,
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("1.0"),
    )
    DetailAHSPExpanded.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        source_detail=DetailAHSPProject.objects.filter(
            project=project, pekerjaan=pekerjaan, kode=kode
        ).first(),
        harga_item=harga,
        kategori="TK",
        kode=kode,
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("1.0"),
        source_bundle_kode=None,
        expansion_depth=0,
    )


@pytest.mark.django_db
def test_save_detail_logs_audit_entry(client_logged, project, pekerjaan_custom):
    url = reverse(
        "detail_project:api_save_detail_ahsp_for_pekerjaan",
        args=[project.id, pekerjaan_custom.id],
    )
    payload = {
        "rows": [
            {
                "kategori": "TK",
                "kode": "TK.010",
                "uraian": "Audit Item",
                "satuan": "OH",
                "koefisien": "1.5",
            }
        ]
    }

    resp = client_logged.post(
        url, data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 200

    entry = DetailAHSPAudit.objects.filter(
        project=project, pekerjaan=pekerjaan_custom
    ).first()
    assert entry is not None
    assert entry.action == DetailAHSPAudit.ACTION_CREATE
    assert entry.new_data


@pytest.mark.django_db
def test_audit_api_returns_results(client_logged, project, pekerjaan_custom):
    DetailAHSPAudit.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        action=DetailAHSPAudit.ACTION_UPDATE,
        change_summary="Manual entry",
    )

    url = reverse("detail_project:api_get_audit_trail", args=[project.id])
    resp = client_logged.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["results"]


@pytest.mark.django_db
def test_cascade_operation_logs_audit(project, pekerjaan_custom, sub_klas):
    pekerjaan_bundle = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="BND.001",
        snapshot_uraian="Bundle",
        snapshot_satuan="SET",
        ordering_index=2,
    )

    _make_detail(project, pekerjaan_custom, kode="TK.020")

    bundle_price = HargaItemProject.objects.create(
        project=project,
        kode_item="LAIN.BUNDLE",
        kategori="LAIN",
        uraian="Bundle Ref",
        satuan="SET",
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_bundle,
        harga_item=bundle_price,
        kategori="LAIN",
        kode="LAIN.001",
        uraian="Bundle Ref",
        satuan="SET",
        koefisien=Decimal("1.0"),
        ref_pekerjaan=pekerjaan_custom,
    )

    _populate_expanded_from_raw(project, pekerjaan_custom)
    _populate_expanded_from_raw(project, pekerjaan_bundle)

    cascade_bundle_re_expansion(project, pekerjaan_custom.id)

    assert DetailAHSPAudit.objects.filter(
        project=project,
        pekerjaan=pekerjaan_bundle,
        action=DetailAHSPAudit.ACTION_CASCADE,
    ).exists()


@pytest.mark.django_db
def test_change_status_api_reports_changes(client_logged, project, pekerjaan_custom):
    tracker = ProjectChangeStatus.objects.create(project=project, last_harga_change=timezone.now())
    pekerjaan_custom.detail_last_modified = timezone.now()
    pekerjaan_custom.save(update_fields=["detail_last_modified"])

    url = reverse("detail_project:api_get_change_status", args=[project.id])
    resp = client_logged.get(url)
    data = resp.json()

    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["harga_changed_at"] == tracker.last_harga_change.isoformat()
    assert data["affected_pekerjaan_count"] == 1


@pytest.mark.django_db
def test_change_status_api_invalid_date(client_logged, project):
    url = reverse("detail_project:api_get_change_status", args=[project.id])
    resp = client_logged.get(url + "?since_ahsp=invalid-date")
    assert resp.status_code == 400
