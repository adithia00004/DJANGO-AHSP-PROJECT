# Rekomendasi Perbaikan Roadmap Option C

## Latar Belakang
Roadmap **Option C (Refactor-First)** menargetkan arsitektur dengan satu sumber kebenaran berbasis `PekerjaanProgressWeekly`, StateManager tunggal di frontend, serta integrasi chart dan grid yang bebas duplikasi. Namun hasil pengujian terakhir menunjukkan kegagalan penyimpanan dan ketidaksinkronan arsitektur yang berpotensi merusak performa serta maintainability. Dokumen ini merangkum rekomendasi konkret untuk menyelaraskan roadmap dengan implementasi aktual.

## Ringkasan Masalah Penting
- **Payload frontend tidak sesuai skema baru.** `save-handler.js` (modules/core) masih mengirim field `proportion` generik, padahal roadmap sudah menghapus kolom tersebut dan menggantinya dengan `planned_proportion`/`actual_proportion`.
- **Backend masih bergantung pada field yang dihapus.** `sync_weekly_to_tahapan`, `api_reset_progress`, serta helper migrasi masih membaca/menulis `proportion`, sehingga setiap eksekusi berpotensi melempar `FieldError`.
- **Tooling & tes tidak merepresentasikan target arsitektur.** Admin, fixtures, dan `test_api_v2_weekly.py` masih memeriksa `.proportion`, sehingga bug serupa mudah lolos.
- **Integrasi storage belum efisien.** Setiap save memicu regenerasi penuh `PekerjaanTahapan`, membuat latensi tinggi dan bertentangan dengan prinsip canonical storage.

### Update 2025-11-28
- API v2 (`api_assign_pekerjaan_weekly`) sekarang menerima field `planned_proportion`/`actual_proportion` langsung, dengan fallback ke `proportion` demi kompatibilitas. SaveHandler modern juga mengirim field tersebut sehingga payload selaras dengan Option C.
- Semua helper kunci (`progress_utils`, `exports/jadwal_pekerjaan_adapter.py`, admin reset) tidak lagi membaca kolom `proportion` yang sudah dihapus dari schema.
- Langkah selanjutnya: migrasikan sisa tooling/tests yang masih mengakses `.proportion` dan lanjutkan pekerjaan EVM (cost fields) sebelum Phase 5.3.
- Tahap 5.3 (EVM) dilanjutkan: field `budgeted_cost`/`actual_cost` ditambahkan, endpoint `kurva-s-harga` kini menyajikan PV/EV/AC + SPI/CPI/EAC sehingga cost view Kurva S bisa menampilkan dashboard EVM.
- Update 5.3 lanjut: endpoint `assign_weekly` kini mengembalikan `saved_assignments` (alias `assignments`) dan frontend baru memunculkan toggle **Cost** saat berada pada mode realisasi sehingga user dapat mengisi `actual_cost` mingguan langsung dari grid AG dengan payload `actual_cost` yang tervalidasi sebelum disimpan. Data loader/StateManager juga menyimpan nilai biaya tersebut sehingga Kurva S cost view dan audit panel membaca sumber yang sama.

### Update 2025-12-01
- Kurva S cost view kini otomatis mengonsumsi endpoint `/detail_project/api/v2/project/<id>/kurva-s-harga/` dengan path yang benar sehingga grafik biaya langsung muncul tanpa interaksi tambahan.
- Legend dan tooltip cost view disederhanakan menjadi dua garis: **Rencana (PV)** dan **Realisasi (AC)**. Garis EV dihapus dari tampilan untuk menghindari kebingungan pengguna, namun struktur data EV masih tersedia untuk analitik lanjutan.
- Save feedback sudah menjumlahkan `created_count + updated_count` sehingga toast “0 perubahan” hanya muncul bila memang tidak ada perubahan yang tersimpan.
- **Checkpoint berikutnya**: (1) dokumentasikan perilaku baru di client guide/Jadwal Kegiatan README, (2) tambahkan smoke test front-end agar default cost toggle & legend naming tidak regresi, (3) selesaikan investigasi error Gantt `format(... '11')` sebelum rilis publik.

