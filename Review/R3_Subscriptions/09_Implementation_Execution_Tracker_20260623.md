# R3.9 - Implementation Execution Tracker (Subscriptions)

**Mulai:** 2026-06-23
**Plan otoritatif:** [08_Implementation_Plan_20260623.md](08_Implementation_Plan_20260623.md)
**Registry temuan:** [00_Audit_Summary_20260623.md](00_Audit_Summary_20260623.md) (A1–A17)
**Status keseluruhan:** **M1+M2 SELESAI; M4 hampir tuntas; SUB-7 DITUNDA** — SUB-1..6 + ACC-1/ACC-2 + SUB-8/9 + **SUB-10/ACC-4 (A14)** DONE. Subscriptions+accounts **84/84**. Sisa: **ACC-3 (A16)** = M4 terakhir; **SUB-7 (A13, PG-gate, DITUNDA)**. Catatan: A12 (lock lintas-koneksi) & A13 perlu gate PostgreSQL 15 sebelum go-live.
**Baseline test (2026-06-23):** `test subscriptions` = **23/23 PASS**; `check` PASS; `makemigrations --check` PASS. Semua perubahan diukur terhadap baseline ini.

---

## 1. Aturan Tracking (kapan dokumen ini WAJIB diperbarui)

Perbarui dokumen ini setiap kali:
- sebuah item (SUB-*/ACC-*) **dimulai, selesai, diblokir, atau berubah scope**;
- ada **perubahan kode** (file dimodifikasi/ditambah/dihapus) → catat di §3 + §4;
- **keputusan** baru diambil atau keputusan lama berubah → catat di §5;
- **artefak ditambah atau dihapus** (command, migrasi, template, test, endpoint) → catat di §4;
- **baseline/test** menghasilkan kegagalan baru atau gate hijau → catat di §6;
- ditemukan kondisi yang **belum dibahas** dalam audit/plan → catat di §7 dan rujuk balik ke doc 00/08.

Aturan emas: **tidak ada perubahan kode tanpa baris di §3.** Tidak ada file baru/terhapus tanpa baris di §4.

### Status legend

| Status | Arti |
|---|---|
| `PENDING` | belum dimulai |
| `IN PROGRESS` | sedang dikerjakan |
| `BLOCKED` | tertahan keputusan/dependency |
| `DONE` | Definition of Done (doc 08) terpenuhi + test hijau |
| `DEFERRED` | ditunda dengan alasan + gate eksplisit |
| `REMOVED` | diselesaikan via cleanup/penghapusan |

---

## 2. Progress Work Item

> Paket SUB = `subscriptions/`; Paket ACC = `accounts/`. ⇄ = lintas-area.

| Item | Paket | Temuan | Prio | Status | Mulai | Selesai | Gate/Dependency | Branch/Commit |
|------|-------|--------|------|--------|-------|---------|-----------------|---------------|
| SUB-1 | SUB | A11+A5 | P0 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 6/6; full 52/52; check PASS; makemigrations PASS | `e9475bed` (branch `fix/subscriptions-sub1-idempotent-activation`) |
| SUB-2 | SUB | A3 | P0 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 3/3; full 55/55; check PASS; makemigrations no-changes | `3bbae422` (code) + `f4fa7a3d` (docs) |
| SUB-3 | SUB | A1 | P0 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 2/2; full 57/57; check PASS | branch `fix/subscriptions-sub3-snap-toggle` (pending commit) |
| SUB-4 ⇄ | SUB | A2 | P0 | DONE | 2026-06-23 | 2026-06-23 | PASS: reconcile 6/6 + webhook 6/6; full 63/63; check PASS; makemigrations no-changes | `b6e6060d` (code) + `a20010a9` (docs) |
| ACC-1 ⇄ | ACC | A12 + EC-1 | P1 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 10/10; full 67/67; check PASS; makemigrations no-changes. **PG gate A12 pending** | `05f17150` (code) + `dbc307a8` (docs) |
| SUB-5 | SUB | A4 | P1 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 3/3 + webhook/refund 11/11; full 70/70; check PASS; no migrations | `184c0659` (code) + `55e951f7` (docs) |
| SUB-6 | SUB | A6/A7/A8 | P1 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 6/6; full 76/76; check PASS; no migrations | `9999e7a4` (code) + `37dee3b3` (docs) |
| ACC-2 | ACC | A15 | P2 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 3/3; full 79/79; check PASS; no migrations | `486c24a4` (code) + `073b58d7` (docs) |
| SUB-7 | SUB | A13 | P2 | PENDING | - | - | data dedupe | - |
| SUB-8 | SUB | A9 | P3 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 12/12 (incl. entitlement/middleware regresi); full 80/80; check PASS; no migrations | `70268184` (code) + `44f8ef0d` (docs); ACC-2 follow-up `01c940c2` |
| SUB-9 | SUB | A10a/A10b | P3 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 11/11; full 82/82; check PASS; no migrations | `d2cd396b` (code) + `d0dc155d` (docs) |
| SUB-10 ⇄ | SUB | A14 (helper) | P3 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 10/10; full 84/84; check PASS; no migrations | branch `fix/a14-entitlement-memoization` (pending commit) |
| ACC-4 ⇄ | ACC | A14 (sites) | P3 | DONE | 2026-06-23 | 2026-06-23 | (digabung dgn SUB-10 di branch yang sama) | branch `fix/a14-entitlement-memoization` (pending commit) |
| ACC-3 | ACC | A16 | P3 | PENDING | - | - | - | - |

