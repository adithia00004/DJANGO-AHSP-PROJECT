/**
 * Export System Test Runner
 * Validates export functionality dengan test fixtures
 *
 * Usage:
 *   node test/run-tests.js                  # Run all tests
 *   node test/run-tests.js --quick          # Run quick tests only
 *   node test/run-tests.js --unit           # Run unit tests only
 *   node test/run-tests.js --integration    # Run integration tests only
 *
 * @module export/test/run-tests
 */

import {
  completeState,
  smallState,
  largeState,
  minimalState,
  plannedOnlyState,
  withGapsState,
  deepHierarchyState,
  paginationTestState,
  getAvailableStates
} from './fixtures/sample-state.js';

import {
  exportReport,
  estimateExportSize,
  validateExportRequest,
  EXPORT_CONFIG
} from '../export-coordinator.js';

import {
  renderKurvaS,
  renderKurvaSBatch
} from '../core/kurva-s-renderer.js';

import {
  renderGanttPaged
} from '../core/gantt-renderer.js';

import {
  splitRowsHierarchical,
  validateRowsHierarchy,
  calculateColsPerPage,
  calculateRowsPerPage
} from '../core/pagination-utils.js';

import {
  generateExcel
} from '../generators/excel-generator.js';

import {
  generateCSV
} from '../generators/csv-generator.js';

/**
 * Test Results Collector
 */
class TestResults {
  constructor() {
    this.tests = [];
    this.passed = 0;
    this.failed = 0;
    this.skipped = 0;
    this.startTime = Date.now();
  }

  addTest(name, status, duration, error = null) {
    this.tests.push({ name, status, duration, error });
    if (status === 'PASS') this.passed++;
    else if (status === 'FAIL') this.failed++;
    else if (status === 'SKIP') this.skipped++;
  }

  report() {
    const totalTime = Date.now() - this.startTime;
    const total = this.tests.length;

    console.log('\n' + '='.repeat(80));
    console.log('TEST SUMMARY');
    console.log('='.repeat(80));
    console.log(`Total Tests: ${total}`);
    console.log(`✅ Passed:   ${this.passed} (${((this.passed / total) * 100).toFixed(1)}%)`);
    console.log(`❌ Failed:   ${this.failed} (${((this.failed / total) * 100).toFixed(1)}%)`);
    console.log(`⏭️  Skipped:  ${this.skipped} (${((this.skipped / total) * 100).toFixed(1)}%)`);
    console.log(`⏱️  Duration: ${(totalTime / 1000).toFixed(2)}s`);
    console.log('='.repeat(80));

    if (this.failed > 0) {
      console.log('\nFAILED TESTS:');
      this.tests.filter(t => t.status === 'FAIL').forEach(t => {
        console.log(`  ❌ ${t.name}`);
        console.log(`     Error: ${t.error}`);
      });
    }

    console.log('\n');
    return this.failed === 0;
  }
}

/**
 * Test Runner Utility
 */
async function runTest(name, testFn, results) {
  const start = Date.now();
  try {
    console.log(`\n🧪 Testing: ${name}...`);
    await testFn();
    const duration = Date.now() - start;
    console.log(`   ✅ PASS (${duration}ms)`);
    results.addTest(name, 'PASS', duration);
    return true;
  } catch (error) {
    const duration = Date.now() - start;
    console.log(`   ❌ FAIL (${duration}ms)`);
    console.log(`   Error: ${error.message}`);
    results.addTest(name, 'FAIL', duration, error.message);
    return false;
  }
}

// ============================================================================
// UNIT TESTS - Core Renderers
// ============================================================================

