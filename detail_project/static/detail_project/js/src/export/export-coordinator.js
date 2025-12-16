/**
 * Export Coordinator
 * Main entry point untuk export system
 * Routes export requests ke appropriate report handler
 *
 * @module export/export-coordinator
 */

import { generateRekapReport, exportRekapReport } from './reports/rekap-report.js';
import { generateMonthlyReport, exportMonthlyReport } from './reports/monthly-report.js';
import { generateWeeklyReport, exportWeeklyReport } from './reports/weekly-report.js';

/**
 * Export Configuration
 * Centralized configuration untuk export system
 */
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
    pdf: 300,
    word: 300,
    xlsx: 150,
    csv: 0 // Not applicable
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
    plannedColor: '#00CED1', // cyan
    actualColor: '#FFD700',  // yellow
    indentPerLevel: 20,
    timezone: 'Asia/Jakarta',
    endExclusive: false
  },

  // Performance limits
  limits: {
    maxCanvasSize: 16384, // px (Chrome limit)
    maxPages: 500,
    warningThreshold: 100 // Show warning jika > 100 pages
  },

  // Feature flags
  features: {
    batchUpload: true, // Enable batch upload untuk large datasets
    fallbackToScreenshot: true, // Fallback ke html2canvas jika rendering gagal
    showProgressBar: true, // Show progress bar during export
    validateData: true // Validate data structure sebelum export
  }
};

/**
 * Export report dengan routing ke appropriate handler
 *
 * @param {Object} exportRequest - Export request object
 * @param {string} exportRequest.reportType - 'rekap' | 'monthly' | 'weekly'
 * @param {string} exportRequest.format - 'pdf' | 'word' | 'xlsx' | 'csv'
 * @param {Object} exportRequest.state - Application state
 * @param {Object} [exportRequest.options={}] - Additional options
 * @param {number} [exportRequest.month] - Month number (for monthly report)
 * @param {number} [exportRequest.week] - Week number (for weekly report)
 * @param {boolean} [exportRequest.autoDownload=true] - Auto-download file setelah generate
 * @returns {Promise<{blob: Blob, metadata: Object}>} Export result
 */
export async function exportReport(exportRequest) {
  const {
    reportType,
    format,
    state,
    options = {},
    month = null,
    week = null,
    autoDownload = true
  } = exportRequest;

  // Validate request
  if (!reportType) {
    throw new Error('[ExportCoordinator] reportType is required');
  }
  if (!format) {
    throw new Error('[ExportCoordinator] format is required');
  }
  if (!state) {
    throw new Error('[ExportCoordinator] state is required');
  }

  console.log('[ExportCoordinator] Export request received:', {
    reportType,
    format,
    month,
    week,
    autoDownload
  });

  // Merge layout options dengan EXPORT_CONFIG
  const mergedOptions = {
    ...options,
    layout: {
      ...EXPORT_CONFIG.layout,
      ...(options.layout || {})
    }
  };

  try {
    let result;

    // Route to appropriate handler
    switch (reportType) {
      case EXPORT_CONFIG.reportTypes.REKAP:
        if (autoDownload) {
          result = await exportRekapReport(state, format, mergedOptions);
        } else {
          result = await generateRekapReport(state, format, mergedOptions);
        }
        break;

      case EXPORT_CONFIG.reportTypes.MONTHLY:
        if (!month) {
          throw new Error('[ExportCoordinator] month parameter required for monthly report');
        }
        if (autoDownload) {
          result = await exportMonthlyReport(state, format, month, mergedOptions);
        } else {
          result = await generateMonthlyReport(state, format, month, mergedOptions);
        }
        break;

      case EXPORT_CONFIG.reportTypes.WEEKLY:
        if (!week) {
          throw new Error('[ExportCoordinator] week parameter required for weekly report');
        }
        if (autoDownload) {
          result = await exportWeeklyReport(state, format, week, mergedOptions);
        } else {
          result = await generateWeeklyReport(state, format, week, mergedOptions);
        }
        break;

      default:
        throw new Error(`[ExportCoordinator] Unknown report type: ${reportType}`);
    }

    // Logging
    console.log(`[ExportCoordinator] ${reportType} report generated successfully:`, {
      format,
      size: result.blob?.size,
      metadata: result.metadata
    });

    return result;

  } catch (error) {
    console.error('[ExportCoordinator] Export failed:', error);

    // Fallback mechanism (if enabled)
    if (EXPORT_CONFIG.features.fallbackToScreenshot && options.allowFallback !== false) {
      console.warn('[ExportCoordinator] Attempting fallback to html2canvas...');
      // TODO: Implement fallback logic
      // return await fallbackToScreenshot(exportRequest);
    }

    throw error;
  }
}

