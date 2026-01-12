from decimal import Decimal
from django.urls.exceptions import NoReverseMatch
import json
import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    HargaItemProject, DetailAHSPProject, DetailAHSPExpanded
)

User = get_user_model()


# ---------- Helper: robust project factory (isi semua field wajib) ----------
def make_project_for_tests(owner):
    """
    Buat Project minimal tanpa menebak skema spesifik:
    - Isi semua field wajib (null=False, tanpa default).
    - FK bernuansa owner/user pakai user test.
    """
    from django.db import models as djm

    kwargs = {}
    fields = Project._meta.fields

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
            alias = {"nama": "Proyek Uji", "name": "Proyek Uji", "title": "Proyek Uji", "project_name": "Proyek Uji"}
            kwargs[f.name] = alias.get(f.name, f"ProyekUji-{f.name}")

        elif isinstance(f, djm.TextField):
            kwargs[f.name] = f"Dummy {f.name}"

        elif isinstance(f, djm.IntegerField):
            kwargs[f.name] = 2025

        elif isinstance(f, djm.DecimalField):
            q = Decimal("0").quantize(Decimal(f"1e-{f.decimal_places}"))
            kwargs[f.name] = q

        elif isinstance(f, djm.DateTimeField):
            from django.utils import timezone
            kwargs[f.name] = timezone.now()

        elif isinstance(f, djm.DateField):
            from django.utils import timezone
            kwargs[f.name] = timezone.now().date()

        elif isinstance(f, djm.ForeignKey):
            rel = f.related_model
            name_lc = f.name.lower()
            if rel == get_user_model() or "owner" in name_lc or "user" in name_lc:
                kwargs[f.name] = owner
            else:
                existing = rel._default_manager.first()
                if existing:
                    kwargs[f.name] = existing
                else:
                    # fallback: buat instansi rel sederhana
                    create_kwargs = {}
                    for rf in rel._meta.fields:
                        if rf.auto_created or rf.primary_key:
                            continue
                        if rf.has_default() or getattr(rf, "null", False):
                            continue
                        if isinstance(rf, djm.CharField):
                            create_kwargs[rf.name] = f"{rel.__name__}-{rf.name}"
                            break
                    if create_kwargs:
                        kwargs[f.name] = rel._default_manager.create(**create_kwargs)

        else:
            try:
                kwargs[f.name] = f.get_default()
            except Exception:
                pass

    if "is_active" in [f.name for f in fields]:
        kwargs["is_active"] = True

    return Project.objects.create(**kwargs)


# =========================
# UI & API tests
# =========================
@pytest.fixture
def volume_page_owner(db):
    return User.objects.create_user(username="owner", password="pass")


@pytest.fixture
def volume_page_other(db):
    return User.objects.create_user(username="other", password="pass")


@pytest.fixture
def volume_page_project(volume_page_owner):
    # Project milik owner (robust untuk berbagai skema)
    project = make_project_for_tests(volume_page_owner)
    # optional nice-to-have fields
    for name, val in [
        ("nama", "Proyek Uji"),
        ("tahun_project", 2025),
        ("sumber_dana", "APBD"),
        ("lokasi_project", "Kota A"),
        ("nama_client", "Client A"),
        ("instansi_client", "Dinas PUPR"),
        ("total_anggaran", Decimal("1000000.00")),
        ("anggaran_owner", Decimal("1000000.00")),
        ("is_active", True),
    ]:
        if hasattr(project, name):
            setattr(project, name, val)
    project.save()

    # Struktur minimal: Klasifikasi -> Sub -> 2 Pekerjaan (custom)
    klas = Klasifikasi.objects.create(project=project, name="Arsitektur", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="Dinding", ordering_index=1)

    pkj1 = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0001", snapshot_uraian="Pekerjaan A", snapshot_satuan="m3",
        ordering_index=1
    )
    pkj2 = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0002", snapshot_uraian="Pekerjaan B", snapshot_satuan="m2",
        ordering_index=2
    )

    return {
        'project': project,
        'klas': klas,
        'sub': sub,
        'pkj1': pkj1,
        'pkj2': pkj2,
    }


