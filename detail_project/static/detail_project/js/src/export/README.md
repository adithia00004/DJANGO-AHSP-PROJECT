# Export Offscreen System - Jadwal Pekerjaan

Sistem export untuk halaman Jadwal Pekerjaan menggunakan offscreen rendering (bukan screenshot).

## Arsitektur

Export system dirancang sebagai matriks **4 Format Output × 3 Jenis Laporan**:

### Format Output
1. **PDF** - Pagination tile untuk print, DPI 300
2. **Word** - Struktur dokumen dengan embedded charts, DPI 300
3. **Excel** - Multi-sheet dengan data tabel + chart images, DPI 150
4. **CSV** - Data tabel raw, UTF-8 dengan BOM untuk Excel Windows

### Jenis Laporan

#### 1. Laporan Rekap (✅ FULLY DEFINED)
Konten:
- Gantt Full Timeline - Planned
- Gantt Full Timeline - Actual
- Kurva S Weekly
- Grid View - Full Data

#### 2. Laporan Bulanan (✅ FULLY IMPLEMENTED - Phase 4)
Konten:
- ✅ Report Title: "Laporan {projectName} Bulan ke-X"
- ✅ Period Identification: Month X period (dd-mm-yyyy - dd-mm-yyyy)
- ✅ Project Identity: Name, Owner, Location, Budget
- ✅ Main Table: Pekerjaan + Total Harga + Bobot Pekerjaan (%)
- ✅ Kurva S Monthly Progressive (M1=W1-W4, M2=W1-W8, dst)
- ✅ Progress Recapitulation: Target Planned, Actual, Cumulative metrics

#### 3. Laporan Mingguan (✅ FULLY IMPLEMENTED - Phase 4)
Konten:
- ✅ Report Title: "Laporan {projectName} Minggu ke-X"
- ✅ Period Identification: Week X period (dd-mm-yyyy - dd-mm-yyyy)
- ✅ Project Identity: Name, Owner, Location, Budget
- ✅ Main Table (7 columns):
  - Pekerjaan
  - Total Harga
  - Bobot Pekerjaan (%)
  - Target Planned Minggu Ini (%)
  - Actual Minggu Ini (%)
  - Kumulatif Target (%)
  - Kumulatif Actual (%)

## Struktur Module

```
export/
├── core/                           # Core rendering engines
│   ├── kurva-s-renderer.js        # Kurva S offscreen renderer (uPlot)
│   ├── gantt-renderer.js          # Gantt offscreen renderer (Canvas 2D)
│   └── pagination-utils.js        # Pagination logic
│
├── generators/                     # Format-specific generators
│   ├── pdf-generator.js           # PDF generation (backend)
│   ├── word-generator.js          # Word generation (backend)
│   ├── excel-generator.js         # Excel file generator (ExcelJS, frontend)
│   └── csv-generator.js           # CSV generation (frontend)
│
├── reports/                        # Report type handlers
│   ├── rekap-report.js            # Laporan Rekap (FULLY IMPLEMENTED)
│   ├── monthly-report.js          # Laporan Bulanan (FULLY IMPLEMENTED - Phase 4)
│   └── weekly-report.js           # Laporan Mingguan (FULLY IMPLEMENTED - Phase 4)
│
├── export-coordinator.js          # Main export coordinator
└── README.md                      # Documentation (this file)
```

## Dependencies

### NPM Packages
```bash
npm install uplot@^1.6.24 exceljs@^4.4.0
```

### Browser Support
- Chrome/Edge >= 90
- Firefox >= 88
- Safari >= 14

## Usage

### Basic Usage

