# Export System Test Suite

Comprehensive test suite untuk validasi Export Offscreen System.

## Test Structure

```
test/
├── fixtures/              # Test data
│   ├── sample-data.js     # Raw data (rows, weeks, progress)
│   └── sample-state.js    # Complete application states
├── run-tests.js           # Node.js test runner (CLI)
├── test-runner.html       # Browser test runner (GUI)
└── README.md              # This file
```

## Running Tests

### Browser Test Runner (Recommended)

**Visual test runner dengan real-time progress:**

```bash
# Serve dengan development server
cd detail_project/static/detail_project/js/src/export
python -m http.server 8000

# Buka browser
http://localhost:8000/test/test-runner.html
```

**Features:**
- ✅ Real-time progress visualization
- ✅ Filter results by status (All/Passed/Failed/Skipped)
- ✅ Console output capture
- ✅ Interactive buttons untuk run different test suites
- ✅ Automatic rendering tests (requires DOM)

**Test Suites:**
- **Run All Tests** - Full test suite (unit + integration + edge cases)
- **Quick Tests** - Unit tests only (fast validation)
- **Unit Tests** - Core renderers + generators
- **Integration Tests** - End-to-end export workflows + edge cases

### Node.js Test Runner (CLI)

**Command-line test runner untuk CI/CD:**

```bash
# Run all tests
node test/run-tests.js

# Run quick tests only (unit tests)
node test/run-tests.js --quick

# Run unit tests only
node test/run-tests.js --unit

# Run integration tests only
node test/run-tests.js --integration
```

**Note:** Node.js runner membutuhkan jsdom atau headless browser untuk DOM rendering tests. Browser test runner is recommended for development.

## Test Coverage

### 1. Unit Tests - Core Renderers

#### Kurva S Renderer (`core/kurva-s-renderer.js`)
- ✅ Weekly mode rendering
- ✅ Monthly mode rendering (progressive M1=W1-W4, M2=W1-W8)
- ✅ Empty data handling
- ✅ Batch rendering (multiple charts)
- ✅ DPI scaling validation
- ✅ Canvas cleanup

#### Gantt Renderer (`core/gantt-renderer.js`)
- ✅ Single page rendering
- ✅ Multi-page pagination (row × time cartesian product)
- ✅ Split view (planned + actual)
- ✅ Hierarchical labels with indentation
- ✅ Segmented bars (gap handling)
- ✅ Page numbering and metadata

#### Pagination Utils (`core/pagination-utils.js`)
- ✅ Hierarchy validation (parentId references)
- ✅ Invalid hierarchy detection
- ✅ Split rows hierarchical algorithm
- ✅ Orphaned header prevention
- ✅ Header chain continuation with "(lanj.)"
- ✅ Calculate cols/rows per page

### 2. Unit Tests - Generators

#### Excel Generator (`generators/excel-generator.js`)
- ✅ Basic workbook creation
- ✅ Multi-sheet with data + charts
- ✅ Embedded PNG images
- ✅ Metadata addition
- ✅ Blob generation with correct MIME type
- ✅ File size validation

#### CSV Generator (`generators/csv-generator.js`)
- ✅ Basic CSV generation
- ✅ UTF-8 BOM addition (for Excel Windows)
- ✅ Semicolon delimiter
- ✅ Cell escaping (quotes, newlines, delimiters)
- ✅ Empty data handling

### 3. Integration Tests - Export Coordinator

#### Validation (`export-coordinator.js`)
- ✅ Valid request validation
- ✅ Invalid request detection (missing fields, wrong types)
- ✅ Report-specific validation (month/week parameters)
- ✅ State structure validation
- ✅ Estimate page count

#### End-to-End Export
- ✅ Rekap Report - CSV export
- ✅ Rekap Report - Excel export
- ✅ Monthly Report - CSV export
- ✅ Weekly Report - Infrastructure check (placeholder)

### 4. Edge Case Tests

#### Data Variations (`fixtures/sample-state.js`)
- ✅ **Minimal State** (1 row, 1 week) - Boundary test
- ✅ **Planned Only** (no actual progress) - Missing data test
- ✅ **With Gaps** (segmented bars) - Interrupted progress
- ✅ **Deep Hierarchy** (4 levels) - Edge case (3 levels is max supported)
- ✅ **Pagination Boundary** (15 rows) - Orphaned header prevention

### 5. Performance Tests (Optional)

#### Large Dataset (`largeState` - 100 rows, 52 weeks)
- ✅ Export duration measurement (target: < 30s)
- ✅ Memory usage monitoring
- ✅ Blob size validation
- ✅ No crashes or hangs

## Test Fixtures

### Available States

| State Name | Rows | Weeks | Description |
|------------|------|-------|-------------|
| `completeState` | 30 | 26 | Medium dataset with full metadata (default) |
| `smallState` | 10 | 12 | Quick testing dataset |
| `largeState` | 100 | 52 | Performance testing dataset |
| `minimalState` | 2 | 1 | Boundary test (1 klasifikasi + 1 pekerjaan) |
| `plannedOnlyState` | 30 | 26 | No actual progress (planned only) |
| `withGapsState` | 2 | 10 | Interrupted progress (gaps in weeks) |
| `deepHierarchyState` | 4 | 4 | 4-level hierarchy (edge case) |
| `paginationTestState` | 15 | 16 | Orphaned header boundary test |

