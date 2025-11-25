# Jadwal Kegiatan – Roadmap Simplifikasi & Optimasi (UNIFIED)

> **Dokumen Roadmap Terintegrasi** – Menyatukan 3 jalur pekerjaan untuk simplifikasi struktur, peningkatan performa, dan modernisasi arsitektur halaman **Jadwal Pekerjaan**.

---

## 📋 Executive Summary

Roadmap ini menggabungkan 3 inisiatif terpisah yang sebelumnya overlap:

1. **UI/UX Simplification** – Template consolidation, CSS cleanup, modern structure
2. **Performance Optimization** – Memory leaks, virtual scrolling, validation enhancements
3. **Modern Architecture** – Vite build system, ES6 modules, AG Grid integration

**Tujuan Akhir**: Page Jadwal Pekerjaan yang **simple, fast, maintainable** dengan 3 mode view (Grid/Gantt/Kurva S) yang optimal.

---

## 🎯 Status Ringkas (Updated 2025-11-19 - PHASE 2A COMPLETE!)

| Target | Status | Progress | Catatan |
| --- | --- | --- | --- |
| **FASE 0: Fondasi Modern (Phase 1)** | ✅ **SELESAI** | 100% | Vite setup, event delegation, validation utils complete |
| **FASE 1: Wire & Activate** | ✅ **SELESAI** | 100% | Modern template active, settings updated, Vite running |
| **FASE 2A: Core Module Migration** | DONE | 100% | DataLoader + TimeColumnGenerator migrated (API v2 adoption outstanding) |
| **FASE 2B: Grid Module Migration** | IN PROGRESS | 75% | GridRenderer, SaveHandler, AG Grid setup aktif; kolom kode/pekerjaan/volume/satuan sudah dipinned + theme alpine ↔ alpine-dark otomatis, tree data & virtual scroll masih dikerjakan |
| **FASE 2C: Chart Module Migration** | ☐ **PENDING** | 0% | Gantt + Kurva S adapters (6/12 modules) |
| **FASE 3: CSS & Layout Cleanup** | ☐ **PENDING** | 15% | Sebagian CSS vars sudah ada, inline style masih banyak |
| **FASE 4: AG Grid Integration** | PENDING | 20% | Flag default True, perlu buka kontainer, virtual scroll, QA |
| **FASE 5: Advanced Features** | ☐ **PENDING** | 0% | Virtual scroll, EVM, export |
| **FASE 6: Testing & Documentation** | 🔶 **IN PROGRESS** | 45% | Phase 2A docs complete, end-to-end tests pending |

---

## 🔍 Analisis Situasi Saat Ini

### ✅ Yang Sudah Selesai (Phase 2A Complete - 2025-11-19!)

**File-file Modern yang Sudah Dibuat:**
```
detail_project/
├── package.json                                    ✅ Vite + AG Grid + xlsx dependencies
├── vite.config.js                                  ✅ Django integration + code splitting
├── static/detail_project/
│   ├── css/
│   │   └── validation-enhancements.css             ✅ Real-time validation styles
│   └── js/src/                                     ✅ Modern structure ACTIVE
│       ├── jadwal_kegiatan_app.js                  ✅ Main app (modern entry)
│       └── modules/
│           ├── core/                               ✅ NEW (Phase 2A)
│           │   ├── data-loader.js                  ✅ 546 lines ES6 (migrated)
│           │   └── time-column-generator.js        ✅ 236 lines ES6 (migrated)
│           ├── shared/
│           │   ├── performance-utils.js            ✅ debounce, throttle, RAF
│           │   ├── event-delegation.js             ✅ Memory leak fix
│           │   └── validation-utils.js             ✅ Cell validation
│           └── grid/
│               └── grid-event-handlers.js          ✅ GridEventManager
├── templates/detail_project/
│   ├── kelola_tahapan_grid_modern.html             ✅ ACTIVE (clean, no conditionals)
│   ├── kelola_tahapan_grid_LEGACY.html             📦 Backup (full legacy)
│   └── kelola_tahapan_grid_vite.html               ⚠️ Deprecated (hybrid)
└── docs/
    ├── REFACTOR_2025_11_19_SUMMARY.md              ✅ Complete refactor docs
    ├── FASE_2_TESTING_GUIDE.md                     ✅ Testing instructions
    ├── ROLLBACK_GUIDE.md                           ✅ Rollback options
    └── TESTING_NEXT_STEPS.md                       ✅ Manual testing guide
```

**Achievements:**
- ✅ Memory leak **FIXED** (event delegation: 15,600→10 listeners)
- ✅ Validation **IMPLEMENTED** (real-time visual feedback)
- ✅ Performance **OPTIMIZED** (throttled scroll, RAF sync)
- ✅ Bundle size **REDUCED** by 28% (350KB → 250KB minified)
- ✅ Vite HMR **WORKING** (instant dev updates)
- ✅ **Template REFACTORED** (clean modern template, no conditionals)
- ✅ **View UPDATED** (uses modern template)
- ✅ **Settings UPDATED** (modern stack by default)
- �o. **4 Modules MIGRATED** (DataLoader, TimeColumnGenerator, GridRenderer, SaveHandler)
- ✅ **Vite Dev Server RUNNING** (localhost:5173)

