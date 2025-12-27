/**
 * Kurva-S Canvas Overlay
 * Plots S-curve as overlay on top of table grid
 * - Y-axis inverted: 0% at bottom (last row), 100% at top (first row)
 * - X-axis: Plots at center of each week column
 * - Shows both planned and actual curves
 * - Y-axis labels on right side of table
 * - Legend for planned vs actual
 */

import { createCanvas, createClipViewport, getContext2D, hitTestPoint, isDarkMode } from './canvas-utils.js';
import { TooltipManager, createLegend, updateLegendColors } from './tooltip-manager.js';
import { StateManager } from '../core/state-manager.js';

export class KurvaSCanvasOverlay {
  constructor(tableManager, options = {}) {
    this.tableManager = tableManager;
    this.debug = Boolean(
      this.tableManager?.options?.debugUnifiedTable ||
      this.tableManager?.state?.debugUnifiedTable ||
      window.DEBUG_UNIFIED_TABLE
    );
    this._missingColumnLog = new Set();

    // Track scroll position and pinned width
    this.scrollLeft = 0;
    this.scrollTop = 0;
    this.pinnedWidth = 0;

    // PHASE 4 FIX: Cost mode support
    this.mode = 'progress';  // 'progress' or 'cost'
    this.projectId = options.projectId || null;

    // Main canvas for curve plotting
    this.canvas = createCanvas('kurva-s-canvas-overlay');
    this.ctx = getContext2D(this.canvas);

    // ClipViewport wrapper - FIXED overlay that clips canvas to visible area
    // z-index 10 is sufficient to be above bodyScroll for mouse events
    this.clipViewport = createClipViewport('kurva-s-clip-viewport', 10);
    // Canvas goes inside clipViewport
    this.clipViewport.appendChild(this.canvas);

    this.visible = false;
    this.curveData = { planned: [], actual: [] };
    this.legendElement = null;
    this.curvePoints = []; // For tooltip hit-testing
    this.tooltipManager = new TooltipManager({ zIndex: 50 });

    // Scroll handler: Update CSS transform to sync canvas with scroll (viewport concept)
    // Only transform update needed - no re-render for performance
    const scrollTarget = this.tableManager?.bodyScroll;
    if (scrollTarget) {
      scrollTarget.addEventListener('scroll', () => {
        if (this.visible) {
          this._updateTransform();
        }
      }, { passive: true });
    }

    // Resize handler: RE-RENDERS canvas when size changes (e.g., fullscreen toggle)
    // This is needed because canvas size changes, requiring new drawing
    this._resizeTimeout = null;
    window.addEventListener('resize', () => {
      if (this.visible) {
        // Debounce: wait for resize to settle, then re-render once
        clearTimeout(this._resizeTimeout);
        this._resizeTimeout = setTimeout(() => {
          this.syncWithTable();
        }, 150);
      }
    });

    this._bindPointerEvents();
  }

  show() {
    this._log('show', { alreadyVisible: this.visible });
    if (this.visible) return;
    const scrollArea = this.tableManager?.bodyScroll;
    const container = scrollArea?.parentElement;
    if (!scrollArea || !container) return;

    // Ensure container has relative positioning for fixed overlay
    container.style.position = 'relative';

    // Add clipViewport to CONTAINER as SIBLING of bodyScroll (FIXED viewport overlay)
    // With z-index 1000, clipViewport is above bodyScroll for mouse events
    if (this.clipViewport.parentNode) {
      this.clipViewport.parentNode.removeChild(this.clipViewport);
    }
    container.appendChild(this.clipViewport);

    this._log('clipViewport-attached', {
      clipViewportInDOM: !!this.clipViewport.parentNode,
      canvasInClipViewport: !!this.canvas.parentNode,
      zIndex: this.clipViewport.style.zIndex,
      canvasPointerEvents: this.canvas.style.pointerEvents,
      clipViewportPointerEvents: this.clipViewport.style.pointerEvents
    });

    this.visible = true;
    this._log('show', { overlay: true, container: 'sibling-of-bodyScroll', zIndex: 10 });
    this._showLegend();

    // Data will be provided by UnifiedTableManager._refreshKurvaSOverlay() → renderCurve()
    // This uses _buildCurveData() which uses StateManager - same data source as Gantt
    this._waitForCellsAndRender();
  }

