/**
 * Export System Test Fixture
 * Provides sample data and test functions to verify export system functionality
 *
 * @module export/test/export-test-fixture
 */

/**
 * Create sample application state for testing
 * @returns {Object} Complete state object with all required fields
 */
export function createTestState() {
  // Sample hierarchy (3 klasifikasi, 6 pekerjaan)
  const hierarchyRows = [
    // Klasifikasi 1
    { id: 1, type: 'klasifikasi', level: 0, name: 'Pekerjaan Persiapan', parentId: null, totalHarga: 50000000 },
    { id: 2, type: 'pekerjaan', level: 1, name: 'Mobilisasi', parentId: 1, totalHarga: 30000000 },
    { id: 3, type: 'pekerjaan', level: 1, name: 'Pemasangan Pagar', parentId: 1, totalHarga: 20000000 },

    // Klasifikasi 2
    { id: 4, type: 'klasifikasi', level: 0, name: 'Pekerjaan Struktur', parentId: null, totalHarga: 300000000 },
    { id: 5, type: 'pekerjaan', level: 1, name: 'Pondasi', parentId: 4, totalHarga: 100000000 },
    { id: 6, type: 'pekerjaan', level: 1, name: 'Kolom dan Balok', parentId: 4, totalHarga: 150000000 },
    { id: 7, type: 'pekerjaan', level: 1, name: 'Plat Lantai', parentId: 4, totalHarga: 50000000 },

    // Klasifikasi 3
    { id: 8, type: 'klasifikasi', level: 0, name: 'Pekerjaan Finishing', parentId: null, totalHarga: 150000000 },
    { id: 9, type: 'pekerjaan', level: 1, name: 'Pengecatan', parentId: 8, totalHarga: 50000000 },
    { id: 10, type: 'pekerjaan', level: 1, name: 'Keramik', parentId: 8, totalHarga: 100000000 }
  ];

  // Week columns (12 weeks = 3 months)
  const weekColumns = [];
  const startDate = new Date('2025-01-06');
  for (let i = 0; i < 12; i++) {
    const weekStart = new Date(startDate);
    weekStart.setDate(startDate.getDate() + (i * 7));

    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    weekEnd.setHours(23, 59, 59);

    weekColumns.push({
      week: i + 1,
      startDate: weekStart.toISOString(),
      endDate: weekEnd.toISOString()
    });
  }

  // Planned progress (task ID → { week → progress% })
  const plannedProgress = {
    2: { 1: 10, 2: 20, 3: 30, 4: 40 }, // Mobilisasi
    3: { 1: 5, 2: 15, 3: 25, 4: 35, 5: 45 }, // Pemasangan Pagar
    5: { 4: 10, 5: 20, 6: 30, 7: 40, 8: 50 }, // Pondasi
    6: { 6: 10, 7: 20, 8: 30, 9: 40, 10: 50 }, // Kolom dan Balok
    7: { 8: 10, 9: 20, 10: 30, 11: 40, 12: 50 }, // Plat Lantai
    9: { 10: 15, 11: 30, 12: 45 }, // Pengecatan
    10: { 10: 10, 11: 25, 12: 40 } // Keramik
  };

  // Actual progress (slightly behind planned)
  const actualProgress = {
    2: { 1: 8, 2: 18, 3: 28, 4: 38 },
    3: { 1: 4, 2: 12, 3: 22, 4: 32, 5: 42 },
    5: { 4: 8, 5: 18, 6: 28, 7: 38, 8: 48 },
    6: { 6: 8, 7: 18, 8: 28, 9: 38, 10: 48 },
    7: { 8: 8, 9: 18, 10: 28, 11: 38, 12: 48 },
    9: { 10: 12, 11: 27, 12: 42 },
    10: { 10: 8, 11: 22, 12: 37 }
  };

  // Kurva S data (cumulative progress by week)
  const kurvaSData = [];
  for (let week = 1; week <= 12; week++) {
    let plannedCumulative = 0;
    let actualCumulative = 0;

    // Sum all tasks' progress up to this week
    Object.keys(plannedProgress).forEach(taskId => {
      for (let w = 1; w <= week; w++) {
        plannedCumulative += plannedProgress[taskId][w] || 0;
        actualCumulative += actualProgress[taskId][w] || 0;
      }
    });

    kurvaSData.push({
      week,
      planned: Math.min(100, plannedCumulative),
      actual: Math.min(100, actualCumulative)
    });
  }

  // Complete state object
  return {
    hierarchyRows,
    weekColumns,
    plannedProgress,
    actualProgress,
    kurvaSData,
    projectName: 'Proyek Gedung Kantor ABC',
    projectOwner: 'PT. ABC Indonesia',
    projectLocation: 'Jakarta Selatan',
    projectBudget: 500000000
  };
}

/**
 * Run comprehensive export system test
 * Tests all report types and formats
 *
 * @returns {Promise<Object>} Test results
 */