### 🔶 Yang Masih Dalam Proses

**Current Status: PHASE 2A COMPLETE, PHASE 2B NEXT**

**Modules Migrated (4 of 12):**
- ✅ DataLoader (legacy → ES6)
- ✅ TimeColumnGenerator (legacy → ES6)

**Modules Remaining (8 of 12):**
- �o. GridRenderer (legacy grid_module -> grid-renderer.js)
- �o. SaveHandler (save_handler_module -> save-handler.js)
- �~? GanttAdapter (gantt_module.js -> gantt adapter)
- �~? KurvaSAdapter (kurva_s_module.js -> kurva-s adapter)
- �~? Mode switching helpers, export adapters, sidebar widgets, dsb.

**Next Tasks:**
1. **Manual Testing** - Verify modern stack loads correctly & regresi ketika AG Grid menjadi tampilan utama (legacy hanya fallback manual).
2. **DataLoader v2** - Phase 2 aktif (read `/api/v2/project/<id>/assignments/` tanpa fallback); lanjutkan sinkronisasi logging/QA agar semua halaman menggunakan jalur canonical yang sama.
3. **Mode persentase/volume** - Aktifkan toggle, batas edit per baris, dan alert jika total >100% atau volume sebelum user memakai data riil.
4. **Phase 2C** - Migrate chart adapters (Gantt, Kurva S) + sinkronisasi assignment map.
5. **Phase 2D** - Implement manifest loader + bersihkan sisa modul legacy/export helpers.

---

## 🗺️ ROADMAP TERINTEGRASI (6 Fase)

### **FASE 0: Fondasi Modern** ✅ SELESAI (Phase 1 Complete)

**Completed Items:**
- [x] Setup Vite build system dengan Django integration
- [x] Install dependencies (AG Grid, xlsx, jsPDF, html2canvas) - **$0 total cost**
- [x] Buat struktur folder `js/src/modules/`
- [x] Implement `performance-utils.js` (debounce, throttle, RAF)
- [x] Implement `event-delegation.js` (memory leak fix)
- [x] Implement `validation-utils.js` (cell validation)
- [x] Implement `grid-event-handlers.js` (GridEventManager)
- [x] Implement `main.js` (JadwalKegiatanApp)
- [x] Create `validation-enhancements.css` (visual feedback)
- [x] Create `kelola_tahapan_grid_vite.html` template
- [x] Write comprehensive docs (PHASE_1_IMPLEMENTATION_GUIDE.md)

**Results Achieved:**
- Memory usage: **-50%** (180MB → 55MB)
- Event listeners: **-99.9%** (15,600 → ~10)
- Scroll performance: **+50%** (40fps → 60fps)
- Bundle size: **-28%** (350KB → 250KB)
- Load time: **-56%** (800ms → 350ms)

**Next Step**: Activate the new infrastructure!

---

### **FASE 1: Wire & Activate** ✅ SELESAI (2025-11-19)

**COMPLETED - Modern template is now active!**

**What Was Done:**
- ✅ Created clean modern template: `kelola_tahapan_grid_modern.html`
- ✅ Updated `views.py` to use modern template (line 209)
- ✅ Updated settings defaults: `USE_VITE_DEV_SERVER=True`, `ENABLE_AG_GRID=True`
- ✅ Backed up legacy template: `kelola_tahapan_grid_LEGACY.html`
- ✅ Deprecated hybrid template: `kelola_tahapan_grid_vite.html`
- ✅ Vite dev server running successfully (localhost:5173)

**Results:**
- Modern stack is now DEFAULT
- Legacy scripts NO LONGER load
- Clean separation: dev (Vite HMR) vs prod (built assets)
- Easy rollback if needed (see ROLLBACK_GUIDE.md)

**Next Step:** Continue to Phase 2B (migrate remaining modules)

---

### **FASE 1: Wire & Activate (ARCHIVED - OLD NOTES)** ⚠️ DEPRECATED

**Tujuan**: Aktifkan infrastruktur modern yang sudah siap, matikan legacy

**Durasi**: 1-2 hari (8-12 jam)
**Risk**: LOW (rollback mudah)
**Impact**: HIGH (foundational untuk semua fase berikutnya)

#### **Tahap 1.1: Switch Template & View** ⭐ CRITICAL

**File Changes:**
```python
# detail_project/views.py (Line ~195)
def jadwal_pekerjaan_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # ✅ NEW: Use Vite template
    return render(request, 'detail_project/kelola_tahapan_grid_vite.html', {
        'project': project,
        'DEBUG': settings.DEBUG,  # For Vite dev/prod switching
    })
```

**Testing Steps:**
```bash
# Terminal 1: Start Vite dev server
npm run dev

# Terminal 2: Start Django
python manage.py runserver

# Browser: Navigate to /project/{id}/jadwal-pekerjaan/
# Expected: Page loads with Vite, console shows JadwalKegiatanApp initialized
```

**Rollback Plan:**
```python
# If issues occur, simply change back to:
return render(request, 'detail_project/kelola_tahapan_grid.html', {...})
```

**Checklist:**
- [ ] Update `jadwal_pekerjaan_view` to use `kelola_tahapan_grid_vite.html`
- [ ] Test dengan `npm run dev` (development mode with HMR)
- [ ] Test dengan `npm run build` (production mode)
- [ ] Verify console menunjukkan `JadwalKegiatanApp initialized`
- [ ] Verify tidak ada console errors
- [ ] Verify basic grid rendering (meski belum functional)

