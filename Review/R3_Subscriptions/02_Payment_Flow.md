# R3.2 - Review Payment Flow (Midtrans Snap)

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| Create Payment URL | `/subscriptions/payment/create/` (POST) |
| Finish URL | `/subscriptions/payment/finish/` (GET) |
| View | `subscriptions.views.CreatePaymentView`, `PaymentFinishView` |
| Midtrans Client | `subscriptions/midtrans.py` |
| Model | `PaymentTransaction` |

---

## Audit Fungsional

### Payment Creation

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Create payment → Snap token generated | snap_token returned | `[ ]` |
| TC-2 | order_id uniqueness | Unique per transaction | `[ ]` |
| TC-3 | Amount matches plan price | Server-side price, not client | `[ ]` |
| TC-4 | Duplicate payment prevention | Block if pending exists | `[ ]` |
| TC-5 | Midtrans API error handling | Graceful error message | `[ ]` |

### Payment Finish (Redirect)

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-6 | Payment success redirect | Status updated, redirect dashboard | `[ ]` |
| TC-7 | Payment pending redirect | Status pending, info message | `[ ]` |
| TC-8 | Payment failed redirect | Error message, retry option | `[ ]` |
| TC-9 | Transaction not found | 404 / error | `[ ]` |

### Transaction Model

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-10 | PaymentTransaction created on init | All fields populated | `[ ]` |
| TC-11 | Status transitions valid | pending→success, pending→failed | `[ ]` |
| TC-12 | paid_at timestamp set on success | Timestamp accurate | `[ ]` |
| TC-13 | subscription_end_date updated | Correct duration added | `[ ]` |

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

- [ ] Payment creation secure
- [ ] Amount verified server-side
- [ ] Redirect handling correct
- [ ] Transaction model integrity
- [ ] Error handling graceful
- [ ] Reviewer sign-off
