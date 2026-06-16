"""WP-B8a — derived LAIN item-type (D-08).

Locks the derivation rule (LAIN+ref=WORK_BUNDLE, LAIN no ref=OTHER_DIRECT, else
DIRECT) and that the detail GET payload exposes item_type / reference_type.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from referensi.models import AHSPReferensi

from .models import (
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from .services import (
    ITEM_TYPE_DIRECT,
    ITEM_TYPE_OTHER_DIRECT,
    ITEM_TYPE_WORK_BUNDLE,
    REFERENCE_TYPE_AHSP,
    REFERENCE_TYPE_PROJECT_JOB,
    item_type_of,
    reference_type_of,
)
from .views_api import build_detail_ahsp_payload


class ItemTypeDerivationTests(TestCase):
    def test_direct_for_base_categories(self):
        for kat in ("TK", "BHN", "ALT"):
            self.assertEqual(item_type_of(kat), ITEM_TYPE_DIRECT)

    def test_other_direct_for_lain_without_reference(self):
        self.assertEqual(item_type_of("LAIN"), ITEM_TYPE_OTHER_DIRECT)
        self.assertEqual(item_type_of("LAIN", None, None), ITEM_TYPE_OTHER_DIRECT)

    def test_work_bundle_for_lain_with_reference(self):
        self.assertEqual(item_type_of("LAIN", ref_ahsp_id=5), ITEM_TYPE_WORK_BUNDLE)
        self.assertEqual(item_type_of("LAIN", ref_pekerjaan_id=9), ITEM_TYPE_WORK_BUNDLE)

    def test_reference_type(self):
        self.assertIsNone(reference_type_of(None, None))
        self.assertEqual(reference_type_of(ref_ahsp_id=1), REFERENCE_TYPE_AHSP)
        self.assertEqual(reference_type_of(ref_pekerjaan_id=2), REFERENCE_TYPE_PROJECT_JOB)


class DetailPayloadItemTypeTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b8-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B8")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="P1",
            snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )

    def _detail(self, kategori, kode, *, ref_ahsp=None, ref_pekerjaan=None):
        hip = HargaItemProject.objects.create(
            project=self.project, kode_item=kode, kategori=kategori,
            uraian=f"Item {kode}", satuan="kg", harga_satuan=Decimal("100"),
        )
        return DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=self.pkj, harga_item=hip,
            kategori=kategori, kode=kode, uraian=f"Item {kode}", satuan="kg",
            koefisien=Decimal("1"), ref_ahsp=ref_ahsp, ref_pekerjaan=ref_pekerjaan,
        )

    def test_payload_exposes_item_type_per_row(self):
        self._detail("BHN", "B-1")
        self._detail("LAIN", "OTH-1")  # other direct cost (no ref)
        master = AHSPReferensi.objects.create(kode_ahsp="A.1", nama_ahsp="M", sumber="AHSP 2025")
        self._detail("LAIN", "BND-1", ref_ahsp=master)

        payload = build_detail_ahsp_payload(self.project, self.pkj)
        by_kode = {i["kode"]: i for i in payload["items"]}
        self.assertEqual(by_kode["B-1"]["item_type"], ITEM_TYPE_DIRECT)
        self.assertIsNone(by_kode["B-1"]["reference_type"])
        self.assertEqual(by_kode["OTH-1"]["item_type"], ITEM_TYPE_OTHER_DIRECT)
        self.assertIsNone(by_kode["OTH-1"]["reference_type"])
        self.assertEqual(by_kode["BND-1"]["item_type"], ITEM_TYPE_WORK_BUNDLE)
        self.assertEqual(by_kode["BND-1"]["reference_type"], REFERENCE_TYPE_AHSP)
        # B8c: human labels exposed for the UI.
        self.assertEqual(by_kode["OTH-1"]["item_type_label"], "Biaya Lain Langsung")
        self.assertEqual(by_kode["BND-1"]["item_type_label"], "Pekerjaan Gabungan")


class SaveOtherDirectTests(TestCase):
    """B8b — save accepts LAIN-without-ref as OTHER_DIRECT (no longer rejected)."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("b8b-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B8b")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pkj = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="P1",
            snapshot_uraian="P", snapshot_satuan="m2", ordering_index=1,
        )

    def _save(self, rows):
        import json

        from django.test import RequestFactory

        from .views_api import api_save_detail_ahsp_for_pekerjaan

        req = RequestFactory().post(
            "/save/", data=json.dumps({"rows": rows}), content_type="application/json"
        )
        req.user = self.owner
        return api_save_detail_ahsp_for_pekerjaan(req, self.project.id, self.pkj.id)

    def test_lain_without_ref_is_accepted_as_other_direct(self):
        import json

        from .models import DetailAHSPExpanded

        resp = self._save([
            {"kategori": "LAIN", "kode": "OTH-1", "uraian": "Mobilisasi", "satuan": "ls", "koefisien": "1"},
        ])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(json.loads(resp.content)["ok"])

        raw = DetailAHSPProject.objects.get(project=self.project, pekerjaan=self.pkj)
        self.assertIsNone(raw.ref_ahsp_id)
        self.assertIsNone(raw.ref_pekerjaan_id)
        # OTHER_DIRECT must reach expanded storage so it counts in rekap.
        exp = DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=self.pkj)
        self.assertEqual(exp.count(), 1)
        self.assertEqual(exp.first().kategori, "LAIN")
        self.assertIsNone(exp.first().source_bundle_kode)

    def test_mixed_direct_and_other_direct_all_saved(self):
        import json

        from .models import DetailAHSPExpanded

        resp = self._save([
            {"kategori": "BHN", "kode": "B-1", "uraian": "Semen", "satuan": "kg", "koefisien": "5"},
            {"kategori": "LAIN", "kode": "OTH-1", "uraian": "Overhead", "satuan": "ls", "koefisien": "1"},
        ])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(json.loads(resp.content)["ok"])
        self.assertEqual(
            DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=self.pkj).count(), 2
        )
