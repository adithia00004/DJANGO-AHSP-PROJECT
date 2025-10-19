# Component Library - Quick Reference

**Cheat sheet untuk developer - copy paste code snippets**

---

## 🚀 Quick Setup

```html
{% extends 'detail_project/base_detail.html' %}
{% load static %}

{% block extra_css %}
  {{ block.super }}
  <link rel="stylesheet" href="{% static 'detail_project/css/components-library.css' %}">
{% endblock %}

{% block dp_content %}
  <div id="app" class="container-fluid ux-scrollbar">
    <!-- Your content -->
  </div>
{% endblock %}
```

---

## 📦 Component Snippets

### Toolbar

```html
<div class="dp-toolbar">
  <div class="input-group dp-toolbar-search">
    <span class="input-group-text"><i class="bi bi-search"></i></span>
    <input type="search" class="form-control" placeholder="Cari...">
  </div>
  <div class="ms-auto">
    <button class="btn btn-primary dp-btn">
      <i class="bi bi-plus-circle"></i> Tambah
    </button>
  </div>
</div>
```

---

### Buttons

```html
<!-- Primary Button -->
<button class="btn btn-primary dp-btn">
  <i class="bi bi-save"></i> Simpan
</button>

<!-- Small Button -->
<button class="btn btn-sm btn-outline-primary dp-btn-sm">
  <i class="bi bi-plus"></i> Add
</button>

<!-- Button Group -->
<div class="btn-group dp-btn-group">
  <button class="btn btn-outline-secondary dp-btn">Expand</button>
  <button class="btn btn-outline-secondary dp-btn">Collapse</button>
</div>
```

---

### Cards

```html
<!-- Primary Card (Level 1) -->
<div class="card dp-card-primary">
  <div class="card-header">
    <input type="text" class="form-control dp-card-title-primary" placeholder="Klasifikasi">
    <button class="btn btn-sm btn-primary dp-btn-sm">
      <i class="bi bi-plus"></i>
    </button>
  </div>
  <div class="card-body">
    <!-- Content -->
  </div>
</div>

<!-- Secondary Card (Level 2) -->
<div class="dp-card-secondary">
  <input type="text" class="form-control dp-card-title-secondary" placeholder="Sub">
  <!-- Content -->
</div>
```

---

### Table

```html
<table class="table dp-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Uraian</th>
      <th>Satuan</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>Pekerjaan A</td>
      <td>m³</td>
    </tr>
  </tbody>
</table>
```

---

### Sidebar Navigation

```html
<aside id="sidebar" class="dp-sidebar-overlay">
  <div class="dp-sidebar-inner dp-scrollbar">
    <div class="dp-sidebar-header">
      <h6>Navigasi</h6>
      <button class="btn btn-sm btn-outline-secondary dp-btn-sm">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>
    <nav class="mt-3">
      <!-- Navigation tree -->
    </nav>
  </div>
</aside>

<script>
// Toggle sidebar
document.getElementById('btn-toggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('is-open');
});
</script>
```

---

### Navigation Tree Node

```html
<div class="dp-nav-node" data-level="klas">
  <div class="dp-nav-node__header">
    <span class="dp-nav-node__toggle">
      <i class="bi bi-caret-down-fill"></i>
    </span>
    <span class="dp-nav-node__label">Item Name</span>
    <span class="dp-nav-node__count">(5)</span>
  </div>
  <div class="dp-nav-node__children">
    <!-- Child nodes -->
  </div>
</div>
```

---

### Autocomplete Dropdown

```html
<div class="position-relative">
  <input type="search" class="form-control">
  <div class="dp-autocomplete dp-scrollbar">
    <div class="dp-autocomplete-group">
      <div class="dp-autocomplete-title">Category</div>
      <div class="dp-autocomplete-item">Item 1</div>
      <div class="dp-autocomplete-item">Item 2</div>
    </div>
  </div>
</div>
```

---

## 🎨 Design Tokens Reference

### Colors

```css
var(--dp-c-bg)              /* Background */
var(--dp-c-text)            /* Text color */
var(--dp-c-muted)           /* Muted text */
var(--dp-c-border)          /* Border color */
var(--dp-c-surface-1)       /* Surface level 1 */
var(--dp-c-surface-2)       /* Surface level 2 */
var(--dp-c-primary)         /* Primary color */
var(--dp-c-focus)           /* Focus ring */
```

### Typography

```css
var(--ux-font-xs)           /* .75rem - Labels */
var(--ux-font-sm)           /* .8125rem - Controls */
var(--ux-font-md)           /* .875rem - Inputs */
var(--ux-font-lg)           /* 1rem - Headings */
```

### Spacing

```css
var(--dp-gap-xs)            /* 4px */
var(--dp-gap-sm)            /* 6px */
var(--dp-gap)               /* 8px */
```

### Shadows

```css
var(--dp-shadow-sm)         /* Subtle */
var(--dp-shadow-md)         /* Medium */
var(--dp-shadow-lg)         /* Large */
```

### Border Radius

```css
var(--dp-radius-sm)         /* .375rem */
var(--dp-radius-md)         /* .5rem */
var(--dp-radius-lg)         /* .75rem */
```

---

## 🎯 Common Patterns

### Full CRUD Page

