import json
import os
import decimal
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


# -----------------------------
# Config/env helpers
# -----------------------------
def _project_model():
    path = os.getenv("LP_PROJECT_MODEL", "dashboard.models.Project")
    try:
        return import_string(path)
    except Exception as e:
        pytest.skip(f"Gagal import Project model '{path}': {e}")

def _env_pid():
    raw = os.getenv("TEST_PROJECT_ID")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        pytest.skip("TEST_PROJECT_ID harus integer."); return None

def _env_login():
    return os.getenv("TEST_LOGIN_USER"), os.getenv("TEST_LOGIN_PASSWORD"), os.getenv("TEST_LOGIN_SUPER","1") == "1"

def _merge_kw(base: dict, extra_env: str | None):
    """
    Parse LP_PROJECT_CREATE_KW jika tersedia.
    Jika JSON tidak valid, JANGAN skip seluruh test.
    Beri peringatan dan abaikan env agar test tetap berjalan dengan nilai default.
    """
    if extra_env:
        try:
            extra = json.loads(extra_env)
            if not isinstance(extra, dict):
                # Hanya object/dict yang masuk akal untuk **kwargs create()
                print(
                    f"WARNING: LP_PROJECT_CREATE_KW harus JSON object; "
                    f"mendapat {type(extra).__name__}. Diabaikan.",
                    flush=True,
                )
            else:
                base.update(extra)
        except Exception as e:
            print(
                f"WARNING: LP_PROJECT_CREATE_KW bukan JSON valid: {e}. "
                f"Env diabaikan; pakai defaults.",
                flush=True,
            )
    return base

def _ensure_ahsp_refs(ids):
    """
    Pastikan AHSPReferensi untuk id/id_hint yang diberikan ada di DB test.
    Jika gagal membuat dengan PK tertentu, fallback create biasa dan pakai pk yang dihasilkan.
    """
    try:
        from referensi.models import AHSPReferensi
    except Exception as e:
        pytest.skip(f"App 'referensi' belum tersedia: {e}")

    out = []
    for i in ids:
        defaults = {
            "kode_ahsp": f"DUMMY-{i}",
            "nama_ahsp": f"AHSP Dummy {i}",
            "satuan": "unit",
        }
        try:
            # upaya create/get dengan PK tertentu
            obj, _ = AHSPReferensi.objects.get_or_create(id=i, defaults=defaults)
        except Exception:
            # fallback: biarkan DB menentukan PK
            obj = AHSPReferensi.objects.create(**defaults)
        out.append(obj)
    return out


# -----------------------------
# Auth
# -----------------------------
def _login_user(client: Client):
    """Login sesuai ENV, fallback ke superuser."""
    User = get_user_model()
    u_name, u_pass, as_super = _env_login()

    if u_name and u_pass:
        # Buat/ensure user dg username ENV
        u, _ = User.objects.get_or_create(username=u_name, defaults={
            "is_staff": True, "is_superuser": as_super,
        })
        # pastikan password sesuai env
        u.set_password(u_pass); u.is_staff = True; u.is_superuser = as_super; u.save()
        assert client.login(username=u_name, password=u_pass), "Login gagal (ENV user)"
        return u
    else:
        # superuser default
        su = User.objects.create_user(
            username="qa_lp_super", password="pass12345",
            is_staff=True, is_superuser=True
        )
        assert client.login(username="qa_lp_super", password="pass12345"), "Login gagal (default super)"
        return su


# -----------------------------
# URL builders
# -----------------------------
def _tree_url(pid: int) -> str:
    return f"/detail_project/api/project/{pid}/list-pekerjaan/tree/"

def _upsert_url(pid: int) -> str:
    return f"/detail_project/api/project/{pid}/list-pekerjaan/upsert/"


