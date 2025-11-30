# Phase 0 Migration Log

**Created**: 2025-11-27
**Purpose**: Track database migration 0043 (remove legacy proportion field)

---

## Migration Overview

**Migration Number**: 0043
**Migration Name**: `remove_legacy_proportion_field`
**Parent Migration**: 0024 (add planned/actual fields)

**Purpose**:
Remove the legacy `proportion` field from `PekerjaanProgressWeekly` model after migrating all data to `planned_proportion` field.

**Impact**:
- ✅ Eliminates technical debt from dual-state architecture
- ✅ Removes circular sync logic (`_normalize_proportion_fields`)
- ✅ Single source of truth for planned vs actual progress
- ⚠️ Breaking change: Any code referencing `.proportion` will fail

---

## Pre-Migration Checklist

### Data Validation Queries

Run these queries BEFORE migration to understand current state:

```sql
-- 1. Count total records
SELECT COUNT(*) as total_records
FROM detail_project_pekerjaanprogressweekly;

-- 2. Count records with NULL proportion (should be 0)
SELECT COUNT(*) as null_proportion
FROM detail_project_pekerjaanprogressweekly
WHERE proportion IS NULL;

-- 3. Count records with NULL planned_proportion (these will be migrated)
SELECT COUNT(*) as null_planned
FROM detail_project_pekerjaanprogressweekly
WHERE planned_proportion IS NULL AND proportion IS NOT NULL;

-- 4. Sample records that will be migrated
SELECT id, pekerjaan_id, week_number, proportion, planned_proportion, actual_proportion
FROM detail_project_pekerjaanprogressweekly
WHERE planned_proportion IS NULL AND proportion IS NOT NULL
LIMIT 10;

-- 5. Verify data consistency
SELECT
  COUNT(*) as inconsistent_records
FROM detail_project_pekerjaanprogressweekly
WHERE planned_proportion IS NOT NULL
  AND proportion IS NOT NULL
  AND planned_proportion != proportion;
```

**Expected Results** (Document here after running):
- Total records: _____
- Records with NULL proportion: _____
- Records to migrate: _____
- Inconsistent records: _____

---

## Migration Execution Log

### Local Environment

**Date**: 2025-11-27
**Database**: Local PostgreSQL
**User**: Adit

#### Pre-Migration State

```bash
# Note: Migration 0024 already copied all data to planned_proportion
# No need for separate validation queries
```

**Validation Results**:
```
Total records: 5
Records to migrate: 0 (migration 0024 already handled this)
```

#### Apply Migration

```bash
# Apply migration
python manage.py migrate detail_project 0025

# Output:
Operations to perform:
  Target specific migration: 0025_remove_legacy_proportion_field, from detail_project
Running migrations:
  Applying detail_project.0025_remove_legacy_proportion_field...
[Migration 0025] SUCCESS: No records need migration (all data already in planned_proportion)
[Migration 0025] SUCCESS: All records have valid planned_proportion
 OK
```

**Status**: ✅ SUCCESS

**Issues encountered**: None

#### Post-Migration Validation

```sql
-- 1. Verify proportion field removed
SELECT column_name
FROM information_schema.columns
WHERE table_name='detail_project_pekerjaanprogressweekly'
  AND column_name='proportion';
-- Expected: 0 rows

-- 2. Verify all planned_proportion filled
SELECT COUNT(*) as null_planned
FROM detail_project_pekerjaanprogressweekly
WHERE planned_proportion IS NULL;
-- Expected: 0

-- 3. Verify data integrity
SELECT COUNT(*) as total
FROM detail_project_pekerjaanprogressweekly;
-- Expected: Same as pre-migration total
```

**Validation Results**:
```
proportion field exists: _____
NULL planned_proportion: _____
Total records: _____
```

#### Rollback Test

```bash
# Rollback migration
python manage.py migrate detail_project 0042

# Verify proportion field restored
python manage.py shell
>>> from detail_project.models import PekerjaanProgressWeekly
>>> PekerjaanProgressWeekly._meta.get_field('proportion')

# Re-apply migration
python manage.py migrate detail_project 0043
```

**Rollback Status**: ⬜ SUCCESS / ⬜ FAILED

**Issues encountered**: ___________

---

### Staging Environment

**Date**: ___________
**Database**: Staging PostgreSQL
**User**: ___________

#### Pre-Migration State

```bash
# Backup database
ssh staging
pg_dump django_ahsp_staging > backups/pre_0043_staging_$(date +%Y%m%d_%H%M%S).sql

# Run validation queries
python manage.py shell < scripts/validate_proportion_migration.sql
```

**Validation Results**:
```
Total records: _____
Records to migrate: _____
```

#### Apply Migration

```bash
# Pull latest code
git pull origin main

# Apply migration
python manage.py migrate detail_project 0043

# Output:
# [Copy console output here]
```

**Status**: ⬜ SUCCESS / ⬜ FAILED

**Issues encountered**: ___________

#### Post-Migration Validation

Run same validation queries as local environment.

**Validation Results**:
```
proportion field exists: _____
NULL planned_proportion: _____
Total records: _____
```

#### Smoke Test

