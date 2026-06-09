# R6.2 - Review AHSP Database (Browse & Search)

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

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
| TC-1 | Browse semua AHSP | Paginated list | `[ ]` |
| TC-2 | Full-text search | Relevant results | `[ ]` |
| TC-3 | Filter by klasifikasi | Results filtered | `[ ]` |
| TC-4 | Filter by sub_klasifikasi | Results filtered | `[ ]` |
| TC-5 | View AHSP detail | Rincian TK/BHN/ALT shown | `[ ]` |
| TC-6 | Search performance | < 500ms response | `[ ]` |
| TC-7 | Empty search results | "Tidak ditemukan" message | `[ ]` |
| TC-8 | Special characters in search | No SQL injection, no crash | `[ ]` |
| TC-9 | Pagination navigation | Previous/Next works | `[ ]` |
| TC-10 | AHSP Stats (materialized view) | Stats accurate | `[ ]` |
| TC-11 | Cache behavior | Search results cached | `[ ]` |

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

- [ ] Browse & pagination OK
- [ ] Search functionality OK
- [ ] Performance OK
- [ ] Security (SQL injection) OK
- [ ] Reviewer sign-off
