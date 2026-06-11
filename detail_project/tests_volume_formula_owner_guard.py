from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, SubKlasifikasi
from detail_project.views_api import api_project_parameters, api_volume_formula_state


class VolumeFormulaOwnerGuardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_formula_guard",
            email="owner-formula-guard@example.com",
            password="Secret123!",
        )
        self.non_owner = user_model.objects.create_user(
            username="non_owner_formula_guard",
            email="non-owner-formula-guard@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Formula Guard",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Guard",
            anggaran_owner=1000,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="K1", ordering_index=1)
        sub = SubKlasifikasi.objects.create(project=self.project, klasifikasi=klas, name="S1", ordering_index=1)
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CST.100",
            snapshot_uraian="Job Guard",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        self.factory = RequestFactory()

    def test_non_owner_cannot_access_project_parameters(self):
        request = self.factory.get("/api/project/parameters/")
        request.user = self.non_owner
        with self.assertRaises(Http404):
            api_project_parameters(request, self.project.id)

    def test_non_owner_cannot_access_volume_formula_state(self):
        request = self.factory.get("/api/project/volume-formula-state/")
        request.user = self.non_owner
        with self.assertRaises(Http404):
            api_volume_formula_state(request, self.project.id)
