# Gantt Frozen Column - Execution Plan (Ready to Execute)

**Tanggal:** 2025-12-11
**Status:** ✅ APPROVED - Ready to Start
**Branch:** Current branch (dedicated for Jadwal Pekerjaan page)
**Timeline:** 10 days (2 weeks)

---

## 🚀 Quick Start

**Kita akan eksekusi di branch saat ini** (tidak perlu branch baru karena branch ini sudah dedicated untuk halaman Jadwal Pekerjaan).

### Immediate Actions

```bash
# 1. Preview cleanup (dry-run)
python cleanup_gantt_legacy.py --dry-run

# 2. Document baseline
# Screenshot current Gantt, run performance test

# 3. Start Phase 1
# Follow phase checklist below
```

---

## 📋 Phase 1: Preparation & Audit (Day 1 - TODAY)

### Checklist

**Morning (2-3 hours):**

- [ ] **1.1 Performance Baseline**
  ```bash
  # Open: http://localhost:8000/detail_project/110/kelola-tahapan/
  # Chrome DevTools > Performance tab
  # Record while:
  # - Initial load
  # - Switch to Gantt tab
  # - Scroll horizontally
  # - Scroll vertically

  # Save performance profile as: baseline_gantt_dual_panel.json
  # Note metrics:
  # - Init time: _____ ms
  # - Scroll avg: _____ ms
  # - Frame drops: _____ %
  # - Memory (5min): _____ MB
  ```

- [ ] **1.2 Visual Baseline**
  ```bash
  # Take screenshots:
  # 1. Gantt initial view (full page)
  # 2. Gantt scrolled right (showing frozen columns)
  # 3. Gantt dark mode
  # 4. Gantt responsive (narrow window)

  # Save to: docs/screenshots/baseline/
  ```

- [ ] **1.3 Functional Baseline**
  ```bash
  # Test and document current behavior:
  # - Expand/collapse hierarchy works? Y/N
  # - Scroll sync works? Y/N (note: should be buggy)
  # - Bars render? Y/N
  # - Tooltip shows? Y/N
  # - Search works? Y/N

  # Save to: docs/GANTT_BASELINE_STATE.md
  ```

**Afternoon (2-3 hours):**

- [ ] **1.4 Preview Cleanup**
  ```bash
  # Dry run to see what will be deleted/archived
  python cleanup_gantt_legacy.py --dry-run

  # Review output, make sure it's safe
  # Expected:
  # - 4 files to delete (gantt-tree-panel.js, etc)
  # - 17 docs to archive
  ```

- [ ] **1.5 Archive Legacy Documentation**
  ```bash
  # Create archive directory
  mkdir -p docs/archive/gantt/dual-panel

  # Move legacy docs (DO THIS MANUALLY to be safe)
  # Or use script to just archive docs first:
  # (modify cleanup script to only archive docs in first run)
  ```

- [ ] **1.6 Verify Current Test Status**
  ```bash
  # Run existing tests to establish baseline
  npm run test:frontend

  # Note current coverage:
  # gantt-tree-panel.js: _____ %
  # gantt-timeline-panel.js: _____ %
  # gantt-chart-redesign.js: _____ %
  # GanttCanvasOverlay.js: _____ %
  ```

**Exit Criteria:**
- ✅ Baseline performance documented
- ✅ Baseline screenshots saved
- ✅ Cleanup script previewed (dry-run)
- ✅ Current test coverage noted

---

## 📋 Phase 2: CSS Migration (Day 2)

### Checklist

**File to Edit:** `detail_project/static/detail_project/css/gantt-chart-redesign.css`

- [ ] **2.1 Backup Current CSS**
  ```bash
  cp detail_project/static/detail_project/css/gantt-chart-redesign.css \
     detail_project/static/detail_project/css/gantt-chart-redesign.css.backup
  ```

- [ ] **2.2 Remove Dual-Panel Layout**
  ```css
  /* REMOVE these sections: */
  /* .gantt-tree-panel-container { ... } */
  /* .gantt-timeline-panel-container { ... } */
  ```

