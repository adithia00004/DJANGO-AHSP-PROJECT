# REFACTOR ROADMAP: Bundle Quantity Semantic
**Project:** Django AHSP - Bundle System Refactoring
**Date:** 2025-01-18
**Objective:** Change bundle koefisien from "expansion multiplier" to "quantity" semantic
**Status:** 🟡 PLANNING
**Risk Level:** 🔴 HIGH (Major architectural change)
**Estimated Duration:** 3-4 days (with comprehensive testing)

---

## EXECUTIVE SUMMARY

### Current Problem:
User mengubah bundle koefisien (e.g., 10 → 5) dengan ekspektasi:
- ✅ Harga Satuan: **TETAP** (harga per 1 unit bundle)
- ✅ Jumlah Harga: **BERUBAH** (quantity × harga satuan)

Sistem saat ini:
- ❌ Harga Satuan: **BERUBAH** (bundle_total / new_koef)
- ❌ Jumlah Harga: **TETAP** (bundle_total)

### Root Cause:
Bundle koefisien digunakan sebagai **"expansion multiplier"** (bukan quantity):
```
expanded_koef = component.koef × bundle.koef
bundle_total = Σ(expanded_koef × harga)
```

### Solution:
Change to **"quantity semantic"**:
```
expanded_koef = component.koef  (NO multiplication)
bundle_total_per_unit = Σ(component.koef × harga)
jumlah = bundle.koef × bundle_total_per_unit
```

---

## IMPACT ANALYSIS

### Files Affected (Estimated):

| File | Changes | Risk | Lines Modified |
|------|---------|------|----------------|
| `detail_project/services.py` | Expansion logic | 🔴 HIGH | ~50 lines |
| `detail_project/views_api.py` | API responses | 🟡 MEDIUM | ~30 lines |
| `detail_project/static/detail_project/js/rincian_ahsp.js` | Display logic | 🟢 LOW | ~10 lines |
| `detail_project/tests/test_*.py` | All bundle tests | 🔴 HIGH | ~200 lines |
| `detail_project/BUNDLE_SYSTEM_ARCHITECTURE.md` | Documentation | 🟢 LOW | Full rewrite |

### Features Affected:

| Feature | Impact | Requires Testing |
|---------|--------|------------------|
| **Template AHSP** (save) | 🔴 CRITICAL | ✅ Full test suite |
| **Rincian AHSP** (display) | 🟡 MEDIUM | ✅ Display tests |
| **Rekap RAB** (aggregation) | 🔴 CRITICAL | ✅ Calculation tests |
| **Rekap Kebutuhan** (aggregation) | 🔴 CRITICAL | ✅ Quantity tests |
| **Tahapan API** | 🔴 CRITICAL | ✅ Integration tests |
| **Exports (CSV/PDF/Word)** | 🔴 CRITICAL | ✅ All export formats |
| **Bundle Expansion API** | 🟡 MEDIUM | ✅ API tests |

---

## REFACTOR PHASES

### PHASE 0: Pre-Flight Checks ✈️
**Duration:** 2-3 hours
**Objective:** Ensure baseline stability and backup

#### Tasks:
- [ ] **0.1** Create full database backup
  ```bash
  python manage.py dumpdata > backup_pre_refactor_$(date +%Y%m%d).json
  ```

- [ ] **0.2** Run full test suite (baseline)
  ```bash
  python manage.py test detail_project
  ```
  - Record all passing tests
  - Note any existing failures (should be 0!)

- [ ] **0.3** Create feature branch
  ```bash
  git checkout -b refactor/bundle-quantity-semantic
  ```

- [ ] **0.4** Document current behavior
  - Create test project with 3-5 bundles
  - Screenshot all displays (Rincian AHSP, Rekap RAB, Rekap Kebutuhan)
  - Export CSV/PDF for baseline comparison

- [ ] **0.5** Create rollback plan
  - Document steps to revert changes
  - Test rollback procedure on dummy data

**Success Criteria:**
- ✅ All tests passing (baseline established)
- ✅ Backup verified (can restore)
- ✅ Baseline screenshots saved

---

### PHASE 1: Update Data Model & Expansion Logic 🔧
**Duration:** 4-6 hours
**Objective:** Change expansion to NOT multiply bundle koef
**Risk:** 🔴 HIGH (core logic change)

#### 1.1 Update Expansion Logic (services.py)

