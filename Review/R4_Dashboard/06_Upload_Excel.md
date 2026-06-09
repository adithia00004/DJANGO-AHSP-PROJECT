# R4.6 - Review Upload Excel

**Status:** `[x]` PASS (functional)
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/dashboard/upload/` |
| View | `dashboard.views.project_upload_view` |
| Template | `dashboard/templates/dashboard/project_upload.html` |
| Form | `dashboard.forms.UploadProjectForm` |
| Auth Required | Ya + subscription active |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Upload valid Excel file | Project(s) created | `[x]` |
| TC-2 | Upload invalid file format (non-xlsx) | Error message | `[x]` |
| TC-3 | Upload empty Excel | Error info (tidak ada data valid) | `[x]` |
| TC-4 | Upload Excel with missing required columns | Validation error detail | `[x]` |
| TC-5 | Upload very large file | Size + row limit enforced | `[x]` |
| TC-6 | File upload XSS (filename) | Safe rendering + tidak dieksekusi | `[x]` |
| TC-7 | Malicious Excel (formula injection) | Formula rows rejected | `[x]` |
| TC-8 | CSRF protection | Token present di form upload | `[x]` |
| TC-9 | Progress indicator | UI menunjukkan state "sedang upload" | `[x]` |
| TC-10 | Duplicate data handling | Duplicate nama di-skip dengan warning | `[x]` |

Evidence test:
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_excel_valid_creates_projects`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_page_contains_csrf_and_file_input`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_rejects_non_xlsx_file`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_missing_required_header_shows_error`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_rejects_formula_cell`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_duplicate_name_in_file_is_skipped`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_row_limit_enforced`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_upload_file_size_limit_enforced`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_expired_owner_blocked_on_project_upload_post`

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Tidak ada temuan blocker terbuka | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| REC-1 | Pertimbangkan antivirus/malware scanning untuk file upload jika deployment menerima file dari tenant publik | P2 | Medium |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Pisahkan validasi header menjadi required vs optional agar sesuai panduan template | - | DONE |
| 2 | 2026-02-17 | Tambahkan guard keamanan upload: limit ukuran file, limit jumlah baris, reject formula cells, dan error message parser yang aman | - | DONE |
| 3 | 2026-02-17 | Tambah duplicate handling berbasis nama project (skip + warning) pada batch import | - | DONE |
| 4 | 2026-02-17 | Perbaiki UX upload page (HTML valid, error display, progress indicator saat submit) | - | DONE |
| 5 | 2026-02-17 | Tambah regression test untuk upload flow, guard subscription, dan validasi security | - | DONE |

---

## Checklist Sign-off

- [x] File validation OK
- [x] Security (XSS, formula injection) OK
- [x] Error handling OK
- [x] CSRF OK
- [x] UX OK
- [ ] Reviewer sign-off
