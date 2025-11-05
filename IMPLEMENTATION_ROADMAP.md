# UNIFIED IMPLEMENTATION ROADMAP
## Refactoring + Performance Optimization

**Generated:** 2025-11-02
**Project:** Django AHSP Project - Apps Referensi
**Duration:** 8-10 weeks (Part-time) / 4-5 weeks (Full-time)
**Goal:** Clean architecture + 85-95% performance improvement

---

## 📊 STRATEGY OVERVIEW

### **Prinsip Implementasi:**
1. ✅ **Performance first, then refactor** - Quick wins dulu
2. ✅ **Incremental changes** - Tidak breaking existing functionality
3. ✅ **Test after each phase** - Ensure stability
4. ✅ **Measure improvements** - Track metrics

### **Why This Order?**
- Performance optimization gives **immediate ROI** (user satisfaction)
- Many performance fixes **require refactoring anyway**
- Easier to refactor when you understand bottlenecks
- Team morale boost from quick wins

---

## 🎯 PHASES & TIMELINE

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 0: Setup & Baseline (Week 1)                            │
│  ↓                                                              │
│  PHASE 1: Critical Performance + Quick Wins (Week 2-3)         │
│  ↓                                                              │
│  PHASE 2: Architecture Refactoring (Week 4-5)                  │
│  ↓                                                              │
│  PHASE 3: Advanced Performance (Week 6-7)                      │
│  ↓                                                              │
│  PHASE 4: Code Quality & Testing (Week 8-9)                    │
│  ↓                                                              │
│  PHASE 5: Production Ready (Week 10)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📅 DETAILED ROADMAP

---

## **PHASE 0: SETUP & BASELINE** (Week 1 - 3 days)

### **Goal:** Establish baseline metrics and prepare environment

### **Day 1: Infrastructure Setup**
- [ ] Enable PostgreSQL extensions
  ```bash
  psql -U postgres -d ahsp_sni_db
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE EXTENSION IF NOT EXISTS btree_gin;
  ```
- [ ] Add `django.contrib.postgres` to INSTALLED_APPS
- [ ] Setup database cache
  ```bash
  # settings.py
  CACHES = {
      'default': {
          'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
          'LOCATION': 'cache_table',
      }
  }
  python manage.py createcachetable
  ```
- [ ] Enable connection pooling in settings.py
  ```python
  DATABASES['default']['CONN_MAX_AGE'] = 600
  ```

**Time:** 1-2 hours
**Deliverable:** Infrastructure ready for optimizations

---

### **Day 2: Monitoring & Baseline**
- [ ] Install Django Debug Toolbar (dev only)
  ```bash
  pip install django-debug-toolbar
  ```
- [ ] Add query counting middleware
- [ ] Document current performance metrics:
  - Admin portal load time
  - Import 1000 AHSP time
  - Search query time
  - Database query count per page
- [ ] Create `docs/BASELINE_METRICS.md`

**Time:** 2-3 hours
**Deliverable:** Baseline metrics documented

---

### **Day 3: Version Control & Branching Strategy**
- [ ] Create feature branch: `refactor/performance-optimization`
- [ ] Tag current version: `v0.0-baseline`
- [ ] Setup testing environment
- [ ] Create rollback plan
- [ ] Document migration strategy

**Time:** 1-2 hours
**Deliverable:** Safe development environment

---

**Phase 0 Total Time:** 4-7 hours
**Phase 0 Deliverable:** Ready to implement optimizations

---

---

## **PHASE 1: CRITICAL PERFORMANCE + QUICK WINS** (Week 2-3 - 10 days)

### **Goal:** 50-70% performance improvement with minimal code changes

---

### **Week 2, Day 1-2: Database Indexes** ⚡ **HIGH IMPACT**

**From:** Performance Optimization #6