**File:** `detail_project/services.py`
**Function:** `expand_bundle_to_components()` (lines 691-847)

**Current Code (line 822):**
```python
# Base component (TK/BHN/ALT) - add with multiplied koefisien
final_koef = comp.koefisien * bundle_koef * base_koef
```

**New Code:**
```python
# Base component (TK/BHN/ALT) - store ORIGINAL koefisien
# Bundle koef will be applied during aggregation/display
final_koef = comp.koefisien * base_koef  # NO bundle_koef multiplication!

# Store bundle_koef separately for reference
bundle_multiplier = bundle_koef
```

**Changes Required:**
```python
# Line 822: Remove bundle_koef from multiplication
# OLD:
final_koef = comp.koefisien * bundle_koef * base_koef

# NEW:
final_koef = comp.koefisien * base_koef  # Component koef only

# Line 830+: Add bundle_multiplier to result dict
result.append({
    'kategori': comp['kategori'],
    'kode': comp['kode'],
    'uraian': comp['uraian'],
    'satuan': comp['satuan'],
    'koefisien': final_koef,  # Original component koef
    'bundle_multiplier': bundle_koef,  # NEW: Store for later use
    # ...
})
```

#### 1.2 Update DetailAHSPExpanded Creation

**File:** `detail_project/views_api.py`
**Function:** `api_save_detail_ahsp_for_pekerjaan()` (lines 1827-1920)

**Changes:**
```python
# Line 1894-1910: Create DetailAHSPExpanded with bundle_multiplier
expanded_to_create.append(DetailAHSPExpanded(
    project=project,
    pekerjaan=pkj,
    source_detail=detail_obj,
    harga_item=comp_hip,
    kategori=comp['kategori'],
    kode=comp['kode'],
    uraian=comp['uraian'],
    satuan=comp['satuan'],
    koefisien=quantize_half_up(comp['koefisien'], dp_koef),  # Original koef!
    # NEW: Store bundle multiplier for aggregation
    # bundle_multiplier=comp.get('bundle_multiplier', Decimal('1.0')),  # If we add field
    source_bundle_kode=detail_obj.kode,
    expansion_depth=comp['depth'],
))
```

**DECISION POINT:** Do we add `bundle_multiplier` field to DetailAHSPExpanded?

**Option A:** Add field (recommended for clarity)
```python
# models.py - Add to DetailAHSPExpanded
bundle_multiplier = models.DecimalField(
    max_digits=18,
    decimal_places=6,
    default=Decimal('1.0'),
    help_text='Bundle koefisien (quantity) from source_detail'
)
```

**Option B:** Query source_detail.koefisien at runtime (simpler, no migration)
```python
# No field needed - join to source_detail when needed
```

**Recommendation:** **Option B** (no migration needed, cleaner)

#### 1.3 Testing Phase 1

**Test Cases:**
```python
# test_bundle_expansion_no_multiplication.py

def test_expansion_stores_original_koef():
    """Bundle expansion should NOT multiply component koef by bundle koef"""
    # Create bundle with koef=10
    bundle = create_bundle(
        koef=Decimal('10.0'),
        ref_pekerjaan=component_pekerjaan
    )

    # Component with koef=0.011
    component = create_component(
        pekerjaan=component_pekerjaan,
        kategori='TK',
        koef=Decimal('0.011')
    )

    # Trigger expansion
    _populate_expanded_from_raw(project, bundle.pekerjaan)

    # Check expanded koef
    expanded = DetailAHSPExpanded.objects.get(
        source_detail=bundle,
        kode=component.kode
    )

    # CRITICAL: Should be 0.011 (original), NOT 0.11 (× 10)!
    assert expanded.koefisien == Decimal('0.011')


def test_bundle_koef_change_preserves_component_koef():
    """Changing bundle koef should NOT change expanded component koef"""
    # Create bundle with koef=10
    bundle = create_bundle(koef=Decimal('10.0'))
    _populate_expanded_from_raw(project, bundle.pekerjaan)

    # Get expanded koef
    exp_before = DetailAHSPExpanded.objects.get(source_detail=bundle).koefisien

    # Change bundle koef to 5
    bundle.koefisien = Decimal('5.0')
    bundle.save()
    _populate_expanded_from_raw(project, bundle.pekerjaan)

    # Check expanded koef
    exp_after = DetailAHSPExpanded.objects.get(source_detail=bundle).koefisien

    # Should be SAME (original component koef)
    assert exp_before == exp_after
```

