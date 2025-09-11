# detail_project/tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

User = get_user_model()

@pytest.fixture
def user(db):
    try:
        u = User.objects.create_user(email="u@example.com", password="pass")
    except TypeError:
        u = User.objects.create_user(username="u", password="pass")
    return u

@pytest.fixture
def client_login(client, user):
    client.force_login(user)
    return client, user

@pytest.fixture
def project(client_login):
    from dashboard.models import Project
    client, user = client_login

    params = {
        "owner": user,
        "nama": "Proyek Uji",
        # Tambahan untuk NOT NULL di model kamu:
        "tahun_project": date.today().year,     # <- FIX baru
        "anggaran_owner": Decimal("0"),         # <- FIX sebelumnya
    }
    # Kalau modelmu tidak punya salah satu field di atas, aman—Django akan abaikan lewat kwargs?
    # Tidak—jadi kita aman-aman saja karena keduanya memang ada pada modelmu.

    return Project.objects.create(**params)

@pytest.fixture
def ahsp_ref(db):
    from referensi.models import AHSPReferensi
    return AHSPReferensi.objects.create(
        kode_ahsp="1.1.1.1",
        nama_ahsp="Galian Tanah",
    )
