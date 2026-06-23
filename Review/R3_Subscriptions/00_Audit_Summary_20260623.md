# R3.0 - Ringkasan Audit App `subscriptions`

**Status:** `[x]` **SELESAI — semua temuan A1–A16 FIXED & terverifikasi.** SUB-1..10 + ACC-1/2/3/4. SQLite 90 (87 + 3 PG skip) + PG integrasi 3/3 (A12 lock + A13 constraint) via `config.settings.test_pg`. **Caveat go-live PG TERTUTUP.** Sisa hanya A17 (INFO/P4 opsional).
**Tanggal audit:** 2026-06-23
**Metode:** Telaah kode statis menyeluruh (read-only) atas seluruh berkas `subscriptions/*` + integrasi `accounts` (User model, middleware, mixins, signals) dan `config` (settings, URL routing), dilanjutkan verifikasi independen serta eksekusi automated test. **Bukan** UAT browser atau transaksi Midtrans nyata.
**Auditor:** Claude Code; diverifikasi ulang oleh Codex pada 2026-06-23

---

## 1. Cakupan

| Komponen | Berkas |
|----------|--------|
| Models | `subscriptions/models.py` |
| Views | `subscriptions/views.py` |
| Midtrans client | `subscriptions/midtrans.py` |
| Pricing service | `subscriptions/pricing_service.py` |
| Entitlement engine | `subscriptions/entitlements.py` |
| Admin | `subscriptions/admin.py` |
| URL | `subscriptions/urls.py` + `config/urls.py` |
| Template | `subscriptions/templates/subscriptions/checkout.html` |
| Seed command | `subscriptions/management/commands/seed_plans.py` |
| Migrasi | `subscriptions/migrations/0001..0005` |
| Integrasi | `accounts/models.py`, `accounts/middleware.py`, `accounts/mixins.py`, `accounts/signals.py`, `config/settings/base.py` |
| Test | `subscriptions/tests.py` |

---

## 2. Penilaian Umum

Arsitektur app memiliki fondasi yang baik: harga dihitung server-side dengan snapshot immutable, webhook memakai row-lock (`select_for_update`), entitlement data-driven dengan fallback matrix deterministik, dan test coverage layak. SUB-1 menutup replay setelah refund/terminal (A11) + kebijakan refund revoke/late terminal (A5); SUB-2 menutup uniqueness order id (A3); SUB-3 menutup checkout produksi (A1, Snap.js prod/sandbox); SUB-4 menutup rekonsiliasi webhook terlewat (A2); ACC-1 menutup lost-update aktivasi konkuren (A12) + refund account-wide (EC-1). **Semua P0 (go-live) + P1 (A4/A6/A7/A8/A12) tertutup; M1 & M2 selesai.** SUB-5 menutup verifikasi field webhook (A4); SUB-6 menutup rate-limit `create_payment`/constant-time/respons webhook (A6/A7/A8); ACC-2 menutup pengingat expiry (A15, email reminder nyata). SUB-8 menutup logging error entitlement (A9); SUB-9 menutup dedup pending (A10a) + cek checkout (A10b); SUB-10/ACC-4 menutup memo entitlement per-request (A14); ACC-3 menutup badge/banner status efektif (A16); SUB-7 menutup uniqueness default entitlement (A13) **dan** memverifikasi lock konkuren A12 langsung di PostgreSQL 15 (Jalur B). **SELESAI — semua temuan A1–A16 tertutup & terverifikasi; caveat go-live PG hilang.** Hanya A17 (INFO/P4) yang opsional.

---

## 3. Daftar Temuan (Severity)

