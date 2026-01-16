# FASE 0.1: Data Audit Script Guide

**Status:** ✅ COMPLETED
**Script Location:** `detail_project/management/commands/audit_current_data.py`
**Version:** 1.0
**Last Updated:** 2025-11-13

---

## EXECUTIVE SUMMARY

Script `audit_current_data.py` melakukan 6 audit checks untuk memastikan data integrity dan quality:

1. **Orphaned HargaItemProject** - Items tidak terpakai
2. **Circular Dependencies** - Bundle reference loops
3. **Stale Expanded Data** - Mismatch timestamp antara raw vs expanded
4. **Empty Bundles** - Bundle mengarah ke pekerjaan kosong
5. **Max Depth Violations** - Expansion depth > 3 levels
6. **Expansion Integrity** - Raw data ada tapi expanded tidak

---

## USAGE

### Basic Usage

```bash
# Audit single project
python manage.py audit_current_data --project-id=1

# Audit all projects
python manage.py audit_current_data --all-projects

# Detailed output (show item lists)
python manage.py audit_current_data --project-id=1 --detailed

# Generate markdown report
python manage.py audit_current_data --project-id=1 --output=report.md
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--project-id=N` | Audit specific project | `--project-id=1` |
| `--all-projects` | Audit all projects | `--all-projects` |
| `--detailed` | Show detailed item lists | `--detailed` |
| `--output=FILE` | Save report to markdown file | `--output=report.md` |

---

## AUDIT CHECKS EXPLAINED

### 1. Orphaned HargaItemProject

**Purpose:** Detect items created but no longer referenced in any pekerjaan.

**How It Works:**
```python
# Find all HargaItemProject
total_items = HargaItemProject.objects.filter(project=project)

# Get all kode referenced in DetailAHSPExpanded
referenced = DetailAHSPExpanded.objects.values_list('kode', flat=True).distinct()

# Orphaned = NOT in referenced list
orphaned = items NOT IN referenced
```

**Output Example:**
```
[1] Checking for Orphaned HargaItemProject...
  Total HargaItemProject: 150
  Referenced in expanded: 142
  Orphaned items: 8 (5.3%)
  Total value: Rp 2,450,000.00
  ⚠️  Found 8 orphaned items
```

**Interpretation:**
- **0 orphans:** ✅ Excellent! No cleanup needed
- **1-5%:** ✅ Normal - minor cleanup recommended
- **5-10%:** ⚠️ Moderate - schedule cleanup soon
- **>10%:** ❌ High - immediate cleanup required

**Action Required:**
- If >5%: Run manual cleanup via UI (FASE 1 deliverable)
- If >10%: Investigate why so many orphans (possible bug?)

---

### 2. Circular Dependencies

**Purpose:** Detect bundle reference loops (A→B→C→A).

**How It Works:**
```python
# Build dependency graph
graph = {pekerjaan_id: [list of ref_pekerjaan_id]}

# Use DFS to detect cycles
def has_cycle(node, visited, rec_stack):
    # Standard cycle detection algorithm
```

**Output Example:**
```
[2] Checking for Circular Dependencies...
  Total bundle references: 25
  Unique source pekerjaan: 12
  ❌ Found 1 circular dependencies!
    Cycle 1: 15 → 23 → 31 → 15
```

**Interpretation:**
- **0 cycles:** ✅ Excellent! No circular dependencies
- **Any cycles:** ❌ CRITICAL - Must fix immediately

**Action Required:**
- **IMMEDIATE FIX REQUIRED**
- Circular dependencies will cause infinite expansion loops
- Break the cycle by:
  1. Identifying which bundle should be removed
  2. Editing pekerjaan to remove problematic bundle
  3. Re-save to trigger re-expansion

**Root Cause:**
- User error: Created bundle chain inadvertently
- Validation bug: Should be blocked by code (check views_api.py)

---

### 3. Stale Expanded Data

**Purpose:** Detect when raw data (DetailAHSPProject) is newer than expanded data (DetailAHSPExpanded).

**How It Works:**
```python
raw_updated = DetailAHSPProject.objects.filter(pekerjaan=pkj).order_by('-updated_at').first()
expanded_updated = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).order_by('-updated_at').first()

if raw_updated.updated_at > expanded_updated.updated_at + 1s:
    # Stale!
```

