# R3.7 - Review Cross-App Integration (subscriptions ↔ app lain)

**Status:** `[~]` AUDIT INTEGRASI SELESAI — kontrak inti terverifikasi; 2 MED (A14/A15), 1 LOW (A16), 1 INFO (A17)
**Terakhir diperbarui:** 2026-06-23 (Claude Code; sweep repo-wide sesuai pelajaran cross-cutting UF-013/AT-01)
**Metode:** grep repo-wide untuk setiap konsumen `subscriptions`/helper langganan + telaah kode titik integrasi. Runtime 23/23 PASS (lihat [00](00_Audit_Summary_20260623.md)).

---

## 1. Peta Ketergantungan

### 1.1 Inbound — app lain bergantung pada `subscriptions`/entitlement

| Konsumen | Bergantung pada | Untuk |
|----------|-----------------|-------|
| `accounts/middleware.py` | `get_feature_access(FEATURE_WRITE_ACCESS)` | Gating write global (POST/PUT/PATCH/DELETE) |
| `accounts/mixins.py` | decorator write/pro/export PDF/Excel-Word | Dipakai view detail_project & dashboard |
| `accounts/models.py` | `FEATURE_WRITE_ACCESS`, `FEATURE_EXPORT_CLEAN` | Properti `can_edit`, `can_export_clean` |
| `accounts/context_processors.py` | `get_feature_access(PDF, EXCEL_WORD)` ×2 | Flag tombol export di semua template (global) |
| `detail_project/views_api.py` | `FEATURE_PRO_ONLY` + `api_pdf_export_allowed` | Gating fitur Pro + 6 endpoint export PDF |
| `detail_project/views_export.py` | `api_pdf_export_allowed`, `api_export_excel_word_required` | Export sesi multi-step + watermark |
| `dashboard/views_export.py` | `api_export_excel_word_required`, `api_pdf_export_allowed` | Export xlsx/csv/pdf + watermark |
| `pages/views.py` | `get_active_pricing_plans()` | Landing + halaman pricing |
| `referensi/views/admin_portal.py` + `forms/pricing.py` | `SubscriptionPlan`, `SubscriptionPlanPromotion`, pricing_service | Kelola harga/promo (staff) |

### 1.2 Outbound — `subscriptions` bergantung pada

| Target | Dipakai untuk |
|--------|---------------|
| `accounts.CustomUser` | `activate_subscription`, `has_full_access`, `is_pro_active`, `is_trial_active`, `subscription_status`, `is_subscription_active` |
| `config.settings` | `MIDTRANS_SERVER_KEY/CLIENT_KEY/IS_PRODUCTION`, `SITE_URL` |
| Midtrans API (eksternal) | Snap token + (idealnya) status reconcile |
| `pages:pricing` (route `/pricing/`) | Target redirect upgrade/expired/legacy |
| allauth `email_confirmed` | Sinyal mulai trial (`accounts/signals.py`) |
| Celery (task di `accounts/tasks.py`) | Expiry harian + reminder |

---

## 2. Kontrak Integrasi — TERVERIFIKASI BAIK ✅

| # | Kontrak | Bukti |
|---|---------|-------|
| C-1 | **Single-writer aktivasi PRO**: hanya webhook (`subscriptions/views.py:203`) memanggil `activate_subscription`. Tak ada app lain membypass snapshot/locking. | grep repo-wide `activate_subscription` |
| C-2 | **Single-owner status langganan**: mutasi `subscription_status`/`*_end_date` di kode produksi hanya `accounts` (model methods + Celery tasks). | grep repo-wide |
| C-3 | **Entitlement = SSOT tunggal**: middleware, mixins, model props, context processor semua lewat `get_feature_access`. Tak ada cek `subscription_status` ad-hoc yang menggantikan policy engine di jalur write/export. | grep `FEATURE_`/`get_feature_access` |
| C-4 | **Export gating + watermark konsisten**: dashboard & detail_project meng-gate via decorator DAN benar-benar menggambar watermark dari `pdf_export_context`/`session.metadata`. | `dashboard/views_export.py:665-680`, `detail_project/views_export.py:448-478` |
| C-5 | **Navigasi `/pricing/` konsisten**: route ada di `pages.urls` (`pricing/`), cocok dengan `upgrade_url="/pricing/"` entitlement, redirect middleware, menu export terkunci (`/pricing/?reason=export_locked`), dan CTA pricing/landing → `subscriptions:checkout plan.id`. | `pages/urls.py:8`, `config/urls.py`, template grep |
| C-6 | **Admin pricing/promo lewat ModelForm/formset** → `model.clean()` + CheckConstraint tetap berjalan (parity validasi); form `DateTimeField` mengaktifkan `from_current_timezone` sehingga lolos cek timezone-aware. | `referensi/forms/pricing.py`, `admin_portal.py:275-285` |
| C-7 | **Trial signal wired**: `accounts.apps.ready()` mengimpor `accounts.signals` (`email_confirmed` → `start_trial`). | `accounts/apps.py:8-10` |
| C-8 | **Snapshot decouple dari edit plan**: harga/promo diubah staff via referensi tidak mempengaruhi transaksi lampau (snapshot immutable). | `PaymentTransaction.*_snapshot` |
| C-9 | **Middleware exclusions tepat**: `/subscriptions/payment/` reachable utk renewal EXPIRED (F9); webhook anonim; `/pricing/`, `/`, `/accounts/` GET. | `accounts/middleware.py:30-45` |

