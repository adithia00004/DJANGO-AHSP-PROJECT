import json
import pytest
from django.urls import reverse
from dashboard.models import Project
from detail_project.models import ProjectPricing
from decimal import Decimal
from django.utils import timezone  # NEW

@pytest.mark.django_db
def test_pricing_get_and_set(client, django_user_model):
    # setup user & login
    user = django_user_model.objects.create_user(username="u", password="p")
    client.login(username="u", password="p")

    # project owned by user
    p = Project.objects.create(
        owner=user,
        nama="P1",
        is_active=True,
        tahun_project=timezone.now().year,  # NEW
        anggaran_owner=Decimal('0'),
    )

    # GET default
    url = reverse("detail_project:api_project_pricing", args=[p.id])
    r = client.get(url)
    j = r.json()
    assert r.status_code == 200 and j["ok"] is True
    assert j["markup_percent"] == "10.00"  # default model

    # POST valid 12,5
    r = client.post(url, data=json.dumps({"markup_percent": "12,5"}), content_type="application/json")
    j = r.json()
    assert r.status_code == 200 and j["ok"] is True and j["markup_percent"] == "12.50"
    obj = ProjectPricing.objects.get(project=p)
    assert float(obj.markup_percent) == 12.5

    # POST invalid >100
    r = client.post(url, data=json.dumps({"markup_percent": "120"}), content_type="application/json")
    assert r.status_code == 400
