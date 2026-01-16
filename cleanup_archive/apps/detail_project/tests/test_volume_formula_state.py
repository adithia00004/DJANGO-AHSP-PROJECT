# detail_project/tests/test_volume_formula_state.py
import json
import importlib
from decimal import Decimal

import pytest
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.test.client import Client

from detail_project.models import Pekerjaan, Klasifikasi, SubKlasifikasi


def _url_formula(project_id: int) -> str:
    """
    Urutkan kandidat:
      1) named route (disarankan)
      2) /volume/formula/ (punya kamu)
      3) /volume-formula-state/ (alias/legacy)
    """
    try:
        return reverse("detail_project:api_volume_formula_state", args=[project_id])
    except NoReverseMatch:
        pass
    return f"/detail_project/api/project/{project_id}/volume/formula/"


def _make_project_minimal(owner):
    """
    Buat Project robust: isi field wajib (null=False tanpa default).
    """
    Project = getattr(importlib.import_module("dashboard.models"), "Project")
    from django.utils import timezone
    from django.db import models as djm

    fields = Project._meta.fields
    kwargs = {}

    if any(f.name == "owner" for f in fields):
        kwargs["owner"] = owner

    for f in fields:
        if f.auto_created or f.primary_key or f.name in kwargs:
            continue
        if f.has_default() or getattr(f, "null", False):
            continue

        if isinstance(f, djm.BooleanField):
            kwargs[f.name] = True
        elif isinstance(f, djm.CharField):
            kwargs[f.name] = "Proj Lain"
        elif isinstance(f, djm.IntegerField):
            kwargs[f.name] = 2025
        elif isinstance(f, djm.DecimalField):
            q = Decimal("0").quantize(Decimal(f"1e-{f.decimal_places}"))
            kwargs[f.name] = q
        elif isinstance(f, djm.DateTimeField):
            kwargs[f.name] = timezone.now()
        elif isinstance(f, djm.DateField):
            kwargs[f.name] = timezone.now().date()

    if "is_active" in [f.name for f in fields]:
        kwargs["is_active"] = True

    return Project.objects.create(**kwargs)


def _ensure_two_custom_jobs(client_logged: Client, project, api_urls, build_payload):
    """
    Pastikan ada 2 pekerjaan custom melalui upsert API.
    """
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
    p1, p2 = qs[0], qs[1]
    return p1, p2


# =========================
# TESTS
# =========================
@pytest.mark.django_db
def test_formula_state_get_empty(client_logged, project):
    resp = client_logged.get(_url_formula(project.id))
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data.get("ok") is True
    assert isinstance(data.get("items"), list)
    assert data["items"] == []


@pytest.mark.django_db
def test_formula_state_create_update(client_logged, project, api_urls, build_payload):
    p1, p2 = _ensure_two_custom_jobs(client_logged, project, api_urls, build_payload)

    payload = {
        "items": [
            {"pekerjaan_id": p1.id, "raw": "= Panjang * Lebar", "is_fx": True},
            {"pekerjaan_id": p2.id, "raw": "=", "is_fx": True},
        ]
    }
    resp = client_logged.post(
        _url_formula(project.id),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("created", 0) >= 1

    payload2 = {"items": [{"pekerjaan_id": p1.id, "raw": "", "is_fx": False}]}
    resp2 = client_logged.post(
        _url_formula(project.id),
        data=json.dumps(payload2),
        content_type="application/json",
    )
    assert resp2.status_code == 200, resp2.content
    d2 = resp2.json()
    assert d2.get("ok") is True
    assert d2.get("updated", 0) >= 1

    g = client_logged.get(_url_formula(project.id))
    assert g.status_code == 200
    items = g.json().get("items") or []
    as_map = {it["pekerjaan_id"]: it for it in items}
    assert as_map[p1.id]["raw"] == ""
    assert as_map[p1.id]["is_fx"] is False
    assert as_map[p2.id]["is_fx"] is True


@pytest.mark.django_db
def test_formula_state_reject_foreign_job(client_logged, user, project, api_urls, build_payload):
    _ensure_two_custom_jobs(client_logged, project, api_urls, build_payload)

    # Proyek lain
    other = _make_project_minimal(user)
    klas = Klasifikasi.objects.create(project=other, name="KX", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=other, klasifikasi=klas, name="SX", ordering_index=1)
    foreign_job = Pekerjaan.objects.create(
        project=other, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="X-1",
        snapshot_uraian="Foreign", snapshot_satuan="m", ordering_index=1
    )

    payload = {"items": [{"pekerjaan_id": foreign_job.id, "raw": "=1", "is_fx": True}]}
    resp = client_logged.post(
        _url_formula(project.id),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        errs = resp.json().get("errors") or []
        assert any("pekerjaan_id" in (e.get("path") or "") for e in errs)
