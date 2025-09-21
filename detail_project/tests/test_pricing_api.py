import json
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

# ====== Stub kecil agar view tidak menyentuh DB ProjectPricing/Project ======
class StubPricing:
    def __init__(self, mp="10.00", ppn="11.00", rb=10000):
        self.markup_percent = Decimal(mp)
        self.ppn_percent = Decimal(ppn)
        self.rounding_base = int(rb)
        self._saved_fields = None

    def save(self, update_fields=None):
        # View memanggil obj.save(update_fields=...)
        self._saved_fields = list(update_fields or [])

class StubProject:
    id = 82

@pytest.fixture
def user():
    U = get_user_model()
    return U.objects.create_user(username="tester", password="x")

@pytest.fixture
def client_logged(client, user):
    client.force_login(user)
    return client

@pytest.fixture
def stubbed_env(monkeypatch):
    # Patch helper dalam module views_api
    from detail_project import views_api as v
    project = StubProject()
    pricing = StubPricing()

    monkeypatch.setattr(v, "_owner_or_404", lambda project_id, user: project)
    monkeypatch.setattr(v, "_get_or_create_pricing", lambda project: pricing)
    # kembalikan objek yang bisa kita inspeksi setelah request
    return pricing

def _url(pid=82):
    return f"/detail_project/api/project/{pid}/pricing/"

def test_get_pricing_ok(client_logged, stubbed_env):
    resp = client_logged.get(_url())
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    # bentuk string utk persen, int utk base
    assert data["markup_percent"] == "10.00"
    assert data["ppn_percent"] == "11.00"
    assert isinstance(data["rounding_base"], int)
    # seharusnya TIDAK ada 'updated_fields' (penyebab 500 sebelumnya)
    assert "updated_fields" not in data

def test_post_pricing_ok_updates_values(client_logged, stubbed_env):
    payload = {"markup_percent": "12,5", "ppn_percent": "10", "rounding_base": 5000}
    resp = client_logged.post(_url(), data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.json()
    # response ter-format
    assert data["markup_percent"] == "12.50"
    assert data["ppn_percent"] == "10.00"
    assert data["rounding_base"] == 5000
    # objek stub ikut berubah & tercatat save()
    assert stubbed_env.markup_percent == Decimal("12.50")
    assert stubbed_env.ppn_percent == Decimal("10.00")
    assert stubbed_env.rounding_base == 5000
    # updated_fields minimal berisi salah satu field yg diubah + updated_at
    assert getattr(stubbed_env, "_saved_fields") and "updated_at" in stubbed_env._saved_fields

@pytest.mark.parametrize(
    "payload, bad_field",
    [
        ({"markup_percent": "abc"}, "markup_percent"),
        ({"ppn_percent": "-1"}, "ppn_percent"),
        ({"rounding_base": 0}, "rounding_base"),
    ],
)
def test_post_pricing_validation_errors(client_logged, payload, bad_field):
    resp = client_logged.post(_url(), data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    # pastikan error menyebut field yang salah
    assert any(e.get("path") == bad_field for e in data.get("errors", []))
