# R6.4 - Review Staging Workflow

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URLs | `/referensi/staging/`, `/referensi/staging/clear/`, `/referensi/staging/commit/` |
| Template | `referensi/templates/referensi/import_staging.html` |
| Model | `AHSPImportStaging` |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Staging page menampilkan data pending | Data listed correctly | `[ ]` |
| TC-2 | Review individual items | Detail view per item | `[ ]` |
| TC-3 | Accept/reject per item | Item status updated | `[ ]` |
| TC-4 | Clear all staging | All data removed | `[ ]` |
| TC-5 | Commit selected → DB | Atomic transaction | `[ ]` |
| TC-6 | Commit with validation errors | Errors shown, no partial | `[ ]` |
| TC-7 | Empty staging state | "Tidak ada data" message | `[ ]` |
| TC-8 | Concurrent staging sessions | Isolated per user/session | `[ ]` |

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

- [ ] Staging display OK
- [ ] Commit transaction OK
- [ ] Clear functionality OK
- [ ] Concurrent safety OK
- [ ] Reviewer sign-off
