# R3.6 - Review Subscriptions Pricing Page

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/subscriptions/pricing/` |
| View | `subscriptions.views.PricingPageView` |
| Template | `subscriptions/templates/subscriptions/pricing.html` |
| Auth Required | Tidak (public), CTA lanjut ke checkout/login |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Semua plan aktif tampil | List plan sesuai DB (`is_active=True`) | `[ ]` |
| TC-2 | Harga plan konsisten | Harga sesuai `SubscriptionPlan` | `[ ]` |
| TC-3 | CTA pilih plan anonymous | Redirect ke login lalu kembali ke checkout | `[ ]` |
| TC-4 | CTA pilih plan user login | Masuk checkout plan yang dipilih | `[ ]` |
| TC-5 | Plan inactive tidak tampil | Tidak dapat dipilih dari UI | `[ ]` |
| TC-6 | Error state tanpa plan aktif | Pesan fallback jelas | `[ ]` |
| TC-7 | Responsive mobile | Card/table tetap terbaca | `[ ]` |

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
- [ ] Data plan sinkron dengan DB
- [ ] Navigasi CTA ke checkout/login benar
- [ ] UX/UI OK
- [ ] Reviewer sign-off