**Output Example:**
```
[3] Checking for Stale Expanded Data...
  Total pekerjaan checked: 45
  Stale expanded data: 2
  ❌ Found 2 pekerjaan with stale expanded data!
    - Pekerjaan 123: A.001 - Pekerjaan Test
      Raw updated:      2025-11-13 10:30:15
      Expanded updated: 2025-11-13 09:15:42
      Diff: 4473 seconds (~75 minutes)
```

**Interpretation:**
- **0 stale:** ✅ Excellent! All data synchronized
- **1-3 stale:** ⚠️ Investigate - possible save error
- **>3 stale:** ❌ CRITICAL - expansion mechanism broken

**Action Required:**
- **Investigate root cause:**
  1. Check Django logs for [POPULATE_EXPANDED] errors
  2. Verify `_populate_expanded_from_raw()` was called
  3. Check for transaction rollback issues

- **Fix:**
  1. Edit affected pekerjaan (add/remove any item)
  2. Save → should trigger re-expansion
  3. Verify timestamps are now synchronized

**Root Cause:**
- Code bug: Expansion failed silently
- Transaction rollback: Save succeeded but expansion rolled back
- Migration issue: Old data before dual storage implementation

---

### 4. Empty Bundles

**Purpose:** Detect LAIN items referencing pekerjaan with no details.

**How It Works:**
```python
bundles = DetailAHSPProject.objects.filter(kategori='LAIN', ref_pekerjaan__isnull=False)

for bundle in bundles:
    target_count = DetailAHSPExpanded.objects.filter(pekerjaan=bundle.ref_pekerjaan).count()
    if target_count == 0:
        # Empty bundle!
```

**Output Example:**
```
[4] Checking for Empty Bundles...
  Total bundles checked: 18
  Empty bundles: 1
  ❌ Found 1 empty bundles!
    - Bundle: LAIN.001 in Pekerjaan 45 (A.010)
      → Target: Pekerjaan 32 (B.020) [EMPTY]
```

**Interpretation:**
- **0 empty:** ✅ Excellent! All bundles valid
- **Any empty:** ❌ CRITICAL - Should be blocked by validation

**Action Required:**
- **IMMEDIATE FIX REQUIRED**
- Empty bundles cause 0 components in expansion
- Fix by:
  1. Edit source pekerjaan (45)
  2. Remove empty bundle reference
  3. Or: Add details to target pekerjaan (32)

**Root Cause:**
- Validation bug: Empty bundle should be blocked (check views_api.py:~1400)
- Timing issue: Target was deleted after bundle created
- Migration artifact: Old data without validation

**Prevention:**
- Ensure validation in `views_api.py::api_save_detail_ahsp_for_pekerjaan()`
- Block bundle save if target has no expanded details

---

### 5. Max Depth Violations

**Purpose:** Detect expansion depth exceeding maximum allowed (3 levels).

**How It Works:**
```python
max_depth = 3
violations = DetailAHSPExpanded.objects.filter(
    project=project,
    expansion_depth__gt=max_depth
)
```

**Output Example:**
```
[5] Checking for Max Depth Violations...
  Max allowed depth: 3
  Violations found: 2
  ❌ Found 2 items exceeding max depth!
    - Pekerjaan 67 | Depth 4 | TK.001 - Mandor
      From bundle: LAIN.DEEP
```

**Interpretation:**
- **0 violations:** ✅ Excellent! All within limits
- **Any violations:** ❌ CRITICAL - Should be blocked by code

**Action Required:**
- **CRITICAL: Code bug detected**
- Max depth validation should prevent this (check `services.py`)
- Fix:
  1. Identify bundle chain causing deep nesting
  2. Restructure bundles to reduce depth
  3. Verify validation in `_recursive_expand_bundle()`

**Root Cause:**
- Validation bug: Max depth check not working
- Recursive expansion logic error
- Database constraint missing

---

### 6. Expansion Integrity

**Purpose:** Detect cases where raw data exists but expanded data is missing.

**How It Works:**
```python
for pekerjaan in project.pekerjaan_list:
    raw_count = DetailAHSPProject.objects.filter(pekerjaan=pkj).count()
    expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()

    if raw_count > 0 and expanded_count == 0:
        # Problem!
```

