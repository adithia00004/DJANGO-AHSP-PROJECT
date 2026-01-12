/**
 * Gantt Offscreen Renderer
 * Renders Gantt timeline charts with hierarchical labels to offscreen canvas
 *
 * @module export/core/gantt-renderer
 */

import { splitRowsHierarchical, calculateColsPerPage, calculateRowsPerPage } from './pagination-utils.js';

/**
 * Preload fonts untuk consistent text metrics
 * @returns {Promise<void>}
 */
async function preloadFonts() {
  const fonts = [
    new FontFace('Arial', 'local(Arial)'),
    new FontFace('Arial', 'local(Arial Bold)', { weight: 'bold' })
  ];

  await Promise.all(fonts.map(f => f.load()));
  fonts.forEach(f => document.fonts.add(f));
  await document.fonts.ready;
}

/**
 * Format week header dengan interval tanggal
 * @param {number} week - Week number
 * @param {string} startDate - ISO 8601 UTC
 * @param {string} endDate - ISO 8601 UTC (inclusive atau exclusive)
 * @param {string} timezone - Project timezone
 * @param {boolean} endExclusive - Whether endDate is exclusive (00:00:00 next day)
 * @returns {string} Formatted header "W12 (01/03 - 07/03)"
 */
function formatWeekHeader(week, startDate, endDate, timezone = 'Asia/Jakarta', endExclusive = false) {
  const start = new Date(startDate);
  let end = new Date(endDate);

  // If endDate is exclusive, subtract 1 day for display
  if (endExclusive) {
    end = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  }

  const formatter = new Intl.DateTimeFormat('id-ID', {
    day: '2-digit',
    month: '2-digit',
    timeZone: timezone
  });

  const startStr = formatter.format(start);
  const endStr = formatter.format(end);

  return `W${week} (${startStr} - ${endStr})`;
}

/**
 * Calculate segmented bars untuk pekerjaan dengan gap (progress = 0)
 * Returns array of segments: [{ startWeek, endWeek, value }]
 *
 * @param {Object} progressMap - Map: week -> progress value
 * @param {Array<number>} weekRange - Array of week numbers to consider
 * @returns {Array<Object>} Segments
 */
function calculateBarSegments(progressMap, weekRange) {
  const segments = [];
  let currentSegment = null;

  for (const week of weekRange) {
    const progress = progressMap[week] || 0;

    if (progress > 0) {
      if (!currentSegment) {
        // Start new segment
        currentSegment = { startWeek: week, endWeek: week, value: progress };
      } else {
        // Extend current segment
        currentSegment.endWeek = week;
      }
    } else {
      if (currentSegment) {
        // Close current segment (gap found)
        segments.push(currentSegment);
        currentSegment = null;
      }
    }
  }

  // Close last segment if exists
  if (currentSegment) {
    segments.push(currentSegment);
  }

  return segments;
}

/**
 * Render single Gantt page ke canvas
 *
 * @param {HTMLCanvasElement} canvas - Target canvas
 * @param {Object} pageData - Page data
 * @param {Array<Object>} pageData.rows - Rows untuk page ini
 * @param {Array<Object>} pageData.timeColumns - Time columns untuk page ini
 * @param {Object} pageData.planned - Planned progress map
 * @param {Object} pageData.actual - Actual progress map
 * @param {Object} layout - Layout configuration
 * @param {number} pageNumber - Page number (for debugging)
 */
function renderGanttPage(canvas, pageData, layout, pageNumber) {
  const {
    labelWidthPx,
    timeColWidthPx,
    rowHeightPx,
    headerHeightPx = 60,
    fontSize = 11,
    fontFamily = 'Arial',
    backgroundColor = '#ffffff',
    gridColor = '#e0e0e0',
    textColor = '#333333',
    plannedColor = '#00CED1', // cyan
    actualColor = '#FFD700',  // yellow
    indentPerLevel = 20,
    timezone = 'Asia/Jakarta',
    endExclusive = false
  } = layout;

  const { rows, timeColumns, planned, actual } = pageData;

  const ctx = canvas.getContext('2d');

  // Fill background
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Render header area
  renderHeader(ctx, timeColumns, layout);

  // Render label area (left)
  renderLabels(ctx, rows, layout);

  // Render timeline grid
  renderTimelineGrid(ctx, rows, timeColumns, layout);

  // Render bars (planned & actual)
  if (planned) {
    renderBars(ctx, rows, timeColumns, planned, 'planned', layout);
  }
  if (actual) {
    renderBars(ctx, rows, timeColumns, actual, 'actual', layout);
  }

  console.log(`[GanttRenderer] Page ${pageNumber} rendered:`, {
    rows: rows.length,
    timeColumns: timeColumns.length
  });
}

/**
 * Render header dengan week labels
 */
