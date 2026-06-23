# R3.2 - Review Payment Flow (Midtrans Snap)

**Status:** `[~]` AUDIT KODE + SUB-1 FIX — A5/A11 tertutup; A3/A6/A10a/A12 pending
**Terakhir diperbarui:** 2026-06-23 (Claude Code, telaah kode statis; SUB-1 oleh Codex)

> Legenda status test: `[x]` terverifikasi via kode/test · `[~]` sebagian / ada temuan / perlu UAT runtime · `[ ]` perlu eksekusi live

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

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-1 | Create payment → Snap token generated | snap_token returned | `[x]` | `views.py:85-95` |
| TC-2 | order_id uniqueness | Unique per transaction | `[x]` | SUB-2: order_id dari UUID pk transaksi + single-insert; diuji `PaymentOrderIdUniquenessTests` |
| TC-3 | Amount matches plan price | Server-side price, not client | `[x]` | diuji `test_create_payment_uses_server_side_effective_pricing` |
| TC-4 | Duplicate payment prevention | Block if pending exists | `[x]` | SUB-9 (A10a): reuse transaksi `pending` ≤30 menit (amount cocok + snap_token) alih-alih buat baru; diuji `test_rapid_double_create_reuses_recent_pending` |
| TC-5 | Midtrans API error handling | Graceful error message | `[x]` | `except MidtransError` → 500 + pesan generik |
| TC-6 | Staff/admin create payment | Diblok | `[x]` | diuji `test_create_payment_blocks_staff_user` (403 `ADMIN_CHECKOUT_BLOCKED`) |

### Payment Finish (Redirect)

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-7 | Payment success redirect | Status updated, redirect dashboard | `[x]` | `views.py:229-240` |
| TC-8 | Payment pending redirect | Status pending, info message | `[x]` | `views.py:241-245` |
| TC-9 | Payment failed redirect | Error message, retry option | `[x]` | `views.py:246-250` |
| TC-10 | Transaction not found | 404 / error | `[x]` | filter `user=request.user` → pesan error |

### Transaction Model

| # | Test Case | Expected | Status | Catatan |
|---|-----------|----------|--------|---------|
| TC-11 | PaymentTransaction created on init | All fields populated | `[x]` | snapshot harga/promo dibekukan |
| TC-12 | Status transitions valid | pending→success, pending→failed | `[x]` | SUB-1: late `cancel/deny/expire` setelah aktivasi diabaikan; `refund` revoke akses |
| TC-13 | paid_at timestamp set on success | Timestamp accurate | `[x]` | `_handle_success` set `timezone.now()` |
| TC-14 | subscription_end_date updated | Correct duration added | `[x]` | diuji `test_success_callback_uses_duration_snapshot_for_activation` |

---

