# AG Grid Migration Checklist & Troubleshooting

**Date**: 2025-11-24
**Status**: ✅ **COMPLETED**
**Goal**: Switch from custom grid to AG Grid and troubleshoot display issues

---

## 🎉 MIGRATION COMPLETED

**Date Completed**: 2025-11-24
**Total Time**: ~3 hours (investigation + fixes)
**Result**: AG Grid successfully displaying with 5 rows and 14 columns

### Issues Found & Fixed

1. **Vite Module Path Mismatch** ❌ → ✅ FIXED
   - **Problem**: Template used full path `/detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`
   - **Root Cause**: Vite serves files relative to `root` config (`./detail_project/static/detail_project`)
   - **Fix**: Changed to `/js/src/jadwal_kegiatan_app.js` in template line 254
   - **File**: `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html:254`

2. **AG Grid Row Height Not Configured** ❌ → ✅ FIXED
   - **Problem**: Grid had 0px height, rows invisible despite data loaded
   - **Root Cause**: Missing `rowHeight` and `headerHeight` in grid options
   - **Fix**: Added `rowHeight: 42` and `headerHeight: 42`
   - **File**: `detail_project/static/detail_project/js/src/modules/grid/ag-grid-setup.js:64-65`

3. **AG Grid Container Height Collapsed** ❌ → ✅ FIXED
   - **Problem**: `.ag-root` had 0px height, `.ag-body` had 0px height
   - **Root Cause**: No CSS forcing AG Grid containers to fill parent height
   - **Fix**: Added CSS with `height: 100% !important` for `.ag-root` and `.ag-root-wrapper`
   - **File**: `detail_project/static/detail_project/css/kelola_tahapan_grid.css:1028-1049`

---

## 🎯 CURRENT SITUATION

### Configuration Status
```python
# Settings (from manage.py diffsettings)
DEBUG = True
ENABLE_AG_GRID = True  ### ✅ ENABLED
USE_VITE_DEV_SERVER = True  ### ✅ ENABLED
```

### Template Being Used
**File**: `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html`
- Line 86: `data-enable-ag-grid="{% if enable_ag_grid %}true{% else %}false{% endif %}"`
- Line 115: Custom grid with class `{% if enable_ag_grid %}d-none{% endif %}` → **HIDDEN**
- Line 152-156: AG Grid container with class `{% if not enable_ag_grid %}d-none{% endif %}` → **VISIBLE**

### Script Loading
**Lines 251-268**:
```html
{% if DEBUG and use_vite_dev_server %}
  {# Development mode: Load from Vite dev server with HMR #}
  <script type="module" src="http://localhost:5175/@vite/client"></script>
  <script type="module" src="http://localhost:5175/detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js"></script>
{% else %}
  {# Production mode: Load built assets via manifest #}
  {% vite_asset 'assets/js/jadwal-kegiatan.js' as jadwal_asset %}
  <script type="module" src="{% static jadwal_asset %}"></script>
{% endif %}
```

---

## 🚨 POTENTIAL ISSUES

### Issue #1: Vite Dev Server Port Mismatch
**Problem**: Template expects **port 5175**, but running servers might be on different ports

**Check**:
```bash
# Your running dev servers
npm run dev  # Multiple instances detected
```

**Symptoms**:
- Browser console: `Failed to load resource: net::ERR_CONNECTION_REFUSED` on http://localhost:5175
- AG Grid container visible but empty
- No JavaScript errors (script never loads)

**Solution**: Check actual Vite server port

---

### Issue #2: Vite Config - Entry Point Not Configured
**Problem**: `jadwal_kegiatan_app.js` might not be in Vite build config

**Check**: `vite.config.js` input configuration

**Solution**: Ensure entry point is configured

---

### Issue #3: AG Grid Not Initializing
**Problem**: Script loads but AG Grid doesn't mount

**Symptoms**:
- Browser console: No error OR "Cannot read property 'createGrid' of undefined"
- AG Grid container exists but empty
- Custom grid is hidden

**Solution**: Check AG Grid initialization in `jadwal_kegiatan_app.js`

