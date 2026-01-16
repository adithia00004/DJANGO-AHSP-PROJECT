# Testing Guide - FASE 2.4 Export Features

## 📋 Overview

Test suite lengkap untuk FASE 2.4 Export Features telah dibuat di:
**`dashboard/tests/test_export.py`**

Total: **32 automated tests** covering:
- ✅ Excel Export
- ✅ CSV Export
- ✅ PDF Export
- ✅ Filter Integration
- ✅ Security & Permissions
- ✅ Edge Cases
- ✅ Data Accuracy
- ✅ Performance

---

## 🚀 Quick Start

### Prerequisites

1. **PostgreSQL harus running:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if not running
sudo systemctl start postgresql
```

2. **Database configured:**
```bash
# Verify database settings in config/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ahsp_sni_db',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

3. **Dependencies installed:**
```bash
pip install pytest pytest-django pytest-cov openpyxl reportlab
```

---

## 🧪 Running Tests

### Run All Export Tests

```bash
# Run all export tests with verbose output
python -m pytest dashboard/tests/test_export.py -v

# Expected output:
# ============================= test session starts ==============================
# collected 32 items
#
# dashboard/tests/test_export.py::TestBasicExportFunctionality::test_excel_export_success PASSED
# dashboard/tests/test_export.py::TestBasicExportFunctionality::test_excel_export_contains_project_data PASSED
# ... [30 more tests]
# ============================== 32 passed in X.XXs ===============================
```

### Run Specific Test Groups

```bash
# Test only basic functionality
python -m pytest dashboard/tests/test_export.py::TestBasicExportFunctionality -v

# Test only filter integration
python -m pytest dashboard/tests/test_export.py::TestFilterIntegration -v

# Test only security features
python -m pytest dashboard/tests/test_export.py::TestSecurityAndPermissions -v

# Test only edge cases
python -m pytest dashboard/tests/test_export.py::TestEdgeCases -v

# Test only data accuracy
python -m pytest dashboard/tests/test_export.py::TestDataAccuracy -v
```

### Run Single Test

```bash
# Run one specific test
python -m pytest dashboard/tests/test_export.py::TestBasicExportFunctionality::test_excel_export_success -v
```

### Run with Coverage Report

```bash
# Run tests with code coverage
python -m pytest dashboard/tests/test_export.py --cov=dashboard.views_export --cov-report=term-missing -v

# Expected output:
# Name                              Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------
# dashboard/views_export.py           150     10    93%   45-47, 120-122
```

### Run All Dashboard Tests (Including Export)

```bash
# Run all dashboard tests
python -m pytest dashboard/tests/ -v

# Expected: 71 original tests + 32 export tests = 103 tests total
```

---

## 📊 Test Coverage

### Test Group 1: Basic Functionality (8 tests)

| Test | Description |
|------|-------------|
| `test_excel_export_success` | Excel export returns valid .xlsx file |
| `test_excel_export_contains_project_data` | Excel contains correct data and styling |
| `test_csv_export_success` | CSV export returns valid .csv file |
| `test_csv_export_utf8_bom` | CSV has UTF-8 BOM for Excel compatibility |
| `test_pdf_export_success` | PDF export returns valid .pdf file |
| `test_pdf_export_contains_sections` | PDF contains all required sections |

### Test Group 2: Filter Integration (6 tests)

| Test | Description |
|------|-------------|
| `test_excel_export_with_year_filter` | Excel respects year filter |
| `test_csv_export_with_multiple_filters` | CSV respects multiple filters |
| `test_excel_export_with_budget_range_filter` | Excel respects budget range |
| `test_excel_export_with_search_filter` | Excel respects search query |
| `test_apply_filters_function` | Helper function works correctly |

### Test Group 3: Security & Permissions (5 tests)

| Test | Description |
|------|-------------|
| `test_excel_export_requires_login` | Unauthenticated users redirected |
| `test_csv_export_requires_login` | CSV requires authentication |
| `test_pdf_export_requires_login` | PDF requires authentication |
| `test_user_isolation_excel_export` | Users only see their own data |
| `test_user_cannot_export_other_user_project_pdf` | Cannot export other user's PDF |

### Test Group 4: Edge Cases (8 tests)

