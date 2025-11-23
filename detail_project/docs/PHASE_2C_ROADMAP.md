# Phase 2C Roadmap: Chart Modules Migration

**Date**: 2025-11-20
**Status**: 🚀 **IN PROGRESS**
**Goal**: Migrate chart modules (Gantt & Kurva-S) to modern ES6
**Strategy**: Full migration for consistency, maintainability, and performance

---

## 📋 EXECUTIVE SUMMARY

### Scope
Migrate 3 legacy chart modules (1,554 lines) to modern ES6 architecture:
- **kurva_s_module.js** (733 lines) → `echarts-setup.js`
- **gantt_module.js** (705 lines) → `frappe-gantt-setup.js`
- **gantt_tab.js** (116 lines) → Integrate into main app

### Why Full Migration?
1. ✅ **Consistency**: Matches Phase 2A & 2B modern architecture
2. ✅ **Maintainability**: Clean ES6 classes, better testability
3. ✅ **Performance**: Optimized rendering, proper cleanup
4. ✅ **UI/UX**: Better theme support, responsive charts

### Timeline
- **Estimated Effort**: 12-16 hours (2 days focused work)
- **Target Completion**: 2025-11-22

---

## 🎯 MIGRATION GOALS

### Technical Goals
- [ ] ES6 class-based architecture
- [ ] Dependency injection (no global state)
- [ ] Proper lifecycle management (init, update, dispose)
- [ ] Theme support (light/dark mode)
- [ ] Responsive & performant
- [ ] Comprehensive error handling
- [ ] Detailed logging with module prefixes

### Quality Goals
- [ ] Type-safe interfaces (JSDoc)
- [ ] Unit test ready (pure functions)
- [ ] Documentation (inline JSDoc)
- [ ] Code splitting optimized
- [ ] Zero breaking changes to UI/UX

---

## 📊 MODULES TO MIGRATE

### 1. Kurva-S (S-Curve) Chart - PRIORITY 1

**Legacy**: `kurva_s_module.js` (733 lines)
**Target**: `echarts-setup.js`
**Library**: ECharts 5.x

**Key Features**:
- S-Curve visualization (planned vs actual)
- 3 calculation strategies:
  - Volume-based (weighted by pekerjaan volume)
  - Sigmoid curve (mathematical interpolation)
  - Linear interpolation (fallback)
- Theme support (light/dark)
- Responsive resizing
- Tooltip with percentage details

**Complexity**: MEDIUM
**Estimated**: 6-8 hours

---

### 2. Gantt Chart - PRIORITY 2

**Legacy**: `gantt_module.js` (705 lines)
**Target**: `frappe-gantt-setup.js`
**Library**: Frappe Gantt

**Key Features**:
- Hierarchical task tree with indentation
- View modes: Day / Week / Month
- Volume-weighted progress by tahapan
- Interactive tooltips (segment details)
- Custom bar colors
- Date range calculation

**Complexity**: MEDIUM-HIGH
**Estimated**: 6-8 hours

---

### 3. Chart Utilities - PRIORITY 3

**New Module**: `chart-utils.js`
**Purpose**: Shared utilities for both charts

**Functions**:
- `normalizeDate()` - Handle multiple date formats
- `getThemeColors()` - Dynamic theme colors
- `calculateDateRange()` - Project date bounds
- `formatPercentage()` - Consistent formatting
- `buildVolumeLookup()` - Volume map helper

**Complexity**: EASY
**Estimated**: 2 hours

---

## 🏗️ ARCHITECTURE DESIGN

### ES6 Class Structure

#### KurvaSChart Class
```javascript
export class KurvaSChart {
  constructor(state, options = {}) {
    this.state = state;
    this.options = options;
    this.chartInstance = null;
    this.resizeObserver = null;
    this.themeObserver = null;
  }

  // Lifecycle
  initialize(container)
  update(data)
  dispose()

  // Chart building
  _buildChartData()
  _buildChartOptions()
  _applyTheme()

  // Calculations
  _calculatePlannedCurve(strategy)
  _calculateActualCurve()
  _getVolumeWeightedProgress()

  // Event handlers
  _handleResize()
  _handleThemeChange()

  // Utilities
  getStats()
  validateData()
}
```