  /**
   * Fetch curve data from SSoT API via StateManager
   * @returns {Promise<void>}
   */
  async _fetchCurveDataFromAPI() {
    try {
      const stateManager = StateManager.getInstance();

      // Set project ID if available
      if (this.projectId && !stateManager.projectId) {
        stateManager.setProjectId(this.projectId);
      }

      // Determine timescale (default weekly, can be changed by setTimescale)
      const timescale = this.timescale || 'weekly';

      // Fetch from SSoT API
      const chartData = await stateManager.fetchChartData(timescale, 'both');

      if (chartData && chartData.curveData) {
        this._log('curveData-from-api', {
          timescale,
          plannedPoints: chartData.curveData.planned?.length || 0,
          actualPoints: chartData.curveData.actual?.length || 0
        });

        // Convert API format to internal format
        this.curveData = {
          planned: this._convertApiCurveData(chartData.curveData.planned, 'planned'),
          actual: this._convertApiCurveData(chartData.curveData.actual, 'actual')
        };
      } else {
        this._log('curveData-fallback', { reason: 'API returned no curveData' });
        // Fallback: keep existing curveData or use empty
      }
    } catch (error) {
      this._log('curveData-error', { error: error.message });
      // On error, proceed with existing curveData
    }
  }

  /**
   * Convert API curve data format to internal format
   * @param {Array} apiData - Array of {weekNumber/monthNumber, cumulative, label}
   * @param {string} type - 'planned' or 'actual'
   * @returns {Array} Internal format {columnId, progress, ...}
   */
  _convertApiCurveData(apiData, type) {
    if (!Array.isArray(apiData)) return [];

    return apiData.map(point => {
      const weekNumber = point.weekNumber;
      const monthNumber = point.monthNumber;

      // Build columnId in format matching grid cells 
      // Grid uses 'col_X' where X is the column index (0-based)
      // But API returns weekNumber (1-based), so we try multiple formats
      const columnId = weekNumber != null
        ? String(weekNumber)  // Try as string first, _mapDataToCanvasPoints will handle it
        : monthNumber != null
          ? String(monthNumber)
          : null;

      return {
        columnId,          // Primary lookup key
        weekId: weekNumber != null ? String(weekNumber) : null,
        week: weekNumber,  // Numeric week for fallback
        month: monthNumber,
        progress: point.cumulative || 0,
        cumulative: point.cumulative || 0,
        cumulativeProgress: point.cumulative || 0,  // Add this for _mapDataToCanvasPoints
        label: point.label || '',
        type
      };
    });
  }

  /**
   * Set timescale for curve data (weekly or monthly)
   * @param {string} timescale - 'weekly' or 'monthly'
   */
  setTimescale(timescale) {
    if (timescale !== this.timescale) {
      this.timescale = timescale;
      // Invalidate cached curve data
      this.curveData = { planned: [], actual: [] };
      // If visible, refetch and re-render
      if (this.visible) {
        this._fetchCurveDataFromAPI().then(() => {
          this.syncWithTable();
        });
      }
    }
  }

  hide() {
    if (!this.visible) return;

    // Remove clipViewport (which contains canvas)
    if (this.clipViewport.parentNode) {
      this.clipViewport.parentNode.removeChild(this.clipViewport);
    }

    this.visible = false;
    this._log('hide');
    this._hideLegend();
    this.tooltipManager.hide();
  }