**Milestone:** M1 (go-live) = SUB-1, SUB-2, SUB-3, SUB-4, ACC-1 · M2 = SUB-5, SUB-6 · M3 = SUB-7, ACC-2 · M4 = SUB-8, SUB-9, SUB-10, ACC-4, ACC-3.

---

## 3. Change Log (Perubahan kode)

> Satu baris per perubahan bermakna. M=modified, A=added, D=deleted.

| # | Tanggal | Item | File(s) | Aksi | Ringkasan perubahan | Test | Commit |
|---|---------|------|---------|------|---------------------|------|--------|
| 1 | 2026-06-23 | SUB-1 | `subscriptions/views.py`, `accounts/models.py` | M | Webhook aktivasi kini idempotent berbasis `paid_at`; late `cancel/deny/expire` setelah aktivasi diabaikan; handler `refund` mengubah transaksi ke REFUND dan revoke subscription user tanpa menghapus marker aktivasi. | PASS | `e9475bed` |
| 2 | 2026-06-23 | SUB-1 | `subscriptions/tests.py` | M | Tambah regression test untuk refund revoke, preservasi `paid_at`, replay settlement pasca-refund, dan late deny setelah success. | PASS | `e9475bed` |
| 3 | 2026-06-23 | SUB-1 | `Review/R3_Subscriptions/00_Audit_Summary_20260623.md`, `02_Payment_Flow.md`, `05_Webhook_Security.md`, `09_Implementation_Execution_Tracker_20260623.md` | M | Update status dokumentasi: A5/A11 tertutup oleh SUB-1; A12 tetap pending. | PASS | `b165e752` |
| 4 | 2026-06-23 | SUB-2 | `subscriptions/models.py`, `subscriptions/views.py` | M | `generate_order_id` kini berbasis UUID pk transaksi (bukan timestamp detik); `CreatePaymentView` membangun transaksi via constructor + set `order_id` sebelum satu `save()` (hapus pola `objects.create()` ber-`order_id=''` + save kedua). | PASS | `3bbae422` |
| 5 | 2026-06-23 | SUB-2 | `subscriptions/tests.py` | M | Tambah `PaymentOrderIdUniquenessTests` (3 test): unik antar-transaksi waktu sama, single-insert non-empty order_id, double-create rapid menghasilkan order_id berbeda. | PASS | `3bbae422` |
| 6 | 2026-06-23 | SUB-3 | `subscriptions/views.py`, `subscriptions/templates/subscriptions/checkout.html` | M | `CheckoutView` mengirim `midtrans_is_production` ke context; template memilih host Snap.js (`app.midtrans.com` vs `app.sandbox.midtrans.com`) berdasarkan flag, menggantikan host sandbox hardcoded. | PASS | `28fa972a` |
| 7 | 2026-06-23 | SUB-3 | `subscriptions/tests.py` | M | Tambah `CheckoutSnapJsToggleTests` (2 test): render checkout memakai URL Snap.js produksi saat flag ON, sandbox saat OFF. | PASS | `28fa972a` |
| 8 | 2026-06-23 | SUB-4 | `subscriptions/reconciliation.py`, `subscriptions/tasks.py`, `.../commands/reconcile_pending_payments.py` | A | Service reconcile (`reconcile_pending_payments` + jalur aktivasi bersama `mark_paid_and_activate`), Celery task wrapper dengan fallback import saat Celery tidak terpasang di test/dev lokal, dan management command. | PASS | `b6e6060d` |
| 9 | 2026-06-23 | SUB-4 | `subscriptions/views.py`, `config/celery.py` | M | `_handle_success` kini delegasi ke `mark_paid_and_activate` (satu jalur aktivasi webhook+reconcile); beat `reconcile-pending-payments` tiap 15 menit memanggil task (bukan command langsung). | PASS | `b6e6060d` |
| 10 | 2026-06-23 | SUB-4 | `subscriptions/tests.py` | M | Tambah `PendingPaymentReconciliationTests` (6 test). | PASS | `b6e6060d` |
| 11 | 2026-06-23 | ACC-1 | `accounts/models.py` | M | `activate_subscription` kini re-read baris user di bawah `select_for_update` dalam `atomic`, hitung end_date dari nilai terkunci (cegah lost-update A12 + stale-instance). | PASS | `05f17150` |
| 12 | 2026-06-23 | ACC-1 (EC-1) | `subscriptions/views.py` | M | Handler refund hanya `revoke_subscription` bila tak ada transaksi SUCCESS lain milik user (jangan cabut akses yang dijustifikasi pembelian lain). | PASS | `05f17150` |
| 13 | 2026-06-23 | ACC-1 | `accounts/tests.py`, `subscriptions/tests.py` | M | Tambah `ActivateSubscriptionAtomicityTests` (2) + `RefundRevocationScopeTests` (2). | PASS | `05f17150` |
| 14 | 2026-06-23 | SUB-5 | `subscriptions/views.py` | M | Helper `_settlement_payload_is_consistent`: sebelum aktivasi, cross-check field **bertanda tangan** (`status_code=='200'` + `gross_amount`==`amount` via Decimal) terhadap record; bila tak konsisten, tidak aktivasi (A4). | PASS | `184c0659` |
| 15 | 2026-06-23 | SUB-5 | `subscriptions/tests.py` | M | Tambah `WebhookSettlementCrossCheckTests` (3 test): amount mismatch tak aktivasi, beda format Decimal tetap aktivasi, status_code salah tak aktivasi. | PASS | `184c0659` |
| 16 | 2026-06-23 | SUB-6 | `subscriptions/midtrans.py` | M | `verify_signature` kini pakai `hmac.compare_digest` (constant-time) + tolak signature non-str (A7). | PASS | `9999e7a4` |
| 17 | 2026-06-23 | SUB-6 | `subscriptions/views.py` | M | A8: webhook order valid-sig tak dikenal balas **200**+log (bukan 404). A6: `CreatePaymentView` di-throttle per-user via cache (5/60s) → 429 `RATE_LIMIT_EXCEEDED`. | PASS | `9999e7a4` |
| 18 | 2026-06-23 | SUB-6 | `subscriptions/tests.py` | M | Tambah `SignatureVerificationTests`(3)/`WebhookUnknownOrderTests`(2)/`CreatePaymentRateLimitTests`(1); isolasi cache test lama (DummyCache 2 kelas RequestFactory + `cache.clear()` full-stack) agar counter rate-limit tak bocor lintas-test. | PASS | `9999e7a4` |
| 19 | 2026-06-23 | ACC-2 | `accounts/tasks.py` | M | `send_expiry_reminder` kini benar-benar kirim email (`send_mail`) ke user trial/PRO yang expired ≤3 hari (link `/pricing/` + support email), bukan stub log (A15). | PASS | `486c24a4` |
| 20 | 2026-06-23 | ACC-2 | `accounts/tests.py` | M | Tambah `ExpiryReminderEmailTests` (3 test): PRO/trial dalam window dapat email; di luar window tak dapat. | PASS | `486c24a4` |
| 21 | 2026-06-23 | ACC-2 | `accounts/tasks.py` | M | Follow-up gate: import `shared_task` dibuat aman saat package Celery tidak terpasang di test/dev lokal, konsisten dengan `subscriptions/tasks.py`. | PASS | `01c940c2` |
| 22 | 2026-06-23 | SUB-8 | `subscriptions/entitlements.py` | M | `except Exception: pass` → `except DatabaseError` + `logger.warning(exc_info)` (A9). Mock tanpa pk sudah ditangani early-return; narrowing aman. | PASS | `70268184` |
| 23 | 2026-06-23 | SUB-8 | `subscriptions/tests.py` | M | Tambah `EntitlementDbErrorFallbackTests` (1 test): DB error di-log + fallback matrix. | PASS | `70268184` |
| 24 | 2026-06-23 | SUB-9 | `subscriptions/views.py` | M | A10a: `CreatePaymentView` reuse transaksi `pending` ≤30 menit dgn `amount` cocok + `snap_token` (hindari row & call Midtrans ganda). A10b: `CheckoutView` cek `is_pro_active` (bukan `status=='PRO' and is_subscription_active`). | PASS | `d2cd396b` |
| 25 | 2026-06-23 | SUB-9 | `subscriptions/tests.py` | M | Update test SUB-2 rapid-create→`reuses_recent_pending` (A10a); tambah `CheckoutActiveSubscriptionTests` (2 test, A10b). | PASS | `d2cd396b` |
| 26 | 2026-06-23 | SUB-10 | `subscriptions/entitlements.py` | M | Tambah `get_request_feature_access(request, feature_code)`: memoize keputusan entitlement per-request (cache di `request._feature_access_cache`) (A14). | PASS | _(pending)_ |
| 27 | 2026-06-23 | ACC-4 | `accounts/middleware.py`, `accounts/context_processors.py` | M | Konsumsi `get_request_feature_access` di middleware (WRITE_ACCESS) + context processor (PDF/Excel-Word) → tak recompute fitur sama per-request (A14). | PASS | _(pending)_ |
| 28 | 2026-06-23 | SUB-10/ACC-4 | `subscriptions/tests.py`, `accounts/tests.py` | M | Tambah `RequestFeatureAccessCacheTests` (dedup same-feature) + test context processor mengisi `_feature_access_cache`. | PASS | _(pending)_ |

