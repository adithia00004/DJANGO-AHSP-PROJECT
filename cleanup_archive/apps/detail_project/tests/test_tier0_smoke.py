# detail_project/tests/test_tier0_smoke.py
from types import SimpleNamespace
import pytest
from django.template.loader import render_to_string
from django.test import override_settings


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
def test_sidebar_renders_with_project_and_active_link():
    html = render_to_string(
        "detail_project/_sidebar_global.html",
        {
            "project": fake_project(),
            "side_active": "volume_pekerjaan",
        },
    )
    # Anchor + ARIA baseline
    assert 'id="dp-sidebar"' in html
    assert 'aria-hidden="true"' in html
    assert 'tabindex="-1"' in html
    # Active link should have aria-current
    assert 'aria-current="page"' in html
    # Mobile close button exists
    assert 'class="btn-close ms-2 d-lg-none"' in html
    # Metadata line shows when tahun/lokasi tersedia
    assert "dp-sidebar__meta" in html


@override_settings(ROOT_URLCONF="detail_project.tests.urls_stub")
def test_sidebar_renders_without_project():
    html = render_to_string(
        "detail_project/_sidebar_global.html",
        {
            "project": None,
            "side_active": "dashboard",
        },
    )
    # Should still render without crashing
    assert 'id="dp-sidebar"' in html
    # Project-only links should not include aria-current on others
    assert 'aria-label="Global project navigation"' in html


@override_settings(ROOT_URLCONF="detail_project.tests.urls_stub")
def test_project_identity_renders_and_formats_numbers():
    html = render_to_string(
        "detail_project/_project_identity.html",
        {"project": fake_project()},
    )
    assert "pi-grid" in html
    assert "Project Anggaran" in html
    # Should contain "Rp " and a number (no crash)
    assert "Rp" in html


@override_settings(ROOT_URLCONF="detail_project.tests.urls_stub")
def test_project_identity_handles_blank_values():
    html = render_to_string(
        "detail_project/_project_identity.html",
        {"project": fake_project(nama=None, sumber_dana=None, lokasi_project=None)},
    )
    # Fallback dash (—) appears for missing values
    assert "—" in html


@override_settings(ROOT_URLCONF="detail_project.tests.urls_stub")
def test_alert_levels_and_auto_dismiss_script_present():
    class Msg:
        def __init__(self, text, tags):
            self.text = text
            self._tags = tags

        def __str__(self):
            return self.text

        @property
        def tags(self):
            return self._tags

        @tags.setter
        def tags(self, v):
            self._tags = v

    messages = [
        Msg("Sukses simpan.", "success"),
        Msg("Info umum.", "info"),
        Msg("Ada peringatan.", "warning"),
        Msg("Kesalahan fatal.", "error"),
    ]
    html = render_to_string("detail_project/_alert.html", {"messages": messages})
    # Varian kelas alert
    assert 'alert-success' in html
    assert 'alert-info' in html
    assert 'alert-warning' in html
    assert 'alert-danger' in html   # 'error' -> 'danger'
    # Auto-dismiss hanya untuk non-danger (class alert-auto ada)
    assert 'alert-auto' in html
    # Script auto-dismiss hadir
    assert 'bootstrap.Alert.getOrCreateInstance' in html
