/**
 * Laporan Mingguan (Weekly Report) Handler
 *
 * Laporan Mingguan Format:
 * - Title: "Laporan pekerjaan A Minggu ke-X"
 * - Identity: Week X period dates
 * - Project Identity (Name, Owner, Location, Budget)
 * - Main Table with 8 columns (same as backend pdf_exporter.py):
 *   1. Uraian Pekerjaan
 *   2. Volume
 *   3. Harga Satuan
 *   4. Total Harga
 *   5. Bobot (%)
 *   6. Kumulatif Minggu Lalu (%)
 *   7. Progress Minggu Ini (%)
 *   8. Kumulatif Minggu Ini (%)
 *
 * @module export/reports/weekly-report
 */

import { downloadPDF } from '../generators/pdf-generator.js';
import { downloadWord } from '../generators/word-generator.js';
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
 * Prepare main table data with 8 columns
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
      cumulativeActual: 0,
      cumulativePrevWeek: 0
    };

    // Calculate cumulative up to previous week
    let cumulativePrevWeek = 0;
    const actualProgress = state.actualProgress || {};
    for (let w = 1; w < week; w++) {
      cumulativePrevWeek += actualProgress[row.id]?.[w] || 0;
    }

    return {
      id: row.id,
      type: row.type,
      level: row.level,
      name: row.name,
      parentId: row.parentId,
      volume: row.volume || 0,
      hargaSatuan: row.hargaSatuan || 0,
      totalHarga: row.totalHarga || 0,
      bobot: taskWeights[row.id] || 0,
      plannedThisWeek: progress.plannedThisWeek,
      actualThisWeek: progress.actualThisWeek,
      cumulativePlanned: progress.cumulativePlanned,
      cumulativeActual: progress.cumulativeActual,
      cumulativePrevWeek: cumulativePrevWeek
    };
  });

  return tableRows;
}

/**
 * Extract project ID from current URL
 */
function extractProjectIdFromUrl() {
  // URL patterns: /detail_project/<project_id>/... or /project/<project_id>/...
  const match = window.location.pathname.match(/\/(detail_project|project)\/([\d]+)/);
  return match ? parseInt(match[2], 10) : null;
}

/**
 * Generate Weekly Report via Backend API
 * Calls the professional export endpoint directly, bypassing frontend image rendering.
 * 
 * @param {Object} state - Application state (for projectId lookup)
 * @param {string} format - 'pdf' or 'word'
 * @param {number|Array<number>} weeksOrWeek - Single week number or array of weeks
 * @param {Object} options - Additional options
 * @returns {Promise<{blob: Blob, metadata: Object}>}
 */
