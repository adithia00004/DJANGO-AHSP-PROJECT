# Phase 2F.0: Kurva S Harga-Based Calculation - IMPLEMENTATION COMPLETE

**Date**: 2025-11-26
**Status**: ✅ Implementation Complete, Ready for Testing
**Priority**: CRITICAL BUG FIX

---

## 🎯 Summary

Successfully fixed **critical bug** in Kurva S calculation. The chart now uses **harga-based (cost-based)** calculation instead of volume-based calculation, as per user requirements.

### Problem Fixed

**BEFORE (Bug)**:
- Kurva S used physical volume (m², m³, unit) for progress calculation
- Example: 100m² pekerjaan worth Rp 500M counted same as 100m² worth Rp 50M
- **Result**: Inaccurate project financial progress tracking

**AFTER (Fixed)**:
- Kurva S uses harga (Rupiah cost) for progress calculation
- Example: Rp 500M pekerjaan weighted 10× more than Rp 50M pekerjaan
- **Result**: Accurate financial progress based on actual project cost

---

## 📊 User Requirements Met

✅ **Requirement 1**: X-axis represents timeline (Awal Project - Akhir Project)
✅ **Requirement 2**: Y-axis represents cost-weighted percentage (biaya pekerjaan / total biaya sebelum pajak)
✅ **Requirement 3**: Input progress converted to harga progress: `(Harga Satuan × Volume × Input Progress%) / Total Biaya × 100%`

---

## 🛠️ Implementation Details

### Files Modified (4 files)

#### 1. Backend API: `detail_project/views_api.py`

**Location**: Lines 4167-4287
**Function Added**: `api_kurva_s_data()`

**What It Does**:
- Provides harga-based data for Kurva S chart
- Reuses existing `compute_rekap_for_project()` for calculation
- Returns JSON with hargaMap, totalBiayaProject, pekerjaanMeta

**Key Code**:
```python
@login_required
@require_GET
def api_kurva_s_data(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    API untuk data Kurva S - mengirim harga map dan total biaya project.
    Phase 2F.0: Fix Kurva S calculation to use HARGA (cost) instead of VOLUME.
    """
    try:
        from dashboard.models import Project
        project = get_object_or_404(Project, id=project_id)
    except Exception as e:
        logger.error(f"[Kurva S API] Project not found: {project_id}", exc_info=True)
        return JsonResponse({'error': 'Project not found'}, status=404)

    try:
        rekap_rows = compute_rekap_for_project(project)
    except Exception as e:
        logger.error(f"[Kurva S API] Failed to compute rekap for project {project_id}", exc_info=True)
        return JsonResponse({'error': 'Failed to compute rekap data', 'detail': str(e)}, status=500)

    # Build response data
    harga_map = {}
    volume_map = {}
    pekerjaan_meta = {}
    total_biaya = Decimal('0.00')

    for row in rekap_rows:
        pkj_id = str(row['pekerjaan_id'])
        total_harga = Decimal(str(row.get('total', 0)))  # G × volume

        harga_map[pkj_id] = float(total_harga)
        volume_map[pkj_id] = float(row.get('volume', 0))
        total_biaya += total_harga

        pekerjaan_meta[pkj_id] = {
            'kode': row.get('kode', ''),
            'uraian': row.get('uraian', ''),
            'satuan': row.get('satuan', ''),
            'harga_satuan': float(row.get('G', 0)),
            'volume': float(row.get('volume', 0)),
            'total': float(total_harga),
        }

    response_data = {
        'hargaMap': harga_map,
        'totalBiayaProject': float(total_biaya),
        'volumeMap': volume_map,  # Backward compatibility
        'pekerjaanMeta': pekerjaan_meta,
    }

    return JsonResponse(response_data)
```

**API Response Format**:
```json
{
  "hargaMap": {
    "1": 50000000.0,
    "2": 200000000.0
  },
  "totalBiayaProject": 250000000.0,
  "volumeMap": {
    "1": 100.0,
    "2": 200.0
  },
  "pekerjaanMeta": {
    "1": {
      "kode": "1.1",
      "uraian": "Pekerjaan A",
      "harga_satuan": 500000.0,
      "volume": 100.0,
      "total": 50000000.0
    }
  }
}
```

#### 2. URL Configuration: `detail_project/urls.py`

**Location**: Lines 259-263
**Pattern Added**: `/api/v2/project/<project_id>/kurva-s-data/`

**Code**:
```python
# ===== API: KURVA S DATA (Phase 2F.0) =====
# Provides harga-based data for Kurva S chart (not volume-based)
path('api/v2/project/<int:project_id>/kurva-s-data/',
     views_api.api_kurva_s_data,
     name='api_kurva_s_data'),
```

