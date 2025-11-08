# Bundle Expansion During Save - Implementation Fix

## Problem Statement

**Original Implementation (WRONG):**
- User saves LAIN item with AHSP reference (e.g., "2.2.1.4.3 - Beton Mutu Rendah")
- System saves LAIN item to both DetailAHSPProject and HargaItemProject
- Expansion to component items (Air, Semen, Pasir, Kerikil, Mandor, etc.) ONLY happens during rekap computation
- **Result:** Harga Items page shows LAIN bundle item, NOT expanded components

**Expected Implementation (CORRECT):**
- User saves LAIN item with AHSP reference
- System IMMEDIATELY expands to component items (TK/BHN/ALT)
- System saves expanded items to DetailAHSPProject and HargaItemProject
- **Result:** Harga Items page shows all expanded components (Air, Semen, Pasir, Mandor, etc.)

## Changes Made

### File: `detail_project/views_api.py`

#### 1. Added Import (line 6, 11, 26)
```python
import logging

logger = logging.getLogger(__name__)

from .services import (
    clone_ref_pekerjaan, _upsert_harga_item, compute_rekap_for_project,
    generate_custom_code, invalidate_rekap_cache, validate_bundle_reference,
    expand_bundle_recursive,  # NEW
)
```

#### 2. Modified `api_save_detail_ahsp_for_pekerjaan()` (lines 1179-1237)

**Added expansion logic BEFORE creating DetailAHSPProject:**

```python
# ========================================================================
# EXPANSION: Expand bundle items (LAIN dengan ref) menjadi component items
# ========================================================================
expanded_normalized = []
dp_koef = DECIMAL_SPEC["KOEF"].dp  # default 6

for kat, kode, uraian, satuan, koef, ref_ahsp_obj, ref_pekerjaan_obj in normalized:
    # Jika LAIN dengan bundle reference → expand ke component items
    if kat == HargaItemProject.KATEGORI_LAIN and (ref_ahsp_obj or ref_pekerjaan_obj):
        # Build detail_dict untuk expansion
        detail_dict = {
            'kategori': kat,
            'kode': kode,
            'uraian': uraian,
            'satuan': satuan,
            'koefisien': str(koef),
            'ref_ahsp_id': ref_ahsp_obj.id if ref_ahsp_obj else None,
            'ref_pekerjaan_id': ref_pekerjaan_obj.id if ref_pekerjaan_obj else None,
        }

        try:
            # Expand bundle recursively
            expanded_items = expand_bundle_recursive(
                detail_dict=detail_dict,
                base_koefisien=Decimal('1.0'),
                project=project,
                depth=0,
                visited=None
            )

            # Add expanded items to final list
            for exp_kat, exp_kode, exp_uraian, exp_satuan, exp_koef in expanded_items:
                expanded_normalized.append((
                    exp_kat, exp_kode, exp_uraian, exp_satuan, exp_koef,
                    None,  # no ref_ahsp for expanded items
                    None   # no ref_pekerjaan for expanded items
                ))

        except ValueError as e:
            # Expansion failed (circular dependency atau max depth)
            logger.error(
                f"Bundle expansion failed during save for pekerjaan {pkj.id}: {str(e)}",
                extra={'kode': kode, 'uraian': uraian}
            )
            errors.append(_err(f"bundle.{kode}", f"Expansion error: {str(e)}"))
            continue

    else:
        # Normal item (TK/BHN/ALT/BUK atau LAIN tanpa ref) → tambahkan langsung
        expanded_normalized.append((kat, kode, uraian, satuan, koef, ref_ahsp_obj, ref_pekerjaan_obj))
```

## Flow Comparison

### Before (WRONG):
```
User Input: LAIN "2.2.1.4.3" koef=1.0
    ↓
Validation
    ↓
Save to DetailAHSPProject:
  - LAIN "2.2.1.4.3" koef=1.0 ref_ahsp=123
    ↓
Save to HargaItemProject:
  - LAIN "2.2.1.4.3"
    ↓
Harga Items Page shows:
  - LAIN "2.2.1.4.3" ❌ WRONG
```

