# Migration Cleanup Checklist - Extended Version

**Document:** Extended cleanup plan untuk AG-Grid + ECharts removal
**Created:** 2025-12-04
**Status:** READY FOR EXECUTION (setelah Phase 3 complete)

---

## ⚠️ **IMPORTANT: TIMING**

**JANGAN jalankan cleanup ini sampai:**
- ✅ Phase 3 (CSS extraction) selesai
- ✅ Production rollout 100% sukses
- ✅ Feature flags permanently enabled atau dihapus
- ✅ Stakeholder approval untuk final removal
- ✅ Rollback sudah tidak diperlukan

**Current Readiness:** ⏳ **80%** (Phase 1-2 done, Phase 3 pending)

---

## 📋 Part 1: NPM Dependencies Cleanup

### Step 1.1: Uninstall Old Libraries

```bash
# Navigate to project root
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"

# Uninstall deprecated dependencies
npm uninstall ag-grid-community echarts frappe-gantt

# Clean up orphaned packages
npm prune

# Verify package.json updated
cat package.json | grep -E "ag-grid|echarts|frappe"
# Expected: (nothing)
```

### Step 1.2: Verify node_modules Cleanup

```bash
# Check AG-Grid removed
ls node_modules/ | grep ag-grid
# Expected: (nothing)

# Check ECharts removed
ls node_modules/ | grep echarts
# Expected: (nothing)

# Check Frappe Gantt removed
ls node_modules/ | grep frappe
# Expected: (nothing)
```

### Step 1.3: Reinstall & Rebuild

```bash
# Reinstall remaining dependencies
npm install

# Rebuild bundle
npm run build

# Verify build success
ls -lh detail_project/static/detail_project/dist/assets/js/*.js
```

**Expected package.json after cleanup:**
```json
{
  "dependencies": {
    "@tanstack/table-core": "^8.20.5",    // ✅ Grid replacement
    "@tanstack/virtual-core": "^3.10.8",  // ✅ Virtual scrolling
    "uplot": "^1.6.30",                   // ✅ Chart replacement
    "html2canvas": "^1.4.1",              // ✅ Export (keep)
    "jspdf": "^2.5.1",                    // ✅ PDF export (keep)
    "xlsx": "^0.18.5"                     // ✅ Excel export (keep)
  }
}
```

---

## 📂 Part 2: Source Files Cleanup

### Step 2.1: Files CONFIRMED for Deletion

Based on actual codebase scan:

```bash
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\src"

# 1. AG-Grid implementation (988 KB dependency removed)
rm modules/grid/ag-grid-setup.js

# 2. ECharts implementation (320 KB dependency removed)
rm modules/kurva-s/echarts-setup.js

# 3. ECharts helper functions
rm modules/kurva-s/week-zero-helpers.js

# 4. Frappe Gantt (deprecated, replaced by Gantt V2)
rm modules/gantt/frappe-gantt-setup.js
```

### Step 2.2: Files to Keep (Already Verified)

**DO NOT DELETE:**
- ✅ `modules/grid/tanstack-grid-manager.js` - New TanStack implementation
- ✅ `modules/kurva-s/uplot-chart.js` - New uPlot implementation
- ✅ `modules/kurva-s/dataset-builder.js` - Shared data adapter
- ✅ `modules/gantt-v2/gantt-frozen-grid.js` - Gantt V2 (current)
- ✅ `modules/core/state-manager.js` - Core state management
- ✅ `modules/shared/chart-utils.js` - Shared utilities (buildHargaLookup, etc.)
- ✅ `jadwal_kegiatan_app.js` - Main app (remove old imports only)

---

## 🔧 Part 3: Code Import Cleanup

### Step 3.1: Update jadwal_kegiatan_app.js

**File:** `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`

