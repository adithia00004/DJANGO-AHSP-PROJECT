"""WP-B3 — Atomic Mutation Convention (B-1 / A-5) failure-injection tests.

Proves that a single save is all-or-nothing: on any error the whole transaction
rolls back (no partial write), returns 400/422/500 (never 207), and does not
leak exception detail. Covers LP-02 (upsert), JDW-01 (assign), JDW-03 (sync).
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

TEST_MIDDLEWARE = [
    m for m in settings.MIDDLEWARE if m != "config.middleware.timeout.TimeoutMiddleware"
]

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    VolumePekerjaan,
    VolumeFormulaState,
    ProjectParameter,
    ProjectComputedParameter,
    HargaItemProject,
    DetailAHSPProject,
)

User = get_user_model()


def _make_pro_user(username):
    return User.objects.create_user(
        username=username,
        password="Secret123!",
        subscription_status=User.SubscriptionStatus.PRO,
        subscription_end_date=timezone.now() + timedelta(days=30),
    )


def _make_project(owner, nama):
    return Project.objects.create(
        owner=owner,
        nama=nama,
        sumber_dana="APBN",
        lokasi_project="Jakarta",
        nama_client="Client",
        anggaran_owner=1000,
        tanggal_mulai=date(2026, 1, 1),
        tanggal_selesai=date(2026, 3, 31),
    )


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class JadwalAtomicSaveTests(TestCase):
    def setUp(self):
        self.owner = _make_pro_user("wpb3_jadwal")
        self.project = _make_project(self.owner, "WP-B3 Jadwal")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="P",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, quantity=100
        )
        self.client.force_login(self.owner)
        self.url = reverse(
            "detail_project:api_v2_assign_weekly", kwargs={"project_id": self.project.id}
        )

    def _assign(self, assignments, mode="planned"):
        return self.client.post(
            self.url,
            data=json.dumps({"mode": mode, "assignments": assignments}),
            content_type="application/json",
        )

    def test_happy_path_saves_one_row(self):
        r = self._assign([{"pekerjaan_id": self.pekerjaan.id, "week_number": 1, "proportion": 50}])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(
            PekerjaanProgressWeekly.objects.filter(project=self.project).count(), 1
        )

    def test_jdw01_invalid_item_rolls_back_valid_item(self):
        r = self._assign([
            {"pekerjaan_id": self.pekerjaan.id, "week_number": 1, "proportion": 50},
            {"pekerjaan_id": 999999, "week_number": 1, "proportion": 50},
        ])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(r.json().get("ok"))
        # All-or-nothing: the valid item must NOT survive (rolled back).
        self.assertEqual(
            PekerjaanProgressWeekly.objects.filter(project=self.project).count(), 0
        )

    def test_jdw03_sync_failure_rolls_back_and_does_not_leak(self):
        with mock.patch(
            "detail_project.views_api_tahapan_v2.sync_weekly_to_tahapan",
            side_effect=Exception("boom-secret"),
        ):
            r = self._assign([{"pekerjaan_id": self.pekerjaan.id, "week_number": 1, "proportion": 50}])
        self.assertEqual(r.status_code, 500, r.content)
        self.assertFalse(r.json().get("ok"))
        self.assertNotIn("boom-secret", r.content.decode("utf-8"))
        # Weekly writes done before sync must be rolled back too.
        self.assertEqual(
            PekerjaanProgressWeekly.objects.filter(project=self.project).count(), 0
        )


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class UpsertAtomicSaveTests(TestCase):
    def setUp(self):
        self.owner = _make_pro_user("wpb3_upsert")
        # Fresh project with NO klas/sub/pekerjaan so the upsert must CREATE them.
        self.project = _make_project(self.owner, "WP-B3 Upsert")
        self.client.force_login(self.owner)
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan", kwargs={"project_id": self.project.id}
        )

    def _payload(self):
        return {
            "klasifikasi": [
                {
                    "ordering_index": 1,
                    "name": "Klas Baru",
                    "sub": [
                        {
                            "ordering_index": 1,
                            "name": "Sub Baru",
                            "pekerjaan": [
                                {
                                    "ordering_index": 1,
                                    "source_type": "custom",
                                    "snapshot_uraian": "Pek Baru",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def test_valid_upsert_succeeds(self):
        r = self.client.post(
            self.url, data=json.dumps(self._payload()), content_type="application/json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Klasifikasi.objects.filter(project=self.project).count(), 1)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 1)

    def test_lp02_processing_error_rolls_back_everything(self):
        # Force a processing-time failure when creating the custom pekerjaan.
        with mock.patch.object(
            Pekerjaan.objects, "create", side_effect=Exception("boom")
        ):
            r = self.client.post(
                self.url, data=json.dumps(self._payload()), content_type="application/json"
            )
        # All-or-nothing: never 207, reject with 4xx/5xx, nothing persisted.
        self.assertNotEqual(r.status_code, 207)
        self.assertGreaterEqual(r.status_code, 400)
        self.assertEqual(Klasifikasi.objects.filter(project=self.project).count(), 0)
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 0)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class VolumeAtomicSyncTests(TestCase):
    """WP-B3 increment-2: VP-01 (formula sync), VP-04 (type guard),
    VP-02 (delete param dependency -> 422), VP-03 (replace validate-before-delete)."""

    def setUp(self):
        from decimal import Decimal

        self.owner = _make_pro_user("wpb3_volume")
        self.project = _make_project(self.owner, "WP-B3 Volume")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="P",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self._Decimal = Decimal
        self.client.force_login(self.owner)

    # ---- VP-01 / VP-04: formula state ----
    def _formula_url(self):
        return reverse(
            "detail_project:api_volume_formula_state", kwargs={"project_id": self.project.id}
        )

    def test_vp01_partial_invalid_rejects_and_rolls_back(self):
        # Existing formula sidecar that a partial save would otherwise delete.
        VolumeFormulaState.objects.create(
            project=self.project, pekerjaan=self.pekerjaan, raw="=10", is_fx=True
        )
        r = self.client.post(
            self._formula_url(),
            data=json.dumps({"items": [
                {"pekerjaan_id": self.pekerjaan.id, "raw": "", "is_fx": False},  # would delete
                {"pekerjaan_id": 999999, "raw": "=5", "is_fx": True},            # error: not found
            ]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(r.json().get("ok"))
        # Atomic: the existing sidecar must NOT have been deleted.
        self.assertTrue(
            VolumeFormulaState.objects.filter(project=self.project, pekerjaan=self.pekerjaan).exists()
        )

    def test_vp04_malformed_item_is_400_not_500(self):
        r = self.client.post(
            self._formula_url(),
            data=json.dumps({"items": [None, "x"]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content)

    def test_quantity_mixed_validity_rejects_whole_batch(self):
        url = reverse(
            "detail_project:api_save_volume_pekerjaan",
            kwargs={"project_id": self.project.id},
        )
        r = self.client.post(
            url,
            data=json.dumps({
                "items": [
                    {"pekerjaan_id": self.pekerjaan.id, "quantity": "12.5"},
                    {"pekerjaan_id": 999999, "quantity": "3"},
                ]
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(r.json().get("ok"))
        self.assertFalse(
            VolumePekerjaan.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan,
            ).exists()
        )

    def test_formula_sync_stale_marker_is_ignored(self):
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            raw="=1",
            is_fx=True,
        )
        r = self.client.post(
            self._formula_url(),
            data=json.dumps({
                "last_sync_at": "2000-01-01T00:00:00+00:00",
                "items": [
                    {
                        "pekerjaan_id": self.pekerjaan.id,
                        "raw": "=2",
                        "is_fx": True,
                    }
                ],
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(
            VolumeFormulaState.objects.get(
                project=self.project,
                pekerjaan=self.pekerjaan,
            ).raw,
            "=2",
        )

    # ---- VP-02: delete parameter dependency guard ----
    def _param_delete_url(self, pid):
        return reverse(
            "detail_project:api_project_parameter_detail",
            kwargs={"project_id": self.project.id, "param_id": pid},
        )

    def test_vp02_delete_param_in_use_returns_422(self):
        p = ProjectParameter.objects.create(
            project=self.project, name="bp_1", value=self._Decimal("5"), label="Panjang"
        )
        ProjectComputedParameter.objects.create(
            project=self.project, name="cp_1", expression="bp_1 * 2", label="Area"
        )
        r = self.client.delete(self._param_delete_url(p.id))
        self.assertEqual(r.status_code, 422, r.content)
        body = r.json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("code"), "parameter_in_use")
        self.assertTrue(body.get("usage"))
        self.assertTrue(ProjectParameter.objects.filter(id=p.id).exists())

    def test_vp02_delete_unused_param_succeeds(self):
        p = ProjectParameter.objects.create(
            project=self.project, name="bp_2", value=self._Decimal("3"), label="Lebar"
        )
        r = self.client.delete(self._param_delete_url(p.id))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(ProjectParameter.objects.filter(id=p.id).exists())

    def test_vp02_token_guard_does_not_false_match_prefix(self):
        # bp_3 referenced; deleting bp_30 (not referenced) must succeed.
        ProjectParameter.objects.create(project=self.project, name="bp_3", value=self._Decimal("1"))
        p30 = ProjectParameter.objects.create(project=self.project, name="bp_30", value=self._Decimal("1"))
        ProjectComputedParameter.objects.create(
            project=self.project, name="cp_2", expression="bp_3 + 1", label="X"
        )
        r = self.client.delete(self._param_delete_url(p30.id))
        self.assertEqual(r.status_code, 200, r.content)

    # ---- VP-03: replace sync validate-before-delete ----
    def test_vp03_replace_with_invalid_name_does_not_delete_existing(self):
        ProjectParameter.objects.create(
            project=self.project, name="bp_1", value=self._Decimal("5"), label="Lama"
        )
        url = reverse(
            "detail_project:api_project_parameters_sync", kwargs={"project_id": self.project.id}
        )
        r = self.client.post(
            url,
            data=json.dumps({"mode": "replace", "parameters": {
                "bp_2": {"value": 10},
                "BAD NAME": {"value": 1},
            }}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 422, r.content)
        # Validate-before-delete: the existing parameter must survive.
        self.assertTrue(ProjectParameter.objects.filter(project=self.project, name="bp_1").exists())
        self.assertFalse(ProjectParameter.objects.filter(project=self.project, name="bp_2").exists())

    def test_vp03_replace_all_valid_succeeds(self):
        url = reverse(
            "detail_project:api_project_parameters_sync", kwargs={"project_id": self.project.id}
        )
        r = self.client.post(
            url,
            data=json.dumps({"mode": "replace", "parameters": {"bp_1": {"value": 10}}}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(ProjectParameter.objects.filter(project=self.project, name="bp_1").exists())

    def test_vp03_stale_marker_is_ignored(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value=self._Decimal("5"),
            label="Lama",
        )
        url = reverse(
            "detail_project:api_project_parameters_sync",
            kwargs={"project_id": self.project.id},
        )
        r = self.client.post(
            url,
            data=json.dumps({
                "mode": "replace",
                "last_sync_at": "2000-01-01T00:00:00+00:00",
                "parameters": {"bp_1": {"value": 10, "label": "Baru"}},
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(
            ProjectParameter.objects.get(project=self.project, name="bp_1").value,
            self._Decimal("10"),
        )


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class HargaAtomicSaveTests(TestCase):
    """WP-B3 increment-3: Harga Items save — HI-06 (reject negative),
    HI-01 (null = belum diisi, not 0), atomic all-or-nothing (no 207)."""

    def setUp(self):
        self.owner = _make_pro_user("wpb3_harga")
        self.project = _make_project(self.owner, "WP-B3 Harga")
        self.item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="SMN",
            kategori="BHN",
            uraian="Semen",
            satuan="zak",
            harga_satuan=Decimal("100"),
        )
        self.client.force_login(self.owner)
        self.url = reverse(
            "detail_project:api_save_harga_items", kwargs={"project_id": self.project.id}
        )

    def _save(self, items, **extra):
        body = {"items": items}
        body.update(extra)
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_happy_save_updates_price(self):
        r = self._save([{"id": self.item.id, "harga_satuan": "250"}])
        self.assertEqual(r.status_code, 200, r.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("250.00"))

    def test_hi06_negative_price_rejected_atomically(self):
        r = self._save([{"id": self.item.id, "harga_satuan": "-5"}])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(r.json().get("ok"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("100"))  # unchanged

    def test_hi01_null_preserved_as_unfilled(self):
        r = self._save([{"id": self.item.id, "harga_satuan": None}])
        self.assertEqual(r.status_code, 200, r.content)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.harga_satuan)

    def test_hi01_empty_string_preserved_as_unfilled(self):
        r = self._save([{"id": self.item.id, "harga_satuan": ""}])
        self.assertEqual(r.status_code, 200, r.content)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.harga_satuan)

    def test_atomic_partial_error_no_207_no_partial(self):
        r = self._save([
            {"id": self.item.id, "harga_satuan": "999"},
            {"id": 999999, "harga_satuan": "5"},  # not editable -> error
        ])
        self.assertNotEqual(r.status_code, 207)
        self.assertEqual(r.status_code, 400, r.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("100"))  # rolled back, not 999

    def test_stale_token_is_ignored_last_write_wins(self):
        r = self._save(
            [{"id": self.item.id, "harga_satuan": "321"}],
            client_updated_at="2000-01-01T00:00:00+00:00",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.harga_satuan, Decimal("321.00"))


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class TemplateSaveAtomicTests(TestCase):
    """WP-B3 increment-4: Template AHSP save — TA-01 (reject negative koefisien,
    0 allowed) + atomic all-or-nothing (already enforced by validate-before-save)."""

    def setUp(self):
        self.owner = _make_pro_user("wpb3_template")
        self.project = _make_project(self.owner, "WP-B3 Template")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="P",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self.client.force_login(self.owner)
        self.url = reverse(
            "detail_project:api_save_detail_ahsp_for_pekerjaan",
            kwargs={"project_id": self.project.id, "pekerjaan_id": self.pekerjaan.id},
        )

    def _save(self, rows):
        return self.client.post(
            self.url, data=json.dumps({"rows": rows}), content_type="application/json"
        )

    def _detail_count(self):
        return DetailAHSPProject.objects.filter(
            project=self.project, pekerjaan=self.pekerjaan
        ).count()

    def test_happy_save_creates_detail(self):
        r = self._save([{"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "2.5"}])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._detail_count(), 1)

    def test_ta01_negative_koef_rejected_atomically(self):
        r = self._save([
            {"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "2.5"},
            {"kategori": "BHN", "kode": "PSR", "uraian": "Pasir", "koefisien": "-1"},
        ])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(r.json().get("ok"))
        # All-or-nothing: the valid row must NOT be saved either.
        self.assertEqual(self._detail_count(), 0)

    def test_ta01_zero_koef_allowed(self):
        r = self._save([{"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "0"}])
        self.assertEqual(r.status_code, 200, r.content)

    def test_stale_token_is_ignored_last_write_wins(self):
        r = self.client.post(
            self.url,
            data=json.dumps({
                "client_updated_at": "2000-01-01T00:00:00+00:00",
                "rows": [
                    {
                        "kategori": "BHN",
                        "kode": "SMN",
                        "uraian": "Semen",
                        "koefisien": "4",
                    }
                ],
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._detail_count(), 1)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class DetailGabunganAtomicSaveTests(TestCase):
    """WP-B3 follow-up: Detail AHSP gabungan save (api_save_detail_ahsp_gabungan)
    must be all-or-nothing across every pekerjaan in the payload — no partial 207,
    and an invalid row in one pekerjaan must not persist another pekerjaan."""

    def setUp(self):
        self.owner = _make_pro_user("wpb3_gabungan")
        self.project = _make_project(self.owner, "WP-B3 Gabungan")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self.pkj_a = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="A", snapshot_satuan="m2", ordering_index=1,
        )
        self.pkj_b = Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_uraian="B", snapshot_satuan="m2", ordering_index=2,
        )
        self.client.force_login(self.owner)
        self.url = reverse(
            "detail_project:api_save_detail_ahsp_gabungan",
            kwargs={"project_id": self.project.id},
        )

    def _save(self, items):
        return self.client.post(
            self.url, data=json.dumps({"items": items}), content_type="application/json"
        )

    def _count(self, pkj):
        return DetailAHSPProject.objects.filter(project=self.project, pekerjaan=pkj).count()

    def test_happy_save_creates_detail_for_all(self):
        r = self._save([
            {"pekerjaan_id": self.pkj_a.id, "rows": [
                {"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "2.5"}]},
            {"pekerjaan_id": self.pkj_b.id, "rows": [
                {"kategori": "BHN", "kode": "PSR", "uraian": "Pasir", "koefisien": "1"}]},
        ])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._count(self.pkj_a), 1)
        self.assertEqual(self._count(self.pkj_b), 1)

    def test_invalid_row_rejects_whole_batch_no_207(self):
        r = self._save([
            {"pekerjaan_id": self.pkj_a.id, "rows": [
                {"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "2.5"}]},
            {"pekerjaan_id": self.pkj_b.id, "rows": [
                {"kategori": "BHN", "kode": "PSR", "uraian": "Pasir", "koefisien": "-1"}]},
        ])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertNotEqual(r.status_code, 207)
        self.assertFalse(r.json().get("ok"))
        # All-or-nothing: the valid pekerjaan A must NOT be persisted either.
        self.assertEqual(self._count(self.pkj_a), 0)
        self.assertEqual(self._count(self.pkj_b), 0)

    def test_invalid_row_does_not_wipe_existing_detail(self):
        # Seed A with existing detail, then a failing batch must leave it intact.
        ok = self._save([
            {"pekerjaan_id": self.pkj_a.id, "rows": [
                {"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "2.5"}]},
        ])
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(self._count(self.pkj_a), 1)
        bad = self._save([
            {"pekerjaan_id": self.pkj_a.id, "rows": [
                {"kategori": "BHN", "kode": "SMN", "uraian": "Semen", "koefisien": "bukan-angka"}]},
        ])
        self.assertEqual(bad.status_code, 400, bad.content)
        # The delete-then-recreate must have rolled back; existing detail survives.
        self.assertEqual(self._count(self.pkj_a), 1)
