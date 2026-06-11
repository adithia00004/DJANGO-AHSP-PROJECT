# R5.4 - Review Harga Items

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/harga-items/` |
| View | `detail_project.views.harga_items_view` |
| Template | `detail_project/templates/detail_project/harga_items.html` |
| JS | `harga_items.js`, `harga_numeric_patch.js` |
| CSS | `harga_items.css` |

### API Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| POST | `api/project/<id>/harga-items/save/` | Save harga |
| GET | `api/project/<id>/harga-items/list/` | List harga |
| GET | `api/project/<id>/orphaned-items/` | List orphans |
| POST | `api/project/<id>/orphaned-items/cleanup/` | Cleanup orphans |
| GET | `api/project/<id>/conversion-profiles/` | Conversion profiles |
| POST | `api/project/<id>/conversion-profile/save/` | Save profile |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | List semua harga items | Grouped by kategori (TK/BHN/ALT) | `[ ]` |
| TC-2 | Edit harga satuan | Nilai updated | `[ ]` |
| TC-3 | Harga = 0 | Diterima | `[ ]` |
| TC-4 | Harga negatif | Validation error | `[ ]` |
| TC-5 | Decimal precision | Konsisten (Rp) | `[ ]` |
| TC-6 | Numeric formatting (thousand separator) | Display format benar | `[ ]` |
| TC-7 | Orphaned items detection | Orphans listed | `[ ]` |
| TC-8 | Orphan cleanup | Items removed | `[ ]` |
| TC-9 | Conversion profiles CRUD | Profile saved/loaded | `[ ]` |
| TC-10 | Harga propagation ke RAB | Rekap RAB updated | `[ ]` |
| TC-11 | IDOR protection | Owner check | `[ ]` |
| TC-12 | XSS pada nama item | Sanitized | `[ ]` |

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

- [ ] Harga CRUD OK
- [ ] Numeric handling OK
- [ ] Orphan management OK
- [ ] Propagation to RAB OK
- [ ] Security OK
- [ ] Reviewer sign-off
