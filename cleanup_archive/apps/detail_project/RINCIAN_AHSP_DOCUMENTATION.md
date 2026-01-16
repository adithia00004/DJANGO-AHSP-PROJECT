# Rincian AHSP – Technical Documentation

**Last updated:** 2025-11-19  
**Scope:** `detail_project` application – page *Rincian AHSP* (`/project/<id>/rincian-ahsp/`)

---

## 1. Page Overview

The page exposes a dual-panel experience to inspect detailed AHSP (Analisa Harga Satuan Pekerjaan) data for every pekerjaan in a project.

| Panel | Purpose | Key UX |
| --- | --- | --- |
| **Left – Rekap Sidebar** | Lists pekerjaan ordered by `ordering_index`. Shows kode, uraian, satuan, effective markup badge, and “Perlu update volume” pill. | Search box (`Ctrl+K`), “Grand Total” summary, export menu, resizable width (`--ra-left-w`). |
| **Right – Detail Panel** | Displays metadata + grouped table (TK/BHN/ALT/LAIN) for the selected pekerjaan. | Sticky header, override modal (`Shift+O`), bundle indicators, keyboard navigation, toast notifications. |

Front-end file: `detail_project/static/detail_project/js/rincian_ahsp.js` (TIER‑3 build).

---

## 2. Key Files & Responsibilities

| File | Role |
| --- | --- |
| `detail_project/views.py::rincian_ahsp_view` | Renders template, injects project + pekerjaan list. |
| `detail_project/templates/detail_project/rincian_ahsp.html` | Base markup, data attributes for API endpoints, toolbar, modal. |
| `detail_project/static/detail_project/css/rincian_ahsp.css` | Layout/styling specific to page (resizer, sticky table, toolbar parity). |
| `detail_project/static/detail_project/js/rincian_ahsp.js` | Page controller: data fetching, caching, override modal, keyboard shortcuts, export wiring. |
| `detail_project/views_api.py` | REST endpoints used by the page (see §4). |
| `detail_project/services.py` | Heavy lifting for rekap computation, bundle expansion, cache invalidation. |
| `detail_project/RINCIAN_AHSP_DOCUMENTATION.md` | (This file) |

Supporting models live in `detail_project/models.py` (`Pekerjaan`, `DetailAHSPProject`, `DetailAHSPExpanded`, `HargaItemProject`, `VolumePekerjaan`, `ProjectPricing`).

---

## 3. Front-end Architecture

### 3.1 Bootstrapping
`#rekap-app` carries data attributes with fully-qualified URLs:

- `data-ep-rekap` → `api_get_rekap_rab`
- `data-ep-detail-prefix` → `api_get_detail_ahsp`
- `data-ep-pricing` → `api_project_pricing`
- `data-ep-pricing-item-prefix` → `api_pekerjaan_pricing`
- `data-ep-reset-prefix` → `api_reset_detail_ahsp_to_ref`

### 3.2 State & Controllers (`rincian_ahsp.js`)

- Uses an IIFE module; early exit if element missing.
- **State:** `rows` (rekap data), `filtered`, `selectedId`, `cacheDetail` (Map<pekerjaan_id, detail payload>), `projectBUK`, `projectPPN`, `pendingVolumeJobs`.
- **Initial load:** `loadProjectBUK()` → `loadRekap()`. Restores last selected pekerjaan from `localStorage`.
- **Selection flow:** `selectItem(id)` fetches pricing + detail (with `AbortController`) and renders right panel. Detail responses are cached to avoid redundant API calls.
- **Bundle inspection:** .bundle-row clicks hit /api/project/<pid>/pekerjaan/<id>/bundle/<detail_id>/expansion/ to display DetailAHSPExpanded components inline.
- **Override Modal:** Applies robust validation; uses `SaveOverride` POST to `api_pekerjaan_pricing`. After success, re-runs `loadRekap()` and refetches detail to keep list + table + grand total in sync.
- **Granular loading:** `setLoading(scope)` toggles opacity on list/detail independently.
- **Keyboard support:** `Ctrl+K` (focus search), `Shift+O` (toggle override modal), arrows (navigate list), `Enter`, `Esc`.
- **Resizer:** writes to CSS custom property `--ra-left-w` (and persists `rk-left-w` in `localStorage`).
- **Export:** Buttons delegated to `ExportManager` (`static/detail_project/js/export/ExportManager.js`), storing last orientation in `localStorage`.
- **Toasts:** uses `DP.core.toast` when available; fallback implementation injects inline to `#rk-toast`.

---

## 4. Back-end APIs & Services

