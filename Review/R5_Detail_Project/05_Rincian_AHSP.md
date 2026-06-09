# R5.5 - Review Rincian AHSP

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/rincian-ahsp/` |
| View | `detail_project.views.rincian_ahsp_view` |
| Template | `detail_project/templates/detail_project/rincian_ahsp.html` |
| JS | `rincian_ahsp.js`, `detail_ahsp_gabungan.js` |

### API Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `api/project/<id>/detail-ahsp/<pekerjaan_id>/` | Get AHSP detail |
| POST | `api/project/<id>/detail-ahsp/<pekerjaan_id>/save/` | Save AHSP |
| POST | `api/project/<id>/detail-ahsp/<pekerjaan_id>/reset-to-ref/` | Reset ke referensi |
| POST | `api/project/<id>/detail-ahsp/save/` | Save gabungan |
| GET | `api/project/<id>/pekerjaan/<id>/bundle/<bid>/expansion/` | Bundle expansion |
| GET | `api/project/<id>/search-ahsp/` | Search AHSP (autocomplete) |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Load AHSP detail per pekerjaan | Rincian TK/BHN/ALT tampil | `[ ]` |
| TC-2 | Edit koefisien item | Nilai updated, total recalculated | `[ ]` |
| TC-3 | Tambah item baru ke AHSP | Item added | `[ ]` |
| TC-4 | Hapus item dari AHSP | Item removed | `[ ]` |
| TC-5 | Reset ke referensi | Data kembali ke AHSP SNI | `[ ]` |
| TC-6 | Bundle expansion | Sub-AHSP ter-expand | `[ ]` |
| TC-7 | Search AHSP (autocomplete) | Results accurate | `[ ]` |
| TC-8 | Save gabungan (multi-pekerjaan) | Batch save works | `[ ]` |
| TC-9 | Kalkulasi harga satuan | koefisien × harga benar | `[ ]` |
| TC-10 | Source type: Reference vs Custom | Visual distinction | `[ ]` |
| TC-11 | Modified-Reference indicator | Perubahan ditandai | `[ ]` |
| TC-12 | IDOR protection | Owner check | `[ ]` |

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

- [ ] AHSP CRUD OK
- [ ] Calculation correct
- [ ] Reference system OK
- [ ] Bundle expansion OK
- [ ] Security OK
- [ ] Reviewer sign-off
