# List Pekerjaan - Manual Test Checklist

## 📋 Overview
Test suite untuk fitur drag-and-drop, dirty tracking, dan cross-tab sync pada halaman List Pekerjaan.

**Test Environment:**
- Browser: Chrome/Firefox/Safari/Edge
- Project ID: _____
- Tester: _____
- Date: _____

---

## ✅ P0: Dirty Tracking System

### Test 1.1: Mark Dirty on User Input
**Steps:**
1. Open List Pekerjaan page
2. Edit uraian pekerjaan (type any text)
3. Observe save button

**Expected:**
- [ ] Save button gets pulsing effect (btn-neon class)
- [ ] FAB button appears at bottom-right
- [ ] Console log: `[DIRTY] Set to dirty`

**Actual Result:** _______________

---

### Test 1.2: beforeunload Warning
**Steps:**
1. Make any edit (trigger dirty state)
2. Try to close tab (Ctrl+W or click X)

**Expected:**
- [ ] Browser shows "Leave site?" confirmation dialog
- [ ] Message: "Anda memiliki perubahan yang belum disimpan. Yakin ingin keluar?"
- [ ] Click "Cancel" → Tab stays open
- [ ] Click "Leave" → Tab closes (data lost)

**Actual Result:** _______________

---

### Test 1.3: Clear Dirty After Save
**Steps:**
1. Make any edit
2. Click Save button
3. Wait for success toast
4. Observe save button

**Expected:**
- [ ] Toast: "Perubahan tersimpan"
- [ ] Save button stops pulsing (btn-neon removed)
- [ ] FAB button hides
- [ ] Console log: `[DIRTY] Cleared`
- [ ] Try to close tab → No warning

**Actual Result:** _______________

---

### Test 1.4: Dirty Tracking on All Actions
**Test each action individually:**

| Action | Triggers Dirty? | Notes |
|--------|----------------|-------|
| Edit uraian pekerjaan | [ ] Yes | |
| Change source type (ref/custom) | [ ] Yes | |
| Select referensi AHSP | [ ] Yes | |
| Edit satuan | [ ] Yes | |
| Edit nama klasifikasi | [ ] Yes | |
| Edit nama sub | [ ] Yes | |
| Delete pekerjaan row | [ ] Yes | |
| Delete sub | [ ] Yes | |
| Delete klasifikasi | [ ] Yes | |
| **Drag-and-drop row** | [ ] Yes | **NEW** |

**Actual Results:** _______________

---

## 🔄 P1: Cross-Tab Sync (BroadcastChannel)

### Test 2.1: Real-Time Notification
**Setup:** Open 2 tabs with same project

**Steps (Tab A):**
1. Drag-and-drop a pekerjaan row
2. Click Save
3. Wait for success

**Steps (Tab B):**
1. Observe for notifications

**Expected (Tab B):**
- [ ] Toast appears: "⚠️ Urutan pekerjaan diubah di tab lain..."
- [ ] Alert banner appears with "Refresh Sekarang" button
- [ ] Console log: `[BROADCAST] Received ordering_changed from other tab`
- [ ] Banner auto-dismisses after 30 seconds

**Actual Result:** _______________

---

### Test 2.2: Refresh After Cross-Tab Change
**Continuation of Test 2.1:**

**Steps (Tab B):**
1. Click "Refresh Sekarang" button in banner

**Expected:**
- [ ] Page reloads
- [ ] New ordering is visible
- [ ] Scroll position preserved (if applicable)

**Actual Result:** _______________

---

### Test 2.3: Different Project - No Notification
**Setup:**
- Tab A: Project X
- Tab B: Project Y (different project)

**Steps:**
1. Tab A: Drag-and-drop, save
2. Tab B: Observe

**Expected (Tab B):**
- [ ] NO notification (different project)
- [ ] Console log: No broadcast message

**Actual Result:** _______________

---

### Test 2.4: Browser Without BroadcastChannel
**Setup:** Test in Safari < 15.4 or use browser developer tools to disable