**Run Tests:**
```bash
python manage.py test detail_project.tests.test_bundle_expansion_no_multiplication
```

**Success Criteria:**
- ✅ Expansion creates DetailAHSPExpanded with original koef
- ✅ Changing bundle koef does NOT change expanded koef
- ✅ No exceptions during expansion

---

### PHASE 2: Update API & Display Logic 🖥️
**Duration:** 3-4 hours
**Objective:** Fix bundle_total calculation and display
**Risk:** 🟡 MEDIUM (calculation changes)

#### 2.1 Update API Bundle Total Calculation

**File:** `detail_project/views_api.py`
**Function:** `api_get_detail_ahsp()` (lines 1326-1376)

**Current Code (lines 1370-1376):**
```python
if is_bundle and bundle_total > Decimal("0"):
    if koef_decimal > Decimal("0"):
        effective_price = bundle_total / koef_decimal  # DIVISION!
    else:
        effective_price = bundle_total
```

**New Code:**
```python
if is_bundle and bundle_total > Decimal("0"):
    # Bundle total is now per-unit price (no bundle koef multiplication in expansion)
    # So we use it directly as harga_satuan
    effective_price = bundle_total  # NO division!

    # Frontend will multiply: jumlah = bundle.koef × harga_satuan
```

**Update Comment:**
```python
# BUNDLE LOGIC (QUANTITY SEMANTIC - Updated 2025-01-18):
# For bundles (kategori LAIN with ref_pekerjaan/ref_ahsp):
# 1. Koefisien = QUANTITY (how many bundle units are used)
# 2. DetailAHSPExpanded stores ORIGINAL component koef (NOT multiplied by bundle koef)
#    Example: Component koef 0.011 → Expanded koef 0.011 (no multiplication!)
# 3. bundle_total = Σ(original_component_koef × component_harga)
#    Example: (0.011 × 165,000) + (0.033 × 135,000) + ... = 23,472
# 4. harga_satuan = bundle_total (price per 1 bundle unit)
#    Example: Rp 23,472 per bundle
# 5. Frontend displays: jumlah_harga = bundle.koef × harga_satuan
#    Example: 10 × 23,472 = 234,720
#
# IMPORTANT: Bundle koef is applied at DISPLAY/AGGREGATION layer, NOT expansion!
```

#### 2.2 Update Frontend Display Logic

**File:** `detail_project/static/detail_project/js/rincian_ahsp.js`
**Lines:** 809-838

**Current Code (line 812):**
```javascript
const jm = kf * hr;  // Always multiply
```

**No Change Needed!** (Already correct for quantity semantic)

**Update Tooltip (line 834):**
```javascript
// OLD:
const hargaCell = isBundle
  ? `<span class="text-info" title="Harga satuan bundle (total komponen ÷ koef bundle)">${fmt(hr)}</span>`
  : fmt(hr);

// NEW:
const hargaCell = isBundle
  ? `<span class="text-info" title="Harga satuan per 1 unit bundle (dari total komponen)">${fmt(hr)}</span>`
  : fmt(hr);
```

#### 2.3 Testing Phase 2

**Test Cases:**
```python
def test_api_bundle_harga_satuan_no_division():
    """API should return bundle_total as harga_satuan (no division)"""
    bundle = create_bundle(koef=Decimal('10.0'))
    create_components_for_bundle(bundle, total=Decimal('23472.00'))

    # Call API
    response = api_get_detail_ahsp(project, bundle.pekerjaan)
    bundle_item = next(it for it in response['items'] if it['kode'] == bundle.kode)

    # Check harga_satuan = bundle_total (NOT bundle_total / 10)
    assert Decimal(bundle_item['harga_satuan']) == Decimal('23472.00')  # Not 2347.20!


def test_frontend_jumlah_calculation():
    """Frontend should calculate jumlah = koef × harga_satuan"""
    # Simulate frontend calculation
    koef = 10.0
    harga_satuan = 23472.00  # Per-unit bundle price

    jumlah = koef * harga_satuan

    assert jumlah == 234720.00  # 10 units × 23,472 per unit
```

**Manual Testing:**
1. Create bundle with koef=10
2. Open Rincian AHSP
3. Verify:
   - Harga Satuan = Rp 23,472 (per unit)
   - Jumlah Harga = Rp 234,720 (10 × 23,472)
