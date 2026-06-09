# R3.5 - Review Webhook Security

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/subscriptions/webhook/midtrans/` |
| View | `subscriptions.views.PaymentWebhookView` |
| Method | POST (CSRF exempt) |
| Auth | Midtrans signature verification |

---

## Audit Keamanan (CRITICAL)

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Valid webhook with correct signature | Process + update transaction | `[ ]` |
| TC-2 | Webhook with invalid signature | 403 Forbidden, no processing | `[ ]` |
| TC-3 | Webhook with missing signature | 400 Bad Request | `[ ]` |
| TC-4 | Replay attack (same notification twice) | Idempotent, no double-process | `[ ]` |
| TC-5 | Webhook for non-existent order_id | 404, logged | `[ ]` |
| TC-6 | Status: capture/settlement | subscription activated | `[ ]` |
| TC-7 | Status: deny/cancel/expire | subscription NOT activated | `[ ]` |
| TC-8 | Status: pending | No change, await next | `[ ]` |
| TC-9 | Refund notification | Handle gracefully | `[ ]` |
| TC-10 | Request body tampering | Signature mismatch → reject | `[ ]` |
| TC-11 | CSRF exempt justified | Webhook dari external service | `[ ]` |
| TC-12 | Rate limiting pada webhook endpoint | Prevent abuse | `[ ]` |
| TC-13 | Logging webhook events | Audit trail for debugging | `[ ]` |
| TC-14 | Webhook timeout handling | Response < 5 detik | `[ ]` |

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

- [ ] Signature verification bulletproof
- [ ] Replay protection
- [ ] Status transitions correct
- [ ] No CSRF vulnerability
- [ ] Logging adequate
- [ ] Reviewer sign-off
