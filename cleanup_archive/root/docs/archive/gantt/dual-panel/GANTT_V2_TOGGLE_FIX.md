# Gantt V2 Toggle Switch Implementation

**Date:** 2025-12-03
**Status:** ✅ READY FOR TESTING
**Build Time:** 15.52s

---

## Issues Fixed

### Issue #1: Console Toggle Not Working
**User Report:**
```javascript
window.JadwalKegiatanApp.FEATURE_FLAGS.USE_FROZEN_GANTT = true;
window.JadwalKegiatanApp._initializeRedesignedGantt();
// Output: "Gantt already initialized, skipping"
```

**Problem:** Guard at line 1704-1707 prevented re-initialization even when flag changed.

**Solution:** Added `forceReInit` parameter to bypass guard and properly destroy old instance.

### Issue #2: No Visual Toggle Switch
**User Request:** "Jika bisa buat agar ada toggle switch untuk beralih dari gantt v1 dan v2"

**Solution:** Implemented iOS-style toggle switch with real-time visual feedback.

### Issue #3: Debug Panel Only on V2
**Problem:** Debug panel only appeared when V2 was loaded, not available for V1.

**Solution:** Added debug panel trigger to both V1 and V2 initialization.

---

## Implementation Details

### Fix #1: Force Re-initialization