function renderHeader(ctx, timeColumns, layout) {
  const {
    labelWidthPx,
    timeColWidthPx,
    headerHeightPx,
    fontSize,
    fontFamily,
    gridColor,
    textColor,
    backgroundColor,
    timezone,
    endExclusive
  } = layout;

  // Background
  ctx.fillStyle = '#f5f5f5';
  ctx.fillRect(0, 0, labelWidthPx + timeColumns.length * timeColWidthPx, headerHeightPx);

  // Label area header
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0, 0, labelWidthPx, headerHeightPx);
  ctx.fillStyle = textColor;
  ctx.font = `bold ${fontSize}px ${fontFamily}`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText('Uraian Pekerjaan', 10, headerHeightPx / 2);

  // Timeline headers
  ctx.font = `${fontSize}px ${fontFamily}`;
  ctx.textAlign = 'center';

  timeColumns.forEach((col, index) => {
    const x = labelWidthPx + index * timeColWidthPx;

    // Vertical separator
    ctx.strokeStyle = gridColor;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, headerHeightPx);
    ctx.stroke();

    // Week label
    const weekLabel = formatWeekHeader(
      col.week,
      col.startDate,
      col.endDate,
      timezone,
      endExclusive
    );

    // Wrap text jika terlalu panjang
    const maxWidth = timeColWidthPx - 4;
    ctx.fillStyle = textColor;
    ctx.fillText(weekLabel, x + timeColWidthPx / 2, headerHeightPx / 2, maxWidth);
  });

  // Bottom border
  ctx.strokeStyle = gridColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, headerHeightPx);
  ctx.lineTo(labelWidthPx + timeColumns.length * timeColWidthPx, headerHeightPx);
  ctx.stroke();
  ctx.lineWidth = 1;
}

/**
 * Render hierarchical labels (left area)
 */
function renderLabels(ctx, rows, layout) {
  const {
    labelWidthPx,
    rowHeightPx,
    headerHeightPx,
    fontSize,
    fontFamily,
    gridColor,
    textColor,
    indentPerLevel
  } = layout;

  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';

  rows.forEach((row, index) => {
    const y = headerHeightPx + index * rowHeightPx;

    // Row background (alternate colors)
    ctx.fillStyle = index % 2 === 0 ? '#ffffff' : '#f9f9f9';
    ctx.fillRect(0, y, labelWidthPx, rowHeightPx);

    // Horizontal separator
    ctx.strokeStyle = gridColor;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(labelWidthPx, y);
    ctx.stroke();

    // Text dengan indentasi
    const indent = row.level * indentPerLevel;
    const textX = 10 + indent;

    // Font weight berdasarkan type
    let fontWeight = 'normal';
    if (row.type === 'klasifikasi') {
      fontWeight = 'bold';
    } else if (row.type === 'sub-klasifikasi') {
      fontWeight = '600';
    }

    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    ctx.fillStyle = textColor;

    // Truncate text jika terlalu panjang
    const maxWidth = labelWidthPx - textX - 10;
    let displayName = row.name;

    const textWidth = ctx.measureText(displayName).width;
    if (textWidth > maxWidth) {
      // Truncate dengan "..."
      while (ctx.measureText(displayName + '...').width > maxWidth && displayName.length > 0) {
        displayName = displayName.slice(0, -1);
      }
      displayName += '...';
    }

    ctx.fillText(displayName, textX, y + rowHeightPx / 2);
  });

  // Right border
  ctx.strokeStyle = gridColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(labelWidthPx, headerHeightPx);
  ctx.lineTo(labelWidthPx, headerHeightPx + rows.length * rowHeightPx);
  ctx.stroke();
  ctx.lineWidth = 1;
}

/**
 * Render timeline grid (vertical lines)
 */
function renderTimelineGrid(ctx, rows, timeColumns, layout) {
  const {
    labelWidthPx,
    timeColWidthPx,
    rowHeightPx,
    headerHeightPx,
    gridColor
  } = layout;

  ctx.strokeStyle = gridColor;

  // Vertical grid lines
  timeColumns.forEach((col, index) => {
    const x = labelWidthPx + (index + 1) * timeColWidthPx;
    ctx.beginPath();
    ctx.moveTo(x, headerHeightPx);
    ctx.lineTo(x, headerHeightPx + rows.length * rowHeightPx);
    ctx.stroke();
  });

  // Horizontal grid lines
  rows.forEach((row, index) => {
    const y = headerHeightPx + (index + 1) * rowHeightPx;
    ctx.beginPath();
    ctx.moveTo(labelWidthPx, y);
    ctx.lineTo(labelWidthPx + timeColumns.length * timeColWidthPx, y);
    ctx.stroke();
  });
}

/**
 * Render bars (planned atau actual) dengan segmentasi
 */
