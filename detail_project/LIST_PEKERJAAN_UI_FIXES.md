# List Pekerjaan - UI Fixes

**Tanggal:** 2025-11-07
**Status:** READY TO IMPLEMENT

---

## 🎯 Issues Ditemukan

### Issue 1: Z-Index Select2 Dropdown
**Severity:** Low (edge case)
**Location:** `list_pekerjaan.css:611-633`

**Problem:** Select2 dropdown mungkin tertutup oleh card stacking context

### Issue 2: Button Toolbar Inconsistency
**Severity:** HIGH
**Location:** `list_pekerjaan.css:63-76`

**Problem:** Button toolbar tidak memiliki tinggi yang seragam

---

## ✅ FIXES

### Fix 1: Ensure Select2 Dropdown Z-Index

**File:** `detail_project/static/detail_project/css/list_pekerjaan.css`
**Location:** After line 633

```css
/* ===== FIX: Select2 Dropdown Z-Index ===== */
/* Pastikan dropdown keluar dari card stacking context */
.list-pekerjaan .select2-container--open {
  position: relative;
  z-index: var(--dp-z-dropdown) !important;
}

/* Pastikan dropdown selalu terlihat */
.list-pekerjaan .select2-dropdown {
  z-index: var(--dp-z-dropdown) !important;
}
```

---

### Fix 2: Standardize Toolbar Button Sizing

**File:** `detail_project/static/detail_project/css/list_pekerjaan.css`
**Location:** Replace lines 63-76

**BEFORE:**
```css
/* Font default kontrol interaktif (kompak) */
#lp-app .form-control,
#lp-app .form-select,
#lp-app .input-group-text,
#lp-app .btn.lp-btn{
  font-size: var(--ux-font-xs);
  transition: all var(--ux-duration-200) var(--ux-ease);
}

/* Tombol aksi cepat - DIPERBAIKI UNTUK PROPORSI */
#btn-add-klas{
  white-space: nowrap;
  font-size: var(--ux-font-xs);
  line-height: 1.5;
  padding: .375rem .75rem;
  border-radius: var(--dp-radius-md);
  box-shadow: var(--dp-shadow-sm);
}
```

**AFTER:**
```css
/* Font default kontrol interaktif (kompak) */
#lp-app .form-control,
#lp-app .form-select,
#lp-app .input-group-text {
  font-size: var(--ux-font-xs);
  transition: all var(--ux-duration-200) var(--ux-ease);
}

/* ===== STANDARDIZE ALL TOOLBAR BUTTONS ===== */
#lp-app .btn.lp-btn {
  font-size: var(--ux-font-xs);
  line-height: 1.5;
  padding: var(--lp-toolbar-py) .75rem;  /* Use toolbar padding variable */
  border-radius: var(--dp-radius-md);
  white-space: nowrap;
  transition: all var(--ux-duration-200) var(--ux-ease);

  /* Ensure consistent height */
  min-height: calc(1.5em + (var(--lp-toolbar-py) * 2) + 2px);  /* line-height + padding + border */
}

/* Specific button overrides (if needed) */
#btn-add-klas,
#btn-save,
#btn-compact {
  /* Inherit dari .lp-btn - tidak perlu override */
}

/* Ensure search button matches input height */
#lp-toolbar-find {
  padding: var(--lp-toolbar-py) .75rem !important;
  line-height: 1.5 !important;
  min-height: calc(1.5em + (var(--lp-toolbar-py) * 2) + 2px);
}
```

---

### Fix 3: Ensure Input Group Consistency

**File:** `detail_project/static/detail_project/css/list_pekerjaan.css`
**Location:** Update lines 31-38

**AFTER:**
```css
/* Toolbar search input & buttons - STANDARDIZED HEIGHT */
#lp-app .lp-toolbar-search .form-control,
#lp-app .lp-toolbar-search .input-group-text,
#lp-toolbar-find {
  font-size: var(--lp-toolbar-fs) !important;
  line-height: 1.5 !important;
  padding-top: var(--lp-toolbar-py) !important;
  padding-bottom: var(--lp-toolbar-py) !important;
  transition: all var(--ux-duration-200) var(--ux-ease);

  /* Ensure pixel-perfect alignment */
  height: calc(1.5em + (var(--lp-toolbar-py) * 2) + 2px);
  display: flex;
  align-items: center;
}
```

---

## 📊 Expected Results

### Before:
- ❌ Button toolbar memiliki tinggi berbeda-beda
- ❌ Search input tidak align dengan button
- ❌ Select2 dropdown mungkin tertutup card

### After:
- ✅ Semua button toolbar tinggi seragam: `calc(1.5em + .75rem + 2px) ≈ 34px`
- ✅ Search input & button perfectly aligned
- ✅ Select2 dropdown selalu muncul di atas card
- ✅ Konsisten dengan design system

---

## 🧪 Testing Checklist

- [ ] Test toolbar pada berbagai screen sizes
- [ ] Verify button heights dengan DevTools
- [ ] Test Select2 dropdown pada card pertama vs terakhir
- [ ] Test hover states semua button
- [ ] Test search input focus state alignment
- [ ] Test dark mode compatibility
- [ ] Test dengan browser berbeda (Chrome, Firefox, Safari)

---

## 📝 Variable Reference

Dari `core.css`:
```css
--lp-toolbar-h: 40px;
--lp-toolbar-fs: .75rem;
--lp-toolbar-py: .375rem;
--ux-font-xs: .75rem;
--dp-radius-md: .5rem;
--dp-z-dropdown: 12040;
```

Expected button height calculation:
```
height = line-height + (padding-top + padding-bottom) + (border-top + border-bottom)
       = 1.5em + (.375rem * 2) + 2px
       = 1.125rem + .75rem + 2px
       = 1.875rem + 2px
       ≈ 32px
```

---

**Created by:** Claude AI
**Ready for:** Implementation