def _url_page(project_id):
    return reverse("detail_project:volume_pekerjaan", kwargs={"project_id": project_id})


def _url_save(project_id):
    return reverse("detail_project:api_save_volume_pekerjaan", kwargs={"project_id": project_id})


def _url_rekap(project_id):
    candidates = [
        ("detail_project:api_get_rekap_rab", {"project_id": project_id}),
        ("detail_project:api_get_rekap", {"project_id": project_id}),
        ("detail_project:api_rekap", {"project_id": project_id}),
        ("detail_project:api_get_rekapitulasi", {"project_id": project_id}),
        ("detail_project:api_project_rekap", {"project_id": project_id}),
    ]
    for name, kwargs in candidates:
        try:
            return reverse(name, kwargs=kwargs)
        except NoReverseMatch:
            continue
    # Fallback: gunakan path yang dipakai FE
    return f"/detail_project/api/project/{project_id}/rekap/"


def _url_list(project_id):
    return reverse("detail_project:api_list_volume_pekerjaan", kwargs={"project_id": project_id})


# ---------- Permission / auth ----------
def test_requires_login_redirect(client, volume_page_project):
    project = volume_page_project['project']
    r = client.get(_url_page(project.id))
    assert r.status_code == 302
    assert "login" in r["Location"]


def test_volume_page_404_for_non_owner(client, volume_page_other, volume_page_project):
    project = volume_page_project['project']
    client.force_login(volume_page_other)
    r = client.get(_url_page(project.id))
    assert r.status_code == 404


