# R6.2 - Review AHSP Database (Browse & Search)

**Status:** `[~]` AUDIT STATIK SELESAI (2026-06-24) — ✅ PASS; N-2 (LOW) ditunda
**Terakhir diperbarui:** 2026-06-24

> **Metode:** telaah kode statis (read-only), bukan UAT runtime. Legend: ✅ = terverifikasi via inspeksi kode · ⏳UAT = perlu runtime. Ringkasan: [00_Audit_Summary_20260624.md](00_Audit_Summary_20260624.md).

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/referensi/database/` (or `/referensi/ahsp-database/`) |
| Template | `referensi/templates/referensi/ahsp_database.html` |
| JS | `ahsp_database.js`, `ahsp_database_v2.js`, `ahsp_database_api.js` |
| Model | `AHSPReferensi`, `RincianReferensi` |
| Search | PostgreSQL full-text search vector |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Browse semua AHSP | Paginated list | ⏳UAT |
| TC-2 | Full-text search | Relevant results | ⏳UAT |
| TC-3 | Filter by klasifikasi | Results filtered | ⏳UAT |
| TC-4 | Filter by sub_klasifikasi | Results filtered | ⏳UAT |
| TC-5 | View AHSP detail | Rincian TK/BHN/ALT shown | ⏳UAT |
| TC-6 | Search performance | < 500ms response | ⏳UAT |
| TC-7 | Empty search results | "Tidak ditemukan" message | ⏳UAT |
| TC-8 | Special characters in search | No SQL injection, no crash | ✅ ORM/`SearchQuery` parameterized (tak ada raw SQL string-format) |
| TC-9 | Pagination navigation | Previous/Next works | ⏳UAT |
| TC-10 | AHSP Stats (materialized view) | Stats accurate | ✅ `AHSPStats` `managed=False` read-only (C-5) |
| TC-11 | Cache behavior | Search results cached | ✅ invalidasi via signal; N-2 (rebuild per `bulk_create`) ditunda |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| N-2 | 🟡 LOW | `bulk_create` memanggil `rebuild_search_cache()` tiap panggilan (rebuild berulang saat chunked import) + `simple_history` kemungkinan tak melacak bulk-import. | Import besar multi-chunk. | `referensi/models.py:16-20`. **DITUNDA** (butuh desain, sesi terpisah). |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| N-2 | Rebuild cache sekali di akhir import (suppress-signal seperti `staging_commit`); evaluasi `bulk_create` history bila audit-trail import diperlukan. | Rendah | Sedang (desain) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| - | - | N-2 ditunda ke sesi terpisah (kesepakatan owner). | - | DITUNDA |

---

## Checklist Sign-off

- [ ] Browse & pagination OK (⏳UAT)
- [ ] Search functionality OK (⏳UAT)
- [ ] Performance OK (⏳UAT; N-2 terkait perf cache)
- [x] Security (SQL injection) OK (kode — ORM/parameterized, TC-8)
- [ ] Reviewer sign-off