async function generateWeeklyReportFromBackend(state, format, weeksOrWeek, options = {}) {
  // Get project ID from state or URL
  const projectId = state.projectId || extractProjectIdFromUrl();
  if (!projectId) {
    throw new Error('[WeeklyReport] projectId not found in state or URL');
  }

  // Build URL params
  const params = new URLSearchParams({
    report_type: 'weekly',
    format: format
  });

  // Support both single week and array of weeks
  if (Array.isArray(weeksOrWeek)) {
    params.set('weeks', weeksOrWeek.join(','));
  } else {
    params.set('period', String(weeksOrWeek));
  }

  const url = `/detail_project/api/project/${projectId}/export/jadwal-pekerjaan/professional/?${params.toString()}`;

  console.log('[WeeklyReport] Calling backend API:', url);

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend export failed: ${response.status} - ${errorText}`);
  }

  const blob = await response.blob();

  // Extract filename from Content-Disposition if available
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = Array.isArray(weeksOrWeek)
    ? `weekly_W${Math.min(...weeksOrWeek)}-W${Math.max(...weeksOrWeek)}.${format === 'word' ? 'docx' : 'pdf'}`
    : `weekly_W${weeksOrWeek}.${format === 'word' ? 'docx' : 'pdf'}`;

  if (contentDisposition) {
    const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
    if (match && match[1]) {
      filename = match[1].replace(/["']/g, '');
    }
  }

  return {
    blob,
    metadata: {
      reportType: 'weekly',
      format: format,
      weeks: Array.isArray(weeksOrWeek) ? weeksOrWeek : [weeksOrWeek],
      generatedAt: new Date().toISOString(),
      filename
    }
  };
}

// ============================================================================
// Main Report Generation Function
// ============================================================================

/**
 * Generate Laporan Mingguan (Weekly Report)
 *
 * For PDF and Word formats, calls the backend professional export endpoint directly.
 * For Excel and CSV, generates locally.
 *
 * @param {Object} state - Application state
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

  const attachments = [];

  try {
    // 1. Prepare Report Header (Title, Period, Project Identity)
    console.log('[WeeklyReport] Preparing report header...');
    const header = prepareReportHeader(state, week);
    console.log('[WeeklyReport] Header:', header.title);

    // 2. Prepare Main Table
    console.log('[WeeklyReport] Preparing main table...');
    const mainTable = prepareMainTable(state, week);
    console.log('[WeeklyReport] Main table prepared:', mainTable.length, 'rows');

    // 3. Prepare Weekly Progress Table (for grid data) - 8 columns matching backend
    const weeklyProgressTable = {
      headers: [
        'Uraian Pekerjaan',
        'Volume',
        'Harga Satuan',
        'Total Harga',
        'Bobot (%)',
        'Kumulatif Minggu Lalu (%)',
        'Progress Minggu Ini (%)',
        'Kumulatif Minggu Ini (%)'
      ],
      rows: mainTable.map(row => [
        row.name,
        row.volume || '-',
        row.hargaSatuan || '-',
        row.totalHarga,
        row.bobot.toFixed(2),
        row.cumulativePrevWeek?.toFixed(2) || '0.00',
        row.actualThisWeek.toFixed(2),
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
      case 'word':
        // For PDF and Word, call backend directly (bypasses attachment requirement)
        result = await generateWeeklyReportFromBackend(state, format, week, options);
        break;

      case 'xlsx':
        // For xlsx, call backend professional export API
        {
          let projectId = state.projectId || extractProjectIdFromUrl();
          if (!projectId && window.jadwalApp?.state?.projectId) {
            projectId = window.jadwalApp.state.projectId;
          }

          if (!projectId) {
            throw new Error('[WeeklyReport] projectId is required for xlsx export');
          }

          const xlsxUrl = `/detail_project/api/project/${projectId}/export/jadwal-pekerjaan/professional/`;

          // Support multi-week export via options.weeks array
          const weeks = options?.weeks;
          const isMultiWeek = weeks && Array.isArray(weeks) && weeks.length > 0;

          console.log('[WeeklyReport] Calling backend xlsx export:', xlsxUrl, 'projectId:', projectId,
            isMultiWeek ? `weeks: [${weeks.join(',')}]` : `week: ${week}`);

          const response = await fetch(xlsxUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || ''
            },
            body: JSON.stringify({
              format: 'xlsx',
              report_type: 'weekly',
              // For multi-week: send weeks array; for single week: send period
              period: isMultiWeek ? null : week,
              weeks: isMultiWeek ? weeks : null
            })
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Excel export failed: ${response.status} - ${errorText}`);
          }

          const blob = await response.blob();

          // Extract filename from Content-Disposition
          const contentDisposition = response.headers.get('Content-Disposition');
          let xlsxFilename = isMultiWeek
            ? `Laporan_Minggu_${weeks[0]}-${weeks[weeks.length - 1]}.xlsx`
            : `Laporan_Minggu_${week}.xlsx`;

          if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
            if (match && match[1]) {
              xlsxFilename = match[1].replace(/["']/g, '');
            }
          }

          result = {
            blob,
            metadata: {
              reportType: 'weekly',
              format: 'xlsx',
              weeks: isMultiWeek ? weeks : [week],
              generatedAt: new Date().toISOString(),
              filename: xlsxFilename
            }
          };
        }
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
  try {
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

    // Hide export progress modal after successful download
    hideExportProgressModal();

    return result;
  } catch (error) {
    // Hide modal on error too
    hideExportProgressModal();
    throw error;
  }
}

/**
 * Helper to hide the export progress modal
 * This is needed because weekly export bypasses the normal flow in jadwal_kegiatan_app.js
 */