- [ ] **2.3 Add Frozen Column Layout**
  ```css
  /* ADD these sections (see roadmap for full CSS) */
  .gantt-grid-container {
    display: block;
    overflow: auto;
    position: relative;
    height: 600px;
  }

  .gantt-row {
    display: flex;
    min-width: max-content;
  }

  .gantt-cell.frozen {
    position: sticky;
    left: 0; /* or cumulative for multiple frozen */
    z-index: 10;
    background: var(--bs-body-bg);
    border-right: 2px solid var(--bs-border-color);
  }

  /* Add shadow effect on frozen edge */
  .gantt-cell.frozen::after {
    content: '';
    position: absolute;
    top: 0;
    right: -2px;
    bottom: 0;
    width: 2px;
    background: linear-gradient(to right, rgba(0,0,0,0.1), transparent);
  }
  ```

- [ ] **2.4 Test CSS Changes**
  ```bash
  # Rebuild CSS
  npm run build

  # Open Gantt in browser
  # Test:
  # - Frozen columns stay fixed on horizontal scroll
  # - Shadow visible on frozen edge
  # - No layout breaks
  # - Dark mode works
  # - Responsive behavior OK
  ```

- [ ] **2.5 Visual Comparison**
  ```bash
  # Take new screenshots (same as baseline)
  # Compare with baseline screenshots
  # Verify layout is correct
  ```

**Exit Criteria:**
- ✅ Dual-panel CSS removed
- ✅ Frozen column CSS added
- ✅ Frozen columns stay fixed on scroll
- ✅ Shadow visible on frozen edge
- ✅ Dark mode works
- ✅ No visual regressions

---

## 📋 Phase 3: JS Refactor (Day 3-4)

### Checklist

**File to Edit:** `detail_project/static/detail_project/js/src/modules/gantt/gantt-chart-redesign.js`

**Day 3 Morning:**

- [ ] **3.1 Update Imports**
  ```javascript
  // REMOVE these imports:
  // import { GanttTreePanel } from './gantt-tree-panel.js';
  // import { GanttTimelinePanel } from './gantt-timeline-panel.js';

  // ADD these imports:
  import { TanStackGridManager } from '@modules/grid/tanstack-grid-manager.js';
  import { GanttCanvasOverlay } from './GanttCanvasOverlay.js';
  import { TimeColumnGenerator } from '@modules/grid/time-column-generator.js';
  ```

- [ ] **3.2 Update Constructor**
  ```javascript
  constructor(container, options = {}) {
    // ... existing code ...

    // REPLACE:
    // this.treePanel = null;
    // this.timelinePanel = null;

    // WITH:
    this.gridManager = null;
    this.canvasOverlay = null;
  }
  ```

**Day 3 Afternoon:**

- [ ] **3.3 Update _buildDOM()**
  ```javascript
  _buildDOM() {
    this.container.innerHTML = '';

    // Create single grid container
    const gridContainer = document.createElement('div');
    gridContainer.className = 'gantt-grid-container';
    gridContainer.id = 'gantt-grid-main';

    this.container.appendChild(gridContainer);
    this.gridContainer = gridContainer;
  }
  ```

- [ ] **3.4 Update _createComponents()**
  ```javascript
  async _createComponents() {
    // Initialize TanStackGridManager
    this.gridManager = new TanStackGridManager(this.state, {
      rowHeight: this.options.rowHeight,
      inputMode: 'percentage'
    });

    // Mount grid
    this.gridManager.mount(this.gridContainer);

    // Initialize canvas overlay
    this.canvasOverlay = new GanttCanvasOverlay(this.gridManager);

    console.log('✅ Gantt components created (frozen column mode)');
  }
  ```

**Day 4 Morning:**

- [ ] **3.5 Add _buildGanttColumns()**
  ```javascript
  _buildGanttColumns() {
    const frozenColumns = [
      {
        field: 'name',
        headerName: 'Pekerjaan',
        width: 250,
        meta: { pinned: true, align: 'start' }
      },
      {
        field: 'volume',
        headerName: 'Volume',
        width: 80,
        meta: { pinned: true, align: 'end' }
      },
      {
        field: 'satuan',
        headerName: 'Satuan',
        width: 80,
        meta: { pinned: true, align: 'center' }
      }
    ];

    // Generate timeline columns
    const timelineColumns = TimeColumnGenerator.generateColumns(
      this.state.tahapanList,
      this.state.timeScale
    );

    return {
      frozen: frozenColumns,
      timeline: timelineColumns,
      all: [...frozenColumns, ...timelineColumns]
    };
  }
  ```

