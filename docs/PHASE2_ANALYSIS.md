# PHASE 2: ARCHITECTURE REFACTORING - ANALYSIS
**Date:** 2025-11-02
**Status:** Planning
**Goal:** Clean code architecture while maintaining Phase 1 performance gains

---

## 🎯 PHASE 2 OBJECTIVES

**Primary Goals:**
1. Reduce code complexity and improve maintainability
2. Extract business logic from views to services
3. Implement clean architecture patterns
4. Improve testability and separation of concerns
5. **Maintain all Phase 1 performance improvements**

**Target Metrics:**
- View complexity: -70% (reduce from 400+ lines to ~100 lines)
- Code duplication: -90%
- Test coverage: 40% → 85%
- Testability: Improve by enabling unit testing of business logic

---

## 📊 CURRENT ARCHITECTURE ANALYSIS

### Current Layer Structure
```
┌─────────────────────────────────────────┐
│           DJANGO VIEWS LAYER            │
│  (preview.py: 550 lines)                │
│  (admin_portal.py: 391 lines)           │
│                                         │
│  ❌ Business logic mixed with UI logic  │
│  ❌ Hard to test                        │
│  ❌ High complexity (cyclomatic: 15+)   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           DJANGO ORM (Models)           │
│  ✅ Clean models with proper indexes    │
│  ✅ Good field definitions              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         PostgreSQL DATABASE              │
│  ✅ Well-indexed (Phase 1)               │
│  ✅ Good schema design                   │
└─────────────────────────────────────────┘
```

### Target Architecture (After Phase 2)
```
┌─────────────────────────────────────────┐
│           DJANGO VIEWS LAYER            │
│  (~100-150 lines per view)              │
│  ✅ Only request/response handling       │
│  ✅ Thin controllers                     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           SERVICE LAYER (NEW)           │
│  - PreviewImportService                 │
│  - AdminPortalService                   │
│  - ImportWriterService                  │
│  ✅ Business logic isolated              │
│  ✅ Easily unit testable                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        REPOSITORY LAYER (NEW)           │
│  - AHSPRepository                       │
│  - ItemRepository                       │
│  ✅ Data access abstraction              │
│  ✅ Query optimization centralized       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           DJANGO ORM (Models)           │
│  ✅ Clean models with proper indexes    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         PostgreSQL DATABASE              │
│  ✅ Well-indexed (Phase 1)               │
└─────────────────────────────────────────┘
```

---

## 🔍 CODE ANALYSIS - CRITICAL ISSUES

### Issue #1: God Function in preview.py (550 lines)
**Location:** `referensi/views/preview.py:preview_import()` (lines 233-495)

**Responsibilities (Too Many!):**
1. File upload handling
2. Excel parsing
3. Session management (pickle files)
4. Form validation
5. Pagination logic
6. AJAX response handling
7. Error handling
8. Data transformation
9. Database commits

**Cyclomatic Complexity:** ~25 (should be <10)

**Refactoring Strategy:**
```python
# Extract to PreviewImportService
class PreviewImportService:
    def __init__(self):
        self.session_manager = ImportSessionManager()
        self.parser = AHSPParser()

    def handle_file_upload(self, file, user) -> ParseResult:
        """Parse Excel and validate"""

    def build_job_page(self, parse_result, page, data=None) -> PageData:
        """Build job formset with pagination"""

    def build_detail_page(self, parse_result, page, data=None) -> PageData:
        """Build detail formset with pagination"""

    def apply_job_updates(self, parse_result, cleaned_data) -> None:
        """Apply changes to jobs"""

    def apply_detail_updates(self, parse_result, cleaned_data) -> None:
        """Apply changes to details"""

    def commit_import(self, parse_result, user) -> ImportSummary:
        """Write to database"""
```

**Expected Result:**
- `preview.py` view: 550 lines → ~150 lines (73% reduction)
- Business logic testable without Django request/response
- Clear separation of concerns

---

### Issue #2: God Function in admin_portal.py (391 lines)
**Location:** `referensi/views/admin_portal.py:admin_portal()` (lines 41-391)

**Responsibilities (Too Many!):**
1. Filter building (jobs + items)
2. Queryset construction with select_related/only
3. Pagination
4. Anomaly detection
5. Dropdown data loading
6. Tab switching logic
7. Form handling
8. Error handling

**Cyclomatic Complexity:** ~18 (should be <10)