```javascript
import { exportReport, EXPORT_CONFIG } from './export/export-coordinator.js';

// Prepare application state
const state = {
  hierarchyRows: [
    { id: 1, type: 'klasifikasi', level: 0, name: 'Pekerjaan Persiapan', parentId: null },
    { id: 2, type: 'pekerjaan', level: 1, name: 'Mobilisasi', parentId: 1 },
    // ... more rows
  ],
  weekColumns: [
    { week: 1, startDate: '2025-01-06T00:00:00Z', endDate: '2025-01-12T23:59:59Z' },
    // ... more weeks
  ],
  plannedProgress: {
    2: { 1: 10, 2: 25, 3: 50 } // pekerjaan_id -> { week -> progress }
  },
  actualProgress: {
    2: { 1: 8, 2: 20, 3: 45 }
  },
  kurvaSData: [
    { week: 1, planned: 10, actual: 8 },
    { week: 2, planned: 25, actual: 20 },
    // ... more weeks
  ]
};

// Export Laporan Rekap as PDF
const result = await exportReport({
  reportType: EXPORT_CONFIG.reportTypes.REKAP,
  format: EXPORT_CONFIG.formats.PDF,
  state,
  autoDownload: true // Auto-trigger download
});

// Export Laporan Bulanan as Excel (manual download)
const monthlyResult = await exportReport({
  reportType: EXPORT_CONFIG.reportTypes.MONTHLY,
  format: EXPORT_CONFIG.formats.EXCEL,
  state,
  month: 2, // M2
  autoDownload: false // Get blob without download
});

// Manually download
import { downloadExcel } from './export/generators/excel-generator.js';
downloadExcel(monthlyResult.blob, 'laporan_bulanan_M2');
```

### Advanced Options

```javascript
// Custom layout
const result = await exportReport({
  reportType: EXPORT_CONFIG.reportTypes.REKAP,
  format: EXPORT_CONFIG.formats.PDF,
  state,
  options: {
    layout: {
      pageSize: 'A3', // Override from A4
      dpi: 300,
      labelWidthPx: 650, // Custom label width
      timezone: 'Asia/Jakarta',
      plannedColor: '#0000FF', // Custom colors
      actualColor: '#FF0000'
    }
  }
});
```

### Estimate Before Export

```javascript
import { estimateExportSize } from './export/export-coordinator.js';

const estimate = estimateExportSize(state, EXPORT_CONFIG.reportTypes.REKAP);

console.log(`Estimated pages: ${estimate.totalPages}`);
// { rowPages: 5, timePages: 2, totalPages: 10, rowsPerPage: 20, colsPerPage: 15 }

if (estimate.totalPages > 100) {
  const confirmed = confirm(`This export will generate ${estimate.totalPages} pages. Continue?`);
  if (!confirmed) return;
}
```

### Validation

```javascript
import { validateExportRequest } from './export/export-coordinator.js';

const validation = validateExportRequest({
  reportType: 'rekap',
  format: 'pdf',
  state
});

if (!validation.valid) {
  console.error('Validation errors:', validation.errors);
  // ["State validation: Row 5: missing 'name' field"]
}
```

## Configuration

### EXPORT_CONFIG

```javascript
export const EXPORT_CONFIG = {
  // Report types
  reportTypes: {
    REKAP: 'rekap',
    MONTHLY: 'monthly',
    WEEKLY: 'weekly'
  },

  // Export formats
  formats: {
    PDF: 'pdf',
    WORD: 'word',
    EXCEL: 'xlsx',
    CSV: 'csv'
  },

  // DPI settings per format
  dpi: {
    pdf: 300,    // High quality for print
    word: 300,   // High quality for print
    xlsx: 150,   // Digital display quality
    csv: 0       // Not applicable
  },

  // Layout parameters
  layout: {
    labelWidthPx: 600,
    timeColWidthPx: 70,
    rowHeightPx: 28,
    headerHeightPx: 60,
    marginMm: 20,
    fontSize: 11,
    fontFamily: 'Arial',
    backgroundColor: '#ffffff',
    gridColor: '#e0e0e0',
    textColor: '#333333',
    plannedColor: '#00CED1',  // cyan
    actualColor: '#FFD700',   // yellow
    indentPerLevel: 20,
    timezone: 'Asia/Jakarta',
    endExclusive: false       // Week endDate is inclusive (23:59:59)
  },

  // Performance limits
  limits: {
    maxCanvasSize: 16384,     // Chrome canvas dimension limit
    maxPages: 500,            // Warning threshold
    warningThreshold: 100     // Show warning jika > 100 pages
  }
};
```

## Technical Details

### Offscreen Rendering Strategy

Menggunakan **Hidden DOM Container** approach (bukan pure OffscreenCanvas):
- uPlot membutuhkan DOM element untuk initialization
- Canvas 2D API membutuhkan `document.fonts` untuk text metrics
- Container di-hide dengan `position: fixed; left: -99999px; visibility: hidden`

