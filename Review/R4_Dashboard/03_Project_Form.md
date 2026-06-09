# R4.3 - Review Project Form (Create/Edit)

**Status:** `[x]` PASS (non-responsive)
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL Create | `/dashboard/project/create/` (atau via dashboard) |
| URL Edit | `/dashboard/project/<pk>/edit/` |
| View | `dashboard.views.project_edit` |
| Template | `dashboard/templates/dashboard/project_form.html` |
| Form | `dashboard.forms.ProjectForm` |
| Auth Required | Ya + subscription active |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Buat project baru dengan data valid | Project tersimpan | `[x]` |
| TC-2 | Edit project existing | Data updated | `[x]` |
| TC-3 | Submit form dengan required field kosong | Validation error | `[x]` |
| TC-4 | XSS pada input (nama project, deskripsi) | Input di-sanitize / escaped | `[x]` |
| TC-5 | CSRF protection | Token present | `[x]` |
| TC-6 | Expired user submit form | Blocked by middleware | `[x]` |
| TC-7 | Non-owner edit project | 403/404 | `[x]` |
| TC-8 | Anggaran field - format angka | Numeric validation benar | `[x]` |
| TC-9 | Tanggal mulai > tanggal selesai | Validation error | `[x]` |
| TC-10 | index_project uniqueness | Unique constraint enforced | `[x]` (model-level) |
| TC-11 | Responsive form layout | Usable di mobile | `[~]` (butuh validasi manual real-device) |

Evidence test:
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_owner_edit_delete_project`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_edit_form_validation_csrf_and_xss_escape`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_edit_parses_currency_and_redirects_to_next`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_expired_owner_blocked_on_project_edit_post`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_non_owner_blocked_from_project_pages`

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Tidak ada temuan terbuka | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| REC-1 | Lakukan uji manual mobile/tablet untuk final sign-off UX form tabs (`IDENTITAS/PEMILIK/TIM`) | P2 | Low |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Tambah summary error form edit agar validation feedback terlihat jelas pada UI | - | DONE |
| 2 | 2026-02-17 | Preserve navigasi `next` pada edit form (hidden field + tombol Batal) | - | DONE |
| 3 | 2026-02-17 | Tambah regression test untuk CSRF, XSS escaping, numeric parsing anggaran, dan guard expired-user POST | - | DONE |

---

## Checklist Sign-off

- [x] Create flow OK
- [x] Edit flow OK
- [x] Validation complete
- [x] XSS protection OK
- [x] CSRF OK
- [x] Authorization OK
- [ ] Reviewer sign-off
