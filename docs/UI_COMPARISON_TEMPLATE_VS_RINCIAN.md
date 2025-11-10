# Perbandingan UI/UX: Template AHSP vs Rincian AHSP

**Date**: 2025-11-10
**Purpose**: Analisis perbedaan tampilan antara Template AHSP dan Rincian AHSP

---

## 📋 Executive Summary

**Filosofi Design**: Kedua page seharusnya **identik** (menurut komentar di `rincian_ahsp.css`), dengan perbedaan utama hanya pada **fungsi tabel** (Template = 5 kolom tanpa harga, Rincian = 7 kolom dengan harga).

**Realitas**: Terdapat **beberapa perbedaan visual** yang membuat Rincian AHSP terasa lebih "polished" dibanding Template AHSP.

---

## 🎯 Perbedaan Utama

### **1. Scrollbar Styling** ⚠️ MAJOR DIFFERENCE

| Feature | Template AHSP | Rincian AHSP |
|---------|---------------|---------------|
| **Custom Scrollbar** | ❌ Tidak ada | ✅ **Ada** (width: 8px, rounded, themed) |
| **Scroll Shadows** | ❌ Tidak ada | ✅ **Ada** (::before & ::after gradients) |
| **Scrollbar Gutter** | ❌ Tidak ada | ✅ **Ada** (stable both-edges) |

**Impact**: Rincian AHSP terasa lebih "smooth" saat scrolling, dengan visual cue jelas kapan list masih bisa di-scroll.

**Code Comparison**:

```css
/* TEMPLATE AHSP - Basic scrollbar */
.ta-app .ta-job-list {
  max-height: calc(100vh - var(--ta-headroom, 220px));
  overflow: auto;
}

/* RINCIAN AHSP - Enhanced scrollbar */
.ra-app .ra-job-list {
  max-height: calc(100vh - var(--ra-headroom, 220px));
  overflow: auto;
  scrollbar-gutter: stable both-edges; /* Prevent layout shift */
}

/* Scroll shadows */
.ra-app .ra-job-list::before {
  content: "";
  position: sticky;
  top: 0;
  height: 14px;
  background: linear-gradient(to bottom,
    color-mix(in srgb, var(--dp-c-text) 14%, transparent),
    transparent
  );
  pointer-events: none;
  z-index: 1;
}

.ra-app .ra-job-list::after {
  bottom: 0;
  background: linear-gradient(to top,
    color-mix(in srgb, var(--dp-c-text) 14%, transparent),
    transparent
  );
}

/* Custom scrollbar thumb */
.ra-app .ra-job-list::-webkit-scrollbar {
  width: 8px;
}

.ra-app .ra-job-list::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--dp-c-text) 20%, transparent);
  border-radius: 8px;
  transition: background var(--ux-duration-200) var(--ux-ease);
}

.ra-app .ra-job-list::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--dp-c-text) 35%, transparent);
}
```

---

### **2. Job Item Styling** ⚠️ MINOR DIFFERENCE

| Feature | Template AHSP | Rincian AHSP |
|---------|---------------|---------------|
| **Default Background** | ❌ Transparent | ✅ `var(--dp-c-surface)` |
| **Uraian Line Clamp** | ❌ Tidak ada | ✅ **2 lines max** (with overflow hidden) |
| **Gap in Primary** | ❌ Tidak ada | ✅ `gap: 2px` |

**Impact**:
- Job items di Rincian AHSP lebih konsisten (semua punya background, tidak ada yang "floating")
- Uraian panjang tidak overflow, dipotong dengan elipsis (...)

**Code Comparison**:

```css
/* TEMPLATE AHSP - Simple */
.ta-app .ta-job-item {
  padding: 8px;
  border-radius: var(--dp-radius-sm);
  cursor: pointer;
  border: 1px solid transparent;
  /* NO background set - defaults to transparent */
}

.ta-app .ta-job-item .primary .uraian {
  font-weight: 400;
  font-size: var(--ux-font-sm);
  /* NO line-clamp - text can overflow */
}

/* RINCIAN AHSP - Enhanced */
.ra-app .ra-job-item {
  padding: 8px;
  border-radius: var(--dp-radius-sm);
  cursor: pointer;
  border: 1px solid transparent;
  background: var(--dp-c-surface); /* ✅ Always has background */
  transition: background-color .15s ease, border-color .15s ease, box-shadow .15s ease;
}

.ra-app .ra-job-item .primary {
  display: flex;
  flex-direction: column;
  gap: 2px; /* ✅ Consistent spacing */
}

.ra-app .ra-job-item .primary .uraian {
  font-weight: 400;
  line-height: 1.35;
  font-size: var(--ux-font-sm);
  /* ✅ Line-clamp prevents overflow */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}
```

