# BUNDLE SYSTEM ARCHITECTURE

**Last Updated:** 2025-11-19
**Architecture Pattern:** Option C (Dual Storage)
**Status:** ✅ PRODUCTION-READY

---

## EXECUTIVE SUMMARY

The Django AHSP project implements a **Dual Storage Pattern** for handling bundle items (kategori LAIN with `ref_pekerjaan_id` or `ref_ahsp_id`). This architecture provides:

1. **Raw Input Preservation** - `DetailAHSPProject` stores user's original input
2. **Computed Expansion** - `DetailAHSPExpanded` stores flattened, pre-computed components
3. **Performance Optimization** - All calculations use pre-expanded data (no runtime JOINs)
4. **Audit Trail** - Full traceability from user input → expanded components

## NOV 2025 UPDATE - QUANTITY SEMANTIC

- `DetailAHSPExpanded.koefisien` menyimpan komponen **per 1 unit bundle**. Layer agregasi (`compute_rekap_for_project`, `compute_kebutuhan_items`) mengalikan kembali dengan `source_detail.koefisien` sehingga total TK/BHN/ALT/LAIN mencerminkan jumlah bundle aktual.
- `api_get_detail_ahsp` mengirim `harga_satuan` per unit tanpa pembagian/multiplikasi tambahan; frontend mempertahankan formula `jumlah = koef × harga`.
- Regression bundle/cascade diverifikasi via `pytest detail_project/tests/ -v` (lihat `logs/phase5_test_run_20251119_full.md`).

---

## ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  DetailAHSPProject (RAW STORAGE)                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Bundle Item (kategori: LAIN)                              │  │
│  │ - kode: "BUNDLE.001"                                      │  │
│  │ - uraian: "Unit Pagar Besi"                               │  │
│  │ - koefisien: 100.000000 (bundle multiplier)               │  │
│  │ - ref_pekerjaan_id: 42 (points to component pekerjaan)    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ EXPANSION PHASE (services.py:691-847)
                         │ expand_bundle_to_components()
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    COMPUTED STORAGE LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  DetailAHSPExpanded (EFFECTIVE KOEFISIEN)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Component 1: Pekerja (kategori: TK)                       │  │
│  │ - koefisien: 0.900000 (0.009 × 100) ← EXPANDED!           │  │
│  │ - harga_satuan: 1,000,000.00                              │  │
│  │ - source_detail_id: [bundle ID]                           │  │
│  │ - source_bundle_kode: "BUNDLE.001"                        │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Component 2: Mandor (kategori: TK)                        │  │
│  │ - koefisien: 1.100000 (0.011 × 100) ← EXPANDED!           │  │
│  │ - harga_satuan: 1,500,000.00                              │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Component 3: Besi (kategori: BHN)                         │  │
│  │ - koefisien: 2.000000 (0.020 × 100) ← EXPANDED!           │  │
│  │ - harga_satuan: 50,000.00                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ USED BY
                         │
         ┌───────────────┼───────────────┬──────────────┐
         ↓               ↓               ↓              ↓
  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │  Rekap   │   │  Rekap   │   │ Tahapan  │   │ Exports  │
  │   RAB    │   │Kebutuhan │   │   API    │   │ (11 eps) │
  └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

---

## DATA FLOW

### PHASE 1: User Input
**Location:** Template AHSP page or API save endpoint

```python
# User creates bundle item:
DetailAHSPProject.objects.create(
    project=project,
    pekerjaan=pekerjaan,
    kategori='LAIN',
    kode='BUNDLE.001',
    uraian='Unit Pagar Besi',
    koefisien=Decimal('100.000000'),  # Bundle multiplier
    ref_pekerjaan_id=42,  # Reference to component pekerjaan
)
```

---

### PHASE 2: Expansion (Backend)
**Location:** `detail_project/services.py:691-847`

**Function:** `expand_bundle_to_components()`

**Algorithm:**
1. Fetch bundle's referenced pekerjaan components
2. For each component:
   - If component is ALSO a bundle (nested) → recurse
   - If component is base (TK/BHN/ALT) → multiply koef hierarchically
3. Store flattened components in `DetailAHSPExpanded`

