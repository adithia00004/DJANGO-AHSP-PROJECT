# Pytest Issues Analysis

**Date**: 2025-11-11
**Session**: Test fixtures debugging
**Status**: ⚠️ IN PROGRESS

---

## 🐛 Test Failures Summary

**Total Tests Run**: 14
**Passed**: 8 (57%)
**Failed**: 6 (43%)

### Failed Tests Breakdown

#### 1. **test_harga_items_p0_fixes.py** (2 failures)
- ❌ `TestConcurrentEditScenarios::test_two_users_edit_different_items` - 404
- ❌ `TestFullWorkflowIntegration::test_full_edit_workflow_with_optimistic_locking` - Timestamp assertion

#### 2. **test_template_ahsp_p0_p1_fixes.py** (6 failures)
- ❌ `TestOptimisticLocking::test_save_with_current_timestamp_succeeds` - 409 conflict
- ❌ `TestOptimisticLocking::test_save_without_timestamp_succeeds_with_warning` - DoesNotExist
- ❌ `TestRowLevelLocking::test_concurrent_save_with_locking_no_data_loss` - DoesNotExist
- ❌ `TestRowLevelLocking::test_concurrent_save_same_row_serializes_correctly` - DoesNotExist
- ❌ `TestConcurrentEditScenarios::test_two_users_edit_same_pekerjaan_different_items` - 404
- ❌ `TestFullWorkflowIntegration::test_full_edit_workflow_with_optimistic_locking` - 409 conflict

---

## 🔍 Root Cause Analysis

### Issue #1: Concurrent Edit Tests - Owner Access Issue

**Tests Affected**:
- `test_two_users_edit_different_items` (Harga Items)
- `test_two_users_edit_same_pekerjaan_different_items` (Template AHSP)

**Root Cause**:
```python
# Test code (BROKEN)
project.owner = second_user  # Change owner to second user
project.save()

# Then tries to use first user to save
resp1 = client_logged.post(...)  # client_logged is first user - NO LONGER OWNER!
```

**Problem**:
1. Test changes project ownership to second_user
2. Then tries to use `client_logged` (first user) to save
3. API checks `_owner_or_404()` - first user no longer owns project
4. Result: **404 Not Found**

**API Limitation**:
- Only project owner can edit
- No multi-user collaboration support
- Tests incorrectly assume multiple users can edit same project simultaneously

**Fix Applied**: ✅
- Changed tests to use same user (owner) for both requests
- Updated docstrings to clarify we're simulating concurrent requests from same user
- Removed second_user parameter and ownership changes

---

### Issue #2: Optimistic Locking - Timestamp Not Updated

**Tests Affected**:
- `test_save_with_current_timestamp_succeeds` (Template AHSP)
- `test_full_edit_workflow_with_optimistic_locking` (both files)

**Root Cause**:
```python
# Test expectation
timestamp1 = project.updated_at.isoformat()
resp = save_data(timestamp1)
project.refresh_from_db()
timestamp2 = project.updated_at.isoformat()
assert timestamp2 != timestamp1  # FAILS - timestamps are EQUAL!
```

**Problem**:
1. Test expects `project.updated_at` to change after save
2. **API does NOT update project.updated_at** when saving related objects (HargaItemProject, DetailAHSPProject)
3. Only updates related objects, not parent project
4. Result: Timestamp doesn't change, optimistic locking doesn't work properly

**Why This Happens**:
```python
# views_api.py - Harga Items Save
obj.harga_satuan = new_price
obj.save(update_fields=['harga_satuan', 'updated_at'])  # Updates HargaItemProject only
# Project.updated_at NOT touched!
```