export async function runExportTest() {
  console.log('========================================');
  console.log('EXPORT SYSTEM TEST FIXTURE');
  console.log('========================================\n');

  const results = {
    passed: 0,
    failed: 0,
    errors: [],
    startTime: new Date()
  };

  const state = createTestState();

  console.log('✅ Test state created:', {
    rows: state.hierarchyRows.length,
    weeks: state.weekColumns.length,
    kurvaSData: state.kurvaSData.length
  });

  // Test 1: Monthly Report - PDF
  try {
    console.log('\n📝 Test 1: Monthly Report - PDF (Month 2)');
    const { generateMonthlyReport } = await import('../reports/monthly-report.js');
    const result = await generateMonthlyReport(state, 'pdf', 2);

    if (result.blob) {
      console.log('✅ PASS: Monthly PDF generated');
      console.log(`   Size: ${(result.blob.size / 1024).toFixed(2)} KB`);
      results.passed++;
    } else {
      throw new Error('No blob returned');
    }
  } catch (error) {
    console.error('❌ FAIL: Monthly PDF - ', error.message);
    results.failed++;
    results.errors.push({ test: 'Monthly PDF', error: error.message });
  }

  // Test 2: Monthly Report - Excel
  try {
    console.log('\n📝 Test 2: Monthly Report - Excel (Month 2)');
    const { generateMonthlyReport } = await import('../reports/monthly-report.js');
    const result = await generateMonthlyReport(state, 'xlsx', 2);

    if (result.blob) {
      console.log('✅ PASS: Monthly Excel generated');
      console.log(`   Size: ${(result.blob.size / 1024).toFixed(2)} KB`);
      results.passed++;
    } else {
      throw new Error('No blob returned');
    }
  } catch (error) {
    console.error('❌ FAIL: Monthly Excel - ', error.message);
    results.failed++;
    results.errors.push({ test: 'Monthly Excel', error: error.message });
  }

  // Test 3: Weekly Report - PDF
  try {
    console.log('\n📝 Test 3: Weekly Report - PDF (Week 5)');
    const { generateWeeklyReport } = await import('../reports/weekly-report.js');
    const result = await generateWeeklyReport(state, 'pdf', 5);

    if (result.blob) {
      console.log('✅ PASS: Weekly PDF generated');
      console.log(`   Size: ${(result.blob.size / 1024).toFixed(2)} KB`);
      results.passed++;
    } else {
      throw new Error('No blob returned');
    }
  } catch (error) {
    console.error('❌ FAIL: Weekly PDF - ', error.message);
    results.failed++;
    results.errors.push({ test: 'Weekly PDF', error: error.message });
  }

  // Test 4: Weekly Report - Excel
  try {
    console.log('\n📝 Test 4: Weekly Report - Excel (Week 5)');
    const { generateWeeklyReport } = await import('../reports/weekly-report.js');
    const result = await generateWeeklyReport(state, 'xlsx', 5);

    if (result.blob) {
      console.log('✅ PASS: Weekly Excel generated');
      console.log(`   Size: ${(result.blob.size / 1024).toFixed(2)} KB`);
      results.passed++;
    } else {
      throw new Error('No blob returned');
    }
  } catch (error) {
    console.error('❌ FAIL: Weekly Excel - ', error.message);
    results.failed++;
    results.errors.push({ test: 'Weekly Excel', error: error.message });
  }

  // Test 5: Helper Functions - Monthly
  try {
    console.log('\n📝 Test 5: Monthly Helper Functions');
    const { generateMonthlyReport } = await import('../reports/monthly-report.js');

    // This should work without errors
    const result = await generateMonthlyReport(state, 'csv', 2);

    console.log('✅ PASS: Monthly helpers working');
    results.passed++;
  } catch (error) {
    console.error('❌ FAIL: Monthly helpers - ', error.message);
    results.failed++;
    results.errors.push({ test: 'Monthly helpers', error: error.message });
  }

  // Test 6: Helper Functions - Weekly
  try {
    console.log('\n📝 Test 6: Weekly Helper Functions');
    const { generateWeeklyReport } = await import('../reports/weekly-report.js');

    // This should work without errors
    const result = await generateWeeklyReport(state, 'csv', 5);

    console.log('✅ PASS: Weekly helpers working');
    results.passed++;
  } catch (error) {
    console.error('❌ FAIL: Weekly helpers - ', error.message);
    results.failed++;
    results.errors.push({ test: 'Weekly helpers', error: error.message });
  }

  // Summary
  results.endTime = new Date();
  results.duration = results.endTime - results.startTime;

  console.log('\n========================================');
  console.log('TEST SUMMARY');
  console.log('========================================');
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  console.log(`⏱️  Duration: ${results.duration}ms`);

  if (results.errors.length > 0) {
    console.log('\nErrors:');
    results.errors.forEach(err => {
      console.log(`  - ${err.test}: ${err.error}`);
    });
  }

  return results;
}

/**
 * Quick test function for console
 * Usage: await quickTest()
 */
export async function quickTest() {
  const state = createTestState();

  console.log('🚀 Quick Test: Generating Monthly Report (Month 2) PDF...');

  const { generateMonthlyReport, exportMonthlyReport } = await import('../reports/monthly-report.js');

  // Generate and auto-download
  await exportMonthlyReport(state, 'pdf', 2);

  console.log('✅ Check your downloads folder!');
}

/**
 * Export test state to window for console access
 */
export function setupTestEnvironment() {
  const state = createTestState();

  window.exportTestState = state;
  window.runExportTest = runExportTest;
  window.quickTest = quickTest;

  console.log('========================================');
  console.log('EXPORT TEST ENVIRONMENT READY');
  console.log('========================================');
  console.log('Available in console:');
  console.log('  window.exportTestState - Sample data');
  console.log('  window.runExportTest() - Run all tests');
  console.log('  window.quickTest() - Quick PDF test');
  console.log('========================================\n');
}

// Auto-setup when loaded
if (typeof window !== 'undefined') {
  setupTestEnvironment();
}
