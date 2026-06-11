# R1.1 - Review Landing Page

**Status:** `[!]` SELESAI DIREVIEW - ADA TEMUAN
**Terakhir diperbarui:** 2026-02-17

---

Catatan:
- Audit ini sudah full-pass untuk R1 pada 2026-02-17. Item responsive tetap membutuhkan verifikasi viewport manual real-device.

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/` |
| View | `pages.views.LandingPageView` (TemplateView) |
| Template | `pages/templates/pages/landing.html` (935 baris) |
| Base Template | `templates/base.html` (365 baris) |
| CSS | ~438 baris inline `<style>` di block `extra_css` + base styles |
| JS | ~13 baris inline smooth-scroll di block `extra_js` |
| Auth Required | Tidak (public page) |
| Redirect | Authenticated user -> `referensi:admin_portal` (staff) / `dashboard:dashboard` (regular) |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Akses `/` sebagai anonymous user | Landing page tampil | `[x]` | OK - view returns template langsung |
| TC-2 | Akses `/` sebagai authenticated user (regular) | Redirect ke dashboard | `[x]` | OK - `dispatch()` checks `is_authenticated` -> redirect `dashboard:dashboard` |
| TC-3 | Akses `/` sebagai authenticated user (staff/referensi) | Redirect ke admin portal | `[x]` | OK - `has_referensi_portal_access()` -> redirect `referensi:admin_portal` |
| TC-4 | Tampilan pricing plans di landing | Plan cards tampil dengan harga benar | `[x]` | OK - 100% dynamic via `subscriptions.pricing_service` (tanpa fallback hardcoded) |
| TC-11 | Promo aktif terlihat jelas di pricing cards | Badge + harga promo terlihat | `[x]` | OK - tampil badge promo + harga awal dicoret + nama promo |
| TC-5 | CTA button "Mulai Gratis 14 Hari" | Navigasi ke signup | `[x]` | OK - `{% url 'account_signup' %}` |
| TC-6 | CTA button "Pelajari Fitur" | Smooth scroll ke #features | `[x]` | OK - anchor + inline JS smooth scroll |
| TC-7 | Responsive - Mobile (< 768px) | Layout stack, readable | `[~]` | Perlu validasi visual manual - lihat F-6 |
| TC-8 | Responsive - Tablet (768-1024px) | Layout adaptif | `[~]` | Perlu validasi visual manual |
| TC-9 | SEO meta tags (title, description, og:*) | Meta tags lengkap | `[x]` | PASS - meta description + OG tags sudah tersedia di landing |
| TC-10 | Semua link internal berfungsi | Tidak ada broken link | `[~]` | PARTIAL - internal `{% url %}` valid; link placeholder `href="#"` masih ada tetapi tidak lagi memicu error JS |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | SEO meta description + Open Graph tags sudah ditambahkan pada landing. | `pages/templates/pages/landing.html:7` | Recheck render 2026-02-17: `landing_meta_description=True`, `landing_og_title=True`, `landing_og_description=True`, `landing_og_image=True` |
| F-2 | **RESOLVED (was HIGH)** | CSS load order sudah diperbaiki: vendor CSS dimuat lebih dulu, diikuti app CSS. | `templates/base.html:35`, `templates/base.html:45` | Urutan baru: Bootstrap/FA/Bootstrap Icons -> core.css -> corporate-theme.css -> error-recovery-modal.css -> toast-global.css |
| F-3 | **RESOLVED (was MEDIUM)** | `PricingPageView` tidak lagi instantiate `LandingPageView` object tanpa request. Data pricing sekarang diambil via `LandingPageView._get_pricing_plans()` (static) yang memakai service terpusat. | `pages/views.py` | Evidence implementasi: `LandingPageView._get_pricing_plans()` static + `PricingPageView.get_context_data()` memanggil static method. |
| F-4 | **RESOLVED (was MEDIUM)** | Hardcoded fallback pricing sudah dihapus. Landing sekarang hanya menampilkan data dari pricing service yang sama dengan checkout/payment. | `pages/views.py:29` | Evidence: `_get_pricing_plans()` langsung `return get_active_pricing_plans()` |
| F-5 | **MEDIUM** | **Inline CSS besar di template.** Landing page menyimpan CSS langsung di template, sehingga cacheability dan maintainability lebih rendah dibanding file static terpisah. | `pages/templates/pages/landing.html:20` | Block `<style>` panjang `landing.html` sampai ~baris 457 |
| F-6 | **MEDIUM** | **Hero tagline belum punya breakpoint responsive eksplisit.** `.hero-tagline` tetap `font-size: 3.5rem` dan tidak ditemukan `@media` override untuk ukuran kecil. | `pages/templates/pages/landing.html:89` | Recheck `rg` 2026-02-17: tidak ada `@media` rule khusus `.hero-tagline` |
| F-7 | **RESOLVED (was HIGH)** | Smooth-scroll handler kini mengabaikan `href="#"` dan hanya melakukan `querySelector` untuk anchor valid. | `pages/templates/pages/landing.html:918` | Guard aktif: `if (!href || href === '#') return;` + cek `if (!target) return;` |
| F-8 | **LOW** | **Footer branding masih nama personal.** Footer di `base.html` dan override footer di landing masih menampilkan "ADIT PORTOFOLIO Project", bukan brand produk final. | `templates/base.html:336`, `pages/templates/pages/landing.html:909` | String branding personal masih aktif di kedua template |
| F-9 | **LOW** | **Klaim marketing belum terverifikasi: "ribuan profesional".** Copy di CTA masih mengklaim skala user yang mungkin belum tervalidasi bisnis. | `pages/templates/pages/landing.html:847` | Klaim "ribuan profesional" di CTA section |
| F-10 | **LOW** | **Duplikat favicon declaration di base.html.** Ada favicon file-based dan inline data URI sekaligus. | `templates/base.html:12`, `templates/base.html:194` | Dua `<link rel="icon">` aktif |
| F-11 | **RESOLVED (was LOW)** | Diskon tidak lagi hardcoded untuk plan DB; landing/pricing memakai `subscriptions.pricing_service` yang menghitung harga efektif + badge promo berdasarkan periode aktif. | `subscriptions/pricing_service.py`, `pages/views.py` | Evidence test: `subscriptions.tests.ScheduledPromotionPricingServiceTests` (active/expired/not-started/overlap) PASS. |
| F-12 | **RESOLVED (was MEDIUM)** | Visual promo landing kini sinkron dengan backend pricing: harga normal dicoret, harga promo tampil, dan nama promo ditampilkan saat aktif. | `pages/templates/pages/landing.html` | Evidence render + test PASS: `pages.tests.PricingPageIntegrationTests.test_landing_shows_active_promo_price_from_database` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Tambahkan `<meta name="description">` dan Open Graph tags (`og:title`, `og:description`, `og:image`, `og:url`) di block `extra_head` landing.html | P0 (Pre-launch) | Low (30 min) | F-1 (`[DONE]`) |
| REC-2 | Pindahkan Bootstrap CSS load ke SEBELUM core.css di base.html, atau tambahkan specificity yang cukup pada custom CSS | P0 (Pre-launch) | Medium (1-2 jam, perlu regression test) | F-2 (`[DONE]`) |
| REC-3 | Refactor `PricingPageView` untuk memanggil `_get_pricing_plans()` sebagai static/class method, atau extract ke shared utility | P1 (Post-launch OK) | Low (30 min) | F-3 (`[DONE]`) |
| REC-4 | Extract inline CSS ke file `landing.css` terpisah di `static/pages/css/` | P1 (Post-launch OK) | Low (30 min) | F-5 |
| REC-5 | Tambahkan responsive font-size untuk `.hero-tagline`: `@media (max-width: 768px) { .hero-tagline { font-size: 2rem; } }` | P1 (Pre-launch ideal) | Low (15 min) | F-6 |
| REC-6 | Perbaiki smooth scroll selector menjadi 'a.nav-link[href^="#"]' atau tambahkan class khusus `scroll-link` | P1 (Pre-launch ideal) | Low (15 min) | F-7 (`[DONE]`) |
| REC-7 | Ganti footer text ke brand produk resmi, misal "Dashboard-RAB" atau nama perusahaan | P0 (Pre-launch) | Low (5 min) | F-8 |
| REC-8 | Ganti klaim "ribuan profesional" dengan kalimat yang lebih akurat, misal "profesional konstruksi yang mulai beralih ke digital" | P0 (Pre-launch) | Low (5 min) | F-9 |
| REC-9 | Hapus salah satu favicon declaration (pertahankan yang SVG file-based) | P2 (Nice-to-have) | Low (5 min) | F-10 |
| REC-10 | Hitung discount percentage secara dinamis dari harga, atau simpan sebagai field di model `SubscriptionPlan` | P2 (Nice-to-have) | Medium (1 jam) | F-11 (`[DONE]` via pricing service + promotion model) |
| REC-11 | Hapus atau beri flag pada hardcoded pricing fallback agar hanya aktif saat `DEBUG=True` | P1 (Pre-launch ideal) | Low (15 min) | F-4 (`[DONE]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-16 | Refactor pricing flow: `PricingPageView` tidak instantiate `LandingPageView`; kedua halaman pakai shared source | - | DONE |
| 2 | 2026-02-16 | Implement pricing service + promo terjadwal untuk pricing effective dan badge diskon | - | DONE |
| 3 | 2026-02-17 | Tambah regression test non-UI untuk redirect landing: anonymous tetap landing, regular -> dashboard, superuser -> referensi portal | - | DONE |
| 4 | 2026-02-17 | Full audit R1 pasca update UI: revalidasi SEO/meta, load-order CSS, anchor/script, branding/footer | - | DONE |
| 5 | 2026-02-17 | Implementasi fix prioritas: meta/OG landing, CSS load order, dan guard smooth-scroll anchor | - | DONE |
| 6 | 2026-02-17 | Sinkronisasi penuh landing pricing: hapus fallback hardcoded + tampilkan harga coret/nama promo dari service backend | - | DONE |
| 7 | 2026-02-17 | Re-run regression tests landing/pricing/payment (`subscriptions.tests`, `pages.tests`, `referensi.tests.test_pricing_management`) | - | DONE |

---

## Checklist Sign-off

- [x] Fungsional OK (redirect auth, pricing dynamic, CTA links valid)
- [ ] Keamanan OK (no XSS/injection risk identified, CSRF handled by base)
- [ ] Performa OK (inline CSS not cached separately - F-5)
- [ ] UX/UI OK (hero responsive perlu validasi - F-6, branding - F-8)
- [ ] Responsive OK (perlu manual testing mobile/tablet - F-6)
- [x] SEO OK (meta description + OG tags sudah aktif)
- [ ] Reviewer sign-off

**Reviewer:** Codex
**Tanggal sign-off:** 2026-02-17 (partial - responsive/performance/brand copy belum pass)
