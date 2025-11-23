# Phase 2E Roadmap (REVISED): Complete Grid Implementation

**Date**: 2025-11-23
**Status**: 📋 **PLANNING COMPLETE**
**Goal**: Production-ready grid with proper UI/UX, validation, mode switching, and performance

---

## 🎯 OBJECTIVES

### Primary Goals
1. ✅ **UI/UX Excellence**: Smooth scrolling, proper validation, visual feedback
2. ✅ **Week Boundaries**: Monday-Sunday alignment, partial weeks handled
3. ✅ **Mode Switching**: Seamless Weekly ↔ Monthly with canonical storage
4. ✅ **Input Validation**: Type, range, and cumulative validation
5. ✅ **Performance**: < 2s load, < 3s mode switch, < 1s save
6. ✅ **Maintainability**: Only Weekly + Monthly modes, clean code

### Success Criteria
- [ ] Synchronized vertical scroll (both panels)
- [ ] Horizontal scroll (right panel only)
- [ ] Input validation (type, range, cumulative)
- [ ] Visual error feedback
- [ ] Standard column widths (weekly 110px, monthly 135px)
- [ ] Week periods aligned to Monday-Sunday
- [ ] Mode switch preserves data
- [ ] Grid loads < 2 seconds
- [ ] Complete documentation

---

## 📋 REVISED PHASE BREAKDOWN

### Phase 2E.0: Grid UI/UX Improvements (CRITICAL - MUST DO FIRST)
**Duration**: 4-6 hours
**Priority**: P0 (Must Have)
**Dependencies**: None

#### Sub-phase 2E.0.1: Scroll Synchronization (2-3h)

**Tasks**:
- [ ] **Implement Synchronized Vertical Scroll**
  - Create shared scroll container
  - Add scroll event listeners (left ↔ right sync)
  - Test with different scroll methods (wheel, trackpad, scrollbar)
  - Verify no row misalignment

- [ ] **Verify Horizontal Scroll**
  - Ensure right panel scrolls horizontally
  - Ensure left panel stays fixed
  - Test scrollbar visibility
  - Test smooth scrolling

- [ ] **Enhance Row Height Sync**
  - Call `_syncRowHeights()` after render
  - Call on window resize (debounced)
  - Call after cell content changes
  - Test with varying content heights

**Files to Modify**:
- `detail_project/static/detail_project/js/src/modules/grid/grid-renderer.js`
- `detail_project/templates/detail_project/kelola_tahapan/_grid_tab.html`
- `detail_project/static/detail_project/css/kelola_tahapan_grid.css`

**Testing**:
- [ ] Vertical scroll syncs both panels
- [ ] Horizontal scroll works on right only
- [ ] Row heights aligned after all operations
- [ ] Smooth performance (no lag)

---

#### Sub-phase 2E.0.2: Input Validation (2-3h)

**Tasks**:
- [ ] **Type Validation**
  - Input type="number", step="0.01"
  - Real-time validation on input event
  - Remove non-numeric characters
  - Max 2 decimal places

- [ ] **Range Validation**
  - Min: 0.01%, Max: 100.00%
  - Visual feedback (red border for invalid)
  - Error tooltip with message
  - Auto-format on blur

- [ ] **Cumulative Validation**
  - Calculate total per pekerjaan
  - Validate total ≤ 100%
  - Show progress indicator per row
  - Color-code: green (100%), yellow (<100%), red (>100%)

- [ ] **Save Validation**
  - Validate all pekerjaan before save
  - Show error modal if any exceed 100%
  - List all invalid pekerjaan
  - Prevent save until fixed

**Files to Create/Modify**:
- `detail_project/static/detail_project/js/src/modules/grid/input-validator.js` (NEW)
- `detail_project/static/detail_project/js/src/modules/grid/save-handler.js` (MODIFY)
- `detail_project/static/detail_project/css/kelola_tahapan_grid.css` (MODIFY - error styles)

**Testing**:
- [ ] Only numeric input accepted
- [ ] Range validation works
- [ ] Error tooltips show
- [ ] Cumulative validation correct
- [ ] Progress indicators update
- [ ] Cannot save if total > 100%

---

#### Sub-phase 2E.0.3: Column Width Standardization (1h)

**Tasks**:
- [ ] **Define Standard Widths**
  - Weekly columns: 110px
  - Monthly columns: 135px
  - Left panel: Fixed widths (tree 40px, uraian 400px, volume 100px, satuan 80px)

