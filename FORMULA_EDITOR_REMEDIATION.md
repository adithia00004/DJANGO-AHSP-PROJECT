# Formula Editor â€” Checklist Remediasi

> **Sumber:** [FORMULA_EDITOR_AUDIT.md](FORMULA_EDITOR_AUDIT.md)  
> **Dibuat:** 13 Februari 2026  
> **Metode:** Setiap item memiliki referensi audit (Ref), file target, dan acceptance criteria.

---

## Cara Menggunakan Checklist Ini

1. Kerjakan **Sprint 1 (Critical)** terlebih dahulu â€” ini memblokir keamanan production
2. Setiap item yang selesai, tandai `[x]` dan catat tanggal
3. Items dalam satu sprint bisa dikerjakan paralel kecuali ada dependensi (ditandai `â†’`)
4. **Verifikasi** (Sprint V) bisa dikerjakan kapanpun setelah item terkait selesai

---

## Sprint 1 — Critical Security 🔴

> **Target:** Menutup celah keamanan server-side yang memblokir production-readiness.

### 1.1 Validasi Formula `raw` di Server

- [x] **Tambahkan whitelist validator** di `views_api.py` — `api_volume_formula_state()` ✅ 13 Feb 2026
  - Ref: J17, B5, S8
  - File: `detail_project/views_api.py`
  - Acceptance:
    - **Layer 1 — Character whitelist:** hanya `[a-zA-Z0-9_., ()+=\-*/^]` serta whitespace (`\r`, `\n`, `\t`, spasi) karena editor modal multiline
    - **Layer 2 — Token/function whitelist:** setelah lolos character check, parse tokens dan validasi:
      - Identifier harus match `^(bp|cp)_[1-9][0-9]*$` (parameter codes)
      - Function names hanya: `sum`, `min`, `max`, `round`, `avg`, `abs`, `floor`, `ceil`, `pow`
      - Operator dan literal angka sesuai grammar engine
    - Length limit: max 500 karakter per formula
    - Reject dengan HTTP 400 + pesan jelas jika tidak valid
    - Unit test: `=bp_1 * 2` → OK, `=eval("hack")` → 400, `=unknown_func(1)` → 400, formula dengan `\n` → OK

- [x] **Tambahkan unit test validasi formula server-side** ✅ 13 Feb 2026
  - File: `detail_project/tests_formula_server_validation.py` [NEW]
  - Acceptance:
    - Test valid formula → 200
    - Test injeksi `eval()`, `__import__`, `<script>` → 400
    - Test length > 500 chars → 400
    - Test empty string → OK (clear formula)

---

## Sprint 2 — High Priority 🟠

> **Target:** Memperkuat keamanan governance, memperbaiki z-index, dan menulis unit test engine.

### 2.1 Unit Test `vol_formula_engine.js`

- [x] **Tambah test suite + integrasi ke CI** (Vitest runner sudah ada via `test:frontend` di package.json) ✅ 13 Feb 2026
  - Ref: T2
  - File: `detail_project/static/detail_project/js/__tests__/vol_formula_engine.test.js` [NEW]
  - Acceptance:
    - Minimal 20 test cases:

      | Kategori | Contoh Input | Expected |
      |----------|-------------|----------|
      | Angka biasa | `=42` | 42 |
      | Operasi dasar | `=2 + 3 * 4` | 14 |
      | Parentheses | `=(2 + 3) * 4` | 20 |
      | Nested parens | `=((1 + 2) * (3 + 4))` | 21 |
      | Fungsi | `=sum(1, 2, 3)` | 6 |
      | Division by zero | `=1 / 0` | Infinity / error |
      | Formula kosong | `=` | Error |
      | Hanya `=` + spasi | `=   ` | Error |
      | Token invalid | `=bp_1 + @#$` | Error |
      | Identifier unknown | `=xyz_999` | Error (unknown var) |

### 2.2 Guard XSS Governance

- [x] **Tambahkan allowlist callsite guard** untuk `innerHTML` ✅ 13 Feb 2026
  - Ref: S3
  - File: `detail_project/tests_formula_ui_regressions.py` (extend)
  - Acceptance:
    - Maintain allowlist fungsi nyata di `volume_pekerjaan.js` yang memang menggunakan `innerHTML`, minimal: `showActionToast`, `renderVarTable`, `renderComputedTable`, `showExportMenu`, dan callsite render dropdown/suggest yang relevan.
    - Setiap fungsi di allowlist harus punya **dedicated test** yang memverifikasi `escapeHtml()` dipanggil pada semua input dinamis.
    - Fungsi baru yang menggunakan `innerHTML` tanpa masuk allowlist -> test gagal.
    - Alternatif: eslint rule custom yang cek source taint (variabel dari user input -> wajib melalui `escapeHtml` sebelum masuk template literal).

