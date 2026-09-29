# 40 — Rencana Implementasi: Tambahan Waktu Kerja

| | |
|---|---|
| Tanggal | 2026-09-29 |
| Rancangan (acuan desain) | [`docs/RENCANA_JADWAL_MELEWATI_AKHIR_KONTRAK.md`](../../docs/RENCANA_JADWAL_MELEWATI_AKHIR_KONTRAK.md) v9 |
| Audit backend | [`docs/REVIEW_BACKEND_JADWAL_KETERLAMBATAN_20260929.md`](../../docs/REVIEW_BACKEND_JADWAL_KETERLAMBATAN_20260929.md) |
| Tracker (satu-satunya sumber status) | [`41_Tambahan_Waktu_Kerja_Implementation_Tracker_20260929.md`](41_Tambahan_Waktu_Kerja_Implementation_Tracker_20260929.md) |
| Terkait | Doc 37/38/39 (layanan perubahan timeline yang dipakai ulang) |

Dokumen ini menjawab **"apa yang dikerjakan, di file mana, bagaimana diuji, dan
kapan dianggap selesai"** untuk setiap langkah. *Mengapa*-nya ada di dokumen
rancangan; *status*-nya hanya di tracker (doc 41).

---

## 1. Aturan kerja

| Aturan | Isi |
|---|---|
| Satu langkah = satu commit | Tidak mencampur langkah. Pesan commit: `<tipe>(jadwal): <langkah> — <ringkas>`, mis. `fix(jadwal): 0.2 — restore memakai aturan minggu kanonik` |
| Uji dulu | Setiap langkah dimulai dari uji yang menggambarkan perilaku target |
| Lingkungan uji | Docker/PostgreSQL: `docker exec ahsp_web sh -c 'cd /app && python manage.py test <modul> --noinput'`. Suite penuh dijalankan **serial** (`--parallel` crash saat ada kegagalan) |
| Baseline merah | 3 kegagalan lama yang diketahui (anggaran query ×2, `scheduleAutoReloadPendingJobs`). Tidak boleh bertambah |
| Hunk terpisah | WIP owner yang belum di-commit tidak boleh ikut commit langkah (stage per hunk bila berbagi file) |
| Tidak mengubah perilaku di luar langkah | Perbaikan temuan lain dicatat di tracker §Log kejadian, bukan dikerjakan diam-diam |
| Dokumen | Tracker diperbarui saat langkah mulai, selesai, diblokir, atau ada temuan/keputusan baru |

---

## 2. Gate 0 — Sebelum langkah pertama

| # | Isi | Selesai bila |
|---|---|---|
| G0-1 | **Rapikan git** (keputusan T-2): WIP owner di-commit atau disimpan; tentukan nasib tiga branch bertumpuk (`fix/laporan-harian` → `fix/laporan-bulanan` → `feat/edit-massal-discoverability`) | Owner memutuskan; working tree bersih dari perubahan yang bukan milik pekerjaan ini |
| G0-2 | Commit dokumen: rancangan v9, audit backend, doc 40, doc 41 | Commit dokumen ada di branch kerja |
| G0-3 | Branch kerja baru: `feat/tambahan-waktu-kerja` | Branch dibuat dari titik yang disepakati di G0-1 |
| G0-4 | Rekam **baseline**: suite penuh `detail_project` + `dashboard` (serial), 42 uji timeline, uji export | Angka lulus/gagal & daftar kegagalan tercatat di tracker §Baseline |
| G0-5 | **Keputusan kebijakan duplikasi** dengan tanggal mulai baru (W-1b) | Owner memilih (lihat tracker Gate 0) |

---

## 3. Tahap 0 — Konsolidasi pinggiran

Tanpa fitur baru. Memperbaiki bug A–C (audit) dan menyiapkan titik tunggal.

### 0.1 — Jaring pengaman: uji bolak-balik

| | |
|---|---|
| File baru | `detail_project/tests_progress_transfer_roundtrip.py` |
| Skenario | (a) backup JSON → restore; (b) duplikasi via service `DeepCopyService`, via API (`views_api.py:6859`), via form Dashboard (`dashboard/views.py:774`) dengan "salin jadwal"; (c) tanpa "salin jadwal" |
| Data uji | Proyek 6–13 Sep 2026 (minggu pertama pendek, 2 minggu kanonik); proyek dengan `week_end_day` non-Minggu; baris dengan rencana, realisasi, `actual_cost=0`, `actual_cost=None`, `actual_cost=5000`, `notes` terisi |
| Pembanding | **Seluruh baris** `PekerjaanProgressWeekly`: pekerjaan (via pemetaan), `week_number`, `week_start_date`, `week_end_date`, `planned_proportion`, `actual_proportion`, `actual_cost`, `notes`; plus metadata proyek `tanggal_selesai`, `week_start_day`, `week_end_day` |
| Penandaan | Uji yang mereproduksi A–C diberi `@unittest.expectedFailure` dengan komentar rujukan temuan, agar suite tetap hijau; penanda dicabut di langkah yang memperbaikinya |
| Selesai bila | Uji ada; kasus A, B, C **gagal sesuai prediksi** (tercatat sebagai expected failure); kasus yang sudah benar lulus |