**Output Example:**
```
[6] Checking Expansion Integrity...
  Total pekerjaan checked: 45
  Expansion issues: 3
  ❌ Found 3 pekerjaan with expansion issues!
    - Pekerjaan 15: A.001 - Test Pekerjaan
      Raw count: 5
      Expanded count: 0
      Issue: NO_EXPANSION
```

**Interpretation:**
- **0 issues:** ✅ Excellent! All raw data expanded correctly
- **1-2 issues:** ⚠️ Investigate specific pekerjaan
- **>2 issues:** ❌ CRITICAL - Expansion mechanism broken

**Action Required:**
- **Investigate root cause:**
  1. Check if pekerjaan is old (before commit 54d123c)
  2. Check if LAIN uses AHSP master (ref_kind='ahsp')
  3. Check Django logs for expansion errors

- **Fix depending on cause:**
  - **Old data:** Run `python manage.py migrate_storage2 --project-id=X --fix`
  - **AHSP bundle:** Edit pekerjaan, remove AHSP bundle, use project bundle
  - **Code bug:** Debug `_populate_expanded_from_raw()`

**Root Cause:**
- Old data: Before dual storage implementation
- AHSP bundle: Not yet supported (FASE X feature)
- Code bug: Expansion failed silently

---

## SUCCESS CRITERIA

### Excellent Health (Ready for Production)
```
✅ Orphaned items: 0-3% (<5 items)
✅ Circular dependencies: 0
✅ Stale expanded data: 0
✅ Empty bundles: 0
✅ Max depth violations: 0
✅ Expansion integrity issues: 0
```

### Acceptable Health (Minor Issues)
```
⚠️ Orphaned items: 3-7% (5-10 items)
✅ Circular dependencies: 0
⚠️ Stale expanded data: 1-2 pekerjaan
✅ Empty bundles: 0
✅ Max depth violations: 0
⚠️ Expansion integrity issues: 1-2 (old data)
```

### Poor Health (Action Required)
```
❌ Orphaned items: >10%
❌ Circular dependencies: ANY
❌ Stale expanded data: >3 pekerjaan
❌ Empty bundles: ANY
❌ Max depth violations: ANY
❌ Expansion integrity issues: >3
```

---

## SAMPLE OUTPUT

### Clean Project Example

```
================================================================================
AUDITING PROJECT 1
================================================================================
--------------------------------------------------------------------------------
Project 1: Proyek Test Audit
--------------------------------------------------------------------------------
Created: 2025-11-01 10:00:00

[1] Checking for Orphaned HargaItemProject...
  Total HargaItemProject: 150
  Referenced in expanded: 148
  Orphaned items: 2 (1.3%)
  Total value: Rp 250,000.00
  ⚠️  Found 2 orphaned items

[2] Checking for Circular Dependencies...
  Total bundle references: 15
  Unique source pekerjaan: 8
  ✅ No circular dependencies found

[3] Checking for Stale Expanded Data...
  Total pekerjaan checked: 35
  Stale expanded data: 0
  ✅ No stale expanded data found

[4] Checking for Empty Bundles...
  Total bundles checked: 15
  Empty bundles: 0
  ✅ No empty bundles found

[5] Checking for Max Depth Violations...
  Max allowed depth: 3
  Violations found: 0
  ✅ No max depth violations found

[6] Checking Expansion Integrity...
  Total pekerjaan checked: 35
  Expansion issues: 0
  ✅ Expansion integrity is good

Summary for this project:
  Warnings: 1

================================================================================
AUDIT SUMMARY
================================================================================
⚠️  Warnings: 1
```

**Interpretation:** Excellent! Only minor orphan cleanup needed.

---

### Problematic Project Example

