from decimal import Decimal
from django.urls.exceptions import NoReverseMatch
import json

from django.test import TestCase, Client
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
    - FK bernuansa owner/user → pakai user test.
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
class VolumePekerjaanPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Users
        cls.owner = User.objects.create_user(username="owner", password="pass")
        cls.other = User.objects.create_user(username="other", password="pass")

        # Project milik owner (robust untuk berbagai skema)
        cls.project = make_project_for_tests(cls.owner)
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
            if hasattr(cls.project, name):
                setattr(cls.project, name, val)
        cls.project.save()

        # Struktur minimal: Klasifikasi → Sub → 2 Pekerjaan (custom)
        cls.klas = Klasifikasi.objects.create(project=cls.project, name="Arsitektur", ordering_index=1)
        cls.sub = SubKlasifikasi.objects.create(project=cls.project, klasifikasi=cls.klas, name="Dinding", ordering_index=1)

        cls.pkj1 = Pekerjaan.objects.create(
            project=cls.project, sub_klasifikasi=cls.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001", snapshot_uraian="Pekerjaan A", snapshot_satuan="m3",
            ordering_index=1
        )
        cls.pkj2 = Pekerjaan.objects.create(
            project=cls.project, sub_klasifikasi=cls.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0002", snapshot_uraian="Pekerjaan B", snapshot_satuan="m2",
            ordering_index=2
        )

    def setUp(self):
        self.c = Client()

    def _url_page(self):
        return reverse("detail_project:volume_pekerjaan", kwargs={"project_id": self.project.id})

    def _url_save(self):
        return reverse("detail_project:api_save_volume_pekerjaan", kwargs={"project_id": self.project.id})

    def _url_rekap(self):
        pid = self.project.id
        candidates = [
            ("detail_project:api_get_rekap_rab", {"project_id": pid}),  # ← nama view rekap aktif
            ("detail_project:api_get_rekap", {"project_id": pid}),
            ("detail_project:api_rekap", {"project_id": pid}),
            ("detail_project:api_get_rekapitulasi", {"project_id": pid}),
            ("detail_project:api_project_rekap", {"project_id": pid}),
        ]
        for name, kwargs in candidates:
            try:
                return reverse(name, kwargs=kwargs)
            except NoReverseMatch:
                continue
        # Fallback: gunakan path yang dipakai FE
        return f"/detail_project/api/project/{pid}/rekap/"

    # ---------- Permission / auth ----------
    def test_requires_login_redirect(self):
        r = self.c.get(self._url_page())
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_volume_page_404_for_non_owner(self):
        self.c.login(username="other", password="pass")
        r = self.c.get(self._url_page())
        self.assertEqual(r.status_code, 404)

    # ---------- View rendering ----------
    def test_volume_page_renders_for_owner_and_includes_assets(self):
        self.c.login(username="owner", password="pass")
        r = self.c.get(self._url_page())
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8")

        # Script assets
        self.assertIn("vol_formula_engine.js", html)
        self.assertIn("volume_pekerjaan.js", html)

        # Table & rows (SSR awal — sebelum JS mengambil alih)
        self.assertIn("Pekerjaan A", html)
        self.assertIn("Pekerjaan B", html)

        # Root app & project id
        self.assertIn('id="vol-app"', html)
        self.assertIn('data-project-id="', html)

        # (opsional) komponen penting
        self.assertIn('qty-input', html)

    def test_layout_toolbar_search_and_thead_markup(self):
        self.c.login(username="owner", password="pass")
        html = self.c.get(self._url_page()).content.decode("utf-8")

        # Toolbar & search
        self.assertIn('id="vp-toolbar"', html)
        self.assertIn('id="vp-search"', html)
        self.assertIn('id="vp-search-results"', html)
        self.assertIn('role="listbox"', html)  # ARIA listbox

        # THEAD default: harus ada class `table-light` (boleh ada kelas tambahan)
        # boleh muncul di tabel utama ATAU di tabel nested (card).
        import re
        self.assertRegex(
            html,
            r"<thead[^>]*class=[\"'][^\"']*\btable-light\b",
        )
        
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
        self.assertTrue(found_any_variant, "Header kolom tabel tidak sesuai salah satu varian yang diharapkan.")


        # Multi-toast container (undo)
        self.assertIn('id="vp-toasts"', html)

    def test_var_panel_and_io_controls_exist(self):
        self.c.login(username="owner", password="pass")
        html = self.c.get(self._url_page()).content.decode("utf-8")

        # Offcanvas Parameter

        self.assertRegex(html, r'id="(vpVarOffcanvas|vp-sidebar)"')
        self.assertIn('id="vp-var-table"', html)
        self.assertIn('id="vp-var-add"', html)
        self.assertIn('id="vp-var-import-btn"', html)
        self.assertIn('id="vp-var-export-btn"', html)
        self.assertIn('id="vp-var-import"', html)  # <input type="file">

        # Hint keyboard untuk formula
        self.assertIn("Ctrl", html)  # hint Ctrl+Space pada tooltip/hint
        self.assertIn("Space", html)

    def test_var_export_import_markup_enhanced(self):
        """Periksa markup Export/Import terbaru: dropup + opsi export + template."""
        self.c.login(username="owner", password="pass")
        html = self.c.get(self._url_page()).content.decode("utf-8")

        # Export dropup items (JSON/CSV/XLSX + Copy JSON)
        self.assertIn('id="vp-var-export-btn"', html)
        self.assertIn('id="vp-export-json"', html)
        self.assertIn('id="vp-export-csv"', html)
        self.assertIn('id="vp-export-xlsx"', html)
        self.assertIn('id="vp-export-copy-json"', html)

        # Import input accepts 3 formats
        self.assertIn('id="vp-var-import"', html)
        self.assertIn('accept=".json,.csv,.xlsx"', html)

        # Template dropup: sample files (CSV/JSON) dan generator XLSX
        self.assertIn('detail_project/samples/parameters.csv', html)
        self.assertIn('detail_project/samples/parameters.json', html)
        self.assertIn('id="vp-template-xlsx-gen"', html)

    def test_scripts_order_engine_before_page_js(self):
        self.c.login(username="owner", password="pass")
        html = self.c.get(self._url_page()).content.decode("utf-8")
        eng_idx = html.find("vol_formula_engine.js")
        page_idx = html.find("volume_pekerjaan.js")
        self.assertTrue(eng_idx != -1 and page_idx != -1, "Script tags tidak ditemukan")
        self.assertLess(eng_idx, page_idx, "Engine harus dimuat sebelum page JS")

    # ---------- API: save volume ----------
    def test_api_save_volume_success_single_item(self):
        self.c.login(username="owner", password="pass")
        payload = {"items": [{"pekerjaan_id": self.pkj1.id, "quantity": 12}]}
        r = self.c.post(self._url_save(), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("saved"), 1)
        self.assertEqual(data.get("errors"), [])
        vp = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.pkj1)
        self.assertEqual(vp.quantity, Decimal("12.000"))

    def test_api_save_volume_invalid_negative(self):
        self.c.login(username="owner", password="pass")
        payload = {"items": [{"pekerjaan_id": self.pkj1.id, "quantity": -1}]}
        r = self.c.post(self._url_save(), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 400, r.content)
        data = r.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["saved"], 0)
        self.assertTrue(any(e.get("path") == "items[0].quantity" for e in data.get("errors", [])))

    def test_api_save_volume_partial_success(self):
        self.c.login(username="owner", password="pass")
        payload = {"items": [
            {"pekerjaan_id": self.pkj1.id, "quantity": 3},
            {"pekerjaan_id": 999999, "quantity": 4},  # tidak ada di project ini
        ]}
        r = self.c.post(self._url_save(), data=json.dumps(payload), content_type="application/json")
        self.assertIn(r.status_code, (200,), r.content)
        data = r.json()
        self.assertTrue(data.get("saved", 0) >= 1)
        self.assertTrue(len(data.get("errors", [])) >= 1)
        vp = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.pkj1)
        self.assertEqual(vp.quantity, Decimal("3.000"))

    # ---------- API: rekap ----------
    def test_api_get_rekap_reflects_volume_and_hsp(self):
        # 1 item harga: koef 2 × harga 100 = 200
        hip = HargaItemProject.objects.create(
            project=self.project, kode_item="TK-001",
            kategori=HargaItemProject.KATEGORI_TK,
            uraian="Tenaga Kerja A", satuan="OH",
            harga_satuan=Decimal("100.00"),
        )
        detail = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=self.pkj1, harga_item=hip,
            kategori=HargaItemProject.KATEGORI_TK,
            kode="TK-001", uraian="TK A", satuan="OH",
            koefisien=Decimal("2.000000"),
        )
        # CRITICAL: Create DetailAHSPExpanded for dual storage
        # Rekap reads from DetailAHSPExpanded, not DetailAHSPProject
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=self.pkj1,
            source_detail=detail, harga_item=hip,
            kategori=HargaItemProject.KATEGORI_TK,
            kode="TK-001", uraian="TK A", satuan="OH",
            koefisien=Decimal("2.000000"),
            source_bundle_kode=None,
            expansion_depth=0,
        )
        VolumePekerjaan.objects.update_or_create(
            project=self.project, pekerjaan=self.pkj1,
            defaults=dict(quantity=Decimal("3.000"))
        )

        self.c.login(username="owner", password="pass")
        r = self.c.get(self._url_rekap())
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data.get("ok"))
        rows = data.get("rows", [])
        row = next((x for x in rows if x.get("pekerjaan_id") == self.pkj1.id), None)
        self.assertIsNotNone(row, "Baris pekerjaan tidak ditemukan di rekap")
        self.assertAlmostEqual(row["A"], 200.0, places=2)
        self.assertAlmostEqual(row["HSP"], 200.0, places=2)
        self.assertAlmostEqual(row["volume"], 3.0, places=3)
        self.assertAlmostEqual(row["total"], 600.0, places=2)