**Steps:**
1. Open DevTools Console
2. Type: `delete window.BroadcastChannel`
3. Reload page
4. Make changes, save

**Expected:**
- [ ] Console log: `[BROADCAST] BroadcastChannel not supported in this browser`
- [ ] Fallback to 30s polling (existing sync indicator)
- [ ] No errors, graceful degradation

**Actual Result:** _______________

---

## 🎨 Drag-and-Drop Functionality

### Test 3.1: Visual Drag Handle
**Steps:**
1. Hover mouse over kolom "No" of any pekerjaan row

**Expected:**
- [ ] Icon `⋮⋮` appears (opacity 0.3 default, 0.6 on hover)
- [ ] Cursor changes to `grab`
- [ ] CSS class: `cursor: move`

**Actual Result:** _______________

---

### Test 3.2: Drag Within Same Sub
**Steps:**
1. Click and hold on a pekerjaan row (kolom No)
2. Drag upward/downward within same sub
3. Observe visual feedback
4. Drop at new position

**Expected:**
- [ ] Row becomes semi-transparent (opacity 0.5)
- [ ] Row has class `lp-row-dragging`
- [ ] Cursor changes to `grabbing`
- [ ] Drop zone (tbody) gets blue highlight
- [ ] On drop: Row moves to new position
- [ ] Numbering auto-updates (1, 2, 3...)
- [ ] Toast: "Urutan pekerjaan diubah"
- [ ] Dirty state triggered (save button pulsing)

**Actual Result:** _______________

---

### Test 3.3: Drag Across Sub
**Steps:**
1. Drag pekerjaan from Sub A
2. Hover over Sub B tbody
3. Drop

**Expected:**
- [ ] Sub B tbody highlights blue (dragover)
- [ ] On drop: Row moves from Sub A to Sub B
- [ ] Both Sub A and Sub B renumber correctly
- [ ] Toast: "Pekerjaan dipindahkan ke sub/klasifikasi lain"
- [ ] Sidebar navigation updates (rebuild)
- [ ] Console log: `[DROP] Complete - moved pekerjaan`

**Actual Result:** _______________

---

### Test 3.4: Drag Across Klasifikasi
**Steps:**
1. Drag pekerjaan from Klas 1 → Sub A
2. Drop to Klas 2 → Sub B

**Expected:**
- [ ] Row successfully moves
- [ ] Both klasifikasi renumber independently
- [ ] Toast notification
- [ ] Dirty state triggered

**Actual Result:** _______________

---

### Test 3.5: Drop Position Precision
**Steps:**
1. Sub has 5 rows (numbered 1-5)
2. Drag row #1
3. Drop between row #3 and #4

**Expected:**
- [ ] Row #1 inserts BEFORE row #3 (becomes new #3)
- [ ] Final order: 2, 3, 1, 4, 5 → renumbers to 1, 2, 3, 4, 5
- [ ] Drop position based on mouse Y-coordinate vs row middle

**Actual Result:** _______________

---

### Test 3.6: Drag and Cancel (ESC key)
**Steps:**
1. Start dragging a row
2. Press ESC key or drag outside drop zone
3. Observe

**Expected:**
- [ ] Row returns to original position
- [ ] Visual states cleared (opacity restored)
- [ ] No dirty state triggered
- [ ] Console log: `[DRAG] End`

**Actual Result:** _______________

---

## 💡 P2: User Education & Tooltips

### Test 4.1: Info Tooltip Button
**Steps:**
1. Locate info button (ℹ️) in toolbar (right side)
2. Hover mouse over button

**Expected:**
- [ ] Tooltip appears with title "💡 Drag & Drop"
- [ ] Lists affected pages:
  - Volume Pekerjaan
  - Rekap RAB
  - Rincian AHSP
  - Jadwal/Gantt Chart
  - Export PDF/Word/CSV
- [ ] Tooltip positioning: bottom
- [ ] HTML formatting works (bullets, bold)

**Actual Result:** _______________

---

