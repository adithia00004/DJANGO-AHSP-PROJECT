# Verifikasi Implementation Plan Save/Sync

Tanggal verifikasi: 2026-06-08

Dokumen yang diverifikasi: `docs/IMPLEMENTATION_PLAN_SAVE_SYNC_20260608.md`

Acuan pembanding:

- `docs/AUDIT_SAVE_SYNC_PAGES_20260608.md`
- `docs/AUDIT_SAVE_SYNC_VERIFIKASI_ADENDUM_20260608.md`

## Kesimpulan

Implementation plan sudah benar pada arah besar: prioritas `no-store`, static pipeline, Sync LED, watch precision, dan read-after-write sudah sejalan dengan audit.

Namun dokumen plan **belum sepenuhnya selaras** dengan audit terbaru. Ada beberapa amendment wajib sebelum plan dipakai sebagai checklist implementasi.

## Status Per Temuan

| Temuan audit | Status di plan | Verifikasi |
|---|---|---|
| S1 static pipeline / WhiteNoise | Tercakup lewat Fase 0, 1C, dan staging gate | Cukup, tetapi Fase 0 perlu menghindari `git add -A` tanpa review karena worktree sangat dirty. |
| S2 HTML tanpa `no-store` | Tercakup di Fase 1A | Baik. Tambahkan `export_test_view` atau gunakan middleware non-API agar halaman baru ikut otomatis. |
| S3 bootstrap SSR stale | Tercakup di Fase 1B | Baik. Pilihan B1 masuk akal setelah S2 ditutup. |
| S4 output tanpa Sync LED | Sebagian tercakup | Plan menyebut Rekap RAB, Rincian RAB, Jadwal, tetapi **belum menyebut Rekap Kebutuhan**. Ini gap wajib. |
| S5 watch Sync LED kurang tepat | Tercakup di Fase 2B | Baik. |
| S6 dead code `sync_indicator.js` | Tercakup di Fase 2C | Baik. |
| S7 read-after-write belum seragam | Tercakup di Fase 3A/3B | Baik sebagai quality phase. |
| Jadwal typo `le.log(...)` | Belum tercakup | Wajib ditambah. Ini temuan audit 6.2. |
| Legacy jadwal `mode: state.timeScale` | Belum tercakup | Wajib ditambah atau legacy fallback dihapus eksplisit. Ini temuan audit 6.3. |
| Import Validate save false-success | Belum tercakup | Wajib ditambah bila scope plan adalah seluruh hasil audit, bukan hanya `detail_project`. |
| Import Validate belum ada `beforeunload` guard | Belum tercakup | Wajib ditambah bersama false-success save UX. |

## Amendment Wajib

### A1. Fase 0: checkpoint tidak boleh `git add -A` tanpa review

Plan saat ini menyarankan checkpoint working tree. Prinsipnya benar, tetapi command contoh `git add -A` terlalu kasar untuk kondisi repo sekarang karena banyak perubahan lintas app dan untracked.

Revisi yang disarankan:

```text
Review git status, pisahkan perubahan tidak terkait bila perlu, lalu commit checkpoint dengan scope jelas. Hindari `git add -A` tanpa review.
```

### A2. Fase 1A: cakupan `no-store` harus otomatis atau lengkap

Jika memakai decorator manual, tambahkan juga:

- `export_test_view`

Jika memakai middleware non-API untuk path `^/detail_project/`, amendment ini otomatis tertutup dan lebih disarankan.

Acceptance:

```text
Semua URL halaman detail_project yang merender HTML, bukan API/export file, mengirim Cache-Control berisi no-store.
```

### A3. Fase 2A: tambahkan Rekap Kebutuhan

Plan harus berubah dari:

```text
Rekap RAB, Rincian RAB, Jadwal
```

menjadi:

```text
Rekap RAB, Rincian RAB, Rekap Kebutuhan, Jadwal
```

Konsekuensi turunan:

- "template ketiga halaman" menjadi "template empat halaman".
- "client.get(url) ketiga halaman" menjadi "empat halaman".
- trade-off polling 3 halaman menjadi 4 halaman.
- read-only refresh mencakup Rekap Kebutuhan.

### A4. Tambahkan Fase 2D: hygiene Jadwal production dan legacy fallback

Tambahkan subfase:

```text
2D. Hygiene Jadwal production & legacy fallback

- Ganti `le.log(...)` menjadi `console.log(...)` di `kelola_tahapan_grid_modern.html`.
- Update legacy `save_handler_module.js` agar tidak mengirim `mode: state.timeScale` ke backend v2.
- Jika legacy fallback sudah tidak dipakai, hapus/tandai eksplisit agar tidak ada rollback ke kontrak usang.
```

Acceptance:

