import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

class StubPricing:
    def __init__(self, mp="10.00", ppn="11.00", rb=10000):
        self.markup_percent = Decimal(mp)
        self.ppn_percent = Decimal(ppn)
        self.rounding_base = int(rb)
    def save(self, update_fields=None):
        pass

class StubProject:
    id = 82

@pytest.fixture
def user():
    U = get_user_model()
    return U.objects.create_user(username="tester2", password="x")

@pytest.fixture
def client_logged(client, user):
    client.force_login(user)
    return client

@pytest.fixture
def stubbed_env(monkeypatch):
    from detail_project import views_api as v
    project = StubProject()
    pricing = StubPricing()
    # Hindari akses DB nyata
    monkeypatch.setattr(v, "_owner_or_404", lambda project_id, user: project)
    monkeypatch.setattr(v, "_get_or_create_pricing", lambda project: pricing)
    # Buat compute_rekap_for_project mengembalikan baris minimal TANPA pekerjaan_id (agar tidak query Pekerjaan)
    monkeypatch.setattr(v, "compute_rekap_for_project", lambda project: [{"uraian": "Dummy Row"}])
    return pricing

def _url(pid=82):
    return f"/detail_project/api/project/{pid}/rekap/"

def test_get_rekap_meta_and_rows(client_logged, stubbed_env):
    resp = client_logged.get(_url())
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    # meta lengkap & format benar
    meta = data["meta"]
    assert meta["markup_percent"] == "10.00"
    assert meta["ppn_percent"] == "11.00"
    assert isinstance(meta["rounding_base"], int)
    # rows ada & setiap row mendapatkan markup_eff (float) dari default project
    assert isinstance(data["rows"], list) and len(data["rows"]) >= 1
    assert "markup_eff" in data["rows"][0]
    assert isinstance(data["rows"][0]["markup_eff"], float) and abs(data["rows"][0]["markup_eff"] - 10.0) < 1e-9
