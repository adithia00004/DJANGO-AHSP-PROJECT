import pytest
from django.urls import reverse

pytestmark = pytest.mark.playwright

@pytest.mark.django_db
def test_list_pekerjaan_flow(live_server, client, user):
    # siapkan project & login
    from dashboard.models import Project
    client.force_login(user)
    project = Project.objects.create(owner=user, nama="Proyek E2E")

    # buat cookie auth di browser playwright
    # (gunakan API request_context untuk ambil session cookie dari Django test client)
    from http.cookies import SimpleCookie
    cookies = []
    for morsel in client.cookies.values():
        c = {
            "name": morsel.key,
            "value": morsel.value,
            "domain": "localhost",
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax"
        }
        cookies.append(c)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context()
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        url = f"{live_server.url}/detail_project/{project.id}/list-pekerjaan/"
        page.goto(url)

        # tambah klasifikasi, sub, pekerjaan (custom)
        page.get_by_text("+ Klasifikasi").click()
        page.get_by_text("+ Sub-Klasifikasi").click()
        page.get_by_text("+ Pekerjaan").click()
        page.locator("input.uraian").first.fill("Pekerjaan Custom E2E")
        page.get_by_text("Simpan Semua").click()

        # tunggu alert (native alert -> tidak ditangkap; alternatif: cek reload tree)
        page.wait_for_timeout(1000)
        # cek ada 1 baris (selector kasar: rows di tabel tbody)
        assert page.locator("table tbody tr").count() >= 1

        browser.close()