- Tidak ada `le.log(`.
- Legacy save handler tidak punya `mode: state.timeScale` untuk endpoint v2.
- Planned dan actual progress mengirim `mode` yang benar: `planned` atau `actual`.

### A5. Tambahkan Fase 3C: Import Validate Report save UX

Tambahkan subfase:

```text
3C. Import Validate Report: save benar-benar menunggu server

- Handler tombol Simpan harus `await persistCurrentEdits()` sebelum menampilkan sukses.
- `persistCurrentEdits()` harus melempar error bila fetch gagal atau response bukan OK.
- Tambahkan `beforeunload` guard saat `changes.modified.length + changes.deleted.length > 0`.
- Saat save gagal, tombol Simpan/counter dirty tetap aktif dan user mendapat pesan error.
```

Acceptance:

- Simulasi save gagal tidak boleh menampilkan "Perubahan tersimpan".
- Edit lalu reload/close tab memunculkan guard unsaved changes.

## Koreksi Prioritas Launch

Plan menyatakan jalur minimum launch: Fase 0 -> 1A -> 1C -> 4.

Itu valid untuk risiko utama `detail_project`, tetapi perlu catatan:

```text
Jika workflow Import Validate akan dipakai sebelum launch, Fase 3C harus masuk jalur minimum.
```

S4/S5/S7 tetap quality/accuracy improvement, tetapi S4 untuk output hilir sebaiknya tidak ditunda terlalu jauh karena user bisa mengambil keputusan dari angka stale.

## Verifikasi Teknis Yang Harus Ditambah

Tambahkan test/guard berikut ke plan:

1. `tests_page_cache_headers.py`: mencakup `export_test_view` atau membuktikan middleware menutup semua HTML detail_project non-API.
2. Test template/source untuk empat Sync LED output: Rekap RAB, Rincian RAB, Rekap Kebutuhan, Jadwal.
3. Source guard: tidak ada `le.log(`.
4. Source guard: legacy jadwal tidak mengirim `mode: state.timeScale` ke backend v2.
5. Source guard Import Validate: save handler memakai `await persistCurrentEdits()`.
6. Source guard Import Validate: ada `beforeunload` berdasarkan `changes.modified/deleted`.

## Verdict

Plan **layak sebagai baseline**, tetapi belum layak sebagai checklist final sampai A1-A5 dimasukkan.

Urutan kerja yang disarankan setelah amendment:

1. Fase 0 dengan checkpoint terkurasi.
2. Fase 1A dan 1C.
3. Fase 2D karena murah dan menutup bug nyata.
4. Fase 3C bila import validate dipakai.
5. Fase 2A/2B/2C.
6. Fase 3A/3B.
7. Fase 4 staging gate.

---

## Re-Verifikasi Plan v2

Waktu verifikasi: 2026-06-08 setelah dokumen plan diperbarui.

Hasil:

- A1 sudah masuk: checkpoint terkurasi dan larangan `git add -A` tanpa review.
- A2 sudah masuk: middleware non-API direkomendasikan, decorator fallback mencakup `export_test_view`.
- A3 sudah masuk: Rekap Kebutuhan tercakup bersama Rekap RAB, Rincian RAB, dan Jadwal.
- A4 sudah masuk sebagai Fase 2D: typo `le.log` dan kontrak legacy Jadwal.
- A5 sudah masuk sebagai Fase 3C: `await persistCurrentEdits()` dan `beforeunload`.
- Guard test A1-A5 sudah dicantumkan.
- Jalur minimum launch sudah memberi kondisi eksplisit untuk Import Validate.

Koreksi minor saat re-verifikasi:

- DoD Fase 2A masih menulis "ketiga halaman" walaupun scope sudah empat halaman. Sudah dikoreksi menjadi "keempat halaman".
- Test timestamp Sync LED tidak boleh memaksa `data-initial-*` non-kosong pada project baru. Sudah ditambahkan catatan bahwa nilai boleh kosong kecuali fixture memang membuat data terkait.
- Jadwal perlu dispatch `dp:sync-led-ack` dengan `jadwal: true` setelah save sukses agar LED tidak menandai save dari halaman sendiri sebagai stale. Sudah ditambahkan sebagai guard test dan DoD Fase 2A.

### Verdict Final

Plan v2 sekarang **selaras dengan audit dan layak menjadi checklist implementasi**.

Tidak ada blocker dokumentasi yang tersisa. Risiko implementasi utama yang perlu dijaga:

1. Middleware `no-store` tidak boleh mengenai API/export/unduhan.
2. Sync refresh Jadwal wajib menghormati unsaved progress.
3. Save Jadwal wajib acknowledge Sync LED setelah sukses.
4. Legacy Jadwal harus diperbaiki atau dinonaktifkan secara eksplisit, bukan dibiarkan ambigu.
5. Import Validate tidak boleh membersihkan dirty state sebelum server mengonfirmasi save.