---

### Issue #4: Module Import Errors
**Problem**: ES6 imports fail to resolve

**Symptoms**:
- Browser console: "Failed to resolve module specifier"
- 404 errors for module paths

**Solution**: Fix import paths or Vite alias configuration

---

## 🔍 INVESTIGATION STEPS

### Step 1: Check Vite Dev Server Status
```bash
# Check what's running on port 5175
netstat -ano | findstr :5175

# Check if Vite is actually running
# Look for npm run dev process
```

**Expected**: Vite dev server running on port 5175

---

### Step 2: Check Browser Console
1. Open page: `http://localhost:8000/detail_project/110/kelola-tahapan/`
2. Open DevTools (F12)
3. Check Console tab for errors

**Look for**:
- ❌ `net::ERR_CONNECTION_REFUSED` → Vite server not running/wrong port
- ❌ `Failed to resolve module` → Import path issue
- ❌ `createGrid is not a function` → AG Grid not loaded
- ❌ `Cannot read property 'createGrid'` → Initialization issue
- ✅ No errors but AG Grid empty → Check initialization logic

---

### Step 3: Check Network Tab
1. Open DevTools → Network tab
2. Reload page
3. Filter by "JS" or "XHR"

**Look for**:
- ❌ Red/failed requests to `localhost:5175` → Vite server issue
- ❌ 404 for `jadwal_kegiatan_app.js` → Entry point not found
- ❌ 404 for AG Grid modules → Import path issue
- ✅ 200 OK for all scripts → Scripts loaded successfully

---

### Step 4: Check AG Grid Container
1. Inspect element: `#ag-grid-container`
2. Check computed styles
3. Check if `.d-none` class is present

**Expected**:
- ✅ `display: block` or `display: flex`
- ✅ No `.d-none` class
- ✅ Width and height > 0

**If found**:
- ❌ `display: none` → Template condition wrong
- ❌ Height = 0 → Grid not initialized or empty data

---

### Step 5: Check Data Loading
Open browser console and run:
```javascript
// Check if app initialized
window.jadwalApp

// Check state
console.log(window.jadwalApp?.state)

// Check if data loaded
console.log(window.jadwalApp?.state?.pekerjaanTree)
console.log(window.jadwalApp?.state?.timeColumns)
```

**Expected**:
- ✅ `window.jadwalApp` exists
- ✅ `pekerjaanTree` has data
- ✅ `timeColumns` has 12 items (weeks)

---

## 📋 CHECKLIST: Enable AG Grid

### Pre-requisites ✅ (Already Done)
- [x] AG Grid CSS loaded (line 17-18)
- [x] `ENABLE_AG_GRID = True` in settings
- [x] `USE_VITE_DEV_SERVER = True` in settings
- [x] Modern template in use (`kelola_tahapan_grid_modern.html`)
- [x] AG Grid container present (line 152-156)
- [x] Custom grid hidden when AG Grid enabled

### To Verify 🔍
- [ ] **Vite dev server running on correct port (5175)**
- [ ] **Scripts loading successfully (check Network tab)**
- [ ] **No console errors**
- [ ] **AG Grid container visible (not `.d-none`)**
- [ ] **AG Grid initialized (check DOM for `.ag-root`)**
- [ ] **Data loaded (check `window.jadwalApp.state`)**
- [ ] **Grid renders with rows**

---

## 🚀 AGENDA: Switch to AG Grid Implementation

### Phase 1: Troubleshooting & Investigation (CURRENT)
**Duration**: 30 minutes - 1 hour

**Tasks**:
1. [ ] **Check Vite Dev Server**
   - Verify port 5175 is correct
   - Check if server is running
   - Check for port conflicts

2. [ ] **Check Browser Console**
   - Identify any JavaScript errors
   - Check module loading
   - Verify AG Grid library loaded

3. [ ] **Check Network Tab**
   - Verify script requests
   - Check for 404 errors
   - Verify AG Grid CSS/JS loaded

4. [ ] **Check AG Grid Container**
   - Inspect DOM
   - Check computed styles
   - Verify not hidden