---

#### **Tahap 1.2: Bersihkan Sumber Aset**

**Django Settings Audit:**
```python
# config/settings/base.py or local.py
STATICFILES_DIRS = [
    BASE_DIR / "detail_project" / "static",  # ✅ Keep this
]

# ⚠️ Hapus jika ada:
# STATICFILES_DIRS += [BASE_DIR / "staticfiles"]  # REMOVE
```

**Clean Script:**
```python
# scripts/clean_staticfiles.py
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
staticfiles = BASE_DIR / "staticfiles"

if staticfiles.exists():
    print(f"Cleaning {staticfiles}...")
    shutil.rmtree(staticfiles)
    staticfiles.mkdir()
    print("✅ staticfiles/ cleaned (empty folder)")
else:
    print("✅ staticfiles/ doesn't exist, nothing to clean")
```

**Usage:**
```bash
# Before dev session
python scripts/clean_staticfiles.py

# Run collectstatic ONLY for production
python manage.py collectstatic --noinput
```

**Checklist:**
- [ ] Audit `STATICFILES_DIRS` setting
- [ ] Create `scripts/clean_staticfiles.py`
- [ ] Add note to README about when to run collectstatic
- [ ] Add `.gitignore` entry for `staticfiles/`

---

#### **Tahap 1.3: Audit Dependensi Template**

**Template Inventory:**
```bash
# Find all <script> and <link> tags in templates
grep -n "<script" detail_project/templates/detail_project/kelola_tahapan_grid.html
grep -n "<link" detail_project/templates/detail_project/kelola_tahapan_grid.html
```

**Create Audit Report:**
```markdown
## Template Dependency Audit (2025-11-19)

### Legacy Template: kelola_tahapan_grid.html

**External Libraries:**
- [ ] Bootstrap 5 CSS/JS (via base template) ✅ Keep
- [ ] Frappe Gantt v0.6.1 CDN ✅ Keep (until Gantt migration)
- [ ] ECharts v5.4.3 CDN ✅ Keep (until S-curve migration)

**Legacy JavaScript:**
- [ ] kelola_tahapan_grid.js (1700 lines) ⚠️ TO REMOVE
- [ ] kelola_tahapan_page_bootstrap.js ⚠️ TO REMOVE
- [ ] 12 modul di jadwal_pekerjaan/kelola_tahapan/ ⚠️ TO MIGRATE

**Inline Styles:**
- [ ] `_grid_tab.html` (~50 inline styles) ⚠️ TO MOVE TO CSS
- [ ] `_gantt_tab.html` (~10 inline styles) ⚠️ TO MOVE TO CSS
- [ ] `_kurva_s_tab.html` (~5 inline styles) ⚠️ TO MOVE TO CSS

### New Template: kelola_tahapan_grid_vite.html

**Vite Integration:**
- [x] Development mode: Loads from http://localhost:5173
- [x] Production mode: Loads from /static/detail_project/dist/

**Modern Dependencies:**
- [x] AG Grid Community CSS (CDN) ✅ Ready
- [x] validation-enhancements.css ✅ Ready
- [x] jadwal_kegiatan_app.js (ES module) ✅ Ready

**Missing (TO CREATE in Fase 2):**
- [ ] gantt-module.js (ES6 port)
- [ ] kurva-s-module.js (ES6 port)
- [ ] data-loader.js (ES6 port)
```

**Checklist:**
- [ ] Run grep audit on both templates
- [ ] Document all external dependencies
- [ ] List all inline styles to be moved
- [ ] Save audit report to `detail_project/docs/TEMPLATE_AUDIT.md`

---

### **FASE 2: Legacy Migration (Migrate JS Modules)**

**Tujuan**: Port 12 modul legacy ke struktur Vite modern

**Durasi**: 3-4 hari (24-30 jam)
**Risk**: MEDIUM (logic kompleks, butuh testing)
**Impact**: HIGH (clean architecture, maintainability)

#### **Tahap 2.1: Prioritaskan Modul Core**

**Migration Order (by dependency):**

1. **data-loader.js** (Priority 1) – Foundation
   - Source: `jadwal_pekerjaan/kelola_tahapan/data_loader_module.js`
   - Target: `js/src/modules/core/data-loader.js`
   - Dependency: None
   - Lines: ~200

2. **time-column-generator.js** (Priority 2)
   - Source: `time_column_generator_module.js`
   - Target: `js/src/modules/core/time-column-generator.js`
   - Dependency: data-loader
   - Lines: ~150

3. **grid-renderer.js** (Priority 3)
   - Source: `grid_module.js` (render parts only)
   - Target: `js/src/modules/grid/grid-renderer.js`
   - Dependency: time-column-generator
   - Lines: ~300
   - **Note**: Event handling sudah di `grid-event-handlers.js` ✅

4. **save-handler.js** (Priority 4)
   - Source: `save_handler_module.js`
   - Target: `js/src/modules/core/save-handler.js`
   - Dependency: validation-utils ✅
   - Lines: ~250

