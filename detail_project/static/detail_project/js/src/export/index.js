/**
 * Export System - Main Entry Point
 * Jadwal Pekerjaan Export Offscreen Rendering
 *
 * @module export
 */

// Main coordinator
export {
  exportReport,
  estimateExportSize,
  validateExportRequest,
  EXPORT_CONFIG
} from './export-coordinator.js';

// Report handlers (direct access)
export {
  generateRekapReport,
  exportRekapReport
} from './reports/rekap-report.js';

export {
  generateMonthlyReport,
  exportMonthlyReport
} from './reports/monthly-report.js';

export {
  generateWeeklyReport,
  exportWeeklyReport,
  getWeeklyReportStatus
} from './reports/weekly-report.js';

// Core renderers (for advanced usage)
export {
  renderKurvaS,
  renderKurvaSBatch
} from './core/kurva-s-renderer.js';

export {
  renderGanttPaged
} from './core/gantt-renderer.js';

// Pagination utilities (for advanced usage)
export {
  mmToPx,
  calculateColsPerPage,
  calculateRowsPerPage,
  selectPageSize,
  splitRowsHierarchical,
  validateRowsHierarchy,
  estimatePageCount
} from './core/pagination-utils.js';

// Generators (for advanced usage)
export {
  generateExcel,
  downloadExcel
} from './generators/excel-generator.js';

export {
  generateCSV,
  downloadCSV,
  prepareGridDataForCSV,
  generateRekapCSV,
  generateMonthlyProgressCSV
} from './generators/csv-generator.js';

export {
  generatePDF,
  downloadPDF
} from './generators/pdf-generator.js';

export {
  generateWord,
  downloadWord
} from './generators/word-generator.js';

/**
 * Quick export function
 * Convenience wrapper untuk most common use case
 *
 * @example
 * import { quickExport } from './export';
 *
 * quickExport('rekap', 'pdf', myState);
 * quickExport('monthly', 'xlsx', myState, { month: 2 });
 *
 * @param {string} reportType - 'rekap' | 'monthly' | 'weekly'
 * @param {string} format - 'pdf' | 'word' | 'xlsx' | 'csv'
 * @param {Object} state - Application state
 * @param {Object} [options={}] - Additional options
 * @returns {Promise<Object>} Export result
 */
export async function quickExport(reportType, format, state, options = {}) {
  const { exportReport, EXPORT_CONFIG } = await import('./export-coordinator.js');

  return await exportReport({
    reportType,
    format,
    state,
    autoDownload: true,
    ...options
  });
}

/**
 * Get export system version and status
 * @returns {Object} Version info
 */
export function getExportSystemInfo() {
  return {
    version: '1.0.0',
    status: {
      rekapReport: 'fully_implemented',
      monthlyReport: 'partially_implemented',
      weeklyReport: 'infrastructure_only'
    },
    supportedFormats: ['pdf', 'word', 'xlsx', 'csv'],
    supportedReportTypes: ['rekap', 'monthly', 'weekly'],
    dependencies: {
      uplot: '^1.6.24',
      exceljs: '^4.4.0'
    }
  };
}
