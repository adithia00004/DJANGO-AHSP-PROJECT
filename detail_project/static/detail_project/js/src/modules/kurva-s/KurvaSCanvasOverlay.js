/**
 * Kurva-S Canvas Overlay
 * Plots S-curve as overlay on top of table grid
 * - Y-axis inverted: 0% at bottom (last row), 100% at top (first row)
 * - X-axis: Plots at center of each week column
 * - Shows both planned and actual curves
 * - Y-axis labels on right side of table
 * - Legend for planned vs actual
 */

export class KurvaSCanvasOverlay {
  constructor(tableManager, options = {}) {
    this.tableManager = tableManager;
    this.debug = Boolean(
      this.tableManager?.options?.debugUnifiedTable ||
      this.tableManager?.state?.debugUnifiedTable ||
      window.DEBUG_UNIFIED_TABLE
    );
    this._missingColumnLog = new Set();

    // PHASE 1 FIX: Track scroll position and pinned width for transform compensation
    this.scrollLeft = 0;
    this._syncScheduled = false;
    this.pinnedWidth = 0;

    // PHASE 4 FIX: Cost mode support
    this.mode = 'progress';  // 'progress' or 'cost'
    this.projectId = options.projectId || null;

    // Main canvas for curve plotting
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'kurva-s-canvas-overlay';
    this.canvas.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: auto;
      z-index: 10;
    `;
    this.ctx = this.canvas.getContext('2d');

    // Y-axis container (HTML ticks)
    this.yAxisContainer = document.createElement('div');
    this.yAxisContainer.className = 'kurva-s-yaxis-overlay';
    this.yAxisContainer.style.cssText = `
      position: absolute;
      top: 0;
      right: 0;
      width: 80px;
      pointer-events: none;
      z-index: 11;
      display: none;
    `;

    this.visible = false;
    this.curveData = { planned: [], actual: [] };
    this.legendElement = null;
    this.curvePoints = []; // For tooltip hit-testing
    this.tooltip = null;

    // FIX 1: Scroll updates transform immediately and throttles resync
    const scrollTarget = this.tableManager?.bodyScroll;
    if (scrollTarget) {
      scrollTarget.addEventListener('scroll', () => {
        if (this.visible) {
          this._updateTransform();
          if (!this._syncScheduled) {
            this._syncScheduled = true;
            requestAnimationFrame(() => {
              this._syncScheduled = false;
              if (this.visible) {
                this.syncWithTable();
              }
            });
          }
        }
      }, { passive: true });
    }

    this._bindPointerEvents();
  }

  show() {
    if (this.visible) return;
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    scrollArea.style.position = scrollArea.style.position || 'relative';

    // Ensure canvas is removed first to avoid duplication
    if (this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    scrollArea.appendChild(this.canvas);
    this.canvas.style.display = 'block';  // Ensure visible

    // Attach Y-axis container
    if (this.yAxisContainer.parentNode) {
      this.yAxisContainer.parentNode.removeChild(this.yAxisContainer);
    }
    scrollArea.appendChild(this.yAxisContainer);
    this.yAxisContainer.style.display = 'block';

    this.visible = true;
    this._log('show', { overlay: true });
    this._showLegend();

    // Force grid render and nudge scroll so TanStack virtualizer measures columns
    // This avoids the "Kurva S muncul setelah scroll horizontal" issue.
    this._forceGridRenderAndNudgeScroll(scrollArea);
  }

  hide() {
    if (!this.visible) return;

    if (this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    if (this.yAxisContainer?.parentNode) {
      this.yAxisContainer.parentNode.removeChild(this.yAxisContainer);
    }

    this.visible = false;
    this._log('hide');
    this._hideLegend();
  }

  syncWithTable() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) {
      this._log('warn-no-scroll-area', { message: 'No scrollArea found' });
      return;
    }

    // PHASE 1 FIX: Update pinned width and scroll position
    this.pinnedWidth = this._getPinnedWidth(scrollArea);
    this.scrollLeft = scrollArea.scrollLeft || 0;

    // PHASE 1 FIX: Viewport-sized canvas (NOT full scrollWidth to avoid >32k px blank canvas)
    const viewportWidth = scrollArea.clientWidth - this.pinnedWidth;
    const MAX_CANVAS_WIDTH = 32000;  // Browser safety limit
    const MAX_CANVAS_HEIGHT = 16000;

    // DEBUG: Ensure we have valid dimensions
    const canvasWidth = Math.max(100, Math.min(viewportWidth, MAX_CANVAS_WIDTH));
    const canvasHeight = Math.max(100, Math.min(scrollArea.clientHeight, MAX_CANVAS_HEIGHT));

    this.canvas.width = canvasWidth;
    this.canvas.height = canvasHeight;

    // Set CSS size explicitly
    this.canvas.style.width = `${canvasWidth}px`;
    this.canvas.style.height = `${canvasHeight}px`;

    // Position Y-axis container (HTML ticks) at right of visible viewport
    const axisWidth = 80;
    const axisHeight = canvasHeight;
    const axisLeft = this.scrollLeft + scrollArea.clientWidth - axisWidth;
    const axisTop = scrollArea.scrollTop || 0;
    if (this.yAxisContainer) {
      this.yAxisContainer.style.width = `${axisWidth}px`;
      this.yAxisContainer.style.height = `${axisHeight}px`;
      this.yAxisContainer.style.left = `${axisLeft}px`;
      this.yAxisContainer.style.top = `${axisTop}px`;
      this.yAxisContainer.style.display = this.visible ? 'block' : 'none';
    }

    // PHASE 1 FIX: Transform compensation for scroll (keeps canvas fixed at frozen boundary)
    this.canvas.style.position = 'absolute';
    this.canvas.style.left = `${this.pinnedWidth}px`;  // Start AFTER frozen column
    this.canvas.style.top = '0px';
    this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;  // Compensate scroll
    this.canvas.style.pointerEvents = 'auto';
    this.canvas.style.zIndex = '10';

    // Position Y-axis container to the right of visible viewport
    if (this.yAxisContainer) {
      const axisWidth = 80;
      const axisHeight = canvasHeight;
      const axisLeft = this.scrollLeft + scrollArea.clientWidth - axisWidth;
      const axisTop = scrollArea.scrollTop || 0;
      this.yAxisContainer.style.width = `${axisWidth}px`;
      this.yAxisContainer.style.height = `${axisHeight}px`;
      this.yAxisContainer.style.left = `${axisLeft}px`;
      this.yAxisContainer.style.top = `${axisTop}px`;
      this.yAxisContainer.style.display = this.visible ? 'block' : 'none';
    }

    this._log('canvas-sizing', {
      viewportWidth,
      pinnedWidth: this.pinnedWidth,
      canvasWidth,
      canvasHeight,
      scrollLeft: this.scrollLeft,
      transform: this.canvas.style.transform,
      left: this.canvas.style.left,
    });

    const cellRects = typeof this.tableManager.getCellBoundingRects === 'function'
      ? this.tableManager.getCellBoundingRects()
      : [];

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.curvePoints = []; // Reset curve points for hit-testing

    this._log('sync-debug', {
      canvasSize: { w: this.canvas.width, h: this.canvas.height },
      scrollAreaSize: { w: scrollArea.scrollWidth, h: scrollArea.scrollHeight },
      visibleSize: { w: scrollArea.clientWidth, h: scrollArea.clientHeight },
      scroll: { left: scrollArea.scrollLeft, top: scrollArea.scrollTop },
      cellRects: cellRects.length,
      plannedPoints: this.curveData.planned.length,
      actualPoints: this.curveData.actual.length,
      canvasVisible: this.visible,
      canvasParent: this.canvas.parentNode ? 'attached' : 'detached',
    });

    this._log('sync', {
      cells: cellRects.length,
      plannedPoints: this.curveData.planned.length,
      actualPoints: this.curveData.actual.length,
      size: { w: this.canvas.width, h: this.canvas.height },
    });

    if (cellRects.length === 0) {
      this._log('warn-no-cell-rects', { message: 'No cell rects available for plotting' });
      return;
    }

    // Draw curves (canvas-relative coordinates)
    this._drawCurve(cellRects, this.curveData.planned, this._getPlannedColor(), 'Planned');
    this._drawCurve(cellRects, this.curveData.actual, this._getActualColor(), 'Actual');

    // Draw Y-axis labels (HTML-based)
    this._drawYAxisLabels(canvasHeight);
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

  // PHASE 1 FIX: Immediate transform update for smooth scrolling (GPU-accelerated <1ms)
  _updateTransform() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    this.scrollLeft = scrollArea.scrollLeft || 0;
    this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;
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

    // DEBUG FIX: Use viewport height for Y calculations, not full scrollHeight
    // Y-axis should be relative to visible viewport, not entire table
    const scrollArea = this.tableManager?.bodyScroll;
    const viewportHeight = scrollArea ? scrollArea.clientHeight : this.canvas.height;

    const y0percent = viewportHeight - 40; // 0% at BOTTOM of viewport
    const y100percent = 40;                 // 100% at TOP of viewport

    this._log('_mapDataToCanvasPoints', {
      canvasHeight: this.canvas.height,
      viewportHeight,
      y0percent,
      y100percent,
      dataPoints: dataPoints.length,
      cellRects: cellRects.length,
    });

    // PHASE 2 FIX: Group cell rects by column to find week grid lines (right edges)
    const columnGridLines = this._getWeekGridLines(cellRects);

    // FIX 2: Add Week 0 node at 0% progress (grid kiri Week 1)
    if (cellRects.length > 0 && dataPoints.length > 0) {
      const firstWeekRect = cellRects.reduce((earliest, rect) => {
        return (!earliest || rect.x < earliest.x) ? rect : earliest;
      }, null);

      if (firstWeekRect) {
        const week0X = -this.scrollLeft;
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
    }

    dataPoints.forEach((dataPoint) => {
      const columnId = dataPoint.columnId || dataPoint.weekId || dataPoint.week;
      const progress = Number.isFinite(dataPoint.cumulativeProgress)
        ? dataPoint.cumulativeProgress
        : dataPoint.progress || 0;

      const columnGridLine = columnGridLines.get(String(columnId));
      if (!columnGridLine) {
        if (this.debug && !this._missingColumnLog.has(String(columnId))) {
          this._missingColumnLog.add(String(columnId));
          this._log('skip-missing-column', { columnId, availableColumns: columnGridLines.size })
        }
        return;
      }

      const y = this._interpolateY(progress, y0percent, y100percent);

      points.push({
        x: columnGridLine,
        y,
        columnId,
        progress,
        weekNumber: dataPoint.weekNumber,
        weekProgress: dataPoint.weekProgress,
      });
    });

    return points;
  }

  // PHASE 2 FIX: Get grid lines (right edges) in canvas-relative coordinates
  _getWeekGridLines(cellRects) {
    const columnGridLines = new Map();

    cellRects.forEach((rect) => {
      const columnId = String(rect.columnId);
      if (!columnGridLines.has(columnId)) {
        // PHASE 2 FIX: Grid line = right edge of column (absolute coordinates)
        const absoluteGridLine = rect.x + rect.width;

        // PHASE 2 FIX: Convert to canvas-relative coordinates
        // Canvas starts at pinnedWidth, so X=0 on canvas = pinnedWidth in absolute
        // Also compensate for scroll: canvasX = absoluteX - pinnedWidth - scrollLeft
        const canvasRelativeX = absoluteGridLine - this.pinnedWidth - this.scrollLeft;

        columnGridLines.set(columnId, canvasRelativeX);
      }
    });

    this._log('grid-lines', {
      sample: Array.from(columnGridLines.entries()).slice(0, 3),
      pinnedWidth: this.pinnedWidth,
      scrollLeft: this.scrollLeft
    });
    return columnGridLines;
  }

  _interpolateY(progress, y0, y100) {
    // 0% → y0 (bottom), 100% → y100 (top)
    // Clamp progress to [0, 100]
    const clampedProgress = Math.max(0, Math.min(100, progress));
    return y0 - (clampedProgress / 100) * (y0 - y100);
  }

  _renderWithRetry(attempt = 1, maxAttempts = 10) {
    if (!this.visible) return;

    const cellRects = typeof this.tableManager?.getCellBoundingRects === 'function'
      ? this.tableManager.getCellBoundingRects()
      : [];

    const hasSize = this.canvas.width > 0 && this.canvas.height > 0;
    const hasCells = Array.isArray(cellRects) && cellRects.length > 0;

    if (hasSize && hasCells) {
      this.syncWithTable();
      return;
    }

    // If cells are not ready yet, force the grid virtualizer to measure/render
    // so bounding rects become available before we retry.
    try {
      if (typeof this.tableManager?._renderRowsOnly === 'function') {
        this.tableManager._renderRowsOnly();
      } else if (this.tableManager?.virtualizer?.measure) {
        this.tableManager.virtualizer.measure();
      }
    } catch (e) {
      this._log('warn-render-retry-measure', { error: e?.message });
    }

    if (attempt < maxAttempts) {
      requestAnimationFrame(() => this._renderWithRetry(attempt + 1, maxAttempts));
    } else {
      this._log('render-retry-exhausted', { hasSize, hasCells })
    }
  }

  /**
   * Force grid to render rows and gently nudge horizontal scroll to trigger measurement.
   * This ensures bounding rects are available immediately after mode switch.
   */
  _forceGridRenderAndNudgeScroll(scrollArea) {
    // Render current virtual rows
    try {
      if (typeof this.tableManager?._renderRowsOnly === 'function') {
        this.tableManager._renderRowsOnly();
      } else if (this.tableManager?.virtualizer?.measure) {
        this.tableManager.virtualizer.measure();
      }
    } catch (e) {
      this._log('warn-force-render', { error: e?.message });
    }

    if (!scrollArea) {
      this._renderWithRetry();
      return;
    }

    const original = scrollArea.scrollLeft || 0;
    const nudge = Math.min(original + 1, scrollArea.scrollWidth);

    // Nudge scroll to trigger layout, then restore on next frame
    scrollArea.scrollLeft = nudge;
    scrollArea.dispatchEvent(new Event('scroll'));

    requestAnimationFrame(() => {
      scrollArea.scrollLeft = original;
      scrollArea.dispatchEvent(new Event('scroll'));
      this._renderWithRetry();
    });
  }

  _drawYAxisLabels(canvasHeight) {
    if (!this.yAxisContainer) return;
    this.yAxisContainer.innerHTML = '';

    const y0 = canvasHeight - 40;
    const y100 = 40;

    // Background
    const bg = document.createElement('div');
    bg.style.position = 'absolute';
    bg.style.inset = '0';
    bg.style.background = 'rgba(255, 255, 255, 0.9)';
    bg.style.borderLeft = '1px solid #dee2e6';
    this.yAxisContainer.appendChild(bg);

    const percentages = [0, 20, 40, 60, 80, 100];
    percentages.forEach((pct) => {
      const y = this._interpolateY(pct, y0, y100);

      const tick = document.createElement('div');
      tick.style.position = 'absolute';
      tick.style.left = '0';
      tick.style.top = `${y}px`;
      tick.style.width = '100%';
      tick.style.height = '1px';
      tick.style.borderTop = '1px solid #dee2e6';
      this.yAxisContainer.appendChild(tick);

      const label = document.createElement('div');
      label.textContent = `${pct}%`;
      label.style.position = 'absolute';
      label.style.left = '10px';
      label.style.top = `${y - 6}px`;
      label.style.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      label.style.color = '#495057';
      label.style.lineHeight = '12px';
      this.yAxisContainer.appendChild(label);
    });
  }

  _showLegend() {
    if (this.legendElement) {
      this.legendElement.style.display = 'flex';
      this._updateLegendColors(); // Update for dark/light mode
      return;
    }

    // Detect dark mode
    const isDarkMode = this._isDarkMode();

    // Create legend element - repositioned to top-right to reduce overlap
    this.legendElement = document.createElement('div');
    this.legendElement.className = 'kurva-s-legend';
    this.legendElement.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: ${isDarkMode ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)'};
      border: 1px solid ${isDarkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'};
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 13px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      box-shadow: 0 4px 12px rgba(0, 0, 0, ${isDarkMode ? '0.5' : '0.15'});
      z-index: 25;
      pointer-events: none;
      display: flex;
      gap: 16px;
      align-items: center;
    `;

    const plannedColor = this._getPlannedColor();
    const actualColor = this._getActualColor();
    const textColor = isDarkMode ? '#e5e7eb' : '#374151';

    this.legendElement.innerHTML = `
      <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 24px; height: 4px; background: ${plannedColor}; border-radius: 2px;"></div>
        <span style="color: ${textColor}; font-weight: 500;">Planned</span>
      </div>
      <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 24px; height: 4px; background: ${actualColor}; border-radius: 2px;"></div>
        <span style="color: ${textColor}; font-weight: 500;">Actual</span>
      </div>
    `;

    document.body.appendChild(this.legendElement);
  }