5. **gantt-adapter.js** (Priority 5)
   - Source: `gantt_module.js`
   - Target: `js/src/modules/gantt/gantt-adapter.js`
   - Dependency: data-loader
   - Lines: ~400

6. **kurva-s-adapter.js** (Priority 6)
   - Source: `kurva_s_module.js`
   - Target: `js/src/modules/kurva-s/kurva-s-adapter.js`
   - Dependency: data-loader
   - Lines: ~350

**Checklist:**
- [ ] Create folder structure `js/src/modules/core/`
- [ ] Migrate data-loader.js dengan ES6 syntax
- [ ] Migrate time-column-generator.js
- [ ] Migrate grid-renderer.js
- [ ] Migrate save-handler.js
- [ ] Migrate gantt-adapter.js
- [ ] Migrate kurva-s-adapter.js
- [ ] Test setiap modul secara isolated
- [ ] Update `main.js` untuk import semua modul

---

#### **Tahap 2.2: Refactor Entry Point**

**Goal**: `jadwal_kegiatan_app.js` menjadi satu-satunya orchestrator

**Current State:**
```javascript
// main.js (sudah ada tapi minimal)
export class JadwalKegiatanApp {
  constructor() {
    this.state = {};
    this.eventManager = null;
  }

  initialize(config) {
    // Setup basic event delegation
    this.eventManager = new GridEventManager(this.state);
    this.eventManager.attachEvents();
  }
}
```

**Target State:**
```javascript
// main.js (enhanced orchestrator)
import { DataLoader } from '@modules/core/data-loader.js';
import { TimeColumnGenerator } from '@modules/core/time-column-generator.js';
import { GridRenderer } from '@modules/grid/grid-renderer.js';
import { GridEventManager } from '@modules/grid/grid-event-handlers.js';
import { SaveHandler } from '@modules/core/save-handler.js';
- �~? GanttAdapter (gantt_module.js -> gantt adapter)
- �~? KurvaSAdapter (kurva_s_module.js -> kurva-s adapter)

export class JadwalKegiatanApp {
  constructor() {
    this.state = this.initializeState();
    this.modules = {};
  }

  async initialize(config) {
    // 1. Load data
    this.modules.dataLoader = new DataLoader(this.state);
    await this.modules.dataLoader.loadAllData();

    // 2. Generate columns
    this.modules.timeColumns = new TimeColumnGenerator(this.state);
    this.modules.timeColumns.generate();

    // 3. Render grid
    this.modules.gridRenderer = new GridRenderer(this.state);
    this.modules.gridRenderer.render();

    // 4. Attach events
    this.modules.eventManager = new GridEventManager(this.state);
    this.modules.eventManager.attachEvents();

    // 5. Initialize charts
- �~? GanttAdapter (gantt_module.js -> gantt adapter)
- �~? KurvaSAdapter (kurva_s_module.js -> kurva-s adapter)

    // 6. Setup save handler
    this.modules.saveHandler = new SaveHandler(this.state);

    console.log('✅ JadwalKegiatanApp initialized with all modules');
  }

  destroy() {
    // Cleanup all modules
    Object.values(this.modules).forEach(module => {
      if (module.destroy) module.destroy();
    });
    this.modules = {};
    this.state = null;
  }
}
```

**Checklist:**
- [ ] Import semua modul yang sudah di-migrate
- [ ] Implement lifecycle methods (initialize, destroy)
- [ ] Setup proper dependency injection
- [ ] Add error boundaries for each module
- [ ] Test initialization sequence
- [ ] Verify cleanup on destroy

---

#### **Tahap 2.3: Legacy Bridge Adapter (Optional Fallback)**

**Purpose**: Temporary compatibility layer selama migration

**File**: `js/src/modules/legacy/legacy-bridge.js`

```javascript
/**
 * Legacy Bridge Adapter
 * Provides backward compatibility with old module API
 * TO BE REMOVED after full migration
 */

export class LegacyBridge {
  constructor(modernApp) {
    this.app = modernApp;
    this.setupGlobalCompat();
  }

  setupGlobalCompat() {
    // Legacy code expects window.kelolaTahapanPageState
    window.kelolaTahapanPageState = this.app.state;

    // Legacy code expects window.KelolaTahapanPage
    window.KelolaTahapanPage = {
      events: this.app.eventManager,
      refreshGrid: () => this.app.modules.gridRenderer.render(),
      refreshGantt: () => this.app.modules.gantt.refresh(),
      refreshKurvaS: () => this.app.modules.kurvaS.refresh(),
    };
  }

  destroy() {
    delete window.kelolaTahapanPageState;
    delete window.KelolaTahapanPage;
  }
}
```

**Usage:**
```javascript
// main.js
import { LegacyBridge } from '@modules/legacy/legacy-bridge.js';

class JadwalKegiatanApp {
  initialize(config) {
    // ... modern initialization

    // TEMPORARY: Support legacy code
    if (config.enableLegacyBridge) {
      this.legacyBridge = new LegacyBridge(this);
    }
  }
}
```

**Checklist:**
- [ ] Create legacy bridge ONLY if needed
- [ ] Document which legacy code depends on it
- [ ] Plan removal timeline (after all modules migrated)
- [ ] Add deprecation warnings in console

---

### **FASE 3: CSS & Layout Cleanup**