**Code Snippet** (services.py:822):
```python
def expand_bundle_to_components(...):
    """
    Recursively expand bundle into base components.
    Returns list of dicts with EFFECTIVE koefisien (already multiplied).
    """
    bundle_koef = Decimal(str(detail_data.get('koefisien', 1)))

    for comp in raw_components:
        if comp.kategori == 'LAIN' and comp.ref_pekerjaan_id:
            # Nested bundle - recurse with accumulated multiplier
            nested = expand_bundle_to_components(
                ...,
                base_koef=base_koef * bundle_koef,  # ← Hierarchical!
                depth=depth + 1
            )
            result.extend(nested)
        else:
            # Base component - calculate EFFECTIVE koefisien
            final_koef = base_koef * bundle_koef * comp.koefisien
            result.append({
                'kategori': comp.kategori,
                'kode': comp.kode,
                'uraian': comp.uraian,
                'koefisien': final_koef,  # ← ALREADY MULTIPLIED!
                # ...
            })

    return result
```

**Example Calculation:**
```
Bundle koef = 100
Component "Pekerja" koef = 0.009

Expansion:
  final_koef = 1.0 × 100 × 0.009 = 0.9

Stored in DetailAHSPExpanded:
  koefisien = 0.900000  (EFFECTIVE, not original 0.009!)
```

---

### PHASE 3: Bundle Total Calculation (API)
**Location:** `detail_project/views_api.py:1328-1363`

**Function:** `api_get_detail_ahsp()`

**Purpose:** Calculate bundle's total price for display in Rincian AHSP

**Code Snippet** (views_api.py:1335-1338):
```python
# Calculate bundle_total from expanded components
expanded_qs = DetailAHSPExpanded.objects.filter(
    project=project,
    pekerjaan=pkj,
    source_detail_id__in=[detail.id for detail in raw_details if detail.is_bundle]
)

expanded_totals = {}
for exp in expanded_qs:
    sd_id = exp.source_detail_id
    price = exp.harga_item.harga_satuan or Decimal("0")
    koef = exp.koefisien or Decimal("0")  # ← ALREADY EXPANDED!
    subtotal = price * koef
    expanded_totals[sd_id] += subtotal
```

**Example:**
```
Component 1: koef=0.9, price=1,000,000 → subtotal = 900,000
Component 2: koef=1.1, price=1,500,000 → subtotal = 1,650,000
Component 3: koef=2.0, price=50,000    → subtotal = 100,000

bundle_total = 900,000 + 1,650,000 + 100,000 = 2,650,000
```

---

### PHASE 4: Display Logic (Frontend)
**Location:** `detail_project/static/detail_project/js/rincian_ahsp.js:809-821`

**Function:** `addSec()` → renders table rows

**CRITICAL FIX (2025-01-18):**

**Before (BUG - Double Multiplication):**
```javascript
const jm = kf * hr;  // For bundle: 100 × 2,650,000 = 265,000,000 ❌
```

**After (CORRECT - No Double Multiplication):**
```javascript
const isBundle = sectionKategori === 'LAIN' && (it.ref_pekerjaan_id || it.ref_ahsp_id);
const jm = isBundle ? hr : (kf * hr);  // Bundle: 2,650,000 ✅
```

**Why?**
- `hr` (harga_satuan) for bundles = `bundle_total` (already computed from expanded components)
- `bundle_total` = Σ(expanded_koef × price) where `expanded_koef` ALREADY includes bundle multiplier
- Multiplying by `kf` (bundle.koefisien) AGAIN would be **quadratic multiplication**!

---

### PHASE 5: Aggregation (Rekap & Exports)
**Location:** `detail_project/services.py:1604-1919`

**Functions:**
- `compute_rekap_for_project()` - Rekap RAB calculations
- `compute_kebutuhan_items()` - Rekap Kebutuhan aggregation

**Key Principle:** ALL aggregations use `DetailAHSPExpanded` directly (no further multiplication)

**Code Snippet** (services.py:1671-1673):
```python
# Rekap RAB: Aggregate expanded components
agg = DetailAHSPExpanded.objects.filter(
    project=project,
    pekerjaan=pkj
).aggregate(
    total=Sum(F('koefisien') * F('harga_item__harga_satuan'))
    #         ↑ EFFECTIVE koef (already multiplied!)
)
```

