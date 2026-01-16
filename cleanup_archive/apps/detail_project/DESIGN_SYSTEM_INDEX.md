# Design System - File Index

**Sistem dokumentasi lengkap untuk konsistensi UI/UX di seluruh aplikasi**

---

## 📁 File Structure

```
detail_project/
├── static/detail_project/css/
│   ├── core.css                    # Design tokens (colors, spacing, typography)
│   ├── components-library.css       # Reusable components (NEW)
│   ├── list_pekerjaan.css          # Reference implementation (original)
│   └── rekap_rab.css               # Reference implementation (original)
│
├── DESIGN_SYSTEM_GUIDE.md          # Complete documentation (NEW)
├── COMPONENT_QUICK_REFERENCE.md    # Developer cheat sheet (NEW)
└── DESIGN_SYSTEM_INDEX.md          # This file
```

---

## 📖 Documentation Files

### 1. [DESIGN_SYSTEM_GUIDE.md](./DESIGN_SYSTEM_GUIDE.md) ⭐ **START HERE**

**Dokumentasi lengkap dengan:**
- ✅ Setup & installation guide
- ✅ Design tokens reference (colors, typography, spacing, shadows)
- ✅ 12 component categories dengan contoh code
- ✅ Usage examples (3 complete page templates)
- ✅ Best practices & anti-patterns
- ✅ Customization guide
- ✅ Troubleshooting

**Untuk siapa:**
- 🎨 Designer yang ingin memahami sistem
- 👨‍💻 Developer baru yang perlu onboarding
- 📚 Developer yang butuh referensi detail

**Buka file ini jika:**
- Pertama kali menggunakan design system
- Ingin memahami filosofi dan struktur
- Butuh contoh implementasi lengkap

---

### 2. [COMPONENT_QUICK_REFERENCE.md](./COMPONENT_QUICK_REFERENCE.md) ⚡ **QUICK START**

**Cheat sheet untuk copy-paste code:**
- ✅ Quick setup template
- ✅ Ready-to-use component snippets
- ✅ Design token reference table
- ✅ Common patterns (CRUD, Hierarchical, Sidebar)
- ✅ Utility classes
- ✅ Do's and Don'ts
- ✅ Common issues & solutions

**Untuk siapa:**
- 👨‍💻 Developer yang sudah familiar dengan sistem
- ⚡ Developer yang butuh snippets cepat
- 🔧 Developer yang troubleshooting

**Buka file ini jika:**
- Sudah paham konsep, butuh code cepat
- Lupa syntax component tertentu
- Troubleshooting issue

---

### 3. [components-library.css](./static/detail_project/css/components-library.css) 📦 **SOURCE CODE**

**File CSS dengan 12 kategori komponen:**

1. **Toolbar Components** - Sticky toolbar dengan search
2. **Button Components** - Standard, small, action, groups
3. **Card Components** - Primary, secondary dengan hierarchy
4. **Table Components** - Standard & hierarchical tables
5. **Sidebar/Navigation** - Overlay sidebar dengan tree nav
6. **Scrollbar Components** - Custom scrollbar styling
7. **Autocomplete/Dropdown** - Dropdown dengan animasi
8. **Density/Compact Mode** - Mode kompak untuk data banyak
9. **Dark Mode Enhancements** - Glow effects untuk dark mode
10. **Responsive Breakpoints** - 4 breakpoint levels
11. **Accessibility** - Forced-colors & reduced-motion
12. **Utility Classes** - Helper classes

**Features:**
- ✅ 800+ lines of production-ready CSS
- ✅ Full light/dark mode support
- ✅ Mobile-first responsive
- ✅ Accessibility built-in
- ✅ Zero dependencies (selain core.css & Bootstrap)

---

## 🎯 Quick Start Guide

### For New Developers

**Step 1:** Read [DESIGN_SYSTEM_GUIDE.md](./DESIGN_SYSTEM_GUIDE.md) bagian "Introduction" dan "Setup"

**Step 2:** Copy template dari [COMPONENT_QUICK_REFERENCE.md](./COMPONENT_QUICK_REFERENCE.md) bagian "Quick Setup"

**Step 3:** Pilih komponen yang dibutuhkan dari [components-library.css](./static/detail_project/css/components-library.css)

**Step 4:** Test di browser, cek light/dark mode

---

### For Experienced Developers

**Quick Copy-Paste:**
1. Buka [COMPONENT_QUICK_REFERENCE.md](./COMPONENT_QUICK_REFERENCE.md)
2. Cari component yang dibutuhkan
3. Copy snippet
4. Paste ke project
5. Done! ✅

---

## 🎨 Design Token Quick Reference

Semua design tokens ada di [`core.css`](./static/detail_project/css/core.css).

**Most Used Tokens:**

```css
/* Colors */
var(--dp-c-bg)              /* Background */
var(--dp-c-text)            /* Text color */
var(--dp-c-border)          /* Borders */
var(--dp-c-primary)         /* Primary actions */

/* Typography */
var(--ux-font-xs)           /* .75rem */
var(--ux-font-sm)           /* .8125rem */
var(--ux-font-md)           /* .875rem */

/* Spacing */
var(--dp-gap)               /* 8px */

/* Shadows */
var(--dp-shadow-sm)         /* Subtle */
var(--dp-shadow-md)         /* Medium */

/* Border Radius */
var(--dp-radius-md)         /* .5rem */
```

---

## 📦 Component Overview

