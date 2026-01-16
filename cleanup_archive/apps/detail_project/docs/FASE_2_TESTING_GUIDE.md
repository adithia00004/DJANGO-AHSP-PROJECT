# FASE 2 - Testing Guide
## Jadwal Kegiatan - Modern Module Migration

**Date**: 2025-11-19
**Status**: Phase 2A Complete (Data Loading)

---

## ✅ Apa yang Sudah Selesai (Phase 2A)

### **Modul yang Sudah Di-Migrate:**
1. ✅ **DataLoader** - `modules/core/data-loader.js` (546 lines)
2. ✅ **TimeColumnGenerator** - `modules/core/time-column-generator.js` (236 lines)
3. ✅ **Main App Integration** - Updated `jadwal_kegiatan_app.js`
4. ✅ **Vite Config** - Added core-modules chunk

### **Fitur yang Sudah Bekerja:**
- ✅ Load tahapan dari API
- ✅ Load pekerjaan tree dari API
- ✅ Load volume data
- ✅ Generate time columns dari tahapan
- ✅ Load assignments (progress data)
- ✅ Concurrent loading dengan concurrency control
- ✅ Auto-detect time scale mode (daily/weekly/monthly/custom)

---

## 🧪 TESTING INSTRUCTIONS

### **Prerequisites:**

```bash
# 1. Pastikan dependencies ter-install
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
npm install

# 2. Check npm packages
npm list --depth=0
# Expected: vite, ag-grid-community, xlsx, jspdf, html2canvas
```

---

### **TEST 1: Vite Dev Server** (BASIC)

**Tujuan**: Verify Vite build system & HMR working

```bash
# Terminal 1: Start Vite dev server
npm run dev
```

**Expected Output:**
```
  VITE v5.4.21  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**✅ Pass Criteria:**
- Server starts without errors
- No module resolution errors
- Port 5173 accessible

**🔧 Troubleshooting:**
```bash
# If port busy:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Try again
npm run dev
```

---

### **TEST 2: Django Server** (BASIC)

**Tujuan**: Verify Django serves the page

```bash
# Terminal 2: Start Django
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
python manage.py runserver
```

**Expected Output:**
```
System check identified no issues (0 silenced).
Django version X.Y.Z, using settings 'config.settings.local'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

**✅ Pass Criteria:**
- Server starts on port 8000
- No migration warnings
- No errors in console

---

### **TEST 3: Page Load** (CRITICAL)

**Tujuan**: Verify page loads and Vite modules are imported

**Steps:**
1. Open browser to: `http://localhost:8000/project/1/jadwal-pekerjaan/`
   - **Note**: Ganti `1` dengan project_id yang valid di database Anda
2. Open DevTools Console (F12)
3. Check for initialization messages

**Expected Console Output:**
```
🚀 Initializing Jadwal Kegiatan App (Vite Build)
[JadwalKegiatanApp] Loading data using modern DataLoader...
[DataLoader] Loading all data...
[DataLoader] ✅ Loaded X tahapan, mode: weekly
[DataLoader] ✅ Loaded Y pekerjaan nodes
[DataLoader] ✅ Loaded Z volume entries
[TimeColumnGenerator] Generating columns for mode: weekly
[TimeColumnGenerator] ✅ Generated N time columns
[DataLoader] Progress: X / Y pekerjaan
[DataLoader] ✅ Total assignments loaded: M
[JadwalKegiatanApp] ✅ Data loaded successfully: Y pekerjaan, X tahapan, N columns
✅ Jadwal Kegiatan App initialized successfully
```

**✅ Pass Criteria:**
- ✅ No console errors
- ✅ All DataLoader steps complete
- ✅ TimeColumnGenerator generates columns
- ✅ "initialized successfully" message appears

**❌ Fail Scenarios:**

**Scenario 1: Module not found**
```
Error: Failed to resolve module specifier "@modules/core/data-loader.js"
```
**Fix**: Check vite.config.js alias settings

**Scenario 2: API 404**
```
[DataLoader] ❌ Failed to load tahapan: HTTP 404
```
**Fix**: Verify project_id exists in database, check API endpoint