### After (CORRECT):
```
User Input: LAIN "2.2.1.4.3" koef=1.0
    ↓
Validation
    ↓
Expansion (expand_bundle_recursive):
  - Air 202 liter
  - Semen Portland 304 kg
  - Pasir Beton 832 kg
  - Kerikil 1009 kg
  - Mandor 0.009 OH
  - Kepala Tukang 0.028 OH
  - Tukang Batu 0.275 OH
  - Pekerja 1.65 OH
    ↓
Save to DetailAHSPProject (8 items):
  - BHN "Air" koef=202.000000
  - BHN "Semen Portland" koef=304.000000
  - BHN "Pasir Beton" koef=832.000000
  - BHN "Kerikil" koef=1009.000000
  - TK "Mandor" koef=0.009000
  - TK "Kepala Tukang" koef=0.028000
  - TK "Tukang Batu" koef=0.275000
  - TK "Pekerja" koef=1.650000
    ↓
Save to HargaItemProject (8 items)
    ↓
Harga Items Page shows:
  - All 8 expanded items ✅ CORRECT
```

## Example: User Scenario from Issue

**User Actions:**
1. Create pekerjaan "Balok Sloof" (custom)
2. Input volume: 100 m3
3. Template AHSP → Add "Pekerjaan Gabungan":
   - Kode: 2.2.1.4.3 (from Master AHSP)
   - Satuan: m3
   - Koefisien: 1
4. Save

**System Behavior (NEW):**
- Detects LAIN with ref_ahsp = "2.2.1.4.3"
- Calls `expand_bundle_recursive()`:
  - Reads RincianReferensi for AHSP "2.2.1.4.3"
  - Extracts 8 component items with koefisien
- Creates 8 DetailAHSPProject records (TK/BHN items)
- Creates 8 HargaItemProject records
- **Harga Items page now shows:**
  - Air (202 liter)
  - Semen Portland (304 kg)
  - Pasir Beton (832 kg)
  - Kerikil (1009 kg)
  - Mandor (0.009 OH)
  - Kepala Tukang (0.028 OH)
  - Tukang Batu (0.275 OH)
  - Pekerja Biasa (1.65 OH)

## Koefisien Calculation

**If user inputs koefisien = 2.0 instead of 1.0:**

Expanded items will have koefisien multiplied:
- Air: 202 × 2.0 = 404.000000 liter
- Semen: 304 × 2.0 = 608.000000 kg
- Pasir: 832 × 2.0 = 1664.000000 kg
- Kerikil: 1009 × 2.0 = 2018.000000 kg
- Mandor: 0.009 × 2.0 = 0.018000 OH
- Kepala Tukang: 0.028 × 2.0 = 0.056000 OH
- Tukang Batu: 0.275 × 2.0 = 0.550000 OH
- Pekerja: 1.65 × 2.0 = 3.300000 OH

## Multi-level Bundle Expansion

**Scenario: Nested Bundles**
- User inputs LAIN with ref_pekerjaan pointing to "Pekerjaan B"
- Pekerjaan B has another LAIN with ref_ahsp "2.2.1.4.3"
- System expands recursively:
  1. Detects ref_pekerjaan → reads Pekerjaan B details
  2. Finds LAIN in Pekerjaan B with ref_ahsp
  3. Expands ref_ahsp to component items
  4. Multiplies all koefisien (cascade)

**Example:**
```
User Input:
  LAIN ref_pekerjaan=B koef=2.0

Pekerjaan B contains:
  LAIN ref_ahsp="2.2.1.4.3" koef=3.0

Final Expansion:
  Air: 202 × 3.0 × 2.0 = 1212.000000 liter
  Semen: 304 × 3.0 × 2.0 = 1824.000000 kg
  ... (all items multiplied by 6.0)
```

