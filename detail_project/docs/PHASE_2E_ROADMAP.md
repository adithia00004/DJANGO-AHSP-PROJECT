# Phase 2E Roadmap: Time Period Configuration & Mode Switching

**Date**: 2025-11-23
**Status**: 📋 **PLANNING**
**Goal**: Implement proper week boundaries, mode switching, and simplify to Weekly/Monthly only

---

## 🎯 OBJECTIVES

### Primary Goals
1. ✅ **Proper Week Boundaries**: Monday-Sunday alignment, handle partial weeks
2. ✅ **Mode Switching**: Seamless switch between Weekly ↔ Monthly with no data loss
3. ✅ **Complexity Reduction**: Remove Daily and Custom modes
4. ✅ **Performance**: Fast rendering, efficient database queries
5. ✅ **Maintainability**: Clean architecture, easy to understand and extend

### Success Criteria
- [ ] Week periods aligned to Monday-Sunday (ISO 8601)
- [ ] Partial weeks handled gracefully (trim to project boundaries)
- [ ] Mode switch preserves canonical data (PekerjaanProgressWeekly)
- [ ] Grid loads in < 2 seconds
- [ ] Only 2 modes: Weekly + Monthly
- [ ] Clear documentation for all design decisions

---

## 📋 PHASE BREAKDOWN

### Phase 2E.1: Week Boundaries Fix (HIGH PRIORITY)
**Duration**: 2-3 hours
**Dependencies**: None

#### Tasks
- [ ] **Update `generate_sample_weekly_tahapan.py`**
  - Add `get_week_start()` function (align to Monday)
  - Trim weeks to project boundaries
  - Calculate actual day count per week
  - Add week day count to tahapan description

- [ ] **Update TimeColumnGenerator**
  - Display week day count in column label (e.g., "Week 1 (3 days)")
  - Add tooltip showing partial week reason
  - Style partial week columns differently

- [ ] **Update Grid CSS**
  - Add `.partial-week` class for narrower columns
  - Add visual indicator (e.g., asterisk or icon)

- [ ] **Testing**
  - Test with project starting mid-week (e.g., Friday)
  - Test with project ending mid-week (e.g., Wednesday)
  - Verify column labels show correct day counts
  - Verify tooltips explain partial weeks

**Deliverables**:
- ✅ Updated management command
- ✅ Updated TimeColumnGenerator with day count display
- ✅ CSS for partial week indicators
- ✅ Test project with partial weeks

---

### Phase 2E.2: Monthly Tahapan Generation (HIGH PRIORITY)
**Duration**: 3-4 hours
**Dependencies**: Phase 2E.1

#### Tasks
- [ ] **Create `generate_monthly_tahapan()` function**
  - Generate monthly periods (e.g., Jan 2026, Feb 2026, Mar 2026)
  - Align to calendar months (1st - last day of month)
  - Trim to project boundaries (like weekly)
  - Set `generation_mode='monthly'`

- [ ] **Create management command**
  - `python manage.py generate_sample_monthly_tahapan <project_id>`
  - Similar options to weekly command (--start-date, --clear-auto)

- [ ] **Update TimeColumnGenerator**
  - Handle monthly columns
  - Display format: "Jan 2026", "Feb 2026", etc.
  - Tooltip shows date range

- [ ] **Testing**
  - Generate monthly tahapan for test project
  - Verify grid displays monthly columns
  - Test partial months (project starts/ends mid-month)

**Deliverables**:
- ✅ `generate_monthly_tahapan()` function
- ✅ Management command: `generate_sample_monthly_tahapan`
- ✅ TimeColumnGenerator updated for monthly display
- ✅ Test project with monthly periods

---

### Phase 2E.3: Canonical Storage (Save Handler) (HIGH PRIORITY)
**Duration**: 4-6 hours
**Dependencies**: Phase 2E.1, 2E.2

#### Tasks
- [ ] **Update SaveHandler to save to PekerjaanProgressWeekly**
  - When user enters percentage in weekly cell → save to PekerjaanProgressWeekly
  - When user enters percentage in monthly cell → disaggregate to weekly, save to PekerjaanProgressWeekly
  - Validate total proportion per pekerjaan ≤ 100%

- [ ] **Create API endpoint for canonical save**
  - `POST /api/project/<id>/save-progress-canonical/`
  - Accept grid cell changes
  - Transform to weekly canonical format
  - Save to PekerjaanProgressWeekly
  - Regenerate PekerjaanTahapan (view layer)