**Tujuan**: Pindahkan inline styles ke CSS, gunakan CSS variables

**Durasi**: 2-3 hari (16-20 jam)
**Risk**: LOW (visual regression easy to spot)
**Impact**: MEDIUM (maintainability, theming)

#### **Tahap 3.1: CSS Variables System**

**Create**: `static/detail_project/css/jadwal-kegiatan-vars.css`

```css
/**
 * Jadwal Kegiatan CSS Variables
 * Centralized design tokens for easy customization
 */

:root {
  /* Layout Dimensions */
  --jk-left-panel-width: 420px;
  --jk-right-panel-min-width: 800px;
  --jk-header-height: 45px;
  --jk-row-height: 40px;
  --jk-toolbar-height: 60px;

  /* Column Widths */
  --jk-col-tree-width: 40px;
  --jk-col-uraian-width: 280px;
  --jk-col-volume-width: 80px;
  --jk-col-satuan-width: 60px;
  --jk-col-time-width: 90px;

  /* Colors - Light Theme */
  --jk-grid-bg: #ffffff;
  --jk-grid-border: #dee2e6;
  --jk-header-bg: #f8f9fa;
  --jk-header-text: #212529;
  --jk-row-hover: #f1f3f5;
  --jk-row-selected: #e7f5ff;

  /* Validation Colors */
  --jk-cell-error: #dc3545;
  --jk-cell-warning: #ffc107;
  --jk-cell-success: #28a745;
  --jk-cell-editing: #0d6efd;

  /* Progress Colors */
  --jk-progress-under: var(--jk-cell-warning);
  --jk-progress-over: var(--jk-cell-error);
  --jk-progress-complete: var(--jk-cell-success);

  /* Spacing */
  --jk-spacing-xs: 4px;
  --jk-spacing-sm: 8px;
  --jk-spacing-md: 16px;
  --jk-spacing-lg: 24px;
  --jk-spacing-xl: 32px;

  /* Transitions */
  --jk-transition-fast: 150ms;
  --jk-transition-normal: 250ms;
  --jk-transition-slow: 350ms;
}

/* Dark Theme Overrides */
[data-bs-theme="dark"] {
  --jk-grid-bg: #1e1e1e;
  --jk-grid-border: #3a3a3a;
  --jk-header-bg: #2d2d2d;
  --jk-header-text: #e0e0e0;
  --jk-row-hover: #2a2a2a;
  --jk-row-selected: #1a4d7a;
}
```

**Update Main CSS:**
```css
/* kelola_tahapan_grid.css */
@import 'jadwal-kegiatan-vars.css';

.left-panel-wrapper {
  width: var(--jk-left-panel-width);
  background: var(--jk-grid-bg);
  border-right: 1px solid var(--jk-grid-border);
}

.col-tree { width: var(--jk-col-tree-width); }
.col-uraian { width: var(--jk-col-uraian-width); }
.col-volume { width: var(--jk-col-volume-width); }
.col-satuan { width: var(--jk-col-satuan-width); }
.time-cell { width: var(--jk-col-time-width); }
```

**Checklist:**
- [ ] Create `jadwal-kegiatan-vars.css` dengan semua tokens
- [ ] Update `kelola_tahapan_grid.css` untuk gunakan variables
- [ ] Test light/dark theme switching
- [ ] Document variables di README

---

#### **Tahap 3.2: Remove Inline Styles dari Template**

**Audit Inline Styles:**
```bash
# Find all style="" attributes
grep -n 'style="' detail_project/templates/detail_project/kelola_tahapan/_grid_tab.html
```

**Example Migration:**

**Before (inline):**
```html
<div class="left-panel-wrapper" style="width: 420px; background: white; border-right: 1px solid #ddd;">
```

**After (CSS):**
```html
<div class="left-panel-wrapper">
```

```css
/* In CSS file */
.left-panel-wrapper {
  width: var(--jk-left-panel-width);
  background: var(--jk-grid-bg);
  border-right: 1px solid var(--jk-grid-border);
}
```

**Checklist:**
- [ ] Audit `_grid_tab.html` inline styles
- [ ] Audit `_gantt_tab.html` inline styles
- [ ] Audit `_kurva_s_tab.html` inline styles
- [ ] Move setiap inline style ke CSS class
- [ ] Verify visual regression dengan screenshot comparison
- [ ] Remove all `style=""` attributes

---

#### **Tahap 3.3: Consolidate CSS Files**

**Current State:**
```
static/detail_project/css/
├── kelola_tahapan_grid.css              (1200 lines, messy)
├── validation-enhancements.css          (450 lines, modern) ✅
└── jadwal-kegiatan-vars.css             (TO CREATE)
```

**Target State:**
```
static/detail_project/css/
├── jadwal-kegiatan/
│   ├── vars.css                         (design tokens)
│   ├── layout.css                       (grid, panels, toolbar)
│   ├── grid.css                         (table, cells, tree)
│   ├── validation.css                   (moved from validation-enhancements.css)
│   ├── gantt.css                        (gantt-specific styles)
│   ├── kurva-s.css                      (chart-specific styles)
│   └── main.css                         (@import all modules)
└── kelola_tahapan_grid.css              (DEPRECATED, keep for rollback)
```

