# detail_project/tests/conftest.py
import os
import copy
import json
import importlib
import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.db import models as djm, IntegrityError


# ================= Helpers =================
def _import_project_model():
    mod = importlib.import_module("dashboard.models")
    return getattr(mod, "Project")


def _env_json(name, default=None):
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _mk_minimal(model, **kw):
    """
    Buat instance minimal untuk model terkait hirarki klasifikasi.
    Caller WAJIB mengirim argumen yang NOT NULL (mis. project/klasifikasi).
    """
    fields = {f.name: f for f in model._meta.fields}
    data = {k: v for k, v in kw.items() if k in fields}

    # isi default umum
    if "name" in fields and "name" not in data:
        data["name"] = "QA"
    if "nama" in fields and "nama" not in data:
        data["nama"] = "QA"
    if "ordering_index" in fields and "ordering_index" not in data:
        data["ordering_index"] = 0

    return model.objects.create(**data)


# ================= Users / Client =================
@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="tester",
        email="tester@example.com",
        password="secret",
    )


@pytest.fixture
def other_user(db):
    """Create a second user for multi-user testing."""
    User = get_user_model()
    return User.objects.create_user(
        username="other_tester",
        email="other@example.com",
        password="secret",
    )


@pytest.fixture
def client_logged(db, user):
    c = Client()
    c.force_login(user)
    # Hindari DisallowedHost ketika pakai test client
    c.defaults["HTTP_HOST"] = "testserver"
    return c


# ================= Project =================
@pytest.fixture
def project(db, user):
    Project = _import_project_model()
    fields = {f.name for f in Project._meta.fields}

    kw = {"nama": "Project QA LP"}
    if "owner" in fields:
        kw["owner"] = user
    if "is_active" in fields:
        kw["is_active"] = True
    if "anggaran_owner" in fields:
        kw["anggaran_owner"] = 0

    # Override opsional via ENV (mis. field wajib lain)
    env_kw = _env_json("LP_PROJECT_CREATE_KW", {}) or {}
    kw.update({k: v for k, v in env_kw.items() if k in fields})

    # Pastikan tahun_project terisi bila NOT NULL
    if "tahun_project" in fields and not kw.get("tahun_project"):
        kw["tahun_project"] = date.today().year

    return Project.objects.create(**kw)


@pytest.fixture
def project_id(project):
    return project.id


# ================= SubKlasifikasi (untuk FK Pekerjaan) =================
@pytest.fixture
def sub_klas(db, project):
    """
    Buat satu SubKlasifikasi sesuai tipe FK di Pekerjaan.sub_klasifikasi,
    beserta parent Klasifikasi bila ada (dan set FK project pada Klasifikasi & SubKlasifikasi jika diperlukan).
    """
    from detail_project.models import Pekerjaan

    sub_f = Pekerjaan._meta.get_field("sub_klasifikasi")
    SubModel = sub_f.remote_field.model  # model SubKlasifikasi actual

    fields = {f.name: f for f in SubModel._meta.fields}
    kwargs = {}

    # Jika SubModel punya FK 'project' → wajib isi project
    if "project" in fields and isinstance(fields["project"], djm.ForeignKey):
        kwargs["project"] = project

    # Jika SubModel punya FK 'klasifikasi' → buat parent Klasifikasi (biasanya juga butuh project)
    if "klasifikasi" in fields and isinstance(fields["klasifikasi"], djm.ForeignKey):
        KlasModel = fields["klasifikasi"].remote_field.model
        klas_kwargs = {}
        kfields = {f.name: f for f in KlasModel._meta.fields}
        if "project" in kfields and isinstance(kfields["project"], djm.ForeignKey):
            klas_kwargs["project"] = project
        klas = _mk_minimal(KlasModel, **klas_kwargs)
        kwargs["klasifikasi"] = klas

    # Nama sub
    if "nama" in fields:
        kwargs.setdefault("nama", "S1")
    elif "name" in fields:
        kwargs.setdefault("name", "S1")

    return _mk_minimal(SubModel, **kwargs)
# ================= Pekerjaan CUSTOM minimal =================
@pytest.fixture
def pekerjaan_custom(db, project, sub_klas):
    from detail_project.models import Pekerjaan

    kwargs = dict(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type="custom",
        snapshot_kode="CUST-TST",
        snapshot_uraian="Pekerjaan Test",
        snapshot_satuan="OH",
        ordering_index=1,
    )
    return Pekerjaan.objects.create(**kwargs)