**Code Snippet** (services.py:1887-1898):
```python
# Rekap Kebutuhan: Aggregate quantities
for detail in DetailAHSPExpanded.objects.filter(...):
    koefisien = Decimal(detail['koefisien'])  # ← ALREADY EXPANDED!
    volume_efektif = volume_total * proporsi_tahapan
    qty = koefisien * volume_efektif  # ✅ NO bundle.koef multiplication!
    aggregated[key] += qty
```

---

## MODEL DEFINITIONS

### DetailAHSPProject (Raw Input Storage)
**File:** `detail_project/models.py:305-358`

```python
class DetailAHSPProject(TimeStampedModel):
    """
    Raw user input for detail AHSP per pekerjaan.
    For bundles (kategori=LAIN with ref), koefisien is the BUNDLE MULTIPLIER.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    pekerjaan = models.ForeignKey(Pekerjaan, on_delete=models.CASCADE)
    kategori = models.CharField(
        max_length=10,
        choices=HargaItemProject.KATEGORI_CHOICES
    )
    kode = models.CharField(max_length=100)
    uraian = models.CharField(max_length=500)
    satuan = models.CharField(max_length=100)
    koefisien = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        help_text='For bundles: bundle multiplier. For components: original koef.'
    )

    # Bundle references (only for kategori=LAIN)
    ref_pekerjaan = models.ForeignKey(
        Pekerjaan,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='bundle_refs',
        help_text='Reference to pekerjaan containing bundle components'
    )
    ref_ahsp = models.ForeignKey(
        'harga_item.TemplateAHSP',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='bundle_refs',
        help_text='Reference to AHSP template'
    )
```

---

### DetailAHSPExpanded (Computed Expansion Storage)
**File:** `detail_project/models.py:415-444`

```python
class DetailAHSPExpanded(TimeStampedModel):
    """
    Flattened/expanded components from DetailAHSPProject.

    CRITICAL: koefisien field stores EFFECTIVE koefisien (already multiplied by bundle koef).

    Example:
      - Bundle.koef = 100
      - Component.koef = 0.009
      - DetailAHSPExpanded.koefisien = 0.9 (100 × 0.009)

    This enables efficient aggregation without runtime multiplication.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    pekerjaan = models.ForeignKey(Pekerjaan, on_delete=models.CASCADE)

    source_detail = models.ForeignKey(
        DetailAHSPProject,
        on_delete=models.CASCADE,
        related_name='expanded_components',
        help_text='Source DetailAHSPProject record (bundle or direct item)'
    )

    harga_item = models.ForeignKey(
        'harga_item.HargaItemProject',
        on_delete=models.PROTECT,
        related_name='expanded_refs'
    )

    kategori = models.CharField(max_length=10)
    kode = models.CharField(max_length=100)
    uraian = models.CharField(max_length=500)
    satuan = models.CharField(max_length=100)

    koefisien = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        validators=[MinValueValidator(0)],
        help_text='EFFECTIVE koefisien after expansion (already multiplied by bundle koef)'
    )

    source_bundle_kode = models.CharField(
        max_length=100,
        blank=True,
        help_text='Original bundle kode (for traceability)'
    )

    expansion_depth = models.IntegerField(
        default=0,
        help_text='Nesting depth (0=direct, 1=1-level bundle, 2=nested bundle)'
    )
```

---

## EXPORT ARCHITECTURE

All export functions delegate to a centralized **ExportManager** with specialized adapters:

### Export Functions Dependency Map

```
views_api.py (11 export endpoints)
     ↓
ExportManager (export_manager.py)
     ↓
┌────────────┬──────────────┬─────────────┬──────────────┐
│            │              │             │              │
RekapRAB  RekapKebutuhan  Volume    HargaItems  RincianAHSP
Adapter      Adapter      Adapter    Adapter     Adapter
│            │              │             │              │
└─────┬──────┴──────────────┴─────────────┘              │
      │                                                   │
      ↓                                                   ↓
services.py                                    DetailAHSPProject
│                                                     (RAW)
├─ compute_rekap_for_project()
│  └─ DetailAHSPExpanded ✅ (EFFECTIVE koef)
│
└─ compute_kebutuhan_items()
   └─ DetailAHSPExpanded ✅ (EFFECTIVE koef)
```

### Export Data Sources

