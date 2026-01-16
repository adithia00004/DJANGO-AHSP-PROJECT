# Testing Guide - Django AHSP Project

## 📋 Ringkasan Status Test

**Coverage Target:** 60% (detail_project saja)
**Coverage Saat Ini:** ~60-65% (setelah perbaikan)
**Total Test Files:** 56 files
**Test Aktif:** ~25 files (core functionality)
**Test Disabled:** ~31 files (pending review)

---

## 🎯 Filosofi Testing

Test difokuskan pada **core business logic** di `detail_project` karena:
1. Core functionality RAB/AHSP ada di sini
2. Perubahan paling sering terjadi di module ini
3. Risk tertinggi ada di kalkulasi dan rekap

Dashboard dan Referensi tests di-disable sementara karena:
- Banyak yang 0% coverage (tidak dijalankan)
- Feature sudah berubah/pindah
- Perlu review apakah masih relevan

---

## 🚀 Menjalankan Test

### **Quick Start - Run All Active Tests**
```bash
pytest
```

### **With Coverage Report**
```bash
pytest --cov-report=html
# Buka htmlcov/index.html di browser untuk lihat detail
```

### **Run Specific Test File**
```bash
pytest detail_project/tests/test_api_formula_state.py -v
```

### **Run Fast Tests Only (Skip Slow Tests)**
```bash
pytest -m "not slow"
```

### **Run Specific Test Categories**
```bash
# API tests only
pytest -m api

# Security tests only
pytest -m security

# Integration tests only
pytest -m integration
```

### **Debug Mode (Show Print Statements)**
```bash
pytest -s -v
```

### **Stop on First Failure**
```bash
pytest -x
```

### **Run Tests in Parallel (Faster)**
```bash
pytest -n auto
```

---

## 📁 Struktur Test

```
tests/
├── dashboard/tests/          # ⚠️  Mostly DISABLED (0% coverage)
│   ├── test_models.py        # ✅ ACTIVE
│   ├── test_forms.py         # ✅ ACTIVE
│   ├── test_views.py         # ✅ ACTIVE
│   ├── test_bulk_actions.py  # ❌ DISABLED
│   ├── test_export.py        # ❌ DISABLED
│   └── test_integration.py   # ❌ DISABLED
│
├── detail_project/tests/     # ✅ CORE TESTS (ACTIVE)
│   ├── test_api_*.py         # API endpoint tests
│   ├── test_rekap_*.py       # Rekap/report tests
│   ├── test_tahapan_*.py     # Scheduling tests
│   ├── test_volume_*.py      # Volume calculation tests
│   ├── test_phase4_*.py      # Infrastructure tests
│   ├── test_phase5_*.py      # Integration & security
│   └── test_*_ui.py          # ❌ DISABLED (UI tests)
│
└── referensi/tests/          # ⚠️  Mostly DISABLED
    ├── test_*.py             # ❌ DISABLED (PostgreSQL specific)
    └── ...                   # Needs review
```

---

## 🏷️ Test Markers

Test markers untuk selective testing:

| Marker | Deskripsi | Contoh |
|--------|-----------|--------|
| `@pytest.mark.unit` | Unit test (fast, isolated) | Test single function |
| `@pytest.mark.integration` | Integration test (needs DB, etc) | Test API endpoint |
| `@pytest.mark.slow` | Slow test (>5 detik) | Export PDF test |
| `@pytest.mark.api` | API endpoint test | Test POST /api/save |
| `@pytest.mark.ui` | UI/template test | Test HTML rendering |
| `@pytest.mark.security` | Security-related test | Test XSS prevention |
| `@pytest.mark.deprecated` | Test for deprecated feature | Will be removed |

**Cara pakai:**
```python
@pytest.mark.slow
@pytest.mark.api
def test_export_large_rab(client_logged, project):
    # Test that takes > 5 seconds
    pass
```

**Run tanpa slow tests:**
```bash
pytest -m "not slow"
```

---

## 🔧 Configuration