### 2.3 Fix Z-Index Help Modal & FAB

- [x] Fix `#vpFormulaHelpModal` z-index: `1060` → `13060` ✅ 13 Feb 2026
  - Ref: Z-Index Map, R5
  - File: `detail_project/static/detail_project/css/volume_pekerjaan.css`
  - Acceptance: Help modal muncul di atas topbar (z-index 12044)

- [x] Fix `.vp-fab-container` z-index: `1030` → `12032` ✅ 13 Feb 2026
  - Ref: Z-Index Map, R5
  - File: `detail_project/static/detail_project/css/volume_pekerjaan.css`
  - Acceptance: FAB tetap visible di atas konten tapi di bawah modals

### 2.4 Import File Size Limit

- [x] Tambahkan file size check di `handleUnifiedImport()` ✅ 13 Feb 2026
  - Ref: IO6, P4, S7
  - File: `detail_project/static/detail_project/js/volume_pekerjaan.js` → `handleUnifiedImport()`
  - Acceptance:
    - File > 5MB → `TOAST.warn()` + abort
    - Bisa di-override via constant `MAX_IMPORT_SIZE_BYTES`

### 2.5 WCAG AA Color Contrast Verification

- [x] Verifikasi chip color contrast ratio ✅ 13 Feb 2026
  - Ref: A6, R6
  - Tool: Chrome DevTools → Inspect → color picker contrast checker
  - Acceptance: Semua chip text memenuhi contrast ratio ≥ 4.5:1
  - Fallback colors darkened for guaranteed WCAG AA compliance:
    - Light: `#3d5a8a` (5.2:1), `#1e4a96` (6.8:1), `#2d5e3f` (6.1:1), `#145939` (8.0:1)
    - Dark: `#60c0db` (7.5:1), `#1abadd` (7.0:1), `#44a872` (5.3:1), `#219660` (4.6:1)
    - Errors: all ≥ 4.5:1

---

## Sprint 3 — Medium Priority 🟡

> **Target:** Meningkatkan UX, resiliensi, dan maintainability.

### 3.1 Unsaved Changes Warning

- [x] Intercept modal close jika ada perubahan belum di-apply ✅ 13 Feb 2026
  - Ref: H2, H4, J11, R7
  - File: `volume_pekerjaan.js` → **`hide.bs.modal`** handler (pre-close event, bukan `hidden.bs.modal` yang post-close)
  - Referensi kode saat ini: L3391 (`hidden.bs.modal` cleanup)
  - Acceptance:
    - Listen pada `hide.bs.modal` (terjadi **sebelum** modal tertutup → bisa `preventDefault()`)
    - Jika draft berbeda dari state saat open → `e.preventDefault()` + tampilkan `confirmModal("Perubahan belum diterapkan. Tutup?")`
    - Jika user confirm → panggil `modal.hide()` ulang dengan flag bypass
    - Jika user cancel → batal close, modal tetap terbuka
    - `data-bs-backdrop="static"` ditambahkan saat draft dirty.
    - Backdrop harus dikembalikan ke mode default saat state sudah clean (setelah apply/discard) agar modal tidak tetap "terkunci".

### 3.2 Import Undo / Snapshot

- [x] Simpan snapshot parameter sebelum import replace ✅ 13 Feb 2026
  - Ref: IO12, R8
  - File: `volume_pekerjaan.js` → `handleUnifiedImport()`
  - Acceptance:
    - Sebelum replace: `previousVars = { ...variables }`, `previousLabels = { ...varLabels }`
    - Setelah import: tampilkan toast "Parameter diimport" dengan tombol **Undo**
    - Undo → restore `previousVars` + `previousLabels`, re-render

### 3.3 Computed Params Export/Import

- [x] Sertakan computed parameters (`cp_N`) dalam export/import ✅ 13 Feb 2026
  - Ref: IO9, R9
  - File: `volume_pekerjaan.js` → exporters + importers
  - Acceptance:
    - JSON export: tambahkan key `computed_parameters`
    - CSV export: section kedua atau file terpisah
    - Import: handle `computed_parameters` key, validate `cp_N` format

### 3.4 `reevaluateAllFormulas()` Batching

- [x] Batch evaluasi menggunakan `requestAnimationFrame` chunks ✅ 13 Feb 2026
  - Ref: P1, R10
  - File: `volume_pekerjaan.js` → `reevaluateAllFormulas()`
  - Acceptance:
    - Proses max 50 rows per frame
    - Tidak ada visible jank pada project dengan 500+ baris
    - Progress indicator opsional

### 3.5 ARIA pada Inline Validation Errors

- [x] Tambahkan `aria-live="polite"` pada container error inline ✅ 13 Feb 2026
  - Ref: A8, R11
  - File: `volume_pekerjaan.js` → `setInputValidationError()`
  - Acceptance: Screen reader mengumumkan error saat muncul