**Refactoring Strategy:**
```python
# Extract to AdminPortalService
class AdminPortalService:
    def __init__(self):
        self.repo = AHSPRepository()

    def build_jobs_queryset(self, filters: dict) -> QuerySet:
        """Build optimized jobs queryset"""
        qs = self.repo.get_all_jobs()
        return self._apply_job_filters(qs, filters)

    def build_items_queryset(self, filters: dict) -> QuerySet:
        """Build optimized items queryset"""
        qs = self.repo.get_all_items()
        return self._apply_item_filters(qs, filters)

    def detect_anomalies(self, items_qs: QuerySet) -> dict:
        """Detect missing codes, negative coefficients, etc."""

    def get_filter_choices(self) -> dict:
        """Get dropdown choices for filters"""
```

**Expected Result:**
- `admin_portal.py` view: 391 lines → ~100 lines (74% reduction)
- Anomaly detection logic testable in isolation
- Filter logic reusable in API endpoints

---

### Issue #3: Code Duplication - Category Normalization
**Locations:**
1. `referensi/services/import_utils.py:canonicalize_kategori()` (lines 12-28)
2. `referensi/management/commands/normalize_referensi.py` (lines 27-30)

**Current Duplication:**
```python
# import_utils.py
def canonicalize_kategori(raw: str) -> str:
    canonical_map = {
        "u": "Upah",
        "upah": "Upah",
        "pekerja": "Upah",
        # ... 15 more mappings
    }
    return canonical_map.get(raw.strip().lower(), raw.strip())

# normalize_referensi.py (DUPLICATE!)
CATEGORY_MAPPING = {
    "u": "Upah",
    "upah": "Upah",
    # ... similar mappings
}
```

**Refactoring Strategy:**
```python
# Create referensi/services/normalizers.py
class KategoriNormalizer:
    """Single source of truth for kategori normalization"""

    CANONICAL_MAP = {
        "u": "Upah",
        "upah": "Upah",
        "pekerja": "Upah",
        "b": "Bahan",
        "bahan": "Bahan",
        "material": "Bahan",
        "a": "Alat",
        "alat": "Alat",
        "equipment": "Alat",
    }

    @classmethod
    def normalize(cls, raw: str) -> str:
        if not raw:
            return ""
        return cls.CANONICAL_MAP.get(raw.strip().lower(), raw.strip())

# Update all usages
from referensi.services.normalizers import KategoriNormalizer

# In import_utils.py
def canonicalize_kategori(raw: str) -> str:
    return KategoriNormalizer.normalize(raw)

# In normalize_referensi.py
normalized = KategoriNormalizer.normalize(value)
```

**Expected Result:**
- 1 source of truth for normalization
- Easy to add new mappings
- 90% code duplication eliminated

---

### Issue #4: No Form Validation
**Location:** `referensi/forms/preview.py`

**Current State:**
```python
class PreviewJobForm(forms.Form):
    job_index = forms.IntegerField(widget=forms.HiddenInput())
    sumber = forms.CharField(max_length=100, required=True)
    kode_ahsp = forms.CharField(max_length=50, required=True)
    # ... no clean methods, no validation!
```

**Problems:**
- No length validation
- No format validation
- No cross-field validation
- Can save invalid data

