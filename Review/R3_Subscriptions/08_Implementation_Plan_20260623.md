# R3.8 - Implementation Plan (Subscriptions Audit Fixes)

**Status:** `[x]` READY FOR EXECUTION — keputusan owner D-1/D-2/D-3 sudah ditetapkan 2026-06-23; catatan presisi Codex ditambahkan 2026-06-23
**Tanggal:** 2026-06-23
**Struktur:** Per-area (blast-radius) — **Paket SUB** (`subscriptions/`) dan **Paket ACC** (`accounts/`), PR/review terisolasi. Item lintas-area ditandai **⇄**.
**Sumber temuan:** [00_Audit_Summary](00_Audit_Summary_20260623.md) (A1–A17), detail di doc 01–07.
**Gate verifikasi global:** `python manage.py test subscriptions accounts --settings=config.settings.test` HARUS hijau (baseline saat ini: subscriptions 23/23; subscriptions+accounts 48/48). Setiap item P0/P1/P2 WAJIB membawa regression test baru.

> Catatan verifikasi Codex: `config.settings.test` memakai SQLite, sehingga test unit ini **tidak cukup** untuk membuktikan locking PostgreSQL (`select_for_update`) dan constraint PostgreSQL-specific (`nulls_distinct=False`). Untuk A12 dan A13, tambahkan gate integration test di PostgreSQL 15 sebelum go-live.
**Tracker eksekusi (WAJIB diperbarui tiap perubahan):** [09_Implementation_Execution_Tracker_20260623.md](09_Implementation_Execution_Tracker_20260623.md) — progress, change log, ledger penambahan/penghapusan, decisions, gate log.

---

## 0. Keputusan Owner — DITETAPKAN 2026-06-23 ✅

| # | Keputusan | Konsekuensi pada plan |
|----|-----------|-----------------------|
| **D-1** | **Refund → CABUT akses PRO segera.** | SUB-1 menambah jalur revoke user saat `refund` (status REFUND + turunkan langganan ke EXPIRED). |
| **D-2** | **Rate-limit webhook di EDGE/WAF** (di luar kode). | A6 webhook → runbook ops (lihat Out-of-scope). Di kode hanya `create_payment` yang di-rate-limit (SUB-6). |
| **D-3** | **Implement email reminder sekarang.** | ACC-2 = tulis pengiriman email (bukan disable beat). |

---

## PAKET SUB — `subscriptions/` (core pembayaran & entitlement)

### Fase SUB-P0 (blocker go-live)

| Item | Temuan | Pendekatan | Files | Test baru |
|------|--------|------------|-------|-----------|
| **SUB-1** | A11 + A5 | Idempotensi aktivasi berbasis `paid_at is not None` (atau flag `activated`), **bukan** `status`. Tolak transisi mundur dari `success` tanpa penanganan. **D-1: `refund` → set REFUND + CABUT akses** (turunkan user ke EXPIRED / potong end_date) via jalur revoke baru. Saat refund, **jangan kosongkan `paid_at`/flag aktivasi**, supaya replay `settlement` setelah refund tidak mengaktifkan ulang. | `views.py` (`_handle_success`, `post`, handler refund), `accounts/models.py` (helper revoke ⇄ ACC-1) | `test_replay_settlement_after_refund_not_reactivate`; `test_refund_after_success_revokes_access`; `test_refund_preserves_activation_marker` |
| **SUB-2** | A3 | Set `order_id` **atomik** di satu `create()` pakai komponen unik (`uuid4().hex[:12]` / pk UUID). Hapus pola two-step `order_id=''`. | `models.py:generate_order_id`, `views.py:CreatePaymentView` | `test_concurrent_create_no_order_id_collision` |
| **SUB-3** | A1 | Kirim `midtrans_is_production` ke context; template pilih Snap.js prod vs sandbox. | `views.py:CheckoutView`, `templates/.../checkout.html` | `test_checkout_uses_production_snap_url_when_flag_on` |
| **SUB-4** ⇄ | A2 | Mgmt command `reconcile_pending_payments` (manual/runbook) + **Celery task wrapper** untuk beat: `get_transaction_status` utk `pending` berumur > N menit → jalankan **jalur aktivasi yang sama** (post-SUB-1, idempotent). Tambah task ke `config/celery.py` beat; jangan jadwalkan management command langsung dari beat tanpa wrapper. | `management/commands/reconcile_pending_payments.py`, `tasks.py` atau task app terkait, `midtrans.py` (reuse), `config/celery.py` | `test_reconcile_activates_paid_pending`; `test_reconcile_idempotent`; `test_reconcile_task_invokes_command_or_service` |

> Urutan wajib: **SUB-1 → SUB-4** (reconcile memakai jalur aktivasi yang sudah idempotent). SUB-2/SUB-3 independen.

### Fase SUB-P1 (pengerasan keamanan)

| Item | Temuan | Pendekatan | Files | Test baru |
|------|--------|------------|-------|-----------|
| **SUB-5** | A4 | Untuk `capture/settlement`: re-fetch status otoritatif via `get_transaction_status` sebelum aktivasi, ATAU minimal validasi `status_code↔transaction_status` + `gross_amount == amount`/snapshot. Normalisasi nominal ke `Decimal` sebelum compare agar variasi format Midtrans (`10000.00` vs `10000`) tidak false-negative. (Reuse helper SUB-4.) | `views.py:PaymentWebhookView`, `midtrans.py` | `test_webhook_rejects_tampered_status_field`; `test_webhook_amount_mismatch_ignored`; `test_webhook_amount_format_normalized` |
| **SUB-6** | A7, A8, A6 | `hmac.compare_digest` di `verify_signature`; webhook balas 200+log utk order **valid-sig-unknown** (403 bad-sig tetap); rate-limit **`create_payment` (app-level)**. **D-2: rate-limit webhook TIDAK di kode** (edge/WAF — Out-of-scope). | `midtrans.py:143`, `views.py` | `test_signature_compare_constant_time` (smoke); `test_unknown_order_valid_sig_returns_200`; `test_create_payment_rate_limited` |