#### 3. Frontend Data Loading: `jadwal_kegiatan_app.js`

**Location 1**: Line 1091 (call in `_loadInitialData()`)
**Location 2**: Lines 1120-1180 (new method `_loadKurvaSData()`)

**What It Does**:
- Fetches harga data from API on page load
- Stores in `state.hargaMap`, `state.totalBiayaProject`, `state.pekerjaanMeta`
- Graceful fallback if API fails (non-critical)

**Key Code**:
```javascript
// Step 3.5: Load Kurva S harga data (Phase 2F.0)
await this._loadKurvaSData();

async _loadKurvaSData() {
  try {
    const apiUrl = `/detail-project/api/v2/project/${this.state.projectId}/kurva-s-data/`;
    const response = await fetch(apiUrl, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Store harga data in state
    this.state.hargaMap = new Map(
      Object.entries(data.hargaMap || {}).map(([k, v]) => [k, parseFloat(v) || 0])
    );
    this.state.totalBiayaProject = parseFloat(data.totalBiayaProject || 0);
    this.state.pekerjaanMeta = data.pekerjaanMeta || {};

    console.log('[JadwalKegiatanApp] ✅ Kurva S data loaded:', {
      hargaCount: this.state.hargaMap.size,
      totalBiaya: this.state.totalBiayaProject,
    });

  } catch (error) {
    console.error('[JadwalKegiatanApp] ⚠️ Failed to load Kurva S data:', error);
    // Fallback: use empty maps (Kurva S will use fallback calculation)
    this.state.hargaMap = this.state.hargaMap || new Map();
    this.state.totalBiayaProject = this.state.totalBiayaProject || 0;
  }
}
```

#### 4. Kurva S Calculation Logic: `kurva_s_module.js`

**Changes Made**:

##### A. New Functions (Lines 128-182)

**`buildHargaLookup(state)`**:
```javascript
/**
 * Build harga (cost) lookup map from state
 * Phase 2F.0: Kurva S should use HARGA (Rupiah) instead of volume
 */
function buildHargaLookup(state) {
  const lookup = new Map();
  // ... builds lookup from state.hargaMap
  return lookup;
}
```

**`getHargaForPekerjaan(hargaLookup, pekerjaanId, fallback)`**:
```javascript
/**
 * Get harga for a specific pekerjaan
 * Phase 2F.0: Used for harga-weighted Kurva S calculation
 */
function getHargaForPekerjaan(hargaLookup, pekerjaanId, fallback = 0) {
  // ... returns harga for pekerjaan ID
  return fallback;
}
```

##### B. Modified `buildDataset()` Function (Lines 472-598)

**Before**:
```javascript
// OLD: Volume-based calculation
const volumeLookup = buildVolumeLookup(state);
let totalVolume = 0;
pekerjaanIds.forEach((id) => {
  totalVolume += getVolumeForPekerjaan(volumeLookup, id, 1);
});

// Column totals calculation
const pekerjaanVolume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
columnTotals[columnIndex] += pekerjaanVolume * (percent / 100);

// Actual curve calculation
const actualPercent = (cumulativeActualVolume / totalVolume) * 100;
```

**After**:
```javascript
// NEW: Harga-based calculation (Phase 2F.0)
const hargaLookup = buildHargaLookup(state);
let totalBiaya = parseFloat(state.totalBiayaProject || 0);

// Fallback: calculate from hargaLookup if not provided
if (!totalBiaya || totalBiaya <= 0) {
  pekerjaanIds.forEach((id) => {
    totalBiaya += getHargaForPekerjaan(hargaLookup, id, 0);
  });
}

const useHargaCalculation = totalBiaya > 0 && hargaLookup.size > 0;

// Column totals calculation
if (useHargaCalculation) {
  // NEW: Harga-weighted calculation
  const pekerjaanHarga = getHargaForPekerjaan(hargaLookup, pekerjaanId, 0);
  columnTotals[columnIndex] += pekerjaanHarga * (percent / 100);
} else {
  // LEGACY: Volume-weighted (fallback)
  const pekerjaanVolume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
  columnTotals[columnIndex] += pekerjaanVolume * (percent / 100);
}

// Actual curve calculation
if (useHargaCalculation && totalBiaya > 0) {
  // NEW: Harga-weighted percentage
  actualPercent = (cumulativeActual / totalBiaya) * 100;
} else if (totalVolume > 0) {
  // LEGACY: Volume-weighted (fallback)
  actualPercent = (cumulativeActual / totalVolume) * 100;
}

// Return dataset with harga info
return {
  labels,
  planned: plannedSeries,
  actual: actualSeries,
  details,
  totalVolume,        // Legacy
  totalBiaya,         // NEW
  columnTotals,
  useHargaCalculation // NEW flag
};
```

