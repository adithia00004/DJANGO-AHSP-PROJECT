# R4.5 - Review Project Duplicate

**Status:** `[x]` PASS (functional)
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/dashboard/project/<pk>/duplicate/` |
| View | `dashboard.views.project_duplicate` |
| Template | `dashboard/templates/dashboard/project_confirm_duplicate.html` |
| Service | `detail_project.services.DeepCopyService` |
| Auth Required | Ya + subscription active |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Duplicate project -> copy terbuat | Copy baru tersimpan dan redirect ke `next` | `[x]` |
| TC-2 | Project copy punya nama berbeda | Auto-suffix `(Copy)` / increment `(Copy 2)` | `[x]` |
| TC-3 | Copy includes: Pekerjaan | Data pekerjaan ikut tercopy | `[x]` |
| TC-4 | Copy includes: Volume & Formula | Volume + formula state ikut tercopy | `[x]` |
| TC-5 | Copy includes: AHSP detail | Detail AHSP ikut tercopy via deep-copy pipeline | `[x]` |
| TC-6 | Copy includes: Harga items | Harga item ikut tercopy via deep-copy pipeline | `[x]` |
| TC-7 | Copy includes: Parameters | Opaque base parameter diregenerasi | `[x]` |
| TC-8 | Copy includes: Computed params | Opaque computed parameter diregenerasi | `[x]` |
| TC-9 | Formula expressions remapped | Formula `bp_*/cp_*` ter-remap ke namespace baru | `[x]` |
| TC-10 | Non-owner duplicate | 403/404 | `[x]` |
| TC-11 | Expired user duplicate | Blocked oleh middleware (redirect `/pricing/`) | `[x]` |
| TC-12 | Large project duplicate performance | Waktu proses masih wajar | `[~]` (perlu benchmark staging) |

Evidence test:
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_duplicate_deep_copy_preserves_related_data_and_next`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_duplicate_get_prefills_incremented_copy_name`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_duplicate_validation_errors_rendered`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_expired_owner_blocked_on_project_duplicate_post`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_non_owner_blocked_from_project_pages`
- `detail_project.tests_volume_export_adapter.DeepCopyVolumeFormulaStateTests.test_copy_project_also_copies_and_remaps_volume_formula_state`

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Tidak ada temuan blocker terbuka | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| REC-1 | Tambah benchmark test/observability untuk deep-copy skala besar (durasi, query count, memory) di staging | P2 | Medium |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Refactor endpoint duplicate dashboard agar memakai `DeepCopyService` (bukan shallow `ProjectForm.save`) | - | DONE |
| 2 | 2026-02-17 | Perbaiki template duplicate: hapus field legacy `tahun_project`, sinkron timeline fields, tambah error summary + preserve `next` | - | DONE |
| 3 | 2026-02-17 | Tambah smoke tests duplicate (success, validation, non-owner, expired-user, name increment) | - | DONE |

---

## Checklist Sign-off

- [x] Deep copy completeness
- [x] Parameter regeneration (Opsi B)
- [x] Formula remapping correct
- [x] Authorization OK
- [ ] Performance benchmark staging
- [ ] Reviewer sign-off
