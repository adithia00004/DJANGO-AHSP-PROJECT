# Gantt Chart Comprehensive Fixes - Batch 1

## Issues to Fix

1. ✅ "Undefined" names in tree panel
2. ✅ Tree hierarchy structure (match Rekap RAB)
3. ✅ Toggle dropdown not working
4. ✅ Bar visibility (planned vs actual)
5. ✅ Grid lines for week/month
6. ✅ Zoom only Week/Month
7. ✅ Fix non-functional features
8. ✅ Alignment issues

## Critical Finding

**Root Issue:** Data preparation sends ALL node types but only fills the name matching the node type.

Example:
```javascript
// For a klasifikasi node:
{
  klasifikasi_name: "Klasifikasi A",  // ✅ Filled
  sub_klasifikasi_name: "",           // ❌ Empty (should have parent info)
  pekerjaan_name: "",                 // ❌ Empty
  node_type: "klasifikasi"
}

// For a pekerjaan node:
{
  klasifikasi_name: "",               // ❌ Should be filled with parent
  sub_klasifikasi_name: "",           // ❌ Should be filled with parent
  pekerjaan_name: "Pekerjaan 1",      // ✅ Filled
  node_type: "pekerjaan"
}
```

**Result:** Data model can't build proper hierarchy!

## Solution Strategy

We should NOT send klasifikasi/sub-klasifikasi as separate data items. The GanttDataModel should build hierarchy from pekerjaan data only, inferring parents from the IDs and names.

### Option 1: Send Only Pekerjaan (RECOMMENDED)
- Filter `flatPekerjaan` to only include `type === 'pekerjaan'`
- Each pekerjaan has full parent chain info
- Data model builds klasifikasi/sub-klasifikasi from pekerjaan data

### Option 2: Fix Data Structure (Current Approach - NEEDS FIX)
- Keep sending all node types
- But ensure EVERY node has complete parent chain info
- More data redundancy, but explicit

I'll implement Option 1 as it's cleaner and matches Gantt Chart semantics (Gantt shows tasks, not categories).

