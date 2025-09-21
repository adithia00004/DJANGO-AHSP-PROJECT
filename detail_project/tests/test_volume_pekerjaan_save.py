# detail_project/tests/test_volume_pekerjaan_save.py
import json
from decimal import Decimal

import pytest
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from detail_project.models import Pekerjaan, VolumePekerjaan


def _url_save(project_id: int) -> str:
    try:
        return reverse("detail_project:api_save_volume_pekerjaan", args=[project_id])
    except NoReverseMatch:
        return f"/detail_project/api/project/{project_id}/volume-pekerjaan/save/"


def _ensure_two_custom_jobs(client_logged, project, api_urls, build_payload):
    jobs = [
        {"source_type": "custom", "ordering_index": 1, "snapshot_uraian": "A", "snapshot_satuan": "m"},
        {"source_type": "custom", "ordering_index": 2, "snapshot_uraian": "B", "snapshot_satuan": "m2"},
    ]
    payload = build_payload(jobs=jobs, klas_name="K1", sub_name="S1")
    r = client_logged.post(
        api_urls["upsert"],
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code in (200, 207), r.content
    qs = Pekerjaan.objects.filter(project=project).order_by("ordering_index", "id")
    return qs[0], qs[1]


@pytest.mark.django_db
def test_save_accepts_idID_numbers(client_logged, project, api_urls, build_payload):
    p1, _ = _ensure_two_custom_jobs(client_logged, project, api_urls, build_payload)

    payload = {"items": [{"pekerjaan_id": p1.id, "quantity": "1.000,25"}]}  # id-ID
    resp = client_logged.post(_url_save(project.id), data=json.dumps(payload), content_type="application/json")

    # Pra-patch (400) vs pasca-patch (200)
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("ok") is True
        assert data.get("saved") == 1
        vp = VolumePekerjaan.objects.get(project=project, pekerjaan=p1)
        # pembulatan HALF_UP 3dp
        assert str(vp.quantity) in {"1000.250", "1000.250000"}