---

### **3. Typography & Spacing** ✅ MINIMAL DIFFERENCE

| Feature | Template AHSP | Rincian AHSP |
|---------|---------------|---------------|
| **Font Family** | Default | ✅ `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` for kode |
| **Line Height** | Default (1.5) | ✅ `line-height: 1.35` for uraian |
| **Meta Gap** | ❌ Tidak explicit | ✅ `gap: 8px` |
| **Meta Margin** | ❌ Tidak explicit | ✅ `margin-top: 4px` |

**Impact**: Text lebih readable, spacing lebih konsisten di Rincian AHSP.

---

### **4. Table Structure** ⚠️ FUNCTIONAL DIFFERENCE

| Feature | Template AHSP | Rincian AHSP |
|---------|---------------|---------------|
| **Columns** | 5 (No, Uraian, Kode, Satuan, Koef) | 7 (+ Harga Satuan, Jumlah Harga) |
| **Segmentation** | 4 sections (TK, BHN, ALT, LAIN) | 1 unified table |
| **Edit Mode** | ✅ Editable (contenteditable, inputs) | ❌ Read-only |
| **Add/Delete Buttons** | ✅ Per segment | ❌ Tidak ada |
| **Pricing Display** | ❌ Tidak ada | ✅ Harga Satuan + Jumlah Harga |

**Impact**: Functional difference yang **disengaja** - Template untuk editing, Rincian untuk viewing.

---

### **5. Additional Features (Rincian AHSP Only)**

| Feature | Purpose |
|---------|---------|
| **Grand Total Display** | Show total biaya for selected pekerjaan |
| **BUK/Profit Badge** | Display profit margin percentage |
| **Override Modal** | Set custom BUK per pekerjaan |
| **Override Status Indicator** | Show if pekerjaan has active override |
| **Reset Override Button** | Reset to default BUK |

**Code Location**: Rincian AHSP template lines 127-147

```html
<!-- Pricing info + action buttons -->
<div class="rk-right-actions d-flex align-items-center gap-2">
  <!-- BUK Efektif Display -->
  <span id="rk-eff" class="rk-chip ra-chip ux-mono mono"
        title="Profit/Margin (BUK) untuk pekerjaan ini">
    <i class="bi bi-lightning-charge"></i>&nbsp;Profit: —%
  </span>

  <!-- Override Status Indicator -->
  <span id="rk-pkj-ovr-chip" class="rk-chip ra-chip-warn ux-mono mono"
        hidden title="Pekerjaan ini memiliki override aktif">
    <i class="bi bi-sliders"></i>&nbsp;Override Aktif
  </span>

  <!-- Action Buttons -->
  <div class="btn-group btn-group-sm">
    <button id="rk-btn-override" class="btn btn-outline-primary">
      <i class="bi bi-sliders"></i><span>Override</span>
    </button>
    <button id="rk-btn-reset" class="btn btn-outline-warning">
      <i class="bi bi-arrow-counterclockwise"></i><span>Reset</span>
    </button>
  </div>
</div>
```

---

## 🎨 Visual Comparison

### **Template AHSP**
```
┌─────────────────────────────────────────────────────────────┐
│ Template AHSP                                               │
│ Kelola komponen AHSP per pekerjaan. (Tanpa kolom harga)    │
├─────────────────────────────────────────────────────────────┤
│ [🔍 Cari pekerjaan...] [Cari] [Export▼] [Bantuan] [Simpan] │
├─────────┬───────────────────────────────────────────────────┤
│         │  Kode: —                                          │
│ ┌─────┐ │  Uraian: —                                        │
│ │ Job │ │  Satuan: —    Sumber: [—]                        │
│ │ Job │ ├───────────────────────────────────────────────────┤
│ │ Job │ │  ▼ Tenaga Kerja  [+ Baris] [🗑️ 0 baris]         │
│ │ Job │ │  ┌──────────────────────────────────────────────┐│
│ │     │ │  │ No │ Uraian │ Kode │ Satuan │ Koefisien   ││
│ │     │ │  └──────────────────────────────────────────────┘│
│ │     │ │                                                   │
│ └─────┘ │  ▼ Bahan  [+ Baris] [🗑️ 0 baris]                │
│         │  ┌──────────────────────────────────────────────┐│
│         │  │ No │ Uraian │ Kode │ Satuan │ Koefisien   ││
│         │  └──────────────────────────────────────────────┘│
└─────────┴───────────────────────────────────────────────────┘
```