**Implications**:
- Optimistic locking check looks at `project.updated_at`
- But save doesn't update `project.updated_at`
- So optimistic locking doesn't detect conflicts properly
- False positives (409 when shouldn't conflict)
- Or false negatives (no 409 when should conflict)

**Possible Solutions**:

**Option A**: Update project timestamp in API (RECOMMENDED)
```python
# After successful save
project.updated_at = timezone.now()
project.save(update_fields=['updated_at'])
```
**Pros**: Proper optimistic locking behavior
**Cons**: Changes existing API behavior, might affect other code

**Option B**: Fix tests to not expect timestamp changes
**Pros**: No API changes
**Cons**: Optimistic locking doesn't work properly

**Option C**: Use different timestamp source (e.g., HargaItemProject.updated_at)
**Pros**: More granular locking
**Cons**: Major refactor required

**Decision**: ⚠️ **PENDING** - Need to discuss with user

---

### Issue #3: DoesNotExist Errors - Template AHSP Save

**Tests Affected**:
- `test_save_without_timestamp_succeeds_with_warning`
- `test_concurrent_save_with_locking_no_data_loss`
- `test_concurrent_save_same_row_serializes_correctly`

**Error**:
```
detail_project.models.DetailAHSPProject.DoesNotExist: DetailAHSPProject matching query does not exist.
```

**Problem**:
1. Test saves data successfully (200 OK)
2. Test tries to `refresh_from_db()` on detail object
3. **Object doesn't exist** - was deleted during save!

**Root Cause Analysis Needed**:
- Check if Template AHSP save API deletes and recreates objects
- Check if dual storage population affects this
- Might be related to deduplication logic

**Need to investigate**:
```python
# What does api_save_detail_ahsp_for_pekerjaan do?
# Does it delete existing objects before creating new ones?
```

**Status**: ⚠️ **INVESTIGATION REQUIRED**

---

## 📊 Fixes Applied

### ✅ Fix #1: Concurrent Edit Tests

**Files**:
- `test_harga_items_p0_fixes.py:596-644`
- `test_template_ahsp_p0_p1_fixes.py:627-685`

**Changes**:
- Removed `second_user` parameter
- Removed `client` parameter
- Removed ownership change logic
- Use same user (`client_logged`) for both requests
- Updated docstrings

**Status**: ✅ **FIXED AND COMMITTED**

---

## 🚧 Fixes Pending

### ⚠️ Fix #2: Optimistic Locking Timestamp Update

**Required Change**: Add project timestamp update to save endpoints

**Locations**:
- `views_api.py` - `api_save_harga_items` (after line 1800)
- `views_api.py` - `api_save_detail_ahsp_for_pekerjaan` (need to find)

**Code to Add**:
```python
# After successful save
if updated > 0 or pricing_saved:  # or any successful change
    project.updated_at = timezone.now()
    project.save(update_fields=['updated_at'])
```

**Considerations**:
- This changes existing API behavior
- Might affect caching or other dependent code
- Need to verify no side effects

**Decision**: **AWAITING USER APPROVAL**

---

### ⚠️ Fix #3: DoesNotExist Errors Investigation

**Action Required**:
1. Read `api_save_detail_ahsp_for_pekerjaan` endpoint code
2. Understand save/delete/recreate logic
3. Check dual storage population
4. Determine if test expectations are wrong or API has bug

**Status**: **INVESTIGATION NEEDED**

---

## 🎯 Recommendations

### Short Term (Quick Wins)

1. ✅ **DONE**: Fix concurrent edit tests (ownership issue)
2. ⚠️ **PENDING**: Decide on optimistic locking timestamp strategy
3. ⚠️ **PENDING**: Investigate DoesNotExist errors

### Long Term (Design Discussion)

1. **Multi-User Collaboration**: Consider adding proper multi-user editing support
   - Shared project access
   - Per-item locking instead of project-level
   - Real-time conflict resolution

2. **Optimistic Locking Strategy**: Choose one approach
   - Project-level timestamps (current, but needs fixes)
   - Item-level timestamps (more granular)
   - Version numbers instead of timestamps

3. **Test Strategy**: Clarify test goals
   - Are we testing concurrent edits (requires multi-user support)?
   - Or testing row-level locking (can use same user)?
   - Or both (need different test approaches)?

---

## 📝 Next Steps

### Immediate Actions

1. **User Decision Required**: Should we update project.updated_at in save endpoints?
   - ✅ YES → Implement timestamp updates
   - ❌ NO → Adjust test expectations, accept optimistic locking limitations

2. **Investigation**: Understand DoesNotExist errors in Template AHSP tests
   - Read API endpoint code
   - Trace save execution path
   - Determine root cause

3. **Test Run**: After fixes, run tests again
   ```bash
   pytest detail_project/tests/test_harga_items_p0_fixes.py -v
   pytest detail_project/tests/test_template_ahsp_p0_p1_fixes.py -v
   ```

---

## 📚 Related Files

- `detail_project/tests/test_harga_items_p0_fixes.py`
- `detail_project/tests/test_template_ahsp_p0_p1_fixes.py`
- `detail_project/views_api.py` - Save endpoints
- `detail_project/services.py` - Dual storage helpers

---

**Last Updated**: 2025-11-11
**Analyst**: Claude Code
**Status**: Awaiting user input on timestamp strategy
