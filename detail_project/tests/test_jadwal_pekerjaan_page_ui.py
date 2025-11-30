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
        'id="ag-grid-container"',
        'id="gantt-container"',
        'id="scurve-container"',
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
    assert f'data-api-tahapan="/detail_project/api/project/{project.id}/tahapan/' in html
    assert f'data-api-list-pekerjaan="/detail_project/api/project/{project.id}/list-pekerjaan/tree/' in html
    assert 'data-enable-ag-grid="true"' in html
    assert f'data-api-save="/detail_project/api/v2/project/{project.id}/assign-weekly/' in html


@pytest.mark.django_db
@override_settings(ENABLE_AG_GRID=False)
def test_jadwal_pekerjaan_page_respects_ag_grid_flag(client_logged, project):
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert 'data-enable-ag-grid="false"' in html


@pytest.mark.django_db
def test_ag_grid_css_loaded(client_logged, project):
    """Test that AG Grid CSS is loaded in the page"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Check AG Grid CSS from CDN
    assert "ag-grid-community" in html
    assert "ag-grid.css" in html
    assert "ag-theme-alpine.css" in html


@pytest.mark.django_db
def test_ag_grid_container_has_proper_classes(client_logged, project):
    """Test that AG Grid container has the correct CSS classes"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Check container has both theme class and wrapper class
    assert 'class="ag-theme-alpine ag-grid-wrapper' in html
    assert 'id="ag-grid-container"' in html


@pytest.mark.django_db
@override_settings(USE_VITE_DEV_SERVER=True, DEBUG=True)
def test_vite_dev_server_mode_loads_correct_path(client_logged, project):
    """Test that Vite dev mode uses correct module path (Issue #1 fix)"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Should use SHORT path relative to Vite root
    assert 'src="http://localhost:5173/js/src/jadwal_kegiatan_app.js"' in html

    # Should NOT use full path (this was the bug)
    assert 'detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js' not in html


@pytest.mark.django_db
def test_custom_grid_not_rendered_when_ag_grid_enabled(client_logged, project):
    """Test that custom grid is hidden when AG Grid is enabled"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    assert 'grid-container legacy-grid-wrapper' not in html


@pytest.mark.django_db
@override_settings(ENABLE_AG_GRID=False)
def test_ag_grid_hidden_when_disabled(client_logged, project):
    """Test that AG Grid is hidden when disabled via settings"""
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # AG Grid container should have d-none when disabled
    assert 'd-none' in html

    # Custom grid should NOT have d-none
    assert 'data-enable-ag-grid="false"' in html
