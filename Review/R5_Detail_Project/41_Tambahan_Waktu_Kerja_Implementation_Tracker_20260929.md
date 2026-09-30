# 41 — Tracker Eksekusi: Tambahan Waktu Kerja

| | |
|---|---|
| Status keseluruhan | **TAHAP 1 REVIEW** — laporan blocker sudah diperbaiki; suite penuh 2026-09-30: **944 tes, 0 gagal** (3 kegagalan baseline lama sudah diperbaiki: kebocoran Silk ke setelan tes + tes sumber usang). D-11 diputuskan & diimplementasikan (2026-09-30). UAT otomatis 16/16 skenario lulus; tersisa cek visual owner (U-1, U-2, U-5 Kurva S, U-6 pesan, U-16). Lihat §4, §6, dan §9 |
| Tanggal dibuat | 2026-09-29 |
| Rencana implementasi | [`40_Tambahan_Waktu_Kerja_Implementation_Plan_20260929.md`](40_Tambahan_Waktu_Kerja_Implementation_Plan_20260929.md) |
| Rancangan | [`docs/RENCANA_JADWAL_MELEWATI_AKHIR_KONTRAK.md`](../../docs/RENCANA_JADWAL_MELEWATI_AKHIR_KONTRAK.md) v9 |
| Audit backend | [`docs/REVIEW_BACKEND_JADWAL_KETERLAMBATAN_20260929.md`](../../docs/REVIEW_BACKEND_JADWAL_KETERLAMBATAN_20260929.md) |
| Branch | `feat/tambahan-waktu-kerja` (dibuat di G0-3) |

Dokumen ini adalah **satu-satunya sumber status** pekerjaan Tambahan Waktu Kerja.
Rancangan dan doc 40 hanya diubah lewat §7 (log keputusan & perubahan scope).

---

## 1. Aturan tracking

Diperbarui ketika: langkah dimulai/selesai/diblokir, gate gagal, ditemukan kondisi
di luar audit, keputusan owner berubah, atau baseline menghasilkan kegagalan baru.

| Status | Arti |
|---|---|
| `TODO` | Belum dimulai |
| `WIP` | Sedang dikerjakan |
| `BLOCKED` | Tertahan; alasan wajib diisi |
| `REVIEW` | Kode & uji selesai, menunggu review/verifikasi owner |
| `DONE` | Kriteria selesai terpenuhi dan commit tercatat |
| `DEFER` | Ditunda dengan keputusan tercatat di §7 |

---

## 2. Gate 0 — Sebelum langkah pertama

| # | Isi | Keputusan / hasil | Status | Tanggal |
|---|---|---|---|---|
| G0-1 | Rapikan git: WIP owner (`dashboard/*`, `views_api.py`, `timeline_repair.js`, template Jadwal, `tests_list_pekerjaan_grow_tree.py`) dan tiga branch bertumpuk | **Owner:** WIP dibiarkan di working tree tanpa disentuh; branch kerja dibuat dari HEAD saat itu (membawa tumpukan laporan & edit massal); commit langkah hanya memuat hunk miliknya. Merge tumpukan ke `main` diputuskan terpisah | DONE | 2026-09-29 |
| G0-2 | Commit dokumen: rancangan v9, audit backend, doc 40, doc 41 | Commit `fc023d93` | DONE | 2026-09-29 |
| G0-3 | Buat branch `feat/tambahan-waktu-kerja` | Dari `e0a4cb71` (`feat/edit-massal-discoverability`) | DONE | 2026-09-29 |
| G0-4 | Rekam baseline (§3) | `detail_project` + `dashboard`: 842 tes, 3 kegagalan lama yang diketahui, 40 skipped, 6 expected failure dari tes 0.1; frontend: 396 lulus, 25 skipped | DONE | 2026-09-29 |
| G0-5 | Kebijakan duplikasi dengan tanggal mulai baru (W-1b) | **Owner: (a) pertahankan nomor minggu** — minggu ke-N tetap minggu ke-N, tanggal minggu dihitung ulang dari tanggal mulai baru; bila durasi baru lebih pendek, minggu yang tidak muat tidak disalin dan dilaporkan | DONE | 2026-09-29 |