### 3.6 Retry Logic pada Network Error

- [x] Implementasi retry dengan exponential backoff pada `syncFormulaStateToServer()` ✅ 13 Feb 2026
  - Ref: J21, R12
  - File: `volume_pekerjaan.js` → sync functions
  - Acceptance:
    - Max 3 retries: 1s → 2s → 4s
    - Setelah 3 gagal → `TOAST.err()` + manual retry button
    - Skip retry pada HTTP 400/409 (bukan transient error)

### 3.7 Integration / E2E Tests

- [x] Tulis minimal 1 integration test untuk formula lifecycle ✅ 13 Feb 2026
  - Ref: T3, T4, R13
  - File: `detail_project/tests_formula_integration.py` [NEW] atau browser test
  - Acceptance:
    - Flow: create param → set formula → save → reload → verify formula persisted

---

## Sprint 4 — Low Priority 🔵

> **Target:** Polish dan edge-case fixes.

### 4.1 `color-mix()` CSS Fallback

- [x] Tambahkan fallback plain color sebelum `color-mix()` ✅ 13 Feb 2026
  - Ref: C5, R14
  - File: `volume_pekerjaan.css`
  - Acceptance: Chip tetap readable di Safari < 16.4

### 4.2 `hideSuggest` Delay

- [x] Naikkan delay dari 120ms → 200ms ✅ 13 Feb 2026
  - Ref: J4, R15
  - File: `volume_pekerjaan.js`
  - Acceptance: Suggest tidak tertutup prematur saat klik item di device lambat

### 4.3 Dark Mode Visual Verification

- [x] Verifikasi visual semua elemen formula editor dalam dark mode ✅ 13 Feb 2026
  - Ref: C6, R16
  - Acceptance: Semua teks readable, chip visible, error highlight kontras cukup
  - Evidence screenshots:
    - `docs/evidence/formula_editor_dark_mode/volume_page_dark.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark_success.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark_chip_success.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark_error.png`

---

## Sprint V — Verifikasi & Reproduksi

> **Items yang memerlukan pengujian manual, bisa dikerjakan paralel.**

- [x] **H1 — Reproduksi stacking context trap** ✅ 13 Feb 2026
  - Semua `transform`/`filter`/`will-change` hanya pada child elements (buttons, FAB, chips)
  - `#vpFormulaEditorModal` adalah direct child `<body>` — tidak ada stacking context trap
  - Hasil: **Not an issue**

- [x] **C6 — Dark mode visual check** ✅ 13 Feb 2026
  - Toggle dark mode → buka formula editor → screenshot
  - WCAG AA fallback colors sudah diimplementasi (Sprint 2.5)
  - Evidence:
    - `docs/evidence/formula_editor_dark_mode/volume_page_dark.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark_success.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark_chip_success.png`
    - `docs/evidence/formula_editor_dark_mode/formula_modal_dark_error.png`
  - Hasil: **Pass** (teks terbaca, chip terlihat jelas, error highlight kontras cukup).  
    Catatan minor: toast sinkronisasi di kanan atas dapat overlap area header modal saat muncul.

- [x] **A9 — ARIA toast standardisasi** ✅ 13 Feb 2026
  - `#vp-toasts` multi-toast container: ditambahkan `aria-live="polite"` + `role="status"`
  - `#vp-toast` single toast: sudah ada `aria-live="assertive"` + `role="status"`
  - JS-created wrapper (L323): sudah ada `aria-live="assertive"`
  - Hasil: **Fixed & Standardized**

- [x] **E6 — Error boundary audit** ✅ 13 Feb 2026
  - 50+ event listeners diaudit
  - Critical handlers (save, import, network): semua sudah ada try/catch
  - Simple UI handlers (click nav, toggle): tidak perlu error boundary
  - Hasil: **Adequate coverage**

- [x] **U6 — Multi-level undo evaluation** ✅ 13 Feb 2026
  - Formula editor: 1-level per-row via `formulaUndoById` (Map) — cukup untuk use case
  - Batch save: multi-level via `undoStack[]` + hotkey `Ctrl+Alt+Z`
  - Import: 1-level via snapshot + Undo toast button
  - Keputusan: **1-level formula undo sufficient. Batch undo already multi-level.**

---

## Progress Tracker

| Sprint | Total Items | Selesai | Progress |
|--------|------------|---------|----------|
| 1 — Critical | 2 | 2 | ██████████ 100% |
| 2 — High | 6 | 6 | ██████████ 100% |
| 3 — Medium | 7 | 7 | ██████████ 100% |
| 4 — Low | 3 | 3 | ██████████ 100% |
| V — Verifikasi | 5 | 5 | ██████████ 100% |
| **Total** | **23** | **23** | **██████████ 100%** |