**Characteristics**:
- Sidebar dengan basic scrollbar (no custom styling)
- Job items tanpa background default
- 4 segmen terpisah (TK, BHN, ALT, LAIN)
- Editable cells
- No pricing information

---

### **Rincian AHSP**
```
┌─────────────────────────────────────────────────────────────┐
│ Rincian AHSP                                                │
│ Detail komponen AHSP per pekerjaan (dengan harga dan total)│
├─────────────────────────────────────────────────────────────┤
│ [🔍 Cari...] [Cari] [Export▼] Grand: Rp 0 [Bantuan] [Save] │
├─────────┬───────────────────────────────────────────────────┤
│ ┏━━━━━┓│  2.2.2.1.1 · m2  [REF]  [⚡Profit: 15%] [Override]│
│ ┃ Job ┃│  1 m2  Pasangan dinding bata merah tebal 1/2 bata │
│ ┃ Job ┃├───────────────────────────────────────────────────┤
│ ┃ Job ┃│  ┌────────────────────────────────────────────────┐│
│ ┃ Job ┃│  │ No │ Uraian │ Kode │ Sat │ Koef │ Rp/sat │ Jum││
│ ┃━━━━━┃│  ├────────────────────────────────────────────────┤│
│ │     ││  │ 1  │ Mandor │ TK-01│ OH  │ 0.01 │ 150K  │ 1.5K││
│ │     ││  │ 2  │ Pekerja│ TK-05│ OH  │ 0.78 │ 100K  │ 78K ││
│ └─────┘│  └────────────────────────────────────────────────┘│
└─────────┴───────────────────────────────────────────────────┘
         ▲
    Custom scrollbar,
    scroll shadows,
    line-clamp text
```

**Characteristics**:
- Sidebar dengan **custom scrollbar** (8px, rounded, themed)
- **Scroll shadows** (gradient at top/bottom)
- Job items dengan **background default** (`var(--dp-c-surface)`)
- **Line-clamp** untuk uraian (max 2 lines)
- Single unified table
- **Pricing columns** (Harga Satuan, Jumlah Harga)
- **BUK/Profit display**
- **Override functionality**

---

## 📊 Summary Table

| Aspect | Template AHSP | Rincian AHSP | Priority |
|--------|---------------|---------------|----------|
| **Scrollbar** | Basic | ✅ Custom + Shadows | 🔴 HIGH |
| **Job Item BG** | Transparent | ✅ Themed | 🟡 MEDIUM |
| **Line Clamp** | ❌ No | ✅ 2 lines | 🟡 MEDIUM |
| **Typography** | Basic | ✅ Enhanced | 🟢 LOW |
| **Table Columns** | 5 (no price) | 7 (with price) | ✅ By design |
| **Edit Mode** | ✅ Editable | ❌ Read-only | ✅ By design |
| **Pricing Features** | ❌ No | ✅ Yes (BUK, Override) | ✅ By design |

**Legend**:
- 🔴 HIGH = Significant visual impact
- 🟡 MEDIUM = Noticeable but minor
- 🟢 LOW = Subtle improvement
- ✅ By design = Intentional functional difference

---

## 🔧 Recommendation

### **Option A: Sync Scrollbar Styling** (Recommended) 🔴

**Goal**: Make Template AHSP scrollbar match Rincian AHSP untuk consistency.

**Changes to Template AHSP CSS**:

```css
/* ADD to template_ahsp.css after line 145 */

/* Scroll shadows untuk job list */
.ta-app .ta-job-list {
  scrollbar-gutter: stable both-edges;
}

.ta-app .ta-job-list::before,
.ta-app .ta-job-list::after {
  content: "";
  position: sticky;
  left: 0;
  right: 0;
  height: 14px;
  pointer-events: none;
  z-index: 1;
}

.ta-app .ta-job-list::before {
  top: 0;
  background: linear-gradient(to bottom, color-mix(in srgb, var(--dp-c-text) 14%, transparent), transparent);
}

.ta-app .ta-job-list::after {
  bottom: 0;
  background: linear-gradient(to top, color-mix(in srgb, var(--dp-c-text) 14%, transparent), transparent);
}

/* Custom scrollbar */
.ta-app .ta-job-list::-webkit-scrollbar {
  width: 8px;
}

.ta-app .ta-job-list::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--dp-c-text) 20%, transparent);
  border-radius: 8px;
  transition: background var(--ux-duration-200) var(--ux-ease);
}

.ta-app .ta-job-list::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--dp-c-text) 35%, transparent);
}

.ta-app .ta-job-list::-webkit-scrollbar-track {
  background: transparent;
  transition: background var(--ux-duration-200) var(--ux-ease);
}

.ta-app .ta-job-list:hover::-webkit-scrollbar-track {
  background: color-mix(in srgb, var(--dp-c-border) 20%, transparent);
}
```