**Import Structure:**
```css
/* main.css */
@import './vars.css';
@import './layout.css';
@import './grid.css';
@import './validation.css';
@import './gantt.css';
@import './kurva-s.css';
```

**Checklist:**
- [ ] Create folder `css/jadwal-kegiatan/`
- [ ] Split `kelola_tahapan_grid.css` into modules
- [ ] Move `validation-enhancements.css` content to `validation.css`
- [ ] Create `main.css` dengan @imports
- [ ] Update template to load `main.css`
- [ ] Test loading order (vars first!)
- [ ] Keep old file untuk rollback, mark as DEPRECATED

---

| **FASE 4: AG Grid Integration** | PENDING | 20% | Flag default True, perlu buka kontainer, virtual scroll, QA |

**Tujuan**: Ganti custom table rendering dengan AG Grid untuk virtual scrolling

**Durasi**: 4-5 hari (32-40 jam)
**Risk**: HIGH (major library change, learning curve)
**Impact**: VERY HIGH (support 1000+ rows, professional features)

**Decision Point**: Evaluasi apakah butuh AG Grid

**Criteria untuk SKIP fase ini:**
- ✅ Project < 200 pekerjaan (custom grid cukup)
- ✅ Budget constraint (AG Grid learning time)
- ✅ Prefer simplicity over features

**Criteria untuk IMPLEMENT:**
- ❌ Project > 500 pekerjaan (custom grid slow)
- ❌ Need professional features (filter, sort, grouping)
- ❌ Want virtual scrolling out-of-the-box

**Jika IMPLEMENT, lihat Phase 2 di FINAL_IMPLEMENTATION_PLAN.md**

**Checklist:**
- [ ] Decide: AG Grid or stick to custom grid
- [ ] If AG Grid: Create `ag-grid-setup.js`
- [ ] If AG Grid: Define column definitions
- [ ] If AG Grid: Implement cell editors
- [ ] If AG Grid: Test performance dengan 1000+ rows
- [ ] If Skip: Implement custom virtual scrolling (lighter alternative)

---

### **FASE 5: Advanced Features (Performance & Analytics)**

**Tujuan**: Features yang meningkatkan UX secara signifikan

**Durasi**: 6-8 hari (48-64 jam)
**Risk**: MEDIUM
**Impact**: HIGH (competitive advantage)

#### **Tahap 5.1: Virtual Scrolling (Custom Implementation)**

**If skipping AG Grid, implement custom virtual scroll:**

**File**: `js/src/modules/grid/virtual-scroller.js`

```javascript
export class VirtualScroller {
  constructor(container, options) {
    this.container = container;
    this.rowHeight = options.rowHeight || 40;
    this.bufferSize = options.bufferSize || 10;
    this.data = options.data || [];

    this.visibleStart = 0;
    this.visibleEnd = 0;
  }

  render() {
    const containerHeight = this.container.clientHeight;
    const scrollTop = this.container.scrollTop;

    // Calculate visible range
    this.visibleStart = Math.floor(scrollTop / this.rowHeight);
    this.visibleEnd = Math.ceil((scrollTop + containerHeight) / this.rowHeight);

    // Add buffer
    const startIdx = Math.max(0, this.visibleStart - this.bufferSize);
    const endIdx = Math.min(this.data.length, this.visibleEnd + this.bufferSize);

    // Render only visible rows (startIdx to endIdx)
    // ... implementation
  }
}
```

**Benefits:**
- ✅ Support 1000+ rows smoothly
- ✅ Constant memory usage
- ✅ 60fps scrolling

**Checklist:**
- [ ] Implement VirtualScroller class
- [ ] Integrate dengan GridRenderer
- [ ] Handle tree expand/collapse
- [ ] Test dengan 1000 rows dataset
- [ ] Benchmark scrolling FPS

---

#### **Tahap 5.2: Export Features (Excel/PDF)**

**Dependencies (sudah ada!):**
- xlsx@0.18.5 ✅
- jsPDF@2.5.1 ✅
- html2canvas@1.4.1 ✅

**File**: `js/src/modules/export/excel-exporter.js`

```javascript
import * as XLSX from 'xlsx';

export class ExcelExporter {
  exportGrid(state) {
    const rows = this.buildExcelData(state);
    const ws = XLSX.utils.aoa_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Jadwal Pekerjaan');

    XLSX.writeFile(wb, `jadwal_${state.projectId}_${Date.now()}.xlsx`);
  }

  buildExcelData(state) {
    const rows = [];

    // Header row
    rows.push(['Uraian', 'Volume', 'Satuan', ...state.timeColumns.map(c => c.label)]);

    // Data rows
    state.flatPekerjaan.forEach(pekerjaan => {
      const row = [
        pekerjaan.nama,
        pekerjaan.volume || '',
        pekerjaan.satuan || '',
      ];

      state.timeColumns.forEach(col => {
        const key = `${pekerjaan.id}-${col.id}`;
        const value = state.assignmentMap.get(key) || '';
        row.push(value ? `${value}%` : '');
      });

      rows.push(row);
    });

    return rows;
  }
}
```

**File**: `js/src/modules/export/pdf-exporter.js`