### pytest.ini
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
addopts = --cov=detail_project --cov-fail-under=60
```

**Key Settings:**
- Coverage fokus di `detail_project` saja
- Target: 60% (akan naik bertahap ke 70% → 80%)
- SQLite in-memory database (faster)
- Migrations disabled (faster table creation)

### Test Settings (config/settings/test.py)
- Database: SQLite in-memory
- Cache: Local memory
- Email: Console backend
- Password hashing: MD5 (faster, OK untuk test)

---

## ✅ Test Coverage Goals

| Module | Current | Target Q1 | Target Q2 |
|--------|---------|-----------|-----------|
| detail_project | 60% | 70% | 80% |
| dashboard | 5% | 50% | 60% |
| referensi | 0% | 30% | 50% |

**Prioritas:**
1. ✅ Phase 1: Core detail_project tests (60%)
2. 🔄 Phase 2: Review & update dashboard tests (50%)
3. 📋 Phase 3: Review & update referensi tests (30%)

---

## 🐛 Debugging Failed Tests

### 1. Check Test Output
```bash
pytest -vv --tb=long
```

### 2. Run with pdb (Python Debugger)
```bash
pytest --pdb
# Test akan pause di failure, bisa inspect variables
```

### 3. Check Coverage for Specific File
```bash
pytest --cov=detail_project.views_api --cov-report=term-missing
```

### 4. Re-run Only Failed Tests
```bash
pytest --lf  # last-failed
```

---

## 📊 Common Test Patterns

### Test dengan Project Fixture
```python
def test_something(client_logged, project):
    # project sudah include semua field wajib
    # client_logged sudah login sebagai owner
    response = client_logged.get(f'/project/{project.id}/')
    assert response.status_code == 200
```

### Test API Endpoint
```python
@pytest.mark.api
def test_api_save(client_logged, project, api_urls):
    payload = {'data': 'value'}
    response = client_logged.post(
        api_urls['save'],
        json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
```

### Test dengan Database Transaction
```python
@pytest.mark.django_db(transaction=True)
def test_concurrent_update(client_logged, project):
    # Test concurrent updates
    pass
```

---

## ❌ Disabled Tests

Test yang di-disable sementara dan alasannya:

### Dashboard Tests
- `test_bulk_actions.py` - Feature moved/changed
- `test_export.py` - Export moved to detail_project
- `test_integration.py` - Needs update for new workflow

### Detail Project Tests
- `test_list_pekerjaan_page_ui.py` - Needs Selenium
- `test_jadwal_pekerjaan_page_ui.py` - Needs Selenium

### Referensi Tests (Most of them)
- PostgreSQL-specific (SQLite incompatible)
- Import features changed significantly
- Audit features need review
- Full-text search needs PostgreSQL

**Action:** Review these tests quarterly untuk decide:
- Update to match current features
- Remove if feature deprecated
- Re-enable if still relevant

---

## 🎓 Best Practices

### DO ✅
1. Write tests for new features
2. Update tests when changing features
3. Run tests before commit: `pytest -x`
4. Use markers for categorization
5. Keep fixtures in conftest.py
6. Use meaningful test names: `test_api_save_validates_required_fields`

### DON'T ❌
1. Don't skip failing tests without documenting why
2. Don't test Django framework (already tested)
3. Don't test third-party libraries
4. Don't write tests that depend on external services
5. Don't commit with failing tests

---

## 🔄 CI/CD Integration

### GitHub Actions / GitLab CI
```yaml
test:
  script:
    - pytest -m "not slow" --cov-fail-under=55
```

### Pre-commit Hook
```bash
#!/bin/sh
pytest -x --tb=short
```

---

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## 📞 Support

Jika ada pertanyaan tentang testing:
1. Check TESTING.md (this file)
2. Check test conftest.py for available fixtures
3. Check pytest.ini for configuration
4. Ask team lead

---

**Last Updated:** 2025-01-11
**Coverage Target:** 60% → 70% (Q1 2025) → 80% (Q2 2025)
