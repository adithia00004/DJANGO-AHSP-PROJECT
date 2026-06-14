import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.models import HargaItemProject
from detail_project.views_api import api_list_harga_items, api_save_harga_items


class HargaItemsSaveApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_harga_items_api",
            email="owner-harga-items-api@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Harga Items API",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Harga",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()

    def _post_json(self, payload):
        request = self.factory.post(
            "/api/project/harga-items/save/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.owner
        return request

    def _get(self):
        request = self.factory.get("/api/project/harga-items/list/?canon=1")
        request.user = self.owner
        return request

    def test_save_allows_standalone_item_shown_by_list_endpoint(self):
        item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="B-0246",
            uraian="Paku Biasa",
            satuan="kg",
            kategori=HargaItemProject.KATEGORI_BAHAN,
            harga_satuan=Decimal("0"),
        )

        list_response = api_list_harga_items(self._get(), self.project.id)
        self.assertEqual(list_response.status_code, 200)
        listed = json.loads(list_response.content.decode("utf-8"))["items"]
        self.assertIn(item.id, {row["id"] for row in listed})

        save_response = api_save_harga_items(
            self._post_json({"items": [{"id": item.id, "harga_satuan": "12500.00"}]}),
            self.project.id,
        )
        self.assertEqual(save_response.status_code, 200, save_response.content.decode("utf-8"))
        body = json.loads(save_response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("updated"), 1)

        item.refresh_from_db()
        self.assertEqual(item.harga_satuan, Decimal("12500.00"))

    def test_save_harga_ignores_stale_token_and_uses_last_write_wins(self):
        item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="B-0246",
            uraian="Paku Biasa",
            satuan="kg",
            kategori=HargaItemProject.KATEGORI_BAHAN,
            harga_satuan=Decimal("0"),
        )
        response = api_save_harga_items(
            self._post_json(
                {
                    "client_updated_at": "2000-01-01T00:00:00+00:00",
                    "items": [{"id": item.id, "harga_satuan": "9999.00"}],
                }
            ),
            self.project.id,
        )

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

        item.refresh_from_db()
        self.assertEqual(item.harga_satuan, Decimal("9999.00"))

    def test_save_harga_without_token_is_last_save_wins(self):
        """Single-user policy: with no client_updated_at the save always applies,
        even when the server row is newer than the client's load time."""
        item = HargaItemProject.objects.create(
            project=self.project,
            kode_item="B-0246",
            uraian="Paku Biasa",
            satuan="kg",
            kategori=HargaItemProject.KATEGORI_BAHAN,
            harga_satuan=Decimal("0"),
        )

        response = api_save_harga_items(
            self._post_json({"items": [{"id": item.id, "harga_satuan": "7500.00"}]}),
            self.project.id,
        )

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        item.refresh_from_db()
        self.assertEqual(item.harga_satuan, Decimal("7500.00"))