**Aturan:** langkah 0.1 boleh dimulai setelah G0-1 s.d. G0-4 lulus. G0-5 harus
diputuskan sebelum langkah 0.3.

---

## 3. Baseline (diisi di G0-4, sebelum perubahan apa pun)

| Suite | Perintah | Hasil | Catatan |
|---|---|---|---|
| `detail_project` + `dashboard` penuh (serial) | Runner Django pada PostgreSQL, database uji terisolasi `test_twk_codex_20260929` | **842 total; 3 gagal, 40 skipped, 6 expected failure** | Tiga kegagalan sama dengan daftar baseline lama di bawah; enam expected failure adalah tes transfer 0.1 |
| Uji timeline terarah | 5 modul timeline/dashboard | **53 lulus** | PostgreSQL; dijalankan bersama tes awal 0.1 sebelum penambahan dua kasus tambahan |
| Uji transfer 0.1 (sebelum langkah 0.2) | `detail_project.tests_progress_transfer_roundtrip` | **12 total; 3 lulus, 9 expected failure** | PostgreSQL; expected failure menandai bug A–C yang belum dikerjakan |
| Uji frontend | `npm run test:frontend -- --reporter=dot` | **32 file lulus; 396 lulus, 25 skipped** | Satu tes sempat timeout pada proses awal, lulus saat diulang sendiri dan pada run penuh berikutnya |

Kegagalan lama yang diketahui (tidak boleh bertambah):
1. `tests_wp_b4_readiness.ReadinessContractTests.test_query_budget_constant_no_n_plus_1`
2. `tests_rekap_calculation_contract.RekapCalculationContractTests.test_shared_signature_has_bounded_query_count`
3. `tests_formula_ui_regressions.SaveSyncUiRegressionGuardsTests.test_template_does_not_auto_reload_pending_jobs_on_open`

---

## 4. Progres langkah

| Langkah | Isi | Status | Commit | Tanggal |
|---|---|---|---|---|
| 0.1 | Uji bolak-balik backup/restore/duplikasi | DONE | `e54679be` | 2026-09-29 |
| 0.2 | Restore memakai aturan minggu kanonik (bug B) | DONE | `7024dfec` | 2026-09-29 |
| 0.3 | Satu penyalin data progres (bug A, C) | DONE | `8a900ffb` | 2026-09-29 |
| 0.4 | Satu layanan tulis progres | DONE | `d004a9c1` | 2026-09-29 |
| 1.1 | Skema, helper, penyisiran, field target | DONE | `606e5668` | 2026-09-29 |
| 1.2 | Tambahan ikut backup/restore/duplikasi | DONE | `36623610` | 2026-09-29 |
| 1.3 | Aturan tulis rencana | DONE | `d615ce08` | 2026-09-29 |
| 1.4 | Perpanjang / pendekkan / hapus tambahan | DONE | `d64494ac` | 2026-09-29 |
| 1.5 | Ubah akhir waktu kerja (Dashboard) + pindahkan rencana | DONE | `33cd8aa7` | 2026-09-29 |
| 1.6 | Ubah hari batas minggu | DONE | `e1482ce6` | 2026-09-29 |
| 1.7 | Frontend (tombol, dialog, grid, Kurva S/Gantt, build) | REVIEW | `d87390af` + `6b506eed` | 2026-09-30 |
| UAT | Checklist §6 | TODO | | |

---

## 5. Catatan per langkah

Setiap langkah diisi dengan format berikut saat dikerjakan.

```
### Langkah X.Y — <judul> — <STATUS> <tanggal>

- Isi yang dikerjakan:
- File diubah:
- Uji baru / diubah:
- Hasil uji (perintah + angka):
- Commit:
- Temuan di luar rencana (→ §8):
- Catatan untuk langkah berikutnya:
```

### Langkah 1.1 — Penyisiran titik rentang (diisi saat 1.1)