# ---------- View rendering ----------
def test_volume_page_renders_for_owner_and_includes_assets(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    client.force_login(volume_page_owner)
    r = client.get(_url_page(project.id))
    assert r.status_code == 200
    html = r.content.decode("utf-8")

    # Script assets
    assert "vol_formula_engine.js" in html
    assert "volume_pekerjaan.js" in html

    # Table & rows (SSR awal — sebelum JS mengambil alih)
    assert "Pekerjaan A" in html
    assert "Pekerjaan B" in html

    # Root app & project id
    assert 'id="vol-app"' in html
    assert 'data-project-id="' in html

    # (opsional) komponen penting
    assert 'qty-input' in html


def test_layout_toolbar_search_and_thead_markup(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    client.force_login(volume_page_owner)
    html = client.get(_url_page(project.id)).content.decode("utf-8")

    # Toolbar & search
    assert 'id="vp-toolbar"' in html
    assert 'id="vp-search"' in html
    assert 'id="vp-search-results"' in html
    assert 'role="listbox"' in html  # ARIA listbox

    # THEAD default: harus ada class `table-light` (boleh ada kelas tambahan)
    # boleh muncul di tabel utama ATAU di tabel nested (card).
    import re
    assert re.search(r"<thead[^>]*class=[\"'][^\"']*\btable-light\b", html) is not None

    # Kolom: terima dua varian header agar kompatibel dengan layout baru
    # Varian A (tabel utama):    #, Kode, Uraian, Satuan, Quantity
    # Varian B (nested card):    No, Uraian, Satuan, Quantity
    variants = [
        ["#", "Kode", "Uraian", "Satuan", "Quantity"],
        ["No", "Uraian", "Satuan", "Quantity"],
    ]
    found_any_variant = any(
        all((f">{label}<") in html for label in cols)
        for cols in variants
    )
    assert found_any_variant is True, "Header kolom tabel tidak sesuai salah satu varian yang diharapkan."

    # Multi-toast container (undo)
    assert 'id="vp-toasts"' in html


def test_var_panel_and_io_controls_exist(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    client.force_login(volume_page_owner)
    html = client.get(_url_page(project.id)).content.decode("utf-8")

    # Offcanvas Parameter
    import re
    assert re.search(r'id="(vpVarOffcanvas|vp-sidebar)"', html) is not None
    assert 'id="vp-var-table"' in html
    assert 'id="vp-var-add"' in html
    assert 'id="vp-var-import-btn"' in html
    assert 'id="vp-var-export-btn"' in html
    assert 'id="vp-var-import"' in html  # <input type="file">

    # Hint keyboard untuk formula
    assert "Ctrl" in html  # hint Ctrl+Space pada tooltip/hint
    assert "Space" in html


def test_var_export_import_markup_enhanced(client, volume_page_owner, volume_page_project):
    """Periksa markup Export/Import terbaru: dropup + opsi export + template."""
    project = volume_page_project['project']
    client.force_login(volume_page_owner)
    html = client.get(_url_page(project.id)).content.decode("utf-8")

    # Export dropup items (JSON/CSV/XLSX + Copy JSON)
    assert 'id="vp-var-export-btn"' in html
    assert 'id="vp-export-json"' in html
    assert 'id="vp-export-csv"' in html
    assert 'id="vp-export-xlsx"' in html
    assert 'id="vp-export-copy-json"' in html

    # Import input accepts 3 formats
    assert 'id="vp-var-import"' in html
    assert 'accept=".json,.csv,.xlsx"' in html

    # Template dropup: sample files (CSV/JSON) dan generator XLSX
    assert 'detail_project/samples/parameters.csv' in html
    assert 'detail_project/samples/parameters.json' in html
    assert 'id="vp-template-xlsx-gen"' in html


def test_scripts_order_engine_before_page_js(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    client.force_login(volume_page_owner)
    html = client.get(_url_page(project.id)).content.decode("utf-8")
    eng_idx = html.find("vol_formula_engine.js")
    page_idx = html.find("volume_pekerjaan.js")
    assert eng_idx != -1 and page_idx != -1, "Script tags tidak ditemukan"
    assert eng_idx < page_idx, "Engine harus dimuat sebelum page JS"


# ---------- API: save volume ----------
def test_api_save_volume_success_single_item(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    pkj1 = volume_page_project['pkj1']
    client.force_login(volume_page_owner)
    payload = {"items": [{"pekerjaan_id": pkj1.id, "quantity": 12}]}
    r = client.post(_url_save(project.id), data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200, r.content
    data = r.json()
    assert data.get("ok") is True
    assert data.get("saved") == 1
    assert data.get("errors") == []
    vp = VolumePekerjaan.objects.get(project=project, pekerjaan=pkj1)
    assert vp.quantity == Decimal("12.000")


def test_api_save_volume_invalid_negative(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    pkj1 = volume_page_project['pkj1']
    client.force_login(volume_page_owner)
    payload = {"items": [{"pekerjaan_id": pkj1.id, "quantity": -1}]}
    r = client.post(_url_save(project.id), data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 400, r.content
    data = r.json()
    assert data["ok"] is False
    assert data["saved"] == 0
    assert any(e.get("path") == "items[0].quantity" for e in data.get("errors", [])) is True


def test_api_save_volume_partial_success(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    pkj1 = volume_page_project['pkj1']
    client.force_login(volume_page_owner)
    payload = {"items": [
        {"pekerjaan_id": pkj1.id, "quantity": 3},
        {"pekerjaan_id": 999999, "quantity": 4},  # tidak ada di project ini
    ]}
    r = client.post(_url_save(project.id), data=json.dumps(payload), content_type="application/json")
    assert r.status_code in (200,), r.content
    data = r.json()
    assert data.get("saved", 0) >= 1
    assert len(data.get("errors", [])) >= 1
    vp = VolumePekerjaan.objects.get(project=project, pekerjaan=pkj1)
    assert vp.quantity == Decimal("3.000")


# ---------- API: list volume ----------
def test_api_list_volume_requires_login(client, volume_page_project):
    project = volume_page_project['project']
    r = client.get(_url_list(project.id))
    assert r.status_code == 302
    assert "login" in r["Location"]


def test_api_list_volume_defaults_to_zero(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    pkj1 = volume_page_project['pkj1']
    pkj2 = volume_page_project['pkj2']
    client.force_login(volume_page_owner)
    response = client.get(_url_list(project.id))
    assert response.status_code == 200, response.content
    payload = response.json()
    assert payload.get("ok") is True
    items = payload.get("items", [])
    assert len(items) >= 2
    qmap = {row["pekerjaan_id"]: row["quantity"] for row in items}
    assert qmap[pkj1.id] == "0.000"
    assert qmap[pkj2.id] == "0.000"
    dp = payload.get("decimal_places")
    expected_dp = VolumePekerjaan._meta.get_field("quantity").decimal_places
    assert dp == expected_dp


def test_api_list_volume_reflects_saved_entries(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    pkj1 = volume_page_project['pkj1']
    pkj2 = volume_page_project['pkj2']
    VolumePekerjaan.objects.update_or_create(
        project=project,
        pekerjaan=pkj1,
        defaults={"quantity": Decimal("12.345")},
    )
    VolumePekerjaan.objects.update_or_create(
        project=project,
        pekerjaan=pkj2,
        defaults={"quantity": Decimal("0.100")},
    )
    client.force_login(volume_page_owner)
    response = client.get(_url_list(project.id))
    assert response.status_code == 200, response.content
    data = response.json()
    qmap = {row["pekerjaan_id"]: row["quantity"] for row in data.get("items", [])}
    assert qmap[pkj1.id] == "12.345"
    assert qmap[pkj2.id] == "0.100"


# ---------- API: rekap ----------
def test_api_get_rekap_reflects_volume_and_hsp(client, volume_page_owner, volume_page_project):
    project = volume_page_project['project']
    pkj1 = volume_page_project['pkj1']
    # 1 item harga: koef 2 × harga 100 = 200
    hip = HargaItemProject.objects.create(
        project=project, kode_item="TK-001",
        kategori=HargaItemProject.KATEGORI_TK,
        uraian="Tenaga Kerja A", satuan="OH",
        harga_satuan=Decimal("100.00"),
    )
    detail = DetailAHSPProject.objects.create(
        project=project, pekerjaan=pkj1, harga_item=hip,
        kategori=HargaItemProject.KATEGORI_TK,
        kode="TK-001", uraian="TK A", satuan="OH",
        koefisien=Decimal("2.000000"),
    )
    # CRITICAL: Create DetailAHSPExpanded for dual storage
    # Rekap reads from DetailAHSPExpanded, not DetailAHSPProject
    DetailAHSPExpanded.objects.create(
        project=project, pekerjaan=pkj1,
        source_detail=detail, harga_item=hip,
        kategori=HargaItemProject.KATEGORI_TK,
        kode="TK-001", uraian="TK A", satuan="OH",
        koefisien=Decimal("2.000000"),
        source_bundle_kode=None,
        expansion_depth=0,
    )
    VolumePekerjaan.objects.update_or_create(
        project=project, pekerjaan=pkj1,
        defaults=dict(quantity=Decimal("3.000"))
    )

    client.force_login(volume_page_owner)
    r = client.get(_url_rekap(project.id))
    assert r.status_code == 200, r.content
    data = r.json()
    assert data.get("ok") is True
    rows = data.get("rows", [])
    row = next((x for x in rows if x.get("pekerjaan_id") == pkj1.id), None)
    assert row is not None, "Baris pekerjaan tidak ditemukan di rekap"
    assert abs(row["A"] - 200.0) < 0.01
    assert abs(row["HSP"] - 200.0) < 0.01
    assert abs(row["volume"] - 3.0) < 0.001
    assert abs(row["total"] - 600.0) < 0.01


# =========================
# Locale input acceptance (BE): fleksibel (pra/pasca patch)
# =========================
@pytest.fixture
def locale_user(db):
    return User.objects.create_user(username="u1", email="u1@example.com", password="pass1234")


@pytest.fixture
def locale_project(locale_user):
    project = make_project_for_tests(locale_user)

    klas = Klasifikasi.objects.create(project=project, name="K1", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="S1", ordering_index=1)
    p1 = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0001", snapshot_uraian="Item 1", snapshot_satuan="m2",
        ordering_index=1,
    )
    p2 = Pekerjaan.objects.create(
        project=project, sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-0002", snapshot_uraian="Item 2", snapshot_satuan="m",
        ordering_index=2,
    )

    return {
        'project': project,
        'p1': p1,
        'p2': p2,
    }


def _post_locale(client, project_id, items):
    url = reverse("detail_project:api_save_volume_pekerjaan", args=[project_id])
    return client.post(
        url,
        data=json.dumps({"items": items}),
        content_type="application/json",
    )


def test_accepts_locale_formats_and_rounds_half_up(client, locale_user, locale_project):
    """
        Terima "1.234,555" -> 1.235 (HALF_UP)
                "1,000.25" -> 1000.250
    """
    project = locale_project['project']
    p1 = locale_project['p1']
    p2 = locale_project['p2']
    client.force_login(locale_user)
    resp = _post_locale(
        client,
        project.id,
        [
            {"pekerjaan_id": p1.id, "quantity": "1.234,555"},
            {"pekerjaan_id": p2.id, "quantity": "1,000.25"},
        ]
    )
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        data = json.loads(resp.content.decode("utf-8"))
        assert data.get("ok") is True
        assert data.get("saved") == 2
        assert data.get("errors") == []
        v1 = VolumePekerjaan.objects.get(project=project, pekerjaan=p1)
        v2 = VolumePekerjaan.objects.get(project=project, pekerjaan=p2)
        assert str(v1.quantity) in {"1.235", "1.235000"}
        assert str(v2.quantity) in {"1000.250", "1000.250000"}


def test_accepts_comma_decimal(client, locale_user, locale_project):
    """'2,5' -> 2.500 (pasca patch); pra-patch boleh 400."""
    project = locale_project['project']
    p1 = locale_project['p1']
    client.force_login(locale_user)
    resp = _post_locale(client, project.id, [{"pekerjaan_id": p1.id, "quantity": "2,5"}])
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        data = json.loads(resp.content.decode("utf-8"))
        assert data.get("ok") is True
        assert data.get("saved") == 1
        assert data.get("errors") == []
        v = VolumePekerjaan.objects.get(project=project, pekerjaan=p1)
        assert str(v.quantity) in {"2.500", "2.500000"}


def test_negative_rejected_partial_success_still_200(client, locale_user, locale_project):
    """
    2 item: valid + negatif -> pasca patch: 200 partial (saved=1, error di items[1].quantity)
    Pra-patch: tergantung implementasi, boleh 400.
    """
    project = locale_project['project']
    p1 = locale_project['p1']
    p2 = locale_project['p2']
    client.force_login(locale_user)
    resp = _post_locale(
        client,
        project.id,
        [
            {"pekerjaan_id": p1.id, "quantity": "3"},
            {"pekerjaan_id": p2.id, "quantity": "-1"},
        ]
    )
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        data = json.loads(resp.content.decode("utf-8"))
        assert data.get("ok") is True
        assert data.get("saved") == 1
        errs = data.get("errors") or []
        assert any("items[1].quantity" in (e.get("path") or "") for e in errs) is True
        v = VolumePekerjaan.objects.get(project=project, pekerjaan=p1)
        assert str(v.quantity) in {"3.000", "3.000000"}


def test_invalid_string_rejected(client, locale_user, locale_project):
    """String non-angka selalu ditolak."""
    project = locale_project['project']
    p1 = locale_project['p1']
    client.force_login(locale_user)
    resp = _post_locale(client, project.id, [{"pekerjaan_id": p1.id, "quantity": "abc"}])
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        data = json.loads(resp.content.decode("utf-8"))
        errs = data.get("errors") or []
        assert any("items[0].quantity" in (e.get("path") or "") for e in errs) is True
        assert VolumePekerjaan.objects.filter(project=project, pekerjaan=p1).exists() is False


def test_plain_number_still_works(client, locale_user, locale_project):
    """Angka float/int biasa tetap diterima (kedua fase)."""
    project = locale_project['project']
    p1 = locale_project['p1']
    client.force_login(locale_user)
    resp = _post_locale(client, project.id, [{"pekerjaan_id": p1.id, "quantity": 7.125}])
    assert resp.status_code in (200, 400), resp.content
    if resp.status_code == 200:
        v = VolumePekerjaan.objects.get(project=project, pekerjaan=p1)
        assert str(v.quantity) in {"7.125", "7.125000"}
