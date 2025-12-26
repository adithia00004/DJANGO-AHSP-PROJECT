/**
 * Excel Generator
 * Generate Excel (.xlsx) files dengan ExcelJS
 * Multi-sheet dengan data tabel + embedded chart images
 *
 * @module export/generators/excel-generator
 */

import ExcelJS from 'exceljs';

/**
 * Convert base64 dataURL to buffer
 * @param {string} dataURL - PNG dataURL (base64)
 * @returns {ArrayBuffer} Image buffer
 */
function dataURLToBuffer(dataURL) {
  const base64 = dataURL.split(',')[1];
  const byteString = atob(base64);
  const ab = new ArrayBuffer(byteString.length);
  const ia = new Uint8Array(ab);
  for (let i = 0; i < byteString.length; i++) {
    ia[i] = byteString.charCodeAt(i);
  }
  return ab;
}

/**
 * Prepare grid data untuk Excel sheet
 * Converts hierarchical rows + week columns to Excel table format
 *
 * @param {Array<Object>} rows - Hierarchical rows
 * @param {Array<Object>} timeColumns - Time columns
 * @param {Object} planned - Planned progress map
 * @param {Object} actual - Actual progress map
 * @returns {Object} { headers, data }
 */
function prepareGridData(rows, timeColumns, planned, actual) {
  // Headers: Uraian Pekerjaan | W1 Planned | W1 Actual | W2 Planned | W2 Actual | ...
  const headers = ['Uraian Pekerjaan'];
  timeColumns.forEach(col => {
    headers.push(`W${col.week} Planned`);
    headers.push(`W${col.week} Actual`);
  });

  // Data rows
  const data = rows.map(row => {
    const rowData = [row.name];

    timeColumns.forEach(col => {
      const week = col.week;

      // Planned progress
      const plannedVal = (row.type === 'pekerjaan' && planned && planned[row.id])
        ? (planned[row.id][week] || 0)
        : '';

      // Actual progress
      const actualVal = (row.type === 'pekerjaan' && actual && actual[row.id])
        ? (actual[row.id][week] || 0)
        : '';

      rowData.push(plannedVal);
      rowData.push(actualVal);
    });

    return {
      cells: rowData,
      level: row.level,
      type: row.type
    };
  });

  return { headers, data };
}

/**
 * Generate Excel file dengan data table + chart images
 *
 * @param {Object} config - Configuration
 * @param {string} config.reportType - 'rekap', 'monthly', 'weekly'
 * @param {Array<Object>} config.attachments - Chart attachments: [{ title, data_url, format }]
 * @param {Array<Object>} [config.rows] - Hierarchical rows (for data sheet)
 * @param {Array<Object>} [config.timeColumns] - Time columns (for data sheet)
 * @param {Object} [config.planned] - Planned progress map
 * @param {Object} [config.actual] - Actual progress map
 * @param {Object} [config.monthlyProgressTable] - Monthly progress table (for monthly report)
 * @param {Object} [config.summaryStats] - Summary statistics (for monthly report)
 * @returns {Promise<Blob>} Excel file blob
 */
