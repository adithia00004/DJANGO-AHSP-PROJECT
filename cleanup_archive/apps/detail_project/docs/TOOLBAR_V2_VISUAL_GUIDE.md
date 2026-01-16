# TOOLBAR V2 VISUAL GUIDE
**Rekap Kebutuhan - Phase 4 Redesign**

---

## 📐 Layout Comparison

### BEFORE (Old Toolbar)
```
┌────────────────────────────────────────────────────────────────────┐
│ [Export▼] [🔍 Search...] [Snapshot|Timeline]  TK:0(0)·BHN:0(0)... │
└────────────────────────────────────────────────────────────────────┘
```
**Issues:**
- ❌ Poor visual hierarchy - all elements same weight
- ❌ Stats hard to read (tiny text, middot separators)
- ❌ No refresh button
- ❌ Cluttered on mobile (everything in one line)

---

### AFTER (New Toolbar V2)

#### Desktop Layout (≥1200px)
```
┌──────────────────────────────────────────────────────────────────────┐
│  ┌─ Actions ─────────┐  ┌─ Search & View ───────────────────────┐   │
│  │ [📥 Export ▼]     │  │ 🔍 [Search.................... ✕]     │   │
│  │ [↻ Refresh]       │  │ [📷 Snapshot │ 📅 Timeline]          │   │
│  └───────────────────┘  └───────────────────────────────────────┘   │
│                                                                       │
│  ┌─ Statistics Cards ──────────────────────────────────────────────┐│
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐││
│  │ │ 👥       │ │ 📦       │ │ 🔧       │ │ ✨       │ │ 💰      │││
│  │ │ TK       │ │ BHN      │ │ ALT      │ │ LAIN     │ │ Total   │││
│  │ │ 12 (150) │ │ 45 (1.2K)│ │ 8 (567)  │ │ 3 (89)   │ │ Rp 15.5M│││
│  │ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘││
│  └──────────────────────────────────────────────────────────────────┘│
│  📊 68 baris · 2025-12-03 10:30                                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### Tablet Layout (768px - 991px)
```
┌─────────────────────────────────────────┐
│ [📥 Export ▼] [↻ Refresh]               │
│ 🔍 [Search................... ✕]        │
│ [📷 Snapshot │ 📅 Timeline]             │
│                                         │
│ ┌─ Stats [▼] ────────────────────────┐ │
│ │ [👥 TK: 12] [📦 BHN: 45]           │ │
│ │ [🔧 ALT: 8] [✨ LAIN: 3]           │ │
│ │ [💰 Total: Rp 15.5M]               │ │
│ └────────────────────────────────────┘ │
│ 📊 68 baris · 10:30                    │
└─────────────────────────────────────────┘
```

#### Mobile Layout (<768px)
```
┌──────────────────────┐
│ [📥▼] [↻] [≡ 68]     │
│ 🔍 [Search..... ✕]   │
│ [📷 Snap │ 📅 Time]   │
│                      │
│ Stats (collapsed)    │
│ Tap to expand...     │
│                      │
│ 📊 68 baris          │
└──────────────────────┘
```

**Improvements:**
- ✅ Clear visual grouping by function
- ✅ Card-based stats with icons and colors
- ✅ Progressive disclosure (mobile stats collapsible)
- ✅ Touch-friendly (44px minimum targets)
- ✅ Animations for feedback

---

## 🎨 Component Details

### 1. Actions Section
**Purpose:** Primary actions (export, refresh)

**Components:**
```
┌─────────────────────┐
│ [📥 Export ▼]       │ ← Export dropdown (unchanged)
│ [↻ Refresh]         │ ← NEW: Refresh button with spinner
└─────────────────────┘
```

**States:**
- Default: Outline buttons
- Hover: Slight lift + shadow
- Loading (Refresh): Spinning icon
- Focus: 2px primary outline

**Tooltips:**
- Export: "Export data"
- Refresh: "Refresh data (Ctrl+R)"

---

### 2. Search & View Section
**Purpose:** Search input and view mode toggle

**Components:**
```
┌──────────────────────────────────────┐
│ 🔍 [Search for items........... ✕]  │ ← Search with clear button
│ [📷 Snapshot │ 📅 Timeline]         │ ← View mode toggle
└──────────────────────────────────────┘
```

**Search States:**
- Empty: Clear button hidden
- Has text: Clear button visible
- Focused: Primary border + outline
- Typing: Debounced (300ms)

**View Toggle:**
- Active: Filled background
- Inactive: Outline only
- ARIA: `aria-pressed="true/false"`

---

### 3. Stats Cards
**Purpose:** Real-time statistics display

**Card Structure:**
```
┌─────────────┐
│ 👥          │ ← Color-coded icon in circle
│ TK          │ ← Category label (uppercase)
│ 12 (150.5)  │ ← Count (quantity)
└─────────────┘
```

**Category Colors:**

| Kategori | Icon | Color | Background |
|----------|------|-------|------------|
| TK | 👥 People | Blue #0d6efd | Light blue 15% |
| BHN | 📦 Box | Green #198754 | Light green 15% |
| ALT | 🔧 Tools | Yellow #ffc107 | Light yellow 15% |
| LAIN | ✨ Dots | Cyan #0dcaf0 | Light cyan 15% |
| Total | 💰 Coin | Purple #6f42c1 | Light purple 5% + border |

**Card States:**
- Default: Subtle shadow
- Hover: Lift effect (translateY -1px)
- Update: Pulse animation (600ms)

**Animations:**
```css
@keyframes statPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); box-shadow: glow; }
}
```

---

### 4. Meta Information
**Purpose:** Additional context (row count, timestamp)

**Display:**
```
📊 68 baris · 2025-12-03 10:30 · [🔍 Filter aktif: BHN,ALT]
```

**Components:**
- List icon + row count (always visible)
- Timestamp (hidden on mobile)
- Filter indicator (conditional)

---

## 📱 Responsive Behavior

### Breakpoint Strategy

| Screen | Width | Layout | Stats | Buttons |
|--------|-------|--------|-------|---------|
| Desktop | ≥1200px | 3-column flex | Expanded (5 cards) | Full text |
| Tablet L | 992-1199px | 3-column compact | Expanded (smaller cards) | Full text |
| Tablet P | 768-991px | Stacked | Collapsible (2-col grid) | Full text |
| Mobile | 576-767px | Stacked | Collapsible (2-col) | Icons only |
| Extra Small | <576px | Single column | Collapsible (1-col) | Icons + 44px touch |

### Progressive Disclosure

**Desktop:** Everything visible
```
[Actions] [Search] [Stats: TK BHN ALT LAIN Total]
```

**Tablet:** Stats collapsible with toggle
```
[Actions] [Search] [Stats ▼ 68]
  └─ (collapsed by default)
