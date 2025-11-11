# 🐛 BUG INVESTIGATION REPORT: Z-INDEX & RESET ISSUES

**Date**: 2025-11-11
**Reported By**: User
**Status**: ✅ **ROOT CAUSE IDENTIFIED**
**Severity**: 🔴 **P0 - High Priority**

---

## 📋 Executive Summary

Ditemukan **2 critical bugs** yang mempengaruhi user experience:

1. **🐛 BUG #1**: Notifikasi toast tertutup oleh modal/backdrop (z-index issue)
2. **🐛 BUG #2**: Reset modified_referensi gagal tanpa error message yang jelas

Kedua bug telah di-investigate dan root cause telah diidentifikasi.

---

## 🐛 BUG #1: Toast Notification Tertutup oleh Modal

### **Problem Statement**

Notifikasi konfirmasi berhasil/gagal simpan **tidak terlihat** karena tertutup oleh:
- Modal Bootstrap (z-index: 13000)
- Modal backdrop (z-index: 12990)

### **Root Cause Analysis**

#### **File**: `detail_project/static/detail_project/js/core/toast.js`

**Line 15**:
```javascript
area.style.zIndex = '12050'; // ❌ PROBLEM: Terlalu rendah!
```

#### **File**: `detail_project/static/detail_project/css/core.css`

**Line 28**:
```css
--dp-z-toast: 12050;  /* ❌ PROBLEM: Di bawah modal! */
```

**Line 26-27**:
```css
--dp-z-modal: 13000;     /* Modal Bootstrap */
--dp-z-backdrop: 12990;  /* backdrop di bawah modal */
```

### **Z-Index Hierarchy (Current - BROKEN)**

```
Modal:          13000  ⬅️ Highest
Modal Backdrop: 12990
Toast:          12050  ⬅️ ❌ PROBLEM: Toast tertutup!
Sidebar:        12045
Topbar:         12044
```

### **Visual Evidence**

**Scenario**: User melakukan save operation yang menampilkan modal loading

```
┌─────────────────────────────────┐
│    Modal Loading (z: 13000)     │  ⬅️ Terlihat
│                                 │
│  ┌──────────────────┐          │
│  │  ✅ Berhasil!    │ z: 12050 │  ⬅️ ❌ TERTUTUP!
│  └──────────────────┘          │
└─────────────────────────────────┘
```

**Result**: Toast tidak terlihat oleh user.

### **Impact**

| Impact | Severity |
|--------|----------|
| **User tidak tahu save berhasil/gagal** | 🔴 Critical |
| **User melakukan double save** | 🟡 Medium |
| **User frustrasi** | 🟡 Medium |
| **Support tickets meningkat** | 🟡 Medium |

### **Affected Files**

1. `detail_project/static/detail_project/js/core/toast.js`
   - Line 15: `area.style.zIndex = '12050';`

2. `detail_project/static/detail_project/css/core.css`
   - Line 28: `--dp-z-toast: 12050;`

3. **All pages using toast notifications**:
   - Harga Items (harga_items.js)
   - Template AHSP (template_ahsp.js)
   - List Pekerjaan (list_pekerjaan.js)
   - Volume Pekerjaan (volume_pekerjaan.js)
   - Rekap Kebutuhan (rekap_kebutuhan.js)

### **Solution Recommendation**

#### **Fix #1: Update Z-Index Values**

**File**: `detail_project/static/detail_project/css/core.css`

```css
/* BEFORE (BROKEN) */
--dp-z-modal: 13000;
--dp-z-backdrop: 12990;
--dp-z-toast: 12050;  /* ❌ Too low! */

/* AFTER (FIXED) */
--dp-z-toast: 13100;     /* ✅ Above modal */
--dp-z-modal: 13000;     /* Modal Bootstrap */
--dp-z-backdrop: 12990;  /* Backdrop below modal */
```

**File**: `detail_project/static/detail_project/js/core/toast.js`

```javascript
// BEFORE (BROKEN)
area.style.zIndex = '12050'; // ❌ Too low!

// AFTER (FIXED)
area.style.zIndex = '13100'; // ✅ Above modal
```

#### **New Z-Index Hierarchy (FIXED)**

