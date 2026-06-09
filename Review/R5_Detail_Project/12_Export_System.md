# R5.12 - Review Export System (Multi-format)

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| JS | `export/ExportManager.js`, `export/ExcelExporter.js` |
| Generators | `src/export/generators/csv-generator.js`, `excel-generator.js`, `pdf-generator.js`, `word-generator.js` |
| Backend | `detail_project/exports/excel_exporter.py`, `volume_pekerjaan_adapter.py` |
| Batch Export | `views_export.py` (init → upload_pages → finalize → download) |

### Export Endpoints (per report type)

| Report | Formats | PRO Required |
|--------|---------|-------------|
| Rekap RAB | CSV, PDF, Word, Excel, JSON | Excel/Word: Yes |
| Rekap Kebutuhan | PDF, Word, Excel, JSON | Excel/Word: Yes |
| Volume Pekerjaan | Excel, PDF, Word | Excel/Word: Yes |
| Rincian RAB | CSV | No |
| List Pekerjaan | JSON | No |
| Full Backup | JSON | No |

---

## Audit Fungsional

### Format-specific Tests

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | CSV export - valid data | Proper CSV format | `[ ]` |
| TC-2 | Excel export - valid data | .xlsx with correct sheets | `[ ]` |
| TC-3 | PDF export - valid data | Formatted PDF | `[ ]` |
| TC-4 | Word export - valid data | .docx formatted | `[ ]` |
| TC-5 | JSON export - valid data | Valid JSON structure | `[ ]` |

### Entitlement & Watermark

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-6 | Trial user → Excel export | Blocked | `[ ]` |
| TC-7 | Trial user → PDF export | PDF with watermark | `[ ]` |
| TC-8 | PRO user → all exports | Clean, no watermark | `[ ]` |
| TC-9 | Expired user → PDF | Watermark applied | `[ ]` |

### Batch Export

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-10 | Init batch export session | Session UUID created | `[ ]` |
| TC-11 | Upload pages sequentially | Pages stored | `[ ]` |
| TC-12 | Finalize → combined document | Single file generated | `[ ]` |
| TC-13 | Download final document | File downloaded | `[ ]` |
| TC-14 | Export status polling | Status returns correctly | `[ ]` |
| TC-15 | Session cleanup after download | Temp files removed | `[ ]` |

### Edge Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-16 | Export empty project | Handled gracefully | `[ ]` |
| TC-17 | Export very large project | Memory/performance OK | `[ ]` |
| TC-18 | Concurrent export sessions | Isolated sessions | `[ ]` |
| TC-19 | Export filename special chars | Sanitized filename | `[ ]` |
| TC-20 | Content-Disposition header | Correct for browser download | `[ ]` |

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

- [ ] All formats generate correctly
- [ ] Entitlement gating correct
- [ ] Watermark system works
- [ ] Batch export pipeline OK
- [ ] Performance OK
- [ ] Security OK
- [ ] Reviewer sign-off
