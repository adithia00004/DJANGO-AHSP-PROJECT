# List Pekerjaan - Quick Testing Guide

## 🚀 Quick Start (5 Minutes)

### **Method 1: Automated Tests (Console)**

1. Open List Pekerjaan page
2. Press `F12` (open DevTools)
3. Go to **Console** tab
4. Copy-paste content from: `static/detail_project/js/list_pekerjaan_test_helpers.js`
5. Run: `LP_TEST.runAllTests()`
6. Watch console for test results

**Expected Output:**
```
✅ Save button correctly shows clean state.
✅ Row is draggable (draggable="true").
✅ All rows have orderingIndex in dataset.
✅ Bootstrap.Tooltip is available.
✅ Dirty tracking works! Save button is pulsing.
```

---

### **Method 2: Manual Tests (5 Critical Scenarios)**

#### **Test 1: Basic Drag-and-Drop**
1. Hover kolom "No" → See `⋮⋮` icon
2. Drag row to new position
3. Release
4. ✅ **Pass:** Row moves, numbering updates, save button pulses

#### **Test 2: Dirty Tracking**
1. Edit any pekerjaan field
2. Try close tab (Ctrl+W)
3. ✅ **Pass:** Browser shows "Leave site?" warning
4. Click Cancel → Tab stays open

#### **Test 3: Save & Clear Dirty**
1. Make edits (save button pulsing)
2. Click Save
3. ✅ **Pass:** Toast "Perubahan tersimpan", button stops pulsing

#### **Test 4: Cross-Tab Sync**
1. Open 2 tabs (same project)
2. Tab A: Drag row, save
3. Tab B: Wait 1 second
4. ✅ **Pass:** Tab B shows toast + banner "Urutan pekerjaan diubah di tab lain"

#### **Test 5: Cross-Page Impact**
1. List Pekerjaan: Reorder significantly
2. Save
3. Go to **Volume Pekerjaan** page
4. ✅ **Pass:** New order is visible

---

## 📋 Feature Checklist

### ✅ Implemented Features

| Feature | Status | How to Test |
|---------|--------|-------------|
| **Drag-and-drop reordering** | ✅ | Drag kolom No |
| **Visual drag handle** | ✅ | Hover → see `⋮⋮` |
| **Dirty tracking** | ✅ | Edit → Save button pulses |
| **beforeunload warning** | ✅ | Edit → Close tab → Confirm dialog |
| **Clear dirty after save** | ✅ | Save → Button stops pulsing |
| **Cross-tab sync (BroadcastChannel)** | ✅ | 2 tabs → Save in one → Other notified |
| **Tooltip help** | ✅ | Hover info button (ℹ️) |
| **Feature intro banner** | ✅ | Fresh load → Blue banner at top |
| **Sidebar rebuild** | ✅ | Drag → Sidebar updates |
| **Ordering index update** | ✅ | Console: check `row.dataset.orderingIndex` |

---

## 🐛 Known Issues / Limitations

### **Expected Behavior:**
1. **Touch drag (mobile):** May not work - HTML5 drag API limited on touch devices
2. **Safari < 15.4:** No BroadcastChannel → Falls back to 30s polling
3. **Concurrent edits:** No conflict resolution (last save wins)

### **Not a Bug:**
- Ordering is **global per project**, not per-sub
- Moving pekerjaan changes many `ordering_index` values (by design)

---

## 🔧 Troubleshooting

### **Problem: Drag not working**

**Check:**
1. Row has `draggable="true"` attribute
   - Console: `document.querySelector('#klas-list tbody tr').draggable`
   - Expected: `true`

2. Event handlers attached
   - Console: `LP_TEST.testDragHandle()`
   - Expected: "Row is draggable"

### **Problem: Dirty tracking not working**

**Check:**
1. `setDirty` function exists
   - Console: `typeof setDirty`
   - Expected: `"function"`

2. Event listeners attached
   - Make edit → Check console for `[DIRTY] Set to dirty`

3. Save button has class
   - Console: `document.querySelector('#btn-save').classList.contains('btn-neon')`
   - Expected: `true` when dirty

