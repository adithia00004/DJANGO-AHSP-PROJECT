# Gantt Chart - Comprehensive Fixes Required

**Date:** 2025-12-03
**Status:** Planning Phase

---

## User-Reported Issues

### 1. "Undefined" Names in Tree Panel
**Problem:** Some nodes showing "Undefined" as name
**Root Cause:** Data includes klasifikasi/sub-klasifikasi nodes but only pekerjaan nodes have names filled properly
**Fix:** Filter to send only pekerjaan nodes; data model builds parent hierarchy from IDs/names

### 2. Tree Hierarchy Mismatch
**Problem:** Tree structure doesn't match Rekap RAB hierarchical structure
**Expected:** Klasifikasi → Sub-Klasifikasi → Pekerjaan (3 levels)
**Current:** Incorrect parent-child relationships
**Fix:** Ensure data model correctly infers hierarchy from pekerjaan data

### 3. Toggle Dropdown Not Working
**Problem:** Expand/collapse buttons don't function
**Root Cause:** Event delegation not catching clicks OR nodes don't have children
**Fix:** Check event handler + ensure parent nodes have isLeaf() = false

### 4. Bar Visibility Issues
**Problem:** Planned vs Actual bars not clearly distinguishable
**Current:** Blue (planned) and Orange (actual) too similar
**Fix:**
- Increase contrast
- Make planned bar MORE transparent (opacity: 0.4)
- Make actual bar SOLID (opacity: 1.0)
- Add stroke/border to bars

### 5. Grid Lines Inconsistent
**Problem:** Grid lines don't match week/month standards
**Expected:**
  - Week mode: Vertical grid every 7 days (week boundaries)
  - Month mode: Vertical grid every 4 weeks (28 days), labeled as months
**Current:** Grid doesn't follow this pattern
**Fix:** Update `_renderScale()` in timeline panel

### 6. Zoom Options Too Many
**Problem:** Shows Day/Week/Month/Quarter
**Expected:** Only Week and Month
**Fix:** Remove Day and Quarter buttons from toolbar

### 7. Non-Functional Features

#### 7.1 Fit to Screen
**Problem:** Button doesn't work
**Fix:** Implement `_fitToScreen()` calculation

#### 7.2 Today Button
**Problem:** Button doesn't scroll to today
**Fix:** Implement `_scrollToToday()` with today marker

#### 7.3 Milestone Marking
**Problem:** No way to add milestones with comments
**Fix:** Add click handler on timeline to create milestones + popup form

#### 7.4 Search
**Problem:** Search doesn't filter/show results
**Fix:** Verify `_filterNodesBySearch()` implementation

### 8. Alignment Issues

#### 8.1 Header Misalignment
**Problem:** Tree header doesn't align with timeline header
**Fix:** Ensure same height for:
- Tree panel header
- Timeline toolbar
- Timeline scale header

#### 8.2 Row Misalignment
**Problem:** Tree rows don't align with timeline bars
**Fix:** Ensure same `rowHeight` (40px) for both panels

#### 8.3 Stats Bar Causes Misalignment
**Problem:** `tree-stats-bar` adds extra height on left side
**Solution:** Hide stats bar OR add equivalent spacer on timeline side

---

## Implementation Plan

### Phase 1: Data & Hierarchy Fixes (Critical)
1. Update `_prepareGanttData()` - filter to pekerjaan only
2. Verify data model builds correct 3-level hierarchy
3. Test tree rendering with correct names
4. Fix expand/collapse functionality

### Phase 2: Visual Improvements
1. Update bar colors/opacity for better distinction
2. Fix grid lines (week = 7 days, month = 28 days)
3. Remove Day/Quarter zoom options
4. Align headers and rows

### Phase 3: Functional Features
1. Implement Fit to Screen
2. Implement Today button
3. Fix Search filtering
4. Add Milestone creation UI

### Phase 4: Polish & Testing
1. Remove stats bar or add timeline equivalent
2. Comprehensive testing
3. Documentation update

---

## Detailed Fixes

### Fix 1: Data Preparation (jadwal_kegiatan_app.js)