```
Toast:          13100  ⬅️ ✅ Highest (always visible)
Modal:          13000
Modal Backdrop: 12990
Sidebar:        12045
Topbar:         12044
Toolbar:        12041
Dropdown:       12040
Sticky:         12031
Thead:          12030
```

**Rationale**: Toast notification harus SELALU terlihat, bahkan di atas modal, karena:
1. Toast adalah feedback critical untuk user actions
2. Toast auto-dismiss (tidak blocking)
3. Toast tidak mengganggu modal interaction

### **Implementation Steps**

1. **Update core.css** (Line 28):
   ```css
   --dp-z-toast: 13100;  /* Above modal */
   ```

2. **Update toast.js** (Line 15):
   ```javascript
   area.style.zIndex = '13100';
   ```

3. **Test Scenarios**:
   - ✅ Toast visible without modal
   - ✅ Toast visible WITH modal open
   - ✅ Toast visible WITH backdrop
   - ✅ Toast auto-dismisses correctly
   - ✅ Multiple toasts stack correctly

### **Alternative Solutions Considered**

#### **Option A**: Move toast inside modal ❌ **Rejected**
- **Pros**: No z-index conflict
- **Cons**:
  - Toast only visible inside modal
  - Not reusable for non-modal scenarios
  - Breaking change

#### **Option B**: Dismiss modal before showing toast ❌ **Rejected**
- **Pros**: Simple
- **Cons**:
  - Bad UX (modal closing unexpectedly)
  - May lose context
  - Confusing for users

#### **Option C**: Increase toast z-index ✅ **SELECTED**
- **Pros**:
  - Simple 1-line change
  - No breaking changes
  - Universal fix
  - Best UX
- **Cons**: None

---

## 🐛 BUG #2: Reset Modified_Referensi Gagal Tanpa Error Message

### **Problem Statement**

User melakukan **reset pekerjaan modified_referensi** ke referensi aslinya, tetapi operation **gagal** tanpa error message yang jelas. User tidak tahu:
- Kenapa gagal?
- Apa yang salah?
- Bagaimana cara fix?

### **Root Cause Analysis**

#### **File**: `detail_project/static/detail_project/js/template_ahsp.js`

**Lines 733-756**: Reset handler code

```javascript
// PROBLEM AREA
resetBtn.addEventListener('click', () => {
  if (!activeJobId || activeSource !== 'ref_modified') return;
  if (!confirm('Reset rincian dari referensi? Perubahan lokal akan hilang.')) return;

  const url = urlFor(endpoints.reset, activeJobId);
  fetch(url, {
    method:'POST',
    credentials:'same-origin',
    headers:{ 'X-CSRFToken': CSRF }
  }).then(r=>r.json()).then(js=>{
    // ❌ PROBLEM #1: Generic error handling
    if (!js.ok) throw new Error('Gagal reset');

    // Success path...
    fetch(urlFor(endpoints.get, activeJobId), {credentials:'same-origin'})
      .then(r=>r.json()).then(js=>{
        rowsByJob[activeJobId] = { items: js.items || [], kategoriMeta: js.meta?.kategori_opts || [], readOnly: !!js.meta?.read_only };
        paint(rowsByJob[activeJobId].items);
        setDirty(false);
        setEditorModeBySource();
        toast('Di-reset dari referensi', 'success');
      });

  // ❌ PROBLEM #2: No error details shown
  }).catch(()=> toast('Gagal reset', 'error'));
});
```

**Line 797**: Toast z-index in template_ahsp.js
```javascript
z-index: 10000;  // ❌ PROBLEM #3: Lower than modal (13000)
```

### **Issues Identified**

#### **Issue #1**: Generic Error Handling (Line 743)
```javascript
if (!js.ok) throw new Error('Gagal reset');  // ❌ No details!
```

**Problems**:
- Error message dari server **tidak ditampilkan**
- User tidak tahu apa yang salah
- Debugging impossible

**Server Response Example**:
```json
{
  "ok": false,
  "errors": [
    {"field": "ref", "message": "Pointer referensi tidak ditemukan"}
  ]
}
```

**Current Behavior**: User hanya lihat "Gagal reset" ❌