4. Change bundle koef to 5 in Template AHSP
5. Save and refresh Rincian AHSP
6. Verify:
   - Harga Satuan = Rp 23,472 (UNCHANGED!)
   - Jumlah Harga = Rp 117,360 (5 × 23,472)

**Success Criteria:**
- ✅ API returns correct harga_satuan (no division)
- ✅ Frontend displays correct jumlah (koef × harga)
- ✅ Changing bundle koef changes jumlah but NOT harga satuan

---

### PHASE 3: Update Aggregation Logic (Rekap & Exports) 📊
**Duration:** 4-6 hours
**Objective:** Fix aggregations to multiply bundle koef at runtime
**Risk:** 🔴 HIGH (affects all financial calculations)

#### 3.1 Update Rekap RAB Computation

**File:** `detail_project/services.py`
**Function:** `compute_rekap_for_project()` (lines 1604-1727)

**Current Code (lines 1646-1673):**
```python
# Direct aggregation from DetailAHSPExpanded
price = DJF('harga_item__harga_satuan')
coef = DJF('koefisien')  # Expanded koef (already × bundle koef)
nilai_expr = ExpressionWrapper(coef * price, ...)

agg = DetailAHSPExpanded.objects.aggregate(
    total=Sum(nilai_expr)
)
```

**New Code:**
```python
# Need to multiply by source bundle koef!
price = DJF('harga_item__harga_satuan')
coef = DJF('koefisien')  # Original component koef (NOT × bundle koef)
bundle_koef = DJF('source_detail__koefisien')  # Bundle quantity

# CRITICAL: Multiply by bundle koef for correct total
nilai_expr = ExpressionWrapper(coef * bundle_koef * price, ...)

agg = DetailAHSPExpanded.objects.aggregate(
    total=Sum(nilai_expr)
)
```

**Challenge:** This requires JOIN to `source_detail`!

**Performance Impact:**
- Before: Single table scan (fast)
- After: JOIN DetailAHSPExpanded → DetailAHSPProject (slower)

**Mitigation:**
```python
# Use select_related to optimize JOIN
expanded_qs = (DetailAHSPExpanded.objects
               .select_related('source_detail')  # Optimize JOIN
               .filter(project=project, pekerjaan=pkj))
```

#### 3.2 Update Rekap Kebutuhan Computation

**File:** `detail_project/services.py`
**Function:** `compute_kebutuhan_items()` (lines 1730-1919)

**Current Code (lines 1887-1898):**
```python
for detail in DetailAHSPExpanded.objects.filter(...):
    koefisien = Decimal(detail['koefisien'])  # Expanded koef
    qty = koefisien * volume_efektif
    aggregated[key] += qty
```

**New Code:**
```python
# Need to fetch bundle koef for each expanded item
details = (DetailAHSPExpanded.objects.filter(...)
           .values('kategori', 'kode', 'uraian', 'satuan',
                   'koefisien', 'source_detail__koefisien'))  # Add bundle koef

for detail in details:
    component_koef = Decimal(detail['koefisien'])  # Original component koef
    bundle_koef = Decimal(detail['source_detail__koefisien'] or 1)  # Bundle quantity

    # CRITICAL: Multiply by bundle koef
    effective_koef = component_koef * bundle_koef
    qty = effective_koef * volume_efektif
    aggregated[key] += qty
```

#### 3.3 Update Tahapan API

**File:** Same as Rekap Kebutuhan (uses `compute_kebutuhan_items`)

**No additional changes needed** if we fix `compute_kebutuhan_items()` correctly.

#### 3.4 Testing Phase 3