| Titik (file:baris) | Acuan yang dipakai | Keputusan | Diuji oleh |
|---|---|---|---|
| `timeline_utils.project_report_period_counts` | Rentang pencatatan | Memakai `work_period_end`; period selector dapat melihat rentang tambahan | Helper 1.1; render export fase berikutnya |
| `timeline_utils._persisted_timeline` | Rentang pencatatan | Membaca akhir tambahan valid sebagai akhir grid efektif | Helper 1.1 |
| `timeline_utils.analyze/apply_project_timeline_change` | Rentang pencatatan + field target | `target_field` memisahkan akhir kontrak dari akhir tambahan; durasi Dashboard hanya dihitung untuk akhir kontrak | Tes API target 5 skenario |
| `progress_utils` pembentukan tahapan mingguan | Rentang pencatatan | Builder/reset memakai akhir masa waktu kerja | Tes regresi timeline 53 lulus |
| `views_api_tahapan_v2.py` batas `week_number` & timeline API | Rentang pencatatan | Save, preview, commit, dan regenerasi menggunakan rentang efektif; API menerima target tambahan/hapus | Tes target-field + API lama |
| `exports/jadwal_pekerjaan_adapter.py` | Rentang pencatatan | Ditunda: rendering/export masuk fase 9 sesuai keputusan owner | Fase export |
| `exports/export_manager.py` laporan harian | Rentang pencatatan | Ditunda: laporan/render masuk fase 9 sesuai keputusan owner | Fase export |
| `readiness.py` | Rentang pencatatan | Pemeriksaan baris di luar timeline memakai helper | Tes timeline |
| `views_api.py` statistik backup JSON | Rentang pencatatan | Jumlah minggu mengikuti akhir efektif; import sudah memakai penyalin kanonik 0.3 | Tes transfer |
| `services.py` duplikasi & signature | Rentang pencatatan | Signature mencakup akhir tambahan; serialisasi/transfer metadata tambahan tetap di langkah 1.2 | 1.2 |
| `detail_project/views.py` + template Jadwal | Rentang pencatatan | `data-project-end` disediakan dari helper, bukan tanggal kontrak langsung | Tes UI setelah 1.7 |
| Kunci rencana, penanda, garis | **Batas rencana** (`tanggal_selesai` via helper) | Belum dipasang; sesuai langkah 1.3/1.7 | 1.3/1.7 |
| `dashboard/*` status, filter, form | **Tidak diubah** sebagai acuan; `ProjectForm` mengecualikan field tambahan | Status & filter tetap memakai akhir kontrak | Tes field/form |

### Langkah 1.6 — Ubah hari batas minggu — DONE 2026-09-29

- Isi yang dikerjakan: kedua API batas minggu meminta pilihan eksplisit sebelum memindahkan rencana yang baru menjadi minggu tambahan; pilihan memindahkan hanya planned, mempertahankan actual/biaya dan rencana historis di minggu tambahan. Tanggal baris mingguan diselaraskan ke bucket baru. Perubahan ditolak bila mengeluarkan baris progres dari seluruh rentang kerja; regenerate gagal me-rollback seluruh perubahan.
- File diubah: `timeline_utils.py`, `views_api_tahapan_v2.py`, `jadwal_kegiatan_app.js`, `tests_additional_plan_guard.py`, `jadwal_batch_b.test.js`.
- Uji baru / diubah: pratinjau, pilihan pindah, minggu historis, actual/biaya, rentang yang menyusut, no-op tanpa rencana, rollback regenerate.
- Hasil uji (perintah + angka): PostgreSQL 21 tes lulus; Vitest `jadwal_batch_b.test.js` 9 tes lulus; `npm run build` berhasil.
- Commit: `e1482ce6`.
- Temuan di luar rencana (→ §8): mengganti hari batas dapat mengurangi jumlah bucket masa kerja dan menyembunyikan baris progres paling akhir; perubahan kini ditolak tanpa menghapus data (D-12).
- Catatan untuk langkah berikutnya: implementasikan tombol/dialog, penanda grid, kunci rencana, Kurva S/Gantt, dan build final di 1.7.

### Langkah 1.7 — Frontend — REVIEW 2026-09-30