| Component | Class | File Reference |
|-----------|-------|----------------|
| Toolbar | `.dp-toolbar` | [components-library.css:23](./static/detail_project/css/components-library.css#L23) |
| Button | `.dp-btn` | [components-library.css:73](./static/detail_project/css/components-library.css#L73) |
| Card Primary | `.dp-card-primary` | [components-library.css:165](./static/detail_project/css/components-library.css#L165) |
| Card Secondary | `.dp-card-secondary` | [components-library.css:194](./static/detail_project/css/components-library.css#L194) |
| Table | `.dp-table` | [components-library.css:218](./static/detail_project/css/components-library.css#L218) |
| Sidebar | `.dp-sidebar-overlay` | [components-library.css:281](./static/detail_project/css/components-library.css#L281) |
| Nav Tree | `.dp-nav-node` | [components-library.css:353](./static/detail_project/css/components-library.css#L353) |
| Autocomplete | `.dp-autocomplete` | [components-library.css:487](./static/detail_project/css/components-library.css#L487) |
| Scrollbar | `.dp-scrollbar` | [components-library.css:463](./static/detail_project/css/components-library.css#L463) |

---

## 🔍 How to Find What You Need

### I need to...

**...understand the system**
→ Read [DESIGN_SYSTEM_GUIDE.md](./DESIGN_SYSTEM_GUIDE.md)

**...get code snippets quickly**
→ Use [COMPONENT_QUICK_REFERENCE.md](./COMPONENT_QUICK_REFERENCE.md)

**...see source code**
→ Open [components-library.css](./static/detail_project/css/components-library.css)

**...know what colors to use**
→ Check [core.css](./static/detail_project/css/core.css) design tokens

**...see real implementation**
→ Study [list_pekerjaan.css](./static/detail_project/css/list_pekerjaan.css) or [rekap_rab.css](./static/detail_project/css/rekap_rab.css)

**...create a new page**
→ Copy template from [COMPONENT_QUICK_REFERENCE.md > Common Patterns](./COMPONENT_QUICK_REFERENCE.md#-common-patterns)

---

## 🎓 Learning Path

### Beginner (Hari 1-2)

1. ✅ Baca [DESIGN_SYSTEM_GUIDE.md](./DESIGN_SYSTEM_GUIDE.md) bagian "Introduction"
2. ✅ Setup project dengan template dari guide
3. ✅ Coba 3 komponen dasar: toolbar, button, table
4. ✅ Test light/dark mode

### Intermediate (Hari 3-5)

1. ✅ Pelajari semua 12 kategori komponen
2. ✅ Buat 1 halaman CRUD sederhana
3. ✅ Implementasi responsive design
4. ✅ Pahami hierarchical patterns (cards + navigation)

### Advanced (Hari 6+)

1. ✅ Master custom styling dengan design tokens
2. ✅ Extend components untuk kasus khusus
3. ✅ Optimize performance & accessibility
4. ✅ Contribute ke design system

---

## 💡 Best Practices Summary

### ✅ DO

- Use component classes (`.dp-btn`, `.dp-table`, etc.)
- Use design tokens for all values
- Test in both light & dark mode
- Check responsive on mobile
- Use semantic HTML
- Reuse components, don't reinvent

### ❌ DON'T

- Hardcode colors, use `var(--dp-c-*)`
- Override component styles arbitrarily
- Create duplicate components
- Ignore accessibility
- Skip responsive testing
- Use inline styles that conflict

---

## 🐛 Troubleshooting

**Common Issues:**

1. **Styles not applying**
   - Check load order: Bootstrap → core.css → components-library.css
   - Check class names (`.dp-btn` not `.dp-button`)

2. **Dark mode not working**
   - Ensure `core.css` is loaded
   - Check `data-bs-theme` attribute on `<html>`

3. **Sidebar not showing**
   - Add `.is-open` class via JavaScript
   - Check z-index conflicts

4. **Responsive issues**
   - Component library is mobile-first by default
   - Check viewport meta tag exists

**For more:** See [COMPONENT_QUICK_REFERENCE.md > Common Issues](./COMPONENT_QUICK_REFERENCE.md#-common-issues)

---

## 📊 Component Statistics

- **Total Components:** 12 categories
- **Total Classes:** 50+ reusable classes
- **Lines of CSS:** 800+
- **Design Tokens Used:** 30+
- **Responsive Breakpoints:** 4 levels
- **Theme Support:** Light + Dark
- **Browser Support:** Modern browsers (Chrome, Firefox, Safari, Edge)

---

## 🔄 Version History

### v1.0.0 (2025-01-18)
- ✅ Initial release
- ✅ Based on list_pekerjaan.css & rekap_rab.css
- ✅ Full component library
- ✅ Complete documentation
- ✅ Quick reference guide

---

## 📞 Getting Help

**Priority order:**

1. 📖 Check [DESIGN_SYSTEM_GUIDE.md](./DESIGN_SYSTEM_GUIDE.md) documentation
2. ⚡ Look up [COMPONENT_QUICK_REFERENCE.md](./COMPONENT_QUICK_REFERENCE.md) for snippets
3. 🔍 Read source code comments in [components-library.css](./static/detail_project/css/components-library.css)
4. 👀 Study reference implementation in [list_pekerjaan.css](./static/detail_project/css/list_pekerjaan.css)

---

## 🎯 Next Steps

**Choose your path:**

### Path A: Quick Start (30 menit)
1. Copy template dari Quick Reference
2. Tambahkan 2-3 komponen
3. Test di browser
4. Deploy!

### Path B: Deep Learning (2-4 jam)
1. Baca complete Design System Guide
2. Pahami design tokens & philosophy
3. Implement complete page
4. Master all components

### Path C: Advanced (1-2 hari)
1. Study all documentation
2. Analyze source code
3. Create custom extensions
4. Contribute improvements

---

**Made with ❤️ for AHSP Project**

*Maintaining consistency, one component at a time.*
