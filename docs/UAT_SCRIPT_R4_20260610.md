# Skrip UAT Browser — Fase R4 (L7) — Pola Client-Side Workflow

**Dibuat:** 2026-06-10 13:05 WITA · **Revisi v2:** 2026-06-10 15:47 WITA — disusun ulang mengikuti **alur perjalanan pengguna nyata** (journey), setiap langkah = *Aksi → Output yang diharapkan*. Penanda `[M*/F*/U*]` = jejak temuan audit yang diverifikasi langkah itu.
**Lingkungan:** stack Docker lokal `http://localhost:8000` (UAT diulang ringkas di staging saat R2).
**Cara pakai:** kerjakan journey berurutan (A→G). Centang bila output SESUAI harapan; bila TIDAK, catat di tabel Hasil (journey, langkah, apa yang terjadi, error console/network bila ada) lalu laporkan.

**Peta cakupan app ↔ journey** (revisi 16:05 — celah dashboard/accounts/referensi ditambal):
| App | Journey/langkah |
|---|---|
| pages | A1-A2 (landing, pricing) |
| accounts (allauth) | A3-A7 (signup, verifikasi, login, rate-limit, reset password) |
| dashboard | B1.1-B1.7 (CRUD, upload Excel, bulk ops, export), B8.4-B8.5 (backup/duplicate) |
| detail_project (12 halaman) | B2-B7 + B6.4 (rincian-rab redirect) + D4-D5 & E10 (orphan/audit per-role) + E11 (export-test) |
| referensi | E1-E12 (portal, database v2, pricing mgmt, import tier-1/2/3, audit, export) + D6 (gate F10) |
| subscriptions | A2 (pricing), C1-C7 (checkout→Snap→webhook→renewal) |
| Lintas app | D (gating), F (tema/responsif/ketahanan), G (Opaque Gate D) |

## 0. Persiapan (status saat revisi)

- [x] Stack sehat (13:20): semua container healthy; `/health/` 200; `/accounts/login/` 200.
- [x] Frontend dist segar (`npm run build` @ HEAD `452401ae`).
- [x] 4 akun uji siap — password sementara `UatAhsp2026!` (ganti/hapus `uat_*` setelah UAT):
  `uat_trial` (TRIAL 7 hari) · `uat_expired` (EXPIRED) · `uat_pro` (PRO 30 hari) · `uat_staff` (staff)
- [ ] **Untuk Journey C (pembayaran):** isi `MIDTRANS_SERVER_KEY` + `MIDTRANS_CLIENT_KEY` sandbox di `.env` → `docker compose restart web`. Journey lain tidak bergantung ini.

---

## Journey A — Pengunjung Baru → Punya Akun
*Persona: calon pelanggan, belum login. Mode incognito.*

| # | Aksi | Output yang diharapkan |
|---|---|---|
| A1 | Buka `http://localhost:8000/` | Landing page render penuh (hero, fitur, navbar fixed-top); tanpa error console; <2 dtk |
| A2 | Klik menu **Pricing** | Halaman pricing menampilkan plan + harga **dari database** (3 plan), tombol CTA per plan |
| A3 | Klik daftar/CTA → isi form signup dengan email baru (mis. `uat_baru@uat.local`) | Form crispy tervalidasi; setelah submit → halaman "verifikasi terkirim" ATAU langsung login (dev: verifikasi `optional`) |
| A4 | (Dev) lihat log web container: `docker compose logs web --tail 20` | Email verifikasi tercetak di console backend (EMAIL_BACKEND console) |
| A5 | Login dengan akun baru | Redirect ke **Dashboard** (kosong, empty-state ramah — bukan error); banner trial muncul |
| A6 | Logout → login lagi salah password 6× cepat | Rate-limit allauth menahan (pesan wajar, **bukan** error 500 — regresi insiden Redis) |
| A7 | Halaman login → **Lupa password** → submit email akun A3 → ambil link reset dari log container → set password baru → login | Seluruh alur reset jalan (form → "email terkirim" → form password baru → sukses login) |

**Catatan A:** akun baru via signup berstatus TRIAL_PENDING sampai email dikonfirmasi (trial 14 hari aktif setelah konfirmasi — signal `email_confirmed`). Konfirmasi via link di log A4 → cek banner berubah.

---

## Journey B — Proyek Pertama: Input → Hasil
*Persona: `uat_pro` (jalur penuh tanpa gangguan gating). Ini journey inti produk — alur data: List Pekerjaan → Volume → Template AHSP → Harga → laporan.*

