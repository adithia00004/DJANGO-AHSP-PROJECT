"""WP-P4 — List Pekerjaan.

P4a (UF-009/UF-012 regression lock): the root cause (sumber-unaware reference
resolution) is already fixed (resolution uses (kode, sumber); the frontend sends
the new ref_id on a version/source change). These tests LOCK the contract that a
genuine reference/source change via the upsert wipes the pekerjaan's stale derived
data (Volume / Template detail / schedule) — mirroring the real client workflow
where changing the AHSP version sends a different ref_id.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from referensi.models import AHSPReferensi, RincianReferensi

from .models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
    VolumePekerjaan,
)
from .services import _populate_expanded_from_raw
from .views_api import (
    api_import_template_from_file,
    api_list_pekerjaan_destructive_impact,
    api_upsert_list_pekerjaan,
)


class RefChangeResetCascadeTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("p4-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P4")
        # Two versions of the SAME kode under different sumber (the UF-009 scenario).
        self.ahsp2025 = AHSPReferensi.objects.create(
            kode_ahsp="A.1", nama_ahsp="Master A.1", sumber="AHSP 2025", satuan="m2",
        )
        RincianReferensi.objects.create(
            ahsp=self.ahsp2025, kategori="TK", kode_item="L.01", uraian_item="Pekerja",
            satuan_item="OH", koefisien=Decimal("5"),
        )
        self.ahsp2026 = AHSPReferensi.objects.create(
            kode_ahsp="A.1", nama_ahsp="Master A.1", sumber="AHSP 2026", satuan="m2",
        )
        RincianReferensi.objects.create(
            ahsp=self.ahsp2026, kategori="TK", kode_item="L.01", uraian_item="Pekerja",
            satuan_item="OH", koefisien=Decimal("8"),  # different version → different koef
        )

    def _upsert(self, payload):
        req = RequestFactory().post(
            reverse("detail_project:api_upsert_list_pekerjaan", kwargs={"project_id": self.project.id}),
            data=json.dumps(payload), content_type="application/json",
        )
        req.user = self.owner
        return api_upsert_list_pekerjaan(req, self.project.id)

    def _tree_payload(self, pekerjaan):
        return {"klasifikasi": [{"name": "K", "ordering_index": 1, "sub": [
            {"name": "S", "ordering_index": 1, "pekerjaan": [pekerjaan]}]}]}

    def test_changing_ref_version_resets_derived_data(self):
        # 1) Create a REF pekerjaan bound to the 2025 version.
        resp = self._upsert(self._tree_payload(
            {"source_type": "ref", "ref_id": self.ahsp2025.id, "ordering_index": 1}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        pkj = Pekerjaan.objects.get(project=self.project, source_type=Pekerjaan.SOURCE_REF)
        self.assertEqual(pkj.ref_id, self.ahsp2025.id)
        # User fills a volume against the 2025-bound pekerjaan.
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pkj, quantity=Decimal("3"))

        # 2) Change the reference to the 2026 version (frontend sends the new ref_id
        #    because the picker is filtered by sumber and resets on sumber change).
        resp = self._upsert(self._tree_payload(
            {"id": pkj.id, "source_type": "ref", "ref_id": self.ahsp2026.id, "ordering_index": 1}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        pkj.refresh_from_db()
        # The pekerjaan is now pinned to the 2026 version (no silent version drift).
        self.assertEqual(pkj.ref_id, self.ahsp2026.id)
        # Reset fired: the stale volume tied to the old version is wiped.
        self.assertFalse(VolumePekerjaan.objects.filter(project=self.project, pekerjaan=pkj).exists())

    def test_changing_source_type_resets_derived_data(self):
        resp = self._upsert(self._tree_payload(
            {"source_type": "ref", "ref_id": self.ahsp2025.id, "ordering_index": 1}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        pkj = Pekerjaan.objects.get(project=self.project, source_type=Pekerjaan.SOURCE_REF)
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pkj, quantity=Decimal("3"))

        # REF → CUSTOM: derived data must be wiped.
        resp = self._upsert(self._tree_payload(
            {"id": pkj.id, "source_type": "custom", "ordering_index": 1,
             "snapshot_uraian": "Custom job", "snapshot_satuan": "m2"}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        pkj.refresh_from_db()
        self.assertEqual(pkj.source_type, Pekerjaan.SOURCE_CUSTOM)
        self.assertFalse(VolumePekerjaan.objects.filter(project=self.project, pekerjaan=pkj).exists())

    def test_same_ref_no_reset(self):
        # Re-upserting the SAME ref must NOT wipe the user's volume (no spurious reset).
        resp = self._upsert(self._tree_payload(
            {"source_type": "ref", "ref_id": self.ahsp2025.id, "ordering_index": 1}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        pkj = Pekerjaan.objects.get(project=self.project, source_type=Pekerjaan.SOURCE_REF)
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pkj, quantity=Decimal("3"))

        resp = self._upsert(self._tree_payload(
            {"id": pkj.id, "source_type": "ref", "ref_id": self.ahsp2025.id, "ordering_index": 1}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(VolumePekerjaan.objects.filter(project=self.project, pekerjaan=pkj).exists())


class _BundleSetupMixin:
    """Shared scaffolding: a project with klas/sub and a bundle (B references A)."""

    def _setup_project(self, name):
        self.owner = get_user_model().objects.create_user(name + "-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama=name)
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1)
        self._order = 0

    def _pekerjaan(self, kode):
        self._order += 1
        return Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode=kode,
            snapshot_uraian=f"P {kode}", snapshot_satuan="m2", ordering_index=self._order,
        )

    def _hip(self, kode, kategori="TK"):
        return HargaItemProject.objects.create(
            project=self.project, kode_item=kode, kategori=kategori,
            uraian=f"Item {kode}", satuan="OH", harga_satuan=Decimal("100"),
        )

    def _base(self, pekerjaan, kode, koef="5"):
        return DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pekerjaan, harga_item=self._hip(kode),
            kategori="TK", kode=kode, uraian=f"Item {kode}", satuan="OH",
            koefisien=Decimal(koef),
        )

    def _bundle(self, pekerjaan, ref_pekerjaan, kode, koef="2"):
        return DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pekerjaan,
            harga_item=self._hip(kode, kategori="LAIN"),
            kategori="LAIN", kode=kode, uraian=f"Bundle {kode}", satuan="ls",
            koefisien=Decimal(koef), ref_pekerjaan=ref_pekerjaan,
        )

    def _upsert(self, payload):
        req = RequestFactory().post(
            reverse("detail_project:api_upsert_list_pekerjaan", kwargs={"project_id": self.project.id}),
            data=json.dumps(payload), content_type="application/json",
        )
        req.user = self.owner
        return api_upsert_list_pekerjaan(req, self.project.id)

    def _tree(self, *pekerjaan):
        return {"klasifikasi": [{"name": "K", "ordering_index": 1, "sub": [
            {"name": "S", "ordering_index": 1, "pekerjaan": list(pekerjaan)}]}]}


class BundleTargetDeleteGuardTests(_BundleSetupMixin, TestCase):
    """WP-P4 C1 — deleting a pekerjaan still used as a 'Pekerjaan Gabungan' target
    is rejected atomically with a clear message (not a 500 ProtectedError)."""

    def setUp(self):
        self._setup_project("P4-C1")
        self.A = self._pekerjaan("A")  # bundle target
        self.B = self._pekerjaan("B")  # depends on A
        self._bundle(self.B, self.A, "BND")

    def test_delete_bundle_target_rejected(self):
        # Upsert keeps B but omits A → A would be deleted while B still references it.
        resp = self._upsert(self._tree(
            {"id": self.B.id, "source_type": "custom", "ordering_index": 1,
             "snapshot_uraian": "P B", "snapshot_satuan": "m2"}
        ))
        self.assertEqual(resp.status_code, 400, resp.content)
        body = json.loads(resp.content)
        self.assertTrue(any("Pekerjaan Gabungan" in e["message"] for e in body["errors"]), body)
        # Atomic: nothing deleted — A (and B) survive.
        self.assertTrue(Pekerjaan.objects.filter(id=self.A.id).exists())
        self.assertTrue(Pekerjaan.objects.filter(id=self.B.id).exists())

    def test_delete_both_target_and_dependent_allowed(self):
        # Removing BOTH B and A together is fine (no surviving referencer).
        resp = self._upsert(self._tree())  # empty sub → both deleted
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(Pekerjaan.objects.filter(id__in=[self.A.id, self.B.id]).exists())


class BundleDependentReExpandTests(_BundleSetupMixin, TestCase):
    """WP-P4 C2 — when a bundle TARGET is reset/re-sourced via upsert, dependents
    that bundle it are re-expanded (no silent stale DetailAHSPExpanded)."""

    def setUp(self):
        self._setup_project("P4-C2")
        self.A = self._pekerjaan("A")
        self.B = self._pekerjaan("B")
        self._base(self.A, "L.01", koef="5")     # A has a base component
        self._bundle(self.B, self.A, "BND")      # B bundles A (koef 2)
        _populate_expanded_from_raw(self.project, self.B)
        # An empty reference (no rincian) to re-source A onto.
        self.ahsp_empty = AHSPReferensi.objects.create(
            kode_ahsp="X.1", nama_ahsp="Empty", sumber="AHSP 2025", satuan="m2")

    def _b_expanded_count(self):
        # A's base component is the only source of B's expanded rows (the expansion
        # normalizes kodes, so count is the stable signal).
        return DetailAHSPExpanded.objects.filter(
            project=self.project, pekerjaan=self.B, kategori="TK").count()

    def test_resetting_target_reexpands_dependent(self):
        # Precondition: B's expanded currently includes A's component.
        self.assertEqual(self._b_expanded_count(), 1)
        # Re-source A custom → REF(empty): A's detail is wiped (reset).
        resp = self._upsert(self._tree(
            {"id": self.A.id, "source_type": "ref", "ref_id": self.ahsp_empty.id, "ordering_index": 1},
            {"id": self.B.id, "source_type": "custom", "ordering_index": 2,
             "snapshot_uraian": "P B", "snapshot_satuan": "m2"},
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        # C2: cascade re-expanded B against A's NEW (empty) state → stale component gone.
        self.assertEqual(self._b_expanded_count(), 0)


class ImportTemplateAtomicTests(TestCase):
    """WP-P4b (LP-07) — template import is all-or-nothing: any error rolls back the
    entire import (no partial klas/sub/pekerjaan committed as 'warnings')."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("p4b-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P4b")

    def _import(self, content):
        req = RequestFactory().post(
            reverse("detail_project:api_import_template_from_file", kwargs={"project_id": self.project.id}),
            data=json.dumps({"content": content}), content_type="application/json",
        )
        req.user = self.owner
        return api_import_template_from_file(req, self.project.id)

    def _content(self, klas_ref):
        # New flat format. klas_ref controls whether the sub points to a real klasifikasi.
        return {
            "klasifikasi": [{"_export_id": "k1", "name": "K1"}],
            "sub_klasifikasi": [{"_export_id": "s1", "_klasifikasi_ref": klas_ref,
                                 "name": "S1", "ordering_index": 1}],
            "pekerjaan": [{"_export_id": "p1", "_sub_klasifikasi_ref": "s1",
                           "source_type": "custom", "snapshot_uraian": "P", "snapshot_satuan": "m2"}],
        }

    def test_clean_import_succeeds(self):
        resp = self._import(self._content("k1"))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(Klasifikasi.objects.filter(project=self.project).count(), 1)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 1)

    def test_partial_error_rolls_back_entirely(self):
        # The sub references a non-existent klasifikasi → import produces an error.
        # LP-07: the whole import must roll back (no orphan klasifikasi committed).
        resp = self._import(self._content("MISSING"))
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(Klasifikasi.objects.filter(project=self.project).count(), 0)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 0)