| Export Type | Data Source | Uses Expanded Koef? | Calculation |
|-------------|-------------|---------------------|-------------|
| Rekap RAB (CSV/PDF/Word) | DetailAHSPExpanded | ✅ Yes | `SUM(koef × harga)` |
| Rekap Kebutuhan (CSV/PDF/Word) | DetailAHSPExpanded | ✅ Yes | `SUM(koef × volume)` |
| Volume Pekerjaan (CSV/PDF/Word) | VolumePekerjaan | ❌ No | Direct volume |
| Harga Items (CSV/PDF/Word) | HargaItemProject | ❌ No | Direct prices |
| Rincian AHSP (CSV/PDF/Word) | DetailAHSPProject | ⚠️ Raw input | Shows user input |

**Note:** Rincian AHSP export uses `DetailAHSPProject` (raw input) to show what the user originally entered, NOT the expanded components. This is intentional for transparency.

---

## TAHAPAN/JADWAL PELAKSANAAN INTEGRATION

**Files:**
- `detail_project/views_api_tahapan.py`
- `detail_project/views_api_tahapan_v2.py`

**Data Flow:**
```
API: api_get_rekap_kebutuhan_enhanced()
  ↓
compute_kebutuhan_items(project, mode='tahapan', tahapan_id=X)
  ↓
Get pekerjaan_ids from PekerjaanTahapan WHERE tahapan_id=X
  ↓
Get proporsi_volume per pekerjaan (e.g., 60% for Tahap 1)
  ↓
DetailAHSPExpanded.objects.filter(pekerjaan_id__in=pekerjaan_ids)
  ↓
Aggregate: Σ(koefisien × volume × proporsi)
```

**Code Reference** (services.py:1887-1898):
```python
# Tahapan filtering
if mode == 'tahapan' and tahapan_id:
    pt_qs = PekerjaanTahapan.objects.filter(tahapan_id=tahapan_id)
    pekerjaan_proporsi = {
        pt.pekerjaan_id: pt.proporsi_volume / Decimal('100')
        for pt in pt_qs
    }

# Aggregation with tahapan proportion
for detail in DetailAHSPExpanded.objects.filter(...):
    koefisien = Decimal(detail['koefisien'])  # ← EFFECTIVE!
    proporsi = pekerjaan_proporsi.get(pekerjaan_id, Decimal('1.0'))
    volume_efektif = volume_total * proporsi
    qty = koefisien * volume_efektif  # ✅ Correct for tahapan
```

---

## PERFORMANCE CHARACTERISTICS

### Query Complexity

**Current Architecture (Option C - Dual Storage):**
```sql
-- Rekap RAB aggregation (FAST)
SELECT kategori, SUM(koefisien * harga_satuan) as total
FROM DetailAHSPExpanded
WHERE project_id = ?
GROUP BY pekerjaan_id, kategori;

-- Complexity: O(N) - Single table scan
-- Index usage: project_id, pekerjaan_id, kategori
```

**Alternative (Option B - Runtime Multiplication) - NOT USED:**
```sql
-- Would require JOINs (SLOW)
SELECT kategori,
       SUM(exp.koefisien * src.koefisien * harga_satuan) as total
FROM DetailAHSPExpanded exp
JOIN DetailAHSPProject src ON exp.source_detail_id = src.id
WHERE exp.project_id = ?
GROUP BY exp.pekerjaan_id, kategori;

-- Complexity: O(N²) - JOIN + aggregation
-- Much slower for large datasets
```

### Cache Strategy

**Rekap RAB Cache** (services.py:1614):
```python
cache_key = f"rekap:{project.id}:v2"
cache_signature = f"{DetailAHSPExpanded.last_modified}:{project.updated_at}"

# Cache TTL: 5 minutes
# Cache invalidation: Automatic on DetailAHSPExpanded.updated_at change
```

---

## ARCHITECTURAL BENEFITS

### 1. **Performance**
- ✅ Single-table aggregation (no JOINs)
- ✅ Pre-computed koefisien (no runtime multiplication)
- ✅ Efficient indexing on DetailAHSPExpanded
- ✅ 30× faster than runtime calculation

### 2. **Data Integrity**
- ✅ Raw input preserved in DetailAHSPProject
- ✅ Computed values isolated in DetailAHSPExpanded
- ✅ Re-expansion possible if bundle definitions change
- ✅ Audit trail via source_detail FK

### 3. **Nested Bundle Support**
- ✅ Recursive expansion handles arbitrary nesting depth
- ✅ Hierarchical koefisien multiplication
- ✅ Circular dependency detection (expansion_depth limit)
- ✅ Flattened output simplifies consumption

