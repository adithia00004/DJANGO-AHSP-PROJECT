# detail_project/tests/test_api_formula_state.py
import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.apps import apps
from django.utils import timezone

from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan, VolumeFormulaState
)


class APITier1Tests(TestCase):
    """
    Tier 1: Backend API tests
    - Formula state GET/POST
    - Volume save partial success + normalisasi angka
    - Tree API sanity (untuk memperoleh pekerjaan_id)
    """

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(username="u1", password="p@ss")
        self.client.login(username="u1", password="p@ss")

        # Buat Project minimal yang kompatibel dengan model 'dashboard.Project' milikmu.
        self.Project = apps.get_model("dashboard", "Project")
        self.project = self._create_project_minimal(owner=self.user)
        if self.project is None:
            self.skipTest(
                "Tidak bisa membuat dashboard.Project secara minimal. "
                "Tambahkan field default pada Project atau sesuaikan helper _create_project_minimal()."
            )

        # Buat hirarki dasar + 2 pekerjaan (custom) untuk project utama
        self.klas = Klasifikasi.objects.create(project=self.project, name="K1", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=self.klas, name="S1", ordering_index=1)
        self.p1 = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001", snapshot_uraian="Pekerjaan 1", snapshot_satuan="m2",
            ordering_index=1
        )
        self.p2 = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0002", snapshot_uraian="Pekerjaan 2", snapshot_satuan="m",
            ordering_index=2
        )

        # Project lain + 1 pekerjaan untuk uji cross-project reject
        self.other_project = self._create_project_minimal(owner=self.user)
        if self.other_project:
            klas2 = Klasifikasi.objects.create(project=self.other_project, name="KX", ordering_index=1)
            sub2 = SubKlasifikasi.objects.create(project=self.other_project, klasifikasi=klas2, name="SX", ordering_index=1)
            self.px = Pekerjaan.objects.create(
                project=self.other_project, sub_klasifikasi=sub2,
                source_type=Pekerjaan.SOURCE_CUSTOM,
                snapshot_kode="CUST-X", snapshot_uraian="Pekerjaan X", snapshot_satuan="m",
                ordering_index=1
            )
        else:
            self.px = None

    # ---------------- helpers ----------------
    def _create_project_minimal(self, owner):
        """Coba membuat dashboard.Project dengan field minimal tanpa asumsi keras."""
        Project = self.Project
        # Deteksi field yang umum
        field_names = {f.name for f in Project._meta.get_fields() if getattr(f, "concrete", False) and not f.auto_created}
        data = {}
        if "owner" in field_names:
            data["owner"] = owner
        if "is_active" in field_names:
            data["is_active"] = True
        # Nama proyek (opsional, jika fieldnya ada & required)
        # coba 'nama' lalu 'name' (dua pola umum)
        if "nama" in field_names:
            data.setdefault("nama", "Test Project")
        if "name" in field_names:
            data.setdefault("name", "Test Project")

        # Tambah fallback untuk field non-nullable tanpa default (Char/Text/Bool/Int/Decimal/DateTime/Date)
        # NOTE: kita tidak akan membuat FK lain selain owner; jika required FK lain ada, kita gagal & skip test.
        for f in Project._meta.get_fields():
            if not getattr(f, "concrete", False) or f.auto_created:
                continue
            if getattr(f, "many_to_many", False):
                continue
            # FK?
            if getattr(f, "remote_field", None) is not None:
                # skip FK selain owner (sulit dipalsukan secara generik)
                if f.name == "owner":
                    continue
                # jika FK required (null=False) tanpa default → tidak bisa dibuat generik
                if not getattr(f, "null", True):
                    return None
                continue

            # Non-relational
            if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
                continue
            if hasattr(f, "has_default") and f.has_default():
                continue
            if getattr(f, "null", False):
                continue  # nullable → tidak wajib diisi
            # Wajib? isi default generik jika belum terisi
            if f.name in data:
                continue
            from django.db import models as m
            if isinstance(f, (m.CharField, m.TextField)):
                data[f.name] = "T"
            elif isinstance(f, m.BooleanField):
                data[f.name] = True
            elif isinstance(f, m.IntegerField):
                data[f.name] = 1
            elif isinstance(f, m.DecimalField):
                data[f.name] = Decimal("0")
            elif isinstance(f, m.DateTimeField):
                data[f.name] = timezone.now()
            elif isinstance(f, m.DateField):
                data[f.name] = timezone.now().date()
            else:
                # tipe tidak dikenali & required → gagal
                return None

        try:
            return Project.objects.create(**data)
        except Exception:
            return None

    def url_formula(self, pid):
        return reverse("detail_project:api_volume_formula_state", args=[pid])

    def url_tree(self, pid):
        return reverse("detail_project:api_get_list_pekerjaan_tree", args=[pid])

    def url_volume_save(self, pid):
        return reverse("detail_project:api_save_volume_pekerjaan", args=[pid])

    def _json(self, resp):
        return json.loads(resp.content.decode("utf-8"))

    # ---------------- tests: formula state ----------------
    def test_formula_get_empty(self):
        # GET harus ok:true & items: []
        r = self.client.get(self.url_formula(self.project.id))
        self.assertEqual(r.status_code, 200)
        j = self._json(r)
        self.assertTrue(j["ok"])
        self.assertEqual(j["items"], [])

    def test_formula_post_upsert_and_get(self):
        # POST satu item → created=1
        payload = {"items": [{"pekerjaan_id": self.p1.id, "raw": "=L*W*H", "is_fx": True}]}
        r = self.client.post(self.url_formula(self.project.id),
                             data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        j = self._json(r)
        self.assertTrue(j["ok"])
        self.assertEqual(j["created"], 1)
        self.assertEqual(j["updated"], 0)
        self.assertEqual(j["errors"], [])

        # GET ulang → items berisi entri tadi
        r2 = self.client.get(self.url_formula(self.project.id))
        self.assertEqual(r2.status_code, 200)
        j2 = self._json(r2)
        self.assertTrue(j2["ok"])
        self.assertEqual(len(j2["items"]), 1)
        self.assertEqual(j2["items"][0]["pekerjaan_id"], self.p1.id)
        self.assertEqual(j2["items"][0]["raw"], "=L*W*H")
        self.assertTrue(j2["items"][0]["is_fx"])

    def test_formula_post_update_same_row(self):
        # Create awal
        VolumeFormulaState.objects.create(project=self.project, pekerjaan=self.p1, raw="=A*B", is_fx=True)
        # Update raw & is_fx
        payload = {"items": [{"pekerjaan_id": self.p1.id, "raw": "123.456", "is_fx": False}]}
        r = self.client.post(self.url_formula(self.project.id),
                             data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        j = self._json(r)
        self.assertTrue(j["ok"])
        self.assertEqual(j["created"], 0)
        self.assertEqual(j["updated"], 1)
        self.assertEqual(j["errors"], [])

        obj = VolumeFormulaState.objects.get(project=self.project, pekerjaan=self.p1)
        self.assertEqual(obj.raw, "123.456")
        self.assertFalse(obj.is_fx)

    def test_formula_post_cross_project_rejected(self):
        if not self.px:
            self.skipTest("Project kedua tidak tersedia; melewati cross-project test.")
        # Kirim pekerjaan milik other_project ke endpoint project utama → harus error
        payload = {"items": [{"pekerjaan_id": self.px.id, "raw": "=BAD", "is_fx": True}]}
        r = self.client.post(self.url_formula(self.project.id),
                             data=json.dumps(payload), content_type="application/json")
        # partial failure → status 400 hanya jika tidak ada yang tersimpan;
        # di sini semuanya invalid → 400
        self.assertEqual(r.status_code, 400)
        j = self._json(r)
        self.assertFalse(j["ok"])
        self.assertGreaterEqual(len(j["errors"]), 1)

    # ---------------- tests: tree sanity ----------------
    def test_tree_contains_pekerjaan(self):
        r = self.client.get(self.url_tree(self.project.id))
        self.assertEqual(r.status_code, 200)
        j = self._json(r)
        self.assertTrue(j["ok"])
        # minimal ada satu klasifikasi dan pekerjaan yang kita buat
        self.assertGreaterEqual(len(j["klasifikasi"]), 1)
        # flatten pekerjaan ids
        ids = []
        for k in j["klasifikasi"]:
            for s in k.get("sub", []):
                ids += [p["id"] for p in s.get("pekerjaan", [])]
        self.assertIn(self.p1.id, ids)
        self.assertIn(self.p2.id, ids)

    # ---------------- tests: volume save (partial + normalisasi angka) ----------------
    def test_volume_partial_success_and_number_normalization(self):
        """
        - Kirim dua item: satu valid (p1: '1234,5'), satu invalid (pekerjaan lain project) → status 200 (partial)
        - Cek pembulatan HALF_UP ke 3dp
        """
        # invalid id → pakai pekerjaan milik project lain jika ada; kalau tidak, pakai id besar
        invalid_id = self.px.id if self.px else 9999999

        payload = {
            "items": [
                {"pekerjaan_id": self.p1.id, "quantity": "1234,5"},  # comma decimal → 1234.5
                {"pekerjaan_id": invalid_id, "quantity": "10"}
            ]
        }
        r = self.client.post(self.url_volume_save(self.project.id),
                             data=json.dumps(payload), content_type="application/json")
        # karena 1 tersimpan dan 1 error → 200
        self.assertEqual(r.status_code, 200)
        j = self._json(r)
        self.assertTrue(j["ok"])
        self.assertEqual(j["saved"], 1)
        self.assertGreaterEqual(len(j["errors"]), 1)
        self.assertEqual(j["decimal_places"], 3)

        # Cek DB tersimpan dengan 3dp HALF_UP
        vp = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.p1)
        self.assertEqual(vp.quantity, Decimal("1234.500"))

    def test_volume_reject_negative_or_invalid(self):
        payload = {"items": [{"pekerjaan_id": self.p2.id, "quantity": "-1"}]}
        r = self.client.post(self.url_volume_save(self.project.id),
                             data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 400)
        j = self._json(r)
        self.assertFalse(j["ok"])
        self.assertGreaterEqual(len(j["errors"]), 1)
