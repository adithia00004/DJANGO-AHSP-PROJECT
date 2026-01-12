/**
 * CSV Generator
 * Generate CSV files dengan UTF-8 BOM untuk Excel Windows compatibility
 *
 * @module export/generators/csv-generator
 */

/**
 * Escape CSV value
 * Wraps dalam quotes jika contains delimiter/newline/quotes
 *
 * @param {*} value - Value to escape
 * @param {string} delimiter - CSV delimiter
 * @returns {string} Escaped value
 */
function escapeCSV(value, delimiter = ';') {
  if (value == null || value === '') return '';

  const str = String(value);

  // Check if needs quoting
  const needsQuoting =
    str.includes(delimiter) ||
    str.includes(',') ||
    str.includes('\n') ||
    str.includes('\r') ||
    str.includes('"');

  if (needsQuoting) {
    // Escape quotes by doubling them
    const escaped = str.replace(/"/g, '""');
    return `"${escaped}"`;
  }

  return str;
}

/**
 * Generate CSV content dari table data
 *
 * @param {Object} config - Configuration
 * @param {Array<string>} config.headers - Table headers
 * @param {Array<Array>} config.rows - Table rows
 * @param {string} [config.delimiter=';'] - CSV delimiter (';' for Excel Windows)
 * @param {boolean} [config.addBOM=true] - Add UTF-8 BOM for Excel Windows
 * @returns {Blob} CSV blob
 */
export function generateCSV(config) {
  const {
    headers = [],
    rows = [],
    delimiter = ';',
    addBOM = true
  } = config;

  console.log('[CSVGenerator] Generating CSV:', {
    headers: headers.length,
    rows: rows.length,
    delimiter
  });

  // Build CSV string
  let csv = '';

  // Add headers
  if (headers.length > 0) {
    csv += headers.map(h => escapeCSV(h, delimiter)).join(delimiter) + '\r\n';
  }

  // Add data rows
  rows.forEach(row => {
    const cells = Array.isArray(row) ? row : (row.cells || []);
    csv += cells.map(cell => escapeCSV(cell, delimiter)).join(delimiter) + '\r\n';
  });

  // Add UTF-8 BOM (required untuk Excel Windows detect UTF-8)
  const BOM = '\uFEFF';
  const content = addBOM ? BOM + csv : csv;

  // Create Blob
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });

  console.log('[CSVGenerator] CSV generated:', {
    size: blob.size,
    withBOM: addBOM
  });

  return blob;
}

/**
 * Prepare grid data untuk CSV export
 * Converts hierarchical rows + week columns to CSV table format
 *
 * @param {Array<Object>} rows - Hierarchical rows
 * @param {Array<Object>} timeColumns - Time columns
 * @param {Object} planned - Planned progress map
 * @param {Object} actual - Actual progress map
 * @returns {Object} { headers, rows }
 */
export function prepareGridDataForCSV(rows, timeColumns, planned, actual) {
  // Headers: Uraian Pekerjaan | W1 Planned | W1 Actual | W2 Planned | W2 Actual | ...
  const headers = ['Uraian Pekerjaan'];
  timeColumns.forEach(col => {
    headers.push(`W${col.week} Planned`);
    headers.push(`W${col.week} Actual`);
  });

  // Data rows
  const dataRows = rows.map(row => {
    const cells = [row.name];

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

      cells.push(plannedVal);
      cells.push(actualVal);
    });

    return cells;
  });

  return { headers, rows: dataRows };
}

/**
 * Generate CSV untuk Laporan Rekap
 *
 * @param {Object} config - Configuration
 * @param {Array<Object>} config.rows - Hierarchical rows
 * @param {Array<Object>} config.timeColumns - Time columns
 * @param {Object} config.planned - Planned progress map
 * @param {Object} config.actual - Actual progress map
 * @returns {Blob} CSV blob
 */
export function generateRekapCSV(config) {
  const { rows, timeColumns, planned, actual } = config;

  const { headers, rows: dataRows } = prepareGridDataForCSV(
    rows,
    timeColumns,
    planned,
    actual
  );

  return generateCSV({
    headers,
    rows: dataRows,
    delimiter: ';',
    addBOM: true
  });
}

/**
 * Generate CSV untuk Monthly Progress Table (placeholder)
 *
 * @param {Object} config - Configuration
 * @returns {Blob} CSV blob
 */
export function generateMonthlyProgressCSV(config) {
  // TODO: Implement when monthlyProgressTable structure is defined
  const headers = ['Pekerjaan', 'Progress Bulan Lalu (%)', 'Progress Bulan Ini (%)', 'Total Progress Project (%)'];
  const rows = [
    ['Placeholder', '0', '0', '0']
  ];

  return generateCSV({
    headers,
    rows,
    delimiter: ';',
    addBOM: true
  });
}

/**
 * Generate CSV untuk Weekly Progress Table
 *
 * @param {Object} config - Configuration
 * @param {Object} [config.weeklyProgressTable] - Weekly progress table { headers, rows }
 * @returns {Blob} CSV blob
 */
export function generateWeeklyProgressCSV(config = {}) {
  const { weeklyProgressTable } = config;

  if (weeklyProgressTable && Array.isArray(weeklyProgressTable.headers) && Array.isArray(weeklyProgressTable.rows)) {
    return generateCSV({
      headers: weeklyProgressTable.headers,
      rows: weeklyProgressTable.rows,
      delimiter: ';',
      addBOM: true
    });
  }

  // Placeholder jika belum ada struktur table
  const headers = [
    'Pekerjaan',
    'Total Harga',
    'Bobot Pekerjaan (%)',
    'Target Planned Minggu Ini (%)',
    'Actual Minggu Ini (%)',
    'Kumulatif Target (%)',
    'Kumulatif Actual (%)'
  ];

  const rows = [['Placeholder', '0', '0', '0', '0', '0', '0']];

  return generateCSV({
    headers,
    rows,
    delimiter: ';',
    addBOM: true
  });
}

/**
 * Download CSV file to user's computer
 * @param {Blob} blob - CSV file blob
 * @param {string} filename - Filename (without extension)
 */
export function downloadCSV(blob, filename = 'export') {
  const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
  const fullFilename = `Laporan_${filename}_${timestamp}.csv`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fullFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log('[CSVGenerator] File downloaded:', fullFilename);
}