  _updateLegendColors() {
    if (!this.legendElement) return;
    const isDarkMode = this._isDarkMode();
    this.legendElement.style.background = isDarkMode ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)';
    this.legendElement.style.borderColor = isDarkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';
    this.legendElement.style.boxShadow = `0 4px 12px rgba(0, 0, 0, ${isDarkMode ? '0.5' : '0.15'})`;

    const textColor = isDarkMode ? '#e5e7eb' : '#374151';
    const spans = this.legendElement.querySelectorAll('span');
    spans.forEach(span => span.style.color = textColor);
  }

  _isDarkMode() {
    // Check if body has dark mode class or if system prefers dark mode
    const bodyClassList = document.body.classList;
    if (bodyClassList.contains('dark-mode') || bodyClassList.contains('dark')) {
      return true;
    }
    // Check CSS variable or system preference
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
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

  _getCssVar(name) {
    try {
      const root = document.documentElement;
      const value = getComputedStyle(root).getPropertyValue(name);
      return value && value.trim().length ? value.trim() : null;
    } catch (e) {
      return null;
    }
  }

  _getBtnColor(selector) {
    try {
      const el = document.querySelector(selector);
      if (!el) return null;
      const style = getComputedStyle(el);
      return style.getPropertyValue('background-color')?.trim() ||
        style.getPropertyValue('border-color')?.trim() ||
        style.getPropertyValue('color')?.trim() ||
        null;
    } catch (e) {
      return null;
    }
  }

  _bindPointerEvents() {
    // Add hover tooltip for curve points
    this.canvas.addEventListener('mousemove', (e) => {
      if (!this.visible || !this.curvePoints || this.curvePoints.length === 0) return;

      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Hit test: find closest point within 10px radius
      const hit = this._hitTestPoint(x, y, 10);
      if (hit) {
        this._showTooltip(e.clientX, e.clientY, hit);
        this.canvas.style.cursor = 'pointer';
      } else {
        this._hideTooltip();
        this.canvas.style.cursor = 'default';
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      this._hideTooltip();
      this.canvas.style.cursor = 'default';
    });
  }

  _hitTestPoint(x, y, radius) {
    if (!this.curvePoints) return null;

    for (const point of this.curvePoints) {
      const dx = point.x - x;
      const dy = point.y - y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance <= radius) {
        return point;
      }
    }
    return null;
  }

  _ensureTooltip() {
    if (this.tooltip) return this.tooltip;
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'kurvas-overlay-tooltip';
    this.tooltip.style.cssText = `
      position: fixed;
      padding: 8px 12px;
      background: rgba(17, 24, 39, 0.95);
      color: #f8fafc;
      border-radius: 6px;
      font-size: 12px;
      pointer-events: none;
      z-index: 30;
      display: none;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      line-height: 1.5;
    `;
    document.body.appendChild(this.tooltip);
    return this.tooltip;
  }

  _showTooltip(clientX, clientY, point) {
    const tip = this._ensureTooltip();
    const weekLabel = point.weekNumber ? `Week ${point.weekNumber}` : point.columnId;
    const progressLabel = Number.isFinite(point.progress) ? `${point.progress.toFixed(1)}%` : '-';
    const weekProgressLabel = Number.isFinite(point.weekProgress) ? `${point.weekProgress.toFixed(1)}%` : '-';

    tip.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px; color: ${point.color};">${point.label}</div>
      <div><strong>${weekLabel}</strong></div>
      <div>Cumulative: ${progressLabel}</div>
      <div>Week Progress: ${weekProgressLabel}</div>
    `;
    tip.style.left = `${clientX + 12}px`;
    tip.style.top = `${clientY + 12}px`;
    tip.style.display = 'block';
  }

  _hideTooltip() {
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
  }

  _log(event, payload) {
    if (!this.debug) return;
    console.log(`[KurvaSOverlay] ${event}`, payload || {});
  }
}