async function testKurvaSRenderer(results) {
  await runTest('Kurva S Renderer - Weekly Mode', async () => {
    const dataURL = await renderKurvaS({
      granularity: 'weekly',
      data: smallState.kurvaSData,
      width: 800,
      height: 400,
      dpi: 96 // Quick test dengan low DPI
    });

    if (!dataURL || !dataURL.startsWith('data:image/png;base64,')) {
      throw new Error('Invalid dataURL returned');
    }

    // Check size (base64 should be > 1000 chars for real chart)
    if (dataURL.length < 1000) {
      throw new Error('Chart image too small, likely rendering failed');
    }
  }, results);

  await runTest('Kurva S Renderer - Monthly Mode', async () => {
    const dataURL = await renderKurvaS({
      granularity: 'monthly',
      weeks_per_month: 4,
      data: smallState.kurvaSData,
      width: 800,
      height: 400,
      dpi: 96
    });

    if (!dataURL || !dataURL.startsWith('data:image/png;base64,')) {
      throw new Error('Invalid dataURL returned');
    }
  }, results);

  await runTest('Kurva S Renderer - Empty Data', async () => {
    const dataURL = await renderKurvaS({
      granularity: 'weekly',
      data: [],
      width: 800,
      height: 400,
      dpi: 96
    });

    if (!dataURL || !dataURL.startsWith('data:image/png;base64,')) {
      throw new Error('Should still return valid dataURL for empty data');
    }
  }, results);

  await runTest('Kurva S Batch Renderer', async () => {
    const configs = [
      { granularity: 'weekly', data: smallState.kurvaSData, width: 600, height: 300, dpi: 96 },
      { granularity: 'monthly', data: smallState.kurvaSData, width: 600, height: 300, dpi: 96, weeks_per_month: 4 }
    ];

    const dataURLs = await renderKurvaSBatch(configs);

    if (!Array.isArray(dataURLs) || dataURLs.length !== 2) {
      throw new Error('Should return array of 2 dataURLs');
    }

    dataURLs.forEach((dataURL, idx) => {
      if (!dataURL || !dataURL.startsWith('data:image/png;base64,')) {
        throw new Error(`Invalid dataURL at index ${idx}`);
      }
    });
  }, results);
}

async function testGanttRenderer(results) {
  await runTest('Gantt Renderer - Single Page', async () => {
    const pages = await renderGanttPaged({
      rows: minimalState.hierarchyRows,
      timeColumns: minimalState.weekColumns,
      planned: minimalState.plannedProgress,
      actual: null,
      layout: {
        labelWidthPx: 400,
        timeColWidthPx: 70,
        rowHeightPx: 28,
        dpi: 96
      }
    });

    if (!Array.isArray(pages) || pages.length === 0) {
      throw new Error('Should return at least 1 page');
    }

    const page = pages[0];
    if (!page.dataURL || !page.dataURL.startsWith('data:image/png;base64,')) {
      throw new Error('Invalid page dataURL');
    }

    if (!page.pageInfo || typeof page.pageInfo.pageNumber !== 'number') {
      throw new Error('Missing or invalid pageInfo');
    }
  }, results);

  await runTest('Gantt Renderer - Multi-Page (Small)', async () => {
    const pages = await renderGanttPaged({
      rows: smallState.hierarchyRows,
      timeColumns: smallState.weekColumns,
      planned: smallState.plannedProgress,
      actual: null,
      layout: {
        labelWidthPx: 400,
        timeColWidthPx: 70,
        rowHeightPx: 28,
        rowsPerPage: 5, // Force pagination
        colsPerPage: 6,
        dpi: 96
      }
    });

    if (pages.length < 2) {
      throw new Error('Should generate multiple pages with forced pagination');
    }

    // Validate all pages
    pages.forEach((page, idx) => {
      if (!page.dataURL || !page.dataURL.startsWith('data:image/png;base64,')) {
        throw new Error(`Invalid dataURL at page ${idx + 1}`);
      }
      if (page.pageInfo.pageNumber !== idx + 1) {
        throw new Error(`Incorrect page number at index ${idx}`);
      }
    });
  }, results);

  await runTest('Gantt Renderer - Split View (Planned + Actual)', async () => {
    const pages = await renderGanttPaged({
      rows: minimalState.hierarchyRows,
      timeColumns: minimalState.weekColumns,
      planned: minimalState.plannedProgress,
      actual: minimalState.actualProgress,
      layout: {
        labelWidthPx: 400,
        timeColWidthPx: 70,
        rowHeightPx: 28,
        dpi: 96
      }
    });

    if (pages.length === 0) {
      throw new Error('Should return pages');
    }

    // Split view should render both bars
    // Cannot validate visually here, but should not crash
  }, results);
}

