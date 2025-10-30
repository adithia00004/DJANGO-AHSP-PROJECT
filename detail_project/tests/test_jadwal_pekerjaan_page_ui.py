import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_jadwal_pekerjaan_page_renders_with_core_anchors(client_logged, project):
    url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
    response = client_logged.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    expected_anchors = [
        'id="tahapan-grid-app"',
        'id="grid-view"',
        'id="gantt-view"',
        'id="scurve-view"',
        'id="left-tbody"',
        'id="right-tbody"',
        'id="gantt-chart"',
        'id="scurve-chart"',
        'id="loading-overlay"',
        'id="btn-save-all"',
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

    expected_scripts = [
        "detail_project/js/jadwal_pekerjaan/kelola_tahapan_page_bootstrap.js",
        "detail_project/js/jadwal_pekerjaan/kelola_tahapan/module_manifest.js",
        "detail_project/js/jadwal_pekerjaan/kelola_tahapan/shared_module.js",
        "detail_project/js/jadwal_pekerjaan/kelola_tahapan/grid_module.js",
        "detail_project/js/jadwal_pekerjaan/kelola_tahapan/gantt_module.js",
        "detail_project/js/jadwal_pekerjaan/kelola_tahapan/kurva_s_module.js",
        "detail_project/js/kelola_tahapan_grid.js",
    ]

    for script in expected_scripts:
        assert script in html, f"Expected script reference missing: {script}"

    assert f'data-api-base="/detail_project/api/project/{project.id}/tahapan/' in html