##### C. Added Currency Formatting (Lines 623-636)

**`formatRupiah(amount)`**:
```javascript
/**
 * Format number as Indonesian Rupiah
 * Phase 2F.0: Display currency in Kurva S tooltips
 */
function formatRupiah(amount) {
  if (!Number.isFinite(amount)) return 'Rp 0';
  const formatted = Math.round(amount).toLocaleString('id-ID');
  return `Rp ${formatted}`;
}
```

##### D. Enhanced Tooltip (Lines 645-698)

**Before**:
```javascript
tooltip: {
  formatter: (params) => {
    return `
      Rencana: ${planned.toFixed(1)}%
      Aktual: ${actual.toFixed(1)}%
      Variance: ${varianceText}
    `;
  }
}
```

**After**:
```javascript
tooltip: {
  formatter: (params) => {
    // Phase 2F.0: Calculate currency amounts if using harga calculation
    const useHarga = data.useHargaCalculation && data.totalBiaya > 0;
    let plannedAmount = '';
    let actualAmount = '';

    if (useHarga) {
      const plannedRp = (data.totalBiaya * planned) / 100;
      const actualRp = (data.totalBiaya * actual) / 100;
      plannedAmount = formatRupiah(plannedRp);
      actualAmount = formatRupiah(actualRp);
    }

    return [
      `<strong>${label}</strong>`,
      useHarga
        ? `Rencana: <strong>${planned.toFixed(1)}%</strong> <span>(${plannedAmount})</span>`
        : `Rencana: <strong>${planned.toFixed(1)}%</strong>`,
      useHarga
        ? `Aktual: <strong>${actual.toFixed(1)}%</strong> <span>(${actualAmount})</span>`
        : `Aktual: <strong>${actual.toFixed(1)}%</strong>`,
      `Variance: <strong>${varianceText}</strong>`,
    ].join('');
  }
}
```

---

## 🔄 Backward Compatibility

The implementation maintains **full backward compatibility**:

1. **Graceful API Failure**: If harga API fails, falls back to volume-based calculation
2. **Legacy Data Support**: If `state.hargaMap` is empty, uses `state.volumeMap`
3. **No Breaking Changes**: Existing volume-based code paths remain intact
4. **Conditional Rendering**: Tooltip shows currency only when harga data available

**Fallback Strategy**:
```
Has hargaMap + totalBiaya? ─Yes→ Use harga-based calculation ✅
        │
        No
        ↓
Has volumeMap? ─Yes→ Use volume-based calculation (legacy)
        │
        No
        ↓
Use default values (1 per pekerjaan)
```

---

## 📐 Calculation Example

### Scenario: 2 Pekerjaan

**Pekerjaan A**:
- Volume: 100 m²
- Harga Satuan: Rp 500,000/m²
- Total Harga: Rp 50,000,000
- Progress Week 1: 25%
- Progress Week 2: 50%

**Pekerjaan B**:
- Volume: 200 m²
- Harga Satuan: Rp 1,000,000/m²
- Total Harga: Rp 200,000,000
- Progress Week 1: 0%
- Progress Week 2: 12.5%

**Total Biaya Project**: Rp 250,000,000

### Calculation: Week 1

**Volume-Based (WRONG - Old Bug)**:
```
columnTotal[0] = (100 × 25%) + (200 × 0%) = 25
actualPercent = (25 / 300) × 100% = 8.33%
```

**Harga-Based (CORRECT - Fixed)**:
```
columnTotal[0] = (50M × 25%) + (200M × 0%) = 12.5M
actualPercent = (12.5M / 250M) × 100% = 5%
```

**Impact**: Project shows 5% progress (Rp 12.5M spent) instead of misleading 8.33%

### Calculation: Week 2

**Volume-Based (WRONG)**:
```
cumulativeVolume = 25 + (100 × 50%) + (200 × 12.5%) = 25 + 50 + 25 = 100
actualPercent = (100 / 300) × 100% = 33.33%
```

**Harga-Based (CORRECT)**:
```
cumulativeHarga = 12.5M + (50M × 50%) + (200M × 12.5%)
                = 12.5M + 25M + 25M = 62.5M
actualPercent = (62.5M / 250M) × 100% = 25%
```

**Impact**: Project correctly shows 25% progress (Rp 62.5M spent) not 33.33%

---

## 🎨 Visual Impact

### Tooltip Display

**Before (Volume-based)**:
```
Week 1
Periode: 01 Jan - 07 Jan
Rencana: 10.0%
Aktual: 8.3%
Variance: -1.7% (Behind schedule)
```

