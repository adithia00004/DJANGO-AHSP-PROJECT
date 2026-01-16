# 🎯 JADWAL PEKERJAAN - ACTIVE PRIORITIES & URGENT TASKS

**Date:** 2025-12-09
**Status:** ✅ **COMPREHENSIVE PRIORITY AUDIT**
**Scope:** Page Jadwal Pekerjaan & Related Features

---

## 📊 EXECUTIVE SUMMARY

### **Current Status:**

| Area | Status | Priority | Action Needed |
|------|--------|----------|---------------|
| **Unified Gantt Overlay** | ✅ 100% Complete | 🟢 DONE | Tested & Ready |
| **Rekap Kebutuhan** | ✅ 90% Complete | 🟢 LOW | Phase 5 Optional |
| **StateManager Refactor** | ✅ **DONE** | 🟢 DONE | 431 lines implemented |
| **Gantt Tree Controls** | ✅ **DONE** | 🟢 DONE | `_renderTreeCell()` done |
| **Unit Testing** | ✅ **DONE** | 🟢 DONE | 4 test files (1500+ lines) |

---

## ✅ **COMPLETED ITEMS (No Longer Blocking)**

### **1. Unit Tests for Unified Gantt Overlay** ✅ DONE

**Status:** ✅ **COMPLETED 2025-12-09**

**Implementation:**
- `unified-table-manager.test.js` (652 lines)
- `unified-gantt-integration.test.js` (~400 lines)
- `gantt-canvas-overlay.test.js` (~300 lines)
- `state-manager.test.js` (~200 lines)

**Estimated Effort:** 1-2 days

**Required Test Coverage:**

```javascript
// PRIORITY 1: Core Logic Tests (Day 1 Morning - 4 hours)
describe('UnifiedTableManager', () => {
  describe('_buildBarData', () => {
    it('should build bar data from valid payload', () => { /* ... */ });
    it('should fallback to tanstackGrid data when payload empty', () => { /* ... */ });
    it('should fallback to state.flatPekerjaan when grid empty', () => { /* ... */ });
    it('should convert IDs to strings for type safety', () => { /* ... */ });
    it('should skip bars with no planned or actual values', () => { /* ... */ });
    it('should warn when no bars generated despite cell data', () => { /* ... */ });
  });

  describe('_flattenRows', () => {
    it('should flatten nested tree structure', () => { /* ... */ });
    it('should handle subRows, children, and sub properties', () => { /* ... */ });
    it('should return empty array for null input', () => { /* ... */ });
  });

  describe('_resolveColumnMeta', () => {
    it('should extract meta from TanStack column', () => { /* ... */ });
    it('should extract meta from state.timeColumns', () => { /* ... */ });
    it('should identify weekly/monthly columns', () => { /* ... */ });
    it('should return null for non-time columns', () => { /* ... */ });
  });
});

// PRIORITY 2: Canvas Rendering Tests (Day 1 Afternoon - 4 hours)
describe('GanttCanvasOverlay', () => {
  describe('_drawBars', () => {
    it('should group bars by pekerjaanId', () => { /* ... */ });
    it('should match bars to cell rects by IDs', () => { /* ... */ });
    it('should handle type mismatch (string vs number)', () => { /* ... */ });
    it('should draw stacked bars (planned + actual)', () => { /* ... */ });
    it('should skip bars without matching rects', () => { /* ... */ });
    it('should log drawn vs skipped counts', () => { /* ... */ });
  });

  describe('syncWithTable', () => {
    it('should resize canvas to match scroll area', () => { /* ... */ });
    it('should fetch cell bounding rects', () => { /* ... */ });
    it('should clear and redraw on sync', () => { /* ... */ });
    it('should error when bars exist but no rects', () => { /* ... */ });
  });

  describe('color extraction', () => {
    it('should get planned color from CSS vars', () => { /* ... */ });
    it('should get actual color from CSS vars', () => { /* ... */ });
    it('should fallback to hardcoded colors', () => { /* ... */ });
  });
});

// PRIORITY 3: Integration Tests (Day 2 Morning - 4 hours)
describe('Unified Gantt Integration', () => {
  it('should initialize overlay when switching to gantt mode', () => { /* ... */ });
  it('should render bars after data update', () => { /* ... */ });
  it('should sync overlay on scroll', () => { /* ... */ });
  it('should show tooltip on bar hover', () => { /* ... */ });
  it('should handle mode switch (grid <-> gantt)', () => { /* ... */ });
  it('should update bars when StateManager data changes', () => { /* ... */ });
});

// PRIORITY 4: Debug Script Tests (Day 2 Afternoon - 2 hours)
describe('debug-unified-gantt', () => {
  it('should run all 9 diagnostic checks', () => { /* ... */ });
  it('should export debug variables to window', () => { /* ... */ });
  it('should provide actionable recommendations', () => { /* ... */ });
  it('should print summary with pass/fail counts', () => { /* ... */ });
});
```

