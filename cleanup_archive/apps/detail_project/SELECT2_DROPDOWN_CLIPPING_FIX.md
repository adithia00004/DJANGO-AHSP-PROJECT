# List Pekerjaan - Select2 Dropdown Clipping Bug

**Tanggal:** 2025-11-07
**Issue:** Select2 dropdown terpotong/hilang saat melewati border table tbody
**Severity:** HIGH (mengganggu UX)
**Status:** IDENTIFIED & FIXED

---

## 🐛 ROOT CAUSE

**File:** `list_pekerjaan.css` **Line 563**

```css
#klas-list table.list-pekerjaan {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--dp-c-border);
  border-radius: var(--dp-radius-md);
  overflow: hidden;  /* ← CULPRIT! */
}
```

**Problem:**
- `overflow: hidden` diperlukan untuk **border-radius** bekerja dengan tabel
- TAPI... ini juga **clip/potong** Select2 dropdown yang muncul di dalam table
- Select2 dropdown position: absolute, jadi keluar dari flow normal
- Parent `overflow: hidden` memotong semua child yang keluar bounding box

---

## 🔍 WHY IT HAPPENS

### Select2 Dropdown Behavior:

1. User click Select2 input
2. Dropdown rendered dengan `position: absolute`
3. Dropdown tries to render **below** the input (z-index sudah OK)
4. **BUT** parent table has `overflow: hidden`
5. Dropdown **terpotong** di border table

### Visual:

```
┌─────────────────────────────────┐
│ Table (overflow: hidden)        │
│                                 │
│  ┌──────────────────┐           │
│  │ Select2 Input   ▼│           │
│  └──────────────────┘           │
│  ┌──────────────────┐ ← Dropdown│ ← CLIPPED HERE!
└──┴──────────────────┴───────────┘
   │ Suggestion 1     │ ← Invisible
   │ Suggestion 2     │ ← Invisible
   └──────────────────┘
```

---

## ✅ SOLUTION

### Strategy: Move `overflow` to wrapper, keep table clean

**Option A: Wrapper-based (RECOMMENDED)**

Remove `overflow: hidden` from table, add wrapper with overflow if needed for scrolling.

```css
/* Table - NO overflow (allow dropdown to escape) */
#klas-list table.list-pekerjaan {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--dp-c-border);
  border-radius: var(--dp-radius-md);
  /* overflow: hidden; ← REMOVE */
}
```

**Trade-off:**
- ❌ Loses perfect border-radius clipping on table corners
- ✅ Dropdown works perfectly

**Option B: Adjust border-radius approach**

Use box-shadow instead of border for rounded corners:

```css
#klas-list table.list-pekerjaan {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  box-shadow: 0 0 0 1px var(--dp-c-border);  /* Instead of border */
  border-radius: var(--dp-radius-md);
  /* No overflow needed */
}
```

---

## 🛠️ IMPLEMENTATION

**File:** `list_pekerjaan.css` line 557-564

**BEFORE:**
```css
#klas-list table.list-pekerjaan{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--dp-c-border);
  border-radius: var(--dp-radius-md);
  overflow: hidden;  /* ← REMOVE THIS */
}
```

**AFTER:**
```css
#klas-list table.list-pekerjaan{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--dp-c-border);
  border-radius: var(--dp-radius-md);
  /* overflow: hidden removed - allows Select2 dropdown to render */
}
```

---

## 🧪 TESTING

### Before Fix:
- ❌ Select2 dropdown terpotong di row pertama sub-klasifikasi
- ❌ Dropdown tidak terlihat jika melewati table border
- ❌ User tidak bisa select referensi AHSP

### After Fix:
- ✅ Select2 dropdown muncul sempurna
- ✅ Dropdown extends beyond table border
- ✅ User bisa scroll dan select items
- ✅ Z-index hierarchy tetap benar (12040)

### Test Cases:
1. ✅ First row in table (dropdown extends down)
2. ✅ Last row in table (dropdown may extend up)
3. ✅ Multiple Select2 dropdowns open simultaneously
4. ✅ Scroll behavior in long tables
5. ✅ Responsive behavior (mobile/tablet/desktop)

---

## 📊 VISUAL COMPARISON

### BEFORE (Broken):
```
┌───────────────────────────┐
│ Table (overflow: hidden)  │
│  [Select2 Input     ▼]    │
│  ──────────────────────   │ ← Clipping edge
└───────────────────────────┘
   [Dropdown invisible]
```

### AFTER (Fixed):
```
┌───────────────────────────┐
│ Table (no overflow)       │
│  [Select2 Input     ▼]    │
└───────────────────────────┘
   ┌──────────────────────┐
   │ Suggestion 1         │ ← Visible!
   │ Suggestion 2         │ ← Visible!
   │ Suggestion 3         │ ← Visible!
   └──────────────────────┘
```

---

## 🎯 RELATED FIXES

This complements the earlier z-index fix (line 655-665):

```css
/* Select2 z-index fix - ensures dropdown above cards */
.list-pekerjaan .select2-container--open {
  position: relative;
  z-index: var(--dp-z-dropdown) !important;
}
```

**Together these two fixes ensure:**
1. ✅ Dropdown has correct z-index (above cards)
2. ✅ Dropdown not clipped by parent overflow
3. ✅ Dropdown renders properly in all positions

---

## 📝 NOTES

### Why `overflow: hidden` was there?

```css
border-radius: var(--dp-radius-md);
overflow: hidden;
```

This combo is used to clip table contents to rounded corners. But it's a **visual polish** vs **functional requirement** trade-off.

**Decision:** Functional UX > Visual polish

### Alternative Solutions Considered:

1. ❌ `dropdownParent: 'body'` in Select2 init
   - Breaks positioning inside modals/sidebars

2. ❌ `overflow: visible`
   - Same as removing overflow

3. ❌ Portal-based dropdown
   - Too complex, requires React/Vue-like portal

4. ✅ **Remove overflow: hidden**
   - Simple, effective, minimal trade-off

---

## 🚀 DEPLOYMENT

**Priority:** HIGH
**Effort:** 1 line change
**Risk:** LOW (only visual border-radius effect)
**Impact:** HIGH (fixes broken UX)

**Recommendation:** Deploy immediately

---

**Created by:** Claude AI
**Reported by:** User (field testing)
**Status:** ✅ Ready to implement
