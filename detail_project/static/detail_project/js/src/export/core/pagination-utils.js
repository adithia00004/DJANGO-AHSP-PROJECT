/**
 * Pagination Utilities
 * Helper functions untuk pagination calculation (colsPerPage, rowsPerPage, hierarchy splitting)
 *
 * @module export/core/pagination-utils
 */

/**
 * Convert mm to px based on DPI
 * @param {number} mm - Millimeters
 * @param {number} dpi - Dots per inch
 * @returns {number} Pixels
 */
export function mmToPx(mm, dpi = 96) {
  return Math.round((mm * dpi) / 25.4);
}

/**
 * Page sizes dalam mm (landscape)
 */
const PAGE_SIZES = {
  A4: { width: 297, height: 210 },
  A3: { width: 420, height: 297 },
  A2: { width: 594, height: 420 }
};

/**
 * Calculate columns per page based on page size and layout
 *
 * @param {Object} layout - Layout configuration
 * @param {string} layout.pageSize - 'A4', 'A3', or 'A2'
 * @param {number} layout.dpi - Target DPI
 * @param {number} layout.labelWidthPx - Label area width in px
 * @param {number} layout.timeColWidthPx - Time column width in px
 * @param {number} layout.marginMm - Page margin in mm
 * @returns {number} Columns per page
 */
export function calculateColsPerPage(layout) {
  const {
    pageSize = 'A4',
    dpi = 300,
    labelWidthPx = 600,
    timeColWidthPx = 70,
    marginMm = 20
  } = layout;

  const pageSizeMm = PAGE_SIZES[pageSize] || PAGE_SIZES.A4;
  const pageWidthPx = mmToPx(pageSizeMm.width, dpi);
  const marginPx = mmToPx(marginMm, dpi);

  const availableWidth = pageWidthPx - (2 * marginPx) - labelWidthPx;
  const colsPerPage = Math.max(1, Math.floor(availableWidth / timeColWidthPx));

  return colsPerPage;
}

/**
 * Calculate rows per page based on page size and layout
 *
 * @param {Object} layout - Layout configuration
 * @param {string} layout.pageSize - 'A4', 'A3', or 'A2'
 * @param {number} layout.dpi - Target DPI
 * @param {number} layout.rowHeightPx - Row height in px
 * @param {number} layout.headerHeightPx - Header area height in px
 * @param {number} layout.marginMm - Page margin in mm
 * @returns {number} Rows per page
 */
export function calculateRowsPerPage(layout) {
  const {
    pageSize = 'A4',
    dpi = 300,
    rowHeightPx = 28,
    headerHeightPx = 60,
    marginMm = 20
  } = layout;

  const pageSizeMm = PAGE_SIZES[pageSize] || PAGE_SIZES.A4;
  const pageHeightPx = mmToPx(pageSizeMm.height, dpi);
  const marginPx = mmToPx(marginMm, dpi);

  const availableHeight = pageHeightPx - (2 * marginPx) - headerHeightPx;
  const rowsPerPage = Math.max(1, Math.floor(availableHeight / rowHeightPx));

  return rowsPerPage;
}

/**
 * Auto-select page size based on total weeks
 * Returns optimal page size (A4/A3/A2) untuk menampung semua minggu tanpa pagination
 * Jika tetap tidak cukup, return A2 + akan di-paginate
 *
 * @param {number} totalWeeks - Total weeks in dataset
 * @param {number} timeColWidthPx - Time column width in px
 * @param {number} labelWidthPx - Label area width in px
 * @param {number} marginMm - Page margin in mm
 * @param {number} dpi - Target DPI
 * @returns {string} Page size: 'A4', 'A3', or 'A2'
 */
export function selectPageSize(totalWeeks, timeColWidthPx = 70, labelWidthPx = 600, marginMm = 20, dpi = 300) {
  const totalTimelineWidth = totalWeeks * timeColWidthPx;
  const marginPx = mmToPx(marginMm, dpi);
  const requiredPageWidth = labelWidthPx + totalTimelineWidth + (2 * marginPx);

  const a4WidthPx = mmToPx(PAGE_SIZES.A4.width, dpi);
  const a3WidthPx = mmToPx(PAGE_SIZES.A3.width, dpi);
  const a2WidthPx = mmToPx(PAGE_SIZES.A2.width, dpi);

  if (requiredPageWidth <= a4WidthPx) {
    return 'A4';
  } else if (requiredPageWidth <= a3WidthPx) {
    return 'A3';
  } else {
    return 'A2'; // Max size, akan di-paginate jika tetap tidak cukup
  }
}

/**
 * Split rows dengan aturan hierarki yang robust untuk nested structure
 * Implements Header Chain Stack by Level algorithm
 *
 * @param {Array<Object>} rows - Flat array with { id, type, level, parentId, name }
 * @param {number} rowsPerPage - Maximum rows per page
 * @returns {Array<Array<Object>>} Pages with injected repeat headers
 */