---

## 4. Ledger Penambahan & Penghapusan Artefak

> Lacak artefak BARU yang kita buat dan artefak LAMA yang kita hapus/deprecate, beserta alasan & guard.

### 4.1 Penambahan (Additions)

| # | Tanggal | Item | Artefak baru | Jenis | Alasan |
|---|---------|------|--------------|-------|--------|
| 1 | 2026-06-23 | SUB-1 | `test_refund_after_success_revokes_access`; `test_refund_preserves_activation_marker`; `test_replay_settlement_after_refund_does_not_reactivate`; `test_late_deny_after_success_does_not_overwrite_success` | Regression tests | Guard A11/A5 agar refund mencabut akses, replay sukses tidak mengaktifkan ulang, dan terminal webhook terlambat tidak menimpa success. |
| 2 | 2026-06-23 | SUB-1 | `CustomUser.revoke_subscription(revoked_at=None)` | Method (API baru `accounts`) | Mencabut akses PRO segera (set EXPIRED + `subscription_end_date=now`) untuk D-1; dipakai handler refund webhook. Lihat catatan EC-1 §7. |
| 3 | 2026-06-23 | SUB-2 | `PaymentOrderIdUniquenessTests` (3 test) | Regression tests | Guard A3: order_id unik per transaksi (UUID pk), single-insert tanpa window `order_id=''`, rapid double-create tak tabrakan. |
| 4 | 2026-06-23 | SUB-3 | `CheckoutSnapJsToggleTests` (2 test) | Regression tests | Guard A1: checkout memuat Snap.js produksi vs sandbox sesuai `MIDTRANS_IS_PRODUCTION`. |
| 5 | 2026-06-23 | SUB-4 | `subscriptions/reconciliation.py` | Module | `reconcile_pending_payments()` + `mark_paid_and_activate()` (jalur aktivasi tunggal webhook+reconcile). Memakai `get_transaction_status` yang sebelumnya dead-code (A2). |
| 6 | 2026-06-23 | SUB-4 | `subscriptions/tasks.py` (`reconcile_pending_payments_task`) | Celery task | Wrapper beat → service (beat tak panggil command langsung); import-safe di environment tanpa package Celery. |
| 7 | 2026-06-23 | SUB-4 | `management/commands/reconcile_pending_payments.py` | Mgmt command | Jalur manual/runbook reconcile (`--older-than-minutes`, `--limit`). |
| 8 | 2026-06-23 | SUB-4 | beat `reconcile-pending-payments` (`config/celery.py`) | Beat schedule | Jadwal tiap 15 menit memanggil `subscriptions.reconcile_pending_payments`. |
| 9 | 2026-06-23 | SUB-4 | `PendingPaymentReconciliationTests` (6 test) | Regression tests | Activate settled, idempotent, leave-pending, skip-recent, task-delegasi, command. |
| 10 | 2026-06-23 | ACC-1 | `ActivateSubscriptionAtomicityTests` (2 test) | Regression tests | Guard A12: aktivasi menumpuk dari nilai DB (bukan stale instance); fresh activation dari now. |
| 11 | 2026-06-23 | ACC-1 | `RefundRevocationScopeTests` (2 test) | Regression tests | Guard EC-1: refund mencabut bila satu-satunya tx sukses; mempertahankan akses bila ada tx sukses lain. |
| 12 | 2026-06-23 | SUB-5 | `_settlement_payload_is_consistent` (helper) + `WebhookSettlementCrossCheckTests` (3 test) | Helper + tests | Guard A4: cross-check field bertanda tangan (status_code/gross_amount-Decimal) sebelum aktivasi webhook. |
| 13 | 2026-06-23 | SUB-6 | konstanta `CREATE_PAYMENT_MAX_ATTEMPTS/WINDOW_SECONDS` + `SignatureVerificationTests`/`WebhookUnknownOrderTests`/`CreatePaymentRateLimitTests` (6 test) | Rate-limit + tests | Guard A6/A7/A8: throttle create_payment, constant-time signature, 200-untuk-valid-sig-unknown. |
| 14 | 2026-06-23 | ACC-2 | `ExpiryReminderEmailTests` (3 test) | Regression tests | Guard A15: email reminder benar-benar terkirim utk user expiring ≤3 hari (PRO/trial), bukan stub. |
| 15 | 2026-06-23 | SUB-8 | `EntitlementDbErrorFallbackTests` (1 test) + `logger` di `entitlements.py` | Test + logger | Guard A9: DB error di-log (tak ditelan diam-diam) lalu fallback. |
| 16 | 2026-06-23 | SUB-9 | `CheckoutActiveSubscriptionTests` (2 test) + reuse-block `CreatePaymentView` | Guard + tests | Guard A10a (reuse pending) + A10b (PRO-active redirect, trial-active lolos). |
| 17 | 2026-06-23 | SUB-10 | `get_request_feature_access` (helper) + `RequestFeatureAccessCacheTests` | Helper + test | A14: memoization keputusan entitlement per-request (cache di `request`). |

