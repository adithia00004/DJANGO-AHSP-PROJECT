import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_jadwal_pekerjaan_page_renders_with_core_anchors(client_logged, project):
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    expected_anchors = [
        'id="tahapan-grid-app"',
        'id="viewTabs"',
        'id="grid-view"',
        'id="gantt-view"',
        'id="scurve-view"',
        'id="tanstack-grid-container"',
        'id="tanstack-grid-scroll-top"',
        'id="gantt-redesign-container"',
        'id="save-button"',
        'id="btn-reset-progress"',
    ]

    for anchor in expected_anchors:
        assert anchor in html, f"Expected anchor missing: {anchor}"


@pytest.mark.django_db
def test_jadwal_pekerjaan_page_includes_module_scripts(client_logged, project):
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert "assets/js/jadwal-kegiatan" in html
    assert f'data-api-base="/detail_project/api/project/{project.id}/tahapan/' in html
    assert f'data-api-save="/detail_project/api/v2/project/{project.id}/assign-weekly/' in html
    assert 'data-enable-uplot-kurva="true"' in html
    assert '<div class="tanstack-grid-section"' in html


@pytest.mark.django_db
def test_tanstack_grid_container_not_hidden(client_logged, project):
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert 'id="tanstack-grid-container"' in html
    assert "tanstack-grid-container d-none" not in html


@pytest.mark.django_db
def test_ag_grid_assets_removed(client_logged, project):
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert "ag-grid-community" not in html
    assert "ag-theme-alpine" not in html


@pytest.mark.django_db
@override_settings(USE_VITE_DEV_SERVER=True, DEBUG=True)
def test_vite_dev_server_mode_loads_correct_path(client_logged, project):
    """Pastikan mode dev Vite memakai path baru yang singkat"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert 'src="http://localhost:5173/js/src/jadwal_kegiatan_app.js"' in html
    assert "detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js" not in html


@pytest.mark.django_db
def test_uplot_flag_always_enabled(client_logged, project):
    """uPlot harus aktif tanpa bergantung flag settings"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert 'data-enable-uplot-kurva="true"' in html
