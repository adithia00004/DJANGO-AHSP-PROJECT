# R3.6 - Review Subscriptions Pricing Page

**Status:** `[~]` AUDIT KODE (STATIC) — tanpa temuan baru; catatan arsitektur (route = redirect)
**Terakhir diperbarui:** 2026-06-23 (Claude Code, telaah kode statis)

> Legenda status test: `[x]` terverifikasi via kode/test · `[~]` sebagian / ada temuan / perlu UAT runtime · `[ ]` perlu eksekusi live

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/subscriptions/pricing/` |
| View | `subscriptions.views.PricingPageView` |
| Perilaku aktual | **Redirect 302 → `pages:pricing`** (route legacy) |
| Logika harga | `subscriptions/pricing_service.py` (`get_active_pricing_plans`, `resolve_effective_plan_pricing`, `serialize_pricing_for_display`) |
| Template | ~~`subscriptions/templates/subscriptions/pricing.html`~~ (tidak ada; rendering kini di app `pages`) |
| Auth Required | Tidak (public) |

> **Catatan arsitektur:** Halaman pricing yang sebenarnya kini dirender oleh app `pages`. `PricingPageView` hanya `redirect("pages:pricing")` — diuji `SubscriptionPricingRouteTests.test_legacy_pricing_route_redirects_to_primary_pricing_page`. Audit halaman pricing **live** (tampilan, CTA, responsif) menjadi cakupan review app `pages`, di luar folder ini. Yang diaudit di sini adalah **logika penyedia harga** di `pricing_service.py` yang dikonsumsi halaman tersebut.

---

## Audit Fungsional

### Route legacy

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-0 | `/subscriptions/pricing/` | Redirect 302 ke `pages:pricing` | `[x]` | diuji `SubscriptionPricingRouteTests` |

### Logika harga (`pricing_service.py`, dikonsumsi halaman pricing)

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-1 | Semua plan aktif tampil | List plan `is_active=True` + `base_tier` 1-3 | `[x]` | `get_active_pricing_plans` filter benar |
| TC-2 | Harga plan konsisten | Harga efektif = base − diskon promo aktif | `[x]` | `resolve_effective_plan_pricing` (diuji `ScheduledPromotionPricingServiceTests`) |
| TC-3 | Promo aktif diterapkan, promo lampau/akan datang diabaikan | Window `start_at<=now<end_at` | `[x]` | diuji 3 kasus (not_started/active/expired) |
| TC-4 | Overlap promo → prioritas tertinggi lalu terbaru | `-priority, -created_at, -id` | `[x]` | diuji `test_overlap_uses_highest_priority_then_newest` |
| TC-5 | Plan inactive tidak tampil | Tidak dipilih dari UI | `[x]` | filter `is_active=True` |
| TC-6 | Diskon fixed di-cap ke base price | `final_price >= 0` | `[x]` | `if discount_amount > base_price: = base_price` + clean() |
| TC-7 | Format mata uang id-ID | `Rp 1.500.000` | `[x]` | `format_currency_idr` |
| TC-8 | N+1 promo dihindari | `Prefetch active_promotions_now` | `[x]` | prefetch dipakai di `get_active_pricing_plans` |
| TC-9 | Tampilan live (card, CTA, responsif) | — | `[ ]` | **cakupan app `pages`**, bukan folder ini |

---

## Temuan (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| - | INFO | Tidak ada temuan korektif pada logika harga. Service sudah server-side, ber-constraint DB, dan teruji. | `subscriptions/pricing_service.py` | Telaah kode + test |
| - | DOC | Baris "Template" pada dokumen ini sebelumnya menyebut `subscriptions/.../pricing.html` yang tidak ada; sudah dikoreksi — view hanya redirect. | `subscriptions/views.py:257-265` | Telaah kode |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Audit tampilan pricing **live** (CTA pilih plan, anonymous→login→checkout, responsif, fallback tanpa plan aktif) di review app `pages`. | P2 | Med | TC-9 |
| REC-2 | Pertimbangkan menghapus route legacy `subscriptions:pricing` bila tak ada konsumen, atau pertahankan sebagai redirect permanen (301) bila masih ada tautan lama. | P3 | Low | TC-0 |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-06-23 | Audit kode statis logika pricing + koreksi catatan arsitektur (route redirect) | - | DONE (audit) |

---

## Checklist Sign-off

- [x] Logika harga server-side & teruji
- [x] Data plan sinkron dengan DB (`is_active`, `base_tier`)
- [x] Promo window/priority benar
- [ ] Navigasi CTA ke checkout/login (cakupan app `pages`)
- [ ] UX/UI live (cakupan app `pages`)
- [ ] Reviewer sign-off
