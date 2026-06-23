# R3.1 - Review Checkout Page

**Status:** `[~]` AUDIT KODE (STATIC) — 1 temuan HIGH (A1), 1 LOW (A10b); perbaikan pending
**Terakhir diperbarui:** 2026-06-23 (Claude Code, telaah kode statis)

> Legenda status test: `[x]` terverifikasi via kode/test · `[~]` sebagian / ada temuan / perlu UAT runtime · `[ ]` perlu eksekusi live

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/subscriptions/checkout/<plan_id>/` |
| View | `subscriptions.views.CheckoutView` |
| Template | `subscriptions/templates/subscriptions/checkout.html` |
| Auth Required | Ya (`LoginRequiredMixin`) |
| Integrasi | Midtrans Snap JS |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-1 | Akses checkout dengan plan valid | Form checkout tampil | `[x]` | `views.py:278` render OK |
| TC-2 | Akses checkout dengan plan_id invalid | 404 / error message | `[x]` | `get_object_or_404` |
| TC-3 | Akses checkout plan non-aktif | Error / redirect | `[x]` | filter `is_active=True` → 404 |
| TC-4 | Detail plan (nama, harga, durasi) tampil | Data akurat dari DB | `[x]` | termasuk harga efektif promo |
| TC-5 | Tombol "Bayar Sekarang" | Trigger Midtrans Snap popup | `[x]` | SUB-3: host Snap.js mengikuti `MIDTRANS_IS_PRODUCTION`; diuji `CheckoutSnapJsToggleTests` |
| TC-6 | Anonymous user akses checkout | Redirect ke login | `[x]` | `LoginRequiredMixin` |
| TC-7 | User sudah PRO akses checkout | Handled gracefully | `[~]` | **A10b**: cek pakai `subscription_status=='PRO' and is_subscription_active`, idealnya `is_pro_active` |
| TC-8 | Responsive - Mobile | Checkout usable di mobile | `[ ]` | perlu UAT runtime |
| TC-9 | CSRF protection | Token present | `[x]` | `X-CSRFToken` + `{{ csrf_token }}` di template |
| TC-10 | Harga tidak bisa dimanipulasi client-side | Harga dari server | `[x]` | `resolve_effective_plan_pricing(plan)` server-side |
| TC-11 | Staff/admin akses checkout | Diblok dengan pesan | `[x]` | `_is_managed_access_user` → redirect dashboard (diuji `test_checkout_blocks_staff_user`) |

---

## Temuan (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| **A1** | 🟢 FIXED (SUB-3) | Template kini memilih host Snap.js (`app.midtrans.com` vs `app.sandbox.midtrans.com`) berdasarkan `midtrans_is_production` yang dikirim `CheckoutView`. Host sandbox hardcoded dihapus → produksi memuat Snap.js produksi. | `subscriptions/templates/subscriptions/checkout.html`, `subscriptions/views.py:CheckoutView` | Regression: `CheckoutSnapJsToggleTests` (2/2) |
| **A10b** | 🟡 LOW | Cek "sudah punya langganan aktif" memakai `request.user.subscription_status == 'PRO' and request.user.is_subscription_active`. Properti `is_subscription_active` juga `True` untuk TRIAL aktif, jadi logika bergantung pada gabungan dua cek; lebih tepat & ringkas memakai `is_pro_active`. | `subscriptions/views.py:286` | Telaah kode |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Kirim flag `midtrans_is_production` ke context view, lalu pilih URL Snap.js di template (`app.midtrans.com` vs `app.sandbox.midtrans.com`). Pertimbangkan juga memuat skrip dari satu sumber config agar tak ada string ganda. | P0 | Low | A1 |
| REC-2 | Ganti cek duplikasi langganan ke `request.user.is_pro_active`. | P3 | Low | A10b |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-06-23 | Audit kode statis Checkout Page; temuan A1/A10b tercatat | - | DONE (audit) |
| 2 | 2026-06-23 | SUB-3: Snap.js prod/sandbox via `midtrans_is_production` (A1) | branch `fix/subscriptions-sub3-snap-toggle` | DONE |
| 3 | - | Perbaikan A10b (`is_pro_active`) | - | TODO |

---

## Checklist Sign-off

- [x] Fungsional OK (render, 404, detail plan)
- [x] Keamanan OK (price tampering ✓ / CSRF ✓ / Snap.js prod ✓ SUB-3)
- [ ] Performa OK (perlu UAT)
- [ ] UX/UI OK (perlu UAT mobile)
- [ ] Reviewer sign-off