**Test Cases:**
```python
def test_rekap_rab_with_bundle_quantity():
    """Rekap RAB should multiply component koef × bundle koef"""
    # Create bundle with koef=10
    bundle = create_bundle(koef=Decimal('10.0'))

    # Component: TK with koef=0.011, harga=165,000
    create_component(kategori='TK', koef=Decimal('0.011'), harga=Decimal('165000'))

    # Expand (stores koef=0.011, NOT 0.11)
    _populate_expanded_from_raw(project, bundle.pekerjaan)

    # Compute rekap
    rekap = compute_rekap_for_project(project)

    # Expected TK total: 0.011 × 10 × 165,000 = 18,150
    assert rekap['TK'] == Decimal('18150.00')


def test_rekap_kebutuhan_with_bundle_quantity():
    """Rekap Kebutuhan should multiply component koef × bundle koef × volume"""
    # Bundle koef=10, component koef=0.011
    # Volume=1.0
    # Expected quantity: 0.011 × 10 × 1.0 = 0.11

    bundle = create_bundle(koef=Decimal('10.0'))
    create_component(koef=Decimal('0.011'))
    set_volume(bundle.pekerjaan, Decimal('1.0'))

    kebutuhan = compute_kebutuhan_items(project)

    tk_item = next(it for it in kebutuhan if it['kategori'] == 'TK')
    assert tk_item['quantity'] == Decimal('0.11')


def test_bundle_koef_change_affects_aggregation():
    """Changing bundle koef should change aggregated totals"""
    bundle = create_bundle(koef=Decimal('10.0'))
    create_component(koef=Decimal('0.011'), harga=Decimal('165000'))
    _populate_expanded_from_raw(project, bundle.pekerjaan)

    rekap_before = compute_rekap_for_project(project)

    # Change bundle koef to 5
    bundle.koefisien = Decimal('5.0')
    bundle.save()
    # Note: No need to re-expand! Component koef stays 0.011

    rekap_after = compute_rekap_for_project(project)

    # Total should be halved
    assert rekap_after['TK'] == rekap_before['TK'] / Decimal('2.0')
```

**Success Criteria:**
- ✅ Rekap RAB totals include bundle koef multiplication
- ✅ Rekap Kebutuhan quantities include bundle koef
- ✅ Changing bundle koef affects aggregations WITHOUT re-expansion
- ✅ Performance acceptable (JOIN overhead minimal)

---

### PHASE 4: Migration & Data Cleanup 🔄
**Duration:** 2-3 hours
**Objective:** Re-expand ALL existing bundles with new logic
**Risk:** 🟡 MEDIUM (data migration)

#### 4.1 Create Migration Script

**File:** `detail_project/management/commands/migrate_bundle_to_quantity_semantic.py`

```python
"""
Management command to migrate existing bundles from expansion multiplier to quantity semantic.

This script:
1. Finds all bundles (kategori LAIN with ref)
2. Re-expands them using new logic (no bundle koef multiplication)
3. Validates that totals are consistent

Usage:
    python manage.py migrate_bundle_to_quantity_semantic --project-id 110
    python manage.py migrate_bundle_to_quantity_semantic --all --dry-run
"""

from django.core.management.base import BaseCommand
from detail_project.models import Project, Pekerjaan, DetailAHSPProject, HargaItemProject
from detail_project.services import _populate_expanded_from_raw


class Command(BaseCommand):
    help = 'Migrate bundles from expansion multiplier to quantity semantic'

    def add_arguments(self, parser):
        parser.add_argument('--project-id', type=int, help='Project ID to migrate')
        parser.add_argument('--all', action='store_true', help='Migrate all projects')
        parser.add_argument('--dry-run', action='store_true', help='Dry run (no actual changes)')

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        migrate_all = options.get('all')
        dry_run = options.get('dry_run')

        if not project_id and not migrate_all:
            self.stdout.write(self.style.ERROR('Error: Specify --project-id or --all'))
            return

        # Get projects
        if migrate_all:
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(pk=project_id)

        if not projects.exists():
            self.stdout.write(self.style.ERROR(f'No projects found'))
            return

        self.stdout.write(f'Found {projects.count()} project(s) to migrate')
        self.stdout.write(f'Dry run: {dry_run}')
        self.stdout.write('')

        total_bundles = 0
        total_pekerjaan = 0

        for project in projects:
            self.stdout.write(self.style.SUCCESS(f'\n=== Project: {project.nama} (ID: {project.id}) ==='))

            # Find all pekerjaan with bundles
            bundles = DetailAHSPProject.objects.filter(
                project=project,
                kategori=HargaItemProject.KATEGORI_LAIN
            ).filter(
                models.Q(ref_pekerjaan__isnull=False) | models.Q(ref_ahsp__isnull=False)
            ).select_related('pekerjaan')

            if not bundles.exists():
                self.stdout.write('  No bundles found, skipping.')
                continue

            bundle_count = bundles.count()
            pekerjaan_ids = set(bundles.values_list('pekerjaan_id', flat=True))
            pekerjaan_count = len(pekerjaan_ids)

            self.stdout.write(f'  Found {bundle_count} bundles across {pekerjaan_count} pekerjaan')

            total_bundles += bundle_count
            total_pekerjaan += pekerjaan_count

            # Re-expand each pekerjaan
            for pekerjaan_id in pekerjaan_ids:
                pekerjaan = Pekerjaan.objects.get(pk=pekerjaan_id)
                bundle_list = bundles.filter(pekerjaan=pekerjaan)

                self.stdout.write(f'  - Pekerjaan {pekerjaan.snapshot_kode}: {bundle_list.count()} bundle(s)')

                if not dry_run:
                    try:
                        # Re-expand with new logic
                        _populate_expanded_from_raw(project, pekerjaan)
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Re-expanded successfully'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    ✗ Error: {str(e)}'))
                else:
                    self.stdout.write('    (dry run - skipped)')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'=== MIGRATION SUMMARY ==='))
        self.stdout.write(f'Total projects: {projects.count()}')
        self.stdout.write(f'Total bundles: {total_bundles}')
        self.stdout.write(f'Total pekerjaan re-expanded: {total_pekerjaan}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** DRY RUN - No actual changes made ***'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Migration complete!'))
```