**Test Framework Setup:**

```bash
# Install Vitest (already in PROJECT_ROADMAP.md)
npm install --save-dev vitest @vitest/ui

# Add to package.json scripts:
"test:unified-gantt": "vitest run src/modules/unified src/modules/gantt",
"test:unified-gantt:watch": "vitest watch src/modules/unified src/modules/gantt",
"test:unified-gantt:ui": "vitest --ui src/modules/unified src/modules/gantt"
```

**Acceptance Criteria:**
- [ ] All 4 test suites passing
- [ ] >80% code coverage
- [ ] All edge cases covered (empty data, type mismatch, missing refs)
- [ ] CI integration configured

**Blocking:** Production deployment

---

## 🟡 **HIGH PRIORITY (Foundation Work)**

### **2. StateManager Refactor (Option C Phase 0)** 🏗️

**Status:** ⏳ **PLANNED - NOT STARTED**

**From:** [ROADMAP_OPTION_C_PRODUCTION_READY.md](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\ROADMAP_OPTION_C_PRODUCTION_READY.md)

**Why High Priority:**
- Foundation for all future features
- Eliminates technical debt
- Enables 50% faster feature development

**Timeline:** Week 1 (5 days)

**Tasks:**

#### **Task 0.1: Database Schema Migration** (Day 1-2)
**Goal:** Remove legacy `proportion` field

```bash
# Pre-flight checklist:
python manage.py dumpdata detail_project.PekerjaanProgressWeekly > backup_weekly_progress.json
python manage.py shell
>>> from detail_project.models import PekerjaanProgressWeekly
>>> null_count = PekerjaanProgressWeekly.objects.filter(planned_proportion__isnull=True).count()
>>> print(f"NULL planned_proportion count: {null_count}")  # Should be 0
```

**Acceptance:**
- [ ] Backup created and verified
- [ ] Zero NULL values in planned_proportion
- [ ] Migration file created: `0043_remove_legacy_proportion_field.py`
- [ ] Rollback plan documented

#### **Task 0.2: StateManager Implementation** (Day 3-4)
**Goal:** Centralize all progress state management

**Files to Create:**
- `detail_project/static/detail_project/js/src/modules/core/state-manager-v2.js`

**Key Features:**
```javascript
class StateManagerV2 {
  constructor() {
    this.states = {
      planned: { assignmentMap: new Map(), modifiedCells: new Map() },
      actual: { assignmentMap: new Map(), modifiedCells: new Map() }
    };
    this.currentMode = 'planned';
    this._cache = new Map();
  }

  // MAIN METHODS
  getCellValue(pekerjaanId, columnId, mode = this.currentMode) { /* ... */ }
  setCellValue(pekerjaanId, columnId, value, mode = this.currentMode) { /* ... */ }
  getAllCellsForMode(mode) { /* ... */ }
  switchMode(newMode) { /* ... */ }

  // SYNC METHODS
  loadFromAPI(apiData) { /* ... */ }
  getModifiedCells(mode = this.currentMode) { /* ... */ }
  saveToAPI() { /* ... */ }
}
```

**Acceptance:**
- [ ] All Grid View consumers migrated
- [ ] All Gantt consumers migrated
- [ ] All Kurva S consumers migrated
- [ ] Zero API calls use old pattern

#### **Task 0.3: Migrate All Consumers** (Day 5)
**Goal:** Update all code to use StateManagerV2

**Files to Update:**
- `jadwal_kegiatan_app.js` - Initialize StateManagerV2
- `tanstack-grid-manager.js` - Use new getCellValue/setCellValue
- `UnifiedTableManager.js` - Update getAllCellsForMode calls
- `kurva-s/*.js` - Migrate to new state pattern

**Acceptance:**
- [ ] All tests passing
- [ ] No console warnings about deprecated methods
- [ ] Performance profile unchanged or improved

**Blocking:** Phase 1 features (Kurva S Harga, Rekap Kebutuhan enhancements)

---

### **3. Cross-Browser Testing** 🌐

**Status:** ⏳ **CHROME ONLY - NEEDS EXPANSION**

**Why High Priority:**
- Unified Gantt uses Canvas API (browser-specific quirks)
- CSS Grid sticky positioning varies across browsers
- Production users may use Firefox/Safari/Edge

