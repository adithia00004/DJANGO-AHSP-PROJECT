# 📊 LAPORAN ANALISIS LENGKAP: BARCHART OVERFLOW ISSUE

**Date:** 2025-12-10
**Issue:** Canvas barchart menutupi frozen column (left panel) saat horizontal scroll
**Status:** UNDER INVESTIGATION

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Backend Data Flow](#backend-data-flow)
3. [Frontend Rendering Pipeline](#frontend-rendering-pipeline)
4. [DOM Structure & Hierarchy](#dom-structure--hierarchy)
5. [CSS Layout & Positioning](#css-layout--positioning)
6. [Canvas Rendering Mechanism](#canvas-rendering-mechanism)
7. [Root Cause Analysis](#root-cause-analysis)
8. [Attempted Solutions](#attempted-solutions)
9. [Technical Constraints](#technical-constraints)
10. [Recommendations](#recommendations)

---

## 🎯 EXECUTIVE SUMMARY

### Problem Statement
Ketika user melakukan **horizontal scroll** pada right panel (scrollable area), **canvas barchart overlay** yang menampilkan Gantt bars **menutupi left panel** (frozen column) yang seharusnya tetap visible di atas.

### Impact
- **UX Critical:** User tidak bisa melihat klasifikasi/sub-klasifikasi/pekerjaan saat scroll
- **Visual Bug:** Barchart "overflow" secara visual keluar dari container boundaries
- **Z-index Confusion:** Meskipun z-index sudah diatur, canvas tetap muncul di atas frozen column

### Key Finding
**Masalah BUKAN hanya z-index**, tapi kombinasi dari:
1. Canvas menggunakan `position: absolute` dengan `left: 0`
2. Canvas size = **full scrollWidth** (bukan hanya visible viewport)
3. Browser rendering engine tidak men-clip absolutely positioned elements dengan benar dalam scroll container
4. CSS `overflow: hidden` tidak bekerja efektif pada absolutely positioned children dalam certain contexts

---

## 🔄 BACKEND DATA FLOW

### 1. Django View Layer

**File:** `detail_project/views.py`

**Function:** `kelola_tahapan_grid_modern(request, project_id)`

```python
# Simplified flow:
def kelola_tahapan_grid_modern(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    # Fetch data
    klasifikasi_list = Klasifikasi.objects.filter(project=project)
    sub_klasifikasi_list = SubKlasifikasi.objects.filter(klasifikasi__project=project)
    pekerjaan_list = Pekerjaan.objects.filter(
        sub_klasifikasi__klasifikasi__project=project
    ).select_related('sub_klasifikasi__klasifikasi')

    # Serialize to JSON
    context = {
        'project': project,
        'klasifikasi_list_json': json.dumps([...]),
        'sub_klasifikasi_list_json': json.dumps([...]),
        'pekerjaan_list_json': json.dumps([...]),
    }

    return render(request, 'detail_project/kelola_tahapan_grid_modern.html', context)
```

**Data Structure Sent to Frontend:**
```json
{
  "klasifikasi": [
    {
      "id": 1,
      "kode": "1",
      "nama": "PEKERJAAN PERSIAPAN",
      "project_id": 123
    }
  ],
  "sub_klasifikasi": [
    {
      "id": 1,
      "kode": "1.1",
      "nama": "Mobilisasi",
      "klasifikasi_id": 1
    }
  ],
  "pekerjaan": [
    {
      "id": 1,
      "kode": "1.1.1",
      "uraian": "Mobilisasi Peralatan",
      "volume": 1.00,
      "satuan": "ls",
      "sub_klasifikasi_id": 1,
      "progres_mingguan": {
        "2024-01-01": 10.5,
        "2024-01-08": 25.0,
        ...
      },
      "progres_harian": {...},
      "progres_bulanan": {...}
    }
  ]
}
```

**No Backend Rendering:** Backend hanya mengirim raw JSON data, **TIDAK** ada HTML rendering untuk barchart.

---

## ⚙️ FRONTEND RENDERING PIPELINE

### Phase 1: Application Bootstrap

**File:** `static/detail_project/js/src/jadwal_kegiatan_app.js`

```javascript
class JadwalKegiatanApp {
  async initialize(config) {
    // 1. Setup state
    this._setupState(config);

    // 2. Load data from backend
    await this._loadInitialData();

    // 3. Initialize UnifiedTableManager
    this.unifiedManager = new UnifiedTableManager({
      state: this.state,
      stateManager: this.stateManager,
      domTargets: {
        gridContainer: this._refs.gridContainer,
        ...
      }
    });

    // 4. Render initial grid
    await this.unifiedManager.initialize();
  }
}
```

**Flow:**
```
JadwalKegiatanApp.initialize()
  ↓
DataLoader.loadInitialData()
  ↓
UnifiedTableManager.initialize()
  ↓
TanStackGridManager.mount()
  ↓
(User switches to Gantt mode)
  ↓
UnifiedTableManager.switchMode('gantt')
  ↓
GanttCanvasOverlay.show() ← **BARCHART DIBUAT DI SINI**
```

### Phase 2: UnifiedTableManager Mode Switching

**File:** `static/detail_project/js/src/modules/unified/UnifiedTableManager.js`

```javascript
export class UnifiedTableManager {
  switchMode(newMode) {
    // Switch cell renderer
    const targetRenderer = newMode === 'gantt' ? 'gantt' : 'input';
    this.tanstackGrid.setCellRenderer(targetRenderer);

    // Show/hide overlays
    if (newMode === 'gantt') {
      // CREATE CANVAS OVERLAY HERE!
      if (!this.overlays.gantt) {
        this.overlays.gantt = new GanttCanvasOverlay(this.tanstackGrid);
      }
      this.overlays.gantt.show(); // ← Canvas di-append ke DOM
      this._refreshGanttOverlay();
    } else {
      // Hide overlay when not in gantt mode
      this.overlays.gantt?.hide();
    }
  }

  _refreshGanttOverlay() {
    if (!this.overlays.gantt) return;

    // Extract bar data from cells
    const barData = [];
    this.state.tree.forEach(klas => {
      klas.subKlasifikasi?.forEach(subKlas => {
        subKlas.pekerjaan?.forEach(pek => {
          // Parse progress data into bars
          const bars = this._parseProgressToGanttBars(pek);
          barData.push(...bars);
        });
      });
    });

    // Update canvas with bar data
    this.overlays.gantt.setBarData(barData);
  }
}
```

**Key Point:** `GanttCanvasOverlay` dibuat **on-demand** saat user switch ke Gantt mode, BUKAN saat initial load.

### Phase 3: GanttCanvasOverlay Creation

**File:** `static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js`

```javascript
export class GanttCanvasOverlay {
  constructor(tableManager) {
    this.tableManager = tableManager;

    // CREATE CANVAS ELEMENT
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'gantt-canvas-overlay';

    // INLINE STYLES - CRITICAL!
    this.canvas.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: auto;
      z-index: 1;  // ← Recently changed from 10
    `;

    this.ctx = this.canvas.getContext('2d');
    this.visible = false;
    this.barData = [];
  }

  show() {
    if (this.visible) return;

    const scrollArea = this.tableManager?.bodyScroll; // .tanstack-grid-body
    if (!scrollArea) return;

    // Force parent to be positioned
    scrollArea.style.position = scrollArea.style.position || 'relative';
    scrollArea.style.overflow = 'auto';

    // CRITICAL FIX (Latest attempt):
    scrollArea.parentElement.style.overflow = 'hidden';
    scrollArea.parentElement.style.position = 'relative';

    // APPEND CANVAS TO DOM
    scrollArea.appendChild(this.canvas); // ← Canvas masuk ke .tanstack-grid-body

    this.visible = true;
    this.syncWithTable();
  }

  syncWithTable() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    // CANVAS SIZE = FULL SCROLL AREA (NOT JUST VISIBLE VIEWPORT!)
    this.canvas.width = scrollArea.scrollWidth;   // ← Bisa 5000px+
    this.canvas.height = scrollArea.scrollHeight; // ← Bisa 3000px+

    // Canvas stays at 0,0 (doesn't move with scroll)
    this.canvas.style.left = '0px';
    this.canvas.style.top = '0px';

    // Render bars
    this._renderBars();
  }

  _renderBars() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Get cell positions from TanStackGridManager
    const cellRects = this.tableManager.getCellBoundingRects();

    // Draw each bar
    this.barData.forEach(bar => {
      const { rowIndex, startCol, endCol, progress, type } = bar;

      // Calculate bar position based on cell rectangles
      const startCell = cellRects.find(c => c.rowIndex === rowIndex && c.colIndex === startCol);
      const endCell = cellRects.find(c => c.rowIndex === rowIndex && c.colIndex === endCol);

      if (startCell && endCell) {
        const x = startCell.x;
        const y = startCell.y + 10;
        const width = endCell.x + endCell.width - x;
        const height = 20;

        // Draw bar rectangle
        this.ctx.fillStyle = type === 'planned' ? '#0dcaf0' : '#ffc107';
        this.ctx.fillRect(x, y, width, height);

        // Draw progress fill
        if (progress > 0) {
          this.ctx.fillStyle = type === 'planned' ? '#084298' : '#997404';
          this.ctx.fillRect(x, y, width * (progress / 100), height);
        }
      }
    });
  }
}
```

**Critical Rendering Details:**
1. Canvas **position: absolute** dengan **left: 0, top: 0**
2. Canvas **ukuran penuh** = `scrollWidth × scrollHeight`
3. Bars di-render menggunakan **absolute coordinates** dari cell rectangles
4. Canvas **tidak bergerak** saat scroll (tetap di left: 0)
5. **Bar positions** di-kalkulasi ulang saat scroll untuk match dengan cell positions

---

## 🏗️ DOM STRUCTURE & HIERARCHY

### Actual DOM Tree (Inspected)

```html
<body data-page="jadwal_pekerjaan">
  <div class="page-container">
    <div class="grid-container">

      <!-- SPLIT PANEL WRAPPER -->
      <div class="split-panel-wrapper">

        <!-- LEFT PANEL (FROZEN COLUMN) -->
        <div class="left-panel-wrapper" style="z-index: 20;">
          <div class="left-panel-scroll">
            <table class="left-table">
              <thead>...</thead>
              <tbody>
                <!-- Klasifikasi, Sub-Klasifikasi, Pekerjaan -->
              </tbody>
            </table>
          </div>
        </div>

        <!-- RIGHT PANEL (SCROLLABLE) -->
        <div class="right-panel-wrapper" style="z-index: 1; position: relative;">
          <div class="horizontal-scroll-wrapper">...</div>

          <div class="right-panel-scroll" style="position: relative;">

            <!-- TANSTACK GRID BODY (CANVAS PARENT) -->
            <div class="tanstack-grid-body" style="position: relative; overflow: auto;">

              <!-- VIRTUAL CONTAINER -->
              <div class="tanstack-grid-virtual-container" style="height: 2480px;">
                <!-- Virtual rows rendered here -->
              </div>

              <!-- CANVAS OVERLAY - THE PROBLEM CHILD! -->
              <canvas
                class="gantt-canvas-overlay"
                width="5024"
                height="2480"
                style="position: absolute; top: 0px; left: 0px; z-index: 1; pointer-events: auto;">
              </canvas>

            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</body>
```

**Key Observations:**
1. Canvas is **INSIDE** `.tanstack-grid-body` (right panel)
2. Canvas size (5024×2480) >> viewport size (≈1400×600)
3. Canvas positioned absolutely at `left: 0`, meaning it starts at the **left edge of `.tanstack-grid-body`**
4. When scrolling horizontally, `.tanstack-grid-body` scrolls but canvas stays at `left: 0`
5. **Canvas visually extends to the left** and overlays `.left-panel-wrapper`

### Stacking Context Hierarchy

```
body (root stacking context)
  ├─ .split-panel-wrapper (isolation: isolate) [NEW]
  │   ├─ .left-panel-wrapper (z-index: 20, position: relative)
  │   │   └─ Left table content
  │   │
  │   └─ .right-panel-wrapper (z-index: 1, position: relative)
  │       └─ .right-panel-scroll (position: relative)
  │           └─ .tanstack-grid-body (position: relative)
  │               └─ canvas (z-index: 1, position: absolute) ← PROBLEM!
```

**Expected Behavior:**
- `.left-panel-wrapper` (z-index: 20) should be **above** canvas (z-index: 1)

**Actual Behavior:**
- Canvas still overlays left panel despite lower z-index

---

## 🎨 CSS LAYOUT & POSITIONING

### Split Panel Layout

**File:** `static/detail_project/css/kelola_tahapan_grid.css`

```css
/* Container */
.split-panel-wrapper {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
  isolation: isolate; /* [NEW] Create stacking context */
}

/* Left Panel (Frozen) */
.left-panel-wrapper {
  flex: 0 0 clamp(360px, 45%, 620px);
  border-right: 2px solid var(--grid-frozen-border);
  background: var(--grid-frozen-bg);
  position: relative;
  z-index: 20; /* [CHANGED from 10 to 20] */
}

/* Right Panel (Scrollable) */
.right-panel-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-width: 0;
  z-index: 1; /* [NEW] */
}

.right-panel-scroll {
  overflow: auto;
  height: 100%;
  position: relative; /* [NEW] */
}

.tanstack-grid-body {
  position: relative;
  overflow: auto;
  max-height: min(70vh, 760px);
}
```

### Z-Index Ladder (Current)

```
z-index: 20 → .left-panel-wrapper (Frozen Column)
z-index: 1  → .right-panel-wrapper (Scrollable Container)
z-index: 1  → canvas.gantt-canvas-overlay (Barchart)
```

**Problem:** Even with higher z-index on `.left-panel-wrapper`, canvas visually appears on top when scrolling.

### Why Z-Index Doesn't Work?

**Hypothesis:**
1. **Stacking Context Issue:** Canvas is in a **different stacking context** (inside `.right-panel-wrapper`)
2. **Absolute Positioning:** Canvas with `position: absolute` can "escape" visual boundaries dalam certain rendering contexts
3. **Overflow Behavior:** `overflow: hidden` on parent doesn't clip absolutely positioned children di semua browser rendering scenarios
4. **Painting Order:** Browser paint order mungkin render canvas **after** left panel karena DOM order

---

## 🎨 CANVAS RENDERING MECHANISM

### How Bars Are Drawn

```javascript
// GanttCanvasOverlay._renderBars()
this.barData.forEach(bar => {
  // bar = { rowIndex, startCol, endCol, progress, type }

  // 1. Get cell rectangles from TanStackGridManager
  const cellRects = this.tableManager.getCellBoundingRects();

  // 2. Find start and end cell positions
  const startCell = cellRects.find(c =>
    c.rowIndex === bar.rowIndex && c.colIndex === bar.startCol
  );
  const endCell = cellRects.find(c =>
    c.rowIndex === bar.rowIndex && c.colIndex === bar.endCol
  );

  // 3. Calculate bar geometry
  const x = startCell.x;  // Absolute X position (could be negative after scroll!)
  const y = startCell.y + 10;
  const width = endCell.x + endCell.width - x;
  const height = 20;

  // 4. Draw on canvas
  this.ctx.fillStyle = bar.type === 'planned' ? '#0dcaf0' : '#ffc107';
  this.ctx.fillRect(x, y, width, height);
});
```

### Cell Rectangle Calculation

**File:** `static/detail_project/js/src/modules/grid/tanstack-grid-manager.js`

```javascript
getCellBoundingRects() {
  const rects = [];
  const bodyRect = this.bodyScroll.getBoundingClientRect();

  // Iterate all visible rows
  const rows = this.bodyInner.querySelectorAll('.tanstack-grid-virtual-row');
  rows.forEach((row, rowIdx) => {
    const cells = row.querySelectorAll('.tanstack-grid-cell');

    cells.forEach((cell, colIdx) => {
      const cellRect = cell.getBoundingClientRect();

      // Convert to coordinates relative to bodyScroll
      rects.push({
        rowIndex: rowIdx,
        colIndex: colIdx,
        x: cellRect.left - bodyRect.left + this.bodyScroll.scrollLeft,
        y: cellRect.top - bodyRect.top + this.bodyScroll.scrollTop,
        width: cellRect.width,
        height: cellRect.height
      });
    });
  });

  return rects;
}
```

**Key Point:** Cell coordinates di-adjust berdasarkan `scrollLeft` dan `scrollTop`, sehingga bars **selalu aligned** dengan cells yang visible.

### Scroll Synchronization

```javascript
// In GanttCanvasOverlay constructor
const scrollTarget = this.tableManager?.bodyScroll;
if (scrollTarget) {
  scrollTarget.addEventListener('scroll', () => {
    if (this.visible) {
      this.syncWithTable(); // Re-render bars with new cell positions
    }
  }, { passive: true });
}
```

**Problem:** Saat scroll horizontal:
1. `.tanstack-grid-body` scrolls (content moves)
2. Canvas stays at `left: 0` (doesn't move)
3. Bars re-rendered di posisi baru (aligned with scrolled cells)
4. **Bar yang di-render di koordinat X < 0 (sebelah kiri) muncul di area left panel!**

---

## 🔍 ROOT CAUSE ANALYSIS

### Primary Root Cause

**Canvas dengan `position: absolute` dan ukuran `scrollWidth×scrollHeight` dapat "overflow" secara visual keluar dari container boundaries-nya karena:**

1. **Canvas Size > Viewport:** Canvas berukuran full scroll area (5000px+), jauh lebih besar dari visible viewport
2. **Positioned at left: 0:** Canvas dimulai dari edge kiri `.tanstack-grid-body`
3. **Browser Rendering:** Absolutely positioned elements dapat "escape" visual clipping dalam scroll containers
4. **Bar Coordinates:** Bars di-render menggunakan absolute coordinates yang bisa negative (X < 0) setelah scroll

### Visual Example

```
Before Horizontal Scroll:
┌──────────────┬─────────────────────────────────────┐
│ Left Panel   │ Right Panel (Canvas)                │
│ (Frozen)     │ ┌─────────────────────────────────┐ │
│ Z-index: 20  │ │ Canvas (left: 0, width: 5000px) │ │
│              │ │ Bar renders at X=100, X=200...   │ │
└──────────────┴─┴─────────────────────────────────┴─┘
                  ↑ Canvas edge aligned with panel edge

After Horizontal Scroll Right (scrollLeft = 500px):
┌──────────────┬─────────────────────────────────────┐
│ Left Panel   │ Right Panel (scrolled 500px)        │
│ (Frozen)     │ ┌─────────────────────────────────┐ │
│ Z-index: 20  │ │ Canvas STILL at left: 0!         │ │
│              │ │ Bars now render at X=-400, X=-300│ │
│ ◄───────────────┤ (Negative X = left of panel!)  │ │
│ BARS OVERLAP!│ │                                  │ │
└──────────────┴─┴─────────────────────────────────┴─┘
   ↑ Canvas visually extends leftward, covering frozen column
```

### Secondary Contributing Factors

1. **Stacking Context Complexity:**
   - Multiple nested `position: relative` containers
   - `isolation: isolate` creates new stacking contexts
   - Z-index di-calculate per-stacking-context, tidak global

2. **Browser Rendering Quirks:**
   - Different browsers handle `overflow: hidden` + `position: absolute` differently
   - Paint ordering dapat berubah tergantung layout phase

3. **CSS Limitations:**
   - `overflow: hidden` tidak selalu clip absolutely positioned children
   - `clip-path` tidak apply ke inline-styled elements secara reliable
   - `contain: paint` breaks layout (force content ke 1 baris)

---

## 🔧 ATTEMPTED SOLUTIONS

### Solution 1: Z-Index Adjustment (FAILED)

**Changes Made:**
```css
.left-panel-wrapper {
  z-index: 20; /* Increased from 10 */
}
.right-panel-wrapper {
  z-index: 1; /* Added */
}
```

```javascript
// GanttCanvasOverlay.js
this.canvas.style.cssText = `
  z-index: 1; /* Changed from 10 */
`;
```

**Result:** ❌ Canvas STILL overlays left panel
**Reason:** Z-index tidak mengatasi physical overflow dari absolutely positioned canvas

### Solution 2: CSS Isolation + Clip Path (FAILED)

**Changes Made:**
```css
.split-panel-wrapper {
  isolation: isolate;
}
.right-panel-wrapper {
  clip-path: inset(0 0 0 0);
}
.gantt-timeline-panel-container {
  clip-path: inset(0 0 0 0);
}
```

**Result:** ❌ No effect
**Reason:** Canvas di-attach via JavaScript setelah CSS apply, clip-path tidak affect inline-styled elements

### Solution 3: CSS Containment (CATASTROPHIC FAILURE)

**Changes Made:**
```css
.right-panel-wrapper {
  contain: layout paint;
}
.tanstack-grid-body {
  contain: paint;
}
```

**Result:** 💥 **Layout RUSAK PARAH**
- Gantt chart diperkecil ke 1 baris pertama
- Content forced fit dalam minimal space
- Scrolling completely broken

**Reason:** `contain: layout` mengubah cara browser calculate layout, causing collapse

### Solution 4: JavaScript Parent Overflow Enforcement (LATEST, PENDING TEST)

**Changes Made:**
```javascript
// GanttCanvasOverlay.show()
show() {
  const scrollArea = this.tableManager?.bodyScroll;
  scrollArea.style.position = 'relative';
  scrollArea.style.overflow = 'auto';

  // CRITICAL FIX: Force parent to clip
  scrollArea.parentElement.style.overflow = 'hidden';
  scrollArea.parentElement.style.position = 'relative';

  scrollArea.appendChild(this.canvas);
}
```

**Status:** ⏳ **Deployed, awaiting user confirmation**
**Hypothesis:** By forcing `overflow: hidden` on `.right-panel-scroll` via JavaScript at runtime, browser should clip canvas

---

## ⚠️ TECHNICAL CONSTRAINTS

### 1. Canvas Must Be Position: Absolute

**Why?**
- Canvas needs to overlay grid cells without disrupting layout
- Bars must align pixel-perfect with cell boundaries
- Canvas size must cover entire scrollable area for smooth rendering

**Cannot Change To:**
- `position: relative` → Would push grid content down
- `position: fixed` → Would break scroll synchronization
- `position: sticky` → Not suitable for overlay behavior

### 2. Canvas Size Must Equal ScrollWidth

**Why?**
- Bars span across multiple columns (could be 50+ columns)
- If canvas smaller than scroll area, bars get cut off
- Rendering performance: redraw entire visible area vs. clip regions

**Implication:**
- Canvas always larger than viewport
- Physical overflow is **inherent to the design**

### 3. Browser Rendering Limitations

**Webkit/Blink (Chrome, Edge):**
- Aggressive paint optimization
- May not clip absolutely positioned children in scroll containers

**Firefox:**
- Different stacking context behavior
- `overflow: hidden` more strictly enforced

**Safari:**
- Unique rendering quirks with transforms and positioning

### 4. Cannot Change DOM Structure

**Constraint:**
- Canvas must be child of `.tanstack-grid-body` for scroll event access
- Moving canvas higher in DOM breaks `getBoundingClientRect()` calculations
- TanStackGrid expects specific DOM structure for virtualization

---

## 💡 RECOMMENDATIONS

### Option A: JavaScript-Based Clip Region (PREFERRED)

**Approach:** Modify canvas rendering to only draw within visible viewport boundaries

```javascript
// GanttCanvasOverlay._renderBars()
_renderBars() {
  const scrollArea = this.tableManager.bodyScroll;
  const viewportLeft = scrollArea.scrollLeft;
  const viewportRight = viewportLeft + scrollArea.clientWidth;
  const viewportTop = scrollArea.scrollTop;
  const viewportBottom = viewportTop + scrollArea.clientHeight;

  // Clear only visible region
  this.ctx.clearRect(viewportLeft, viewportTop, scrollArea.clientWidth, scrollArea.clientHeight);

  // Draw only bars within viewport
  this.barData.forEach(bar => {
    const { x, y, width, height } = this._calculateBarGeometry(bar);

    // Skip bars completely outside viewport
    if (x + width < viewportLeft || x > viewportRight) return;
    if (y + height < viewportTop || y > viewportBottom) return;

    // Clip bar to viewport boundaries
    const clippedX = Math.max(x, viewportLeft);
    const clippedWidth = Math.min(x + width, viewportRight) - clippedX;

    // Draw clipped bar
    this.ctx.fillRect(clippedX, y, clippedWidth, height);
  });
}
```

**Pros:**
- ✅ Guaranteed to work (software clipping)
- ✅ No CSS hacks needed
- ✅ Works across all browsers
- ✅ Maintains existing architecture

**Cons:**
- ⚠️ Requires modifying `GanttCanvasOverlay.js`
- ⚠️ Slight performance overhead for clip calculations

### Option B: CSS Mask/Clip on Parent

**Approach:** Use CSS mask or overflow:clip on right-panel-wrapper

```css
.right-panel-wrapper {
  overflow: clip; /* Modern CSS, not widely supported */
  /* OR */
  -webkit-mask-image: linear-gradient(to right, black, black);
  mask-image: linear-gradient(to right, black, black);
}
```

**Pros:**
- ✅ Pure CSS solution
- ✅ No JavaScript changes

**Cons:**
- ❌ `overflow: clip` not supported in older browsers
- ❌ CSS masks have performance implications
- ❌ May break other styling

### Option C: Canvas Transform Strategy

**Approach:** Move canvas with scroll using CSS transform

```javascript
scrollArea.addEventListener('scroll', () => {
  const scrollLeft = scrollArea.scrollLeft;

  // Move canvas to keep bars in viewport
  this.canvas.style.transform = `translateX(${-scrollLeft}px)`;

  // Render bars at shifted coordinates
  this._renderBars(scrollLeft);
});
```

**Pros:**
- ✅ Hardware accelerated (GPU)
- ✅ Smooth scrolling performance

**Cons:**
- ⚠️ Complex coordinate math
- ⚠️ May cause rendering artifacts
- ⚠️ Requires extensive testing

### Option D: Switch to SVG Instead of Canvas

**Approach:** Replace canvas with SVG elements for bars

```javascript
// Instead of canvas
this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
this.svg.style.cssText = `
  position: absolute;
  top: 0;
  left: 0;
  overflow: visible;
`;

// Bars as <rect> elements
bars.forEach(bar => {
  const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  rect.setAttribute('x', bar.x);
  rect.setAttribute('y', bar.y);
  rect.setAttribute('width', bar.width);
  rect.setAttribute('height', bar.height);
  rect.setAttribute('fill', bar.color);
  this.svg.appendChild(rect);
});
```

**Pros:**
- ✅ SVG respects CSS clipping better
- ✅ DOM-based (easier debugging)
- ✅ Better accessibility

**Cons:**
- ❌ Major refactoring required
- ❌ Performance worse for large datasets (100+ bars)
- ❌ Breaks existing architecture

---

## 🎯 FINAL RECOMMENDATION

**IMPLEMENT OPTION A: JavaScript-Based Clip Region**

### Implementation Plan

1. **Modify GanttCanvasOverlay._renderBars():**
   - Add viewport boundary calculations
   - Implement bar clipping logic
   - Test with various scroll positions

2. **Add Configuration:**
   ```javascript
   this.clipToViewport = true; // Enable clipping
   this.clipPadding = 0; // Extra pixels to render outside viewport
   ```

3. **Performance Optimization:**
   - Only re-render on scroll if visible bars changed
   - Use requestAnimationFrame for smooth updates
   - Cache bar geometries

4. **Testing:**
   - Test on Chrome, Firefox, Safari
   - Test with 100+ bars
   - Test rapid scrolling
   - Test zoom levels

### Estimated Effort

- **Development:** 2-3 hours
- **Testing:** 1-2 hours
- **Total:** ~4-5 hours

### Success Criteria

- ✅ Bars never appear in left panel area
- ✅ Smooth scroll performance (60fps)
- ✅ Works in all major browsers
- ✅ No layout breaks
- ✅ Existing functionality preserved

---

## 📝 CONCLUSION

Masalah barchart overflow adalah **architectural issue** yang tidak bisa diselesaikan dengan pure CSS karena:

1. Canvas positioning strategy (absolute + full scrollWidth)
2. Browser rendering limitations dengan absolutely positioned elements
3. Scroll synchronization requirements

**Solusi terbaik** adalah **software clipping** di JavaScript level, dimana kita secara eksplisit hanya render bars yang visible dan clip bars yang melampaui viewport boundaries.

Solusi ini:
- ✅ Reliable across browsers
- ✅ Maintainable
- ✅ Performant
- ✅ Doesn't break existing functionality

---

**End of Report**

---

## 📚 APPENDIX

### File Reference Table

| Component | File Path | Lines |
|-----------|-----------|-------|
| Canvas Overlay | `static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js` | 1-960 |
| Unified Manager | `static/detail_project/js/src/modules/unified/UnifiedTableManager.js` | 68-75 |
| TanStack Grid | `static/detail_project/js/src/modules/grid/tanstack-grid-manager.js` | 34, 72 |
| Main App | `static/detail_project/js/src/jadwal_kegiatan_app.js` | 27-150 |
| Grid CSS | `static/detail_project/css/kelola_tahapan_grid.css` | 143-183, 1421-1428 |
| Gantt CSS | `static/detail_project/css/gantt-chart-redesign.css` | 38-109 |
| HTML Template | `templates/detail_project/kelola_tahapan_grid_modern.html` | 1-500 |

### Version Info

- **Vite Build:** v5.4.21
- **TanStack Table Core:** (version from package.json)
- **Django:** (version from requirements.txt)
- **Analysis Date:** 2025-12-10

### Change Log

| Date | Change | Result |
|------|--------|--------|
| 2025-12-10 | Changed canvas z-index from 10 to 1 | ❌ No effect |
| 2025-12-10 | Added z-index: 20 to left-panel-wrapper | ❌ No effect |
| 2025-12-10 | Added isolation: isolate to containers | ❌ No effect |
| 2025-12-10 | Added clip-path to timeline containers | ❌ No effect |
| 2025-12-10 | Added contain: layout paint | 💥 Broke layout |
| 2025-12-10 | Reverted contain: layout paint | ✅ Layout restored |
| 2025-12-10 | Added JS overflow enforcement in show() | ⏳ Pending test |