### 0.2 — Satu aturan minggu untuk restore

| | |
|---|---|
| File | `detail_project/views_api.py` — import JSON (`:9680-9719`) dan statistik export JSON (`:9292-9301`) |
| Perubahan | Ganti `ceil(hari/7)` dengan `timeline_utils.expected_week_count`; tanggal fallback baris dari `progress_utils.build_week_buckets`, bukan `mulai + 7n` |
| Uji | Cabut `expectedFailure` kasus B di 0.1; tambah: minggu terakhir pendek, `week_end_day` nondefault, realisasi di minggu terakhir |
| Selesai bila | Kasus B lulus; tidak ada baris yang terbuang untuk rentang yang sah |

### 0.3 — Satu penyalin data progres

| | |
|---|---|
| File baru | `detail_project/progress_transfer.py` — `serialize_weekly_rows(project)`, `restore_weekly_rows(project, rows, pekerjaan_map)`, `copy_weekly_rows(source, target, pekerjaan_map)` |
| Dipakai oleh | Export JSON (`views_api.py:8917-8926`, `9267-9278`), import JSON (`:9721-9729`), `DeepCopyService._copy_jadwal_pekerjaan` (`services.py:5134`) |
| Field disalin | rencana, realisasi, `actual_cost` (**0 ≠ kosong**), `notes`, nomor & tanggal minggu |
| Duplikasi | Menyalin data mingguan saat "salin jadwal"; proyeksi `PekerjaanTahapan` **disinkronkan dari** data mingguan (`sync_weekly_to_tahapan`), bukan disalin sebagai sumber. `_copy_project` (`services.py:4348`) menyalin `tanggal_selesai`, `week_start_day`, `week_end_day` sesuai kebijakan G0-5 |
| Kompatibilitas | Backup lama tanpa `actual_cost`/`notes` tetap bisa direstore (field dianggap kosong) |
| Uji | Cabut `expectedFailure` kasus A & C |
| Selesai bila | Seluruh uji 0.1 lulus; uji import/duplikasi lama tetap lulus |

### 0.4 — Satu layanan tulis progres

| | |
|---|---|
| File baru | `detail_project/progress_write_service.py` — `write_progress(project, cells, *, kind)` dengan `kind ∈ {planned_new, actual, historical, user_move}` |
| Dipakai oleh | Simpan grid v2 (`views_api_tahapan_v2.py:313-347`), restore (via 0.3), duplikasi (via 0.3) |
| Isi | Memindahkan logika tulis yang ada **apa adanya** (get_or_create, tanggal minggu, field per mode, `actual_cost`, notes) ke satu tempat. **Belum** ada aturan tambahan waktu kerja |
| Uji | Uji simpan grid, import, duplikasi yang ada + uji unit layanan per `kind` |
| Selesai bila | Semua uji lama lulus tanpa perubahan; 42 uji timeline lulus |

---

## 4. Tahap 1 — Tambahan Waktu Kerja

### 1.1 — Skema, helper, penyisiran, field target

| | |
|---|---|
| Skema | `dashboard/models.py`: `tanggal_akhir_tambahan = DateField(null=True, blank=True)`; validasi `> tanggal_selesai` bila terisi; masuk daftar pemicu `schedule_revision` (`:150-157`). Migrasi skema baru di `dashboard/migrations/` |
| Helper | `detail_project/timeline_utils.py`: `work_period_end`, `boundary_week`, `is_extension_week`, `is_extension_day` (rancangan 5.2) |
| Penyisiran | Setiap titik rancangan 4.6 dipilah: **rentang pencatatan** → `work_period_end`; **batas rencana** → helper batas. Daftar titik & keputusan per titik dicatat di tracker |
| Field target | `apply_project_timeline_change` / `analyze_project_timeline_change` menerima `target_field ∈ {'tanggal_selesai', 'tanggal_akhir_tambahan'}`; hanya field itu (dan `durasi_hari` bila target `tanggal_selesai`) yang ditulis. `_persisted_timeline` membaca rentang pencatatan |
| Uji | Seluruh suite tanpa tambahan: perilaku identik. Uji helper: kontrak berakhir Rabu, tambahan Jumat (tipe 1) & +n minggu (tipe 2). Uji field target: perubahan dengan target tambahan **tidak** mengubah `tanggal_mulai`, `tanggal_selesai`, `durasi_hari` |
| Selesai bila | Kriteria rancangan 6.2/1.1 terpenuhi; penyisiran tercatat lengkap di tracker |