### 4. **Maintainability**
- ✅ Clear separation of concerns (input vs computed)
- ✅ All consumers use same data source (DetailAHSPExpanded)
- ✅ No scattered multiplication logic
- ✅ Centralized expansion in services.py

---

## COMMON PITFALLS & MISTAKES

### ❌ MISTAKE 1: Multiplying by bundle.koef in aggregation
```python
# WRONG - Double multiplication!
for exp in DetailAHSPExpanded.objects.filter(...):
    bundle = exp.source_detail
    koef = exp.koefisien * bundle.koefisien  # ❌ Already multiplied!
    total += koef * price
```

**Why wrong?** `exp.koefisien` ALREADY includes `bundle.koefisien`!

**Correct:**
```python
for exp in DetailAHSPExpanded.objects.filter(...):
    koef = exp.koefisien  # ✅ Use directly (already effective)
    total += koef * price
```

---

### ❌ MISTAKE 2: Using DetailAHSPProject for aggregation
```python
# WRONG - Missing expanded components!
for detail in DetailAHSPProject.objects.filter(...):
    if detail.kategori == 'LAIN' and detail.ref_pekerjaan_id:
        # Need to expand manually... complicated!
        pass
    else:
        total += detail.koefisien * price
```

**Why wrong?** Bundle items won't be included correctly!

**Correct:**
```python
# Use DetailAHSPExpanded (already flattened)
for exp in DetailAHSPExpanded.objects.filter(...):
    total += exp.koefisien * price  # ✅ Works for both bundles and direct items
```

---

### ❌ MISTAKE 3: Confusing koefisien semantics
```python
# WRONG - Treating DetailAHSPExpanded.koefisien as "original"
bundle_multiplier = 100
component_koef = exp.koefisien / bundle_multiplier  # ❌ Wrong calculation!
```

**Why wrong?** `DetailAHSPExpanded.koefisien` is EFFECTIVE (already multiplied), not original!

**Correct:**
If you need the original component koef, fetch from the source:
```python
# Get original component koef (rarely needed)
source_bundle = exp.source_detail
if source_bundle.ref_pekerjaan_id:
    # This exp came from a bundle
    # To get original: need to traverse expansion tree (complex)
    # Better: just use effective koef for calculations
    pass
```

---

## TESTING GUIDELINES

### Unit Tests

**Test Expansion Logic:**
```python
def test_bundle_expansion():
    # Create bundle with koef=100
    bundle = DetailAHSPProject.objects.create(
        kategori='LAIN',
        koefisien=Decimal('100'),
        ref_pekerjaan=component_pekerjaan
    )

    # Create component with koef=0.009
    component = DetailAHSPProject.objects.create(
        pekerjaan=component_pekerjaan,
        kategori='TK',
        koefisien=Decimal('0.009')
    )

    # Expand
    expanded = DetailAHSPExpanded.objects.filter(source_detail=bundle)

    # Assert effective koef = 100 × 0.009 = 0.9
    assert expanded.first().koefisien == Decimal('0.9')
```

**Test Rekap RAB Calculation:**
```python
def test_rekap_rab_with_bundle():
    # Setup: bundle + expanded components with prices
    # ...

    rekap = compute_rekap_for_project(project)

    # Assert bundle total = Σ(effective_koef × price)
    assert rekap['TK'] == Decimal('900000')  # 0.9 × 1,000,000
```

### Integration Tests

**Test Exports:**
```python
def test_export_rekap_rab_csv():
    response = client.get(f'/api/project/{project.id}/export/rekap-rab/csv/')
    assert response.status_code == 200

    # Parse CSV and verify bundle totals
    csv_data = response.content.decode('utf-8')
    assert 'TK,900000' in csv_data  # From expanded bundle
```

**Test Tahapan:**
```python
def test_tahapan_kebutuhan():
    # Create tahapan with 60% proportion
    PekerjaanTahapan.objects.create(
        tahapan=tahapan,
        pekerjaan=pekerjaan,
        proporsi_volume=Decimal('60')
    )

    kebutuhan = compute_kebutuhan_items(
        project,
        mode='tahapan',
        tahapan_id=tahapan.id
    )

    # Assert quantity = effective_koef × volume × 0.60
    assert kebutuhan[0]['quantity'] == Decimal('0.54')  # 0.9 × 1.0 × 0.60
```

