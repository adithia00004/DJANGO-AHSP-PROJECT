# PHASE 4 TESTING CHECKLIST
**Toolbar V2 - Rekap Kebutuhan**

**Date:** 2025-12-03
**Tester:** _______________
**Environment:** ☐ Development ☐ Staging ☐ Production

---

## 📋 Pre-Testing Setup

- [ ] Clear browser cache
- [ ] Clear sessionStorage: `sessionStorage.clear()`
- [ ] Verify files deployed:
  - [ ] `rekap_kebutuhan.html` (modified)
  - [ ] `rekap_kebutuhan.css` (modified)
  - [ ] `rekap_kebutuhan_toolbar.js` (new)
- [ ] Open browser console for errors
- [ ] Prepare test project with data

---

## 🖥️ Desktop Testing (≥1200px)

### Visual Layout
- [ ] Toolbar shows 3 distinct sections
- [ ] Sections have proper spacing (1.5rem gap)
- [ ] All 5 stat cards visible in one row
- [ ] Icons displayed correctly:
  - [ ] 👥 People (TK - Blue)
  - [ ] 📦 Box (BHN - Green)
  - [ ] 🔧 Tools (ALT - Yellow)
  - [ ] ✨ Dots (LAIN - Cyan)
  - [ ] 💰 Coin (Total - Purple highlight)
- [ ] Row count and timestamp visible below stats
- [ ] No layout overflow or horizontal scroll

### Actions Section
- [ ] Export dropdown button visible
- [ ] Export dropdown opens on click
- [ ] All 3 export options visible:
  - [ ] CSV (green icon)
  - [ ] PDF (red icon)
  - [ ] Word (blue icon)
- [ ] Refresh button visible with text "Refresh"
- [ ] Refresh button shows tooltip on hover
- [ ] Clicking refresh adds spinning animation
- [ ] Spinning stops after data loads

### Search & View Section
- [ ] Search input full width (max 400px)
- [ ] Search placeholder: "Cari kode atau uraian"
- [ ] Typing in search shows clear button (X)
- [ ] Clear button hidden when empty
- [ ] View toggle shows both buttons:
  - [ ] Snapshot (active by default)
  - [ ] Timeline
- [ ] Clicking view button switches active state

### Stats Display
- [ ] Each stat card shows:
  - [ ] Category icon in colored circle
  - [ ] Category label (TK/BHN/ALT/LAIN/Total)
  - [ ] Count number (bold)
  - [ ] Quantity in parentheses (or total amount)
- [ ] Cards have subtle shadow
- [ ] Hover on card shows lift effect
- [ ] Total card has purple border

### Animations
- [ ] Refresh button spins on click
- [ ] Stat cards pulse when values change
- [ ] Dropdown slides in smoothly
- [ ] Card hover lift is smooth (no jank)

---

## 📱 Tablet Testing (768px - 991px)

### Layout Changes
- [ ] Sections stack vertically
- [ ] Actions section full width
- [ ] Search input full width
- [ ] View toggle full width (buttons stretch)
- [ ] Stats section full width
- [ ] Stats toggle button visible
- [ ] Stats cards in 2-column grid
- [ ] Row count centered below stats

### Stats Collapse
- [ ] Stats toggle shows icon + badge
- [ ] Badge shows total item count
- [ ] Clicking toggle collapses/expands stats
- [ ] Collapse animation smooth
- [ ] Collapsed state persists on refresh
- [ ] Expanding stats updates sessionStorage

### Touch Targets
- [ ] All buttons ≥44px touchable area
- [ ] Buttons not too close together
- [ ] Dropdown items easy to tap

---

## 📱 Mobile Testing (<768px)

### Compact Layout
- [ ] Action buttons show icons only (no text)
- [ ] Export button: "📥▼"
- [ ] Refresh button: "↻"
- [ ] Stats toggle: "≡ [badge]"
- [ ] Search input full width
- [ ] View toggle buttons equal width

### Stats Display
- [ ] Stats collapsed by default
- [ ] Toggle button prominent
- [ ] Expanded stats in 2 columns
- [ ] Total card full width (1 column)
- [ ] Cards readable size