- Isi yang dikerjakan: API kolom mengirim metadata minggu batas/tambahan dari helper server; tombol hanya tampil di mode Realisasi; dialog tanggal menjalankan preview sebelum commit dan meminta pilihan bila planned akan ditata. Grid memberi label, arsiran, divider, dan penguncian minggu tambahan di mode Rencana. Kurva S dan Gantt menampilkan garis vertikal akhir waktu kerja. PNG Kurva S kini dirender langsung pada ukuran piksel target; unduhan PNG penuh memakai skala adaptif 3×.
- File diubah: template Jadwal, `views_api_tahapan.py`, `timeline_utils.py`, `jadwal_kegiatan_app.js`, DataLoader, TimeColumnGenerator, TanStack grid, overlay Kurva S/Gantt, `canvas-export-scale.js`, `kurva-s-renderer.js`, tes JS/Python, bundle `dist/`.
- Uji baru / diubah: metadata API dan halaman, lock planned vs actual, tanggal lokal, penanda grafik, perpanjangan/pengurangan, progres/catatan di luar rentang.
- Hasil uji (perintah + angka): PostgreSQL 46 tes gabungan lulus; suite halaman/API 13 tes lulus; Vitest penuh 33 file, 408 lulus dan 25 skipped; `npm run build` berhasil.
- Commit: `d87390af`; perbaikan review `6b506eed`; kualitas PNG `c10656c4` + bundle `584ccef4`.
- Temuan di luar rencana (→ §8): minggu yang akan dipendekkan bisa berisi catatan walau progresnya nol; perubahan kini ditahan agar catatan tidak hilang (D-13).
- Catatan untuk langkah berikutnya: kode siap UAT; checklist manual §6 belum dijalankan.

---

## 6. Checklist UAT (setelah 1.7)

| # | Skenario | Hasil yang diharapkan | Hasil | Tanggal |
|---|---|---|---|---|
| U-1 | Buka Jadwal mode Rencana | Tombol "Perpanjang Waktu Kerja" tidak tampil | Otomatis sebagian: kode `_syncWorkExtensionButtonVisibility` + tes sumber `jadwal_batch_b`. **Cek visual owner** | 2026-09-30 |
| U-2 | Mode Realisasi, ada editan belum disimpan, tekan tombol | Dialog tidak terbuka; pesan "Simpan atau batalkan…" | Otomatis sebagian: pesan penjaga ada (`jadwal_batch_b`). **Cek visual owner** | 2026-09-30 |
| U-3 | Akhir waktu kerja Rabu, isi tambahan Jumat minggu yang sama | Terdeteksi tipe 1; tidak ada kolom baru; header minggu batas "Waktu kerja berakhir Rab" | PASS otomatis (API preview: `tipe_1`, minggu 7→7) | 2026-09-30 |
| U-4 | Akhir waktu kerja 30 Sep, isi tambahan 31 Des | Terdeteksi tipe 2; kolom M27–M39 "Penambahan"; grid tetap di mode Realisasi | PASS otomatis (API: `tipe_2`, minggu 7→21; commit menyimpan 31/12; mulai/selesai/durasi tetap) | 2026-09-30 |
| U-5 | Isi realisasi (persen, volume, biaya) di minggu tambahan, simpan | Tersimpan; Kurva S realisasi berlanjut melewati garis "Akhir Waktu Kerja" | PASS otomatis (realisasi 5% tersimpan di M10 lewat API). Kurva S: **cek visual owner** | 2026-09-30 |
| U-6 | Pindah ke mode Rencana | Minggu tambahan terkunci & berlabel; minggu batas tidak terkunci; klik sel terkunci memunculkan pesan | PASS otomatis sisi server (`planned_in_extension`) + tes grid `tanstack-grid-manager` (kunci hanya mode Rencana). Pesan klik: **cek visual owner** | 2026-09-30 |
| U-7 | Pendekkan tambahan melewati minggu yang berisi realisasi | Ditolak dengan pesan minggu terkait | PASS otomatis (ditolak `actual_out_of_window`, minggu 7) | 2026-09-30 |
| U-8 | Hapus tambahan tanpa realisasi di masa tambahan | Masa waktu kerja kembali ke akhir waktu kerja | PASS otomatis (tambahan dihapus; masa kerja = akhir waktu kerja) | 2026-09-30 |
| U-9 | Edit Project: akhir waktu kerja 30 Sep → 31 Okt, tambahan 31 Des | Tambahan tetap 31 Des | PASS otomatis (form Edit Project: selesai 30/09, tambahan 31/12 tetap) | 2026-09-30 |
| U-10 | Edit Project: akhir waktu kerja → 15 Jan (melewati tambahan) | Tambahan dikosongkan; masa s.d. 15 Jan | PASS otomatis (selesai 15/01/2027; tambahan dikosongkan) | 2026-09-30 |
| U-11 | Edit Project: akhir waktu kerja dimajukan, ada rencana di minggu yang menjadi minggu tambahan | Dialog; "Pindahkan rencana" hanya memindah rencana; realisasi & biaya tetap | PASS otomatis (dialog tanpa simpan; "pindahkan rencana" → rencana ke minggu batas, realisasi & biaya tetap) | 2026-09-30 |
| U-12 | Edit Massal dengan kasus U-11 | Proyek dilewati & dilaporkan | PASS otomatis (Edit Massal: proyek dilewati, `needs_decision`) | 2026-09-30 |
| U-13 | Backup → restore proyek bertambahan | Tambahan, semua minggu, biaya aktual & catatan kembali utuh | PASS otomatis (backup→restore: tambahan & semua baris/biaya/catatan identik) | 2026-09-30 |
| U-14 | Duplikasi proyek bertambahan dengan "salin jadwal" | Progres & tambahan ikut tersalin | PASS otomatis (duplikasi tanggal sama: tambahan & progres tersalin; D-11: tanggal kontrak baru → tanpa tambahan) | 2026-09-30 |
| U-15 | Dua tab: perpanjang di tab A, lalu di tab B | Tab B ditolak; diminta memuat ulang | PASS otomatis (revisi usang → 409) | 2026-09-30 |
| U-16 | Proyek tanpa tambahan | Tidak ada perbedaan dari sebelum fitur (selain tombol di mode Realisasi) | PASS otomatis via suite penuh (I-1). **Cek visual owner** sekilas | 2026-09-30 |