---

## 3. Temuan Integrasi (Findings)

| ID | Severity | Deskripsi | Lokasi | Evidence |
|----|----------|-----------|--------|----------|
| **A14** | 🟠 MED | `subscription_context` adalah context processor **global** (terdaftar di `TEMPLATES`), jalan tiap render terotentikasi dan memanggil `get_feature_access` **dua kali** (PDF + Excel/Word). Tiap panggilan: lookup `SubscriptionFeature` + `_latest_success_plan_for_user` (query `PaymentTransaction`) + lookup `PlanFeatureEntitlement`. **Tanpa memoization per-request** (tak ada cache di `entitlements.py`). Akibat: ~beberapa query ekstra per halaman, di **seluruh** app — plus middleware memanggil `get_feature_access` sekali lagi pada request write. | `accounts/context_processors.py:36-53`, `config/settings/base.py:146`, `subscriptions/entitlements.py:163-237` | Telaah kode + grep cache |
| **A15** | 🟢 FIXED (ACC-2) | `send_expiry_reminder` kini benar-benar mengirim email (`send_mail`) ke user trial/PRO yang expired ≤3 hari — salam personal + sisa hari + link `/pricing/` + support email. Bukan lagi stub. | `accounts/tasks.py:send_expiry_reminder` | Regression: `ExpiryReminderEmailTests` (3/3) |
| **A16** | 🟡 LOW | `subscription_status` tersimpan bisa **stale** (`PRO`/`TRIAL`) di jendela antara momen lapse dan task harian `check_subscription_expiry` (00:05). Entitlement dinormalisasi benar saat runtime (gating aman), tetapi context processor memakai field mentah: badge tampil `PRO` dan `show_upgrade_banner=False` untuk user yang efektif sudah expired → UX membingungkan (badge PRO tapi write ditolak). | `accounts/context_processors.py:48,56-62`, `accounts/tasks.py:13-47` | Telaah kode |
| **A17** | ℹ️ INFO | Pada export multi-step `detail_project`, flag watermark dibekukan ke `session.metadata` saat `export_init`. Bila entitlement berubah (mis. trial→expired) antara init dan finalize, hasil memakai flag lama. Edge case, dampak rendah. | `detail_project/views_export.py:56-66,448-453` | Telaah kode |

---

## 4. Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Memoize keputusan entitlement per-request: hitung matrix sekali (mis. attach ke `request`, atau cache `(user.pk, feature_code)` dalam siklus request) dan pakai ulang di middleware + context processor. | P3 | Med | A14 |
| REC-2 | Implementasikan pengiriman email pada `send_expiry_reminder` (pakai template + `support_email`), atau nonaktifkan jadwal bila belum siap agar tak memberi rasa aman palsu. | P2 | Med | A15 |
| REC-3 | Turunkan badge & banner dari status **efektif** (`is_pro_active`/`is_trial_active`) alih-alih `subscription_status` mentah; atau jalankan `check_and_expire()` lazily saat akses. | P3 | Low | A16 |
| REC-4 | (Opsional) Re-evaluasi entitlement saat `export_finalize`, bukan hanya saat init. | P4 | Low | A17 |

---

## 5. Catatan untuk Implementation Plan

- **Cakupan internal app `subscriptions` + lintas-app sudah disapu** (inbound & outbound). Tidak ditemukan: penulis status liar, cek entitlement ad-hoc yang membypass policy engine, route pricing yang tidak match, atau bypass validasi pada admin pricing.
- **Blocker go-live tetap A1/A2/A3/A11** (lihat [00](00_Audit_Summary_20260623.md)). Temuan lintas-app A14–A17 **bukan** blocker go-live tetapi harus masuk backlog implementasi.
- **Dependensi perbaikan lintas-app**: fix A14 menyentuh `accounts` (middleware + context processor) selain `subscriptions/entitlements.py`; fix A15/A16 murni di `accounts`. Implementation plan harus memperlakukan `accounts` sebagai bagian dari blast-radius perbaikan langganan, bukan hanya folder `subscriptions/`.
- **Belum ada test** untuk A11/A12/A13/A14/A15/A16 — tulis regression saat fase perbaikan.

---

## 6. Checklist Sign-off

- [x] Peta ketergantungan inbound/outbound dipetakan
- [x] Kontrak integrasi C-1..C-9 terverifikasi
- [x] Tidak ada penulis status langganan liar / cek entitlement ad-hoc
- [x] Navigasi pricing/checkout/upgrade konsisten
- [~] Performa lintas-page (→ A14)
- [x] Kelengkapan lifecycle (reminder email A15 tertutup ACC-2)
- [ ] Reviewer sign-off
