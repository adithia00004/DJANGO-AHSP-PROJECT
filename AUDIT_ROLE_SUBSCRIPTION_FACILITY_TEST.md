# AUDIT ROLE, SUBSCRIPTION, FACILITY, DAN TEST
## Django AHSP Project
**Tanggal audit:** 2026-02-08  
**Tujuan:** Menjadi dokumen fokus untuk memastikan setiap role memiliki akses/fasilitas yang tepat, subscription berjalan benar, dan pengujian cukup kuat untuk scale ke depan.

---

## 1) Scope Audit

Area yang dicakup:
- Autentikasi, redirect login, dan pemisahan area user/admin.
- Otorisasi role/permission untuk modul referensi dan fitur utama aplikasi.
- Subscription plan, status subscription, dan enforcement fasilitas.
- Matrix fasilitas per role/subscription.
- Test strategy (otomatis + manual) untuk validasi behavior.

Dokumen ini melengkapi:
- `AUDIT_PRE_LAUNCH.md` (ringkasan pre-launch umum).

---

## 2) Baseline Implementasi Saat Ini

### 2.1 Auth & Identity
- User model: `accounts.CustomUser`.
- Backend auth: Django + allauth.
- Redirect login:
  - Berbasis helper akses portal referensi (`has_referensi_portal_access`) untuk staff/admin.
  - User reguler diarahkan ke dashboard.

### 2.2 Role & Permission Gate
- Helper terpusat:
  - `referensi.permissions.has_referensi_portal_access`
  - `referensi.permissions.has_referensi_import_access`
- Referensi admin portal dan import flow sudah diseragamkan ke permission-based gate.

### 2.3 Subscription
- Status user saat ini: `TRIAL`, `PRO`, `EXPIRED`.
- Plan komersial disimpan di `SubscriptionPlan` (durasi 3/6/12 bulan; dapat ditambah data plan baru).
- Enforce akses sekarang memakai policy engine terpusat `subscriptions.entitlements.get_feature_access(...)`.
- Matrix entitlement dimodelkan data-driven via:
  - `subscriptions.SubscriptionFeature`
  - `subscriptions.PlanFeatureEntitlement` (status-level default + plan-level override)
- Admin/staff full-access diperlakukan sebagai bypass akses subscription dan sekarang diblok dari flow checkout/payment creation.

### 2.4 Facility/Entitlement yang Sudah Dijalankan
- Trial/pro/expired sudah memengaruhi akses write/export.
- Upgrade banner admin sudah disesuaikan agar tidak salah tampil.
- Non-API write untuk user expired sudah ditolak via redirect pricing.

---

## 3) Definisi Role Operasional

Role operasional yang dipakai untuk audit:
1. `superuser`
2. `staff_with_referensi_perms`
3. `staff_without_referensi_perms`
4. `regular_trial`
5. `regular_pro`
6. `regular_expired`

Catatan:
- Role internal (`staff/superuser`) dan subscription status masih hidup berdampingan.
- Untuk scale jangka panjang, keduanya sebaiknya dipisahkan lebih tegas di layer policy.

---

## 4) Matrix Fasilitas (Target vs Aktual)

### 4.1 Target Behavior

| Fitur / Area | superuser | staff_with_referensi_perms | staff_without_referensi_perms | regular_trial | regular_pro | regular_expired |
|---|---|---|---|---|---|---|
| Login & redirect ke area kerja | Admin Portal | Admin Portal | Dashboard | Dashboard | Dashboard | Dashboard |
| Akses dashboard/project milik sendiri | Ya | Ya | Ya | Ya | Ya | Read-only |
| Akses Referensi Admin Portal | Ya | Ya | Tidak | Tidak | Tidak | Tidak |
| Akses import referensi | Ya | Ya | Tidak | Tidak | Tidak | Tidak |
| Checkout subscription | Diblok | Diblok | Diblok | Ya | Umumnya tidak perlu saat aktif | Ya (untuk reaktivasi) |
| Create payment transaction | Diblok | Diblok | Diblok | Ya | Ya (sesuai policy billing) | Ya |
| Write operation (save/edit data) | Ya | Ya | Ya | Ya | Ya | Ditolak |
| Export PDF | Ya (clean) | Ya (clean) | Ya (clean) | Ditolak | Ya (clean) | Ya (watermark) |
| Export Excel/Word | Ya | Ya | Ya | Ditolak | Ya | Ditolak |
| Export download (GET) | Ya | Ya | Ya | Sesuai tier | Sesuai tier | Sesuai tier |

### 4.2 Kondisi Aktual (Gap Analysis)

