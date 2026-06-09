# R1.2 - Review Pricing Page

**Status:** `[!]` SELESAI DIREVIEW - ADA TEMUAN
**Terakhir diperbarui:** 2026-02-17

---

Catatan:
- Full audit R1 sudah dijalankan ulang pada 2026-02-17 setelah update UI frontend.
- Temuan yang tersisa di dokumen ini dianggap aktif (bukan temuan sementara).

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/pricing/` |
| View | `pages.views.PricingPageView` (TemplateView) |
| Template | `pages/templates/pages/pricing.html` (78 baris) |
| Extends | `pages/templates/pages/landing.html` (inherit topbar/footer/extra_js) |
| Auth Required | Tidak (public page, authenticated user tetap bisa akses pricing) |
| Context | `pricing_plans` via shared pricing service (`subscriptions.pricing_service`) |
| Legacy Route | `/subscriptions/pricing/` -> redirect ke `/pricing/` |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Tampilan semua paket langganan | Semua plan tampil dengan harga benar | `[x]` | OK - pricing data dari shared service |
| TC-2 | Perbandingan fitur antar paket | Tabel fitur akurat | `[!]` | GAGAL - belum ada tabel perbandingan fitur dedicated |
| TC-3 | CTA "Pilih Paket" per plan | Navigasi ke checkout dengan `plan_id` benar | `[x]` | OK - user login diarahkan ke `subscriptions:checkout` |
| TC-4 | Harga konsisten dengan database | Harga match `SubscriptionPlan` + promo aktif | `[x]` | OK - dihitung server-side via pricing service |
| TC-5 | Responsive - Mobile | Cards stack, readable | `[~]` | Perlu validasi visual manual |
| TC-6 | Anonymous user klik CTA | Redirect ke signup | `[x]` | OK - tetap ke signup |
| TC-7 | Authenticated user klik CTA | Langsung ke checkout | `[x]` | OK - diverifikasi di test `pages.tests.PricingPageIntegrationTests.test_authenticated_user_cta_goes_to_checkout` |
| TC-8 | Highlight recommended plan | Visual distinction jelas | `[x]` | OK - `popular` class + badge |
| TC-9 | Navigasi topbar anchor links (`#features`, `#faq`) | Link mengarah ke section valid | `[x]` | PASS - link `#features/#faq` di pricing kini diarahkan ke landing (`/#features`, `/#faq`) |
| TC-10 | Akses `/subscriptions/pricing/` (pricing alternatif) | Tidak 500, route valid | `[x]` | OK - redirect ke `/pricing/` |
| TC-11 | Saat promo aktif, pricing card tampil harga promo | Harga promo + harga awal dicoret tampil | `[x]` | OK - sinkron dengan service pricing backend |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | CTA pricing sekarang conditional: user login dengan `plan.id` diarahkan ke checkout, non-login tetap ke signup. | `pages/templates/pages/pricing.html` | Evidence test PASS: `pages.tests.PricingPageIntegrationTests.test_authenticated_user_cta_goes_to_checkout` |
| F-2 | **MEDIUM** | Tidak ada redirect untuk authenticated users dari `/pricing/`. Ini sekarang keputusan produk, tapi perlu dipastikan konsisten dengan landing redirect policy. | `pages/views.py` | Authenticated user bisa tetap melihat pricing page |
| F-3 | **MEDIUM** | `pricing.html` masih extends `landing.html`, sehingga mewarisi CSS/JS landing yang tidak semuanya relevan untuk pricing dedicated page. | `pages/templates/pages/pricing.html` | Inheritance chain: pricing -> landing -> base |
| F-4 | **MEDIUM** | Belum ada tabel perbandingan fitur dedicated. Pricing page masih card-based seperti landing. | `pages/templates/pages/pricing.html` | Tidak ada section table comparison |
| F-5 | **LOW** | CTA section masih klaim "ribuan profesional" (klaim marketing belum diverifikasi). | `pages/templates/pages/pricing.html` | Copywriting belum disesuaikan |
| F-6 | **RESOLVED (was LOW)** | SEO meta tags spesifik pricing (`description`, OG tags) sudah ditambahkan. | `pages/templates/pages/pricing.html:6` | Recheck render 2026-02-17: `pricing_meta_description=True`, `pricing_og_title=True` |
| F-7 | **RESOLVED (was LOW)** | `PricingPageView` tidak lagi instantiate `LandingPageView()` object untuk context. | `pages/views.py` | Context pricing via static helper + service shared |
| F-8 | **RESOLVED (was HIGH)** | Broken topbar anchor links pada pricing dedicated sudah diperbaiki dengan navigasi ke landing anchors untuk `features/faq`. | `pages/templates/pages/pricing.html:37` | Link aktif: `{% url 'pages:landing' %}#features` dan `{% url 'pages:landing' %}#faq` |
| F-9 | **RESOLVED (was CRITICAL)** | Route legacy `/subscriptions/pricing/` tidak lagi 500; sekarang redirect ke route utama `/pricing/`. | `subscriptions/views.py` | Evidence test PASS: `subscriptions.tests.SubscriptionPricingRouteTests.test_legacy_pricing_route_redirects_to_primary_pricing_page` |
| F-10 | **RESOLVED (was MEDIUM)** | Visual pricing page saat promo aktif kini sinkron: badge promo, harga awal dicoret, nama promo tampil dari backend. | `pages/templates/pages/pricing.html` | Evidence: `discount_amount/base_price_display/promotion_name` dirender dari service; test PASS `pages.tests.PricingPageIntegrationTests` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Tambahkan conditional checkout link untuk authenticated users | P0 | Low | F-1 (`[DONE]`) |
| REC-2 | Tegaskan keputusan produk: authenticated user boleh tetap melihat pricing atau di-redirect | P1 | Low | F-2 |
| REC-3 | Pertimbangkan `pricing.html` extends `base.html` langsung untuk payload lebih bersih | P1 | Medium | F-3 |
| REC-4 | Tambahkan tabel perbandingan fitur detail | P2 | Medium | F-4 |
| REC-5 | Tambahkan meta description + OG tags spesifik pricing | P1 | Low | F-6 (`[DONE]`) |
| REC-6 | Gunakan shared utility/service untuk pricing context antar view | P1 | Low | F-7 (`[DONE]`) |
| REC-7 | Selaraskan topbar links dengan section yang benar di halaman pricing | P0 | Low | F-8 (`[DONE]`) |
| REC-8 | SSOT route pricing: redirect `/subscriptions/pricing/` ke `/pricing/` | P0 | Low | F-9 (`[DONE]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-16 | CTA pricing page untuk authenticated user diarahkan ke checkout plan | - | DONE |
| 2 | 2026-02-16 | Refactor source pricing context ke shared service (tanpa instantiate LandingPageView object) | - | DONE |
| 3 | 2026-02-16 | Route legacy `/subscriptions/pricing/` diubah menjadi redirect ke `/pricing/` | - | DONE |
| 4 | 2026-02-17 | Revalidasi non-UI PASS: legacy route pricing redirect, CTA auth ke checkout, dan server-side pricing integrity transaksi | - | DONE |
| 5 | 2026-02-17 | Full audit pasca update UI: verifikasi ulang inherited anchor nav, SEO/meta pricing, dan konsistensi struktur extends | - | DONE |
| 6 | 2026-02-17 | Implementasi fix prioritas pricing: SEO meta tags + topbar nav diarahkan ke landing anchors valid | - | DONE |
| 7 | 2026-02-17 | Sinkronisasi visual promo pricing card dengan backend pricing service (harga coret + nama promo) | - | DONE |

---

## Checklist Sign-off

- [x] Fungsional OK (checkout CTA auth + route legacy pricing sudah valid)
- [x] Keamanan OK (public page, no new injection surface)
- [x] Performa OK (tidak ada query diskon di template)
- [ ] UX/UI OK (feature comparison table masih perlu tindak lanjut)
- [ ] Responsive OK (perlu manual testing)
- [ ] Reviewer sign-off

**Reviewer:** Codex
**Tanggal sign-off:** 2026-02-17 (partial - feature comparison & responsive follow-up)