**Effort**: 5 minutes (copy-paste + test)
**Impact**: 🔴 HIGH (significant visual improvement)

---

### **Option B: Sync Job Item Styling** (Optional) 🟡

**Goal**: Make Template AHSP job items match Rincian AHSP styling.

**Changes to Template AHSP CSS**:

```css
/* UPDATE template_ahsp.css line 146 */

.ta-app .ta-job-item {
  padding: 8px;
  border-radius: var(--dp-radius-sm);
  cursor: pointer;
  border: 1px solid transparent;
  background: var(--dp-c-surface); /* ✅ ADD: default background */
  transition: background-color .15s ease, border-color .15s ease, box-shadow .15s ease;
}

/* ADD after line 169 */

.ta-app .ta-job-item .primary {
  display: flex;
  flex-direction: column;
  gap: 2px; /* ✅ ADD: consistent spacing */
}

.ta-app .ta-job-item .primary .kode {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; /* ✅ ADD: monospace */
  font-weight: 600;
  font-size: var(--ux-font-xs);
  color: var(--dp-c-muted); /* ✅ ADD: themed color */
}

.ta-app .ta-job-item .primary .uraian {
  font-weight: 400;
  line-height: 1.35; /* ✅ ADD: tighter line-height */
  font-size: var(--ux-font-sm);
  /* ✅ ADD: Line-clamp untuk prevent overflow */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}

/* ADD after .ta-job-item structure */

.ta-app .ta-job-item .meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px; /* ✅ ADD: consistent gap */
  align-items: center;
  font-size: var(--ux-font-xs);
  color: var(--dp-c-muted);
  margin-top: 4px; /* ✅ ADD: spacing */
}
```

**Effort**: 10 minutes
**Impact**: 🟡 MEDIUM (visual consistency improvement)

---

### **Option C: Do Nothing** (Not Recommended)

**Pros**: No development effort
**Cons**:
- Visual inconsistency between pages
- User confusion ("why do they look different?")
- Perceived as "unfinished" or "inconsistent"

---

## 🎯 Recommended Action Plan

**Priority Order**:

1. ✅ **[P0] Sync Scrollbar Styling** (5 min, HIGH impact)
   - Most visible difference
   - Significantly improves UX
   - Easy to implement (copy-paste)

2. ✅ **[P1] Sync Job Item Background** (3 min, MEDIUM impact)
   - Add `background: var(--dp-c-surface)`
   - Simple one-line change

3. ✅ **[P2] Add Line-Clamp for Uraian** (5 min, MEDIUM impact)
   - Prevents overflow
   - Cleaner appearance

4. ⏸️ **[P3] Typography enhancements** (OPTIONAL)
   - Monospace font for kode
   - Tighter line-height
   - Only if you want 100% consistency

**Total Effort**: 15-20 minutes for P0-P2

---

## 📝 Implementation Checklist

```
[ ] P0: Add custom scrollbar styling to Template AHSP
    [ ] scrollbar-gutter
    [ ] ::before and ::after scroll shadows
    [ ] ::-webkit-scrollbar styles
    [ ] Test on Chrome/Safari/Firefox

[ ] P1: Add default background to job items
    [ ] background: var(--dp-c-surface)
    [ ] Test hover states still work

[ ] P2: Add line-clamp for uraian
    [ ] -webkit-line-clamp: 2
    [ ] Test with long text
    [ ] Test with short text

[ ] P3: (OPTIONAL) Typography enhancements
    [ ] Monospace font for kode
    [ ] line-height: 1.35 for uraian
    [ ] gap and margin adjustments

[ ] Final: Cross-browser testing
    [ ] Chrome
    [ ] Firefox
    [ ] Safari
    [ ] Edge

[ ] Commit & Deploy
```

---

## 🎨 Before & After Preview (Expected)

### **BEFORE** (Current Template AHSP):
- Basic scrollbar (browser default)
- Job items blend into sidebar (no background)
- Long uraian text overflows
- No scroll indicators

### **AFTER** (With P0-P2 changes):
- ✅ Custom scrollbar (8px, rounded, themed)
- ✅ Scroll shadows indicate more content
- ✅ Job items have clear boundaries (background)
- ✅ Uraian text clamped to 2 lines
- ✅ **Visually identical to Rincian AHSP** (minus functional differences)

---

**Apakah Anda ingin saya implement changes P0-P2 sekarang?** 🚀

**Estimated Time**: 15 minutes total
**Risk**: Very low (CSS only, no functionality changes)
**Benefit**: Significant visual consistency improvement