```bash
# Restart Django server
sudo systemctl restart gunicorn

# Open browser
# Navigate to: https://staging.example.com/detail_project/110/kelola-tahapan/

# Verify:
# 1. Page loads without errors
# 2. Grid renders with data
# 3. Charts render (Gantt + Kurva S)
# 4. Can input new values
# 5. Save works correctly
```

**Smoke Test Status**: ⬜ PASS / ⬜ FAIL

**Issues encountered**: ___________

---

## Code Changes Log

### Files Modified

#### 1. models.py

**File**: `detail_project/models.py`
**Lines Modified**: ~710, ~780-796
**Commit**: ___________

**Changes**:
- ✅ Removed `proportion` field declaration
- ✅ Removed `_normalize_proportion_fields()` method
- ✅ Removed calls to `_normalize_proportion_fields()` in save()
- ✅ Updated model docstring

**Before**:
```python
class PekerjaanProgressWeekly(models.Model):
    planned_proportion = models.DecimalField(...)
    actual_proportion = models.DecimalField(...)
    proportion = models.DecimalField(...)  # LEGACY

    def _normalize_proportion_fields(self):
        # Sync logic
```

**After**:
```python
class PekerjaanProgressWeekly(models.Model):
    planned_proportion = models.DecimalField(...)
    actual_proportion = models.DecimalField(...)
    # proportion field removed - use planned_proportion or actual_proportion
```

---

#### 2. views_api.py (if modified)

**File**: `detail_project/views_api.py`
**Lines Modified**: ___________
**Commit**: ___________

**Changes**:
- [ ] Updated serializers to remove `proportion` field
- [ ] Updated API endpoints to use `planned_proportion` or `actual_proportion`

**Code Search Results**:
```bash
grep -n "\.proportion" detail_project/views_api.py
# [Paste results here]
```

---

#### 3. Other Files (if modified)

Document any other files that reference `.proportion` field:

```bash
grep -r "\.proportion" detail_project/ --include="*.py"
# [Paste results here]
```

**Files to update**:
- [ ] ___________
- [ ] ___________

---

## Testing Log

### Unit Tests

**Test Command**:
```bash
pytest detail_project/tests/ -v
```

**Before Migration**:
```
Total tests: _____
Passed: _____
Failed: _____
```

**After Migration**:
```
Total tests: _____
Passed: _____
Failed: _____
```

**Failed Tests** (if any):
- Test name: ___________
  - Reason: ___________
  - Fix applied: ___________

---

### Integration Tests

**Test Scenarios**:

#### Scenario 1: Load Jadwal Pekerjaan Page
- [ ] Page loads without errors
- [ ] Grid renders with correct data
- [ ] Charts render (Gantt + Kurva S)
- [ ] Console shows no errors

**Status**: ⬜ PASS / ⬜ FAIL
**Notes**: ___________

#### Scenario 2: Input Progress Data
- [ ] Can input percentage in Perencanaan mode
- [ ] Chart updates in real-time
- [ ] Save works correctly
- [ ] Data persists after refresh

**Status**: ⬜ PASS / ⬜ FAIL
**Notes**: ___________

#### Scenario 3: Mode Switching
- [ ] Can switch to Realisasi mode
- [ ] Can input percentage in Realisasi mode
- [ ] Both modes show correct data
- [ ] Charts render both curves correctly

**Status**: ⬜ PASS / ⬜ FAIL
**Notes**: ___________

---

## Rollback Procedure

### When to Rollback

Trigger rollback if:
1. Migration fails on staging
2. Data loss detected in validation queries
3. Critical functionality broken (grid doesn't load, save fails)
4. API errors in production logs

### Rollback Steps

#### Database Rollback

```bash
# 1. Stop application server
sudo systemctl stop gunicorn

# 2. Rollback migration
python manage.py migrate detail_project 0042

# 3. Verify proportion field restored
python manage.py dbshell
\d detail_project_pekerjaanprogressweekly
# Should see 'proportion' column

# 4. Restore from backup (if needed)
psql django_ahsp_db < backups/pre_0043_staging_YYYYMMDD_HHMMSS.sql

# 5. Restart application
sudo systemctl start gunicorn
```

#### Code Rollback

```bash
# 1. Revert model changes
git revert <commit-hash>

# 2. Rebuild static files (if needed)
npm run build

# 3. Collect static
python manage.py collectstatic --noinput

# 4. Restart application
sudo systemctl restart gunicorn
```

#### Verification After Rollback

- [ ] Page loads correctly
- [ ] Old code using `.proportion` works
- [ ] No data loss
- [ ] Charts render correctly

---

## Lessons Learned

### What Went Well
- ___________
- ___________

### What Could Be Improved
- ___________
- ___________

### Unexpected Issues
- ___________
- ___________

### Recommendations for Future Migrations
- ___________
- ___________

---

## Sign-Off

### Local Environment
- **Tested by**: ___________
- **Date**: ___________
- **Status**: ⬜ APPROVED / ⬜ REJECTED

### Staging Environment
- **Tested by**: ___________
- **Date**: ___________
- **Status**: ⬜ APPROVED / ⬜ REJECTED

### Production Environment (Week 5)
- **Deployed by**: ___________
- **Date**: ___________
- **Status**: ⬜ APPROVED / ⬜ REJECTED

---

**Last Updated**: 2025-11-27
**Migration Status**: 🟡 READY FOR EXECUTION
**Next Update**: After Day 1 execution