**Current state (lines 8-10, 16-18):**
```javascript
import { AGGridManager } from '@modules/grid/ag-grid-setup.js';  // ❌ REMOVE
import { TanStackGridManager } from '@modules/grid/tanstack-grid-manager.js';  // ✅ KEEP

// Chart modules now lazy loaded
// import { KurvaSChart } from '@modules/kurva-s/echarts-setup.js';  // ❌ REMOVE (commented)
// import { GanttChart } from '@modules/gantt/frappe-gantt-setup.js'; // ❌ REMOVE (commented)
```

**After cleanup:**
```javascript
// Only TanStack Grid import (AG-Grid removed)
import { TanStackGridManager } from '@modules/grid/tanstack-grid-manager.js';

// Lazy loading via dynamic import() - already implemented
// See lines 1776-1788 for lazy load logic
```

**Changes needed:**
1. Remove `import { AGGridManager }` line
2. Remove commented ECharts/Frappe imports
3. Remove `this.agGridManager` property references
4. Remove `_initAgGridIfNeeded()` method
5. Remove `useAgGrid` flag logic (always use TanStack)

### Step 3.2: Search for Remaining References

```bash
# Find all AG-Grid imports
grep -r "from.*ag-grid" detail_project/static/detail_project/js/src/

# Find all ECharts imports
grep -r "from.*echarts" detail_project/static/detail_project/js/src/

# Find AGGridManager usage
grep -r "AGGridManager" detail_project/static/detail_project/js/src/

# Find KurvaSChart (ECharts class) usage
grep -r "KurvaSChart" detail_project/static/detail_project/js/src/
```

**Expected after cleanup:** Only lazy-load references in `jadwal_kegiatan_app.js` for feature flag logic (which will also be removed in Step 4)

---

## 🚩 Part 4: Feature Flag Removal

### Step 4.1: Template Cleanup

**File:** `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html`

**Current state (lines 245-247):**
```html
data-enable-ag-grid="{% if enable_ag_grid %}true{% else %}false{% endif %}"
data-enable-tanstack-grid="{% if enable_tanstack_grid %}true{% else %}false{% endif %}"
data-enable-uplot-kurva="{% if enable_uplot_kurva %}true{% else %}false{% endif %}"
```

**After cleanup:**
```html
data-enable-uplot-kurva="true"
<!-- atribut TanStack/AG Grid dihapus karena selalu aktif -->
```

**Note:** Template conditional rendering juga harus dihapus (lines 308-312)

### Step 4.2: Settings Cleanup

**File:** `config/settings/base.py` (or equivalent)

**Remove these settings:**
```python
# (Removed Jan 2026) TanStack grid + uPlot sekarang default sehingga tidak ada flag lagi.
```

**Context variables to remove from view:**
```python
# View context sudah dibersihkan (tidak ada kunci enable_ag_grid / enable_tanstack_grid / enable_uplot_kurva).
```

### Step 4.3: JavaScript Flag Logic Cleanup

**File:** `jadwal_kegiatan_app.js`

**Remove these state properties (lines 182-184):**
```javascript
useAgGrid: true,           // ❌ REMOVE
useTanStackGrid: false,    // ❌ REMOVE (always true now)
useUPlotKurva: false,      // ❌ REMOVE (always true now)
```

**Remove flag reading logic (lines 615-621):**
```javascript
this.state.useAgGrid = dataset.enableAgGrid === 'true' || this.state.useAgGrid;           // ❌ REMOVE
this.state.useTanStackGrid = dataset.enableTanstackGrid === 'true' || this.state.useTanStackGrid;  // ❌ REMOVE
this.state.useUPlotKurva = dataset.enableUplotKurva === 'true' || this.state.useUPlotKurva;      // ❌ REMOVE

if (this.state.useTanStackGrid) {
  this.state.useAgGrid = false;  // ❌ REMOVE
}
```

**Remove conditional imports (lines 1776-1788):**
```javascript
// OLD - Conditional chart loading
const kurvaSPromise = this.state.useUPlotKurva
  ? import('@modules/kurva-s/uplot-chart.js')
  : import('@modules/kurva-s/echarts-setup.js');  // ❌ ECharts removed

// NEW - Always load uPlot
const kurvaSPromise = import('@modules/kurva-s/uplot-chart.js');
```