5. [ ] **Check Data Loading**
   - Verify API calls successful
   - Check data in state
   - Verify time columns exist

**Deliverable**: Root cause identified

---

### Phase 2: Fix Identified Issues
**Duration**: 1-2 hours (depends on issue complexity)

#### Scenario A: Vite Server Not Running/Wrong Port
**Fix**:
```bash
# Stop all npm processes
taskkill /F /IM node.exe

# Start Vite on correct port
npm run dev  # Should start on 5175

# Or update template to match actual port
# kelola_tahapan_grid_modern.html line 253-254
```

#### Scenario B: Entry Point Not in Vite Config
**Fix**:
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        'jadwal-kegiatan': path.resolve(__dirname,
          'detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js'
        ),
        // ...
      }
    }
  }
});
```

#### Scenario C: AG Grid Not Initializing
**Fix**: Check `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`

```javascript
// Ensure AG Grid setup module is imported and called
import { setupAGGrid } from './modules/grid/ag-grid-setup.js';

// In app initialization
async init() {
  // ...
  if (this.state.enableAGGrid) {
    await setupAGGrid(this.state);
  }
  // ...
}
```

#### Scenario D: Import Path Issues
**Fix**: Update import paths or Vite alias config

```javascript
// vite.config.js
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'detail_project/static/detail_project/js/src'),
      '@modules': path.resolve(__dirname, 'detail_project/static/detail_project/js/src/modules'),
    }
  }
});
```

**Deliverable**: AG Grid displays correctly

---

### Phase 3: Testing & Validation
**Duration**: 1-2 hours

**Test Cases**:
1. [ ] **Grid Renders**
   - AG Grid container visible
   - Rows display correctly
   - Columns match time periods

2. [ ] **Data Display**
   - Pekerjaan names shown
   - Volume/Satuan correct
   - Time columns correct (12 weeks)

3. [ ] **Editing**
   - Can click cells
   - Can enter percentages
   - Validation works (0.01-100%)

4. [ ] **Saving**
   - Save button works
   - API call succeeds
   - Data persists after reload

5. [ ] **Charts**
   - Kurva-S renders
   - Gantt renders
   - Charts update after save

6. [ ] **Performance**
   - Grid loads < 2 seconds
   - No memory leaks
   - Smooth scrolling

**Deliverable**: All tests pass

---

### Phase 4: Compare Custom Grid vs AG Grid
**Duration**: 30 minutes

**Comparison Matrix**:

| Feature | Custom Grid | AG Grid | Winner |
|---------|-------------|---------|---------|
| **Performance** | Good (optimized) | Excellent (virtualized) | AG Grid |
| **Features** | Basic | Enterprise-grade | AG Grid |
| **Maintenance** | High (custom code) | Low (library) | AG Grid |
| **Customization** | Full control | Limited by API | Custom |
| **Bundle Size** | Small (~50KB) | Large (~500KB) | Custom |
| **Development** | More work | Less work | AG Grid |
| **Scrolling** | Custom sync | Built-in | AG Grid |
| **Validation** | Custom | Built-in | AG Grid |
| **Export** | Custom | Built-in | AG Grid |

**Decision Factors**:
1. **If prioritize features & speed**: Use AG Grid
2. **If prioritize bundle size**: Use Custom Grid
3. **If prioritize full control**: Use Custom Grid
4. **If prioritize less maintenance**: Use AG Grid

**Deliverable**: Decision documented

---

### Phase 5: Document AG Grid Implementation
**Duration**: 1 hour

**Documentation**:
1. [ ] **Setup Guide**
   - How to enable AG Grid
   - Configuration options
   - Vite setup

2. [ ] **API Documentation**
   - AG Grid column definitions
   - Cell renderers
   - Cell editors
   - Value formatters

3. [ ] **Developer Guide**
   - How to customize
   - How to add features
   - How to debug

4. [ ] **User Guide**
   - How to use grid
   - Keyboard shortcuts
   - Tips & tricks

**Deliverable**: Complete AG Grid documentation

---

## 🎯 RECOMMENDED APPROACH

### Option A: Fix AG Grid (Recommended if issues are simple)
**Pros**:
- Modern, feature-rich
- Less maintenance long-term
- Built-in features (export, filtering, etc.)

**Cons**:
- Larger bundle size
- Learning curve
- Less control

**When to choose**:
- Issues are simple (port/config)
- Want modern features
- Don't mind bundle size

---

### Option B: Stick with Custom Grid (Recommended if AG Grid too complex)
**Pros**:
- Already working
- Smaller bundle
- Full control
- Optimized for use case

**Cons**:
- More maintenance
- Need to build features manually
- Need to fix scrolling issues (from Phase 2E.0)

**When to choose**:
- AG Grid issues too complex
- Bundle size critical
- Want full control

**Action**: Set `ENABLE_AG_GRID = False` in settings

---

### Option C: Hybrid Approach
**Implementation**:
- Use custom grid as default
- Add AG Grid as optional (feature flag)
- Allow users to switch via UI

**Pros**:
- Best of both worlds
- Users can choose
- Gradual migration

**Cons**:
- Maintain both implementations
- More complex codebase

---

## 🔧 QUICK FIXES

### Fix #1: Disable AG Grid (Immediate Workaround)
If AG Grid not working and need immediate solution:

**In settings (or env vars)**:
```python
ENABLE_AG_GRID = False
```

**Result**: Custom grid will show, AG Grid hidden

---

### Fix #2: Use Production Build Instead of Dev Server
If Vite dev server causing issues:

**In settings**:
```python
USE_VITE_DEV_SERVER = False
```

**Then build**:
```bash
npm run build
```

**Result**: Uses pre-built assets from `static/dist/`

---

### Fix #3: Rollback to Legacy Template
If modern template too problematic:

**In `detail_project/views.py` line 209**:
```python
# Change from:
return render(request, "detail_project/kelola_tahapan_grid_modern.html", context)

