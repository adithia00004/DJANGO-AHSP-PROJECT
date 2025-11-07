# List Pekerjaan - Comprehensive Dropdown Clipping Analysis

**Tanggal:** 2025-11-07
**Issue:** Select2 dropdown still clipped by `.card-body.sub-wrap`
**Status:** INVESTIGATING

---

## 🔍 DOM STRUCTURE ANALYSIS

Based on JS line 498 (`list_pekerjaan.js`):

```html
<div class="card">
  <div class="card-header">
    <input class="klas-name" />
    <button class="btn-add-sub">Sub-Klasifikasi</button>
  </div>

  <div class="card-body vstack gap-2 sub-wrap">
    <!-- Sub-klasifikasi container -->
    <div class="sub-card">
      <table class="list-pekerjaan">
        <tbody>
          <tr>
            <td class="col-ref">
              <div class="select2-host">
                <select class="ref-select">...</select>
                <!-- DROPDOWN RENDERS HERE (position: absolute) -->
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
```

---

## 🐛 CLIPPING HIERARCHY

### Potential Culprits:

1. ✅ **Table** (`overflow: hidden`) - **FIXED** ✓
2. ⚠️ **`.card-body`** (line 528-531)
3. ⚠️ **`.card`** (line 506-512)
4. ⚠️ **`.sub-wrap > div`** (line 547-554)
5. ⚠️ **Bootstrap `.vstack`** (implicit)

---

## 📋 CSS ANALYSIS

### Current CSS (list_pekerjaan.css):

#### 1. `.card-body` (line 528-531):
```css
#klas-list .card-body {
  padding: 1rem;
  background: var(--dp-c-bg);
  /* NO overflow property ✓ */
}
```
**Status:** ✅ Safe

#### 2. `.card` (line 506-512):
```css
#klas-list .card {
  border: 2px solid var(--dp-c-border);
  border-radius: var(--dp-radius-lg);
  box-shadow: var(--dp-shadow-sm);
  transition: all var(--ux-duration-200) var(--ux-ease);
  margin-bottom: 1rem;
  /* NO overflow property ✓ */
}
```
**Status:** ✅ Safe

#### 3. `.sub-wrap > div` (line 547-554):
```css
#klas-list .sub-wrap > div {
  background: var(--dp-c-surface-1);
  border: 1px solid var(--dp-c-border);
  border-radius: var(--dp-radius-md);
  padding: .75rem;
  margin-bottom: .75rem;
  box-shadow: var(--dp-shadow-sm);
  /* NO overflow property ✓ */
}
```
**Status:** ✅ Safe

#### 4. `.sub-wrap` scrollbar (line 461-498):
```css
#lp-app .sub-wrap {
  scrollbar-gutter: stable both-edges;
  /* Only scrollbar styling, NO overflow ✓ */
}
```
**Status:** ✅ Safe

---

## 🤔 WHY STILL CLIPPING?

### Possible Causes:

#### A. **Bootstrap `.vstack` default behavior**

Bootstrap's `.vstack` is:
```css
.vstack {
  display: flex;
  flex-direction: column;
  /* NO overflow by default */
}
```

**Status:** ✅ Should be safe

#### B. **Parent Container with Hidden Overflow**

Check if parent of `.card` has overflow:
- `#klas-list`
- `.lp-main`
- `#lp-app`

#### C. **Transform/Contain Properties**

CSS properties that create stacking context can clip:
- `transform`
- `contain: layout`
- `will-change`

---

## 🛠️ COMPREHENSIVE FIX

### Strategy: Add explicit `overflow: visible` cascade

```css
/* Ensure no parent clips Select2 dropdown */
#klas-list .card,
#klas-list .card-body,
#klas-list .sub-wrap,
#klas-list .sub-wrap > div {
  overflow: visible !important;
}

/* Special case: table container */
#klas-list .sub-wrap > div {
  position: relative; /* Establish positioning context */
}
```

---

## ⚠️ RISKS OF FIXES

### Risk #1: Removing `overflow: hidden` from Table
**What we did:**
```css
#klas-list table.list-pekerjaan {
  /* overflow: hidden removed */
}
```

