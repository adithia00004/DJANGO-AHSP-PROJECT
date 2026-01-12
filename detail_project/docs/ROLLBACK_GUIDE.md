# Rollback Guide - Phase 2A Modern Stack

**Date**: 2025-11-19
**Purpose**: Instructions for reverting to legacy or hybrid stack if issues occur

---

## 🎯 WHEN TO ROLLBACK

Rollback if you encounter:

1. ❌ **Critical bugs** preventing page load
2. ❌ **Data loss** or corruption
3. ❌ **Vite server issues** that can't be fixed quickly
4. ❌ **Module errors** breaking core functionality
5. ⚠️ **Performance regression** (slower than legacy)

**DO NOT rollback for:**
- ✅ Minor visual issues
- ✅ Console warnings (not errors)
- ✅ Missing features (Phase 2B task)
- ✅ Grid not rendering (expected in Phase 2A)

---

## 📋 ROLLBACK OPTIONS

Three rollback options with different levels of reversion:

| Option | Speed | Risk | Use Case |
|--------|-------|------|----------|
| **Option 1: Full Legacy** | Fast | Low | Critical failure, need stability NOW |
| **Option 2: Hybrid** | Medium | Medium | Modern modules work, need fallback option |
| **Option 3: Fix Forward** | Slow | Low | Minor issue, prefer to fix modern code |

---

## 🔄 OPTION 1: FULL LEGACY ROLLBACK

**Goal**: 100% legacy code, as before Phase 2A refactor

**When to Use**: Critical failure, production emergency, need immediate stability

### **Steps:**

#### 1. Update View (1 minute)

Edit [detail_project/views.py](../views.py) line ~209:

**Change FROM:**
```python
# MODERN TEMPLATE (2025-11-19): Clean, no conditional legacy code
return render(request, "detail_project/kelola_tahapan_grid_modern.html", context)
```

**Change TO:**
```python
# ROLLBACK: Full legacy template
return render(request, "detail_project/kelola_tahapan_grid_LEGACY.html", context)
```

#### 2. Update Settings (2 minutes)

Edit [config/settings/base.py](../../config/settings/base.py) lines ~384-385:

**Change FROM:**
```python
USE_VITE_DEV_SERVER = os.getenv("USE_VITE_DEV_SERVER", "True").lower() == "true"
ENABLE_AG_GRID = os.getenv("ENABLE_AG_GRID", "True").lower() == "true"
```

**Change TO:**
```python
USE_VITE_DEV_SERVER = os.getenv("USE_VITE_DEV_SERVER", "False").lower() == "true"
ENABLE_AG_GRID = os.getenv("ENABLE_AG_GRID", "False").lower() == "true"
```

#### 3. Restart Django (1 minute)

```bash
# Stop current Django server (Ctrl+C)
# Restart
python manage.py runserver
```

#### 4. Stop Vite (Optional)

```bash
# In Vite terminal (Ctrl+C)
# No need to run Vite anymore
```

#### 5. Verify (2 minutes)

Open browser to: `http://localhost:8000/project/1/jadwal-pekerjaan/`

**Expected Console Output:**
```
[KelolaTahapanPageApp] Kelola Tahapan page bootstrap initialized...
```

**Network Tab Should Show:**
- `kelola_tahapan_page_bootstrap.js`
- `data_loader_module.js`
- Legacy IIFE modules

**Total Time**: ~6 minutes

---

## 🔄 OPTION 2: HYBRID ROLLBACK

**Goal**: Keep Vite setup, but use hybrid template with conditional fallback

**When to Use**: Modern modules working but want legacy as backup option

### **Steps:**

#### 1. Update View (1 minute)

Edit [detail_project/views.py](../views.py) line ~209:

**Change FROM:**
```python
return render(request, "detail_project/kelola_tahapan_grid_modern.html", context)
```

**Change TO:**
```python
# ROLLBACK: Hybrid template with conditionals
return render(request, "detail_project/kelola_tahapan_grid_vite.html", context)
```

#### 2. Keep Settings (No Change)

Keep modern settings:
```python
USE_VITE_DEV_SERVER = True  # Keep Vite enabled
ENABLE_AG_GRID = True        # Keep modern modules enabled
```

#### 3. Restart Django (1 minute)

```bash
python manage.py runserver
```

#### 4. Keep Vite Running (No Change)

Vite server should still run: `npm run dev`

#### 5. Verify (2 minutes)

**Expected**: Modern modules load via Vite, but legacy scripts also available

**Console Output:**
```
🚀 VITE DEV MODE
[JadwalKegiatanApp] ...
```

**Fallback**: If Vite fails, template will load legacy scripts

**Total Time**: ~4 minutes

---

## 🔄 OPTION 3: FIX FORWARD (Recommended)

**Goal**: Don't rollback! Fix the issue in modern code

**When to Use**: Minor issues, prefer maintainability over quick fix

### **Common Issues & Fixes:**

#### **Issue 1: Vite Connection Refused**

**Symptoms**: `ERR_CONNECTION_REFUSED` to localhost:5173

**Fix**:
1. Check Vite is running: `npm run dev`
2. Check port 5173 not blocked
3. Try: `rm -rf node_modules/.vite && npm run dev`
4. Check firewall/antivirus

#### **Issue 2: Module Not Found**

**Symptoms**: `Failed to load module .../data-loader.js`

**Fix**:
1. Check file exists at correct path
2. Check import paths in `jadwal_kegiatan_app.js`
3. Check vite.config.js aliases
4. Restart Vite server