### 1.2 — Tambahan ikut backup/restore/duplikasi (W-1e)

| | |
|---|---|
| File | `progress_transfer.py` (metadata), export/import JSON, `_copy_project` |
| Uji | Uji 0.1 diperluas: proyek bertambahan kembali utuh; backup lama tanpa field → kosong |
| Selesai bila | Bolak-balik mempertahankan `tanggal_akhir_tambahan` |

### 1.3 — Aturan tulis rencana

| | |
|---|---|
| File | `progress_write_service.py`; `detail_project/readiness.py` (penanda data lama) |
| Aturan | `planned_new` > 0 di minggu tambahan → tolak dengan pesan rancangan 3.8; `actual` diterima; `historical` dipertahankan & ditandai readiness "rencana di masa tambahan (data lama)"; `user_move` tujuan dibatasi ke minggu waktu kerja. Tidak dipasang di `full_clean()` model |
| Uji | Tolak rencana; terima realisasi & biaya; restore rencana M9 (batas M8) dipertahankan & ditandai; perpanjang/bentuk ulang tidak memindahkan rencana M9 |
| Selesai bila | Semua kasus di atas lulus |

### 1.4 — Perpanjang / pendekkan / hapus tambahan

| | |
|---|---|
| Backend | Endpoint pratinjau & eksekusi yang ada (`views_api_tahapan_v2.py:619, 662`) menerima `tanggal_akhir_tambahan` (atau `hapus_tambahan`) dengan `target_field='tanggal_akhir_tambahan'`. Pratinjau mengembalikan `jenis ∈ {tipe_1, tipe_2, pengurangan, hapus, tidak_berubah}`, rentang minggu baru, dan alasan penolakan bila ada |
| Minggu pendek | Saat rentang berubah, `week_start_date`/`week_end_date` baris progres pada minggu yang rentangnya berubah diselaraskan; nomor minggu & nilai tetap |
| Uji | Rabu → Jumat: tipe 1, jumlah minggu tetap, tanggal kolom & baris progres sampai Jumat. 30 Sep → 31 Des: tipe 2. Pendekkan/hapus ditolak bila minggu dibuang berisi realisasi/biaya. Tanggal ≤ akhir waktu kerja ditolak. Konflik revisi ditolak |
| Selesai bila | Semua kasus lulus; tidak ada field selain `tanggal_akhir_tambahan` yang berubah |

### 1.5 — Perubahan akhir waktu kerja di Dashboard + pindahkan rencana

| | |
|---|---|
| Aturan | Rancangan 3.6 & 5.4: pasangan hasil dihitung dulu (akhir baru, tambahan tetap/dikosongkan), divalidasi di layanan |
| Operasi baru | `timeline_utils.move_planned_to_boundary(project, new_end, user)`: hanya `planned_proportion` dari minggu yang menjadi minggu tambahan dipindah ke minggu batas; realisasi & biaya tidak disentuh; lalu `sync_weekly_to_tahapan`, naikkan revisi, `invalidate_schedule_caches` |
| Edit Project | Dialog "Ringkasan dampak" (`project_form.html`) mendapat kasus baru: pilihan **Pindahkan rencana ke minggu batas** / **Batalkan** |
| Edit Massal | Kasus baru dilewati & dilaporkan (pola `views_mass_edit.py:197-267`) |
| Uji | Semua baris tabel rancangan 3.6; contoh M10 → M8 dengan tambahan mencakup M9 (hanya rencana pindah; realisasi & biaya tetap; proyeksi/revisi/cache diperbarui); tanpa tambahan → penolakan yang ada |
| Selesai bila | Semua kasus lulus di Edit Project dan Edit Massal |

### 1.6 — Perubahan hari batas minggu

| | |
|---|---|
| File | `views_api_tahapan_v2.py`: `api_update_week_boundaries` (`:525-570`), `api_regenerate_tahapan_v2` (`:1106-1155`) |
| Aturan | Bila minggu batas bergeser dan ada rencana di minggu yang menjadi minggu tambahan → pratinjau & pilihan yang sama dengan 1.5; tanpa pemindahan otomatis |
| Uji | Minggu berakhir Minggu → Senin dengan rencana di minggu yang bergeser |
| Selesai bila | Perubahan tidak tersimpan tanpa pilihan; tanpa rencana terdampak tersimpan langsung |

### 1.7 — Frontend