### Test 4.2: Feature Introduction Banner
**Steps:**
1. Fresh page load (or clear localStorage)
2. Observe top of page

**Expected:**
- [ ] Blue info banner appears below toolbar
- [ ] Icon: 💡 (lightbulb)
- [ ] Text: "Fitur Drag & Drop Aktif"
- [ ] Mentions kolom nomor badge `⋮⋮`
- [ ] Close button (X) works
- [ ] Banner dismissal persists on refresh

**Actual Result:** _______________

---

### Test 4.3: Bootstrap Tooltips Initialization
**Steps:**
1. Open DevTools Console
2. Check for initialization log

**Expected:**
- [ ] Console log: `[TOOLTIP] Bootstrap tooltips initialized`
- [ ] If Bootstrap not available: `[TOOLTIP] Bootstrap not available - tooltips disabled`
- [ ] No JavaScript errors

**Actual Result:** _______________

---

## 🔗 Integration Tests

### Test 5.1: Drag → Save → Broadcast Flow
**Setup:** 2 tabs, same project

**Steps:**
1. Tab A: Drag row #3 to position #1
2. Tab A: Click Save
3. Observe both tabs

**Expected:**
- [ ] **Tab A:**
  - Toast: "Perubahan tersimpan"
  - Dirty cleared
  - Ordering updated in DOM
  - Console: `[BROADCAST] Sent ordering_changed notification`

- [ ] **Tab B:**
  - Toast: "⚠️ Urutan pekerjaan diubah di tab lain..."
  - Banner with refresh button
  - Click refresh → sees new order

**Actual Result:** _______________

---

### Test 5.2: Multiple Drags Before Save
**Steps:**
1. Drag row A to position 1
2. Drag row B to position 2
3. Drag row C to position 3
4. Click Save ONCE

**Expected:**
- [ ] All 3 changes persist
- [ ] Only 1 save request to server
- [ ] Final ordering correct: A, B, C, (rest...)
- [ ] Only 1 broadcast message sent

**Actual Result:** _______________

---

### Test 5.3: Sidebar Navigation Sync
**Steps:**
1. Open sidebar (Navigasi button)
2. Drag-and-drop a pekerjaan
3. Observe sidebar tree

**Expected:**
- [ ] Sidebar auto-rebuilds after drop
- [ ] Pekerjaan appears in new location in tree
- [ ] Tree structure correct (Klas > Sub > Pekerjaan)
- [ ] Console log: `scheduleSidebarRebuild()` called

**Actual Result:** _______________

---

### Test 5.4: Ordering Index Updates
**Steps:**
1. Inspect row dataset before drag: `row.dataset.orderingIndex`
2. Drag row to new position
3. Inspect dataset after drop

**Expected:**
- [ ] `dataset.orderingIndex` updates to new sequential value
- [ ] Global ordering maintained (not per-sub)
- [ ] Example: Klas A rows: 1,2,3; Klas B rows: 4,5,6

**Actual Result:** _______________

---

## 🚨 Error Handling & Edge Cases

### Test 6.1: Save Conflict Detection
**Setup:** Simulate concurrent edit

**Steps:**
1. Tab A: Load data
2. Backend: Manually change ordering_index in database
3. Tab A: Make edit, click Save