/**
 * Estimate page count sebelum export
 * Useful untuk showing warning atau progress bar
 *
 * @param {Object} state - Application state
 * @param {string} reportType - Report type
 * @param {Object} [options={}] - Options
 * @returns {Object} { rowPages, timePages, totalPages }
 */
export function estimateExportSize(state, reportType, options = {}) {
  const { estimatePageCount } = require('./core/pagination-utils.js');

  const layout = {
    ...EXPORT_CONFIG.layout,
    ...(options.layout || {})
  };

  let totalRows, totalWeeks;

  switch (reportType) {
    case EXPORT_CONFIG.reportTypes.REKAP:
      totalRows = state.hierarchyRows?.length || 0;
      totalWeeks = state.weekColumns?.length || 0;
      break;

    case EXPORT_CONFIG.reportTypes.MONTHLY:
      totalRows = 0; // Chart only (1 page for Kurva S)
      totalWeeks = 0;
      break;

    case EXPORT_CONFIG.reportTypes.WEEKLY:
      totalRows = 0; // Not yet specified
      totalWeeks = 0;
      break;

    default:
      totalRows = 0;
      totalWeeks = 0;
  }

  const estimate = estimatePageCount(totalRows, totalWeeks, layout);

  // Add warning if exceeds threshold
  if (estimate.totalPages > EXPORT_CONFIG.limits.warningThreshold) {
    console.warn(`[ExportCoordinator] Large export detected: ${estimate.totalPages} pages (threshold: ${EXPORT_CONFIG.limits.warningThreshold})`);
  }

  if (estimate.totalPages > EXPORT_CONFIG.limits.maxPages) {
    console.error(`[ExportCoordinator] Export too large: ${estimate.totalPages} pages (max: ${EXPORT_CONFIG.limits.maxPages})`);
  }

  return estimate;
}

/**
 * Validate export request sebelum processing
 *
 * @param {Object} exportRequest - Export request
 * @returns {Object} { valid: boolean, errors: Array<string> }
 */
export function validateExportRequest(exportRequest) {
  const errors = [];

  // Required fields
  if (!exportRequest.reportType) {
    errors.push('reportType is required');
  }
  if (!exportRequest.format) {
    errors.push('format is required');
  }
  if (!exportRequest.state) {
    errors.push('state is required');
  }

  // Valid report type
  const validReportTypes = Object.values(EXPORT_CONFIG.reportTypes);
  if (exportRequest.reportType && !validReportTypes.includes(exportRequest.reportType)) {
    errors.push(`Invalid reportType: ${exportRequest.reportType}. Must be one of: ${validReportTypes.join(', ')}`);
  }

  // Valid format
  const validFormats = Object.values(EXPORT_CONFIG.formats);
  if (exportRequest.format && !validFormats.includes(exportRequest.format)) {
    errors.push(`Invalid format: ${exportRequest.format}. Must be one of: ${validFormats.join(', ')}`);
  }

  // Report-specific validation
  if (exportRequest.reportType === EXPORT_CONFIG.reportTypes.MONTHLY && !exportRequest.month) {
    errors.push('month parameter required for monthly report');
  }

  if (exportRequest.reportType === EXPORT_CONFIG.reportTypes.WEEKLY && !exportRequest.week) {
    errors.push('week parameter required for weekly report');
  }

  // State validation
  if (exportRequest.state && EXPORT_CONFIG.features.validateData) {
    const { validateRowsHierarchy } = require('./core/pagination-utils.js');

    if (exportRequest.state.hierarchyRows) {
      const rowErrors = validateRowsHierarchy(exportRequest.state.hierarchyRows);
      if (rowErrors.length > 0) {
        errors.push(...rowErrors.map(e => `State validation: ${e}`));
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

// Export all report handlers untuk direct usage
export {
  generateRekapReport,
  exportRekapReport,
  generateMonthlyReport,
  exportMonthlyReport,
  generateWeeklyReport,
  exportWeeklyReport
};