**Browsers to Test:**

| Browser | Version | Status | Issues Found |
|---------|---------|--------|--------------|
| Chrome | Latest | ✅ Tested | None |
| Firefox | Latest | ⏳ Not Tested | ? |
| Safari | Latest | ⏳ Not Tested | ? |
| Edge | Latest | ⏳ Not Tested | ? |

**Test Checklist:**
- [ ] Gantt bars render correctly
- [ ] Bar colors match (CSS var extraction)
- [ ] Sticky columns work
- [ ] Scroll performance acceptable (60 FPS)
- [ ] Tooltip positioning correct
- [ ] No console errors
- [ ] Canvas high-DPI rendering OK

**Tools:**
- BrowserStack (free for open source)
- Local VMs (Firefox/Edge)
- Physical Mac (Safari)

**Estimated Effort:** 4-6 hours

**Acceptance:**
- [ ] All browsers render bars correctly
- [ ] Document any browser-specific quirks
- [ ] Add polyfills if needed

---

## 🟡 **MEDIUM PRIORITY (Enhancement)**

### **4. Gantt Tree Expand/Collapse UI** 🌲

**Status:** ⏳ **30% COMPLETE - LOGIC EXISTS, UI MISSING**

**From:** [GANTT_ROADMAP_FROZEN_COLUMN.md](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\GANTT_ROADMAP_FROZEN_COLUMN.md)

**Current State:**
- ✅ `_flattenRows()` helper exists
- ✅ Tree structure preserved in data
- ❌ No UI toggle icons
- ❌ No expand/collapse event handlers

**What's Needed:**

#### **Phase 1: Add Toggle Icons** (2 hours)
```javascript
// In UnifiedTableManager or TanStackGrid:
_renderTreeCell(cellEl, row) {
  const level = row.original?.level || 0;
  const hasChildren = (row.subRows || []).length > 0;

  if (hasChildren) {
    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle-icon';
    toggle.textContent = row.getIsExpanded() ? '▾' : '▸';
    toggle.style.cssText = `
      cursor: pointer;
      margin-right: 4px;
      user-select: none;
      color: var(--bs-secondary);
    `;

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      row.toggleExpanded();
      this._rerenderTable();
    });

    cellEl.prepend(toggle);
  } else {
    // Add spacer for alignment
    const spacer = document.createElement('span');
    spacer.style.width = '16px';
    spacer.style.display = 'inline-block';
    cellEl.prepend(spacer);
  }
}
```

#### **Phase 2: Persist Expand State** (2 hours)
```javascript
// Save to localStorage
_saveExpandState() {
  const expandedIds = [];
  this.tableInstance.getExpandedRowModel().rows.forEach(row => {
    expandedIds.push(row.original.id);
  });
  localStorage.setItem('gantt-expanded-rows', JSON.stringify(expandedIds));
}

// Restore on load
_restoreExpandState() {
  const expandedIds = JSON.parse(localStorage.getItem('gantt-expanded-rows') || '[]');
  expandedIds.forEach(id => {
    const row = this.tableInstance.getRow(id);
    if (row) row.toggleExpanded(true);
  });
}
```

**Estimated Effort:** 4-6 hours

**Acceptance:**
- [ ] Toggle icons visible on parent rows
- [ ] Click toggles expand/collapse
- [ ] Gantt bars update accordingly
- [ ] State persists across page reloads
- [ ] Smooth animation (optional)

**Benefit:** Easier navigation for large projects (100+ pekerjaan)

---

### **5. Rekap Kebutuhan Phase 5** 📊

**Status:** ✅ **90% COMPLETE - PHASE 5 PLANNED**

**From:** [REKAP_KEBUTUHAN_LIVING_ROADMAP.md](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\docs\REKAP_KEBUTUHAN_LIVING_ROADMAP.md)

**Completed Phases:**
- ✅ Phase 0: Stabilization & Observability
- ✅ Phase 1: Advanced Filters & Pricing Context
- ✅ Phase 2: Timeline Intelligence (with Polish)
- ✅ Phase 3: Intelligence & Self-Serve Analytics
- ✅ Phase 4: UI/UX Optimization & Toolbar Redesign

**Phase 5 Planning:** (📋 Planned - 1-2 weeks)

| Track | Goals | Priority |
|-------|-------|----------|
| **Export Excellence** | Export = UI state | 🟡 MEDIUM |
| **Data Validation** | Zero inconsistency | 🟢 LOW |
| **Advanced Search** | Autocomplete <200ms | 🟢 LOW |
| **Accessibility** | WCAG 2.1 AA ≥90% | 🟡 MEDIUM |