| ID | Sev | Temuan | Dokumen detail |
|----|-----|--------|----------------|
| **A1** | 🟢 FIXED (SUB-3) | Host Snap.js checkout kini mengikuti `MIDTRANS_IS_PRODUCTION` (produksi vs sandbox) | [01](01_Checkout_Page.md), [03](03_Midtrans_Integration.md) |
| **A2** | 🟢 FIXED (SUB-4) | Reconcile (`reconcile_pending_payments`) memulihkan transaksi paid-but-pending via Status API + jalur aktivasi sama; Celery beat tiap 15 menit + command manual | [03](03_Midtrans_Integration.md), [02](02_Payment_Flow.md) |
| **A3** | 🟢 FIXED (SUB-2) | `order_id` kini dari UUID pk transaksi + single-insert (hapus window `order_id=''`); double-click/konkuren tak lagi tabrakan | [02](02_Payment_Flow.md) |
| **A4** | 🟢 FIXED (SUB-5) | Webhook cross-check field bertanda tangan (`status_code`/`gross_amount`-Decimal) ke record sebelum aktivasi → tampering `transaction_status`/`fraud_status` tak cukup meng-aktivasi | [05](05_Webhook_Security.md) |
| **A5** | 🟢 FIXED (SUB-1) | `refund` susulan kini mencabut akses PRO; late `cancel`/`deny`/`expire` setelah success tidak menimpa record aktif | [05](05_Webhook_Security.md), [02](02_Payment_Flow.md) |
| **A6** | 🟢 FIXED (SUB-6) | `create_payment` di-throttle app-level (5/60s→429); rate-limit webhook → edge/WAF (D-2, di luar kode) | [05](05_Webhook_Security.md), [02](02_Payment_Flow.md) |
| **A7** | 🟢 FIXED (SUB-6) | `verify_signature` pakai `hmac.compare_digest` (constant-time) + tolak signature non-`str` | [05](05_Webhook_Security.md), [03](03_Midtrans_Integration.md) |
| **A8** | 🟢 FIXED (SUB-6) | Order valid-sig tak dikenal → 200+log (Midtrans berhenti retry); 403 bad-sig dipertahankan | [05](05_Webhook_Security.md) |
| **A9** | 🟢 FIXED (SUB-8) | `except Exception: pass` → `except DatabaseError` + `logger.warning` sebelum fallback | [04](04_Entitlement_System.md) |
| **A10a** | 🟢 FIXED (SUB-9) | `create_payment` reuse transaksi `pending` segar (≤30 mnt, amount cocok, snap_token) alih-alih menumpuk baris | [02](02_Payment_Flow.md) |
| **A10b** | 🟢 FIXED (SUB-9) | Cek checkout disederhanakan ke `is_pro_active` (ekuivalen; PRO-active redirect, trial-active lolos) | [01](01_Checkout_Page.md) |
| **A11** | 🟢 FIXED (SUB-1) | Idempotensi aktivasi kini berbasis `paid_at`; replay `settlement` setelah refund tidak mengaktifkan/memperpanjang subscription ulang | [05](05_Webhook_Security.md), [02](02_Payment_Flow.md) |
| **A12** | 🟢 FIXED (ACC-1) | `activate_subscription` re-read baris user di bawah `select_for_update` → pembayaran konkuren menumpuk. **Terverifikasi di PG15** (test konkurensi 2-thread, SUB-7) | `accounts/models.py:activate_subscription` |
| **A13** | 🟢 FIXED (SUB-7) | `UniqueConstraint` + `nulls_distinct=False` (PG15 `NULLS NOT DISTINCT`) + migrasi 0006 dedupe; **diverifikasi di PG15** (duplicate `plan=NULL` ditolak) | `subscriptions/models.py`, migrasi 0006 |
| **A14** | 🟢 FIXED (SUB-10/ACC-4) | `get_request_feature_access` memoize keputusan entitlement per-request (cache di `request`); middleware + context processor memakainya | [07](07_Cross_App_Integration_20260623.md) |
| **A15** | 🟢 FIXED (ACC-2) | `send_expiry_reminder` kini benar-benar kirim email (sisa hari + link `/pricing/`) ke user expiring ≤3 hari; bukan stub | [07](07_Cross_App_Integration_20260623.md) |
| **A16** | 🟢 FIXED (ACC-3) | Badge & `show_upgrade_banner` context processor diturunkan dari status efektif (`is_pro_active`/`is_trial_active`), bukan field mentah → user lapse tampil EXPIRED+banner tanpa menunggu task harian | [07](07_Cross_App_Integration_20260623.md) |
| **A17** | ℹ️ INFO | Keputusan watermark export multi-step `detail_project` dibekukan saat `export_init`; perubahan entitlement mid-session tak tercermin di finalize | [07](07_Cross_App_Integration_20260623.md) |

---

## 4. Yang Sudah Baik (jangan diubah)

- **Harga server-side + snapshot immutable** (`amount`, `base/discount/duration_months_snapshot`, detail promo dibekukan saat create) — diuji `PaymentPricingIntegrityTests`.
- **Webhook idempotent untuk duplicate success dan replay setelah refund** via `select_for_update` + marker `paid_at` — diuji `PaymentWebhookIdempotencyTests`; batas konkuren multi-transaksi masih dicatat pada A12.
- **Aktivasi memakai `duration_months_snapshot`**, tahan perubahan/penghapusan plan (FK `SET_NULL` + fallback).
- **Entitlement data-driven** dengan override per-plan, normalisasi status (`TRIAL_PENDING`/stale-PRO→EXPIRED), dan fallback matrix — sudah PASS di [04](04_Entitlement_System.md).
- **Promo terjadwal** dengan CheckConstraint DB (`end>start`, `value>0`, `percent≤100`) + validasi timezone-aware.
- **F9 renewal flow**: middleware mengecualikan `/subscriptions/payment/` agar user EXPIRED bisa membayar — diuji `ExpiredUserRenewalFlowTests`.
- **CSRF**: webhook `csrf_exempt` (benar untuk eksternal); `create_payment` tetap dilindungi CsrfViewMiddleware + token AJAX.

