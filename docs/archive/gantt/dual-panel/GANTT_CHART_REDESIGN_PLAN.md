# 📊 Gantt Chart Comprehensive Redesign Plan

**Date**: 2025-12-02
**Status**: 🔄 **IN PROGRESS**
**Goal**: Create a professional, hierarchical Gantt chart with dual-bar (planned vs actual) visualization

---

## 🎯 Requirements Analysis

### **User Requirements:**
1. ✅ **Hierarchical display** - Klasifikasi → Sub-Klasifikasi → Pekerjaan
2. ✅ **Dual-bar visualization** - Rencana (blue) vs Realisasi (green)
3. ✅ **Period accuracy** - Match input data & project date range
4. ✅ **Milestone markers** - Add comments/notes on specific dates
5. ✅ **Data sync** - Real-time sync between input & visualization
6. ✅ **Performance** - Handle 500+ pekerjaan smoothly
7. ✅ **Maintainability** - Clean, modular code
8. ✅ **Memory efficient** - Minimal overhead

---

## 🎨 Proposed UI Design

### **Layout Structure:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  GANTT CHART TOOLBAR                                                │
│  [View: Week ▼] [Zoom: - 100% +] [Expand All] [Collapse All]      │
│  [Today] [← Previous] [Next →] [Add Milestone]                      │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────┬──────────────────────────────────────────────┐
│  TREE PANEL (30%)    │  TIMELINE PANEL (70%)                        │
├──────────────────────┼──────────────────────────────────────────────┤
│                      │  ┌─ Timeline Header ────────────────────┐   │
│  Search: [____]      │  │ Nov  │  Dec  │  Jan  │  Feb  │ Mar │   │
│                      │  │ W1 W2│ W3 W4 │ W1 W2 │ W3 W4 │ ... │   │
│  ▼ Klasifikasi A     │  └──────────────────────────────────────┘   │
│    ├─ ▼ Sub A.1      │  ┌─ Task Bars ──────────────────────────┐   │
│    │   ├─ Pekerjaan 1│  │ ▼ Klasifikasi A                      │   │
│    │   │   • 45%     │  │   ├─ ▼ Sub A.1                       │   │
│    │   └─ Pekerjaan 2│  │   │   ├─ Pekerjaan 1                 │   │
│    │       • 80%     │  │   │   │   ░░░░░[====]░░░░ Planned    │   │
│    └─ ► Sub A.2      │  │   │   │   ████[████]████ Actual      │   │
│        (collapsed)   │  │   │   └─ Pekerjaan 2                 │   │
│                      │  │   │       ░░░░░[========]░░ Planned   │   │
│  ► Klasifikasi B     │  │   │       ███[█████]███ Actual       │   │
│    (collapsed)       │  │   └─ ► Sub A.2 (collapsed)           │   │
│                      │  │ ► Klasifikasi B (collapsed)          │   │
│  Legend:             │  └──────────────────────────────────────┘   │
│  ░░░ Planned (Blue)  │                                              │
│  ███ Actual (Green)  │  ┌─ Milestones ─────────────────────────┐   │
│  ◆ Milestone         │  │ ◆ Phase 1 Complete (Jan 15)          │   │
│  ⚠ Critical delay    │  │ ◆ Inspection Due (Feb 20)             │   │
└──────────────────────┴──────────────────────────────────────────────┘
```

---

## 🏗️ Architecture Design

### **Component Structure:**

```
GanttChartApp (Main Controller)
├─ TreePanel (Left side - 30%)
│  ├─ SearchBar
│  ├─ HierarchicalTree
│  │  ├─ KlasifikasiNode (Level 1)
│  │  ├─ SubKlasifikasiNode (Level 2)
│  │  └─ PekerjaanNode (Level 3)
│  └─ Legend
│
├─ TimelinePanel (Right side - 70%)
│  ├─ TimelineHeader (Month/Week labels)
│  ├─ TaskBars (Dual-bar visualization)
│  │  ├─ PlannedBar (Blue, transparent)
│  │  └─ ActualBar (Green, solid)
│  └─ MilestoneMarkers (Diamond shapes)
│
├─ Toolbar (Actions & controls)
│  ├─ ViewModeSelector (Day/Week/Month)
│  ├─ ZoomControls
│  ├─ NavigationControls
│  └─ MilestoneManager
│
├─ DataManager (State & sync)
│  ├─ StateStore (Redux-like state)
│  ├─ DataTransformer (Tree → Gantt tasks)
│  └─ SyncManager (Bidirectional sync)
│
└─ RenderEngine (Performance layer)
   ├─ VirtualScroll (Render only visible rows)
   ├─ Canvas rendering (For bars - faster than DOM)
   └─ RAF scheduler (RequestAnimationFrame)