| Fitur / Area | Target | Aktual | Gap? |
|---|---|---|---|
| Login redirect | Sesuai role | Sesuai role | OK |
| Referensi portal access | Permission-based | Permission-based | OK |
| Checkout admin block | Diblok | Diblok (`_is_managed_access_user`) | OK |
| Write expired block (API POST) | Ditolak 403 | Ditolak via middleware | OK |
| Write expired block (form POST) | Redirect pricing | Redirect pricing | OK |
| **Export PDF trial** | **Ditolak** | **Ditolak via `api_pdf_export_allowed`** | **OK** |
| **Export Excel/Word trial** | **Ditolak** | **Ditolak via `api_export_excel_word_required`** | **OK** |
| **Export Excel/Word expired** | **Ditolak** | **Ditolak via `_enforce_export_tier()`** | **OK** |
| **Export PDF expired** | **Watermark** | **Allowed dengan flag watermark pada metadata/options** | **OK** |
| **Export download GET** | **Sesuai tier** | **Sudah tier-protected (`export_download`, `api_export_download_async`)** | **OK** |
| **Export legacy PDF (views_api.py)** | **Sesuai tier** | **Sudah di-protect `api_pdf_export_allowed`** | **OK** |
| **Export legacy Word/Excel/CSV (views_api.py)** | **Sesuai tier** | **Sudah PRO-only via `_api_pro_export_required(...)`** | **OK** |
| **Export legacy JSON (views_api.py)** | **Perlu keputusan** | **Diputuskan PRO-only; semua endpoint JSON sudah di-protect** | **OK** |
| **Dashboard export (views_export.py)** | **Sesuai tier** | **Sudah diproteksi (`xlsx/csv` PRO-only, `pdf` pakai `api_pdf_export_allowed`)** | **OK** |
| Webhook idempotency | Skip jika sudah SUCCESS | Row lock + duplicate success guard | OK |

### 4.3 Root Cause Gap

Gap decorator di endpoint export aktif dan endpoint legacy sudah ditutup pada 2026-02-08 dengan:
- enforcement format-tier terpusat (`detail_project/views_export.py`),
- hardening endpoint legacy (`detail_project/views_api.py`),
- hardening endpoint dashboard export (`dashboard/views_export.py`).

Keterangan:
- Matrix target adalah definisi operasional. Jika kebutuhan bisnis berubah, update matrix terlebih dahulu sebelum ubah kode.

---

## 5) Temuan Utama dan Status

### 5.1 Sudah Ditangani
1. Otorisasi referensi/import sudah dipusatkan ke helper permission.
2. Redirect role pasca-login/root sudah konsisten berbasis permission portal.
3. Checkout/payment creation untuk akun full-access sudah diblok eksplisit.
4. Banner upgrade admin sudah diperbaiki.
5. Non-API write untuk expired user sudah ditolak.
6. Guard environment production (`DJANGO_ENV`) sudah ditambahkan.

### 5.2 Update Penutupan Gap Role/Subscription (CLOSED 2026-02-08)
1. Policy engine tunggal level fitur sudah aktif:
   - `subscriptions/entitlements.py` (`get_feature_access`, `has_feature_access`).
2. Entitlement tidak lagi hardcoded penuh di layer gate:
   - middleware/mixins/user property sudah mengacu ke policy engine.
3. Matrix tier/facility dimigrasi ke model data-driven:
   - default matrix per status (`TRIAL/PRO/EXPIRED`) disimpan di DB.
   - support override per plan disimpan di DB.
4. Relasi `SubscriptionPlan` -> feature entitlements sudah tersedia:
   - melalui `PlanFeatureEntitlement.plan` (related name: `feature_entitlements`).
5. Negative test referensi/import tanpa permission sudah ditambahkan dan PASS:
   - `referensi/tests/test_import_permissions.py`.

### 5.3 KRITIS - Decorator Subscription pada Export Endpoint (CLOSED)

**Status implementasi (2026-02-08):**
- `detail_project/views_export.py` sekarang memakai `@api_pdf_export_allowed` pada endpoint export aktif.
- Enforcement format-tier dipusatkan lewat `_enforce_export_tier()`:
  - PDF: PRO clean, EXPIRED boleh dengan watermark flag.
  - Word/Excel: wajib PRO via `@api_export_excel_word_required`.
- Endpoint GET download sekarang ikut policy tier:
  - `export_download()`
  - `api_export_download_async()`

**Regression test yang ditambahkan:**
- `detail_project/tests_export_access.py`
  - trial blocked untuk PDF download.
  - expired blocked untuk Word download.
  - expired allowed untuk PDF download.
  - async download mengikuti rule tier yang sama.

### 5.4 KRITIS - Legacy Export Endpoints Tanpa Tier Policy (CLOSED)

**Status implementasi (2026-02-08):**
- `detail_project/views_api.py` sudah diberi enforcement tier untuk endpoint legacy export:
  - PDF: `api_pdf_export_allowed`
  - Word/XLSX/CSV: PRO-only via `_api_pro_export_required(...)`
  - JSON: diputuskan **PRO-only** dan semua endpoint JSON sudah diproteksi.
