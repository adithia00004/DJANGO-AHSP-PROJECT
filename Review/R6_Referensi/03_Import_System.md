# R6.3 - Review Import System (3-Tier)

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| Views | `referensi/views/import_views.py` (~104KB) |
| URLs | `/referensi/import/`, `/referensi/import/pdf/`, `/referensi/import/excel/` |
| Middleware | `ImportRateLimitMiddleware` |
| Staging Model | `AHSPImportStaging` |

### 3-Tier Import Flow

```
1. Upload (PDF/Excel) → 2. Validate/Clean → 3. Staging → 4. Commit to DB
```

---

## Audit Fungsional

### Tier 1: Upload & Convert

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Upload valid Excel (.xlsx) | File accepted | `[ ]` |
| TC-2 | Upload valid PDF | PDF → Excel conversion | `[ ]` |
| TC-3 | Upload invalid file format | Error message | `[ ]` |
| TC-4 | Upload oversized file | Size limit enforced | `[ ]` |
| TC-5 | Upload malicious file (zip bomb, etc) | Rejected | `[ ]` |
| TC-6 | Rate limiting | Too many imports blocked | `[ ]` |

### Tier 2: Validation & Cleaning

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-7 | Validate Excel structure | Column mapping verified | `[ ]` |
| TC-8 | Validate data types | Numeric, string checks | `[ ]` |
| TC-9 | Validation report | Detailed error report | `[ ]` |
| TC-10 | Clean import (auto-fix) | Minor issues auto-corrected | `[ ]` |
| TC-11 | Duplicate AHSP detection | Duplicates flagged | `[ ]` |

### Tier 3: Staging & Commit

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-12 | Data goes to staging table | AHSPImportStaging populated | `[ ]` |
| TC-13 | Staging review UI | User can review before commit | `[ ]` |
| TC-14 | Staging clear | All staging data removed | `[ ]` |
| TC-15 | Staging commit | Data moved to production tables | `[ ]` |
| TC-16 | Partial commit (select items) | Only selected items committed | `[ ]` |
| TC-17 | Commit rollback on error | Transaction rollback | `[ ]` |

### Security

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-18 | Excel formula injection | Formulas not executed | `[ ]` |
| TC-19 | XSS in imported data | Data sanitized | `[ ]` |
| TC-20 | Access control | Only portal admins | `[ ]` |

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

- [ ] Upload validation OK
- [ ] PDF conversion OK
- [ ] Validation reporting OK
- [ ] Staging workflow OK
- [ ] Commit transaction safe
- [ ] Security OK
- [ ] Rate limiting OK
- [ ] Reviewer sign-off
