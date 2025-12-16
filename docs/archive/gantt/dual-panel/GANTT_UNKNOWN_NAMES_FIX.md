# Gantt Chart "Unknown" Names Fix

**Date:** 2025-12-03
**Issue:** All klasifikasi, sub-klasifikasi, and pekerjaan names showing "Unknown"
**Status:** ✅ FIXED (Pending User Testing)

---

## Problem Description

### Symptoms

**Browser Console:**
```
📁 Node collapsed: undefined
📁 Node collapsed: undefined
📌 Node selected: undefined
```

**Visual:**
```
📁 Unknown Klasifikasi
  📁 Unknown Sub-Klasifikasi
    📄 Unknown Pekerjaan
    📄 Unknown Pekerjaan
```

All hierarchy levels displayed "Unknown" instead of actual names from database.

---

## Root Cause Analysis

### Investigation Trail

1. **Checked `_prepareGanttData()`** in [jadwal_kegiatan_app.js:1824-1853](jadwal_kegiatan_app.js#L1824-L1853)
   ```javascript
   data.push({
     klasifikasi_name: node.klasifikasi_name || 'Unknown Klasifikasi',  // ← Fallback triggered
     sub_klasifikasi_name: node.sub_klasifikasi_name || 'Unknown Sub-Klasifikasi',
     pekerjaan_name: node.name || 'Unknown Pekerjaan'  // ← Wrong property!
   });
   ```

2. **Traced to DataLoader** in [data-loader.js:145-220](data-loader.js#L145-L220)
   - Found `buildPekerjaanTree()` function
   - **CRITICAL FINDING:** Pekerjaan nodes DON'T have parent info properties!

### The Actual Bugs

#### Bug #1: Missing Parent Information

In `buildPekerjaanTree()` (lines 189-197), pekerjaan nodes created like this:

```javascript
// BEFORE FIX:
const pkjNode = {
  id: pkj.id || pkj.pekerjaan_id,
  type: 'pekerjaan',
  kode: pkj.snapshot_kode || pkj.kode || '',
  nama: pkj.snapshot_uraian || pkj.uraian || '',  // ← Only has own name
  volume: pkj.volume || 0,
  satuan: pkj.snapshot_satuan || pkj.satuan || '-',
  level: 2,
  budgeted_cost: Number.parseFloat(pkj.budgeted_cost ?? pkj.total_cost ?? 0) || 0
  // ❌ NO klasifikasi_name!
  // ❌ NO sub_klasifikasi_name!
};
```

**Result:** When `_prepareGanttData()` reads `node.klasifikasi_name` → **undefined** → "Unknown Klasifikasi"

#### Bug #2: Property Name Mismatch

DataLoader uses: `nama` (Indonesian)
_prepareGanttData expected: `name` (English)

```javascript
pekerjaan_name: node.name || 'Unknown Pekerjaan'
//                    ↑ undefined (should be node.nama)
```

---

## The Solution

### Fix #1: Enrich Pekerjaan Nodes with Parent Info

**File:** [data-loader.js:156-216](data-loader.js#L156-L216)

**Strategy:** Capture parent names at each hierarchy level and inject into pekerjaan nodes.

**Code Changes:**

```javascript
data.forEach(klas => {
  const klasNode = {
    id: `klas-${klas.id || klas.nama}`,
    type: 'klasifikasi',
    nama: klas.name || klas.nama || 'Klasifikasi',
    children: [],
    level: 0,
    expanded: true
  };

  // ✅ Store for enrichment
  const klasifikasiId = klas.id;
  const klasifikasiName = klas.name || klas.nama || 'Klasifikasi';
  const klasifikasiKode = klas.kode || '';

  if (klas.sub && Array.isArray(klas.sub)) {
    klas.sub.forEach(sub => {
      const subNode = {
        id: `sub-${sub.id || sub.nama}`,
        type: 'sub-klasifikasi',
        nama: sub.name || sub.nama || 'Sub-Klasifikasi',
        children: [],
        level: 1,
        expanded: true
      };

      // ✅ Store for enrichment
      const subKlasifikasiId = sub.id;
      const subKlasifikasiName = sub.name || sub.nama || 'Sub-Klasifikasi';
      const subKlasifikasiKode = sub.kode || '';

      if (sub.pekerjaan && Array.isArray(sub.pekerjaan)) {
        sub.pekerjaan.forEach(pkj => {
          const pkjNode = {
            id: pkj.id || pkj.pekerjaan_id,
            type: 'pekerjaan',
            kode: pkj.snapshot_kode || pkj.kode || '',
            nama: pkj.snapshot_uraian || pkj.uraian || '',
            volume: pkj.volume || 0,
            satuan: pkj.snapshot_satuan || pkj.satuan || '-',
            level: 2,
            budgeted_cost: Number.parseFloat(pkj.budgeted_cost ?? pkj.total_cost ?? 0) || 0,

            // ✅ ADD: Parent information for Gantt Chart
            klasifikasi_id: klasifikasiId,
            klasifikasi_name: klasifikasiName,
            klasifikasi_kode: klasifikasiKode,
            sub_klasifikasi_id: subKlasifikasiId,
            sub_klasifikasi_name: subKlasifikasiName,
            sub_klasifikasi_kode: subKlasifikasiKode
          };
          subNode.children.push(pkjNode);
        });
      }

      klasNode.children.push(subNode);
    });
  }

  tree.push(klasNode);
});
```

**What This Does:**
1. At klasifikasi level: Store `klasifikasiId`, `klasifikasiName`, `klasifikasiKode`
2. At sub-klasifikasi level: Store `subKlasifikasiId`, `subKlasifikasiName`, `subKlasifikasiKode`
3. **Inject all parent info into each pekerjaan node**
4. Now pekerjaan nodes are "self-sufficient" with complete hierarchy context

### Fix #2: Handle Property Name Mismatch

**File:** [jadwal_kegiatan_app.js:1837](jadwal_kegiatan_app.js#L1837)

**Change:**
```javascript
// BEFORE:
pekerjaan_name: node.name || 'Unknown Pekerjaan',

// AFTER:
pekerjaan_name: node.nama || node.name || 'Unknown Pekerjaan',
//               ↑ Check Indonesian property first
```

**Why:** DataLoader convention uses `nama`, so check that property first before falling back to `name`.

---

## Data Flow Architecture

### Before Fix

```
1. API Response
   ↓
2. buildPekerjaanTree()
   ├─ klasifikasi node: { nama: "Klasifikasi A" }
   ├─ sub-klasifikasi node: { nama: "Sub A1" }
   └─ pekerjaan node: {
        nama: "Pekerjaan 1"
        ❌ klasifikasi_name: MISSING
        ❌ sub_klasifikasi_name: MISSING
      }
   ↓
3. flattenTree() → this.state.flatPekerjaan
   ↓
4. _prepareGanttData()
   ├─ Reads node.klasifikasi_name → undefined
   └─ Falls back to "Unknown Klasifikasi"
   ↓
5. Gantt Data Model
   ↓
6. Tree Rendering: "Unknown Klasifikasi"
```

### After Fix

```
1. API Response
   ↓
2. buildPekerjaanTree()
   ├─ klasifikasi level:
   │  Store: klasifikasiName = "Klasifikasi A"
   │
   ├─ sub-klasifikasi level:
   │  Store: subKlasifikasiName = "Sub A1"
   │
   └─ pekerjaan node: {
        nama: "Pekerjaan 1"
        ✅ klasifikasi_name: "Klasifikasi A"
        ✅ klasifikasi_id: 1
        ✅ klasifikasi_kode: "A"
        ✅ sub_klasifikasi_name: "Sub A1"
        ✅ sub_klasifikasi_id: 10
        ✅ sub_klasifikasi_kode: "A.1"
      }
   ↓
3. flattenTree() → this.state.flatPekerjaan (with parent info!)
   ↓
4. _prepareGanttData()
   ├─ Reads node.klasifikasi_name → "Klasifikasi A" ✅
   ├─ Reads node.sub_klasifikasi_name → "Sub A1" ✅
   └─ Reads node.nama → "Pekerjaan 1" ✅
   ↓
5. Gantt Data Model (receives proper names)
   ↓
6. Tree Rendering: Actual names displayed!
```

---

## Expected Result

### Console Output

```
[JadwalKegiatanApp] Transforming 5 pekerjaan nodes for Gantt (filtered from 7 total nodes)
[JadwalKegiatanApp] Sample pekerjaan node: {
  id: 123,
  type: 'pekerjaan',
  nama: 'Galian Tanah Biasa',
  kode: 'A.1.1.001',
  klasifikasi_id: 1,
  klasifikasi_name: 'Pekerjaan Tanah',  // ✅ NOT "Unknown"
  klasifikasi_kode: 'A',
  sub_klasifikasi_id: 10,
  sub_klasifikasi_name: 'Galian Tanah',  // ✅ NOT "Unknown"
  sub_klasifikasi_kode: 'A.1',
  volume: 100,
  satuan: 'm3'
}
[JadwalKegiatanApp] Prepared 5 nodes for Gantt Chart
✅ Gantt Data Model initialized: 1 klasifikasi, 5 pekerjaan
```

### Visual Output

**Tree Panel:**
```
📁 Pekerjaan Tanah
  📁 Galian Tanah
    📄 Galian Tanah Biasa (100 m3)
    📄 Galian Tanah Keras (50 m3)
  📁 Urugan Tanah
    📄 Urugan Tanah Pilihan (80 m3)
```

**Timeline Panel:**
- Bars aligned with actual pekerjaan names
- No more "undefined" in hover tooltips
- Progress labels show actual task names

---

## Testing Instructions

1. **Clear Browser Cache:** Ctrl+Shift+R (hard refresh)
2. **Open Jadwal Pekerjaan page**
3. **Click "Gantt Chart" tab**
4. **Check Browser Console:**
   - Should see sample pekerjaan node with `klasifikasi_name` filled
   - Should NOT see "Unknown" in any names
   - Should see node count > 0

5. **Visual Verification:**
   - Tree panel shows actual klasifikasi names (not "Unknown")
   - Tree panel shows actual sub-klasifikasi names (not "Unknown")
   - Tree panel shows actual pekerjaan names (not "Unknown")
   - Node collapse/expand shows correct names in console

6. **Hover Test:**
   - Hover over bars in timeline
   - Tooltip should show actual names (not "Unknown")

---

## Build Status

✅ **Build completed successfully** in 15.97s

**Command:**
```bash
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT" && npm run build
```

**Bundle Sizes:**
- core-modules: 26.60 KB (gzip: 7.87 KB)
- grid-modules: 36.84 KB (gzip: 10.20 KB)
- jadwal-kegiatan: **103.80 KB** (gzip: 25.91 KB) ← Contains fix
- vendor-ag-grid: 988.31 KB (gzip: 246.07 KB)
- chart-modules: 1,144.05 KB (gzip: 371.06 KB)

---

## Files Modified

1. **[data-loader.js:156-216](data-loader.js#L156-L216)**
   - Function: `buildPekerjaanTree()`
   - Changes: Added parent info enrichment to pekerjaan nodes
   - Lines added: 6 new properties per pekerjaan node

2. **[jadwal_kegiatan_app.js:1837](jadwal_kegiatan_app.js#L1837)**
   - Function: `_prepareGanttData()`
   - Changes: Check `node.nama` before `node.name`
   - Impact: Handles Indonesian property naming convention

---

## Related Issues

This fix addresses **Issue #1** from user feedback list. Remaining issues:

- [ ] Fix header horizontal scroll (still frozen)
- [ ] Re-add search UI (currently removed)
- [ ] Perfect vertical alignment (left higher than right)
- [ ] Week/month segmentation sync with grid
- [ ] Bar positioning sync with grid progress

---

## Technical Lessons

### 1. Data Enrichment Pattern

When building hierarchical structures, **enrich child nodes with parent context** at creation time:

```javascript
// ✅ GOOD: Enrich during build
parent.children.forEach(child => {
  child.parentName = parent.name;
  child.parentId = parent.id;
});

// ❌ BAD: Expect to traverse up later
child.getParentName() // Requires tree traversal
```

### 2. Property Naming Consistency

Establish naming conventions early:
- Document which system uses `name` vs `nama`
- Create adapters if systems use different conventions
- Always check both properties when uncertain

### 3. Self-Sufficient Data

Make nodes "self-sufficient" for downstream consumers:
```javascript
// ✅ GOOD: Node has everything it needs
const node = {
  id: 1,
  name: 'Task 1',
  parentName: 'Parent',  // Pre-populated
  parentId: 10
};

// ❌ BAD: Node requires parent lookup
const node = {
  id: 1,
  name: 'Task 1',
  parentId: 10  // Must look up parent separately
};
```

---

**Next Step:** User to test and confirm "Unknown" names are now showing actual data.

**Document End**
