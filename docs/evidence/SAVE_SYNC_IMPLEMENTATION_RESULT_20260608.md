# Save/Sync Implementation Result - 2026-06-08

## Scope Implemented

- Fase 0: baseline lokal dan checkpoint terkurasi.
  - Checkpoint tag: `pre-sync-hardening-20260608`
  - Commit object: `8495de6e73e16606f62c99de70a37973de7d7b8c`
  - Baseline detail: `docs/evidence/SAVE_SYNC_BASELINE_20260608.md`
- Fase 1: dynamic HTML `detail_project` diberi `Cache-Control: private, no-cache, no-store, must-revalidate`; API/download/non-HTML tidak disentuh.
- Fase 1: bootstrap SSR diberi kontrak freshness berbasis middleware `no-store`.
- Fase 1: Docker build tidak lagi menelan error `collectstatic`.
- Fase 2: Sync LED mencakup `rekap_rab`, `rincian_rab`, `rekap_kebutuhan`, dan `jadwal_pekerjaan`.
- Fase 2: watch policy diperketat:
  - `template_ahsp`: `pekerjaan,harga`
  - `volume_pekerjaan`: `pekerjaan`
  - halaman rekap/read-only: full reload saat sinkron.
  - `jadwal_pekerjaan`: refresh via app dan tetap menjaga guard unsaved changes.
- Fase 2: `sync_indicator.js` dan partial `_sync_indicator.html` legacy dihapus dari jalur aktif.
- Fase 2: Jadwal production typo `le.log` diperbaiki; legacy save handler tidak lagi mengirim `mode: state.timeScale`.
- Fase 2: save Jadwal mengirim `dp:sync-led-ack` untuk menghindari false positive LED setelah save.
- Fase 2: Vite `outDir` diperbaiki menjadi path absolut. Konfigurasi lama menulis hasil build ke direktori bersarang sehingga manifest aktif tetap menunjuk bundle lama.
- Fase 2: aset production Jadwal dibangun ulang; manifest aktif menunjuk `assets/js/jadwal-kegiatan-C9Ct7gjz.js`.
- Fase 3: Template AHSP memakai optimistic lock detail-scoped (`client_updated_at`) dengan respons `409 Conflict` untuk token usang.
- Fase 3: frontend Template AHSP menyediakan pilihan Muat Ulang atau Timpa dengan konfirmasi kedua.
- Fase 3: Import Validate Report menunggu `persistCurrentEdits()` sebelum menandai sukses, melempar error saat server gagal, menahan pagination saat persist gagal, dan memasang `beforeunload` guard.

## Deliberately Deferred

- Fase 3B standardisasi util save lintas halaman ditunda. Bagian ini opsional di plan dan berisiko regresi karena menyentuh banyak page yang sudah punya kontrak save masing-masing.
- Verifikasi runtime staging/browser manual belum dilakukan dari sesi ini. Yang sudah dilakukan adalah verifikasi lokal via test/source/build checks.

## Verification Commands

### Passed

- `python manage.py check` -> OK.
- `python manage.py test detail_project.tests_page_cache_headers detail_project.tests_volume_pekerjaan_save_api detail_project.tests_change_status_sync --keepdb -v 1` -> 18 tests OK.
- `python manage.py test detail_project.tests_change_status_sync detail_project.tests_formula_ui_regressions detail_project.tests_page_cache_headers --keepdb -v 1` -> 50 tests OK.
- Targeted Fase 3:
  - stale detail token -> `409`
  - current detail token -> `200`
  - force overwrite -> `200`
  - frontend/source guards -> OK
  - Import Validate source guards -> OK
- `node --check` for touched JS:
  - `sync_led.js`
  - `template_ahsp.js`
  - `volume_pekerjaan.js`
  - `harga_items.js`
  - `src/jadwal_kegiatan_app.js`
  - `src/modules/core/save-handler.js`
  - `jadwal_pekerjaan/kelola_tahapan/save_handler_module.js`
- `python manage.py collectstatic --noinput --clear --dry-run` -> OK.
- `npm run build` -> OK; bundle production aktif memuat `dp:sync-led-ack`, `dp:sync-refresh-request`, dan handler refresh error baru.
  - Warning non-blocking: entry Jadwal sekitar 1.1 MB sebelum gzip (sekitar 305 KB gzip), melewati threshold warning Vite 500 KB.
- `python manage.py makemigrations detail_project --check --dry-run` -> OK.
- Targeted `git diff --check` for touched implementation files -> OK.

### Full Suite Result

- `python -m pytest detail_project/ -q`
  - Result: `258 passed, 5 failed, 4 warnings`.
  - Baseline before implementation was `246 passed, 6 failed, 4 warnings`.
  - Remaining failures are baseline/domain issues:
    - 3 parameter decimal precision expectations (`22.000` vs `22.000000000000`, negative values likewise).
    - 2 Template AHSP tests expecting user-provided `kode` to remain literal, while current item SSOT policy auto-generates item code.
- `python -m pytest referensi/tests -q`
  - Result: `90 passed, 1 failed, 4 warnings`.
  - Failure: `ReferensiImportPermissionTests.test_import_endpoints_block_user_without_permissions` expects login redirect but actual response is pricing/subscription redirect for an expired/no-permission user.

### Environment/Baseline Constraints

- Running `pytest detail_project/` and `pytest referensi/tests` in parallel caused SQLite test DB lock:
  - `PermissionError: test_pytest_db.sqlite3 is being used by another process`.
  - Rerunning `detail_project` alone produced the valid result above.
- `python manage.py makemigrations referensi --check --dry-run` reports a pending migration:
  - `referensi/migrations/0024_alter_ahspimportstaging_segment_type.py`
  - This is unrelated to the save/sync changes but is a staging gate item.
- Whole-repo `git diff --check` still has known baseline whitespace issues documented in `SAVE_SYNC_BASELINE_20260608.md`; targeted diff-check for touched implementation files is clean.

## Staging Gate

Before launch, run these in staging:

1. Build image using production assets and fail-fast `collectstatic`.
2. Open these pages and confirm latest saved data is shown after reload:
   - List Pekerjaan
   - Volume Pekerjaan
   - Template AHSP
   - Harga Items
   - Rincian AHSP
   - Rekap RAB
   - Rincian RAB
   - Rekap Kebutuhan
   - Jadwal Pekerjaan
   - Import Validate Report
3. Confirm `Cache-Control` on dynamic `detail_project` HTML contains `no-store`.
4. Confirm Template AHSP two-tab conflict:
   - tab A saves
   - tab B with stale token receives conflict dialog
   - dismiss does not overwrite
   - explicit Timpa overwrites only after second confirmation.
5. Confirm Import Validate offline/500 save failure does not show success and blocks pagination/reload with unsaved edits.