```

**Mobile:** Compact icons + collapsed stats
```
[📥▼][↻] [🔍 Search] [📷│📅]
[Stats ▼ 68] (tap to expand)
```

---

## ⌨️ Keyboard Shortcuts

### Global Shortcuts
| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+R` / `Cmd+R` | Refresh data | Anywhere |
| `Ctrl+F` / `Cmd+F` | Focus search | Anywhere |
| `Esc` | Clear search | Search focused |
| `Tab` | Navigate forward | Toolbar |
| `Shift+Tab` | Navigate backward | Toolbar |
| `Enter` / `Space` | Activate button | Button focused |

### Focus Order
```
1. Export button
2. Refresh button
3. Search input
4. Search clear button (if visible)
5. Snapshot button
6. Timeline button
7. Stats toggle (mobile/tablet)
```

---

## ♿ Accessibility Features

### ARIA Labels
```html
<!-- Toolbar -->
<div role="toolbar" aria-label="Toolbar Rekap Kebutuhan">

<!-- Sections -->
<div role="group" aria-label="Actions">
<div role="group" aria-label="Search and view">
<div role="group" aria-label="Statistics">

<!-- Buttons -->
<button aria-label="Export options" title="Export data">
<button aria-label="Refresh data" title="Refresh data (Ctrl+R)">
<button aria-label="Clear search" title="Clear search">

<!-- Toggle -->
<button aria-pressed="true">Snapshot</button>
<button aria-pressed="false">Timeline</button>

<!-- Collapse -->
<button aria-expanded="true" aria-controls="rk-stats-collapse">
```

### Screen Reader Announcements
```javascript
// Status region for live updates
<div id="rk-sr-announcement"
     role="status"
     aria-live="polite"
     class="visually-hidden">
</div>

// Announcements:
- "Switched to timeline view"
- "Statistics collapsed"
- "Statistics expanded"
- "Search cleared"
```

### Focus Indicators
```css
/* Visible focus on keyboard navigation */
.rk-toolbar-v2 button:focus-visible,
.rk-toolbar-v2 input:focus-visible {
  outline: 2px solid var(--dp-c-primary);
  outline-offset: 2px;
}
```

---

## 🎭 Animation Reference

### 1. Refresh Button Spinner
```css
#rk-btn-refresh.spinning .bi-arrow-clockwise {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```
**Duration:** Continuous until data loaded
**Trigger:** Button click

---