export function splitRowsHierarchical(rows, rowsPerPage) {
  if (!rows || rows.length === 0) {
    return [];
  }

  if (rowsPerPage <= 0) {
    throw new Error('[PaginationUtils] rowsPerPage must be > 0');
  }

  const pages = [];
  let currentPage = [];

  // Header chain stack: map level → header row
  // Contoh: Map { 0: klasifikasiRow, 1: subKlasifikasiRow }
  const headerChainByLevel = new Map();

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const level = row.level;
    const isHeader = row.type === 'klasifikasi' || row.type === 'sub-klasifikasi';

    // Check if page is full BEFORE adding this row
    if (currentPage.length >= rowsPerPage) {
      // Check if last item is orphaned header (no children in this page)
      const lastRow = currentPage[currentPage.length - 1];
      const isLastOrphaned =
        (lastRow.type === 'klasifikasi' || lastRow.type === 'sub-klasifikasi') &&
        (currentPage.length === 1 || // Only header in page
         currentPage[currentPage.length - 1] === lastRow); // No child after it

      if (isLastOrphaned) {
        // Remove orphaned header, akan di-inject ke page berikutnya
        currentPage.pop();
      }

      // Commit current page
      if (currentPage.length > 0) {
        pages.push([...currentPage]);
      }
      currentPage = [];

      // Inject header chain dengan "(lanj.)" suffix
      // Urutkan by level (ascending) untuk maintain hierarchy
      const sortedLevels = Array.from(headerChainByLevel.keys()).sort((a, b) => a - b);
      for (const lvl of sortedLevels) {
        const header = headerChainByLevel.get(lvl);
        currentPage.push({
          ...header,
          name: `${header.name} (lanj.)`
        });
      }
    }

    // Add current row to page
    currentPage.push(row);

    // Update header chain
    if (isHeader) {
      // Set header untuk level ini
      headerChainByLevel.set(level, row);

      // Clear headers di level lebih dalam (karena context berubah)
      // Contoh: jika row ini level 0, hapus header level 1, 2, dst
      const levelsToRemove = Array.from(headerChainByLevel.keys())
        .filter(lvl => lvl > level);
      levelsToRemove.forEach(lvl => headerChainByLevel.delete(lvl));
    } else if (row.type === 'pekerjaan') {
      // Pekerjaan row: tidak modify header chain, tapi ini artinya headers punya child
      // (jadi tidak orphaned lagi)
    }
  }

  // Add last page
  if (currentPage.length > 0) {
    pages.push(currentPage);
  }

  return pages;
}

/**
 * Validate rows untuk memastikan struktur hierarki benar
 * Returns validation errors atau empty array jika valid
 *
 * @param {Array<Object>} rows - Rows to validate
 * @returns {Array<string>} Validation errors (empty if valid)
 */
export function validateRowsHierarchy(rows) {
  const errors = [];

  rows.forEach((row, index) => {
    // Check required fields
    if (!row.id) {
      errors.push(`Row ${index}: missing 'id' field`);
    }
    if (!row.type) {
      errors.push(`Row ${index}: missing 'type' field`);
    }
    if (row.level === undefined) {
      errors.push(`Row ${index}: missing 'level' field`);
    }
    if (!row.name) {
      errors.push(`Row ${index}: missing 'name' field`);
    }

    // Check type values
    if (row.type && !['klasifikasi', 'sub-klasifikasi', 'pekerjaan'].includes(row.type)) {
      errors.push(`Row ${index}: invalid type '${row.type}'`);
    }

    // Check level consistency
    if (row.type === 'klasifikasi' && row.level !== 0) {
      errors.push(`Row ${index}: klasifikasi should have level 0, got ${row.level}`);
    }
    if (row.type === 'sub-klasifikasi' && row.level !== 1) {
      errors.push(`Row ${index}: sub-klasifikasi should have level 1, got ${row.level}`);
    }
    if (row.type === 'pekerjaan' && row.level < 1) {
      errors.push(`Row ${index}: pekerjaan should have level >= 1, got ${row.level}`);
    }
  });

  return errors;
}

/**
 * Calculate estimated page count before rendering
 * Useful untuk showing progress bar atau warning
 *
 * @param {number} totalRows - Total rows
 * @param {number} totalWeeks - Total weeks
 * @param {Object} layout - Layout configuration
 * @returns {Object} { rowPages, timePages, totalPages }
 */
export function estimatePageCount(totalRows, totalWeeks, layout) {
  const colsPerPage = calculateColsPerPage(layout);
  const rowsPerPage = calculateRowsPerPage(layout);

  const rowPages = Math.ceil(totalRows / rowsPerPage);
  const timePages = Math.ceil(totalWeeks / colsPerPage);
  const totalPages = rowPages * timePages;

  return {
    rowPages,
    timePages,
    totalPages,
    rowsPerPage,
    colsPerPage
  };
}
