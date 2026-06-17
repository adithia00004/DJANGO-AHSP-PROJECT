"""WP-B7a — master reference signature + snapshot stamping.

Locks: master_reference_signature is deterministic and content-based; the raw
bundle row (DetailAHSPProject.ref_ahsp) is stamped with the master signature at
expansion time; non-master rows are left untouched.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from referensi.models import AHSPReferensi, RincianReferensi

from .models import (
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from .readiness import compute_project_readiness, master_reference_signature
from .services import _populate_expanded_from_raw


class MasterReferenceSignatureTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b7-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B7 Ref Sync")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )

    def _master(self, kode, sumber="AHSP 2025"):
        return AHSPReferensi.objects.create(kode_ahsp=kode, nama_ahsp=f"Master {kode}", sumber=sumber)

    def _rincian(self, ahsp, kategori, kode_item, koef, satuan="kg", uraian=None):
        return RincianReferensi.objects.create(
            ahsp=ahsp, kategori=kategori, kode_item=kode_item,
            uraian_item=uraian or f"Item {kode_item}", satuan_item=satuan,
            koefisien=Decimal(str(koef)),
        )

    def _custom_pekerjaan(self, kode="P1"):
        return Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode=kode,
            snapshot_uraian=f"P {kode}", snapshot_satuan="m2", ordering_index=1,
        )

    def _bundle_row(self, pekerjaan, ahsp, koef=2):
        hip = HargaItemProject.objects.create(
            project=self.project, kode_item=ahsp.kode_ahsp, kategori="LAIN",
            uraian=ahsp.nama_ahsp, satuan="ls",
        )
        return DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pekerjaan, harga_item=hip,
            kategori="LAIN", kode=ahsp.kode_ahsp, uraian=ahsp.nama_ahsp, satuan="ls",
            koefisien=Decimal(str(koef)), ref_ahsp=ahsp,
        )

    # ---- signature determinism & content sensitivity ----
    def test_signature_is_deterministic(self):
        ahsp = self._master("A.1")
        self._rincian(ahsp, "BHN", "B-1", 5)
        self._rincian(ahsp, "TK", "T-1", 2)
        self.assertEqual(
            master_reference_signature(ahsp.id),
            master_reference_signature(ahsp.id),
        )

    def test_signature_changes_when_koefisien_changes(self):
        ahsp = self._master("A.1")
        r = self._rincian(ahsp, "BHN", "B-1", 5)
        before = master_reference_signature(ahsp.id)
        r.koefisien = Decimal("6")
        r.save(update_fields=["koefisien"])
        self.assertNotEqual(before, master_reference_signature(ahsp.id))

    def test_signature_changes_when_component_added(self):
        ahsp = self._master("A.1")
        self._rincian(ahsp, "BHN", "B-1", 5)
        before = master_reference_signature(ahsp.id)
        self._rincian(ahsp, "BHN", "B-2", 1)  # new "Aditif"-style item
        self.assertNotEqual(before, master_reference_signature(ahsp.id))

    def test_signature_none_for_missing_or_empty_master(self):
        self.assertIsNone(master_reference_signature(None))
        empty = self._master("A.empty")
        self.assertIsNone(master_reference_signature(empty.id))

    def test_signature_independent_of_insertion_order(self):
        a1 = self._master("A.1")
        self._rincian(a1, "BHN", "B-1", 5)
        self._rincian(a1, "TK", "T-1", 2)
        a2 = self._master("A.2")
        self._rincian(a2, "TK", "T-1", 2)
        self._rincian(a2, "BHN", "B-1", 5)
        self.assertEqual(
            master_reference_signature(a1.id),
            master_reference_signature(a2.id),
        )

    # ---- stamping at expansion time ----
    def test_expansion_stamps_master_signature_on_bundle_row(self):
        ahsp = self._master("A.1")
        self._rincian(ahsp, "BHN", "B-1", 5)
        self._rincian(ahsp, "TK", "T-1", 2)
        pkj = self._custom_pekerjaan()
        row = self._bundle_row(pkj, ahsp)
        self.assertIsNone(row.ref_snapshot_signature)

        _populate_expanded_from_raw(self.project, pkj)

        row.refresh_from_db()
        self.assertEqual(row.ref_snapshot_signature, master_reference_signature(ahsp.id))
        self.assertIsNotNone(row.ref_synced_at)

    def test_user_koefisien_is_not_touched_by_stamping(self):
        ahsp = self._master("A.1")
        self._rincian(ahsp, "BHN", "B-1", 5)
        pkj = self._custom_pekerjaan()
        row = self._bundle_row(pkj, ahsp, koef=3)

        _populate_expanded_from_raw(self.project, pkj)

        row.refresh_from_db()
        self.assertEqual(row.koefisien, Decimal("3.000000000000"))

    def test_non_master_rows_are_not_stamped(self):
        pkj = self._custom_pekerjaan()
        hip = HargaItemProject.objects.create(
            project=self.project, kode_item="B-1", kategori="BHN",
            uraian="Bahan", satuan="kg",
        )
        row = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pkj, harga_item=hip,
            kategori="BHN", kode="B-1", uraian="Bahan", satuan="kg",
            koefisien=Decimal("1"),
        )
        _populate_expanded_from_raw(self.project, pkj)
        row.refresh_from_db()
        self.assertIsNone(row.ref_snapshot_signature)
        self.assertIsNone(row.ref_synced_at)


class ReferenceUpdateAvailableSignalTests(MasterReferenceSignatureTests):
    """B7b — readiness reference_update_available (schema b4.5)."""

    @staticmethod
    def _signal(readiness):
        return readiness["reference_update_available"]

    def test_schema_version_is_b4_6(self):
        self.assertEqual(compute_project_readiness(self.project)["schema_version"], "b4.6")

    def test_no_signal_when_in_sync(self):
        ahsp = self._master("A.1")
        self._rincian(ahsp, "BHN", "B-1", 5)
        pkj = self._custom_pekerjaan()
        self._bundle_row(pkj, ahsp)
        _populate_expanded_from_raw(self.project, pkj)
        self.assertEqual(self._signal(compute_project_readiness(self.project)), [])

    def test_signal_fires_when_master_corrected_in_place(self):
        # Scenario 1 (in-place edit / re-import same sumber): the chosen master
        # version is changed underneath the project → must surface.
        ahsp = self._master("A.1")
        r = self._rincian(ahsp, "BHN", "B-1", 5)
        pkj = self._custom_pekerjaan()
        row = self._bundle_row(pkj, ahsp)
        _populate_expanded_from_raw(self.project, pkj)

        r.koefisien = Decimal("6")  # in-place correction of master 2025
        r.save(update_fields=["koefisien"])

        sig = self._signal(compute_project_readiness(self.project))
        self.assertEqual(len(sig), 1)
        self.assertEqual(sig[0]["issue"], "reference_update_available")
        self.assertEqual(sig[0]["ref_ahsp_id"], ahsp.id)
        self.assertIn(pkj.id, compute_project_readiness(self.project)["affected_pekerjaan"])

    def test_new_yearly_version_does_not_fire(self):
        # Scenario 2 (owner's case): admin ADDS a new yearly version (different
        # `sumber`, new row) instead of editing 2025. The project's ref_ahsp still
        # points to the unchanged 2025 row → no signal; project stays pinned.
        ahsp_2025 = self._master("A.1", sumber="AHSP 2025")
        self._rincian(ahsp_2025, "BHN", "B-1", 5)
        pkj = self._custom_pekerjaan()
        self._bundle_row(pkj, ahsp_2025)
        _populate_expanded_from_raw(self.project, pkj)

        # New version published as a separate master — does not touch 2025.
        ahsp_2027 = self._master("A.1", sumber="AHSP SNI 2027")
        self._rincian(ahsp_2027, "BHN", "B-1", 6)
        self._rincian(ahsp_2027, "BHN", "B-2", 1)

        self.assertEqual(self._signal(compute_project_readiness(self.project)), [])

    def test_legacy_unstamped_row_does_not_fire(self):
        # A bundle whose snapshot was never stamped (null) must not false-positive.
        ahsp = self._master("A.1")
        self._rincian(ahsp, "BHN", "B-1", 5)
        pkj = self._custom_pekerjaan()
        self._bundle_row(pkj, ahsp)  # no _populate_expanded_from_raw → not stamped
        self.assertEqual(self._signal(compute_project_readiness(self.project)), [])


class ResetCascadeTests(TestCase):
    """B7c (TA-03) — reset-to-reference cascades re-expansion to dependents."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user("b7c-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B7c Reset")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )

    def test_reset_re_expands_dependent_bundle(self):
        from django.test import RequestFactory

        from .models import DetailAHSPExpanded
        from .services import _populate_expanded_from_raw, clone_ref_pekerjaan
        from .views_api import api_reset_detail_ahsp_to_ref

        # Master M with a single TK component.
        master = AHSPReferensi.objects.create(
            kode_ahsp="A.X", nama_ahsp="Master A.X", sumber="AHSP 2025", satuan="m2",
        )
        RincianReferensi.objects.create(
            ahsp=master, kategori="TK", kode_item="L.01", uraian_item="Pekerja",
            satuan_item="OH", koefisien=Decimal("5"),
        )

        # A = ref_modified pekerjaan cloned from M (auto-loads rincian).
        a = clone_ref_pekerjaan(
            self.project, self.sub, master, Pekerjaan.SOURCE_REF_MOD, ordering_index=1,
            auto_load_rincian=True,
        )
        _populate_expanded_from_raw(self.project, a)

        # B = custom pekerjaan bundling A (LAIN ref_pekerjaan), koef 2.
        b = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode="B1",
            snapshot_uraian="B", snapshot_satuan="m2", ordering_index=2,
        )
        b_hip = HargaItemProject.objects.create(
            project=self.project, kode_item=a.snapshot_kode, kategori="LAIN",
            uraian="Bundle A", satuan="ls",
        )
        DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=b, harga_item=b_hip,
            kategori="LAIN", kode=a.snapshot_kode, uraian="Bundle A", satuan="ls",
            koefisien=Decimal("2"), ref_pekerjaan=a,
        )
        _populate_expanded_from_raw(self.project, b)
        self.assertTrue(
            DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=b).exists()
        )

        # Simulate B going stale: drop its expanded storage entirely.
        DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=b).delete()

        # Reset A. Without B7c, B stays empty (silent stale). With B7c the cascade
        # rebuilds B inside the same atomic transaction.
        req = RequestFactory().post("/reset/")
        req.user = self.owner
        resp = api_reset_detail_ahsp_to_ref(req, self.project.id, a.id)
        self.assertEqual(resp.status_code, 200)

        b_expanded = list(
            DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=b)
        )
        self.assertTrue(b_expanded, "reset must cascade re-expansion to dependent bundle B")
        # Expanded stores the PER-UNIT bundle koef (RA-19): master TK koef = 5;
        # the bundle koef (×2) is applied at calc time, not in expanded storage.
        tk = next(x for x in b_expanded if x.kategori == "TK")
        self.assertEqual(tk.koefisien, Decimal("5.000000000000"))