```javascript
_prepareGanttData() {
  const data = [];

  if (this.state?.flatPekerjaan && Array.isArray(this.state.flatPekerjaan)) {
    // ✅ FILTER: Only pekerjaan nodes (actual tasks)
    const pekerjaanNodes = this.state.flatPekerjaan.filter(n => n.type === 'pekerjaan');

    console.log(`Transforming ${pekerjaanNodes.length} pekerjaan for Gantt`);

    pekerjaanNodes.forEach(node => {
      // Pekerjaan nodes already have complete parent info
      const progressRencana = this._calculateProgress(node, 'planned');
      const progressRealisasi = this._calculateProgress(node, 'actual');

      data.push({
        // IDs
        klasifikasi_id: node.klasifikasi_id,
        sub_klasifikasi_id: node.sub_klasifikasi_id,
        pekerjaan_id: node.id,

        // Names (pekerjaan node has parent names)
        klasifikasi_name: node.klasifikasi_name || 'Unknown Klasifikasi',
        klasifikasi_kode: node.klasifikasi_kode || '',

        sub_klasifikasi_name: node.sub_klasifikasi_name || 'Unknown Sub-Klasifikasi',
        sub_klasifikasi_kode: node.sub_klasifikasi_kode || '',

        pekerjaan_name: node.name || 'Unknown Pekerjaan',
        pekerjaan_kode: node.kode || '',

        // Dates
        tgl_mulai_rencana: node.tgl_mulai_rencana || this.state.projectStart,
        tgl_selesai_rencana: node.tgl_selesai_rencana || this.state.projectEnd,
        tgl_mulai_realisasi: node.tgl_mulai_realisasi || this.state.projectStart,
        tgl_selesai_realisasi: node.tgl_selesai_realisasi || this.state.projectEnd,

        // Progress
        progress_rencana: progressRencana,
        progress_realisasi: progressRealisasi,

        // Volume
        volume: node.volume || 0,
        satuan: node.satuan || ''
      });
    });
  }

  return {
    data,
    project: {
      project_id: this.state.projectId,
      project_name: this.state.projectName,
      start_date: this.state.projectStart,
      end_date: this.state.projectEnd
    },
    milestones: []
  };
}
```

### Fix 2: Timeline Toolbar (gantt-timeline-panel.js)

```html
<!-- BEFORE: 4 zoom options -->
<button data-zoom="day">Day</button>
<button data-zoom="week">Week</button>
<button data-zoom="month">Month</button>
<button data-zoom="quarter">Quarter</button>

<!-- AFTER: 2 zoom options only -->
<button data-zoom="week" class="active">Week</button>
<button data-zoom="month">Month</button>
```

### Fix 3: Bar Rendering (gantt-timeline-panel.js)

```javascript
_renderBar(ctx, taskBar, y, colors, type, height = 24) {
  const startX = this._dateToX(taskBar.startDate);
  const endX = this._dateToX(taskBar.endDate);
  const width = endX - startX;

  // Different opacity for planned vs actual
  if (type === 'planned') {
    // Planned: Semi-transparent with border
    ctx.globalAlpha = 0.4;
    ctx.fillStyle = '#0d6efd'; // Blue
    ctx.fillRect(startX, y, width, height);

    // Border for visibility
    ctx.globalAlpha = 1.0;
    ctx.strokeStyle = '#0d6efd';
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, y, width, height);
  } else {
    // Actual: Solid with darker border
    ctx.globalAlpha = 1.0;
    ctx.fillStyle = '#fd7e14'; // Orange
    ctx.fillRect(startX, y, width, height);

    ctx.strokeStyle = '#dc6d08'; // Darker orange
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, y, width, height);
  }

  // Progress fill
  const progressWidth = (width * taskBar.progress) / 100;
  if (progressWidth > 0) {
    ctx.globalAlpha = 1.0;
    ctx.fillStyle = type === 'planned' ? '#084298' : '#b34d00';
    ctx.fillRect(startX, y, progressWidth, height);
  }

  ctx.globalAlpha = 1.0; // Reset
}
```

### Fix 4: Grid Lines (gantt-timeline-panel.js)

