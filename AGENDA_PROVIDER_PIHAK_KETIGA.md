# AGENDA PROVIDER & PIHAK KETIGA
## Django AHSP Project

Dokumen ini untuk mengontrol pekerjaan eksternal/non-kode:
- pembelian domain
- penyediaan hosting/server
- integrasi provider email/payment
- pengaturan operasional pihak ketiga

Tanggal mulai: 2026-02-08
Status: ACTIVE

---

## 1) Aturan Eksekusi

1. Setiap item wajib punya `PIC`, `target date`, dan `bukti`.
2. Status hanya boleh: `TODO`, `IN PROGRESS`, `BLOCKED`, `DONE`.
3. Satu item dianggap `DONE` hanya jika bukti verifikasi sudah ada.
4. Semua perubahan provider dicatat di dokumen ini di hari yang sama.

---

## 2) Scope & Prioritas

### P0 (Wajib sebelum GO-LIVE)
- Domain aktif + DNS benar.
- Server/hosting siap + akses aman.
- SSL HTTPS aktif.
- DB backup & restore drill.
- Firewall/network restriction DB.

### P1 (Bergantung fitur launch)
- Provider email (jika verifikasi email wajib di launch).
- Provider payment Midtrans (jika subscription/payment aktif di launch).

### P2 (Setelah launch awal)
- Observability lanjutan (Sentry, alerting lanjutan, dashboard metrik).
- Optimasi biaya provider.

---

## 3) Tracker Utama

| ID | Workstream | Status | PIC | Target | Bukti |
|---|---|---|---|---|---|
| PVD-01 | Registrasi domain `rabdashboard.com` | TODO |  |  | Invoice + panel domain aktif |
| PVD-02 | DNS records (A/CNAME) untuk web/app/api | TODO |  |  | `dig/nslookup` hasil resolve |
| PVD-03 | Provision server production (VPS/Cloud) | TODO |  |  | Akses SSH key-only + spec server |
| PVD-04 | Hardening server (firewall, user non-root, fail2ban opsional) | TODO |  |  | Rule firewall + audit akses |
| PVD-05 | Deploy app stack (Django, Postgres, Redis, Nginx) | TODO |  |  | Health check endpoint 200 |
| PVD-06 | SSL cert + auto renew | TODO |  |  | HTTPS valid + renewal test |
| PVD-07 | DB backup job harian | TODO |  |  | Log backup + file backup terbaru |
| PVD-08 | DB restore drill di staging | TODO |  |  | Berita acara restore PASS |
| PVD-09 | Restriksi akses DB hanya internal | TODO |  |  | Konfigurasi network/pg_hba |
| PVD-10 | Email provider SMTP (conditional) | TODO |  |  | Kirim email test PASS |
| PVD-11 | Midtrans production key (conditional) | TODO |  |  | Payment sandbox/prod flow PASS |
| PVD-12 | Monitoring + alert dasar (uptime, 5xx, CPU/RAM) | TODO |  |  | Screenshot dashboard alert |

---

## 4) Checklist Per Workstream

### A. Domain & DNS
- [ ] Beli domain `rabdashboard.com`.
- [ ] Set nameserver sesuai provider.
- [ ] Buat record `A` untuk root domain.
- [ ] Buat record `CNAME` untuk `www`.
- [ ] Jika pakai subdomain API, set `api.rabdashboard.com`.
- [ ] Verifikasi propagasi DNS global.

### B. Hosting/Server
- [ ] Tentukan provider (contoh: Hostinger VPS/cloud).
- [ ] Tetapkan ukuran minimal server awal (contoh: 2 vCPU, 4 GB RAM).
- [ ] Aktifkan login SSH via key (nonaktifkan password login root).
- [ ] Buat user deploy non-root.
- [ ] Terapkan firewall hanya port yang diperlukan (80/443/SSH terbatas).

### C. Runtime Deployment
- [ ] Deploy aplikasi dengan env production.
- [ ] Set reverse proxy Nginx/Caddy.
- [ ] Aktifkan HTTPS.
- [ ] Jalankan `python scripts/prelaunch_autocheck.py` di server target.
- [ ] Jalankan smoke test manual end-to-end.

### D. Database & Reliability
- [ ] Backup otomatis harian aktif.
- [ ] Retensi backup ditentukan (contoh: 7/14/30 hari).
- [ ] Restore test berhasil di staging.
- [ ] Akses DB hanya dari private/internal network.

### E. Email Provider (Conditional)
- [ ] Pilih provider (SMTP transactional).
- [ ] Isi `EMAIL_HOST_USER` dan `EMAIL_HOST_PASSWORD`.
- [ ] Uji verifikasi email dan reset password.

### F. Payment Provider Midtrans (Conditional)
- [ ] Isi `MIDTRANS_SERVER_KEY` dan `MIDTRANS_CLIENT_KEY`.
- [ ] Set `MIDTRANS_IS_PRODUCTION=True` saat live payment.
- [ ] Uji checkout sukses + webhook + idempotency.