  syncWithTable() {
    const scrollArea = this.tableManager?.bodyScroll;
    const container = scrollArea?.parentElement;
    if (!scrollArea || !container) {
      this._log('warn-no-scroll-area', { message: 'No scrollArea found' });
      return;
    }

    // Get cell rects FIRST to determine canvas bounds
    // Use getAllCellBoundingRects for virtual calculation (all cells) like Gantt
    // Fallback to getCellBoundingRects for visible-only cells
    const cellRects = typeof this.tableManager.getAllCellBoundingRects === 'function'
      ? this.tableManager.getAllCellBoundingRects()
      : typeof this.tableManager.getCellBoundingRects === 'function'
        ? this.tableManager.getCellBoundingRects()
        : [];

    if (cellRects.length === 0) {
      this._log('warn-no-cell-rects', { message: 'No cell rects available for plotting' });
      return;
    }

    // Update pinned width and scroll position
    this.pinnedWidth = this._getPinnedWidth(scrollArea);
    this.scrollLeft = scrollArea.scrollLeft || 0;
    this.scrollTop = scrollArea.scrollTop || 0;

    // Calculate actual grid bounds from cellRects
    // X: from first week column to last week column
    // Y: from first row to last row
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    cellRects.forEach(rect => {
      // Only consider week columns (after pinned columns)
      if (rect.x >= this.pinnedWidth) {
        minX = Math.min(minX, rect.x);
        maxX = Math.max(maxX, rect.x + rect.width);
      }
      minY = Math.min(minY, rect.y);
      maxY = Math.max(maxY, rect.y + rect.height);
    });

    // Fallback if no valid cells found
    if (minX === Infinity || maxX === -Infinity) {
      minX = this.pinnedWidth;
      maxX = scrollArea.scrollWidth;
    }
    if (minY === Infinity || maxY === -Infinity) {
      minY = 0;
      maxY = scrollArea.scrollHeight;
    }

    // Grid dimensions - INCLUDE Week 0 space at left edge
    // gridLeft starts at pinnedWidth (left boundary of week columns area)
    // This ensures Week 0 (at x=0 in canvas) is visible
    const gridLeft = this.pinnedWidth;  // Start from frozen column boundary, not first cell
    const gridWidth = maxX - gridLeft;  // Width from frozen boundary to last week
    const gridHeight = maxY - minY;
    const gridTop = minY;

    // Get header height for clipViewport positioning
    const header = container.querySelector('.tanstack-grid-header');
    const headerHeight = header?.offsetHeight || 0;

    const containerRect = container.getBoundingClientRect();
    const scrollAreaRect = scrollArea.getBoundingClientRect();

    // Viewport margins
    const marginLeft = 5;
    const marginRight = 20;
    const marginBottom = 15;

    // ClipViewport: FIXED overlay - shows only visible portion of canvas
    // Positioned at frozen column boundary, below header
    const viewportWidth = containerRect.width - this.pinnedWidth - marginLeft - marginRight;
    const viewportHeight = scrollAreaRect.height - marginBottom;

    this.clipViewport.style.left = `${this.pinnedWidth + marginLeft}px`;
    this.clipViewport.style.top = `${headerHeight}px`;
    this.clipViewport.style.width = `${viewportWidth}px`;
    this.clipViewport.style.height = `${viewportHeight}px`;
    this.clipViewport.style.overflow = 'hidden'; // CLIP canvas to visible area

    // Canvas: FULL content size - moves via CSS transform
    const MAX_CANVAS_WIDTH = 32000;
    const MAX_CANVAS_HEIGHT = 16000;
    const canvasWidth = Math.min(Math.max(100, gridWidth), MAX_CANVAS_WIDTH);
    const canvasHeight = Math.min(Math.max(100, gridHeight), MAX_CANVAS_HEIGHT);

    this.canvas.width = canvasWidth;
    this.canvas.height = canvasHeight;
    this.canvas.style.width = `${canvasWidth}px`;
    this.canvas.style.height = `${canvasHeight}px`;
    this.canvas.style.position = 'absolute';

    // Canvas offset inside clipViewport
    const canvasOffsetX = -marginLeft;
    const canvasOffsetY = gridTop;
    this.canvas.style.left = `${canvasOffsetX}px`;
    this.canvas.style.top = `${canvasOffsetY}px`;

    // CSS transform for scroll sync (viewport concept)
    this.canvas.style.transform = `translate(${-this.scrollLeft}px, ${-this.scrollTop}px)`;
    this.canvas.style.pointerEvents = 'auto';

    // Store grid info for curve drawing
    this.gridBounds = { minX, maxX, minY, maxY, gridLeft, gridTop, gridWidth, gridHeight };

    this._log('canvas-sizing', {
      gridBounds: { minX, maxX, minY, maxY },
      gridSize: { width: gridWidth, height: gridHeight },
      canvasSize: { width: canvasWidth, height: canvasHeight },
      clipViewport: { left: this.pinnedWidth + marginLeft, top: headerHeight, width: viewportWidth, height: viewportHeight },
      scroll: { left: this.scrollLeft, top: this.scrollTop },
      cellRects: cellRects.length,
    });

    // Clear and draw
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.curvePoints = [];

    // Draw 11 dashed guide lines (0%, 10%, 20%, ... 100%)
    this._drawGuideLines();

    // Draw curves (canvas-relative coordinates)
    this._drawCurve(cellRects, this.curveData.planned, this._getPlannedColor(), 'Planned');
    this._drawCurve(cellRects, this.curveData.actual, this._getActualColor(), 'Actual');

    // DEBUG: Log canvas info for hover debugging
    const canvasRect = this.canvas.getBoundingClientRect();
    const centerX = canvasRect.left + canvasRect.width / 2;
    const centerY = canvasRect.top + canvasRect.height / 2;
    const elementAtCenter = document.elementFromPoint(centerX, centerY);
    this._log('sync-complete', {
      canvasWidth: this.canvas.width,
      canvasHeight: this.canvas.height,
      canvasRect: { top: canvasRect.top, left: canvasRect.left, width: canvasRect.width, height: canvasRect.height },
      canvasCenter: { x: centerX, y: centerY },
      elementAtCenter: elementAtCenter?.className || elementAtCenter?.tagName || 'null',
      isCanvasOnTop: elementAtCenter === this.canvas,
      curvePointsCount: this.curvePoints?.length || 0,
      curvePointsSample: this.curvePoints?.[0] || null
    });
  }

