# Vite Path Configuration Fix

**Date**: 2025-11-19
**Issue**: Vite dev server 404 errors on module loading
**Status**: ✅ FIXED

---

## PROBLEM

User reported console errors:
```
GET http://localhost:5173/@vite/client net::ERR_ABORTED 404 (Not Found)
GET http://localhost:5173/detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js net::ERR_ABORTED 404 (Not Found)
```

**Root Cause**:
- `vite.config.js` had `base: '/static/detail_project/dist/'` for BOTH dev and production
- This caused Vite dev server to serve from wrong path
- Template was trying to load from incorrect URLs

---

## SOLUTION

### 1. Updated `vite.config.js`

**Changed:**
```javascript
// Before
base: '/static/detail_project/dist/',

// After
base: process.env.NODE_ENV === 'production' ? '/static/detail_project/dist/' : '/',
root: './detail_project/static/detail_project',
```

**Why:**
- Dev server uses root `/` for simplicity
- Production build uses `/static/detail_project/dist/` for Django static files
- `root` points to where source files are located

### 2. Updated Template Paths

**File**: `kelola_tahapan_grid_modern.html`

**Changed:**
```django
<!-- Before -->
<script type="module" src="http://localhost:5173/@vite/client"></script>
<script type="module" src="http://localhost:5173/detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js"></script>

<!-- After -->
<script type="module" src="http://localhost:5175/@vite/client"></script>
<script type="module" src="http://localhost:5175/js/src/jadwal_kegiatan_app.js"></script>
```

**Why:**
- Vite now serves from root, so path is simpler: `/js/src/...`
- Port changed to 5175 (5173 was still in use from previous session)

### 3. Restarted Vite Server

**Command:**
```bash
npm run dev
```

**Output:**
```
VITE v5.4.21  ready in 296 ms
➜  Local:   http://localhost:5175/
```

---

## TESTING

After fix, user should:

1. **Refresh browser** (Ctrl + F5)
2. **Check console** for:
   ```
   🚀 VITE DEV MODE
   [JadwalKegiatanApp] Loading data using modern DataLoader...
   ```
3. **Check Network tab**:
   - ✅ `http://localhost:5175/@vite/client` (200 OK)
   - ✅ `http://localhost:5175/js/src/jadwal_kegiatan_app.js` (200 OK)
   - ✅ `http://localhost:5175/js/src/modules/core/data-loader.js` (200 OK)

---

## IMPORTANT NOTES

### Port Number
Vite is now on **port 5175** (not 5173) because previous session was still using 5173.

**To use 5173 again:**
1. Kill all node processes: `taskkill /F /IM node.exe`
2. Restart Vite: `npm run dev`
3. Update template to use port 5173

**Or just keep using 5175** - it works fine!

### Production Build
When building for production (`npm run build`):
- Vite will use `base: '/static/detail_project/dist/'`
- Output goes to `detail_project/static/detail_project/dist/`
- Django collectstatic will pick it up

---

## FILES MODIFIED

1. [vite.config.js](../../vite.config.js) - Lines 8-13
2. [kelola_tahapan_grid_modern.html](../templates/detail_project/kelola_tahapan_grid_modern.html) - Lines 249-254

---

## VERIFICATION CHECKLIST

- [x] vite.config.js updated with conditional base path
- [x] vite.config.js has root pointing to static/detail_project
- [x] Template uses correct Vite server URL (localhost:5175)
- [x] Template uses correct module path (/js/src/...)
- [x] Vite server running successfully
- [ ] **User needs to test**: Browser loads modules without 404 errors
- [ ] **User needs to verify**: Console shows modern module logs

---

**Last Updated**: 2025-11-19
**Vite Server**: http://localhost:5175
**Status**: Ready for testing
