"""
Regression tests for automatic orphan HargaItemProject cleanup.

Behaviour under test: ketika Detail AHSP disimpan dan sebuah komponen dihapus,
HargaItemProject yang tidak lagi dipakai pekerjaan mana pun harus terbuang otomatis
(via transaction.on_commit) sehingga tidak muncul lagi di halaman Harga Items.
Item yang masih dipakai pekerjaan lain TIDAK boleh ikut terhapus.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, HargaItemProject,
)
from detail_project.views_api import (
    api_save_detail_ahsp_for_pekerjaan,
    build_harga_items_payload,
)


class OrphanAutoCleanupTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner_orphan_autoclean",
            email="owner-orphan-autoclean@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner, nama="P Orphan", sumber_dana="APBN",
            lokasi_project="Jakarta", nama_client="C", anggaran_owner=1000,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="K1", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S1", ordering_index=1
        )
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUS.001", snapshot_uraian="Custom", snapshot_satuan="m2",
            ordering_index=1,
        )
        self.factory = RequestFactory()

    def _row(self, kode):
        return {
            "kategori": "TK", "kode": kode, "uraian": f"U {kode}", "satuan": "m2",
            "koefisien": "1.000000", "koef_formula_raw": "", "koef_is_fx": False,
        }

    def _save(self, pekerjaan, rows):
        req = self.factory.post(
            "/api/mock/", data=json.dumps({"rows": rows}), content_type="application/json"
        )
        req.user = self.owner
        # on_commit callbacks (auto-cleanup) only fire when the outer atomic commits.
        with self.captureOnCommitCallbacks(execute=True):
            resp = api_save_detail_ahsp_for_pekerjaan(req, self.project.id, pekerjaan.id)
        return resp

    def test_removed_component_harga_item_is_auto_cleaned(self):
        # NOTE: item identity is the URAIAN (kode is resolved canonically from the
        # registry via resolve_item_code), so assertions key on uraian, not kode.
        resp = self._save(self.pkj, [self._row("TK.001"), self._row("TK.002")])
        self.assertEqual(resp.status_code, 200, resp.content.decode())
        self.assertTrue(
            HargaItemProject.objects.filter(project=self.project, uraian="U TK.002").exists()
        )

        # Save again without TK.002 -> it becomes orphan and should be removed.
        resp2 = self._save(self.pkj, [self._row("TK.001")])
        self.assertEqual(resp2.status_code, 200, resp2.content.decode())

        self.assertFalse(
            HargaItemProject.objects.filter(project=self.project, uraian="U TK.002").exists(),
            "Orphan harga item 'U TK.002' should have been auto-cleaned after save",
        )
        self.assertTrue(
            HargaItemProject.objects.filter(project=self.project, uraian="U TK.001").exists()
        )

        # And it must not appear in the Harga Items list payload anymore.
        payload = build_harga_items_payload(self.project, canon=True)
        uraians = {it["uraian"] for it in payload["items"]}
        self.assertIn("U TK.001", uraians)
        self.assertNotIn("U TK.002", uraians)

    def test_shared_item_not_deleted_when_still_used_elsewhere(self):
        pkj2 = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUS.002", snapshot_uraian="Custom2", snapshot_satuan="m2",
            ordering_index=2,
        )
        # Both pekerjaan use the same shared item.
        self._save(self.pkj, [self._row("TK.SHARED")])
        self._save(pkj2, [self._row("TK.SHARED")])

        # Remove the shared item from pkj only; pkj2 still uses it -> must survive.
        self._save(self.pkj, [self._row("TK.OTHER")])

        self.assertTrue(
            HargaItemProject.objects.filter(project=self.project, uraian="U TK.SHARED").exists(),
            "Shared item still used by another pekerjaan must NOT be auto-cleaned",
        )
