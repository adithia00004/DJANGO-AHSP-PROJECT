# PHASE 2 TIMELINE POLISH PLAN
**Timeline Intelligence - Weekly/Monthly View Enhancement**

**Date:** 2025-12-03
**Status:** 🔄 In Progress → ✅ Completing

---

## 📊 Current Implementation Status

### What's Already Built ✅

#### Backend (services.py)
- ✅ `compute_kebutuhan_timeline()` function complete
- ✅ Weekly/monthly bucket distribution
- ✅ Period aggregation with start/end dates
- ✅ Filter support (klasifikasi, sub, kategori, pekerjaan)
- ✅ Quantity and cost totals per period
- ✅ Integration with PekerjaanTahapan schedules

#### Frontend (HTML/CSS/JS)
- ✅ Timeline view toggle (Snapshot | Timeline)
- ✅ Timeline container with loading/empty states
- ✅ CSS styling for timeline blocks
- ✅ Period breakdown rendering
- ✅ View switching logic

### What Needs Polish 🔄

According to roadmap:
> "timeline API + UI shipped; **insights polish pending**"

---

## 🎯 Polish Objectives

### 1. **Period Visual Indicators Enhancement**
**Current State:** Basic period blocks
**Target:** Rich visual period cards with clear hierarchy

**Improvements Needed:**
- Add period type badges (Week/Month)
- Color-coded period status
- Visual date range display
- Progress indicators (if applicable)
- Hover state enhancements

---

### 2. **Tooltip & Hover States**
**Current State:** Minimal interaction feedback
**Target:** Informative tooltips with contextual data

**Improvements Needed:**
- Tooltip on period header (date range, duration)
- Tooltip on item rows (breakdown details)
- Hover highlights for better readability
- Quick stats popup (total items, total cost)

---

### 3. **Transition Animations**
**Current State:** Instant view switching
**Target:** Smooth transitions between states

**Improvements Needed:**
- Fade-in animation for timeline view
- Slide-in animation for period blocks
- Smooth collapse/expand for period details
- Loading skeleton during data fetch

---

### 4. **Reconciliation with Jadwal Grid**
**Current State:** Timeline generated from schedule
**Target:** Visual verification that numbers match

**Improvements Needed:**
- Link to Jadwal Pekerjaan for verification
- Period consistency check (dates align)
- Tooltip showing source schedule
- Warning if schedule missing/incomplete

---

## 📋 Implementation Tasks

### Task 1: Enhanced Period Cards
**Priority:** HIGH
**Effort:** 2 hours

**HTML Changes:**
```html
<!-- Enhanced Period Block -->
<div class="rk-timeline-period" data-period-value="1">
  <div class="rk-timeline-period__header">
    <div class="rk-timeline-period__badge">
      <i class="bi bi-calendar-week"></i>
      <span>Minggu 1</span>
    </div>
    <div class="rk-timeline-period__dates">
      <small>1 Jan - 7 Jan 2025</small>
      <span class="rk-timeline-period__duration">7 hari</span>
    </div>
    <div class="rk-timeline-period__stats">
      <span class="badge bg-info">150 items</span>
      <span class="badge bg-success">Rp 15.5M</span>
    </div>
  </div>
  <!-- ... content ... -->
</div>
```

**CSS Additions:**
```css
.rk-timeline-period__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(to right, #f8f9fa, #fff);
  border-bottom: 2px solid var(--dp-c-border);
}

.rk-timeline-period__badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--dp-c-primary);
}

.rk-timeline-period__dates {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.rk-timeline-period__duration {
  font-size: 0.75rem;
  color: var(--dp-c-text-muted);
}
```

---

### Task 2: Tooltips Implementation
**Priority:** MEDIUM
**Effort:** 1.5 hours

**Using Bootstrap Tooltips:**
```javascript
// Initialize tooltips
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
const tooltipList = [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
```

**HTML with Tooltips:**
```html
<div class="rk-timeline-period__badge"
     data-bs-toggle="tooltip"
     data-bs-placement="top"
     title="Periode 1-7 Januari 2025 (7 hari kerja)">
  <i class="bi bi-calendar-week"></i>
  <span>Minggu 1</span>
</div>

<td data-bs-toggle="tooltip"
    data-bs-html="true"
    title="<strong>Pasir</strong><br>Qty: 150 m3<br>@Rp 100,000 = Rp 15,000,000">
  Pasir
</td>
```

