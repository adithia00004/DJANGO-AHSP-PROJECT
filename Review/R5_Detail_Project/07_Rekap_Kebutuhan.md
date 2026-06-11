# R5.7 - Review Rekap Kebutuhan

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/rekap-kebutuhan/` |
| View | `detail_project.views.rekap_kebutuhan_view` |
| Template | `detail_project/templates/detail_project/rekap_kebutuhan.html` |
| JS | `rekap_kebutuhan.js` |

### API & Export Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `api/project/<id>/rekap-kebutuhan/` | Get data |
| POST | `api/project/<id>/rekap-kebutuhan/validate/` | Validate |
| GET | `api/project/<id>/export/rekap-kebutuhan/{pdf,word,xlsx,json}/` | Exports |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Rekap kebutuhan material | Aggregated per item | `[ ]` |
| TC-2 | Rekap kebutuhan tenaga kerja | Aggregated per TK | `[ ]` |
| TC-3 | Rekap kebutuhan alat | Aggregated per alat | `[ ]` |
| TC-4 | Total quantity per item benar | Sum across pekerjaan | `[ ]` |
| TC-5 | Total biaya per item | qty × harga | `[ ]` |
| TC-6 | Validation endpoint | Detects inconsistencies | `[ ]` |
| TC-7 | Export formats (PDF, Word, Excel, JSON) | All work | `[ ]` |
| TC-8 | Empty project | Empty state | `[ ]` |
| TC-9 | Items with same name, different satuan | Grouped correctly | `[ ]` |

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

- [ ] Aggregation correct
- [ ] Exports OK
- [ ] Validation OK
- [ ] Reviewer sign-off
