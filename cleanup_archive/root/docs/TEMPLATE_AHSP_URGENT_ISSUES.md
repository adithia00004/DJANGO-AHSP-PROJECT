# ⚠️ Template AHSP - Urgent Issues & Action Plan

**Review Date**: 2025-11-10
**Reviewer**: Claude Code Assistant
**Status**: 🔴 **CRITICAL ISSUES FOUND**

---

## 🔥 CRITICAL (P0) - MUST FIX BEFORE PRODUCTION

### **1. Race Condition pada Concurrent Save** 🔴 BLOCKER

**Severity**: 🔴 **CRITICAL**
**Impact**: Silent data loss jika 2+ users edit pekerjaan yang sama bersamaan
**Likelihood**: HIGH di production multi-user environment

**Location**: `detail_project/views_api.py:1156-1167`

**Problem**:
```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan(request, project_id, pekerjaan_id):
    project = _owner_or_404(project_id, request.user)
    pkj = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)
    # ❌ NO select_for_update() here!

    # ... validation ...

    # Line 1330: DELETE old rows
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()

    # Line 1334: INSERT new rows
    DetailAHSPProject.objects.bulk_create(raw_details_to_create)
```

**Race Scenario**:
```
Time    User A                                  User B
T0      GET detail for Pekerjaan 1             -
T1      Edit koefisien: 2.0 → 3.0              -
T2      -                                      GET detail for Pekerjaan 1
T3      -                                      Edit koefisien: 2.0 → 5.0
T4      POST save → DELETE + INSERT (koef=3.0) -
T5      -                                      POST save → DELETE + INSERT (koef=5.0)
T6      ❌ User A's changes LOST               ✅ User B's data saved

Result: User A sees success, but data is GONE!
```

**Fix** (REQUIRED):
```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan(request, project_id, pekerjaan_id):
    project = _owner_or_404(project_id, request.user)

    # ✅ ADD: Lock the pekerjaan row to prevent concurrent edits
    pkj = (Pekerjaan.objects
           .select_for_update()  # ← ADD THIS
           .get(id=pekerjaan_id, project=project))

    # ... rest of code unchanged ...
```

**Why This Works**:
- `select_for_update()` acquires a **row-level lock** on Pekerjaan
- User B's request will **WAIT** until User A's transaction commits
- After User A commits, User B gets fresh data (no stale reads)
- **No silent data loss**

**Effort**: ⏱️ 5 minutes (1 line change + test)
**Risk**: 🟢 Very Low (standard Django pattern)
**Priority**: 🔴 **P0 - MUST FIX**

---

### **2. Race Condition di _upsert_harga_item** 🔴 HIGH

**Severity**: 🔴 **HIGH**
**Impact**: IntegrityError atau kategori flip-flop
**Likelihood**: MEDIUM (happens when same kode_item used by multiple pekerjaan)

**Location**: `detail_project/services.py:49-66`

**Problem**:
```python
def _upsert_harga_item(project, kategori, kode_item, uraian, satuan):
    obj, _created = HargaItemProject.objects.get_or_create(
        project=project,
        kode_item=kode_item,
        defaults=dict(kategori=kategori, uraian=uraian, satuan=satuan)
    )
    # ❌ No locking! Race condition between get_or_create and update
    changed = False
    if obj.kategori != kategori:
        obj.kategori = kategori; changed = True  # ← Kategori can flip-flop!
    # ...
    if changed:
        obj.save(update_fields=[...])
    return obj
```

**Race Scenario**:
```
Thread A: _upsert_harga_item(kategori='TK', kode='L.01')
Thread B: _upsert_harga_item(kategori='BHN', kode='L.01')

T1: A: get_or_create('L.01') → creates with kategori='TK'
T2: B: get_or_create('L.01') → gets existing, kategori='TK'
T3: B: sees kategori != 'BHN', updates to 'BHN'
T4: A: continues with kategori='TK' in memory
T5: A: sees kategori != 'TK', tries to update → kategori flip-flop!

Result: Kategori keeps changing based on last write
```

**Additional Problem**:
```python
# Line 1312: Called N times (once per row)
hip = _upsert_harga_item(project, kat, kode, uraian, satuan)
```
- **N+1 queries**: For 100 rows, this is 100 individual queries
- Not critical for performance, but inefficient

