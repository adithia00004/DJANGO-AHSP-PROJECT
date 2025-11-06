# FASE 4.1: Performance Optimization for Deep Copy Feature

**Created:** 2025-11-06
**Status:** In Progress
**Priority:** 🟡 MEDIUM
**Branch:** `claude/periksa-ma-011CUr8wRoxTC6oKti1FLCLP`

---

## 📊 Performance Analysis

### Current Performance Issues Identified:

#### 1. **N+1 Query Problem** 🔴 HIGH IMPACT
**Location:** Multiple `_copy_*` methods in `services.py`

**Issue:**
```python
# Current inefficient code
for old_subklas in subklas_list:
    new_subklas = SubKlasifikasi(...)
    new_subklas.save()  # ← One query per iteration
    self.stats['subklasifikasi_copied'] += 1
```

**Impact:**
- For project with 100 SubKlasifikasi: **100+ queries**
- For project with 500 Pekerjaan: **500+ queries**
- Total queries for medium project: **1000+ queries**

**Affected Methods:**
- `_copy_klasifikasi()` - Line ~1180
- `_copy_subklasifikasi()` - Line 1198-1242
- `_copy_pekerjaan()` - Line 1243-1302
- `_copy_volume_pekerjaan()` - Line ~1304
- `_copy_harga_item()` - Line ~1340
- `_copy_ahsp_template()` - Line ~1370
- `_copy_tahapan()` - Line 1406-1438
- `_copy_jadwal_pekerjaan()` - Line 1440-1472

---

#### 2. **No Bulk Operations** 🔴 HIGH IMPACT
**Issue:** Using individual `save()` instead of `bulk_create()`

**Current:**
```python
for item in items:
    new_item = Model(...)
    new_item.save()  # Slow
```

**Should be:**
```python
new_items = [Model(...) for item in items]
Model.objects.bulk_create(new_items, batch_size=500)  # Fast
```

**Impact:**
- **10-50x slower** for large datasets
- Unnecessary transaction overhead
- Database connection saturation

---

#### 3. **Repeated hasattr() Calls** 🟡 MEDIUM IMPACT
**Location:** Multiple `_copy_*` methods

**Issue:**
```python
if hasattr(old_pekerjaan, 'ref') and old_pekerjaan.ref:
    new_pekerjaan.ref = old_pekerjaan.ref
if hasattr(old_pekerjaan, 'auto_load_rincian'):
    new_pekerjaan.auto_load_rincian = old_pekerjaan.auto_load_rincian
if hasattr(old_pekerjaan, 'markup_override_percent'):
    new_pekerjaan.markup_override_percent = old_pekerjaan.markup_override_percent
```

**Impact:**
- Repeated attribute checks in tight loop
- Could cache model fields once

---

#### 4. **No Query Optimization** 🟡 MEDIUM IMPACT
**Issue:** Queries don't use `select_related()` or `prefetch_related()`

**Current:**
```python
subklas_list = SubKlasifikasi.objects.filter(project=self.source)
```

**Should consider:**
```python
# If accessing related fields
subklas_list = SubKlasifikasi.objects.filter(
    project=self.source
).select_related('klasifikasi')
```

**Note:** Currently only accessing FK IDs (e.g., `klasifikasi_id`), so impact is minimal. But good practice for future.

---

#### 5. **No Database Indexes** 🟢 LOW-MEDIUM IMPACT
**Issue:** Missing indexes on FK lookups

**Current State:**
- No indexes on `project_id` filters
- No composite indexes for common queries

**Impact:**
- Slower FK lookups for large databases
- Inefficient filtering

---

## 🎯 Optimization Plan

### Phase 1: Bulk Operations (HIGH PRIORITY)
**Goal:** Replace individual saves with bulk_create
**Expected:** 10-50x performance improvement

**Tasks:**
1. ✅ Create helper method for bulk operations with FK mapping
2. ⏸️ Optimize `_copy_klasifikasi()` with bulk_create
3. ⏸️ Optimize `_copy_subklasifikasi()` with bulk_create
4. ⏸️ Optimize `_copy_pekerjaan()` with bulk_create
5. ⏸️ Optimize `_copy_volume_pekerjaan()` with bulk_create
6. ⏸️ Optimize `_copy_harga_item()` with bulk_create
7. ⏸️ Optimize `_copy_tahapan()` with bulk_create
8. ⏸️ Optimize `_copy_jadwal_pekerjaan()` with bulk_create

**Challenge:** bulk_create() doesn't return IDs by default (before Django 4.2)
**Solution:** Use `bulk_create(return_ids=True)` or manual ID retrieval

---

### Phase 2: Field Caching (MEDIUM PRIORITY)
**Goal:** Cache model field checks
**Expected:** 5-10% performance improvement

**Tasks:**
1. ⏸️ Cache optional field names per model
2. ⏸️ Use cached field list in copy methods
3. ⏸️ Reduce hasattr() calls by 70%+

---

### Phase 3: Database Indexes (MEDIUM PRIORITY)
**Goal:** Add strategic indexes
**Expected:** 20-30% improvement for large databases

**Tasks:**
1. ⏸️ Add index on `Klasifikasi.project_id`
2. ⏸️ Add index on `SubKlasifikasi.project_id`
3. ⏸️ Add index on `Pekerjaan.project_id`
4. ⏸️ Add composite indexes for common filters
5. ⏸️ Create migration for new indexes