---

## 🧪 Part 5: Build Artifacts Verification

### Step 5.1: Bundle Size Verification

```bash
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"

# Build production bundle
npm run build

# Check bundle sizes
ls -lh detail_project/static/detail_project/dist/assets/js/*.js

# Expected bundles (WITHOUT ag-grid/echarts):
# - chart-modules-*.js (uPlot + Gantt V2)
# - grid-modules-*.js (TanStack Table)
# - jadwal-kegiatan-*.js (Main app)
# - vendor-export-*.js (html2canvas, jsPDF, xlsx)

# Should NOT exist:
# - vendor-ag-grid-*.js ❌
# - Any file with "echarts" in name ❌
```

### Step 5.2: No CDN References

```bash
# Verify no CDN dependencies in bundle
grep -r "cdn.jsdelivr" detail_project/static/detail_project/dist/
grep -r "unpkg.com" detail_project/static/detail_project/dist/

# Expected: (nothing)
```

### Step 5.3: Dependency Audit

```bash
# Check no deprecated packages
npm list --depth=0

# Expected output should show:
# ✅ @tanstack/table-core@8.20.5
# ✅ @tanstack/virtual-core@3.10.8
# ✅ uplot@1.6.30
# ❌ ag-grid-community (should NOT exist)
# ❌ echarts (should NOT exist)
# ❌ frappe-gantt (should NOT exist)

# Security audit
npm audit
# Expected: No high/critical vulnerabilities
```

---

## 📊 Part 6: Expected Savings

### Before Cleanup

```
Total Bundle: 1,353 KB (raw) / 420 KB (gzip)
├─ AG-Grid: 988 KB (73%)        ← TO BE REMOVED
├─ ECharts: 320 KB (24%)        ← TO BE REMOVED
├─ Main App: 34 KB (2.5%)
└─ Gantt V2: 11 KB (0.8%)
```

### After Cleanup

```
Total Bundle: 174 KB (raw) / 61 KB (gzip) ← -87.2% reduction
├─ TanStack Table: 14 KB (8%)
├─ TanStack Virtual: 3 KB (2%)
├─ uPlot: 45 KB (26%)
├─ Main App: 70 KB (40%)        ← Grows +36 KB (custom logic)
├─ Gantt V2: 11 KB (6%)
└─ Other: 31 KB (18%)
```