### 4.2 Penghapusan / Deprecation (Deletions)

| # | Tanggal | Item | Artefak dihapus/deprecated | Pengganti / Guard | Alasan |
|---|---------|------|----------------------------|-------------------|--------|
| - | - | - | _(belum ada)_ | - | - |

---

## 5. Decisions Ledger

> Keputusan owner & kontrak teknis. Keputusan runtime baru diberi nomor lanjut (D-4, D-5, …).

| # | Tanggal | Keputusan | Konteks/Alasan | Dampak implementasi |
|---|---------|-----------|----------------|---------------------|
| D-1 | 2026-06-23 | **Refund → CABUT akses PRO segera** | Integritas: refund/chargeback tak boleh tetap dapat akses | SUB-1 + ACC-1: handler `refund` set status REFUND **dan** turunkan user ke EXPIRED |
| D-2 | 2026-06-23 | **Rate-limit webhook di EDGE/WAF** (di luar kode) | Limit app-level berisiko men-drop burst notifikasi Midtrans yang sah | A6 webhook → runbook ops; di kode hanya `create_payment` (SUB-6) |
| D-3 | 2026-06-23 | **Implement email reminder sekarang** | Tutup celah silent-churn (task saat ini stub) | ACC-2 = tulis pengiriman email reminder |

