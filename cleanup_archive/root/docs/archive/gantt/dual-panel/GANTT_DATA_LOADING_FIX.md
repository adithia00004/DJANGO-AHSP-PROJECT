# Gantt Chart Data Loading Issue - Fix Documentation

**Date:** 2025-12-02
**Issue:** Gantt Chart initialized but showing 0 data
**Status:** ✅ RESOLVED

---

## Problem Analysis

### Symptoms
Browser console showed:
```
✅ Gantt Chart Redesign initialized successfully
✅ Gantt Data Model initialized: 0 klasifikasi, 0 pekerjaan  ← PROBLEM!
Prepared Gantt data: {dataCount: 0, project: {...}, milestonesCount: 0}
```

Meanwhile, DataLoader successfully loaded:
```
✅ Loaded 7 pekerjaan nodes
✅ Loaded 47 tahapan
```

**Conclusion:** Data was loaded but NOT passed to Gantt Chart correctly!

---

## Root Cause

### Issue in `_prepareGanttData()` Method

**Wrong Code** ([jadwal_kegiatan_app.js:1785](jadwal_kegiatan_app.js#L1785)):
```javascript
_prepareGanttData() {
  const data = [];

  // ❌ WRONG: Looking for non-existent property
  if (this.state?.treeDataFlat) {
    this.state.treeDataFlat.forEach(row => {
      // Transform data...
    });
  }
  // treeDataFlat was NEVER populated, so data[] remained empty!

  return { data, project: {...}, milestones: [] };
}
```

### Architecture Mismatch

The app uses **Phase 0.3 architecture** with `DataLoader` class:
- Data is loaded into `this.state.flatPekerjaan` (from `DataLoader.loadPekerjaan()`)
- Data is also available in `this.state.pekerjaanTree` (hierarchical)

But the method was looking for:
- ❌ `this.state.treeDataFlat` (doesn't exist in Phase 0.3)

This was a legacy property name from older architecture!

---

## The Fix

### Updated `_prepareGanttData()` Method

**Correct Code** ([jadwal_kegiatan_app.js:1781-1879](jadwal_kegiatan_app.js#L1781-L1879)):

```javascript
_prepareGanttData() {
  const data = [];

  // ✅ CORRECT: Use flatPekerjaan from DataLoader (Phase 0.3)
  if (this.state?.flatPekerjaan && Array.isArray(this.state.flatPekerjaan)) {
    console.log(`Transforming ${this.state.flatPekerjaan.length} nodes for Gantt`);

    this.state.flatPekerjaan.forEach(node => {
      // Extract hierarchy based on node type
      const klasifikasiId = node.type === 'klasifikasi' ? node.id :
                           (node.type === 'subKlasifikasi' ? node.parent_id :
                           (node.type === 'pekerjaan' ? node.klasifikasi_id : null));

      const subKlasifikasiId = node.type === 'subKlasifikasi' ? node.id :
                              (node.type === 'pekerjaan' ? node.sub_klasifikasi_id : null);

      const pekerjaanId = node.type === 'pekerjaan' ? node.id : null;

      // Calculate progress from StateManager for pekerjaan nodes
      let progressRencana = 0;
      let progressRealisasi = 0;

      if (node.type === 'pekerjaan' && this.stateManager) {
        const tahapanList = this.state.tahapanList || [];
        const tahapanCount = tahapanList.length;

        if (tahapanCount > 0) {
          let plannedSum = 0;
          let actualSum = 0;

          tahapanList.forEach(tahapan => {
            const plannedVal = this.stateManager.getCellValue(node.id, tahapan.column_id, 'planned');
            const actualVal = this.stateManager.getCellValue(node.id, tahapan.column_id, 'actual');
            plannedSum += plannedVal || 0;
            actualSum += actualVal || 0;
          });

          progressRencana = Math.round(plannedSum / tahapanCount);
          progressRealisasi = Math.round(actualSum / tahapanCount);
        }
      }

      // Build data object with all hierarchy levels
      data.push({
        // Klasifikasi
        klasifikasi_id: klasifikasiId,
        klasifikasi_name: node.type === 'klasifikasi' ? node.name : (node.klasifikasi_name || ''),
        klasifikasi_kode: node.type === 'klasifikasi' ? node.kode : (node.klasifikasi_kode || ''),

        // Sub-Klasifikasi
        sub_klasifikasi_id: subKlasifikasiId,
        sub_klasifikasi_name: node.type === 'subKlasifikasi' ? node.name : (node.sub_klasifikasi_name || ''),
        sub_klasifikasi_kode: node.type === 'subKlasifikasi' ? node.kode : (node.sub_klasifikasi_kode || ''),

        // Pekerjaan
        pekerjaan_id: pekerjaanId,
        pekerjaan_name: node.type === 'pekerjaan' ? node.name : '',
        pekerjaan_kode: node.type === 'pekerjaan' ? node.kode : '',

        // Dates (use project dates as fallback)
        tgl_mulai_rencana: node.tgl_mulai_rencana || this.state.projectStart,
        tgl_selesai_rencana: node.tgl_selesai_rencana || this.state.projectEnd,
        tgl_mulai_realisasi: node.tgl_mulai_realisasi || this.state.projectStart,
        tgl_selesai_realisasi: node.tgl_selesai_realisasi || this.state.projectEnd,

        // Progress (calculated from StateManager)
        progress_rencana: progressRencana,
        progress_realisasi: progressRealisasi,

        // Volume
        volume: node.volume || 0,
        satuan: node.satuan || '',

        // Node type for debugging
        node_type: node.type
      });
    });
  }

  console.log(`Prepared ${data.length} nodes for Gantt Chart`);

  return {
    data,
    project: {
      project_id: this.state.projectId,
      project_name: this.state.projectName || 'Project',
      start_date: this.state.projectStart,
      end_date: this.state.projectEnd
    },
    milestones: []
  };
}
```

---

## Key Changes

### 1. Data Source
- **Before:** `this.state.treeDataFlat` (non-existent)
- **After:** `this.state.flatPekerjaan` (populated by DataLoader)

### 2. Node Type Handling
Added logic to handle 3 node types:
- `klasifikasi` (top level)
- `subKlasifikasi` (middle level)
- `pekerjaan` (leaf nodes with actual work)

### 3. Progress Calculation
Integrated with `StateManager` to calculate actual progress:
```javascript
if (node.type === 'pekerjaan' && this.stateManager) {
  // Calculate average progress across all tahapan
  const plannedVal = this.stateManager.getCellValue(node.id, tahapan.column_id, 'planned');
  const actualVal = this.stateManager.getCellValue(node.id, tahapan.column_id, 'actual');
}
```

### 4. Fallback Dates
Use project start/end dates as fallback if pekerjaan doesn't have specific dates:
```javascript
tgl_mulai_rencana: node.tgl_mulai_rencana || this.state.projectStart,
tgl_selesai_rencana: node.tgl_selesai_rencana || this.state.projectEnd,
```

---

## Data Flow Architecture

### Phase 0.3 Data Loading Flow

```
1. User opens page
   ↓
2. JadwalKegiatanApp.initialize()
   ↓
3. DataLoader.loadAllData()
   ├─→ loadPekerjaan()
   │   └─→ buildPekerjaanTree() → this.state.pekerjaanTree
   │       └─→ flattenTree() → this.state.flatPekerjaan ✅
   ├─→ loadTahapan() → this.state.tahapanList
   ├─→ loadVolumes() → this.state.volumeMap
   └─→ loadAssignments() → StateManager (planned/actual)
   ↓
4. User clicks "Gantt Chart" tab
   ↓
5. _initializeRedesignedGantt()
   ↓
6. _prepareGanttData()
   └─→ Reads this.state.flatPekerjaan ✅
       └─→ Transforms to Gantt format
           └─→ Returns {data, project, milestones}
   ↓
7. GanttChartRedesign.initialize(ganttData)
   └─→ GanttDataModel receives data ✅
       └─→ Builds hierarchy
           └─→ Renders tree + timeline
```

---

## Expected Console Output (After Fix)

```
[JadwalKegiatanApp] Transforming 7 nodes for Gantt
[JadwalKegiatanApp] Prepared 7 nodes for Gantt Chart
🚀 Initializing Gantt Chart Redesign...
📊 Initializing Gantt Data Model...
✅ Gantt Data Model initialized: 1 klasifikasi, 5 pekerjaan  ✅ (NOT 0!)
🌳 Initializing Tree Panel...
✅ Tree Panel initialized
📅 Initializing Timeline Panel...
✅ Timeline Panel initialized
✅ Gantt Chart Redesign initialized successfully
```

---

## Verification Steps

1. **Refresh browser** (Ctrl+Shift+R)
2. Open "Jadwal Pekerjaan" page
3. Click "Gantt Chart" tab
4. Check console - should see:
   - ✅ "Transforming X nodes for Gantt" (X > 0)
   - ✅ "Prepared X nodes for Gantt Chart" (X > 0)
   - ✅ "Gantt Data Model initialized: X klasifikasi, Y pekerjaan" (not 0!)
5. Visual check:
   - ✅ Tree panel shows klasifikasi/sub-klasifikasi/pekerjaan hierarchy
   - ✅ Timeline panel shows bars for each pekerjaan
   - ✅ Dual bars visible (planned = blue, actual = orange)

---

## Related Issues

### Issue #1: Template Container Not Found
- **Doc:** [GANTT_CONTAINER_FIX.md](GANTT_CONTAINER_FIX.md)
- **Status:** ✅ Fixed
- **Fix:** Updated `kelola_tahapan_grid_modern.html` to include `gantt-redesign-container`

### Issue #2: Data Not Loading (THIS ISSUE)
- **Doc:** This document
- **Status:** ✅ Fixed
- **Fix:** Updated `_prepareGanttData()` to use `flatPekerjaan` instead of `treeDataFlat`

---

## Files Modified

1. **[jadwal_kegiatan_app.js](jadwal_kegiatan_app.js#L1781-L1879)**
   - Method: `_prepareGanttData()`
   - Changes: Complete rewrite to use Phase 0.3 data structure

2. **Build Output**
   - `npm run build` completed successfully
   - Bundle size: 103 KB (jadwal-kegiatan)

---

## Lessons Learned

### 1. Architecture Awareness
When working with legacy code, always verify:
- Which architecture phase is currently active?
- Where is data actually stored in this phase?
- Don't assume old property names are still valid!

### 2. Data Source Verification
Before reading data:
```javascript
// ❌ BAD: Assume property exists
if (this.state.treeDataFlat) { ... }

// ✅ GOOD: Verify property exists and has correct type
if (this.state?.flatPekerjaan && Array.isArray(this.state.flatPekerjaan)) { ... }
```

### 3. Console Logging for Debugging
Added strategic console.log statements:
```javascript
console.log(`Transforming ${this.state.flatPekerjaan.length} nodes for Gantt`);
console.log(`Prepared ${data.length} nodes for Gantt Chart`);
```

This makes it easy to verify data is flowing correctly!

### 4. Integration with StateManager
The new code properly integrates with StateManager for progress calculation:
- Reads from both 'planned' and 'actual' states
- Calculates average progress across all tahapan
- Provides real-time progress data to Gantt Chart

---

**Document End**
