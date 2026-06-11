# Checklist Implementasi: Opaque ID Parameter System

**Referensi:** IMPLEMENTATION_PLAN_OPAQUE_ID.md v1.11
**Mulai:** -
**Target selesai:** -

---

## Legenda Status

- `[ ]` Belum dimulai
- `[~]` Sedang dikerjakan
- `[x]` Selesai
- `[!]` Blocked / perlu diskusi
- `[-]` Dibatalkan / tidak relevan

---

## Preflight (Hari 0)

**Fokus:** Persiapan sebelum mulai coding. Pastikan baseline aman.

- [-] Buat branch khusus: `feature/opaque-id` (historical, fase sudah berjalan)
- [-] Commit atau stash semua perubahan dirty di worktree saat ini (historical, fase sudah berjalan)
- [-] Jalankan baseline test: pastikan semua fitur existing berfungsi normal (historical, fase sudah berjalan)
- [-] Backup database production (snapshot) (tracking dipindah ke gate production)
- [-] Freeze scope: tidak ada fitur lain masuk ke branch ini (historical, fase sudah berjalan)
- [-] Review dokumen rencana final (IMPLEMENTATION_PLAN_OPAQUE_ID.md v1.9) (historical, fase sudah berjalan)

---

## Phase 0A: Data Safety -- Export/Import/Copy Computed Params

**Fokus:** Tutup gap existing (bug fix). Deploy independen, backward compatible.

### Backend: Export Computed Parameters

- [x] **0.1** Tambah ProjectComputedParameter di export full backup
  - File: `views_api.py` â†’ `_build_export_data()`, `export_project_full_json()`
  - AC: AC-0.1
- [x] **0.2** Tambah ProjectComputedParameter di export template
  - File: `views_api.py` â†’ `_build_export_data()` template mode
  - AC: AC-0.5

### Backend: Import Computed Parameters

- [x] **0.3** Tambah ProjectComputedParameter di import full backup
  - File: `views_api.py` â†’ `import_project_from_json()`
  - AC: AC-0.2
- [x] **0.4** Tambah ProjectComputedParameter di import template
  - File: `views_api.py` â†’ `_import_template_data()`
  - AC: AC-0.2

### Backend: Copy Service

- [x] **0.5** Tambah `_copy_project_computed_parameters()` di copy service
  - File: `services.py` â†’ tambah method baru + panggil dari copy orchestrator (~line 3418)
  - Termasuk remap expression
  - Referensi: `_copy_project_parameters()` (~line 3718) sebagai template
  - AC: AC-0.3
  - Catatan: implementasi Phase 0 bersifat bridge; final policy Opsi B (regenerate kode target) dieksekusi di Phase 3B item 3.2b

### Phase 0A Gate

- [x] Test: Export full backup â†’ JSON mengandung `project_computed_parameters`
- [x] Test: Import full backup dengan computed â†’ computed params tersedia
- [x] Test: Copy project â†’ computed params ikut ter-copy, expression valid
- [x] Test: Export template â†’ mengandung computed params
  - Verifikasi otomatis: `detail_project.tests_phase0_data_safety` + `detail_project.tests_volume_export_adapter`

---

## Phase 0B: Engine & Schema Preparation

**Fokus:** Persiapan engine dan schema untuk migrasi.

### Frontend: Tokenizer Expose

- [x] **0.6** Expose `tokenize()` di `vol_formula_engine.js`
  - Ubah line 380: `G.VolFormula = { evaluate }` â†’ `G.VolFormula = { evaluate, tokenize }`
  - AC: AC-0.4

### Backend: Python Tokenizer

- [x] **0.7** Buat Python tokenizer mirror untuk migration script
  - File baru: utility module di `detail_project/`
  - Termasuk `tokenize_formula()` dan `remap_expression()`
  - Referensi: pseudocode di IMPLEMENTATION_PLAN_OPAQUE_ID.md Section 6.3

### Schema Definition