```

---

## 📐 Data Model

### **Hierarchical Structure:**

```typescript
interface GanttDataModel {
  klasifikasi: KlasifikasiNode[];
  milestones: Milestone[];
  projectMeta: ProjectMetadata;
}

interface KlasifikasiNode {
  id: string;
  kode: string;
  nama: string;
  level: 1;
  expanded: boolean;
  subKlasifikasi: SubKlasifikasiNode[];

  // Aggregated data
  totalPekerjaan: number;
  avgProgress: number;
  dateRange: { start: Date; end: Date };
}

interface SubKlasifikasiNode {
  id: string;
  kode: string;
  nama: string;
  level: 2;
  parentId: string;
  expanded: boolean;
  pekerjaan: PekerjaanNode[];

  // Aggregated data
  totalPekerjaan: number;
  avgProgress: number;
  dateRange: { start: Date; end: Date };
}

interface PekerjaanNode {
  id: string;
  kode: string;
  nama: string;
  level: 3;
  parentId: string;
  volume: number;
  satuan: string;

  // Timeline data
  planned: TaskBar;
  actual: TaskBar;

  // Progress
  plannedProgress: number; // 0-100
  actualProgress: number;   // 0-100

  // Status
  status: 'not-started' | 'in-progress' | 'complete' | 'delayed';
  criticality: 'low' | 'medium' | 'high' | 'critical';
}

interface TaskBar {
  start: Date;
  end: Date;
  duration: number; // in days
  progress: number; // 0-100
  color: string;
  style: 'solid' | 'transparent' | 'dashed';
}

interface Milestone {
  id: string;
  date: Date;
  title: string;
  description: string;
  icon: string;
  color: string;
  comments: Comment[];
  linkedPekerjaan: string[]; // Pekerjaan IDs
}

interface Comment {
  id: string;
  author: string;
  text: string;
  timestamp: Date;
}

interface ProjectMetadata {
  projectId: number;
  projectName: string;
  startDate: Date;
  endDate: Date;
  totalDuration: number;
  currentDate: Date;
}
```

---

## 🎨 Visual Design Specifications

### **Color Palette:**

```css
/* Planned (Blue theme) */
--color-planned-bar: rgba(13, 110, 252, 0.3);
--color-planned-progress: rgba(13, 110, 252, 0.6);
--color-planned-border: #0d6efd;

/* Actual (Green theme) */
--color-actual-bar: rgba(25, 135, 84, 0.3);
--color-actual-progress: rgba(25, 135, 84, 0.8);
--color-actual-border: #198754;

/* Status colors */
--color-on-track: #198754;
--color-delayed: #dc3545;
--color-critical: #8b0000;
--color-completed: #20c997;

/* Milestone */
--color-milestone: #fd7e14;
--color-milestone-critical: #dc3545;

/* Hierarchy levels */
--color-level-1: #212529;  /* Klasifikasi */
--color-level-2: #495057;  /* Sub */
--color-level-3: #6c757d;  /* Pekerjaan */

/* Background */
--color-weekend: rgba(0, 0, 0, 0.03);
--color-today: rgba(255, 193, 7, 0.1);
```

### **Bar Design:**

```
Dual-bar overlay design:

Planned bar (behind, transparent):
┌────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ ← Background (transparent blue)
│░░░░[████████████]░░░░░░░░░░░░░░░░│ ← Progress (solid blue)
└────────────────────────────────────┘

Actual bar (front, solid):
      ┌──────────────────────────┐
      │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ ← Background (light green)
      │[████████]▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ ← Progress (dark green)
      └──────────────────────────┘

Combined view:
┌────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░[████████████]░░░░░░░░░░░░░░░░│
│░░░░░░░░┌──────────────────────────┐
│░░░░░░░░│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
│░░░░[███│████]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
└────────└──────────────────────────┘
         ↑
         Overlap shows comparison
```

### **Milestone Design:**

```
◆ Normal milestone (orange)
◈ Critical milestone (red)
⬥ Completed milestone (green)

With popup on hover:
┌───────────────────────────┐
│ ◆ Phase 1 Complete        │
│ ─────────────────────────│
│ Date: Jan 15, 2025        │
│ Status: On track          │
│ ─────────────────────────│
│ Comments (2):             │
│ • John: All done! ✓       │
│ • Maria: Great work       │
│ ─────────────────────────│
│ [Add Comment] [Edit]      │
└───────────────────────────┘
```

---

## ⚙️ Technical Implementation

### **1. Hierarchical Tree Component**

**File**: `gantt-tree-panel.js`

```javascript
export class GanttTreePanel {
  constructor(container, data, options) {
    this.container = container;
    this.data = data; // Hierarchical structure
    this.options = options;
    this.expandedNodes = new Set();
    this.searchQuery = '';
  }

  render() {
    const tree = this._buildTreeHTML(this.data);
    this.container.innerHTML = `
      <div class="gantt-tree-panel">
        <div class="gantt-tree-search">
          <input type="text" placeholder="Search pekerjaan..."
                 class="form-control form-control-sm">
        </div>
        <div class="gantt-tree-toolbar">
          <button class="btn btn-sm" data-action="expand-all">
            Expand All
          </button>
          <button class="btn btn-sm" data-action="collapse-all">
            Collapse All
          </button>
        </div>
        <div class="gantt-tree-content">
          ${tree}
        </div>
        <div class="gantt-tree-legend">
          ${this._buildLegendHTML()}
        </div>
      </div>
    `;

    this._attachEventListeners();
  }