### DPI Strategy

**Logical Units + Scale Transform**:
```javascript
const BASE_DPI = 96;  // Browser standard
const TARGET_DPI = 300; // For PDF/Word
const SCALE = TARGET_DPI / BASE_DPI; // 3.125x

canvas.width = logicalWidth * SCALE;
ctx.scale(SCALE, SCALE);
ctx.font = '12px Arial'; // Renders 37.5px physically
```

### Memory Management

**Sequential Rendering + Batch Upload**:
- Render 1 halaman → convert to PNG → clear canvas
- Upload dalam batch (10 pages per batch)
- Proper cleanup: `chart.destroy()` + canvas reset
- Fallback `toDataURL` jika `toBlob()` gagal

### Pagination Algorithm

**Header Chain Stack by Level**:
- Handles nested hierarchy (Klasifikasi → Sub → Pekerjaan)
- Prevents orphaned headers
- Injects "(lanj.)" untuk repeated headers
- Context switch clears deeper levels

## Backend Integration

### PDF & Word (Backend Generation)

```javascript
// Single upload (< 50 pages)
POST /api/export/generate
{
  "reportType": "rekap",
  "format": "pdf",
  "attachments": [
    { "title": "Gantt W1-W12", "data_url": "data:image/png;base64,...", "format": "png" }
  ]
}

// Batch upload (>= 50 pages)
POST /api/export/init
→ { "exportId": "abc123" }

POST /api/export/upload-pages
{ "exportId": "abc123", "batchIndex": 0, "pages": [...] }

POST /api/export/finalize
{ "exportId": "abc123" }
→ { "downloadUrl": "/downloads/abc123.pdf" }
```

### Excel & CSV (Frontend Only)

Generated completely in browser using ExcelJS/Blob, no backend involvement.

## Testing

```bash
# Unit tests (to be implemented)
npm test

# Manual testing
# Open browser console and use the examples above
```

## Status

### System Completion Matrix

| Component | Status | Phase |
|-----------|--------|-------|
| **Core Renderers** | ✅ COMPLETE | Phase 1-2 |
| **Generators (All 4 Formats)** | ✅ COMPLETE | Phase 1-2 |
| **Backend Endpoints** | ✅ COMPLETE | Phase 3 |
| **Database Models** | ✅ COMPLETE | Phase 3 |
| **Laporan Rekap** | ✅ COMPLETE | Phase 1-2 |
| **Laporan Bulanan** | ✅ COMPLETE | Phase 4 |
| **Laporan Mingguan** | ✅ COMPLETE | Phase 4 |

### Export Matrix (3 Reports × 4 Formats)

| Report Type | PDF | Word | Excel | CSV |
|-------------|-----|------|-------|-----|
| **Rekap** | ✅ | ✅ | ✅ | ✅ |
| **Monthly** | ✅ | ✅ | ✅ | ✅ |
| **Weekly** | ✅ | ✅ | ✅ | ✅ |

**Total**: 12 export combinations - **ALL OPERATIONAL** ✅

### Production Status

🚀 **PRODUCTION READY**

- ✅ All 3 report types fully implemented
- ✅ All 4 export formats operational
- ✅ Backend integration complete (PDF/Word)
- ✅ Frontend generation complete (Excel/CSV)
- ✅ Batch upload system operational
- ✅ Admin interface with progress tracking
- ✅ Error handling and validation
- ✅ Comprehensive documentation

## Next Steps (Optional Enhancements)

### Testing
1. Unit tests untuk helper functions (~200 LOC)
2. Integration tests dengan real data
3. Performance benchmarking
4. Load testing untuk large datasets (>500 pages)

### Performance Optimization
1. Memoization untuk weight calculations
2. Progress bar untuk long-running exports
3. Web Worker untuk offscreen rendering
4. Canvas pooling untuk memory optimization

### Feature Enhancements
1. Report templates (custom layouts)
2. Custom date ranges
3. Chart customization options
4. Report scheduling
5. Export history tracking

## Reference

See [d:\PORTOFOLIO ADIT\EXPORT_OFFSCREEN_RENDER_PLAN.md](../../../../../../EXPORT_OFFSCREEN_RENDER_PLAN.md) for complete technical specification.