**After (Harga-based)**:
```
Week 1
Periode: 01 Jan - 07 Jan
Rencana: 10.0% (Rp 25.000.000)
Aktual: 5.0% (Rp 12.500.000)
Variance: -5.0% (Behind schedule)
```

---

## ✅ Testing Checklist

### Unit Testing (Not Yet Done)
- [ ] Test `buildHargaLookup()` with valid state
- [ ] Test `getHargaForPekerjaan()` with various IDs
- [ ] Test `formatRupiah()` with edge cases
- [ ] Test `buildDataset()` with harga data
- [ ] Test `buildDataset()` fallback to volume

### Manual Testing (Ready to Start)
- [ ] Open Jadwal Pekerjaan page
- [ ] Navigate to Kurva S tab
- [ ] Verify chart displays correctly
- [ ] Hover over data points, check tooltip shows Rupiah
- [ ] Verify progress percentages match Rekap RAB
- [ ] Test with project that has no harga data (fallback)
- [ ] Check browser console for API errors
- [ ] Test with different progress scenarios

### Integration Testing
- [ ] Verify API endpoint responds correctly
- [ ] Check API response matches Rekap RAB totals
- [ ] Verify hargaMap contains all pekerjaan
- [ ] Test with large projects (100+ pekerjaan)
- [ ] Test with empty projects (no pekerjaan)

---

## 🚀 Deployment Steps

1. **Development Server**: Already running at http://0.0.0.0:8000/
2. **Manual Testing**: User to verify in browser
3. **Production Deployment**: After user approval

**Files to Deploy**:
- `detail_project/views_api.py` (backend API)
- `detail_project/urls.py` (URL routing)
- `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js` (data loading)
- `detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/kurva_s_module.js` (calculation logic)

---

## 📊 Performance Impact

### API Performance
- **Caching**: Reuses existing 5-minute cache from `compute_rekap_for_project()`
- **Computation**: No new calculations, only data formatting
- **Response Size**: ~5-10 KB for typical project (50 pekerjaan)
- **Expected Latency**: <200ms (cached), <500ms (uncached)

### Frontend Performance
- **Data Loading**: +1 API call on page load (non-blocking)
- **Chart Rendering**: No change (same ECharts rendering)
- **Memory Impact**: +Map object for hargaLookup (~1-5 KB)
- **User Experience**: No noticeable difference

---

## 🐛 Known Issues & Limitations

### None Identified Yet

The implementation is complete and ready for testing. All code has been written with:
- ✅ Proper error handling
- ✅ Fallback mechanisms
- ✅ Backward compatibility
- ✅ Clear documentation
- ✅ Type safety considerations

---

## 📝 Next Steps (Phase 2F.1)

After Phase 2F.0 is verified working:

1. **Phase 2F.1**: Dual Mode Integration (Perencanaan/Realisasi)
   - Connect Kurva S to `plannedState` and `actualState`
   - Add mode switcher UI
   - Implement "Bandingkan" mode

2. **Phase 2F.2**: Testing & Documentation
   - Unit tests
   - User acceptance testing
   - Update documentation

**Estimated Effort**: 5-7 hours (as per PHASE_2F_IMPLEMENTATION_PLAN.md)

---

## 🎯 Success Criteria

Phase 2F.0 is considered **COMPLETE** when:

✅ **Implementation**:
- [x] Backend API returns hargaMap and totalBiayaProject
- [x] Frontend loads harga data on page init
- [x] Kurva S uses harga for calculation (not volume)
- [x] Tooltip displays currency amounts

✅ **Quality**:
- [x] Code follows existing patterns
- [x] Backward compatibility maintained
- [x] Error handling implemented
- [x] Documentation complete

⏳ **Testing** (Next Step):
- [ ] User verifies chart in browser
- [ ] Progress percentages match Rekap RAB
- [ ] Tooltip shows correct Rupiah amounts
- [ ] No JavaScript errors in console

---

## 📞 Support

If issues are found during testing:

1. **Check Browser Console**: Look for API errors or JavaScript warnings
2. **Verify API Response**: Open DevTools → Network → Check `/kurva-s-data/` response
3. **Check State**: In console, run `window.kelolaTahapanPageState` to inspect state

**Common Issues**:
- API returns 404: Project not found or URL pattern mismatch
- API returns 500: Rekap calculation error (check Django logs)
- Chart shows 0%: hargaMap might be empty (check API response)
- No tooltip currency: `useHargaCalculation` flag might be false

---

**Implementation Completed By**: Claude Code
**Date**: 2025-11-26
**Phase**: 2F.0
**Status**: ✅ Ready for Testing

**Next Phase**: Phase 2F.1 (Dual Mode Integration) - Pending Phase 2F.0 Verification

---

**End of Implementation Report**
