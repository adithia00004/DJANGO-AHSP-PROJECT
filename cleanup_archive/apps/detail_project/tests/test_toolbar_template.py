import pathlib


def test_toolbar_controls_exist():
    """
    Smoke test template: pastikan kontrol Time Scale dan Week Boundaries
    tersedia di toolbar desktop (menghindari hilang di UI).
    """
    tpl_path = (
        pathlib.Path(__file__)
        .resolve()
        .parent.parent
        / "templates"
        / "detail_project"
        / "kelola_tahapan_grid_modern.html"
    )
    content = tpl_path.read_text(encoding="utf-8")

    # Radio time scale (desktop)
    assert 'id="scale-weekly"' in content
    assert 'id="scale-monthly"' in content

    # Week boundary selects
    assert 'id="week-start-day-select"' in content
    assert 'id="week-end-day-select"' in content