- [ ] **Update frontend SaveHandler**
  - Call new API endpoint
  - Handle response (success/error)
  - Update grid and charts on success

- [ ] **Testing**
  - Save in weekly mode → verify PekerjaanProgressWeekly created
  - Save in monthly mode → verify disaggregated to weekly
  - Verify PekerjaanTahapan regenerated correctly
  - Test validation (total > 100%)

**Deliverables**:
- ✅ Updated SaveHandler (frontend)
- ✅ API endpoint: `/save-progress-canonical/`
- ✅ Backend logic for canonical save
- ✅ Tests for save and validation

---

### Phase 2E.4: Mode Switching Implementation (HIGH PRIORITY)
**Duration**: 4-6 hours
**Dependencies**: Phase 2E.3

#### Tasks
- [ ] **Create mode switch API endpoint**
  - `POST /api/project/<id>/switch-mode/`
  - Params: `new_mode` (weekly/monthly)
  - Delete old auto-generated tahapan
  - Generate new tahapan for new mode
  - Regenerate PekerjaanTahapan from PekerjaanProgressWeekly (canonical)

- [ ] **Create aggregation logic (weekly → monthly)**
  - Sum weekly proportions within each month
  - Create PekerjaanTahapan for monthly tahapan

- [ ] **Create disaggregation logic (monthly → weekly)**
  - Distribute monthly proportion evenly across weeks
  - Or use existing PekerjaanProgressWeekly if available

- [ ] **Add UI toggle (Weekly/Monthly)**
  - Bootstrap toggle button in grid header
  - Confirm dialog before switch
  - Loading indicator during switch
  - Reload grid after switch

- [ ] **Testing**
  - Switch weekly → monthly → verify columns change
  - Switch monthly → weekly → verify columns change
  - Verify assignments preserved (canonical storage)
  - Verify charts update correctly

**Deliverables**:
- ✅ API endpoint: `/switch-mode/`
- ✅ Aggregation logic (weekly → monthly)
- ✅ Disaggregation logic (monthly → weekly)
- ✅ UI toggle for mode switching
- ✅ Tests for mode switching

---

### Phase 2E.5: Remove Daily/Custom Modes (MEDIUM PRIORITY)
**Duration**: 2-3 hours
**Dependencies**: Phase 2E.4

#### Tasks
- [ ] **Remove daily mode from code**
  - Remove 'daily' from `GENERATION_MODE_CHOICES`
  - Remove daily-specific logic in TimeColumnGenerator
  - Remove daily generation functions

- [ ] **Remove custom mode from code**
  - Remove 'custom' from `GENERATION_MODE_CHOICES`
  - Remove custom mode handling
  - Update TimeColumnGenerator to only handle weekly/monthly

- [ ] **Migrate existing data**
  - Find projects with daily/custom tahapan
  - Migrate to weekly or delete (user decision)
  - Update generation_mode field

- [ ] **Update documentation**
  - Remove references to daily/custom
  - Update user guide to show only Weekly/Monthly
  - Update API docs

- [ ] **Testing**
  - Verify no daily/custom options in UI
  - Verify TimeColumnGenerator only handles weekly/monthly
  - Verify existing projects migrated correctly

**Deliverables**:
- ✅ Code cleanup (remove daily/custom)
- ✅ Data migration script
- ✅ Updated documentation
- ✅ Tests for weekly/monthly only

---

### Phase 2E.6: Performance Optimization (MEDIUM PRIORITY)
**Duration**: 2-4 hours
**Dependencies**: Phase 2E.5

#### Tasks
- [ ] **Database query optimization**
  - Add database indexes for common queries
  - Optimize tahapan loading (select_related, prefetch_related)
  - Cache project time configuration

- [ ] **Frontend optimization**
  - Lazy load charts (only render when tab active)
  - Debounce cell input (reduce save calls)
  - Virtual scrolling for large grids (if needed)

- [ ] **Performance testing**
  - Measure grid load time (target: < 2 seconds)
  - Measure mode switch time (target: < 3 seconds)
  - Measure save time (target: < 1 second)
  - Profile memory usage

- [ ] **Optimization based on results**
  - Implement improvements for slow areas
  - Re-test after optimizations

