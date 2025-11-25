# Phase 2D – Input Experience Readiness Tracker

_Last updated: 2025-11-24 – maintained while refactoring Jadwal Kegiatan AG Grid UI._

## 1. Current Snapshot (2025-11-24)
- AG Grid is now the default renderer; legacy HTML grid only shows up when the feature flag is off. Left-panel pinning, status bar, per-row highlight, and dual horizontal scrollbars (top & bottom) are in place for both AG Grid and the legacy fallback.
- DataLoader + TimeColumnGenerator consume `/detail_project/api/v2/project/<id>/assignments/` exclusively. Weekly columns expose `fieldId`, `index`, and `weekNumber`, so assignments for week > 1 persist and reload correctly.
- SaveHandler/AG Grid accept 0–100% proportions, convert volume↔persentase automatically, track totals per pekerjaan, and surface detailed validation errors (toast + row highlight) sebelum maupun sesudah panggilan API.
- Regression tests are green: `pytest detail_project/tests/test_jadwal_pekerjaan_page_ui.py --no-cov` dan `pytest detail_project/tests/test_weekly_canonical_validation.py --no-cov` (round-trip + zero-progress).
- Outstanding gaps: monthly switch belum aktif, volume semantics belum memvalidasi terhadap volume total, dan keyboard navigation legacy masih perlu perapihan.

## 2. Acceptance Criteria for “Phase 2 done”
1. **Pekerjaan-only inputs**
   - Tree nodes expose `type` metadata down to AG Grid row data.
   - Dynamic columns set `editable` via callback so only `type === 'pekerjaan'` can edit; classification/sub rows remain read-only with muted style.
   - Attempted edits on locked rows show tooltip/toast explaining restriction.

2. **Dual input mode (Persentase vs Volume)**
   - Toolbar toggle/segmented control stored in `state.inputMode ∈ {'percentage','volume'}` plus persisted preference.
   - Grid renders values + placeholders in the selected unit (e.g. `45%` vs `12.00 m³`).
   - Save payload converts volume entries back to percentage relative to pekerjaan volume; toggle respects rows without volume by disabling volume mode.

3. **Total validation & visual alerts**
   - Real-time aggregation per pekerjaan; totals > 100% (percentage mode) or > volume (volume mode) highlight the row (red border) and show warning pill.
   - `validation-utils.js` gains helpers for dual-mode ranges and reuses them before save.

4. **Focus & unsaved-state UX**
   - Values are stored on blur/enter; leaving the cell does not reset typed input.
   - Modified rows show a subtle badge; Save button enables only when `state.isDirty`.
   - Toast/spinner on save success/error plus dirty state reset after success.

5. **Time-scale switch (weekly ↔ monthly)**
   - UI control next to mode toggle lets user pick weekly/monthly (future daily/custom disabled).
   - Switching triggers DataLoader reload + TimeColumnGenerator regeneration; state/save handler know current scale (`state.timeScale`).
   - URL `/assignments/` called with the correct mode query param once backend supports it (guarded with feature flag until API ready).

6. **Responsive & navigation polish**
   - Column pinning persists on resize; pekerjaan column never jumps to the right side on small widths.
   - Keyboard navigation (arrow/tab) stays within editable fields, skipping read-only rows.
   - Optional backlog: row grouping/collapse controls, change history drawer, unsaved changes prompt on page exit.

7. **Docs & tests**
   - Update: `JADWAL_KEGIATAN_README.md`, `JADWAL_KEGIATAN_CLIENT_GUIDE.md`, `JADWAL_KEGIATAN_SIMPLIFICATION_ROADMAP.md`, `FINAL_IMPLEMENTATION_PLAN.md`, `PROJECT_ROADMAP.md`.
   - UI test (`test_jadwal_pekerjaan_page_ui.py`) extended to assert toolbar buttons exist + legacy markup hidden.
   - Manual checklist appended to `JADWAL_KEGIATAN_SIMPLIFICATION_ROADMAP.md`.