| | |
|---|---|
| Data | API kolom waktu Jadwal mengirim `is_extension_week`, `is_boundary_week`, `work_end_date` per kolom (dari helper server) |
| Toolbar & dialog | Tombol "Perpanjang Waktu Kerja" hanya di mode Realisasi (`_applyProgressModeSwitch`, `jadwal_kegiatan_app.js:2043`); dialog satu input tanggal + hasil deteksi dari pratinjau + penjaga `state.isDirty`; pola `timeline_repair.js` |
| Grid | `tanstack-grid-manager.js`: `readOnly` minggu tambahan hanya di mode Rencana; baris kecil penanda di header (`:334-346`); pesan klik sel terkunci |
| Kurva S & Gantt | Garis "Akhir Waktu Kerja" di posisi tanggal |
| Build | `npm run build` (Vite) → bundle `dist/` ikut di-commit sesuai kebiasaan repo |
| Uji | Uji JS yang ada tetap lulus; uji baru untuk kunci bergantung mode; **UAT manual** (tracker §UAT): tombol hanya di Realisasi, tipe 1/2, pendekkan ditolak, sel terkunci di Rencana |
| Selesai bila | Semua kriteria rancangan 6.2/1.7 dan checklist UAT lulus |

---

## 5. Logging dan audit aplikasi

Mengikuti pola yang sudah ada: layanan timeline mencatat ke `DetailAHSPAudit`
(`timeline_utils.py:785-812`), dan audit **tidak pernah** membatalkan transaksi yang sah.

### 5.1 Jejak audit (`DetailAHSPAudit`)

| Peristiwa | `old_data` | `new_data` | `change_summary` (contoh) |
|---|---|---|---|
| Perpanjang/pendekkan/hapus tambahan | `tanggal_akhir_tambahan` lama; `rows_before` bila ada baris berubah | `tanggal_akhir_tambahan` baru, `jenis`, `target_field`, rentang minggu baru | "Tambahan waktu kerja: – → 31 Des 2026 (tipe 2, +13 minggu)" |
| Ubah akhir waktu kerja (Dashboard) yang mengosongkan tambahan | tanggal & tambahan lama | tanggal baru, tambahan `null`, alasan | "Akhir waktu kerja 30 Sep → 15 Jan 2027; tambahan 31 Des dikosongkan" |
| Pindahkan rencana ke minggu batas | Snapshot rencana per pekerjaan & minggu sumber/tujuan | Nilai sesudah | "Rencana dipindah ke minggu batas M8 (3 pekerjaan)" |
| Ubah hari batas minggu dengan rencana terdampak | Hari batas lama, snapshot rencana terdampak | Hari batas baru, pilihan user | "Hari batas minggu Minggu → Senin; rencana dipindah (2 pekerjaan)" |
| Restore dengan rencana di masa tambahan | — | Jumlah baris historis yang ditandai | "Restore: 4 baris rencana di masa tambahan dipertahankan" |

### 5.2 Log teknis (`logging`)

| Logger | Level | Isi |
|---|---|---|
| `detail_project.timeline` | INFO | Commit perubahan rentang: `project_id`, `target_field`, `jenis`, jumlah minggu lama/baru, `schedule_revision` baru |
| `detail_project.timeline` | WARNING | Penolakan: alasan (`actual_out_of_window`, `planned_in_extension`, `revision_conflict`, `invalid_date`), `project_id`, minggu terkait |
| `detail_project.timeline` | EXCEPTION | Kegagalan menulis audit (pola yang ada) |
| `detail_project.progress_transfer` | WARNING | Backup tanpa field baru (kompatibilitas), baris dilewati beserta alasan |

Aturan: tanpa data pribadi (nama/email) di log; pakai ID. Pesan ke user tetap
dari rancangan 3.8 dan tidak membocorkan detail internal (pola `export_error_response`).

---

## 6. Rollback

| Lapisan | Cara |
|---|---|
| Per langkah | `git revert` commit langkah tersebut; setiap langkah berdiri sendiri |
| Skema | Kolom `tanggal_akhir_tambahan` nullable → migrasi dapat dibalik; sebelum membalik, pastikan tidak ada proyek bertambahan (atau dokumentasikan) |
| Data proyek | Mengosongkan tambahan (lewat "Hapus tambahan") mengembalikan perilaku lama, dengan aturan tolak realisasi yang sama |
| Frontend | Bundle Vite sebelumnya dikembalikan lewat revert commit build |
| Audit | Snapshot `rows_before` & snapshot pemindahan rencana memungkinkan pemulihan manual |

---

## 7. Urutan & ketergantungan

```
Gate 0 ─► 0.1 ─► 0.2 ─► 0.3 ─► 0.4 ─► 1.1 ─► 1.2
                                        │
                                        ├─► 1.3 ─► 1.4 ─► 1.5 ─► 1.6
                                        │                          │
                                        └──────────────────────────┴─► 1.7 ─► UAT
```

- 1.3 butuh layanan tulis (0.4) dan helper (1.1).
- 1.4–1.6 butuh aturan tulis (1.3).
- 1.7 butuh data kolom dari server (1.1) dan endpoint 1.4–1.5.
- Fase export (rancangan §9) dimulai setelah UAT lulus.