## Temuan (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| **A3** | 🟢 FIXED (SUB-2) | `generate_order_id()` kini berbasis UUID pk transaksi (`f"AHSP-{user_id}-{id.hex}"`, unik per transaksi, tersedia sebelum save) menggantikan timestamp detik; `CreatePaymentView` membangun transaksi + set `order_id` sebelum **satu** `save()`, menghapus window `order_id=''`. Double-submit/konkuren tak lagi tabrakan. | `subscriptions/models.py:generate_order_id`, `subscriptions/views.py:CreatePaymentView` | Regression: `PaymentOrderIdUniquenessTests` (3/3) |
| **A5** | 🟢 FIXED (SUB-1) | Notifikasi `refund` kini set `REFUND` + revoke subscription user; late `cancel/deny/expire` setelah aktivasi tidak lagi menimpa transaksi `success`. | `subscriptions/views.py`, `accounts/models.py` | Regression: `test_refund_after_success_revokes_access`, `test_late_deny_after_success_does_not_overwrite_success` |
| **A6** | 🟢 FIXED (SUB-6) | `CreatePaymentView` di-throttle per-user via cache (5/60s → 429 `RATE_LIMIT_EXCEEDED`) sebelum membuat baris/memanggil Midtrans. | `subscriptions/views.py:CreatePaymentView` | Regression: `CreatePaymentRateLimitTests` |
| **A10a** | 🟢 FIXED (SUB-9) | `CreatePaymentView` me-reuse transaksi `pending` yang masih segar (≤30 menit), ber-`amount` sesuai harga efektif terkini, dan ber-`snap_token` — alih-alih menumpuk baris + call Midtrans baru tiap klik. | `subscriptions/views.py:CreatePaymentView` | Regression: `test_rapid_double_create_reuses_recent_pending` |
| **A11** | 🟢 FIXED (SUB-1) | Idempotensi aktivasi kini berbasis marker `paid_at is not None`, bukan `status`. Replay `settlement` setelah `refund` tidak mengaktifkan ulang karena `paid_at` tetap dipertahankan. Detail webhook di [05](05_Webhook_Security.md). | `subscriptions/views.py`, `accounts/models.py` | Regression: `test_refund_preserves_activation_marker`, `test_replay_settlement_after_refund_does_not_reactivate` |
| **A12** | 🟢 FIXED (ACC-1) | `activate_subscription` kini re-read baris user di bawah `select_for_update` dalam `atomic` dan menghitung `subscription_end_date` dari nilai terkunci → dua pembayaran konkuren menumpuk, bukan saling menimpa. **Terverifikasi di PG15** (SUB-7: `ActivateSubscriptionConcurrencyPgTests` — 2 thread menumpuk di bawah row-lock); test SQLite membuktikan perbaikan stale-instance. | `accounts/models.py:activate_subscription` | Regression: `ActivateSubscriptionAtomicityTests` (2/2) + PG concurrency (1/1) |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Set `order_id` **atomik** di dalam satu `create()` memakai komponen unik (UUID pk transaksi atau `uuid4().hex[:12]`); hapus pola save-ganda dan window `order_id=''`. | P0 | Low | A3 |
| REC-2 | Tetapkan kebijakan eksplisit untuk `refund`/`cancel`/`deny` susulan (cabut akses bila refund?) dan jaga agar status tidak mundur dari `success` tanpa penanganan langganan yang menyertainya. | P2 | Med | A5 |
| REC-3 | Terapkan `django-ratelimit` pada `create_payment` (pola yang sudah dipakai app lain, lih. TA-07). | P1 | Low | A6 |
| REC-4 | Pertimbangkan reuse transaksi `pending` aktif (atau batasi jumlah) alih-alih selalu membuat baru. | P3 | Low | A10a |
| REC-5 | Dasarkan idempotensi aktivasi pada `paid_at is not None` (atau flag `activated` terpisah), bukan pada `status` yang bisa diturunkan; tolak/abaikan transisi mundur dari `success`. | P0 | Low | A11 |
| REC-6 | Kunci baris user saat aktivasi (`select_for_update` pada user, atau gunakan update atomik `F()`-expression untuk `subscription_end_date`) agar dua pembayaran konkuren tidak saling menimpa. | P1 | Med | A12 |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-06-23 | Audit kode statis Payment Flow; temuan A3/A5/A6/A10a tercatat | - | DONE (audit) |
| 1b | 2026-06-23 | Verifikasi independen (Codex + Claude): tambah A11 (replay re-activate) & A12 (lost update) | - | DONE (audit) |
| 2 | 2026-06-23 | SUB-2: order_id atomik (UUID pk) + hapus window `order_id=''` (A3) | branch `fix/subscriptions-sub2-order-id` | DONE |
| 3 | 2026-06-23 | SUB-1: Kebijakan refund/transisi status (A5) + idempotensi replay setelah terminal (A11) | - | DONE |
| 3b | 2026-06-23 | ACC-1: aktivasi atomik re-read user (A12) + refund revoke hanya bila sole-paid (EC-1) | branch `fix/accounts-acc1-atomic-activation` | DONE |
| 4 | 2026-06-23 | SUB-6: rate-limit `create_payment` per-user 5/60s (A6) | branch `fix/subscriptions-sub6-webhook-hardening` | DONE |
| 5 | 2026-06-23 | SUB-9: reuse transaksi `pending` segar (A10a) + cek checkout `is_pro_active` (A10b) | branch `fix/subscriptions-sub9-pending-dedup` | DONE |

---

## Checklist Sign-off

- [x] Payment creation secure (auth, staff-block, server-side amount)
- [x] Amount verified server-side
- [x] Redirect handling correct
- [x] Transaction model integrity (transisi status mundur A5 tertutup oleh SUB-1)
- [x] order_id uniqueness robust (SUB-2: UUID pk + single-insert)
- [x] Aktivasi idempotent & bebas lost-update (A11 + A12 tertutup; lock lintas-koneksi A12 terverifikasi PG15 — SUB-7)
- [ ] Reviewer sign-off