- [ ] **3.6 Add _buildGanttRows()**
  ```javascript
  _buildGanttRows() {
    const flatData = this.dataModel.getFlatData();

    return flatData.map(node => ({
      id: node.id,
      name: node.name,
      volume: node.volume || '-',
      satuan: node.satuan || '-',
      level: node.level,
      subRows: node.children?.length > 0 ?
        this._buildGanttRows(node.children) : undefined,
      raw: node
    }));
  }
  ```

**Day 4 Afternoon:**

- [ ] **3.7 Update render()**
  ```javascript
  render() {
    if (!this.state.initialized || this.state.loading) return;

    // Build columns
    const columns = this._buildGanttColumns();

    // Build rows
    const rows = this._buildGanttRows();

    // Update grid
    this.gridManager.updateData({
      tree: rows,
      timeColumns: columns.timeline,
      inputMode: this.state.mode,
      timeScale: this.state.timeScale
    });

    // Show canvas overlay
    this.canvasOverlay.show();

    // Render bars
    this._renderBars();
  }
  ```

- [ ] **3.8 Add _renderBars() with StateManager**
  ```javascript
  _renderBars() {
    const barData = this._computeBarData();
    this.canvasOverlay.renderBars(barData);
  }

  _computeBarData() {
    const bars = [];

    this.state.tahapanList.forEach(tahapan => {
      this.dataModel.getFlatData().forEach(pekerjaan => {
        const planned = this.stateManager.getCellValue(
          pekerjaan.id,
          tahapan.column_id,
          'planned'
        ) || 0;

        const actual = this.stateManager.getCellValue(
          pekerjaan.id,
          tahapan.column_id,
          'actual'
        ) || 0;

        if (planned > 0 || actual > 0) {
          bars.push({
            pekerjaanId: pekerjaan.id,
            columnId: tahapan.column_id,
            planned: planned,
            actual: actual,
            variance: actual - planned,
            label: pekerjaan.name,
            color: this._getBarColor(actual - planned)
          });
        }
      });
    });

    return bars;
  }

  _getBarColor(variance) {
    if (variance > 0.1) return '#22c55e'; // Green (ahead)
    if (variance < -0.1) return '#ef4444'; // Red (behind)
    return '#3b82f6'; // Blue (on track)
  }
  ```

- [ ] **3.9 Add StateManager Event Listeners**
  ```javascript
  _setupStateListeners() {
    this.stateManager.on('cell:updated', (event) => {
      const { field } = event;
      if (field === 'planned' || field === 'actual') {
        this._renderBars();
      }
    });

    this.stateManager.on('bulk:updated', () => {
      this._renderBars();
    });

    this.stateManager.on('mode:changed', (mode) => {
      this.state.mode = mode;
      this._renderBars();
    });
  }

  // Call in initialize()
  initialize(rawData) {
    // ... existing code ...
    this._setupStateListeners();
    // ... existing code ...
  }
  ```

- [ ] **3.10 Remove Old Methods**
  ```javascript
  // DELETE these methods:
  // _setupSync() - No longer needed
  // Any manual scroll sync handlers
  // Any coordinate conversion functions
  ```

- [ ] **3.11 Test Refactored Code**
  ```bash
  # Rebuild
  npm run build

  # Test in browser:
  # - Gantt loads without errors
  # - Bars render correctly
  # - Bars align with grid cells
  # - No scroll sync issues
  # - Expand/collapse works
  ```

**Exit Criteria:**
- ✅ No imports of gantt-tree-panel.js or gantt-timeline-panel.js
- ✅ TanStackGridManager integrated
- ✅ StateManager events hooked up
- ✅ Bars render and align perfectly
- ✅ No scroll sync code remaining
- ✅ No console errors

---

## 📋 Phase 4: Cleanup (Day 5 Morning)

### Checklist

- [ ] **4.1 Run Cleanup Script**
  ```bash
  # Final check with dry-run
  python cleanup_gantt_legacy.py --dry-run

  # If everything looks good, execute:
  python cleanup_gantt_legacy.py
  # Confirm with 'yes' when prompted
  ```

- [ ] **4.2 Verify No Broken Imports**
  ```bash
  # Check for any remaining imports
  grep -r "gantt-tree-panel" detail_project/static/
  grep -r "gantt-timeline-panel" detail_project/static/

  # Should return nothing
  ```