#### GanttChart Class
```javascript
export class GanttChart {
  constructor(state, options = {}) {
    this.state = state;
    this.options = options;
    this.ganttInstance = null;
    this.viewMode = 'Week';
  }

  // Lifecycle
  initialize(container)
  update(data, mode)
  dispose()

  // Task building
  _buildTasks()
  _buildTaskTree(node, level)
  _calculateTaskProgress(task)

  // View control
  changeViewMode(mode)
  _applyViewMode()

  // Event handlers
  _handleTaskClick(task)
  _handleDateChange(task, start, end)

  // Utilities
  getStats()
  validateTasks()
}
```

---

## 📅 IMPLEMENTATION PLAN

### Week 1: Core Migration (12 hours)

#### Day 1: Kurva-S Chart (6-8 hours)
- [x] ✅ Analyze legacy kurva_s_module.js
- [ ] 🔶 Extract pure functions to chart-utils.js
- [ ] 🔶 Create KurvaSChart class skeleton
- [ ] 🔶 Implement chart data calculation
- [ ] 🔶 Implement ECharts integration
- [ ] 🔶 Add theme support
- [ ] 🔶 Add resize handling
- [ ] 🔶 Test S-Curve rendering

#### Day 2: Gantt Chart (6-8 hours)
- [x] ✅ Analyze legacy gantt_module.js
- [ ] 🔶 Create GanttChart class skeleton
- [ ] 🔶 Implement task tree building
- [ ] 🔶 Implement progress calculation
- [ ] 🔶 Integrate Frappe Gantt
- [ ] 🔶 Add view mode switching
- [ ] 🔶 Add event handlers
- [ ] 🔶 Test Gantt rendering

### Week 2: Integration & Testing (4 hours)

#### Day 3: Integration (2 hours)
- [ ] 🔶 Update jadwal_kegiatan_app.js
- [ ] 🔶 Add chart imports
- [ ] 🔶 Initialize chart instances
- [ ] 🔶 Connect to tab switching
- [ ] 🔶 Update vite.config.js

#### Day 4: Testing & Docs (2 hours)
- [ ] 🔶 Test S-Curve with real data
- [ ] 🔶 Test Gantt with real data
- [ ] 🔶 Test theme switching
- [ ] 🔶 Test responsive behavior
- [ ] 🔶 Create PHASE_2C_PROGRESS.md
- [ ] 🔶 Update main roadmap

---

## 🔧 TECHNICAL SPECIFICATIONS

### Dependencies
```json
{
  "echarts": "^5.4.0",
  "frappe-gantt": "^0.6.1"
}
```

### File Structure
```
detail_project/static/detail_project/js/src/modules/
├── kurva-s/
│   └── echarts-setup.js          (NEW - KurvaSChart class)
├── gantt/
│   └── frappe-gantt-setup.js     (NEW - GanttChart class)
└── shared/
    └── chart-utils.js             (NEW - Shared utilities)
```

### Vite Configuration
```javascript
'chart-modules': [
  path.resolve(__dirname,
    'detail_project/static/detail_project/js/src/modules/kurva-s/echarts-setup.js'),
  path.resolve(__dirname,
    'detail_project/static/detail_project/js/src/modules/gantt/frappe-gantt-setup.js'),
  path.resolve(__dirname,
    'detail_project/static/detail_project/js/src/modules/shared/chart-utils.js'),
],
```

---

## 🎨 UI/UX REQUIREMENTS

### Consistency with Phase 2B
- Same logging format: `[ModuleName] Message`
- Same error handling pattern
- Same initialization lifecycle
- Same theme support mechanism

### Performance Targets
- Initial render: < 100ms
- Update render: < 50ms
- Theme switch: < 30ms
- Memory leak: 0 (proper cleanup)