### 4.1 View Functions (`detail_project/views_api.py`)

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `api_get_rekap_rab(project_id)` | Returns consolidated rows for sidebar (`rows` + `meta`). | Uses `compute_rekap_for_project`. Provides `markup_eff`, `biaya_langsung`, `HSP`, `volume`, `total`. |
| `api_get_detail_ahsp(project_id, pekerjaan_id)` | Returns detailed items for selected pekerjaan. | `read_only = pkj.is_ref`. Pulls base data from `DetailAHSPProject`, merges totals from `DetailAHSPExpanded`. |
| `api_pekerjaan_pricing(project_id, pekerjaan_id)` | GET/POST override BUK. | Persists `markup_override_percent` on `Pekerjaan`; invalidates rekap cache on commit. |
| `api_project_pricing(project_id)` | GET/POST project-wide markup/PPN/rounding. | Used for toolbar badge + dirty indicator. |
| `api_reset_detail_ahsp_to_ref` | Resets pekerjaan detail back to referensi (if allowed). | Inaccessible from UI at the moment but endpoint is exposed for parity. |
| `api_get_bundle_expansion` | Returns expanded TK/BHN/ALT rows for a bundle item. | Triggered when users click bundle rows so the page can render the `DetailAHSPExpanded` breakdown inline. |
| pi_get_bundle_expansion | Returns expanded TK/BHN/ALT rows for a bundle item. | Triggered when users click bundle rows so the page can render the DetailAHSPExpanded breakdown inline. |

### 4.2 Services (`detail_project/services.py`)

- `_populate_expanded_from_raw(project, pekerjaan)` – dual-storage writer. Mulai Phase 1, komponen bundle disimpan **per unit bundle** (tidak lagi dikali koef bundle). Nilai koef bundle dipertahankan di `DetailAHSPProject` sehingga layer agregasi bisa menerapkannya.
- `compute_rekap_for_project(project)` – agregator sidebar. Sejak Phase 3, fungsi ini membaca `DetailAHSPExpanded` lalu mengalikan kembali koef komponen dengan `source_detail.koefisien` apabila baris berasal dari bundle (`kategori='LAIN'` dengan referensi). Hasil `A/B/C/LAIN` kembali identik dengan harapan user, sementara `total = G × volume` tetap benar.
- `compute_kebutuhan_items(project, ...)` – rekap kebutuhan global. Logika baru mendeteksi setiap komponen bundle dan mengalikan koef per unit dengan kuantitas bundle * volume pekerjaan (dan proporsi tahapan bila ada). Output row memiliki `quantity_decimal` yang sudah siap dipakai ekspor.
- `invalidate_rekap_cache(project)` + sinyal di `detail_project/signals.py` masih menjadi pintu untuk menghapus cache `rekap:{pid}:v2` saat detail, volume, pekerjaan, atau pricing berubah.

---

## 5. Data Flow

1. **Page load**
   - Template renders with project + pekerjaan list (no detail).
   - JS fetches `/api/project/<id>/pricing/` for default markup/PPN then `/api/project/<id>/rincian-rab/`.

2. **User selects pekerjaan**
   - `api_pekerjaan_pricing` (if override feature enabled) → populates chips + modal.
   - `api_get_detail_ahsp` → returns grouped items. Backend folds `DetailAHSPExpanded` totals into `harga_satuan` for LAIN lines.
   - Table renders `TK/BHN/ALT/LAIN` sections; summary rows compute `E`, `F`, `G`.

3. **Override Profit/Margin (BUK)**
   - Modal collects value (0–100%). JS validates, POSTs to `api_pekerjaan_pricing`.
   - Response triggers `cacheDetail.delete(id)`, `loadRekap()`, detail refetch, and toast.

4. **Exports**
   - `ExportManager` hits `/api/project/<id>/export/rincian-ahsp/{csv|pdf|word}` (implemented via `detail_project/static/detail_project/js/export/ExportManager.js` + `detail_project/views_api.py`).

5. **Bundle Handling**
   - When raw detail has `kategori=LAIN` and `ref_pekerjaan`/`ref_ahsp`, `_populate_expanded_from_raw` writes computed lines to `DetailAHSPExpanded`.
   - `api_get_detail_ahsp` uses expanded subtotals to derive `harga_satuan` and `jumlah` per bundle.
   - `api_get_bundle_expansion` surfaces the stored `DetailAHSPExpanded` rows so the UI can show bundle breakdowns on demand.

---

## 6. Calculations & Formulas

Definitions (per pekerjaan):