**Scenario 3: CORS error**
```
Access to fetch at '...' from origin 'http://localhost:5173' has been blocked by CORS
```
**Fix**: Ensure Vite dev server running, check vite.config.js proxy settings

---

### **TEST 4: Network Tab Inspection** (DETAILED)

**Tujuan**: Verify all API calls succeed

**Steps:**
1. Open DevTools → Network tab (F12)
2. Reload page (Ctrl+R)
3. Filter by "Fetch/XHR"

**Expected Requests:**

| Request | Method | Status | Response |
|---------|--------|--------|----------|
| `/api/project/1/tahapan/` | GET | 200 | `{tahapan: [...]}` |
| `/api/project/1/list-pekerjaan/tree/` | GET | 200 | `{klasifikasi: [...]}` |
| `/api/project/1/volume-pekerjaan/list/` | GET | 200 | `{items: [...]}` |
| `/api/project/1/pekerjaan/{id}/assignments/` | GET | 200 | `{assignments: [...]}` (many) |

**✅ Pass Criteria:**
- All requests return 200 OK
- Response has expected data structure
- No 404/500 errors
- Concurrent pekerjaan assignment requests (6-10 parallel)

---

### **TEST 5: State Inspection** (ADVANCED)

**Tujuan**: Verify state is populated correctly

**Steps:**
1. Open DevTools Console
2. Run commands:

```javascript
// Check global state
window.kelolaTahapanPageState

// Expected output:
{
  tahapanList: Array(52),         // Weekly mode = 52 weeks
  pekerjaanTree: Array(X),        // Klasifikasi hierarchy
  flatPekerjaan: Array(Y),        // Flattened pekerjaan list
  timeColumns: Array(52),         // Generated columns
  volumeMap: Map(Y),              // Pekerjaan ID → Volume
  assignmentMap: Map(Z),          // Cell key → Proportion %
  expandedNodes: Set(N),          // Expanded tree nodes
  ...
}

// Check specific data
window.kelolaTahapanPageState.tahapanList.length
// Expected: > 0

window.kelolaTahapanPageState.timeColumns.length
// Expected: matches tahapanList for current mode

window.kelolaTahapanPageState.flatPekerjaan.filter(n => n.type === 'pekerjaan').length
// Expected: actual pekerjaan count

window.kelolaTahapanPageState.assignmentMap.size
// Expected: > 0 (if project has assignments)
```

**✅ Pass Criteria:**
- State object exists
- All arrays populated
- Maps have entries (if data exists in DB)
- No null/undefined critical fields

---

### **TEST 6: Module Loading Performance** (PERFORMANCE)

**Tujuan**: Verify loading speed is acceptable

**Steps:**
1. Open DevTools → Performance tab
2. Reload page with recording
3. Stop recording after page loads

**Metrics to Check:**

| Metric | Target | Status |
|--------|--------|--------|
| **Page Load Time** | < 2s | ⏱️ |
| **Data Load Time** | < 3s for 100 pekerjaan | ⏱️ |
| **Module Parse Time** | < 500ms | ⏱️ |
| **Memory Usage** | < 100MB initial | ⏱️ |

**Check via Console:**
```javascript
// Measure load time
performance.getEntriesByType('navigation')[0].loadEventEnd
// Expected: < 2000ms

// Check memory (in Chrome)
performance.memory.usedJSHeapSize / 1024 / 1024
// Expected: < 100 MB
```

**✅ Pass Criteria:**
- Load time < 2s on fast connection
- No blocking operations > 1s
- Smooth page rendering (60fps)

---

## 🐛 Common Issues & Solutions

### **Issue 1: Blank Page / No Output**

**Symptoms:**
- Page loads but shows nothing
- Console shows no logs

**Diagnosis:**
```javascript
// Check if app initialized
window.JadwalKegiatanApp
// Should be object, not undefined
```

**Solutions:**
1. Check template uses `kelola_tahapan_grid_vite.html`
2. Verify `data-project-id` attribute exists
3. Check Vite dev server is running
4. Clear browser cache (Ctrl+Shift+Delete)

---

### **Issue 2: "State is required" Error**

**Symptoms:**
```
[DataLoader] State is required
```