# To:
return render(request, "detail_project/kelola_tahapan_grid_LEGACY.html", context)
```

**Result**: Uses old working template with legacy scripts

---

## 📊 DEBUGGING COMMANDS

### Check Vite Server
```bash
# Windows
netstat -ano | findstr :5175
netstat -ano | findstr :5177

# Kill node processes
taskkill /F /IM node.exe

# Restart Vite
npm run dev
```

### Check Django Server
```bash
# Check what template is rendered
python manage.py diffsettings | grep -E "ENABLE_AG_GRID|USE_VITE|DEBUG"

# Check if URLs work
python manage.py show_urls | grep kelola-tahapan
```

### Build for Production
```bash
# Build Vite assets
npm run build

# Check manifest
cat detail_project/static/detail_project/dist/.vite/manifest.json
```

---

## 📝 INVESTIGATION REPORT TEMPLATE

```markdown
## AG Grid Investigation Report

**Date**: 2025-11-23
**Investigator**: [Name]

### 1. Configuration
- [ ] `ENABLE_AG_GRID`: True/False
- [ ] `USE_VITE_DEV_SERVER`: True/False
- [ ] `DEBUG`: True/False
- [ ] Template: [filename]

### 2. Vite Server Status
- [ ] Running: Yes/No
- [ ] Port: [port number]
- [ ] URL accessible: Yes/No

### 3. Browser Console Errors
```
[List any errors here]
```

### 4. Network Tab Issues
```
[List any failed requests]
```

### 5. AG Grid Container
- [ ] Element exists: Yes/No
- [ ] Visible (not `.d-none`): Yes/No
- [ ] Has `.ag-root` child: Yes/No

### 6. Data Status
- [ ] `window.jadwalApp` exists: Yes/No
- [ ] `pekerjaanTree` loaded: Yes/No (X items)
- [ ] `timeColumns` loaded: Yes/No (X columns)

### 7. Root Cause
[Describe the root cause]

### 8. Recommended Fix
[Describe the fix]

### 9. Estimated Time
[Hours needed]
```

---

**Last Updated**: 2025-11-23
**Status**: Investigation Checklist Ready
**Next**: Execute Investigation Steps 1-5