#### **Issue 3: Console Errors in Module**

**Symptoms**: JavaScript error in DataLoader or TimeColumnGenerator

**Fix**:
1. Read error message carefully
2. Check browser console stack trace
3. Add `console.log()` debugging
4. Fix the specific bug
5. HMR will auto-update

#### **Issue 4: Data Not Loading**

**Symptoms**: Empty grid, no data

**Fix**:
1. Check Network tab for API errors
2. Check `state.projectId` is set correctly
3. Check API endpoints return data
4. Add debugging to DataLoader.loadAllData()

#### **Issue 5: Performance Slower**

**Symptoms**: Page loads slower than legacy

**Fix**:
1. Check Network tab for slow requests
2. Check bundle size in `dist/stats.html`
3. Use browser Performance tab
4. Check for unnecessary re-renders
5. Review Phase 1 performance optimizations

---

## 🔍 VERIFICATION CHECKLIST

After rollback, verify:

### **Option 1 (Full Legacy):**
- [ ] Console shows `[KelolaTahapanPageApp]` logs
- [ ] Network tab shows legacy scripts
- [ ] No Vite connections
- [ ] Grid renders and works
- [ ] Save functionality works

### **Option 2 (Hybrid):**
- [ ] Console shows modern logs if Vite works
- [ ] Console shows legacy logs if Vite fails
- [ ] Both script sets available
- [ ] Grid renders and works

### **Option 3 (Fix Forward):**
- [ ] Console shows modern logs
- [ ] Specific issue is fixed
- [ ] No errors in console
- [ ] Functionality restored

---

## 📁 FILE BACKUP LOCATIONS

If you need to restore files:

| File | Backup Location | Purpose |
|------|----------------|---------|
| `kelola_tahapan_grid_LEGACY.html` | Active file | Full legacy template |
| `kelola_tahapan_grid_vite.html.backup` | Backup | Hybrid template before refactor |
| Legacy JS modules | `static/.../jadwal_pekerjaan/kelola_tahapan/` | All legacy IIFE modules |

**DO NOT DELETE** these files until Phase 2D (final cleanup)!

---

## 🚨 EMERGENCY ROLLBACK

If page is completely broken and users are affected:

### **FASTEST ROLLBACK (2 minutes):**

1. **Edit views.py line 209:**
   ```python
   return render(request, "detail_project/kelola_tahapan_grid_LEGACY.html", context)
   ```

2. **Restart Django:**
   ```bash
   python manage.py runserver
   ```

3. **Done!** Page now uses 100% legacy code.

4. **Investigate later** when users are not affected.

---

## 🔙 RE-APPLYING MODERN STACK

If you rolled back and want to re-enable modern stack:

### **Steps:**

1. **Fix the issue** that caused rollback

2. **Update views.py** line 209:
   ```python
   return render(request, "detail_project/kelola_tahapan_grid_modern.html", context)
   ```

3. **Update settings** (if changed):
   ```python
   USE_VITE_DEV_SERVER = True
   ENABLE_AG_GRID = True
   ```

4. **Restart both servers:**
   ```bash
   # Terminal 1
   npm run dev

   # Terminal 2
   python manage.py runserver
   ```

5. **Test thoroughly** before deploying

---

## 📊 ROLLBACK DECISION MATRIX

| Symptom | Severity | Action | Option |
|---------|----------|--------|--------|
| Page won't load | 🔴 Critical | Rollback immediately | Option 1 |
| Data corruption | 🔴 Critical | Rollback immediately | Option 1 |
| Vite connection errors | 🟡 Medium | Try fix first | Option 3 |
| Module errors | 🟡 Medium | Fix forward | Option 3 |
| Grid not rendering | 🟢 Low | Expected (Phase 2B) | Continue |
| Console warnings | 🟢 Low | Ignore or fix | Continue |
| Slower performance | 🟡 Medium | Investigate | Option 3 |

---

## 🛠️ TOOLS FOR DEBUGGING

Before rollback, try these debugging tools:

### **1. Browser DevTools**
- Console: See error messages
- Network: Check failed requests
- Performance: Check slowness
- Sources: Debug with breakpoints

### **2. Django Debug Toolbar**
- Check SQL queries
- Check template rendering
- Check context data

### **3. Vite Logs**
- Check Terminal 1 for Vite errors
- Look for build errors
- Check HMR updates

### **4. Git Diff**
- Compare before/after changes
- Check what was modified
- Revert specific commits if needed

---

## 📝 REPORTING ISSUES

If rollback was necessary, document:

1. **What went wrong**: Specific error messages
2. **When it happened**: After which step
3. **Rollback option used**: 1, 2, or 3
4. **Time to resolve**: How long rollback took
5. **Root cause**: What caused the issue
6. **Prevention**: How to avoid in future

---

## ✅ POST-ROLLBACK CHECKLIST

After rollback:

- [ ] Page loads without errors
- [ ] Grid renders correctly
- [ ] Save functionality works
- [ ] Charts render (Gantt, S-curve)
- [ ] Time scale switching works
- [ ] Export features work
- [ ] Performance acceptable
- [ ] No console errors
- [ ] Users can work normally

---

**Last Updated**: 2025-11-19
**Rollback Options**: 3 (Full Legacy, Hybrid, Fix Forward)
**Emergency Rollback Time**: ~2 minutes
**Recommended**: Option 3 (Fix Forward)