- [x] **0.8** Definisikan format export v3.0
  - Bump `export_version` ke `"3.0"` di jalur yang membawa parameter
  - Tambah `project_computed_parameters` section di export output
  - Implementasi `to_version_tuple()` di import parser
  - Tambah fallback legacy key di import handler

### Phase 0 Deployment Gate

- [x] Semua test Phase 0A + 0B pass
- [ ] Deploy Phase 0 ke production (backward compatible, tidak breaking)

---

## Phase 3A: Data Migration (Dijalankan SEBELUM Phase 1 deploy)

**Fokus:** Migrasi data existing ke format opaque.

### DB Migration

- [x] **3.0a** Buat Django migration: tabel `ParameterSequence`
- [x] **3.0b** Buat Django migration: tabel `ParameterMigrationLog`

### Migration Script

- [x] **3.1** Management command: rename kode existing ke opaque format
  - Per-project `@transaction.atomic`
  - Span-based replace pada expression (pakai Python tokenizer dari 0.7)
  - Validasi post-replace: semua identifier merujuk kode valid
  - Log mapping ke `ParameterMigrationLog`
  - Log hasil per-project: {project_id, params_migrated, formulas_updated, status}
  - AC: AC-3.1

### Migration Verification

- [x] Test M1: Basic migration (3 base + 2 computed) â†’ kode berubah, formula valid
- [x] Test M2: Formula multi-ref (`panjang * lebar + panjang`) â†’ `bp_1 * bp_2 + bp_1`
- [x] Test M3: Computed referencing computed â†’ cross-type ref benar
- [x] Test M4: Empty project â†’ sukses tanpa error
- [x] Test M5: Large project (100+ params) â†’ sukses < 10 detik
- [x] Test M6: Substring safety (`abs(a) + a * max(a, b)`) â†’ fungsi tidak rusak
- [x] Test M7: Transaction rollback on invalid formula â†’ project tidak berubah

### Inisialisasi Counter

- [x] **3.1b** Inisialisasi `ParameterSequence.last_num` dari data yang sudah dimigrasikan

### Run Migration

- [x] Backup database sebelum migration
- [ ] Jalankan migration script di staging
- [ ] Verifikasi hasil di staging (spot-check formula, count params)
- [x] Jalankan migration script di production
- [x] Verifikasi hasil di production
  - Bukti eksekusi 2026-02-12: dry-run + real migration `failed: 0`, validasi `NON_OPAQUE_BASE=0`, `NON_OPAQUE_CP=0`, dan `OPAQUE_ID_ENABLED=True`.

---

## Phase 1: Foundation -- Server-Side Opaque ID

**Fokus:** Ganti sistem kode, stabilkan sync. Deploy SETELAH Phase 3A migration.

### Backend: ID Generation

- [x] **1.1** Server-side `_next_opaque_name()` dalam `@transaction.atomic`
  - Model: `ParameterSequence` (sudah dibuat di Phase 3A)
  - `generate_bp_name()`, `generate_cp_name()`
  - AC: AC-1.1, AC-1.2, AC-1.7

### Backend: API Changes

- [x] **1.2** Update API create: server generate kode, return di response
  - File: `views_api.py` â†’ `api_project_parameters()`, `api_project_computed_parameters()`
  - AC: AC-1.1, AC-1.2
- [x] **1.3** Update API sync: regex per-model + per-item warnings
  - `^bp_[1-9][0-9]*$` untuk base, `^cp_[1-9][0-9]*$` untuk computed
  - Return `warnings[]` untuk item invalid (partial success 200, bukan 400)
  - AC: AC-1.10, AC-1.12
- [x] **1.4** Update model `clean()` di kedua model
  - `ProjectParameter`: reject non-`bp_*` dan reject `cp_*`
  - `ProjectComputedParameter`: reject non-`cp_*` dan reject `bp_*`
  - AC: AC-1.11

### Backend: Conflict Detection (409)