async function testPaginationUtils(results) {
  await runTest('Pagination Utils - Hierarchy Validation', async () => {
    const errors = validateRowsHierarchy(completeState.hierarchyRows);

    if (errors.length > 0) {
      throw new Error(`Hierarchy validation failed: ${errors.join(', ')}`);
    }
  }, results);

  await runTest('Pagination Utils - Invalid Hierarchy', async () => {
    const invalidRows = [
      { id: 1, type: 'klasifikasi', level: 0, parentId: null, name: 'A' },
      { id: 2, type: 'pekerjaan', level: 1, parentId: 999, name: 'B' } // Invalid parentId
    ];

    const errors = validateRowsHierarchy(invalidRows);

    if (errors.length === 0) {
      throw new Error('Should detect invalid parentId');
    }
  }, results);

  await runTest('Pagination Utils - Split Rows Hierarchical', async () => {
    const pages = splitRowsHierarchical(smallState.hierarchyRows, 5);

    if (!Array.isArray(pages) || pages.length === 0) {
      throw new Error('Should return pages');
    }

    // Check that no page exceeds limit (except with continued headers)
    pages.forEach((page, idx) => {
      if (page.length === 0) {
        throw new Error(`Page ${idx + 1} is empty`);
      }
    });
  }, results);

  await runTest('Pagination Utils - Orphaned Header Prevention', async () => {
    const pages = splitRowsHierarchical(paginationTestState.hierarchyRows, 14);

    // Should prevent orphaned header at boundary (row 15)
    // Check that klasifikasi at row 15 is not alone at end of page
    const lastPageOfFirst = pages[0];
    const lastRow = lastPageOfFirst[lastPageOfFirst.length - 1];

    if (lastRow.type === 'klasifikasi' && lastRow.id === 15) {
      throw new Error('Orphaned header not prevented');
    }
  }, results);

  await runTest('Pagination Utils - Calculate Cols/Rows Per Page', async () => {
    const layout = {
      pageSize: 'A4',
      orientation: 'landscape',
      marginMm: 20,
      labelWidthPx: 600,
      timeColWidthPx: 70,
      rowHeightPx: 28,
      headerHeightPx: 60,
      dpi: 300
    };

    const colsPerPage = calculateColsPerPage(layout);
    const rowsPerPage = calculateRowsPerPage(layout);

    if (typeof colsPerPage !== 'number' || colsPerPage <= 0) {
      throw new Error('Invalid colsPerPage calculation');
    }

    if (typeof rowsPerPage !== 'number' || rowsPerPage <= 0) {
      throw new Error('Invalid rowsPerPage calculation');
    }

    console.log(`     Cols/page: ${colsPerPage}, Rows/page: ${rowsPerPage}`);
  }, results);
}

// ============================================================================
// UNIT TESTS - Generators
// ============================================================================

async function testGenerators(results) {
  await runTest('Excel Generator - Basic', async () => {
    const attachments = [
      {
        title: 'Test Chart',
        data_url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        format: 'png'
      }
    ];

    const headers = ['Pekerjaan', 'W1', 'W2', 'W3'];
    const rows = [
      ['Task A', 10, 20, 30],
      ['Task B', 15, 25, 35]
    ];

    const blob = await generateExcel({
      attachments,
      headers,
      rows,
      metadata: { projectName: 'Test Project' }
    });

    if (!(blob instanceof Blob)) {
      throw new Error('Should return Blob instance');
    }

    if (blob.size === 0) {
      throw new Error('Blob should not be empty');
    }

    if (blob.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
      throw new Error('Incorrect MIME type');
    }

    console.log(`     Excel size: ${(blob.size / 1024).toFixed(2)} KB`);
  }, results);

  await runTest('CSV Generator - Basic', async () => {
    const headers = ['Pekerjaan', 'W1', 'W2', 'W3'];
    const rows = [
      ['Task A', 10, 20, 30],
      ['Task B', 15, 25, 35]
    ];

    const blob = generateCSV({ headers, rows, delimiter: ';', addBOM: true });

    if (!(blob instanceof Blob)) {
      throw new Error('Should return Blob instance');
    }

    if (blob.size === 0) {
      throw new Error('Blob should not be empty');
    }

    if (blob.type !== 'text/csv;charset=utf-8;') {
      throw new Error('Incorrect MIME type');
    }

    // Read content to validate BOM
    const text = await blob.text();
    if (!text.startsWith('\uFEFF')) {
      throw new Error('Missing UTF-8 BOM');
    }

    console.log(`     CSV size: ${blob.size} bytes`);
  }, results);

  await runTest('CSV Generator - Escaping', async () => {
    const headers = ['Name', 'Description'];
    const rows = [
      ['Task "A"', 'Contains; semicolon'],
      ['Task\nB', 'Contains\nnewline']
    ];

    const blob = generateCSV({ headers, rows, delimiter: ';' });
    const text = await blob.text();

    // Should escape quotes and wrap semicolons
    if (!text.includes('"Task ""A"""')) {
      throw new Error('Quote escaping failed');
    }

    if (!text.includes('"Contains; semicolon"')) {
      throw new Error('Semicolon escaping failed');
    }
  }, results);
}

