# R3.1 - Review Checkout Page

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/subscriptions/checkout/<plan_id>/` |
| View | `subscriptions.views.CheckoutView` |
| Template | `subscriptions/templates/subscriptions/checkout.html` |
| Auth Required | Ya (login_required) |
| Integrasi | Midtrans Snap JS |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Akses checkout dengan plan valid | Form checkout tampil | `[ ]` |
| TC-2 | Akses checkout dengan plan_id invalid | 404 / error message | `[ ]` |
| TC-3 | Akses checkout plan non-aktif | Error / redirect | `[ ]` |
| TC-4 | Detail plan (nama, harga, durasi) tampil | Data akurat dari DB | `[ ]` |
| TC-5 | Tombol "Bayar Sekarang" | Trigger Midtrans Snap popup | `[ ]` |
| TC-6 | Anonymous user akses checkout | Redirect ke login | `[ ]` |
| TC-7 | User sudah PRO akses checkout | Handled gracefully | `[ ]` |
| TC-8 | Responsive - Mobile | Checkout usable di mobile | `[ ]` |
| TC-9 | CSRF protection | Token present | `[ ]` |
| TC-10 | Harga tidak bisa dimanipulasi client-side | Harga dari server | `[ ]` |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Belum ada temuan | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| - | Belum ada rekomendasi | - | - |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| - | - | Belum ada perbaikan | - | - |

---

## Checklist Sign-off

- [ ] Fungsional OK
- [ ] Keamanan OK (price tampering, CSRF)
- [ ] Performa OK
- [ ] UX/UI OK
- [ ] Reviewer sign-off