- [ ] **Update CSS**
  - Add classes: `.time-column.weekly`, `.time-column.monthly`
  - Set min-width, max-width, width
  - Update header templates

- [ ] **Create Column Headers**
  - Weekly: "Week 1" + "(09/01 - 15/01)" + "3d" (for partial)
  - Monthly: "Jan 2026" + "(01/01 - 31/01)" + "4w"

**Files to Modify**:
- `detail_project/static/detail_project/css/kelola_tahapan_grid.css`
- `detail_project/static/detail_project/js/src/modules/core/time-column-generator.js`

**Testing**:
- [ ] Weekly columns 110px
- [ ] Monthly columns 135px
- [ ] Headers formatted correctly
- [ ] Visual consistency

---

### Phase 2E.1: Week Boundaries Fix (HIGH PRIORITY)
**Duration**: 2-3 hours
**Priority**: P0
**Dependencies**: Phase 2E.0

**Tasks**:
- [ ] **Update `generate_sample_weekly_tahapan.py`**
  - Add `get_week_start()` function (align to Monday)
  - Trim weeks to project boundaries
  - Calculate actual day count per week
  - Mark partial weeks

- [ ] **Update TimeColumnGenerator**
  - Display day count for partial weeks
  - Add tooltips explaining partial weeks
  - Pass week metadata to grid renderer

**Deliverables**:
- ✅ Updated management command with Monday alignment
- ✅ Partial week handling
- ✅ Week day count display

---

### Phase 2E.2: Monthly Tahapan Generation (HIGH PRIORITY)
**Duration**: 3-4 hours
**Priority**: P0
**Dependencies**: Phase 2E.1

**Tasks**:
- [ ] **Create `generate_monthly_tahapan()` function**
  - Monthly periods (Jan, Feb, Mar)
  - Align to calendar months
  - Trim to project boundaries

- [ ] **Create management command**
  - `python manage.py generate_sample_monthly_tahapan <project_id>`

**Deliverables**:
- ✅ Monthly tahapan generator
- ✅ Management command
- ✅ TimeColumnGenerator updated

---

### Phase 2E.3: Canonical Storage (Save Handler) (HIGH PRIORITY)
**Duration**: 4-6 hours
**Priority**: P0
**Dependencies**: Phase 2E.0.2 (Input Validation)

**Tasks**:
- [ ] **Update SaveHandler to save to PekerjaanProgressWeekly**
  - Transform grid cell data to weekly canonical format
  - Handle both weekly and monthly modes
  - Disaggregate monthly to weekly

- [ ] **Create API endpoint**
  - `POST /api/project/<id>/save-progress-canonical/`
  - Accept cell changes
  - Save to PekerjaanProgressWeekly
  - Regenerate PekerjaanTahapan

**Deliverables**:
- ✅ Updated SaveHandler (frontend)
- ✅ API endpoint for canonical save
- ✅ Backend logic

---

### Phase 2E.4: Mode Switching Implementation (HIGH PRIORITY)
**Duration**: 4-6 hours
**Priority**: P0
**Dependencies**: Phase 2E.3

**Tasks**:
- [ ] **Create mode switch API**
  - `POST /api/project/<id>/switch-mode/`
  - Delete old tahapan
  - Generate new tahapan
  - Regenerate assignments

- [ ] **Add UI toggle**
  - Bootstrap toggle: Weekly / Monthly
  - Confirm dialog
  - Loading indicator

**Deliverables**:
- ✅ Mode switch API
- ✅ UI toggle
- ✅ Aggregation/disaggregation logic

---

### Phase 2E.5: Remove Daily/Custom Modes (MEDIUM PRIORITY)
**Duration**: 2-3 hours
**Priority**: P1
**Dependencies**: Phase 2E.4

**Tasks**:
- [ ] Remove daily/custom from code
- [ ] Update `GENERATION_MODE_CHOICES`
- [ ] Migrate existing data

**Deliverables**:
- ✅ Code cleanup
- ✅ Data migration
- ✅ Updated docs

---

### Phase 2E.6: UI Polish & Advanced Features (MEDIUM PRIORITY)
**Duration**: 3-4 hours
**Priority**: P1
**Dependencies**: All above phases

**Tasks**:
- [ ] **Loading States**
  - Grid loading overlay
  - Save progress indicator

- [ ] **Empty States**
  - No time columns message
  - No pekerjaan message

- [ ] **Keyboard Shortcuts**
  - Tab/Shift+Tab navigation
  - Enter to save and move down
  - Escape to cancel
  - Ctrl+S to save all