function renderBars(ctx, rows, timeColumns, progressMap, type, layout) {
  const {
    labelWidthPx,
    timeColWidthPx,
    rowHeightPx,
    headerHeightPx,
    plannedColor,
    actualColor
  } = layout;

  const barColor = type === 'planned' ? plannedColor : actualColor;
  const barHeight = rowHeightPx * 0.6; // 60% of row height
  const barY = (rowHeightPx - barHeight) / 2; // Center vertically

  // Week range dari timeColumns
  const weekRange = timeColumns.map(col => col.week);
  const weekToIndex = {};
  weekRange.forEach((week, index) => {
    weekToIndex[week] = index;
  });

  rows.forEach((row, rowIndex) => {
    // Hanya render bar untuk pekerjaan
    if (row.type !== 'pekerjaan') return;

    const pekerjaanProgress = progressMap[row.id];
    if (!pekerjaanProgress) return;

    // Calculate segments
    const segments = calculateBarSegments(pekerjaanProgress, weekRange);

    // Render each segment
    segments.forEach(segment => {
      const startIdx = weekToIndex[segment.startWeek];
      const endIdx = weekToIndex[segment.endWeek];

      if (startIdx === undefined || endIdx === undefined) return;

      const x = labelWidthPx + startIdx * timeColWidthPx;
      const width = (endIdx - startIdx + 1) * timeColWidthPx;
      const y = headerHeightPx + rowIndex * rowHeightPx + barY;

      // Draw bar
      ctx.fillStyle = barColor;
      ctx.fillRect(x + 2, y, width - 4, barHeight);

      // Border
      ctx.strokeStyle = barColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 2, y, width - 4, barHeight);
    });
  });
}

/**
 * Render Gantt chart dengan pagination
 * Returns multiple pages jika data terlalu besar
 *
 * @param {Object} config - Rendering configuration
 * @param {Array<Object>} config.rows - Hierarchical rows: [{ id, type, name, level, parentId }]
 * @param {Array<Object>} config.timeColumns - Week columns: [{ week, startDate, endDate }]
 * @param {Object} config.planned - Planned progress map: pekerjaan_id -> { week -> progress }
 * @param {Object} config.actual - Actual progress map: pekerjaan_id -> { week -> progress }
 * @param {Object} config.layout - Layout configuration
 * @returns {Promise<Array<Object>>} Array of pages: [{ dataURL, pageInfo }]
 */
export async function renderGanttPaged(config) {
  const {
    rows = [],
    timeColumns = [],
    planned = null,
    actual = null,
    layout = {}
  } = config;

  // Default layout parameters
  const fullLayout = {
    pageSize: 'A4',
    dpi: 300,
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
    ...layout
  };

  console.log('[GanttRenderer] Starting paged rendering:', {
    totalRows: rows.length,
    totalWeeks: timeColumns.length,
    dpi: fullLayout.dpi
  });

  // Preload fonts
  await preloadFonts();

  // Calculate pagination
  const colsPerPage = calculateColsPerPage(fullLayout);
  const rowsPerPage = calculateRowsPerPage(fullLayout);

  console.log('[GanttRenderer] Pagination calculated:', {
    colsPerPage,
    rowsPerPage
  });

  // Split rows dengan hierarchy rules
  const rowPages = splitRowsHierarchical(rows, rowsPerPage);

  // Split time columns
  const timePages = [];
  for (let i = 0; i < timeColumns.length; i += colsPerPage) {
    timePages.push(timeColumns.slice(i, i + colsPerPage));
  }

  // Generate pages (cartesian product: rowPages × timePages)
  const pages = [];
  const DPI_SCALE = fullLayout.dpi / 96;

  for (let rowPageIdx = 0; rowPageIdx < rowPages.length; rowPageIdx++) {
    for (let timePageIdx = 0; timePageIdx < timePages.length; timePageIdx++) {
      const pageRows = rowPages[rowPageIdx];
      const pageTimeCols = timePages[timePageIdx];

      // Calculate canvas size
      const logicalWidth = fullLayout.labelWidthPx + pageTimeCols.length * fullLayout.timeColWidthPx;
      const logicalHeight = fullLayout.headerHeightPx + pageRows.length * fullLayout.rowHeightPx;

      const physicalWidth = Math.round(logicalWidth * DPI_SCALE);
      const physicalHeight = Math.round(logicalHeight * DPI_SCALE);

      // Create canvas
      const canvas = document.createElement('canvas');
      canvas.width = physicalWidth;
      canvas.height = physicalHeight;
      canvas.style.width = `${logicalWidth}px`;
      canvas.style.height = `${logicalHeight}px`;

      const ctx = canvas.getContext('2d');
      ctx.scale(DPI_SCALE, DPI_SCALE);

      // Render page
      const pageData = {
        rows: pageRows,
        timeColumns: pageTimeCols,
        planned,
        actual
      };

      const pageNumber = rowPageIdx * timePages.length + timePageIdx + 1;
      renderGanttPage(canvas, pageData, fullLayout, pageNumber);

      // Convert to dataURL
      const dataURL = canvas.toDataURL('image/png');

      // Page info
      const weekRange = `W${pageTimeCols[0].week}-W${pageTimeCols[pageTimeCols.length - 1].week}`;
      const rowRange = `Rows ${rowPageIdx * rowsPerPage + 1}-${rowPageIdx * rowsPerPage + pageRows.length}`;

      pages.push({
        dataURL,
        pageInfo: {
          pageNumber,
          weekRange,
          rowRange,
          rowCount: pageRows.length,
          weekCount: pageTimeCols.length
        }
      });

      // GC hint
      if (pageNumber % 10 === 0) {
        await new Promise(resolve => setTimeout(resolve, 50));
      }
    }
  }

  console.log(`[GanttRenderer] Rendering completed: ${pages.length} pages generated`);

  return pages;
}