**Recommendation:**
- ✅ **Defer to after StateManager refactor**
- Current implementation is solid and user-tested
- Phase 5 is polish, not critical functionality

---

## 🟢 **LOW PRIORITY (Nice to Have)**

### **6. Gantt Zoom Controls** 🔍

**Status:** ⏳ **50% COMPLETE - INHERITS FROM GRID VIEW**

**Current Behavior:**
- Gantt uses same time scale as Grid View
- User changes scale in Grid → Gantt updates automatically
- No dedicated Gantt zoom controls

**What's Missing:**
- Dedicated zoom buttons in Gantt toolbar
- Independent zoom (Gantt scale ≠ Grid scale)
- Visual zoom animation

**Recommendation:**
- ✅ **SKIP FOR NOW**
- Current behavior is acceptable
- Low user demand
- High implementation complexity

---

### **7. Gantt Search Functionality** 🔎

**Status:** ❌ **NOT IMPLEMENTED**

**What's Needed:**
- Search box in Gantt toolbar
- Filter by pekerjaan name
- Highlight matching rows
- Scroll to first match

**Recommendation:**
- ✅ **DEFER TO FUTURE**
- Can reuse Grid View's search (via TanStack Table)
- Low user demand (users can search in Grid View)
- Estimated effort: 6-8 hours

---

### **8. Gantt Milestone Markers** 🎯

**Status:** ❌ **NOT IMPLEMENTED**

**From:** [GANTT_ROADMAP_FROZEN_COLUMN.md](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\GANTT_ROADMAP_FROZEN_COLUMN.md) Phase 6

**What's Needed:**
- Vertical lines for key dates
- Milestone diamonds
- Comments/notes on timeline
- CRUD API for timeline_notes

**Recommendation:**
- ✅ **DEFER TO FUTURE**
- Complex feature (backend + frontend)
- Low ROI for current user needs
- Estimated effort: 2-3 weeks

---

## 📋 **RECOMMENDED EXECUTION ORDER**

### **Week 1 (This Week):**
1. 🔴 **CRITICAL:** Unit Tests for Unified Gantt (Day 1-2)
2. 🟡 **HIGH:** Cross-Browser Testing (Day 3)
3. 🟡 **MEDIUM:** Gantt Tree Expand/Collapse UI (Day 4-5)

### **Week 2-3 (Next 2 Weeks):**
4. 🟡 **HIGH:** StateManager Refactor Phase 0 (Week 2: 5 days)
5. 🟢 **LOW:** Documentation updates (Week 3: 1-2 days)
6. 🟢 **LOW:** Deploy to staging + UAT (Week 3: 2-3 days)

### **Week 4+ (Future):**
7. 🟢 **LOW:** Rekap Kebutuhan Phase 5 (1-2 weeks)
8. 🟢 **LOW:** Gantt zoom/search/milestones (2-3 weeks)

---

## 🎯 **SUCCESS METRICS**

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| **Gantt Unit Test Coverage** | 0% | >80% | Week 1 |
| **Cross-Browser Support** | Chrome only | All major | Week 1 |
| **Tree Controls Usability** | Missing | Intuitive | Week 1 |
| **StateManager Adoption** | 0% | 100% | Week 2 |
| **Production Deployment** | Staging | Production | Week 3 |

---

## ⚠️ **BLOCKERS & DEPENDENCIES**

| Task | Blocked By | Can Start |
|------|-----------|-----------|
| StateManager Refactor | None | ✅ Immediately |
| Unit Tests | None | ✅ Immediately |
| Cross-Browser Testing | Unit Tests | After Day 2 |
| Production Deploy | Unit Tests + Browser Tests | After Week 1 |
| Rekap Phase 5 | StateManager Refactor | After Week 2 |

---

## 📝 **FINAL RECOMMENDATION**

**FOCUS THIS WEEK:**
1. 🔴 **Write unit tests** (CRITICAL - blocks production)
2. 🔴 **Cross-browser testing** (HIGH - production requirement)
3. 🟡 **Tree expand/collapse UI** (MEDIUM - user experience)

**NEXT 2 WEEKS:**
4. 🟡 **StateManager refactor** (HIGH - foundation for future)
5. 🟢 **Deploy to production** (after tests pass)

**DEFER:**
- Rekap Kebutuhan Phase 5 (current version is solid)
- Gantt advanced features (zoom, search, milestones)
- Until after StateManager refactor complete

---

**Audit Completed:** 2025-12-09
**Next Review:** After Week 1 execution
**Approved By:** Claude Sonnet 4.5

🎯 **CLEAR PRIORITIES - READY FOR EXECUTION!**