---

## 7. Log keputusan & perubahan scope

| Tanggal | # | Keputusan / perubahan | Oleh | Dampak |
|---|---|---|---|---|
| 2026-09-28 | D-1 | Minggu tambahan hanya menerima realisasi; tidak ada pembekuan baseline | Owner | Rancangan 2.3 |
| 2026-09-29 | D-2 | Satu input tanggal; jenis perpanjangan dideteksi sistem; hanya di mode Realisasi; tanpa banner | Owner | Rancangan 3 |
| 2026-09-29 | D-3 | Akhir waktu kerja (Dashboard) tetap batas kontrak; kolom baru menyimpan tambahan; masa waktu kerja = sampai akhir tambahan bila ada | Owner | Rancangan v8 |
| 2026-09-29 | D-4 | Mengubah akhir waktu kerja tidak memendekkan tambahan; tambahan hanya diubah dari halaman Jadwal | Owner | Rancangan 2.2, 5.4 |
| 2026-09-29 | D-5 | Label penanda "Penambahan Waktu Kerja" | Owner | Rancangan 3.7 |
| 2026-09-29 | D-6 | Rencana terdampak saat akhir waktu kerja dimajukan: dialog Edit Project (pindahkan rencana saja / batalkan); Edit Massal lewati & laporkan | Owner + review | Rancangan 3.6 |
| 2026-09-29 | D-7 | Export dibahas setelah fase ini; teks tanggal di export tidak sekarang | Owner | Rancangan 9 |
| 2026-09-29 | D-8 | Konsolidasi pinggiran (Tahap 0) sebelum fitur | Owner | Doc 40 §3 |
| 2026-09-29 | D-9 | G0-1: WIP owner dibiarkan; branch kerja dari HEAD `e0a4cb71` | Owner | Gate 0 |
| 2026-09-29 | D-10 | G0-5: duplikasi dengan tanggal mulai baru mempertahankan nomor minggu; luapan tidak disalin & dilaporkan | Owner | Langkah 0.3 |
| 2026-09-30 | D-11 | **Diputuskan owner: tambahan TIDAK disalin** saat duplikasi dengan tanggal kontrak baru; duplikasi tanggal sama tetap menyalin; minggu progres yang tidak muat tidak disalin & dilaporkan (G0-5). Diimplementasikan Claude (`services.py` DeepCopyService) + tes `tests_progress_transfer_roundtrip` | Owner / Claude | W-1b |
| 2026-09-29 | D-12 | Perubahan hari batas yang mengurangi jumlah minggu dan akan menyembunyikan baris progres di luar rentang baru ditolak; tidak ada baris yang dihapus | Implementasi 1.6 | Invariant I-3; 409 pada kedua API; pengguna perlu menyesuaikan timeline terlebih dahulu |
| 2026-09-30 | D-13 | Pemendekan tambahan ditolak bila minggu yang akan dikeluarkan masih memiliki catatan, termasuk baris dengan nilai progres nol | Implementasi 1.7 | Catatan tidak lagi hilang saat resolusi timeline; catatan harus dipindahkan atau dihapus terlebih dahulu |
| 2026-09-30 | D-14 | Repair timeline tanpa perubahan tanggal tetap menganalisis baris mingguan basi; target tambahan melarang perubahan tanggal mulai; resolusi yang akan menaruh planned pada minggu tambahan tidak ditawarkan | Review Codex | Memperbaiki temuan blocker/major/minor; tanpa mengubah tanggal kontrak |

