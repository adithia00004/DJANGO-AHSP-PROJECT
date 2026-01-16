# TOOLBAR V2 QUICK REFERENCE
**Rekap Kebutuhan - Developer Cheat Sheet**

---

## 🚀 Quick Start

### Include Files
```html
<!-- CSS (already included) -->
<link rel="stylesheet" href="{% static 'detail_project/css/rekap_kebutuhan.css' %}">

<!-- JavaScript -->
<script src="{% static 'detail_project/js/rekap_kebutuhan.js' %}" defer></script>
<script src="{% static 'detail_project/js/rekap_kebutuhan_toolbar.js' %}" defer></script>
```

### HTML Structure
```html
<div class="rk-toolbar-v2">
  <!-- Actions -->
  <div class="rk-toolbar-section rk-toolbar-actions">...</div>

  <!-- Search & View -->
  <div class="rk-toolbar-section rk-toolbar-search-view">...</div>

  <!-- Stats -->
  <div class="rk-toolbar-section rk-toolbar-stats">...</div>
</div>
```

---

## 🎨 CSS Classes

### Toolbar
```css
.rk-toolbar-v2                 /* Main container */
.rk-toolbar-section            /* Section wrapper */
.rk-toolbar-actions            /* Actions group */
.rk-toolbar-search-view        /* Search & view group */
.rk-toolbar-stats              /* Stats group */
```

### Stat Cards
```css
.rk-stat-card                  /* Card base */
.rk-stat-card--tk              /* TK variant */
.rk-stat-card--bhn             /* BHN variant */
.rk-stat-card--alt             /* ALT variant */
.rk-stat-card--lain            /* LAIN variant */
.rk-stat-card--total           /* Total variant */
.rk-stat-card--highlight       /* Highlighted card */
.rk-stat-card--pulse           /* Pulse animation */
```

### Components
```css
.rk-stat-icon                  /* Icon circle */
.rk-stat-content               /* Card content */
.rk-stat-label                 /* Category label */
.rk-stat-values                /* Values wrapper */
.rk-stat-count                 /* Count number */
.rk-stat-qty                   /* Quantity */
.rk-stat-total                 /* Total amount */
.rk-stats-toggle               /* Mobile toggle */
.rk-stats-cards                /* Cards container */
.rk-toolbar-meta               /* Meta info */
```

---

## 🎯 Element IDs

### Action Buttons
```html
#btn-export-csv                /* CSV export */
#btn-export-pdf                /* PDF export */
#btn-export-word               /* Word export */
#rk-btn-refresh                /* Refresh button */
```

### Search & View
```html
#rk-search                     /* Search input */
#rk-search-clear               /* Clear button */
#rk-view-toggle                /* View toggle group */
```

### Stats Display
```html
<!-- Count elements -->
#rk-count-TK                   /* TK count */
#rk-count-BHN                  /* BHN count */
#rk-count-ALT                  /* ALT count */
#rk-count-LAIN                 /* LAIN count */

<!-- Quantity elements -->
#rk-qty-TK                     /* TK quantity */
#rk-qty-BHN                    /* BHN quantity */
#rk-qty-ALT                    /* ALT quantity */
#rk-qty-LAIN                   /* LAIN quantity */

<!-- Meta elements -->
#rk-total-cost                 /* Total cost */
#rk-nrows                      /* Row count */
#rk-generated                  /* Timestamp */

<!-- Collapse -->
#rk-stats-collapse             /* Collapse container */
#rk-stats-summary              /* Summary badge */
```

---

## 📡 JavaScript Events

### Listening (Your app should listen)
```javascript
// Refresh requested
document.addEventListener('rk:refresh', () => {
  // Re-fetch data
  await loadRekapKebutuhan();

  // Notify toolbar when done
  document.dispatchEvent(new CustomEvent('rk:dataLoaded'));
});

// Toolbar ready
document.addEventListener('rk:toolbarReady', (e) => {
  console.log('Toolbar version:', e.detail.version); // "2.0"
});
```

### Dispatching (From your app)
```javascript
// Data loaded (stops spinner)
document.dispatchEvent(new CustomEvent('rk:dataLoaded'));

// Trigger refresh programmatically
document.dispatchEvent(new CustomEvent('rk:refresh'));
```

---

## 🔧 Common Tasks

### Update Stats
```javascript
// Update count
document.getElementById('rk-count-TK').textContent = '12';

// Update quantity
document.getElementById('rk-qty-TK').textContent = '(150.5)';

// Update total
document.getElementById('rk-total-cost').textContent = 'Rp 15.500.000';

// Toolbar automatically:
// 1. Detects change
// 2. Applies pulse animation
// 3. Updates summary badge
```

### Trigger Refresh
```javascript
// Method 1: Click button
document.getElementById('rk-btn-refresh').click();

// Method 2: Dispatch event
document.dispatchEvent(new CustomEvent('rk:refresh'));
```

### Check Collapse State
```javascript
// Get current state
const isCollapsed = sessionStorage.getItem('rk-stats-collapsed') === 'true';

// Set state
sessionStorage.setItem('rk-stats-collapsed', 'true');

// Collapse programmatically
const $collapse = document.getElementById('rk-stats-collapse');
const bsCollapse = bootstrap.Collapse.getInstance($collapse);
bsCollapse.hide();
```