### Savings Summary

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| **Raw Bundle** | 1,353 KB | 174 KB | **-1,179 KB (-87.1%)** |
| **Gzipped** | 420 KB | 61 KB | **-359 KB (-85.5%)** |
| **Dependencies** | 6 | 6 | 0 (replaced, not added) |
| **node_modules/** | ~150 MB | ~50 MB | **-100 MB (-67%)** |

---

## ✅ Part 7: Verification Checklist

### Pre-Cleanup Verification

Before running cleanup, verify:

- [ ] Phase 1 (TanStack Grid) production tested 100%
- [ ] Phase 2 (uPlot Kurva-S) production tested 100%
- [ ] Phase 3 (CSS extraction) complete
- [ ] Feature flags removed from all environments (dev/staging/prod)
- [ ] Rollback plan no longer needed (>30 days stable)
- [ ] Stakeholder approval obtained
- [ ] Backup created: `git commit -m "Pre-cleanup snapshot"`

### Post-Cleanup Verification

After running cleanup, verify:

- [ ] `npm install` runs without errors
- [ ] `npm run build` succeeds
- [ ] Bundle size < 200 KB (target: 174 KB)
- [ ] No AG-Grid chunks in `dist/assets/js/`
- [ ] No ECharts chunks in `dist/assets/js/`
- [ ] `npm list` shows only 6 dependencies
- [ ] `npm audit` shows no vulnerabilities
- [ ] `grep -r "ag-grid" src/` returns nothing
- [ ] `grep -r "echarts" src/` returns nothing (except comments)
- [ ] Dev server starts: `python manage.py runserver`
- [ ] Page loads without console errors
- [ ] Grid View renders correctly
- [ ] Kurva-S renders correctly
- [ ] Gantt V2 renders correctly
- [ ] All CRUD operations work
- [ ] Theme switching works
- [ ] Export to PNG/PDF/Excel works

---

## 🚨 Part 8: Rollback Plan (If Cleanup Fails)

### Emergency Rollback

```bash
# 1. Revert git commit
git revert HEAD

# 2. Reinstall old dependencies
npm install ag-grid-community@^31.0.0 echarts@^6.0.0 frappe-gantt@^1.0.4

# 3. Restore deleted files from git
git checkout HEAD~1 -- detail_project/static/detail_project/js/src/modules/grid/ag-grid-setup.js
git checkout HEAD~1 -- detail_project/static/detail_project/js/src/modules/kurva-s/echarts-setup.js

# 4. Rebuild
npm run build

# 5. Restart server
python manage.py runserver
```

### Partial Rollback (Keep TanStack, Restore ECharts)

If only uPlot has issues:

```bash
# Reinstall ECharts only
npm install echarts@^6.0.0

# Restore ECharts files
git checkout HEAD~1 -- detail_project/static/detail_project/js/src/modules/kurva-s/echarts-setup.js

# Update app to use ECharts conditionally
# (Set useUPlotKurva = false in jadwal_kegiatan_app.js)

# Rebuild
npm run build
```

---

## 📝 Part 9: Additional Cleanup Recommendations

### 9.1 CSS Cleanup (Phase 3 Task)

```bash
# After CSS extraction complete, remove inline styles:
# 1. AG-Grid inline styles in templates
# 2. ECharts theme inline CSS
# 3. Unused CSS classes (.ag-theme-alpine, etc.)
```

### 9.2 Test File Cleanup

```bash
# Update test files to remove AG-Grid references
# File: detail_project/tests/test_jadwal_pekerjaan_page_ui.py

# Remove AG-Grid test cases:
# - test_ag_grid_renders()
# - test_ag_grid_cell_edit()
# etc.
```

### 9.3 Documentation Cleanup

```bash
# Update README files to remove AG-Grid/ECharts mentions
# Update architecture diagrams
# Update deployment guides
```

---

## 🎯 Part 10: Success Criteria

### All cleanup successful if:

✅ **Bundle size:** < 200 KB (target: 174 KB)
✅ **Build time:** < 30 seconds
✅ **Zero console errors** in production
✅ **All features working:** Grid, Gantt, Kurva-S, Export
✅ **Performance:** First paint < 1s, 60fps scrolling
✅ **No regressions:** All tests pass
✅ **Clean dependencies:** Only 6 packages in package.json
✅ **No dead code:** grep finds no ag-grid/echarts references

---

## 📅 Recommended Timeline

### Phase 3 (Current) - Week 1
- [ ] Complete CSS extraction
- [ ] Run Day 8B offline verification tests
- [ ] Final QA round

### Cleanup Phase - Week 2
- [ ] Execute Part 1-4 (Dependencies + Files + Imports + Flags)
- [ ] Run verification checklist (Part 7)
- [ ] Monitor production for 48 hours

### Stabilization - Week 3
- [ ] Address any issues found
- [ ] Complete documentation updates
- [ ] Archive old implementation files (don't delete yet)

### Final Removal - Week 4
- [ ] If no issues, permanently delete archived files
- [ ] Close migration project
- [ ] Celebrate! 🎉

---

## 📞 Support

**If cleanup encounters issues:**
1. Check rollback plan (Part 8)
2. Review verification checklist (Part 7)
3. Consult migration roadmap v1.2
4. Check implementation verification report

**Files to reference:**
- `MIGRATION_ROADMAP_TANSTACK_UPLOT.md` (main roadmap)
- `PHASE_1_2_IMPLEMENTATION_VERIFICATION.md` (implementation review)
- `MIGRATION_VERIFICATION_CHECKLIST.md` (audit results)

---

**End of Cleanup Checklist**

**Status:** READY FOR EXECUTION (after Phase 3)
**Created:** 2025-12-04
**Last Updated:** 2025-12-04
**Version:** 1.0 (Extended from roadmap Part 4)
### Phase 3 Step 1 Audit (Des 2025)

**Status:** Audit selesai; ekstraksi CSS & refactor template masih pending.

**Temuan Utama:**
- `detail_project/static/detail_project/css/kelola_tahapan_grid.css`
  - Masih memuat >20 selector `ag-*` (mis. `.ag-grid-wrapper`, `.ag-theme-alpine .ag-header`, `.ag-row.row-has-error`, `.ag-cell.ag-cell-invalid`, dll.) lengkap dengan varian dark-mode.
  - Blok khusus `ag-pekerjaan-label`, `ag-volume-col`, `ag-unit-col` mengatur layout kolom AG Grid lama. Siapkan padanan `.tanstack-grid` bila fitur tersebut tetap dibutuhkan.
- `detail_project/staticfiles/detail_project/css/kelola_tahapan_grid.css` (artefak collectstatic) menyimpan selector identik; akan ikut terbersihkan setelah sumber utama diekstrak.
- Template `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html`
  - Masih memuat CDN CSS `ag-grid-community@31` (ag-grid.css, ag-theme-alpine, ag-theme-alpine-dark).
  - Kontainer `div.ag-grid-section` + atribut `data-enable-ag-grid` aktif secara default; perlu dipagari supaya hanya muncul saat legacy flag ON.

**Tindak Lanjut:**
1. Pindahkan seluruh style `.ag-*` ke `ag-grid-legacy.css` dan load hanya jika `ENABLE_AG_GRID=True`.
2. Siapkan stylesheet baru untuk TanStack grid (`.tanstack-grid-wrapper`, state error/warning) lalu update referensinya.
3. Ubah template `kelola_tahapan_grid_modern.html` agar CDN AG Grid hanya dimuat ketika legacy flag aktif; jalur default memakai bundel TanStack.
4. Revisi checklist ini setelah modul CSS baru siap sebelum lanjut Step 2 (offline verification).
### Phase 3 Step 3 Plan (Dependency Cleanup Preparation)

**Tujuan:** Menyiapkan rencana detail sebelum Phase 4 mengeksekusi penghapusan AG Grid + ECharts dari stack.

**Aksi Utama:**
1. **Paket yang akan dihapus**
   - npm: `ag-grid-community`, `echarts`, `frappe-gantt`.
   - CSS legacy: `static/detail_project/css/ag-grid-legacy.css` hanya dipertahankan sampai Phase 4 selesai; tandai untuk penghapusan.
   - Modul JS: `static/detail_project/js/src/modules/grid/ag-grid-setup.js`, `static/detail_project/js/src/modules/kurva-s/echarts-setup.js`, serta referensi di `jadwal_kegiatan_app.js`, `templates/detail_project/kelola_tahapan_grid_modern.html`.
2. **Langkah eksekusi (Phase 4)**
   ```bash
   npm uninstall ag-grid-community echarts frappe-gantt
   # Hapus import/require yang tersisa pada file JS
   # Hapus CSS legacy + CDN tag pada template legacy
   npm run build
   python -m pytest detail_project/tests/test_jadwal_pekerjaan_page_ui.py --no-cov
   ```
3. **Rollback Plan**
   - Jalankan `npm install ag-grid-community@^31 echarts@^6 frappe-gantt@^1.0.4`.
   - Restore file-file legacy dari git (ag-grid-legacy.css, ag-grid-setup.js, echarts-setup.js, template) lalu `npm run build`.
   - Update view untuk memakai template legacy dan lakukan sanity check manual sebelum re-open user akses.
4. **Dokumentasi & Komunikasi**
   - Catat status Phase 4 di roadmap + checklist ketika dieksekusi.
   - Siapkan pengumuman singkat untuk tim infra/QA sebelum melakukan uninstall di staging/produksi.
