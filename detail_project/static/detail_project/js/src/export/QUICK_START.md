# Quick Start Guide - Export System

**5-minute guide untuk testing export system yang baru diimplementasikan**

---

## 1️⃣ Run Tests (Browser - Recommended)

### Step 1: Start Server

```bash
# Navigate ke export directory
cd "d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\src\export"

# Start development server (Python 3)
python -m http.server 8000
```

### Step 2: Open Test Runner

Buka browser dan navigasi ke:
```
http://localhost:8000/test/test-runner.html
```

### Step 3: Run Tests

Click salah satu tombol:
- **"▶️ Run All Tests"** - Full test suite (27 tests, ~15-20 detik)
- **"⚡ Quick Tests"** - Unit tests only (15 tests, ~5-10 detik)
- **"📦 Unit Tests"** - Core renderers + generators
- **"🔗 Integration Tests"** - E2E workflows + edge cases

### Expected Results

```
✅ Total Tests: 27
✅ Passed: 27 (100%)
❌ Failed: 0 (0%)
⏭️ Skipped: 0 (0%)
⏱️ Duration: ~15-20s
```

**Screenshot:**
![Test Runner](https://placeholder.com/test-runner-screenshot.png)

---

## 2️⃣ Test Export Manually (Browser Console)

### Step 1: Import Modules

Buka browser console (F12) di halaman test runner dan jalankan:

```javascript
// Import sample state
import { smallState } from './fixtures/sample-state.js';

// Import export coordinator
import { exportReport, EXPORT_CONFIG } from '../export-coordinator.js';
```

### Step 2: Test CSV Export

```javascript
// Export Rekap Report as CSV
const result = await exportReport({
  reportType: EXPORT_CONFIG.reportTypes.REKAP,
  format: EXPORT_CONFIG.formats.CSV,
  state: smallState,
  autoDownload: true // Will trigger download
});

console.log('Export complete:', result.metadata);
// File "laporan_rekap.csv" should download automatically
```

### Step 3: Test Excel Export

```javascript
// Export Rekap Report as Excel
const result = await exportReport({
  reportType: EXPORT_CONFIG.reportTypes.REKAP,
  format: EXPORT_CONFIG.formats.EXCEL,
  state: smallState,
  autoDownload: true
});

console.log('Export complete:', result.metadata);
// File "laporan_rekap.xlsx" should download automatically
```

### Step 4: Test Monthly Report

```javascript
// Export Monthly Report (M2) as CSV
const result = await exportReport({
  reportType: EXPORT_CONFIG.reportTypes.MONTHLY,
  format: EXPORT_CONFIG.formats.CSV,
  state: smallState,
  month: 2, // M2 = W1-W8
  autoDownload: true
});

console.log('Export complete:', result.metadata);
// File "laporan_bulanan_M2.csv" should download
```

---

## 3️⃣ Verify Downloaded Files

### CSV File (Excel Windows)

1. Open dengan Microsoft Excel
2. File → Open → Browse
3. Pilih downloaded `.csv` file
4. Excel akan otomatis detect delimiter (semicolon) dan UTF-8 encoding
5. Verify:
   - ✅ Hierarchy indentation correct
   - ✅ Week columns displayed correctly
   - ✅ Progress percentages correct
   - ✅ No encoding issues (Indonesian characters display correctly)

### Excel File (.xlsx)

1. Open dengan Microsoft Excel
2. Double-click downloaded `.xlsx` file
3. Verify sheets:
   - **Sheet "Gantt Planned"** - Timeline chart planned progress
   - **Sheet "Gantt Actual"** - Timeline chart actual progress
   - **Sheet "Kurva S"** - Cumulative progress chart
   - **Sheet "Data"** - Raw data table
4. Verify charts:
   - ✅ Images display correctly
   - ✅ High quality (not blurry)
   - ✅ Colors: Planned = cyan, Actual = yellow

---

## 4️⃣ Test Different Datasets

### Small Dataset (Quick Test)

```javascript
import { smallState } from './fixtures/sample-state.js';

await exportReport({
  reportType: 'rekap',
  format: 'csv',
  state: smallState, // 10 rows, 12 weeks
  autoDownload: true
});
// Expected duration: < 2s
```

### Complete Dataset (Default)

```javascript
import { completeState } from './fixtures/sample-state.js';

await exportReport({
  reportType: 'rekap',
  format: 'xlsx',
  state: completeState, // 30 rows, 26 weeks
  autoDownload: true
});
// Expected duration: < 8s
```

### Large Dataset (Performance Test)

```javascript
import { largeState } from './fixtures/sample-state.js';

await exportReport({
  reportType: 'rekap',
  format: 'csv',
  state: largeState, // 100 rows, 52 weeks
  autoDownload: true
});
// Expected duration: < 15s
// Warning may appear if > 100 pages
```

---

## 5️⃣ Test Edge Cases

### Minimal State (1 row, 1 week)

```javascript
import { minimalState } from './fixtures/sample-state.js';

await exportReport({
  reportType: 'rekap',
  format: 'csv',
  state: minimalState,
  autoDownload: true
});
// Should handle gracefully without errors
```

### Planned Only (No Actual Progress)

```javascript
import { plannedOnlyState } from './fixtures/sample-state.js';

await exportReport({
  reportType: 'rekap',
  format: 'xlsx',
  state: plannedOnlyState,
  autoDownload: true
});
// Actual bars should be empty/missing
```

### With Gaps (Segmented Bars)

```javascript
import { withGapsState } from './fixtures/sample-state.js';

await exportReport({
  reportType: 'rekap',
  format: 'xlsx',
  state: withGapsState,
  autoDownload: true
});
// Gantt bars should have gaps (no progress in some weeks)
```

---

## 6️⃣ Validate Request Before Export

```javascript
import { validateExportRequest } from '../export-coordinator.js';

// Valid request
const validation = validateExportRequest({
  reportType: 'rekap',
  format: 'pdf',
  state: completeState
});

console.log(validation);
// { valid: true, errors: [] }

// Invalid request
const badValidation = validateExportRequest({
  reportType: 'invalid',
  format: 'pdf',
  state: null
});

console.log(badValidation);
// { valid: false, errors: ['Invalid reportType...', 'state is required'] }
```

---

## 7️⃣ Estimate Page Count

```javascript
import { estimateExportSize } from '../export-coordinator.js';

const estimate = estimateExportSize(completeState, 'rekap');

console.log(estimate);
// {
//   rowPages: 2,
//   timePages: 2,
//   totalPages: 4,
//   rowsPerPage: 20,
//   colsPerPage: 15
// }

if (estimate.totalPages > 100) {
  console.warn('Large export detected! This will generate', estimate.totalPages, 'pages');
}
```

---

## 8️⃣ Test with Custom Layout

```javascript
await exportReport({
  reportType: 'rekap',
  format: 'csv',
  state: completeState,
  options: {
    layout: {
      pageSize: 'A3',          // Override from A4
      labelWidthPx: 700,       // Wider label column
      rowHeightPx: 32,         // Taller rows
      plannedColor: '#0000FF', // Blue instead of cyan
      actualColor: '#FF0000',  // Red instead of yellow
      timezone: 'UTC'          // Different timezone
    }
  },
  autoDownload: true
});
```

---

## 9️⃣ Troubleshooting

### Issue: Tests Not Loading

**Symptom:** Test runner shows blank page atau "Module not found"

**Solution:**
1. Verify server is running: `python -m http.server 8000`
2. Check URL: `http://localhost:8000/test/test-runner.html` (not `file:///...`)
3. Check browser console for errors (F12)
4. Ensure all files exist in correct directory structure

### Issue: CORS Errors

**Symptom:** "Access to fetch... has been blocked by CORS policy"

**Solution:**
- Use development server (python/node) instead of opening HTML file directly
- ES6 modules require HTTP/HTTPS protocol (not `file://`)

### Issue: Font Not Loading

**Symptom:** Text rendering looks incorrect or misaligned

**Solution:**
```javascript
// Wait for fonts to load
await document.fonts.ready;
console.log('Fonts loaded:', document.fonts.size);
```

### Issue: Download Not Triggered

**Symptom:** Export completes but no file downloads

**Solution:**
```javascript
// Manual download
const result = await exportReport({
  reportType: 'rekap',
  format: 'csv',
  state: smallState,
  autoDownload: false // Don't auto-download
});

// Download manually
import { downloadCSV } from '../generators/csv-generator.js';
downloadCSV(result.blob, 'my_custom_filename');
```

### Issue: Memory Error on Large Dataset

**Symptom:** "Out of memory" or browser crash

**Solution:**
1. Reduce dataset size
2. Use CSV format (lighter than Excel)
3. Close other browser tabs
4. Increase Chrome memory limit: `chrome.exe --js-flags="--max-old-space-size=4096"`

---

## 🔟 Check System Info

```javascript
import { getExportSystemInfo } from '../index.js';

const info = getExportSystemInfo();

console.log(info);
// {
//   version: '1.0.0',
//   status: {
//     rekapReport: 'fully_implemented',
//     monthlyReport: 'partially_implemented',
//     weeklyReport: 'infrastructure_only'
//   },
//   supportedFormats: ['pdf', 'word', 'xlsx', 'csv'],
//   supportedReportTypes: ['rekap', 'monthly', 'weekly'],
//   dependencies: {
//     uplot: '^1.6.24',
//     exceljs: '^4.4.0'
//   }
// }
```

---

## ✅ Success Checklist

After running all tests, verify:

- [ ] Browser test runner displays 27/27 tests passing
- [ ] CSV file downloads and opens correctly in Excel
- [ ] Excel file contains multiple sheets with charts
- [ ] Charts display correctly (not blurry, correct colors)
- [ ] Hierarchy indentation is correct
- [ ] Progress percentages match test data
- [ ] No console errors (F12)
- [ ] Large dataset (100 rows, 52 weeks) exports without crashing
- [ ] Edge cases (minimal, planned-only, with-gaps) handled correctly

---

## 📚 Further Reading

- [export/README.md](README.md) - Complete export system documentation
- [test/README.md](test/README.md) - Test suite documentation
- [EXPORT_IMPLEMENTATION_ROADMAP.md](../../../../EXPORT_IMPLEMENTATION_ROADMAP.md) - Roadmap with progress tracking
- [EXPORT_SYSTEM_PHASE_1-2_COMPLETE.md](../../../../EXPORT_SYSTEM_PHASE_1-2_COMPLETE.md) - Phase 1-2 completion summary

---

## 🎯 Next Steps

After verifying Phase 1-2 is working correctly:

1. **Phase 3.1** - Implement backend API endpoints (`/api/export/init`, `upload-pages`, `finalize`)
2. **Phase 3.2** - Implement backend PDF/Word generation
3. **Phase 5.1** - UI integration (export button di Jadwal Pekerjaan page)
4. **Phase 4.1** - Complete Laporan Bulanan specification
5. **Phase 4.2** - Complete Laporan Mingguan specification

---

**Questions?** Check documentation atau ask development team.

**Last Updated:** 2025-12-16