- [ ] **Progress Summary Panel**
  - Total pekerjaan count
  - Complete (100%) count
  - Partial (<100%) count
  - Exceeded (>100%) count

**Deliverables**:
- ✅ Loading indicators
- ✅ Empty state components
- ✅ Keyboard navigation
- ✅ Summary panel

---

### Phase 2E.7: Performance Optimization (MEDIUM PRIORITY)
**Duration**: 2-4 hours
**Priority**: P1
**Dependencies**: All above phases

**Tasks**:
- [ ] **Database Optimization**
  - Add indexes
  - Optimize queries (select_related, prefetch_related)
  - Cache tahapan list

- [ ] **Frontend Optimization**
  - Lazy load charts
  - Debounce input (500ms)
  - Update only changed cells (not full re-render)

**Deliverables**:
- ✅ Database indexes added
- ✅ Optimized queries
- ✅ Frontend optimizations
- ✅ Performance benchmarks

---

### Phase 2E.8: Documentation & User Guide (LOW PRIORITY)
**Duration**: 2-3 hours
**Priority**: P2
**Dependencies**: All above phases

**Tasks**:
- [ ] **User Guide**
  - How to generate periods
  - How to switch modes
  - How to enter progress
  - Validation rules

- [ ] **API Documentation**
  - Document new endpoints
  - Request/response examples

- [ ] **Developer Guide**
  - Architecture overview
  - How to extend

**Deliverables**:
- ✅ User guide (with screenshots)
- ✅ API docs
- ✅ Developer guide

---

## 📊 REVISED PROGRESS TRACKING

| Phase | Tasks | Priority | Duration | Dependencies | Complete |
|-------|-------|----------|----------|--------------|----------|
| **2E.0: UI/UX** | **12 tasks** | **P0** | **4-6h** | None | **0%** |
| 2E.0.1: Scroll Sync | 4 tasks | P0 | 2-3h | None | 0% |
| 2E.0.2: Input Validation | 4 tasks | P0 | 2-3h | None | 0% |
| 2E.0.3: Column Widths | 3 tasks | P0 | 1h | None | 0% |
| 2E.1: Week Boundaries | 2 tasks | P0 | 2-3h | 2E.0 | 0% |
| 2E.2: Monthly Gen | 2 tasks | P0 | 3-4h | 2E.1 | 0% |
| 2E.3: Canonical Save | 2 tasks | P0 | 4-6h | 2E.0.2 | 0% |
| 2E.4: Mode Switching | 2 tasks | P0 | 4-6h | 2E.3 | 0% |
| 2E.5: Remove Daily/Custom | 3 tasks | P1 | 2-3h | 2E.4 | 0% |
| 2E.6: UI Polish | 4 tasks | P1 | 3-4h | All P0 | 0% |
| 2E.7: Performance | 2 tasks | P1 | 2-4h | All above | 0% |
| 2E.8: Documentation | 3 tasks | P2 | 2-3h | All above | 0% |
| **TOTAL** | **36 tasks** | - | **28-42h** | - | **0%** |

---

## 🚀 RECOMMENDED IMPLEMENTATION ORDER

### Sprint 1: Foundation (P0 - Critical) - 4-6 hours
**Focus**: Get basic UI/UX right first

1. **Phase 2E.0.1**: Scroll Synchronization (2-3h)
   - Must work perfectly before anything else
   - Core UX requirement

2. **Phase 2E.0.2**: Input Validation (2-3h)
   - Prevent bad data from day one
   - Essential for data integrity

3. **Phase 2E.0.3**: Column Standardization (1h)
   - Visual consistency
   - Simple but important

**Deliverable**: Grid with proper scrolling, validation, and standard widths

---

### Sprint 2: Core Functionality (P0 - Critical) - 9-13 hours

4. **Phase 2E.1**: Week Boundaries (2-3h)
   - Monday alignment
   - Partial weeks

5. **Phase 2E.2**: Monthly Generation (3-4h)
   - Monthly tahapan generator
   - Monthly display

6. **Phase 2E.3**: Canonical Storage (4-6h)
   - Save to PekerjaanProgressWeekly
   - Backend API

**Deliverable**: Both modes (weekly/monthly) working with proper data storage

---

### Sprint 3: Mode Switching (P0 - Critical) - 4-6 hours

7. **Phase 2E.4**: Mode Switching (4-6h)
   - Switch API
   - UI toggle
   - Aggregation logic

**Deliverable**: Seamless mode switching with no data loss

---