---

## 5) Keputusan Launch Scope

Isi salah satu skenario:

1. Launch tanpa payment/email wajib:
- Payment: OFF
- Email verification mandatory: OFF/ditunda
- Fokus: core app + dashboard + export policy

2. Launch dengan payment/email aktif:
- Payment: ON
- Email verification mandatory: ON
- Semua item provider P1 wajib DONE

Keputusan saat ini:
- Skenario terpilih: 
- Tanggal efektif:
- PIC approval:

---

## 6) Risiko Provider & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Domain belum aktif saat jadwal launch | Delay go-live | Lock domain purchase lebih awal |
| SSL gagal/expired | Akses user terganggu | Auto-renew + monitor expiry |
| Backup tidak valid | Risiko kehilangan data | Restore drill berkala |
| SMTP gagal | Verifikasi/reset tidak jalan | Fallback manual + provider alternatif |
| Payment callback bermasalah | Transaksi gagal/duplikat | Uji webhook end-to-end sebelum live |

---

## 7) Log Eksekusi Provider

| Tanggal | ID | Perubahan | Status | Bukti |
|---|---|---|---|---|
| 2026-02-08 | DOC-01 | Dokumen agenda provider dibuat | DONE | File ini dibuat |
| 2026-02-08 | DOC-02 | Tambah urutan purchasing + rekomendasi vendor + spesifikasi standar launch | DONE | Section 8-10 |

---

## 8) Urutan Purchasing & Integrasi (Disarankan)

1. Beli domain (`rabdashboard.com`).
2. Pilih registrar/DNS strategy:
   - Opsi A: beli domain di Hostinger, DNS di Cloudflare.
   - Opsi B: langsung transfer domain ke Cloudflare Registrar setelah masa lock memungkinkan.
3. Beli VPS production.
4. Setup DNS record (`A`, `CNAME`, opsional `api`), tunggu propagasi.
5. Provision server + hardening dasar (SSH key, firewall, non-root).
6. Deploy stack app (Django + Postgres + Redis + reverse proxy).
7. Aktifkan SSL (Let's Encrypt + auto renew).
8. Setup backup otomatis + restore drill staging.
9. (Conditional) Aktifkan provider email.
10. (Conditional) Aktifkan Midtrans production + webhook publik.
11. Jalankan `python scripts/prelaunch_autocheck.py` dan smoke test manual.
12. Isi keputusan `GO/NO-GO`.

---

## 9) Rekomendasi Vendor & Spesifikasi Standard

### A. Domain + DNS
- Registrar kandidat:
  - Hostinger (praktis jika sekaligus beli hosting/VPS).
  - Cloudflare Registrar (model at-cost, wajib gunakan Cloudflare authoritative DNS).
- DNS/CDN/WAF dasar:
  - Cloudflare Free sudah cukup untuk fase awal.

### B. VPS / Server
- Rekomendasi minimum untuk launch awal project ini:
  - 2 vCPU, 8 GB RAM, 100 GB NVMe, bandwidth >= 4 TB/bulan.
- Rekomendasi lebih aman (headroom):
  - 4 vCPU, 16 GB RAM, 200 GB NVMe.
- Mapping cepat (Hostinger):
  - KVM 2 = 2 vCPU / 8 GB / 100 GB.
  - KVM 4 = 4 vCPU / 16 GB / 200 GB.
- Catatan:
  - VPS Hostinger bersifat self-managed, jadi setup OS/security/deploy ditangani sendiri.

### C. Email (Conditional)
- Jika email verification/reset belum wajib di launch: boleh ditunda.
- Kandidat vendor:
  - Resend (developer-friendly, ada free tier).
  - Amazon SES (pay-as-you-go, cocok skala naik).

### D. Payment (Conditional)
- Midtrans (sesuai implementasi project saat ini).
- Kebutuhan minimum:
  - Server Key + Client Key dari MAP.
  - Notification URL publik HTTPS (tidak boleh localhost/private).
  - Verifikasi signature + idempotency webhook (sudah ditangani di codebase).

### E. Monitoring (Opsional tapi disarankan)
- UptimeRobot:
  - Free plan bisa dipakai untuk fase awal monitoring endpoint publik.
- Tambahan internal:
  - monitoring CPU/RAM/disk + log error (Sentry opsional).

---

## 10) Ringkasan Biaya (Kategori)

- Wajib beli dari awal:
  - Domain.
  - VPS/server.
- Bisa gratis di awal:
  - DNS/CDN dasar Cloudflare Free.
  - Monitoring dasar (UptimeRobot Free, sesuai ketentuan penggunaan).
- Conditional berbayar saat fitur aktif:
  - Email provider (jika butuh verifikasi/reset real user).
  - Payment setup operasional (tergantung skema bisnis).