class UpsertPayloadLimitTests(TestCase):
    """WP-P4c (LP-06) — per-endpoint body-size cap on the upsert (DoS guard)."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("p4c-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="P4c")

    def _post(self, body):
        req = RequestFactory().post(
            reverse("detail_project:api_upsert_list_pekerjaan", kwargs={"project_id": self.project.id}),
            data=body, content_type="application/json",
        )
        req.user = self.owner
        return api_upsert_list_pekerjaan(req, self.project.id)

    def test_oversized_body_rejected_413(self):
        resp = self._post("x" * 2_000_001)
        self.assertEqual(resp.status_code, 413, resp.content)

    def test_normal_body_not_413(self):
        resp = self._post(json.dumps({"klasifikasi": []}))
        self.assertNotEqual(resp.status_code, 413)


class DestructiveImpactPreviewTests(_BundleSetupMixin, TestCase):
    """WP-P4d (LP-04) — read-only preview of what a save would delete + the downstream
    data lost, and bundle-target deletions that would be blocked (C1)."""

    def setUp(self):
        self._setup_project("P4d")

    def _impact(self, payload):
        req = RequestFactory().post(
            reverse("detail_project:api_list_pekerjaan_destructive_impact",
                    kwargs={"project_id": self.project.id}),
            data=json.dumps(payload), content_type="application/json",
        )
        req.user = self.owner
        resp = api_list_pekerjaan_destructive_impact(req, self.project.id)
        return resp, json.loads(resp.content)

    def test_reports_downstream_loss_for_deletion(self):
        A = self._pekerjaan("A")
        self._base(A, "L.01")  # 1 template component
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=A, quantity=Decimal("3"))
        # Payload omits A → A would be deleted.
        resp, body = self._impact(self._tree())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(body["has_destructive"])
        self.assertFalse(body["has_blocked"])
        self.assertEqual(body["totals"]["pekerjaan"], 1)
        self.assertEqual(body["totals"]["volume"], 1)
        self.assertEqual(body["totals"]["detail"], 1)
        self.assertEqual(body["to_delete"][0]["label"], "A")

    def test_flags_blocked_bundle_target(self):
        A = self._pekerjaan("A")
        B = self._pekerjaan("B")
        self._bundle(B, A, "BND")  # B depends on A
        # Payload keeps B, omits A → deleting A is blocked.
        resp, body = self._impact(self._tree(
            {"id": B.id, "source_type": "custom", "ordering_index": 1,
             "snapshot_uraian": "P B", "snapshot_satuan": "m2"}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(body["has_blocked"])
        self.assertEqual(body["blocked"][0]["label"], "A")
        self.assertIn("B", body["blocked"][0]["blocked_by"])

    def test_no_deletion_no_destructive(self):
        A = self._pekerjaan("A")
        resp, body = self._impact(self._tree(
            {"id": A.id, "source_type": "custom", "ordering_index": 1,
             "snapshot_uraian": "P A", "snapshot_satuan": "m2"}
        ))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(body["has_destructive"])
        self.assertEqual(body["totals"]["pekerjaan"], 0)