**Expected Behavior**: User lihat "Pointer referensi tidak ditemukan" ✅

#### **Issue #2**: No Error Details in Catch Block (Line 754)
```javascript
.catch(()=> toast('Gagal reset', 'error'));  // ❌ Generic message!
```

**Problems**:
- Network errors tidak dibedakan dari validation errors
- User tidak tahu apakah:
  - Network timeout?
  - Server error?
  - Validation error?
  - Permission denied?

#### **Issue #3**: Toast Z-Index Too Low (Line 797)
```javascript
z-index: 10000;  // ❌ Lower than modal (13000)
```

**Problem**: Sama seperti Bug #1, toast tertutup oleh modal.

### **Affected Scenarios**

| Scenario | Current Behavior | Expected Behavior |
|----------|------------------|-------------------|
| **Ref pointer null** | "Gagal reset" | "Pointer referensi tidak ditemukan" |
| **Wrong source type** | "Gagal reset" | "Hanya ref_modified yang bisa di-reset" |
| **Network timeout** | "Gagal reset" | "Koneksi timeout. Coba lagi." |
| **Permission denied** | "Gagal reset" | "Anda tidak memiliki akses." |
| **Server error 500** | "Gagal reset" | "Server error. Hubungi admin." |

### **Solution Recommendation**

#### **Fix #1: Show Detailed Error Messages**

```javascript
// BEFORE (BROKEN)
.then(js=>{
  if (!js.ok) throw new Error('Gagal reset');  // ❌ Generic!
  // ...
})
.catch(()=> toast('Gagal reset', 'error'));  // ❌ No details!

// AFTER (FIXED)
.then(js=>{
  if (!js.ok) {
    // ✅ Show specific error from server
    const errorMsg = js.errors && js.errors.length > 0
      ? js.errors[0].message
      : 'Gagal reset. Silakan coba lagi.';
    throw new Error(errorMsg);
  }
  // ...
})
.catch((err)=> {
  // ✅ Show error details
  const msg = err.message || 'Gagal reset. Silakan coba lagi.';
  toast(msg, 'error');
  console.error('[RESET ERROR]', err);
});
```

#### **Fix #2: Handle HTTP Errors**

```javascript
// AFTER (COMPLETE FIX)
fetch(url, {
  method:'POST',
  credentials:'same-origin',
  headers:{ 'X-CSRFToken': CSRF }
})
.then(async r => {
  // ✅ Check HTTP status first
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`HTTP ${r.status}: ${text || 'Server error'}`);
  }
  return r.json();
})
.then(js=>{
  if (!js.ok) {
    // ✅ Show specific validation error
    const errorMsg = js.errors && js.errors.length > 0
      ? js.errors.map(e => e.message).join('; ')
      : js.user_message || 'Gagal reset. Silakan coba lagi.';
    throw new Error(errorMsg);
  }

  // ✅ Success: reload data
  return fetch(urlFor(endpoints.get, activeJobId), {credentials:'same-origin'});
})
.then(r => r.json())
.then(js=>{
  rowsByJob[activeJobId] = {
    items: js.items || [],
    kategoriMeta: js.meta?.kategori_opts || [],
    readOnly: !!js.meta?.read_only
  };
  paint(rowsByJob[activeJobId].items);
  setDirty(false);
  setEditorModeBySource();

  // ✅ Show success with details
  const count = js.items?.length || 0;
  toast(`✅ Berhasil reset ${count} item dari referensi`, 'success');
})
.catch((err)=> {
  // ✅ Comprehensive error handling
  console.error('[RESET ERROR]', err);

  let errorMsg = 'Gagal reset. Silakan coba lagi.';

  if (err.message) {
    if (err.message.includes('HTTP 403')) {
      errorMsg = '⛔ Anda tidak memiliki akses untuk reset pekerjaan ini.';
    } else if (err.message.includes('HTTP 404')) {
      errorMsg = '❌ Pekerjaan atau referensi tidak ditemukan.';
    } else if (err.message.includes('HTTP 500')) {
      errorMsg = '⚠️ Server error. Hubungi administrator.';
    } else if (err.message.includes('timeout') || err.message.includes('Failed to fetch')) {
      errorMsg = '⏱️ Koneksi timeout. Periksa internet dan coba lagi.';
    } else {
      errorMsg = err.message;  // Use specific error from server
    }
  }

  toast(errorMsg, 'error');
});
```

