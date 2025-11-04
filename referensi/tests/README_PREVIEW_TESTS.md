# Preview Import Test Suite

Comprehensive test suite untuk semua fitur pada halaman preview import.

## 📋 Test Coverage

### ✅ Backend Search Functionality
- `test_search_jobs_filters_by_nama_ahsp` - Search di kolom Nama Pekerjaan
- `test_search_jobs_filters_by_kode_ahsp` - Search di kolom Kode
- `test_search_jobs_filters_by_sumber` - Search di kolom Sumber
- `test_search_jobs_case_insensitive` - Case-insensitive search
- `test_search_jobs_with_no_results` - Handle no results
- `test_search_jobs_pagination_works` - Pagination dengan search results
- `test_search_details_filters_by_kode_item` - Search details by kode
- `test_search_details_filters_by_uraian_item` - Search details by uraian
- `test_search_without_query_returns_all` - Empty query returns all

### ✅ Pagination
- `test_default_page_size_is_50` - Default 50 rows per page
- `test_pagination_calculates_correctly` - Correct calculation
- `test_pagination_last_page` - Last page with partial results
- `test_pagination_handles_invalid_page` - Invalid page number handling
- `test_jobs_pagination_with_search` - Pagination with filtered results

### ✅ Service Layer
- `test_filter_jobs_method` - Filter jobs helper
- `test_filter_jobs_empty_query_returns_all` - Empty query handling
- `test_filter_jobs_partial_match` - Partial keyword match
- `test_build_job_page_without_data` - Handle None data
- `test_build_detail_page_without_data` - Handle None data

### ✅ View Layer
- `test_view_accepts_search_query_parameter` - Accept search params
- `test_view_passes_search_query_to_service` - Pass params to service
- `test_view_requires_permission` - Permission checking

### ✅ Integration Tests
- `test_complete_search_workflow` - End-to-end search
- `test_search_across_multiple_fields` - Multi-field search
- `test_performance_with_large_dataset` - Performance with 1000+ rows

## 🚀 Running Tests

### Run All Preview Tests
```bash
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
pytest referensi/tests/test_preview_import_features.py -v
```

### Run Specific Test Class
```bash
# Test search functionality only
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportSearchFunctionality -v

# Test pagination only
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportPagination -v

# Test service layer only
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportService -v

# Test view layer only
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportView -v

# Test integration
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportIntegration -v
```

### Run Specific Test
```bash
# Test search by name
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_filters_by_nama_ahsp -v

# Test pagination
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportPagination::test_default_page_size_is_50 -v
```

### Run with Coverage
```bash
pytest referensi/tests/test_preview_import_features.py --cov=referensi.services.preview_service --cov=referensi.views.preview --cov-report=html
```

### Run with Performance Profiling
```bash
pytest referensi/tests/test_preview_import_features.py::TestPreviewImportIntegration::test_performance_with_large_dataset -v --durations=10
```

## 📊 Expected Test Results