**Expected:**
- [ ] No conflict (List Pekerjaan doesn't use optimistic locking like Template AHSP)
- [ ] Save succeeds with new ordering
- [ ] Server unique constraint prevents corruption

**Actual Result:** _______________

---

### Test 6.2: Network Error During Save
**Steps:**
1. Open DevTools Network tab
2. Set to "Offline" mode
3. Drag row, click Save

**Expected:**
- [ ] Toast: Error message about network
- [ ] Dirty state remains (save button still pulsing)
- [ ] User can retry after going online
- [ ] No data loss

**Actual Result:** _______________

---

### Test 6.3: Empty Sub - Drag Into
**Steps:**
1. Create empty Sub (no pekerjaan rows)
2. Drag pekerjaan from another sub
3. Drop into empty sub tbody

**Expected:**
- [ ] Row successfully adds to empty sub
- [ ] Becomes row #1 in that sub
- [ ] No JavaScript errors

**Actual Result:** _______________

---

### Test 6.4: Rapid Drag Operations
**Steps:**
1. Quickly drag 5 different rows in succession
2. Don't wait for animations to complete
3. Observe behavior

**Expected:**
- [ ] All drags process correctly
- [ ] No visual glitches
- [ ] Final ordering correct
- [ ] No duplicate rows or lost rows

**Actual Result:** _______________

---

## 📊 Cross-Page Impact Verification

### Test 7.1: Volume Pekerjaan Page
**Steps:**
1. List Pekerjaan: Change order, save
2. Navigate to Volume Pekerjaan page

**Expected:**
- [ ] Pekerjaan appear in new order
- [ ] Hierarchical display correct
- [ ] No broken references

**Actual Result:** _______________

---

### Test 7.2: Rekap RAB Page
**Steps:**
1. List Pekerjaan: Reorder, save
2. Navigate to Rekap RAB

**Expected:**
- [ ] Tree structure shows new order
- [ ] Calculations still correct (order doesn't affect totals)
- [ ] Export reflects new order

**Actual Result:** _______________

---

### Test 7.3: Export PDF/Word/CSV
**Steps:**
1. List Pekerjaan: Reorder pekerjaan significantly
2. Save changes
3. Volume Pekerjaan: Export to PDF

**Expected:**
- [ ] PDF shows new ordering
- [ ] Numbering sequential and correct
- [ ] No missing or duplicate entries

**Actual Result:** _______________

---

## 🌐 Browser Compatibility

| Browser | Version | Drag-Drop | Dirty Track | BroadcastChannel | Tooltip | Pass/Fail |
|---------|---------|-----------|-------------|------------------|---------|-----------|
| Chrome  | 120+    | [ ]       | [ ]         | [ ]              | [ ]     | [ ]       |
| Firefox | 121+    | [ ]       | [ ]         | [ ]              | [ ]     | [ ]       |
| Safari  | 17+     | [ ]       | [ ]         | [ ]              | [ ]     | [ ]       |
| Edge    | 120+    | [ ]       | [ ]         | [ ]              | [ ]     | [ ]       |

**Known Limitations:**
- Safari < 15.4: No BroadcastChannel (falls back to polling)
- Mobile: Touch drag may need testing

---

## 📱 Mobile/Tablet Testing

### Test 8.1: Touch Drag-and-Drop
**Device:** ___________ (iOS/Android)

**Steps:**
1. Long-press on pekerjaan row
2. Drag to new position
3. Release

**Expected:**
- [ ] Touch drag works (HTML5 drag API)
- [ ] Visual feedback appears
- [ ] Drop works correctly
- [ ] OR: Touch drag not supported, needs implementation

**Actual Result:** _______________

---

## 🔍 Performance & Console Checks

### Test 9.1: Console Errors
**Steps:**
1. Perform all drag-drop operations
2. Monitor DevTools Console

**Expected:**
- [ ] No JavaScript errors
- [ ] No network errors (except intentional tests)
- [ ] Debug logs appear when `__DEBUG__ = true`

**Actual Result:** _______________

---

### Test 9.2: Memory Leaks
**Steps:**
1. Perform 20 drag-drop operations
2. Monitor DevTools Memory tab

**Expected:**
- [ ] No significant memory growth
- [ ] Event listeners properly cleaned up
- [ ] No detached DOM nodes accumulating

**Actual Result:** _______________

---

## ✅ Final Sign-Off

**Test Summary:**
- Total Tests: _____ / _____
- Passed: _____
- Failed: _____
- Blocked: _____

**Critical Issues Found:**
1. _______________
2. _______________

**Recommendations:**
_______________

**Tester Signature:** _______________
**Date:** _______________
**Status:** [ ] APPROVED [ ] NEEDS FIXES [ ] BLOCKED
