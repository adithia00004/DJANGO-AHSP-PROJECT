# Rincian AHSP - Complete Documentation

**Last Updated**: 2025-01-17
**Page**: Rincian AHSP (Detail Analysis Harga Satuan Pekerjaan)
**Purpose**: Menampilkan breakdown detail komponen biaya untuk setiap pekerjaan dalam project

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Page Architecture](#page-architecture)
3. [Data Flow](#data-flow)
4. [Formula & Calculations](#formula--calculations)
5. [Bundle System](#bundle-system)
6. [Recent Fixes](#recent-fixes)
7. [API Endpoints](#api-endpoints)
8. [Frontend Components](#frontend-components)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose
Page Rincian AHSP menampilkan detail breakdown biaya untuk setiap pekerjaan dalam project, dengan 2 panel:
- **Panel Kiri (Sidebar)**: List semua pekerjaan dengan HSP summary
- **Panel Kanan (Detail)**: Breakdown komponen (TK/BHN/ALT/LAIN) untuk pekerjaan terpilih

### Key Features
1. **Dual Panel Layout**: List pekerjaan (kiri) + Detail items (kanan)
2. **Real-time Calculation**: Automatic calculation saat user edit koefisien/harga
3. **Bundle Support**: Support untuk pekerjaan yang mereferensikan pekerjaan lain (Custom Segment D)
4. **Override BUK**: Support override profit/margin per pekerjaan
5. **Grand Total**: Total keseluruhan project dengan PPN

---

## Page Architecture

### File Structure
```
detail_project/
├── views.py                           # Django view untuk render page
├── views_api.py                       # API endpoints
│   ├── api_get_rekap_rab()           # Get rekap semua pekerjaan (sidebar kiri)
│   ├── api_get_detail_ahsp()         # Get detail items (sidebar kanan)
│   ├── api_pekerjaan_pricing()       # Get/Set override BUK
│   └── api_get_pricing()             # Get project-level pricing
├── static/detail_project/js/
│   └── rincian_ahsp.js               # Frontend logic (TIER 3 Complete)
├── services.py                        # Business logic
│   ├── compute_rekap_for_project()   # Calculate rekap (backend)
│   └── _populate_expanded_from_raw() # Bundle expansion
└── models.py
    ├── Pekerjaan                      # Pekerjaan master
    ├── DetailAHSPProject              # Raw storage untuk detail items
    ├── DetailAHSPExpanded             # Expanded storage (post bundle expansion)
    ├── HargaItemProject               # Harga satuan per item
    └── VolumePekerjaan                # Volume per pekerjaan
```

### Component Hierarchy
```
┌─────────────────────────────────────────────────────────────────┐
│                     Rincian AHSP Page                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────────────┐ │
│  │  Sidebar Kiri    │  │       Sidebar Kanan (Detail)         │ │
│  │  (Rekap List)    │  │                                      │ │
│  │                  │  │  ┌──────────────────────────────┐   │ │
│  │  ┌────────────┐  │  │  │   Pekerjaan Info             │   │ │
│  │  │ Pekerjaan  │  │  │  │   - Kode, Uraian, Satuan     │   │ │
│  │  │   #1       │  │  │  │   - Source Type              │   │ │
│  │  │ HSP: xxx   │◄─┼──┼──│   - Override BUK Controls    │   │ │
│  │  └────────────┘  │  │  └──────────────────────────────┘   │ │
│  │                  │  │                                      │ │
│  │  ┌────────────┐  │  │  ┌──────────────────────────────┐   │ │
│  │  │ Pekerjaan  │  │  │  │   Detail Items Table         │   │ │
│  │  │   #2       │  │  │  │                              │   │ │
│  │  │ HSP: xxx   │  │  │  │   A — Tenaga Kerja           │   │ │
│  │  └────────────┘  │  │  │     - TK items...            │   │ │
│  │                  │  │  │   Subtotal A: xxx            │   │ │
│  │  [Search box]    │  │  │                              │   │ │
│  │                  │  │  │   B — Bahan                  │   │ │
│  │                  │  │  │     - BHN items...           │   │ │
│  └──────────────────┘  │  │   Subtotal B: xxx            │   │ │
│                        │  │                              │   │ │
│  ┌──────────────────┐  │  │   C — Peralatan              │   │ │
│  │  Grand Total     │  │  │     - ALT items...           │   │ │
│  │  - Subtotal      │  │  │   Subtotal C: xxx            │   │ │
│  │  - PPN           │  │  │                              │   │ │
│  │  - Total         │  │  │   LAIN — Lainnya (Bundle)    │   │ │
│  └──────────────────┘  │  │     - LAIN items...          │   │ │
│                        │  │   Subtotal LAIN: xxx         │   │ │
│                        │  │                              │   │ │
│                        │  │   E — Jumlah (A+B+C+LAIN)    │   │ │
│                        │  │   F — Profit/Margin (x%)     │   │ │
│                        │  │   G — Harga Satuan (E+F)     │   │ │
│                        │  └──────────────────────────────┘   │ │
│                        └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Initial Page Load
```
User visits /project/{id}/rincian-ahsp/
    ↓
Django view renders template
    ↓
Frontend JavaScript loads
    ↓
API Call: GET /api/project/{id}/pricing/
    → Returns: project BUK%, PPN%
    ↓
API Call: GET /api/project/{id}/rekap/
    → Returns: List pekerjaan with A,B,C,LAIN,E_base,F,G,HSP,total
    ↓
Render sidebar kiri (list pekerjaan)
    ↓
Select first pekerjaan (or last selected from localStorage)
    ↓
API Call: GET /api/project/{id}/detail-ahsp/{pekerjaan_id}/
    → Returns: Detail items (TK/BHN/ALT/LAIN) with koef & harga
    ↓
API Call: GET /api/project/{id}/pekerjaan/{pekerjaan_id}/pricing/
    → Returns: Override BUK if exists
    ↓
Render sidebar kanan (detail breakdown)
    ↓
Calculate & display totals (E, F, G)
```

### 2. User Selects Different Pekerjaan
```
User clicks pekerjaan in sidebar kiri
    ↓
Abort pending API calls (prevent race condition)
    ↓
Update selectedId & highlight active item
    ↓
API Call: GET /api/project/{id}/detail-ahsp/{pekerjaan_id}/
    ↓
API Call: GET /api/project/{id}/pekerjaan/{pekerjaan_id}/pricing/
    ↓
Render sidebar kanan with new data
    ↓
Store selectedId to localStorage (for page refresh)
```

### 3. User Changes Override BUK
```
User clicks override BUK button
    ↓
Modal opens with input field
    ↓
User enters new BUK% (or clears)
    ↓
API Call: POST /api/project/{id}/pekerjaan/{pekerjaan_id}/pricing/
    Body: {"override_markup": "12.5"} or null
    ↓
Backend:
  - Validate 0 ≤ BUK ≤ 100
  - Save to Pekerjaan.markup_override_percent
  - Invalidate rekap cache
    ↓
Response: {effective_markup: "12.5"}
    ↓
Frontend:
  - Update F calculation with new BUK%
  - Re-render detail table
  - Reload rekap list (sidebar kiri) untuk update nilai
```

---

## Formula & Calculations

### Backend Calculation (services.py - compute_rekap_for_project)

#### Storage Model
```
DetailAHSPProject (Raw Storage):
  - User manually input items
  - Contains LAIN bundle items (unexpanded)

DetailAHSPExpanded (Expanded Storage):
  - Auto-generated from raw storage
  - Bundle items expanded to components
  - Used for rekap calculation
```

#### Aggregation Formula
```python
# Read from DetailAHSPExpanded (preferred) or DetailAHSPProject (fallback)
nilai_expr = koefisien × harga_satuan

# Aggregate per kategori per pekerjaan
A = Σ(nilai_expr where kategori='TK')    # Tenaga Kerja
B = Σ(nilai_expr where kategori='BHN')   # Bahan
C = Σ(nilai_expr where kategori='ALT')   # Alat/Peralatan
LAIN = Σ(nilai_expr where kategori='LAIN')  # Lainnya (usually 0 after expansion)

# Calculate totals
D = A + B + C                           # Biaya Langsung (historical)
E_base = A + B + C + LAIN               # Biaya komponen sebelum markup
markup_eff = override_BUK ?? project_BUK  # Effective markup (%)
F = E_base × (markup_eff / 100)         # Profit/Margin
G = E_base + F                          # Harga Satuan dengan markup
HSP = E_base                            # HSP = E_base (tanpa markup)
volume = VolumePekerjaan.quantity
total = G × volume                      # Total biaya pekerjaan
```

#### Example: Normal Pekerjaan (No Bundle)
```
Pekerjaan: 2.2.1.3.3 - Pemasangan bekisting
Volume: 1.000 m2

DetailAHSPExpanded:
  TK-0001: koef=0.009, harga=180000 → 1,620
  TK-0002: koef=0.026, harga=150000 → 3,900
  TK-0003: koef=0.260, harga=135000 → 35,100
  TK-0005: koef=0.520, harga=120000 → 62,400
  B-0153:  koef=0.100, harga=12000  → 1,200
  B-0159:  koef=0.018, harga=6500000 → 117,000
  B-0160:  koef=0.300, harga=45000  → 13,500

Calculation:
  A = 1,620 + 3,900 + 35,100 + 62,400 = 103,020
  B = 1,200 + 117,000 + 13,500 = 131,700
  C = 0
  LAIN = 0
  E_base = 103,020 + 131,700 = 234,720
  F = 234,720 × 10% = 23,472
  G = 234,720 + 23,472 = 258,192
  HSP = 234,720
  total = 258,192 × 1 = 258,192
```

### Frontend Calculation (rincian_ahsp.js)

#### Sidebar Kiri (Rekap List)
```javascript
// Data from API: /api/project/{id}/rekap/
rows.forEach(r => {
  const A = num(r.A)
  const B = num(r.B)
  const C = num(r.C)
  const L = num(r.LAIN || 0)
  const E = A + B + C + L
  const bukEff = (r.markup_eff != null ? Number(r.markup_eff) : projectBUK)
  const F = E * (bukEff/100)
  const G = E + F

  // Display: HSP: Rp {G}
})
```

#### Sidebar Kanan (Detail Items)
```javascript
// Data from API: /api/project/{id}/detail-ahsp/{pekerjaan_id}/
function renderDetailTable(items, effPct) {
  // Group by kategori
  const group = {TK:[], BHN:[], ALT:[], LAIN:[]}
  items.forEach(it => {
    const k = it.kategori
    if (group[k]) group[k].push(it)
  })

  // Calculate subtotals
  function addSec(title, arr) {
    let subtotal = 0
    arr.forEach(it => {
      const kf = num(it.koefisien)
      const hr = num(it.harga_satuan)
      const jm = kf * hr
      subtotal += jm
      // Render row: No | Uraian | Kode | Satuan | Koef | Harga | Jumlah
    })
    return subtotal
  }

  const A = addSec('A — Tenaga Kerja', group.TK)
  const B = addSec('B — Bahan', group.BHN)
  const C = addSec('C — Peralatan', group.ALT)
  const LAIN = addSec('LAIN — Lainnya', group.LAIN)

  const E_base = A + B + C + LAIN
  const F = E_base * (num(effPct)/100)
  const G = E_base + F

  // Render totals:
  // E — Jumlah (A+B+C+LAIN): {E_base}
  // F — Profit/Margin ({effPct}% × E): {F}
  // G — Harga Satuan (E + F): {G}
}
```

---

## Bundle System

### Concept
Bundle (Segment D / LAIN) memungkinkan user untuk mereferensikan pekerjaan lain sebagai komponen, dengan koefisien pengali.

### Example Use Case
```
Pekerjaan CUST-0001: "Pembangunan 10 Rumah Tipe 36"
  └─ LAIN "2.2.1.3.3 - Pemasangan bekisting" koef=10
     (Artinya: butuh 10 unit bekisting)
```

### Storage Flow

#### 1. User Input (DetailAHSPProject)
```
User creates pekerjaan CUST-0001
User adds LAIN item:
  - Kategori: LAIN
  - Kode: 2.2.1.3.3
  - Uraian: Pemasangan bekisting
  - Koefisien: 10.000000
  - ref_pekerjaan_id: 443 (ID pekerjaan 2.2.1.3.3)
  - harga_item: HargaItemProject (created automatically, harga_satuan=0)

Saved to: DetailAHSPProject
```

#### 2. Bundle Expansion (_populate_expanded_from_raw)
```
System calls: _populate_expanded_from_raw(project, pekerjaan)

For LAIN item with ref_pekerjaan_id:
  1. Get detail items dari pekerjaan referensi (2.2.1.3.3)
  2. Multiply ALL koefisien dengan bundle koef (10)
  3. Save to DetailAHSPExpanded

DetailAHSPExpanded created:
  TK-0001: koef = 0.009 × 10 = 0.090
  TK-0002: koef = 0.026 × 10 = 0.260
  TK-0003: koef = 0.260 × 10 = 2.600
  TK-0005: koef = 0.520 × 10 = 5.200
  B-0153:  koef = 0.100 × 10 = 1.000
  B-0159:  koef = 0.018 × 10 = 0.180
  B-0160:  koef = 0.300 × 10 = 3.000

  All items have:
    - source_detail_id: pointing to LAIN item
    - source_bundle_kode: "2.2.1.3.3"
    - expansion_depth: 1
```

#### 3. Rekap Calculation
```
Backend reads DetailAHSPExpanded:
  A = Σ(TK expanded) = 39,000 + 351,000 + 624,000 + 16,200 = 1,030,200
  B = Σ(BHN expanded) = 12,000 + 1,170,000 + 135,000 = 1,317,000
  C = 0
  LAIN = 0  ← Bundle already expanded!
  E_base = 2,347,200
  F = 234,720 (10%)
  G = 2,581,920 ✅
```

#### 4. API Detail Response
```
API: /api/project/{id}/detail-ahsp/{pekerjaan_id}/

For LAIN bundle item:
  1. Calculate bundle_total from DetailAHSPExpanded
     bundle_total = Σ(expanded_koef × harga) = 2,347,200

  2. Divide by bundle koef to get price per unit
     harga_satuan = 2,347,200 / 10 = 234,720

  3. Return to frontend:
     {
       "kategori": "LAIN",
       "kode": "2.2.1.3.3",
       "koefisien": "10.000000",
       "harga_satuan": "234720.00",  ← Price per unit
     }

Frontend displays:
  LAIN — Lainnya
    2.2.1.3.3 | Pemasangan bekisting | koef=10.000 | harga=234,720 | jumlah=2,347,200
  Subtotal LAIN: 2,347,200 ✅
```

### Bundle Types

#### Type 1: AHSP Bundle (ref_ahsp_id)
```
LAIN item references master AHSP dari database referensi
Example: "2.2.1.4.3 - Beton Mutu Rendah"
Expansion: From referensi.RincianReferensi
```

#### Type 2: Pekerjaan Bundle (ref_pekerjaan_id)
```
LAIN item references pekerjaan lain dalam same project
Example: "2.2.1.3.3 - Pemasangan bekisting"
Expansion: From DetailAHSPExpanded of referenced pekerjaan
```

### Cascade Re-expansion
```
When referenced pekerjaan is modified:
  System automatically re-expands all pekerjaan that reference it

Example:
  Pekerjaan A references Pekerjaan B (bundle)
  User edits Pekerjaan B items
  → System re-expands Pekerjaan A automatically
  → Ensures data consistency
```

---

## Recent Fixes

### Fix #1: HSP Inconsistency (2025-01-17)

**Problem**: HSP di API Rekap RAB di-overwrite dengan D (missing LAIN untuk data lama)

**Files Modified**:
- `detail_project/views_api.py` (lines 2936-2969)

**Fix**:
```python
# BEFORE:
r["HSP"] = d_direct  # Missing LAIN!

# AFTER:
r["biaya_langsung"] = d_direct  # New field
if "HSP" not in r or r["HSP"] is None:
    lain = float(r.get("LAIN") or 0.0)
    r["HSP"] = d_direct + lain  # E_base
```

**Documentation**: [HSP_FIX_FINAL_SUMMARY.md](HSP_FIX_FINAL_SUMMARY.md)

---

### Fix #2: Bundle Koefisien Not Applied (2025-01-17) ⭐ CRITICAL

**Problem**: Bundle expansion menggunakan `base_koef=1.0` hardcoded, menyebabkan koefisien bundle tidak diterapkan

**Files Modified**:
- `detail_project/services.py` (lines 1048-1057, 1115-1124)
- `detail_project/views_api.py` (lines 1350-1358)

**Bug #1 - Bundle Expansion**:
```python
# BEFORE (WRONG):
expanded_components = expand_ahsp_bundle_to_components(
    ref_ahsp_id=detail_obj.ref_ahsp_id,
    project=project,
    base_koef=Decimal('1.0'),  # ❌ Hardcoded!
    depth=1,
    visited=None
)

# AFTER (CORRECT):
bundle_koef = detail_obj.koefisien or Decimal('1.0')
expanded_components = expand_ahsp_bundle_to_components(
    ref_ahsp_id=detail_obj.ref_ahsp_id,
    project=project,
    base_koef=bundle_koef,  # ✅ Use actual bundle koef
    depth=1,
    visited=None
)
```

**Bug #2 - API Harga Satuan**:
```python
# BEFORE (WRONG):
if it.get("kategori") == HargaItemProject.KATEGORI_LAIN and bundle_total > Decimal("0"):
    effective_price = bundle_total  # ❌ Not divided by koef!

# AFTER (CORRECT):
if it.get("kategori") == HargaItemProject.KATEGORI_LAIN and bundle_total > Decimal("0"):
    if koef_decimal > Decimal("0"):
        effective_price = bundle_total / koef_decimal  # ✅ Price per unit
    else:
        effective_price = bundle_total
```

**Impact**:
- **Before**: Bundle koef=10 → Backend calculated 10x smaller → Inconsistency
- **After**: Bundle koef=10 → Backend & Frontend both correct → Consistent ✅

**Documentation**: [BUNDLE_KOEF_FIX.md](BUNDLE_KOEF_FIX.md)

---

## API Endpoints

### 1. GET /api/project/{project_id}/pricing/
**Purpose**: Get project-level pricing (BUK%, PPN%)

**Response**:
```json
{
  "ok": true,
  "markup_percent": "10.00",
  "ppn_percent": "11.00",
  "rounding_base": 10000
}
```

---

### 2. GET /api/project/{project_id}/rekap/
**Purpose**: Get rekap semua pekerjaan untuk sidebar kiri

**Response**:
```json
{
  "ok": true,
  "rows": [
    {
      "pekerjaan_id": 443,
      "kode": "2.2.1.3.3",
      "uraian": "Pemasangan bekisting",
      "satuan": "m2",
      "A": 103020.00,        // Tenaga Kerja
      "B": 131700.00,        // Bahan
      "C": 0.00,             // Peralatan
      "LAIN": 0.00,          // Lainnya (after expansion)
      "D": 234720.00,        // A+B+C
      "E_base": 234720.00,   // A+B+C+LAIN
      "F": 23472.00,         // Profit (E_base × markup%)
      "G": 258192.00,        // Harga Satuan (E_base + F)
      "HSP": 234720.00,      // E_base (tanpa markup)
      "markup_eff": 10.00,   // Effective markup (override or project)
      "volume": 1.000,
      "total": 258192.00     // G × volume
    },
    // ... more rows
  ],
  "meta": {
    "markup_percent": "10.00",
    "ppn_percent": "11.00"
  }
}
```

**Used For**: Render sidebar kiri list pekerjaan

---

### 3. GET /api/project/{project_id}/detail-ahsp/{pekerjaan_id}/
**Purpose**: Get detail items untuk pekerjaan terpilih (sidebar kanan)

**Response**:
```json
{
  "ok": true,
  "pekerjaan": {
    "id": 443,
    "kode": "2.2.1.3.3",
    "uraian": "Pemasangan bekisting",
    "satuan": "m2",
    "source_type": "ref",
    "detail_ready": true
  },
  "items": [
    {
      "id": 1234,
      "kategori": "TK",
      "kode": "TK-0001",
      "uraian": "Mandor",
      "satuan": "OH",
      "koefisien": "0.009000",
      "harga_satuan": "180000.00",
      "ref_ahsp_id": null,
      "ref_pekerjaan_id": null
    },
    {
      "id": 1235,
      "kategori": "LAIN",
      "kode": "2.2.1.3.3",
      "uraian": "Pemasangan bekisting",
      "satuan": "m2",
      "koefisien": "10.000000",
      "harga_satuan": "234720.00",  // ← Price per unit (bundle_total / koef)
      "ref_ahsp_id": null,
      "ref_pekerjaan_id": 443
    }
    // ... more items
  ],
  "meta": {
    "kategori_opts": [...],
    "read_only": false
  }
}
```

**Used For**: Render sidebar kanan detail breakdown

---

### 4. GET /api/project/{project_id}/pekerjaan/{pekerjaan_id}/pricing/
**Purpose**: Get override BUK for specific pekerjaan

**Response**:
```json
{
  "ok": true,
  "project_markup": "10.00",
  "override_markup": "12.50",  // or null if not overridden
  "effective_markup": "12.50"   // override ?? project_markup
}
```

---

### 5. POST /api/project/{project_id}/pekerjaan/{pekerjaan_id}/pricing/
**Purpose**: Set/clear override BUK for specific pekerjaan

**Request Body**:
```json
{
  "override_markup": "12.5"  // or null to clear
}
```

**Response**:
```json
{
  "ok": true,
  "saved": true,
  "project_markup": "10.00",
  "override_markup": "12.50",
  "effective_markup": "12.50"
}
```

**Side Effects**:
- Invalidates rekap cache
- Triggers re-calculation

---

## Frontend Components

### Key Files
- **rincian_ahsp.js**: Main JavaScript module (TIER 3 Complete)
  - IIFE pattern for encapsulation
  - Fetch API with AbortController
  - Map-based caching
  - Token-based race condition prevention
  - Keyboard navigation support (Ctrl+K, Arrow keys)

### Key Functions

#### loadRekap()
```javascript
// Load rekap data untuk sidebar kiri
async function loadRekap() {
  setLoading(true, 'list')
  try {
    const r = await fetch(EP_REKAP, {credentials:'same-origin'})
    const j = await safeJson(r)
    if (!r.ok || !j.ok) throw new Error('rekap fail')
    rows = j.rows || []
    renderList()
    updateGrandTotalFromRekap()
    // Restore last selected or select first
    const last = localStorage.getItem('rk-last-pkj-id')
    const target = (last && rows.some(x => String(x.pekerjaan_id)===last))
      ? Number(last)
      : filtered[0]?.pekerjaan_id
    if (target) selectItem(target)
  } finally {
    setLoading(false, 'list')
  }
}
```

#### selectItem(id)
```javascript
// Select pekerjaan dan load detail
async function selectItem(id) {
  selectedId = id
  const myToken = ++selectToken  // Race condition prevention

  setLoading(true, 'detail')
  try {
    // Parallel fetch detail + pricing
    const [detail, pp] = await Promise.all([
      getDetail(id),
      EP_POV_PREF ? getPricingItem(id) : Promise.resolve(null)
    ])

    if (myToken !== selectToken) return  // Stale request

    const effPct = pp ? Number(pp.effective_markup) : projectBUK
    renderDetailTable(detail.items, effPct)

    localStorage.setItem('rk-last-pkj-id', String(id))
  } finally {
    setLoading(false, 'detail')
  }
}
```

#### renderDetailTable(items, effPct)
```javascript
// Render detail breakdown di sidebar kanan
function renderDetailTable(items, effPct) {
  const group = {TK:[], BHN:[], ALT:[], LAIN:[]}
  items.forEach(it => {
    const k = it.kategori?.toUpperCase()
    if (group[k]) group[k].push(it)
  })

  const A = addSec('A — Tenaga Kerja', group.TK)
  const B = addSec('B — Bahan', group.BHN)
  const C = addSec('C — Peralatan', group.ALT)
  const LAIN = addSec('LAIN — Lainnya', group.LAIN)

  const E_base = A + B + C + LAIN
  const F = E_base * (num(effPct)/100)
  const G = E_base + F

  // Render E, F, G rows
  // ...
}
```

---

## Testing

### Manual Testing Checklist

#### Basic Flow
- [ ] Page loads without errors
- [ ] Sidebar kiri displays all pekerjaan
- [ ] Sidebar kanan displays detail for first pekerjaan
- [ ] Grand Total displays correct values
- [ ] Search pekerjaan works
- [ ] Select different pekerjaan loads correct detail

#### Bundle Testing
- [ ] Pekerjaan with bundle (LAIN item) displays correctly
- [ ] Bundle koef > 1 applied correctly
- [ ] Harga satuan bundle = (sum of components) / koef
- [ ] Jumlah bundle = harga_satuan × koef
- [ ] Sidebar kiri & kanan show consistent values

#### Override BUK Testing
- [ ] Override BUK modal opens
- [ ] Can set override value (0-100)
- [ ] Can clear override (reset to project default)
- [ ] F value updates with new BUK%
- [ ] G value updates correctly
- [ ] Sidebar kiri reloads with new values

### Automated Testing

#### Backend Tests
```bash
# HSP consistency verification
python manage.py verify_hsp_fix --project=110

# Bundle koef fix verification
python manage.py test_bundle_koef_fix --project=110

# Check for LAIN items across all projects
python manage.py check_lain_items
```

#### Integration Tests
```bash
pytest detail_project/tests/test_rekap_rab_with_buk_and_lain.py -v
pytest detail_project/tests/test_rekap_consistency.py -v
pytest detail_project/tests/test_rincian_ahsp.py -v
```

---

## Troubleshooting

### Issue: Sidebar Kiri & Kanan Menampilkan Nilai Berbeda

**Symptoms**:
- Sidebar kiri: HSP = Rp 258.192
- Sidebar kanan: G = Rp 2.581.920

**Cause**: Bundle koefisien tidak diterapkan di backend expansion

**Solution**:
1. Verify fix applied: Check [services.py:1050](../services.py#L1050) menggunakan `bundle_koef`
2. Re-expand bundles: See [BUNDLE_KOEF_FIX.md](BUNDLE_KOEF_FIX.md#re-expansion-steps)
3. Clear cache: `python manage.py shell -c "from django.core.cache import cache; cache.clear()"`
4. Hard refresh browser: Ctrl+F5

---

### Issue: Bundle Harga Satuan Salah

**Symptoms**: LAIN item harga_satuan = 0 or very large number

**Cause**:
- Bundle belum di-expand ke DetailAHSPExpanded
- API tidak membagi bundle_total dengan koefisien

**Solution**:
1. Check DetailAHSPExpanded exists:
   ```python
   from detail_project.models import DetailAHSPExpanded, Pekerjaan
   pkj = Pekerjaan.objects.get(id=PEKERJAAN_ID)
   expanded = DetailAHSPExpanded.objects.filter(pekerjaan=pkj)
   print(f"Expanded items: {expanded.count()}")
   ```

2. If count = 0, re-expand:
   ```python
   from detail_project.services import _populate_expanded_from_raw
   from django.db import transaction
   with transaction.atomic():
       _populate_expanded_from_raw(project, pkj)
   ```

3. Verify API fix: Check [views_api.py:1355](../views_api.py#L1355) does division

---

### Issue: Override BUK Tidak Tersimpan

**Symptoms**: Override BUK hilang setelah page refresh

**Cause**:
- API validation error (BUK < 0 or > 100)
- Transaction rollback
- Cache not invalidated

**Solution**:
1. Check console for API errors
2. Verify value range: 0 ≤ BUK ≤ 100
3. Check database:
   ```python
   from detail_project.models import Pekerjaan
   pkj = Pekerjaan.objects.get(id=PEKERJAAN_ID)
   print(f"Override BUK: {pkj.markup_override_percent}")
   ```

---

### Issue: Grand Total Tidak Update

**Symptoms**: Grand Total tidak berubah setelah edit

**Cause**:
- Rekap cache not invalidated
- PPN% not loaded

**Solution**:
1. Hard refresh: Ctrl+F5
2. Clear cache manually
3. Check PPN loaded: Console → `projectPPN`

---

## Appendix

### Keyboard Shortcuts
- **Ctrl+K**: Focus search box
- **Shift+O**: Open override BUK modal
- **Arrow Up/Down**: Navigate pekerjaan list
- **Enter**: Select highlighted pekerjaan
- **Esc**: Close modal

### Browser Console Debug
```javascript
// Check current state
console.log('Selected ID:', selectedId)
console.log('Rows data:', rows)
console.log('Project BUK:', projectBUK)
console.log('Project PPN:', projectPPN)

// Check cached detail
console.log('Cached details:', cacheDetail)

// Force reload rekap
loadRekap()

// Force reload detail for current pekerjaan
selectItem(selectedId)
```

### Performance Tips
1. **Pagination**: Consider pagination for projects with >1000 pekerjaan
2. **Lazy Loading**: Load detail only when pekerjaan selected (already implemented)
3. **Caching**: Detail data cached to avoid redundant fetches (already implemented)
4. **Debouncing**: Search debounced 120ms (already implemented)

---

## Related Documentation

- [HSP_FIX_FINAL_SUMMARY.md](HSP_FIX_FINAL_SUMMARY.md) - HSP inconsistency fix
- [BUNDLE_KOEF_FIX.md](BUNDLE_KOEF_FIX.md) - Bundle koefisien fix ⭐
- [FIX_HSP_INCONSISTENCY.md](FIX_HSP_INCONSISTENCY.md) - Technical HSP fix details
- [BUNDLE_EXPANSION_FIX.md](BUNDLE_EXPANSION_FIX.md) - Bundle expansion system

---

**Maintained By**: Development Team
**Last Review**: 2025-01-17
**Status**: Complete & Up-to-date