**JavaScript Enhancement:**
```javascript
// Custom tooltip with detailed breakdown
function showItemTooltip(item) {
  return `
    <div class="rk-tooltip-content">
      <strong>${item.uraian}</strong>
      <div class="mt-1">
        <small>Kode: ${item.kode}</small><br>
        <small>Qty: ${item.quantity} ${item.satuan}</small><br>
        <small>Harga: ${item.harga_satuan}</small><br>
        <strong>Total: ${item.harga_total}</strong>
      </div>
    </div>
  `;
}
```

---

### Task 3: Smooth Transitions
**Priority:** MEDIUM
**Effort:** 1 hour

**CSS Animations:**
```css
/* Fade-in for timeline view */
#rk-timeline {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

#rk-timeline.d-none {
  opacity: 0;
  transform: translateY(10px);
}

#rk-timeline:not(.d-none) {
  opacity: 1;
  transform: translateY(0);
}

/* Slide-in for period blocks */
.rk-timeline-period {
  animation: slideIn 0.4s ease forwards;
  opacity: 0;
}

.rk-timeline-period:nth-child(1) { animation-delay: 0.1s; }
.rk-timeline-period:nth-child(2) { animation-delay: 0.2s; }
.rk-timeline-period:nth-child(3) { animation-delay: 0.3s; }

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Loading skeleton */
.rk-timeline-skeleton {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rk-timeline-skeleton__item {
  height: 100px;
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 0.5rem;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**JavaScript Implementation:**
```javascript
// Smooth view switching
function switchToTimeline() {
  const $snapshot = document.getElementById('rk-tablewrap');
  const $timeline = document.getElementById('rk-timeline');

  // Fade out snapshot
  $snapshot.style.opacity = '0';

  setTimeout(() => {
    $snapshot.classList.add('d-none');
    $timeline.classList.remove('d-none');

    // Trigger animation
    requestAnimationFrame(() => {
      $timeline.style.opacity = '1';
    });
  }, 300);
}
```

---

### Task 4: Jadwal Reconciliation UI
**Priority:** LOW
**Effort:** 1 hour

**Add Verification Link:**
```html
<div class="rk-timeline-period__header">
  <!-- ... existing content ... -->

  <a href="{% url 'detail_project:jadwal_pekerjaan' project.id %}?highlight=week-1"
     class="btn btn-sm btn-outline-secondary"
     target="_blank"
     title="Lihat di Jadwal Pekerjaan">
    <i class="bi bi-calendar2-check"></i>
    <span class="d-none d-md-inline ms-1">Verifikasi</span>
  </a>
</div>
```

**Add Schedule Source Indicator:**
```html
<div class="rk-timeline-period__source">
  <small class="text-muted">
    <i class="bi bi-info-circle"></i>
    Data dari: <strong>Jadwal Pekerjaan</strong>
    <a href="#" data-bs-toggle="tooltip" title="Periode ini dihitung berdasarkan tahapan pekerjaan yang terjadwal">
      <i class="bi bi-question-circle"></i>
    </a>
  </small>
</div>
```

**Warning for Missing Schedule:**
```html
<div class="alert alert-warning d-flex align-items-center" role="alert">
  <i class="bi bi-exclamation-triangle-fill me-2"></i>
  <div>
    <strong>Peringatan:</strong>
    Beberapa pekerjaan belum memiliki jadwal.
    <a href="{% url 'detail_project:jadwal_pekerjaan' project.id %}">
      Lengkapi jadwal
    </a>
    untuk distribusi timeline yang akurat.
  </div>
