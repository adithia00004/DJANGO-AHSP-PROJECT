# test.py — E2E sanity checks untuk sidebar overlay "List Pekerjaan"
# Jalankan: python test.py --url http://127.0.0.1:8000/detail_project/79/list-pekerjaan/ [--user ... --password ...] [--headed]
import argparse
from contextlib import contextmanager
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="URL halaman list_pekerjaan")
    ap.add_argument("--user", default=None, help="Username/email untuk login (opsional)")
    ap.add_argument("--password", default=None, help="Password untuk login (opsional)")
    ap.add_argument("--headed", action="store_true", help="Tampilkan browser UI (default headless)")
    return ap.parse_args()

@contextmanager
def launch(headed=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        ctx = browser.new_context()
        page = ctx.new_page()
        try:
            yield page
        finally:
            ctx.close()
            browser.close()

def screenshot(page, name):
    Path(".e2e_artifacts").mkdir(exist_ok=True)
    path = f".e2e_artifacts/{name}"
    try:
        page.screenshot(path=path, full_page=True)
        print(f"[DEBUG] Screenshot saved: {path}")
    except Exception as e:
        print(f"[WARN] Gagal ambil screenshot {name}: {e}")

def try_login_if_needed(page, user, password):
    """Deteksi form login via URL atau keberadaan password field; login jika kredensial disediakan."""
    on_login_like = ("login" in page.url) or ("account" in page.url) or page.locator('input[type="password"]').count() > 0
    if not on_login_like:
        return
    if not (user and password):
        screenshot(page, "00_login_required.png")
        raise AssertionError("[FAIL] Halaman membutuhkan login. Jalankan test.py dengan --user dan --password (lihat 00_login_required.png).")

    email = page.locator('input[type="email"], input[name="login"], input[name="username"], input[type="text"]').first
    pwd   = page.locator('input[type="password"]').first
    submit= page.locator('button[type="submit"], input[type="submit"]').first

    if not (email and pwd and submit) or not email.is_visible() or not pwd.is_visible():
        screenshot(page, "00_login_unknown.png")
        raise AssertionError("[FAIL] Form login tidak dikenali. Lihat 00_login_unknown.png dan sesuaikan selector di test.py.")

    email.fill(user)
    pwd.fill(password)
    submit.click()
    page.wait_for_load_state("networkidle")
    print("[OK] Login attempt done. Current URL:", page.url)

def assert_visible(page, sel, msg, timeout=8000):
    try:
        page.wait_for_selector(sel, state="visible", timeout=timeout)
        print(f"[OK] {msg}")
    except Exception as e:
        screenshot(page, f"__missing_{sel.replace('#','id_').replace('.','class_')}.png")
        title_txt = page.title()
        raise AssertionError(f"[FAIL] {msg} — selector '{sel}' tidak terlihat di '{page.url}' (title: '{title_txt}'). Detail: {e}")

def first_existing_selector(page, selectors):
    """Kembalikan selector pertama yang ada/terlihat dari daftar; None jika tidak ada."""
    for sel in selectors:
        if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
            return sel
    return None

def main():
    args = parse_args()
    with launch(args.headed) as page:
        print("[INFO] Opening:", args.url)
        page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        print("[DEBUG] Landed on:", page.url)
        screenshot(page, "01_landing.png")

        # Login jika perlu
        try_login_if_needed(page, args.user, args.password)

        # Pastikan di halaman target setelah login
        page.goto(args.url, wait_until="networkidle")
        print("[DEBUG] After login goto:", page.url)
        screenshot(page, "02_after_login_goto.png")

        # 1) Tombol toggle kanonik terlihat
        assert_visible(page, "#btn-sidebar-toggle", "Tombol toggle kanonik terlihat")

        # 2) Klik toggle → overlay terlihat + body lock + fokus search
        page.click("#btn-sidebar-toggle")
        assert_visible(page, "#lp-sidebar", "Overlay sidebar terlihat")
        # body lock
        has_lock = page.evaluate("() => document.body.classList.contains('lp-overlay-open')")
        assert has_lock, "[FAIL] Body lock (lp-overlay-open) tidak aktif"
        print("[OK] Body locked")

        # fokus ke search (sidebar = sumber kebenaran)
        assert_visible(page, "#lp-nav-search-side", "Input search sidebar ada")
        expect(page.locator("#lp-nav-search-side")).to_be_focused(timeout=3000)
        print("[OK] Fokus ke search sidebar")

        # 3) Expand/Collapse All — dukung class atau id
        expand_sel = first_existing_selector(page, [".lp-nav-expand-all", "#lp-nav-expand-all"])
        collapse_sel = first_existing_selector(page, [".lp-nav-collapse-all", "#lp-nav-collapse-all"])
        if expand_sel and collapse_sel:
            page.click(expand_sel)
            page.click(collapse_sel)
            print("[OK] Expand/Collapse All dapat diklik")
        else:
            print("[WARN] Tombol Expand/Collapse All tidak ditemukan (class/id). Lewati uji ini.")

        # 4) Autocomplete (sidebar): ≥2 huruf → saran → Enter → navigate & overlay close (jika data memadai)
        search = page.locator("#lp-nav-search-side")
        search.fill("ab")  # ubah huruf sesuai data kamu bila perlu
        page.wait_for_timeout(300)
        has_suggest = page.locator("#lp-nav-suggest .lp-ac-item").count() > 0
        if has_suggest:
            search.press("Enter")
            # overlay harus tertutup
            expect(page.locator("#lp-sidebar")).not_to_be_visible(timeout=4000)
            # buka lagi memastikan bisa lanjut test2 berikutnya
            page.click("#btn-sidebar-toggle")
            print("[OK] Autocomplete (sidebar): Enter pada saran → navigate & overlay close")
        else:
            print("[WARN] Tidak ada saran (dataset mungkin minim). Lewati Enter navigate.")

        # 5) Clear keyword on close
        page.fill("#lp-nav-search-side", "xyz")
        page.keyboard.press("Escape")  # tutup overlay
        expect(page.locator("#lp-sidebar")).not_to_be_visible(timeout=3000)
        page.click("#btn-sidebar-toggle")  # buka lagi
        expect(page.locator("#lp-nav-search-side")).to_have_value("", timeout=2000)
        print("[OK] Keyword sidebar dikosongkan saat overlay ditutup")

        # 6) +Klas & +Sub dari sidebar
        klas_btn = first_existing_selector(page, ["#btn-add-klas--sidebar"])
        sub_btn  = first_existing_selector(page, ["#btn-add-sub--sidebar"])
        if klas_btn:
            before_cards = page.locator("#klas-list .card.shadow-sm").count()
            page.click(klas_btn)
            expect(page.locator("#klas-list .card.shadow-sm")).to_have_count(before_cards + 1, timeout=3000)
            print("[OK] +Klas di sidebar menambah kartu klasifikasi")
        else:
            print("[WARN] Tombol +Klas sidebar tidak ditemukan; Lewati test ini.")

        if sub_btn:
            last_subs_before = page.locator("#klas-list .card.shadow-sm:last-of-type .sub-wrap > *").count()
            page.click(sub_btn)
            expect(page.locator("#klas-list .card.shadow-sm:last-of-type .sub-wrap > *")).to_have_count(last_subs_before + 1, timeout=3000)
            print("[OK] +Sub di sidebar menambah sub-klasifikasi ke konteks terakhir/aktif")
        else:
            print("[WARN] Tombol +Sub sidebar tidak ditemukan; Lewati test ini.")

        # 7) Focus trap + restore: backdrop click → kembali fokus ke toggle
        # (pastikan overlay terbuka dulu)
        if not page.locator("#lp-sidebar").is_visible():
            page.click("#btn-sidebar-toggle")
        # klik backdrop di sisi kiri atas
        page.mouse.click(5, 5)
        expect(page.locator("#lp-sidebar")).not_to_be_visible(timeout=3000)
        expect(page.locator("#btn-sidebar-toggle")).to_be_focused(timeout=1500)
        print("[OK] Focus trap aktif & fokus kembali ke toggle saat overlay ditutup")

        # 8) ESC close overlay
        page.click("#btn-sidebar-toggle")
        expect(page.locator("#lp-sidebar")).to_be_visible(timeout=3000)
        page.keyboard.press("Escape")
        expect(page.locator("#lp-sidebar")).not_to_be_visible(timeout=3000)
        print("[OK] ESC menutup overlay")

        # 9) Toolbar search (opsional, jika ada): saran & navigate
        if page.locator("#lp-nav-search").count() > 0:
            page.fill("#lp-nav-search", "ab")
            page.wait_for_timeout(250)
            has_tb_suggest = page.locator(".lp-toolbar-search .lp-autocomplete .lp-ac-item").count() > 0
            if has_tb_suggest:
                page.locator(".lp-toolbar-search input").press("Enter")
                # overlay sempat terbuka untuk navigate lalu tertutup
                expect(page.locator("#lp-sidebar")).not_to_be_visible(timeout=4000)
                print("[OK] Toolbar search → navigate OK")
            else:
                print("[WARN] Saran toolbar kosong. Lewati Enter test.")
        else:
            print("[INFO] Toolbar search tidak ada di halaman ini. Lewati uji toolbar.")

        # 10) Resizer: drag & persist width di localStorage
        page.click("#btn-sidebar-toggle")
        if page.locator("#lp-sidebar .lp-resizer").count() > 0:
            box = page.locator("#lp-sidebar .lp-resizer").bounding_box()
            if box:
                page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                page.mouse.down()
                page.mouse.move(box["x"] - 120, box["y"] + box["height"]/2, steps=8)
                page.mouse.up()
                lw = page.evaluate("() => localStorage.getItem('lp_sidebar_w')")
                print("[OK] Resizer moved, saved width:", lw)
        else:
            print("[WARN] Resizer tidak terlihat. Lewati uji ini.")

        print("\n✅ SEMUA CEK UTAMA SELESAI.\n")

if __name__ == "__main__":
    main()