  _buildTreeHTML(nodes, level = 1) {
    return nodes.map(node => {
      const isExpanded = this.expandedNodes.has(node.id);
      const hasChildren = this._hasChildren(node);
      const indent = (level - 1) * 20;

      return `
        <div class="gantt-tree-node level-${level}"
             data-node-id="${node.id}"
             data-level="${level}">
          <div class="gantt-tree-node-content"
               style="padding-left: ${indent}px">
            ${hasChildren ? `
              <button class="gantt-tree-toggle"
                      data-node-id="${node.id}">
                <i class="bi bi-chevron-${isExpanded ? 'down' : 'right'}"></i>
              </button>
            ` : '<span class="gantt-tree-spacer"></span>'}

            <span class="gantt-tree-icon">
              ${this._getNodeIcon(node, level)}
            </span>

            <span class="gantt-tree-label">
              <span class="gantt-tree-kode">${node.kode}</span>
              <span class="gantt-tree-nama">${node.nama}</span>
            </span>

            ${level === 3 ? `
              <span class="gantt-tree-progress">
                <span class="progress-badge planned">${node.plannedProgress}%</span>
                <span class="progress-badge actual">${node.actualProgress}%</span>
              </span>
            ` : ''}
          </div>

          ${hasChildren && isExpanded ? `
            <div class="gantt-tree-children">
              ${this._buildTreeHTML(this._getChildren(node), level + 1)}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  toggle(nodeId) {
    if (this.expandedNodes.has(nodeId)) {
      this.expandedNodes.delete(nodeId);
    } else {
      this.expandedNodes.add(nodeId);
    }
    this.render();
    this._notifyChange('toggle', nodeId);
  }

  expandAll() {
    this.data.forEach(klas => {
      this.expandedNodes.add(klas.id);
      klas.subKlasifikasi.forEach(sub => {
        this.expandedNodes.add(sub.id);
      });
    });
    this.render();
  }

  collapseAll() {
    this.expandedNodes.clear();
    this.render();
  }

  search(query) {
    this.searchQuery = query.toLowerCase();
    // Highlight matching nodes
    this._highlightSearchResults();
  }
}
```

### **2. Dual-Bar Timeline Component**

**File**: `gantt-timeline-canvas.js`

```javascript
export class GanttTimelineCanvas {
  constructor(container, data, options) {
    this.container = container;
    this.data = data;
    this.options = options;

    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.pixelRatio = window.devicePixelRatio || 1;

    this._setupCanvas();
  }

  render() {
    this._clearCanvas();
    this._drawGrid();
    this._drawWeekends();
    this._drawToday();
    this._drawBars();
    this._drawMilestones();
  }

  _drawBars() {
    const visibleNodes = this._getVisibleNodes();

    visibleNodes.forEach((node, index) => {
      const y = index * this.options.rowHeight;

      if (node.level === 3) { // Pekerjaan only
        // Draw planned bar (behind, transparent)
        this._drawBar({
          x: this._dateToX(node.planned.start),
          y: y + 5,
          width: this._durationToWidth(node.planned.duration),
          height: this.options.barHeight,
          progress: node.plannedProgress,
          color: this.options.colors.planned,
          style: 'transparent'
        });

        // Draw actual bar (front, solid)
        this._drawBar({
          x: this._dateToX(node.actual.start),
          y: y + this.options.barHeight + 10,
          width: this._durationToWidth(node.actual.duration),
          height: this.options.barHeight,
          progress: node.actualProgress,
          color: this.options.colors.actual,
          style: 'solid'
        });

        // Draw comparison indicator
        this._drawComparisonIndicator(node, y);
      }
    });
  }

  _drawBar({ x, y, width, height, progress, color, style }) {
    const ctx = this.ctx;

    // Bar background
    ctx.fillStyle = style === 'transparent'
      ? `${color.bg}80` // Add alpha for transparency
      : color.bg;
    ctx.fillRect(x, y, width, height);

    // Progress fill
    const progressWidth = (width * progress) / 100;
    ctx.fillStyle = color.progress;
    ctx.fillRect(x, y, progressWidth, height);

    // Border
    ctx.strokeStyle = color.border;
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, width, height);

    // Progress text
    if (progress > 0 && width > 40) {
      ctx.fillStyle = '#fff';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(
        `${progress}%`,
        x + width / 2,
        y + height / 2 + 4
      );
    }
  }

  _drawComparisonIndicator(node, y) {
    // Draw warning if actual is behind planned
    const plannedEnd = node.planned.end.getTime();
    const actualEnd = node.actual.end.getTime();

    if (actualEnd > plannedEnd && node.actualProgress < 100) {
      const x = this._dateToX(node.planned.end);
      const y2 = y + this.options.rowHeight / 2;

      // Warning triangle
      this.ctx.fillStyle = '#ffc107';
      this.ctx.beginPath();
      this.ctx.moveTo(x, y2 - 5);
      this.ctx.lineTo(x + 5, y2 + 5);
      this.ctx.lineTo(x - 5, y2 + 5);
      this.ctx.closePath();
      this.ctx.fill();

      // Tooltip on hover
      this._addTooltip(x, y2, `Delayed by ${this._daysDiff(plannedEnd, actualEnd)} days`);
    }
  }
}
```

### **3. Milestone Manager**

**File**: `gantt-milestone-manager.js`

```javascript
export class MilestoneManager {
  constructor(ganttApp) {
    this.app = ganttApp;
    this.milestones = [];
  }

  add(milestone) {
    const id = `milestone-${Date.now()}`;
    const newMilestone = {
      id,
      date: new Date(milestone.date),
      title: milestone.title,
      description: milestone.description || '',
      icon: milestone.icon || '◆',
      color: milestone.color || '#fd7e14',
      comments: [],
      linkedPekerjaan: milestone.linkedPekerjaan || [],
      createdAt: new Date(),
      createdBy: milestone.createdBy || 'Unknown'
    };

    this.milestones.push(newMilestone);
    this._save();
    this.app.render();

    return newMilestone;
  }

  addComment(milestoneId, comment) {
    const milestone = this.milestones.find(m => m.id === milestoneId);
    if (!milestone) return;

    milestone.comments.push({
      id: `comment-${Date.now()}`,
      author: comment.author,
      text: comment.text,
      timestamp: new Date()
    });

    this._save();
    this.app.render();
  }

  showPopup(milestoneId, x, y) {
    const milestone = this.milestones.find(m => m.id === milestoneId);
    if (!milestone) return;

    const popup = document.createElement('div');
    popup.className = 'gantt-milestone-popup';
    popup.style.left = `${x}px`;
    popup.style.top = `${y}px`;
    popup.innerHTML = `
      <div class="milestone-popup-header">
        <span class="milestone-icon">${milestone.icon}</span>
        <h6>${milestone.title}</h6>
        <button class="btn-close" data-action="close"></button>
      </div>
      <div class="milestone-popup-body">
        <p><strong>Date:</strong> ${formatDate(milestone.date)}</p>
        <p><strong>Description:</strong> ${milestone.description}</p>
        ${milestone.linkedPekerjaan.length > 0 ? `
          <p><strong>Linked:</strong> ${milestone.linkedPekerjaan.length} pekerjaan</p>
        ` : ''}
        <hr>
        <h6>Comments (${milestone.comments.length})</h6>
        <div class="milestone-comments">
          ${this._renderComments(milestone.comments)}
        </div>
        <div class="milestone-add-comment">
          <textarea placeholder="Add a comment..." rows="2"></textarea>
          <button class="btn btn-sm btn-primary" data-action="add-comment">
            Post Comment
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(popup);
    this._attachPopupEvents(popup, milestoneId);
  }
}
```

---

## 🚀 Performance Optimizations

### **1. Virtual Scrolling**

```javascript
class VirtualScrollManager {
  constructor(container, totalItems, itemHeight) {
    this.container = container;
    this.totalItems = totalItems;
    this.itemHeight = itemHeight;
    this.visibleCount = Math.ceil(container.clientHeight / itemHeight) + 2; // Buffer
    this.scrollTop = 0;
  }

  getVisibleRange() {
    const start = Math.floor(this.scrollTop / this.itemHeight);
    const end = Math.min(start + this.visibleCount, this.totalItems);
    return { start, end };
  }

  onScroll(scrollTop) {
    this.scrollTop = scrollTop;
    const { start, end } = this.getVisibleRange();

    // Only render visible items
    this.renderVisibleItems(start, end);
  }
}
```

### **2. Canvas Rendering**

Use Canvas instead of DOM for bars → **10x faster for 500+ items**

### **3. RequestAnimationFrame Scheduler**

```javascript
class RAFScheduler {
  constructor() {
    this.pendingUpdates = new Set();
    this.rafId = null;
  }

  schedule(component, updateFn) {
    this.pendingUpdates.add({ component, updateFn });

    if (!this.rafId) {
      this.rafId = requestAnimationFrame(() => this.flush());
    }
  }

  flush() {
    this.pendingUpdates.forEach(({ component, updateFn }) => {
      updateFn.call(component);
    });

    this.pendingUpdates.clear();
    this.rafId = null;
  }
}
```

### **4. Data Memoization**

```javascript
class DataCache {
  constructor() {
    this.cache = new Map();
  }

  get(key, computeFn) {
    if (!this.cache.has(key)) {
      this.cache.set(key, computeFn());
    }
    return this.cache.get(key);
  }

  invalidate(key) {
    this.cache.delete(key);
  }

  clear() {
    this.cache.clear();
  }
}
```

---

## 📊 Data Synchronization Strategy

### **Bidirectional Sync:**

```
User Input (Grid) ↔ StateStore ↔ Gantt Visualization

1. User edits cell in grid
   ↓
2. StateManager updates central state
   ↓
3. Gantt chart listens to state change
   ↓
4. Gantt re-renders affected bars only (not full re-render)
   ↓
5. Both grid & Gantt show same data
```

**Implementation:**

```javascript
class SyncManager {
  constructor() {
    this.listeners = new Set();
  }

  subscribe(listener) {
    this.listeners.add(listener);
  }

  notify(change) {
    this.listeners.forEach(listener => {
      listener.onDataChange(change);
    });
  }

  handleGridChange(pekerjaanId, field, newValue) {
    // Update state
    StateStore.update(pekerjaanId, field, newValue);

    // Notify Gantt
    this.notify({
      type: 'pekerjaan-update',
      pekerjaanId,
      field,
      newValue
    });
  }
}

// In Gantt Chart:
class GanttChartApp {
  onDataChange(change) {
    if (change.type === 'pekerjaan-update') {
      // Only re-render affected bar, not entire chart
      this.updateBar(change.pekerjaanId);
    }
  }

  updateBar(pekerjaanId) {
    const node = this.findNode(pekerjaanId);
    const barBounds = this.getBarBounds(node);

    // Clear only that bar's area
    this.ctx.clearRect(
      barBounds.x,
      barBounds.y,
      barBounds.width,
      barBounds.height
    );

    // Redraw only that bar
    this._drawBar(node, barBounds);
  }
}
```

---

## 🧪 Testing Strategy

### **Unit Tests:**
- Tree expand/collapse
- Date calculations
- Progress aggregation
- Milestone CRUD

### **Integration Tests:**
- Grid ↔ Gantt sync
- Zoom & pan
- Filter & search

### **Performance Tests:**
- Render 500 pekerjaan: Target <2s
- Scroll smoothness: Target 60 FPS
- Memory usage: Target <100MB

---

## 📅 Implementation Timeline

### **Phase 1: Core Structure** (Day 1-2)
- [x] Design document (this file)
- [ ] Data model implementation
- [ ] Tree panel basic rendering
- [ ] Timeline canvas setup

### **Phase 2: Visualization** (Day 3-4)
- [ ] Dual-bar rendering
- [ ] Hierarchical tree with expand/collapse
- [ ] Timeline header (months/weeks)
- [ ] Responsive layout

### **Phase 3: Milestones** (Day 5)
- [ ] Milestone markers
- [ ] Popup with comments
- [ ] Add/edit/delete milestones

### **Phase 4: Sync & Performance** (Day 6-7)
- [ ] Grid ↔ Gantt synchronization
- [ ] Virtual scrolling
- [ ] Canvas optimization
- [ ] Memory profiling

### **Phase 5: Polish** (Day 8)
- [ ] Dark mode support
- [ ] Accessibility (keyboard nav)
- [ ] Print styles
- [ ] Documentation

---

## ✅ Success Criteria

- [ ] Clear 3-level hierarchy (Klasifikasi → Sub → Pekerjaan)
- [ ] Dual bars (Planned vs Actual) clearly distinguishable
- [ ] Period matches project date range accurately
- [ ] Milestones with comments functional
- [ ] Real-time sync between grid & Gantt
- [ ] Handles 500+ pekerjaan smoothly (60 FPS)
- [ ] Memory usage < 100MB
- [ ] Code is modular & maintainable

---

**Status**: 📝 Design complete, ready for implementation

**Next Step**: Review & approve design, then start Phase 1

---

**End of Design Document**