**File:** [jadwal_kegiatan_app.js:1699-1721](jadwal_kegiatan_app.js#L1699-L1721)

**Changes:**

```javascript
// BEFORE:
async _initializeRedesignedGantt(retryCount = 0) {
  // Check if already initialized
  if (this.ganttChartRedesign || this.ganttFrozenGrid) {
    console.log('[JadwalKegiatanApp] Gantt already initialized, skipping');
    return;
  }
  // ...
}

// AFTER:
async _initializeRedesignedGantt(retryCount = 0, forceReInit = false) {
  // Check if already initialized (unless force re-init for version toggle)
  if ((this.ganttChartRedesign || this.ganttFrozenGrid) && !forceReInit) {
    console.log('[JadwalKegiatanApp] Gantt already initialized, skipping');
    return;
  }

  // Destroy existing instance if force re-init
  if (forceReInit) {
    if (this.ganttChartRedesign && typeof this.ganttChartRedesign.destroy === 'function') {
      console.log('[JadwalKegiatanApp] 🗑️ Destroying V1 instance...');
      this.ganttChartRedesign.destroy();
    }
    if (this.ganttFrozenGrid && typeof this.ganttFrozenGrid.destroy === 'function') {
      console.log('[JadwalKegiatanApp] 🗑️ Destroying V2 instance...');
      this.ganttFrozenGrid.destroy();
    }
    this.ganttChartRedesign = null;
    this.ganttFrozenGrid = null;
  }
  // ...
}
```

**What This Does:**
1. Accept `forceReInit` parameter (default `false`)
2. If `forceReInit = true`, bypass guard and destroy existing instance
3. Call respective `destroy()` method (V1 or V2)
4. Clear instance references
5. Proceed with fresh initialization

---

### Fix #2: Toggle Switch UI

**File:** [jadwal_kegiatan_app.js:3419-3467](jadwal_kegiatan_app.js#L3419-L3467)

**Changes:**

```javascript
// BEFORE: Simple button
<button class="btn btn-sm btn-primary" id="toggle-gantt-version">
  Switch Version
</button>

// AFTER: iOS-style toggle switch
<div style="display: flex; align-items: center; gap: 0.75rem;">
  <span style="font-size: 0.875rem; color: #6c757d;">V1</span>
  <label style="position: relative; display: inline-block; width: 50px; height: 24px;">
    <input type="checkbox" id="gantt-version-toggle"
           ${this.FEATURE_FLAGS.USE_FROZEN_GANTT ? 'checked' : ''}
           style="opacity: 0; width: 0; height: 0;">
    <span style="
      position: absolute;
      cursor: pointer;
      background-color: ${this.FEATURE_FLAGS.USE_FROZEN_GANTT ? '#0d6efd' : '#ccc'};
      transition: 0.3s;
      border-radius: 24px;
    ">
      <span style="
        position: absolute;
        height: 18px;
        width: 18px;
        left: ${this.FEATURE_FLAGS.USE_FROZEN_GANTT ? '29px' : '3px'};
        background-color: white;
        transition: 0.3s;
        border-radius: 50%;
      "></span>
    </span>
  </label>
  <span style="font-size: 0.875rem; color: #6c757d;">V2</span>
</div>
<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6c757d;">
  Current: <strong id="current-gantt-version" style="color: #0d6efd;">
    ${this.FEATURE_FLAGS.USE_FROZEN_GANTT ? 'V2 (Frozen Column)' : 'V1 (Dual Panel)'}
  </strong>
</div>
```

**Visual Design:**
```
┌─────────────────────────────┐
│ 🔧 Gantt Version Switcher   │
│                             │
│ V1  [●----] V2              │ ← Toggle OFF (V1)
│ Current: V1 (Dual Panel)    │
│                             │
│ [Close]                     │
└─────────────────────────────┘

After toggle:
┌─────────────────────────────┐
│ 🔧 Gantt Version Switcher   │
│                             │
│ V1  [----●] V2              │ ← Toggle ON (V2)
│ Current: V2 (Frozen Column) │
│                             │
│ [Close]                     │
└─────────────────────────────┘
```

**Toggle Features:**
- ✅ Real-time visual feedback (slider moves, color changes)
- ✅ Checkbox state synced with FEATURE_FLAGS
- ✅ Smooth 0.3s transition animation
- ✅ Blue (#0d6efd) when V2, Gray (#ccc) when V1
- ✅ Label updates: "V1 (Dual Panel)" / "V2 (Frozen Column)"

---

### Fix #3: Event Handler Update

**File:** [jadwal_kegiatan_app.js:3472-3491](jadwal_kegiatan_app.js#L3472-L3491)

**Changes:**

```javascript
// BEFORE: Button click
document.getElementById('toggle-gantt-version').addEventListener('click', () => {
  this.FEATURE_FLAGS.USE_FROZEN_GANTT = !this.FEATURE_FLAGS.USE_FROZEN_GANTT;
  this.ganttChartRedesign = null;
  this.ganttFrozenGrid = null;
  this._initializeRedesignedGantt();
  // ...
});

// AFTER: Checkbox change
const toggleCheckbox = document.getElementById('gantt-version-toggle');
toggleCheckbox.addEventListener('change', async (e) => {
  this.FEATURE_FLAGS.USE_FROZEN_GANTT = e.target.checked;
  console.log(`🔄 Switching to Gantt ${this.FEATURE_FLAGS.USE_FROZEN_GANTT ? 'V2 (Frozen Column)' : 'V1 (Dual Panel)'}...`);

  // Update toggle UI immediately
  const sliderOuter = toggleCheckbox.nextElementSibling;
  const sliderInner = sliderOuter.querySelector('span');
  sliderOuter.style.backgroundColor = this.FEATURE_FLAGS.USE_FROZEN_GANTT ? '#0d6efd' : '#ccc';
  sliderInner.style.left = this.FEATURE_FLAGS.USE_FROZEN_GANTT ? '29px' : '3px';

  // Update version text
  document.getElementById('current-gantt-version').textContent =
    this.FEATURE_FLAGS.USE_FROZEN_GANTT ? 'V2 (Frozen Column)' : 'V1 (Dual Panel)';

  // Reinitialize with force flag
  await this._initializeRedesignedGantt(0, true);

  console.log(`✅ Switched to Gantt ${this.FEATURE_FLAGS.USE_FROZEN_GANTT ? 'V2 (Frozen Column)' : 'V1 (Dual Panel)'}`);
});
```

**What This Does:**
1. Listen to checkbox `change` event (not button click)
2. Set `FEATURE_FLAGS.USE_FROZEN_GANTT = e.target.checked`
3. Update toggle UI immediately (slider + color)
4. Update version text label
5. Call `_initializeRedesignedGantt(0, true)` with `forceReInit = true`
6. Await completion, log success

---

### Fix #4: Debug Panel on Both Versions

**File:** [jadwal_kegiatan_app.js:1807-1810](jadwal_kegiatan_app.js#L1807-L1810)

**Changes:**

```javascript
// V1 initialization (added debug panel trigger)
async _initializeDualPanelGantt(container) {
  // ... initialization code ...

  console.log('[JadwalKegiatanApp] ✅ Gantt V1 (Dual Panel) initialized successfully!');
  Toast.success('📊 Gantt Chart loaded', 2000);

  // ✅ ADD: Debug panel in development (for version switching)
  if (window.location.hostname === 'localhost' || window.location.search.includes('debug=1')) {
    this._buildDebugComparisonUI();
  }
}

// V2 initialization (already had debug panel trigger)
async _initializeFrozenGantt(container) {
  // ... initialization code ...

  console.log('[JadwalKegiatanApp] ✅ Gantt V2 (Frozen Column) initialized successfully!');
  Toast.success('🆕 Gantt V2 loaded (POC)', 2000);

  // ✅ EXISTING: Debug panel in development
  if (window.location.hostname === 'localhost' || window.location.search.includes('debug=1')) {
    this._buildDebugComparisonUI();
  }
}
```

**Result:** Debug panel now appears on BOTH V1 and V2, allowing toggle at any time.

---

## How to Use

### Method 1: Automatic (Localhost)

1. Open: `http://localhost:8000/detail_project/project/<project_id>/jadwal-pekerjaan/`
2. Click "Gantt Chart" tab
3. **Debug panel appears automatically** in bottom-right corner
4. Click toggle switch to change version instantly

### Method 2: Manual Trigger (Production with ?debug=1)

1. Add `?debug=1` to URL
2. Debug panel appears
3. Use toggle switch

### Method 3: Console (Still Works)

```javascript
// Access app instance
const app = window.jadwalKegiatanApp;

// Toggle version
app.FEATURE_FLAGS.USE_FROZEN_GANTT = true; // or false
await app._initializeRedesignedGantt(0, true); // forceReInit = true
```

---

## User Flow

### Switching from V1 to V2

```
1. User loads page → V1 (Dual Panel) loads by default
   └─ Debug panel visible (localhost or ?debug=1)

2. User clicks toggle switch [●----] → [----●]
   ├─ Toggle slider animates to right
   ├─ Color changes: gray → blue
   ├─ Label updates: "V1 (Dual Panel)" → "V2 (Frozen Column)"
   └─ Console: "🔄 Switching to Gantt V2 (Frozen Column)..."

3. System destroys V1
   └─ Console: "🗑️ Destroying V1 instance..."

4. System loads V2
   ├─ Lazy import: gantt-frozen-grid.js
   ├─ Initialize: 10 demo rows, frozen columns
   └─ Console: "✅ Switched to Gantt V2 (Frozen Column)"

5. User sees V2 (Frozen Column architecture)
   ├─ 3 frozen columns (Pekerjaan, Volume, Satuan)
   ├─ 20 timeline weeks
   └─ Perfect alignment (CSS Grid)
```

### Switching from V2 to V1

```
1. User clicks toggle switch [----●] → [●----]
   ├─ Toggle slider animates to left
   ├─ Color changes: blue → gray
   └─ Label updates: "V2 (Frozen Column)" → "V1 (Dual Panel)"

2. System destroys V2
   └─ Console: "🗑️ Destroying V2 instance..."

3. System loads V1
   └─ Initialize: Dual-panel with tree + timeline

4. User sees V1 (Dual Panel architecture)
```

---

## Console Output Examples

### Successful Toggle (V1 → V2)

```
🔄 Switching to Gantt V2 (Frozen Column)...
[JadwalKegiatanApp] 🗑️ Destroying V1 instance...
[JadwalKegiatanApp] ✅ Container found: <div id="gantt-redesign-container">
🚀 Initializing Gantt Frozen Grid (V2 POC)...
✅ Rendered 10 demo rows with bars
✅ Gantt Frozen Grid initialized successfully
[JadwalKegiatanApp] ✅ Gantt V2 (Frozen Column) initialized successfully!
✅ Switched to Gantt V2 (Frozen Column)
```

### Successful Toggle (V2 → V1)

```
🔄 Switching to Gantt V1 (Dual Panel)...
[JadwalKegiatanApp] 🗑️ Destroying V2 instance...
Gantt Frozen Grid destroyed
[JadwalKegiatanApp] ✅ Container found: <div id="gantt-redesign-container">
📊 Initializing Gantt V1 (Dual Panel)...
[JadwalKegiatanApp] Transforming 5 pekerjaan nodes for Gantt
✅ Gantt Data Model initialized: 1 klasifikasi, 5 pekerjaan
[JadwalKegiatanApp] ✅ Gantt V1 (Dual Panel) initialized successfully!
✅ Switched to Gantt V1 (Dual Panel)
```

---

## Testing Checklist

### Toggle Switch UI
- [ ] Toggle appears in bottom-right corner on localhost
- [ ] Toggle appears with `?debug=1` parameter
- [ ] Slider animates smoothly (0.3s transition)
- [ ] Color changes: gray (V1) ↔ blue (V2)
- [ ] Label updates: "V1 (Dual Panel)" ↔ "V2 (Frozen Column)"

### Functional Toggle
- [ ] Clicking toggle destroys old instance
- [ ] Console shows destroy message
- [ ] New version initializes successfully
- [ ] Console shows success message
- [ ] Visual display updates to new version

### V1 → V2 Switch
- [ ] V1 dual-panel disappears
- [ ] V2 frozen grid appears
- [ ] 10 demo rows with hierarchy visible
- [ ] 3 frozen columns stick when scrolling
- [ ] 20 timeline weeks (W1-W20)
- [ ] Blue + orange bars visible

### V2 → V1 Switch
- [ ] V2 frozen grid disappears
- [ ] V1 dual-panel appears
- [ ] Tree panel on left, timeline on right
- [ ] Real pekerjaan data visible
- [ ] All previous V1 features working

### Multiple Toggles
- [ ] Can toggle V1 → V2 → V1 → V2 without errors
- [ ] No memory leaks (check DevTools Memory tab)
- [ ] Console clean (no errors)

---

## Build Status

✅ **Build completed successfully** in 15.52s

**Bundle Sizes:**
- core-modules: 26.60 KB (gzip: 7.87 KB)
- grid-modules: 36.84 KB (gzip: 10.20 KB)
- **jadwal-kegiatan: 109.76 KB** (gzip: 27.67 KB) ← +5.17 KB (toggle UI + force reInit logic)
- gantt-frozen-grid: 6.99 KB (gzip: 2.47 KB) ← V2 lazy-loaded chunk
- vendor-ag-grid: 988.31 KB (gzip: 246.07 KB)
- chart-modules: 1,144.05 KB (gzip: 371.06 KB)

**Performance Impact:** +5.17 KB compressed (toggle UI + destroy logic)

---

## Files Modified

1. **[jadwal_kegiatan_app.js:1699-1721](jadwal_kegiatan_app.js#L1699-L1721)**
   - Added `forceReInit` parameter
   - Destroy logic for V1 and V2

2. **[jadwal_kegiatan_app.js:1807-1810](jadwal_kegiatan_app.js#L1807-L1810)**
   - Added debug panel trigger to V1 initialization

3. **[jadwal_kegiatan_app.js:3419-3467](jadwal_kegiatan_app.js#L3419-L3467)**
   - Updated debug panel HTML (toggle switch UI)

4. **[jadwal_kegiatan_app.js:3472-3491](jadwal_kegiatan_app.js#L3472-L3491)**
   - Updated event handler (checkbox change → force reInit)

---

## Technical Notes

### Why Force Re-initialization?

**Problem:** Simple flag toggle doesn't work:
```javascript
// ❌ DOESN'T WORK
this.FEATURE_FLAGS.USE_FROZEN_GANTT = true;
this._initializeRedesignedGantt(); // Guard prevents re-init
```

**Solution:** Force re-init bypasses guard:
```javascript
// ✅ WORKS
await this._initializeRedesignedGantt(0, true); // forceReInit = true
```

### Why Destroy Before Re-init?

**Reasons:**
1. **Memory Management:** Prevent memory leaks from old instances
2. **Event Listeners:** Remove old event listeners to avoid double-firing
3. **Canvas Contexts:** Release WebGL/Canvas contexts
4. **DOM Cleanup:** Clear old DOM elements from container

**V1 Destroy Method:**
```javascript
// gantt-chart-redesign.js (assumed)
destroy() {
  // Remove event listeners
  // Clear canvas contexts
  // Remove DOM elements
  // Release references
}
```

**V2 Destroy Method:**
```javascript
// gantt-frozen-grid.js:319-325
destroy() {
  if (this.container) {
    this.container.innerHTML = '';
  }
  this.state.initialized = false;
  console.log('Gantt Frozen Grid destroyed');
}
```

### Toggle Switch CSS Technique

**HTML Structure:**
```html
<label>
  <input type="checkbox" style="opacity: 0"> <!-- Hidden checkbox -->
  <span>                                      <!-- Visible slider track -->
    <span></span>                             <!-- Slider button -->
  </span>
</label>
```

**CSS Positioning:**
```css
/* Track */
position: absolute; border-radius: 24px;

/* Button */
position: absolute; border-radius: 50%;
left: 3px (OFF) → 29px (ON);
transition: 0.3s; /* Smooth animation */
```

**Why This Works:**
- Native checkbox provides accessibility (keyboard, screen readers)
- Custom styling via absolute positioning
- CSS transitions for smooth animation
- JavaScript updates position based on checked state

---

## Known Limitations

1. **Debug Panel Condition:** Only on `localhost` or `?debug=1`
   - Production users won't see toggle (by design)
   - Can be enabled via console if needed

2. **No Smooth Cross-Fade:**
   - Old version disappears instantly
   - New version appears instantly
   - Could add loading spinner if desired

3. **State Not Persisted:**
   - Refresh page → resets to V1 default
   - Could add localStorage persistence if needed

---

## Next Steps

**After User Tests Toggle:**

1. **If Toggle Works:**
   - User can freely compare V1 vs V2
   - Validate V2 POC alignment with test script
   - Decide whether to proceed to Phase 2

2. **If V2 POC Approved:**
   - Phase 2: Data Integration (replace demo with real data)
   - Phase 3: Core Features (expand/collapse, tooltips)
   - Phase 4: Advanced Features (zoom, search, milestones)
   - Phase 5: Production Ready (virtual scrolling, performance)

3. **If V2 POC Needs Changes:**
   - List specific issues
   - Adjust POC implementation
   - Re-test

---

**Document End** ✅