// ============================================================================
// INTEGRATION TESTS - End-to-End
// ============================================================================

async function testExportCoordinator(results) {
  await runTest('Export Coordinator - Validation', async () => {
    const validation = validateExportRequest({
      reportType: 'rekap',
      format: 'pdf',
      state: completeState
    });

    if (!validation.valid) {
      throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
    }
  }, results);

  await runTest('Export Coordinator - Invalid Request', async () => {
    const validation = validateExportRequest({
      reportType: 'invalid',
      format: 'pdf',
      state: null
    });

    if (validation.valid) {
      throw new Error('Should detect invalid request');
    }

    if (validation.errors.length === 0) {
      throw new Error('Should return error messages');
    }
  }, results);

  await runTest('Export Coordinator - Estimate Size', async () => {
    const estimate = estimateExportSize(completeState, 'rekap');

    if (typeof estimate.totalPages !== 'number' || estimate.totalPages <= 0) {
      throw new Error('Invalid estimate');
    }

    console.log(`     Estimated pages: ${estimate.totalPages} (rows: ${estimate.rowPages}, time: ${estimate.timePages})`);
  }, results);

  await runTest('Export Report - Rekap CSV (Full E2E)', async () => {
    const result = await exportReport({
      reportType: 'rekap',
      format: 'csv',
      state: smallState,
      autoDownload: false
    });

    if (!result.blob || !(result.blob instanceof Blob)) {
      throw new Error('Should return Blob');
    }

    if (!result.metadata || result.metadata.reportType !== 'rekap') {
      throw new Error('Missing or invalid metadata');
    }

    console.log(`     CSV Blob size: ${(result.blob.size / 1024).toFixed(2)} KB`);
  }, results);

  await runTest('Export Report - Rekap Excel (Full E2E)', async () => {
    const result = await exportReport({
      reportType: 'rekap',
      format: 'xlsx',
      state: minimalState,
      autoDownload: false
    });

    if (!result.blob || !(result.blob instanceof Blob)) {
      throw new Error('Should return Blob');
    }

    if (result.blob.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
      throw new Error('Incorrect MIME type');
    }

    console.log(`     Excel Blob size: ${(result.blob.size / 1024).toFixed(2)} KB`);
  }, results);

  await runTest('Export Report - Monthly CSV', async () => {
    const result = await exportReport({
      reportType: 'monthly',
      format: 'csv',
      state: smallState,
      month: 2,
      autoDownload: false
    });

    if (!result.blob || !(result.blob instanceof Blob)) {
      throw new Error('Should return Blob');
    }

    if (result.metadata.reportType !== 'monthly' || result.metadata.month !== 2) {
      throw new Error('Incorrect metadata');
    }
  }, results);

  await runTest('Export Report - Weekly (Infrastructure Check)', async () => {
    const result = await exportReport({
      reportType: 'weekly',
      format: 'csv',
      state: smallState,
      week: 5,
      autoDownload: false
    });

    if (result.metadata.status !== 'pending_specification') {
      throw new Error('Weekly report should return pending status');
    }

    if (result.blob !== null) {
      throw new Error('Weekly report should not generate blob yet');
    }
  }, results);
}