```javascript
_renderScale() {
  const ctx = this.canvas.scaleCtx;
  const zoom = this.options.zoom;

  if (zoom === 'week') {
    // Draw grid every 7 days
    let currentDate = new Date(this.dateRange.start);
    while (currentDate <= this.dateRange.end) {
      const x = this._dateToX(currentDate);

      // Vertical grid line
      ctx.strokeStyle = '#dee2e6';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.totalHeight);
      ctx.stroke();

      // Week label
      const weekNum = this._getWeekNumber(currentDate);
      ctx.fillStyle = '#6c757d';
      ctx.font = '12px sans-serif';
      ctx.fillText(`Week ${weekNum}`, x + 5, 20);

      // Move to next week (7 days)
      currentDate.setDate(currentDate.getDate() + 7);
    }
  } else if (zoom === 'month') {
    // Draw grid every 4 weeks (28 days) but label as months
    let currentDate = new Date(this.dateRange.start);
    let monthNum = 0;

    while (currentDate <= this.dateRange.end) {
      const x = this._dateToX(currentDate);

      // Vertical grid line
      ctx.strokeStyle = '#dee2e6';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.totalHeight);
      ctx.stroke();

      // Month label
      const monthName = currentDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      ctx.fillStyle = '#6c757d';
      ctx.font = '12px sans-serif';
      ctx.fillText(monthName, x + 5, 20);

      // Move to next 4-week period (28 days)
      currentDate.setDate(currentDate.getDate() + 28);
      monthNum++;
    }
  }
}
```

### Fix 5: Remove Stats Bar (gantt-tree-panel.js)

```javascript
_buildDOM() {
  this.container.innerHTML = '';
  this.container.className = 'gantt-tree-panel';

  // Header with search
  if (this.options.showSearch) {
    const header = document.createElement('div');
    header.className = 'tree-panel-header';
    // ... search input ...
    this.container.appendChild(header);
  }

  // ❌ REMOVE Stats Bar for alignment
  // if (this.options.showStats) {
  //   const statsBar = document.createElement('div');
  //   statsBar.className = 'tree-stats-bar';
  //   this.container.appendChild(statsBar);
  //   this.elements.statsBar = statsBar;
  // }

  // Tree content
  const treeContent = document.createElement('div');
  treeContent.className = 'tree-content';
  this.container.appendChild(treeContent);
  this.elements.treeContent = treeContent;

  // Resize handle
  const resizeHandle = document.createElement('div');
  resizeHandle.className = 'tree-resize-handle';
  this.container.appendChild(resizeHandle);
  this.elements.resizeHandle = resizeHandle;
}
```

OR add equivalent spacer on timeline side.

### Fix 6: Fit to Screen (gantt-timeline-panel.js)

```javascript
_fitToScreen() {
  const contentWidth = this.elements.content.offsetWidth;
  const totalDays = this.dateRange.totalDays;

  // Calculate pixels per day to fit all content
  this.canvas.pixelsPerDay = Math.max(0.5, contentWidth / totalDays);
  this.canvas.totalWidth = this.dateRange.totalDays * this.canvas.pixelsPerDay;

  // Update canvas sizes
  this.canvas.timeline.style.width = this.canvas.totalWidth + 'px';
  this.canvas.scale.style.width = this.canvas.totalWidth + 'px';

  // Re-render
  this._scheduleRender();

  console.log(`Fit to screen: ${this.canvas.pixelsPerDay.toFixed(2)} px/day`);
}
```

### Fix 7: Today Button (gantt-timeline-panel.js)

```javascript
_scrollToToday() {
  const today = new Date();

  // Check if today is within date range
  if (today < this.dateRange.start || today > this.dateRange.end) {
    Toast.warning('Today is outside the project date range');
    return;
  }

  const daysFromStart = Math.floor((today - this.dateRange.start) / (1000 * 60 * 60 * 24));
  const scrollX = daysFromStart * this.canvas.pixelsPerDay - (this.elements.content.offsetWidth / 2);

  this.elements.content.scrollLeft = Math.max(0, scrollX);

  // Draw today marker (in render)
  this.todayMarkerVisible = true;
  this._scheduleRender();

  console.log(`Scrolled to today: ${today.toLocaleDateString()}`);
}
```

---

## Testing Checklist

After all fixes:

- [ ] No "Undefined" names
- [ ] Correct 3-level hierarchy (Klasifikasi → Sub → Pekerjaan)
- [ ] Expand/collapse works
- [ ] Blue (planned) and Orange (actual) clearly distinguishable
- [ ] Week mode: Grid every 7 days
- [ ] Month mode: Grid every 28 days (4 weeks)
- [ ] Only Week/Month zoom buttons
- [ ] Fit to Screen works
- [ ] Today button scrolls and shows marker
- [ ] Search filters correctly
- [ ] Tree and timeline headers aligned
- [ ] Tree and timeline rows aligned
- [ ] No stats bar (or has timeline equivalent)

---

**Next Step:** Implement fixes systematically, starting with Phase 1 (Data & Hierarchy).

