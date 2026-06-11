# R5.15 - Review API Endpoints (General)

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| File | `detail_project/views_api.py` (~361KB) |
| Helpers | `detail_project/api_helpers.py` |
| Total Endpoints | 100+ |

---

## Audit Keamanan API (Cross-cutting)

### Authentication & Authorization

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Semua API require login | 401/redirect for anonymous | `[ ]` |
| TC-2 | Project ownership check | 403 for non-owner | `[ ]` |
| TC-3 | Subscription check on write APIs | Blocked if expired | `[ ]` |
| TC-4 | Staff bypass works | Full access | `[ ]` |

### Input Validation

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-5 | Invalid project_id | 404 | `[ ]` |
| TC-6 | Invalid pekerjaan_id | 404 | `[ ]` |
| TC-7 | Malformed JSON body | 400 with message | `[ ]` |
| TC-8 | Oversized request body | Rejected | `[ ]` |
| TC-9 | SQL injection in parameters | Parameterized queries | `[ ]` |
| TC-10 | XSS in string fields | Escaped/sanitized | `[ ]` |

### Response Format

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-11 | Success response format | `{"status": "ok", "data": ...}` | `[ ]` |
| TC-12 | Error response format | `{"error": "message"}` consistent | `[ ]` |
| TC-13 | HTTP status codes | Correct per operation | `[ ]` |
| TC-14 | Content-Type headers | application/json | `[ ]` |

### CSRF & Methods

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-15 | CSRF on POST/PUT/DELETE | Token required | `[ ]` |
| TC-16 | Method not allowed | 405 for wrong method | `[ ]` |
| TC-17 | GET endpoints idempotent | No side effects | `[ ]` |

### Performance

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-18 | N+1 query detection | No N+1 queries | `[ ]` |
| TC-19 | Response time < 500ms | For typical requests | `[ ]` |
| TC-20 | Large dataset pagination | Pagination implemented | `[ ]` |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Belum ada temuan | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| - | Belum ada rekomendasi | - | - |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| - | - | Belum ada perbaikan | - | - |

---

## Checklist Sign-off

- [ ] All endpoints authenticated
- [ ] Authorization (owner check) consistent
- [ ] Input validation complete
- [ ] Response format consistent
- [ ] CSRF protection OK
- [ ] Performance OK
- [ ] Reviewer sign-off