---

## 8. Log kejadian (temuan selama eksekusi)

Catat setiap kondisi yang tidak ada di rancangan/audit: apa yang ditemukan, bukti,
dampak, dan keputusan (kerjakan sekarang / catat / tunda).

| Tanggal | Langkah | Temuan | Bukti | Keputusan |
|---|---|---|---|---|
| 2026-09-29 | G0-4 | Percobaan pertama memakai database uji bawaan gagal karena database itu tidak ada; hasil dibuang dan baseline diulang dengan nama database khusus | Log `/tmp/twk-baseline-isolated-20260929.log` di container | Baseline terisolasi selesai; database aplikasi tidak disentuh |
| 2026-09-29 | 1.6 | Perubahan hari batas dapat mengurangi jumlah bucket dan membuat baris progres akhir tidak lagi punya kolom | Tes `test_week_boundary_that_would_hide_progress_outside_new_work_range_is_blocked` | D-12: tolak perubahan dan pertahankan data; kebijakan ini menghindari nilai progres tersembunyi |
| 2026-09-30 | 1.7 | Baris catatan tanpa planned/actual/biaya tetap merupakan data dan bisa berada di minggu yang dipendekkan | Tes `test_shortening_additional_period_does_not_drop_notes_outside_new_range` | D-13: preview dan commit menolak perubahan; catatan harus dipindahkan/dihapus dulu |
| 2026-09-30 | Review | Repair timeline dengan tanggal tidak berubah tidak memeriksa baris mingguan yang tanggalnya sudah di luar jendela; API tambahan juga belum melarang perubahan tanggal mulai | `tests_timeline_repair_ui`, tes target tambahan, dan suite penuh terisolasi | Diperbaiki: deteksi kembali ke tanggal baris aktual; tambahan menolak tanggal mulai berbeda; opsi `accumulate_edge` dihilangkan bila targetnya minggu tambahan |
| 2026-09-30 | Review | Perbaikan repair perlu memilih `tanggal_akhir_tambahan` saat proyek punya tambahan; bila memakai akhir waktu kerja sebagai akhir kontrak, tombol dapat mengubah kontrak | Tes repair proyek bertambahan mempertahankan `tanggal_selesai` | `timeline_repair.js` kini memilih target sesuai metadata proyek; API service tetap menjadi pagar tanggal mulai |

---

## 9. Log bukti uji