# ================= Detail TK.SMOKE & Volume =================
@pytest.fixture
def detail_tk_smoke(db, pekerjaan_custom):
    """
    Tambahkan 1 detail TK.SMOKE koef 0.125 ke pekerjaan custom.
    Model DetailAHSPProject di proyekmu mewajibkan FK 'harga_item' (NOT NULL),
    jadi kita buat objek harga_item minimal secara dinamis terlebih dahulu.
    """
    from detail_project.models import DetailAHSPProject

    # Siapkan kwargs dasar untuk DetailAHSPProject
    create_kwargs = dict(
        project=pekerjaan_custom.project,
        pekerjaan=pekerjaan_custom,
        kategori="TK",
        kode="TK.SMOKE",
        uraian="TK Smoke",
        satuan="OH",
        koefisien=Decimal("0.125000"),
    )

    # Jika kolom 'harga_item' ada dan NOT NULL, buatkan record harga minimal
    fields = {f.name: f for f in DetailAHSPProject._meta.fields}
    hi_field = fields.get("harga_item")
    if isinstance(hi_field, djm.ForeignKey) and not hi_field.null:
        HargaModel = hi_field.remote_field.model
        hfields = {f.name: f for f in HargaModel._meta.fields}
        harga_kwargs = {}

        # Project biasanya wajib
        if "project" in hfields and isinstance(hfields["project"], djm.ForeignKey):
            harga_kwargs["project"] = pekerjaan_custom.project

        # Isi kolom typical pada harga item
        if "kategori" in hfields:
            harga_kwargs["kategori"] = "TK"
        # model kamu pakai 'kode_item' (bukan 'kode')
        if "kode_item" in hfields:
            harga_kwargs["kode_item"] = "TK.SMOKE"
        elif "kode" in hfields:
            harga_kwargs["kode"] = "TK.SMOKE"
        if "uraian" in hfields:
            harga_kwargs["uraian"] = "TK Smoke"
        if "satuan" in hfields:
            harga_kwargs["satuan"] = "OH"

        # Cari field harga yang umum dipakai
        price_candidates = ("harga_satuan", "harga", "nilai", "amount")
        price_field = next((n for n in price_candidates if n in hfields), None)
        if price_field:
            harga_kwargs[price_field] = Decimal("1.00")

        # Boolean umum
        for bname in ("is_active", "aktif", "enabled"):
            if bname in hfields and not hfields[bname].null:
                harga_kwargs[bname] = True

        # Buat objek harga_item
        harga_item = HargaModel.objects.create(**harga_kwargs)
        create_kwargs["harga_item"] = harga_item

    return DetailAHSPProject.objects.create(**create_kwargs)

@pytest.fixture
def volume5(db, pekerjaan_custom):
    from detail_project.models import VolumePekerjaan
    VolumePekerjaan.objects.update_or_create(
        project=pekerjaan_custom.project,
        pekerjaan=pekerjaan_custom,
        defaults={"quantity": Decimal("5.000")},
    )
    return pekerjaan_custom


# ================= Autouse: Allowed hosts untuk test client =================
@pytest.fixture(autouse=True, scope="session")
def _allowed_hosts():
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")


@pytest.fixture
def api_urls(project):
    """
    Kumpulan URL untuk test, sudah terisi project.id default dari fixture `project`.
    Dipakai di test seperti: api_urls["upsert"], api_urls["rekap"], dll.
    """
    pid = project.id
    return {
        # List Pekerjaan
        "upsert":        reverse("detail_project:api_upsert_list_pekerjaan",   kwargs={"project_id": pid}),
        "tree":          reverse("detail_project:api_get_list_pekerjaan_tree", kwargs={"project_id": pid}),
        # dipakai oleh test untuk cek redirect anonymous (endpoint GET ber-login)
        "page":          reverse("detail_project:list_pekerjaan", args=[project.id]),
        "save":          reverse("detail_project:api_save_list_pekerjaan",     kwargs={"project_id": pid}),

        # Volume & Formula
        "volume_save":   reverse("detail_project:api_save_volume_pekerjaan",   kwargs={"project_id": pid}),
        "formula_state": reverse("detail_project:api_volume_formula_state",    kwargs={"project_id": pid}),

        # Pricing
        "pricing":       reverse("detail_project:api_project_pricing",         kwargs={"project_id": pid}),

        # Rekap
        "rekap":             reverse("detail_project:api_get_rekap_rab",           kwargs={"project_id": pid}),
        "rekap_kebutuhan":   reverse("detail_project:api_get_rekap_kebutuhan",     kwargs={"project_id": pid}),
        # Tambahan kalau diperlukan nanti:
        # "rincian_rab":    reverse("detail_project:api_get_rincian_rab",       kwargs={"project_id": pid}),
    }