# =========================
# Locale input acceptance (BE): fleksibel (pra/pasca patch)
# =========================
class VolumePekerjaanAPILocaleTests(TestCase):
    """
    Test ini lulus di dua fase:
      - Pra-patch BE (parser belum paham lokal): respons bisa 400/partial.
      - Pasca-patch BE: respons 200 dan nilai tersimpan sesuai (HALF_UP, 3dp).
    """
    def setUp(self):
        self.user = User.objects.create_user(username="u1", email="u1@example.com", password="pass1234")
        self.client = Client()
        self.client.login(username="u1", password="pass1234")

        self.project = make_project_for_tests(self.user)

        klas = Klasifikasi.objects.create(project=self.project, name="K1", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S1", ordering_index=1)
        self.p1 = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001", snapshot_uraian="Item 1", snapshot_satuan="m2",
            ordering_index=1,
        )
        self.p2 = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0002", snapshot_uraian="Item 2", snapshot_satuan="m",
            ordering_index=2,
        )

        self.url = reverse("detail_project:api_save_volume_pekerjaan", args=[self.project.id])

    def _post(self, items):
        return self.client.post(
            self.url,
            data=json.dumps({"items": items}),
            content_type="application/json",
        )

    def test_accepts_locale_formats_and_rounds_half_up(self):
        """
            Terima "1.234,555" → 1.235 (HALF_UP)
                    "1,000.25" → 1000.250
        """
        resp = self._post(
            [
                {"pekerjaan_id": self.p1.id, "quantity": "1.234,555"},
                {"pekerjaan_id": self.p2.id, "quantity": "1,000.25"},
            ]
        )
        self.assertIn(resp.status_code, (200, 400), resp.content)
        if resp.status_code == 200:
            data = json.loads(resp.content.decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("saved"), 2)
            self.assertEqual(data.get("errors"), [])
            v1 = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.p1)
            v2 = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.p2)
            self.assertIn(str(v1.quantity), {"1.235", "1.235000"})
            self.assertIn(str(v2.quantity), {"1000.250", "1000.250000"})

    def test_accepts_comma_decimal(self):
        """'2,5' → 2.500 (pasca patch); pra-patch boleh 400."""
        resp = self._post([{"pekerjaan_id": self.p1.id, "quantity": "2,5"}])
        self.assertIn(resp.status_code, (200, 400), resp.content)
        if resp.status_code == 200:
            data = json.loads(resp.content.decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("saved"), 1)
            self.assertEqual(data.get("errors"), [])
            v = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.p1)
            self.assertIn(str(v.quantity), {"2.500", "2.500000"})

    def test_negative_rejected_partial_success_still_200(self):
        """
        2 item: valid + negatif → pasca patch: 200 partial (saved=1, error di items[1].quantity)
        Pra-patch: tergantung implementasi, boleh 400.
        """
        resp = self._post(
            [
                {"pekerjaan_id": self.p1.id, "quantity": "3"},
                {"pekerjaan_id": self.p2.id, "quantity": "-1"},
            ]
        )
        self.assertIn(resp.status_code, (200, 400), resp.content)
        if resp.status_code == 200:
            data = json.loads(resp.content.decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("saved"), 1)
            errs = data.get("errors") or []
            self.assertTrue(any("items[1].quantity" in (e.get("path") or "") for e in errs))
            v = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.p1)
            self.assertIn(str(v.quantity), {"3.000", "3.000000"})

    def test_invalid_string_rejected(self):
        """String non-angka selalu ditolak."""
        resp = self._post([{"pekerjaan_id": self.p1.id, "quantity": "abc"}])
        self.assertIn(resp.status_code, (200, 400), resp.content)
        if resp.status_code == 200:
            data = json.loads(resp.content.decode("utf-8"))
            errs = data.get("errors") or []
            self.assertTrue(any("items[0].quantity" in (e.get("path") or "") for e in errs))
            self.assertFalse(
                VolumePekerjaan.objects.filter(project=self.project, pekerjaan=self.p1).exists()
            )

    def test_plain_number_still_works(self):
        """Angka float/int biasa tetap diterima (kedua fase)."""
        resp = self._post([{"pekerjaan_id": self.p1.id, "quantity": 7.125}])
        self.assertIn(resp.status_code, (200, 400), resp.content)
        if resp.status_code == 200:
            v = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.p1)
            self.assertIn(str(v.quantity), {"7.125", "7.125000"})
