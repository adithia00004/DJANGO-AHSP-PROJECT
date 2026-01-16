# REFACTORING RECOMMENDATIONS - APPS REFERENSI
**Generated:** 2025-11-02
**Project:** Django AHSP Project
**App:** referensi

---

## EXECUTIVE SUMMARY

Apps referensi adalah sistem Reference Data Management untuk AHSP (Analisis Harga Satuan Pekerjaan). Aplikasi memiliki fondasi solid namun mengalami technical debt signifikan di view layer dan state management.

**Overall Code Quality Score: 5.8/10**

---

## CRITICAL ISSUES (Prioritas Tertinggi)

### 1. God Functions di View Layer
**File:** `referensi/views/preview.py` (550 lines), `referensi/views/admin_portal.py` (391 lines)

**Problem:**
- Single function menangani terlalu banyak tanggung jawab
- Sulit di-test, maintain, dan debug
- Business logic tercampur dengan presentation logic

**Solution:**
```python
# Pisahkan menjadi service class
class PreviewImportService:
    def validate_file(self, file) -> ValidationResult
    def load_from_session(self, session) -> ParseResult
    def save_to_session(self, session, data) -> str
    def build_job_formset(self, parse_result, page) -> FormSet
    def build_detail_formset(self, parse_result, page) -> FormSet
    def commit_to_database(self, parse_result) -> ImportSummary
```

### 2. Session-based State Management dengan Pickle
**File:** `referensi/views/preview.py`

**Problem:**
- Pickle files di temporary directory berisiko gagal cleanup
- Concurrent requests bisa conflict
- Tidak ada TTL → memory leak
- Sulit di-debug dan trace

**Solution:**
```python
# Gunakan Django Cache dengan Redis/Memcached
from django.core.cache import cache
import uuid

class ImportSessionManager:
    TIMEOUT = 3600  # 1 hour
    PREFIX = "import_session"

    def store(self, user_id, parse_result):
        key = f"{self.PREFIX}:{user_id}:{uuid.uuid4()}"
        cache.set(key, parse_result, timeout=self.TIMEOUT)
        return key

    def retrieve(self, key):
        return cache.get(key)

    def delete(self, key):
        cache.delete(key)
```

### 3. Duplikasi Logic Category Normalization
**Files:**
- `referensi/services/import_utils.py:canonicalize_kategori()`
- `referensi/management/commands/normalize_referensi.py` (lines 27-30)

**Solution:**
```python
# Gunakan satu source of truth
from referensi.services.import_utils import canonicalize_kategori

# Di normalize_referensi.py, hapus duplikasi dan import dari import_utils
```

---

## HIGH PRIORITY ISSUES

### 4. Tidak Ada Validasi Input di Forms
**Files:** `referensi/forms/preview.py`

**Solution:**
```python
class PreviewJobForm(forms.Form):
    def clean_kode_ahsp(self):
        kode = self.cleaned_data.get('kode_ahsp', '')
        if not kode or len(kode) > 50:
            raise ValidationError("Kode AHSP maksimal 50 karakter")
        return kode.strip()

    def clean_koefisien(self):
        koef = self.cleaned_data.get('koefisien')
        if koef is not None and koef < 0:
            raise ValidationError("Koefisien tidak boleh negatif")
        return koef

    def clean(self):
        # Cross-field validation
        cleaned_data = super().clean()
        return cleaned_data
```

### 5. Hardcoded Constants Tersebar

**Problem:** Constants ada di berbagai file tanpa centralized config

**Solution:**
```python
# settings.py
REFERENSI_CONFIG = {
    'page_sizes': {
        'jobs': 50,
        'details': 100,
    },
    'display_limits': {
        'jobs': 150,
        'items': 150,
    },
    'file_upload': {
        'max_size_mb': 10,
        'allowed_extensions': ['.xlsx', '.xls'],
    },
    'api': {
        'search_limit': 30,
        'rate_limit': '100/hour',
    },
}
```

### 6. Weak Permission Model

**Problem:** Hanya cek `is_superuser or is_staff` secara global

**Solution:**
```python
# Gunakan granular permissions
from django.contrib.auth.decorators import permission_required

@permission_required('referensi.view_ahspreferencesi')
def admin_portal(request):
    ...

@permission_required('referensi.change_ahspreferencesi')
def preview_import(request):
    ...

@permission_required('referensi.delete_ahspreferencesi')
def purge_data(request):
    ...
```

### 7. Tidak Ada Audit Trail