### **Problem: Cross-tab sync not working**

**Check:**
1. BroadcastChannel support
   - Console: `typeof BroadcastChannel`
   - Expected: `"function"` (not "undefined")

2. Same project ID
   - Both tabs must have same `data-project-id`
   - Console: `document.querySelector('#lp-app').dataset.projectId`

3. Channel initialization
   - Console log should show: `[BROADCAST] BroadcastChannel initialized`

### **Problem: Tooltips not showing**

**Check:**
1. Bootstrap loaded
   - Console: `typeof bootstrap`
   - Expected: `"object"`

2. Tooltip instance exists
   - Console: `LP_TEST.testTooltips()`
   - Expected: "Tooltip instance found"

---

## 📊 Test Results Template

```
========================================
TEST SESSION
========================================
Date: _____________
Tester: _____________
Browser: _____________
Project ID: _____________

QUICK TESTS:
[ ] Test 1: Drag-and-drop works
[ ] Test 2: Dirty tracking works
[ ] Test 3: Save clears dirty
[ ] Test 4: Cross-tab sync works
[ ] Test 5: Cross-page impact verified

AUTOMATED TESTS:
[ ] LP_TEST.runAllTests() - All passed
[ ] Console errors: None

ISSUES FOUND:
1. _____________
2. _____________

OVERALL: [ ] PASS [ ] FAIL
========================================
```

---

## 🎯 Critical Path Test (2 Minutes)

**Fastest way to verify all features work:**

```javascript
// 1. Open Console, run automated tests
LP_TEST.runAllTests()

// 2. Manual drag-drop
// (Drag row 1 to row 3)

// 3. Check dirty state
LP_TEST.testSaveButton()
// Expected: "Save button correctly shows dirty state (pulsing)"

// 4. Open second tab (same project)

// 5. First tab: Click Save

// 6. Second tab: Check for toast/banner
// Expected: "⚠️ Urutan pekerjaan diubah di tab lain..."

// 7. Second tab: Click "Refresh Sekarang"
// Expected: New order visible

// ✅ ALL FEATURES WORKING!
```

---

## 📞 Support

**If tests fail:**
1. Check browser console for errors
2. Verify file modifications were saved
3. Hard refresh (Ctrl+Shift+R)
4. Clear cache and retry
5. Check `LIST_PEKERJAAN_TEST_CHECKLIST.md` for detailed steps

**Debug Mode:**
1. Open `list_pekerjaan.js`
2. Change line 18: `const __DEBUG__ = true;`
3. Reload page
4. Console will show detailed logs: `[LP] [DRAG] [DIRTY] [BROADCAST]`

---

## 🎓 Understanding the System

### **Dirty Tracking Flow:**
```
User Input → setDirty(true) → Save button pulses + FAB appears
    ↓
Click Save → handleSave() → Success → setDirty(false)
    ↓
Save button stops pulsing + FAB hides
```

### **Cross-Tab Sync Flow:**
```
Tab A: Save → broadcastOrderingChange()
    ↓
BroadcastChannel: Send message {type: 'ordering_changed', projectId}
    ↓
Tab B: bc.onmessage → Show toast + banner
    ↓
User clicks "Refresh Sekarang" → location.reload()
```

### **Drag-Drop Flow:**
```
dragstart → Add 'lp-row-dragging' class
    ↓
dragover → Highlight tbody (blue outline)
    ↓
drop → Move row + Renumber + Update ordering + setDirty(true)
    ↓
dragend → Clean up visual states
```

---

## ✅ Success Criteria

**All features pass if:**
1. ✅ Drag-and-drop moves rows correctly
2. ✅ Dirty state prevents accidental data loss
3. ✅ Save clears dirty and broadcasts to other tabs
4. ✅ Other tabs receive real-time notifications (<1s)
5. ✅ Cross-page ordering is consistent (Volume, Rekap RAB, etc.)
6. ✅ No console errors during normal usage
7. ✅ Tooltips provide helpful guidance

**Ready for Production:** All 7 criteria met ✅