### B1. Buat proyek
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B1.1 | Login `uat_pro` → Dashboard → **+ Tambah Project** (modal) | Modal `addProjectModal` terbuka rapi; form lengkap |
| B1.2 | Isi nama/tahun/lokasi/anggaran → simpan | Toast sukses (kanan-atas); project muncul di tabel dashboard dengan statistik 0 |
| B1.3 | Klik project → halaman Project Detail → tombol masuk detail | Sidebar global muncul: seksi **Input Data / Analisis & Laporan / Perencanaan**; **TANPA** Orphan Cleanup & Audit Trail (bukan staff) [U14] |
| B1.4 | Kembali ke Dashboard → **Edit** project (ubah nama/anggaran) → simpan | Perubahan tersimpan; tabel & statistik ter-update |
| B1.5 | Dashboard → **Upload Excel** (mass create) dengan file template berisi 2-3 project | Project baru muncul; baris invalid ditolak dengan pesan jelas per baris |
| B1.6 | Centang beberapa project uji → **Bulk Archive** → lalu **Unarchive**; satu project uji → **Bulk Delete** (konfirmasi `dpConfirmModal`) | Status berubah benar; delete butuh konfirmasi; project nyata TIDAK tersentuh (hanya data uji!) |
| B1.7 | Dashboard → **Export Excel** dan **Export CSV** (level dashboard) + Project Detail → **Export PDF** | Ketiga file terunduh; isi sesuai filter aktif |

### B2. List Pekerjaan (susun struktur pekerjaan)
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B2.1 | Buka **List Pekerjaan** | Render tanpa flash kosong (SSR-bootstrap); console bersih |
| B2.2 | Tambah Klasifikasi + Sub + pekerjaan **custom** | Baris baru muncul di tree dengan ordering benar |
| B2.3 | Tambah pekerjaan **dari referensi**: buka picker AHSP (select2), ketik kata kunci | Dropdown muncul utuh (tidak terpotong topbar saat dekat tepi [M3/U3]); hasil menampilkan kode+uraian |
| B2.4 | Pilih 2-3 AHSP ref → drag-drop ubah urutan → **Simpan** | Toast sukses; reload → struktur & urutan persisten; sync LED hijau |
| B2.5 | Tombol **Template Library** → simpan list sebagai template → buka library → import template ke project | Modal library terbuka; **toast sukses import TERLIHAT DI ATAS modal** [M1/U1 — verifikasi visual fix]; item template masuk list |

### B3. Volume Pekerjaan (parameter + formula)
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B3.1 | Buka **Volume Pekerjaan** | Tabel pekerjaan dari B2 muncul; tanpa flash; console bersih |
| B3.2 | Sidebar parameter → tambah parameter (mis. `panjang=10`) | Chip parameter muncul dengan ID server `bp_N` (bukan slug nama) |
| B3.3 | Tambah **computed param** (mis. `cp = bp_1 * 2`) di tab computed | Nilai terevaluasi benar; ID `cp_N` |
| B3.4 | Isi volume satu pekerjaan via **formula** (`bp_1 * cp_1`) pakai autocomplete | Suggest list muncul (tidak terpotong di tepi bawah); preview hasil benar |
| B3.5 | Buka **Formula Editor** (modal) → edit → klik tutup TANPA simpan | Confirm dialog muncul **DI ATAS** editor; pilih batal → kembali ke editor; tutup semua → **tanpa backdrop nyangkut**, halaman bisa scroll [M4/U4] |
| B3.6 | **Simpan** → reload halaman | Nilai & formula persisten; volume non-formula manual juga tersimpan |

### B4. Template AHSP (rincian koefisien per pekerjaan)
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B4.1 | Buka **Template AHSP** → pilih pekerjaan ref dari B2 | Komponen TK/BHN/ALT ter-load dari referensi (snapshot) |
| B4.2 | Ubah koefisien satu komponen → tambah 1 komponen baru → **Simpan** | Konfirmasi tampil (catat: masih `confirm()` native — known U11, fungsional tetap benar); toast sukses; status pekerjaan jadi `ref_modified` |
| B4.3 | Tombol **Reset to Ref** pada pekerjaan tadi | Konfirmasi → komponen kembali persis seperti referensi |

### B5. Harga Items
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B5.1 | Buka **Harga Items** | Daftar item gabungan dari semua detail AHSP project (SSOT item); tanpa duplikat |
| B5.2 | Isi harga beberapa item (TK/BHN/ALT) → **Simpan** | Toast sukses; reload persisten; item yang tidak terpakai TIDAK muncul (orphan auto-cleanup) |