### Sprint 4: Cleanup & Polish (P1 - Important) - 7-11 hours

8. **Phase 2E.5**: Remove Daily/Custom (2-3h)
9. **Phase 2E.6**: UI Polish (3-4h)
10. **Phase 2E.7**: Performance (2-4h)

**Deliverable**: Production-ready grid with all polish

---

### Sprint 5: Documentation (P2 - Nice to Have) - 2-3 hours

11. **Phase 2E.8**: Documentation (2-3h)

**Deliverable**: Complete user and developer documentation

---

## 🎯 PRIORITY BREAKDOWN

### Must Have (P0) - 19-31 hours
- ✅ Scroll synchronization
- ✅ Input validation
- ✅ Column standardization
- ✅ Week boundaries
- ✅ Monthly generation
- ✅ Canonical storage
- ✅ Mode switching

### Should Have (P1) - 7-11 hours
- ✅ Remove daily/custom
- ✅ UI polish (loading, empty states, shortcuts)
- ✅ Performance optimization

### Nice to Have (P2) - 2-3 hours
- ✅ Documentation

**Total**: 28-45 hours (4-6 days full-time)

---

## 📋 FILES TO CREATE/MODIFY

### New Files (7 files)
1. `detail_project/static/detail_project/js/src/modules/grid/input-validator.js`
2. `detail_project/services/time_period_service.py`
3. `detail_project/services/canonical_storage_service.py`
4. `detail_project/services/mode_switch_service.py`
5. `detail_project/api/views/mode_switch_views.py`
6. `detail_project/management/commands/generate_monthly_tahapan.py`
7. `detail_project/docs/USER_GUIDE_GRID.md`

### Modified Files (8 files)
1. `detail_project/management/commands/generate_sample_weekly_tahapan.py`
2. `detail_project/static/detail_project/js/src/modules/grid/grid-renderer.js`
3. `detail_project/static/detail_project/js/src/modules/grid/save-handler.js`
4. `detail_project/static/detail_project/js/src/modules/core/time-column-generator.js`
5. `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`
6. `detail_project/static/detail_project/css/kelola_tahapan_grid.css`
7. `detail_project/templates/detail_project/kelola_tahapan/_grid_tab.html`
8. `detail_project/models.py` (cleanup GENERATION_MODE_CHOICES)

---

## 🎯 SUCCESS METRICS

### Performance Targets
- [ ] Grid loads in < 2 seconds (12 columns, 50 rows)
- [ ] Mode switch in < 3 seconds
- [ ] Save operation in < 1 second
- [ ] No memory leaks (< 50MB stable)
- [ ] Smooth scrolling (60fps)

### Functionality Targets
- [ ] Vertical scroll synced perfectly
- [ ] Input validation prevents all bad data
- [ ] Cumulative validation accurate
- [ ] Mode switch preserves 100% of data
- [ ] Standard column widths consistent

### UX Targets
- [ ] No visual glitches
- [ ] Clear error messages
- [ ] Loading states provide feedback
- [ ] Empty states guide users
- [ ] Keyboard shortcuts work

---

## 📚 REFERENCE DOCUMENTS

1. [PHASE_2E_UI_UX_REQUIREMENTS.md](PHASE_2E_UI_UX_REQUIREMENTS.md) - Detailed UI/UX specs
2. [TIME_PERIOD_CONFIGURATION_DISCUSSION.md](TIME_PERIOD_CONFIGURATION_DISCUSSION.md) - Design decisions
3. [PERFORMANCE_MAINTENANCE_NOTES.md](PERFORMANCE_MAINTENANCE_NOTES.md) - Performance guidelines
4. [DATA_MODEL_ARCHITECTURE.md](DATA_MODEL_ARCHITECTURE.md) - Architecture overview

---

## 🚨 CRITICAL PATH

**Must Complete in Order**:
1. Phase 2E.0.1 (Scroll Sync) → 2E.0.2 (Validation) → 2E.0.3 (Columns)
2. Phase 2E.1 (Week Boundaries)
3. Phase 2E.2 (Monthly)
4. Phase 2E.3 (Canonical Save) - **Depends on 2E.0.2 validation**
5. Phase 2E.4 (Mode Switching) - **Depends on 2E.3**

**Remaining phases can be done in any order after critical path complete.**

---

**Last Updated**: 2025-11-23
**Status**: Revised Roadmap Complete - Ready for Implementation
**Estimated Total Time**: 28-45 hours (4-6 days full-time)
**Next**: Start Phase 2E.0.1 (Scroll Synchronization)