- [x] **1.8** Tambah `last_sync_at` di sync payload
  - Endpoint: `api_project_parameters_sync()` (views_api.py:2938)
  - Endpoint: `api_project_computed_parameters_sync()` (views_api.py:3078)
  - Return `synced_at` di response sukses
  - Return 409 jika `updated_at > last_sync_at`
  - AC: AC-1.8

### Frontend: Create Flow

- [x] **1.5** Ubah add parameter flow: POST ke server, terima `bp_N`
  - File: `volume_pekerjaan.js` handler line 1893-1954
  - AC: AC-1.1
- [x] **1.6** Ubah add computed flow: POST ke server, terima `cp_N`
  - File: `volume_pekerjaan.js` handler line 1958-2019
  - AC: AC-1.2

### Frontend: Sync & Render

- [x] **1.7** Fix sync mode: `merge` â†’ `replace`
  - File: `volume_pekerjaan.js` line 2808
  - AC: AC-1.6
- [x] **1.9** Hapus `normalizeParamCode()`, `slugifyName()` dari JS
  - Lines 1584-1600
  - AC: AC-1.9
- [x] **1.10** Ubah render: tampilkan label saja
  - `renderVarTable()`, `renderComputedTable()`
  - AC: AC-1.5
- [x] **1.10b** Refactor `loadParamsFromServer()` agar return Promise
  - Prasyarat untuk localStorage migration snippet
  - File: `volume_pekerjaan.js` line 2856

### Frontend: localStorage Migration

- [x] **1.10c** Implementasi one-time migration flag per-project
  - Key: `opaque_migrated:${projectId}:v2`
  - Snapshot + restore on failure + retry

### Backend: Validation Consistency

- [x] **1.11** Validasi opaque format di semua jalur
  - model clean(), API sync, API create, import, backup restore, copy service
  - AC: AC-1.12

### Phase 1 Testing

- [x] Test C1: Multi-tab create â†’ kode berbeda (`bp_6`, `bp_7`)
- [x] Test C2: Tab A delete, Tab B edit â†’ conflict prompt
- [x] Test C3: Concurrent sync replace â†’ DB serial, tidak corrupt
- [x] AC-1.3: Dua tab bersamaan â†’ no collision
- [x] AC-1.4: Edit label â†’ kode tetap sama
- [x] AC-1.5: Kode tidak ditampilkan di sidebar
- [x] AC-1.6: Hapus + reload â†’ tidak muncul kembali

### Phase 1 Deployment Gate

- [x] Semua test Phase 1 pass
- [x] Deploy Phase 1 ke production (strict opaque mode ON)
  - Sign-off QA manual Gate D lulus (2026-02-12): create base `bp_*`, create computed `cp_*`, conflict sync 409 muncul saat multi-tab, dan parameter terhapus tidak muncul kembali.

---

## Phase 2: Formula Editor -- Chip/Tag UI

**Fokus:** User menulis formula via autocomplete + chip display.

### UI Components

- [x] **2.1** Chip/tag rendering di formula editor
  - Display label, store kode
  - AC: AC-2.1, AC-2.2
- [x] **2.2** Autocomplete: search by label, insert kode sebagai chip
  - Refactor system line 798-830+
  - AC: AC-2.1
- [x] **2.4** Parameter Palette modal
  - Browse semua parameter, klik insert
  - AC: AC-2.4

### Formula Display

- [x] **2.3** `buildFormulaPreview()` mode Label
  - Translate kode â†’ label via exposed tokenizer
  - AC: AC-2.3
- [x] **2.5** Error messages pakai label
  - Format: "Variabel: Panjang Dinding (bp_1) error"
  - AC: AC-2.5

### Race Condition Guard

- [x] **2.6** Guard dirty state tidak ketimpa fetch server
  - `isDirty` flag + prompt resolusi
  - AC: AC-2.6

### Documentation