## 3. Task Breakdown & Owners
| ID | Task | Files / Modules | Status |
|----|------|-----------------|--------|
| T2D-01 | Surface `node.type` + `isEditable` on AG Grid rows; lock editing for klas/sub rows (toast on attempt). | `data-loader.js`, `ag-grid-setup.js`, `column-definitions.js`, `kelola_tahapan_grid_modern.html` | ✅ AG Grid rows locked; legacy split-panel read-only |
| T2D-02 | Implement toolbar toggle for Persentase vs Volume with state + persistence. | `jadwal_kegiatan_app.js`, toolbar template | ✅ Toggle aktif (Persentase default), auto-konversi volume↔persentase + batas 0–volume |
| T2D-03 | Extend SaveHandler/DataLoader to understand `inputMode`, convert values, and display formatting helpers. | `save-handler.js`, `validation-utils.js` | ✅ `assignments` payload stabil (week_number akurat, error detail, zero progress) |
| T2D-04 | Row total aggregation + over-limit styling (CSS + AG Grid rowClass rules). | `ag-grid-setup.js`, `kelola_tahapan_grid.css`, `validation-utils.js` | ✅ Total per pekerjaan dihitung ulang & warning otomatis sebelum Save; row highlight menyala |
| T2D-05 | Focus/dirty trackers + toast/spinner improvements. | `jadwal_kegiatan_app.js`, `grid-event-handlers.js`, `save-handler.js` | 🟡 Status bar + dirty state + dual scrollbar live; keyboard nav & tooltip minor WIP |
| T2D-06 | Weekly↔Monthly switch & DataLoader refresh pipeline. | `jadwal_kegiatan_app.js`, `time-column-generator.js`, `data-loader.js` | ☐ UI toggle rendered, backend regenerate hook belum dipanggil |
| T2D-07 | Documentation refresh + regression tests. | `_docs listed above_`, `detail_project/tests/test_jadwal_pekerjaan_page_ui.py`, `test_weekly_canonical_validation.py` | ⏳ Fixtures/tests selesai; docs update (README/Roadmap) ongoing |

> Backlog items (row grouping, change history, per-user column pinning) stay listed but are **not blockers** for Phase 2 sign-off.

## 4. Implementation Notes
- **Row metadata**: `ag-grid-setup.js` menyuntik `rowType` & `rowClass` sehingga klas/sub read-only dan baris gagal terlihat jelas.
- **AG Grid hooks**: `colDef.editable` mengecek `rowType === 'pekerjaan'`; percobaan edit klasifikasi memunculkan toast “progress hanya dapat diisi …”.
- **Assignments Map**: kunci `pekerjaanId-fieldId` dipakai konsisten di DataLoader, SaveHandler, dan AG Grid → reload langsung memunculkan nilai minggu ke‑N.
- **Validation**: SaveHandler + AG Grid menghitung ulang total per pekerjaan, memvalidasi nilai 0–100/0–volume, serta menggabungkan detail `errors`/`validation_errors` dari API (toast multi-baris).
- **UI placement**: toolbar menampung toggle persentase/volume, time-scale, Save/Refresh, serta info status bar di bawah grid.

## 5. Testing & Rollback
- **Automated**:  
  `pytest detail_project/tests/test_jadwal_pekerjaan_page_ui.py --no-cov`  
  `pytest detail_project/tests/test_weekly_canonical_validation.py --no-cov` (round-trip + zero progress)  
  `pytest detail_project/tests/test_hsp_fix.py`
- **Manual smoke**:  
  1. Load project 110 → pastikan AG Grid render, klas/sub read-only.  
  2. Toggle Persentase ↔ Volume → nilai otomatis terkonversi dan validasi menyesuaikan (0–100 vs 0–volume).  
  3. Input nilai 0–100 di beberapa minggu, simpan → `/assignments/` menampilkan nilai tersebut setelah reload.  
  4. Paksa error (misal total >100) → toast menampilkan detail dan row highlight merah sebelum request ke server.  
  5. Uji horizontal scroll (atas/bawah) + status bar + dirty state (Save disabled hingga ada perubahan).  
- **Rollback**: matikan feature flag untuk kembali ke legacy grid atau `git checkout -- kelola_tahapan_grid_modern.html detail_project/static/detail_project/js/src` jika AG Grid mengalami regresi besar.