## Analisa Mendalam per Layer

### Frontend (AG Grid + StateManager + SaveHandler)
- **StateManager** (`static/detail_project/js/src/modules/core/state-manager.js`) sudah menyimpan data per-mode, tetapi pipeline penyimpanan masih membaca `modifiedCells` dan langsung mengemasnya menjadi `{pekerjaan_id, proportion}`. Hal ini memutus janji “mode-aware save” pada Phase 2E.1.
- **Time metadata**: `time-column-generator.js` dan `grid-renderer.js` masih meneruskan `tahapan_id`/`col_*` yang tadinya dibutuhkan API v1. Untuk API v2, cukup `week_number` + rentang tanggal. Metadata berlebih memperbesar payload ±35% (diukur dari 2 cell percobaan).
- **Event chaining** (`ag-grid-setup.js` → `jadwal_kegiatan_app.js`) sudah memanggil chart update secara sinkron. Ketika save gagal, chart sudah menampilkan data baru padahal DB tidak tersimpan. Diperlukan rollback visual (StateManager.setCellValue → revert) agar UX konsisten.

### Backend & Storage
- **API v2** (`views_api_tahapan_v2.py:46-376 & 820-876`) sudah memiliki logika mode planned/actual, tetapi:
  - `defaults` pada `get_or_create` mengisi `planned_proportion`/`actual_proportion` benar, sementara update block lupa menghapus assignment `record.proportion`.  
  - `api_reset_progress` dan `sync_weekly_to_tahapan` tetap membaca/menulis `record.proportion`, menyebabkan exception ketika field benar-benar dihapus oleh migration Phase 0.
- **Helper konversi** (`progress_utils.py:179-487`) masih mengagregasi `weekly_rec.proportion`. Begitu schema dibersihkan, perhitungan tahapan akan selalu 0 sehingga UI lama tidak mendapatkan data. Perlu helper `get_weekly_value(weekly_rec, mode)` dan parameter mode diteruskan sampai ke `sync_weekly_to_tahapan`.
- **Migrasi & rollback** di roadmap (migration 0043) belum dieksekusi di codebase aktif (masih ada field di admin/tests). Tanpa menjalankan migrasi ini segera, struktur DB antar environment berbeda dan raw SQL manual (mis. `SELECT proportion`) masih dijalankan oleh script diagnose.

### Tooling, Testing & Operasional
- **Admin panel** (`admin.py:96-118`) memuat field `proportion`. Ketika staff menyimpan entri, Django akan gagal dengan FieldError. Ini menunjukkan jalur QA internal pun tidak siap.
- **Test suite** (`tests/test_api_v2_weekly.py`, `tests/test_models_weekly.py`, `tests/test_phase_2e1_dual_fields.py`) masih membuat objek `PekerjaanProgressWeekly(proportion=Decimal(...))`. Walaupun DB belum dimigrasikan, test ini memperkuat ketergantungan ke field lama dan tidak menangkap bug SaveHandler.
- **Dokumentasi operasional** (`JADWAL_KEGIATAN_CLIENT_GUIDE.md`) sudah menyebut `mode: planned/actual`, tetapi tidak mencantumkan contoh payload / expected response terbaru. User QA tidak memiliki acuan ketika memverifikasi.

### Performa & Observability
- **Sync tahapan** dieksekusi pada setiap save → `PekerjaanTahapan.objects.filter(...).delete()` + bulk create. Pada proyek dengan 2.000 baris x 52 minggu, proses ini bisa menghapus & menulis >100k rows per klik, menembus batas <250 ms yang diinginkan roadmap.
- **Monitoring** belum ada. Tidak ada tracing/log metrics untuk `/assign-weekly/`, sehingga kegagalan 500 baru terlihat lewat console browser. Aplikasi perlu minimal logging ke `structlog`/Sentry + counter metrik (durasi, jumlah assignment, mode).
- **Caching**: StateManager sudah menyatukan state, tetapi API tidak memanfaatkan caching/konsistensi (mis. ETag) saat load assignments. Integrasi caching bisa menurunkan waktu load (target <300 ms) sesuai roadmap Option C.