- [x] **2.7** Update help text + placeholder di `volume_pekerjaan.html`
  - Line 462, 508
  - AC: AC-2.7
- [x] **2.8** Update `PANDUAN_USER.md`
  - Hilangkan referensi kode manual
  - AC: AC-2.8

### Phase 2 Deployment Gate

- [~] Semua AC Phase 2 pass
  - Gunakan checklist manual: `docs/QA_GATE_D_PHASE2_CHECKLIST.md`
- [ ] Deploy Phase 2 ke production

---

## Phase 3B: Import/Export Remap & Backward Compat

**Fokus:** Opsi B -- semua operasi lintas project regenerate kode target, backward compatibility.

### Import Remap

- [x] **3.2** Import remap: kode dari source selalu di-remap ke kode target baru
  - Server-side, dalam transaction via `ParameterSequence` (`_next_opaque_name()`)
  - AC: AC-3.3
  - Verifikasi: full-backup import + template import smoke test lulus (base/computed regenerated, expression formula ter-remap)

- [x] **3.2b** Copy project remap: base + computed selalu generate kode target baru
  - Update `DeepCopyService` agar tidak preserve `bp_N/cp_N` source
  - Token-level remap expression dengan mapping source->target
  - AC: AC-3.3
  - Verifikasi: E2E copy lulus (`bp_*/cp_*` regenerated, expression ter-remap, tidak ada legacy identifier tersisa)
  - Verifikasi tambahan: `VolumeFormulaState` ikut tercopy; `raw` formula `is_fx=true` ikut remap ke kode target
  - Catatan teknis: allocator copy masih bridge (`max+1`) dan akan diganti ke `ParameterSequence` pada Phase 3A/1.1

### Export

- [x] **3.3** Export ke Excel/CSV: formula ditampilkan dengan label
  - Update `volume_pekerjaan_adapter.py` line 116
  - AC: AC-3.4
  - Verifikasi: adapter export menerjemahkan formula `bp_*/cp_*` ke label DB; mode XLSX menjaga formula sebagai teks human-readable (bukan formula Excel mentah) agar tidak fallback ke kode opaque.
  - Hardening edge-case: payload parameter export dinormalisasi (key case-insensitive, dukung shape `{code: {value}}`)

### Backward Compatibility

- [x] **3.4** Import file v1 (kode deskriptif lama) â†’ auto-remap ke opaque
  - Detect via `to_version_tuple(export_version) < (3, 0)`
  - AC: AC-3.2
  - Verifikasi: payload legacy `export_version: 1.0` + key `parameters` berhasil di-remap ke `bp_*`; formula legacy ikut ter-remap

### Backup Restore

- [x] **3.5** Backup restore: computed params + regenerate kode target
  - Full cycle test
  - AC: AC-3.5
  - Verifikasi: full backup (`export_version 3.0`) -> restore/import lulus; base/computed regenerated, expression + volume_formula ter-remap

### Round-Trip Tests

- [x] Test IE1: Export v3.0 â†’ Import v3.0 ke project kosong â†’ semantik identik (kode boleh beda)
- [x] Test IE2: Export v3.0 â†’ Import v3.0 ke project dengan params â†’ remap valid
- [x] Test IE3: Export v1 â†’ Import ke opaque project â†’ auto-remap valid
- [x] Test IE4: Export Excel â†’ human readable formula (label)
- [x] Test IE5: Backup full → Restore → base + computed lengkap, kode regenerated, formula valid
- [x] Test IE6: Copy project â†’ base + computed lengkap, kode regenerated, formula valid

### Catatan Operasional Phase 3B

- Guard `ProgrammingError/OperationalError` untuk copy computed dipertahankan sementara untuk kompatibilitas env yang belum apply migration `0037`; dijadwalkan cleanup setelah semua env confirmed migrated.

---

## Phase 4: Reliability & Polish

**Fokus:** Edge cases, safety, UX polish.

