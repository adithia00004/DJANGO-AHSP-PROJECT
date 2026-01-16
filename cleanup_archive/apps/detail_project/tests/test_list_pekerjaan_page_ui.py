def test_page_renders_and_core_anchors_exist(client_logged, api_urls):
    r = client_logged.get(api_urls["page"])
    assert r.status_code == 200
    html = r.content.decode("utf-8")

    # Anchor utama untuk app & toolbar
    must_have = [
        'id="lp-app"', 'id="klas-list"',
        'id="btn-add-klas"', 'id="btn-save"', 'id="btn-compact"',
        'id="lp-sidebar"', 'id="lp-nav"',
        'id="tpl-pekerjaan-row-table"',  # template row
    ]
    for m in must_have:
        assert m in html, f"Anchor hilang: {m}"

def test_referensi_search_url_resolves_during_render(client_logged, api_urls):
    # Jika URL name 'referensi:api_search_ahsp' tak ada, render akan 500; test ini memastikan resolvable.
    r = client_logged.get(api_urls["page"])
    assert r.status_code == 200