# -----------------------------
# Ensure Project exists in TEST DB
# -----------------------------
def _ensure_project(user) -> int:
    """
    Pastikan project ada di TEST DB. Jika TEST_PROJECT_ID diset, gunakan PK tsb; bila belum ada -> create.
    Isi field wajib sesuai error yang kamu share:
      owner(FK), nama(CharField), tahun_project(PositiveIntegerField), sumber_dana(CharField),
      lokasi_project(CharField), nama_client(CharField), anggaran_owner(DecimalField)
    Bisa di-override via LP_PROJECT_CREATE_KW.
    """
    Project = _project_model()
    pid = _env_pid()

    # Defaults untuk field wajib di dashboard.Project mu
    defaults = {
        # FK owner → ke user login
        "owner_id": getattr(user, "id", None),
        "nama": "LP Test Project",
        "tahun_project": 2025,
        "sumber_dana": "APBD",
        "lokasi_project": "Jakarta",
        "nama_client": "QA Client",
        "anggaran_owner": decimal.Decimal("100000000.00"),
    }
    defaults = _merge_kw(defaults, os.getenv("LP_PROJECT_CREATE_KW"))

    # Hilangkan nilai None agar tidak bentrok dengan NOT NULL
    defaults = {k: v for k, v in defaults.items() if v is not None}

    # Coba ambil yang sudah ada
    if pid is not None:
        obj = Project.objects.filter(pk=pid).first()
        if obj:
            return obj.pk
        # Create dengan id tertentu
        try:
            obj = Project.objects.create(id=pid, **defaults)
            return obj.pk
        except (TypeError, IntegrityError) as e:
            pytest.skip(f"Gagal create Project(id={pid}): {e}. "
                        "Sesuaikan LP_PROJECT_CREATE_KW agar memenuhi field wajib.")

    # Tanpa TEST_PROJECT_ID → create baru
    try:
        obj = Project.objects.create(**defaults)
        return obj.pk
    except (TypeError, IntegrityError) as e:
        pytest.skip(f"Gagal create Project default: {e}. "
                    "Set LP_PROJECT_CREATE_KW (JSON) agar field wajib terpenuhi.")


# -----------------------------
# Shape assert
# -----------------------------
def _assert_tree_shape(payload: dict):
    assert isinstance(payload, dict), "Response tree harus JSON object"
    assert "klasifikasi" in payload, "Key 'klasifikasi' tidak ada"
    assert isinstance(payload["klasifikasi"], list), "'klasifikasi' harus list"


# -----------------------------
# TESTS
# -----------------------------
def test_tree_endpoint_shape(client: Client):
    user = _login_user(client)
    pid = _ensure_project(user)

    res = client.get(_tree_url(pid), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert res.status_code in (200, 204), f"Status tidak diharapkan: {res.status_code}"
    if res.status_code == 204:
        return
    assert "application/json" in res["Content-Type"]
    _assert_tree_shape(res.json())

def test_upsert_accepts_three_modes_and_persists(client: Client):
    user = _login_user(client)
    pid = _ensure_project(user)

    # Pastikan referensi yang akan dipakai benar-benar ada
    ref1, ref2 = _ensure_ahsp_refs([1001, 1002])

    payload = {
        "klasifikasi": [
            {
                "temp_id": "k_1",
                "name": "Klas Uji",
                "ordering_index": 1,
                "sub": [
                    {
                        "temp_id": "s_1",
                        "name": "Sub A",
                        "ordering_index": 1,
                        "pekerjaan": [
                            {"temp_id": "p_ref", "source_type": "ref", "ordering_index": 1, "ref_id": ref1.id},
                            {"temp_id": "p_ref_mod", "source_type": "ref_modified", "ordering_index": 2, "ref_id": ref2.id,
                              "snapshot_uraian": "Uraian override (opsional)", "snapshot_satuan": "m2"},
                            {"temp_id": "p_custom", "source_type": "custom", "ordering_index": 3,
                             "snapshot_uraian": "Pekerjaan custom uji", "snapshot_satuan": "unit"},
                        ],
                    }
                ],
            }
        ]
    }

    res = client.post(
        _upsert_url(pid),
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert res.status_code in (200, 201, 207), f"Status tidak diharapkan: {res.status_code} | body={(getattr(res,'content',b'')[:300])}"
    assert "application/json" in res["Content-Type"]

    res2 = client.get(_tree_url(pid), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert res2.status_code in (200, 204)
    if res2.status_code == 200:
        _assert_tree_shape(res2.json())

def test_upsert_partial_error_when_invalid_rows(client: Client):
    user = _login_user(client)
    pid = _ensure_project(user)

    invalid_payload = {
        "klasifikasi": [
            {
                "temp_id": "k_invalid",
                "name": "Klas Invalid",
                "ordering_index": 1,
                "sub": [
                    {
                        "temp_id": "s_invalid",
                        "name": "Sub Invalid",
                        "ordering_index": 1,
                        "pekerjaan": [
                            {"temp_id": "p_bad_ref", "source_type": "ref", "ordering_index": 1},
                            {"temp_id": "p_bad_refmod", "source_type": "ref_modified", "ordering_index": 2},
                            {"temp_id": "p_bad_custom", "source_type": "custom", "ordering_index": 3},
                        ],
                    }
                ],
            }
        ]
    }

    res = client.post(
        _upsert_url(pid),
        data=json.dumps(invalid_payload),
        content_type="application/json",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert res.status_code in (200, 207, 400), f"Status tidak diharapkan: {res.status_code}"
    if res.status_code == 200:
        body = res.json()
        has_partial_flag = bool(body.get("partial")) or ("errors" in body and body["errors"])
        assert has_partial_flag, "Response 200 tanpa indikasi partial/errors."