#### 4.2 Run Migration

```bash
# Dry run first
python manage.py migrate_bundle_to_quantity_semantic --all --dry-run

# Review output, then run for real
python manage.py migrate_bundle_to_quantity_semantic --all

# Or specific project
python manage.py migrate_bundle_to_quantity_semantic --project-id 110
```

#### 4.3 Validation

After migration, run diagnostic:
```bash
python manage.py shell
exec(open('diagnose_bundle_koef_issue.py').read())
```

Check:
- ✅ Expanded koef = original component koef (NOT × bundle koef)
- ✅ Bundle total = per-unit price
- ✅ API harga_satuan = bundle_total

**Success Criteria:**
- ✅ All bundles re-expanded successfully
- ✅ No errors during migration
- ✅ Diagnostic shows correct values

---

### PHASE 5: Comprehensive Testing 🧪
**Duration:** 6-8 hours
**Objective:** Test ALL features end-to-end
**Risk:** 🟡 MEDIUM (regression testing)

#### 5.1 Unit Tests

```bash
# Run all bundle-related tests
python manage.py test detail_project.tests.test_bundle_expansion
python manage.py test detail_project.tests.test_template_ahsp_bundle
python manage.py test detail_project.tests.test_rekap_rab
python manage.py test detail_project.tests.test_rekap_kebutuhan
```

#### 5.2 Integration Tests

**Test Scenarios:**

**Scenario 1: Create Bundle from Scratch**
1. Create pekerjaan reference with components (TK, BHN, ALT)
2. Create bundle in new pekerjaan with koef=10
3. Save Template AHSP
4. Verify:
   - DetailAHSPExpanded created with original koef
   - Rincian AHSP shows correct harga satuan & jumlah
   - Rekap RAB totals correct

**Scenario 2: Change Bundle Koef**
1. Existing bundle with koef=10
2. Change to koef=5
3. Save
4. Verify:
   - DetailAHSPExpanded koef UNCHANGED (still original)
   - Rincian AHSP harga satuan UNCHANGED
   - Rincian AHSP jumlah HALVED
   - Rekap RAB totals HALVED

**Scenario 3: Change Component Price**
1. Bundle with koef=10
2. Change component harga satuan in Harga Items
3. Verify:
   - Rincian AHSP bundle harga satuan CHANGED
   - Jumlah changes proportionally

**Scenario 4: Exports**
1. Project with bundles
2. Export Rekap RAB (CSV/PDF/Word)
3. Export Rekap Kebutuhan (CSV/PDF/Word)
4. Verify:
   - All totals match Rincian AHSP
   - Bundle quantities correct

**Scenario 5: Tahapan**
1. Bundle in tahapan with proportion 60%
2. Verify:
   - Rekap Kebutuhan per tahapan shows 60% of quantities
   - Totals match

#### 5.3 Manual Testing Checklist

- [ ] **Template AHSP Page**
  - [ ] Create new bundle
  - [ ] Edit bundle koef
  - [ ] Delete bundle
  - [ ] Save with validation errors

- [ ] **Rincian AHSP Page**
  - [ ] Display bundle row
  - [ ] Click bundle to expand (show components)
  - [ ] Verify harga satuan & jumlah
  - [ ] Override BUK modal

