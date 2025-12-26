/**
 * Laporan Mingguan (Weekly Report) Handler
 *
 * Laporan Mingguan Format:
 * - Title: "Laporan pekerjaan A Minggu ke-X"
 * - Identity: Week X period dates
 * - Project Identity (Name, Owner, Location, Budget)
 * - Main Table with 7 columns:
 *   1. Pekerjaan
 *   2. Total Harga
 *   3. Bobot Pekerjaan (%)
 *   4. Target Planned Minggu Ini (%)
 *   5. Actual Minggu Ini (%)
 *   6. Kumulatif Target (%)
 *   7. Kumulatif Actual (%)
 *
 * @module export/reports/weekly-report
 */

import { generatePDF, downloadPDF } from '../generators/pdf-generator.js';
import { generateWord, downloadWord } from '../generators/word-generator.js';
import { generateExcel, downloadExcel } from '../generators/excel-generator.js';
import { generateWeeklyProgressCSV, downloadCSV } from '../generators/csv-generator.js';

// ============================================================================
// Helper Functions for Weekly Report Data Preparation
// ============================================================================

/**
 * Format date to dd-mm-yyyy
 * @param {Date|string} date - Date object or ISO string
 * @returns {string} Formatted date
 */
function formatDate(date) {
  const d = new Date(date);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}-${month}-${year}`;
}

/**
 * Prepare report title and identity section
 * @param {Object} state - Application state
 * @param {number} week - Week number (1-based)
 * @returns {Object} Title and identity data
 */
function prepareReportHeader(state, week) {
  const projectName = state.projectName || 'Project A';

  // Get week period from week columns
  const weekData = state.weekColumns?.find(w => w.week === week);

  const startDate = weekData ? formatDate(weekData.startDate) : 'N/A';
  const endDate = weekData ? formatDate(weekData.endDate) : 'N/A';

  return {
    title: `Laporan ${projectName} Minggu ke-${week}`,
    period: `Minggu ke-${week} periode ${startDate} - ${endDate}`,
    projectIdentity: {
      name: projectName,
      owner: state.projectOwner || 'N/A',
      location: state.projectLocation || 'N/A',
      budget: state.projectBudget || 0
    }
  };
}

/**
 * Calculate task weight (Bobot Pekerjaan) as percentage of total budget
 * @param {Array} hierarchyRows - All tasks
 * @returns {Object} Map of task ID to weight percentage
 */
function calculateTaskWeights(hierarchyRows) {
  const weights = {};

  // Calculate total budget from all "pekerjaan" type tasks
  let totalBudget = 0;
  const tasks = hierarchyRows.filter(row => row.type === 'pekerjaan');

  tasks.forEach(task => {
    totalBudget += task.totalHarga || 0;
  });

  // Calculate weight percentage for each task
  tasks.forEach(task => {
    const weight = totalBudget > 0
      ? ((task.totalHarga || 0) / totalBudget) * 100
      : 0;
    weights[task.id] = weight;
  });

  return weights;
}

/**
 * Calculate weekly progress for each task
 * @param {Object} state - Application state
 * @param {number} week - Week number
 * @returns {Object} Map of task ID to weekly progress data
 */
function calculateWeeklyProgress(state, week) {
  const weeklyProgress = {};

  const plannedProgress = state.plannedProgress || {};
  const actualProgress = state.actualProgress || {};

  // Get all tasks
  const tasks = (state.hierarchyRows || []).filter(row => row.type === 'pekerjaan');

  tasks.forEach(task => {
    const taskId = task.id;

    // Get progress for current week
    const plannedThisWeek = plannedProgress[taskId]?.[week] || 0;
    const actualThisWeek = actualProgress[taskId]?.[week] || 0;

    // Calculate cumulative progress up to this week
    let cumulativePlanned = 0;
    let cumulativeActual = 0;

    for (let w = 1; w <= week; w++) {
      cumulativePlanned += plannedProgress[taskId]?.[w] || 0;
      cumulativeActual += actualProgress[taskId]?.[w] || 0;
    }

    weeklyProgress[taskId] = {
      plannedThisWeek,
      actualThisWeek,
      cumulativePlanned,
      cumulativeActual
    };
  });

  return weeklyProgress;
}

/**
 * Prepare main table data with 7 columns
 * @param {Object} state - Application state
 * @param {number} week - Week number
 * @returns {Array} Table rows
 */
function prepareMainTable(state, week) {
  const taskWeights = calculateTaskWeights(state.hierarchyRows || []);
  const weeklyProgress = calculateWeeklyProgress(state, week);

  const tableRows = (state.hierarchyRows || []).map(row => {
    const progress = weeklyProgress[row.id] || {
      plannedThisWeek: 0,
      actualThisWeek: 0,
      cumulativePlanned: 0,
      cumulativeActual: 0
    };

    return {
      id: row.id,
      type: row.type,
      level: row.level,
      name: row.name,
      parentId: row.parentId,
      totalHarga: row.totalHarga || 0,
      bobot: taskWeights[row.id] || 0,
      plannedThisWeek: progress.plannedThisWeek,
      actualThisWeek: progress.actualThisWeek,
      cumulativePlanned: progress.cumulativePlanned,
      cumulativeActual: progress.cumulativeActual
    };
  });

  return tableRows;
}

// ============================================================================
// Main Report Generation Function
// ============================================================================

/**
 * Generate Laporan Mingguan (Weekly Report)
 *
 * Status: ✅ FULLY IMPLEMENTED (Phase 4)
 *
 * Components:
 * - ✅ Report Title: "Laporan pekerjaan A Minggu ke-X"
 * - ✅ Identity: Week X period (dd-mm-yyyy - dd-mm-yyyy)
 * - ✅ Project Identity: Name, Owner, Location, Budget
 * - ✅ Main Table with 7 columns:
 *   - Pekerjaan
 *   - Total Harga
 *   - Bobot Pekerjaan (%)
 *   - Target Planned Minggu Ini (%)
 *   - Actual Minggu Ini (%)
 *   - Kumulatif Target (%)
 *   - Kumulatif Actual (%)
 *
 * @param {Object} state - Application state
 * @param {Array<Object>} state.hierarchyRows - Task hierarchy: [{ id, type, level, name, parentId, totalHarga }]
 * @param {Array<Object>} state.weekColumns - Week columns: [{ week, startDate, endDate }]
 * @param {Object} state.plannedProgress - Planned progress: { taskId: { week: progress } }
 * @param {Object} state.actualProgress - Actual progress: { taskId: { week: progress } }
 * @param {string} state.projectName - Project name
 * @param {string} state.projectOwner - Project owner
 * @param {string} state.projectLocation - Project location
 * @param {number} state.projectBudget - Project budget
 * @param {string} format - Export format: 'pdf' | 'word' | 'xlsx' | 'csv'
 * @param {number} week - Target week number (1-based)
 * @param {Object} [options={}] - Additional options
 * @returns {Promise<{blob: Blob|null, metadata: Object}>} Export result
 */
export async function generateWeeklyReport(state, format, week, options = {}) {
  console.log('[WeeklyReport] Generating report:', {
    format,
    week,
    rows: state.hierarchyRows?.length || 0
  });

  // Validate state
  if (!state.hierarchyRows || state.hierarchyRows.length === 0) {
    throw new Error('[WeeklyReport] hierarchyRows tidak boleh kosong');
  }

  // Determine DPI based on format
  const dpi = (format === 'pdf' || format === 'word') ? 300 : 150;

  const attachments = [];

  try {
    // ========================================================================
    // Phase 4: Complete Weekly Report Implementation
    // ========================================================================

    // 1. Prepare Report Header (Title, Period, Project Identity)
    console.log('[WeeklyReport] Preparing report header...');
    const header = prepareReportHeader(state, week);
    console.log('[WeeklyReport] Header:', header.title);

    // 2. Prepare Main Table (7 columns)
    console.log('[WeeklyReport] Preparing main table...');
    const mainTable = prepareMainTable(state, week);
    console.log('[WeeklyReport] Main table prepared:', mainTable.length, 'rows');

    // 3. Prepare Weekly Progress Table (for grid data)
    const weeklyProgressTable = {
      headers: [
        'Pekerjaan',
        'Total Harga',
        'Bobot Pekerjaan (%)',
        'Target Planned Minggu Ini (%)',
        'Actual Minggu Ini (%)',
        'Kumulatif Target (%)',
        'Kumulatif Actual (%)'
      ],
      rows: mainTable.map(row => [
        row.name,
        row.totalHarga,
        row.bobot.toFixed(2),
        row.plannedThisWeek.toFixed(2),
        row.actualThisWeek.toFixed(2),
        row.cumulativePlanned.toFixed(2),
        row.cumulativeActual.toFixed(2)
      ]),
      metadata: {
        reportHeader: header
      }
    };

    console.log('[WeeklyReport] Weekly progress table prepared');

    // 4. Generate final output based on format
    console.log(`[WeeklyReport] Generating final ${format} file...`);

    let result;

    switch (format) {
      case 'pdf':
        result = await generatePDF({
          attachments,
          gridData: weeklyProgressTable,
          reportType: 'weekly',
          options: { week, ...options }
        });
        break;

      case 'word':
        result = await generateWord({
          attachments,
          gridData: weeklyProgressTable,
          reportType: 'weekly',
          options: { week, ...options }
        });
        break;

      case 'xlsx':
        result = await generateExcel({
          reportType: 'weekly',
          attachments,
          weeklyProgressTable
        });
        break;

      case 'csv':
        // CSV only includes data tables (no charts)
        result = {
          blob: generateWeeklyProgressCSV({
            weeklyProgressTable
          }),
          metadata: {
            reportType: 'weekly',
            format: 'csv',
            week,
            generatedAt: new Date().toISOString()
          }
        };
        break;

      default:
        throw new Error(`[WeeklyReport] Unsupported format: ${format}`);
    }

    console.log('[WeeklyReport] Report generated successfully:', {
      format,
      week,
      attachments: attachments.length,
      size: result.blob?.size
    });

    return result;

  } catch (error) {
    console.error('[WeeklyReport] Report generation failed:', error);
    throw error;
  }
}

/**
 * Generate and download Laporan Mingguan
 * Convenience function yang langsung trigger download
 *
 * @param {Object} state - Application state
 * @param {string} format - Export format
 * @param {number} week - Target week number
 * @param {Object} [options={}] - Additional options
 * @param {string} [filename='weekly'] - Base filename
 */
export async function exportWeeklyReport(state, format, week, options = {}, filename = 'weekly') {
  const result = await generateWeeklyReport(state, format, week, options);

  // Auto-download based on format
  const fullFilename = `${filename}_W${week}`;

  switch (format) {
    case 'pdf':
      downloadPDF(result.blob, fullFilename);
      break;
    case 'word':
      downloadWord(result.blob, fullFilename);
      break;
    case 'xlsx':
      downloadExcel(result.blob, fullFilename);
      break;
    case 'csv':
      downloadCSV(result.blob, fullFilename);
      break;
  }

  return result;
}
