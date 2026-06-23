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
| TC-3 | Webhook with missing signature | 400 Bad Request | `[~]` | Aktual: signature `None` → verify gagal → **403** (bukan 400). Body non-JSON → 400 |
| TC-4 | Replay attack (same notification twice) | Idempotent, no double-process | `[x]` | `select_for_update` + guard berbasis `paid_at`; diuji `PaymentWebhookIdempotencyTests` |
| TC-4b | Replay settlement **setelah** refund/cancel/deny | Tetap idempotent, tak re-activate | `[x]` | SUB-1: replay `settlement` setelah `refund` tidak re-activate karena `paid_at` dipertahankan |
| TC-5 | Webhook for non-existent order_id | 404, logged | `[x]` | `views.py:150-152` |
| TC-6 | Status: capture/settlement | subscription activated | `[x]` | `_handle_success` |
| TC-7 | Status: deny/cancel/expire | subscription NOT activated | `[x]` | pending → terminal; late terminal setelah aktivasi diabaikan |
| TC-8 | Status: pending | No change, await next | `[x]` | komentar eksplisit "keep as pending" |
| TC-9 | Refund notification | Handle gracefully | `[x]` | SUB-1: set `REFUND` + revoke akses; marker `paid_at` tetap ada |
| TC-10 | Request body tampering | Signature mismatch → reject | `[x]` | SUB-5: settlement di-cross-check ke field bertanda tangan (`status_code`/`gross_amount`); body tampering pada `transaction_status` tak meng-aktivasi |
| TC-11 | CSRF exempt justified | Webhook dari external service | `[x]` | `@method_decorator(csrf_exempt)` |
| TC-12 | Rate limiting pada webhook endpoint | Prevent abuse | `[ ]` | **A6**: belum ada |
| TC-13 | Logging webhook events | Audit trail for debugging | `[x]` | `logger.warning/info/exception` + simpan `midtrans_response` |
| TC-14 | Webhook timeout handling | Response < 5 detik | `[x]` | aktivasi lokal (tanpa call eksternal). **Catatan:** bila REC A2 menambah call Status API, jaga agar tetap cepat / asinkron |

---

## Temuan (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| **A4** | 🟢 FIXED (SUB-5) | Sebelum aktivasi `capture/settlement`, webhook kini cross-check field **bertanda tangan** (`status_code=='200'` + `gross_amount`==`amount` via Decimal-normalize) terhadap record (`_settlement_payload_is_consistent`). Body tampering pada `transaction_status`/`fraud_status` (yang tak ditandatangani) tak lagi cukup untuk meng-aktivasi. Jalur otoritatif API tetap dipakai reconcile (SUB-4) untuk kasus recovery. | `subscriptions/views.py:_settlement_payload_is_consistent` | Regression: `WebhookSettlementCrossCheckTests` (3/3) |
| **A5** | 🟢 FIXED (SUB-1) | `refund` susulan mencabut akses PRO dan late `cancel/deny/expire` tidak lagi menimpa transaksi yang sudah aktif. (Detail di [02 Payment Flow](02_Payment_Flow.md).) | `subscriptions/views.py`, `accounts/models.py` | Regression SUB-1 |
| **A6** | 🟠 MED | Endpoint webhook publik tanpa rate limiting (TC-12). | `subscriptions/views.py:118-189` | Telaah kode |
| **A7** | 🟡 LOW | Perbandingan signature `==` (non constant-time). | `subscriptions/midtrans.py:143` | Telaah kode |
| **A8** | ℹ️ INFO | Kalibrasi respons webhook. Signature diverifikasi **sebelum** lookup order, jadi 404 hanya terjadi untuk notifikasi **bertanda tangan sah** namun order tak dikenal — ini yang memicu retry Midtrans dan boleh dijadikan 200 + logging/alerting. **403 untuk signature tidak sah sudah tepat dan TIDAK boleh diganti 200.** | `subscriptions/views.py:144,152` | Telaah kode + dok Midtrans |
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
| 3 | - | Rate limit webhook (A6) | - | TODO |
| 4 | - | Constant-time compare (A7) | - | TODO |

---

## Checklist Sign-off

- [~] Signature verification bulletproof (algoritma ✓ / cakupan field ✓ cross-check SUB-5 / compare non-CT → A7)
- [x] Replay protection untuk duplicate/replay terminal (A11 tertutup oleh SUB-1)
- [x] Status transitions correct untuk refund + late terminal setelah success (A5 tertutup oleh SUB-1)
- [x] Aktivasi bebas lost-update saat konkuren (A12 tertutup ACC-1; lock lintas-koneksi perlu gate PG)
- [x] No CSRF vulnerability (exempt beralasan)
- [x] Logging adequate
- [ ] Rate limiting (→ A6)
- [ ] Reviewer sign-off
