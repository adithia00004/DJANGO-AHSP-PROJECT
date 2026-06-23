# R3.5 - Review Webhook Security

**Status:** `[~]` AUDIT KODE + SUB-1 FIX — A5/A11 tertutup; A4/A6/A7/A8/A12 pending/tercatat
**Terakhir diperbarui:** 2026-06-23 (Claude Code, telaah kode statis; SUB-1 oleh Codex)

> Legenda status test: `[x]` terverifikasi via kode/test · `[~]` sebagian / ada temuan / perlu UAT runtime · `[ ]` perlu eksekusi live

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/subscriptions/webhook/midtrans/` |
| View | `subscriptions.views.PaymentWebhookView` |
| Method | POST (CSRF exempt) |
| Auth | Midtrans signature verification (SHA512) |

---

## Audit Keamanan (CRITICAL)

### Test Cases

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-1 | Valid webhook with correct signature | Process + update transaction | `[x]` | `views.py:128-183` |
| TC-2 | Webhook with invalid signature | 403 Forbidden, no processing | `[x]` | `views.py:140-144` |
| TC-3 | Webhook with missing signature | 400 Bad Request | `[x]` | Kalibrasi A8: signature hilang/salah → **403** (benar); body non-JSON → 400. SUB-6: `verify_signature` tolak non-`str` |
| TC-4 | Replay attack (same notification twice) | Idempotent, no double-process | `[x]` | `select_for_update` + guard berbasis `paid_at`; diuji `PaymentWebhookIdempotencyTests` |
| TC-4b | Replay settlement **setelah** refund/cancel/deny | Tetap idempotent, tak re-activate | `[x]` | SUB-1: replay `settlement` setelah `refund` tidak re-activate karena `paid_at` dipertahankan |
| TC-5 | Webhook for non-existent order_id | 404, logged | `[x]` | SUB-6 (A8): valid-sig + order tak dikenal → **200**+log (Midtrans berhenti retry); bad-sig tetap 403 |
| TC-6 | Status: capture/settlement | subscription activated | `[x]` | `_handle_success` |
| TC-7 | Status: deny/cancel/expire | subscription NOT activated | `[x]` | pending → terminal; late terminal setelah aktivasi diabaikan |
| TC-8 | Status: pending | No change, await next | `[x]` | komentar eksplisit "keep as pending" |
| TC-9 | Refund notification | Handle gracefully | `[x]` | SUB-1: set `REFUND` + revoke akses; marker `paid_at` tetap ada |
| TC-10 | Request body tampering | Signature mismatch → reject | `[x]` | SUB-5: settlement di-cross-check ke field bertanda tangan (`status_code`/`gross_amount`); body tampering pada `transaction_status` tak meng-aktivasi |
| TC-11 | CSRF exempt justified | Webhook dari external service | `[x]` | `@method_decorator(csrf_exempt)` |
| TC-12 | Rate limiting pada webhook endpoint | Prevent abuse | `[~]` | D-2: webhook rate-limit → **edge/WAF** (runbook ops, di luar kode). `create_payment` di-throttle app-level (SUB-6) |
| TC-13 | Logging webhook events | Audit trail for debugging | `[x]` | `logger.warning/info/exception` + simpan `midtrans_response` |
| TC-14 | Webhook timeout handling | Response < 5 detik | `[x]` | aktivasi lokal (tanpa call eksternal). **Catatan:** bila REC A2 menambah call Status API, jaga agar tetap cepat / asinkron |

---

## Temuan (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| **A4** | 🟢 FIXED (SUB-5) | Sebelum aktivasi `capture/settlement`, webhook kini cross-check field **bertanda tangan** (`status_code=='200'` + `gross_amount`==`amount` via Decimal-normalize) terhadap record (`_settlement_payload_is_consistent`). Body tampering pada `transaction_status`/`fraud_status` (yang tak ditandatangani) tak lagi cukup untuk meng-aktivasi. Jalur otoritatif API tetap dipakai reconcile (SUB-4) untuk kasus recovery. | `subscriptions/views.py:_settlement_payload_is_consistent` | Regression: `WebhookSettlementCrossCheckTests` (3/3) |
| **A5** | 🟢 FIXED (SUB-1) | `refund` susulan mencabut akses PRO dan late `cancel/deny/expire` tidak lagi menimpa transaksi yang sudah aktif. (Detail di [02 Payment Flow](02_Payment_Flow.md).) | `subscriptions/views.py`, `accounts/models.py` | Regression SUB-1 |
| **A6** | 🟢 FIXED (SUB-6) | `create_payment` di-throttle app-level (5/60s per user → 429 `RATE_LIMIT_EXCEEDED`). Rate-limit **webhook → edge/WAF** (D-2, di luar kode) agar notifikasi Midtrans yang sah tak ikut terblokir. | `subscriptions/views.py:CreatePaymentView` | Regression: `CreatePaymentRateLimitTests` |
| **A7** | 🟢 FIXED (SUB-6) | `verify_signature` kini `hmac.compare_digest` (constant-time) + tolak signature non-`str`. | `subscriptions/midtrans.py:verify_signature` | Regression: `SignatureVerificationTests` (3/3) |
| **A8** | 🟢 FIXED (SUB-6) | Webhook untuk order **bertanda tangan sah namun tak dikenal** kini balas **200**+log (Midtrans berhenti retry); **403 untuk signature tidak sah dipertahankan**. | `subscriptions/views.py` | Regression: `WebhookUnknownOrderTests` (2/2) |
| **A11** | 🟢 FIXED (SUB-1) | Idempotensi aktivasi sekarang berbasis `paid_at is not None`; replay `settlement` setelah `refund` tidak mengaktifkan/memperpanjang ulang. | `subscriptions/views.py`, `accounts/models.py` | Regression: `test_replay_settlement_after_refund_does_not_reactivate` |
| **A12** | 🟢 FIXED (ACC-1) | `activate_subscription` kini mengunci baris user (`select_for_update`) dan menghitung dari nilai terkunci → pembayaran konkuren menumpuk. (Detail di [02 Payment Flow](02_Payment_Flow.md).) Lock lintas-koneksi penuh perlu gate PostgreSQL 15. | `accounts/models.py:activate_subscription` | Regression: `ActivateSubscriptionAtomicityTests` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Untuk `capture/settlement`, re-fetch status otoritatif via `get_transaction_status()` sebelum aktivasi (defense-in-depth), atau minimal validasi pemetaan `status_code ↔ transaction_status` dan cocokkan `gross_amount` dengan `amount`/snapshot. | P1 | Med | A4, A2 |
| REC-2 | Tetapkan kebijakan refund/cancel + jaga transisi status (lihat REC-2 doc [02](02_Payment_Flow.md)). | P2 | Med | A5 |
| REC-3 | Terapkan rate limiting pada endpoint webhook. | P1 | Low | A6 |
| REC-4 | `hmac.compare_digest` untuk signature. | P1 | Low | A7 |
| REC-5 | Balas 200 (setelah logging/alerting) untuk order **bertanda tangan sah** namun tak dikenal agar Midtrans berhenti retry; pertahankan 403 untuk signature gagal. | P3 | Low | A8 |
| REC-6 | Dasarkan idempotensi pada `paid_at is not None`/flag aktivasi terpisah dan tolak transisi mundur dari `success` (selaras REC-5 doc [02](02_Payment_Flow.md)). | P0 | Low | A11 |
| REC-7 | Kunci baris user / update atomik `F()` saat aktivasi (selaras REC-6 doc [02](02_Payment_Flow.md)). | P1 | Med | A12 |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-06-23 | Audit kode statis Webhook Security; temuan A4/A5/A6/A7/A8 tercatat | - | DONE (audit) |
| 1b | 2026-06-23 | Verifikasi independen: A8→INFO (403 dipertahankan), tambah A11 (replay re-activate, HIGH) & A12 (lost update) | - | DONE (audit) |
| 1c | 2026-06-23 | SUB-1: idempotensi aktivasi berbasis `paid_at`, refund revoke, dan late terminal guard (A5/A11) | - | DONE |
| 2 | 2026-06-23 | SUB-5: cross-check field bertanda tangan (status_code/gross_amount-Decimal) sebelum aktivasi (A4) | branch `fix/subscriptions-sub5-webhook-verify` | DONE |
| 3 | 2026-06-23 | SUB-6: rate-limit `create_payment` app-level (A6); webhook→edge/WAF (D-2) | branch `fix/subscriptions-sub6-webhook-hardening` | DONE |
| 4 | 2026-06-23 | SUB-6: `hmac.compare_digest` (A7) + 200-untuk-valid-sig-unknown (A8) | branch `fix/subscriptions-sub6-webhook-hardening` | DONE |

---

## Checklist Sign-off

- [x] Signature verification bulletproof (algoritma ✓ / cakupan field ✓ cross-check SUB-5 / compare constant-time ✓ SUB-6)
- [x] Replay protection untuk duplicate/replay terminal (A11 tertutup oleh SUB-1)
- [x] Status transitions correct untuk refund + late terminal setelah success (A5 tertutup oleh SUB-1)
- [x] Aktivasi bebas lost-update saat konkuren (A12 tertutup ACC-1; lock lintas-koneksi perlu gate PG)
- [x] No CSRF vulnerability (exempt beralasan)
- [x] Logging adequate
- [x] Rate limiting (`create_payment` app-level SUB-6; webhook→edge/WAF D-2)
- [ ] Reviewer sign-off