## Error Handling

**Circular Dependency:**
- If expansion detects circular reference → raises ValueError
- Error logged and returned as 400 response
- User sees error message: "Circular dependency detected: A001 → B002 → A001"

**Max Depth Exceeded:**
- If bundle nesting > 10 levels → raises ValueError
- Error logged and returned as 400 response
- User sees error message: "Maksimum kedalaman bundle (10 level) terlampaui"

## Impact on Rekap Computation

**Previous behavior:**
- Rekap expands LAIN bundles during computation
- LAIN items stored in database, expanded in memory

**New behavior:**
- Rekap receives already-expanded items (TK/BHN/ALT)
- No expansion needed (backward compatible logic still exists for old data)
- Faster rekap computation (no expansion overhead)

## UX Changes

**Before:**
1. User saves LAIN "2.2.1.4.3"
2. Template AHSP shows: 1 LAIN item
3. Harga Items shows: 1 LAIN item (wrong!)
4. User can re-edit LAIN bundle easily

**After:**
1. User saves LAIN "2.2.1.4.3"
2. Template AHSP shows: 8 expanded items (TK/BHN)
3. Harga Items shows: 8 expanded items (correct!)
4. User can edit individual item koefisien (e.g., adjust Semen amount)

**Trade-off:**
- ✅ Harga Items shows correct breakdown
- ✅ User can adjust individual items
- ⚠️ Re-referencing bundle requires deleting all expanded items and re-inputting LAIN

## Testing

**Test Scenario 1: AHSP Reference**
```python
# Input
rows = [{
    'kategori': 'LAIN',
    'kode': '2.2.1.4.3',
    'uraian': 'Beton Mutu Rendah',
    'satuan': 'm3',
    'koefisien': '1.0',
    'ref_kind': 'ahsp',
    'ref_id': 123
}]

# Expected: 8 DetailAHSPProject records created (TK/BHN items)
# Expected: 8 HargaItemProject records created
# Expected: No LAIN item in database
```

**Test Scenario 2: Pekerjaan Reference**
```python
# Input
rows = [{
    'kategori': 'LAIN',
    'kode': 'BUNDLE.001',
    'uraian': 'Bundle Job B',
    'satuan': 'LS',
    'koefisien': '2.0',
    'ref_kind': 'job',
    'ref_id': 456
}]

# Expected: Expanded items from Pekerjaan #456
# Expected: All koefisien multiplied by 2.0
```

**Test Scenario 3: Circular Reference**
```python
# Setup: Pekerjaan A → Pekerjaan B → Pekerjaan A

# Input
rows = [{
    'kategori': 'LAIN',
    'kode': 'CIRC.001',
    'uraian': 'Circular Bundle',
    'satuan': 'LS',
    'koefisien': '1.0',
    'ref_kind': 'job',
    'ref_id': <points to circular chain>
}]

# Expected: 400 error
# Expected: Error message contains "Circular dependency detected"
```

## Backward Compatibility

**Old data with LAIN + ref still in database:**
- GET endpoint still returns ref_pekerjaan_id (if exists)
- Rekap computation still has expansion logic (for old data)
- No breaking changes for existing data

**New data (after this fix):**
- Only expanded items stored
- ref_pekerjaan = NULL for expanded items
- GET endpoint returns TK/BHN/ALT items (not LAIN)

## Files Modified

1. `detail_project/views_api.py`:
   - Added logging import
   - Added expand_bundle_recursive import
   - Modified api_save_detail_ahsp_for_pekerjaan() with expansion logic

## Notes

- Decimal precision: 6 decimal places (HALF_UP rounding)
- Expansion happens BEFORE bulk_create (atomic transaction)
- Error logging includes pekerjaan_id and kode for debugging
- Expanded items do NOT have ref_ahsp or ref_pekerjaan (set to NULL)