### B6. Laporan (hasil hitung)
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B6.1 | Buka **Rekap RAB** | Total per pekerjaan = volume × harga satuan; grand total konsisten dengan input B3+B5; pricing/margin bisa diubah dan tersimpan |
| B6.2 | Buka **Rincian AHSP** | Penjabaran A-G per pekerjaan; subtotal & harga satuan = yang dipakai Rekap RAB; override kode/uraian via modal bekerja |
| B6.3 | Buka **Rekap Kebutuhan** | Agregat kebutuhan TK/BHN/ALT (qty = Σ koefisien×volume); chart echarts render; filter & validasi jalan |
| B6.4 | Ketik manual URL `/detail_project/<id>/rincian-rab/` | **Redirect ke Rincian AHSP** [U15 ✓] |
| B6.5 | Di Rekap RAB → Ctrl+P (print preview) | Stylesheet print rapi (tabel tidak terpotong aneh) |

### B7. Jadwal Pekerjaan
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B7.1 | Buka **Jadwal Pekerjaan** | Grid Excel-like render; daftar pekerjaan = B2 |
| B7.2 | Assign progress mingguan ≥2 pekerjaan (total 100%) → **Simpan** | Validasi total; toast sukses; reload persisten |
| B7.3 | Tab **Gantt** | Bar sesuai minggu ter-assign; tooltip muncul mengikuti kursor |
| B7.4 | Tab **Kurva-S** | Kurva planned (dan actual bila ada) render; legend terlihat; angka kumulatif = bobot harga |
| B7.5 | Mode **fullscreen** → keluar | Grid memenuhi layar, topbar tidak menembus [U5]; keluar kembali normal |

### B8. Export (persona PRO — semua terbuka)
| # | Aksi | Output yang diharapkan |
|---|---|---|
| B8.1 | Di Rekap RAB → dropdown **Export** | 4 item tampil **normal semua** (tanpa gembok) [M7 sisi PRO] |
| B8.2 | Unduh **XLSX** dan **PDF** | File terunduh, terbuka benar, isi = data layar |
| B8.3 | Jadwal → Export → professional report | Progress modal muncul → file jadi |
| B8.4 | Dashboard → project → **Export full backup JSON**; lalu **import** JSON itu sebagai project baru | Import sukses; project hasil import punya **nilai RAB ≠ 0** [regresi fix `38046135`] |
| B8.5 | Dashboard → **Duplicate** project | Salinan lengkap (struktur, volume+formula, harga); parameter di-remap ID opaque baru (Opsi B) |

---

## Journey C — Upgrade & Pembayaran (Midtrans sandbox)
*Persona: `uat_expired` — persis user yang HARUS bisa membayar [F9].*

| # | Aksi | Output yang diharapkan |
|---|---|---|
| C1 | Login `uat_expired` → buka project (boleh buat dulu saat masih punya akses, atau pakai project lama) | Halaman terbuka **read-only**: data terlihat |
| C2 | Coba edit volume → Simpan | Ditolak halus: pesan "langganan berakhir" / redirect pricing — **bukan crash/500** |
| C3 | Buka **Pricing** → pilih plan → **Checkout** | Halaman checkout: ringkasan plan + harga server-side |
| C4 | Klik **Bayar** | **POST `payment/create` TIDAK diblokir middleware** [F9 ✓ — verifikasi browser]; **Snap popup Midtrans muncul di atas semua elemen** [M10/U13] |
| C5 | Bayar dengan kartu test sandbox (`4811 1111 1111 1114`, CVV 123, OTP 112233) | Popup sukses → redirect `payment/finish` → status transaksi tampil |
| C6 | Tunggu webhook (sandbox dashboard → kirim notifikasi bila perlu) → refresh dashboard | Status akun jadi **PRO**; banner upgrade hilang |
| C7 | Ulangi C2 (edit volume → simpan) | **Write terbuka kembali** — siklus renewal lengkap |

---

## Journey D — Gating Trial (nilai konversi)
*Persona: `uat_trial`.*

| # | Aksi | Output yang diharapkan |
|---|---|---|
| D1 | Login `uat_trial` → buat/buka project → input data ringan (list+volume) | Write BOLEH (trial aktif) |
| D2 | Rekap RAB → dropdown **Export** | PDF/Excel/Word tampil **TERKUNCI**: ikon gembok + badge **Pro** [M7 ✓]; CSV/JSON tetap normal |
| D3 | Klik item terkunci | Mendarat di `/pricing/?reason=export_locked` (bukan error 403 mendadak) |
| D4 | Periksa sidebar project | **TIDAK ada** Orphan Cleanup & Audit Trail [M8/U14 ✓] |
| D5 | Ketik manual URL `/detail_project/<id>/orphan-cleanup/` | Redirect ke List Pekerjaan + pesan "hanya admin" [U14 ✓] |
| D6 | Buka URL export referensi langsung: `/referensi/export/search/excel/?q=beton` | Redirect `/` + pesan akses portal [F10 ✓] |

