# Rencana Induk Pra-Launching

**Dibuat:** 2026-08-11 · **Status:** aktif · **Pemilik keputusan:** owner

Parameter yang menentukan bentuk rencana ini (ditegaskan owner 2026-08-11):

| Parameter | Nilai | Akibatnya pada rencana |
|---|---|---|
| Tenggat | Tidak ada tanggal tetap, kualitas dulu | Boleh menutup akar masalah, bukan menambal. Tapi butuh gate eksplisit agar tidak molor tanpa ujung |
| Skala awal | Puluhan user, soft launch terbatas | Kerja kapasitas **turun drastis**. 4 worker cukup. Fokus geser ke data, uang, dan observabilitas |
| Pembayaran | **Belum didaftarkan karena belum ada server** | Server jadi jalur kritis; pendaftaran merchant terkunci di belakangnya |
| Model | SaaS multi-tenant, 1 project = 1 user | Tak ada kerja concurrent-editing. Isolasi antar-tenant tetap wajib |

---

## Prinsip audit: buktikan berjalan, jangan percaya terkonfigurasi

Sesi 2026-08-11 menemukan **empat** komponen yang tampak terpasang rapi tapi sebenarnya mati. Semuanya lolos dari empat putaran audit sebelumnya karena audit itu membaca kode, bukan mengukur sistem berjalan.

| Komponen | Terlihat | Kenyataan | Status |
|---|---|---|---|
| `TimeoutMiddleware` | Timeout 180 dtk | Gunicorn membunuh di 120 dtk — cabangnya tak pernah tercapai | ✅ dihapus `53edafe7` |
| `celery_beat` | Penjadwal aktif | Crash 1212× — tugas terjadwal tak pernah jalan sekali pun | ✅ diperbaiki |
| `STATICFILES_STORAGE` | Kompresi + hash | Setting dihapus Django 5.1; proyek di 5.2 → inert | ⬜ terbuka |
| `init_sentry()` | Error tracking | Fungsi ada, tak pernah dipanggil → `capture_exception` no-op | ⬜ terbuka |

**Aturan untuk seluruh fase di bawah:** tidak ada item yang boleh ditandai selesai berdasarkan "konfigurasinya sudah benar". Setiap item punya kolom bukti yang harus diisi hasil pengukuran atau percobaan nyata.

---

## Yang SUDAH selesai — jangan diaudit ulang

Audit lapisan aplikasi sebagian besar tuntas. Ini penting supaya cakupan pra-launching tidak membengkak tanpa perlu.

| Area | Cakupan | Status |
|---|---|---|
| R2 `accounts` | Auth, allauth, verifikasi email, middleware | ✅ Tuntas, residual ops ditutup `cbcd4383` |
| R3 `subscriptions` | A1–A17, entitlement, normalisasi status | ✅ Semua fixed & terverifikasi |
| R5 `detail_project` | 8 halaman, page-scope penuh | ✅ Tuntas |
| R6 `referensi` | Read-only, validasi impor, kontrol akses | ✅ Praktis tuntas |
| Kebocoran koneksi DB | Penghambat multi-user keras | ✅ `53edafe7`, terverifikasi 120 request datar di 4 |
| Gate test | Polusi counter limiter antar-test | ✅ `20764342` |

**Sisa yang belum pernah diaudit: lapisan operasional dan launching.** Itulah isi rencana ini.

---

## Fase 0 — Fondasi produksi (jalur kritis)

Belum ada server. Semua hal di bawah ini terkunci di sini, termasuk pendaftaran Midtrans.