- [ ] **4.3 Rebuild Everything**
  ```bash
  # Clean build
  rm -rf detail_project/static/detail_project/dist/
  npm run build

  # Collect static
  python manage.py collectstatic --no-input
  ```

- [ ] **4.4 Smoke Test**
  ```bash
  # Open Gantt page
  # Verify:
  # - Page loads
  # - No console errors
  # - Gantt renders
  # - Bars show
  # - Interactions work
  ```

**Exit Criteria:**
- ✅ 4 legacy files deleted
- ✅ 17 docs archived to docs/archive/gantt/dual-panel/
- ✅ No broken imports
- ✅ Gantt functional
- ✅ Clean build successful

---

## 📋 Phase 5: Testing & QA (Day 5-6)

### Checklist

**Day 5 Afternoon:**

- [ ] **5.1 Run Test Suite**
  ```bash
  # Run all frontend tests
  npm run test:frontend

  # Run with coverage
  npm run test:frontend -- --coverage

  # Check coverage report
  # Target: >85% overall
  ```

- [ ] **5.2 Integration Tests**
  ```bash
  # Create new test file:
  # detail_project/static/detail_project/js/tests/gantt-frozen-integration.test.js

  # Test:
  # - TanStackGridManager integration
  # - Frozen columns stay fixed
  # - Canvas overlay clips correctly
  # - Bars align with cells
  # - StateManager events trigger re-render
  ```

- [ ] **5.3 Performance Benchmarks**
  ```bash
  # Run same performance test as baseline
  # Compare with baseline:

  # Target improvements:
  # - Init time: <600ms (from ~800ms)
  # - Scroll: <15ms (from ~25ms)
  # - Frame drops: <5% (from ~15%)
  # - Memory: <100MB (from ~120MB)
  ```

**Day 6:**

- [ ] **5.4 Manual QA Checklist**

  **Frozen Columns:**
  - [ ] Frozen columns stay fixed on horizontal scroll
  - [ ] Shadow/border visible on frozen edge
  - [ ] No gaps between frozen and scrollable area
  - [ ] Frozen columns don't overlap bars

  **Canvas Overlay:**
  - [ ] Bars never overlap frozen columns
  - [ ] Bars align perfectly with timeline cells
  - [ ] Tooltip shows correct data on hover
  - [ ] Bars update when Grid View data changes

  **Scroll Behavior:**
  - [ ] Smooth horizontal scroll (no jank)
  - [ ] Smooth vertical scroll
  - [ ] No scroll sync issues
  - [ ] Touch scroll works on mobile

  **Responsiveness:**
  - [ ] Works on desktop (>1200px)
  - [ ] Works on tablet (768px-1199px)
  - [ ] Works on mobile (≥576px)
  - [ ] Frozen columns adjust on resize

  **Dark Mode:**
  - [ ] Frozen column background matches theme
  - [ ] Shadow visible in dark mode
  - [ ] Canvas bars visible in dark mode
  - [ ] No contrast issues

  **Data Integration:**
  - [ ] Update cell in Grid View → Gantt updates
  - [ ] Bars reflect correct planned/actual values
  - [ ] Variance colors correct (green/red/blue)
  - [ ] No data inconsistencies

- [ ] **5.5 Visual Regression Tests**
  ```bash
  # Compare screenshots:
  # - New frozen column vs baseline dual-panel
  # - Document differences (expected changes)
  # - No unexpected visual changes
  ```

- [ ] **5.6 Rollback Test (on local/staging)**
  ```bash
  # Simulate rollback procedure:

  # 1. Commit current frozen column changes
  git add .
  git commit -m "WIP: Frozen column implementation"

  # 2. Test rollback
  git revert HEAD --no-edit

  # 3. Verify dual-panel restored
  npm run build
  # Check Gantt works

  # 4. Re-apply frozen column
  git revert HEAD --no-edit
  npm run build

  # 5. Document rollback procedure works
  ```

**Exit Criteria:**
- ✅ All tests pass (>85% coverage)
- ✅ Manual QA checklist 100% complete
- ✅ Performance benchmarks met
- ✅ Visual regression acceptable
- ✅ Rollback procedure tested and works

---

## 📋 Phase 6: Rollout (Day 7-8)

### Checklist

**Day 7: Staging Deployment**

- [ ] **6.1 Deploy to Staging**
  ```bash
  # If you have staging environment:
  # Deploy frozen column version
  # Run smoke tests
  ```

