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

/**
 * Generate Laporan Bulanan (Monthly Report)
 *
 * Konten:
 * - ✅ Kurva S Monthly Progressive (M1=W1-W4, M2=W1-W8, dst)
 * - 🔜 Tabel Progress Bulanan (infrastructure ready, detail menyusul)
 * - 🔜 Summary Statistics (infrastructure ready, detail menyusul)
 *
 * @param {Object} state - Application state
 * @param {Array<Object>} state.kurvaSData - Kurva S data: [{ week, planned, actual }]
 * @param {string} format - Export format: 'pdf' | 'word' | 'xlsx' | 'csv'
 * @param {number} month - Target month number (untuk filtering data, if needed)
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
    // 1. Kurva S Monthly Progressive (DEFINED)
    console.log('[MonthlyReport] Rendering Kurva S Monthly Progressive...');
    const kurvaSMonthlyURL = await renderKurvaS({
      granularity: 'monthly',
      weeks_per_month: 4,
      data: state.kurvaSData,
      width: 1200,
      height: 600,
      dpi,
      backgroundColor: '#ffffff',
      timezone: options.timezone || 'Asia/Jakarta'
    });

    attachments.push({
      title: 'Kurva S Monthly Progressive',
      data_url: kurvaSMonthlyURL,
      format: 'png',
      section: 'kurva-s-monthly'
    });

    console.log('[MonthlyReport] Kurva S Monthly rendered');

    // 2. Tabel Progress Bulanan (TBD - infrastructure ready)
    // TODO: Implement when details are provided
    // Expected structure:
    // {
    //   headers: ['Pekerjaan', 'Progress Bulan Lalu (%)', 'Progress Bulan Ini (%)', 'Total Progress Project (%)'],
    //   rows: [...]
    // }
    const monthlyProgressTable = null; // Placeholder

    if (monthlyProgressTable) {
      console.log('[MonthlyReport] Monthly Progress Table provided');
    } else {
      console.warn('[MonthlyReport] Monthly Progress Table not yet implemented (awaiting specification)');
    }

    // 3. Summary Statistics (TBD - infrastructure ready)
    // TODO: Implement when details are provided
    const summaryStats = null; // Placeholder

    if (summaryStats) {
      console.log('[MonthlyReport] Summary Statistics provided');
    } else {
      console.warn('[MonthlyReport] Summary Statistics not yet implemented (awaiting specification)');
    }

    // 4. Generate final output based on format
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
        result = await generateExcel({
          reportType: 'monthly',
          attachments,
          monthlyProgressTable,
          summaryStats
        });
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