**Problem:** Tidak ada tracking siapa mengubah data kapan

**Solution:**
```python
# Option 1: Django Simple History
# pip install django-simple-history

from simple_history.models import HistoricalRecords

class AHSPReferensi(models.Model):
    ...
    history = HistoricalRecords()

# Option 2: Custom Audit Log
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20)  # CREATE, UPDATE, DELETE
    model_name = models.CharField(max_length=50)
    object_id = models.IntegerField()
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['-timestamp']),
        ]
```

### 8. No Rate Limiting on API

**Solution:**
```python
# pip install django-ratelimit

from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='100/h', method='GET')
def api_search_ahsp(request):
    ...
```

---

## MEDIUM PRIORITY ISSUES

### 9. Inefficient Anomaly Detection
**File:** `referensi/views/admin_portal.py`

**Problem:** Annotate semua category counts bahkan saat tidak digunakan

**Solution:**
```python
# Lazy evaluation - hanya compute saat dibutuhkan
def _base_ahsp_queryset(include_counts=False):
    qs = AHSPReferensi.objects.select_related()

    if include_counts:
        qs = qs.annotate(
            tk_count=Count('rincianreferensi', filter=Q(rincianreferensi__kategori='TK')),
            bhn_count=Count('rincianreferensi', filter=Q(rincianreferensi__kategori='BHN')),
            # ...
        )

    return qs
```

### 10. No Caching

**Problem:** Repeated queries untuk item code lookups

**Solution:**
```python
from django.core.cache import cache

class ItemCodeService:
    CACHE_KEY = "item_code_map"
    CACHE_TIMEOUT = 3600  # 1 hour

    @classmethod
    def get_item_code_map(cls) -> dict:
        cached = cache.get(cls.CACHE_KEY)
        if cached:
            return cached

        # Build map from database
        item_map = {}
        for item in KodeItemReferensi.objects.all():
            key = (item.kategori, item.uraian_item, item.satuan_item)
            item_map[key] = item.kode_item

        cache.set(cls.CACHE_KEY, item_map, cls.CACHE_TIMEOUT)
        return item_map

    @classmethod
    def invalidate_cache(cls):
        cache.delete(cls.CACHE_KEY)
```

### 11. Missing Type Hints Consistency

**Solution:**
```python
# Tambahkan type hints di semua functions
from typing import Optional, Dict, List, Tuple
from decimal import Decimal

def normalize_num(val: any, default: Decimal = Decimal(0)) -> Decimal:
    """Normalize value to Decimal."""
    ...

def canonicalize_kategori(text: Optional[str]) -> str:
    """Convert category text to standard code (TK/BHN/ALT/LAIN)."""
    ...
```

---

## ARCHITECTURAL RECOMMENDATIONS

### Recommended Directory Structure

```
referensi/
├── models/
│   ├── __init__.py
│   ├── ahsp.py              # AHSPReferensi
│   ├── rincian.py           # RincianReferensi
│   └── item_code.py         # KodeItemReferensi
├── services/
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── excel_parser.py  # ahsp_parser.py
│   │   ├── validators.py    # Validation logic
│   │   └── normalizers.py   # import_utils.py
│   ├── import_service.py    # import_writer.py
│   ├── session_manager.py   # NEW - Session handling
│   └── item_code_service.py # item_code_registry.py
├── repositories/             # NEW - Data access layer
│   ├── __init__.py
│   ├── ahsp_repository.py
│   └── item_repository.py
├── views/
│   ├── __init__.py
│   ├── mixins.py            # NEW - Shared view logic
│   ├── admin_portal.py
│   ├── preview.py
│   └── api.py
├── api/                      # Consider Django REST Framework
│   ├── __init__.py
│   ├── serializers.py
│   ├── viewsets.py
│   └── urls.py
├── forms/
│   ├── __init__.py
│   ├── database.py
│   └── preview.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_views.py
│   └── factories.py
├── management/
│   └── commands/
│       ├── import_ahsp.py
│       ├── purge_ahsp_referensi.py
│       └── normalize_referensi.py
├── static/referensi/
├── templates/referensi/
├── admin.py
├── urls.py
└── apps.py
```

### Repository Pattern Implementation