## Rekomendasi Per Area

### 1. Frontend (State & Save Handler)
1. Terapkan hotfix dari _BUGFIX_HOTFIX_SAVE_API.md_: definisikan `const proportionField = progressMode === 'actual' ? 'actual_proportion' : 'planned_proportion';` lalu gunakan property dinamis `[proportionField]`. Pastikan `_buildPayload()` tidak lagi mem-attach `proportion`.
2. Sertakan hanya metadata yang benar-benar dibutuhkan API (ID pekerjaan, `week_number`, tanggal minggu bila tersedia). Kolom tahapan legacy sebaiknya di-drop untuk mengurangi beban payload dan mencegah kebingungan backend.
3. Tambahkan tes unit (Jest/Vitest) untuk memastikan `saveChanges()` pada kedua mode menghasilkan field yang benar serta memverifikasi bahwa payload tidak mengandung `proportion`. Integrasikan ke pipeline Vite agar build gagal bila tes absen.
4. Implementasikan mekanisme rollback visual: bila fetch gagal, panggil `stateManager.rollbackCellValue(pekerjaanId, cellKey)` (tambahkan fungsi baru jika perlu) dan tampilkan toast “Data batal disimpan”.

### 2. Backend (API & Utilitas)
1. Refactor `sync_weekly_to_tahapan` dan helper konversi minggu agar bekerja terhadap field eksplisit (`planned_proportion`/`actual_proportion`). Buat helper `get_progress_value(wp, mode)` agar fungsi existing cukup meneruskan parameter mode.
2. Perbarui `api_reset_progress`, `api_get_project_assignments_v2`, `api_regenerate_tahapan_v2`, serta migration helper reverse untuk menghapus seluruh referensi `record.proportion`. Bila perlu, tambahkan `@property def proportion(self): return self.planned_proportion` sebagai guard sementara dan beri TODO untuk dihapus setelah seluruh konsumen bersih.
3. Pastikan tidak ada bulk-create/bulk-update yang masih mengirim `proportion=`. Gunakan `update_fields=['planned_proportion']` dlsb agar query lebih ringan dan jelas di log audit.
4. Jalankan migration penghapusan kolom di lingkungan dev/staging segera, lalu tambahkan “schema drift check” (mis. `python manage.py showmigrations | grep detail_project`) ke Step Definition Phase 0.

### 3. Tooling & Testing
1. Hilangkan field `proportion` dari Django admin (`PekerjaanProgressWeeklyAdmin.fieldsets`) supaya UI admin tidak mem-break jika staf mencoba menyimpan data.
2. Update semua fixtures/tests (`test_api_v2_weekly.py`, `test_models_weekly.py`, `test_weekly_canonical_validation.py`, dsb.) agar memeriksa `planned_proportion`/`actual_proportion`. Tambahkan scenario e2e: POST planned, POST actual, GET assignments → verifikasi payload response sesuai.
3. Masukkan checklist “tes save planned & actual” ke `REFACTOR_PROGRESS_TRACKER.md` agar menjadi ritual QA sebelum fase ditandai selesai. Tambahkan juga item “API schema vs frontend payload” sebagai quality gate.
4. Dokumentasikan payload terbaru di `JADWAL_KEGIATAN_CLIENT_GUIDE.md` lengkap dengan contoh request/response dan error umum (periksa `Invalid field name`), sehingga QA dan pengguna eksternal punya acuan.

