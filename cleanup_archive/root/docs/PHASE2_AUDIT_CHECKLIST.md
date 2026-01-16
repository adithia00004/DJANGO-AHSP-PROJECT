# Phase 2 Audit Checklist & Workflow Guide

Dokumen ini berisi panduan untuk memverifikasi seluruh komponen **SaaS Infrastructure & Monetization** yang telah diimplementasikan. Gunakan daftar ini untuk memastikan semua fitur berjalan sesuai ekspektasi.

## 📋 Daftar Halaman untuk Diperiksa

| Halaman | URL Local | Ekspektasi |
|---------|-----------|------------|
| **Landing Page** | `http://localhost:8000/` | Hero section, Features, Pricing cards, FAQ, Footer. Tombol 'Login'/'Mulai Gratis'. |
| **Pricing Page** | `http://localhost:8000/subscriptions/pricing/` | 3 Paket (Quarterly, Semi, Annual) dengan harga benar. Tombol Action. |
| **Register** | `http://localhost:8000/accounts/signup/` | Form: Email (wajib), Username, Password. |
| **Login** | `http://localhost:8000/accounts/login/` | Login menggunakan **Email** (bukan username). |
| **Email Helper** | Docker Console Logs | Link verifikasi email akan muncul di terminal docker. |
| **Dashboard** | `http://localhost:8000/dashboard/` | Redirect kesini setelah login. Indikator status subscription (jika ada). |
| **Admin Panel** | `http://localhost:8000/admin/` | Management SubscriptionPlans, PaymentTransactions, Users. |

---

## 🧪 Workflow Checklist

### 1. Authentication & Onboarding Flow
- [ ] **Registrasi User Baru:**
    - Buka halaman Signup.
    - Isi email sample (misal: `test01@example.com`).
    - **Verify:** Harusnya redirect ke halaman "Verifikasi E-mail Anda".
    - **Action:** Cek terminal docker (`docker-compose logs web`), cari link verifikasi (console backend).
    - **Action:** Klik link verifikasi tersebut.
    - **Verify:** User berhasil login dan masuk ke Dashboard.
- [ ] **Cek Status Awal (Trial):**
    - Masuk ke Admin Panel (`/admin`).
    - Buka user `test01@example.com`.
    - **Verify:** `Subscription Status` = **TRIAL**.
    - **Verify:** `Trial End Date` terisi (H+14 dari hari ini).

### 2. Feature Restriction (Access Control)
- [ ] **Test Write Access (Trial User):**
    - Sebagai user Trial, coba buat Project baru atau edit data AHSP.
    - **Verify:** Operasi berhasil (Trial user punya akses full fitur).
- [ ] **Simulasi Expired User:**
    - Di Admin Panel, ubah user tadi:
        - `Subscription Status` ➔ **EXPIRED**.
        - `Subscription End Date` ➔ kosongkan atau set tanggal lampau.
    - Simpan.
- [ ] **Test Write Block (Expired User):**
    - Di browser, coba Edit Project atau Simpan Harga di dashboard.
    - **Verify:** Harusnya GAGAL. Jika via API, return JSON error 403. Jika form submit, muncul pesan error/warning.
    - **Verify:** Read access (lihat data) masih bisa jalan.

### 3. Payment Flow (Midtrans Integration)
*Note: Ini membutuhkan koneksi internet dan Midtrans Sandbox Environment.*

- [ ] **Initiate Payment:**
    - Login sebagai user.
    - Buka `/subscriptions/pricing/`.
    - Klik salah satu paket (misal: 3 Bulan).
    - **Verify:** (Jika Frontend JS belum dipasang) Harusnya return JSON response sukses berisi `snap_token`.
    - *Jika JSON muncul, artinya backend `/payment/create/` sukses.*

- [ ] **Simulasi Webhook (via Postman/cURL):**
    - Kita akan pura-pura menjadi Midtrans yang mengirim notifikasi "Settlement" (Pembayaran Sukses).
    - Ambil **Order ID** dari JSON response langkah sebelumnya (atau lihat di Admin Panel row paling atas).
    - Gunakan tool seperti Postman mengirim **POST** ke `http://localhost:8000/subscriptions/webhook/midtrans/`.
    - **Set Header:** `Content-Type: application/json`
    - **Body JSON:**
      ```json
      {
        "order_id": "paste_order_id_disini",
        "transaction_status": "settlement",
        "fraud_status": "accept",
        "status_code": "200",
        "gross_amount": "900000",
        "signature_key": "generate_signature_manual_jika_verifikasi_aktif" 
      }
      ```
      *(Note: Signature verification di backend mungkin akan reject kalau signature salah. Cara termudah bypass untuk test manual adalah matikan sementara `verify_signature` di `views.py` atau generate signature SHA512 valid: `order_id+200+amount+server_key`)*.

- [ ] **Verify Pro Status:**
    - Jika webhook sukses (`HTTP 200`), cek Admin Panel.
    - **PaymentTransaction:** Status harusnya **Success**.
    - **User:** Status harusnya **PRO**, dan `Subscription End Date` bertambah sesuai durasi paket.

---

## 🛠️ Troubleshooting Guide

**Isu: Email verifikasi tidak muncul.**
- **Cek:** `settings.py`, pastikan `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`.
- **Cek:** Docker logs. Kadang tertumpuk log lain.

**Isu: 403 Forbidden saat Webhook.**
- Ini karena **Signature Verification** gagal.
- **Solusi Dev:** Di `subscriptions/views.py`, comment sementara logic `midtrans_client.verify_signature(...)` untuk testing manual tanpa signature generator yang ribet. Jangan lupa uncomment untuk production!

**Isu: Landing page berantakan.**
- **Cek:** Browser hard refresh (`Ctrl+F5`) untuk update CSS.
- **Cek:** Pastikan file static sudah terload (cek Network tab console browser).

**Isu: Feature Restriction tidak jalan (User Expired masih bisa edit).**
- **Cek:** Pastikan user benar-benar status **EXPIRED** di database.
- **Cek:** Pastikan Middleware `accounts.middleware.SubscriptionMiddleware` aktif di `settings.py`.
- Notes: Superuser/Admin mungkin di-bypass oleh logic tertentu (walau di code saat ini `is_authenticated` saja yang dicek, tapi pastikan tidak testing pakai Superuser).

---

## ✅ Final Verification
Jika semua checklist di atas lolos, maka sistem SaaS backend (Auth, Subs logic, Payment gateway core) sudah siap untuk integrasi Frontend lebih lanjut.
