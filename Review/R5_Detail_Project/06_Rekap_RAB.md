# R5.6 - Review Rekap RAB

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/rekap-rab/` |
| View | `detail_project.views.rekap_rab_view` |
| Template | `detail_project/templates/detail_project/rekap_rab.html` |
| JS | `rekap_rab.js` |

### API & Export Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `api/project/<id>/rekap/` | Get rekap data |
| GET | `api/project/<id>/export/rekap-rab/csv/` | Export CSV |
| GET | `api/project/<id>/export/rekap-rab/pdf/` | Export PDF |
| GET | `api/project/<id>/export/rekap-rab/word/` | Export Word |
| GET | `api/project/<id>/export/rekap-rab/xlsx/` | Export Excel |
| GET | `api/project/<id>/export/rekap-rab/json/` | Export JSON |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Rekap RAB tampil | Summary per klasifikasi/sub | `[ ]` |
| TC-2 | Total RAB benar | Sum semua pekerjaan correct | `[ ]` |
| TC-3 | Harga satuan × volume = subtotal | Kalkulasi akurat | `[ ]` |
| TC-4 | Markup/profit calculation | Percentage applied correctly | `[ ]` |
| TC-5 | PPN calculation | 11% (or configured %) correct | `[ ]` |
| TC-6 | Grand total = subtotal + markup + PPN | Sum correct | `[ ]` |
| TC-7 | Export CSV | Data complete, format correct | `[ ]` |
| TC-8 | Export PDF | Layout proper, data correct | `[ ]` |
| TC-9 | Export Word | Document formatted | `[ ]` |
| TC-10 | Export Excel | Cells & formulas correct | `[ ]` |
| TC-11 | Export entitlement (PRO check) | Gating enforced | `[ ]` |
| TC-12 | Empty project rekap | Empty state handled | `[ ]` |
| TC-13 | Numeric formatting (Rp) | Currency format consistent | `[ ]` |
| TC-14 | Print view | Print CSS applied | `[ ]` |

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

- [ ] Calculation accuracy
- [ ] All export formats OK
- [ ] Entitlement gating OK
- [ ] Print layout OK
- [ ] Reviewer sign-off
