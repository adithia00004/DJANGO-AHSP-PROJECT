# Skrip UAT Browser — Fase R4 (L7)

**Tanggal dibuat:** 2026-06-10 13:05 WITA
**Basis:** `IMPLEMENTATION_PLAN_RC_20260610.md` R4 + `AUDIT_UI_UX_20260610.md` §7/§9.2 + tabel per-halaman audit launch.
**Lingkungan:** stack Docker lokal `http://localhost:8000` (R2/VPS belum tersedia — UAT diulang ringkas di staging saat R2).
**Cara pakai:** kerjakan berurutan, centang `[ ]`, catat temuan di kolom bawah tiap seksi. Hasil akhir → Record Eksekusi SSOT.

## 0. Persiapan (sekali)

- [ ] Stack sehat: `docker compose ps` semua healthy; buka `http://localhost:8000` → login page tanpa error.
- [ ] Frontend dist segar: `npm run build` sudah dijalankan pada HEAD terbaru.
- [ ] Siapkan 4 akun uji (via Django admin atau shell):
  | Akun | Setup | Untuk skenario |
  |---|---|---|
  | `uat_trial` | `subscription_status=TRIAL`, `trial_end_date=+7 hari` | gating export terkunci, batas trial |
  | `uat_expired` | `subscription_status=EXPIRED` | read-only + renewal F9 |
  | `uat_pro` | `subscription_status=PRO`, `subscription_end_date=+30 hari` | jalur penuh |
  | `uat_staff` | `is_staff=True` | menu admin (U14), portal referensi |
- [ ] `uat_pro` punya 1 project uji berisi beberapa pekerjaan ref + custom (boleh duplicate dari project nyata via dashboard → Duplicate).

## 1. Volume Pekerjaan (prioritas #1 — JS terbesar + formula opaque)

Login `uat_pro` → buka project uji → Volume Pekerjaan.
- [ ] Halaman render tanpa flash kosong (SSR-bootstrap); console browser bersih dari error.
- [ ] Tambah parameter via sidebar → ID `bp_N` muncul; pakai di formula volume → hasil terhitung.
- [ ] Tambah computed param (`cp_N`) yang mereferensi `bp_N` → evaluasi benar.
- [ ] **M4 modal bertumpuk**: buka Formula Editor → ubah sesuatu → tutup tanpa simpan → confirm muncul DI ATAS editor; tutup keduanya → tidak ada backdrop nyangkut, halaman bisa scroll.
- [ ] Simpan (dirty-guard → save) → sync LED hijau; reload → data persisten.
- [ ] Export dropdown: keempat tombol tampil normal (pro) → unduh XLSX & PDF → file terbuka benar.
- [ ] Autocomplete param dekat tepi bawah viewport → dropdown tidak terpotong.

## 2. Jadwal Pekerjaan (grid + Gantt + Kurva-S)

- [ ] Grid render; assign progress mingguan ke ≥2 pekerjaan → simpan → reload persisten.
- [ ] Tab Gantt: bar sesuai assignment; tooltip canvas muncul; tidak menembus toolbar.
- [ ] Tab Kurva-S: kurva planned/actual render; legend terlihat.
- [ ] **M5-jadwal fullscreen**: masuk fullscreen → topbar/sidebar tidak menembus; keluar normal.
- [ ] Export modal → progress modal → file jadi (XLSX + PDF professional).

## 3. List Pekerjaan + Template Library

- [ ] Drag-drop reorder klasifikasi/pekerjaan → simpan upsert → urutan persisten.
- [ ] Picker AHSP (select2): buka dekat topbar dan scroll saat terbuka → **M3**: dropdown tidak terpotong (bila terpotong = U3, catat — fix `dropdownParent` sudah direncanakan R6).
- [ ] **M1 toast vs modal**: buka Template Library → import template → **toast sukses/gagal HARUS terlihat di atas modal** (fix sudah masuk; ini verifikasi visualnya).
- [ ] Simpan list sebagai template baru → muncul di library.

## 4. Template AHSP, Harga Items, Rincian AHSP, Rekap RAB & Kebutuhan