### 4. Kinerja & Integrasi Storage
1. Hentikan regenerasi penuh `PekerjaanTahapan` setiap kali save. Gunakan strategi incremental (update hanya minggu yang berubah) atau jadwalkan sinkronisasi melalui background task/management command.
2. Evaluasi ulang kebutuhan menyimpan TahapPelaksanaan auto-generated. Jika hanya view sementara, cukup rebuild saat user mengganti mode atau jalankan caching di sisi frontend (StateManager sudah menyimpan assignmentMap).
3. Profil endpoint `/assign-weekly/` setelah refactor; tetapkan target latensi (mis. <250 ms untuk 200 assignment) sebagaimana target performa di roadmap.
4. Pasang logging terstruktur (timing, jumlah assignment, mode) di API v2 serta instrumentation sederhana (mis. Prometheus counter) agar bottleneck mudah terlihat sebelum pengguna melapor.

## Roadmap Eksekusi Terperinci

| Fase | Durasi | Fokus | Task Detail | Output/Kriteria Sukses |
|------|--------|-------|-------------|------------------------|
| **Phase 0A** | Hari 0 | Hotfix kritikal | Implementasi perubahan SaveHandler + patch API `_sendToServer`, tambahkan tes frontend minimal | Payload sesuai mode, tes unit lulus, tidak ada `proportion` di request |
| **Phase 0B** | Hari 1-2 | Cleanup schema | Jalankan migration drop `proportion`, refactor admin/test, tambahkan property guard sementara | `python manage.py check` & `pytest detail_project/tests/test_api_v2_weekly.py` lulus tanpa referensi legacy |
| **Phase 1A** | Hari 3-4 | Refactor utilitas | Update `progress_utils.py`, `sync_weekly_to_tahapan`, `api_reset_progress` agar mode-aware | Regenerasi tahapan berjalan tanpa error, data planned/actual terbaca |
| **Phase 1B** | Hari 5 | QA + dokumentasi | Update client guide, tracker QA, jalankan regression scenario (planned + actual) | Checklist QA ditandatangani, screenshot bukti disimpan |
| **Phase 2** | Minggu 2 | Performa & observability | Implement incremental sync / background job, tambahkan logging & profiling, susun baseline metrik | Latensi save <250 ms pada dataset contoh, metrik tercatat |

## Checklist Validasi Akhir
1. **Schema parity:** `python manage.py showmigrations detail_project` menunjukkan semua migrasi terbaru sudah diterapkan pada dev/staging/production.
2. **Frontend payload audit:** Network tab menampilkan field `planned_proportion`/`actual_proportion` sesuai mode, tanpa `proportion`.
3. **Backend smoke test:** `pytest detail_project/tests/test_api_v2_weekly.py::TestAssignWeeklyProgress::test_assign_weekly_progress_success` berjalan dan memeriksa field baru.
4. **Performance sample:** Jalankan 200 assignment via script (mis. `test_api_v2_weekly.py` parametris) dan catat response time <250 ms.
5. **Monitoring hook:** Endpoint `/assign-weekly/` log minimal `project_id`, `mode`, `assignment_count`, `duration_ms`.

Checklist ini wajib dipenuhi sebelum roadmap Option C dinyatakan kembali on-track.

## Prioritas Implementasi
1. **Blokir Data Loss (Hari 0‑1)**  
   - Perbaiki SaveHandler + API agar field cocok.  
   - Tambahkan tes otomatis minimal untuk regressi ini.
2. **Bersihkan Backend Dependencies (Hari 2‑3)**  
   - Refactor utilitas & admin/tests dari referensi `proportion`.  
   - Re-run migrasi verifikasi (schema sync + pytest).
3. **Optimasi Integrasi & Performa (Hari 4‑5)**  
   - Rancang ulang mekanisme sync tahapan → weekly.  
   - Tambahkan monitoring latensi & ukuran payload untuk memastikan roadmap “<300 ms load time” tercapai.

## Penutup
Dengan menerapkan langkah di atas, roadmap Option C kembali selaras dengan implementasi: satu sumber data weekly, frontend-backend terintegrasi, serta jalur penyimpanan yang stabil dan mudah diuji. Dokumentasikan setiap perubahan di tracker fase agar tim memiliki visibilitas dan risiko data loss tidak terulang.