```html
<div id="app" class="container-fluid">
  <!-- Toolbar -->
  <div class="dp-toolbar">
    <div class="input-group dp-toolbar-search">
      <span class="input-group-text"><i class="bi bi-search"></i></span>
      <input type="search" class="form-control" placeholder="Cari...">
    </div>
    <div class="ms-auto">
      <button class="btn btn-primary dp-btn" id="btn-add">
        <i class="bi bi-plus-circle"></i> Tambah
      </button>
    </div>
  </div>

  <!-- Table -->
  <div class="mt-3">
    <table class="table dp-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Nama</th>
          <th>Aksi</th>
        </tr>
      </thead>
      <tbody id="table-body">
        <!-- Rows here -->
      </tbody>
    </table>
  </div>
</div>
```

---

### Hierarchical Data Page

```html
<div id="app" class="container-fluid">
  <div class="dp-toolbar">
    <button class="btn btn-primary dp-btn">
      <i class="bi bi-plus-circle"></i> Klasifikasi
    </button>
    <div class="btn-group dp-btn-group ms-2">
      <button class="btn btn-outline-secondary dp-btn">Expand</button>
      <button class="btn btn-outline-secondary dp-btn">Collapse</button>
    </div>
  </div>

  <div id="data-list" class="mt-3">
    <!-- Cards with nested structure -->
  </div>
</div>
```

---

### Page with Sidebar

```html
<div id="app" class="container-fluid">
  <div class="dp-toolbar">
    <button class="btn btn-outline-secondary dp-btn" id="btn-nav">
      <i class="bi bi-list"></i> Navigasi
    </button>
    <div class="input-group dp-toolbar-search">
      <span class="input-group-text"><i class="bi bi-search"></i></span>
      <input type="search" class="form-control">
    </div>
  </div>

  <main id="main-content" class="mt-3">
    <!-- Main content -->
  </main>

  <aside id="sidebar" class="dp-sidebar-overlay">
    <!-- Sidebar content -->
  </aside>
</div>
```

---

## 🔧 Utility Classes

```html
<!-- Scrollbar -->
<div class="dp-scrollbar" style="max-height: 400px; overflow-y: auto;">
  <!-- Content -->
</div>

<!-- Highlight -->
<span>Search <span class="dp-hit">match</span></span>

<!-- Loading State -->
<div class="dp-loading">
  <!-- Content grayed out -->
</div>

<!-- Flash Animation -->
<div class="dp-flash">
  <!-- Animates on page load -->
</div>
```

---

## 📱 Responsive Classes

Component library sudah responsive by default. Untuk custom logic:

```css
/* Laptop (< 1200px) */
@media (max-width: 1199.98px) { }

/* Tablet Landscape (< 992px) */
@media (max-width: 991.98px) { }

/* Tablet Portrait (< 768px) */
@media (max-width: 767.98px) { }

/* Mobile (< 420px) */
@media (max-width: 420px) { }
```

---

## 🎨 Density/Compact Mode

Tambahkan class ke root container:

```html
<!-- Normal Mode -->
<div id="app" class="container-fluid">...</div>

<!-- Compact Mode -->
<div id="app" class="container-fluid dp-app-compact">...</div>

<!-- Dense Mode (sama seperti compact) -->
<div id="app" class="container-fluid dp-app-dense">...</div>
```

JavaScript toggle:

```javascript
document.getElementById('btn-compact').addEventListener('click', () => {
  document.getElementById('app').classList.toggle('dp-app-compact');
});
```

---

## 🌗 Dark Mode

Component library otomatis support dark mode via `[data-bs-theme]`:

```html
<!-- Light Mode (default) -->
<html data-bs-theme="light">

<!-- Dark Mode -->
<html data-bs-theme="dark">
```

Toggle JavaScript:

```javascript
const theme = document.documentElement.getAttribute('data-bs-theme');
const newTheme = theme === 'dark' ? 'light' : 'dark';
document.documentElement.setAttribute('data-bs-theme', newTheme);
```

---

## ✅ Do's and Don'ts

### ✅ DO

```html
<!-- Use component classes -->
<button class="btn btn-primary dp-btn">Save</button>

<!-- Use design tokens -->
<style>
.my-element {
  color: var(--dp-c-text);
  border-radius: var(--dp-radius-md);
}
</style>

<!-- Use semantic HTML -->
<button type="button">Click</button>
```

### ❌ DON'T

```html
<!-- Don't inline styles that conflict -->
<button class="dp-btn" style="padding: 20px;">Bad</button>

<!-- Don't hardcode colors -->
<style>
.my-element {
  color: #212529; /* Use var(--dp-c-text) instead */
}
</style>

<!-- Don't use divs for buttons -->
<div onclick="save()">Save</div>
```

---

## 🐛 Common Issues

### Issue: Styles not applying

**Check:**
1. ✅ `components-library.css` loaded after `core.css`?
2. ✅ Class name correct? (`.dp-btn` not `.dp-button`)
3. ✅ Bootstrap 5 loaded?

---

### Issue: Dark mode colors wrong

**Solution:** Make sure `core.css` is loaded. Check `data-bs-theme` attribute.

---

### Issue: Sidebar not showing

**Solution:** Add `.is-open` class via JavaScript:

```javascript
document.querySelector('.dp-sidebar-overlay').classList.add('is-open');
```

---

## 📚 Full Documentation

Untuk dokumentasi lengkap, lihat:
- `DESIGN_SYSTEM_GUIDE.md` - Complete guide dengan contoh detail
- `components-library.css` - Source code dengan komentar
- `core.css` - Design tokens definition

---

**Happy Coding! 🚀**