### Touch Friendly
- [ ] All buttons minimum 44px × 44px
- [ ] Sufficient spacing between elements
- [ ] No accidental clicks
- [ ] Scrolling smooth (no lag)

### Extra Small (<576px)
- [ ] Stats cards stack (1 column)
- [ ] All text readable
- [ ] No content cut off
- [ ] Buttons still 44px × 44px

---

## ⌨️ Keyboard Navigation Testing

### Tab Order
- [ ] Tab navigates in logical order:
  1. Export button
  2. Refresh button
  3. Search input
  4. Clear button (if visible)
  5. Snapshot button
  6. Timeline button
  7. Stats toggle (mobile/tablet)
- [ ] Shift+Tab navigates backward
- [ ] Focus indicators visible (2px outline)

### Keyboard Shortcuts
- [ ] `Ctrl+R` triggers refresh
- [ ] `Cmd+R` triggers refresh (Mac)
- [ ] Refresh shortcut prevented browser reload
- [ ] `Ctrl+F` focuses search input
- [ ] `Cmd+F` focuses search input (Mac)
- [ ] Search focused when F pressed with Ctrl/Cmd
- [ ] `Esc` clears search (when focused)
- [ ] `Enter` submits search
- [ ] `Space` activates focused button
- [ ] `Enter` activates focused button

### Focus Management
- [ ] Focus indicator high contrast
- [ ] Focus visible on all interactive elements
- [ ] Focus not trapped
- [ ] Focus returns after modal/dropdown

---

## ♿ Accessibility Testing

### Screen Reader (NVDA/JAWS/VoiceOver)
- [ ] Toolbar announced as "Toolbar Rekap Kebutuhan"
- [ ] Sections announced with proper labels:
  - [ ] "Actions" group
  - [ ] "Search and view" group
  - [ ] "Statistics" group
- [ ] Export button announced with label
- [ ] Refresh button announced with tooltip
- [ ] Search input has proper label
- [ ] View toggle buttons announce pressed state
- [ ] Stats toggle announces expanded state
- [ ] Stat cards content readable
- [ ] View switch announced: "Switched to timeline view"
- [ ] Stats collapse announced: "Statistics collapsed"

### ARIA Attributes
- [ ] `role="toolbar"` on main container
- [ ] `role="group"` on sections
- [ ] `aria-label` on action buttons
- [ ] `aria-pressed` on view toggle (true/false)
- [ ] `aria-expanded` on stats toggle
- [ ] `aria-controls` points to collapse target
- [ ] `aria-live="polite"` for announcements

### Color Contrast
- [ ] Text meets WCAG AA (4.5:1)
- [ ] Icon colors sufficient contrast
- [ ] Focus indicators visible
- [ ] Disabled states distinguishable

---

## 🎭 Animation & Performance

### Smooth Animations
- [ ] No frame drops during animations
- [ ] Pulse animation 60fps
- [ ] Refresh spinner smooth rotation
- [ ] Dropdown slide-in smooth
- [ ] Hover effects instant response

### Performance
- [ ] Page load <3 seconds
- [ ] Toolbar renders immediately
- [ ] No layout shift during load
- [ ] Stats update lag <100ms
- [ ] Search debounce 300ms working
- [ ] MutationObserver not affecting performance
- [ ] No memory leaks (check DevTools)

---

## 🔄 Functional Testing

### Refresh Button
- [ ] Clicking refresh triggers `rk:refresh` event
- [ ] Spinner starts immediately
- [ ] Data reloads correctly
- [ ] Spinner stops after data loaded
- [ ] Toast notification shows (if available)
- [ ] Button disabled during refresh
- [ ] Can't spam-click refresh

### Search Clear Button
- [ ] Appears when typing
- [ ] Disappears when empty
- [ ] Clicking clear empties input
- [ ] Focus returns to search input
- [ ] Search reruns after clear
- [ ] Debounce working (300ms)

### Stats Animation
- [ ] Stats update when data changes
- [ ] Pulse animation triggers on update
- [ ] Animation plays only once per update
- [ ] Summary badge updates correctly
- [ ] Total item count accurate

