# Testing Guide: Phase 0 & Phase 1 (Day 1-7)

**Date**: 2025-11-28
**Purpose**: Comprehensive manual testing checklist for all implemented features
**Scope**: Phase 0 (StateManager) + Phase 1 (Kurva S Harga + Rekap Kebutuhan Backend)

---

## Table of Contents

1. [Pre-Testing Setup](#pre-testing-setup)
2. [Phase 0: StateManager Tests](#phase-0-statemanager-tests)
3. [Phase 1 Day 1-4: Kurva S Harga Tests](#phase-1-day-1-4-kurva-s-harga-tests)
4. [Phase 1 Day 5-7: Rekap Kebutuhan Backend Tests](#phase-1-day-5-7-rekap-kebutuhan-backend-tests)
5. [Integration Tests](#integration-tests)
6. [Performance Tests](#performance-tests)
7. [Browser Compatibility Tests](#browser-compatibility-tests)

---

## Pre-Testing Setup

### 1. Django Server Check

```bash
# Test: Django configuration is valid
python manage.py check

# Expected: System check identified no issues (0 silenced)
```

**Status**: ☐ Pass / ☐ Fail

---

### 2. Build Frontend Assets

```bash
# Test: Frontend builds without errors
npm run build

# Expected: Build completes in ~13-15 seconds with no errors
```

**Status**: ☐ Pass / ☐ Fail

**Expected Output**:
```
✓ built in 13.22s
detail_project/static/detail_project/js/dist/jadwal-kegiatan-bundle.js
detail_project/static/detail_project/js/dist/chart-modules-bundle.js
```

---

### 3. Start Development Server

```bash
# Test: Server starts without errors
python manage.py runserver

# Expected: Development server running at http://127.0.0.1:8000/
```

**Status**: ☐ Pass / ☐ Fail

---

### 4. Prepare Test Data

**Requirements**:
- ☐ At least 1 project with pekerjaan (work items)
- ☐ Project has VolumePekerjaan data
- ☐ Project has HargaItemProject data (for cost calculation)
- ☐ Project has PekerjaanProgressWeekly data (planned & actual)
- ☐ Project has DetailPekerjaanComponent data (for rekap kebutuhan)

> **Catatan 2025-11-28:** Saat menguji penyimpanan, pastikan payload di console sudah menampilkan `planned_proportion` atau `actual_proportion`. Endpoint `api/v2/.../assign-weekly/` tetap menerima `proportion` sebagai fallback, tetapi roadmap Option C menargetkan field baru tersebut sebagai sumber kebenaran.

**Navigation**: Login → Projects → Select a project with complete data

---

## Phase 0: StateManager Tests

### Test 0.1: StateManager Initialization

**Location**: Browser Console (F12)

**Steps**:
1. Navigate to project detail page with Kurva S chart
2. Open browser console (F12)
3. Type: `window.StateManager`

**Expected Result**:
```javascript
▼ Object {version: "1.0.0", stores: Object, ...}
  ├─ version: "1.0.0"
  ├─ stores: {projectData: Store, chartData: Store, ...}
  └─ subscribe: function()
```

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 0.2: ProjectData Store

**Steps**:
1. Open browser console
2. Type: `StateManager.stores.projectData.getState()`

**Expected Result**:
```javascript
{
  projectId: 123,           // Your project ID
  projectName: "...",       // Your project name
  startDate: "2024-01-01",  // Project dates
  endDate: "2024-12-31",
  isLoading: false,
  error: null
}
```

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 0.3: ChartData Store

**Steps**:
1. Open browser console
2. Type: `StateManager.stores.chartData.getState()`

**Expected Result**:
```javascript
{
  kurvaSData: {
    labels: ["W1", "W2", "W3", ...],
    planned: [5, 12, 20, ...],
    actual: [4, 10, 18, ...],
    isLoading: false
  },
  ganttData: {...},
  error: null
}
```

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 0.4: State Persistence (LocalStorage)

**Steps**:
1. Open browser console
2. Type: `localStorage.getItem('stateManager_projectData')`
3. Type: `localStorage.getItem('stateManager_chartData')`

**Expected Result**:
- Both should return JSON strings with project data
- Data should match current state

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 0.5: State Subscription

**Steps**:
1. Open browser console
2. Run this code:
```javascript
const unsubscribe = StateManager.stores.projectData.subscribe(
  (state) => console.log('State changed:', state)
);
```
3. Refresh the page or navigate to another project
4. Check console for state change logs

**Expected Result**:
- Console logs "State changed: {...}" when data updates
- No errors in console

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

## Phase 1 Day 1-4: Kurva S Harga Tests

### Test 1.1: Kurva S Chart Initial Load (Progress View)

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Navigate to project detail page
2. Click on "Kurva S" tab
3. Wait for chart to load

**Expected Result**:
- ✅ Chart displays with two lines: "Planned" (blue) and "Actual" (red)
- ✅ X-axis shows weeks (W1, W2, W3, ...)
- ✅ Y-axis shows "Progress %" (0-100)
- ✅ Legend shows "Planned" and "Actual"
- ✅ No console errors

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.2: Toggle Button Visibility

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Look for toggle button in top-right corner of chart area
2. Check button text and icon

**Expected Result**:
- ✅ Button visible with text "Show Cost View"
- ✅ Icon: 💵 (fa-money-bill-wave)
- ✅ Button has blue outline (btn-outline-primary)
- ✅ Button has tooltip "Toggle between Progress View and Cost View"

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.3: Backend API - Kurva S Harga Endpoint

**Location**: Browser or API Testing Tool

**Steps**:
1. Get your project ID (e.g., 123)
2. Navigate to: `http://127.0.0.1:8000/detail-project/api/v2/project/123/kurva-s-harga/`
3. Check response (login required)

**Expected Result**:
```json
{
  "success": true,
  "weeklyData": {
    "planned": [
      {
        "week_number": 1,
        "start_date": "2024-01-01",
        "end_date": "2024-01-07",
        "weekly_cost": "5000000.00",
        "cumulative_cost": "5000000.00",
        "cumulative_percent": 5.5
      },
      ...
    ],
    "actual": [...]
  },
  "summary": {
    "total_planned_cost": "90000000.00",
    "total_actual_cost": "85000000.00",
    ...
  },
  "pekerjaanMeta": [...]
}
```

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.4: Toggle to Cost View (First Time Load)

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Click "Show Cost View" button
2. Observe:
   - Button becomes disabled
   - Spinner appears next to button text
   - Network request to `/kurva-s-harga/` API
   - Chart updates after data loads

**Expected Result**:
- ✅ Loading spinner shows during API call
- ✅ Button text changes to "Show Progress View"
- ✅ Icon changes to 📊 (fa-chart-line)
- ✅ Chart legend changes to "Cost Planned" and "Cost Actual"
- ✅ Y-axis label changes to "% of Total Cost"
- ✅ Data values represent cost percentages (not progress percentages)
- ✅ Button re-enabled after load completes
- ✅ No console errors

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.5: Toggle Back to Progress View (Cached Data)

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Click "Show Progress View" button (after completing Test 1.4)
2. Observe instant switch (no API call)

**Expected Result**:
- ✅ Chart switches instantly (no loading spinner)
- ✅ Button text changes back to "Show Cost View"
- ✅ Icon changes back to 💵 (fa-money-bill-wave)
- ✅ Chart legend changes back to "Planned" and "Actual"
- ✅ Y-axis label changes back to "Progress %"
- ✅ No network request (data cached)

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.6: Toggle Multiple Times (Cache Test)

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Click toggle button 5 times rapidly
2. Observe behavior

**Expected Result**:
- ✅ Only ONE API call made (on first switch to cost view)
- ✅ Subsequent toggles use cached data
- ✅ Smooth transitions with no delays
- ✅ No duplicate network requests
- ✅ No console errors

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.7: Chart Tooltip (Progress View)

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Ensure chart is in Progress View
2. Hover mouse over data points on chart lines

**Expected Result**:
- ✅ Tooltip appears showing:
  - Week number (e.g., "Week 1")
  - Planned: X%
  - Actual: Y%
- ✅ Tooltip follows mouse cursor
- ✅ Format is clean and readable

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.8: Chart Tooltip (Cost View)

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Toggle to Cost View
2. Hover mouse over data points on chart lines

**Expected Result**:
- ✅ Tooltip appears showing:
  - Week number (e.g., "Week 1")
  - Cost Planned: Rp X.XXX.XXX (Y%)
  - Cost Actual: Rp X.XXX.XXX (Y%)
- ✅ Currency formatted with Rupiah symbol
- ✅ Percentages show portion of total cost

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.9: Chart Responsiveness

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Resize browser window (make smaller/larger)
2. Observe chart behavior

**Expected Result**:
- ✅ Chart resizes to fit container
- ✅ Legend remains readable
- ✅ Axis labels don't overlap
- ✅ Toggle button remains visible and functional

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 1.10: Network Error Handling

**Location**: Project Detail → "Kurva S" Tab

**Steps**:
1. Open browser DevTools → Network tab
2. Enable "Offline" mode (or throttle to offline)
3. Click "Show Cost View" button
4. Observe error handling

**Expected Result**:
- ✅ Error message displays (console or UI)
- ✅ Chart doesn't break
- ✅ Button re-enabled after error
- ✅ User can retry toggle
- ✅ Graceful degradation (shows progress view)

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

## Phase 1 Day 5-7: Rekap Kebutuhan Backend Tests

### Test 2.1: Backend API - Rekap Kebutuhan Endpoint Exists

**Location**: Browser or API Testing Tool

**Steps**:
1. Navigate to: `http://127.0.0.1:8000/detail-project/api/v2/project/123/rekap-kebutuhan-weekly/`
   (Replace 123 with your project ID)
2. Check response

**Expected Result**:
- ✅ HTTP 200 OK response
- ✅ JSON response with structure:
```json
{
  "success": true,
  "weeklyData": [...],
  "summary": {...},
  "metadata": {...}
}
```

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 2.2: API Response - Weekly Data Structure

**Location**: API Response from Test 2.1

**Steps**:
1. Examine `weeklyData` array in response
2. Check first week's structure

**Expected Result**:
```json
{
  "week_number": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-01-07",
  "items": [
    {
      "kategori": "BHN",
      "kategori_display": "Bahan",
      "item_name": "Semen Portland",
      "satuan": "zak",
      "quantity": 150.50,
      "pekerjaan_name": "Pekerjaan Pondasi"
    },
    ...
  ]
}
```

**Validation**:
- ✅ All weeks have week_number, start_date, end_date
- ✅ Each item has kategori (TK/BHN/ALT/LAIN)
- ✅ Each item has kategori_display
- ✅ Quantity is numeric (not null)
- ✅ Items are grouped by week

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 2.3: API Response - Summary Data

**Location**: API Response from Test 2.1

**Steps**:
1. Examine `summary` object in response

**Expected Result**:
```json
{
  "total_weeks": 12,
  "categories": {
    "TK": {
      "count": 45,
      "display": "Tenaga Kerja"
    },
    "BHN": {
      "count": 120,
      "display": "Bahan"
    },
    "ALT": {
      "count": 30,
      "display": "Alat"
    },
    "LAIN": {
      "count": 15,
      "display": "Lain-lain"
    }
  }
}
```

**Validation**:
- ✅ total_weeks matches number of weeks in weeklyData
- ✅ All 4 categories present (TK/BHN/ALT/LAIN)
- ✅ Count reflects actual items per category
- ✅ Display names are in Indonesian

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 2.4: API Response - Metadata

**Location**: API Response from Test 2.1

**Steps**:
1. Examine `metadata` object in response

**Expected Result**:
```json
{
  "project_id": 123,
  "project_name": "Proyek ABC",
  "generated_at": "2025-11-28T10:30:00"
}
```

**Validation**:
- ✅ project_id matches request parameter
- ✅ project_name is correct
- ✅ generated_at is valid ISO timestamp

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 2.5: Calculation Accuracy - Weekly Requirement Formula

**Location**: API Response + Database

**Steps**:
1. Pick one item from week 1 response
2. Manually verify calculation:
   - Get VolumePekerjaan.volume_value
   - Get DetailPekerjaanComponent.koefisien
   - Get PekerjaanProgressWeekly.planned_proportion for week 1
3. Calculate: `volume × koefisien × (proportion / 100)`
4. Compare with API response quantity

**Example**:
```
Volume: 100 m³
Koefisien: 8 zak/m³
Week 1 Proportion: 25%
Expected: 100 × 8 × 0.25 = 200 zak
```

**Expected Result**:
- ✅ API quantity matches manual calculation
- ✅ Decimal precision is maintained
- ✅ No rounding errors

**Status**: ☐ Pass / ☐ Fail

**Manual Calculation**:
_________________________________

**API Result**:
_________________________________

---

### Test 2.6: Category Aggregation (TK/BHN/ALT/LAIN)

**Location**: API Response

**Steps**:
1. Check that items are correctly categorized
2. Verify each item has correct kategori value

**Expected Result**:
- ✅ TK items: Tenaga kerja (labor) items
- ✅ BHN items: Bahan (materials) items
- ✅ ALT items: Alat (equipment) items
- ✅ LAIN items: Lain-lain (other) items
- ✅ No items without kategori
- ✅ kategori_display matches kategori

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 2.7: Empty/Null Data Handling

**Location**: API Testing

**Steps**:
1. Test with project that has NO weekly progress data
2. Test with project that has NO components
3. Check API responses

**Expected Result**:
- ✅ No crashes or 500 errors
- ✅ Returns empty weeklyData array `[]`
- ✅ Summary shows zero counts
- ✅ Graceful handling of missing data

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 2.8: Permission & Authentication

**Location**: API Testing (Logged Out)

**Steps**:
1. Log out from Django admin/application
2. Try to access API endpoint directly
3. Check response

**Expected Result**:
- ✅ Redirects to login page OR
- ✅ Returns 401/403 error
- ✅ Does not expose data to unauthenticated users

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

## Integration Tests

### Test 3.1: StateManager + Kurva S Chart Integration

**Location**: Project Detail → Kurva S Tab

**Steps**:
1. Open browser console
2. Check StateManager stores before toggling
3. Toggle to Cost View
4. Check StateManager stores after data loads
5. Verify chartData store updated

**Expected Result**:
- ✅ chartData.kurvaSData updates after API call
- ✅ Cost data stored in chartData store
- ✅ No state conflicts or overwrites

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 3.2: Multi-Tab Navigation (State Persistence)

**Location**: Project Detail Page

**Steps**:
1. Navigate to Kurva S tab
2. Toggle to Cost View (load cost data)
3. Switch to another tab (e.g., Gantt Chart)
4. Switch back to Kurva S tab

**Expected Result**:
- ✅ Cost View remains active (state persisted)
- ✅ No re-fetch of cost data (cache works)
- ✅ Chart renders immediately with cached data
- ✅ Toggle button shows correct state

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 3.3: Page Refresh (LocalStorage Persistence)

**Location**: Project Detail → Kurva S Tab

**Steps**:
1. Toggle to Cost View
2. Refresh browser (F5)
3. Check if Cost View is restored

**Expected Result**:
- ✅ State restored from localStorage
- ✅ Cost View loads on page refresh (if implemented)
- ✅ No data loss

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 3.4: Multiple Projects (State Isolation)

**Location**: Project List → Multiple Projects

**Steps**:
1. Navigate to Project A → Toggle to Cost View
2. Navigate to Project B → Check default view
3. Navigate back to Project A → Check view state

**Expected Result**:
- ✅ Project B starts in Progress View (default)
- ✅ Project A maintains Cost View (if state persisted per project)
- ✅ No state leakage between projects

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

## Performance Tests

### Test 4.1: Initial Page Load Time

**Location**: Project Detail Page

**Steps**:
1. Open browser DevTools → Network tab
2. Hard refresh page (Ctrl+Shift+R)
3. Measure DOMContentLoaded and Load times

**Expected Result**:
- ✅ DOMContentLoaded < 2 seconds
- ✅ Load < 5 seconds
- ✅ Chart renders within 1 second after data loads

**Status**: ☐ Pass / ☐ Fail

**Measurements**:
- DOMContentLoaded: _______ ms
- Load: _______ ms
- Chart render: _______ ms

---

### Test 4.2: API Response Time

**Location**: Browser DevTools → Network Tab

**Steps**:
1. Click "Show Cost View" button
2. Check Network tab for `/kurva-s-harga/` request
3. Note response time

**Expected Result**:
- ✅ Response time < 1 second for small projects
- ✅ Response time < 3 seconds for large projects (100+ pekerjaan)

**Status**: ☐ Pass / ☐ Fail

**Measurements**:
- kurva-s-harga API: _______ ms
- rekap-kebutuhan-weekly API: _______ ms

---

### Test 4.3: Memory Usage (No Memory Leaks)

**Location**: Browser DevTools → Performance/Memory Tab

**Steps**:
1. Open Performance Monitor
2. Toggle between views 20 times
3. Check memory usage trend

**Expected Result**:
- ✅ Memory usage stabilizes (no continuous increase)
- ✅ No significant memory leaks
- ✅ Garbage collection works properly

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

### Test 4.4: Bundle Size Check

**Location**: Terminal

**Steps**:
```bash
npm run build
ls -lh detail_project/static/detail_project/js/dist/
```

**Expected Result**:
- ✅ jadwal-kegiatan-bundle.js < 500 KB
- ✅ chart-modules-bundle.js < 300 KB
- ✅ No significant bundle size increase from Phase 0

**Status**: ☐ Pass / ☐ Fail

**Measurements**:
- jadwal-kegiatan-bundle.js: _______ KB
- chart-modules-bundle.js: _______ KB

---

## Browser Compatibility Tests

### Test 5.1: Chrome/Edge (Chromium)

**Steps**:
Run all tests above in Chrome or Edge browser

**Expected Result**:
- ✅ All features work correctly
- ✅ No console errors
- ✅ UI renders properly

**Status**: ☐ Pass / ☐ Fail

---

### Test 5.2: Firefox

**Steps**:
Run critical tests in Firefox:
- Test 1.1, 1.4, 1.5 (Kurva S toggle)
- Test 2.1, 2.2 (Rekap API)

**Expected Result**:
- ✅ Features work in Firefox
- ✅ No browser-specific errors

**Status**: ☐ Pass / ☐ Fail

---

### Test 5.3: Mobile Responsive (Chrome DevTools)

**Steps**:
1. Open DevTools → Toggle device toolbar (Ctrl+Shift+M)
2. Test on:
   - iPhone SE (375px)
   - iPad (768px)
   - Desktop (1920px)

**Expected Result**:
- ✅ Toggle button visible on mobile
- ✅ Chart readable on small screens
- ✅ No horizontal scroll
- ✅ Touch events work on mobile

**Status**: ☐ Pass / ☐ Fail

**Notes**:
_________________________________

---

## Test Summary

### Overall Results

**Phase 0 Tests**:
- Total: 5 tests
- Passed: ☐ _____ / 5
- Failed: ☐ _____ / 5

**Phase 1 Day 1-4 Tests**:
- Total: 10 tests
- Passed: ☐ _____ / 10
- Failed: ☐ _____ / 10

**Phase 1 Day 5-7 Tests**:
- Total: 8 tests
- Passed: ☐ _____ / 8
- Failed: ☐ _____ / 8

**Integration Tests**:
- Total: 4 tests
- Passed: ☐ _____ / 4
- Failed: ☐ _____ / 4

**Performance Tests**:
- Total: 4 tests
- Passed: ☐ _____ / 4
- Failed: ☐ _____ / 4

**Browser Compatibility**:
- Total: 3 tests
- Passed: ☐ _____ / 3
- Failed: ☐ _____ / 3

---

### Critical Issues Found

1. ____________________________________________
   - Severity: ☐ High / ☐ Medium / ☐ Low
   - Status: ☐ Open / ☐ Fixed

2. ____________________________________________
   - Severity: ☐ High / ☐ Medium / ☐ Low
   - Status: ☐ Open / ☐ Fixed

3. ____________________________________________
   - Severity: ☐ High / ☐ Medium / ☐ Low
   - Status: ☐ Open / ☐ Fixed

---

### Sign-off

**Tester Name**: _______________________________

**Date**: _______________________________

**Overall Assessment**:
☐ All tests passed - Ready for production
☐ Minor issues - Ready with caveats
☐ Major issues - Needs fixes before deployment

**Notes**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

## Quick Test Checklist (For Rapid Validation)

If you want a quick smoke test, run these essential tests:

### Quick Test Suite (15 minutes)

1. ☐ **Django Check**: `python manage.py check` → No errors
2. ☐ **Build**: `npm run build` → Success in ~13s
3. ☐ **Server**: `python manage.py runserver` → Starts without errors
4. ☐ **StateManager**: Console → `window.StateManager` → Object exists
5. ☐ **Kurva S Load**: Navigate to Kurva S tab → Chart displays
6. ☐ **Toggle to Cost**: Click "Show Cost View" → Chart updates with cost data
7. ☐ **Toggle Back**: Click "Show Progress View" → Instant switch (cached)
8. ☐ **API Test**: Visit `/api/v2/project/123/kurva-s-harga/` → JSON response
9. ☐ **Rekap API**: Visit `/api/v2/project/123/rekap-kebutuhan-weekly/` → JSON response
10. ☐ **Browser Console**: Check for errors → No critical errors

**All Quick Tests Pass?** ☐ Yes / ☐ No

If all quick tests pass, the implementation is likely working correctly!

---

## Automated Test Recommendations (Future)

For future phases, consider implementing:

1. **Jest/Vitest Unit Tests**:
   - StateManager store tests
   - Chart data transformation tests
   - API response mocking

2. **Django Unit Tests**:
   ```python
   # test_api.py
   def test_kurva_s_harga_api(self):
       response = self.client.get(f'/api/v2/project/{self.project.id}/kurva-s-harga/')
       self.assertEqual(response.status_code, 200)
       self.assertIn('weeklyData', response.json())
   ```

3. **E2E Tests (Playwright/Cypress)**:
   - Full user journey tests
   - Cross-browser automation
   - Visual regression testing

---

**End of Testing Guide**
