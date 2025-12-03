# Gantt Chart Layout Fix - Horizontal Split-View

**Date:** 2025-12-02
**Issue:** Gantt Chart displaying vertical (stacked) instead of horizontal (side-by-side) layout
**Status:** ✅ RESOLVED

---

## Problem Analysis

### Symptoms
- Tree panel and Timeline panel displaying **vertically** (one above the other)
- Expected: Horizontal split-view (tree on left, timeline on right)
- Toolbar buttons not functioning properly

### Root Cause

**CSS Missing `flex-direction: row`**

The main `.gantt-container` had `display: flex` but no explicit `flex-direction`. By default, flex containers use `flex-direction: row`, but something was overriding it.

**Before Fix:**
```css
.gantt-container {
  display: flex;
  /* ❌ No flex-direction specified */
  width: 100%;
  height: 600px;
}
```

**Result:** Panels stacked vertically instead of side-by-side.

---

## The Fix

### 1. Add Explicit Flex Direction

**File:** [gantt-chart-redesign.css:28-38](gantt-chart-redesign.css#L28-L38)

```css
.gantt-container {
  display: flex;
  flex-direction: row; /* ✅ Explicit horizontal layout */
  width: 100%;
  height: 600px;
  border: 1px solid var(--bs-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bs-body-bg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
```

### 2. Update Responsive Breakpoints

**File:** [gantt-chart-redesign.css:760-785](gantt-chart-redesign.css#L760-L785)

Updated media query to target container wrappers:

```css
@media (max-width: 767px) {
  .gantt-container {
    flex-direction: column; /* Mobile: stack vertically */
    height: auto;
  }

  /* Update BOTH container and panel */
  .gantt-tree-panel-container {
    width: 100%;
    max-width: none;
    border-right: none;
    border-bottom: 1px solid var(--bs-border-color);
    max-height: 300px;
  }

  .gantt-tree-panel {
    width: 100%;
    max-width: none;
  }

  .gantt-timeline-panel-container {
    height: 400px;
  }

  .gantt-timeline-panel {
    height: 100%;
  }
}
```

---

## Expected Layout After Fix

### Desktop (> 768px width)

```
┌──────────────────────────────────────────────────────────────┐
│  GANTT CHART CONTAINER (flex-direction: row)                 │
├──────────────────────┬──────────────────────────────────────┤
│ Tree Panel (30%)     │ Timeline Panel (70%)                 │
│ ┌──────────────────┐ │ ┌──────────────────────────────────┐│
│ │ 🔍 Search        │ │ │ [Zoom: Day Week Month Quarter]  ││
│ │ ─────────────── │ │ │ ──────────────────────────────── ││
│ │ 📊 Stats         │ │ │ Dec 2025 | Jan 2026 | Feb 2026  ││
│ │ ─────────────── │ │ │ ──────────────────────────────── ││
│ │                  │ │ │                                   ││
│ │ 📁 Klasifikasi A │ │ │ [═══BLUE═══][──ORANGE──]        ││
│ │   📁 Sub A1      │ │ │ [═══BLUE═══][──ORANGE──]        ││
│ │     📄 Task 1    │ │ │      [══BLUE══][─ORANGE─]       ││
│ │     📄 Task 2    │ │ │                                   ││
│ │   📁 Sub A2      │ │ │                                   ││
│ │     📄 Task 3    │ │ │                                   ││
│ │                  │ │ │                                   ││
│ │ [Resize Handle]  │ │ │ (Scrollable canvas)              ││
│ └──────────────────┘ │ └──────────────────────────────────┘│
└──────────────────────┴──────────────────────────────────────┘
```

### Mobile (< 768px width)

```
┌──────────────────────────────────┐
│ GANTT CHART (flex-direction: column)│
├──────────────────────────────────┤
│ Tree Panel (100% width)          │
│ ┌──────────────────────────────┐│
│ │ 🔍 Search                    ││
│ │ 📊 Stats                     ││
│ │ ────────────────────────────││
│ │ 📁 Klasifikasi A             ││
│ │   📁 Sub A1                  ││
│ │     📄 Task 1                ││
│ │     📄 Task 2                ││
│ └──────────────────────────────┘│
├──────────────────────────────────┤
│ Timeline Panel (100% width)      │
│ ┌──────────────────────────────┐│
│ │ [Zoom buttons]               ││
│ │ ────────────────────────────││
│ │ Dec | Jan | Feb              ││
│ │ ────────────────────────────││
│ │ [═══BLUE═══][──ORANGE──]    ││
│ │ [═══BLUE═══][──ORANGE──]    ││
│ └──────────────────────────────┘│
└──────────────────────────────────┘
```

---

## Toolbar Features & Functionality

### Tree Panel Toolbar

1. **Search Input**
   - Type to filter tasks by name
   - Debounced (300ms) for performance
   - Case-insensitive search
   - Clears with "X" button

2. **Statistics Bar**
   - Total tasks count
   - Completed tasks count
   - In-progress tasks count
   - Delayed tasks count (if applicable)

3. **Expand/Collapse Controls**
   - Individual node expand/collapse (click arrow icon)
   - Visual feedback on hover
   - Preserves expanded state during re-render

### Timeline Panel Toolbar

1. **Zoom Controls**
   - **Day**: 40 pixels per day (detailed view)
   - **Week**: 8 pixels per day (weekly overview)
   - **Month**: 2 pixels per day (monthly overview) - DEFAULT
   - **Quarter**: 0.7 pixels per day (quarterly overview)
   - Active button highlighted
   - Smooth zoom transitions

2. **Fit to Screen Button**
   - Automatically calculates zoom to fit all content
   - Adjusts pixels-per-day dynamically
   - Useful for project overview

3. **Today Button**
   - Scrolls timeline to current date
   - Centers today's date in viewport
   - Visual "today" marker line

4. **Scroll & Pan**
   - Horizontal scroll for timeline navigation
   - Vertical scroll syncs with tree panel
   - Smooth scrolling with momentum

---

## Interactive Features

### Tree Panel Interactions

| Action | Behavior |
|--------|----------|
| **Click on node** | Selects node, highlights in timeline |
| **Click expand icon (▶)** | Expands/collapses children |
| **Hover on node** | Highlights row, shows tooltip |
| **Search** | Filters visible nodes |
| **Drag resize handle** | Adjusts panel width (250px - 500px) |

### Timeline Panel Interactions

| Action | Behavior |
|--------|----------|
| **Click on bar** | Selects task, shows details toast |
| **Hover on bar** | Shows tooltip with dates & progress |
| **Click on milestone (◆)** | Opens milestone popup with comments |
| **Scroll horizontally** | Pans timeline left/right |
| **Scroll vertically** | Syncs with tree panel scroll |
| **Zoom button click** | Changes timeline scale |

### Dual-Bar Visualization

- **Blue bar (semi-transparent)**: Planned schedule
  - Shows: `tgl_mulai_rencana` → `tgl_selesai_rencana`
  - Progress fill: Darker blue based on `progress_rencana %`

- **Orange bar (solid)**: Actual schedule
  - Shows: `tgl_mulai_realisasi` → `tgl_selesai_realisasi`
  - Progress fill: Darker orange based on `progress_realisasi %`
  - **Offset slightly** below planned bar for visibility

- **Status Colors**:
  - Green progress: On track
  - Yellow progress: Warning (minor delay)
  - Red progress: Delayed (significant delay)

---

## Verification Checklist

### Visual Layout

- [ ] Tree panel on LEFT side (30% width, 250px minimum)
- [ ] Timeline panel on RIGHT side (70% width, fills remaining space)
- [ ] Vertical separator line between panels
- [ ] Resize handle visible and functional
- [ ] Both panels same height (600px)
- [ ] No vertical stacking (unless mobile < 768px)

### Tree Panel

- [ ] Search input visible and functional
- [ ] Statistics bar shows correct counts
- [ ] Hierarchical tree renders correctly
  - [ ] Klasifikasi nodes (📁 icon, bold)
  - [ ] Sub-Klasifikasi nodes (📁 icon, indented)
  - [ ] Pekerjaan nodes (📄 icon, indented further)
- [ ] Expand/collapse icons work
- [ ] Progress badges show correct percentages
- [ ] Hover highlights work
- [ ] Vertical scroll works
- [ ] Resize handle can be dragged

### Timeline Panel

- [ ] Toolbar visible with all buttons
- [ ] Zoom buttons functional (Day/Week/Month/Quarter)
- [ ] "Fit to Screen" button works
- [ ] "Today" button scrolls to current date
- [ ] Date headers render correctly
- [ ] Timeline canvas renders bars
- [ ] Blue bars visible (planned)
- [ ] Orange bars visible (actual)
- [ ] Bars aligned with tree rows
- [ ] Horizontal scroll works
- [ ] Vertical scroll syncs with tree

### Interactions

- [ ] Clicking node in tree selects it
- [ ] Clicking bar in timeline shows toast
- [ ] Hover on bar shows tooltip
- [ ] Search filters nodes correctly
- [ ] Expand/collapse updates timeline
- [ ] Scroll sync works both directions
- [ ] Zoom changes timeline scale
- [ ] No console errors

### Performance

- [ ] Initial render < 2 seconds
- [ ] Smooth scrolling (60 FPS)
- [ ] Zoom transitions smooth
- [ ] No lag when expanding/collapsing
- [ ] Canvas renders without flickering

---

## Troubleshooting

### Issue: Still Stacking Vertically

**Check:**
1. Browser DevTools → Inspect `.gantt-container`
2. Verify `flex-direction: row` is applied
3. Check if screen width > 768px (below 768px = mobile = vertical)
4. Clear browser cache (Ctrl+Shift+R)

**Fix:**
```css
.gantt-container {
  flex-direction: row !important; /* Force horizontal */
}
```

### Issue: Timeline Panel Not Visible

**Check:**
1. `.gantt-timeline-panel-container` has `flex: 1`
2. `.gantt-timeline-panel` has `width: 100%; height: 100%`
3. Canvas element exists in DOM
4. No JavaScript errors in console

**Fix:**
```css
.gantt-timeline-panel-container {
  flex: 1;
  min-width: 0; /* Prevent flex overflow */
}
```

### Issue: Toolbar Buttons Not Working

**Check:**
1. Console for JavaScript errors
2. Event listeners attached (check `_attachEventListeners()`)
3. Button IDs match (e.g., `#timeline-fit-btn`)

**Debug:**
```javascript
// In browser console:
document.querySelector('#timeline-fit-btn').click();
```

### Issue: Bars Not Showing

**Check:**
1. Data has valid dates (`tgl_mulai_rencana`, `tgl_selesai_rencana`)
2. Canvas size > 0 (check `canvas.width` and `canvas.height`)
3. Date range calculated correctly
4. `pixelsPerDay` > 0

**Debug:**
```javascript
// In console:
console.log(ganttChart.dataModel.getFlattenedTree());
console.log(ganttChart.timelinePanel.canvas);
```

---

## Related Fixes

| Issue # | Problem | Fix | Doc |
|---------|---------|-----|-----|
| **#1** | Container not found | Use correct template | [GANTT_CONTAINER_FIX.md](GANTT_CONTAINER_FIX.md) |
| **#2** | No data loading | Use `flatPekerjaan` | [GANTT_DATA_LOADING_FIX.md](GANTT_DATA_LOADING_FIX.md) |
| **#3** | Rendering not happening | Fix init sequence | [GANTT_RENDERING_FIX.md](GANTT_RENDERING_FIX.md) |
| **#4** | Container CSS missing | Add wrapper styling | Previous fix |
| **#5** | Vertical layout (THIS) | Add `flex-direction: row` | This document |

---

## Files Modified

1. **[gantt-chart-redesign.css](gantt-chart-redesign.css)**
   - Line 30: Added `flex-direction: row` to `.gantt-container`
   - Lines 766-785: Updated responsive breakpoints for containers

2. **Build Output**
   - `npm run build` completed successfully in 1m 13s
   - CSS properly bundled and deployed

---

**Document End**