- [ ] **Rekap RAB**
  - [ ] View rekap with bundles
  - [ ] Verify totals (A, B, C, LAIN, E, F, G)
  - [ ] Export CSV/PDF/Word

- [ ] **Rekap Kebutuhan**
  - [ ] View kebutuhan with bundles
  - [ ] Filter by kategori
  - [ ] Export CSV/PDF/Word

- [ ] **Tahapan**
  - [ ] Assign bundle pekerjaan to tahapan
  - [ ] View rekap kebutuhan per tahapan
  - [ ] Verify proportional quantities

- [ ] **Volume Pekerjaan**
  - [ ] Change volume for pekerjaan with bundle
  - [ ] Verify rekap kebutuhan updates

#### 5.4 Performance Testing

```python
# Benchmark aggregation queries
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_rekap_performance():
    # Create project with 100 bundles
    project = create_large_project(bundle_count=100)

    # Measure query time
    import time
    start = time.time()
    rekap = compute_rekap_for_project(project)
    elapsed = time.time() - start

    # Check query count
    query_count = len(connection.queries)

    print(f'Elapsed: {elapsed:.2f}s')
    print(f'Queries: {query_count}')

    # Should be < 2 seconds for 100 bundles
    assert elapsed < 2.0
    # Should use < 10 queries (with select_related optimization)
    assert query_count < 10
```

**Success Criteria:**
- ✅ All unit tests passing
- ✅ All integration scenarios passing
- ✅ Manual testing checklist complete
- ✅ Performance acceptable (< 2s for 100 bundles)

---

### PHASE 6: Documentation & Cleanup 📚
**Duration:** 2-3 hours
**Objective:** Update all documentation
**Risk:** 🟢 LOW

#### 6.1 Update Technical Documentation

**Files to Update:**
- [ ] `BUNDLE_SYSTEM_ARCHITECTURE.md` - Complete rewrite for quantity semantic
- [ ] `BUNDLE_SYSTEM_CORRECT_LOGIC.md` - Archive or delete (outdated)
- [ ] `CRITICAL_FIXES_BUNDLE_SYSTEM.md` - Update with refactor notes
- [ ] `REVIEW_USER_CHANGES_2025_11_18.md` - Add refactor decision notes
- [ ] `RINCIAN_AHSP_DOCUMENTATION.md` - Update bundle display explanation

#### 6.2 Update Code Comments

**Files:**
- [ ] `services.py` - Update expansion function docstrings
- [ ] `views_api.py` - Update bundle logic comments
- [ ] `rincian_ahsp.js` - Update frontend calculation comments

#### 6.3 Create Migration Notes

**File:** `MIGRATION_NOTES_QUANTITY_SEMANTIC.md`

Document:
- What changed
- Why it changed
- How to verify correct behavior
- Rollback procedure (if needed)
- Known issues / limitations

#### 6.4 Cleanup

- [ ] Delete diagnostic scripts (or move to `scripts/archive/`)
- [ ] Remove old test files (if refactored)
- [ ] Clean up commented-out code
- [ ] Update TODO comments

**Success Criteria:**
- ✅ All documentation updated and accurate
- ✅ Code comments clear and helpful
- ✅ No outdated/misleading documentation

---

### PHASE 7: Deployment & Monitoring 🚀
**Duration:** 1-2 hours
**Objective:** Deploy to production (or staging)
**Risk:** 🟡 MEDIUM

#### 7.1 Pre-Deployment Checklist

- [ ] All tests passing (100% pass rate)
- [ ] Code review completed
- [ ] Documentation reviewed
- [ ] Migration script tested on copy of production data
- [ ] Rollback plan documented and tested

#### 7.2 Deployment Steps

```bash
# 1. Merge feature branch
git checkout main
git merge refactor/bundle-quantity-semantic

# 2. Run migrations (if any schema changes)
python manage.py migrate

# 3. Run data migration
python manage.py migrate_bundle_to_quantity_semantic --all

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Restart server
# (depends on deployment setup)

# 6. Clear cache
python manage.py shell
from django.core.cache import cache
cache.clear()
```

#### 7.3 Post-Deployment Validation

**Immediate Checks (5 minutes):**
- [ ] Site loads without errors
- [ ] Template AHSP save works
- [ ] Rincian AHSP displays bundles correctly
- [ ] No errors in server logs