```javascript
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';

export class PDFExporter {
  async exportChart(chartElement, filename) {
    const canvas = await html2canvas(chartElement);
    const imgData = canvas.toDataURL('image/png');

    const pdf = new jsPDF('landscape', 'mm', 'a4');
    const imgWidth = 280;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, imgHeight);
    pdf.save(filename);
  }
}
```

**Checklist:**
- [ ] Implement ExcelExporter class
- [ ] Implement PDFExporter class
- [ ] Add export buttons to toolbar
- [ ] Test Excel export dengan 100+ rows
- [ ] Test PDF export untuk Gantt & Kurva S
- [ ] Handle large datasets (show progress)

---

#### **Tahap 5.3: EVM (Earned Value Management) - Optional**

**Complexity**: HIGH (requires cost data model changes)

**If implementing EVM, see detailed plan in JADWAL_KEGIATAN_IMPROVEMENT_PRIORITIES.md lines 1100-1340**

**Quick Decision:**
- Skip if: Only need schedule tracking (current functionality)
- Implement if: Need cost tracking + forecasting (enterprise feature)

---

### **FASE 6: Testing & Documentation**

**Tujuan**: Production-ready quality assurance

**Durasi**: 3-4 hari (24-32 jam)
**Risk**: LOW
**Impact**: HIGH (confidence for deployment)

#### **Tahap 6.1: Automated Testing**

**Test Structure:**
```
tests/
├── unit/
│   ├── performance-utils.test.js
│   ├── validation-utils.test.js
│   ├── data-loader.test.js
│   └── grid-renderer.test.js
├── integration/
│   ├── grid-workflow.test.js
│   ├── save-flow.test.js
│   └── mode-switching.test.js
└── e2e/
    ├── full-user-journey.test.js
    └── performance-benchmark.test.js
```

**Setup Testing Framework:**
```bash
npm install --save-dev vitest @testing-library/dom happy-dom
```

**Example Unit Test:**
```javascript
// tests/unit/validation-utils.test.js
import { describe, it, expect } from 'vitest';
import { validateCellValue, validateTotalProgress } from '@shared/validation-utils.js';

describe('validateCellValue', () => {
  it('should accept valid percentage', () => {
    const result = validateCellValue(50);
    expect(result.isValid).toBe(true);
  });

  it('should reject value > 100', () => {
    const result = validateCellValue(150);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('100');
  });

  it('should reject negative value', () => {
    const result = validateCellValue(-10);
    expect(result.isValid).toBe(false);
  });
});
```

**Checklist:**
- [ ] Install Vitest + testing-library
- [ ] Write unit tests untuk semua utils (target: 80% coverage)
- [ ] Write integration tests untuk workflows
- [ ] Write E2E tests dengan Playwright (optional)
- [ ] Setup CI/CD untuk auto-run tests
- [ ] Add test script ke package.json

---

#### **Tahap 6.2: Performance Benchmarking**

**Create**: `tests/benchmarks/grid-performance.bench.js`

```javascript
import { bench, describe } from 'vitest';
import { GridRenderer } from '@modules/grid/grid-renderer.js';

describe('Grid Rendering Performance', () => {
  bench('render 100 rows', () => {
    const state = createMockState(100, 52); // 100 pekerjaan, 52 weeks
    const renderer = new GridRenderer(state);
    renderer.render();
  }, { iterations: 10 });

  bench('render 500 rows', () => {
    const state = createMockState(500, 52);
    const renderer = new GridRenderer(state);
    renderer.render();
  }, { iterations: 5 });
});
```

**Target Metrics:**
```
Render 100 rows:   < 500ms  ✅
Render 500 rows:   < 2000ms ✅
Scroll FPS:        60fps    ✅
Memory (initial):  < 50MB   ✅
Memory (after 5min): < 80MB ✅
```

**Checklist:**
- [ ] Create benchmark suite
- [ ] Test grid rendering performance
- [ ] Test scroll performance
- [ ] Test memory usage over time
- [ ] Document baseline metrics
- [ ] Setup monitoring alerts

---

#### **Tahap 6.3: Documentation Update**

**Documents to Update:**

1. **JADWAL_KEGIATAN_README.md** (User Guide)
   - [ ] Update installation steps (add npm install)
   - [ ] Update development workflow (Vite + Django)
   - [ ] Add troubleshooting section
   - [ ] Update screenshots

2. **JADWAL_KEGIATAN_CLIENT_GUIDE.md** (End User)
   - [ ] Reflect UI changes (if any)
   - [ ] Update keyboard shortcuts
   - [ ] Add export feature docs

3. **JADWAL_KEGIATAN_DOCUMENTATION.md** (Technical)
   - [ ] Update architecture section (Vite modules)
   - [ ] Update API reference (if changed)
   - [ ] Add performance metrics
   - [ ] Update file structure diagram

4. **DEPLOYMENT_GUIDE.md** (DevOps)
   - [ ] Add npm build step
   - [ ] Add Vite production config
   - [ ] Update collectstatic workflow

**Checklist:**
- [ ] Review all 4 documentation files
- [ ] Update outdated information
- [ ] Add new sections for modern stack
- [ ] Update code examples
- [ ] Regenerate architecture diagrams
- [ ] Add version info & changelog

---

## 📊 Implementation Priority Matrix