### Responsive Behavior
- Charts resize on window resize
- Debounced resize handler (150ms)
- Maintain aspect ratio
- Mobile-friendly tooltips

---

## 🧪 TESTING CHECKLIST

### Kurva-S Chart Tests
- [ ] Chart renders with planned curve
- [ ] Chart shows actual curve when data exists
- [ ] Tooltip displays correct percentages
- [ ] Theme switches correctly (light/dark)
- [ ] Chart resizes responsively
- [ ] No console errors
- [ ] Proper cleanup on dispose

### Gantt Chart Tests
- [ ] Tasks render in tree hierarchy
- [ ] Task indentation reflects depth
- [ ] Progress bars show correct percentage
- [ ] View mode switches (Day/Week/Month)
- [ ] Tooltips show segment details
- [ ] Date ranges calculate correctly
- [ ] No console errors
- [ ] Proper cleanup on dispose

### Integration Tests
- [ ] Charts initialize on tab switch
- [ ] Charts update on data change
- [ ] Charts dispose on tab close
- [ ] No memory leaks
- [ ] Theme observer works
- [ ] Resize observer works

---

## 📈 SUCCESS METRICS

### Code Quality
- ✅ Zero global state dependencies
- ✅ 100% ES6 modules
- ✅ JSDoc coverage > 90%
- ✅ No linter errors
- ✅ Consistent code style

### Performance
- ✅ Bundle size < 100KB (chart chunk)
- ✅ Initial load < 200ms
- ✅ Memory usage stable
- ✅ No layout thrashing

### Maintainability
- ✅ Clear separation of concerns
- ✅ Pure functions extracted
- ✅ Easy to test
- ✅ Well documented

---

## 🚨 RISK MITIGATION

### High Risk: Complex Algorithms
**Risk**: S-Curve calculation algorithms are complex
**Mitigation**:
- Extract to pure functions first
- Unit test each strategy
- Keep legacy code as reference
- Validate results match legacy

### Medium Risk: Third-Party Libraries
**Risk**: ECharts/Frappe Gantt API changes
**Mitigation**:
- Pin exact versions in package.json
- Check documentation carefully
- Test thoroughly before release

### Low Risk: Theme Integration
**Risk**: Theme colors don't match design
**Mitigation**:
- Extract colors to shared constants
- Use CSS variables when possible
- Test both light/dark modes

---

## 📦 DELIVERABLES

### Code Files
1. `echarts-setup.js` (~400 lines)
2. `frappe-gantt-setup.js` (~400 lines)
3. `chart-utils.js` (~200 lines)
4. Updated `jadwal_kegiatan_app.js` (~50 lines modified)
5. Updated `vite.config.js` (~10 lines)

### Documentation
1. `CHART_MODULES_ANALYSIS.md` (already created)
2. `PHASE_2C_PROGRESS.md` (to be created)
3. `PHASE_2C_ROADMAP.md` (this file)
4. Inline JSDoc in all files

### Testing
1. Manual browser testing checklist
2. Console log verification
3. Performance profiling results

---

## 🎯 ALIGNMENT WITH PROJECT GOALS

### Consistency ✅
- Matches Phase 2A & 2B architecture
- Same patterns, same conventions
- Unified codebase

### Maintainability ✅
- Clean, testable code
- Clear documentation
- Easy to extend

### Performance ✅
- Optimized rendering
- Proper cleanup
- Code splitting

### UI/UX ✅
- No breaking changes
- Better responsiveness
- Smooth theme switching

---

## 📞 NEXT ACTIONS

### Immediate (Today)
1. ✅ Create roadmap document (this file)
2. 🔶 Start Kurva-S chart migration
3. 🔶 Extract chart utilities

### Tomorrow
1. 🔶 Complete Kurva-S chart
2. 🔶 Start Gantt chart migration

### Day After
1. 🔶 Complete Gantt chart
2. 🔶 Integration & testing
3. 🔶 Documentation

---

**Last Updated**: 2025-11-20
**Status**: Ready to start implementation
**Confidence**: High (based on Phase 2B success)