function hideExportProgressModal() {
  try {
    const modal = document.getElementById('exportProgressModal');
    if (modal && window.bootstrap) {
      const modalInstance = window.bootstrap.Modal.getInstance(modal);
      if (modalInstance) {
        modalInstance.hide();
      }
    }
  } catch (e) {
    console.warn('[WeeklyReport] Failed to hide progress modal:', e);
  }
}

// ============================================================================
// Multi-Week Export Functions (for batch export like multi-month)
// ============================================================================

/**
 * Generate Laporan Mingguan for multiple weeks (combined PDF)
 * Uses backend API directly for PDF/Word exports.
 * 
 * @param {Object} state - Application state
 * @param {string} format - Export format: 'pdf' | 'word'
 * @param {Array<number>} weeks - Array of week numbers (1-based)
 * @param {Object} [options={}] - Additional options
 * @returns {Promise<{blob: Blob|null, metadata: Object}>} Export result
 */
export async function generateMultiWeeklyReport(state, format, weeks, options = {}) {
  console.log('[WeeklyReport] Generating multi-week report:', {
    format,
    weeks,
    rows: state.hierarchyRows?.length || 0
  });

  // Validate
  if (!weeks || weeks.length === 0) {
    throw new Error('[WeeklyReport] weeks array tidak boleh kosong');
  }

  // For PDF/Word, call backend API directly with weeks array
  if (format === 'pdf' || format === 'word') {
    return await generateWeeklyReportFromBackend(state, format, weeks, options);
  }

  // For xlsx, call backend professional export API
  if (format === 'xlsx') {
    let projectId = state.projectId || extractProjectIdFromUrl();
    if (!projectId && window.jadwalApp?.state?.projectId) {
      projectId = window.jadwalApp.state.projectId;
    }

    if (!projectId) {
      throw new Error('[WeeklyReport] projectId is required for xlsx multi-week export');
    }

    const xlsxUrl = `/detail_project/api/project/${projectId}/export/jadwal-pekerjaan/professional/`;

    console.log('[WeeklyReport] Calling backend xlsx multi-week export:', xlsxUrl, 'projectId:', projectId, `weeks: [${weeks.join(',')}]`);

    const response = await fetch(xlsxUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || ''
      },
      body: JSON.stringify({
        format: 'xlsx',
        report_type: 'weekly',
        period: null,
        weeks: weeks
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Excel multi-week export failed: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();

    // Extract filename from Content-Disposition
    const contentDisposition = response.headers.get('Content-Disposition');
    let xlsxFilename = `Laporan_Minggu_${weeks[0]}-${weeks[weeks.length - 1]}.xlsx`;

    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
      if (match && match[1]) {
        xlsxFilename = match[1].replace(/["']/g, '');
      }
    }

    return {
      blob,
      metadata: {
        reportType: 'weekly',
        format: 'xlsx',
        weeks: weeks,
        generatedAt: new Date().toISOString(),
        filename: xlsxFilename
      }
    };
  }

  // For other formats (csv), not supported yet
  throw new Error(`[WeeklyReport] Multi-week export not supported for format: ${format}`);
}

/**
 * Generate and download Laporan Mingguan for multiple weeks
 * 
 * @param {Object} state - Application state
 * @param {string} format - Export format
 * @param {Array<number>} weeks - Array of week numbers
 * @param {Object} [options={}] - Additional options
 * @param {string} [filename='weekly'] - Base filename
 */
export async function exportMultiWeeklyReport(state, format, weeks, options = {}, filename = 'weekly') {
  const result = await generateMultiWeeklyReport(state, format, weeks, options);

  // Create filename with week range
  const minWeek = Math.min(...weeks);
  const maxWeek = Math.max(...weeks);
  const fullFilename = weeks.length === 1
    ? `${filename}_W${minWeek}`
    : `${filename}_W${minWeek}-W${maxWeek}`;

  try {
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
    }

    // Hide export progress modal after successful download
    hideExportProgressModal();

    return result;
  } catch (error) {
    // Hide modal on error too
    hideExportProgressModal();
    throw error;
  }
}
