# detail_project/tests/test_list_pekerjaan_api.py
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models as djm
from decimal import Decimal
import json

from dashboard.models import Project
from referensi.models import AHSPReferensi
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, DetailAHSPProject, HargaItemProject
)

# =========================
# URL NAME CONSTANTS (EDIT DI SINI JIKA PERLU)
# FE (JS) memanggil:
#   GET  /detail_project/api/project/<id>/list-pekerjaan/tree/
#   POST /detail_project/api/project/<id>/list-pekerjaan/upsert/
# Pastikan urls.py memetakan ke nama di bawah.
# =========================
API_UPSERT_NAME = "detail_project:api_upsert_list_pekerjaan"
API_TREE_NAME   = "detail_project:api_get_list_pekerjaan_tree"


def make_project_for_tests(owner):
    """
    Buat Project minimal tanpa menebak skema.
    - Isi semua field wajib (null=False, tanpa default).
    - Untuk FK bernuansa owner/user, isi dengan user test.
    - Untuk FK lain, coba reuse existing; kalau tidak ada, buat minimal berdasarkan CharField pertama yang wajib.
    """
    kwargs = {}
    fields = Project._meta.fields

    # isi owner jika ada
    if any(f.name == "owner" for f in fields):
        kwargs["owner"] = owner

    for f in fields:
        if f.auto_created or f.primary_key:
            continue
        if f.name in kwargs:
            continue

        # kalau sudah punya default atau null=True → biarkan
        if f.has_default() or getattr(f, "null", False):
            continue

        if isinstance(f, djm.BooleanField):
            kwargs[f.name] = True
        elif isinstance(f, djm.CharField):
            alias = {"name": "P1", "title": "P1", "nama": "P1", "project_name": "P1", "judul": "P1"}
            kwargs[f.name] = alias.get(f.name, f"P1-{f.name}")
        elif isinstance(f, djm.TextField):
            kwargs[f.name] = f"Dummy {f.name}"
        elif isinstance(f, djm.IntegerField):
            kwargs[f.name] = 0
        elif isinstance(f, djm.PositiveIntegerField):
            kwargs[f.name] = 2025
        elif isinstance(f, djm.DecimalField):
            q = Decimal("0").quantize(Decimal(f"1e-{f.decimal_places}"))
            kwargs[f.name] = q
        elif isinstance(f, djm.DateTimeField):
            kwargs[f.name] = timezone.now()
        elif isinstance(f, djm.DateField):
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
                    # buat minimal object untuk relasi tersebut
                    create_kwargs = {}
                    for rf in rel._meta.fields:
                        if rf.auto_created or rf.primary_key:
                            continue
                        if rf.has_default() or getattr(rf, "null", False):
                            continue
                        if isinstance(rf, djm.CharField):
                            create_kwargs[rf.name] = f"{rel.__name__}-{rf.name}"
                            break
                        if isinstance(rf, djm.IntegerField):
                            create_kwargs[rf.name] = 0
                            break
                    if create_kwargs:
                        kwargs[f.name] = rel._default_manager.create(**create_kwargs)
                    else:
                        # biarkan gagal → memberi tahu field mana yang wajib
                        pass
        else:
            # fallback: coba default (bila ada API kompatibel)
            try:
                kwargs[f.name] = f.get_default()
            except Exception:
                pass

    if "is_active" in [f.name for f in fields]:
        kwargs["is_active"] = True

    return Project.objects.create(**kwargs)


class ListPekerjaanUpsertAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="u1", password="pass12345")
        cls.project = make_project_for_tests(cls.user)

        # minimal dua referensi untuk variasi
        cls.ref1 = AHSPReferensi.objects.create(kode_ahsp="A.01", nama_ahsp="Galian tanah")
        cls.ref2 = AHSPReferensi.objects.create(kode_ahsp="A.02", nama_ahsp="Urugan tanah")

    def setUp(self):
        self.c = Client()
        self.c.login(username="u1", password="pass12345")

    # ---------- helpers ----------
    def _upsert(self, payload: dict):
        try:
            url = reverse(API_UPSERT_NAME, kwargs={"project_id": self.project.id})
        except NoReverseMatch as e:
            raise AssertionError(
                f"URL name '{API_UPSERT_NAME}' tidak ditemukan. "
                "Samakan dengan pola FE: /detail_project/api/project/<id>/list-pekerjaan/upsert/"
            ) from e
        return self.c.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def _get_tree(self):
        try:
            url = reverse(API_TREE_NAME, kwargs={"project_id": self.project.id})
        except NoReverseMatch as e:
            raise AssertionError(
                f"URL name '{API_TREE_NAME}' tidak ditemukan. "
                "Samakan dengan pola FE: /detail_project/api/project/<id>/list-pekerjaan/tree/"
            ) from e
        return self.c.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    # ---------- tests ----------
    def test_upsert_custom_minimal_success(self):
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "1.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "Pekerjaan custom 1",
                                    "snapshot_satuan": "m2"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        r = self._upsert(payload)
        self.assertIn(r.status_code, (200, 207), r.content)
        self.assertEqual(
            Pekerjaan.objects.filter(project=self.project, source_type=Pekerjaan.SOURCE_CUSTOM).count(), 1
        )

        t = self._get_tree()
        self.assertEqual(t.status_code, 200)
        data = t.json()
        self.assertIn("klasifikasi", data)
        self.assertIsInstance(data["klasifikasi"], list)
        p0 = data["klasifikasi"][0]["sub"][0]["pekerjaan"][0]
        self.assertEqual(p0["source_type"], "custom")
        self.assertEqual(p0["snapshot_uraian"], "Pekerjaan custom 1")
        self.assertEqual(p0["snapshot_satuan"], "m2")

    def test_upsert_ref_requires_ref_id(self):
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "1.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "ref",
                                    "ordering_index": 1
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        r = self._upsert(payload)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 0)

    def test_upsert_ref_success(self):
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "1.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "ref",
                                    "ordering_index": 10,
                                    "ref_id": self.ref1.id
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        r = self._upsert(payload)
        self.assertIn(r.status_code, (200, 207), r.content)
        self.assertEqual(
            Pekerjaan.objects.filter(project=self.project, source_type=Pekerjaan.SOURCE_REF).count(), 1
        )

    def test_upsert_ref_modified_with_override(self):
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "1.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "ref_modified",
                                    "ordering_index": 2,
                                    "ref_id": self.ref2.id,
                                    "snapshot_uraian": "Uraian modifikasi",
                                    "snapshot_satuan": "unit"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        r = self._upsert(payload)
        self.assertIn(r.status_code, (200, 207), r.content)
        p = Pekerjaan.objects.get(project=self.project, ordering_index=2)
        self.assertEqual(p.source_type, Pekerjaan.SOURCE_REF_MOD)
        self.assertEqual(p.snapshot_uraian, "Uraian modifikasi")
        self.assertEqual(p.snapshot_satuan, "unit")

    def test_upsert_idempotent_and_reuse_ordering(self):
        payload1 = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "1.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {"source_type": "custom", "ordering_index": 1, "snapshot_uraian": "C-1"}
                            ]
                        }
                    ]
                }
            ]
        }
        r1 = self._upsert(payload1)
        self.assertIn(r1.status_code, (200, 207), r1.content)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 1)

        payload2 = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "1.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {"source_type": "ref", "ordering_index": 1, "ref_id": self.ref1.id}
                            ]
                        }
                    ]
                }
            ]
        }
        r2 = self._upsert(payload2)
        self.assertIn(r2.status_code, (200, 207), r2.content)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 1)
        p_now = Pekerjaan.objects.get(project=self.project)
        self.assertEqual(p_now.ordering_index, 1)

    def test_tree_returns_consistent_structure(self):
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas A",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "A.1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {"source_type": "ref", "ordering_index": 1, "ref_id": self.ref1.id}
                            ]
                        },
                        {
                            "name": "A.2",
                            "ordering_index": 2,
                            "pekerjaan": [
                                {"source_type": "custom", "ordering_index": 2, "snapshot_uraian": "Custom A2-1"}
                            ]
                        }
                    ]
                }
            ]
        }
        self._upsert(payload)

        resp = self._get_tree()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # FE toleran soal 'ok', tapi kita pastikan 'klasifikasi' selalu ada (kontrak FE)
        self.assertIn("klasifikasi", data)
        klas = data["klasifikasi"]
        self.assertEqual(len(klas), 1)
        self.assertEqual(len(klas[0]["sub"]), 2)
        p1 = klas[0]["sub"][0]["pekerjaan"]
        self.assertEqual(len(p1), 1)
        self.assertEqual(p1[0]["source_type"], "ref")
        p2 = klas[0]["sub"][1]["pekerjaan"]
        self.assertEqual(len(p2), 1)
        self.assertEqual(p2[0]["source_type"], "custom")
        self.assertEqual(p2[0]["snapshot_uraian"], "Custom A2-1")

    def test_tree_empty_is_ok_and_returns_empty_list(self):
        """Saat belum ada data, FE mengharapkan 'klasifikasi' tetap ada (array)."""
        resp = self._get_tree()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("klasifikasi", data)
        self.assertIsInstance(data["klasifikasi"], list)
