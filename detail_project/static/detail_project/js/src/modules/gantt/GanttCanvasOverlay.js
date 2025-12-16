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
      z-index: 1;
    `;
    this.ctx = this.canvas.getContext('2d');
    this.mask = document.createElement('div');
    this.mask.className = 'gantt-overlay-mask';
    this.mask.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
      z-index: 10;
      background: var(--grid-frozen-bg, var(--bs-body-bg));
    `;
    this.visible = false;
    this.barData = [];
    this.dependencies = [];
    this.barRects = [];
    this.tooltip = null;
    this.pinnedWidth = 0;
    this.scrollLeft = 0; // Track scroll position for coordinate adjustment
    this._syncScheduled = false; // Track if sync is already scheduled
    this.lastDrawMetrics = { barsDrawn: 0, barsSkipped: 0 };

    const scrollTarget = this.tableManager?.bodyScroll;
    if (scrollTarget) {
      // FIXED: Immediate transform update on scroll (no lag)
      scrollTarget.addEventListener('scroll', () => {
        if (this.visible) {
          // Update transform IMMEDIATELY to prevent overlap on fast scroll
          this._updateTransform();

          // Full sync can be throttled for performance
          if (!this._syncScheduled) {
            this._syncScheduled = true;
            requestAnimationFrame(() => {
              this._syncScheduled = false;
              this.syncWithTable();
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
    scrollArea.style.overflow = 'auto'; // Ensure overflow is clipped

    // Ensure parent clips overflow to avoid covering frozen columns
    const parent = scrollArea.parentElement;
    if (parent) {
      parent.style.overflow = 'hidden';
      parent.style.position = 'relative';
    }

    this._updatePinnedClip();

    if (!this.mask.parentNode) {
      scrollArea.appendChild(this.mask);
    }
    scrollArea.appendChild(this.canvas);
    this.visible = true;
    console.log('[GanttOverlay] ✅ OVERLAY SHOWN - Canvas clipping enabled to prevent overflow');
    this._log('show');
    this.syncWithTable();
  }

  hide() {
    if (!this.visible) return;
    if (this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    if (this.mask.parentNode) {
      this.mask.parentNode.removeChild(this.mask);
    }
    this.visible = false;
    this._log('hide');
    this._hideTooltip();
  }

  _updateTransform() {
    // FIXED: Immediate transform update without full canvas re-render
    // This prevents overlap lag on fast scroll
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    this.scrollLeft = scrollArea.scrollLeft || 0;
    this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;
  }

  syncWithTable() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    this._updatePinnedClip();

    // FIXED: Canvas uses translate to stay aligned while keeping left boundary fixed
    this.scrollLeft = scrollArea.scrollLeft || 0;

    // CRITICAL FIX: Canvas width should be VIEWPORT width, not full scrollWidth
    // Full scrollWidth can exceed browser limits (32,767px) causing blank canvas
    // We only need to render what's visible in the viewport
    const viewportWidth = scrollArea.clientWidth - this.pinnedWidth;
    const MAX_CANVAS_WIDTH = 32000; // Browser safety limit

    this.canvas.width = Math.min(viewportWidth, MAX_CANVAS_WIDTH);
    this.canvas.height = Math.min(scrollArea.clientHeight, 16000); // Height limit too

    // Use transform instead of left to avoid affecting layout
    // Translate compensates for scroll to keep canvas fixed after frozen column
    this.canvas.style.position = 'absolute';
    this.canvas.style.left = `${this.pinnedWidth}px`; // Static: start after frozen
    this.canvas.style.top = '0px';
    this.canvas.style.transform = `translateX(${this.scrollLeft}px)`; // Dynamic: compensate scroll

    // Mask no longer needed since canvas doesn't overlap frozen area
    if (this.mask) {
      this.mask.style.display = 'none';
    }

    const cellRects = typeof this.tableManager.getCellBoundingRects === 'function'
      ? this.tableManager.getCellBoundingRects()
      : [];

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    // Clear and clip to the canvas; mask element handles frozen cover.
    this.ctx.save();
    this.barRects = [];

    console.log('[GanttOverlay] 🔍 SYNC DEBUG:', {
      canvasSize: { w: this.canvas.width, h: this.canvas.height },
      scrollAreaSize: { w: scrollArea.scrollWidth, h: scrollArea.scrollHeight },
      visibleSize: { w: scrollArea.clientWidth, h: scrollArea.clientHeight },
      scroll: { left: scrollArea.scrollLeft, top: scrollArea.scrollTop },
      cellRects: cellRects.length,
      bars: this.barData.length,
    });

    this._log('sync', {
      cells: cellRects.length,
      bars: this.barData.length,
      deps: this.dependencies.length,
      size: { w: this.canvas.width, h: this.canvas.height },
      scroll: { left: scrollArea.scrollLeft, top: scrollArea.scrollTop },
    });

    if (this.barData.length > 0 && cellRects.length === 0) {
      console.error('[GanttOverlay] Have bar data but no cell rects. Overlay cannot draw bars.', {
        bars: this.barData.length,
      });
    }

    // Outline cells only when debugging alignment
    if (this.debug) {
      this.ctx.strokeStyle = '#e2e8f0';
      cellRects.forEach((rect) => {
        // FIXED: Convert to canvas-relative coordinates for debug grid
        // Account for both pinnedWidth and scrollLeft
        const canvasX = rect.x - this.pinnedWidth - this.scrollLeft;

        // Viewport culling: skip cells outside canvas bounds
        if (canvasX < -rect.width || canvasX > this.canvas.width) return;

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
        const rectRight = rect.x + rect.width;
        if (rectRight <= clipLeft || (viewportRight !== null && rect.x >= viewportRight)) {
          barsSkipped += 1;
          return;
        }

        const paddingX = 0; // no gap to keep continuity
        const paddingY = 2;
        const maxWidth = rect.width - paddingX * 2;

        // FIXED: Convert absolute coordinates to canvas-relative coordinates
        // Canvas starts at pinnedWidth and is translated by scrollLeft
        // Canvas is only viewport-width, so we render relative to current viewport
        const baseX = (rect.x - this.pinnedWidth - this.scrollLeft) + paddingX;
        const baseY = rect.y + paddingY;

        // CRITICAL: Skip bars outside canvas bounds (viewport culling)
        // Canvas width is limited to viewport, so skip bars outside
        if (baseX < -rect.width || baseX > this.canvas.width) {
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

      // FIXED: Convert to canvas-relative coordinates
      // Account for both pinnedWidth and scrollLeft
      const fromX = (fromRect.x - this.pinnedWidth - this.scrollLeft) + fromRect.width;
      const fromY = fromRect.y + fromRect.height / 2;
      const toX = toRect.x - this.pinnedWidth - this.scrollLeft;
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
      this._getCssVar('--gantt-actual-fill') ||
      this._getCssVar('--bs-warning') ||
      this._getBtnColor('.progress-mode-tabs .btn-outline-warning') ||
      this._getBtnColor('.progress-mode-tabs .btn-warning');
    if (cssVar) return cssVar;
    return this._resolveVarianceColor(variance);
  }

  _getPlannedColor() {
    return (
      this._getCssVar('--gantt-bar-fill') ||
      this._getCssVar('--bs-info') ||
      this._getBtnColor('.progress-mode-tabs .btn-outline-info') ||
      this._getBtnColor('.progress-mode-tabs .btn-info') ||
      '#e2e8f0'
    );
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
    this.canvas.addEventListener('mousemove', (e) => {
      if (!this.visible || !this.barRects.length) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = this._hitTest(x, y);
      if (hit) {
        this._showTooltip(e.clientX, e.clientY, hit);
      } else {
        this._hideTooltip();
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      this._hideTooltip();
    });
  }

  _hitTest(x, y) {
    return this.barRects.find(
      (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height,
    );
  }

  _ensureTooltip() {
    if (this.tooltip) return this.tooltip;
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'gantt-overlay-tooltip';
    this.tooltip.style.cssText = `
      position: fixed;
      padding: 4px 8px;
      background: rgba(17,24,39,0.85);
      color: #f8fafc;
      border-radius: 4px;
      font-size: 12px;
      pointer-events: none;
      z-index: 20;
      display: none;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    `;
    document.body.appendChild(this.tooltip);
    return this.tooltip;
  }

  _showTooltip(clientX, clientY, hit) {
    const tip = this._ensureTooltip();
    const name = hit.label || hit.pekerjaanId;
    const planned = Number.isFinite(hit.planned) ? `${hit.planned}%` : '-';
    const actual = Number.isFinite(hit.value) ? `${hit.value}%` : '-';
    const variance = Number.isFinite(hit.variance) ? `${hit.variance}%` : '-';
    tip.innerHTML = `Pekerjaan: ${name}<br/>Kolom: ${hit.columnId}<br/>Planned: ${planned}<br/>Actual: ${actual}<br/>Variance: ${variance}`;
    tip.style.left = `${clientX + 10}px`;
    tip.style.top = `${clientY + 10}px`;
    tip.style.display = 'block';
  }

  _hideTooltip() {
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
  }

  _log(event, payload) {
    if (!this.debug) return;
    console.log(`[GanttOverlay] ${event}`, payload || {});
  }
}
