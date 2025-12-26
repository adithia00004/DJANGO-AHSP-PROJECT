import { getCssVar, getBtnColor } from '../shared/canvas-utils.js';
import { TooltipManager } from '../shared/tooltip-manager.js';

export class GanttCanvasOverlay {
  constructor(tableManager) {
    this.tableManager = tableManager;
    this.debug = Boolean(
      this.tableManager?.options?.debugUnifiedTable ||
      this.tableManager?.state?.debugUnifiedTable ||
      window.DEBUG_UNIFIED_TABLE
    );
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'gantt-canvas-overlay';
    this.canvas.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: auto;
    `;
    this.ctx = this.canvas.getContext('2d');

    // ClipViewport: container with overflow:hidden to clip canvas
    // pointer-events:none allows scroll events to pass through to bodyScroll
    this.clipViewport = document.createElement('div');
    this.clipViewport.className = 'gantt-clip-viewport';
    this.clipViewport.style.cssText = `
      position: absolute;
      overflow: hidden;
      pointer-events: none;
      z-index: 1;
    `;
    // Canvas needs pointer-events:auto for tooltip interaction
    this.canvas.style.pointerEvents = 'auto';
    this.clipViewport.appendChild(this.canvas);
    this.visible = false;
    this.barData = [];
    this.dependencies = [];
    this.barRects = [];
    this.tooltipManager = new TooltipManager({ zIndex: 20 });
    this.pinnedWidth = 0;
    this.scrollLeft = 0;
    this.scrollTop = 0;  // Track vertical scroll for transform
    this.lastDrawMetrics = { barsDrawn: 0, barsSkipped: 0 };

    const scrollTarget = this.tableManager?.bodyScroll;
    if (scrollTarget) {
      // OPTIMIZED: Transform-only scroll (no re-render)
      // Re-render only happens on: data change, resize, mode switch
      scrollTarget.addEventListener('scroll', () => {
        if (this.visible) {
          this._updateTransform();
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

    // Attach clipViewport as sibling of scrollArea
    const container = scrollArea.parentElement;
    if (container && !this.clipViewport.parentNode) {
      container.appendChild(this.clipViewport);
    }

    this._updatePinnedClip();
    this.visible = true;
    this._log('show', { clipping: true, container: 'sibling-of-bodyScroll' });
    this.syncWithTable();
  }

  hide() {
    if (!this.visible) return;
    if (this.clipViewport.parentNode) {
      this.clipViewport.parentNode.removeChild(this.clipViewport);
    }
    this.visible = false;
    this._log('hide');
    this.tooltipManager.hide();
  }

  // Immediate transform update for smooth scrolling (GPU-accelerated)
  // Canvas moves via NEGATIVE transform to simulate viewport scrolling
  _updateTransform() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    this.scrollLeft = scrollArea.scrollLeft || 0;
    this.scrollTop = scrollArea.scrollTop || 0;
    // Negative transform: canvas shifts opposite to scroll direction
    this.canvas.style.transform = `translate(${-this.scrollLeft}px, ${-this.scrollTop}px)`;
  }

  syncWithTable() {
    const scrollArea = this.tableManager?.bodyScroll;
    const container = scrollArea?.parentElement;
    if (!scrollArea || !container) return;

    this._updatePinnedClip();
    this.scrollLeft = scrollArea.scrollLeft || 0;
    this.scrollTop = scrollArea.scrollTop || 0;

    // Get header height to position clipViewport below header
    const header = container.querySelector('.tanstack-grid-header');
    const headerHeight = header?.offsetHeight || 0;

    // Use bounding rect for accurate viewport sizing
    const containerRect = container.getBoundingClientRect();
    const scrollAreaRect = scrollArea.getBoundingClientRect();

    // Margins to avoid covering scrollbars and add spacing
    const marginLeft = 10;   // Space from frozen columns
    const marginRight = 20;  // Space for vertical scrollbar
    // Note: marginBottom not needed for height since pointer-events:none allows scroll through

    // ClipViewport: positioned after frozen columns, acts as viewport window
    const viewportWidth = containerRect.width - this.pinnedWidth - marginLeft - marginRight;
    const viewportHeight = scrollAreaRect.height; // Full height, no margin needed

    this.clipViewport.style.left = `${this.pinnedWidth + marginLeft}px`;
    this.clipViewport.style.top = `${headerHeight}px`;
    this.clipViewport.style.width = `${viewportWidth}px`;
    this.clipViewport.style.height = `${viewportHeight}px`;

    // Canvas size = FULL content size (both width and height)
    const MAX_CANVAS_WIDTH = 32000;
    const MAX_CANVAS_HEIGHT = 16000;
    // Use full scrollWidth for canvas - pinnedWidth is handled by clipViewport positioning
    const contentWidth = Math.max(scrollArea.scrollWidth, 100);
    const contentHeight = scrollArea.scrollHeight || scrollArea.clientHeight;

    this.canvas.width = Math.min(contentWidth, MAX_CANVAS_WIDTH);
    this.canvas.height = Math.min(contentHeight, MAX_CANVAS_HEIGHT);

    // Canvas position inside clipViewport
    this.canvas.style.position = 'absolute';
    this.canvas.style.left = '0px';
    this.canvas.style.top = '0px';
    // Negative transform for both horizontal and vertical scroll
    this.canvas.style.transform = `translate(${-this.scrollLeft}px, ${-this.scrollTop}px)`;

    // Use getAllCellBoundingRects for virtual calculation (all cells)
    // Fallback to getCellBoundingRects for visible-only cells
    const cellRects = typeof this.tableManager.getAllCellBoundingRects === 'function'
      ? this.tableManager.getAllCellBoundingRects()
      : typeof this.tableManager.getCellBoundingRects === 'function'
        ? this.tableManager.getCellBoundingRects()
        : [];

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    // Clear and clip to the canvas; mask element handles frozen cover.
    this.ctx.save();
    this.barRects = [];

    this._log('sync-debug', {
      canvasSize: { w: this.canvas.width, h: this.canvas.height },
      scrollAreaSize: { w: scrollArea.scrollWidth, h: scrollArea.scrollHeight },
      visibleSize: { w: scrollArea.clientWidth, h: scrollArea.clientHeight },
      scroll: { left: scrollArea.scrollLeft, top: scrollArea.scrollTop },
      cellRects: cellRects.length,
      bars: this.barData.length,
    });

    // DEBUG: Analyze cellRects column distribution
    const columnIds = [...new Set(cellRects.map(r => r.columnId))];
    const maxX = cellRects.length > 0 ? Math.max(...cellRects.map(r => r.x + r.width)) : 0;
    console.log('[GanttOverlay] 📐 CellRects analysis:', {
      totalCells: cellRects.length,
      uniqueColumns: columnIds.length,
      sampleColumnIds: columnIds.slice(0, 10),
      maxX: maxX,
      canvasWidth: this.canvas.width,
      scrollWidth: scrollArea.scrollWidth,
    });

    this._log('sync', {
      cells: cellRects.length,
      bars: this.barData.length,
      deps: this.dependencies.length,
      size: { w: this.canvas.width, h: this.canvas.height },
      scroll: { left: scrollArea.scrollLeft, top: scrollArea.scrollTop },
    });

    if (this.barData.length > 0 && cellRects.length === 0) {
      this._log('warn-no-cell-rects', { bars: this.barData.length });
    }

    // Outline cells only when debugging alignment
    if (this.debug) {
      this.ctx.strokeStyle = '#e2e8f0';
      cellRects.forEach((rect) => {
        // Canvas-relative coordinates (no scrollLeft, handled by transform)
        const canvasX = rect.x - this.pinnedWidth;
        this.ctx.strokeRect(canvasX, rect.y, rect.width, rect.height);
      });
    }

    this._drawBars(cellRects);
    this._publishMetrics(cellRects, scrollArea);
    this._drawDependencies(cellRects);
    this.ctx.restore();
  }

  renderBars(barData) {
    this.barData = Array.isArray(barData) ? barData : [];
    this._log('renderBars', { bars: this.barData.length });
    if (this.visible) {
      this.syncWithTable();
    }
  }

  renderDependencies(dependencyData) {
    this.dependencies = Array.isArray(dependencyData) ? dependencyData : [];
    this._log('renderDependencies', { deps: this.dependencies.length });
    if (this.visible) {
      this.syncWithTable();
    }
  }

  _updatePinnedClip() {
    const scrollArea = this.tableManager?.bodyScroll;
    const pinnedWidth = typeof this.tableManager?.getPinnedColumnsWidth === 'function'
      ? Number(this.tableManager.getPinnedColumnsWidth()) || 0
      : 0;
    this.pinnedWidth = Math.max(0, pinnedWidth);

    // FIXED: No need for clip-path anymore since canvas starts after frozen columns
    // Remove clip-path if exists
    this.canvas.style.clipPath = '';
    this.canvas.style.webkitClipPath = '';

    if (scrollArea?.style) {
      scrollArea.style.setProperty('--gantt-overlay-pinned-width', `${this.pinnedWidth}px`);
    }
    this._log('clip', { pinnedWidth: this.pinnedWidth });
    return this.pinnedWidth;
  }

  _publishMetrics(cellRects, scrollArea) {
    const viewportLeft = typeof scrollArea?.scrollLeft === 'number' ? scrollArea.scrollLeft : 0;
    const viewportWidth = typeof scrollArea?.clientWidth === 'number' ? scrollArea.clientWidth : 0;
    const viewportRight = viewportWidth ? viewportLeft + viewportWidth : null;
    const metrics = {
      timestamp: Date.now(),
      pinnedWidth: this.pinnedWidth,
      clipLeft: Math.max(this.pinnedWidth, viewportLeft),
      viewportLeft,
      viewportWidth,
      viewportRight,
      scrollWidth: scrollArea?.scrollWidth || 0,
      scrollHeight: scrollArea?.scrollHeight || 0,
      barsDrawn: this.lastDrawMetrics.barsDrawn || 0,
      barsSkipped: this.lastDrawMetrics.barsSkipped || 0,
      cellRects: Array.isArray(cellRects) ? cellRects.length : 0,
    };
    if (typeof window !== 'undefined') {
      window.GanttOverlayMetrics = metrics;
    }
    this._log('metrics', metrics);
    return metrics;
  }

  _drawBars(cellRects) {
    if (!Array.isArray(cellRects) || cellRects.length === 0 || this.barData.length === 0) {
      this.lastDrawMetrics = { barsDrawn: 0, barsSkipped: 0 };
      return;
    }
    const scrollArea = this.tableManager?.bodyScroll;
    const viewportLeft = typeof scrollArea?.scrollLeft === 'number' ? scrollArea.scrollLeft : 0;
    const viewportWidth = typeof scrollArea?.clientWidth === 'number' ? scrollArea.clientWidth : 0;
    const viewportRight = viewportWidth ? viewportLeft + viewportWidth : null;
    const clipLeft = Math.max(this.pinnedWidth, viewportLeft);

    // Group cell rects by pekerjaan
    const rectIndex = new Map();
    cellRects.forEach((r) => {
      const key = String(r.pekerjaanId);
      if (!rectIndex.has(key)) rectIndex.set(key, []);
      rectIndex.get(key).push(r);
    });
    rectIndex.forEach((list) => list.sort((a, b) => a.x - b.x));

    const barsByRow = new Map();
    this.barData.forEach((bar) => {
      const key = String(bar.pekerjaanId);
      if (!barsByRow.has(key)) barsByRow.set(key, []);
      barsByRow.get(key).push(bar);
    });

    let barsDrawn = 0;
    let barsSkipped = 0;

    barsByRow.forEach((bars, pkjId) => {
      const rects = rectIndex.get(pkjId) || [];
      const rectMap = new Map(rects.map((r) => [String(r.columnId), r]));
      // track heights for stacked view: planned bottom, actual top
      bars.forEach((bar) => {
        const rect = rectMap.get(String(bar.columnId));
        if (!rect) {
          barsSkipped += 1;
          return;
        }

        // No viewport clipping needed - canvas is full content width
        // ClipViewport handles visibility, we render ALL bars

        const paddingX = 0; // no gap to keep continuity
        const paddingY = 2;
        const maxWidth = rect.width - paddingX * 2;

        // Canvas is full content width, so coordinates are relative to pinnedWidth only
        // No scrollLeft adjustment needed - transform handles viewport positioning
        const baseX = (rect.x - this.pinnedWidth) + paddingX;
        const baseY = rect.y + paddingY;

        // Skip bars with negative X (shouldn't happen with correct cell rects)
        if (baseX < -rect.width) {
          barsSkipped += 1;
          return;
        }

        const fullHeight = Math.max(8, rect.height - paddingY * 2);
        const trackHeight = fullHeight / 2; // split planned/actual vertically

        const plannedValue = Number.isFinite(bar.planned) ? Math.max(0, Math.min(100, bar.planned)) : 0;
        const actualValue = Number.isFinite(bar.actual) ? Math.max(0, Math.min(100, bar.actual)) : Math.max(0, Math.min(100, bar.value || 0));

        // Planned track (bottom half): full width only if >0, otherwise gap
        const plannedWidth = maxWidth > 0 && plannedValue > 0 ? maxWidth : 0;
        this.ctx.fillStyle = this._getPlannedColor();
        if (plannedWidth > 0) {
          this.ctx.fillRect(baseX, baseY + trackHeight, plannedWidth, trackHeight - 1);
        }

        // Actual track (top half): full width only if >0, otherwise gap
        const actualWidth = maxWidth > 0 && actualValue > 0 ? maxWidth : 0;
        const barColor = bar.color || this._resolveActualColor(bar.variance);
        this.ctx.fillStyle = barColor;
        if (actualWidth > 0) {
          this.ctx.fillRect(baseX, baseY, actualWidth, trackHeight - 1);
        }

        this.barRects.push({
          x: baseX,
          y: baseY,
          width: Math.max(actualWidth, plannedWidth),
          height: fullHeight,
          pekerjaanId: bar.pekerjaanId,
          columnId: bar.columnId,
          value: actualValue,
          planned: plannedValue,
          variance: bar.variance,
          label: bar.label,
          color: barColor,
        });
        barsDrawn += 1;
      });
    });

    this.lastDrawMetrics = { barsDrawn, barsSkipped };
    // DEBUG: Log render stats
    console.log('[GanttOverlay] 📊 Render stats:', {
      barsDrawn,
      barsSkipped,
      total: this.barData.length,
      cellRectsCount: cellRects.length,
      canvasSize: { w: this.canvas.width, h: this.canvas.height },
    });
    this._log('bars:drawn', { drawn: barsDrawn, skipped: barsSkipped, total: this.barData.length });
  }

  _drawDependencies(cellRects) {
    if (!Array.isArray(cellRects) || cellRects.length === 0 || this.dependencies.length === 0) {
      return;
    }

    this.dependencies.forEach((dep) => {
      const fromRect = cellRects.find(
        (c) => c.pekerjaanId === dep.fromPekerjaanId && c.columnId === dep.fromColumnId,
      );
      const toRect = cellRects.find(
        (c) => c.pekerjaanId === dep.toPekerjaanId && c.columnId === dep.toColumnId,
      );
      if (!fromRect || !toRect) return;

      // Canvas-relative coordinates (no scrollLeft, handled by transform)
      const fromX = (fromRect.x - this.pinnedWidth) + fromRect.width;
      const fromY = fromRect.y + fromRect.height / 2;
      const toX = toRect.x - this.pinnedWidth;
      const toY = toRect.y + toRect.height / 2;

      this.ctx.strokeStyle = dep.color || '#94a3b8';
      this.ctx.lineWidth = 1.5;
      this.ctx.beginPath();
      this.ctx.moveTo(fromX, fromY);
      this.ctx.lineTo(toX, toY);
      this.ctx.stroke();

      const arrowSize = 5;
      const angle = Math.atan2(toY - fromY, toX - fromX);
      this.ctx.beginPath();
      this.ctx.moveTo(toX, toY);
      this.ctx.lineTo(toX - arrowSize * Math.cos(angle - Math.PI / 6), toY - arrowSize * Math.sin(angle - Math.PI / 6));
      this.ctx.lineTo(toX - arrowSize * Math.cos(angle + Math.PI / 6), toY - arrowSize * Math.sin(angle + Math.PI / 6));
      this.ctx.closePath();
      this.ctx.fillStyle = dep.color || '#94a3b8';
      this.ctx.fill();
    });
  }

  _resolveVarianceColor(variance) {
    if (!Number.isFinite(variance)) return '#3b82f6';
    if (variance < -0.1) return '#ef4444';
    if (variance > 0.1) return '#22c55e';
    return '#3b82f6';
  }

  _resolveActualColor(variance) {
    const cssVar =
      getCssVar('--gantt-actual-fill') ||
      getCssVar('--bs-warning') ||
      getBtnColor('.progress-mode-tabs .btn-outline-warning') ||
      getBtnColor('.progress-mode-tabs .btn-warning');
    if (cssVar) return cssVar;
    return this._resolveVarianceColor(variance);
  }

  _getPlannedColor() {
    return (
      getCssVar('--gantt-bar-fill') ||
      getCssVar('--bs-info') ||
      getBtnColor('.progress-mode-tabs .btn-outline-info') ||
      getBtnColor('.progress-mode-tabs .btn-info') ||
      '#e2e8f0'
    );
  }

  _bindPointerEvents() {
    this.canvas.addEventListener('mousemove', (e) => {
      if (!this.visible || !this.barRects.length) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = this._hitTest(x, y);
      if (hit) {
        // Format tooltip content for Gantt bar
        const tooltipData = {
          label: `Pekerjaan: ${hit.label || hit.pekerjaanId}`,
          color: hit.color || '#3b82f6',
          weekNumber: null,
          columnId: hit.columnId,
          progress: hit.value,
          weekProgress: hit.planned,
        };
        this.tooltipManager.show(e.clientX, e.clientY, tooltipData);
      } else {
        this.tooltipManager.hide();
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      this.tooltipManager.hide();
    });
  }

  _hitTest(x, y) {
    return this.barRects.find(
      (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height,
    );
  }

  _log(event, payload) {
    if (!this.debug) return;
    console.log(`[GanttOverlay] ${event}`, payload || {});
  }
}