```
================================================================================
AUDITING PROJECT 5
================================================================================
--------------------------------------------------------------------------------
Project 5: Proyek Bermasalah
--------------------------------------------------------------------------------
Created: 2025-10-15 08:30:00

[1] Checking for Orphaned HargaItemProject...
  Total HargaItemProject: 200
  Referenced in expanded: 170
  Orphaned items: 30 (15.0%)
  Total value: Rp 4,500,000.00
  ⚠️  Found 30 orphaned items

[2] Checking for Circular Dependencies...
  Total bundle references: 25
  Unique source pekerjaan: 12
  ❌ Found 2 circular dependencies!
    Cycle 1: 45 → 52 → 58 → 45
    Cycle 2: 67 → 71 → 67

[3] Checking for Stale Expanded Data...
  Total pekerjaan checked: 50
  Stale expanded data: 5
  ❌ Found 5 pekerjaan with stale expanded data!

[4] Checking for Empty Bundles...
  Total bundles checked: 25
  Empty bundles: 1
  ❌ Found 1 empty bundles!

[5] Checking for Max Depth Violations...
  Max allowed depth: 3
  Violations found: 0
  ✅ No max depth violations found

[6] Checking Expansion Integrity...
  Total pekerjaan checked: 50
  Expansion issues: 3
  ❌ Found 3 pekerjaan with expansion issues!

Summary for this project:
  Critical Issues: 4
  Warnings: 1

================================================================================
AUDIT SUMMARY
================================================================================
❌ Critical Issues: 4
⚠️  Warnings: 1
```

**Interpretation:** CRITICAL! Multiple issues requiring immediate attention.

**Action Plan:**
1. **URGENT:** Fix circular dependencies (Cycles 1 & 2)
2. **HIGH:** Fix empty bundle
3. **HIGH:** Investigate 5 stale pekerjaan
4. **HIGH:** Fix 3 expansion integrity issues
5. **MEDIUM:** Schedule orphan cleanup (15% is high)

---

## TROUBLESHOOTING

### Error: "No module named 'django'"
**Cause:** Django not installed or virtual environment not activated

**Fix:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Or install Django
pip install -r requirements.txt
```

---

### Error: "Project X not found!"
**Cause:** Invalid project ID

**Fix:**
```bash
# List all projects
python manage.py shell
>>> from dashboard.models import Project
>>> Project.objects.values_list('id', 'nama')
```

---

### Script runs but shows 0 for everything
**Cause:** Database is empty or project has no data

**Fix:**
- Verify project has pekerjaan: `Pekerjaan.objects.filter(project_id=X).count()`
- Check if DetailAHSPProject has data
- May need to import AHSP data first

---

## NEXT STEPS AFTER AUDIT

### If Audit is Clean (0 issues)
✅ **Proceed to FASE 0.2: Test Coverage Baseline**

---

### If Minor Issues Found (1-2 warnings)
1. Schedule orphan cleanup (FASE 1)
2. Note issues for monitoring (FASE 0.3)
3. **Proceed to FASE 0.2**

---

### If Critical Issues Found (Any ❌)
1. **STOP** - Do not proceed to next phase
2. Fix all critical issues:
   - Circular dependencies: Break cycles
   - Empty bundles: Remove or fix
   - Stale data: Investigate + re-save
   - Expansion integrity: Debug root cause
3. **Re-run audit** to verify fixes
4. Once clean: Proceed to FASE 0.2

---

## MAINTENANCE

### Recommended Audit Schedule

| Frequency | When to Run | Purpose |
|-----------|-------------|---------|
| **Weekly** | Monday morning | Catch orphan accumulation |
| **Before deployment** | Pre-production | Verify data integrity |
| **After major changes** | Post-migration, post-refactor | Ensure no breakage |
| **Monthly** | First of month | Comprehensive health check |

---

## INTEGRATION WITH FASE 1

Audit script outputs feed directly into **FASE 1: Orphan Cleanup Mechanism**:

1. **Detection API** (FASE 1.1) will use same logic as Check #1
2. **Manual Cleanup UI** (FASE 1.2) will display orphaned items from Check #1
3. **Automated Cleanup** (FASE 1.3) will run Check #1 on schedule

---

## FILES CREATED

- ✅ `detail_project/management/commands/audit_current_data.py` (620 lines)
- ✅ `detail_project/FASE_0_AUDIT_GUIDE.md` (this document)

---

## DELIVERABLES CHECKLIST

- [x] Script: `audit_current_data.py`
- [x] Documentation: `FASE_0_AUDIT_GUIDE.md`
- [x] 6 audit checks implemented
- [x] Help command (`--help`)
- [x] Detailed output mode (`--detailed`)
- [x] Report generation (`--output`)
- [x] Success criteria defined
- [x] Troubleshooting guide included

---

**FASE 0.1 STATUS: ✅ COMPLETED**

**Next:** FASE 0.2 - Test Coverage Baseline
