# R3.3 - Review Midtrans Integration

**Status:** `[~]` AUDIT KODE (STATIC) — 1 HIGH (A1), 1 MED (A2), 1 LOW (A7); perbaikan pending
**Terakhir diperbarui:** 2026-06-23 (Claude Code, telaah kode statis)

> Legenda status test: `[x]` terverifikasi via kode/test · `[~]` sebagian / ada temuan / perlu UAT runtime · `[ ]` perlu eksekusi live

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| File | `subscriptions/midtrans.py` |
| Functions | `create_snap_token()`, `verify_signature()`, `get_transaction_status()` |
| Env Vars | `MIDTRANS_SERVER_KEY`, `MIDTRANS_CLIENT_KEY`, `MIDTRANS_IS_PRODUCTION` |

---

## Audit Fungsional & Keamanan

### Test Cases

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-1 | Server key tidak di-expose ke frontend | Hanya client key di template | `[x]` | hanya `MIDTRANS_CLIENT_KEY` masuk context |
| TC-2 | Sandbox vs Production toggle | `MIDTRANS_IS_PRODUCTION` env var | `[x]` | SUB-3: backend ✓ (`midtrans.py:44-51`) + frontend Snap.js kini ikut flag; diuji `CheckoutSnapJsToggleTests` |
| TC-3 | Snap token request format | Sesuai Midtrans API spec | `[x]` | `transaction_details`/`item_details`/`callbacks` lengkap |
| TC-4 | Signature verification algorithm | SHA512 sesuai Midtrans docs | `[x]` | `SHA512(order_id+status_code+gross_amount+server_key)` |
| TC-5 | Invalid signature rejection | Request ditolak | `[x]` | webhook → 403 (diuji `test_duplicate_success_callback_is_idempotent` mem-bypass dengan mock) |
| TC-6 | Timeout handling | Graceful pada network timeout | `[x]` | `timeout=30` + `except RequestException` |
| TC-7 | Error response dari Midtrans | Logged + user-friendly error | `[x]` | `logger.error` + `MidtransError` |
| TC-8 | Idempotency pada retry | Tidak double-charge | `[x]` | webhook idempotent ✓; SUB-4: reconcile memulihkan paid-but-pending bila webhook terlewat (jalur aktivasi sama) |

---

## Temuan (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| **A1** | 🟢 FIXED (SUB-3) | Toggle produksi kini lengkap: backend (`MidtransClient`) dan frontend (template checkout via `midtrans_is_production`) sama-sama mengikuti `MIDTRANS_IS_PRODUCTION`. Detail di [01](01_Checkout_Page.md). | `subscriptions/midtrans.py:44-51`, `templates/subscriptions/checkout.html`, `views.py:CheckoutView` | Regression: `CheckoutSnapJsToggleTests` |
| **A2** | 🟢 FIXED (SUB-4) | `reconcile_pending_payments` (service) memakai `get_transaction_status` untuk memulihkan transaksi paid-but-pending lewat jalur aktivasi yang sama (`mark_paid_and_activate`). Dijalankan via Celery task `subscriptions.reconcile_pending_payments` (beat tiap 15 menit) + management command manual. `get_transaction_status` tak lagi dead-code. | `subscriptions/reconciliation.py`, `subscriptions/tasks.py`, `config/celery.py`, `management/commands/reconcile_pending_payments.py` | Regression: `PendingPaymentReconciliationTests` (6/6) |
| **A7** | 🟡 LOW | `verify_signature` membandingkan dengan `==` (bukan constant-time). Praktik aman: `hmac.compare_digest`. Dampak rendah (server-to-server HTTPS), tetapi mudah dikeraskan. | `subscriptions/midtrans.py:143` | Telaah kode |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Lengkapi toggle produksi di frontend (lihat REC-1 doc [01](01_Checkout_Page.md)). | P0 | Low | A1 |
| REC-2 | Buat management command `reconcile_pending_payments` (cron) yang memanggil `get_transaction_status` untuk transaksi `pending` berumur > X menit, lalu jalankan jalur aktivasi yang sama. Sekaligus memakai method yang kini dead code. | P0 | Med | A2 |
| REC-3 | Ganti `==` dengan `hmac.compare_digest` di `verify_signature`. | P1 | Low | A7 |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-06-23 | Audit kode statis Midtrans client; temuan A1/A2/A7 tercatat | - | DONE (audit) |
| 1b | 2026-06-23 | SUB-3: lengkapi toggle produksi di frontend Snap.js (A1) | branch `fix/subscriptions-sub3-snap-toggle` | DONE |
| 2 | 2026-06-23 | SUB-4: service+task+command+beat reconcile paid-but-pending (A2) | branch `fix/subscriptions-sub4-reconcile` | DONE |
| 3 | - | Constant-time signature (A7) | - | TODO |

---

## Checklist Sign-off

- [x] Server key secure
- [x] Signature verification correct (algoritma)
- [x] Production/sandbox toggle works (backend ✓ / frontend ✓ SUB-3)
- [x] Error handling robust
- [x] No double-charge risk (idempotent ✓ / recovery webhook terlewat ✓ SUB-4)
- [ ] Reviewer sign-off
