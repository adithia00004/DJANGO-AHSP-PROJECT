# Debug Panel Troubleshooting Guide

**Date:** 2025-12-03
**Issue:** Debug panel tidak muncul meskipun sudah di dev mode

---

## Changes Made

### Enhanced Debug Panel Conditions

**File:** [jadwal_kegiatan_app.js:1807-1823](jadwal_kegiatan_app.js#L1807-L1823)

```javascript
// BEFORE (restrictive):
if (window.location.hostname === 'localhost' || window.location.search.includes('debug=1')) {
  this._buildDebugComparisonUI();
}

// AFTER (relaxed + logging):
console.log('[JadwalKegiatanApp] Checking debug panel conditions:', {
  hostname: window.location.hostname,
  hasDebugParam: window.location.search.includes('debug=1'),
  isDev: import.meta.env.DEV
});

if (window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.search.includes('debug=1') ||
    import.meta.env.DEV) {  // ✅ NEW: Always show in Vite dev mode
  console.log('[JadwalKegiatanApp] 🔧 Building debug panel...');
  this._buildDebugComparisonUI();
} else {
  console.log('[JadwalKegiatanApp] ⏭️ Debug panel skipped (not in dev mode)');
}
```

---

## Testing Steps

### Step 1: Hard Refresh Browser

**Chrome/Edge:**
```
Ctrl + Shift + R
```

atau

```
Ctrl + F5
```

**Why:** HMR might not have reloaded the module completely.

---

### Step 2: Check Console Log

After refresh, klik "Gantt Chart" tab dan cari log ini:

**Expected Console Output:**
```javascript
[JadwalKegiatanApp] Checking debug panel conditions: {
  hostname: "localhost",  // atau IP address
  hasDebugParam: false,   // atau true jika pakai ?debug=1
  isDev: true             // ✅ Important: Should be true in dev mode
}
[JadwalKegiatanApp] 🔧 Building debug panel...
🔧 Debug panel added - use button to switch between V1 and V2
```

**If You See This Instead:**
```javascript
[JadwalKegiatanApp] ⏭️ Debug panel skipped (not in dev mode)
```

Then `import.meta.env.DEV` is `false`, which means HMR didn't reload properly.

---

### Step 3: Alternative - Use Console to Force Show

If debug panel still tidak muncul, gunakan console untuk force trigger:

```javascript
// Get app instance
const app = window.jadwalKegiatanApp;

// Manually build debug panel
app._buildDebugComparisonUI();

// Should see message:
// 🔧 Debug panel added - use button to switch between V1 and V2
```

Debug panel sekarang muncul di bottom-right corner.

---

### Step 4: Toggle Version via Console (Fallback)

Jika debug panel masih tidak muncul sama sekali, gunakan console command langsung:

```javascript
// Get app instance
const app = window.jadwalKegiatanApp;

// Switch to V2
app.FEATURE_FLAGS.USE_FROZEN_GANTT = true;
await app._initializeRedesignedGantt(0, true);

// Switch back to V1
app.FEATURE_FLAGS.USE_FROZEN_GANTT = false;
await app._initializeRedesignedGantt(0, true);
```

---

## Common Issues & Solutions

### Issue 1: "hostname is not 'localhost'"

**Symptom:**
```javascript
{ hostname: "127.0.0.1", hasDebugParam: false, isDev: false }
// Debug panel skipped
```

**Solution:**
- ✅ Already fixed: Added `127.0.0.1` check
- ✅ Already fixed: Added `import.meta.env.DEV` check

---

### Issue 2: "isDev is false in dev mode"

**Symptom:**
```javascript
{ hostname: "localhost", hasDebugParam: false, isDev: false }
// But you're running npm run dev!
```

**Cause:** HMR didn't reload module

**Solution:**
1. Stop Vite dev server (Ctrl+C)
2. Restart: `npm run dev`
3. Hard refresh browser (Ctrl+Shift+R)

---

### Issue 3: "Debug panel exists but hidden"

**Check with DevTools:**
```javascript
// In browser console:
document.getElementById('gantt-debug-panel')
// Should return: <div id="gantt-debug-panel">...</div>
// If null: Panel not created
// If element: Panel exists but might be hidden
```

**If panel exists but hidden, force show:**
```javascript
const panel = document.getElementById('gantt-debug-panel');
panel.style.display = 'block';
panel.style.visibility = 'visible';
panel.style.opacity = '1';
```

---

## V2 Alignment Test (Only Works in V2)

**IMPORTANT:** The test function you ran checks for `.gantt-cell` class, which **ONLY EXISTS in V2 (Frozen Column)**.

### Current State (V1):
```javascript
document.querySelectorAll('.gantt-cell')
// Returns: NodeList(0) - empty!
// V1 uses different classes: .tree-node, .gantt-bar, etc.
```

### After Switching to V2:
```javascript
document.querySelectorAll('.gantt-cell')
// Returns: NodeList(230) - 10 rows × 23 cells each
// Now the test will work!
```

---

## Complete Testing Flow

### 1. Hard Refresh
```
Ctrl + Shift + R
```

### 2. Open Gantt Tab
Click "Gantt Chart" tab

### 3. Check Console for Debug Conditions
Look for:
```
[JadwalKegiatanApp] Checking debug panel conditions: {...}
[JadwalKegiatanApp] 🔧 Building debug panel...
```

### 4a. If Panel Appears (Success Path)
- Look for panel in bottom-right corner
- Toggle switch: V1 ⟷ V2
- Watch console logs during toggle

### 4b. If Panel Missing (Fallback Path)
```javascript
// Force build panel
window.jadwalKegiatanApp._buildDebugComparisonUI();

// Or directly toggle version
window.jadwalKegiatanApp.FEATURE_FLAGS.USE_FROZEN_GANTT = true;
await window.jadwalKegiatanApp._initializeRedesignedGantt(0, true);
```

### 5. Test V2 Alignment (After Toggling to V2)
```javascript
function testAlignment() {
  const cells = document.querySelectorAll('.gantt-cell');

  if (cells.length === 0) {
    console.error('❌ No .gantt-cell found! Are you in V2 mode?');
    return false;
  }

  const rows = [];
  let currentRow = [];

  cells.forEach((cell, i) => {
    currentRow.push(cell);
    if (currentRow.length === 23) { // 3 frozen + 20 timeline
      const tops = currentRow.map(c => c.getBoundingClientRect().top);
      const maxDiff = Math.max(...tops) - Math.min(...tops);
      rows.push({ row: rows.length + 1, maxDiff, aligned: maxDiff < 1 });
      currentRow = [];
    }
  });

  console.table(rows);
  return rows.every(r => r.aligned);
}

const result = testAlignment();
console.log(result ? '✅ PERFECT ALIGNMENT' : '❌ MISALIGNED');
```

---

## What to Report Back

Please copy-paste console output for:

**1. Debug Panel Conditions:**
```
[JadwalKegiatanApp] Checking debug panel conditions: { ... }
```

**2. Debug Panel Build Status:**
```
[JadwalKegiatanApp] 🔧 Building debug panel...
// OR
[JadwalKegiatanApp] ⏭️ Debug panel skipped (not in dev mode)
```

**3. Visual Check:**
- [ ] Debug panel visible di bottom-right?
- [ ] Toggle switch berfungsi?
- [ ] Version label updates saat toggle?

**4. V2 Toggle Test (via console if panel missing):**
```javascript
window.jadwalKegiatanApp.FEATURE_FLAGS.USE_FROZEN_GANTT = true;
await window.jadwalKegiatanApp._initializeRedesignedGantt(0, true);
```

Copy-paste console output setelah command di atas.

---

## Expected V2 Visual Features

After switching to V2, you should see:

### Layout
```
┌─────────────┬──────┬────────┬───────────────────────────┐
│ Pekerjaan   │ Vol  │ Satuan │ W1 W2 W3 W4 W5 ... W20    │
│ (FROZEN)    │(FRZ) │ (FRZ)  │ (SCROLLABLE →)            │
├─────────────┼──────┼────────┼───────────────────────────┤
│ 📁 Tanah    │ 100  │  m3    │ ████████                  │
│   📁 Galian │  60  │  m3    │ ██████                    │
│     📄 Biasa│  40  │  m3    │ ████                      │
└─────────────┴──────┴────────┴───────────────────────────┘
```

### Features to Validate
- [ ] 10 demo rows with hierarchy (📁 level 0, 1 and 📄 level 2)
- [ ] 3 frozen columns stay when scrolling horizontally
- [ ] 20 timeline week headers (W1-W20)
- [ ] Blue bars (planned, semi-transparent)
- [ ] Orange bars (actual, solid)
- [ ] Progress fill inside bars

---

**Document End** ✅