### Add Custom Animation
```javascript
// Pulse specific card
const $card = document.querySelector('.rk-stat-card--tk');
$card.classList.add('rk-stat-card--pulse');
setTimeout(() => {
  $card.classList.remove('rk-stat-card--pulse');
}, 600);
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` / `Cmd+R` | Refresh data |
| `Ctrl+F` / `Cmd+F` | Focus search |
| `Esc` | Clear search (when focused) |
| `Tab` | Navigate forward |
| `Shift+Tab` | Navigate backward |
| `Enter` / `Space` | Activate button |

---

## 📱 Responsive Breakpoints

```css
/* Desktop */
@media (min-width: 1200px) { /* 3-column layout */ }

/* Tablet landscape */
@media (max-width: 1199.98px) { /* Compact cards */ }

/* Tablet portrait */
@media (max-width: 991.98px) { /* Stacked, stats collapsible */ }

/* Mobile */
@media (max-width: 767.98px) { /* Icon-only buttons, 2-col stats */ }

/* Extra small */
@media (max-width: 575.98px) { /* Single column stats */ }
```

---

## 🎨 Color Palette

```css
/* Category colors */
--tk-color: #0d6efd;      /* Blue */
--bhn-color: #198754;     /* Green */
--alt-color: #ffc107;     /* Yellow */
--lain-color: #0dcaf0;    /* Cyan */
--total-color: #6f42c1;   /* Purple */

/* Usage */
.rk-stat-card--tk .rk-stat-icon {
  background: color-mix(in srgb, #0d6efd 15%, transparent);
  color: #0d6efd;
}
```

---

## 🔍 Debugging

### Console Logging
```javascript
// Toolbar loaded
console.log('[rk-toolbar] Toolbar V2 enhancements loaded');

// Check version
document.addEventListener('rk:toolbarReady', (e) => {
  console.log('Version:', e.detail.version);
});

// Monitor events
document.addEventListener('rk:refresh', () => {
  console.log('Refresh requested');
});
```

### Browser DevTools
```javascript
// Check collapse state
sessionStorage.getItem('rk-stats-collapsed');

// Get stat card element
document.querySelector('.rk-stat-card--tk');

// Check event listeners
getEventListeners(document);

// Force pulse animation
document.querySelector('.rk-stat-card--bhn').classList.add('rk-stat-card--pulse');
```

### CSS Debug Classes
```css
/* Add red borders to sections */
.rk-toolbar-section {
  border: 2px dashed red !important;
}

/* Highlight stat cards */
.rk-stat-card {
  background: yellow !important;
}
```

---

## ⚡ Performance Tips

1. **Debounce Search**
   ```javascript
   // Already implemented (300ms)
   ```

2. **Use CSS Transforms**
   ```css
   /* Good - hardware accelerated */
   transform: translateY(-1px);

   /* Bad - causes reflow */
   top: -1px;
   ```

3. **Minimize DOM Access**
   ```javascript
   // Cache elements
   const $countTK = document.getElementById('rk-count-TK');

   // Update multiple times
   $countTK.textContent = '10';
   $countTK.textContent = '11';
   $countTK.textContent = '12';
   ```

---

## 🐛 Common Issues

### Issue: Spinner Won't Stop
**Cause:** `rk:dataLoaded` not dispatched
**Fix:**
```javascript
// Always dispatch after data loads
await loadData();
document.dispatchEvent(new CustomEvent('rk:dataLoaded'));
```

### Issue: Stats Not Updating
**Cause:** Wrong element ID or typo
**Fix:**
```javascript
// Check element exists
const $el = document.getElementById('rk-count-TK');
if (!$el) console.error('Element not found!');
```

### Issue: Keyboard Shortcut Not Working
**Cause:** Event listener not attached
**Fix:**
```javascript
// Check toolbar.js loaded
console.log('Toolbar loaded:', !!window.rkToolbarReady);
```

### Issue: Mobile Layout Broken
**Cause:** Missing Bootstrap CSS
**Fix:**
```html
<!-- Ensure Bootstrap 5 loaded -->
<link href="bootstrap.min.css" rel="stylesheet">
```

---

## 📚 Quick Links

- **Full Documentation:** `docs/PHASE_4_IMPLEMENTATION_SUMMARY.md`
- **Visual Guide:** `docs/TOOLBAR_V2_VISUAL_GUIDE.md`
- **Analysis:** `docs/TOOLBAR_REDESIGN_ANALYSIS.md`
- **Testing:** `docs/PHASE_4_TESTING_CHECKLIST.md`
- **Roadmap:** `docs/REKAP_KEBUTUHAN_LIVING_ROADMAP.md`

---

## 🆘 Support

### Before Asking for Help
1. ✅ Check browser console for errors
2. ✅ Verify all files included (CSS + both JS files)
3. ✅ Check element IDs match
4. ✅ Test in incognito (clear cache)
5. ✅ Review this quick reference

### Report Issues
Include:
- Browser & version
- Screen size
- Console errors
- Steps to reproduce
- Expected vs actual behavior

---

**Version:** 2.0
**Last Updated:** 2025-12-03
**Status:** ✅ Production Ready