| Tanggal | Langkah | Perintah | Hasil | Catatan |
|---|---|---|---|---|
| 2026-09-29 | G0-4 | Runner Django PostgreSQL; `detail_project` + `dashboard`; database `test_twk_codex_20260929` | 842 tes: 3 gagal lama, 40 skipped, 6 expected failure | Kegagalan sama dengan tiga guard lama yang sudah didokumentasikan |
| 2026-09-29 | G0-4 | `npm run test:frontend -- --reporter=dot` | 32 file; 396 lulus, 25 skipped | Run penuh ulang lulus |
| 2026-09-29 | 0.1 | `detail_project.tests_progress_transfer_roundtrip` pada PostgreSQL terisolasi | 12 tes: 3 lulus, 9 expected failure | Menangkap A–C, duplikasi form Dashboard, batas minggu nondefault, statistik export, dan tanggal fallback legacy |
| 2026-09-29 | 0.2 | `detail_project.tests_progress_transfer_roundtrip` pada PostgreSQL terisolasi | 12 tes: 6 lulus, 6 expected failure | Statistik export, minggu pendek Minggu/Jumat, dan tanggal fallback lulus; expected failure tersisa untuk bug A/C |
| 2026-09-29 | 0.3 | Runner Django PostgreSQL: round-trip transfer, pemisahan format export JSON, dan smoke test Dashboard | 50 tes lulus | Mencakup biaya/catatan, duplikasi service/API/form, tanggal mulai baru, dan minggu yang tidak muat |
| 2026-09-29 | 0.4 | Lima suite timeline/dashboard dan tes transfer pada PostgreSQL | 73 tes lulus | Termasuk uji jenis tulis planned_new, actual, historical, user_move; planned/realisasi/biaya tetap terpisah |
| 2026-09-29 | 0.4 | Round-trip transfer, pemisahan export JSON, dan smoke test Dashboard | 56 tes lulus | Backup/restore, salin jadwal, duplikasi Dashboard dan API lulus setelah memakai layanan tulis tunggal |
| 2026-09-29 | 1.1 | Migrasi Dashboard 0017; 8 modul helper/timeline di PostgreSQL | 65 tes lulus | Field, constraint tanggal, revisi jadwal, Dashboard form, API target-field, helper dan regresi timeline |
| 2026-09-29 | 1.1 | `python manage.py makemigrations dashboard --check --dry-run` | Tidak ada perubahan model yang belum dimigrasikan | Migrasi 0017 sesuai model |
| 2026-09-29 | 1.2 | Round-trip progres, export JSON, dashboard smoke di PostgreSQL | 62 tes lulus | Tambahan waktu pulih dari backup dan duplikasi service/API/form; backup legacy tanpa field menghasilkan tambahan kosong |
| 2026-09-29 | 1.3 | Guard API/timeline, readiness historis, regresi Jadwal di PostgreSQL | 73 tes lulus | Planned baru ditolak; actual/biaya diterima; planned historis ditandai dan tetap bisa berdampingan dengan input actual |
| 2026-09-29 | 1.3 | `npm run test:frontend -- detail_project/static/detail_project/js/tests/readiness_banner.test.js --reporter=dot` | 16 tes lulus | Readiness banner menampilkan planned historis di minggu tambahan |
| 2026-09-29 | 1.3 | `detail_project.tests_wp_b7_reference_sync` pada PostgreSQL | 46 tes lulus | Kontrak readiness/API lama tetap sesuai setelah versi schema menjadi b4.7 |
| 2026-09-29 | 1.4 | Resolver timeline, target-field API, field model, dan dialog lama | 50 tes lulus | Tipe perpanjangan/pengurangan, hapus tambahan, penjagaan minggu terbuang, penyelarasan tanggal baris, dan snapshot audit |
| 2026-09-29 | 1.5 | Dashboard Edit Project, Edit Massal, K-6 planned-only move, timeline guard | 66 tes lulus | Preview menahan penyimpanan; planned masuk ke batas; actual dan biaya sumber/tujuan tidak berubah; proyek mass edit yang butuh keputusan dilewati |
| 2026-09-29 | 1.5 | Uji tampilan tanggal tambahan dan ubah akhir kontrak melewati tambahan | 17 tes lulus | Tanggal tambahan hanya ditampilkan; form tidak menulis ulang field tersembunyi yang dikosongkan oleh layanan |
| 2026-09-29 | 1.6 | Uji API batas minggu, rencana terdampak, progres di luar rentang, rollback regenerate | 21 tes lulus | PostgreSQL terisolasi; mencakup kedua API, planned-only move, rencana historis, actual/biaya, dan gagal-regenerate tanpa perubahan parsial |
| 2026-09-29 | 1.6 | Uji frontend `jadwal_batch_b.test.js` | 9 tes lulus | Dialog pilihan eksplisit dan penolakan aman diperiksa |
| 2026-09-29 | 1.6 | `npm run build` | Berhasil | Vite menampilkan peringatan bundle Jadwal >500 kB; bundle final dikerjakan bersama tahap 1.7 |
| 2026-09-30 | 1.7 | PostgreSQL: API metadata, timeline, batas minggu, audit, dan guard catatan | 46 tes gabungan lulus; suite halaman/API 13 tes lulus | Database uji terisolasi; render halaman baru dicek oleh Django Client |
| 2026-09-30 | 1.7 | `npm run test:frontend -- --reporter=dot` | 33 file; 408 lulus, 25 skipped | Pengulangan penuh lulus; satu percobaan paralel dengan build sempat timeout lalu tes dan suite lulus saat build selesai |
| 2026-09-30 | 1.7 | `npm run build` | Berhasil | Bundle Jadwal tetap >500 kB; artifact Vite baru ikut commit `d87390af` |
| 2026-09-30 | Review fixes | PostgreSQL: `tests_timeline_repair_ui` + `tests_additional_plan_guard` | 27 tes lulus | Tiga regresi repair, target tambahan, tanggal mulai yang dimanipulasi, dan resolusi planned yang aman |
| 2026-09-30 | Review gate | Runner penuh PostgreSQL terisolasi `test_twk_reviewfix_full_20260930`; `detail_project` + `dashboard` | 894 tes: **3 gagal baseline**, 40 skipped | Tidak ada kegagalan baru. Tiga yang gagal sama dengan §3: `test_shared_signature_has_bounded_query_count`, `test_query_budget_constant_no_n_plus_1`, `test_template_does_not_auto_reload_pending_jobs_on_open` |
| 2026-09-30 | Review fixes | `npm run test:frontend -- --reporter=dot` | 33 file; 408 lulus, 25 skipped | Berhasil setelah perubahan target payload timeline repair |
| 2026-09-30 | Export PNG Kurva S | Uji skala ekspor + kontrak renderer | 6 tes lulus; Vitest penuh 38 file, 428 lulus, 25 skipped | DPI tidak lagi dicapai dengan membesarkan chart kecil; renderer membuat plot pada resolusi target; unduhan penuh dibatasi maksimal 64 MP |
| 2026-09-30 | Export PNG Kurva S | `npm run build` di worktree bersih dari WIP lain | Berhasil | Bundle `jadwal-kegiatan-BUExKZfW.js` sesuai source yang di-commit; peringatan ukuran chunk >500 kB tetap ada |
| 2026-09-30 | Review fixes | PostgreSQL: `tests_timeline_repair_ui` + `tests_additional_plan_guard` | 27 tes lulus | Termasuk preview/commit repair tanpa mengubah kontrak pada proyek bertambahan, reject tanggal mulai, dan satu-satunya resolusi yang aman |
| 2026-09-30 | Review gate final | Runner penuh serial PostgreSQL; database `test_twk_reviewfix_full_20260930`; `detail_project` + `dashboard` | **894 tes; 3 gagal baseline, 40 skipped** | Sama persis dengan tiga kegagalan §3; tidak ada kegagalan baru. Runner berakhir non-zero hanya karena tiga guard baseline |
| 2026-09-30 | Review gate final | `npm run test:frontend -- --reporter=dot` | 33 file; 408 lulus, 25 skipped | Lulus setelah perubahan repair payload |
| | | | | |

