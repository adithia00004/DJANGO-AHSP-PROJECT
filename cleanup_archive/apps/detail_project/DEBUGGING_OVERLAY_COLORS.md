# Debugging Overlay Colors - Quick Guide
**Date:** 2025-12-10
**Status:** Hardcoded colors + console logs added

---

## 🔍 **What I Fixed**

### **Problem**
Warna Gantt dan Kurva-S overlay tidak terlihat berbeda (masih biru semua).

### **Root Cause**
Method `_getBtnColor()` tidak berhasil extract warna dari CSS button selector.

### **Solution**
Hardcode warna langsung ke constant values:
- **Planned**: `#0dcaf0` (Cyan - matches `.btn-outline-info`)
- **Actual**: `#ffc107` (Yellow - matches `.btn-outline-warning`)

---

## ✅ **Changes Made**

### **1. GanttCanvasOverlay.js**
```javascript
_resolveActualColor(variance) {
  // ALWAYS use yellow/warning color for actual bars
  return '#ffc107';
}

_getPlannedColor() {
  // ALWAYS use cyan/info color for planned bars
  return '#0dcaf0';
}
```

### **2. KurvaSCanvasOverlay.js**
```javascript
_getPlannedColor() {
  // ALWAYS use cyan/info color for planned curve
  return '#0dcaf0';
}

_getActualColor() {
  // ALWAYS use yellow/warning color for actual curve
  return '#ffc107';
}
```

### **3. Added Console Logs for Debugging**

**GanttCanvasOverlay.js:**
- `show()` → Logs when overlay is shown
- `_drawBars()` → Logs first bar rendered with color info

**KurvaSCanvasOverlay.js:**
- `show()` → Logs when overlay is shown

---

## 🧪 **How to Test**

### **Step 1: Open Browser Console**
1. Buka halaman Jadwal Pekerjaan
2. Buka DevTools (F12)
3. Buka tab "Console"

### **Step 2: Test Gantt Mode**
1. Klik tab "Gantt"
2. **Expected Console Logs:**
   ```
   [GanttOverlay] ✅ OVERLAY SHOWN - Cyan planned (#0dcaf0), Yellow actual (#ffc107)
   [GanttOverlay] First bar rendered: {
     pekerjaanId: "123",
     planned: { value: 50, width: 80, color: "#0dcaf0" },
     actual: { value: 75, width: 120, color: "#ffc107" },
     position: { x: 200, y: 100, height: 20 }
   }
   ```