**Fix Option 1** (Recommended - Make kategori immutable):
```python
def _upsert_harga_item(project, kategori, kode_item, uraian, satuan):
    try:
        obj = HargaItemProject.objects.select_for_update().get(
            project=project,
            kode_item=kode_item
        )
        # ✅ Validate kategori is consistent
        if obj.kategori != kategori:
            raise ValidationError(
                f"Kode {kode_item} sudah ada dengan kategori {obj.kategori}. "
                f"Tidak bisa diubah ke {kategori}."
            )
        # Update metadata only
        changed = False
        if uraian and obj.uraian != uraian:
            obj.uraian = uraian; changed = True
        if (satuan or None) != obj.satuan:
            obj.satuan = satuan or None; changed = True
        if changed:
            obj.save(update_fields=["uraian", "satuan", "updated_at"])
        return obj

    except HargaItemProject.DoesNotExist:
        # Create new
        obj = HargaItemProject.objects.create(
            project=project,
            kode_item=kode_item,
            kategori=kategori,
            uraian=uraian,
            satuan=satuan
        )
        return obj
```

**Fix Option 2** (Include kategori in unique constraint):
```python
# models.py
class HargaItemProject(TimeStampedModel):
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["project", "kategori", "kode_item"],
                name="uniq_harga_kategori_kode_per_project"
            )
        ]
```
⚠️ **Requires migration + data cleanup**

**Effort**: ⏱️ 30 minutes (Option 1) or 2 hours (Option 2 + migration)
**Risk**: 🟡 Medium (needs testing)
**Priority**: 🔴 **P0 - MUST FIX**

---

## 🟡 HIGH PRIORITY (P1) - RECOMMENDED FIX

### **3. XSS Vulnerability di Contenteditable** 🟡 SECURITY

**Severity**: 🟡 **HIGH**
**Impact**: Potential XSS if malicious HTML injected
**Likelihood**: LOW (only affects team members, not public)

**Location**:
- `detail_project/templates/detail_project/template_ahsp.html:534` (contenteditable div)
- `detail_project/static/detail_project/js/template_ahsp.js:91,152,319` (textContent)

**Problem**:
```html
<!-- template_ahsp.html -->
<div class="cell-wrap" contenteditable="true" data-field="uraian"></div>
```

```javascript
// template_ahsp.js:91
$('.cell-wrap', tr).textContent = r.uraian || '';  // ✅ SAFE - textContent

// template_ahsp.js:319
$('.cell-wrap', tr).textContent = nama;  // ✅ SAFE - textContent

// template_ahsp.js:152 - Reading
uraian: $('.cell-wrap', tr).textContent.trim(),  // ✅ SAFE - textContent
```

**Good News**: ✅ **Already using textContent instead of innerHTML**
- `textContent` automatically escapes HTML
- No XSS vulnerability detected in current code

**Potential Issue**:
- Contenteditable allows **paste** of HTML content
- User bisa paste `<script>alert('XSS')</script>` dari clipboard

**Recommendation** (Optional hardening):
```javascript
// Add paste event handler to strip HTML
document.addEventListener('paste', (e) => {
  const el = e.target;
  if (!(el instanceof HTMLElement)) return;
  if (!el.classList.contains('cell-wrap')) return;
  if (!el.hasAttribute('contenteditable')) return;

  // Prevent default paste
  e.preventDefault();

  // Get plain text only (strip HTML)
  const text = (e.clipboardData || window.clipboardData).getData('text/plain');

  // Insert as plain text
  document.execCommand('insertText', false, text);
}, true);
```

**Effort**: ⏱️ 10 minutes
**Risk**: 🟢 Very Low
**Priority**: 🟡 **P1 - Recommended** (low urgency since already safe)

---

### **4. Kategori Mismatch Validation** 🟡 DATA INTEGRITY

**Severity**: 🟡 **MEDIUM**
**Impact**: Data inconsistency between DetailAHSPProject and HargaItemProject
**Likelihood**: MEDIUM (if same kode used across different kategori)

**Problem**:
```sql
-- Scenario: User creates detail with different kategori for same kode
-- DetailAHSPProject
pekerjaan_id | kategori | kode  | harga_item_id
1            | TK       | L.01  | 100

-- HargaItemProject (after _upsert_harga_item update)
id  | kategori | kode_item
100 | BHN      | L.01      ← MISMATCH!
```

**Impact**:
- Rekap calculations might use wrong kategori
- Filter by kategori returns inconsistent results
- Confusing for users