```
========================= test session starts =========================
collected 29 items

test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_filters_by_nama_ahsp PASSED [ 3%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_filters_by_kode_ahsp PASSED [ 6%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_filters_by_sumber PASSED [ 10%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_case_insensitive PASSED [ 13%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_with_no_results PASSED [ 17%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_jobs_pagination_works PASSED [ 20%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_details_filters_by_kode_item PASSED [ 24%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_details_filters_by_uraian_item PASSED [ 27%]
test_preview_import_features.py::TestPreviewImportSearchFunctionality::test_search_without_query_returns_all PASSED [ 31%]
test_preview_import_features.py::TestPreviewImportPagination::test_default_page_size_is_50 PASSED [ 34%]
test_preview_import_features.py::TestPreviewImportPagination::test_pagination_calculates_correctly PASSED [ 37%]
test_preview_import_features.py::TestPreviewImportPagination::test_pagination_last_page PASSED [ 41%]
test_preview_import_features.py::TestPreviewImportPagination::test_pagination_handles_invalid_page PASSED [ 44%]
test_preview_import_features.py::TestPreviewImportPagination::test_jobs_pagination_with_search PASSED [ 48%]
test_preview_import_features.py::TestPreviewImportService::test_filter_jobs_method PASSED [ 51%]
test_preview_import_features.py::TestPreviewImportService::test_filter_jobs_empty_query_returns_all PASSED [ 55%]
test_preview_import_features.py::TestPreviewImportService::test_filter_jobs_partial_match PASSED [ 58%]
test_preview_import_features.py::TestPreviewImportService::test_build_job_page_without_data PASSED [ 62%]
test_preview_import_features.py::TestPreviewImportService::test_build_detail_page_without_data PASSED [ 65%]
test_preview_import_features.py::TestPreviewImportView::test_view_accepts_search_query_parameter PASSED [ 68%]
test_preview_import_features.py::TestPreviewImportView::test_view_passes_search_query_to_service PASSED [ 72%]
test_preview_import_features.py::TestPreviewImportView::test_view_requires_permission PASSED [ 75%]
test_preview_import_features.py::TestPreviewImportIntegration::test_complete_search_workflow PASSED [ 79%]
test_preview_import_features.py::TestPreviewImportIntegration::test_search_across_multiple_fields PASSED [ 82%]
test_preview_import_features.py::TestPreviewImportIntegration::test_performance_with_large_dataset PASSED [ 86%]

========================= 29 tests passed in 0.85s =========================
```

## 🔍 Test Data

Test menggunakan `create_test_parse_result()` helper yang membuat:
- Configurable number of jobs (default: 10)
- Configurable details per job (default: 5)
- Jobs dengan searchable content:
  - Every 3rd job has "beton" in name
  - Every 3rd+1 job has "pagar" in name
  - Every 3rd+2 job has "pasir" in name
- Rotating sources: "Sumber 0", "Sumber 1", "Sumber 2"
- Sequential codes: AHSP-0000, AHSP-0001, etc.

## 🐛 Debugging Failed Tests

### Enable Verbose Output
```bash
pytest referensi/tests/test_preview_import_features.py -v -s
```

### Show Print Statements
```bash
pytest referensi/tests/test_preview_import_features.py -v -s --capture=no
```

### Stop on First Failure
```bash
pytest referensi/tests/test_preview_import_features.py -x
```

### Run Only Failed Tests
```bash
pytest referensi/tests/test_preview_import_features.py --lf
```

## 📝 Adding New Tests

Template untuk menambah test baru:

```python
def test_your_new_feature(self):
    """Test description"""
    # 1. Setup
    parse_result = create_test_parse_result(num_jobs=30)

    # 2. Execute
    service = PreviewImportService(
        search_queries={"jobs": "keyword", "details": ""}
    )
    page_data = service.build_job_page(parse_result, page=1)

    # 3. Assert
    assert page_data.page_info.total_items > 0
    # ... more assertions
```

## 🔧 Troubleshooting

### Import Errors
```bash
# Make sure you're in project root
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"

# Activate virtual environment
.\env\Scripts\activate

# Install pytest if not installed
pip install pytest pytest-django pytest-cov
```

### Database Errors
```bash
# Run migrations
python manage.py migrate

# Create test database
python manage.py test --keepdb
```

### Session Errors
Tests use `override_settings` decorator:
```python
@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
```

## 📚 Related Test Files

- `test_preview_view.py` - Original view tests (older tests)
- `test_preview_service.py` - Service layer unit tests
- `services/test_preview_service.py` - More service tests
- `test_preview_parser.py` - Parser tests

## ✅ Continuous Integration

Tambahkan ke CI/CD pipeline:

```yaml
# .github/workflows/tests.yml
- name: Run Preview Import Tests
  run: |
    pytest referensi/tests/test_preview_import_features.py -v --cov --cov-report=xml
```

## 📈 Coverage Goals

Target coverage untuk preview import features:
- Service Layer: **>95%**
- View Layer: **>85%**
- Integration: **>90%**

Check current coverage:
```bash
pytest referensi/tests/test_preview_import_features.py --cov=referensi.services.preview_service --cov=referensi.views.preview --cov-report=term-missing
```
