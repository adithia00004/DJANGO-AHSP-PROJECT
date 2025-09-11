# detail_project/tests/test_tier0_smoke.py
from types import SimpleNamespace
from django.test import SimpleTestCase, override_settings
from django.template.loader import render_to_string

# Helper: dummy project object with attributes accessed by templates
def fake_project(**kwargs):
    defaults = dict(
        id=77,
        nama="Proyek Jalan Nasional",
        ket_project1="Paket 1",
        ket_project2="Tahap II",
        nama_client="Dinas PUPR",
        instansi_client="Pemprov Jabar",
        tahun_project="2025",
        sumber_dana="APBD",
        lokasi_project="Bandung Raya",
        anggaran_owner=1250000000,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)

@override_settings(ROOT_URLCONF="detail_project.tests.urls_stub")
class Tier0TemplateSmokeTests(SimpleTestCase):
    def test_sidebar_renders_with_project_and_active_link(self):
        html = render_to_string(
            "detail_project/_sidebar_global.html",
            {
                "project": fake_project(),
                "side_active": "volume_pekerjaan",
            },
        )
        # Anchor + ARIA baseline
        self.assertIn('id="dp-sidebar"', html)
        self.assertIn('aria-hidden="true"', html)
        self.assertIn('tabindex="-1"', html)
        # Active link should have aria-current
        self.assertIn('aria-current="page"', html)
        # Mobile close button exists
        self.assertIn('class="btn-close ms-2 d-lg-none"', html)
        # Metadata line shows when tahun/lokasi tersedia
        self.assertIn("dp-sidebar__meta", html)

    def test_sidebar_renders_without_project(self):
        html = render_to_string(
            "detail_project/_sidebar_global.html",
            {
                "project": None,
                "side_active": "dashboard",
            },
        )
        # Should still render without crashing
        self.assertIn('id="dp-sidebar"', html)
        # Project-only links should not include aria-current on others
        self.assertIn('aria-label="Global project navigation"', html)

    def test_project_identity_renders_and_formats_numbers(self):
        html = render_to_string(
            "detail_project/_project_identity.html",
            {"project": fake_project()},
        )
        self.assertIn("pi-grid", html)
        self.assertIn("Project Anggaran", html)
        # Should contain "Rp " and a number (no crash)
        self.assertIn("Rp", html)

    def test_project_identity_handles_blank_values(self):
        html = render_to_string(
            "detail_project/_project_identity.html",
            {"project": fake_project(nama=None, sumber_dana=None, lokasi_project=None)},
        )
        # Fallback dash (—) appears for missing values
        self.assertIn("—", html)

    def test_alert_levels_and_auto_dismiss_script_present(self):
        class Msg:
            def __init__(self, text, tags): self.text, self.tags = text, tags
            def __str__(self): return self.text
            @property
            def tags(self): return self._tags
            @tags.setter
            def tags(self, v): self._tags = v

        messages = [
            Msg("Sukses simpan.", "success"),
            Msg("Info umum.", "info"),
            Msg("Ada peringatan.", "warning"),
            Msg("Kesalahan fatal.", "error"),
        ]
        html = render_to_string("detail_project/_alert.html", {"messages": messages})
        # Varian kelas alert
        self.assertIn('alert-success', html)
        self.assertIn('alert-info', html)
        self.assertIn('alert-warning', html)
        self.assertIn('alert-danger', html)   # 'error' -> 'danger'
        # Auto-dismiss hanya untuk non-danger (class alert-auto ada)
        self.assertIn('alert-auto', html)
        # Script auto-dismiss hadir
        self.assertIn('bootstrap.Alert.getOrCreateInstance', html)