**Extended Checks (30 minutes):**
- [ ] Create new bundle (full workflow)
- [ ] Export Rekap RAB (verify totals)
- [ ] Export Rekap Kebutuhan (verify totals)
- [ ] Check all pages (no JavaScript errors)

#### 7.4 Monitoring

**Week 1 Monitoring:**
- Check server logs daily for errors
- Monitor user feedback (if any)
- Watch for performance degradation
- Be ready for quick rollback if needed

**Success Criteria:**
- ✅ Deployment completed without errors
- ✅ All validation checks passing
- ✅ No user-reported issues in first 24 hours

---

## ROLLBACK PLAN

If critical issues are discovered:

### Immediate Rollback (< 30 minutes)

```bash
# 1. Revert code changes
git revert <commit-hash>
git push

# 2. Restore database backup
# (if data migration was run)
python manage.py loaddata backup_pre_refactor_YYYYMMDD.json

# 3. Restart server
# 4. Clear cache

# 5. Verify site works
```

### Partial Rollback

If only specific features broken:
- Feature flag to disable new bundle logic
- Fallback to old calculation methods
- Gradual migration (some projects on new, some on old)

---

## RISK MITIGATION

### High-Risk Areas

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| **Aggregation SQL breaks** | Test extensively with real data | Add fallback to Python aggregation |
| **Performance degradation** | Benchmark before/after | Optimize with indexes/caching |
| **Data corruption** | Full backup before migration | Restore from backup |
| **User confusion** | Clear documentation + tooltips | Add help modal |
| **Export totals wrong** | Compare with baseline exports | Revert and debug |

### Testing Strategy

**Test Coverage Goals:**
- Unit tests: > 90% coverage for bundle-related code
- Integration tests: 100% of user workflows
- Manual testing: All pages with bundles

---

## SUCCESS METRICS

### Technical Metrics
- ✅ All tests passing (0 failures)
- ✅ Code coverage > 90% for bundle code
- ✅ Performance < 2s for rekap with 100 bundles
- ✅ Zero data corruption

### User Experience Metrics
- ✅ Bundle koef change works as expected
- ✅ Harga satuan remains constant when koef changes
- ✅ Jumlah harga changes proportionally
- ✅ All exports show correct totals

### Business Metrics
- ✅ Zero critical bugs in production
- ✅ No user complaints about bundle behavior
- ✅ Reduced support tickets about bundle confusion

---

## TIMELINE SUMMARY

| Phase | Duration | Dependencies | Risk |
|-------|----------|--------------|------|
| 0. Pre-Flight | 2-3 hours | None | 🟢 LOW |
| 1. Expansion Logic | 4-6 hours | Phase 0 | 🔴 HIGH |
| 2. API & Display | 3-4 hours | Phase 1 | 🟡 MEDIUM |
| 3. Aggregation | 4-6 hours | Phase 2 | 🔴 HIGH |
| 4. Migration | 2-3 hours | Phase 3 | 🟡 MEDIUM |
| 5. Testing | 6-8 hours | Phase 4 | 🟡 MEDIUM |
| 6. Documentation | 2-3 hours | Phase 5 | 🟢 LOW |
| 7. Deployment | 1-2 hours | Phase 6 | 🟡 MEDIUM |

**TOTAL:** 24-35 hours (3-4 days with testing)

---

## DECISION LOG

**Date:** 2025-01-18

**Decision:** Refactor bundle system from "expansion multiplier" to "quantity semantic"

**Rationale:**
- User expectation: Bundle koef represents quantity, not expansion multiplier
- Current system confusing: Harga satuan changes when koef changes
- Dummy data only: Safe to make breaking change

**Approved by:** User (Adit)

**Risk Assessment:** HIGH but acceptable (no production data)

**Go/No-Go:** ✅ **GO** - Proceed with refactor

---

## NEXT STEPS

**Immediate:**
1. Review this roadmap with team/stakeholders
2. Get final approval
3. Create feature branch
4. Start Phase 0 (Pre-Flight Checks)

**Questions to Answer:**
- [ ] Timeline acceptable? (3-4 days)
- [ ] Any additional test cases needed?
- [ ] Prefer adding `bundle_multiplier` field or query source_detail at runtime?
- [ ] Deploy to staging first or directly to development?

---

**END OF ROADMAP**

**Status:** 🟡 AWAITING APPROVAL
**Next Update:** After Phase 0 completion