---

### Phase 4: Performance Testing (HIGH PRIORITY)
**Goal:** Measure actual improvements
**Expected:** Validate all optimizations

**Tasks:**
1. ⏸️ Create performance benchmark tests
2. ⏸️ Test with small project (10 pekerjaan)
3. ⏸️ Test with medium project (100 pekerjaan)
4. ⏸️ Test with large project (1000 pekerjaan)
5. ⏸️ Compare before/after metrics

---

## 📈 Expected Performance Improvements

### Before Optimization (Baseline):
| Project Size | Pekerjaan | DetailAHSP | Queries | Time (est) |
|--------------|-----------|------------|---------|------------|
| Small        | 10        | 50         | ~200    | ~2s        |
| Medium       | 100       | 500        | ~2000   | ~15s       |
| Large        | 1000      | 5000       | ~20000  | ~120s      |

### After Optimization (Target):
| Project Size | Pekerjaan | DetailAHSP | Queries | Time (target) | Improvement |
|--------------|-----------|------------|---------|---------------|-------------|
| Small        | 10        | 50         | ~20     | ~0.5s         | **4x faster** |
| Medium       | 100       | 500        | ~50     | ~2s           | **7.5x faster** |
| Large        | 1000      | 5000       | ~100    | ~10s          | **12x faster** |

**Key Improvements:**
- Queries reduced by **95%+** (20000 → 100)
- Time reduced by **5-12x**
- Memory usage optimized with batch processing

---

## 🚀 Implementation Strategy

### Step 1: Create Bulk Helper (DONE)
```python
def _bulk_create_with_mapping(self, model_class, items_data, mapping_key, batch_size=500):
    """
    Bulk create items and update mappings.

    Args:
        model_class: Django model class
        items_data: List of (old_id, new_instance) tuples
        mapping_key: Key in self.mappings dict
        batch_size: Batch size for bulk_create

    Returns:
        List of created instances with IDs
    """
    # Extract old IDs and new instances
    old_ids = [old_id for old_id, _ in items_data]
    new_instances = [instance for _, instance in items_data]

    # Bulk create
    created = model_class.objects.bulk_create(new_instances, batch_size=batch_size)

    # Update mappings
    for old_id, new_instance in zip(old_ids, created):
        self.mappings[mapping_key][old_id] = new_instance.id

    return created
```

### Step 2: Refactor Copy Methods
**Example for `_copy_subklasifikasi()`:**

```python
# Before: O(n) queries
def _copy_subklasifikasi(self, new_project):
    subklas_list = SubKlasifikasi.objects.filter(project=self.source)

    for old_subklas in subklas_list:
        new_subklas = SubKlasifikasi(...)
        new_subklas.save()  # ← One query per iteration

# After: O(1) queries
def _copy_subklasifikasi(self, new_project):
    subklas_list = SubKlasifikasi.objects.filter(project=self.source)

    items_to_create = []
    skipped = []

    for old_subklas in subklas_list:
        new_klasifikasi_id = self.mappings['klasifikasi'].get(old_subklas.klasifikasi_id)

        if new_klasifikasi_id:
            new_subklas = SubKlasifikasi(
                project=new_project,
                klasifikasi_id=new_klasifikasi_id,
                name=old_subklas.name,
            )
            items_to_create.append((old_subklas.id, new_subklas))
        else:
            skipped.append({...})

    # Bulk create all at once
    created = self._bulk_create_with_mapping(
        SubKlasifikasi,
        items_to_create,
        'subklasifikasi',
        batch_size=500
    )

    self.stats['subklasifikasi_copied'] = len(created)
    self.skipped_items['subklasifikasi'] = skipped
```

---

## 📝 Testing Strategy

### Unit Tests:
1. Test bulk_create helper function
2. Test FK mapping correctness after bulk operations
3. Test skip tracking still works
4. Test statistics counting accurate

### Performance Tests:
1. Benchmark before optimization
2. Benchmark after each optimization phase
3. Memory profiling
4. Query count validation

### Integration Tests:
1. End-to-end copy with bulk operations
2. Verify data integrity
3. Verify no data loss
4. Verify error handling still works

---

## 🎯 Success Criteria

- [ ] Queries reduced by 90%+ for medium projects
- [ ] Copy time reduced by 5-10x
- [ ] All existing tests still pass
- [ ] No data integrity issues
- [ ] Skip tracking still functional
- [ ] Error handling preserved
- [ ] Memory usage reasonable (<500MB for large projects)

---

## 📊 Metrics to Track

**Before Each Optimization:**
- Query count (django-debug-toolbar)
- Execution time (pytest-benchmark)
- Memory usage (memory_profiler)

**After Each Optimization:**
- Compare metrics
- Document improvement %
- Identify bottlenecks

---

## 🔄 Next Steps

1. **Implement bulk_create helper** ✅
2. **Refactor _copy_klasifikasi()** ← START HERE
3. **Refactor _copy_subklasifikasi()**
4. **Refactor _copy_pekerjaan()**
5. **Run performance benchmarks**
6. **Document results**

---

**Last Updated:** 2025-11-06
**Version:** 1.0
**Status:** Phase 1 Starting