- [x] **4.1** Warning saat hapus parameter yang digunakan di formula
  - Scan formulas sebelum delete
  - AC: AC-4.1
- [x] **4.2** Parameter usage tracking (badge "Dipakai di N formula")
  - AC: AC-4.2
  - Implementasi UI: scan dependency dari formula turunan + formula volume pekerjaan (tokenizer-aware), tampilkan badge usage di tabel Parameter/Formula, dan tampilkan warning breakdown sebelum aksi delete.
- [x] **4.3** Multi-tab conflict UX: prompt resolusi (reload/keep local)
  - Build on Phase 1 basic 409 detection
  - AC: AC-4.3
  - Implementasi: frontend sync menangani response `409 conflict` dengan modal pilihan `Reload` atau `Tetap Lokal`; verifikasi manual E2E C2/C3 lulus.
- [x] **4.4** Izinkan nilai parameter negatif
  - Hapus `MinValueValidator(0)`
  - AC: AC-4.4
  - Implementasi: model `ProjectParameter.value` tanpa MinValueValidator + parser API parameter yang mengizinkan nilai negatif + migration `0038_alter_projectparameter_value`.
  - Verifikasi: test `detail_project.tests_phase4_negative_param` lulus (model create negative + sync endpoint negative).
- [x] **4.5** Rollback drill: test full revert scenario
  - AC: AC-4.5
  - Implementasi: command `rollback_parameters_from_opaque` (reverse mapping berbasis `ParameterMigrationLog`, transaction-safe, dry-run, strict missing-log guard).
  - Implementasi tambahan R1: feature flag `OPAQUE_ID_ENABLED` (env setting) untuk fallback runtime legacy pada create/sync parameter + validasi model.
  - Verifikasi otomatis: `detail_project.tests_phase45_rollback` (round-trip migrate->rollback, dry-run no-write, rollback fail on missing mapping + atomicity, mixed-state rollback via `--allow-missing-log`).

### Rollback Tests

- [x] Test R1: Feature flag off â†’ sistem kembali ke deskriptif
- [x] Test R2: Reverse migration â†’ opaque â†’ deskriptif â†’ formula valid
- [x] Test R3: Mixed state (partial migration) â†’ dual-mode resolve

---

## Post-Implementation

- [x] Susun runbook production: `docs/RUNBOOK_OPAQUE_ID_PRODUCTION.md`
- [x] Susun command status pasca deploy: `python manage.py opaque_post_deploy_status`
- [x] Susun script monitoring harian: `scripts/opaque_daily_monitor.sh`
- [x] Susun template monitoring 7 hari: `docs/OPAQUE_MONITORING_7D_TEMPLATE.md`
- [x] Susun checklist QA Gate D/Phase 2: `docs/QA_GATE_D_PHASE2_CHECKLIST.md`
- [x] Arsipkan `REVIEW_PARAMETER_FORMULA.md` (sudah marked ARSIP)
- [x] Update `IMPLEMENTATION_PLAN_OPAQUE_ID.md` status ke IMPLEMENTED
- [~] Cleanup: hapus `ParameterMigrationLog` data setelah rollback window lewat
  - Command siap pakai: `cleanup_parameter_migration_logs` (support `--dry-run`, `--older-than-days`, `--project-id`)
- [~] Monitor: pantau error rate 1 minggu post-deploy
  - Command harian: `bash scripts/opaque_daily_monitor.sh`

---

## Catatan Urutan Deploy

```
0. Preflight           â†’ branch, backup, baseline test, freeze scope
1. Deploy Phase 0A     â†’ bug fixes computed params (backward compatible)
2. Deploy Phase 0B     â†’ tokenizer expose, schema v3.0 (backward compatible)
3. Phase 3A migration  â†’ data migration (sebelum strict mode)
4. Deploy Phase 1 + 2  â†’ strict opaque mode ON + chip/tag UI
5. Phase 3B            â†’ import/export remap + backward compat
6. Phase 4             â†’ reliability & polish
```