**Refactoring Strategy:**
```python
class PreviewJobForm(forms.Form):
    job_index = forms.IntegerField(widget=forms.HiddenInput())
    sumber = forms.CharField(max_length=100, required=True)
    kode_ahsp = forms.CharField(max_length=50, required=True)
    nama_ahsp = forms.CharField(max_length=500, required=True)
    klasifikasi = forms.CharField(max_length=100, required=False)
    sub_klasifikasi = forms.CharField(max_length=100, required=False)
    satuan = forms.CharField(max_length=50, required=False)

    def clean_kode_ahsp(self):
        """Validate kode AHSP format and length"""
        kode = self.cleaned_data.get('kode_ahsp', '')
        if not kode:
            raise ValidationError("Kode AHSP tidak boleh kosong")
        if len(kode) > 50:
            raise ValidationError("Kode AHSP maksimal 50 karakter")
        # Remove leading/trailing whitespace
        return kode.strip()

    def clean_nama_ahsp(self):
        """Validate nama AHSP"""
        nama = self.cleaned_data.get('nama_ahsp', '')
        if not nama:
            raise ValidationError("Nama AHSP tidak boleh kosong")
        if len(nama) > 500:
            raise ValidationError("Nama AHSP maksimal 500 karakter")
        return nama.strip()

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        # If klasifikasi specified, sub_klasifikasi should also be specified
        klasifikasi = cleaned_data.get('klasifikasi')
        sub_klasifikasi = cleaned_data.get('sub_klasifikasi')

        if klasifikasi and not sub_klasifikasi:
            # This is a warning, not error
            pass

        return cleaned_data

class PreviewDetailForm(forms.Form):
    job_index = forms.IntegerField(widget=forms.HiddenInput())
    detail_index = forms.IntegerField(widget=forms.HiddenInput())
    kategori = forms.CharField(max_length=50, required=True)
    kode_item = forms.CharField(max_length=50, required=False)
    uraian_item = forms.CharField(max_length=500, required=True)
    satuan_item = forms.CharField(max_length=50, required=True)
    koefisien = forms.DecimalField(max_digits=20, decimal_places=6, required=True)

    def clean_kategori(self):
        """Validate and normalize kategori"""
        from referensi.services.normalizers import KategoriNormalizer

        kategori = self.cleaned_data.get('kategori', '')
        if not kategori:
            raise ValidationError("Kategori tidak boleh kosong")

        # Normalize
        normalized = KategoriNormalizer.normalize(kategori)

        # Validate against allowed values
        allowed = ["Upah", "Bahan", "Alat"]
        if normalized not in allowed:
            raise ValidationError(
                f"Kategori harus salah satu dari: {', '.join(allowed)}"
            )

        return normalized

    def clean_koefisien(self):
        """Validate koefisien is non-negative"""
        koef = self.cleaned_data.get('koefisien')
        if koef is None:
            raise ValidationError("Koefisien tidak boleh kosong")
        if koef < 0:
            raise ValidationError("Koefisien tidak boleh negatif")
        return koef

    def clean_uraian_item(self):
        """Validate uraian"""
        uraian = self.cleaned_data.get('uraian_item', '')
        if not uraian:
            raise ValidationError("Uraian item tidak boleh kosong")
        if len(uraian) > 500:
            raise ValidationError("Uraian item maksimal 500 karakter")
        return uraian.strip()
```

**Expected Result:**
- Better data quality
- Better user experience (clear error messages)
- Prevent invalid data from entering database
- Automatic category normalization

---

### Issue #5: Session Management with Pickle
**Location:** `referensi/views/preview.py`

**Current Approach:**
```python
def _store_pending_import(session, parse_result: ParseResult, uploaded_name: str) -> str:
    token = secrets.token_urlsafe(16)
    fd, tmp_path = tempfile.mkstemp(prefix="ahsp_preview_", suffix=".pkl")
    try:
        with os.fdopen(fd, "wb") as handle:
            pickle.dump(parse_result, handle, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        os.remove(tmp_path)
        raise

    session[PENDING_IMPORT_SESSION_KEY] = {
        "parse_path": tmp_path,
        "uploaded_name": uploaded_name,
        "token": token,
    }
    session.modified = True
    return token
```

**Problems:**
1. ❌ Pickle files in temp directory - no automatic cleanup
2. ❌ No TTL - old files accumulate
3. ❌ Concurrent requests could conflict
4. ❌ Hard to debug/trace
5. ❌ Security risk (pickle deserialization)

**Refactoring Strategy (Phase 3 - Redis):**
```python
# For now in Phase 2, we'll keep pickle but improve cleanup
# In Phase 3, we'll migrate to Redis/Memcached

# Phase 2 improvement:
class ImportSessionManager:
    """Manages import session data with better cleanup"""

    CLEANUP_AGE_HOURS = 2

    def store(self, session, parse_result: ParseResult, uploaded_name: str) -> str:
        """Store parse result with automatic cleanup of old files"""
        # Cleanup old files first
        self._cleanup_old_files()

        token = secrets.token_urlsafe(16)
        fd, tmp_path = tempfile.mkstemp(prefix="ahsp_preview_", suffix=".pkl")
        try:
            with os.fdopen(fd, "wb") as handle:
                pickle.dump(parse_result, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            os.remove(tmp_path)
            raise

        session[PENDING_IMPORT_SESSION_KEY] = {
            "parse_path": tmp_path,
            "uploaded_name": uploaded_name,
            "token": token,
            "created_at": timezone.now().isoformat(),
        }
        session.modified = True
        return token

    def retrieve(self, session) -> tuple[ParseResult, str, str]:
        """Retrieve parse result from session"""
        data = session.get(PENDING_IMPORT_SESSION_KEY)
        if not data:
            raise FileNotFoundError("No pending import")

        # Check age
        created_at = data.get("created_at")
        if created_at:
            created_dt = timezone.datetime.fromisoformat(created_at)
            age_hours = (timezone.now() - created_dt).total_seconds() / 3600
            if age_hours > self.CLEANUP_AGE_HOURS:
                self.cleanup(session)
                raise FileNotFoundError("Import session expired")

        parse_path = data.get("parse_path")
        if not parse_path or not os.path.exists(parse_path):
            raise FileNotFoundError("Parse file not found")

        with open(parse_path, "rb") as handle:
            parse_result = pickle.load(handle)

        uploaded_name = data.get("uploaded_name", "")
        token = data.get("token", "")
        return parse_result, uploaded_name, token

    def cleanup(self, session) -> None:
        """Cleanup session and temp file"""
        data = session.pop(PENDING_IMPORT_SESSION_KEY, None)
        if data:
            path = data.get("parse_path")
            if path and os.path.exists(path):
                os.remove(path)
        session.modified = True

    def _cleanup_old_files(self):
        """Remove old pickle files from temp directory"""
        import tempfile
        import time

        temp_dir = tempfile.gettempdir()
        cutoff_time = time.time() - (self.CLEANUP_AGE_HOURS * 3600)

        for filename in os.listdir(temp_dir):
            if filename.startswith("ahsp_preview_") and filename.endswith(".pkl"):
                filepath = os.path.join(temp_dir, filename)
                try:
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                except (OSError, FileNotFoundError):
                    pass
```