class SyncReferenceEndpointTests(MasterReferenceSignatureTests):
    """B7d — manual master→project sync endpoint."""

    def _sync(self, pekerjaan_id=None):
        from django.test import RequestFactory

        from .views_api import api_sync_reference

        body = {} if pekerjaan_id is None else {"pekerjaan_id": pekerjaan_id}
        req = RequestFactory().post(
            "/sync-reference/", data=json.dumps(body), content_type="application/json"
        )
        req.user = self.owner
        return api_sync_reference(req, self.project.id)

    def _setup_stale_bundle(self):
        """A custom pekerjaan with a ref_ahsp bundle, expanded, then master edited."""
        from .models import DetailAHSPExpanded

        ahsp = self._master("A.1")
        r = self._rincian(ahsp, "BHN", "B-1", 5)
        pkj = self._custom_pekerjaan()
        row = self._bundle_row(pkj, ahsp, koef=3)
        _populate_expanded_from_raw(self.project, pkj)
        # Master corrected in place after the project expanded it.
        r.koefisien = Decimal("6")
        r.save(update_fields=["koefisien"])
        self._rincian(ahsp, "BHN", "B-2", 1)  # new component added
        return ahsp, pkj, row

    def test_sync_clears_reference_update_available(self):
        import json as _json

        _, pkj, _ = self._setup_stale_bundle()
        before = compute_project_readiness(self.project)["reference_update_available"]
        self.assertEqual(len(before), 1)

        resp = self._sync(pkj.id)
        self.assertEqual(resp.status_code, 200)
        body = _json.loads(resp.content)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["synced_pekerjaan"], [pkj.id])

        after = compute_project_readiness(self.project)["reference_update_available"]
        self.assertEqual(after, [])

    def test_sync_rebuilds_expanded_from_new_master(self):
        from .models import DetailAHSPExpanded

        ahsp, pkj, _ = self._setup_stale_bundle()
        # Before sync: expanded reflects the old master (1 component).
        before = DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=pkj).count()
        self.assertEqual(before, 1)
        self._sync(pkj.id)
        # After sync: the newly added master component is now in expanded storage
        # (codes are normalized, so assert on the grown component count).
        after = DetailAHSPExpanded.objects.filter(project=self.project, pekerjaan=pkj).count()
        self.assertEqual(after, 2)

    def test_sync_preserves_user_bundle_koefisien(self):
        _, pkj, row = self._setup_stale_bundle()
        self._sync(pkj.id)
        row.refresh_from_db()
        self.assertEqual(row.koefisien, Decimal("3.000000000000"))  # user input untouched

    def test_sync_writes_audit_entry(self):
        from .models import DetailAHSPAudit

        _, pkj, _ = self._setup_stale_bundle()
        self._sync(pkj.id)
        audit = DetailAHSPAudit.objects.filter(project=self.project, pekerjaan=pkj)
        self.assertTrue(audit.exists())
        self.assertEqual(audit.latest("id").change_summary, "Sinkronisasi referensi AHSP master")

    def test_sync_is_idempotent(self):
        import json as _json

        _, pkj, _ = self._setup_stale_bundle()
        self._sync(pkj.id)
        resp2 = self._sync(pkj.id)
        self.assertEqual(_json.loads(resp2.content)["count"], 0)  # nothing left to sync

    def test_sync_all_when_no_pekerjaan_id(self):
        import json as _json

        _, pkj, _ = self._setup_stale_bundle()
        resp = self._sync()  # no target → project-wide
        self.assertEqual(_json.loads(resp.content)["synced_pekerjaan"], [pkj.id])