#### **Fix #3: Use Global Toast System**

**Replace inline toast z-index (line 797)** with global toast system:

```javascript
// BEFORE (BROKEN - inline toast with wrong z-index)
function toast(msg, type='info') {
  // ... inline implementation with z-index: 10000 ...
}

// AFTER (FIXED - use global toast)
function toast(msg, type='info', delay=3000) {
  // ✅ Use global toast from DP.core.toast (z-index: 13100)
  if (window.DP && window.DP.core && window.DP.core.toast) {
    window.DP.core.toast.show(msg, type, delay);
  } else {
    // Fallback to console
    console.log(`[TOAST ${type.toUpperCase()}] ${msg}`);
  }
}
```

### **Backend Validation (Already Correct)**

**File**: `detail_project/views_api.py` (Lines 1636-1688)

Backend validation is **already good**:

```python
# Line 1651-1652: Check source type
if pkj.source_type != Pekerjaan.SOURCE_REF_MOD:
    return JsonResponse({
        "ok": False,
        "errors": [_err("source_type", "Hanya ref_modified yang bisa di-reset")]
    }, status=400)

# Line 1654-1656: Check ref pointer
ref_obj = getattr(pkj, "ref", None)
if not ref_obj:
    return JsonResponse({
        "ok": False,
        "errors": [_err("ref", "Pointer referensi tidak ditemukan")]
    }, status=400)
```

✅ **Backend is fine** - problem is in **frontend error handling**

### **Impact**

| Impact | Severity |
|--------|----------|
| **User tidak tahu kenapa reset gagal** | 🔴 Critical |
| **Debugging sangat sulit** | 🔴 Critical |
| **Support tickets meningkat** | 🟡 Medium |
| **User frustrasi** | 🟡 Medium |
| **Data bisa corrupted (jika user retry blindly)** | 🟠 High |

---

## 📊 Summary of Fixes

### **Bug #1: Toast Z-Index**

| File | Line | Change | Impact |
|------|------|--------|--------|
| `core.css` | 28 | `--dp-z-toast: 12050` → `13100` | Global fix |
| `toast.js` | 15 | `zIndex = '12050'` → `'13100'` | Global fix |

**Estimated Time**: 5 minutes
**Testing Time**: 10 minutes
**Risk**: 🟢 Low (no breaking changes)

### **Bug #2: Reset Error Handling**

| File | Line | Change | Impact |
|------|------|--------|--------|
| `template_ahsp.js` | 743 | Add detailed error extraction from `js.errors` | Better UX |
| `template_ahsp.js` | 754 | Add error categorization (HTTP status, message) | Better UX |
| `template_ahsp.js` | 740-756 | Add HTTP status checking before JSON parse | Prevent crashes |
| `template_ahsp.js` | 752 | Add success message with item count | Better feedback |
| `template_ahsp.js` | 785-856 | Replace inline toast with global `DP.core.toast` | Consistency |

**Estimated Time**: 30 minutes
**Testing Time**: 20 minutes
**Risk**: 🟢 Low (backward compatible)

---

## 🧪 Testing Checklist

### **Bug #1: Toast Z-Index**

**Manual Tests**:
- [ ] Open Harga Items, save changes
  - [ ] Toast visible without modal
  - [ ] Toast visible with loading modal
- [ ] Open Template AHSP, save changes
  - [ ] Toast visible without modal
  - [ ] Toast visible with modal
- [ ] Test in all browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test dark mode
- [ ] Test with multiple toasts stacking

**Expected**: Toast ALWAYS visible, even with modal open

### **Bug #2: Reset Error Handling**

**Manual Tests**:
- [ ] **Scenario 1**: Reset pekerjaan dengan ref pointer valid
  - **Expected**: Success toast dengan jumlah item
  - **Example**: "✅ Berhasil reset 15 item dari referensi"

- [ ] **Scenario 2**: Reset pekerjaan tanpa ref pointer
  - **Expected**: Error toast dengan detail
  - **Example**: "Pointer referensi tidak ditemukan"