---

## 10. Invariant lintas langkah

Diperiksa ulang di setiap langkah; pelanggaran = langkah tidak boleh `DONE`.

| # | Invariant |
|---|---|
| I-1 | Proyek tanpa tambahan berperilaku identik dengan sebelum fitur |
| I-2 | Tindakan dari halaman Jadwal tidak mengubah `tanggal_mulai`, `tanggal_selesai`, `durasi_hari` |
| I-3 | Realisasi & biaya aktual tidak pernah dipindah atau dihapus diam-diam |
| I-4 | Rencana hanya dipindah atas pilihan user; pembentukan ulang tidak memindahkan nilai |
| I-5 | Rentang pencatatan dan batas rencana hanya dihitung lewat helper `timeline_utils` |
| I-6 | Backup → restore mempertahankan seluruh baris progres; duplikasi menyalin semua baris yang muat pada timeline tujuan dan melaporkan baris yang tidak muat |
| I-7 | Kegagalan suite tidak melebihi baseline (§3) |

---

## 11. Rollback

Lihat doc 40 §6. Catat di sini setiap rollback yang benar-benar dilakukan:

| Tanggal | Langkah | Alasan | Tindakan |
|---|---|---|---|
| | | | |

---

## 12. Di luar scope

Rancangan §10, plus fase export (rancangan §9) dan catatan bobot laporan
(rancangan §8.3).