```python
# repositories/ahsp_repository.py
from django.db.models import QuerySet, Q, Count
from typing import Optional, Dict, Any

class AHSPRepository:
    """Data access layer for AHSP models."""

    @staticmethod
    def get_with_category_counts() -> QuerySet:
        """Get AHSP queryset with category counts annotated."""
        return AHSPReferensi.objects.annotate(
            tk_count=Count('rincianreferensi', filter=Q(rincianreferensi__kategori='TK')),
            bhn_count=Count('rincianreferensi', filter=Q(rincianreferensi__kategori='BHN')),
            alt_count=Count('rincianreferensi', filter=Q(rincianreferensi__kategori='ALT')),
            lain_count=Count('rincianreferensi', filter=Q(rincianreferensi__kategori='LAIN')),
        ).select_related()

    @staticmethod
    def filter_by_classification(queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Apply classification filters to queryset."""
        if 'klasifikasi' in filters:
            queryset = queryset.filter(klasifikasi=filters['klasifikasi'])
        if 'sub_klasifikasi' in filters:
            queryset = queryset.filter(sub_klasifikasi=filters['sub_klasifikasi'])
        return queryset

    @staticmethod
    def filter_by_anomalies(queryset: QuerySet) -> QuerySet:
        """Filter queryset to only items with anomalies."""
        return queryset.filter(
            Q(rincianreferensi__koefisien=0) |
            Q(rincianreferensi__satuan_item='')
        ).distinct()

    @staticmethod
    def search(query: str, limit: int = 30) -> QuerySet:
        """Search AHSP by code or name."""
        return AHSPReferensi.objects.filter(
            Q(kode_ahsp__icontains=query) |
            Q(nama_ahsp__icontains=query)
        )[:limit]
```

---

## REFACTORING ROADMAP

### Phase 1: Quick Wins (1-2 minggu)
- [ ] Extract helper functions dari view menjadi service methods
- [ ] Hapus duplikasi category normalization
- [ ] Add form validators
- [ ] Centralize constants ke settings
- [ ] Add type hints consistency

### Phase 2: Architecture (2-4 minggu)
- [ ] Implement repository pattern
- [ ] Replace session pickle dengan cache
- [ ] Add comprehensive error handling
- [ ] Implement audit logging
- [ ] Add rate limiting

### Phase 3: Enhancement (1-2 bulan)
- [ ] Migrate ke Django REST Framework untuk API
- [ ] Add caching layer (Redis)
- [ ] Implement granular permissions
- [ ] Add data quality dashboard
- [ ] Optimize database queries

---

## CODE QUALITY METRICS

| Aspek | Score | Keterangan |
|-------|-------|------------|
| Architecture | 6/10 | Service layer ada, tapi view masih fat |
| Testability | 7/10 | Ada test structure, perlu lebih banyak |
| Maintainability | 5/10 | God functions sulit maintain |
| Security | 6/10 | Basic permission, kurang granular |
| Performance | 7/10 | Query annotations bagus, kurang caching |
| Documentation | 4/10 | Sparse docstrings |

**Overall: 5.8/10** - Needs significant refactoring

---

## WHAT'S ALREADY GOOD

1. Service Layer Sudah Ada - Terpisah dari view
2. Parser Logic Bersih - Well-structured dengan dataclasses
3. Test Coverage - Ada struktur test yang baik
4. Clear Data Classes - Menggunakan @dataclass dengan baik
5. Error Collection - Tidak langsung fail, mengumpulkan errors
6. Atomic Transactions - Menggunakan transaction.atomic()
7. Flexible Column Mapping - Parser bisa handle berbagai format Excel

---

## ADDITIONAL RECOMMENDATIONS

1. **Type Hints Consistency** - Gunakan mypy untuk enforce typing
2. **API Versioning** - Jika akan public, tambahkan versioning (v1/, v2/)
3. **Monitoring** - Consider django-silk atau django-debug-toolbar
4. **Logging** - Structured logging dengan structlog
5. **Documentation** - Add comprehensive docstrings (Google style)
6. **CI/CD** - Setup automated testing dan linting (black, flake8, mypy)

---

## ANTI-PATTERNS IDENTIFIED

1. **God Function** - preview_import() handles too many concerns
2. **Implicit State via Session** - Heavy reliance on session pickling
3. **Inline Business Logic in Views** - Filter, pagination logic in views
4. **Missing Abstractions** - No repository pattern
5. **Inconsistent Error Handling** - Some collect, some raise

---

## NOTES

- This document should be updated as refactoring progresses
- Prioritize based on impact vs effort matrix
- Consider backward compatibility when making changes
- Add tests before refactoring critical paths
- Use feature flags for gradual rollout

---

**Last Updated:** 2025-11-02