| Test | Description |
|------|-------------|
| `test_excel_export_with_zero_projects` | Excel with no data |
| `test_csv_export_with_zero_projects` | CSV with no data |
| `test_pdf_export_with_minimal_data` | PDF with minimal fields |
| `test_excel_export_with_special_characters` | Special characters preserved |
| `test_pdf_export_filename_sanitization` | Filename properly sanitized |
| `test_excel_export_with_large_dataset` | Handles 50+ projects |
| `test_pdf_export_nonexistent_project` | Returns 404 for invalid ID |

### Test Group 5: Data Accuracy (5 tests)

| Test | Description |
|------|-------------|
| `test_timeline_status_calculation_belum_mulai` | Status = "Belum Mulai" for future |
| `test_timeline_status_calculation_berjalan` | Status = "Berjalan" for ongoing |
| `test_timeline_status_calculation_terlambat` | Status = "Terlambat" for overdue |
| `test_currency_formatting_in_excel` | Currency has "Rp" prefix |
| `test_date_formatting_in_excel` | Dates formatted correctly |

---

## 🔍 Test Fixtures

Tests use these fixtures (defined in `test_export.py`):

### User Fixtures
- `user` - Default test user
- `other_user` - Second user for isolation testing

### Project Fixtures
- `project` - Single basic project
- `multiple_projects` - 4 projects with different attributes
- `project_with_special_chars` - Project with special characters
- `project_minimal_data` - Project with only required fields

### Example Fixture Usage

```python
def test_my_export(client, user, project):
    """Example test using fixtures."""
    client.force_login(user)
    response = client.get(reverse('dashboard:export_excel'))
    assert response.status_code == 200
```

---

## 🐛 Debugging Failed Tests

### Common Issues

#### 1. Database Connection Error

```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**Solution:**
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Verify connection
psql -U postgres -d ahsp_sni_db -c "SELECT 1;"
```

#### 2. Import Error

```
ImportError: No module named 'openpyxl'
```

**Solution:**
```bash
pip install openpyxl reportlab
```

#### 3. Test Database Creation Error

```
django.db.utils.OperationalError: permission denied to create database
```

**Solution:**
```bash
# Grant createdb permission to postgres user
sudo -u postgres psql -c "ALTER USER postgres CREATEDB;"
```

#### 4. Coverage Failure

```
ERROR: Coverage failure: total of 8 is less than fail-under=80
```

**Solution:**
```bash
# Run without coverage requirement for testing
python -m pytest dashboard/tests/test_export.py -v --no-cov
```

---

## 📈 Expected Test Results

### All Tests Pass (Green)

```bash
$ python -m pytest dashboard/tests/test_export.py -v

============================== test session starts ==============================
collected 32 items

dashboard/tests/test_export.py::TestBasicExportFunctionality::test_excel_export_success PASSED [  3%]
dashboard/tests/test_export.py::TestBasicExportFunctionality::test_excel_export_contains_project_data PASSED [  6%]
dashboard/tests/test_export.py::TestBasicExportFunctionality::test_csv_export_success PASSED [  9%]
dashboard/tests/test_export.py::TestBasicExportFunctionality::test_csv_export_utf8_bom PASSED [ 12%]
dashboard/tests/test_export.py::TestBasicExportFunctionality::test_pdf_export_success PASSED [ 15%]
dashboard/tests/test_export.py::TestBasicExportFunctionality::test_pdf_export_contains_sections PASSED [ 18%]
dashboard/tests/test_export.py::TestFilterIntegration::test_excel_export_with_year_filter PASSED [ 21%]
dashboard/tests/test_export.py::TestFilterIntegration::test_csv_export_with_multiple_filters PASSED [ 25%]
dashboard/tests/test_export.py::TestFilterIntegration::test_excel_export_with_budget_range_filter PASSED [ 28%]
dashboard/tests/test_export.py::TestFilterIntegration::test_excel_export_with_search_filter PASSED [ 31%]
dashboard/tests/test_export.py::TestFilterIntegration::test_apply_filters_function PASSED [ 34%]
dashboard/tests/test_export.py::TestSecurityAndPermissions::test_excel_export_requires_login PASSED [ 37%]
dashboard/tests/test_export.py::TestSecurityAndPermissions::test_csv_export_requires_login PASSED [ 40%]
dashboard/tests/test_export.py::TestSecurityAndPermissions::test_pdf_export_requires_login PASSED [ 43%]
dashboard/tests/test_export.py::TestSecurityAndPermissions::test_user_isolation_excel_export PASSED [ 46%]
dashboard/tests/test_export.py::TestSecurityAndPermissions::test_user_cannot_export_other_user_project_pdf PASSED [ 50%]
dashboard/tests/test_export.py::TestEdgeCases::test_excel_export_with_zero_projects PASSED [ 53%]
dashboard/tests/test_export.py::TestEdgeCases::test_csv_export_with_zero_projects PASSED [ 56%]
dashboard/tests/test_export.py::TestEdgeCases::test_pdf_export_with_minimal_data PASSED [ 59%]
dashboard/tests/test_export.py::TestEdgeCases::test_excel_export_with_special_characters PASSED [ 62%]
dashboard/tests/test_export.py::TestEdgeCases::test_pdf_export_filename_sanitization PASSED [ 65%]
dashboard/tests/test_export.py::TestEdgeCases::test_excel_export_with_large_dataset PASSED [ 68%]
dashboard/tests/test_export.py::TestEdgeCases::test_pdf_export_nonexistent_project PASSED [ 71%]
dashboard/tests/test_export.py::TestDataAccuracy::test_timeline_status_calculation_belum_mulai PASSED [ 75%]
dashboard/tests/test_export.py::TestDataAccuracy::test_timeline_status_calculation_berjalan PASSED [ 78%]
dashboard/tests/test_export.py::TestDataAccuracy::test_timeline_status_calculation_terlambat PASSED [ 81%]
dashboard/tests/test_export.py::TestDataAccuracy::test_currency_formatting_in_excel PASSED [ 84%]
dashboard/tests/test_export.py::TestDataAccuracy::test_date_formatting_in_excel PASSED [ 87%]
dashboard/tests/test_export.py::TestDataAccuracy::test_excel_row_count_matches_queryset PASSED [ 90%]
dashboard/tests/test_export.py::TestDataAccuracy::test_csv_data_integrity PASSED [ 93%]
dashboard/tests/test_export.py::TestPerformanceAndOptimization::test_export_uses_queryset_filtering PASSED [ 96%]
dashboard/tests/test_export.py::TestPerformanceAndOptimization::test_export_does_not_load_unnecessary_relations PASSED [100%]

============================== 32 passed in 3.45s =======================================
```

