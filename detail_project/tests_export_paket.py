"""Paket perencanaan — 4 dokumen dalam satu berkas.

Isi paket WAJIB memakai adapter yang sama dengan unduhan tunggal; kalau tidak,
paket dan dokumen satuan bisa menyimpang tanpa ada yang menyadarinya.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import Project


class PaketPerencanaanTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("paket-owner", password="x")
        self.other = get_user_model().objects.create_user("paket-other", password="x")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Paket",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas Peternakan",
            nama_konsultan_perencana="Rozan Fahriady",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2026, 1, 1),
        )

    def _url(self, fmt):
        return reverse(
            "detail_project:export_paket_perencanaan",
            kwargs={"project_id": self.project.id, "format_type": fmt},
        )

    def test_package_contains_all_four_planning_documents(self):
        from detail_project.exports.export_manager import ExportManager

        documents = ExportManager(self.project)._collect_paket_documents()

        self.assertEqual(
            [title for title, _ in documents],
            [title for title, _ in ExportManager.PAKET_PERENCANAAN],
        )
        for title, data in documents:
            with self.subTest(title=title):
                self.assertTrue(data, f"data {title} kosong")

    def test_every_format_returns_a_single_file(self):
        self.client.force_login(self.owner)
        for fmt in ("pdf", "word", "xlsx"):
            with self.subTest(fmt=fmt):
                response = self.client.get(self._url(fmt))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response["Content-Disposition"].startswith("attachment"))
                self.assertGreater(len(response.content), 5000)

    def test_unknown_format_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.get(self._url("csv"))

        self.assertEqual(response.status_code, 400)

    def test_non_owner_cannot_download_another_projects_package(self):
        """Paket memuat seluruh nilai proyek; 404 menyembunyikan keberadaannya."""
        self.client.force_login(self.other)
        response = self.client.get(self._url("pdf"))

        self.assertEqual(response.status_code, 404)

    def test_package_reuses_single_download_data(self):
        """Paket tidak boleh punya jalur data sendiri yang bisa menyimpang."""
        from detail_project.exports.export_manager import ExportManager

        manager = ExportManager(self.project)
        paket_rekap = dict(manager._collect_paket_documents())[
            "REKAPITULASI RENCANA ANGGARAN BIAYA"
        ]

        self.assertEqual(paket_rekap, manager._build_rekap_rab_data())