**Deliverables**:
- ✅ Database indexes added
- ✅ Frontend optimizations implemented
- ✅ Performance benchmarks documented
- ✅ Target metrics achieved

---

### Phase 2E.7: Documentation & User Guide (LOW PRIORITY)
**Duration**: 2-3 hours
**Dependencies**: All above phases

#### Tasks
- [ ] **Create user guide**
  - How to generate time periods (weekly/monthly)
  - How to switch modes
  - How to assign pekerjaan to periods
  - How partial weeks work

- [ ] **Update API documentation**
  - Document new endpoints
  - Document canonical storage model
  - Document mode switching behavior

- [ ] **Create developer guide**
  - Architecture overview
  - Data flow diagrams
  - How to extend (e.g., add quarterly mode)

- [ ] **Update PHASE_2E_PROGRESS.md**
  - Track progress through phases
  - Document challenges and solutions
  - Record performance benchmarks

**Deliverables**:
- ✅ User guide (with screenshots)
- ✅ API documentation
- ✅ Developer guide
- ✅ Progress tracking document

---

## 📊 PROGRESS TRACKING

| Phase | Tasks | Priority | Duration | Status | Complete |
|-------|-------|----------|----------|--------|----------|
| 2E.1: Week Boundaries | 4 tasks | HIGH | 2-3h | ☐ TODO | 0% |
| 2E.2: Monthly Generation | 4 tasks | HIGH | 3-4h | ☐ TODO | 0% |
| 2E.3: Canonical Save | 4 tasks | HIGH | 4-6h | ☐ TODO | 0% |
| 2E.4: Mode Switching | 5 tasks | HIGH | 4-6h | ☐ TODO | 0% |
| 2E.5: Remove Daily/Custom | 5 tasks | MEDIUM | 2-3h | ☐ TODO | 0% |
| 2E.6: Performance | 4 tasks | MEDIUM | 2-4h | ☐ TODO | 0% |
| 2E.7: Documentation | 4 tasks | LOW | 2-3h | ☐ TODO | 0% |
| **TOTAL** | **30 tasks** | - | **19-29h** | **0%** | **0%** |

---

## 🎯 IMPLEMENTATION ORDER (Recommended)

### Sprint 1: Core Functionality (High Priority)
**Duration**: 2-3 days

1. **Phase 2E.1**: Week Boundaries Fix (2-3h)
   - Fix Monday alignment
   - Handle partial weeks
   - Update UI display

2. **Phase 2E.2**: Monthly Generation (3-4h)
   - Create monthly tahapan generator
   - Test monthly display

3. **Phase 2E.3**: Canonical Save (4-6h)
   - Implement PekerjaanProgressWeekly save
   - Update SaveHandler
   - Test save functionality

**Deliverable**: Working weekly/monthly with proper boundaries and canonical storage

---

### Sprint 2: Mode Switching (High Priority)
**Duration**: 1-2 days

4. **Phase 2E.4**: Mode Switching (4-6h)
   - Implement mode switch API
   - Add UI toggle
   - Test switching both ways

**Deliverable**: Seamless mode switching with preserved assignments

---

### Sprint 3: Cleanup & Optimization (Medium Priority)
**Duration**: 1-2 days

5. **Phase 2E.5**: Remove Daily/Custom (2-3h)
   - Clean up code
   - Migrate data
   - Update docs

6. **Phase 2E.6**: Performance (2-4h)
   - Optimize queries
   - Optimize frontend
   - Benchmark results

**Deliverable**: Clean, fast, maintainable system

---

### Sprint 4: Documentation (Low Priority)
**Duration**: 0.5-1 day

7. **Phase 2E.7**: Documentation (2-3h)
   - User guide
   - API docs
   - Developer guide

**Deliverable**: Complete documentation for users and developers

---

## 🔧 TECHNICAL ARCHITECTURE

### Data Flow (After Phase 2E)

```
User Input (Grid Cell)
    ↓
Frontend SaveHandler
    ↓
POST /api/project/{id}/save-progress-canonical/
    ↓
Backend: Transform to Weekly Canonical
    ↓
Save to PekerjaanProgressWeekly (Canonical Storage)
    ↓
Regenerate PekerjaanTahapan (View Layer)
    ↓
Response: Success + Updated Data
    ↓
Frontend: Update Grid + Charts
```

### Mode Switch Flow