@pytest.fixture
def build_payload():
    """
    Builder payload aman untuk API List Pekerjaan.
    Struktur: { "klasifikasi": [ { "nama": <klas_name>, "subs": [ { "nama": <sub_name>, "jobs": [...] } ] } ] }
    - Tidak menambah field konten (snapshot_*) jika tidak diberikan → agar test 'missing/400' tetap valid.
    - Hanya menambahkan ordering_index bertahap jika absen.
    - Bisa dioverride nama klas/sub di test (klas_name, sub_name).
    """
    def _build(*, jobs, klas_name="K1", sub_name="S1"):
        # defensive copy; jangan mutasi input test
        prepared = []
        next_idx = 1
        for j in jobs:
            j_copy = copy.deepcopy(j)
            # Isi ordering_index hanya jika tidak disediakan test
            if "ordering_index" not in j_copy:
                j_copy["ordering_index"] = next_idx
            next_idx += 1
            prepared.append(j_copy)

        payload = {
            "klasifikasi": [
                {
                    "nama": klas_name,
                    "subs": [
                        {
                            "nama": sub_name,
                            "jobs": prepared,
                        }
                    ],
                }
            ]
        }
        return payload
    return _build


def _mk_minimal_record(model, base_kw=None):
    """
    Buat 1 record untuk `model` dengan mengisi field non-null tanpa default.
    - Char/Text → 'X' (spesial: 'kode'='REF-001', 'uraian'='Referensi A', 'satuan'='u')
    - Decimal → 1.00
    - Integer/BigInteger → 1
    - Boolean → True
    - Date/DateTime → today/now (biarkan default jika ada)
    - ForeignKey (required) → tidak diisi (FAIL FAST) karena jarang ada di AHSPReferensi.
    """
    fields = {f.name: f for f in model._meta.fields}
    kw = {} if base_kw is None else dict(base_kw)

    for name, f in fields.items():
        if f.primary_key:
            continue
        # skip yang sudah diisi
        if name in kw:
            continue
        # skip nullable atau punya default
        has_default = (f.default is not djm.NOT_PROVIDED) or getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False)
        if getattr(f, "null", False) or has_default:
            continue

        # Isi berdasarkan tipe
        if isinstance(f, (djm.CharField, djm.TextField)):
            if name == "kode":
                kw[name] = "REF-001"
            elif name == "uraian":
                kw[name] = "Referensi A"
            elif name == "satuan":
                kw[name] = "u"
            else:
                kw[name] = "X"
        elif isinstance(f, djm.DecimalField):
            kw[name] = Decimal("1.00")
        elif isinstance(f, (djm.IntegerField, djm.BigIntegerField, djm.SmallIntegerField, djm.PositiveIntegerField, djm.PositiveSmallIntegerField)):
            kw[name] = 1
        elif isinstance(f, djm.BooleanField):
            kw[name] = True
        elif isinstance(f, (djm.DateField, djm.DateTimeField)):
            # biarkan default/auto_now(_add) jika ada; kalau wajib tapi tanpa default, isi now/today
            from django.utils import timezone
            kw[name] = timezone.now() if isinstance(f, djm.DateTimeField) else timezone.now().date()
        elif isinstance(f, djm.ForeignKey):
            # kalau ternyata ada FK wajib, kita biarkan error supaya kelihatan modelnya butuh apa
            pass

    return model.objects.create(**kw)

@pytest.fixture
def ahsp_ref(db):
    """Buat satu AHSP referensi valid sesuai model di proyek ini."""
    from referensi.models import AHSPReferensi
    return AHSPReferensi.objects.create(
        kode_ahsp="REF-001",
        nama_ahsp="Referensi A",
        satuan="OH",
    )