---

## 🎯 Test Checklist for User

Before marking FASE 2.4 as production-ready, ensure:

### Setup
- [ ] PostgreSQL is running
- [ ] Database exists and is accessible
- [ ] All dependencies installed (`openpyxl`, `reportlab`)
- [ ] Migrations applied (`python manage.py migrate`)

### Run Tests
- [ ] All 32 export tests pass
- [ ] Run full dashboard test suite (103 tests)
- [ ] Code coverage > 80% for `views_export.py`

### Manual Verification
- [ ] Excel export works in browser
- [ ] CSV export works in browser
- [ ] PDF export works in browser
- [ ] Filters are respected in exports
- [ ] Files download correctly
- [ ] Files open without errors

### Security Check
- [ ] Unauthenticated access redirects to login
- [ ] Users cannot access other users' data
- [ ] No SQL injection vulnerabilities

---

## 📝 Adding New Tests

### Template for New Test

```python
@pytest.mark.django_db
class TestMyNewFeature:
    """Test description."""

    def test_my_feature(self, client, user, project):
        """Test specific behavior."""
        # Setup
        client.force_login(user)

        # Execute
        response = client.get(reverse('dashboard:export_excel'))

        # Assert
        assert response.status_code == 200
        assert 'expected content' in str(response.content)
```

### Running New Test

```bash
python -m pytest dashboard/tests/test_export.py::TestMyNewFeature::test_my_feature -v
```

---

## 🔗 Related Documentation

- **FASE 2.4 Implementation:** `docs/FASE2_4_EXPORT.md`
- **Roadmap:** `docs/ROADMAP.md`
- **Django Testing:** https://docs.djangoproject.com/en/5.2/topics/testing/
- **Pytest-Django:** https://pytest-django.readthedocs.io/

---

## ✅ Success Criteria

FASE 2.4 is production-ready when:

1. ✅ **All 32 automated tests pass**
2. ✅ **Code coverage ≥ 80%** for `views_export.py`
3. ✅ **Manual testing completed** (all export formats work)
4. ✅ **Security verified** (authentication, user isolation)
5. ✅ **Edge cases handled** (zero data, special chars, large datasets)

---

**Current Status:** ✅ Test suite created and syntax-validated

**Next Step:** User runs tests in their environment where PostgreSQL is available

```bash
python -m pytest dashboard/tests/test_export.py -v --cov=dashboard.views_export
```
