"""Edit massal mudah dijangkau — regresi review 2026-09-28.

Dulu jalurnya tersembunyi: tombol toolbar "Pilih Project" (tanpa kata "edit")
-> kolom checkbox baru muncul -> bar -> "Edit Massal". Bar juga bisa hilang
saat pilihan kosong padahal "mode pilih" masih aktif.

Kini: tombol "Edit Massal" langsung di toolbar & FAB, kolom checkbox selalu
terlihat, dan bar aksi mengikuti jumlah pilihan.
"""
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project

User = get_user_model()
BASE = Path(settings.BASE_DIR)


def _read(relative):
    return (BASE / relative).read_text(encoding="utf-8")


class MassEditEntryPointTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="mass-edit-entry",
            password="StrongPass123!",
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        Project.objects.create(
            owner=self.owner,
            nama="Proyek Edit Massal",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 3, 31),
        )
        self.client.force_login(self.owner)
        self.html = self.client.get(reverse("dashboard:dashboard")).content.decode("utf-8")

    def test_toolbar_has_direct_mass_edit_button(self):
        match = re.search(r'<button[^>]*id="massEditEntryBtn"[^>]*>(.*?)</button>', self.html, re.S)
        self.assertIsNotNone(match, "tombol Edit Massal tidak ada di toolbar")
        self.assertIn("Edit Massal", match.group(1))
        self.assertNotIn("disabled", match.group(0))
        # Pintu masuk lama yang menyesatkan sudah hilang.
        self.assertNotIn('id="bulkModeToggleBtn"', self.html)
        self.assertNotIn("Pilih Project", self.html)

    def test_fab_quick_actions_offers_mass_edit(self):
        self.assertRegex(self.html, r'id="fabMassEdit"[^>]*>\s*<i[^>]*></i>\s*<span class="fab-label">Edit Massal</span>')

    def test_selection_bar_shows_edit_count(self):
        self.assertIn('id="massEditSelectedCount"', self.html)
        self.assertIn("Batalkan pilihan", self.html)

    def test_rows_have_selectable_checkboxes_with_labels(self):
        self.assertIn('aria-label="Pilih Proyek Edit Massal"', self.html)
        self.assertIn('aria-label="Pilih semua project di halaman ini"', self.html)


class MassEditEntrySourceTests(TestCase):
    def test_checkbox_column_is_visible_without_a_selection_mode(self):
        css = _read("dashboard/static/dashboard/css/dashboard.css")
        rule = re.search(r"\.dashboard-project-table \.checkbox-column \{([^}]*)\}", css)
        self.assertIsNotNone(rule)
        self.assertIn("display: table-cell", rule.group(1))
        self.assertNotIn("bulk-mode-active", css)

    def test_bulk_script_has_no_separate_selection_mode(self):
        template = _read("dashboard/templates/dashboard/_project_stats_and_table.html")
        for stale in ("bulkModeToggleBtn", "toggleBulkMode", "bulk-mode-active"):
            self.assertNotIn(stale, template)
        self.assertIn("function clearSelection()", template)

    def test_entry_click_handles_empty_selection_and_small_screens(self):
        script = _read("dashboard/static/dashboard/js/mass-edit-toggle.js")
        self.assertIn("[entryBtn, fabEntryBtn].forEach", script)
        self.assertIn("async function handleEntryClick(event)", script)
        self.assertIn("confirmText: 'Edit semua'", script)
        # Layar kecil: dijelaskan lewat toast, bukan tombol mati diam-diam.
        self.assertNotIn("updateMobileAvailability", script)
        self.assertIn("Edit massal membutuhkan layar desktop", script)