### Fase SUB-P2/P3 (integritas data & kebersihan)

| Item | Temuan | Pendekatan | Files | Test baru |
|------|--------|------------|-------|-----------|
| **SUB-7** | A13 | `UniqueConstraint(..., nulls_distinct=False)` (Django 5.2 + PG15). Data-migration dedupe `plan=NULL` duplikat lebih dulu. Verifikasi harus berjalan di PostgreSQL 15; SQLite test backend tidak membuktikan perilaku `NULLS NOT DISTINCT`. | `models.py:PlanFeatureEntitlement.Meta`, migrasi baru | `test_duplicate_null_plan_default_rejected` + PG integration check |
| **SUB-8** | A9 | Persempit `except Exception` → `DatabaseError`/`OperationalError` + `logger.warning`. | `entitlements.py:226-229` | `test_entitlement_db_error_logged_then_fallback` |
| **SUB-9** | A10a, A10b | Reuse/limit transaksi `pending` aktif; ganti cek checkout ke `is_pro_active`. | `views.py` | `test_duplicate_pending_reused` |
| **SUB-10** ⇄ | A14 (helper) | Sediakan helper memoization keputusan entitlement per-request (cache di objek `request`), dikonsumsi Paket ACC. | `entitlements.py` | `test_get_feature_access_request_cached` |

---

## PAKET ACC — `accounts/` (lifecycle, middleware, context)

| Item | Temuan | Prio | Pendekatan | Files | Test baru |
|------|--------|------|------------|-------|-----------|
| **ACC-1** ⇄ | A12 | P1 | `activate_subscription` atomik: kunci baris user (`select_for_update`) **di dalam** transaksi webhook, atau update `subscription_end_date` berbasis re-read terkunci. Koordinasi dgn SUB-1 (webhook sudah `atomic`). | `accounts/models.py:123-136`, (verifikasi call-site `subscriptions/views.py`) | `test_concurrent_activation_no_lost_update` |
| **ACC-2** | A15 | P2 | **D-3: implement** kirim email reminder (template + `support_email`) untuk trial/PRO yang akan expired ≤3 hari. | `accounts/tasks.py:50-84`, template email baru | `test_expiry_reminder_sends_email` |
| **ACC-3** | A16 | P3 | Turunkan badge & `show_upgrade_banner` dari status **efektif** (`is_pro_active`/`is_trial_active`), bukan `subscription_status` mentah. | `accounts/context_processors.py:48-62` | `test_lapsed_pro_shows_upgrade_not_pro_badge` |
| **ACC-4** ⇄ | A14 (sites) | P3 | Konsumsi helper memoization (SUB-10) di middleware + context processor agar `get_feature_access` tak dipanggil berulang per-request. | `accounts/middleware.py`, `accounts/context_processors.py` | `test_single_entitlement_eval_per_request` (query count) |

---

## Lintas-area ⇄ (koordinasi PR)

| Item | Bagian SUB | Bagian ACC | Catatan |
|------|-----------|-----------|---------|
| A12 | webhook membungkus lock (SUB-1 sudah `atomic`) | `activate_subscription` jadi atomic (ACC-1) | Merge ACC-1 boleh setelah SUB-1; webhook tinggal perluas lock |
| A14 | helper cache (SUB-10) | call-site (ACC-4) | Merge SUB-10 dulu, lalu ACC-4 |
| A2 | reconcile command (SUB-4) | — (beat di config) | — |

---

## Milestone & Urutan Merge

1. **M1 (go-live)**: SUB-1 → SUB-2, SUB-3 → SUB-4. + ACC-1 (setelah SUB-1). Gate: blocker A1/A2/A3/A11/A12 tertutup + test hijau.
2. **M2 (hardening)**: SUB-5, SUB-6. + (❓D-2 bila app-level).
3. **M3 (data & lifecycle)**: SUB-7, ACC-2 (❓D-3).
4. **M4 (kebersihan & perf)**: SUB-8, SUB-9, SUB-10 → ACC-4, ACC-3. (+ A17 detail_project opsional, P4.)

---

## Definition of Done (per item)

- Kode + regression test baru (skenario spesifik temuan) hijau di `config.settings.test`.
- Untuk A12/A13: jalankan minimal satu verifikasi PostgreSQL 15 karena SQLite tidak memvalidasi lock row/constraint NULL seperti produksi.
- Tidak menurunkan baseline (subscriptions 23/23 + accounts existing).
- Update dokumen review terkait (kolom "Aktivitas Perbaikan" + status `[~]`→`[x]`/commit).
- Untuk migrasi (SUB-7): `makemigrations --check` bersih + dedupe terverifikasi.

---

## Out-of-scope (tetap backlog terpisah)

- **A6 webhook-side → edge/WAF** (D-2): runbook ops, BUKAN kode. Buat catatan deploy: rate-limit `POST /subscriptions/webhook/midtrans/` di reverse-proxy/WAF dengan ambang yang mengakomodasi burst notifikasi Midtrans.
- A17 (re-eval watermark finalize) — P4.
- Item non-subscriptions yang ditemukan saat audit page R5 (lihat memory) tidak masuk plan ini.
