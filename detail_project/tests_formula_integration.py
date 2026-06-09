import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
    VolumeFormulaState,
)
from detail_project.views_api import (
    api_project_parameters,
    api_volume_formula_state,
)


class FormulaLifecycleIntegrationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="formula_lifecycle_user",
            email="formula-lifecycle@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Formula Lifecycle Project",
            sumber_dana="APBN",
            lokasi_project="Bandung",
            nama_client="Client",
            anggaran_owner=1000,
        )
        klas = Klasifikasi.objects.create(
            project=self.project,
            name="Klas Test",
            ordering_index=1,
        )
        sub_klas = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub Test",
            ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-INT-001",
            snapshot_uraian="Pekerjaan Integration Test",
            snapshot_satuan="m3",
            ordering_index=1,
        )
        self.factory = RequestFactory()

    def _post_project(self, view_func, payload: dict):
        request = self.factory.post(
            "/api/project/integration/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.user
        return view_func(request, self.project.id)

    def _get_project(self, view_func):
        request = self.factory.get("/api/project/integration/")
        request.user = self.user
        return view_func(request, self.project.id)

    def test_formula_lifecycle_create_param_set_formula_save_reload(self):
        create_param_response = self._post_project(api_project_parameters, {
            "label": "Panjang",
            "value": "2.5",
        })
        self.assertEqual(create_param_response.status_code, 201)
        create_param_data = json.loads(create_param_response.content.decode("utf-8"))
        self.assertTrue(create_param_data.get("ok"))
        param = create_param_data.get("parameter", {})
        param_name = str(param.get("name") or "")
        self.assertRegex(param_name, r"^bp_[1-9][0-9]*$")

        formula_raw = f"={param_name} * 3"
        save_formula_response = self._post_project(api_volume_formula_state, {
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": formula_raw,
                "is_fx": True,
            }]
        })
        self.assertEqual(save_formula_response.status_code, 200)
        save_formula_data = json.loads(save_formula_response.content.decode("utf-8"))
        self.assertTrue(save_formula_data.get("ok"))

        reload_response = self._get_project(api_volume_formula_state)
        self.assertEqual(reload_response.status_code, 200)
        reload_data = json.loads(reload_response.content.decode("utf-8"))
        self.assertTrue(reload_data.get("ok"))
        reload_items = reload_data.get("items", [])
        row = next(
            (it for it in reload_items if int(it.get("pekerjaan_id")) == self.pekerjaan.id),
            None,
        )
        self.assertIsNotNone(row)
        self.assertEqual(str(row.get("raw") or ""), formula_raw)
        self.assertTrue(bool(row.get("is_fx")))

        persisted = VolumeFormulaState.objects.get(
            project=self.project,
            pekerjaan=self.pekerjaan,
        )
        self.assertEqual(persisted.raw, formula_raw)
        self.assertTrue(persisted.is_fx)
