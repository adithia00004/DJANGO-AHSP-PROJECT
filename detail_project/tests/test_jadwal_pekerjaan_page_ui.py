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
        'id="left-tbody"',
        'id="right-tbody"',
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
