# Refactor Guide – Penyetaraan Source Workflow

Dokumen ini menjadi panduan tambahan saat menjalankan refactor besar untuk menyetarakan perilaku pekerjaan `source_type`. Gunakan bersamaan dengan `CELAH_PERUBAHAN_SOURCE_ROADMAP.md`.

## Struktur Fase & Checkpoint

| Fase | Fokus | Checkpoint OK | Catatan Test |
|------|-------|---------------|--------------|
| 1. Backend Handler | Service tunggal untuk source change, API response dengan `change_flags`, reset volume/tahapan | - Semua kombinasi source di `test_list_pekerjaan_source_change.py` hijau.<br>- Manual Project test 1–5 mencatat log audit & change-status konsisten. | Sudah diselesaikan 2025-11-15 (log di bawah). |
| 2. Template Frontend | Auto reload setelah source change, dialog baru mengganti toast lama | - Template memuat ulang otomatis (tidak ada 409 lokal).<br>- UX review copywriting dialog. | Sudah diselesaikan 2025-11-16 (autolock + modal konflik). |
| 3. Harga & Rincian | Sinkronisasi lintas halaman berdasarkan `change_flags` & change-status | - Harga blokir form sampai versi diakui.<br>- Rincian menampilkan badge sinkron konsisten.<br>- Badge volume/tahapan aktif. | Sudah diselesaikan 2025-11-16 (Harga lock + badge Rincian). |
| 4. Observability & Otomasi | Audit summary, cron validate, telemetry reload | - Audit mencatat “Source change: X → Y”.<br>- Command `validate_ahsp_data` terjadwal dan log laporan. | **Next** |

## Panduan Eksekusi Per Fase

### Fase 1 – Backend Handler (status: ✅)
1. **Analisis**: inventarisasi entry point (`api_upsert_list_pekerjaan`, `_reset_pekerjaan_related_data`, `_adopt_tmp_into`, `clone_ref_pekerjaan`).
2. **Implementasi**:
   - Tambah `source_change_state` pada `api_upsert_list_pekerjaan`.
   - Tandai job yang butuh reload/volume reset di helper reset/adopt/new job.
   - Sertakan `change_flags` di response JSON.
3. **Testing**:
   - Jalankan `pytest detail_project/tests/test_list_pekerjaan_source_change.py -k source_change` (harus hijau).
   - Manual project test 1–5 (khususnya skenario REF→CUSTOM yang sebelumnya memunculkan alert).
4. **Dokumentasi**:
   - Update `CELAH_PERUBAHAN_SOURCE_ROADMAP.md` (done pada 2025-11-15).

### Fase 2 – Template Frontend
- **Langkah**:
  1. Konsumsi `change_flags` → jika id pekerjaan ada di `reload_job_ids`, otomatis fetch ulang sebelum user bisa input.
  2. Redesign dialog konflik menjadi pilihan jelas: “Muat ulang data terbaru” vs “Timpa perubahan”.
  3. Tampilkan banner “menunggu sinkronisasi” sampai change-status menyamai versi baru.
  4. [2025-11-16] Overlay blocker + modal konflik baru diterapkan; tombol simpan ikut terkunci ketika reload belum selesai.
- **Checkpoint**: manual QA project test 1 (REF only) & test 3 (CUSTOM) memastikan tidak ada konflik lokal.

### Fase 3 – Harga & Rincian
- **Langkah**:
  1. Harga Items membaca change-status & `reload_job_ids` → disable form jika masih menunggu Template.
  2. Rincian memanfaatkan metadata volume reset untuk menampilkan badge “Perlu update volume”.
  3. Integrasikan change-status acknowledgement tombol “Tandai sinkron” agar lintas halaman konsisten.
  4. [2025-11-16] Harga Items menampilkan banner/overlay lock; Rincian AHSP menandai pekerjaan pending volume dan memberi alert di panel kanan.
- **Checkpoint**: Project test 2 (REF_MOD) & test 4/5 (bundle) memastikan daftar harga tidak kosong dan badge muncul sesuai.

### Fase 4 – Observability & Otomasi
- **Langkah**:
  1. Audit trail menulis summary `Source change: {old} -> {new}` dan tag `triggered_by`.
  2. Cron `validate_ahsp_data` + laporan (Slack/email) untuk referensi hilang.
  3. Telemetry: log jumlah reload otomatis vs timpa manual.
- **Checkpoint**: review log harian + laporan cron.

## Catatan Aktivitas (Log)

| Tanggal | Aktivitas | File/Command | Status |
|---------|-----------|--------------|--------|
| 2025-11-15 | Menambahkan `source_change_state`, `change_flags` dan updating helper reset/adopt. | `detail_project/views_api.py` | ✅ |
| 2025-11-15 | Dokumentasi catatan fase 1 di roadmap (`CELAH_PERUBAHAN_SOURCE_ROADMAP.md`). | Dokumentasi | ✅ |
| 2025-11-15 | Pytest subset `detail_project/tests/test_list_pekerjaan_source_change.py -k source_change` | Tests | ✅ |
| 2025-11-15 | Dokumen panduan refactor (`REF_SOURCE_REFACTOR_GUIDE.md`) dibuat. | Dokumentasi | ✅ |
| 2025-11-16 | Template AHSP: banner sinkron, overlay blocker, dan modal konflik baru (konsumsi `change_flags`). | `template_ahsp.html/css/js` | ✅ |
| 2025-11-16 | Harga Items: form lock saat Template belum sinkron + integrasi change-status. | `harga_items.html/css/js` | ✅ |
| 2025-11-16 | Volume/Tahapan & Rincian: badge per pekerjaan + highlight state `volume_reset_jobs`. | `volume_pekerjaan.*`, `kelola_tahapan_grid.*`, `grid_module.js`, `rincian_ahsp.*` | ✅ |

Tambahkan baris baru untuk setiap perubahan/test berikutnya agar histori refactor terdokumentasi rapih.
