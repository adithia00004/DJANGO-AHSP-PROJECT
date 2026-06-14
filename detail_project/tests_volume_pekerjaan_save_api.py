import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
    VolumeFormulaState,
    VolumePekerjaan,
)
from detail_project.views_api import (
    api_save_volume_pekerjaan,
    api_volume_formula_state,
    build_volume_list_payload,
)


class SaveVolumePekerjaanApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_volume_api",
            email="owner-volume-api@example.com",
            password="Secret123!",
        )
        self.non_owner = user_model.objects.create_user(
            username="non_owner_volume_api",
            email="non-owner-volume-api@example.com",
            password="Secret123!",
        )

        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Volume API",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Volume",
            anggaran_owner=1000,
        )
        self.other_project = Project.objects.create(
            owner=self.non_owner,
            nama="Other Project Volume API",
            sumber_dana="APBN",
            lokasi_project="Bandung",
            nama_client="Client Other",
            anggaran_owner=1000,
        )

        klas = Klasifikasi.objects.create(project=self.project, name="K1", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S1", ordering_index=1)
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CST.001",
            snapshot_uraian="Pekerjaan 1",
            snapshot_satuan="m2",
            ordering_index=1,
        )

        other_klas = Klasifikasi.objects.create(project=self.other_project, name="K1", ordering_index=1)
        other_sub = SubKlasifikasi.objects.create(
            project=self.other_project,
            klasifikasi=other_klas,
            name="S1",
            ordering_index=1,
        )
        self.foreign_pekerjaan = Pekerjaan.objects.create(
            project=self.other_project,
            sub_klasifikasi=other_sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CST.999",
            snapshot_uraian="Pekerjaan Foreign",
            snapshot_satuan="m2",
            ordering_index=1,
        )

        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_save_volume_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

    def _post(self, payload, *, user=None):
        request = self.factory.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = user or self.owner
        return api_save_volume_pekerjaan(request, self.project.id)

    def test_accepts_zero_and_quantizes_half_up(self):
        response = self._post(
            [
                {"pekerjaan_id": self.pekerjaan.id, "quantity": "1.2345"},
            ]
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))

        saved = VolumePekerjaan.objects.get(project=self.project, pekerjaan=self.pekerjaan)
        self.assertEqual(saved.quantity, Decimal("1.235"))

        response_zero = self._post(
            [
                {"pekerjaan_id": self.pekerjaan.id, "quantity": "0"},
            ]
        )
        self.assertEqual(response_zero.status_code, 200, response_zero.content.decode("utf-8"))
        saved.refresh_from_db()
        self.assertEqual(saved.quantity, Decimal("0.000"))

    def test_volume_list_marks_explicit_zero_as_filled(self):
        before = build_volume_list_payload(self.project)
        before_item = before["items"][0]
        self.assertEqual(before_item["quantity"], "0.000")
        self.assertFalse(before_item["has_quantity"])
        self.assertIsNone(before_item["updated_at"])

        response_zero = self._post(
            [
                {"pekerjaan_id": self.pekerjaan.id, "quantity": "0"},
            ]
        )
        self.assertEqual(response_zero.status_code, 200, response_zero.content.decode("utf-8"))

        after = build_volume_list_payload(self.project)
        after_item = after["items"][0]
        self.assertEqual(after_item["quantity"], "0.000")
        self.assertTrue(after_item["has_quantity"])
        self.assertTrue(after_item["updated_at"])

    def test_volume_formula_state_deletes_stale_sidecar_for_numeric_input(self):
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            raw="=1+1",
            is_fx=True,
        )
        url = reverse(
            "detail_project:api_volume_formula_state",
            kwargs={"project_id": self.project.id},
        )
        request = self.factory.post(
            url,
            data=json.dumps({
                "items": [
                    {
                        "pekerjaan_id": self.pekerjaan.id,
                        "raw": "2",
                        "is_fx": False,
                    }
                ]
            }),
            content_type="application/json",
        )
        request.user = self.owner

        response = api_volume_formula_state(request, self.project.id)

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body.get("deleted"), 1)
        self.assertFalse(
            VolumeFormulaState.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan,
            ).exists()
        )

    def test_volume_frontend_flushes_pending_inputs_before_save(self):
        with open(
            "detail_project/static/detail_project/js/volume_pekerjaan.js",
            encoding="utf-8",
        ) as handle:
            script = handle.read()

        save_idx = script.index("async function saveDirty")
        flush_idx = script.index("flushPendingQtyInputs();", save_idx)
        posting_idx = script.index("const postingIds = Array.from(dirtySet.values());", save_idx)
        self.assertLess(flush_idx, posting_idx)

    def test_volume_flush_commits_pending_debounced_edits(self):
        # Regression: a fast save (within the 120ms input debounce) must NOT drop edits.
        # bindRow records each keystroke in pendingInputIds; flush must commit those before
        # reading dirtySet. The old guard compared input.value vs rawInputById (updated
        # eagerly on every keystroke -> always equal -> skipped), silently losing
        # recently-typed rows on reload.
        with open(
            "detail_project/static/detail_project/js/volume_pekerjaan.js",
            encoding="utf-8",
        ) as handle:
            script = handle.read()

        # Each keystroke marks the row as pending (uncommitted debounce).
        self.assertIn("pendingInputIds.add(id)", script)
        # Committing the edit clears the pending mark.
        self.assertIn("pendingInputIds.delete(Number(id))", script)
        # flush must drive off pendingInputIds, not the eagerly-updated rawInputById.
        flush_idx = script.index("function flushPendingQtyInputs()")
        flush_body = script[flush_idx: flush_idx + 1000]
        self.assertIn("pendingInputIds", flush_body)

    def test_frontend_does_not_apply_stale_formula_over_newer_volume(self):
        with open(
            "detail_project/static/detail_project/js/volume_pekerjaan.js",
            encoding="utf-8",
        ) as handle:
            script = handle.read()

        self.assertIn("function isFormulaStateFreshForVolume", script)
        self.assertIn("formulaMs >= volumeMs", script)
        self.assertIn("volUpdatedMap[id]", script)
        self.assertIn("raw: isFx ? raw : ''", script)

    def test_rejects_negative_quantity(self):
        response = self._post(
            [
                {"pekerjaan_id": self.pekerjaan.id, "quantity": "-5"},
            ]
        )
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        paths = [e.get("path") for e in body.get("errors", [])]
        self.assertIn("[0].quantity", paths)
        self.assertFalse(VolumePekerjaan.objects.filter(project=self.project, pekerjaan=self.pekerjaan).exists())

    def test_rejects_foreign_project_pekerjaan_id(self):
        response = self._post(
            [
                {"pekerjaan_id": self.foreign_pekerjaan.id, "quantity": "2"},
            ]
        )
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        paths = [e.get("path") for e in body.get("errors", [])]
        self.assertIn("[0].pekerjaan_id", paths)

    def test_rejects_non_object_item_in_payload(self):
        response = self._post(["invalid"])
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        paths = [e.get("path") for e in body.get("errors", [])]
        self.assertIn("[0]", paths)

    def test_mixed_validity_rejects_whole_batch_atomically(self):
        response = self._post(
            [
                {"pekerjaan_id": self.pekerjaan.id, "quantity": "2.5"},
                {"pekerjaan_id": self.foreign_pekerjaan.id, "quantity": "3"},
            ]
        )
        self.assertEqual(response.status_code, 400, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(body.get("errors"))
        self.assertFalse(
            VolumePekerjaan.objects.filter(
                project=self.project,
                pekerjaan=self.pekerjaan,
            ).exists()
        )

    def test_non_owner_cannot_save_foreign_project(self):
        with self.assertRaises(Http404):
            self._post([], user=self.non_owner)