3. **Visual Check:**
   - Lihat bars di atas cells
   - **Planned bar** (bottom): **Cyan/Biru muda** (#0dcaf0)
   - **Actual bar** (top): **Yellow/Kuning** (#ffc107)

### **Step 3: Test Kurva-S Mode**
1. Klik tab "Kurva-S"
2. **Expected Console Logs:**
   ```
   [KurvaSOverlay] ✅ OVERLAY SHOWN - Cyan planned (#0dcaf0), Yellow actual (#ffc107)
   [UnifiedTable] refreshKurvaSOverlay { plannedPoints: 52, actualPoints: 52 }
   [KurvaSOverlay] sync { cells: 520, plannedPoints: 52, actualPoints: 52, ... }
   [KurvaSOverlay] _drawCurve:Planned { points: 52 }
   [KurvaSOverlay] _drawCurve:Actual { points: 52 }
   ```

3. **Visual Check:**
   - Lihat S-curve lines di atas table
   - **Planned curve**: **Cyan/Biru muda** (#0dcaf0)
   - **Actual curve**: **Yellow/Kuning** (#ffc107)
   - **Y-axis labels**: 0%, 20%, ..., 100% di sisi kanan
   - **Legend**: Top-left corner dengan warna indicators

---

## 🚨 **Troubleshooting**

### **Issue 1: Console log tidak muncul**

**Possible Cause:**
- Unified overlay tidak aktif
- Legacy Gantt V2 masih digunakan

**Check:**
```javascript
// Di browser console
console.log('useUnifiedTable:', kelolaTahapanPageState.useUnifiedTable);
console.log('keepLegacyGantt:', kelolaTahapanPageState.keepLegacyGantt);
```

**Expected:**
```
useUnifiedTable: true
keepLegacyGantt: false
```

**If keepLegacyGantt is true:**
- Legacy Gantt V2 aktif
- Unified overlay TIDAK digunakan
- Perlu set `config.enableLegacyGantt = false` saat init

---

### **Issue 2: Console log "[GanttOverlay] ✅ OVERLAY SHOWN" muncul tapi tidak ada bars**

**Possible Cause:**
- Tidak ada data di StateManager
- Bar data building gagal

**Check:**
```javascript
// Di browser console
window.DEBUG_UNIFIED_TABLE = true;
// Klik tab Gantt lagi
```

**Expected Logs:**
```
[UnifiedTable] buildBarData:start { rows: 100, cols: 52, plannedSize: 500, actualSize: 400, ... }
[UnifiedTable] buildBarData:done { bars: 450 }
[GanttOverlay] renderBars { bars: 450 }
[GanttOverlay] sync { cells: 520, bars: 450, deps: 0, ... }
[GanttOverlay] bars:drawn { drawn: 450, skipped: 0, total: 450 }
```

**If bars: 0:**
- StateManager tidak punya data
- Perlu edit beberapa cell di Grid mode dulu

---

### **Issue 3: Kurva-S overlay muncul tapi tidak ada curves**

**Possible Cause:**
- Cumulative progress calculation gagal
- Tidak ada time columns

**Check:**
```javascript
// Di browser console
window.DEBUG_UNIFIED_TABLE = true;
// Klik tab Kurva-S lagi
```

**Expected Logs:**
```
[UnifiedTable] buildCurveData:state { timeColumns: 52, plannedCells: 500, actualCells: 400 }
[UnifiedTable] refreshKurvaSOverlay { plannedPoints: 52, actualPoints: 52 }
[KurvaSOverlay] _drawCurve:Planned { points: 52 }
[KurvaSOverlay] _drawCurve:Actual { points: 52 }
```

**If plannedPoints: 0:**
- Time columns tidak terdeteksi
- Atau cell data kosong

---

### **Issue 4: Warna masih biru semua**

**This should NOT happen after this fix!**

**Double Check:**
1. Refresh browser dengan hard reload (Ctrl+Shift+R)
2. Clear cache
3. Check bundle hash berubah:
   ```
   OLD: jadwal-kegiatan-SIa_jVx5.js
   NEW: jadwal-kegiatan-CmjUaEPY.js ← Should be different!
   ```

**If still blue:**
- Check console logs untuk confirm `color: "#0dcaf0"` dan `color: "#ffc107"`
- Take screenshot dan share ke developer

---

## 🎯 **Expected Visual Results**

### **Gantt Mode:**
```
┌──────────────────────────────────────┐
│ Week-1      │ Week-2      │ Week-3   │
├──────────────────────────────────────┤
│ ▓▓▓▓▓▓▓▓    │ ▓▓▓▓▓▓▓▓    │          │ ← YELLOW (#ffc107) actual
│ ░░░░░░░░░░  │ ░░░░░░░░░░  │ ░░░░     │ ← CYAN (#0dcaf0) planned
└──────────────────────────────────────┘
```

### **Kurva-S Mode:**
```
┌────────────────────────────────────────┬──────┐
│ ┌─────────────┐                        │ 100% │
│ │ ─ Planned   │ (CYAN)    ●━━━●━━━●   │ 80%  │
│ │ ─ Actual    │ (YELLOW) ╱         ╲  │ 60%  │
│ └─────────────┘         ●           ● │ 40%  │
│                        ╱              │ 20%  │
│                       ●               │ 0%   │
└────────────────────────────────────────┴──────┘
  Legend                               Y-Axis
```

---

## 📝 **Quick Checklist**

Before reporting issue, check:

- [ ] Hard refresh browser (Ctrl+Shift+R)
- [ ] Console shows "[GanttOverlay] ✅ OVERLAY SHOWN"
- [ ] Console shows "[KurvaSOverlay] ✅ OVERLAY SHOWN"
- [ ] Console shows bars/curves rendered
- [ ] Check `useUnifiedTable: true`
- [ ] Check `keepLegacyGantt: false`
- [ ] Grid mode has data (edit some cells first)
- [ ] Bundle hash changed (new build loaded)

---

## 🔧 **Manual Color Override (Emergency)**

If colors still don't work, you can force override:

```javascript
// In browser console
const canvas = document.querySelector('.gantt-canvas-overlay');
if (canvas) {
  const ctx = canvas.getContext('2d');
  // Force redraw with correct colors
  // (this is just for testing, not permanent solution)
}
```

---

## ✅ **Build Info**

**Build Time:** 2025-12-10
**Build Hash:** `jadwal-kegiatan-CmjUaEPY.js`
**Changes:**
- Hardcoded colors in GanttCanvasOverlay.js
- Hardcoded colors in KurvaSCanvasOverlay.js
- Added console.log debugging
- Removed CSS color extraction (was failing)

**Status:** ✅ Ready for testing

---

**If you still see issues after following this guide, please share:**
1. Console logs screenshot
2. Visual screenshot of Gantt/Kurva-S
3. Value of `kelolaTahapanPageState.useUnifiedTable`
4. Value of `kelolaTahapanPageState.keepLegacyGantt`
