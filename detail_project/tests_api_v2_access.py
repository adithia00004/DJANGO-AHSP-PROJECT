from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.views_api import (
    api_chart_data,
    api_kurva_s_data,
    api_kurva_s_harga_data,
    api_rekap_kebutuhan_weekly,
)


class ApiV2OwnershipAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_v2_access",
            email="owner-v2@example.com",
            password="Secret123!",
        )
        self.non_owner = user_model.objects.create_user(
            username="non_owner_v2_access",
            email="non-owner-v2@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Owner",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )

    def test_api_kurva_s_data_blocks_non_owner(self):
        request = self.factory.get("/detail_project/api/v2/project/kurva-s-data/")
        request.user = self.non_owner
        response = api_kurva_s_data(request, self.project.id)

        self.assertEqual(response.status_code, 404)

    def test_api_kurva_s_harga_data_blocks_non_owner(self):
        request = self.factory.get("/detail_project/api/v2/project/kurva-s-harga/")
        request.user = self.non_owner
        response = api_kurva_s_harga_data(request, self.project.id)

        self.assertEqual(response.status_code, 404)

    def test_api_rekap_kebutuhan_weekly_blocks_non_owner(self):
        request = self.factory.get("/detail_project/api/v2/project/rekap-kebutuhan-weekly/")
        request.user = self.non_owner
        response = api_rekap_kebutuhan_weekly(request, self.project.id)

        self.assertEqual(response.status_code, 404)

    def test_api_chart_data_blocks_non_owner(self):
        request = self.factory.get("/detail_project/api/v2/project/chart-data/")
        request.user = self.non_owner
        response = api_chart_data(request, self.project.id)

        self.assertEqual(response.status_code, 404)
