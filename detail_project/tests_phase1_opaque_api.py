import json
from unittest import SkipTest

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings

from dashboard.models import Project
from detail_project import models as detail_models

if not hasattr(detail_models, "ProjectComputedParameter"):
    raise SkipTest(
        "Opaque parameter API masih WIP; model ProjectComputedParameter belum tersedia."
    )

from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    ProjectComputedParameter,
    ProjectParameter,
    SubKlasifikasi,
    VolumeFormulaState,
)
from detail_project.views_api import (
    api_project_computed_parameters,
    api_project_computed_parameters_sync,
    api_project_parameter_detail,
    api_project_parameters,
    api_project_parameters_sync,
    api_volume_formula_state,
)


class Phase1OpaqueApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="phase1_opaque_user",
            email="phase1-opaque@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Phase 1 Opaque",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )
        self.klasifikasi = Klasifikasi.objects.create(
            project=self.project,
            name="Klasifikasi Test",
            ordering_index=1,
        )
        self.sub_klasifikasi = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=self.klasifikasi,
            name="Sub Test",
            ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-001",
            snapshot_uraian="Pekerjaan Test Formula",
            snapshot_satuan="m3",
            ordering_index=1,
        )
        self.factory = RequestFactory()

    def _post_json(self, path: str, payload: dict):
        request = self.factory.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.user
        return request

    def _put_json(self, path: str, payload: dict):
        request = self.factory.put(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.user
        return request

    def _delete(self, path: str):
        request = self.factory.delete(path)
        request.user = self.user
        return request

    def _get(self, path: str):
        request = self.factory.get(path)
        request.user = self.user
        return request

    def test_create_base_parameter_uses_server_generated_bp_name(self):
        request = self._post_json(
            "/api/project/parameters/",
            {"name": "panjang_dinding", "label": "Panjang", "value": 10},
        )
        response = api_project_parameters(request, self.project.id)
        self.assertEqual(response.status_code, 201)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertRegex(body["parameter"]["name"], r"^bp_[1-9][0-9]*$")

    def test_create_computed_parameter_uses_server_generated_cp_name(self):
        request = self._post_json(
            "/api/project/computed-parameters/",
            {"name": "luas", "label": "Luas", "expression": "bp_1 * 2"},
        )
        response = api_project_computed_parameters(request, self.project.id)
        self.assertEqual(response.status_code, 201)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertRegex(body["computed_parameter"]["name"], r"^cp_[1-9][0-9]*$")

    def test_sync_base_parameters_invalid_name_rejects_atomically(self):
        # WP-B3 / VP-03 (supersedes old partial-success-with-warnings): an invalid
        # item rejects the WHOLE replace sync (422); nothing is created or deleted.
        request = self._post_json(
            "/api/project/parameters/sync/",
            {
                "mode": "replace",
                "parameters": {
                    "bp_1": {"value": 7.25, "label": "Valid"},
                    "diskon": {"value": -2, "label": "Invalid Legacy"},
                },
            },
        )
        response = api_project_parameters_sync(request, self.project.id)
        self.assertEqual(response.status_code, 422)
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(body.get("errors"))
        # Validate-before-delete: the valid item is NOT created when payload is partly invalid.
        self.assertFalse(ProjectParameter.objects.filter(project=self.project, name="bp_1").exists())
        self.assertFalse(ProjectParameter.objects.filter(project=self.project, name="diskon").exists())

    def test_sync_computed_parameters_invalid_name_rejects_atomically(self):
        # WP-B3 / VP-03 (supersedes old partial-success-with-warnings).
        request = self._post_json(
            "/api/project/computed-parameters/sync/",
            {
                "mode": "replace",
                "computed_parameters": {
                    "cp_1": {"label": "Valid", "expression": "bp_1 * 2"},
                    "total_luas": {"label": "Invalid Legacy", "expression": "bp_1 * 3"},
                },
            },
        )
        response = api_project_computed_parameters_sync(request, self.project.id)
        self.assertEqual(response.status_code, 422)
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(body.get("errors"))
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project, name="cp_1").exists())
        self.assertFalse(ProjectComputedParameter.objects.filter(project=self.project, name="total_luas").exists())

    def test_sync_base_ignores_stale_marker_and_uses_last_write_wins(self):
        ProjectParameter.objects.create(
            project=self.project,
            name="bp_1",
            value="1",
            label="Panjang",
        )
        request = self._post_json(
            "/api/project/parameters/sync/",
            {
                "mode": "replace",
                "last_sync_at": "2000-01-01T00:00:00+00:00",
                "parameters": {"bp_1": {"value": 2, "label": "Panjang"}},
            },
        )
        response = api_project_parameters_sync(request, self.project.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ProjectParameter.objects.get(project=self.project, name="bp_1").value,
            2,
        )
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

    def test_formula_state_get_returns_updated_at_and_synced_at(self):
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            raw="=bp_1 * 2",
            is_fx=True,
        )

        request = self._get("/api/project/volume-formula-state/")
        response = api_volume_formula_state(request, self.project.id)
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertIn("synced_at", body)
        self.assertEqual(len(body.get("items", [])), 1)
        row = body["items"][0]
        self.assertEqual(row["pekerjaan_id"], self.pekerjaan.id)
        self.assertEqual(row["raw"], "=bp_1 * 2")
        self.assertTrue(row["is_fx"])
        self.assertTrue(row.get("updated_at"))

    def test_formula_state_ignores_stale_marker_and_uses_last_write_wins(self):
        VolumeFormulaState.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            raw="=bp_1 * 2",
            is_fx=True,
        )

        request = self._post_json(
            "/api/project/volume-formula-state/",
            {
                "last_sync_at": "2000-01-01T00:00:00+00:00",
                "items": [
                    {
                        "pekerjaan_id": self.pekerjaan.id,
                        "raw": "=bp_1 * 3",
                        "is_fx": True,
                    }
                ],
            },
        )
        response = api_volume_formula_state(request, self.project.id)
        self.assertEqual(response.status_code, 200)
        state = VolumeFormulaState.objects.get(
            project=self.project,
            pekerjaan=self.pekerjaan,
        )
        self.assertEqual(state.raw, "=bp_1 * 3")

        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

    def test_model_validation_rejects_cross_prefix_names(self):
        with self.assertRaises(ValidationError):
            ProjectParameter.objects.create(
                project=self.project,
                name="cp_1",
                value="1",
                label="Invalid",
            )
        with self.assertRaises(ValidationError):
            ProjectComputedParameter.objects.create(
                project=self.project,
                name="bp_1",
                expression="bp_1 * 2",
                label="Invalid",
            )

    def test_server_counter_is_monotonic_after_delete(self):
        req1 = self._post_json("/api/project/parameters/", {"label": "P1", "value": 1})
        res1 = api_project_parameters(req1, self.project.id)
        body1 = json.loads(res1.content.decode("utf-8"))
        first_name = body1["parameter"]["name"]

        req2 = self._post_json("/api/project/parameters/", {"label": "P2", "value": 2})
        res2 = api_project_parameters(req2, self.project.id)
        body2 = json.loads(res2.content.decode("utf-8"))
        second_name = body2["parameter"]["name"]

        self.assertEqual(first_name, "bp_1")
        self.assertEqual(second_name, "bp_2")

        ProjectParameter.objects.filter(project=self.project, name="bp_2").delete()

        req3 = self._post_json("/api/project/parameters/", {"label": "P3", "value": 3})
        res3 = api_project_parameters(req3, self.project.id)
        body3 = json.loads(res3.content.decode("utf-8"))
        self.assertEqual(body3["parameter"]["name"], "bp_3")

    def test_c1_multi_tab_create_returns_different_codes(self):
        req_a = self._post_json("/api/project/parameters/", {"label": "Tab A", "value": 10})
        req_b = self._post_json("/api/project/parameters/", {"label": "Tab B", "value": 20})
        res_a = api_project_parameters(req_a, self.project.id)
        res_b = api_project_parameters(req_b, self.project.id)
        body_a = json.loads(res_a.content.decode("utf-8"))
        body_b = json.loads(res_b.content.decode("utf-8"))

        self.assertEqual(res_a.status_code, 201)
        self.assertEqual(res_b.status_code, 201)
        self.assertNotEqual(body_a["parameter"]["name"], body_b["parameter"]["name"])
        self.assertRegex(body_a["parameter"]["name"], r"^bp_[1-9][0-9]*$")
        self.assertRegex(body_b["parameter"]["name"], r"^bp_[1-9][0-9]*$")

    def test_ac14_edit_label_keeps_opaque_code(self):
        req_create = self._post_json("/api/project/parameters/", {"label": "Awal", "value": 3})
        res_create = api_project_parameters(req_create, self.project.id)
        body_create = json.loads(res_create.content.decode("utf-8"))
        param_id = body_create["parameter"]["id"]
        original_name = body_create["parameter"]["name"]

        req_update = self._put_json(
            f"/api/project/{self.project.id}/parameters/{param_id}/",
            {"label": "Label Baru"},
        )
        res_update = api_project_parameter_detail(req_update, self.project.id, param_id)
        self.assertEqual(res_update.status_code, 200)
        body_update = json.loads(res_update.content.decode("utf-8"))
        self.assertEqual(body_update["parameter"]["name"], original_name)

        row = ProjectParameter.objects.get(id=param_id, project=self.project)
        self.assertEqual(row.name, original_name)
        self.assertEqual(row.label, "Label Baru")

    def test_c3_replace_sync_keeps_database_consistent(self):
        req_first = self._post_json(
            "/api/project/parameters/sync/",
            {
                "mode": "replace",
                "parameters": {
                    "bp_1": {"value": 1, "label": "A"},
                    "bp_2": {"value": 2, "label": "B"},
                },
            },
        )
        req_second = self._post_json(
            "/api/project/parameters/sync/",
            {
                "mode": "replace",
                "parameters": {
                    "bp_2": {"value": 22, "label": "B2"},
                    "bp_3": {"value": 3, "label": "C"},
                },
            },
        )
        res_first = api_project_parameters_sync(req_first, self.project.id)
        res_second = api_project_parameters_sync(req_second, self.project.id)
        self.assertEqual(res_first.status_code, 200)
        self.assertEqual(res_second.status_code, 200)

        rows = list(
            ProjectParameter.objects.filter(project=self.project)
            .order_by("name")
            .values_list("name", "label", "value")
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "bp_2")
        self.assertEqual(rows[0][1], "B2")
        # ProjectParameter.value kini 12dp (expand precision koef/param, migrasi 0043/0044).
        self.assertEqual(str(rows[0][2]), "22.000000000000")
        self.assertEqual(rows[1][0], "bp_3")
        self.assertEqual(rows[1][1], "C")
        self.assertEqual(str(rows[1][2]), "3.000000000000")

    def test_ac16_delete_then_reload_does_not_return_parameter(self):
        req_create = self._post_json("/api/project/parameters/", {"label": "To Delete", "value": 8})
        res_create = api_project_parameters(req_create, self.project.id)
        body_create = json.loads(res_create.content.decode("utf-8"))
        param_id = body_create["parameter"]["id"]

        req_delete = self._delete(f"/api/project/{self.project.id}/parameters/{param_id}/")
        res_delete = api_project_parameter_detail(req_delete, self.project.id, param_id)
        self.assertEqual(res_delete.status_code, 200)

        req_get = self._get(f"/api/project/{self.project.id}/parameters/")
        res_get = api_project_parameters(req_get, self.project.id)
        self.assertEqual(res_get.status_code, 200)
        body_get = json.loads(res_get.content.decode("utf-8"))
        names = [p.get("name") for p in body_get.get("parameters", [])]
        self.assertNotIn(body_create["parameter"]["name"], names)

    @override_settings(OPAQUE_ID_ENABLED=False)
    def test_r1_feature_flag_off_create_uses_legacy_descriptive_name(self):
        request = self._post_json(
            "/api/project/parameters/",
            {"label": "Panjang Dinding", "value": 10},
        )
        response = api_project_parameters(request, self.project.id)
        self.assertEqual(response.status_code, 201)
        body = json.loads(response.content.decode("utf-8"))
        name = body["parameter"]["name"]
        self.assertEqual(name, "panjang_dinding")
        self.assertNotRegex(name, r"^bp_[1-9][0-9]*$")

        req_cp = self._post_json(
            "/api/project/computed-parameters/",
            {"label": "Luas Dinding", "expression": "panjang_dinding * 2"},
        )
        res_cp = api_project_computed_parameters(req_cp, self.project.id)
        self.assertEqual(res_cp.status_code, 201)
        body_cp = json.loads(res_cp.content.decode("utf-8"))
        cp_name = body_cp["computed_parameter"]["name"]
        self.assertEqual(cp_name, "luas_dinding")
        self.assertNotRegex(cp_name, r"^cp_[1-9][0-9]*$")

    @override_settings(OPAQUE_ID_ENABLED=False)
    def test_r1_feature_flag_off_sync_accepts_legacy_names(self):
        req_sync_base = self._post_json(
            "/api/project/parameters/sync/",
            {
                "mode": "replace",
                "parameters": {
                    "panjang_dinding": {"value": 7.5, "label": "Panjang Dinding"},
                },
            },
        )
        res_sync_base = api_project_parameters_sync(req_sync_base, self.project.id)
        self.assertEqual(res_sync_base.status_code, 200)
        body_base = json.loads(res_sync_base.content.decode("utf-8"))
        self.assertEqual(body_base.get("created"), 1)
        self.assertEqual(body_base.get("warnings"), [])
        self.assertTrue(
            ProjectParameter.objects.filter(project=self.project, name="panjang_dinding").exists()
        )

        req_sync_cp = self._post_json(
            "/api/project/computed-parameters/sync/",
            {
                "mode": "replace",
                "computed_parameters": {
                    "luas_dinding": {"label": "Luas", "expression": "panjang_dinding * 2"},
                },
            },
        )
        res_sync_cp = api_project_computed_parameters_sync(req_sync_cp, self.project.id)
        self.assertEqual(res_sync_cp.status_code, 200)
        body_cp = json.loads(res_sync_cp.content.decode("utf-8"))
        self.assertEqual(body_cp.get("created"), 1)
        self.assertEqual(body_cp.get("warnings"), [])
        self.assertTrue(
            ProjectComputedParameter.objects.filter(project=self.project, name="luas_dinding").exists()
        )