| # | Item | Kenapa penting | Bukti yang harus ada |
|---|---|---|---|
| 0.1 | Sediakan server | Untuk puluhan user, 2–4 vCPU / 4–8 GB sudah lapang. Jangan beli lebih dulu | Stack jalan, `docker compose ps` semua healthy |
| 0.2 | Domain + DNS | Midtrans dan email butuh domain nyata | `dig` menunjuk ke server |
| 0.3 | Deploy pertama via `deploy/docker-compose.prod.proxy.yml` | Caddy sudah siap menerbitkan TLS otomatis | Sertifikat terbit, HTTPS hijau |
| 0.4 | Verifikasi startup guard produksi | `production.py` sudah punya guard yang menolak konfigurasi buruk — buktikan ia benar-benar menolak | Coba jalankan dengan SECRET_KEY placeholder, harus gagal start |
| 0.5 | Email nyata (SMTP + SPF/DKIM) | allauth mewajibkan verifikasi email di produksi. Email tak sampai = **tak ada satu pun user bisa mendaftar** | Signup dari alamat luar, email masuk inbox bukan spam |

**Gate Fase 0:** dari perangkat lain di jaringan luar, buka domain lewat HTTPS, daftar akun baru, terima email verifikasi, dan berhasil masuk.

---

## Fase 1 — Keselamatan data & observabilitas

Bisa dikerjakan paralel dengan Fase 0 sebagian. Ini yang kerusakannya paling sulit dipulihkan.

| # | Item | Kenapa penting | Bukti yang harus ada |
|---|---|---|---|
| 1.1 | Backup otomatis terjadwal | Backup terakhir sebelum 2026-08-11 berasal dari **Januari dan Februari**. `celery_beat` kini hidup dan menganggur — bisa langsung dipakai | Dump harian berjalan 3 hari berturut-turut |
| 1.2 | **Uji restore**, bukan sekadar dump | Backup yang tak pernah dipulihkan bukan backup | Restore ke database kosong, hitung baris cocok |
| 1.3 | Hidupkan Sentry | `init_sentry()` tak pernah dipanggil → buta total saat produksi | Lempar error sengaja, muncul di dashboard Sentry |
| 1.4 | Perbaiki `STATICFILES_STORAGE` → `STORAGES` | Tanpa hash, tak ada cache jangka panjang; aset 1,7 MB diunduh ulang terus | `collectstatic` menghasilkan nama ber-hash + `.gz`/`.br` |
| 1.5 | Memory limit container (RT-04) | Di SaaS, satu request boros bisa meng-OOM host dan menjatuhkan **seluruh tenant** | `docker stats` menunjukkan limit terpasang |
| 1.6 | Uptime check eksternal | Anda tidak boleh jadi orang terakhir yang tahu situs mati | Matikan paksa web, alert masuk |

**Gate Fase 1:** matikan paksa satu container. Anda harus tahu dari alert, bukan dari mata sendiri. Lalu pulihkan database dari backup ke instance kosong dan buktikan datanya utuh.

---

## Fase 2 — Keamanan pra-publik

Kontrol akses sudah diaudit di R2–R6. Fase ini soal higienis produksi, bukan mengulang audit itu.

| # | Item | Kenapa penting | Bukti yang harus ada |
|---|---|---|---|
| 2.1 | Rotasi **semua** secret | `DJANGO_SECRET_KEY`, password DB, password Redis. Nilai dev sudah pernah terpapar di log terminal | Secret produksi berbeda total dari dev, tidak ada di git |
| 2.2 | CSP report-only → enforce | Saat ini hanya melapor. Sudah lama disiapkan (WP-A2) | Header `Content-Security-Policy` aktif, tak ada pelanggaran di konsol |
| 2.3 | Mode rate limiter produksi | Default `v2` (enforcing) sudah benar. Kalibrasi ambang setelah melihat trafik nyata | Metrik `blocked`/`would_block` dipantau seminggu |
| 2.4 | Client-IP trust repo-wide (N-6) | Sudah di backlog cross-cutting Anda. Jangan tambal satu titik — pelajaran UF-013/AT-01 | Helper tunggal dipakai semua pemanggil |
| 2.5 | Uji isolasi antar-tenant di server nyata | Sudah diaudit, tapi belum pernah diuji di lingkungan produksi | User B mencoba akses data user A lewat URL langsung → 404 |