**Fix**: Implement immutable kategori (See Issue #2 Fix Option 1)

**Effort**: ⏱️ 30 minutes (same as Issue #2)
**Priority**: 🟡 **P1 - Recommended**

---

## 🟢 MEDIUM PRIORITY (P2) - NICE TO HAVE

### **5. Performance: Bulk Upsert Optimization** 🟢 OPTIMIZATION

**Severity**: 🟢 **LOW**
**Impact**: Slightly slower save for large datasets (100+ rows)
**Likelihood**: LOW (most pekerjaan have < 50 rows)

**Problem**:
```python
# Line 1312: Called N times (1 query per row)
for kat, kode, uraian, satuan, koef, ... in normalized:
    hip = _upsert_harga_item(project, kat, kode, uraian, satuan)  # N queries!
```

**Current Performance**:
- 100 rows → 100 individual queries
- Still acceptable (< 1 second on modern DB)

**Optimization** (Optional):
```python
def _bulk_upsert_harga_items(project, rows_data):
    """Optimize for bulk upsert."""
    kodes = {r['kode'] for r in rows_data}

    # Single query to fetch all existing
    existing = {
        obj.kode_item: obj
        for obj in HargaItemProject.objects.filter(
            project=project,
            kode_item__in=kodes
        ).select_for_update()
    }

    to_create = []
    to_update = []
    result_map = {}

    for r in rows_data:
        if r['kode'] in existing:
            obj = existing[r['kode']]
            # Validate & update
            if obj.kategori != r['kategori']:
                raise ValidationError(...)
            # ... update logic
            to_update.append(obj)
        else:
            # Create new
            obj = HargaItemProject(...)
            to_create.append(obj)

        result_map[r['kode']] = obj

    # Bulk operations
    HargaItemProject.objects.bulk_create(to_create, ignore_conflicts=True)
    HargaItemProject.objects.bulk_update(to_update, fields=[...])

    return result_map
```

**Benefit**:
- 100 rows: 100 queries → 3 queries (1 fetch + 1 create + 1 update)
- ~10x faster for large datasets

**Effort**: ⏱️ 2-3 hours
**Priority**: 🟢 **P2 - Nice to have**

---

### **6. Cache Invalidation Race** 🟢 MINOR

**Severity**: 🟢 **LOW**
**Impact**: Users see stale rekap data temporarily (self-healing after 5 min TTL)
**Likelihood**: LOW

**Problem**:
```python
# Line 1475: Invalidate BEFORE transaction commits
invalidate_rekap_cache(project)  # ← Called inside @transaction.atomic
# Transaction commits AFTER this
```

**Race Scenario**:
```
T1: Thread A: saves detail
T2: Thread A: cache.delete("rekap:123:v2")  ← Invalidate
T3: Thread B: compute_rekap() checks cache (MISS)
T4: Thread A: transaction.commit()  ← Data now visible
T5: Thread B: computes rekap using OLD data (before T4!)
T6: Thread B: cache.set("rekap:123:v2", stale_data)  ← Stale!
```

**Fix**:
```python
# Line 1475: Use transaction.on_commit()
transaction.on_commit(lambda: invalidate_rekap_cache(project))
```

**Effort**: ⏱️ 5 minutes
**Priority**: 🟢 **P2 - Low urgency** (auto-fixes after TTL)

---

## 📊 Priority Summary

| Priority | Issue | Severity | Effort | Status |
|----------|-------|----------|--------|--------|
| 🔴 **P0** | Concurrent save race condition | CRITICAL | 5 min | ⏳ **MUST FIX** |
| 🔴 **P0** | _upsert_harga_item race | HIGH | 30 min | ⏳ **MUST FIX** |
| 🟡 **P1** | XSS hardening (paste) | LOW | 10 min | ✅ Optional |
| 🟡 **P1** | Kategori mismatch validation | MEDIUM | 30 min | 🟡 Recommended |
| 🟢 **P2** | Bulk upsert optimization | LOW | 2-3 hours | 🟢 Nice to have |
| 🟢 **P2** | Cache invalidation race | LOW | 5 min | 🟢 Nice to have |

---

## 🎯 Recommended Action Plan

### **Phase 1: Critical Fixes (BEFORE PRODUCTION)** 🔴
**Timeline**: 1-2 hours
**Must Do**:

1. ✅ **Fix concurrent save race** (5 min)
   ```python
   # views_api.py:1167
   pkj = Pekerjaan.objects.select_for_update().get(id=pekerjaan_id, project=project)
   ```

2. ✅ **Fix _upsert_harga_item race + immutable kategori** (30 min)
   ```python
   # services.py:49
   # Implement select_for_update() + kategori validation
   ```

3. ✅ **Test concurrent scenarios** (30 min)
   ```python
   # Write test: 2 users save same pekerjaan simultaneously
   # Expected: Second user waits, no data loss
   ```

**Total Effort**: ~1 hour
**Impact**: 🔴 **CRITICAL** - Prevents silent data loss

---

### **Phase 2: High Priority Fixes (NEXT SPRINT)** 🟡
**Timeline**: 1 day
**Recommended**:

4. ✅ **Add paste sanitization** (10 min)
5. ✅ **Fix cache invalidation timing** (5 min)
6. ✅ **Write integration tests** (2 hours)

**Total Effort**: ~3 hours
**Impact**: 🟡 **HIGH** - Improved robustness

---

### **Phase 3: Performance Optimization (FUTURE)** 🟢
**Timeline**: Optional
**Nice to have**:

7. ⏸️ **Bulk upsert optimization** (2-3 hours)
8. ⏸️ **Add audit log** (1 day)
9. ⏸️ **Implement optimistic locking UI** (2 days)

**Total Effort**: ~4 days
**Impact**: 🟢 **LOW** - Marginal performance improvement

---

## 🧪 Testing Checklist (CRITICAL)

**Before deploying to production**:

### Concurrent Edit Test:
```python
# test_concurrent_save.py
def test_concurrent_save_no_data_loss():
    """
    Test: 2 users edit same pekerjaan simultaneously.
    Expected: No data loss, second user waits for first.
    """
    # Setup: Create pekerjaan with initial details
    # Thread 1: Save with koef=3.0
    # Thread 2: Save with koef=5.0 (concurrent)
    # Assert: One of them succeeds, other gets fresh data
    # Assert: No silent data loss
```

### Race Condition Test:
```python
def test_upsert_harga_item_concurrent():
    """
    Test: 2 threads upsert same kode_item with different kategori.
    Expected: One succeeds, other raises ValidationError.
    """
    # Thread 1: _upsert_harga_item(kategori='TK', kode='L.01')
    # Thread 2: _upsert_harga_item(kategori='BHN', kode='L.01')
    # Assert: One succeeds, other gets ValidationError
```

---

## ✅ What's Already Good

1. ✅ **@transaction.atomic** - All save operations are atomic
2. ✅ **CSRF protection** - Frontend sends CSRF token
3. ✅ **Circular dependency detection** - Bundle validation working
4. ✅ **Input validation** - Comprehensive frontend + backend validation
5. ✅ **XSS protection** - Using textContent (not innerHTML)
6. ✅ **Test coverage** - Excellent (21 tests, 1064 lines)
7. ✅ **Documentation** - Comprehensive (1191 lines)

---

## 🚀 Deployment Recommendation

**Current Status**: ⚠️ **NOT READY for production multi-user environment**

**Blocker**:
- 🔴 Race condition issues (P0)

**Safe Scenarios**:
- ✅ Single-user environment (development, testing)
- ✅ Low-concurrency environment (< 5 simultaneous users)
- ✅ Sequential editing (one user at a time per pekerjaan)

**After P0 Fixes**:
- ✅ **READY for production multi-user environment**

---

## 📝 Implementation Checklist

```markdown
Phase 1 (CRITICAL - 1 hour):
[ ] Add select_for_update() to api_save_detail_ahsp_for_pekerjaan
[ ] Refactor _upsert_harga_item with locking + immutable kategori
[ ] Write concurrent edit test
[ ] Test on staging environment
[ ] Deploy to production

Phase 2 (HIGH - 3 hours):
[ ] Add paste event sanitization
[ ] Fix cache invalidation timing (transaction.on_commit)
[ ] Write integration tests
[ ] Update documentation

Phase 3 (OPTIONAL - 4 days):
[ ] Implement bulk upsert optimization
[ ] Add audit log
[ ] Implement optimistic locking UI
```

---

**Report Date**: 2025-11-10
**Next Review**: After P0 fixes implemented
**Status**: 🔴 **ACTION REQUIRED**