---

## 6. Test & Gate Log

| # | Tanggal | Item | Perintah | Hasil | Catatan |
|---|---------|------|----------|-------|---------|
| 0 | 2026-06-23 | baseline | `test subscriptions --settings=config.settings.test` | **23/23 PASS** | titik nol sebelum perubahan |
| 1 | 2026-06-23 | SUB-1 | `python manage.py test subscriptions.tests.PaymentWebhookIdempotencyTests --settings=config.settings.test --noinput --verbosity 1` | **6/6 PASS** | refund revoke, marker `paid_at`, replay settlement pasca-refund, late deny |
| 2 | 2026-06-23 | SUB-1 | `python manage.py test subscriptions --settings=config.settings.test --noinput --verbosity 1` | **27/27 PASS** | subscriptions gate setelah 4 regression test baru |
| 3 | 2026-06-23 | SUB-1 | `python manage.py test subscriptions accounts --settings=config.settings.test --noinput --verbosity 1` | **52/52 PASS** | full subscriptions+accounts gate |
| 4 | 2026-06-23 | SUB-1 | `python manage.py check --settings=config.settings.test` | **PASS** | warning Allauth deprecation existing |
| 5 | 2026-06-23 | SUB-1 | `python manage.py makemigrations --check --dry-run --settings=config.settings.test` | **PASS** | no changes detected |
| 6 | 2026-06-23 | SUB-2 | `test subscriptions.tests.PaymentOrderIdUniquenessTests` | **3/3 PASS** | unik antar-tx, single-insert, double-create |
| 7 | 2026-06-23 | SUB-2 | `test subscriptions accounts --settings=config.settings.test` | **55/55 PASS** | +3 dari baseline 52 (SUB-1) |
| 8 | 2026-06-23 | SUB-2 | `check` + `makemigrations --check` | **PASS** | no changes (perubahan metode, bukan field) |
| 9 | 2026-06-23 | SUB-3 | `test subscriptions.tests.CheckoutSnapJsToggleTests` | **2/2 PASS** | URL Snap.js prod saat flag ON, sandbox saat OFF |
| 10 | 2026-06-23 | SUB-3 | `test subscriptions accounts` + `check` | **57/57 PASS** + check PASS | +2 dari 55; tanpa migrasi (template/context saja) |
| 11 | 2026-06-23 | SUB-4 | `test PendingPaymentReconciliationTests + PaymentWebhookIdempotencyTests` | **12/12 PASS** | reconcile 6 + webhook 6 (refaktor `_handle_success` aman) |
| 12 | 2026-06-23 | SUB-4 | `test subscriptions accounts` + `check` + `makemigrations --check` | **63/63 PASS** + check PASS + no changes | +6 dari 57; tanpa migrasi (service/task/command/beat saja) |
| 13 | 2026-06-23 | ACC-1 | `test ActivateSubscriptionAtomicityTests + RefundRevocationScopeTests + PaymentWebhookIdempotencyTests` | **10/10 PASS** | A12 + EC-1 + webhook regresi aman |
| 14 | 2026-06-23 | ACC-1 | `test subscriptions accounts` + `check` + `makemigrations --check` | **67/67 PASS** + check PASS + no changes | +4 dari 63; tanpa migrasi (metode+query saja) |
| 15 | 2026-06-23 | SUB-5 | `test WebhookSettlementCrossCheckTests + PaymentWebhookIdempotencyTests + RefundRevocationScopeTests` | **11/11 PASS** | cross-check + regresi webhook/refund aman |
| 16 | 2026-06-23 | SUB-5 | `test subscriptions accounts` + `check` + `makemigrations --check` | **70/70 PASS** + check PASS + no changes | +3 dari 67; tanpa migrasi (helper+guard saja) |
| 17 | 2026-06-23 | SUB-6 | `test SignatureVerificationTests + WebhookUnknownOrderTests + CreatePaymentRateLimitTests` | **6/6 PASS** | A7/A8/A6 targeted |
| 18 | 2026-06-23 | SUB-6 | `test subscriptions accounts` | sempat **FAILED 4** (polusi cache rate-limit lintas-test) → **76/76 PASS** setelah isolasi cache | +6 dari 70; tanpa migrasi. Pelajaran: LocMemCache test persisten + reuse PK user |
| 19 | 2026-06-23 | ACC-2 | `test ExpiryReminderEmailTests` | **3/3 PASS** | email reminder window 3 hari (locmem outbox) |
| 20 | 2026-06-23 | ACC-2 | `test subscriptions accounts` + `check` + `makemigrations` | **79/79 PASS** + check PASS + no changes | +3 dari 76; tanpa migrasi (task body saja) |
| 21 | 2026-06-23 | SUB-8 | `test EntitlementDbErrorFallbackTests + EntitlementPolicyEngineTests + SubscriptionMiddlewareTests + TrialAccessGuardTests` | **12/12 PASS** | narrowing tak merusak fallback mock/real |
| 22 | 2026-06-23 | SUB-8 | `test subscriptions accounts` + `check` + `makemigrations` | **80/80 PASS** + check PASS + no changes | +1 dari 79; tanpa migrasi |
| 23 | 2026-06-23 | SUB-9 | `test PaymentOrderIdUniquenessTests + CheckoutActiveSubscriptionTests + PaymentPricingIntegrityTests + SubscriptionRolePolicyTests + ExpiredUserRenewalFlowTests` | **11/11 PASS** | A10a reuse + A10b + regresi create/checkout |
| 24 | 2026-06-23 | SUB-9 | `test subscriptions accounts` + `check` + `makemigrations` | **82/82 PASS** + check PASS + no changes | +2 dari 80; tanpa migrasi (view+test saja) |
| 25 | 2026-06-23 | SUB-10/ACC-4 | `test RequestFeatureAccessCacheTests + SubscriptionContextTests + SubscriptionMiddlewareTests + TrialAccessGuardTests` | **10/10 PASS** | memo + regresi middleware/context aman |
| 26 | 2026-06-23 | SUB-10/ACC-4 | `test subscriptions accounts` + `check` + `makemigrations` | **84/84 PASS** + check PASS + no changes | +2 dari 82; tanpa migrasi (helper+wiring) |

