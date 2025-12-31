/**
 * Laporan Rekap (Full Report) Handler
 * Generates complete report dengan Gantt Planned/Actual + Kurva S Weekly + Grid Data
 *
 * @module export/reports/rekap-report
 */

import { renderKurvaS } from '../core/kurva-s-renderer.js';
import { renderGanttPaged } from '../core/gantt-renderer.js';
import { generatePDF, downloadPDF } from '../generators/pdf-generator.js';
import { generateWord, downloadWord } from '../generators/word-generator.js';
import { generateExcel, downloadExcel } from '../generators/excel-generator.js';
import { generateRekapCSV, downloadCSV } from '../generators/csv-generator.js';

/**
 * Generate Laporan Rekap (Full Report)
 *
 * Konten:
 * - Gantt Full Timeline - Planned
 * - Gantt Full Timeline - Actual
 * - Kurva S Weekly
 * - Grid View - Full Data
 *
 * @param {Object} state - Application state
 * @param {Array<Object>} state.hierarchyRows - Hierarchical rows
 * @param {Array<Object>} state.weekColumns - Week columns
 * @param {Object} state.plannedProgress - Planned progress map: pekerjaan_id -> { week -> progress }
 * @param {Object} state.actualProgress - Actual progress map: pekerjaan_id -> { week -> progress }
 * @param {Array<Object>} state.kurvaSData - Kurva S data: [{ week, planned, actual }]
 * @param {string} format - Export format: 'pdf' | 'word' | 'xlsx' | 'csv'
 * @param {Object} [options={}] - Additional options
 * @returns {Promise<{blob: Blob, metadata: Object}>} Export result
 */
export async function generateRekapReport(state, format, options = {}) {
  console.log('[RekapReport] Generating report:', {
    format,
    rows: state.hierarchyRows?.length || 0,
    weeks: state.weekColumns?.length || 0
  });

  // Validate state
  if (!state.hierarchyRows || state.hierarchyRows.length === 0) {
    throw new Error('[RekapReport] hierarchyRows tidak boleh kosong');
  }
  if (!state.weekColumns || state.weekColumns.length === 0) {
    throw new Error('[RekapReport] weekColumns tidak boleh kosong');
  }
  if (!state.kurvaSData || state.kurvaSData.length === 0) {
    throw new Error('[RekapReport] kurvaSData tidak boleh kosong');
  }

  // Determine DPI based on format
  const dpi = (format === 'pdf' || format === 'word') ? 300 : 150;

  // Layout configuration
  const layout = {
    pageSize: 'A4',
    dpi,
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
    plannedColor: '#00CED1',
    actualColor: '#FFD700',
    indentPerLevel: 20,
    timezone: 'Asia/Jakarta',
    endExclusive: false,
    ...options.layout
  };

  const attachments = [];

  try {
    // 1. Gantt Full Timeline - Planned
    console.log('[RekapReport] Rendering Gantt Planned...');
    const ganttPlannedPages = await renderGanttPaged({
      rows: state.hierarchyRows,
      timeColumns: state.weekColumns,
      planned: state.plannedProgress,
      actual: null, // Planned only
      layout
    });

    ganttPlannedPages.forEach((page, index) => {
      attachments.push({
        title: `Gantt Planned ${page.pageInfo.weekRange}`,
        data_url: page.dataURL,
        format: 'png',
        pageNumber: index + 1,
        section: 'gantt-planned'
      });
    });

    console.log(`[RekapReport] Gantt Planned: ${ganttPlannedPages.length} pages`);

    // 2. Gantt Full Timeline - Actual
    console.log('[RekapReport] Rendering Gantt Actual...');
    const ganttActualPages = await renderGanttPaged({
      rows: state.hierarchyRows,
      timeColumns: state.weekColumns,
      planned: null,
      actual: state.actualProgress, // Actual only
      layout
    });

    ganttActualPages.forEach((page, index) => {
      attachments.push({
        title: `Gantt Actual ${page.pageInfo.weekRange}`,
        data_url: page.dataURL,
        format: 'png',
        pageNumber: index + 1,
        section: 'gantt-actual'
      });
    });

    console.log(`[RekapReport] Gantt Actual: ${ganttActualPages.length} pages`);

    // 3. Kurva S Weekly
    console.log('[RekapReport] Rendering Kurva S Weekly...');
    const kurvaSDataURL = await renderKurvaS({
      granularity: 'weekly',
      data: state.kurvaSData,
      width: 1200,
      height: 600,
      dpi,
      backgroundColor: '#ffffff',
      timezone: layout.timezone
    });

    attachments.push({
      title: 'Kurva S Weekly',
      data_url: kurvaSDataURL,
      format: 'png',
      section: 'kurva-s'
    });

    console.log('[RekapReport] Kurva S Weekly rendered');

    // 4. Generate final output based on format
    console.log(`[RekapReport] Generating final ${format} file...`);

    let result;

    switch (format) {
      case 'pdf':
        result = await generatePDF({
          attachments,
          gridData: null, // Backend akan generate dari state
          reportType: 'rekap',
          options
        });
        break;

      case 'word':
        result = await generateWord({
          attachments,
          gridData: null, // Backend akan generate dari state
          reportType: 'rekap',
          options
        });
        break;

      case 'xlsx':
        // Direct call to backend ExportManager for native Excel with charts
        // DO NOT use generatePDF - that's for image-based export
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
            throw new Error('[RekapReport] projectId is required for xlsx export. Cannot determine project ID.');
          }

          // Call professional export endpoint directly
          const xlsxUrl = `/detail_project/api/project/${projectId}/export/jadwal-pekerjaan/professional/`;

          console.log('[RekapReport] Calling backend xlsx export:', xlsxUrl, 'projectId:', projectId);

          const response = await fetch(xlsxUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || ''
            },
            body: JSON.stringify({
              format: 'xlsx',
              report_type: 'rekap'
            })
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Excel export failed: ${response.status} - ${errorText}`);
          }

          const blob = await response.blob();
          result = {
            blob,
            metadata: {
              reportType: 'rekap',
              format: 'xlsx',
              size: blob.size,
              generatedAt: new Date().toISOString()
            }
          };
        }
        break;

      case 'csv':
        result = {
          blob: generateRekapCSV({
            rows: state.hierarchyRows,
            timeColumns: state.weekColumns,
            planned: state.plannedProgress,
            actual: state.actualProgress
          }),
          metadata: {
            reportType: 'rekap',
            format: 'csv',
            generatedAt: new Date().toISOString()
          }
        };
        break;

      default:
        throw new Error(`[RekapReport] Unsupported format: ${format}`);
    }

    console.log('[RekapReport] Report generated successfully:', {
      format,
      attachments: attachments.length,
      size: result.blob?.size
    });

    return result;

  } catch (error) {
    console.error('[RekapReport] Report generation failed:', error);
    throw error;
  }
}

/**
 * Generate and download Laporan Rekap
 * Convenience function yang langsung trigger download
 *
 * @param {Object} state - Application state
 * @param {string} format - Export format
 * @param {Object} [options={}] - Additional options
 * @param {string} [filename='rekap'] - Base filename
 */
export async function exportRekapReport(state, format, options = {}, filename = 'rekap') {
  const result = await generateRekapReport(state, format, options);

  // Auto-download based on format
  switch (format) {
    case 'pdf':
      downloadPDF(result.blob, filename);
      break;
    case 'word':
      downloadWord(result.blob, filename);
      break;
    case 'xlsx':
      downloadExcel(result.blob, filename);
      break;
    case 'csv':
      downloadCSV(result.blob, filename);
      break;
  }

  return result;
}
