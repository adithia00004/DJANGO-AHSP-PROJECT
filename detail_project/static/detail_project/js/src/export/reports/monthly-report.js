/**
 * Laporan Bulanan (Monthly Report) Handler
 * Generates monthly progressive report dengan Kurva S Monthly + placeholder untuk tabel progress
 *
 * @module export/reports/monthly-report
 */

import { renderKurvaS } from '../core/kurva-s-renderer.js';
import { generatePDF, downloadPDF } from '../generators/pdf-generator.js';
import { generateWord, downloadWord } from '../generators/word-generator.js';
import { generateExcel, downloadExcel } from '../generators/excel-generator.js';
import { generateMonthlyProgressCSV, downloadCSV } from '../generators/csv-generator.js';

// ============================================================================
// Helper Functions for Monthly Report Data Preparation
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
 * @param {number} month - Month number (1-based)
 * @returns {Object} Title and identity data
 */
function prepareReportHeader(state, month) {
  const projectName = state.projectName || 'Project A';

  // Calculate month period (4 weeks per month)
  const startWeek = (month - 1) * 4 + 1;
  const endWeek = month * 4;

  // Get start and end dates from week columns
  const startWeekData = state.weekColumns?.find(w => w.week === startWeek);
  const endWeekData = state.weekColumns?.find(w => w.week === endWeek);

  const startDate = startWeekData ? formatDate(startWeekData.startDate) : 'N/A';
  const endDate = endWeekData ? formatDate(endWeekData.endDate) : 'N/A';

  return {
    title: `Laporan ${projectName} Bulan ke-${month}`,
    period: `Bulan ke-${month} periode ${startDate} - ${endDate}`,
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
 * Prepare main table data (Pekerjaan hierarchy with Total Harga and Bobot)
 * @param {Object} state - Application state
 * @returns {Array} Table rows
 */
function prepareMainTable(state) {
  const taskWeights = calculateTaskWeights(state.hierarchyRows || []);

  const tableRows = (state.hierarchyRows || []).map(row => {
    return {
      id: row.id,
      type: row.type,
      level: row.level,
      name: row.name,
      parentId: row.parentId,
      totalHarga: row.totalHarga || 0,
      bobot: taskWeights[row.id] || 0
    };
  });

  return tableRows;
}

/**
 * Calculate progress recapitulation metrics for a month
 * @param {Object} state - Application state
 * @param {number} month - Month number (1-based)
 * @returns {Object} Progress metrics
 */
function calculateProgressRecap(state, month) {
  const startWeek = (month - 1) * 4 + 1;
  const endWeek = month * 4;

  // Get cumulative progress at start and end of month
  const kurvaSData = state.kurvaSData || [];

  // Progress at start of month (end of previous month)
  const prevMonthEndWeek = startWeek - 1;
  const prevMonthData = kurvaSData.find(d => d.week === prevMonthEndWeek) || { planned: 0, actual: 0 };

  // Progress at end of current month
  const currentMonthData = kurvaSData.find(d => d.week === endWeek) || { planned: 0, actual: 0 };

  return {
    targetPlannedThisMonth: currentMonthData.planned - prevMonthData.planned,
    actualThisMonth: currentMonthData.actual - prevMonthData.actual,
    cumulativeTarget: currentMonthData.planned,
    cumulativeActual: currentMonthData.actual
  };
}

// ============================================================================
// Main Report Generation Function
// ============================================================================

/**
 * Generate Laporan Bulanan (Monthly Report)
 *
 * Status: ✅ FULLY IMPLEMENTED (Phase 4)
 *
 * Components:
 * - ✅ Report Title: "Laporan pekerjaan A Bulan ke-X"
 * - ✅ Identity: Month X period (dd-mm-yyyy - dd-mm-yyyy)
 * - ✅ Project Identity: Name, Owner, Location, Budget
 * - ✅ Main Table: Pekerjaan + Total Harga + Bobot Pekerjaan
 * - ✅ Kurva S Planned vs Actual (current month)
 * - ✅ Progress Recapitulation: Target Planned, Actual this month, Cumulative Target, Cumulative Actual
 *
 * @param {Object} state - Application state
 * @param {Array<Object>} state.hierarchyRows - Task hierarchy: [{ id, type, level, name, parentId, totalHarga }]
 * @param {Array<Object>} state.weekColumns - Week columns: [{ week, startDate, endDate }]
 * @param {Array<Object>} state.kurvaSData - Kurva S data: [{ week, planned, actual }]
 * @param {string} state.projectName - Project name
 * @param {string} state.projectOwner - Project owner
 * @param {string} state.projectLocation - Project location
 * @param {number} state.projectBudget - Project budget
 * @param {string} format - Export format: 'pdf' | 'word' | 'xlsx' | 'csv'
 * @param {number} month - Target month number (1-based)
 * @param {Object} [options={}] - Additional options
 * @returns {Promise<{blob: Blob, metadata: Object}>} Export result
 */
export async function generateMonthlyReport(state, format, month, options = {}) {
  console.log('[MonthlyReport] Generating report:', {
    format,
    month,
    weeks: state.kurvaSData?.length || 0
  });

  // Validate state
  if (!state.kurvaSData || state.kurvaSData.length === 0) {
    throw new Error('[MonthlyReport] kurvaSData tidak boleh kosong');
  }

  // Determine DPI based on format
  const dpi = (format === 'pdf' || format === 'word') ? 300 : 150;

  const attachments = [];

  try {
    // ========================================================================
    // Phase 4: Complete Monthly Report Implementation
    // ========================================================================

    // 1. Prepare Report Header (Title, Period, Project Identity)
    console.log('[MonthlyReport] Preparing report header...');
    const header = prepareReportHeader(state, month);
    console.log('[MonthlyReport] Header:', header.title);

    // 2. Prepare Main Table (Pekerjaan + Total Harga + Bobot)
    console.log('[MonthlyReport] Preparing main table...');
    const mainTable = prepareMainTable(state);
    console.log('[MonthlyReport] Main table prepared:', mainTable.length, 'rows');

    // 3. Render Kurva S Monthly Progressive
    console.log('[MonthlyReport] Rendering Kurva S Monthly Progressive...');
    const kurvaSMonthlyURL = await renderKurvaS({
      granularity: 'monthly',
      weeks_per_month: 4,
      data: state.kurvaSData,
      width: 1200,
      height: 600,
      dpi,
      backgroundColor: '#ffffff',
      timezone: options.timezone || 'Asia/Jakarta',
      title: header.title
    });

    attachments.push({
      title: 'Kurva S Planned vs Actual - ' + header.period,
      data_url: kurvaSMonthlyURL,
      format: 'png',
      section: 'kurva-s-monthly'
    });

    console.log('[MonthlyReport] Kurva S Monthly rendered');

    // 4. Calculate Progress Recapitulation
    console.log('[MonthlyReport] Calculating progress recapitulation...');
    const progressRecap = calculateProgressRecap(state, month);
    console.log('[MonthlyReport] Progress recap:', progressRecap);

    // 5. Prepare Monthly Progress Table (for grid data)
    // Structure compatible with existing infrastructure
    const monthlyProgressTable = {
      headers: [
        'Pekerjaan',
        'Total Harga',
        'Bobot Pekerjaan (%)',
        'Target Planned Bulan Ini (%)',
        'Actual Bulan Ini (%)',
        'Kumulatif Target (%)',
        'Kumulatif Actual (%)'
      ],
      rows: mainTable.map(row => [
        row.name,
        row.totalHarga,
        row.bobot.toFixed(2),
        progressRecap.targetPlannedThisMonth.toFixed(2),
        progressRecap.actualThisMonth.toFixed(2),
        progressRecap.cumulativeTarget.toFixed(2),
        progressRecap.cumulativeActual.toFixed(2)
      ]),
      metadata: {
        reportHeader: header,
        progressRecap
      }
    };

    console.log('[MonthlyReport] Monthly progress table prepared');

    // 6. Generate final output based on format
    console.log(`[MonthlyReport] Generating final ${format} file...`);

    let result;

    switch (format) {
      case 'pdf':
        result = await generatePDF({
          attachments,
          gridData: monthlyProgressTable,
          reportType: 'monthly',
          options: { month, ...options }
        });
        break;

      case 'word':
        result = await generateWord({
          attachments,
          gridData: monthlyProgressTable,
          reportType: 'monthly',
          options: { month, ...options }
        });
        break;

      case 'xlsx':
        // Direct call to backend ExportManager for native Excel with charts
        // Same pattern as rekap-report.js but with report_type: 'monthly'
        {
          // Try multiple sources for projectId
          let projectId = state.projectId || options.projectId || window.PROJECT_ID;

          // Fallback: extract from URL (e.g., /jadwal-pekerjaan/109/)
          if (!projectId) {
            const urlMatch = window.location.pathname.match(/\/(\d+)\//);
            if (urlMatch) {
              projectId = urlMatch[1];
            }
          }

          // Fallback: try to get from state manager or app
          if (!projectId && window.jadwalApp?.state?.projectId) {
            projectId = window.jadwalApp.state.projectId;
          }

          if (!projectId) {
            throw new Error('[MonthlyReport] projectId is required for xlsx export. Cannot determine project ID.');
          }

          // Call professional export endpoint directly
          const xlsxUrl = `/detail_project/api/project/${projectId}/export/jadwal-pekerjaan/professional/`;

          // Support multi-month export via options.months array
          const months = options?.months;
          const isMultiMonth = months && Array.isArray(months) && months.length > 0;

          console.log('[MonthlyReport] Calling backend xlsx export:', xlsxUrl, 'projectId:', projectId,
            isMultiMonth ? `months: [${months.join(',')}]` : `month: ${month}`);

          const response = await fetch(xlsxUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || ''
            },
            body: JSON.stringify({
              format: 'xlsx',
              report_type: 'monthly',
              // For multi-month: send months array; for single month: send period
              period: isMultiMonth ? null : month,
              months: isMultiMonth ? months : null
            })
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Excel export failed: ${response.status} - ${errorText}`);
          }

          // Validate content-type to ensure we got an xlsx file, not an error
          const contentType = response.headers.get('Content-Type') || '';
          if (!contentType.includes('spreadsheet') && !contentType.includes('octet-stream')) {
            // Might be JSON error response
            const errorText = await response.text();
            console.error('[MonthlyReport] Unexpected content-type:', contentType, 'Response:', errorText);
            throw new Error(`Excel export returned invalid content-type: ${contentType}. Response: ${errorText.substring(0, 200)}`);
          }

          const blob = await response.blob();
          console.log('[MonthlyReport] Excel blob received:', blob.size, 'bytes, type:', blob.type);

          result = {
            blob,
            metadata: {
              reportType: 'monthly',
              format: 'xlsx',
              month,
              generatedAt: new Date().toISOString()
            }
          };
        }
        break;

      case 'csv':
        // CSV only includes data tables (no charts)
        if (monthlyProgressTable) {
          result = {
            blob: generateMonthlyProgressCSV({
              monthlyProgressTable
            }),
            metadata: {
              reportType: 'monthly',
              format: 'csv',
              month,
              generatedAt: new Date().toISOString()
            }
          };
        } else {
          // Placeholder CSV
          result = {
            blob: generateMonthlyProgressCSV({}),
            metadata: {
              reportType: 'monthly',
              format: 'csv',
              month,
              status: 'placeholder',
              generatedAt: new Date().toISOString()
            }
          };
        }
        break;

      default:
        throw new Error(`[MonthlyReport] Unsupported format: ${format}`);
    }

    console.log('[MonthlyReport] Report generated successfully:', {
      format,
      month,
      attachments: attachments.length,
      size: result.blob?.size
    });

    return result;

  } catch (error) {
    console.error('[MonthlyReport] Report generation failed:', error);
    throw error;
  }
}

/**
 * Generate and download Laporan Bulanan
 * Convenience function yang langsung trigger download
 *
 * @param {Object} state - Application state
 * @param {string} format - Export format
 * @param {number} month - Target month number
 * @param {Object} [options={}] - Additional options
 * @param {string} [filename='monthly'] - Base filename
 */
export async function exportMonthlyReport(state, format, month, options = {}, filename = 'monthly') {
  const result = await generateMonthlyReport(state, format, month, options);

  // Auto-download based on format
  const fullFilename = `${filename}_M${month}`;

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
