# R5.13 - Review Copy / Import / Backup System

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| Service | `detail_project/services.py` (DeepCopyService) |
| Tokenizer | `detail_project/formula_tokenizer.py` |

### API Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| POST | `api/project/<id>/deep-copy/` | Deep copy project |
| POST | `api/project/<id>/batch-copy/` | Batch copy projects |
| GET | `api/project/<id>/export/full-backup/json/` | Full JSON backup |
| POST | `api/project/import/json/` | Import from JSON |

---

## Audit Fungsional

### Deep Copy

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Copy project → semua data ter-copy | Complete copy | `[ ]` |
| TC-2 | Parameter IDs regenerated (Opsi B) | New bp_N / cp_N | `[ ]` |
| TC-3 | Formula expressions remapped | Old → new param IDs | `[ ]` |
| TC-4 | VolumeFormulaState ter-copy | Formula state included | `[ ]` |
| TC-5 | Harga items ter-copy | All prices copied | `[ ]` |
| TC-6 | Tahapan/schedule ter-copy | Schedule included | `[ ]` |
| TC-7 | Copy performance (large project) | Reasonable time | `[ ]` |
| TC-8 | Batch copy multiple projects | All copied | `[ ]` |

### JSON Backup/Import

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-9 | Export full backup JSON | Complete data dump | `[ ]` |
| TC-10 | Import valid JSON | Project recreated | `[ ]` |
| TC-11 | Import JSON - schema v3.0 | Version handled | `[ ]` |
| TC-12 | Import JSON - invalid format | Error message | `[ ]` |
| TC-13 | Import JSON - malicious content | Sanitized / rejected | `[ ]` |
| TC-14 | Import JSON - parameter remap | IDs regenerated | `[ ]` |
| TC-15 | Round-trip: export → import | Data identical | `[ ]` |

### Security

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-16 | IDOR on copy endpoint | Owner check | `[ ]` |
| TC-17 | JSON import XSS payload | Sanitized | `[ ]` |
| TC-18 | Large JSON import (DoS) | Size limit enforced | `[ ]` |

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

- [ ] Deep copy complete
- [ ] Parameter remap correct
- [ ] Formula remap correct
- [ ] JSON backup round-trip OK
- [ ] Security OK
- [ ] Performance OK
- [ ] Reviewer sign-off