### Usage

```javascript
import { completeState, smallState, getStateByName } from './fixtures/sample-state.js';

// Direct import
const result = await exportReport({
  reportType: 'rekap',
  format: 'csv',
  state: smallState,
  autoDownload: false
});

// By name
const state = getStateByName('withGaps');
```

## Test Data Structure

### Hierarchy Rows

```javascript
{
  id: 1,
  type: 'klasifikasi' | 'sub-klasifikasi' | 'pekerjaan',
  level: 0 | 1 | 2,  // Indentation level
  parentId: null | number,  // Reference to parent row
  name: 'Row Name'
}
```

### Week Columns

```javascript
{
  week: 1,
  startDate: '2025-01-06T00:00:00Z',  // ISO 8601 UTC
  endDate: '2025-01-12T23:59:59Z'     // Inclusive
}
```

### Progress Maps

```javascript
{
  [pekerjaanId]: {
    [weekNumber]: progressPercent  // 0-100
  }
}

// Example:
{
  2: { 1: 10, 2: 25, 3: 50 },  // Pekerjaan ID 2 progress di W1, W2, W3
  5: { 1: 15, 2: 30 }          // Pekerjaan ID 5 progress di W1, W2
}
```

### Kurva S Data

```javascript
[
  { week: 1, planned: 10, actual: 8 },
  { week: 2, planned: 25, actual: 20 },
  // Cumulative progress per week
]
```

## Expected Test Results

### Success Criteria

**Unit Tests:**
- ✅ All core renderers return valid dataURLs
- ✅ Pagination splits rows correctly without orphaned headers
- ✅ Generators produce valid Blobs with correct MIME types

**Integration Tests:**
- ✅ All export workflows complete without errors
- ✅ Validation catches invalid requests
- ✅ Edge cases handled gracefully (no crashes)

**Performance:**
- ✅ Large dataset (100 rows, 52 weeks) exports in < 30s
- ✅ Memory usage remains reasonable (< 500 MB delta)

### Known Limitations

1. **Deep Hierarchy (4 levels)** - System supports 3 levels officially, 4th level will render but may have layout issues
2. **Node.js Runner** - Requires jsdom or headless browser for DOM-based tests (browser runner recommended)
3. **Visual Regression** - Not implemented yet (future enhancement)

## Debugging Failed Tests

### Common Issues

**Issue: "Invalid dataURL returned"**
- Cause: Rendering failed or canvas empty
- Fix: Check console for uPlot/Canvas errors, ensure fonts loaded

**Issue: "Orphaned header not prevented"**
- Cause: Pagination algorithm edge case
- Fix: Check `splitRowsHierarchical` logic, verify header chain stack

**Issue: "Export too large" warning**
- Cause: Dataset exceeds `EXPORT_CONFIG.limits.warningThreshold` (100 pages)
- Fix: Expected for large datasets, not an error

**Issue: "Cannot read property of undefined"**
- Cause: Missing data in state (e.g., hierarchyRows, weekColumns)
- Fix: Validate state structure, ensure all required fields present

### Debug Mode

Enable verbose logging:

```javascript
// In browser console
localStorage.setItem('export_debug', 'true');

// In code
console.log('[ExportCoordinator] Debug info:', state);
```

## Adding New Tests

### 1. Add Test Fixture

```javascript
// test/fixtures/sample-state.js
export const myCustomState = {
  hierarchyRows: [...],
  weekColumns: [...],
  plannedProgress: {...},
  actualProgress: {...},
  kurvaSData: [...],
  projectName: 'My Test Case'
};
```

### 2. Add Test Case

**Browser (test-runner.html):**

```javascript
await runTest('My New Test', async () => {
  const result = await exportReport({
    reportType: 'rekap',
    format: 'csv',
    state: myCustomState,
    autoDownload: false
  });

  if (!result.blob) {
    throw new Error('Test failed: no blob returned');
  }
}, 'Custom Tests');
```

**Node.js (run-tests.js):**

```javascript
async function testMyFeature(results) {
  await runTest('My New Test', async () => {
    // Test logic
  }, results);
}

// Add to main()
await testMyFeature(results);
```

## CI/CD Integration

### Example GitHub Actions Workflow

```yaml
name: Export System Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: npm test  # Runs test/run-tests.js
```

## Next Steps

1. ✅ **Test Fixtures** - DONE
2. ✅ **Test Runner (Browser)** - DONE
3. ✅ **Test Runner (Node.js)** - DONE
4. 🔜 **Visual Regression Tests** - Compare rendered PNGs against baseline
5. 🔜 **Performance Benchmarks** - Track rendering speed over time
6. 🔜 **Backend Integration Tests** - Test PDF/Word generation endpoints

## Reference

See:
- [../README.md](../README.md) - Export system documentation
- [../../../../../../EXPORT_IMPLEMENTATION_ROADMAP.md](../../../../../../EXPORT_IMPLEMENTATION_ROADMAP.md) - Implementation roadmap
- [../../../../../../EXPORT_OFFSCREEN_RENDER_PLAN.md](../../../../../../EXPORT_OFFSCREEN_RENDER_PLAN.md) - Technical specification