**Gate Fase 2:** satu putaran percobaan sebagai penyerang ringan — user B menebak ID project user A di setiap halaman dan endpoint API.

---

## Fase 3 — Pembayaran (terkunci Fase 0)

Midtrans sudah terpasang lengkap di kode (`subscriptions/midtrans.py`, sandbox/produksi via `MIDTRANS_IS_PRODUCTION`). Yang belum ada adalah sisi bisnisnya.

| # | Item | Catatan |
|---|---|---|
| 3.1 | Daftar merchant Midtrans | Butuh domain live dari Fase 0 |
| 3.2 | Kredensial produksi + verifikasi merchant | Proses eksternal, bisa makan waktu — mulai sedini mungkin setelah 0.2 |
| 3.3 | Uji transaksi nyata nominal kecil | Sandbox tidak membuktikan jalur produksi |
| 3.4 | Verifikasi webhook + rekonsiliasi status langganan | Titik paling rawan: pembayaran sukses tapi status tidak naik |
| 3.5 | Skenario gagal | Bayar gagal, kedaluwarsa, dobel-bayar, refund |

**Gate Fase 3:** satu siklus penuh terbukti — trial → bayar → aktif → kedaluwarsa → akses ditutup.

---

## Fase 4 — Kualitas & performa

**Diturunkan prioritasnya** karena skala puluhan user. Dikerjakan karena benar, bukan karena mendesak.

| # | Item | Status |
|---|---|---|
| 4.1 | Empat test merah yang nyata | 2 anggaran query (30>15, 16>12), 1 format (`'60' != '60.00'`), 1 fungsi JS hilang |
| 4.2 | WIP diselesaikan **atau diparkir sadar** | WP Export Jadwal 2C/2D, limiter v2. Jangan biarkan menggantung saat launching |
| 4.3 | N+1 pada dua jalur di atas | Jadi jauh lebih penting kalau database dipindah ke jaringan |
| 4.4 | Aset besar — hanya perbaikan murah | echarts 1 MB, bundle jadwal 1,1 MB, `volume_pekerjaan.js` 309 KB tanpa minifikasi |

**Ditunda sadar** (aman pada puluhan user, tinjau ulang kalau tumbuh): sizing worker gunicorn, pemisahan penyajian static dari gunicorn, uji beban konkurensi sungguhan, self-hosting 7 dependensi CDN.

---

## Fase 5 — Go / No-Go

| # | Item |
|---|---|
| 5.1 | Runbook deploy + **rollback yang sudah pernah dicoba** |
| 5.2 | Checklist Go/No-Go diisi dengan bukti tiap gate di atas |
| 5.3 | Soft launch ke lingkaran terbatas, pantau ketat 1–2 minggu |
| 5.4 | Baru buka pendaftaran umum |

---

## Urutan pengerjaan yang disarankan

```
Fase 0 (server, domain, deploy, email)  ──┬──> Fase 3 (pembayaran)
                                          │
Fase 1 (backup, Sentry, static, limit) ───┤
                                          ├──> Fase 5 (Go/No-Go)
Fase 2 (secret, CSP, isolasi tenant) ─────┤
                                          │
Fase 4 (test merah, WIP, N+1) ────────────┘
```

Fase 1 dan 4 bisa dimulai **sekarang** tanpa menunggu server. Fase 3 sepenuhnya terkunci di Fase 0.

## Catatan kejujuran

Rencana ini disusun dari bukti terukur sesi 2026-08-11 dan riwayat audit R2–R6. Bagian yang **belum terukur** dan sengaja tidak saya klaim: waktu respons per halaman, jumlah query per halaman di project besar, query termahal, dan perilaku di bawah beban bersamaan. Semua itu butuh Docker berjalan, dan hasilnya bisa memindahkan item Fase 4 naik atau turun.