**Risks:**
- ❌ Border-radius may not clip table corners perfectly
- ❌ Content might overflow table visually (minor)

**Mitigation:**
- Table has `border-radius` on outer border
- Modern browsers handle this reasonably
- Visual impact is minimal

**Verdict:** ✅ **Acceptable trade-off**

---

### Risk #2: Adding `overflow: visible !important`
**What we might do:**
```css
.card-body { overflow: visible !important; }
```

**Risks:**
- ⚠️ May break intentional overflow hiding elsewhere
- ⚠️ Could expose content that should be hidden
- ⚠️ `!important` makes future overrides harder

**Mitigation:**
- Scope specifically to Select2 containers
- Use specific selectors
- Test all card types

**Verdict:** ⚠️ **Use with caution, scope carefully**

---

### Risk #3: Changing Stacking Context
**What happens:**
```css
.select2-container {
  z-index: 12040;
  position: relative; /* Creates stacking context */
}
```

**Risks:**
- ⚠️ May affect other dropdowns on page
- ⚠️ Could interfere with modals/overlays
- ⚠️ Z-index wars with other components

**Mitigation:**
- Already using proper z-index hierarchy
- Tested in previous fix
- Isolated to `.list-pekerjaan` scope

**Verdict:** ✅ **Safe (already implemented)**

---

## 🧪 DEBUGGING STEPS

### Step 1: Identify Actual Clipper

Open DevTools and:

1. Inspect Select2 dropdown element
2. Check computed style for `overflow` on all parents:
   ```
   .select2-dropdown
   └─ .select2-container
      └─ .select2-host
         └─ td.col-ref
            └─ tr
               └─ tbody
                  └─ table.list-pekerjaan ← FIXED ✓
                     └─ (sub-wrap > div)
                        └─ .sub-wrap ← CHECK THIS
                           └─ .card-body ← CHECK THIS
                              └─ .card ← CHECK THIS
                                 └─ #klas-list
   ```

3. Look for:
   - `overflow: hidden`
   - `overflow: auto`
   - `overflow: scroll`
   - `contain: layout`
   - `transform: ...`

### Step 2: Test Each Level

Add to browser console:
```javascript
// Find all parents with overflow
const dropdown = document.querySelector('.select2-dropdown');
let el = dropdown?.parentElement;
while (el) {
  const style = window.getComputedStyle(el);
  if (style.overflow !== 'visible') {
    console.log('CLIPPER FOUND:', el.className, 'overflow:', style.overflow);
  }
  el = el.parentElement;
}
```

---

## ✅ RECOMMENDED FIX

Based on analysis, apply targeted fix:

```css
/* FIX: Ensure dropdown container hierarchy allows overflow */

/* Card and card-body must allow overflow */
#klas-list .card,
#klas-list .card-body {
  overflow: visible;
}

/* Sub-wrap container must allow overflow */
#klas-list .sub-wrap {
  overflow: visible;
}

/* Sub-wrap child divs must allow overflow */
#klas-list .sub-wrap > div {
  overflow: visible;
}

/* Ensure Select2 container can escape */
#klas-list .select2-host {
  position: relative;
  z-index: 1; /* Above siblings, below dropdown */
}
```

---

## 📊 FINAL RISK ASSESSMENT

| Component | Risk Level | Impact | Mitigation |
|-----------|-----------|--------|------------|
| Table `overflow` removal | LOW | Visual only | ✅ Acceptable |
| Card `overflow: visible` | LOW | Minor layout shift | ✅ Test thoroughly |
| Z-index changes | VERY LOW | Isolated scope | ✅ Already tested |
| `!important` usage | MEDIUM | Future maintainability | ⚠️ Avoid if possible |

**Overall Risk:** **LOW to MEDIUM**

**Recommendation:**
1. Apply targeted `overflow: visible` without `!important`
2. Test on all screen sizes
3. Verify no layout breaks
4. Document in code comments

---

**Next Steps:**
1. User identifies exact clipper via DevTools
2. Apply targeted fix
3. Test comprehensively
4. Commit with risk assessment

---

**Created by:** Claude AI
**Status:** Analysis complete, awaiting user feedback on exact clipper