- [ ] **6.2 UAT Testing**
  ```bash
  # User Acceptance Testing:
  # - Invite stakeholders to test
  # - Collect feedback
  # - Fix any issues found
  ```

**Day 8: Production Deployment**

- [ ] **6.3 Final Checks**
  ```bash
  # Pre-deployment checklist:
  # - All tests pass: ✓
  # - QA approved: ✓
  # - Performance benchmarks met: ✓
  # - Rollback tested: ✓
  # - Team briefed: ✓
  ```

- [ ] **6.4 Deploy to Production**
  ```bash
  # Build production bundle
  npm run build

  # Collect static files
  python manage.py collectstatic --no-input

  # Restart application
  # (depends on your deployment setup)
  ```

- [ ] **6.5 Monitor (24 hours)**
  ```bash
  # Monitor for:
  # - Console errors (browser devtools)
  # - Server errors (logs)
  # - Performance metrics
  # - User feedback
  # - Alignment issues
  ```

- [ ] **6.6 Document Lessons Learned**
  ```markdown
  # Create: docs/GANTT_FROZEN_COLUMN_RETROSPECTIVE.md

  ## What Went Well
  - ...

  ## What Could Be Improved
  - ...

  ## Metrics Achieved
  - Init time: ___ ms (target: <600ms)
  - Scroll: ___ ms (target: <15ms)
  - Coverage: ___ % (target: >85%)

  ## Issues Encountered
  - ...

  ## Recommendations for Next Migration
  - ...
  ```

**Exit Criteria:**
- ✅ Production deployed successfully
- ✅ No critical bugs reported
- ✅ Performance metrics healthy
- ✅ Zero alignment complaints
- ✅ Team satisfied with result

---

## 📊 Progress Tracking

Update this table daily:

| Phase | Status | Start Date | End Date | Notes |
|-------|--------|------------|----------|-------|
| Phase 1: Preparation | 📋 Pending | | | |
| Phase 2: CSS Migration | 📋 Pending | | | |
| Phase 3: JS Refactor | 📋 Pending | | | |
| Phase 4: Cleanup | 📋 Pending | | | |
| Phase 5: Testing | 📋 Pending | | | |
| Phase 6: Rollout | 📋 Pending | | | |

**Legend:**
- 📋 Pending
- 🔄 In Progress
- ✅ Complete
- ❌ Blocked

---

## 🆘 Troubleshooting

### Issue: Frozen columns not sticky

**Solution:**
```css
.gantt-cell.frozen {
  position: sticky !important;
  left: 0 !important;
  z-index: 10 !important;
}
```

### Issue: Bars overlap frozen columns

**Solution:**
```javascript
// Verify GanttCanvasOverlay clip-path
const pinnedWidth = this.gridManager.getPinnedColumnsWidth();
console.log('Pinned width:', pinnedWidth);
console.log('Canvas clip-path:', this.canvasOverlay.canvas.style.clipPath);

// Should be: inset(0px 0px 0px ${pinnedWidth}px)
```

### Issue: TanStackGridManager not found

**Solution:**
```bash
# Check import path
# Should be: @modules/grid/tanstack-grid-manager.js
# Verify file exists at:
# detail_project/static/detail_project/js/src/modules/grid/tanstack-grid-manager.js
```

### Issue: StateManager events not firing

**Solution:**
```javascript
// Verify StateManager initialized
console.log('StateManager:', this.stateManager);

// Verify event registration
this.stateManager.on('cell:updated', (event) => {
  console.log('Cell updated:', event);
  this._renderBars();
});

// Test manually
this.stateManager.updateCell('test-id', 'test-column', 'actual', 50);
```

---

## 📞 Need Help?

**During execution, if you encounter issues:**

1. Check troubleshooting section above
2. Review roadmap details: [GANTT_FROZEN_COLUMN_ROADMAP.md](detail_project/docs/GANTT_FROZEN_COLUMN_ROADMAP.md)
3. Check validation report: [GANTT_FROZEN_COLUMN_VALIDATION.md](detail_project/docs/GANTT_FROZEN_COLUMN_VALIDATION.md)
4. Ask me! I can help debug specific issues

---

**Ready to Start?** Begin with Phase 1 checklist above! 🚀

**Prepared by:** Claude Code
**Date:** 2025-12-11
**Status:** READY TO EXECUTE
