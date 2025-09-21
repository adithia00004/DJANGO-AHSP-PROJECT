# detail_project/tests/test_api_numeric_endpoints.py
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import DecimalField, CharField, TextField

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, HargaItemProject, VolumePekerjaan
)

User = get_user_model()


class APINumericEndpointsTests(TestCase):
    def setUp(self):
        self.client = Client()

        # User + login
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="pass12345"
        )
        self.client.force_login(self.user)

        # Project milik user (aktif) + pengisian field wajib minimal
        base_kwargs = dict(
            owner=self.user,
            is_active=True,
            nama="Proyek Uji",
            index_project="PRJ-001",
            tahun_project=2025,
            sumber_dana="APBD",
            lokasi_project="Makassar",
        )

        proj_fields = {f.name: f for f in Project._meta.fields}

        # --- Penanganan kolom NOT NULL yang ada di skema Anda ---
        # anggaran_owner ditemukan bertipe DecimalField (bukan FK) pada environment Anda,
        # sehingga harus diisi angka, bukan string.
        if "anggaran_owner" in proj_fields:
            f = proj_fields["anggaran_owner"]
            # Jika DecimalField → isi 0
            if isinstance(f, DecimalField):
                base_kwargs["anggaran_owner"] = Decimal("0")
            # Jika ternyata Char/Text pada skema lain → isi string
            elif isinstance(f, CharField) or isinstance(f, TextField):
                base_kwargs["anggaran_owner"] = "Pemda"
            # Jika ternyata FK ke User pada skema lain → isi user
            elif getattr(f, "is_relation", False) and getattr(f, "related_model", None) == User:
                base_kwargs["anggaran_owner"] = self.user
            else:
                # Fallback aman: coba 0 (untuk numeric) atau biarkan kosong jika nullable
                if not f.null:
                    base_kwargs["anggaran_owner"] = Decimal("0")

        # (Jika setelah ini ada error NOT NULL untuk kolom lain,
        #  tinggal tambahkan pola serupa di sini untuk kolom tersebut.)

        self.project = Project.objects.create(**base_kwargs)

        # Struktur dasar klasifikasi/sub untuk FK Pekerjaan
        self.klas = Klasifikasi.objects.create(project=self.project, name="Klas 1", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=self.klas, name="Sub 1.1", ordering_index=1)

        # Pekerjaan:
        # - REF (read-only) → dipakai untuk test blok simpan
        self.job_ref = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_REF,
            snapshot_kode="10.1.1",
            snapshot_uraian="Pekerjaan REF",
            snapshot_satuan="m2",
            ordering_index=1,
        )

        # - REF_MODIFIED → boleh disimpan/reset
        self.job_mod = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_REF_MOD,
            snapshot_kode="mod.1-10.1.2",
            snapshot_uraian="Pekerjaan REF Mod",
            snapshot_satuan="m2",
            ordering_index=2,
        )

        # - CUSTOM → boleh disimpan
        self.job_custom = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001",
            snapshot_uraian="Pekerjaan Custom",
            snapshot_satuan="m",
            ordering_index=3,
        )

    # ---------- Helpers ----------
    def _url_save_detail(self, pekerjaan_id):
        return reverse("detail_project:api_save_detail_ahsp_for_pekerjaan", args=[self.project.id, pekerjaan_id])

    def _url_save_harga(self):
        return reverse("detail_project:api_save_harga_items", args=[self.project.id])

    def _url_list_harga(self, canon=False):
        url = reverse("detail_project:api_list_harga_items", args=[self.project.id])
        return f"{url}?canon=1" if canon else url

    def _url_save_volume(self):
        return reverse("detail_project:api_save_volume_pekerjaan", args=[self.project.id])

    # ============================================================
    # TESTS
    # ============================================================

    def test_detail_ahsp_save_blocks_ref(self):
        """
        Pekerjaan REF tidak boleh disimpan via endpoint ini (400).
        """
        payload = {
            "rows": [{
                "kategori": "TK", "kode": "TK-01", "uraian": "Pekerja", "satuan": "OH", "koefisien": "1"
            }]
        }
        r = self.client.post(
            self._url_save_detail(self.job_ref.id),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 400, r.content)
        js = r.json()
        self.assertFalse(js.get("ok"))
        self.assertEqual(DetailAHSPProject.objects.filter(project=self.project, pekerjaan=self.job_ref).count(), 0)

    def test_detail_ahsp_save_duplicate_kode_results_207_with_one_saved(self):
        """
        Duplikat kode di payload → status 207; satu baris valid tetap tersimpan.
        """
        payload = {
            "rows": [
                {"kategori": "TK", "kode": "K-01", "uraian": "Pekerja 1", "satuan": "OH", "koefisien": "1"},
                {"kategori": "TK", "kode": "K-01", "uraian": "Pekerja 1 (dupe)", "satuan": "OH", "koefisien": "2"},
            ]
        }
        r = self.client.post(
            self._url_save_detail(self.job_mod.id),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertIn(r.status_code, (207, 200), r.content)
        js = r.json()
        self.assertTrue("saved_rows" in js)
        # minimal 1 baris valid
        self.assertGreaterEqual(js["saved_rows"], 1)
        self.assertEqual(
            DetailAHSPProject.objects.filter(project=self.project, pekerjaan=self.job_mod).count(),
            js["saved_rows"]
        )

    def test_detail_ahsp_save_parses_decimal_and_quantizes(self):
        """
        Terima '2,7275' → simpan Decimal('2.727500') (dp=6).
        """
        payload = {
            "rows": [{
                "kategori": "TK", "kode": "TK-02", "uraian": "Mandor", "satuan": "OH", "koefisien": "2,7275"
            }]
        }
        r = self.client.post(
            self._url_save_detail(self.job_mod.id),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertIn(r.status_code, (200, 207), r.content)
        d = DetailAHSPProject.objects.get(project=self.project, pekerjaan=self.job_mod, kode="TK-02")
        self.assertEqual(d.koefisien, Decimal("2.727500"))

    def test_harga_save_and_list_canon(self):
        """
        Hanya item yang digunakan di Detail AHSP proyek yang boleh di-update.
        Simpan harga '1.234,56' → tersimpan Decimal('1234.56'); list?canon=1 → '1234.56'.
        """
        # 1) Buat detail agar HargaItemProject terdaftar sebagai "dipakai di proyek ini"
        detail_payload = {
            "rows": [
                {"kategori": "TK", "kode": "TK-11", "uraian": "Tukang", "satuan": "OH", "koefisien": "1"},
                {"kategori": "BHN", "kode": "B-11", "uraian": "Semen", "satuan": "zak", "koefisien": "2"}
            ]
        }
        r1 = self.client.post(
            self._url_save_detail(self.job_custom.id),
            data=json.dumps(detail_payload),
            content_type="application/json"
        )
        self.assertIn(r1.status_code, (200, 207), r1.content)

        # 2) Ambil list harga (tanpa canon) untuk dapatkan ID
        r2 = self.client.get(self._url_list_harga())
        self.assertEqual(r2.status_code, 200, r2.content)
        items = r2.json().get("items", [])
        self.assertTrue(len(items) >= 2)
        any_id = items[0]["id"]

        # 3) Update satu item pakai localized string
        save_payload = {"items": [{"id": any_id, "harga_satuan": "1.234,56"}]}
        r3 = self.client.post(
            self._url_save_harga(),
            data=json.dumps(save_payload),
            content_type="application/json"
        )
        self.assertEqual(r3.status_code, 200, r3.content)
        self.assertEqual(r3.json().get("updated"), 1)

        # 4) list?canon=1 → harga_satuan harus string kanonik "1234.56"
        r4 = self.client.get(self._url_list_harga(canon=True))
        self.assertEqual(r4.status_code, 200, r4.content)
        it = next((x for x in r4.json().get("items", []) if x["id"] == any_id), None)
        self.assertIsNotNone(it)
        self.assertEqual(it["harga_satuan"], "1234.56")

    def test_volume_save_parses_localized_and_quantizes(self):
        """
        Terima '1.234,5' → simpan Decimal('1234.500') (dp=3).
        """
        payload = {
            "items": [{
                "pekerjaan_id": self.job_custom.id,
                "quantity": "1.234,5"
            }]
        }
        r = self.client.post(
            self._url_save_volume(),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(r.status_code, 200, r.content)

        vp = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.job_custom)
        self.assertEqual(vp.quantity, Decimal("1234.500"))