- `export_jadwal_pekerjaan_professional` sudah memakai policy dinamis:
  - `format=pdf` mengikuti `api_pdf_export_allowed`
  - `format=word/xlsx` wajib PRO.
- `dashboard/views_export.py` sudah diproteksi:
  - `export_dashboard_xlsx` dan `export_csv`: PRO-only
  - `export_project_pdf`: `api_pdf_export_allowed`

**Regression test yang ditambahkan:**
- `detail_project/tests_export_access.py`
  - blokir trial/expired pada legacy `views_api` non-PDF sesuai policy.
  - blokir trial/expired pada dashboard export sesuai policy.
  - blokir expired untuk professional format `word`.

### 5.5 Webhook Payment Idempotency (CLOSED)

**Status implementasi (2026-02-08):**
- `PaymentWebhookView.post()` sekarang lock row transaction dengan `select_for_update()` di `transaction.atomic()`.
- Callback sukses duplikat di-skip jika transaksi sudah `SUCCESS` dan `paid_at` sudah terisi, sehingga `activate_subscription()` tidak dipanggil ulang.
- Metadata webhook (`midtrans_response`, `payment_type`, `midtrans_transaction_id`) tetap tersimpan untuk audit.

**Regression test yang ditambahkan:**
- `subscriptions/tests.py::PaymentWebhookIdempotencyTests`
  - callback settlement dua kali tidak memperpanjang subscription dua kali.
---

## 6) Strategy Test (Wajib)

### 6.1 Automated Test Minimum

Sudah tersedia baseline test:
- Redirect role (home/login/landing).
- Middleware subscription expired write behavior.
- Context banner admin.
- Checkout/payment policy staff/admin.

Tambahan test yang wajib dibuat:
1. Negative test untuk endpoint referensi/import penting dengan `staff_without_referensi_perms`. (**DONE**)
2. Test matrix per endpoint kritis:
   - Dashboard write API
   - Detail project write/export API
   - Referensi import/commit endpoint
   - Subscription checkout/payment
3. Regression test untuk perubahan policy redirect/permission.

### 6.2 Manual E2E Test Matrix

Akun uji:
- `superuser`
- `staff_with_referensi_perms`
- `staff_without_referensi_perms`
- `regular_trial`
- `regular_pro`
- `regular_expired`

Skenario wajib:
1. Login redirect tiap akun sesuai matrix.
2. Akses URL referensi/import langsung (harus terblokir untuk non-permitted).
3. Aksi write saat expired (API dan non-API) benar-benar tertolak.
4. Checkout/payment untuk full-access user tertolak.
5. Export behavior sesuai subscription status.

---

## 7) Rencana Pengembangan Infrastruktur (Roadmap)

### Phase A (Stabilisasi)
- Tutup semua negative test permission endpoint referensi/import.
- Pastikan semua gate menggunakan helper terpusat (hindari gate campuran).

### Phase B (Policy Consolidation)
- Bentuk policy layer tunggal untuk entitlement fitur.
- Kurangi hardcoded check status di view/template.

### Phase C (Scalable Subscription)
- Introduce model entitlement per plan (feature flags per plan).
- Support tier baru tanpa ubah banyak titik kode.
- Tambahkan audit trail perubahan entitlement/plan.

---

## 8) Checklist Readiness

- [x] Dokumen audit khusus role/subscription/facility/test tersedia.
- [x] Permission helper terpusat tersedia dan dipakai endpoint utama.
- [x] Redirect role berbasis akses portal konsisten.
- [x] Policy admin/staff untuk checkout/payment ditetapkan.
- [x] Baseline automated test untuk perubahan policy tersedia.
- [x] **KRITIS: Decorator subscription diterapkan di semua export endpoint `detail_project/views_export.py`.**
- [x] **KRITIS: Idempotency guard pada webhook payment (`PaymentWebhookView`).**
- [x] **TINGGI: Export download (GET) di-protect sesuai subscription tier.**
- [x] Negative test referensi/import tanpa permission sudah lengkap.
- [x] Negative test export per subscription tier (trial blocked, expired watermark/blocked).
- [x] **KRITIS: Tier policy diterapkan di endpoint legacy `detail_project/views_api.py`.**
- [x] **KRITIS: Tier policy diterapkan di endpoint `dashboard/views_export.py`.**
- [x] **TINGGI: Keputusan policy untuk endpoint JSON export + professional ditetapkan (PRO-only untuk JSON, dynamic policy untuk professional).**
- [x] Policy engine entitlement tunggal sudah diterapkan.
- [x] Tiering/facility matrix sudah dimigrasi penuh ke model data-driven.
- [x] `SubscriptionPlan` punya relasi ke feature entitlements (bukan hardcoded).

---

## 9) Catatan Operasional

- Setiap perubahan policy role/subscription wajib:
  1. Update matrix di dokumen ini.
  2. Update test otomatis terkait.
  3. Tambah entry pada log perubahan di `AUDIT_PRE_LAUNCH.md`.

