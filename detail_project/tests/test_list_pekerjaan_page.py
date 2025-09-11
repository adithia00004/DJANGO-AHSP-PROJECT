# detail_project/tests/test_list_pekerjaan_page.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from dashboard.models import Project

try:
    from .test_list_pekerjaan_api import make_project_for_tests
except Exception:
    def make_project_for_tests(owner):
        return Project.objects.create(owner=owner, is_active=True, nama="P1")


class ListPekerjaanPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="u1", password="pass12345")
        cls.project = make_project_for_tests(cls.user)

        def set_if_exists(obj, name, value):
            if hasattr(obj, name):
                setattr(obj, name, value)

        set_if_exists(cls.project, "nama", "Proyek Jalan Nasional")
        set_if_exists(cls.project, "ket_project1", "Peningkatan Ruas A")
        set_if_exists(cls.project, "ket_project2", "Segmen Km 12+000 – Km 18+500")
        set_if_exists(cls.project, "nama_client", "PT Maju Mundur")
        set_if_exists(cls.project, "instansi_client", "Dinas PUPR")
        set_if_exists(cls.project, "tahun_project", 2025)
        set_if_exists(cls.project, "sumber_dana", "APBD")
        set_if_exists(cls.project, "lokasi_project", "Kota Semarang")
        set_if_exists(cls.project, "total_anggaran", Decimal("1234567"))
        if hasattr(cls.project, "is_active"):
            cls.project.is_active = True
        cls.project.save()

    def setUp(self):
        self.c = Client()

    def _url(self, pid=None):
        pid = pid or self.project.id
        return reverse("detail_project:list_pekerjaan", kwargs={"project_id": pid})

    def test_requires_login_redirect(self):
        resp = self.c.get(self._url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])

    def test_page_renders_ok_and_uses_template(self):
        self.c.login(username="u1", password="pass12345")
        resp = self.c.get(self._url())
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "detail_project/list_pekerjaan.html")
        html = resp.content.decode("utf-8")
        # Topbar global hadir dan menggunakan kelas sticky-top (jangan cek literal z-index di HTML)
        self.assertIn('id="dp-topbar"', html)
        self.assertIn('sticky-top', html)

    def test_global_sidebar_present_and_controls(self):
        """dp-sidebar ada, tombol global ada. Badge lama (dp-sidebadge) boleh ada/tiada."""
        self.c.login(username="u1", password="pass12345")
        html = self.c.get(self._url()).content.decode("utf-8")
        # Sidebar global ada
        self.assertIn('id="dp-sidebar"', html)
        # Tombol kontrol global (Tier-0) ada
        self.assertIn('id="dp-sidebar-toggle"', html)
        # Badge lama opsional → jangan dipaksa ada/tiada di sini

    def test_legacy_sidebar_absent_and_hotspot_is_disabled_on_page(self):
        """Legacy lpSidebar tidak ada. Hotspot global boleh ada di HTML, tapi harus dinonaktifkan di halaman LP."""
        self.c.login(username="u1", password="pass12345")
        html = self.c.get(self._url()).content.decode("utf-8")
        # Legacy id lama tidak ada
        self.assertNotIn('id="lpSidebar"', html)
        self.assertNotIn('id="lpSidebarMini"', html)
        # ID tombol lama tidak ada
        self.assertNotIn('id="btn-sidebar-toggle"', html)
        # Hotspot bisa hadir secara global; pastikan di halaman ini ada aturan untuk menyembunyikannya
        # Kita cek style inline yang kita tambahkan di block extra_css halaman LP.
        self.assertIn(".lp-sidebar-hotspot { display: none !important; }", html)

    def test_side_active_marks_list_pekerjaan(self):
        self.c.login(username="u1", password="pass12345")
        html = self.c.get(self._url()).content.decode("utf-8")
        # class aktif dan label link List Pekerjaan
        self.assertIn('class="dp-link is-active"', html)
        self.assertIn('<span>List Pekerjaan</span>', html)

    def test_identity_component_labels_and_values_render(self):
        self.c.login(username="u1", password="pass12345")
        html = self.c.get(self._url()).content.decode("utf-8")
        # label utama
        for label in ["Proyek", "Pemilik Project", "Tahun", "Sumber Dana", "Lokasi", "Project Anggaran"]:
            self.assertIn(label, html)
        # sebagian nilai
        for val in [
            "Proyek Jalan Nasional",
            "Peningkatan Ruas A",
            "Segmen Km 12+000 – Km 18+500",
            "PT Maju Mundur",
            "Dinas PUPR",
            "2025",
            "APBD",
            "Kota Semarang",
        ]:
            self.assertIn(val, html)
        # Anggaran: cek ada "Rp" + angka (tanpa asumsi format ribuan spesifik)
        self.assertRegex(html, r"Project Anggaran.*?Rp\s*[0-9][0-9.,\s]*")

    def test_identity_handles_missing_optional_lines(self):
        """Jika ket_project1/2 kosong, baris tambahan Proyek tidak dirender."""
        self.c.login(username="u1", password="pass12345")
        # Project baru MILIK user yang sama (hindari 404 owner mismatch)
        p2 = make_project_for_tests(self.user)
        if hasattr(p2, "nama"): p2.nama = "Proyek B"
        if hasattr(p2, "ket_project1"): p2.ket_project1 = ""
        if hasattr(p2, "ket_project2"): p2.ket_project2 = None
        if hasattr(p2, "total_anggaran"): p2.total_anggaran = Decimal("0")
        p2.save()

        html = self.c.get(self._url(p2.id)).content.decode("utf-8")
        self.assertIn("Proyek B", html)
        # baris ket1/ket2 tidak muncul
        self.assertNotIn("Peningkatan Ruas A", html)
        self.assertNotIn("Segmen Km 12+000 – Km 18+500", html)
        # Anggaran 0 harus tampil "Rp 0"
        self.assertRegex(html, r"Project Anggaran.*?Rp\s*0")

    def test_sidebar_links_point_to_correct_project(self):
        self.c.login(username="u1", password="pass12345")
        html = self.c.get(self._url()).content.decode("utf-8")
        expected = reverse("detail_project:list_pekerjaan", kwargs={"project_id": self.project.id})
        self.assertIn(f'href="{expected}"', html)

    def test_sidebar_js_asset_included(self):
        """Pastikan controller Tier-0 termuat dari base_detail (non-override zone)."""
        self.c.login(username="u1", password="pass12345")
        html = self.c.get(self._url()).content.decode("utf-8")
        self.assertIn("detail_project/js/sidebar_global.js", html)
