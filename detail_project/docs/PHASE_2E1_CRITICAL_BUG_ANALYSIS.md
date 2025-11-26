# Phase 2E.1: Critical Bug Analysis - Shared State Issue

**Date**: 2025-11-26
**Severity**: 🔴 **CRITICAL**
**Status**: 🔍 **ROOT CAUSE IDENTIFIED**

---

## User-Reported Issue

**From Console Logs Analysis**:
```
data-loader.js:475 [DataLoader] Mode PLANNED: Reading planned_proportion=40 for pekerjaan=443, week=1
```

✅ Data loading works correctly (reads correct field)

**But**:
- ❌ Save di mode Perencanaan affect mode Realisasi
- ❌ Save di mode Realisasi affect mode Perencanaan
- ❌ Kedua tabs menampilkan data yang sama

---

## Root Cause: SHARED STATE

### Critical Discovery

**File**: `jadwal_kegiatan_app.js`
**Line**: 2162-2164

```javascript
_handleAgGridCellChange({...}) {
  // ...

  this.state.modifiedCells = this.state.modifiedCells || new Map();
  this.state.modifiedCells.set(cellKey, normalizedValue);  // ❌ SHARED!
  this.state.isDirty = true;
}
```

**Problem**: `modifiedCells` is a **SINGLE Map** shared between:
- Mode Perencanaan
- Mode Realisasi

### Why This Causes the Bug

**Scenario**:
1. User in mode **Perencanaan**: Input 40% → stored in `modifiedCells['443-week1'] = 40`
2. User switches to mode **Realisasi**: Grid reads from SAME `modifiedCells` → shows 40%!
3. User in mode **Realisasi**: Input 20% → OVERWRITES `modifiedCells['443-week1'] = 20`
4. User switches back to **Perencanaan**: Grid shows 20% (not 40%)!

**Result**: Both modes share the same in-memory state!

---

## Additional Shared State Issues

### 1. Assignment Map
```javascript
this.state.assignmentMap = new Map();  // SHARED between modes
```

### 2. Modified Cells
```javascript
this.state.modifiedCells = new Map();  // SHARED between modes
```

### 3. Cell Validation States
```javascript
this.state.cellValidations = new Map();  // SHARED between modes
```

---

## Impact Analysis

| State | Shared? | Impact |
|-------|---------|--------|
| `modifiedCells` | ✅ YES | User edits in one mode affect other mode |
| `assignmentMap` | ✅ YES | Saved data appears in both modes |
| `cellValidations` | ✅ YES | Validation errors shown incorrectly |
| `progressMode` | ❌ NO | Mode switching works |
| `pekerjaanTree` | ❌ NO | Pekerjaan list correct |

---

## Solution Design

### Option 1: Dual State Maps (Recommended)

**Structure**:
```javascript
this.state = {
  progressMode: 'planned',  // Current active mode

  // Separate state per mode
  plannedState: {
    modifiedCells: new Map(),
    assignmentMap: new Map(),
    cellValidations: new Map(),
    isDirty: false,
  },

  actualState: {
    modifiedCells: new Map(),
    assignmentMap: new Map(),
    cellValidations: new Map(),
    isDirty: false,
  },

  // Shared state (mode-independent)
  pekerjaanTree: [],
  tahapanList: [],
  volumeMap: new Map(),
  timeColumns: [],
}
```

**Access Pattern**:
```javascript
// Get current mode state
const currentState = this.state.progressMode === 'actual'
  ? this.state.actualState
  : this.state.plannedState;

// Set cell value
currentState.modifiedCells.set(cellKey, value);
```

**Pros**:
- ✅ Complete isolation between modes
- ✅ Each mode has its own dirty state
- ✅ Clear separation of concerns

**Cons**:
- Requires refactoring all state access
- More complex state management

### Option 2: Prefixed Keys (Quick Fix)

**Structure**:
```javascript
// Keep single Map, but prefix keys with mode
const cellKey = `${this.state.progressMode}-${pekerjaanId}-${week}`;
// Planned: "planned-443-week1"
// Actual: "actual-443-week1"
```

**Pros**:
- ✅ Minimal code changes
- ✅ Quick to implement

**Cons**:
- ❌ Still uses shared Map
- ❌ Harder to debug
- ❌ Mode switch complexity

---

## Recommendation

**Use Option 1** (Dual State Maps) because:
1. Proper architectural separation
2. Easier to maintain long-term
3. Better debugging experience
4. Supports future features (e.g., undo/redo per mode)

---

## Implementation Plan

### Phase 1: State Structure (1 hour)
1. Add `plannedState` and `actualState` to state initialization
2. Create helper methods:
   - `_getCurrentModeState()` → returns current state object
   - `_getModifiedCells()` → returns current mode's modifiedCells
   - `_getAssignmentMap()` → returns current mode's assignmentMap

### Phase 2: Refactor State Access (2 hours)
1. Update `_handleAgGridCellChange()` to use current mode state
2. Update `_handleProgressModeChange()` to switch state context
3. Update save handler to read from correct mode state
4. Update data loader to write to correct mode state

### Phase 3: Testing (1 hour)
1. Test save in Perencanaan → switch → verify Realisasi unchanged
2. Test save in Realisasi → switch → verify Perencanaan unchanged
3. Test multiple edits and mode switches
4. Test reset per mode

---

## Files to Modify

1. `jadwal_kegiatan_app.js`:
   - State initialization (add dual state structure)
   - `_handleAgGridCellChange()` - use current mode state
   - `_handleProgressModeChange()` - switch state context
   - `_getCurrentModeState()` - NEW helper method

2. `data-loader.js`:
   - Update assignment map writing to use correct mode

3. `save-handler.js`:
   - Read from correct mode's modifiedCells

---

## Timeline

- **Analysis**: ✅ Complete (30 min)
- **Implementation**: ⏳ Est. 4 hours
- **Testing**: ⏳ Est. 1 hour
- **Total**: ~5 hours

---

## User Communication

**Current Status**:
Saya telah menemukan root cause masalahnya. Ini adalah architectural issue dimana state di-share antara kedua mode, bukan bug kecil yang bisa di-patch.

**Next Steps**:
1. Implementasi dual state structure (proper fix)
2. Refactor semua state access
3. Comprehensive testing

**Estimated Fix Time**: 4-5 jam untuk implementasi yang benar dan stabil.

**Alternative**: Quick fix dengan prefixed keys (2 jam), tapi kurang maintainable.

**Recommendation untuk User**:
Tunggu proper fix (Option 1) untuk solution yang robust dan long-term.

---

**Analysis By**: Phase 2E.1 Team
**Date**: 2025-11-26
**Status**: ROOT CAUSE IDENTIFIED - Ready for Implementation