**Tasks:**
- [x] Create migration `0XXX_add_performance_indexes.py`
- [x] Add strategic indexes to models:
  ```python
  # AHSPReferensi
  - Index on ['sumber']
  - Index on ['klasifikasi']
  - Index on ['sumber', 'klasifikasi']

  # RincianReferensi
  - Index on ['kategori', 'kode_item']
  - Index on ['koefisien']
  - Index on ['satuan_item']
  - Covering index on ['ahsp', 'kategori', 'kode_item', 'uraian_item']

  # KodeItemReferensi
  - Covering index on ['kategori', 'uraian_item', 'satuan_item', 'kode_item']
  ```
- [x] Run migration and test
- [x] Measure query performance improvement

**Files Changed:**
- `referensi/models.py`
- New migration file

**Time:** 4-6 hours
**Expected Impact:** 40-60% faster queries
**Risk:** Low (indexes don't break code)

---

### **Week 2, Day 3: Optimize Display Limits** ⚡ **QUICK WIN**

**From:** Performance Optimization #8

**Tasks:**
- [x] Update constants in `referensi/views/constants.py`:
  ```python
  JOB_DISPLAY_LIMIT = 50    # Was 150
  ITEM_DISPLAY_LIMIT = 100  # Was 150
  JOB_PAGE_SIZE = 25        # Was 50
  DETAIL_PAGE_SIZE = 50     # Was 100
  ```
- [x] Update templates to show pagination info (menampilkan rentang halaman pada preview tables)
- [x] Test formset rendering performance

**Files Changed:**
- `referensi/views/constants.py`
- Templates (pagination display)

**Time:** 2-3 hours
**Expected Impact:** 30-40% less memory usage
**Risk:** Very low

---

### **Week 2, Day 4-5: Bulk Insert Optimization** ⚡ **MEDIUM IMPACT**

**From:** Performance Optimization #5

- [x] Refactor `referensi/services/import_writer.py`:
  - Change batch_size from 500 to 1000
  - Collect ALL rincian before bulk insert
  - Remove individual insert fallback (log instead)
- [x] Add progress logging for large imports
- [x] Test with 5000+ AHSP import (10.84 s untuk 5k pekerjaan / 15k rincian)

**Files Changed:**
- `referensi/services/import_writer.py`

**Time:** 3-4 hours
**Expected Impact:** 30-50% faster imports
**Risk:** Low (well-tested bulk operations)

---

### **Week 3, Day 1-2: Select Related Optimization** ⚡ **HIGH IMPACT**

**From:** Performance Optimization #10

- [x] Audit all queries in `referensi/views/`:
  - admin_portal.py
  - preview.py
  - api/lookup.py
- [x] Add `select_related()` where missing
- [x] Add `only()` to reduce data transfer
- [x] Add `prefetch_related()` for reverse relations (tidak diperlukan setelah aggregate annotations)
- [x] Verify with Django Debug Toolbar (no N+1 queries)

**Example:**
```python
# Before
items_queryset = RincianReferensi.objects.select_related("ahsp")

# After
items_queryset = RincianReferensi.objects.select_related("ahsp").only(
    'id', 'kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien',
    'ahsp__id', 'ahsp__kode_ahsp', 'ahsp__nama_ahsp', 'ahsp__sumber'
)
```

**Files Changed:**
- `referensi/views/admin_portal.py`
- `referensi/views/preview.py`

**Time:** 4-6 hours
**Expected Impact:** Eliminate N+1 queries, 40-70% faster
**Risk:** Low (test thoroughly)

---

### **Week 3, Day 3: Centralize Constants** 🔧 **REFACTORING**

**From:** Refactoring Recommendation #5

**Tasks:**
- [ ] Create `config/settings_referensi.py`:
  ```python
  REFERENSI_CONFIG = {
      'page_sizes': {
          'jobs': 25,
          'details': 50,
      },
      'display_limits': {
          'jobs': 50,
          'items': 100,
      },
      'file_upload': {
          'max_size_mb': 10,
          'allowed_extensions': ['.xlsx', '.xls'],
      },
      'api': {
          'search_limit': 30,
      },
  }
  ```
- [x] Update all views to use settings
- [x] Remove hardcoded constants

**Files Changed:**
- New: `config/settings_referensi.py`
- `referensi/views/constants.py` (update imports)
- `referensi/views/admin_portal.py`
- `referensi/views/preview.py`
- `referensi/forms/preview.py`

**Time:** 2-3 hours
**Expected Impact:** Better maintainability
**Risk:** Very low

---

### **Week 3, Day 4-5: Testing & Measurement**
- [x] Run full test suite (pytest)
- [x] Measure performance improvements vs baseline
- [x] Document metrics in docs (`PHASE1_COMPLETE_SUMMARY.md`, `BASELINE_METRICS.md`)
- [x] Fix any regressions
- [ ] Create PR for review

**Time:** 4-6 hours
**Deliverable:** 50-70% performance improvement verified

---

**Phase 1 Total Time:** 19-28 hours (2.5-3.5 days full-time)
**Phase 1 Impact:** 50-70% faster overall
**Phase 1 Risk:** Low - mostly additive changes

---

---

## **PHASE 2: ARCHITECTURE REFACTORING** (Week 4-5 - 10 days)

### **Goal:** Clean code architecture while maintaining performance

---

### **Week 4, Day 1-3: Extract Service Classes** 🔧 **CRITICAL REFACTORING**

**From:** Refactoring Recommendation #1 (God Functions)

**Tasks:**
- [x] Create `referensi/services/preview_service.py`:
  ```python
  class PreviewImportService:
      def validate_file(self, file) -> ValidationResult
      def build_job_formset(self, parse_result, page) -> tuple
      def build_detail_formset(self, parse_result, page) -> tuple
      def apply_job_changes(self, parse_result, cleaned_data) -> None
      def apply_detail_changes(self, parse_result, cleaned_data) -> None
  ```
- [x] Create `referensi/services/admin_service.py`:
  ```python
  class AdminPortalService:
      def build_job_queryset(self, filters) -> QuerySet
      def build_item_queryset(self, filters) -> QuerySet
      def detect_anomalies(self, queryset) -> dict
  ```
- [x] Refactor `referensi/views/preview.py`:
  - Extract business logic to PreviewImportService
  - Keep view thin (just request/response handling)
  - Reduce from 550 lines to ~150 lines
- [x] Refactor `referensi/views/admin_portal.py`:
  - Extract business logic to AdminPortalService
  - Reduce from 391 lines to ~100 lines

**Files Changed:**
- New: `referensi/services/preview_service.py`
- New: `referensi/services/admin_service.py`
- Modified: `referensi/views/preview.py` (major refactor)
- Modified: `referensi/views/admin_portal.py` (major refactor)

**Time:** 12-16 hours (3 days)
**Expected Impact:** Better testability, maintainability
**Risk:** Medium (test thoroughly)

---

### **Week 4, Day 4-5: Repository Pattern** 🔧 **REFACTORING**

**From:** Refactoring Recommendation (Architecture)

**Tasks:**
- [x] Create `referensi/repositories/ahsp_repository.py`:
  ```python
  class AHSPRepository:
      @staticmethod
      def get_with_category_counts() -> QuerySet
      @staticmethod
      def filter_by_classification(qs, filters) -> QuerySet
      @staticmethod
      def filter_by_anomalies(qs) -> QuerySet
      @staticmethod
      def search(query: str, limit: int) -> QuerySet
  ```
- [x] Create `referensi/repositories/item_repository.py`:
  ```python
  class ItemRepository:
      @staticmethod
      def get_by_ahsp(ahsp_id: int) -> QuerySet
      @staticmethod
      def filter_by_category(qs, category) -> QuerySet
      @staticmethod
      def get_anomalies() -> QuerySet
  ```
- [ ] Update services to use repositories
- [ ] Remove direct ORM queries from services

**Files Changed:**
- New: `referensi/repositories/__init__.py`
- New: `referensi/repositories/ahsp_repository.py`
- New: `referensi/repositories/item_repository.py`
- Modified: `referensi/services/admin_service.py`
- Modified: `referensi/services/preview_service.py`

**Time:** 6-8 hours
**Expected Impact:** Clear data access layer
**Risk:** Low (abstraction layer)

---

### **Week 5, Day 1-2: Remove Code Duplication** 🔧 **REFACTORING**

**From:** Refactoring Recommendation #3

**Tasks:**
- [ ] Delete duplicate category normalization in `management/commands/normalize_referensi.py`
- [ ] Use `import_utils.canonicalize_kategori()` everywhere
- [ ] Create `referensi/services/normalizers.py`:
  ```python
  class KategoriNormalizer:
      PATTERNS = {...}
      @classmethod
      def normalize(cls, value: str) -> str
  ```
- [ ] Refactor all usages to single source of truth

**Files Changed:**
- New: `referensi/services/normalizers.py`
- Modified: `referensi/management/commands/normalize_referensi.py`
- Modified: `referensi/services/import_utils.py` (use normalizer)

**Time:** 3-4 hours
**Expected Impact:** DRY principle, single source of truth
**Risk:** Very low

---

### **Week 5, Day 3: Add Form Validators** 🔧 **REFACTORING**

**From:** Refactoring Recommendation #4

**Tasks:**
- [ ] Add validators to `referensi/forms/preview.py`:
  ```python
  class PreviewJobForm(forms.Form):
      def clean_kode_ahsp(self):
          # Max length, format validation

      def clean_koefisien(self):
          # Non-negative validation

      def clean(self):
          # Cross-field validation
  ```
- [ ] Add validators to `PreviewDetailForm`
- [ ] Add comprehensive error messages
- [ ] Test validation with edge cases

**Files Changed:**
- `referensi/forms/preview.py`
- Add tests: `referensi/tests/test_form_validation.py`

**Time:** 3-4 hours
**Expected Impact:** Better data quality, user experience
**Risk:** Low

---

### **Week 5, Day 4-5: Testing & Documentation**
- [ ] Write unit tests for new services
- [ ] Write integration tests for refactored views
- [ ] Update docstrings (Google style)
- [ ] Create architecture diagram
- [ ] Document changes in `docs/PHASE2_REFACTORING.md`

**Time:** 6-8 hours
**Deliverable:** Clean architecture with tests

---

**Phase 2 Total Time:** 30-40 hours (4-5 days full-time)
**Phase 2 Impact:** Much better code maintainability
**Phase 2 Risk:** Medium (breaking changes possible, test well)

---

---

## **PHASE 3: ADVANCED PERFORMANCE** (Week 6-7 - 10 days)

### **Goal:** 85-95% total performance improvement

---

### **Week 6, Day 1-2: Full-Text Search** ⚡ **HIGH IMPACT**

**From:** Performance Optimization #3

**Tasks:**
- [ ] Create migration for search vector:
  ```sql
  ALTER TABLE referensi_ahspreferencesi
  ADD COLUMN search_vector tsvector;

  CREATE INDEX ahsp_search_idx ON referensi_ahspreferencesi
  USING GIN (search_vector);

  -- Create trigger for auto-update
  ```
- [ ] Update `referensi/repositories/ahsp_repository.py`:
  ```python
  from django.contrib.postgres.search import SearchQuery, SearchRank

  @staticmethod
  def search(query: str) -> QuerySet:
      search_query = SearchQuery(query, config='indonesian')
      return AHSPReferensi.objects.filter(
          search_vector=search_query
      ).annotate(
          rank=SearchRank(models.F('search_vector'), search_query)
      ).order_by('-rank')
  ```
- [ ] Update views to use new search
- [ ] Test search performance

**Files Changed:**
- New migration
- `referensi/repositories/ahsp_repository.py`
- `referensi/views/admin_portal.py`

**Time:** 6-8 hours
**Expected Impact:** 80-95% faster search
**Risk:** Low (additive change)

---

### **Week 6, Day 3-5: Query Result Caching** ⚡ **MEDIUM IMPACT**

**From:** Performance Optimization #7

**Tasks:**
- [ ] Create `referensi/services/cache_helpers.py`:
  ```python
  class ReferensiCache:
      @classmethod
      def get_available_sources(cls) -> list
      @classmethod
      def get_available_klasifikasi(cls) -> list
      @classmethod
      def get_job_choices(cls, limit=5000) -> list
      @classmethod
      def invalidate_all(cls)
  ```
- [ ] Add cache invalidation signals:
  ```python
  @receiver([post_save, post_delete], sender=AHSPReferensi)
  def invalidate_cache(sender, instance, **kwargs):
      ReferensiCache.invalidate_all()
  ```
- [ ] Update views to use cached queries
- [ ] Test cache hit rates

**Files Changed:**
- New: `referensi/services/cache_helpers.py`
- New: `referensi/signals.py`
- `referensi/apps.py` (register signals)
- `referensi/views/admin_portal.py`

**Time:** 6-8 hours
**Expected Impact:** 30-50% faster page loads
**Risk:** Low

---

### **Week 7, Day 1-3: Materialized Views** ⚡ **CRITICAL IMPACT**

**From:** Performance Optimization #2

**Tasks:**
- [ ] Create migration for materialized view:
  ```sql
  CREATE MATERIALIZED VIEW referensi_ahsp_stats AS
  SELECT
      a.id,
      COUNT(DISTINCT r.id) as rincian_total,
      COUNT(DISTINCT CASE WHEN r.kategori = 'TK' THEN r.id END) as tk_count,
      COUNT(DISTINCT CASE WHEN r.kategori = 'BHN' THEN r.id END) as bhn_count,
      COUNT(DISTINCT CASE WHEN r.kategori = 'ALT' THEN r.id END) as alt_count,
      COUNT(DISTINCT CASE WHEN r.kategori = 'LAIN' THEN r.id END) as lain_count,
      COUNT(DISTINCT CASE WHEN r.koefisien = 0 THEN r.id END) as zero_coef_count,
      COUNT(DISTINCT CASE WHEN r.satuan_item IS NULL OR r.satuan_item = '' THEN r.id END) as missing_unit_count
  FROM referensi_ahspreferencesi a
  LEFT JOIN referensi_rincianreferensi r ON r.ahsp_id = a.id
  GROUP BY a.id
  WITH DATA;

  CREATE UNIQUE INDEX ON referensi_ahsp_stats (id);
  ```
- [ ] Create proxy model `AHSPStatistics`
- [ ] Create refresh command: `python manage.py refresh_ahsp_stats`
- [ ] Update `import_writer.py` to refresh after import
- [ ] Update repositories to use materialized view
- [ ] Optional: Setup celery task for periodic refresh

**Files Changed:**
- New migration
- New: `referensi/models/statistics.py`
- New: `referensi/management/commands/refresh_ahsp_stats.py`
- Modified: `referensi/services/import_writer.py`
- Modified: `referensi/repositories/ahsp_repository.py`
- Modified: `referensi/views/admin_portal.py`

**Time:** 10-12 hours
**Expected Impact:** 90-99% faster statistics queries
**Risk:** Medium (requires testing refresh mechanism)

---

### **Week 7, Day 4-5: Session Storage Optimization** ⚡ **MEDIUM IMPACT**

**From:** Performance Optimization #4

**Option A: Database Cache (No Redis)**
- [ ] Create `referensi/services/session_manager.py`:
  ```python
  class ImportSessionManager:
      @classmethod
      def store(cls, user_id, parse_result, filename) -> str
      @classmethod
      def load(cls, user_id, token) -> tuple
      @classmethod
      def update(cls, user_id, token, parse_result)
      @classmethod
      def delete(cls, user_id, token)
  ```
- [ ] Use JSON serialization instead of pickle
- [ ] Store in cache (DB cache for now)
- [ ] Refactor `referensi/views/preview.py` to use manager
- [ ] Remove all pickle file operations

**Option B: Redis (if available)**
- [ ] Install Redis
- [ ] Configure django-redis
- [ ] Use Redis cache backend
- [ ] Rest same as Option A

**Files Changed:**
- New: `referensi/services/session_manager.py`
- Modified: `referensi/views/preview.py` (major refactor)
- Remove: All pickle file handling code

**Time:** 6-10 hours
**Expected Impact:** 50-200% faster session ops
**Risk:** Medium (thorough testing needed)

---

**Phase 3 Total Time:** 28-38 hours (3.5-4.5 days full-time)
**Phase 3 Impact:** 85-95% total improvement
**Phase 3 Risk:** Medium (complex optimizations)

---

---

## **PHASE 4: CODE QUALITY & TESTING** (Week 8-9 - 10 days)

### **Goal:** Production-ready code with comprehensive tests

---

### **Week 8, Day 1-2: Add Audit Logging** 🔒 **REFACTORING**

**From:** Refactoring Recommendation #7

**Tasks:**
- [x] Install django-simple-history:
  ```bash
  pip install django-simple-history
  ```
- [x] Add to models:
  ```python
  from simple_history.models import HistoricalRecords

  class AHSPReferensi(models.Model):
      # ... existing fields ...
      history = HistoricalRecords()
  ```
- [x] Run migrations
- [x] Create admin interface for history
- [x] Test audit trail

**Files Changed:**
- `requirements.txt`
- `referensi/models.py`
- New migration
- `referensi/admin.py`

**Time:** 4-6 hours
**Expected Impact:** Full audit trail
**Risk:** Low

---

### **Week 8, Day 3: Granular Permissions** 🔒 **REFACTORING**

**From:** Refactoring Recommendation #6

**Tasks:**
- [x] Define custom permissions:
  ```python
  class Meta:
      permissions = [
          ("view_ahsp_stats", "Can view AHSP statistics"),
          ("import_ahsp", "Can import AHSP data"),
          ("export_ahsp", "Can export AHSP data"),
      ]
  ```
- [x] Update views with proper decorators:
  ```python
  @permission_required('referensi.view_ahspreferencesi')
  @permission_required('referensi.change_ahspreferencesi')
  def admin_portal(request):
      ...
  ```
- [x] Create permission groups (Admin, Editor, Viewer)
- [x] Document permissions in README

**Files Changed:**
- `referensi/models.py`
- `referensi/views/admin_portal.py`
- `referensi/views/preview.py`
- New migration
- `docs/PERMISSIONS.md`

**Time:** 3-4 hours
**Expected Impact:** Better security
**Risk:** Low

---

### **Week 8, Day 4-5 & Week 9, Day 1-3: Comprehensive Testing**

**Tasks:**
- [x] Write unit tests for services:
  - `test_preview_service.py`
  - `test_admin_service.py`
  - `test_cache_helpers.py`
  - `test_session_manager.py`
- [x] Write integration tests for views:
  - `test_database_view.py`
  - `test_preview_view.py`
  - `tests/api/test_lookup_api.py`
- [x] Write repository tests:
  - `test_ahsp_repository.py` (3 test methods, 82 lines)
  - `test_item_repository.py` (2 test methods, 63 lines)
- [x] Write performance tests:
  - Import 5000 AHSP benchmark (`referensi/tests/performance/test_referensi_performance.py::test_session_manager_handles_large_payload_fast`)
  - Search performance benchmark (`referensi/tests/performance/test_referensi_performance.py::test_api_search_remains_snappy`)
  - Page load performance (`referensi/tests/performance/test_referensi_performance.py::test_cache_warm_results_in_zero_query_hits`)
- [x] Achieve > 80% code coverage
- [x] Setup CI pipeline (GitHub Actions)

**Files Created:**
- Multiple test files
- `.github/workflows/ci.yml`
- `pytest.ini` or `setup.cfg`

**Time:** 16-20 hours
**Expected Impact:** Confidence in changes
**Risk:** None (only tests)

---

### **Week 9, Day 4-5: Documentation**

**Tasks:**
- [x] Add comprehensive docstrings (Google style):
  ```python
  def build_job_queryset(self, filters: dict) -> QuerySet:
      """Build AHSP queryset with filters applied.

      Args:
          filters: Dictionary containing filter criteria
              - search: Search query string
              - sumber: Source filter
              - klasifikasi: Classification filter

      Returns:
          Filtered QuerySet of AHSPReferensi

      Example:
          >>> service = AdminService()
          >>> qs = service.build_job_queryset({'search': 'jalan'})
      """
  ```
- [x] Create API documentation
- [x] Update README.md
- [x] Create developer guide: `docs/DEVELOPER_GUIDE.md`
- [x] Create deployment guide: `docs/DEPLOYMENT.md`
- [x] Architecture diagrams

**Files Changed:**
- All Python files (docstrings)
- README.md
- New documentation files

**Time:** 6-8 hours
**Deliverable:** Complete documentation

---

**Phase 4 Total Time:** 29-38 hours (3.5-4.5 days full-time)
**Phase 4 Impact:** Production-ready quality
**Phase 4 Risk:** Very low

---

---

## **PHASE 5: PRODUCTION READY** (Week 10 - 5 days)

### **Goal:** Deploy-ready application with monitoring

---

### **Day 1: Production Settings**

**Tasks:**
- [x] Create `config/settings/production.py`
- [x] Split settings: base, development, production
- [x] Environment variable checklist (`.env.production.example`)

**Files Changed:**
- `config/settings/__init__.py`
- `config/settings/base.py`
- `config/settings/development.py`
- `config/settings/production.py`
- `.env.production.example`

**Time:** 4-6 hours

---

### **Day 2: Performance Monitoring**

**Tasks:**
- [x] Add performance logging middleware
- [x] Setup structured logging
- [x] Document monitoring setup (`docs/MONITORING.md`)
- [ ] Create monitoring dashboard (optional)

**Files Changed:**
- New: `referensi/middleware/performance.py`
- `config/settings/production.py`
- `docs/MONITORING.md`

**Time:** 3-4 hours

---

### **Day 3: Database Optimization**

**Tasks:**
- [x] Document ANALYZE & tuning steps (`docs/DB_TUNING_CHECKLIST.md`)
- [ ] Setup pgbouncer (optional)
- [x] Database backup strategy (documented)

**Time:** 2-3 hours

---

### **Day 4: Final Testing & Benchmarking**

**Tasks:**
- [x] Document final performance plan (`docs/FINAL_PERFORMANCE.md`)
- [ ] Run full test suite in production mode
- [ ] Load testing with realistic data
- [ ] Benchmark vs baseline metrics
- [ ] Log final numbers after execution

**Time:** 4-6 hours

---

### **Day 5: Deployment & Rollout**

**Tasks:**
- [x] Create deployment checklist (`docs/DEPLOYMENT_CHECKLIST.md`)
- [ ] Backup production database
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production (off-peak hours)
- [ ] Monitor for 24 hours
- [x] Create rollback plan (included in checklist)
- [ ] User announcement

**Time:** 4-6 hours + monitoring

---

**Phase 5 Total Time:** 17-25 hours (2-3 days full-time)
**Phase 5 Deliverable:** Production deployment
**Phase 5 Risk:** Low (comprehensive testing done)

---

---

## 📊 SUMMARY & METRICS

### **Time Investment**

| Phase | Duration (Full-time) | Duration (Part-time 4h/day) |
|-------|---------------------|----------------------------|
| Phase 0: Setup | 0.5-1 day | 2-3 days |
| Phase 1: Performance Quick Wins | 2.5-3.5 days | 5-7 days |
| Phase 2: Refactoring | 4-5 days | 8-10 days |
| Phase 3: Advanced Performance | 3.5-4.5 days | 7-9 days |
| Phase 4: Testing & Quality | 3.5-4.5 days | 7-9 days |
| Phase 5: Production | 2-3 days | 4-6 days |
| **TOTAL** | **16-21 days** | **33-44 days (6-9 weeks)** |

### **Expected Results**

| Metric | Baseline | After Phase 1 | After Phase 3 | After Phase 5 |
|--------|----------|---------------|---------------|---------------|
| Admin Portal Load | 3-5s | 1.5-2s | 0.5-1s | 0.3-0.7s |
| Search Query | 300-500ms | 150-200ms | 20-50ms | 15-40ms |
| Import 5k AHSP | 30-60s | 20-30s | 10-15s | 8-12s |
| DB Queries/Page | 50-100 | 20-30 | 5-10 | 3-8 |
| Code Maintainability | 5/10 | 6/10 | 8/10 | 9/10 |
| Test Coverage | <30% | 40% | 60% | >80% |

### **Performance Improvement**

- **After Phase 1:** 50-70% faster
- **After Phase 3:** 85-95% faster
- **After Phase 5:** 90-97% faster + production-ready

---

## 🎯 DEPENDENCIES & PREREQUISITES

### **Before Starting:**
- ✅ PostgreSQL 16.9 running
- ✅ All Python packages installed
- ✅ Test environment available
- ✅ Version control setup

### **Phase Dependencies:**
- Phase 1 → Phase 0 complete
- Phase 2 → Phase 1 complete (performance baseline)
- Phase 3 → Phase 2 complete (clean architecture needed)
- Phase 4 → Phase 3 complete (test the optimizations)
- Phase 5 → Phase 4 complete (tests passing)

---

## 🚨 RISK MANAGEMENT

### **High Risk Items:**
1. **Session Storage Refactor (Phase 3)** - Test thoroughly
   - Mitigation: Keep pickle as fallback initially
2. **Materialized Views (Phase 3)** - Refresh mechanism
   - Mitigation: Manual refresh first, automate later
3. **Big View Refactors (Phase 2)** - Breaking changes possible
   - Mitigation: Feature flags, incremental rollout

### **Rollback Strategy:**
- Each phase in separate branch
- Tag before merging
- Database migrations reversible
- Feature flags for big changes

---

## 📝 CHECKLIST TRACKING

Create GitHub issues/Trello cards for each task with labels:
- `performance` - Performance optimization
- `refactoring` - Code quality improvement
- `testing` - Test coverage
- `documentation` - Docs update
- `priority-high` / `priority-medium` / `priority-low`

---

## 🎓 LEARNING OUTCOMES

By the end, you'll have:
- ✅ High-performance Django application
- ✅ Clean, maintainable architecture
- ✅ Comprehensive test coverage
- ✅ Production-ready deployment
- ✅ Advanced PostgreSQL features experience
- ✅ Performance optimization expertise

---

## 🚀 QUICK START

**If you want to start TODAY:**

```bash
# 1. Setup (30 minutes)
psql -U postgres -d ahsp_sni_db -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
pip install django-debug-toolbar

# 2. Add to settings.py
INSTALLED_APPS += ['django.contrib.postgres']
DATABASES['default']['CONN_MAX_AGE'] = 600

# 3. Create baseline metrics
python manage.py runserver
# Note down current performance

# 4. Start Phase 1
git checkout -b refactor/performance-optimization
# Begin with database indexes
```

---

**Last Updated:** 2025-11-02
**Next Review:** After each phase completion
**Maintainer:** Development Team