**Gate per-item (Definition of Done, doc 08):** kode + regression test baru hijau di `config.settings.test`; tidak menurunkan baseline (subscriptions 23/23 + accounts existing); doc review terkait diupdate; migrasi → `makemigrations --check` bersih.

---

## 7. Catatan / Temuan Baru Selama Implementasi (Deviasi dari Plan)

> Bila saat coding ditemukan hal di luar audit/plan, catat di sini dan rujuk balik ke doc 00/08 (jangan diam-diam ubah scope).

| # | Tanggal | Item | Temuan/Deviasi | Tindakan |
|---|---------|------|----------------|----------|
| EC-1 | 2026-06-23 | SUB-1 | **Revoke bersifat account-wide.** `revoke_subscription()` set `subscription_end_date=now` + EXPIRED untuk SELURUH akun. Bila user punya >1 transaksi sukses dengan masa berlaku tumpang-tindih (mis. renewal mendekati expiry), refund pada SATU order ikut mencabut sisa masa berlaku order lain. **Eksposur rendah**: `CheckoutView` memblok checkout saat `is_subscription_active`, jadi overlap umumnya hanya via renewal-near-expiry atau direct `create_payment`. **Bukan regresi SUB-1** (D-1 diimplementasikan sesuai spec) dan **bukan blocker**. | Track sebagai **refinement D-1** (kaitkan ke A12/ACC-1): saat revoke, pertimbangkan recompute `subscription_end_date` dari transaksi sukses non-refund tersisa, bukan blanket EXPIRED. **RESOLVED di ACC-1 (2026-06-23):** handler refund hanya `revoke_subscription` bila tak ada transaksi SUCCESS lain milik user → akses yang dijustifikasi pembelian lain tidak ikut tercabut; diuji `RefundRevocationScopeTests` (2/2). |

---

## 8. Konvensi Commit & Branch

- Branch per paket/item (mis. `fix/subscriptions-sub1-idempotent-activation`) agar PR/review terisolasi (sesuai keputusan struktur per-area).
- Pesan commit merujuk ID item + temuan (mis. `SUB-1 (A11/A5): idempotent activation by paid_at + refund revoke`).
- Setiap commit yang menyentuh kode HARUS punya baris di §3; setiap file baru/hapus di §4.
- Update kolom Status §2 + Branch/Commit saat item DONE.