- [ ] **Scenario 3**: Reset pekerjaan dengan source_type = CUSTOM
  - **Expected**: Error toast dengan detail
  - **Example**: "Hanya ref_modified yang bisa di-reset"

- [ ] **Scenario 4**: Network timeout
  - **Expected**: Error toast user-friendly
  - **Example**: "⏱️ Koneksi timeout. Periksa internet dan coba lagi."

- [ ] **Scenario 5**: Server error 500
  - **Expected**: Error toast user-friendly
  - **Example**: "⚠️ Server error. Hubungi administrator."

- [ ] **Scenario 6**: Permission denied (403)
  - **Expected**: Error toast user-friendly
  - **Example**: "⛔ Anda tidak memiliki akses untuk reset pekerjaan ini."

**Browser Console Check**:
- [ ] Error details logged to console for debugging
- [ ] No unhandled promise rejections
- [ ] No console errors

---

## 🚀 Deployment Plan

### **Phase 1: Bug #1 (Toast Z-Index) - URGENT**

**Day 1**:
1. Update `core.css` line 28
2. Update `toast.js` line 15
3. Test manually (all pages)
4. Commit & push
5. Deploy to staging
6. Smoke test
7. Deploy to production (low risk)

**Risk**: 🟢 **Very Low** (CSS-only change)

### **Phase 2: Bug #2 (Reset Error Handling)**

**Day 2**:
1. Update `template_ahsp.js` (lines 733-856)
2. Test all scenarios manually
3. Test in all browsers
4. Commit & push
5. Deploy to staging
6. Full manual testing
7. UAT with 2+ users
8. Deploy to production

**Risk**: 🟡 **Medium** (JS logic change, but backward compatible)

---

## 📝 Code Changes Required

### **File 1**: `detail_project/static/detail_project/css/core.css`

**Line 28**:
```css
/* BEFORE */
--dp-z-toast: 12050;

/* AFTER */
--dp-z-toast: 13100;  /* Above modal for always-visible feedback */
```

### **File 2**: `detail_project/static/detail_project/js/core/toast.js`

**Line 15**:
```javascript
// BEFORE
area.style.zIndex = '12050';

// AFTER
area.style.zIndex = '13100'; // Above modal
```

### **File 3**: `detail_project/static/detail_project/js/template_ahsp.js`

**Replace Lines 733-756** with comprehensive error handling (see detailed code in solution recommendation above).

---

## ✅ Acceptance Criteria

### **Bug #1: Toast Z-Index**

✅ **DONE WHEN**:
1. Toast visible without modal
2. Toast visible WITH modal open
3. Toast visible WITH backdrop
4. All pages work correctly (Harga Items, Template AHSP, List Pekerjaan, Volume, Rekap)
5. No visual regressions
6. Works in all browsers

### **Bug #2: Reset Error Handling**

✅ **DONE WHEN**:
1. Success message shows item count
2. Validation errors show specific message from server
3. HTTP errors show user-friendly categorized messages
4. Network errors show timeout/connection messages
5. All errors logged to console for debugging
6. Toast uses global DP.core.toast system (z-index correct)
7. No unhandled promise rejections

---

## 📞 Rollback Plan

### **If Issues Found After Deployment**

**Bug #1 (Toast Z-Index)**:
```bash
# Immediate rollback (revert CSS)
git revert <commit-hash>
git push origin main
# Redeploy
```

**Bug #2 (Reset Error Handling)**:
```bash
# Rollback JS file
git revert <commit-hash>
git push origin main
# Redeploy
```

**Risk Mitigation**: Both changes are **backward compatible** and **non-breaking**.

---

## 🎯 Conclusion

**Status**: ✅ **ROOT CAUSE IDENTIFIED, SOLUTION DESIGNED**

**Next Steps**:
1. Implement fixes (estimated: 35 minutes)
2. Test thoroughly (estimated: 30 minutes)
3. Deploy to staging
4. Deploy to production

**Priority**: 🔴 **HIGH** - Both bugs affect critical user interactions

**Last Updated**: 2025-11-11
**Investigator**: Claude Code
**Reviewer**: Pending