---

## Journey E — Admin/Staff: Referensi & Operasional
*Persona: `uat_staff` (atau superuser Anda untuk import).*

| # | Aksi | Output yang diharapkan |
|---|---|---|
| E1 | Login `uat_staff` → buka `http://localhost:8000/` | Redirect ke **Admin Portal** referensi (root redirect role-aware) |
| E2 | Buka **Database AHSP v2** | Tabel jobs/items ter-load; search & filter jalan |
| E3 | Edit satu item via `edit-modal` → simpan | **Toast hasil TERLIHAT** (tidak tertutup modal) [M2/U2 ✓]; data berubah |
| E4 | Pilih beberapa → **Bulk Delete** → modal konfirmasi → eksekusi | Modal di atas konten, hasil tampil; data terhapus (pakai data uji!) |
| E5 | **Export** single & multiple dari database | File terunduh [F10 — staff boleh] |
| E6 | **Pricing Management** → ubah harga plan/promo | Tersimpan; cek halaman Pricing publik ikut berubah |
| E7 | **Import Tier-1**: upload PDF AHSP → konversi → unduh hasil Excel (per-part bila besar) | Konversi selesai; progress bar jalan; file Excel valid untuk tier-2 |
| E8 | **Import Tier-2/3** dengan file Excel AHSP nyata: upload → validate report | Report tanpa false "Kolom Bergeser" [Bug C fixed]; WYSIWYG repair bisa edit |
| E9 | Staging → commit | Data masuk; AHSP suffix `.a` namanya BUKAN kodenya [Bug A fixed] |
| E10 | Buka project (staff punya akses penuh) → sidebar | Orphan Cleanup & Audit Trail **MUNCUL** [U14 staff-side ✓]; keduanya terbuka dan berfungsi |
| E11 | Ketik URL `/detail_project/<id>/export-test/` (staff) lalu coba juga dengan `uat_trial` | Staff: halaman uji export terbuka; trial: redirect + pesan admin [F14 ✓] |
| E12 | Audit dashboard referensi | Log import tampil; statistik render; mark-resolved bekerja |

---

## Journey F — Tema, Responsif, Ketahanan
*Persona: bebas (pakai `uat_pro`).*

| # | Aksi | Output yang diharapkan |
|---|---|---|
| F1 | Toggle **dark mode** → telusuri SEMUA halaman detail_project | Konsisten gelap; teks terbaca |
| F2 | Masih gelap → telusuri referensi (database, import) & dashboard | **Catat area putih/kontras rusak** [U10 — known, tujuan: inventaris untuk R6] |
| F3 | Kecilkan jendela ke lebar ponsel | Sidebar jadi offcanvas + backdrop; toolbar responsive; tabel bisa di-scroll |
| F4 | DevTools → Network → block `cdn.jsdelivr.net` & `cdnjs.cloudflare.com` → reload | Layout hancur = **EXPECTED** [U7, keputusan sadar; self-host di R6] — catat saja |
| F5 | Settings browser → disable JavaScript → buka halaman login | Halaman **tetap terlihat** (tidak blank) [M12/U8 ✓] |
| F6 | Console browser di tiap halaman Journey B | Tidak ada error merah (warning boleh dicatat) |

---

## Journey G — Opaque ID Gate D (berjalan paralel)

| # | Aksi | Output yang diharapkan |
|---|---|---|
| G1 | Selama Journey B, pantau tab Network saat operasi parameter/formula | Semua 2xx; tidak ada 409/500 tak terduga |
| G2 | `bash scripts/opaque_daily_monitor.sh` (hari ini, lalu harian ×7) | Nol anomali per run |
| G3 | Setelah window 7 hari bersih | Tulis sign-off Gate D di SSOT |

---

## Hasil

| Journey | Status | Temuan (langkah → apa yang terjadi) |
|---|---|---|
| A Pengunjung→Akun | [ ] | |
| B Proyek: input→hasil | [ ] | |
| C Upgrade & bayar | [ ] | |
| D Gating trial | [ ] | |
| E Admin/referensi | [ ] | |
| F Tema/ketahanan | [ ] | |
| G Opaque Gate D | [ ] | |

**Sign-off UAT:** nama: ____ · tanggal: ____ · keputusan: LULUS / LULUS bersyarat / GAGAL