export async function generateExcel(config) {
  const {
    reportType = 'rekap',
    attachments = [],
    rows = [],
    timeColumns = [],
    planned = null,
    actual = null,
    monthlyProgressTable = null,
    summaryStats = null
  } = config;

  console.log('[ExcelGenerator] Generating Excel file:', {
    reportType,
    attachmentsCount: attachments.length,
    rowsCount: rows.length
  });

  // Create workbook
  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'AHSP Export System';
  workbook.created = new Date();

  // Sheet 1: Data Table (if rows provided)
  if (rows.length > 0 && timeColumns.length > 0) {
    const dataSheet = workbook.addWorksheet('Data');

    const { headers, data } = prepareGridData(rows, timeColumns, planned, actual);

    // Add headers
    const headerRow = dataSheet.addRow(headers);
    headerRow.font = { bold: true };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFE0E0E0' }
    };

    // Add data rows
    data.forEach(rowData => {
      const excelRow = dataSheet.addRow(rowData.cells);

      // Apply styling based on hierarchy
      if (rowData.type === 'klasifikasi') {
        excelRow.font = { bold: true };
        excelRow.fill = {
          type: 'pattern',
          pattern: 'solid',
          fgColor: { argb: 'FFF5F5F5' }
        };
      } else if (rowData.type === 'sub-klasifikasi') {
        excelRow.font = { bold: false, italic: true };
      }

      // Indent based on level
      const indent = rowData.level * 2;
      excelRow.getCell(1).alignment = { indent };
    });

    // Auto-fit columns (first column wider)
    dataSheet.getColumn(1).width = 50;
    for (let i = 2; i <= headers.length; i++) {
      dataSheet.getColumn(i).width = 12;
    }

    // Freeze panes (header row)
    dataSheet.views = [
      { state: 'frozen', xSplit: 0, ySplit: 1 }
    ];
  }

  // Add chart image sheets
  for (let i = 0; i < attachments.length; i++) {
    const attachment = attachments[i];

    if (attachment.format !== 'png' || !attachment.data_url) {
      console.warn(`[ExcelGenerator] Skipping invalid attachment ${i}: ${attachment.title}`);
      continue;
    }

    // Create sheet for this chart
    const sheetName = attachment.title.substring(0, 31); // Excel sheet name limit: 31 chars
    const chartSheet = workbook.addWorksheet(sheetName);

    // Convert dataURL to buffer
    const imageBuffer = dataURLToBuffer(attachment.data_url);

    // Add image to workbook
    const imageId = workbook.addImage({
      buffer: imageBuffer,
      extension: 'png'
    });

    // Insert image to sheet (top-left corner)
    chartSheet.addImage(imageId, {
      tl: { col: 0, row: 0 }, // Top-left: A1
      ext: { width: 800, height: 400 } // Display size (adjust as needed)
    });

    console.log(`[ExcelGenerator] Added chart sheet: ${sheetName}`);
  }

  // Add Monthly Progress Table sheet (jika ada)
  if (monthlyProgressTable) {
    const monthlySheet = workbook.addWorksheet('Progress Bulanan');
    // TODO: Implement when monthlyProgressTable structure is defined
    monthlySheet.addRow(['Placeholder for Monthly Progress Table']);
  }

  // Add Summary Stats sheet (jika ada)
  if (summaryStats) {
    const summarySheet = workbook.addWorksheet('Summary');
    // TODO: Implement when summaryStats structure is defined
    summarySheet.addRow(['Placeholder for Summary Statistics']);
  }

  // Generate Excel buffer
  const buffer = await workbook.xlsx.writeBuffer();

  // Convert to Blob
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  });

  console.log('[ExcelGenerator] Excel file generated:', {
    size: blob.size,
    sheetCount: workbook.worksheets.length
  });

  return {
    blob,
    metadata: {
      reportType,
      format: 'xlsx',
      sheetCount: workbook.worksheets.length,
      size: blob.size,
      generatedAt: new Date().toISOString()
    }
  };
}

/**
 * Download Excel file to user's computer
 * @param {Blob} blob - Excel file blob
 * @param {string} filename - Filename (without extension)
 */
export function downloadExcel(blob, filename = 'export') {
  // Validate blob
  if (!blob || !(blob instanceof Blob)) {
    console.error('[ExcelGenerator] Invalid blob:', blob);
    throw new Error('Invalid blob provided to downloadExcel');
  }

  console.log('[ExcelGenerator] Downloading file:', {
    filename: `${filename}.xlsx`,
    size: blob.size,
    type: blob.type
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.xlsx`;
  document.body.appendChild(a);
  a.click();

  // Clean up with slight delay to ensure download starts
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.log('[ExcelGenerator] File downloaded:', `${filename}.xlsx`);
  }, 100);
}
