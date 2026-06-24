# R6.3 - Review Import System (3-Tier)

**Status:** `[~]` AUDIT STATIK SELESAI (2026-06-24) — ✅ PASS; N-7/N-5/N-1 FIXED
**Terakhir diperbarui:** 2026-06-24

> **Metode:** telaah kode statis (read-only), bukan UAT runtime. Legend: ✅ = terverifikasi via inspeksi kode · ⏳UAT = perlu runtime. Ringkasan: [00_Audit_Summary_20260624.md](00_Audit_Summary_20260624.md). Permukaan risiko utama app = pipeline ini; validasi input (C-2) sangat matang.

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
| TC-1 | Upload valid Excel (.xlsx) | File accepted | ⏳UAT |
| TC-2 | Upload valid PDF | PDF → Excel conversion | ⏳UAT |
| TC-3 | Upload invalid file format | Error message | ✅ `validate_extension` + `validate_mime_type` (C-2) |
| TC-4 | Upload oversized file | Size limit enforced | ✅ `validate_file_size` 50MB (C-2) |
| TC-5 | Upload malicious file (zip bomb, etc) | Rejected | ✅ `validate_zip_bomb` (rasio + uncompressed 500MB) (C-2) |
| TC-6 | Rate limiting | Too many imports blocked | ✅ **N-7 FIXED** — middleware kini cakup `/referensi/import/` (write-only) |

### Tier 2: Validation & Cleaning

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-7 | Validate Excel structure | Column mapping verified | ⏳UAT |
| TC-8 | Validate data types | Numeric, string checks | ⏳UAT |
| TC-9 | Validation report | Detailed error report | ⏳UAT (N-5: pesan error tak bocor `str(e)` lagi) |
| TC-10 | Clean import (auto-fix) | Minor issues auto-corrected | ⏳UAT |
| TC-11 | Duplicate AHSP detection | Duplicates flagged | ✅ `_commit_preflight` (ABORT_DUPLICATE) + unik `(sumber,kode_ahsp)` |

### Tier 3: Staging & Commit

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-12 | Data goes to staging table | AHSPImportStaging populated | ✅ per-user scoped (C-3) — detail di R6.4 |
| TC-13 | Staging review UI | User can review before commit | ⏳UAT |
| TC-14 | Staging clear | All staging data removed | ✅ `staging_clear` (POST, user-scoped) |
| TC-15 | Staging commit | Data moved to production tables | ✅ `staging_commit` atomic + `select_for_update` (C-3) |
| TC-16 | Partial commit (select items) | Only selected items committed | ⏳UAT |
| TC-17 | Commit rollback on error | Transaction rollback | ✅ **N-4 FIXED** — `except` set batch FAILED + rollback (R6.4) |

### Security

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-18 | Excel formula injection | Formulas not executed | ✅ `validate_content_security` (blokir WEBSERVICE/IMPORTXML/HYPERLINK/EXEC/SYSTEM/CALL…) (C-2) |
| TC-19 | XSS in imported data | Data sanitized | ✅ auto-escape Django + toolkit `safe_display` (C-4) |
| TC-20 | Access control | Only portal admins | ✅ `@user_passes_test(is_admin=has_referensi_import_access)` + `@require_POST` (C-1) |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| N-7 | 🟠→🟢 MED FIXED | `IMPORT_RATE_LIMIT_PATHS` legacy tak cocok endpoint import nyata → import tak ter-rate-limit. | Spam POST `/referensi/import/...` | `config/settings/base.py`; tes `ImportRateLimitMiddlewareTests` |
| N-5 | 🟡→🟢 LOW FIXED | `validate_content_security` membocorkan `str(e)` ke user saat gagal scan. | File yang bikin openpyxl error | `referensi/validators.py`; tes `ContentSecurityErrorLeakTests` |
| N-1 | 🟡→🟢 LOW FIXED | Route `debug/clear-data/` terdaftar di URL utama (view sudah DEBUG+superuser-only). | — | `referensi/urls.py`; tes `DebugClearDataRouteGatingTests` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| - | Lakukan UAT runtime untuk TC upload/convert/validate/report (⏳UAT). | Sedang | Sedang |
| - | Parser internal (`ahsp_parser`/`import_writer`/`import_schema`/`import_repair`) = korektnes parsing; keamanan input sudah ditutup C-2. | Rendah | — |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| N-7 | 2026-06-24 | Rate-limit cakup `/referensi/import/` (write-only) + test settings anti-polusi | `83f45f64`, `7aad846e` | ✅ DONE |
| N-5 | 2026-06-24 | Hapus `str(e)` dari pesan validator → `logger.warning` | `b23c518b` | ✅ DONE |
| N-1 | 2026-06-24 | Route clear-data hanya `if settings.DEBUG` + guard template | (pending commit) | ✅ DONE (kode) |

---

## Checklist Sign-off

- [x] Upload validation OK (kode — C-2: size/ext/mime/zip-bomb/formula/row)
- [ ] PDF conversion OK (⏳UAT)
- [ ] Validation reporting OK (⏳UAT; N-5 fixed)
- [x] Staging workflow OK (kode — C-3; detail R6.4)
- [x] Commit transaction safe (kode — atomic + lock + N-4 rollback)
- [x] Security OK (kode — formula-injection, XSS, access control)
- [x] Rate limiting OK (kode — N-7 fixed)
- [ ] Reviewer sign-off
