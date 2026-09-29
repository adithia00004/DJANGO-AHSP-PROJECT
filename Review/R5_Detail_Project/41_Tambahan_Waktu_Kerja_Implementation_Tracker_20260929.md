# 41 — Tracker Eksekusi: Tambahan Waktu Kerja

| | |
|---|---|
| Status keseluruhan | **TAHAP 1 BERJALAN** — Langkah 1.1–1.3 selesai; berikutnya 1.4. Lihat bukti §3–§5 dan §9 |
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
| 1.4 | Perpanjang / pendekkan / hapus tambahan | TODO | | |
| 1.5 | Ubah akhir waktu kerja (Dashboard) + pindahkan rencana | TODO | | |
| 1.6 | Ubah hari batas minggu | TODO | | |
| 1.7 | Frontend (tombol, dialog, grid, Kurva S/Gantt, build) | TODO | | |
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

---

## 6. Checklist UAT (setelah 1.7)

| # | Skenario | Hasil yang diharapkan | Hasil | Tanggal |
|---|---|---|---|---|
| U-1 | Buka Jadwal mode Rencana | Tombol "Perpanjang Waktu Kerja" tidak tampil | | |
| U-2 | Mode Realisasi, ada editan belum disimpan, tekan tombol | Dialog tidak terbuka; pesan "Simpan atau batalkan…" | | |
| U-3 | Akhir waktu kerja Rabu, isi tambahan Jumat minggu yang sama | Terdeteksi tipe 1; tidak ada kolom baru; header minggu batas "Waktu kerja berakhir Rab" | | |
| U-4 | Akhir waktu kerja 30 Sep, isi tambahan 31 Des | Terdeteksi tipe 2; kolom M27–M39 "Penambahan"; grid tetap di mode Realisasi | | |
| U-5 | Isi realisasi (persen, volume, biaya) di minggu tambahan, simpan | Tersimpan; Kurva S realisasi berlanjut melewati garis "Akhir Waktu Kerja" | | |
| U-6 | Pindah ke mode Rencana | Minggu tambahan terkunci & berlabel; minggu batas tidak terkunci; klik sel terkunci memunculkan pesan | | |
| U-7 | Pendekkan tambahan melewati minggu yang berisi realisasi | Ditolak dengan pesan minggu terkait | | |
| U-8 | Hapus tambahan tanpa realisasi di masa tambahan | Masa waktu kerja kembali ke akhir waktu kerja | | |
| U-9 | Edit Project: akhir waktu kerja 30 Sep → 31 Okt, tambahan 31 Des | Tambahan tetap 31 Des | | |
| U-10 | Edit Project: akhir waktu kerja → 15 Jan (melewati tambahan) | Tambahan dikosongkan; masa s.d. 15 Jan | | |
| U-11 | Edit Project: akhir waktu kerja dimajukan, ada rencana di minggu yang menjadi minggu tambahan | Dialog; "Pindahkan rencana" hanya memindah rencana; realisasi & biaya tetap | | |
| U-12 | Edit Massal dengan kasus U-11 | Proyek dilewati & dilaporkan | | |
| U-13 | Backup → restore proyek bertambahan | Tambahan, semua minggu, biaya aktual & catatan kembali utuh | | |
| U-14 | Duplikasi proyek bertambahan dengan "salin jadwal" | Progres & tambahan ikut tersalin | | |
| U-15 | Dua tab: perpanjang di tab A, lalu di tab B | Tab B ditolak; diminta memuat ulang | | |
| U-16 | Proyek tanpa tambahan | Tidak ada perbedaan dari sebelum fitur (selain tombol di mode Realisasi) | | |

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
| 2026-09-29 | D-11 | Saat tanggal timeline duplikasi berubah, durasi tambahan (jumlah hari dari akhir kontrak ke akhir tambahan) dipertahankan dari akhir kontrak hasil salinan | Implementasi 1.2 | W-1b; uji duplikasi dengan tanggal baru |

---

## 8. Log kejadian (temuan selama eksekusi)

Catat setiap kondisi yang tidak ada di rancangan/audit: apa yang ditemukan, bukti,
dampak, dan keputusan (kerjakan sekarang / catat / tunda).

| Tanggal | Langkah | Temuan | Bukti | Keputusan |
|---|---|---|---|---|
| 2026-09-29 | G0-4 | Percobaan pertama memakai database uji bawaan gagal karena database itu tidak ada; hasil dibuang dan baseline diulang dengan nama database khusus | Log `/tmp/twk-baseline-isolated-20260929.log` di container | Baseline terisolasi selesai; database aplikasi tidak disentuh |

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