// ============================================================================
// EDGE CASE TESTS
// ============================================================================

async function testEdgeCases(results) {
  await runTest('Edge Case - Minimal State', async () => {
    const result = await exportReport({
      reportType: 'rekap',
      format: 'csv',
      state: minimalState,
      autoDownload: false
    });

    if (!result.blob) {
      throw new Error('Should handle minimal state');
    }
  }, results);

  await runTest('Edge Case - Planned Only (No Actual)', async () => {
    const result = await exportReport({
      reportType: 'rekap',
      format: 'csv',
      state: plannedOnlyState,
      autoDownload: false
    });

    if (!result.blob) {
      throw new Error('Should handle planned-only state');
    }
  }, results);

  await runTest('Edge Case - With Gaps', async () => {
    const result = await exportReport({
      reportType: 'rekap',
      format: 'csv',
      state: withGapsState,
      autoDownload: false
    });

    if (!result.blob) {
      throw new Error('Should handle state with gaps');
    }
  }, results);

  await runTest('Edge Case - Deep Hierarchy (4 levels)', async () => {
    const result = await exportReport({
      reportType: 'rekap',
      format: 'csv',
      state: deepHierarchyState,
      autoDownload: false
    });

    if (!result.blob) {
      throw new Error('Should handle deep hierarchy');
    }
  }, results);
}

// ============================================================================
// PERFORMANCE TESTS
// ============================================================================

async function testPerformance(results) {
  await runTest('Performance - Large Dataset (100 rows, 52 weeks)', async () => {
    const startMem = performance.memory ? performance.memory.usedJSHeapSize : 0;
    const startTime = Date.now();

    const result = await exportReport({
      reportType: 'rekap',
      format: 'csv',
      state: largeState,
      autoDownload: false
    });

    const duration = Date.now() - startTime;
    const endMem = performance.memory ? performance.memory.usedJSHeapSize : 0;
    const memDelta = (endMem - startMem) / (1024 * 1024);

    if (!result.blob) {
      throw new Error('Failed to generate large dataset');
    }

    console.log(`     Duration: ${(duration / 1000).toFixed(2)}s`);
    console.log(`     Memory delta: ${memDelta.toFixed(2)} MB`);
    console.log(`     Blob size: ${(result.blob.size / 1024).toFixed(2)} KB`);

    if (duration > 30000) {
      console.warn('     ⚠️  Warning: Export took longer than 30s');
    }
  }, results);
}

// ============================================================================
// MAIN TEST RUNNER
// ============================================================================

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('EXPORT SYSTEM TEST SUITE');
  console.log('='.repeat(80));

  const args = process.argv.slice(2);
  const runQuickOnly = args.includes('--quick');
  const runUnitOnly = args.includes('--unit');
  const runIntegrationOnly = args.includes('--integration');
  const runAll = !runQuickOnly && !runUnitOnly && !runIntegrationOnly;

  const results = new TestResults();

  try {
    // Unit Tests
    if (runAll || runUnitOnly || runQuickOnly) {
      console.log('\n📦 UNIT TESTS - Core Renderers');
      console.log('-'.repeat(80));
      await testKurvaSRenderer(results);
      await testGanttRenderer(results);
      await testPaginationUtils(results);

      console.log('\n📦 UNIT TESTS - Generators');
      console.log('-'.repeat(80));
      await testGenerators(results);
    }

    // Integration Tests
    if (runAll || runIntegrationOnly) {
      console.log('\n🔗 INTEGRATION TESTS - End-to-End');
      console.log('-'.repeat(80));
      await testExportCoordinator(results);
    }

    // Edge Cases
    if (runAll || runIntegrationOnly) {
      console.log('\n⚠️  EDGE CASE TESTS');
      console.log('-'.repeat(80));
      await testEdgeCases(results);
    }

    // Performance Tests
    if (runAll) {
      console.log('\n⚡ PERFORMANCE TESTS');
      console.log('-'.repeat(80));
      await testPerformance(results);
    }

    // Final Report
    const success = results.report();
    process.exit(success ? 0 : 1);

  } catch (error) {
    console.error('\n❌ FATAL ERROR:', error);
    process.exit(1);
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { main, TestResults };