```
User Clicks "Switch to Monthly"
    ↓
Confirm Dialog
    ↓
POST /api/project/{id}/switch-mode/ (new_mode='monthly')
    ↓
Backend:
  1. Delete auto-generated tahapan (weekly)
  2. Generate monthly tahapan
  3. Aggregate PekerjaanProgressWeekly → PekerjaanTahapan (monthly)
    ↓
Response: Success + New Tahapan List
    ↓
Frontend:
  1. Reload data (tahapan, assignments)
  2. Regenerate time columns (monthly)
  3. Re-render grid
  4. Update charts
```

---

## 📋 FILES TO CREATE/MODIFY

### New Files
1. `detail_project/services/time_period_service.py` - Week/month generation logic
2. `detail_project/services/canonical_storage_service.py` - Save/load canonical data
3. `detail_project/services/mode_switch_service.py` - Mode switching logic
4. `detail_project/api/views/mode_switch_views.py` - API endpoints
5. `detail_project/management/commands/generate_monthly_tahapan.py` - Monthly generator
6. `detail_project/docs/USER_GUIDE_TIME_PERIODS.md` - User guide

### Modified Files
1. `detail_project/management/commands/generate_sample_weekly_tahapan.py` - Add Monday alignment
2. `detail_project/static/detail_project/js/src/modules/core/time-column-generator.js` - Add day count display
3. `detail_project/static/detail_project/js/src/modules/grid/save-handler.js` - Call canonical API
4. `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js` - Add mode toggle
5. `detail_project/models.py` - Remove daily/custom from choices (optional field cleanup)
6. `detail_project/templates/detail_project/kelola_tahapan/_grid_tab.html` - Add mode toggle UI

---

## 🎯 SUCCESS METRICS

### Performance
- [ ] Grid loads in < 2 seconds (with 12 weeks or 3 months)
- [ ] Mode switch completes in < 3 seconds
- [ ] Save operation completes in < 1 second
- [ ] No frontend memory leaks

### Functionality
- [ ] Week boundaries aligned to Monday-Sunday
- [ ] Partial weeks handled correctly
- [ ] Mode switch preserves all assignments
- [ ] Charts update correctly after mode switch

### Code Quality
- [ ] Test coverage > 80% for new code
- [ ] No console errors
- [ ] Clear, documented code
- [ ] Easy to maintain (< 2 modes)

### User Experience
- [ ] Clear visual indicators for partial weeks
- [ ] Smooth mode switching (with confirmation)
- [ ] Helpful tooltips and error messages
- [ ] Responsive grid (works on tablet)

---

## 🚨 RISKS & MITIGATION

### Risk 1: Data Loss During Mode Switch
**Mitigation**: Use canonical storage (PekerjaanProgressWeekly), never delete

### Risk 2: Performance Issues with Many Columns
**Mitigation**: Limit to weekly/monthly only (max 12 columns)

### Risk 3: Complex Aggregation Logic
**Mitigation**: Write comprehensive tests, start simple (sum weekly → monthly)

### Risk 4: User Confusion About Partial Weeks
**Mitigation**: Clear visual indicators, tooltips, user guide

---

## 📝 DEPENDENCIES

### External Dependencies
- ✅ Django ORM (for models and queries)
- ✅ Bootstrap 5 (for UI toggle)
- ✅ ECharts (for charts)
- ✅ Frappe Gantt (for Gantt chart)

### Internal Dependencies
- ✅ Phase 2A-2C Complete (modules migrated)
- ✅ Phase 2D Complete (testing, sample data)
- ✅ TahapPelaksanaan model (exists)
- ✅ PekerjaanProgressWeekly model (exists)
- ✅ PekerjaanTahapan model (exists)

---

## 🎓 LEARNING RESOURCES

### ISO 8601 Week Dates
- https://en.wikipedia.org/wiki/ISO_8601#Week_dates
- Monday = first day of week (international standard)

### Construction Project Scheduling
- Most projects track weekly progress (not daily)
- Monthly summaries for high-level reporting

### Canonical Storage Pattern
- Single source of truth (PekerjaanProgressWeekly)
- Derived/aggregated views (PekerjaanTahapan)
- Enables mode switching without data loss

---

**Last Updated**: 2025-11-23
**Status**: Planning Complete - Ready for Implementation
**Next**: Start Phase 2E.1 (Week Boundaries Fix)
**Estimated Total Time**: 19-29 hours (3-5 days full-time)
