"""WP-B5 inc-B5b — canonical project-identity provider tests."""
import os
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project
from detail_project.exports.identity import get_project_identity

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


class ProjectIdentityProviderTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="b5b-owner", password="x"
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Uji",
            sumber_dana="APBD",
            lokasi_project="Kota Bandung",
            nama_client="Dinas PU",
            ket_project1="Keterangan A",
            ket_project2="Keterangan B",
            jabatan_client="PA",
            instansi_client="Pemkot Bandung",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2027, 3, 1),
            tanggal_selesai=date(2027, 8, 1),
        )

    def test_reads_real_dashboard_fields(self):
        ident = get_project_identity(self.project)
        self.assertEqual(ident["name"], "Proyek Uji")
        # location previously returned '-' (read non-existent 'lokasi' field).
        self.assertEqual(ident["location"], "Kota Bandung")
        self.assertNotEqual(ident["location"], "-")
        self.assertEqual(ident["owner"], "Dinas PU")
        self.assertEqual(ident["client"], "Dinas PU")
        self.assertEqual(ident["sumber_dana"], "APBD")
        self.assertEqual(ident["anggaran_owner"], Decimal("1000000"))
        self.assertEqual(ident["ket_project1"], "Keterangan A")
        self.assertEqual(ident["ket_project2"], "Keterangan B")
        self.assertEqual(ident["jabatan_client"], "PA")
        self.assertEqual(ident["instansi_client"], "Pemkot Bandung")

    def test_year_comes_from_tahun_project(self):
        self.project.refresh_from_db()
        ident = get_project_identity(self.project)
        if self.project.tahun_project:
            self.assertEqual(ident["year"], str(self.project.tahun_project))
            self.assertNotEqual(ident["year"], "-")

    def test_absent_attributes_default_to_dash(self):
        # Defensive: a project-like object missing the fields → '-' (never crash).
        class _Bare:
            id = 0

        ident = get_project_identity(_Bare())
        self.assertEqual(ident["name"], "-")
        self.assertEqual(ident["location"], "-")
        self.assertEqual(ident["owner"], "-")
        self.assertEqual(ident["sumber_dana"], "-")
        self.assertEqual(ident["year"], "-")
        self.assertIsNone(ident["anggaran_owner"])


class IdentityDelegationGuardTests(TestCase):
    """Producers must delegate to the canonical provider, not the old wrong fields."""

    def _src(self, rel):
        with open(os.path.join(_APP_DIR, rel), encoding="utf-8") as f:
            return f.read()

    def test_export_manager_delegates_and_drops_wrong_fields(self):
        src = self._src(os.path.join("exports", "export_manager.py"))
        self.assertIn("get_project_identity", src)
        # actual wrong-field READS (not docstring prose) must be gone
        self.assertNotIn("getattr(self.project, 'tahun_anggaran'", src)
        self.assertNotIn("getattr(self.project, 'lokasi',", src)

    def test_jadwal_adapter_delegates(self):
        src = self._src(os.path.join("exports", "jadwal_pekerjaan_adapter.py"))
        self.assertIn("get_project_identity", src)
        self.assertNotIn('getattr(self.project, "lokasi",', src)


class ExportManagerIdentityPassthroughTests(TestCase):
    """Nilai identitas harus SAMPAI ke exporter, bukan sekadar didelegasikan.

    Guard di atas hanya memindai teks sumber, jadi ia lolos ketika
    ``_get_project_identity()`` memanggil provider kanonik dengan benar lalu
    menjatuhkan sebagian hasilnya saat menyempitkan dict. Itu persis yang
    terjadi: keempat field konsultan/kontraktor tidak pernah diteruskan,
    sehingga blok "Konsultan Pengawas" di laporan selalu kosong meski datanya
    terisi di Dashboard.

    Exporter membaca kunci-kunci ini di level ATAS project_info
    (``excel_exporter`` 3868, ``pdf_exporter`` 3858/3876, ``word_exporter``
    1734), dan memakai dua penamaan bergantian -- keduanya diuji di sini.
    """

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="identity-passthrough-owner", password="x"
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Identitas",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas Peternakan",
            jabatan_client="PPK",
            instansi_client="Pemkab Lombok Barat",
            nama_kontraktor="CV Pelaksana",
            instansi_kontraktor="CV Pelaksana Jaya",
            nama_konsultan_perencana="Perencana A",
            instansi_konsultan_perencana="CV Perencana",
            nama_konsultan_pengawas="Pengawas B",
            instansi_konsultan_pengawas="CV Pengawas",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2027, 3, 1),
            tanggal_selesai=date(2027, 8, 1),
        )

    def test_every_party_field_reaches_exporters(self):
        from detail_project.exports.export_manager import ExportManager

        info = ExportManager(self.project)._get_project_identity()

        expected = {
            "client": "Dinas Peternakan",
            "nama_client": "Dinas Peternakan",
            "jabatan_client": "PPK",
            "instansi_client": "Pemkab Lombok Barat",
            "kontraktor": "CV Pelaksana",
            "nama_kontraktor": "CV Pelaksana",
            "instansi_kontraktor": "CV Pelaksana Jaya",
            "konsultan_perencana": "Perencana A",
            "nama_konsultan_perencana": "Perencana A",
            "instansi_konsultan_perencana": "CV Perencana",
            "konsultan_pengawas": "Pengawas B",
            "nama_konsultan_pengawas": "Pengawas B",
            "instansi_konsultan_pengawas": "CV Pengawas",
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(
                    info.get(key),
                    value,
                    f"'{key}' tidak sampai ke project_info; laporan akan "
                    "menampilkannya kosong meski datanya ada di Dashboard.",
                )