**Diagnosis:**
State not initialized properly

**Solutions:**
1. Check `_setupState()` runs before data loading
2. Verify `this.state` is not null
3. Check for JavaScript errors before initialization

---

### **Issue 3: Time Columns Not Generated**

**Symptoms:**
```
[TimeColumnGenerator] ✅ Generated 0 time columns
```

**Diagnosis:**
Tahapan list empty OR filtering too strict

**Solutions:**
1. Check database has tahapan for project
2. Verify time scale mode matches tahapan generation_mode
3. Check console for fallback warnings
4. Regenerate tahapan via API if needed

---

### **Issue 4: Assignments Not Loading**

**Symptoms:**
```
[DataLoader] Total assignments loaded: 0
```

**Diagnosis:**
Pekerjaan has no assignments OR API failing

**Solutions:**
1. Check Network tab for 404/500 errors on assignment endpoints
2. Verify pekerjaan IDs exist in database
3. Check tahapan IDs match between load and assignments
4. Create sample assignments via Django admin

---

### **Issue 5: Concurrent Request Timeout**

**Symptoms:**
```
[DataLoader] Failed to load assignments for pekerjaan X: timeout
```

**Diagnosis:**
Too many concurrent requests or slow server

**Solutions:**
1. Reduce concurrency in DataLoader options:
```javascript
this.dataLoader = new DataLoader(this.state, {
  assignmentConcurrency: 3  // Reduce from 6 to 3
});
```
2. Check Django server performance
3. Add database indexes on `pekerjaan_id`, `tahapan_id`

---

## 📊 Success Metrics

**FASE 2A is considered successful if:**

| Metric | Target | Status |
|--------|--------|--------|
| **Data Loading** | Tahapan + Pekerjaan + Volumes loaded | ☐ |
| **Time Columns** | Generated from tahapan (weekly mode) | ☐ |
| **Assignments** | Loaded with concurrency control | ☐ |
| **Console Errors** | Zero errors | ☐ |
| **Network Errors** | Zero 404/500 | ☐ |
| **Load Time** | < 3s for typical project | ☐ |
| **Memory Usage** | < 100MB initial | ☐ |

**Mark ✅ when all pass!**

---

## 🚀 Next Steps (FASE 2B)

After testing Phase 2A successfully, proceed to:

1. **Grid Renderer Module** - Render data to HTML table
2. **Save Handler Module** - Save changes to backend
3. **Gantt Adapter** - Chart visualization
4. **Kurva S Adapter** - S-curve visualization

**Estimated Time**: 2-3 days additional

---

## 📝 Test Results Template

**Copy this and fill after testing:**

```markdown
## Test Results - FASE 2A

**Date**: YYYY-MM-DD
**Tester**: [Your Name]
**Environment**: Windows/Linux/Mac
**Browser**: Chrome X.Y / Firefox X.Y

### Test 1: Vite Dev Server
- [ ] Started successfully
- [ ] No module errors
- Notes:

### Test 2: Django Server
- [ ] Started on port 8000
- [ ] No migration warnings
- Notes:

### Test 3: Page Load
- [ ] Page loads without errors
- [ ] Console shows initialization
- [ ] All DataLoader steps complete
- Notes:

### Test 4: Network Requests
- [ ] Tahapan API: 200 OK
- [ ] Pekerjaan API: 200 OK
- [ ] Volume API: 200 OK
- [ ] Assignments API: 200 OK
- Notes:

### Test 5: State Inspection
- [ ] State object populated
- [ ] tahapanList: X items
- [ ] flatPekerjaan: Y items
- [ ] timeColumns: Z items
- [ ] assignmentMap: W entries
- Notes:

### Test 6: Performance
- [ ] Load time: ___ms
- [ ] Memory usage: ___MB
- Notes:

### Issues Found:
1.
2.
3.

### Overall Status:
- [ ] ✅ PASS - Ready for Phase 2B
- [ ] ⚠️ PARTIAL - Some issues, can proceed with caution
- [ ] ❌ FAIL - Needs fixes before continuing
```

---

**Last Updated**: 2025-11-19
**Next Review**: After Phase 2B completion (Grid Renderer)
