# Design System & Component Library Guide

**Version:** 1.0.0
**Last Updated:** 2025-01-18
**Based on:** list_pekerjaan.css & rekap_rab.css

---

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Setup & Installation](#setup--installation)
3. [Design Tokens](#design-tokens)
4. [Components](#components)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)
7. [Customization Guide](#customization-guide)

---

## 🎯 Introduction

Design System ini dibuat untuk memastikan **konsistensi visual dan UX** di seluruh aplikasi AHSP Project. Semua parameter (warna, ukuran, spacing, font, shadow, dll) telah distandarisasi berdasarkan implementasi sukses di halaman **List Pekerjaan** dan **Rekap RAB**.

### Prinsip Desain

✅ **Consistency First** - Semua komponen menggunakan design tokens yang sama
✅ **Accessibility** - Support untuk screen readers, keyboard navigation, forced-colors
✅ **Responsive** - Mobile-first dengan 4 breakpoint utama
✅ **Theme-aware** - Full support untuk light/dark mode
✅ **Performance** - Efficient CSS dengan minimal specificity

---

## 🚀 Setup & Installation

### 1. File Dependencies

Pastikan file-file ini di-load dalam urutan yang benar:

```html
<!-- 1. Bootstrap 5.x (base framework) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/.../bootstrap.min.css">

<!-- 2. Core CSS (WAJIB - design tokens) -->
<link rel="stylesheet" href="{% static 'detail_project/css/core.css' %}">

<!-- 3. Components Library (komponen reusable) -->
<link rel="stylesheet" href="{% static 'detail_project/css/components-library.css' %}">

<!-- 4. Page-specific CSS (opsional) -->
<link rel="stylesheet" href="{% static 'detail_project/css/your-page.css' %}">
```

### 2. HTML Structure Template

```html
{% extends 'detail_project/base_detail.html' %}
{% load static %}

{% block body_attrs %}data-page="your-page-name"{% endblock %}

{% block extra_css %}
  {{ block.super }}
  <link rel="stylesheet" href="{% static 'detail_project/css/components-library.css' %}">
{% endblock %}

{% block dp_content %}
  <div id="your-app" class="container-fluid ux-scrollbar">
    <!-- Your content here -->
  </div>
{% endblock %}
```

---

## 🎨 Design Tokens

### Color Tokens

Semua warna menggunakan CSS variables dari `core.css`:

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--dp-c-bg` | `#fff` | `#0f1215` | Background utama |
| `--dp-c-text` | `#212529` | `#e9ecef` | Text utama |
| `--dp-c-muted` | `#6c757d` | `#adb5bd` | Text sekunder |
| `--dp-c-border` | `#e5e7eb` | `rgba(255,255,255,.14)` | Border |
| `--dp-c-surface-1` | `#fff` | `#12161a` | Surface level 1 |
| `--dp-c-surface-2` | `#f7f8fa` | `#1b2026` | Surface level 2 |
| `--dp-c-primary` | `#0d6efd` | `#4dabf7` | Primary actions |
| `--dp-c-focus` | `rgba(13,110,253,.25)` | `rgba(77,171,247,.28)` | Focus ring |

### Typography Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--ux-font-2xs` | `.70rem` | Micro badges |
| `--ux-font-xs` | `.75rem` | Labels, helper text |
| `--ux-font-sm` | `.8125rem` | Controls kompak |
| `--ux-font-md` | `.875rem` | Input/select/textarea |
| `--ux-font-lg` | `1rem` | Headings kecil |

### Spacing Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--dp-gap-xs` | `4px` | Tight spacing |
| `--dp-gap-sm` | `6px` | Small spacing |
| `--dp-gap` | `8px` | Default spacing |

### Shadow Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--dp-shadow-sm` | `0 1px 2px rgba(0,0,0,.06)` | Subtle elevation |
| `--dp-shadow-md` | `0 6px 16px rgba(0,0,0,.12)` | Medium elevation |
| `--dp-shadow-lg` | `0 12px 28px rgba(0,0,0,.18)` | High elevation |

### Border Radius Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--dp-radius-sm` | `.375rem` | Small elements |
| `--dp-radius-md` | `.5rem` | Default radius |
| `--dp-radius-lg` | `.75rem` | Large containers |

---

## 🧩 Components

### 1. Toolbar Component

**Class:** `.dp-toolbar`

Toolbar sticky yang tetap terlihat saat scroll.

```html
<div class="dp-toolbar">
  <!-- Search -->
  <div class="input-group dp-toolbar-search">
    <span class="input-group-text">
      <i class="bi bi-search"></i>
    </span>
    <input type="search" class="form-control" placeholder="Cari...">
  </div>

  <!-- Actions (kanan) -->
  <div class="ms-auto">
    <button class="btn btn-primary dp-btn">
      <i class="bi bi-plus-circle"></i> Tambah
    </button>
    <button class="btn btn-success dp-btn">
      <i class="bi bi-save"></i> Simpan
    </button>
  </div>
</div>
```

**Features:**
- ✅ Sticky positioning (top: `--dp-topbar-h`)
- ✅ Responsive search bar
- ✅ Auto-wrap pada layar kecil
- ✅ Consistent spacing dengan `.ms-auto`

---

### 2. Button Component

**Classes:** `.dp-btn`, `.dp-btn-sm`, `.dp-btn-action`

```html
<!-- Standard Button -->
<button class="btn btn-primary dp-btn">
  <i class="bi bi-save"></i> Simpan
</button>

<!-- Small Button (sidebar) -->
<button class="btn btn-sm btn-outline-primary dp-btn-sm">
  <i class="bi bi-plus"></i> Add
</button>

<!-- Action Button (Add/Delete) -->
<button class="btn btn-danger dp-btn-action">
  <i class="bi bi-trash"></i> Hapus
</button>

<!-- Button Group -->
<div class="btn-group dp-btn-group">
  <button class="btn btn-outline-secondary dp-btn">Expand</button>
  <button class="btn btn-outline-secondary dp-btn">Collapse</button>
</div>
```

**Features:**
- ✅ Hover effect: `translateY(-1px)` + shadow
- ✅ Active effect: `scale(0.98)`
- ✅ Icon margin: `.35rem`
- ✅ Disabled state otomatis

**States:**
- Normal: `padding: .375rem .75rem`
- Hover: Shadow medium + lift
- Active: Scale down
- Disabled: Opacity 50% + grayscale

---

### 3. Card Component

**Classes:** `.dp-card-primary`, `.dp-card-secondary`

```html
<!-- Primary Card (Level 1 - Klasifikasi) -->
<div class="card dp-card-primary">
  <div class="card-header">
    <input type="text" class="form-control dp-card-title-primary" placeholder="Nama Klasifikasi">
    <button class="btn btn-sm btn-primary dp-btn-sm">
      <i class="bi bi-plus"></i> Sub
    </button>
    <button class="btn btn-sm btn-outline-danger dp-btn-sm">
      <i class="bi bi-trash"></i>
    </button>
  </div>
  <div class="card-body">
    <!-- Content here -->
  </div>
</div>

<!-- Secondary Card (Level 2 - Sub-Klasifikasi) -->
<div class="dp-card-secondary">
  <input type="text" class="form-control dp-card-title-secondary" placeholder="Nama Sub">
  <!-- Content here -->
</div>
```

**Hierarchy:**

| Level | Class | Border | Font Weight | Usage |
|-------|-------|--------|-------------|-------|
| 1 | `.dp-card-primary` | 2px | 700 | Klasifikasi |
| 2 | `.dp-card-secondary` | 1px | 600 | Sub-Klasifikasi |

**Features:**
- ✅ Hover shadow enhancement
- ✅ Border radius hierarchy
- ✅ Auto background color dari theme
- ✅ Responsive spacing

---

### 4. Table Component

**Classes:** `.dp-table`, `.dp-table-hierarchy`

```html
<!-- Standard Table -->
<table class="table dp-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Uraian</th>
      <th>Satuan</th>
      <th class="text-end">Volume</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>Pekerjaan Tanah</td>
      <td>m³</td>
      <td class="text-end">100.00</td>
    </tr>
  </tbody>
</table>

<!-- Hierarchical Table (untuk rekap) -->
<table class="table dp-table dp-table-hierarchy">
  <tbody>
    <tr data-level="1">
      <td>Klasifikasi A</td>
      <td class="text-end">1,000,000</td>
    </tr>
    <tr data-level="2">
      <td>Sub-Klasifikasi A1</td>
      <td class="text-end">500,000</td>
    </tr>
    <tr data-level="3">
      <td>Pekerjaan 1</td>
      <td class="text-end">250,000</td>
    </tr>
  </tbody>
</table>
```

**Features:**
- ✅ Border radius pada container
- ✅ Hover effect pada row
- ✅ Last row tanpa border
- ✅ Hierarchical font weight (700/600/400)
- ✅ Hierarchical padding-left

---

### 5. Sidebar/Navigation Component

**Classes:** `.dp-sidebar-overlay`, `.dp-sidebar-inner`, `.dp-nav-node__*`

```html
<!-- Sidebar Overlay -->
<aside id="my-sidebar" class="dp-sidebar-overlay">
  <div class="dp-sidebar-inner dp-scrollbar">
    <!-- Header -->
    <div class="dp-sidebar-header">
      <h6>Navigasi</h6>
      <div class="d-flex gap-2">
        <button class="btn btn-sm btn-primary dp-btn-sm">
          <i class="bi bi-plus"></i> Tambah
        </button>
        <button class="btn btn-sm btn-outline-secondary dp-btn-sm" data-action="close">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
    </div>

    <!-- Tree Navigation -->
    <nav class="mt-3">
      <!-- Klasifikasi Node -->
      <div class="dp-nav-node" data-level="klas">
        <div class="dp-nav-node__header">
          <span class="dp-nav-node__toggle">
            <i class="bi bi-caret-down-fill"></i>
          </span>
          <span class="dp-nav-node__label">Klasifikasi A</span>
          <span class="dp-nav-node__count">(3)</span>
        </div>
        <div class="dp-nav-node__children">
          <!-- Sub Node -->
          <div class="dp-nav-node" data-level="sub">
            <div class="dp-nav-node__header">
              <span class="dp-nav-node__toggle">
                <i class="bi bi-caret-down-fill"></i>
              </span>
              <span class="dp-nav-node__label">Sub A1</span>
              <span class="dp-nav-node__count">(5)</span>
            </div>
            <div class="dp-nav-node__children">
              <!-- Job Node -->
              <div class="dp-nav-node" data-level="job">
                <div class="dp-nav-node__header">
                  <span class="dp-nav-node__label">Pekerjaan 1</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>
  </div>
</aside>
```

**Features:**
- ✅ Backdrop blur effect
- ✅ Slide-in animation dari kanan
- ✅ Hierarchical indentation (border-left)
- ✅ Font weight hierarchy (700/600/400)
- ✅ Hover effect dengan translateX
- ✅ Active state dengan outline

**JavaScript Integration:**
```javascript
// Open sidebar
document.querySelector('.dp-sidebar-overlay').classList.add('is-open');

// Close sidebar
document.querySelector('.dp-sidebar-overlay').classList.remove('is-open');
```

---

### 6. Autocomplete/Dropdown Component

**Class:** `.dp-autocomplete`

```html
<div class="position-relative">
  <input type="search" class="form-control" placeholder="Cari...">

  <!-- Autocomplete Dropdown -->
  <div class="dp-autocomplete dp-scrollbar">
    <!-- Group 1 -->
    <div class="dp-autocomplete-group">
      <div class="dp-autocomplete-title">Klasifikasi</div>
      <div class="dp-autocomplete-item">
        <span>Klasifikasi A</span>
      </div>
      <div class="dp-autocomplete-item is-active">
        <span>Klasifikasi <span class="dp-hit">B</span></span>
      </div>
    </div>

    <!-- Group 2 -->
    <div class="dp-autocomplete-group">
      <div class="dp-autocomplete-title">Pekerjaan</div>
      <div class="dp-autocomplete-item">
        <span>Pekerjaan Tanah</span>
      </div>
    </div>
  </div>
</div>
```

**Features:**
- ✅ Slide-in animation
- ✅ Auto max-height dengan scroll
- ✅ Grouped items
- ✅ Highlight untuk search match (`.dp-hit`)
- ✅ Hover effect dengan translateX

---

### 7. Scrollbar Component

**Class:** `.dp-scrollbar`

Tambahkan class `.dp-scrollbar` ke element yang perlu custom scrollbar:

```html
<div class="dp-scrollbar" style="max-height: 400px; overflow-y: auto;">
  <!-- Long content -->
</div>
```

**Features:**
- ✅ Width: 8px (konsisten)
- ✅ Thumb: 20% opacity → 35% on hover
- ✅ Track: Transparent → 20% opacity on container hover
- ✅ Smooth transition

---

## 💡 Usage Examples

### Example 1: Simple CRUD Page

```html
{% extends 'detail_project/base_detail.html' %}
{% load static %}

{% block extra_css %}
  {{ block.super }}
  <link rel="stylesheet" href="{% static 'detail_project/css/components-library.css' %}">
{% endblock %}

{% block dp_content %}
<div id="crud-app" class="container-fluid ux-scrollbar">

  <!-- Toolbar -->
  <div class="dp-toolbar">
    <div class="input-group dp-toolbar-search">
      <span class="input-group-text"><i class="bi bi-search"></i></span>
      <input type="search" class="form-control" placeholder="Cari data...">
    </div>
    <div class="ms-auto">
      <button class="btn btn-primary dp-btn" id="btn-add">
        <i class="bi bi-plus-circle"></i> Tambah
      </button>
    </div>
  </div>

  <!-- Data Table -->
  <div class="mt-3">
    <table class="table dp-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Nama</th>
          <th>Keterangan</th>
          <th>Aksi</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td>Item A</td>
          <td>Deskripsi item A</td>
          <td>
            <button class="btn btn-sm btn-outline-primary dp-btn-sm">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger dp-btn-sm">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

</div>
{% endblock %}
```

---

### Example 2: Hierarchical Data Display

```html
<div id="hierarchy-app" class="container-fluid">

  <!-- Toolbar -->
  <div class="dp-toolbar">
    <button class="btn btn-primary dp-btn">
      <i class="bi bi-plus-circle"></i> Klasifikasi
    </button>
    <div class="btn-group dp-btn-group ms-2">
      <button class="btn btn-outline-secondary dp-btn">Expand All</button>
      <button class="btn btn-outline-secondary dp-btn">Collapse All</button>
    </div>
  </div>

  <!-- Hierarchical Cards -->
  <div id="klas-list" class="mt-3">

    <!-- Level 1: Klasifikasi -->
    <div class="card dp-card-primary">
      <div class="card-header">
        <input type="text" class="form-control dp-card-title-primary"
               value="Klasifikasi A">
        <button class="btn btn-sm btn-primary dp-btn-sm">
          <i class="bi bi-plus"></i> Sub
        </button>
        <button class="btn btn-sm btn-outline-danger dp-btn-sm">
          <i class="bi bi-trash"></i>
        </button>
      </div>

      <div class="card-body">
        <!-- Level 2: Sub-Klasifikasi -->
        <div class="dp-card-secondary mb-3">
          <div class="d-flex align-items-center gap-2 mb-2">
            <input type="text" class="form-control dp-card-title-secondary"
                   value="Sub A1">
            <button class="btn btn-sm btn-primary dp-btn-action">
              <i class="bi bi-plus"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger dp-btn-action">
              <i class="bi bi-trash"></i>
            </button>
          </div>

          <!-- Level 3: Data Table -->
          <table class="table dp-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Pekerjaan</th>
                <th>Satuan</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1</td>
                <td>Pekerjaan Tanah</td>
                <td>m³</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div>
</div>
```

---

### Example 3: Page with Sidebar Navigation

```html
<div id="nav-app" class="container-fluid">

  <!-- Toolbar with Sidebar Toggle -->
  <div class="dp-toolbar">
    <button class="btn btn-outline-secondary dp-btn" id="btn-toggle-sidebar">
      <i class="bi bi-list"></i> Navigasi
    </button>
    <div class="input-group dp-toolbar-search">
      <span class="input-group-text"><i class="bi bi-search"></i></span>
      <input type="search" class="form-control" placeholder="Cari...">
    </div>
  </div>

  <!-- Main Content -->
  <div class="mt-3">
    <p>Main content here...</p>
  </div>

  <!-- Sidebar (initially hidden) -->
  <aside id="app-sidebar" class="dp-sidebar-overlay">
    <div class="dp-sidebar-inner dp-scrollbar">
      <div class="dp-sidebar-header">
        <h6>Navigasi</h6>
        <button class="btn btn-sm btn-outline-secondary dp-btn-sm"
                id="btn-close-sidebar">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <!-- Navigation Tree -->
      <nav class="mt-3">
        <div class="dp-nav-node" data-level="klas">
          <div class="dp-nav-node__header">
            <span class="dp-nav-node__toggle">
              <i class="bi bi-caret-down-fill"></i>
            </span>
            <span class="dp-nav-node__label">Section 1</span>
          </div>
          <div class="dp-nav-node__children">
            <div class="dp-nav-node" data-level="sub">
              <div class="dp-nav-node__header">
                <span class="dp-nav-node__label">Subsection 1.1</span>
              </div>
            </div>
          </div>
        </div>
      </nav>
    </div>
  </aside>
</div>

<script>
// Toggle sidebar
document.getElementById('btn-toggle-sidebar').addEventListener('click', () => {
  document.getElementById('app-sidebar').classList.toggle('is-open');
});

document.getElementById('btn-close-sidebar').addEventListener('click', () => {
  document.getElementById('app-sidebar').classList.remove('is-open');
});
</script>
```

---

## ✅ Best Practices

### 1. Always Use Design Tokens

❌ **BAD:**
```css
.my-button {
  background: #0d6efd;
  color: #fff;
  padding: 8px 16px;
  border-radius: 8px;
}
```

✅ **GOOD:**
```css
.my-button {
  background: var(--dp-c-primary);
  color: var(--dp-c-bg);
  padding: .375rem .75rem;
  border-radius: var(--dp-radius-md);
}
```

### 2. Reuse Component Classes

❌ **BAD:**
```html
<button style="padding: 6px 12px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,.06);">
  Click Me
</button>
```

✅ **GOOD:**
```html
<button class="btn btn-primary dp-btn">
  <i class="bi bi-check"></i> Click Me
</button>
```

### 3. Maintain Hierarchy

❌ **BAD:**
```html
<div class="card">
  <div class="card-header" style="font-size: 18px; font-weight: bold;">
    Title
  </div>
</div>
```

✅ **GOOD:**
```html
<div class="card dp-card-primary">
  <div class="card-header">
    <h6 class="dp-card-title-primary">Title</h6>
  </div>
</div>
```

### 4. Use Semantic HTML

❌ **BAD:**
```html
<div class="dp-btn" onclick="save()">Save</div>
```

✅ **GOOD:**
```html
<button type="button" class="btn btn-success dp-btn" onclick="save()">
  <i class="bi bi-save"></i> Save
</button>
```

### 5. Responsive by Default

❌ **BAD:**
```css
.my-toolbar {
  display: flex;
  /* No responsive handling */
}
```

✅ **GOOD:**
```html
<!-- Uses .dp-toolbar which is responsive by default -->
<div class="dp-toolbar">
  <!-- Content wraps automatically on mobile -->
</div>
```

---

## 🎨 Customization Guide

### When to Create Custom Styles

Buat custom styles **HANYA** untuk:
1. ✅ Logic bisnis spesifik page (bukan visual)
2. ✅ Layout unik yang tidak ada di component library
3. ✅ Interaksi khusus yang butuh JS integration

**JANGAN** buat custom styles untuk:
1. ❌ Warna (gunakan design tokens)
2. ❌ Button styles (gunakan `.dp-btn`)
3. ❌ Spacing (gunakan Bootstrap utilities)
4. ❌ Shadow/radius (gunakan design tokens)

### How to Extend Components

Jika perlu extend component:

```css
/* your-page.css */

/* ✅ GOOD: Extend dengan composability */
.my-special-card {
  /* Reuse base card */
  /* Tambahkan logic spesifik saja */
  position: relative;
}

.my-special-card::before {
  content: "⭐";
  position: absolute;
  top: .5rem;
  right: .5rem;
}

/* ❌ BAD: Override everything */
.my-special-card {
  border: 2px solid red; /* DON'T - use var(--dp-c-border) */
  padding: 20px; /* DON'T - inconsistent with .dp-card-primary */
  background: #fff; /* DON'T - use var(--dp-c-bg) */
}
```

### Creating Page-Specific Styles

```css
/* your-page.css */

/* Scope dengan ID page */
#your-app {
  /* Page-specific layout only */
}

#your-app .special-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--dp-gap); /* Use design token */
}

/* DON'T override component styles */
#your-app .dp-btn {
  /* ❌ JANGAN override .dp-btn */
}

/* DO extend dengan class tambahan */
#your-app .my-custom-action {
  /* Logic khusus page */
  animation: pulse 2s infinite;
}
```

---

## 📚 Component Reference Quick Guide

| Component | Class | Usage |
|-----------|-------|-------|
| **Toolbar** | `.dp-toolbar` | Sticky toolbar dengan search & actions |
| **Button** | `.dp-btn` | Standard button dengan hover effects |
| **Button Small** | `.dp-btn-sm` | Small button untuk sidebar |
| **Button Group** | `.dp-btn-group` | Grouped buttons (Expand/Collapse) |
| **Card Primary** | `.dp-card-primary` | Level 1 container (Klasifikasi) |
| **Card Secondary** | `.dp-card-secondary` | Level 2 container (Sub) |
| **Table** | `.dp-table` | Standard table dengan border radius |
| **Table Hierarchy** | `.dp-table-hierarchy` | Table dengan level hierarchy |
| **Sidebar** | `.dp-sidebar-overlay` | Overlay sidebar dengan backdrop |
| **Nav Node** | `.dp-nav-node` | Tree navigation node |
| **Autocomplete** | `.dp-autocomplete` | Dropdown autocomplete |
| **Scrollbar** | `.dp-scrollbar` | Custom scrollbar styling |
| **Search Highlight** | `.dp-hit` | Highlight untuk search match |

---

## 🔧 Troubleshooting

### Issue: Warna tidak sesuai theme

**Solution:** Pastikan menggunakan design tokens, bukan hardcoded colors.

```css
/* ❌ Wrong */
background: #fff;

/* ✅ Correct */
background: var(--dp-c-bg);
```

---

### Issue: Button tidak responsive

**Solution:** Gunakan class `.dp-btn` yang sudah responsive.

---

### Issue: Sidebar tidak muncul

**Solution:** Pastikan JavaScript menambahkan class `.is-open`:

```javascript
document.querySelector('.dp-sidebar-overlay').classList.add('is-open');
```

---

### Issue: Dark mode tidak berfungsi

**Solution:** Pastikan `core.css` loaded sebelum `components-library.css`.

---

## 📝 Changelog

### Version 1.0.0 (2025-01-18)
- ✅ Initial release
- ✅ Based on list_pekerjaan.css & rekap_rab.css
- ✅ 12 component categories
- ✅ Full light/dark mode support
- ✅ Responsive breakpoints (4 levels)
- ✅ Accessibility features
- ✅ Complete documentation

---

## 🤝 Contributing

Jika ingin menambahkan komponen baru:

1. Pastikan komponen menggunakan design tokens dari `core.css`
2. Test di light & dark mode
3. Test responsive di 4 breakpoint
4. Dokumentasikan penggunaan di guide ini
5. Update changelog

---

## 📞 Support

Untuk pertanyaan atau issue:
- Periksa dokumentasi ini terlebih dahulu
- Lihat `core.css` untuk design tokens available
- Review `list_pekerjaan.css` & `rekap_rab.css` untuk referensi implementasi

---

**Made with ❤️ for AHSP Project**