- [ ] Template AHSP: ubah koefisien → save → orphan auto-cleanup tidak menghapus item terpakai; **M6 catat**: dialog konfirmasi masih native `confirm()` (known U11, migrasi R6) — fungsional harus tetap benar.
- [ ] Harga Items: isi harga beberapa item → save → Rekap RAB menghitung total.
- [ ] Rincian AHSP: override kode/uraian via modal → tersimpan; subtotal A-G benar.
- [ ] Rekap Kebutuhan: chart echarts render; filter + timeline + export berfungsi.
- [ ] Print preview Rekap RAB (Ctrl+P) → stylesheet print rapi.
- [ ] `/detail_project/<id>/rincian-rab/` (ketik manual) → **redirect ke Rincian AHSP** (U15 ✓).

## 5. Skenario per-role (gating)

**`uat_trial`:**
- [ ] **M7**: dropdown Export di Rekap RAB/Harga/Volume/Rincian → item PDF/Excel/Word tampil **terkunci** (gembok + badge Pro) → klik → mendarat di `/pricing/`.
- [ ] CSV/JSON tetap bisa diunduh.
- [ ] Menu sidebar TIDAK menampilkan Orphan Cleanup & Audit Trail (**M8/U14**); akses URL langsung → redirect + pesan.

**`uat_expired`:**
- [ ] Write diblokir: edit volume → save → pesan langganan berakhir (bukan crash).
- [ ] **F9 (kritis)**: buka Pricing → pilih plan → checkout → **POST payment/create TIDAK diblokir** → Snap popup Midtrans sandbox muncul (**M10**: popup di atas semua elemen).
- [ ] Selesaikan pembayaran sandbox (kartu test Midtrans) → webhook → status jadi PRO → write terbuka kembali.

**`uat_staff`:**
- [ ] Sidebar menampilkan Orphan Cleanup & Audit Trail; keduanya terbuka.
- [ ] Portal referensi terbuka; **F10**: export single/multiple dari Database AHSP berfungsi.
- [ ] Login `uat_trial` → akses URL export referensi langsung → redirect `/` + pesan (F10 ✓).

## 6. Referensi: import 3-tier (akun staff/superuser)

- [ ] Upload file AHSP 2026 nyata → validate report → tidak ada false "Kolom Bergeser" (Bug C fixed).
- [ ] **M2 toast vs modal**: di Database AHSP v2, bulk delete → notifikasi hasil TERLIHAT (fix sudah masuk; verifikasi visual).
- [ ] Staging → commit → data masuk; suffix code (`.a`) nama tidak menjadi kode (Bug A fixed).
- [ ] Import full-backup project JSON → **nilai proyek TIDAK nol** (fix `38046135`).

## 7. Lintas tema & ketahanan

- [ ] **M5 dark mode**: toggle gelap → telusuri SEMUA halaman referensi & dashboard → catat panel yang rusak (known U10, perbaikan menyusul; yang penting terdata).
- [ ] Mobile/responsive: sidebar offcanvas di layar sempit; toolbar responsive.
- [ ] **M11**: DevTools → block `cdn.jsdelivr.net` + `cdnjs.cloudflare.com` → reload → layout hancur (EXPECTED, keputusan sadar U7; self-host di R6).
- [ ] **M12**: disable JS → halaman login tetap terlihat (noscript fix ✓).

## 8. Opaque ID Gate D (paralel UAT)

- [ ] Selama UAT di atas, semua operasi parameter/formula tanpa error 4xx/5xx tak terduga (cek Network tab).
- [ ] Jalankan `bash scripts/opaque_daily_monitor.sh` → nol anomali; ulangi harian selama 7 hari window.
- [ ] Setelah window bersih → tulis sign-off Gate D di SSOT.

## Hasil

| Seksi | Status | Temuan |
|---|---|---|
| 1 Volume | [ ] | |
| 2 Jadwal | [ ] | |
| 3 List+Template | [ ] | |
| 4 Halaman laporan | [ ] | |
| 5 Per-role/gating | [ ] | |
| 6 Import referensi | [ ] | |
| 7 Tema/ketahanan | [ ] | |
| 8 Opaque Gate D | [ ] | |

**Sign-off UAT:** nama: ____ · tanggal: ____ · keputusan: LULUS / LULUS bersyarat / GAGAL