### Stats Collapse (Mobile/Tablet)
- [ ] Toggle button functional
- [ ] Collapse smooth (no jank)
- [ ] State persists on page refresh
- [ ] State stored in sessionStorage
- [ ] Multiple collapses don't break
- [ ] Works with Bootstrap collapse API

### View Toggle
- [ ] Clicking switches active button
- [ ] Only one button active at a time
- [ ] ARIA pressed state updates
- [ ] Screen reader announces switch
- [ ] View actually changes (if implemented)

---

## 🌐 Cross-Browser Testing

### Chrome/Edge
- [ ] Desktop layout correct
- [ ] Mobile layout correct
- [ ] Animations smooth
- [ ] Keyboard shortcuts work
- [ ] DevTools shows no errors

### Firefox
- [ ] Desktop layout correct
- [ ] Mobile layout correct
- [ ] Animations smooth
- [ ] Keyboard shortcuts work
- [ ] Console shows no errors

### Safari (if available)
- [ ] Desktop layout correct
- [ ] Mobile layout correct
- [ ] Animations smooth
- [ ] Keyboard shortcuts work
- [ ] Console shows no errors

### Mobile Safari (iOS)
- [ ] Touch targets sufficient
- [ ] Animations smooth
- [ ] No tap delay
- [ ] Collapse works
- [ ] No layout issues

### Chrome Mobile (Android)
- [ ] Touch targets sufficient
- [ ] Animations smooth
- [ ] No tap delay
- [ ] Collapse works
- [ ] No layout issues

---

## 🔍 Edge Cases

### Data States
- [ ] Empty data (0 items) displays correctly
- [ ] Very large numbers format properly
- [ ] Negative numbers (if possible) handle correctly
- [ ] Decimal quantities show correctly

### Long Text
- [ ] Long category names don't break layout
- [ ] Long search queries don't overflow
- [ ] Stat cards handle overflow

### Network Issues
- [ ] Slow network: spinner shows
- [ ] Failed request: error handling
- [ ] Timeout: stops spinner
- [ ] Multiple rapid refreshes handled

### Rapid Interactions
- [ ] Spam-clicking refresh doesn't break
- [ ] Rapid search typing debounces
- [ ] Multiple collapse toggles smooth
- [ ] View switching rapid clicks ok

### Browser Actions
- [ ] Window resize: responsive works
- [ ] Zoom in/out: layout adapts
- [ ] Print preview: toolbar hidden
- [ ] Back button: state preserved

---

## 🐛 Bug Tracking

### Issues Found

#### Issue #1
- **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
- **Description:**
- **Steps to Reproduce:**
- **Expected:**
- **Actual:**
- **Browser/Device:**
- **Screenshot:**

#### Issue #2
- **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
- **Description:**
- **Steps to Reproduce:**
- **Expected:**
- **Actual:**
- **Browser/Device:**
- **Screenshot:**

*(Add more as needed)*

---

## ✅ Sign-Off

### Testing Summary
- **Total Tests:** _____
- **Passed:** _____
- **Failed:** _____
- **Blocked:** _____

### Environments Tested
- [ ] Desktop Chrome
- [ ] Desktop Firefox
- [ ] Desktop Safari
- [ ] Mobile Safari
- [ ] Mobile Chrome
- [ ] Tablet

### Critical Issues
- [ ] None found
- [ ] Issues documented above

### Recommendation
- [ ] ✅ **APPROVED** - Ready for production
- [ ] ⚠️ **APPROVED WITH ISSUES** - Non-critical bugs acceptable
- [ ] ❌ **REJECTED** - Critical bugs must be fixed

### Notes
```
[Additional notes, observations, or recommendations]
```

---

**Tester Signature:** _______________
**Date:** _______________
**QA Lead Approval:** _______________

---

## 📎 Attachments

- [ ] Screenshots (desktop/tablet/mobile)
- [ ] Screen recordings (if issues found)
- [ ] Console logs (if errors found)
- [ ] Network traces (if performance issues)
- [ ] Accessibility audit report (Lighthouse)

---

**Template Version:** 1.0
**Phase:** 4 - Toolbar Redesign
**Last Updated:** 2025-12-03