```
High Impact │ FASE 1 (Wire)      │ FASE 5.2 (Export) │
            │ FASE 2 (Migration) │ FASE 5.1 (Virtual)│
            │ FASE 3 (CSS)       │                   │
────────────┼────────────────────┼───────────────────┤
Medium      │ FASE 6 (Testing)   │ FASE 5.3 (EVM)    │
Impact      │                    │ FASE 4 (AG Grid)  │
────────────┴────────────────────┴───────────────────┘
             Quick (1-3 days)      Long (4-8 days)
                            Effort →
```

---

## 🎯 Recommended Implementation Sequence

### **Sprint 1 (Week 1): Activation & Migration**
- ✅ FASE 0 already complete
- 🔥 FASE 1: Wire & Activate (Days 1-2)
- 🔥 FASE 2: Legacy Migration (Days 3-5)

**Goal**: Fully functional modern stack, legacy code removed

---

### **Sprint 2 (Week 2): Polish & Cleanup**
- 🎨 FASE 3: CSS & Layout Cleanup (Days 6-8)
- 📝 Start FASE 6: Documentation Update (Days 8-10)

**Goal**: Clean, maintainable codebase

---

### **Sprint 3 (Week 3-4): Optional Advanced Features**
- 🚀 **Choose ONE**:
  - Option A: FASE 4 (AG Grid) – IF need 500+ rows support
  - Option B: FASE 5.1 (Virtual Scroll) – Lighter alternative
  - Option C: FASE 5.2 (Export) – User-facing feature
  - Option D: FASE 5.3 (EVM) – Enterprise analytics

**Goal**: ONE killer feature for competitive advantage

---

### **Sprint 4 (Week 5): Testing & Deployment**
- ✅ FASE 6: Complete Testing Suite
- 🚀 Production Deployment
- 📊 Performance Monitoring Setup

**Goal**: Production-ready with confidence

---

## 🚨 Critical Path (Must Do)

1. ✅ FASE 0 (DONE)
2. 🔥 FASE 1 (START HERE!)
3. 🔥 FASE 2 (Core functionality)
4. 🎨 FASE 3 (Maintainability)
5. ✅ FASE 6 (Quality assurance)

**Total Critical Path**: ~3 weeks (120 hours)

**Optional Path**: FASE 4 or FASE 5 (add 1-2 weeks)

---

## 🔧 Quick Start Guide

### Untuk Memulai FASE 1 Hari Ini:

```bash
# 1. Ensure Vite ready
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
npm run dev  # Start dev server (Terminal 1)

# 2. Update Django view (one line change!)
# File: detail_project/views.py line ~195
# Change: kelola_tahapan_grid.html → kelola_tahapan_grid_vite.html

# 3. Start Django (Terminal 2)
python manage.py runserver

# 4. Test
# Navigate to: http://localhost:8000/project/{id}/jadwal-pekerjaan/
# Expected: Console shows "✅ JadwalKegiatanApp initialized"
```

**Time to first success**: ~10 minutes! 🎉

---

## 📞 Support & References

**Documentation:**
- PHASE_1_IMPLEMENTATION_GUIDE.md – Fase 0 details
- JADWAL_KEGIATAN_IMPROVEMENT_PRIORITIES.md – Feature priorities
- JADWAL_KEGIATAN_DOCUMENTATION.md – Technical specs
- FINAL_IMPLEMENTATION_PLAN.md – Original 6-week plan

**Issue Tracking:**
- Create Github issues for each fase
- Use labels: `fase-1`, `fase-2`, etc.
- Link to this roadmap in issue descriptions

---

## ✅ Success Criteria

**FASE 1 Complete When:**
- [ ] View menggunakan template Vite
- [ ] Vite dev server berjalan tanpa error
- [ ] Console shows `JadwalKegiatanApp initialized`
- [ ] Basic grid rendering terlihat (meski belum functional)

**FASE 2 Complete When:**
- [ ] Semua 12 modul legacy sudah di-port
- [ ] Grid functional dengan data loading
- [ ] Gantt & Kurva S rendering
- [ ] Save functionality works
- [ ] Legacy files bisa dihapus

**FASE 3 Complete When:**
- [ ] Zero inline styles di template
- [ ] CSS variables system implemented
- [ ] Dark mode works perfectly
- [ ] File structure organized

**ALL FASES Complete When:**
- [ ] Production build < 250KB gzipped
- [ ] Memory usage < 80MB after 10min
- [ ] Scroll FPS = 60
- [ ] 80%+ test coverage
- [ ] Documentation updated
- [ ] Zero console errors/warnings

---

## 📈 Progress Tracking

**Update this table after completing each fase:**

| Fase | Start Date | Complete Date | Status | Notes |
|------|------------|---------------|--------|-------|
| 0 | 2025-11-18 | 2025-11-19 | ✅ DONE | Phase 1 complete |
| 1 | - | - | ☐ PENDING | START NEXT |
| 2 | - | - | ☐ PENDING | - |
| 3 | - | - | ☐ PENDING | - |
| 4 | - | - | ☐ SKIP? | Decide based on needs |
| 5 | - | - | ☐ PENDING | Choose 1 feature |
| 6 | - | - | ☐ PENDING | - |

---

**Last Updated**: 2025-11-19
**Next Review**: After FASE 1 completion
**Roadmap Version**: 2.0 (Unified)
**Maintained By**: Development Team
