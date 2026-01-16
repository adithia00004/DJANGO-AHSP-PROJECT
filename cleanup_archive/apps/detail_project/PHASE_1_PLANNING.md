# Phase 1: Core Features Development

**Timeline**: Week 2-3 (2-3 weeks)
**Goal**: Implement missing core features for project management
**Status**: 🔵 READY TO START
**Prerequisites**: ✅ Phase 0 Complete

---

## 🎯 Phase 1 Objectives

### Primary Goals:
1. **Kurva S Harga** - Cost-based S-curve visualization
2. **Rekap Kebutuhan** - Resource requirements summary
3. **Code Cleanup** - Remove deprecated functions
4. **Performance Optimization** - Improve chart rendering

### Secondary Goals:
- Add StateManager event listeners to charts
- Implement real-time chart updates
- Add export functionality
- Improve error handling

---

## 📊 Feature Breakdown

### Feature 1: Kurva S Harga (Price Curve) 💰
**Priority**: HIGH
**Duration**: 1 week
**Complexity**: MEDIUM

#### Description:
Display cost-based S-curve alongside progress curve. Shows planned vs actual spending over time.

#### Requirements:
- **Backend**:
  - Add `harga_satuan` (unit price) field to pekerjaan
  - Calculate cost = volume × harga_satuan × proportion
  - API endpoint: `/api/project/{id}/kurva-s-harga/`

- **Frontend**:
  - Add price curve to existing Kurva S chart
  - Display both progress % and cost (Rp)
  - Toggle between progress view and cost view
  - Format currency (Rupiah)

#### Acceptance Criteria:
- [ ] Price data loads from backend
- [ ] Kurva S displays 4 curves: planned progress, actual progress, planned cost, actual cost
- [ ] Toggle button switches between views
- [ ] Currency formatted correctly (Rp 1.000.000)
- [ ] Chart updates in real-time when cells change
- [ ] Performance: render < 500ms

#### Tasks:
1. **Backend** (3 days):
   - Add migration for `harga_satuan` field
   - Update `PekerjaanProgressWeekly` model
   - Create API view for cost data
   - Write unit tests

2. **Frontend** (3 days):
   - Update `echarts-setup.js` to handle cost data
   - Add toggle button component
   - Implement cost calculation logic
   - Update chart options for dual-axis
   - Add currency formatter
   - Write integration tests

3. **Integration** (1 day):
   - Connect frontend to backend API
   - Test with real data
   - Fix any bugs
   - Performance optimization

---

### Feature 2: Rekap Kebutuhan (Resource Summary) 📦
**Priority**: HIGH
**Duration**: 1 week
**Complexity**: MEDIUM

#### Description:
Summary table showing resource requirements per time period. Useful for procurement planning.

#### Requirements:
- **Backend**:
  - Calculate material requirements per period
  - Calculate labor requirements per period
  - Group by resource type
  - API endpoint: `/api/project/{id}/rekap-kebutuhan/`

- **Frontend**:
  - Table view with columns: Period, Material, Quantity, Unit, Cost
  - Grouping by klasifikasi/sub-klasifikasi
  - Export to Excel
  - Print view

#### Acceptance Criteria:
- [ ] Resource summary displays correctly
- [ ] Data grouped by period (weekly/monthly)
- [ ] Export to Excel works
- [ ] Print view formatted correctly
- [ ] Handles large datasets (>1000 items)

#### Tasks:
1. **Backend** (3 days):
   - Create `RekapKebutuhan` view
   - Implement aggregation logic
   - Add export functionality
   - Write unit tests

2. **Frontend** (2 days):
   - Create `rekap-kebutuhan-table.js` component
   - Add export button
   - Add print stylesheet
   - Write integration tests

3. **Integration** (2 days):
   - Connect to backend API
   - Test with various data sizes
   - Optimize rendering
   - Fix bugs

---

### Feature 3: Code Cleanup 🧹
**Priority**: MEDIUM
**Duration**: 2 days
**Complexity**: LOW

#### Tasks:
1. **Remove Deprecated Functions** (1 day):
   - Fully remove `buildCellValueMap()` from chart-utils.js
   - Remove fallback code from echarts-setup.js
   - Update all imports
   - Run full test suite

2. **Add Event Listeners** (1 day):
   - Add StateManager event listeners to Gantt chart
   - Add StateManager event listeners to Kurva S chart
   - Test real-time updates
   - Verify performance

---

### Feature 4: Performance Optimization ⚡
**Priority**: MEDIUM
**Duration**: 3 days
**Complexity**: MEDIUM

#### Optimizations:
1. **Chart Rendering** (1 day):
   - Debounce chart updates
   - Implement virtual scrolling for large datasets
   - Lazy load charts

2. **StateManager Caching** (1 day):
   - Add cache statistics
   - Implement cache warming
   - Optimize invalidation logic

3. **Bundle Optimization** (1 day):
   - Code splitting for charts
   - Tree shaking unused code
   - Lazy load non-critical modules

---

## 📅 Timeline

### Week 1 (Days 1-5): Kurva S Harga
- **Day 1-3**: Backend implementation
- **Day 4-5**: Frontend implementation

### Week 2 (Days 6-10): Rekap Kebutuhan
- **Day 6-8**: Backend + Frontend implementation
- **Day 9**: Integration testing
- **Day 10**: Bug fixes

### Week 3 (Days 11-15): Cleanup & Optimization
- **Day 11-12**: Code cleanup
- **Day 13-14**: Performance optimization
- **Day 15**: Integration testing + deployment

---

## 🛠️ Technical Stack

### Backend:
- Django 4.x
- Django REST Framework
- PostgreSQL
- Celery (for async tasks)

### Frontend:
- Vanilla JavaScript (ES6+)
- ECharts (for charts)
- AG Grid (for tables)
- Vite (bundler)

### Testing:
- Jest (unit tests)
- Playwright (integration tests)
- Pytest (backend tests)

---

## 📋 Acceptance Criteria

### Phase 1 Complete When:
- [x] ✅ Phase 0 complete (prerequisite)
- [ ] ⬜ Kurva S Harga implemented and tested
- [ ] ⬜ Rekap Kebutuhan implemented and tested
- [ ] ⬜ Deprecated code removed
- [ ] ⬜ Performance improvements deployed
- [ ] ⬜ All tests passing (>95% coverage)
- [ ] ⬜ Documentation updated
- [ ] ⬜ Deployed to staging
- [ ] ⬜ User acceptance testing passed

---

## 🚀 Getting Started

### Phase 1 Day 1: Kurva S Harga (Backend - Part 1)

**Goal**: Add `harga_satuan` field and create migration

**Tasks**:
1. Create migration file for `harga_satuan` field
2. Update `PekerjaanProgressWeekly` model
3. Update admin interface
4. Run migration on local database
5. Test data integrity

**Estimated Time**: 4 hours

---

## 📝 Notes

### Dependencies:
- Phase 0 must be complete ✅
- Database backup before migration
- Staging environment ready
- Test data prepared

### Risks:
- Database migration on large dataset (mitigation: batch processing)
- Chart performance with dual-axis (mitigation: debouncing)
- Excel export memory usage (mitigation: streaming)

### Out of Scope (Phase 2):
- Multi-project dashboard
- Advanced reporting
- User permissions
- Notification system

---

**Created**: 2025-11-27
**Status**: READY TO START
**Next**: Phase 1 Day 1 - Backend Implementation