  // PHASE 1 FIX: Get frozen column width from table manager
  _getPinnedWidth(scrollArea) {
    const pinnedCols = this.tableManager?.getPinnedColumnsWidth?.();
    if (pinnedCols && pinnedCols > 0) {
      return pinnedCols;
    }

    let total = 0;
    const header = scrollArea?.previousElementSibling;
    if (header) {
      const pinned = header.querySelectorAll('th[data-pinned="left"], td[data-pinned="left"]');
      pinned.forEach((cell) => {
        total += cell.offsetWidth || 0;
      });
    }

    return total;
  }

  // Immediate transform update for smooth scrolling (GPU-accelerated <1ms)
  // Updates CSS transform to sync canvas with scroll position (viewport concept)
  _updateTransform() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    this.scrollLeft = scrollArea.scrollLeft || 0;
    this.scrollTop = scrollArea.scrollTop || 0;

    // Canvas moves via NEGATIVE transform (clipViewport clips to visible area)
    this.canvas.style.transform = `translate(${-this.scrollLeft}px, ${-this.scrollTop}px)`;
  }

  // PHASE 4 FIX: Set mode (progress or cost) and reload data
  async setMode(mode) {
    if (mode !== 'progress' && mode !== 'cost') {
      console.error('[KurvaSOverlay] Invalid mode:', mode);
      return;
    }

    this.mode = mode;
    this._log('mode-changed', { mode });

    if (this.mode === 'cost') {
      await this._loadCostMode();
    } else {
      await this._loadProgressMode();
    }
  }

  // PHASE 4 FIX: Load cost mode data from API
  async _loadCostMode() {
    if (!this.projectId) {
      console.error('[KurvaSOverlay] Cannot load cost mode: no projectId');
      return;
    }

    try {
      const response = await fetch(
        `/detail_project/api/v2/project/${this.projectId}/kurva-s-harga/`,
        { credentials: 'include' }
      );
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const costData = await response.json();
      this._log('cost-data-loaded', costData);

      // Import buildCostDataset dynamically
      const { buildCostDataset } = await import('./dataset-builder.js');
      const dataset = buildCostDataset(costData);

      if (!dataset) {
        console.error('[KurvaSOverlay] Failed to build cost dataset');
        return;
      }

      // Convert to curve format
      const curveData = {
        planned: this._convertDatasetSeriesToCurvePoints(dataset, 'planned'),
        actual: this._convertDatasetSeriesToCurvePoints(dataset, 'actual'),
      };

      this.renderCurve(curveData);
    } catch (error) {
      console.error('[KurvaSOverlay] Failed to load cost mode:', error);
    }
  }

  // PHASE 4 FIX: Load progress mode data from UnifiedTableManager
  async _loadProgressMode() {
    // Progress mode uses grid-based data from UnifiedTableManager
    // Trigger a refresh by calling tableManager's updateCurvaS
    if (typeof this.tableManager?.updateCurvaS === 'function') {
      this.tableManager.updateCurvaS();
    } else {
      this._log('warn-update-curvas-missing', { message: 'updateCurvaS not available' })
    }
  }

  // PHASE 4 FIX: Convert dataset series to curve points format
  _convertDatasetSeriesToCurvePoints(dataset, seriesKey) {
    const series = dataset[seriesKey] || [];
    const labels = dataset.labels || [];
    const details = dataset.details || [];

    return series.map((cumulativeProgress, index) => {
      const detail = details[index] || {};
      const label = labels[index] || `Week ${index + 1}`;

      // Extract column ID from detail or label
      const columnId = detail?.metadata?.id ||
        detail?.metadata?.fieldId ||
        detail?.metadata?.columnId ||
        detail?.weekNumber ||
        label.match(/W(\d+)/)?.[1] ||
        `week_${index + 1}`;

      return {
        columnId: String(columnId),
        weekNumber: detail?.weekNumber || detail?.metadata?.weekNumber || index + 1,
        weekProgress: Number(
          seriesKey === 'planned'
            ? (detail.planned ?? detail.plannedPercent ?? cumulativeProgress)
            : (detail.actual ?? detail.actualPercent ?? cumulativeProgress)
        ) || 0,
        cumulativeProgress: Number(cumulativeProgress) || 0,
        label: label,
      };
    });
  }

  renderCurve(curveData) {
    this.curveData = {
      planned: Array.isArray(curveData.planned) ? curveData.planned : [],
      actual: Array.isArray(curveData.actual) ? curveData.actual : [],
    };

    this._log('renderCurve', {
      plannedPoints: this.curveData.planned.length,
      actualPoints: this.curveData.actual.length,
    });

    if (this.visible) {
      this.syncWithTable();
    }
  }

  // Draw 11 horizontal dashed guide lines (0%, 10%, 20%, ... 100%)
  _drawGuideLines() {
    const gridBounds = this.gridBounds;
    if (!gridBounds) return;

    const ctx = this.ctx;
    const canvasWidth = this.canvas.width;
    const canvasHeight = gridBounds.gridHeight;

    // Y-axis margins (same as _mapDataToCanvasPoints)
    const marginY = 40;
    const y0percent = canvasHeight - marginY;  // 0% at bottom
    const y100percent = marginY;                // 100% at top

    ctx.save();
    ctx.strokeStyle = 'rgba(80, 80, 80, 0.4)';
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);  // Dashed line pattern
    ctx.font = '11px sans-serif';
    ctx.fillStyle = 'rgba(80, 80, 80, 0.7)';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    // Draw 11 lines: 0%, 10%, 20%, ..., 100%
    for (let percent = 0; percent <= 100; percent += 10) {
      const y = this._interpolateY(percent, y0percent, y100percent);

      // Draw dashed line
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvasWidth, y);
      ctx.stroke();

      // Draw label on the right side
      ctx.fillText(`${percent}%`, canvasWidth - 5, y);
    }

    ctx.restore();
  }

  _drawCurve(cellRects, dataPoints, color, label) {
    if (!Array.isArray(dataPoints) || dataPoints.length === 0) {
      this._log(`_drawCurve:${label}`, { info: 'No dataPoints' });
      return;
    }

    const points = this._mapDataToCanvasPoints(cellRects, dataPoints);
    if (points.length === 0) {
      this._log(`_drawCurve:${label}`, { error: 'No points mapped' });
      return;
    }

    this._log(`_drawCurve:${label}`, { points: points.length, sample: points[0] });

    // Draw line connecting points
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = 3;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    this.ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) {
        this.ctx.moveTo(point.x, point.y);
      } else {
        this.ctx.lineTo(point.x, point.y);
      }
    });
    this.ctx.stroke();

    // Draw points (nodes) with hover detection data
    this.ctx.fillStyle = color;
    points.forEach((point) => {
      this.ctx.beginPath();
      this.ctx.arc(point.x, point.y, 6, 0, 2 * Math.PI);
      this.ctx.fill();

      // White center for better visibility
      this.ctx.fillStyle = '#ffffff';
      this.ctx.beginPath();
      this.ctx.arc(point.x, point.y, 2.5, 0, 2 * Math.PI);
      this.ctx.fill();
      this.ctx.fillStyle = color;

      // Store point data for tooltip
      point.color = color;
      point.label = label;
    });

    // Store points for hover detection
    if (!this.curvePoints) this.curvePoints = [];
    this.curvePoints.push(...points);
  }

  _mapDataToCanvasPoints(cellRects, dataPoints) {
    const points = [];

    // Use gridBounds for coordinate calculations (set in syncWithTable)
    const gridBounds = this.gridBounds || {
      minX: this.pinnedWidth,
      maxX: this.canvas.width + this.pinnedWidth,
      minY: 0,
      maxY: this.canvas.height,
      gridLeft: this.pinnedWidth,
      gridTop: 0,
      gridWidth: this.canvas.width,
      gridHeight: this.canvas.height,
    };

    // Y-axis: 0% at BOTTOM of grid, 100% at TOP of grid
    const marginY = 40; // pixels margin at top and bottom
    const y0percent = gridBounds.gridHeight - marginY;  // 0% at bottom
    const y100percent = marginY;                         // 100% at top

    this._log('_mapDataToCanvasPoints', {
      gridBounds,
      y0percent,
      y100percent,
      dataPoints: dataPoints.length,
      cellRects: cellRects.length,
    });

    // Group cell rects by column to find week grid lines (right edges)
    const columnGridLines = this._getWeekGridLines(cellRects);

    // Week 0 node at x=0 (left edge of grid), y=0% progress
    if (cellRects.length > 0 && dataPoints.length > 0) {
      const week0X = 0; // Left edge of canvas = left edge of grid
      const week0Y = this._interpolateY(0, y0percent, y100percent); // 0% progress

      points.push({
        x: week0X,
        y: week0Y,
        columnId: 'week_0',
        progress: 0,
        weekNumber: 0,
        weekProgress: 0,
      });
    }

    dataPoints.forEach((dataPoint) => {
      const columnId = dataPoint.columnId || dataPoint.weekId || dataPoint.week;
      const progress = Number.isFinite(dataPoint.cumulativeProgress)
        ? dataPoint.cumulativeProgress
        : dataPoint.progress || 0;

      // Try direct match first
      let columnGridLine = columnGridLines.get(String(columnId));

      // Fallback: Try weekNumber-based lookup with various formats
      if (!columnGridLine && dataPoint.week) {
        const weekNum = dataPoint.week;
        // Try common column ID formats
        const tryFormats = [
          String(weekNum),           // "1", "2", ...
          `week_${weekNum}`,         // "week_1", "week_2", ...
          `col_${weekNum}`,          // "col_1", "col_2", ...
          `col_${weekNum - 1}`,      // "col_0", "col_1", ... (0-indexed)
        ];
        for (const fmt of tryFormats) {
          if (columnGridLines.has(fmt)) {
            columnGridLine = columnGridLines.get(fmt);
            break;
          }
        }
      }

      if (!columnGridLine) {
        if (this.debug && !this._missingColumnLog.has(String(columnId))) {
          this._missingColumnLog.add(String(columnId));
          this._log('skip-missing-column', {
            columnId,
            weekNumber: dataPoint.week,
            availableColumns: Array.from(columnGridLines.keys()).slice(0, 5)
          });
        }
        return;
      }

      // Convert columnGridLine to canvas-relative X coordinate
      // columnGridLine is absolute X, canvas starts at gridLeft
      const x = columnGridLine - gridBounds.gridLeft;
      const y = this._interpolateY(progress, y0percent, y100percent);

      points.push({
        x,
        y,
        columnId,
        progress,
        weekNumber: dataPoint.weekNumber,
        weekProgress: dataPoint.weekProgress,
      });
    });

    return points;
  }

  // Get grid lines (right edges) in ABSOLUTE coordinates
  // Conversion to canvas-relative is done in _mapDataToCanvasPoints
  _getWeekGridLines(cellRects) {
    const columnGridLines = new Map();

    cellRects.forEach((rect) => {
      const columnId = String(rect.columnId);
      if (!columnGridLines.has(columnId)) {
        // Grid line = right edge of column (absolute X coordinate)
        const absoluteGridLine = rect.x + rect.width;
        columnGridLines.set(columnId, absoluteGridLine);
      }
    });

    this._log('grid-lines', {
      sample: Array.from(columnGridLines.entries()).slice(0, 3),
      pinnedWidth: this.pinnedWidth,
      count: columnGridLines.size,
    });

    return columnGridLines;
  }

  _interpolateY(progress, y0, y100) {
    // 0% → y0 (bottom), 100% → y100 (top)
    // Clamp progress to [0, 100]
    const clampedProgress = Math.max(0, Math.min(100, progress));
    return y0 - (clampedProgress / 100) * (y0 - y100);
  }

  /**
   * Wait for virtualizer cells to be ready, then render
   * Uses simple 2-RAF approach instead of complex retry mechanism
   */
  _waitForCellsAndRender() {
    if (!this.visible) return;

    // Frame 1: Force virtualizer to measure/render current rows
    requestAnimationFrame(() => {
      try {
        if (typeof this.tableManager?._renderRowsOnly === 'function') {
          this.tableManager._renderRowsOnly();
        } else if (this.tableManager?.virtualizer?.measure) {
          this.tableManager.virtualizer.measure();
        }
      } catch (e) {
        this._log('warn-force-render', { error: e?.message });
      }

      // Frame 2: Cells should be ready now, render the curve
      requestAnimationFrame(() => {
        this.syncWithTable();
      });
    });
  }

  _showLegend() {
    if (this.legendElement) {
      this.legendElement.style.display = 'flex';
      this._updateLegendColors(); // Update for dark/light mode
      return;
    }

    // Create legend using shared utility
    this.legendElement = createLegend({
      plannedColor: this._getPlannedColor(),
      actualColor: this._getActualColor(),
      zIndex: 40
    });

    // Change to fixed positioning for legend
    this.legendElement.style.position = 'fixed';

    document.body.appendChild(this.legendElement);
  }

  _updateLegendColors() {
    if (!this.legendElement) return;
    updateLegendColors(
      this.legendElement,
      this._getPlannedColor(),
      this._getActualColor()
    );
  }

  _isDarkMode() {
    return isDarkMode();
  }

  _hideLegend() {
    if (this.legendElement) {
      this.legendElement.style.display = 'none';
    }
  }

  _getPlannedColor() {
    // ALWAYS use cyan/info color for planned curve
    // This matches the toolbar btn-outline-info color
    return '#0dcaf0';
  }

  _getActualColor() {
    // ALWAYS use yellow/warning color for actual curve
    // This matches the toolbar btn-outline-warning color
    return '#ffc107';
  }

  _bindPointerEvents() {
    // Add hover tooltip for curve points
    this.canvas.addEventListener('mousemove', (e) => {
      // DEBUG: Log to verify event is firing
      this._log('tooltip-mousemove', {
        visible: this.visible,
        curvePointsCount: this.curvePoints?.length || 0,
      });

      if (!this.visible || !this.curvePoints || this.curvePoints.length === 0) {
        this._log('tooltip-early-return', { reason: 'no-points' });
        return;
      }

      const rect = this.canvas.getBoundingClientRect();

      // Canvas visual coords = canvas drawing coords
      // getBoundingClientRect() already incorporates CSS transform (translate(-scrollX, -scrollY))
      // So we DON'T need to add scroll offset - visual position = drawing position
      const canvasX = e.clientX - rect.left;
      const canvasY = e.clientY - rect.top;

      this._log('tooltip-coords', { canvasX, canvasY, scrollLeft: this.scrollLeft, scrollTop: this.scrollTop });

      // Hit test: find closest point within 15px radius
      const hit = hitTestPoint(this.curvePoints, canvasX, canvasY, 15);
      this._log('tooltip-hit', hit);
      if (hit) {
        this.tooltipManager.show(e.clientX, e.clientY, hit);
        this.canvas.style.cursor = 'pointer';
      } else {
        this.tooltipManager.hide();
        this.canvas.style.cursor = 'default';
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      this.tooltipManager.hide();
      this.canvas.style.cursor = 'default';
    });

    // Wheel passthrough: forward scroll events to bodyScroll
    // ClipViewport is fixed overlay above bodyScroll with z-index 1000
    this.canvas.addEventListener('wheel', (e) => {
      const scrollArea = this.tableManager?.bodyScroll;
      if (scrollArea) {
        scrollArea.scrollLeft += e.deltaX;
        scrollArea.scrollTop += e.deltaY;
      }
    }, { passive: true });
  }

  _log(event, payload) {
    if (!this.debug) return;
    console.log(`[KurvaSOverlay] ${event}`, payload || {});
  }
}