### 2. Stat Card Pulse
```css
.rk-stat-card--pulse {
  animation: statPulse 0.6s ease;
}

@keyframes statPulse {
  0%, 100% { transform: scale(1); }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 12px rgba(111, 66, 193, 0.3);
  }
}
```
**Duration:** 600ms (single run)
**Trigger:** Value change detected by MutationObserver

---

### 3. Dropdown Slide-In
```css
.dropdown-menu {
  animation: dropdownSlideIn 200ms ease;
}

@keyframes dropdownSlideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```
**Duration:** 200ms
**Trigger:** Dropdown open

---

### 4. Card Hover Lift
```css
.rk-stat-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}
```
**Duration:** 200ms
**Trigger:** Mouse hover

---

## 🧩 Component API

### Stats Update
**Method:** Update inner HTML of stat elements
```javascript
// Main app updates
document.getElementById('rk-count-TK').textContent = '12';
document.getElementById('rk-qty-TK').textContent = '(150.5)';
document.getElementById('rk-total-cost').textContent = 'Rp 15.500.000';

// Toolbar automatically:
// 1. Detects change via MutationObserver
// 2. Applies pulse animation
// 3. Updates summary badge
```

### Refresh Event
**Dispatch:** When refresh button clicked
```javascript
// Toolbar dispatches
document.dispatchEvent(new CustomEvent('rk:refresh'));

// Main app listens
document.addEventListener('rk:refresh', () => {
  loadRekapKebutuhan();
});

// Main app dispatches when done
document.dispatchEvent(new CustomEvent('rk:dataLoaded'));
```

### Collapse State
**Storage:** `sessionStorage.getItem('rk-stats-collapsed')`
```javascript
// Save state
sessionStorage.setItem('rk-stats-collapsed', 'true');

// Restore on page load
const isCollapsed = sessionStorage.getItem('rk-stats-collapsed') === 'true';
```

---

## 🎨 CSS Custom Properties

### Colors
```css
--dp-c-primary: #0d6efd;
--dp-c-success: #198754;
--dp-c-warning: #ffc107;
--dp-c-info: #0dcaf0;
--dp-c-purple: #6f42c1;

--dp-c-surface: #ffffff;
--dp-c-bg: #f8f9fa;
--dp-c-text: #212529;
--dp-c-text-muted: #6c757d;
--dp-c-border: rgba(0,0,0,0.125);
```

### Spacing
```css
--dp-spacing-sm: 0.5rem;
--dp-spacing-md: 1rem;
--dp-spacing-lg: 1.5rem;
```

### Shadows
```css
--dp-shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
--dp-shadow-md: 0 4px 6px rgba(0,0,0,0.08);
--dp-shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
```

### Border Radius
```css
--dp-radius-sm: 0.25rem;
--dp-radius-md: 0.5rem;
--dp-radius-lg: 0.75rem;
```

---

## 📚 Usage Examples

### Example 1: Basic Implementation
```html
<!-- Just include the new toolbar HTML -->
<div class="rk-toolbar-v2">
  <!-- 3 sections here -->
</div>

<!-- Include toolbar.js -->
<script src="rekap_kebutuhan_toolbar.js" defer></script>
```

### Example 2: Listening for Events
```javascript
// Listen for refresh
document.addEventListener('rk:refresh', async () => {
  await loadData();
  document.dispatchEvent(new CustomEvent('rk:dataLoaded'));
});

// Listen for toolbar ready
document.addEventListener('rk:toolbarReady', (e) => {
  console.log('Toolbar version:', e.detail.version);
});
```

### Example 3: Programmatic Refresh
```javascript
// Trigger refresh from code
document.getElementById('rk-btn-refresh').click();

// Or dispatch event directly
document.dispatchEvent(new CustomEvent('rk:refresh'));
```

---

## 🔍 Debugging

### CSS Classes for Debugging
```css
/* Add borders to see sections */
.rk-toolbar-section {
  border: 1px dashed red !important;
}

/* Highlight stat cards */
.rk-stat-card {
  background: yellow !important;
}
```

### Console Logging
```javascript
// Toolbar logs
[rk-toolbar] Toolbar V2 enhancements loaded
[rk-toolbar] Stats summary updated: 68

// Check event listeners
getEventListeners(document).find(e => e.type === 'rk:refresh')
```

### Browser DevTools
```javascript
// Check collapse state
sessionStorage.getItem('rk-stats-collapsed')

// Check toolbar version
document.dispatchEvent(new CustomEvent('rk:toolbarReady'))
```

---

**Version:** 2.0
**Last Updated:** 2025-12-03
**Status:** ✅ Production Ready
