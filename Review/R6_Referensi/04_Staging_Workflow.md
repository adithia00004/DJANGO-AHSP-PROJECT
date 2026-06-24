# R6.4 - Review Staging Workflow

**Status:** `[~]` AUDIT STATIK SELESAI (2026-06-24) — ✅ PASS; N-4 FIXED
**Terakhir diperbarui:** 2026-06-24

> **Metode:** telaah kode statis (read-only), bukan UAT runtime. Legend: ✅ = terverifikasi via inspeksi kode · ⏳UAT = perlu runtime. Ringkasan: [00_Audit_Summary_20260624.md](00_Audit_Summary_20260624.md). `staging_commit` = jalur tulis paling kritikal; terverifikasi atomic + signal-safe.

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
| TC-1 | Staging page menampilkan data pending | Data listed correctly | ⏳UAT |
| TC-2 | Review individual items | Detail view per item | ⏳UAT |
| TC-3 | Accept/reject per item | Item status updated | ⏳UAT |
| TC-4 | Clear all staging | All data removed | ✅ `staging_clear` (POST, user-scoped) |
| TC-5 | Commit selected → DB | Atomic transaction | ✅ `transaction.atomic` + `select_for_update` (C-3) |
| TC-6 | Commit with validation errors | Errors shown, no partial | ✅ **N-4 FIXED** — `except` set batch FAILED + rollback + pesan ramah |
| TC-7 | Empty staging state | "Tidak ada data" message | ⏳UAT |
| TC-8 | Concurrent staging sessions | Isolated per user/session | ✅ `AHSPImportStaging.user` FK + queryset user-scoped (C-3) |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| N-4 | 🟡→🟢 LOW FIXED | `staging_commit` saat exception → 500 tanpa set batch `FAILED`/pesan ramah. | Paksa error mid-commit | `referensi/views/import_views.py`; tes `test_commit_failure_marks_batch_failed_and_rolls_back` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| - | UAT runtime: tampilan staging, review/accept-reject per item, empty state. | Rendah | Kecil |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| N-4 | 2026-06-24 | `except` → batch FAILED + rollback + `messages.error` + redirect staging (signal reconnect via `finally`) | `f527bbb0` | ✅ DONE |

---

## Checklist Sign-off

- [ ] Staging display OK (⏳UAT)
- [x] Commit transaction OK (kode — atomic + lock + N-4 rollback)
- [x] Clear functionality OK (kode — user-scoped)
- [x] Concurrent safety OK (kode — per-user isolation + `select_for_update`)
- [ ] Reviewer sign-off