**Expected Result:**
- Automatic cleanup of old files
- Session expiration (2 hours)
- Better error messages
- Preparation for Phase 3 Redis migration

---

## 📋 PHASE 2 ROADMAP

### Week 4, Day 1-3: Extract Service Classes (12-16 hours)

**Day 1 Tasks (4-5 hours):**
1. Create `referensi/services/preview_service.py`
   - Extract pagination logic (_build_job_page, _build_detail_page)
   - Extract session management (ImportSessionManager class)
   - Extract formset building logic
2. Update `referensi/views/preview.py` to use service
3. Test preview functionality thoroughly

**Day 2 Tasks (4-5 hours):**
1. Create `referensi/services/admin_service.py`
   - Extract filter building logic
   - Extract queryset construction
   - Extract anomaly detection
2. Update `referensi/views/admin_portal.py` to use service
3. Test admin portal functionality

**Day 3 Tasks (4-6 hours):**
1. Refactor `referensi/services/import_writer.py` into class-based service
2. Add proper error handling and logging
3. Create unit tests for services
4. Integration testing

**Expected Files Created:**
- `referensi/services/preview_service.py` (NEW)
- `referensi/services/admin_service.py` (NEW)
- `referensi/services/session_manager.py` (NEW)
- `referensi/tests/services/test_preview_service.py` (NEW)
- `referensi/tests/services/test_admin_service.py` (NEW)

**Expected Files Modified:**
- `referensi/views/preview.py` (550→150 lines, -73%)
- `referensi/views/admin_portal.py` (391→100 lines, -74%)
- `referensi/services/import_writer.py` (refactor to class)

---

### Week 4, Day 4-5: Repository Pattern (6-8 hours)

**Day 4 Tasks (3-4 hours):**
1. Create `referensi/repositories/__init__.py`
2. Create `referensi/repositories/ahsp_repository.py`
   - `get_all_jobs()` - with select_related/only optimization
   - `filter_by_source()`, `filter_by_classification()`
   - `search()` - optimized search
   - `get_with_category_counts()` - for statistics
3. Create `referensi/repositories/item_repository.py`
   - `get_all_items()` - with select_related/only
   - `filter_by_category()`, `filter_by_ahsp()`
   - `get_anomalies()` - missing codes, negative coef
4. **IMPORTANT:** Maintain all Phase 1 optimizations (indexes, select_related, only)

**Day 5 Tasks (3-4 hours):**
1. Update services to use repositories
2. Remove direct ORM queries from services
3. Create unit tests for repositories
4. Verify performance not degraded (use Debug Toolbar)

**Expected Files Created:**
- `referensi/repositories/__init__.py` (NEW)
- `referensi/repositories/ahsp_repository.py` (NEW)
- `referensi/repositories/item_repository.py` (NEW)
- `referensi/tests/repositories/test_ahsp_repository.py` (NEW)
- `referensi/tests/repositories/test_item_repository.py` (NEW)

**Expected Files Modified:**
- `referensi/services/admin_service.py` (use repositories)
- `referensi/services/preview_service.py` (use repositories)

---

### Week 5, Day 1-2: Remove Code Duplication (3-4 hours)