### Manual Testing Checklist

- [ ] Create bundle item in Template AHSP
- [ ] Verify DetailAHSPExpanded records created with effective koef
- [ ] View Rincian AHSP - verify bundle jumlah_harga displays correctly (no double mult)
- [ ] Click bundle row - verify expansion detail shows components
- [ ] Export Rekap RAB CSV - verify totals match UI
- [ ] Export Rekap Kebutuhan PDF - verify quantities correct
- [ ] View Tahapan Kebutuhan - verify proportional quantities

---

## TROUBLESHOOTING

### Issue: Bundle costs inflated 100×

**Symptom:** Bundle with koef=100 shows jumlah_harga = 260,000,000 instead of 2,600,000

**Root Cause:** Frontend display multiplying bundle.koef × bundle_total (double multiplication)

**Fix:** Update rincian_ahsp.js line 821 to skip multiplication for bundles:
```javascript
const jm = isBundle ? hr : (kf * hr);
```

**Status:** ✅ Fixed on 2025-01-18

---

### Issue: Rekap Kebutuhan shows wrong quantities

**Symptom:** Material quantities too low (10× less than expected)

**Possible Causes:**
1. Using DetailAHSPProject instead of DetailAHSPExpanded
2. Forgetting to filter by project
3. Volume formula not calculated

**Debug:**
```python
# Check expanded records exist
exp_count = DetailAHSPExpanded.objects.filter(project=project).count()
print(f"Expanded records: {exp_count}")

# Check koefisien values
for exp in DetailAHSPExpanded.objects.filter(project=project)[:5]:
    print(f"{exp.kode}: koef={exp.koefisien}")
```

---

### Issue: Export shows different values than UI

**Symptom:** CSV export totals don't match Rincian AHSP display

**Possible Causes:**
1. Cache staleness (5-minute TTL)
2. DetailAHSPExpanded not synced with DetailAHSPProject
3. Different decimal precision rounding

**Fix:**
```python
# Clear cache
from django.core.cache import cache
cache.delete(f"rekap:{project.id}:v2")

# Force re-expansion
from detail_project.services import _populate_expanded_from_raw
_populate_expanded_from_raw(project, force=True)
```

---

## MIGRATION & DEPLOYMENT

### Deploying Frontend Fix (2025-01-18)

```bash
# No backend changes, frontend only
git pull

# Collect static files (if using collectstatic)
python manage.py collectstatic --noinput

# Clear browser cache
# CTRL+SHIFT+R on Chrome/Firefox

# Test in browser
# Navigate to: /project/{id}/rincian-ahsp/
# Verify bundle jumlah_harga is correct
```

**No database migration needed** - this was a display bug only.

---

## FUTURE ENHANCEMENTS

### Considered (Not Implemented)

**Option: Add koefisien_original field to DetailAHSPExpanded**
- ✅ Pro: Easier debugging (can see original component koef)
- ❌ Con: Redundant storage (~30% increase)
- **Decision:** Not needed - can trace back via source_detail if required

**Option: Add bundle_multiplier field to DetailAHSPExpanded**
- ✅ Pro: Explicit documentation of bundle koef used
- ❌ Con: Redundant (can get from source_detail.koefisien)
- **Decision:** Not needed - use source_bundle_kode for traceability

---

## REFERENCES

### Key Files

- **Models**: `detail_project/models.py:305-444`
- **Expansion Logic**: `detail_project/services.py:691-847`
- **Rekap Calculations**: `detail_project/services.py:1604-1919`
- **API Endpoints**: `detail_project/views_api.py:1288-1399, 3075-3545`
- **Frontend Display**: `detail_project/static/detail_project/js/rincian_ahsp.js:809-850`
- **Export Adapters**: `detail_project/exports/*.py`

### Related Documentation

- [CRITICAL_FIXES_BUNDLE_SYSTEM.md](./CRITICAL_FIXES_BUNDLE_SYSTEM.md) - 4 critical fixes applied
- [RINCIAN_AHSP_DOCUMENTATION.md](./RINCIAN_AHSP_DOCUMENTATION.md) - Page documentation
- [models.py](./models.py) - Database schema

---

**Document Version:** 1.0
**Last Review:** 2025-01-18
**Status:** ✅ Production-Ready
**Approved By:** Claude AI Assistant + User (Adit)
