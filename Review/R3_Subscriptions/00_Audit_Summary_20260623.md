# R3.0 - Ringkasan Audit App `subscriptions`

**Status:** `[~]` AUDIT + VERIFIKASI RUNTIME; **M1 + M2 SELESAI — semua P0 & P1 FIXED (SUB-1..6 + ACC-1)** — sisa M3/M4 (A13/A15/A9/A10a/A14/A16); A12/A13 perlu gate PG15
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

Arsitektur app memiliki fondasi yang baik: harga dihitung server-side dengan snapshot immutable, webhook memakai row-lock (`select_for_update`), entitlement data-driven dengan fallback matrix deterministik, dan test coverage layak. SUB-1 menutup replay setelah refund/terminal (A11) + kebijakan refund revoke/late terminal (A5); SUB-2 menutup uniqueness order id (A3); SUB-3 menutup checkout produksi (A1, Snap.js prod/sandbox); SUB-4 menutup rekonsiliasi webhook terlewat (A2); ACC-1 menutup lost-update aktivasi konkuren (A12) + refund account-wide (EC-1). **Semua P0 (go-live) + P1 (A4/A6/A7/A8/A12) tertutup; M1 & M2 selesai.** SUB-5 menutup verifikasi field webhook (A4); SUB-6 menutup rate-limit `create_payment`/constant-time/respons webhook (A6/A7/A8). Sisa (bukan blocker): uniqueness entitlement (A13), kebersihan (A9/A10a), perf/lifecycle (A14–A16). A12 (lock lintas-koneksi) & A13 perlu gate PostgreSQL 15.

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
| **A9** | 🟡 LOW | `except Exception: pass` di entitlements menelan error DB tanpa log | [04](04_Entitlement_System.md) |
| **A10a** | 🟡 LOW | Tak ada pencegahan transaksi `pending` ganda (TC-4) | [02](02_Payment_Flow.md) |
| **A10b** | ℹ️ INFO | Cek `subscription_status=='PRO' and is_subscription_active` ekuivalen dengan `is_pro_active` untuk user non-staff; penggantian hanya penyederhanaan/refactor | [01](01_Checkout_Page.md) |
| **A11** | 🟢 FIXED (SUB-1) | Idempotensi aktivasi kini berbasis `paid_at`; replay `settlement` setelah refund tidak mengaktifkan/memperpanjang subscription ulang | [05](05_Webhook_Security.md), [02](02_Payment_Flow.md) |
| **A12** | 🟢 FIXED (ACC-1) | `activate_subscription` re-read baris user di bawah `select_for_update` + hitung dari nilai terkunci → pembayaran konkuren menumpuk (lock lintas-koneksi perlu gate PG15) | `accounts/models.py:activate_subscription` |
| **A13** | 🟠 MED | UniqueConstraint entitlement `(feature, plan, status)` tidak mencegah beberapa default row dengan `plan=NULL` di PostgreSQL | `subscriptions/models.py:212-219` |
| **A14** | 🟠 MED | Context processor global `subscription_context` memanggil `get_feature_access` **2×** tiap render terotentikasi tanpa memoization per-request → overhead query repo-wide (tiap halaman) | [07](07_Cross_App_Integration_20260623.md) |
| **A15** | 🟠 MED | Task terjadwal `accounts.send_expiry_reminder` adalah **stub** (`TODO: Implement actual email sending`) → tak ada email pengingat dikirim; user lapse tanpa peringatan | [07](07_Cross_App_Integration_20260623.md) |
| **A16** | 🟡 LOW | `subscription_status` tersimpan bisa stale (PRO/TRIAL) antara saat lapse dan task harian 00:05 → badge & `show_upgrade_banner` di context processor pakai field mentah (gating tetap benar) | [07](07_Cross_App_Integration_20260623.md) |
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
| **P2 — integritas bisnis/data** | A13, A15 | Uniqueness default entitlement dan pengingat expiry |
| **P3 — kebersihan/perf** | A9, A10a, A14, A16 | Robustness, konsistensi, dan overhead query lintas-page |
| **Informational** | A10b, A17 (~~A8 FIXED SUB-6~~) | Penyederhanaan kode, edge-case watermark |

---

## 6. Hasil Verifikasi Runtime

- `python manage.py makemigrations --check --dry-run`: **PASS**, tidak ada perubahan migrasi yang belum dibuat.
- `python manage.py check`: **PASS**, tidak ada system-check error.
- `python manage.py test subscriptions --settings=config.settings.test --noinput`: **PASS, 49/49 test** setelah SUB-1..SUB-6 + ACC-1.
- `python manage.py test subscriptions accounts --settings=config.settings.test --noinput`: **PASS, 76/76 test** setelah SUB-1..SUB-6 + ACC-1.
- Eksekusi test harus memakai `config.settings.test`; settings ini sengaja menonaktifkan `TimeoutMiddleware` yang dapat mengganggu autentikasi `force_login` pada Django test client.
- Automated test saat ini sudah mencakup SUB-1 (A5/A11), SUB-2 (A3), SUB-3 (A1), SUB-4 (A2), ACC-1 (A12/EC-1), SUB-5 (A4), dan SUB-6 (A6/A7/A8). Skenario A13 + A14–A16 belum tercakup; **A12 (lock lintas-koneksi) & A13 perlu gate PostgreSQL 15** (SQLite test backend tak membuktikan locking/`NULLS NOT DISTINCT`).

---

## 7. Catatan Tindak Lanjut

- Temuan ini **belum diperbaiki** (audit read-only). Setiap dokumen per-halaman memuat rekomendasi + status `[ ]`/`[~]` per test case.
- Dokumen [04 Entitlement](04_Entitlement_System.md) tetap berstatus PASS; A9 ditambahkan sebagai follow-up minor non-blocking.
- Halaman pricing kini ditangani oleh app `pages` (route `subscriptions/pricing/` hanya redirect 302) — lihat [06](06_Subscriptions_Pricing_Page.md).
- A8 dikalibrasi: pertahankan 403 untuk signature tidak sah; keputusan mengubah 404 menjadi 200 hanya berlaku untuk order tidak dikenal yang signature-nya valid dan harus disertai logging/alerting.
- A10b diturunkan menjadi informational karena tidak mengubah perilaku efektif saat ini.
- A11-A13 merupakan temuan tambahan dari verifikasi independen dan belum tercakup dalam dokumen detail per-halaman.