- `A` = Σ TK subtotals
- `B` = Σ BHN subtotals
- `C` = Σ ALT subtotals
- `LAIN` = Σ LAIN subtotals (after bundle expansion)
- `D` = `A + B + C` (legacy direct cost)
- `E_base` = `A + B + C + LAIN`
- `F` = `E_base * (effective_markup / 100)`
- `G` = `E_base + F` (Harga Satuan dengan markup)
- `total` = `G * volume`
- `Grand Total (toolbar)` = Σ `total` + PPN.

API ensures `biaya_langsung` still reports `D` for downstream compatibility, while `HSP` stays equal to `E_base`.

---

## 7. Styling & Responsiveness

- CSS tokens defined in `static/detail_project/css/core.css`:
  - `--ra-left-w` (default `360px`, updated via JS resizer).
  - `--ra-col-*-w` for table column widths.
  - `--ra-toolbar-h` to sync sticky offsets.
- `static/detail_project/css/rincian_ahsp.css` implements:
  - Grid layout (`.ra-body`), resizer hit area, sticky table header with `top: calc(var(--dp-topbar-h) + var(--ra-toolbar-h))`.
  - Toolbar parity with Template AHSP (button heights, search input).
  - Scroll shadows and custom scrollbars for job list.
- Modal/backdrop z-index overrides to avoid being hidden by sticky toolbar.

---

## 8. Testing & Fixtures

| Test file | Coverage |
| --- | --- |
| `detail_project/tests/test_rincian_ahsp.py` | API contract, bundle pricing, override behavior. |
| `detail_project/tests/test_workflow_baseline.py` | Cascade expansion + bundle koef regression tests. |
| `detail_project/tests/test_hsp_fix.py` | Smoke script ensuring backend vs API HSP parity (includes `_ensure_sample_project` helper for dummy data). |

Manual checks:

1. `pytest detail_project/tests/test_rincian_ahsp.py`
2. `pytest detail_project/tests/test_workflow_baseline.py -k bundle`
3. Full regression: `pytest detail_project/tests/ -v` (lihat `logs/phase5_test_run_20251119_full.md` untuk coverage 71.91%).
4. Run page locally, verify keyboard shortcuts and export buttons.

---

## 9. Troubleshooting Cheat Sheet

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| Sidebar HSP ≠ detail table G | Bundle expansion stale / cache not invalidated. | Run `_populate_expanded_from_raw` for the pekerjaan, then `invalidate_rekap_cache`. |
| LAIN rows show `harga_satuan = 0` | Missing `DetailAHSPExpanded` data. | Trigger re-expansion; confirm `DetailAHSPExpanded` rows exist. |
| Override BUK not persisted | Validation error or cache still serving old data. | Check network tab for 4xx, ensure value 0–100, wait for toast, rerun `loadRekap()`. |
| Grand Total not updating | Rekap cache stale. | `from detail_project.services import invalidate_rekap_cache; invalidate_rekap_cache(project_id)`. |
| Keyboard shortcuts inactive | Focus is inside inputs or JS not loaded. | Ensure `detail_project/static/detail_project/js/rincian_ahsp.js` is included (template bottom). |

---

## 10. Recent Fixes & Notes (Nov 2025)

1. **Cache Invalidation:** `compute_rekap_for_project` switched to deterministic key + signature. `_clear_rekap_cache` now deletes both `v1` and `v2`.
2. **Toolbar Markup:** Corrected mis-placed Bootstrap utility classes, removed stray unicode placeholders.
3. **Sticky Table:** `top` offset defined explicitly to keep header visible under toolbar.
4. **Resizer Sync:** CSS, JS, and default tokens now consistently use `--ra-left-w`.
5. **Override Race Condition:** Modal apply/clear capture `targetId` to avoid cross-updating when user switches selection mid-request.
6. **Bundle Pricing:** `api_get_detail_ahsp` membaca `DetailAHSPExpanded` per-unit (tidak lagi membagi/mengalikan ulang). Frontend tetap memakai formula generik `jumlah = koef × harga`, sementara layer agregasi menambahkan `source_detail.koefisien` saat menghitung A/B/C/LAIN.
7. **HSP Smoke Test:** `_ensure_sample_project()` helper seeds dummy data so `test_hsp_fix.py` can run even on empty DBs.
8. **Export Alignment (2025-11-19):** `exports/rincian_ahsp_adapter.py` kini menggunakan `bundle_total` per unit tanpa pembagian ulang, sehingga pekerjaan custom/bundle pada berkas ekspor identik dengan UI Rincian AHSP.

Keep this document updated whenever UI/API contracts change or new shortcuts/features are added.

--- 

**Contacts:** Detail Project squad (@team-detail-project)  
**Jira tags:** `DET-AHSP`, `DET-RAB`, `DET-BUNDLE`