</div>
```

---

## 🎨 Visual Design Improvements

### Color Coding by Period Status
```css
/* Active period (ongoing) */
.rk-timeline-period--active {
  border-left: 4px solid #0d6efd;
  background: color-mix(in srgb, #0d6efd 3%, white);
}

/* Past period (completed) */
.rk-timeline-period--past {
  opacity: 0.7;
  border-left: 4px solid #6c757d;
}

/* Future period (upcoming) */
.rk-timeline-period--future {
  border-left: 4px solid #198754;
}
```

### Period Type Badges
```html
<!-- Week badge -->
<span class="rk-period-badge rk-period-badge--week">
  <i class="bi bi-calendar-week"></i>
  Minggu 1
</span>

<!-- Month badge -->
<span class="rk-period-badge rk-period-badge--month">
  <i class="bi bi-calendar-month"></i>
  Januari 2025
</span>
```

---

## 📊 Enhanced Stats Display

### Per-Period Summary Card
```html
<div class="rk-period-summary">
  <div class="row g-3">
    <div class="col-md-3">
      <div class="rk-summary-item">
        <div class="rk-summary-icon bg-primary">
          <i class="bi bi-people-fill"></i>
        </div>
        <div class="rk-summary-content">
          <div class="rk-summary-label">Tenaga Kerja</div>
          <div class="rk-summary-value">12 items</div>
          <div class="rk-summary-cost">Rp 5.2M</div>
        </div>
      </div>
    </div>
    <!-- Repeat for BHN, ALT, LAIN -->
  </div>
</div>
```

---

## 🧪 Testing Checklist

### Visual Testing
- [ ] Period cards display correctly on desktop/tablet/mobile
- [ ] Tooltips appear on hover with correct information
- [ ] Animations smooth (60fps) during view switch
- [ ] Color coding consistent and accessible
- [ ] Loading skeleton displays during data fetch

### Functional Testing
- [ ] View toggle switches between snapshot/timeline
- [ ] Period data matches snapshot totals
- [ ] Link to Jadwal Pekerjaan works
- [ ] Tooltips work on touch devices
- [ ] Keyboard navigation functional

### Data Integrity
- [ ] Period dates align with Jadwal Pekerjaan
- [ ] Item quantities sum correctly per period
- [ ] Costs calculate accurately
- [ ] Filters apply correctly to timeline
- [ ] Empty periods handled gracefully

---

## 📈 Success Metrics

### User Experience
- **Visual Clarity:** 8/10 → 10/10
- **Interaction Smoothness:** 6/10 → 9/10
- **Information Density:** 7/10 → 9/10
- **Reconciliation Confidence:** 5/10 → 9/10

### Technical
- **Animation FPS:** >55fps
- **Tooltip Response:** <100ms
- **View Switch Time:** <300ms
- **Data Accuracy:** 100% match with snapshot

---

## ✅ Implementation Checklist

### Phase 2A: Visual Enhancements (2-3 hours)
- [ ] Enhanced period card headers
- [ ] Period type badges (week/month)
- [ ] Color coding by status (past/active/future)
- [ ] Visual date range display
- [ ] Summary stats per period

### Phase 2B: Interactions (1.5-2 hours)
- [ ] Bootstrap tooltips initialization
- [ ] Custom tooltip content (item details)
- [ ] Hover state CSS enhancements
- [ ] Touch-friendly interactions

### Phase 2C: Animations (1 hour)
- [ ] Fade-in/out transitions
- [ ] Slide-in period blocks
- [ ] Loading skeleton during fetch
- [ ] Smooth view switching

### Phase 2D: Reconciliation (1 hour)
- [ ] Link to Jadwal Pekerjaan
- [ ] Schedule source indicator
- [ ] Warning for missing schedules
- [ ] Period consistency verification

---

## 🚀 Quick Implementation (Start Here)

### Step 1: Add Enhanced Period Headers
**File:** Update `rekap_kebutuhan.js` render function

```javascript
// Add to renderTimelinePeriod function
function renderTimelinePeriod(period) {
  const badge = period.value <= 4 ?
    `<i class="bi bi-calendar-week"></i> Minggu ${period.value}` :
    `<i class="bi bi-calendar-month"></i> ${period.label}`;

  return `
    <div class="rk-timeline-period" data-period="${period.value}">
      <div class="rk-timeline-period__header">
        <div class="rk-timeline-period__badge">${badge}</div>
        <div class="rk-timeline-period__dates">
          <small>${formatDateRange(period.start_date, period.end_date)}</small>
        </div>
        <div class="rk-timeline-period__stats">
          <span class="badge bg-info">${period.item_count} items</span>
          <span class="badge bg-success">${formatCurrency(period.total_cost)}</span>
        </div>
      </div>
      ${renderPeriodContent(period)}
    </div>
  `;
}
```

### Step 2: Add CSS for Enhanced Headers
**File:** `rekap_kebutuhan_enhancements.css`

```css
.rk-timeline-period__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border-bottom: 2px solid var(--dp-c-border);
  border-radius: 0.5rem 0.5rem 0 0;
}

.rk-timeline-period__badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 1rem;
  color: var(--dp-c-primary);
}

.rk-timeline-period__dates {
  flex: 1;
  text-align: center;
  color: var(--dp-c-text-muted);
}

.rk-timeline-period__stats {
  display: flex;
  gap: 0.5rem;
}
```

### Step 3: Initialize Tooltips
**File:** `rekap_kebutuhan.js`

```javascript
// After timeline rendered
function initTimelineTooltips() {
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(el => {
    new bootstrap.Tooltip(el, {
      html: true,
      delay: { show: 500, hide: 100 }
    });
  });
}
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-03
**Status:** 🔄 Ready for Implementation