**Tasks:**
1. Create `referensi/services/normalizers.py`
   - `KategoriNormalizer` class
   - Single source of truth for category mappings
2. Update `referensi/services/import_utils.py`
   - Use `KategoriNormalizer.normalize()`
3. Update `referensi/management/commands/normalize_referensi.py`
   - Remove duplicate mapping
   - Use `KategoriNormalizer.normalize()`
4. Update forms to use normalizer
5. Create tests

**Expected Files Created:**
- `referensi/services/normalizers.py` (NEW)
- `referensi/tests/test_normalizers.py` (NEW)

**Expected Files Modified:**
- `referensi/services/import_utils.py`
- `referensi/management/commands/normalize_referensi.py`
- `referensi/forms/preview.py` (use in clean methods)

---

### Week 5, Day 3: Add Form Validators (3-4 hours)

**Tasks:**
1. Add validation to `PreviewJobForm`
   - `clean_kode_ahsp()` - length, format
   - `clean_nama_ahsp()` - length
   - `clean()` - cross-field validation
2. Add validation to `PreviewDetailForm`
   - `clean_kategori()` - normalize and validate
   - `clean_koefisien()` - non-negative
   - `clean_uraian_item()` - length
   - `clean()` - cross-field validation
3. Add comprehensive error messages
4. Create form validation tests

**Expected Files Modified:**
- `referensi/forms/preview.py` (add clean methods)

**Expected Files Created:**
- `referensi/tests/forms/test_preview_forms.py` (NEW)

---

### Week 5, Day 4-5: Testing & Documentation (6-8 hours)

**Tasks:**
1. Write unit tests for all new services
2. Write integration tests for refactored views
3. Update docstrings (Google style)
4. Create architecture diagram
5. Create Phase 2 summary document
6. Run full test suite
7. Verify all Phase 1 performance maintained

**Expected Files Created:**
- `docs/PHASE2_ARCHITECTURE_DIAGRAM.md` (NEW)
- `docs/PHASE2_COMPLETE_SUMMARY.md` (NEW)
- Multiple test files

---

## ✅ SUCCESS CRITERIA

### Code Quality
- ✅ View complexity reduced 70% (400+ lines → ~100 lines)
- ✅ Cyclomatic complexity <10 for all functions
- ✅ Code duplication <5%
- ✅ All business logic in services (testable)

### Testing
- ✅ Test coverage: 40% → 85%
- ✅ Unit tests for all services
- ✅ Unit tests for all repositories
- ✅ Form validation tests
- ✅ Integration tests pass

### Performance
- ✅ **All Phase 1 improvements maintained**
- ✅ No performance regression
- ✅ Query count same or better
- ✅ Page load time same or better

### Architecture
- ✅ Clear separation of concerns
- ✅ Service layer implemented
- ✅ Repository layer implemented
- ✅ Validators implemented
- ✅ Single source of truth for normalization

---

## ⚠️ RISKS & MITIGATIONS

### Risk 1: Performance Regression
**Mitigation:**
- Use Django Debug Toolbar throughout
- Run performance tests before/after
- Keep Phase 1 optimizations in repositories
- Never add extra database queries

### Risk 2: Breaking Changes
**Mitigation:**
- Comprehensive testing at each step
- Keep old code until new code verified
- Use feature flags if needed
- Incremental refactoring

### Risk 3: Test Coverage Too Low
**Mitigation:**
- Write tests DURING refactoring (not after)
- Aim for 85% coverage minimum
- Test edge cases and error paths
- Use coverage.py to measure

---

## 📊 PROGRESS TRACKING

| Task | Duration | Status | Notes |
|------|----------|--------|-------|
| Analysis | 1h | ✅ DONE | This document |
| Day 1: Preview Service | 4-5h | ⏳ Next | Extract from preview.py |
| Day 2: Admin Service | 4-5h | Pending | Extract from admin_portal.py |
| Day 3: Service Tests | 4-6h | Pending | Unit + integration tests |
| Day 4: Repositories | 3-4h | Pending | AHSP + Item repos |
| Day 5: Repository Tests | 3-4h | Pending | Verify performance |
| Day 6-7: Duplication | 3-4h | Pending | Normalizers |
| Day 8: Validators | 3-4h | Pending | Form validation |
| Day 9-10: Testing | 6-8h | Pending | Full test suite |

**Total Estimated:** 30-40 hours (4-5 days full-time)

---

**Analysis Completed By:** Claude + User
**Date:** 2025-11-02
**Next Action:** Start Week 4, Day 1 - Create PreviewImportService

---

**End of Phase 2 Analysis**