---

## 5. Prioritas Tindakan

| Prioritas | Temuan | Alasan |
|-----------|--------|--------|
| **P0 — sebelum go-live** | ✅ SELESAI (A1 SUB-3, A2 SUB-4, A3 SUB-2, A11 SUB-1) | Semua blocker go-live tertutup; sisa P1+ (A4/A12/...) bukan blocker langsung |
| **P1 — integritas transaksi** | ✅ SELESAI (A4 SUB-5, A6/A7/A8 SUB-6, A12 ACC-1) | Semua P1 webhook/pricing tertutup |
| **P2 — integritas bisnis/data** | ✅ SELESAI (A15 ACC-2, A13 SUB-7) | Pengingat expiry + uniqueness default entitlement (terverifikasi PG15) |
| **P3 — kebersihan/perf** | ✅ SELESAI (A9 SUB-8, A10a SUB-9, A14 SUB-10/ACC-4, A16 ACC-3) | Semua kebersihan/perf tertutup |
| **Informational** | A17 (~~A8 SUB-6, A10b SUB-9 FIXED~~) | Edge-case watermark mid-session |

---

## 6. Hasil Verifikasi Runtime

- `python manage.py makemigrations --check --dry-run`: **PASS**, tidak ada perubahan migrasi yang belum dibuat.
- `python manage.py check`: **PASS**, tidak ada system-check error.
- `python manage.py test subscriptions --settings=config.settings.test --noinput`: **PASS, 53/53 test** (subscriptions; ACC-2/ACC-4 menambah test di app accounts).
- `python manage.py test subscriptions accounts --settings=config.settings.test --noinput`: **PASS, 90 test (skipped=3)** setelah SUB-1..SUB-10 + ACC-1/2/3/4 + SUB-7 (3 test PG di-skip di SQLite).
- `python manage.py test subscriptions.tests_pg --settings=config.settings.test_pg`: **PASS, 3/3 test di PostgreSQL 15** (A13 constraint + A12 lock konkuren).
- `makemigrations --check` untuk SUB-7 dijalankan via **`config.settings.base`** (migrasi nyata) — `config.settings.test` memakai `MIGRATION_MODULES=DisableMigrations` sehingga cek migrasi di test settings tidak valid.
- Eksekusi test harus memakai `config.settings.test`; settings ini sengaja menonaktifkan `TimeoutMiddleware` yang dapat mengganggu autentikasi `force_login` pada Django test client.
- Automated test saat ini sudah mencakup SUB-1 (A5/A11), SUB-2 (A3), SUB-3 (A1), SUB-4 (A2), ACC-1 (A12/EC-1), SUB-5 (A4), SUB-6 (A6/A7/A8), ACC-2 (A15), SUB-8 (A9), SUB-9 (A10a/A10b), SUB-10/ACC-4 (A14), ACC-3 (A16), dan **SUB-7 (A13 + A12 PG)**. **A12 (lock konkuren) & A13 (`NULLS NOT DISTINCT`) kini terverifikasi langsung di PostgreSQL 15** via `config.settings.test_pg` (3 test PG-only, di-skip pada SQLite). Caveat go-live PG tertutup.

---

## 7. Catatan Tindak Lanjut

- Temuan ini **belum diperbaiki** (audit read-only). Setiap dokumen per-halaman memuat rekomendasi + status `[ ]`/`[~]` per test case.
- Dokumen [04 Entitlement](04_Entitlement_System.md) tetap berstatus PASS; A9 ditambahkan sebagai follow-up minor non-blocking.
- Halaman pricing kini ditangani oleh app `pages` (route `subscriptions/pricing/` hanya redirect 302) — lihat [06](06_Subscriptions_Pricing_Page.md).
- A8 dikalibrasi: pertahankan 403 untuk signature tidak sah; keputusan mengubah 404 menjadi 200 hanya berlaku untuk order tidak dikenal yang signature-nya valid dan harus disertai logging/alerting.
- A10b diturunkan menjadi informational karena tidak mengubah perilaku efektif saat ini.
- A11-A13 merupakan temuan tambahan dari verifikasi independen dan belum tercakup dalam dokumen detail per-halaman.
